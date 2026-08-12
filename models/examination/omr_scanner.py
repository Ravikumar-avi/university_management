# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
import base64
import io
import json
import logging
import re

_logger = logging.getLogger(__name__)

# Optional imports — gracefully degrade when not installed OR when
# native/system dependencies (DLLs on Windows, .so on Linux) are missing.
# NOTE: pyzbar and pytesseract can raise more than ImportError at import
# time — e.g. pyzbar raises FileNotFoundError/OSError when libzbar's
# native library isn't found on the system, which would otherwise crash
# the entire Odoo module load. We must catch broadly here.
try:
    from PIL import Image, ImageFilter, ImageEnhance
    HAS_PIL = True
except Exception as e:
    HAS_PIL = False
    _logger.warning('Pillow (PIL) not available — OMR image processing disabled: %s', e)

try:
    from pyzbar.pyzbar import decode as pyzbar_decode
    HAS_PYZBAR = True
except Exception as e:
    HAS_PYZBAR = False
    _logger.warning(
        'pyzbar not available — barcode decoding disabled. '
        'On Windows this usually means the libzbar DLL is missing '
        '(install the zbar shared libraries, e.g. via the '
        '"pyzbar[scripts]" extra or by placing libzbar-64.dll on PATH). '
        'Detail: %s', e
    )

try:
    import pytesseract
    HAS_TESSERACT = True
except Exception as e:
    HAS_TESSERACT = False
    _logger.warning(
        'pytesseract not available — OCR marks detection disabled. '
        'Ensure the Tesseract OCR engine is installed and on PATH. '
        'Detail: %s', e
    )


class OMRScanner(models.Model):
    """
    Scanned OMR answer-sheet processor.
    1. Upload the scanned image / PDF of the corrected OMR sheet.
    2. OCR reads the barcode → identifies the student + subject + exam.
    3. OCR detects the handwritten marks in the grid cells
       (question-wise a, b, c, d and grand total).
    4. Marks are written back to the examination.result record.
    5. The scanned document is saved as an attachment.
    """
    _name = 'exam.omr.scanner'
    _description = 'OMR Sheet Scanner (OCR)'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'scan_date desc'

    name = fields.Char(string='Scan Reference',
                       default=lambda self: self.env['ir.sequence'].next_by_code('exam.omr.scanner') or 'NEW',
                       required=True, copy=False)

    # ---- Upload ----
    scanned_file = fields.Binary(string='Scanned OMR Sheet', required=True,
                                 attachment=True,
                                 help='Upload the scanned image (JPEG/PNG) or PDF of the corrected OMR sheet.')
    scanned_filename = fields.Char(string='Filename')
    scan_date = fields.Datetime(string='Scan Date', default=fields.Datetime.now)

    # ---- Barcode-decoded info ----
    barcode_raw = fields.Char(string='Barcode Raw Data', readonly=True)
    decoded_registration = fields.Char(string='Registration No. (decoded)', readonly=True)
    decoded_student_name = fields.Char(string='Student Name (decoded)', readonly=True)
    decoded_subject_code = fields.Char(string='Subject Code (decoded)', readonly=True)
    decoded_exam_id = fields.Integer(string='Examination ID (decoded)', readonly=True)
    decoded_serial = fields.Char(string='OMR Serial (decoded)', readonly=True)
    decoded_hall_ticket = fields.Char(string='Hall Ticket (decoded)', readonly=True)

    # ---- Linked records (auto-resolved from barcode) ----
    student_id = fields.Many2one('student.student', string='Student', readonly=True,
                                 tracking=True)
    examination_id = fields.Many2one('examination.examination', string='Examination',
                                     readonly=True, tracking=True)
    subject_id = fields.Many2one('university.subject', string='Subject',
                                 readonly=True, tracking=True)
    omr_sheet_id = fields.Many2one('exam.omr.sheet', string='OMR Sheet',
                                   readonly=True)
    result_id = fields.Many2one('examination.result', string='Result Record',
                                readonly=True, tracking=True)

    # ---- OCR-detected marks ----
    detected_marks_json = fields.Text(
        string='Detected Marks (JSON)', readonly=True,
        help='JSON dict of question-wise marks as detected by OCR.',
    )
    detected_grand_total = fields.Integer(string='Detected Grand Total', readonly=True)

    # Editable fields for manual correction before confirmation
    question_marks_display = fields.Text(
        string='Question-wise Marks',
        help='Edit if OCR detection was incorrect. Format: Q1a=5, Q1b=3 …',
    )
    grand_total = fields.Integer(string='Grand Total Marks')

    # ---- Valuation part detected ----
    valuation_part = fields.Selection([
        ('valuation_1', 'Valuation 1 (Part-II)'),
        ('revaluation', 'Re-Valuation (Part-III)'),
    ], string='Valuation Part', default='valuation_1')

    # ---- Status ----
    state = fields.Selection([
        ('draft', 'Uploaded'),
        ('decoded', 'Barcode Decoded'),
        ('ocr_done', 'Marks Detected'),
        ('confirmed', 'Confirmed & Updated'),
        ('failed', 'Failed'),
    ], string='Status', default='draft', tracking=True)

    error_message = fields.Text(string='Error / Warnings', readonly=True)

    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)

    # ==================================================================
    # 1. DECODE BARCODE
    # ==================================================================
    def action_decode_barcode(self):
        """Read the barcode from the scanned image to identify the student."""
        self.ensure_one()
        if not self.scanned_file:
            raise UserError(_('Please upload a scanned OMR sheet first.'))

        if not HAS_PYZBAR and not HAS_TESSERACT:
            raise UserError(_(
                'Barcode decoding is unavailable on this server: neither '
                'pyzbar nor pytesseract could be loaded. Check the server '
                'log at startup for the exact reason (commonly a missing '
                'native library — libzbar on Linux/Mac, libzbar-64.dll on '
                'Windows — or a missing Tesseract OCR installation).'
            ))
        if not HAS_PYZBAR:
            _logger.info(
                'pyzbar unavailable, falling back to Tesseract text '
                'recognition for barcode data (less reliable).'
            )

        img = self._get_image()
        if img is None:
            raise UserError(_('Could not read the uploaded file as an image.'))

        barcode_data = self._read_barcode(img)
        if not barcode_data:
            self.write({
                'state': 'failed',
                'error_message': 'No barcode detected in the scanned image. '
                                 'Please ensure the barcode area is clearly visible.',
            })
            return

        # Parse barcode: REG|NAME|SUBCODE|EXAMID|SERIAL|HALLTICKET
        parts = barcode_data.split('|')
        vals = {
            'barcode_raw': barcode_data,
            'decoded_registration': parts[0] if len(parts) > 0 else '',
            'decoded_student_name': parts[1] if len(parts) > 1 else '',
            'decoded_subject_code': parts[2] if len(parts) > 2 else '',
            'decoded_exam_id': int(parts[3]) if len(parts) > 3 and parts[3].isdigit() else 0,
            'decoded_serial': parts[4] if len(parts) > 4 else '',
            'decoded_hall_ticket': parts[5] if len(parts) > 5 else '',
        }

        # Resolve linked records
        student = self.env['student.student'].search([
            ('registration_number', '=', vals['decoded_registration']),
        ], limit=1)
        if student:
            vals['student_id'] = student.id

        if vals['decoded_exam_id']:
            exam = self.env['examination.examination'].browse(vals['decoded_exam_id'])
            if exam.exists():
                vals['examination_id'] = exam.id

        subject = self.env['university.subject'].search([
            ('code', '=', vals['decoded_subject_code']),
        ], limit=1)
        if subject:
            vals['subject_id'] = subject.id

        # Find OMR sheet
        omr = self.env['exam.omr.sheet'].search([
            ('serial_number', '=', vals.get('decoded_serial', '')),
        ], limit=1)
        if omr:
            vals['omr_sheet_id'] = omr.id

        vals['state'] = 'decoded'
        vals['error_message'] = False
        self.write(vals)

    # ==================================================================
    # 2. OCR — DETECT HANDWRITTEN MARKS
    # ==================================================================
    def action_detect_marks(self):
        """
        Run OCR on the marks grid area to detect handwritten digits
        in each cell (question-wise) and the grand total.
        """
        self.ensure_one()
        if self.state not in ('decoded', 'ocr_done'):
            raise UserError(_('Please decode the barcode first.'))

        if not HAS_TESSERACT:
            raise UserError(_(
                'pytesseract is not installed on the server. '
                'Install it with: pip install pytesseract\n'
                'Also ensure Tesseract OCR engine is installed on the OS.'
            ))

        img = self._get_image()
        if img is None:
            raise UserError(_('Could not read the uploaded file.'))

        marks_data, grand_total = self._ocr_marks_grid(img)

        display_lines = []
        for key in sorted(marks_data.keys()):
            display_lines.append(f"{key}={marks_data[key]}")

        self.write({
            'detected_marks_json': json.dumps(marks_data, indent=2),
            'detected_grand_total': grand_total,
            'question_marks_display': ', '.join(display_lines),
            'grand_total': grand_total,
            'state': 'ocr_done',
            'error_message': False,
        })

    # ==================================================================
    # 3. CONFIRM & UPDATE RESULT
    # ==================================================================
    def action_confirm_marks(self):
        """
        Write the confirmed marks to the examination.result record
        and save the scanned document as an attachment.
        """
        self.ensure_one()
        if not self.student_id:
            raise UserError(_('Student not identified. Please decode barcode or set manually.'))
        if not self.examination_id:
            raise UserError(_('Examination not identified.'))

        # Find or create the result record
        result = self.env['examination.result'].search([
            ('student_id', '=', self.student_id.id),
            ('examination_id', '=', self.examination_id.id),
            ('subject_id', '=', self.subject_id.id) if self.subject_id else (1, '=', 1),
        ], limit=1)

        if result:
            result.write({
                'external_marks': self.grand_total,
                'evaluation_date': fields.Date.today(),
            })
            self.result_id = result.id
        else:
            # Log warning — result record not found
            self.write({
                'error_message': _(
                    'No existing result record found for student %s, exam %s, subject %s. '
                    'Please create the result record first or enter marks manually.',
                    self.student_id.name,
                    self.examination_id.name,
                    self.subject_id.name if self.subject_id else '(unknown)',
                ),
            })

        # Save scanned file as attachment on the result (and OMR sheet)
        if self.scanned_file:
            attachment_vals = {
                'name': self.scanned_filename or f'OMR_Scan_{self.name}',
                'type': 'binary',
                'datas': self.scanned_file,
                'res_model': 'examination.result',
                'res_id': result.id if result else False,
                'mimetype': 'image/jpeg',
            }
            self.env['ir.attachment'].create(attachment_vals)

            # Also attach to OMR sheet record
            if self.omr_sheet_id:
                self.env['ir.attachment'].create({
                    'name': self.scanned_filename or f'OMR_Scan_{self.name}',
                    'type': 'binary',
                    'datas': self.scanned_file,
                    'res_model': 'exam.omr.sheet',
                    'res_id': self.omr_sheet_id.id,
                    'mimetype': 'image/jpeg',
                })
                self.omr_sheet_id.write({'state': 'scanned'})

        # Save question-wise marks as a note on the result
        if result and self.question_marks_display:
            result.message_post(
                body=_(
                    '<b>Question-wise marks (OCR scan %s):</b><br/>%s<br/>'
                    '<b>Grand Total:</b> %s',
                    self.name,
                    self.question_marks_display.replace(',', '<br/>'),
                    self.grand_total,
                ),
            )

        self.write({'state': 'confirmed', 'error_message': False})

    def action_reset_draft(self):
        self.write({'state': 'draft', 'error_message': False})

    # ==================================================================
    # Batch processing
    # ==================================================================
    def action_process_all(self):
        """One-click: decode barcode → detect marks → confirm."""
        self.ensure_one()
        self.action_decode_barcode()
        if self.state == 'decoded':
            self.action_detect_marks()
        if self.state == 'ocr_done':
            self.action_confirm_marks()

    # ==================================================================
    # INTERNAL HELPERS
    # ==================================================================
    def _get_image(self):
        """Return a PIL Image from the uploaded binary field."""
        if not HAS_PIL:
            _logger.error('Pillow (PIL) not installed.')
            return None
        try:
            data = base64.b64decode(self.scanned_file)
            return Image.open(io.BytesIO(data))
        except Exception as e:
            _logger.warning('Failed to open scanned file: %s', e)
            return None

    def _read_barcode(self, img):
        """
        Attempt to read barcodes from the image using pyzbar.
        Falls back to pytesseract if pyzbar is not available.
        """
        if HAS_PYZBAR:
            try:
                # Try multiple preprocessing approaches
                for attempt_img in self._preprocess_for_barcode(img):
                    decoded = pyzbar_decode(attempt_img)
                    for obj in decoded:
                        data = obj.data.decode('utf-8', errors='ignore')
                        if '|' in data:
                            return data
                # If no pipe-delimited barcode found, return first barcode
                decoded = pyzbar_decode(img)
                if decoded:
                    return decoded[0].data.decode('utf-8', errors='ignore')
            except Exception as e:
                _logger.warning('pyzbar decode failed: %s', e)

        # Fallback: try tesseract to read barcode number as text
        if HAS_TESSERACT:
            try:
                # Crop top portion where barcode usually is
                w, h = img.size
                top_crop = img.crop((0, 0, w, int(h * 0.15)))
                text = pytesseract.image_to_string(top_crop, config='--psm 6')
                # Look for pipe-delimited pattern
                for line in text.split('\n'):
                    if '|' in line and len(line.split('|')) >= 3:
                        return line.strip()
            except Exception as e:
                _logger.warning('Tesseract barcode fallback failed: %s', e)

        return None

    def _preprocess_for_barcode(self, img):
        """Yield preprocessed versions of the image for better barcode detection."""
        # Original
        yield img
        # Grayscale
        gray = img.convert('L')
        yield gray
        # High contrast
        enhancer = ImageEnhance.Contrast(gray)
        yield enhancer.enhance(2.0)
        # Sharpened
        yield gray.filter(ImageFilter.SHARPEN)
        # Binarized
        threshold = 128
        yield gray.point(lambda p: 255 if p > threshold else 0, '1')

    def _ocr_marks_grid(self, img):
        """
        Detect handwritten digits in the marks grid area.
        Returns (marks_dict, grand_total).

        Strategy:
        - Convert to grayscale, enhance contrast.
        - Use Tesseract with digit-only whitelist.
        - Parse the output looking for numbers in grid positions.
        """
        if not HAS_TESSERACT:
            return {}, 0

        w, h = img.size

        # The marks grid is typically in the lower 60% of the page
        # (below the header / student info)
        grid_region = img.crop((0, int(h * 0.35), w, h))

        # Preprocess
        gray = grid_region.convert('L')
        enhancer = ImageEnhance.Contrast(gray)
        enhanced = enhancer.enhance(2.5)
        sharpened = enhanced.filter(ImageFilter.SHARPEN)

        # Binarize for better OCR
        threshold = 140
        binary = sharpened.point(lambda p: 255 if p > threshold else 0, 'L')

        # OCR with digit-only config
        custom_config = r'--oem 3 --psm 6 -c tessedit_char_whitelist=0123456789'
        try:
            # Use image_to_data for positional information
            data = pytesseract.image_to_data(
                binary, config=custom_config, output_type=pytesseract.Output.DICT
            )
        except Exception as e:
            _logger.warning('Tesseract OCR failed: %s', e)
            return {}, 0

        # Collect detected numbers with their positions
        numbers = []
        for i in range(len(data['text'])):
            text = data['text'][i].strip()
            conf = int(data['conf'][i]) if data['conf'][i] != '-1' else 0
            if text and conf > 30:
                try:
                    val = int(text)
                    numbers.append({
                        'value': val,
                        'x': data['left'][i],
                        'y': data['top'][i],
                        'w': data['width'][i],
                        'h': data['height'][i],
                        'conf': conf,
                    })
                except ValueError:
                    pass

        # Sort by position (top-to-bottom, left-to-right)
        numbers.sort(key=lambda n: (n['y'] // 20, n['x']))

        # Build marks dict — heuristic mapping based on grid layout
        marks_dict = {}
        grand_total = 0
        q_num = 1
        sub_idx = 0
        sub_labels = ['a', 'b', 'c', 'd']

        for n in numbers:
            # Numbers > 100 likely are grand total
            if n['value'] > 100:
                grand_total = n['value']
                continue

            # Map to question + sub-part
            key = f"Q{q_num}{sub_labels[sub_idx] if sub_idx < len(sub_labels) else ''}"
            marks_dict[key] = n['value']

            sub_idx += 1
            if sub_idx >= len(sub_labels):
                sub_idx = 0
                q_num += 1

        # If grand total not found, sum all values
        if grand_total == 0:
            grand_total = sum(marks_dict.values())

        return marks_dict, grand_total

    # ==================================================================
    # Bulk scan wizard entry point
    # ==================================================================
    @api.model
    def action_open_bulk_scan(self):
        """Open the bulk scanning wizard."""
        return {
            'type': 'ir.actions.act_window',
            'name': _('Bulk OMR Scan'),
            'res_model': 'exam.omr.bulk.scan.wizard',
            'view_mode': 'form',
            'target': 'new',
        }