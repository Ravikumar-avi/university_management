# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
import base64
import io
import json
import logging

_logger = logging.getLogger(__name__)

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm, cm
    from reportlab.pdfgen import canvas
    from reportlab.lib import colors
    from reportlab.lib.utils import ImageReader
    from reportlab.graphics.barcode import code128
    from reportlab.graphics.barcode import createBarcodeDrawing
    HAS_REPORTLAB = True
except ImportError:
    HAS_REPORTLAB = False
    _logger.warning('reportlab not installed — OMR PDF generation disabled.')


class OMRSheet(models.Model):
    """
    Per-student OMR answer-evaluation sheet.
    Contains a barcode that encodes the student's registration number,
    name, subject code, and examination reference.
    Each sheet is downloadable as PDF and attached to the answer booklet.
    """
    _name = 'exam.omr.sheet'
    _description = 'Student OMR Sheet'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'serial_number'

    name = fields.Char(string='Reference', compute='_compute_name', store=True)

    serial_number = fields.Char(
        string='SI No.', required=True, copy=False,
        default=lambda self: self.env['ir.sequence'].next_by_code('exam.omr.sheet') or 'NEW',
    )

    # Student
    student_id = fields.Many2one('student.student', string='Student',
                                 required=True, tracking=True, index=True)
    registration_number = fields.Char(related='student_id.registration_number',
                                      string='Registration Number', store=True)
    student_name = fields.Char(related='student_id.name', string='Student Name',
                               store=True)
    student_photo = fields.Binary(related='student_id.student_photo', string='Photo')
    hall_ticket_number = fields.Char(string='Hall Ticket No.',
                                     compute='_compute_hall_ticket_number', store=True)

    # Academic
    program_id = fields.Many2one(related='student_id.program_id', store=True)
    department_id = fields.Many2one(related='student_id.department_id', store=True)
    branch_name = fields.Char(string='Branch', compute='_compute_branch', store=True)

    # Examination
    examination_id = fields.Many2one('examination.examination', string='Examination',
                                     required=True, tracking=True, index=True)
    exam_month_year = fields.Char(string='Month-Year')
    exam_date = fields.Date(string='Date of Exam')

    # Subject
    subject_id = fields.Many2one('university.subject', string='Subject',
                                 required=True, tracking=True)
    subject_code = fields.Char(related='subject_id.code', string='Sub Code', store=True)
    subject_name = fields.Char(related='subject_id.name', string='Sub Name', store=True)

    # OMR Template
    omr_template_id = fields.Many2one('exam.omr.template', string='OMR Template',
                                      required=True, tracking=True)

    # Barcode — encodes student reg no + name + subject + exam info
    barcode_data = fields.Char(string='Barcode Data', compute='_compute_barcode_data',
                               store=True)
    barcode_image = fields.Binary(string='Barcode Image',
                                  compute='_compute_barcode_image', store=True)

    # Generated PDF
    omr_pdf = fields.Binary(string='OMR Sheet PDF', attachment=True)
    omr_pdf_filename = fields.Char(string='PDF Filename')

    # Status
    state = fields.Selection([
        ('draft', 'Draft'),
        ('generated', 'Generated'),
        ('downloaded', 'Downloaded'),
        ('attached', 'Attached to Booklet'),
        ('scanned', 'Scanned'),
    ], string='Status', default='draft', tracking=True)

    download_count = fields.Integer(default=0)

    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)

    _sql_constraints = [
        ('unique_student_exam_subject',
         'unique(student_id, examination_id, subject_id)',
         'OMR sheet already exists for this student, exam, and subject!'),
    ]

    # ------------------------------------------------------------------
    # Computes
    # ------------------------------------------------------------------
    @api.depends('student_id', 'subject_id', 'serial_number')
    def _compute_name(self):
        for rec in self:
            parts = [rec.serial_number or '']
            if rec.student_id:
                parts.append(rec.student_id.registration_number or rec.student_id.name or '')
            if rec.subject_id:
                parts.append(rec.subject_id.code or '')
            rec.name = ' - '.join(filter(None, parts))

    @api.depends('department_id')
    def _compute_branch(self):
        for rec in self:
            rec.branch_name = rec.department_id.name if rec.department_id else ''

    @api.depends('student_id', 'examination_id')
    def _compute_hall_ticket_number(self):
        for rec in self:
            hall_ticket = False
            if rec.student_id and rec.examination_id:
                hall_ticket = self.env['examination.hall.ticket'].search([
                    ('student_id', '=', rec.student_id.id),
                    ('examination_id', '=', rec.examination_id.id),
                ], limit=1)
            rec.hall_ticket_number = hall_ticket.name if hall_ticket else ''

    @api.depends('student_id', 'examination_id', 'subject_id', 'serial_number',
                 'registration_number', 'student_name', 'hall_ticket_number')
    def _compute_barcode_data(self):
        """
        Encode student info into a compact string for barcode generation.
        Format: REG|NAME|SUBCODE|EXAMID|SERIAL
        """
        for rec in self:
            if rec.student_id and rec.examination_id and rec.subject_id:
                data = '|'.join([
                    rec.registration_number or '',
                    (rec.student_name or '')[:30],
                    rec.subject_id.code or '',
                    str(rec.examination_id.id),
                    rec.serial_number or '',
                    rec.hall_ticket_number or '',
                ])
                rec.barcode_data = data
            else:
                rec.barcode_data = False

    @api.depends('barcode_data')
    def _compute_barcode_image(self):
        for rec in self:
            if rec.barcode_data:
                try:
                    barcode_drawing = createBarcodeDrawing(
                        'Code128', value=rec.barcode_data,
                        width=250, height=40,
                        humanReadable=False,
                    )
                    buf = io.BytesIO()
                    barcode_drawing.save(formats=['png'], outDir=None, fnRoot=None)
                    from reportlab.graphics import renderPM
                    renderPM.drawToFile(barcode_drawing, buf, fmt='PNG')
                    rec.barcode_image = base64.b64encode(buf.getvalue())
                except Exception as e:
                    _logger.warning('Barcode generation failed for OMR %s: %s',
                                    rec.serial_number, e)
                    rec.barcode_image = False
            else:
                rec.barcode_image = False

    # ------------------------------------------------------------------
    # PDF Generation
    # ------------------------------------------------------------------
    def action_generate_pdf(self):
        """Generate the OMR sheet PDF with barcode, student info, and marks grid."""
        self.ensure_one()
        if not HAS_REPORTLAB:
            raise UserError(_('reportlab is not installed. Please install it to generate OMR PDFs.'))

        pdf_data = self._render_omr_pdf()
        filename = f"OMR_{self.serial_number}_{self.registration_number}.pdf"
        self.write({
            'omr_pdf': base64.b64encode(pdf_data),
            'omr_pdf_filename': filename,
            'state': 'generated',
        })

    def action_download(self):
        self.ensure_one()
        if not self.omr_pdf:
            self.action_generate_pdf()
        self.write({
            'download_count': self.download_count + 1,
            'state': 'downloaded',
        })
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content?model=exam.omr.sheet&id={self.id}'
                   f'&field=omr_pdf&filename_field=omr_pdf_filename&download=true',
            'target': 'self',
        }

    def action_mark_attached(self):
        self.write({'state': 'attached'})

    def action_reset_draft(self):
        self.write({'state': 'draft'})

    # ------------------------------------------------------------------
    # Internal PDF builder
    # ------------------------------------------------------------------
    def _render_omr_pdf(self):
        """Build a single-page OMR sheet PDF matching the uploaded image format."""
        buf = io.BytesIO()
        c = canvas.Canvas(buf, pagesize=A4)
        width, height = A4  # 595.27 × 841.89 points

        grid_config = self.omr_template_id.get_grid_config()

        # ----- Company Logo (from res.company, not a separate upload) -----
        company_logo = self.omr_template_id.company_id.logo
        if company_logo:
            try:
                logo_bytes = base64.b64decode(company_logo)
                logo_img = ImageReader(io.BytesIO(logo_bytes))
                c.drawImage(logo_img, 40, height - 65, width=45, height=45,
                            preserveAspectRatio=True, anchor='c', mask='auto')
            except Exception as e:
                _logger.warning('Logo render failed for OMR %s: %s', self.serial_number, e)

        # ----- Header -----
        y = height - 30
        c.setFont('Helvetica-Bold', 11)
        inst = self.omr_template_id.institution_name or 'INSTITUTION NAME'
        c.drawCentredString(width / 2, y, inst)
        y -= 14
        c.setFont('Helvetica', 8)
        subtitle = self.omr_template_id.institution_subtitle or ''
        if subtitle:
            c.drawCentredString(width / 2, y, subtitle)
            y -= 12

        # ----- SI No + Barcode -----
        y -= 10
        c.setFont('Helvetica-Bold', 10)
        c.drawString(40, y, f"SI No.: {self.serial_number}")

        # Draw barcode
        if self.barcode_data:
            try:
                barcode_obj = code128.Code128(
                    self.barcode_data, barWidth=0.8, barHeight=25,
                )
                barcode_obj.drawOn(c, 120, y - 20)
            except Exception:
                pass

        # ----- Student Info -----
        y -= 50
        c.setFont('Helvetica', 9)
        info_lines = [
            ('Hall Ticket No.:', self.hall_ticket_number or ''),
            ('Name:', self.student_name or ''),
            ('Examination:', self.examination_id.name or ''),
            ('Month-Year:', self.exam_month_year or ''),
            ('Branch:', self.branch_name or ''),
            ('Sub Code:', self.subject_code or ''),
            ('Sub Name:', self.subject_name or ''),
            ('Date of Exam:', str(self.exam_date) if self.exam_date else ''),
        ]
        for label, val in info_lines:
            c.setFont('Helvetica-Bold', 8)
            c.drawString(40, y, label)
            c.setFont('Helvetica', 8)
            c.drawString(140, y, val)
            y -= 14

        # ----- Student Photo -----
        photo_x, photo_y, photo_w, photo_h = width - 120, height - 160, 80, 100
        if self.student_photo:
            try:
                photo_bytes = base64.b64decode(self.student_photo)
                photo_img = ImageReader(io.BytesIO(photo_bytes))
                c.drawImage(photo_img, photo_x, photo_y, width=photo_w, height=photo_h,
                            preserveAspectRatio=True, anchor='c', mask='auto')
                c.rect(photo_x, photo_y, photo_w, photo_h)
            except Exception as e:
                _logger.warning('Photo render failed for OMR %s: %s', self.serial_number, e)
                c.rect(photo_x, photo_y, photo_w, photo_h)
                c.setFont('Helvetica', 7)
                c.drawCentredString(photo_x + photo_w / 2, photo_y - 10, 'Photo')
        else:
            c.rect(photo_x, photo_y, photo_w, photo_h)
            c.setFont('Helvetica', 7)
            c.drawCentredString(photo_x + photo_w / 2, photo_y - 10, 'Photo')

        # ----- Signature boxes -----
        sig_y = y - 5
        c.setFont('Helvetica', 7)
        c.drawString(width - 200, sig_y, 'Signature of the Controller of Exams')
        c.drawString(width - 200, sig_y - 14, 'Signature of the Student with date')
        c.drawString(width - 200, sig_y - 28, 'Signature of the Invigilator with date')

        # =====================================================================
        # MARKS GRID (Valuation sections)
        # =====================================================================
        for copy_num in range(1, grid_config['valuation_copies'] + 1):
            y -= 50
            c.setLineWidth(0.5)

            # Section header
            c.setFont('Helvetica-Bold', 9)
            c.drawCentredString(width / 2, y, inst)
            y -= 14

            part_label = f"PART - {'III' if copy_num == 2 else 'II'}"
            val_label = f"{'Re-Valuation' if copy_num == 2 else 'Valuation'}"
            c.setFont('Helvetica-Bold', 8)
            c.drawString(width - 120, y + 10, part_label)
            c.drawString(width - 120, y - 4, val_label)
            c.drawCentredString(width - 100, y - 18, str(copy_num))

            # Mini student info
            y -= 10
            c.setFont('Helvetica', 7)
            mini_info = [
                ('Examination:', self.examination_id.name or ''),
                ('Month-Year:', self.exam_month_year or ''),
                ('Branch:', self.branch_name or ''),
                ('Sub Code:', self.subject_code or ''),
                ('Sub Name:', self.subject_name or ''),
                ('Date of Exam:', str(self.exam_date) if self.exam_date else ''),
            ]
            for label, val in mini_info:
                c.setFont('Helvetica-Bold', 6)
                c.drawString(40, y, label)
                c.setFont('Helvetica', 6)
                c.drawString(110, y, val)
                y -= 10

            # Draw the marks grid based on format
            y = self._draw_marks_grid(c, 40, y - 10, width - 80, grid_config)

            # Examiner / Scrutinizer signature
            y -= 15
            c.setFont('Helvetica', 6)
            c.drawString(40, y, "Examiner's Name & Signature")
            c.drawString(250, y, "Scrutinizer's Name & Signature")
            c.drawString(400, y, "Marks in Words")

            y -= 5

        c.save()
        return buf.getvalue()

    def _draw_marks_grid(self, c, x, y, avail_width, grid_config):
        """Draw the question marks grid. Returns the new y position."""
        cell_w = 18
        cell_h = 14
        fmt = grid_config['format']

        if fmt == 'r20':
            # Part-A header
            parts = grid_config['parts']
            for part in parts:
                c.setFont('Helvetica-Bold', 7)
                c.drawString(x, y, part.get('label', 'PART'))
                y -= 4

                if part['name'] == 'part_a':
                    # Columns: Q.No, A, B, C, D, E, F, G, H, I, J, Total
                    cols = part.get('columns', 10)
                    headers = ['Q.No'] + [chr(65 + i) for i in range(cols)] + ['Total']
                    for i, h in enumerate(headers):
                        cx = x + i * cell_w
                        c.rect(cx, y - cell_h, cell_w, cell_h)
                        c.setFont('Helvetica-Bold', 5)
                        c.drawCentredString(cx + cell_w / 2, y - cell_h + 3, h)
                    y -= cell_h
                    # One row for question 1
                    for row in range(part.get('rows', 1)):
                        c.rect(x, y - cell_h, cell_w, cell_h)
                        c.setFont('Helvetica', 5)
                        c.drawCentredString(x + cell_w / 2, y - cell_h + 3, str(row + 1))
                        for i in range(cols + 1):
                            cx = x + (i + 1) * cell_w
                            c.rect(cx, y - cell_h, cell_w, cell_h)
                        y -= cell_h

                elif part['name'] in ('part_b', 'main'):
                    # Columns: Q.No, a, b, c, d, Total, Q.No, a, b, c, d, Total, BEST
                    sub = part.get('sub_parts', 4)
                    q_count = part.get('questions', 12)
                    sub_labels = [chr(97 + i) for i in range(sub)]

                    # Header row
                    headers_left = ['Q.No'] + sub_labels + ['Total']
                    headers_right = ['Q.No'] + sub_labels + ['Total', 'BEST']
                    col_count_left = len(headers_left)
                    col_count_right = len(headers_right)

                    for i, h in enumerate(headers_left):
                        cx = x + i * cell_w
                        c.rect(cx, y - cell_h, cell_w, cell_h)
                        c.setFont('Helvetica-Bold', 5)
                        c.drawCentredString(cx + cell_w / 2, y - cell_h + 3, h)
                    offset_right = x + col_count_left * cell_w + 5
                    for i, h in enumerate(headers_right):
                        cx = offset_right + i * cell_w
                        c.rect(cx, y - cell_h, cell_w, cell_h)
                        c.setFont('Helvetica-Bold', 5)
                        c.drawCentredString(cx + cell_w / 2, y - cell_h + 3, h)
                    y -= cell_h

                    # Question rows in pairs
                    for row in range(0, q_count, 2):
                        q_left = row + 1
                        q_right = row + 2
                        # Left
                        c.rect(x, y - cell_h, cell_w, cell_h)
                        c.setFont('Helvetica', 5)
                        c.drawCentredString(x + cell_w / 2, y - cell_h + 3, str(q_left))
                        for i in range(sub + 1):
                            cx = x + (i + 1) * cell_w
                            c.rect(cx, y - cell_h, cell_w, cell_h)
                        # Right
                        if q_right <= q_count:
                            c.rect(offset_right, y - cell_h, cell_w, cell_h)
                            c.drawCentredString(offset_right + cell_w / 2, y - cell_h + 3,
                                                str(q_right))
                            for i in range(sub + 2):  # +2 for Total and BEST
                                cx = offset_right + (i + 1) * cell_w
                                c.rect(cx, y - cell_h, cell_w, cell_h)
                        y -= cell_h

                    # Grand Total row
                    c.setFont('Helvetica-Bold', 6)
                    c.drawString(offset_right, y - cell_h + 3, 'GRAND TOTAL')
                    c.rect(offset_right + (sub + 1) * cell_w, y - cell_h,
                           cell_w * 2, cell_h)
                    y -= cell_h

                y -= 5

        else:
            # R22 or custom — single grid with Q.No, a, b, c, d, Total pairs
            parts = grid_config['parts']
            for part in parts:
                sub = part.get('sub_parts', 4)
                q_count = part.get('questions', 10)
                sub_labels = [chr(97 + i) for i in range(sub)]

                # Header
                headers_left = ['Q.No'] + sub_labels + ['Total']
                headers_right = ['Q.No'] + sub_labels + ['Total', 'BEST']
                col_left = len(headers_left)

                for i, h in enumerate(headers_left):
                    cx = x + i * cell_w
                    c.rect(cx, y - cell_h, cell_w, cell_h)
                    c.setFont('Helvetica-Bold', 5)
                    c.drawCentredString(cx + cell_w / 2, y - cell_h + 3, h)
                offset_r = x + col_left * cell_w + 5
                for i, h in enumerate(headers_right):
                    cx = offset_r + i * cell_w
                    c.rect(cx, y - cell_h, cell_w, cell_h)
                    c.setFont('Helvetica-Bold', 5)
                    c.drawCentredString(cx + cell_w / 2, y - cell_h + 3, h)
                y -= cell_h

                for row in range(0, q_count, 2):
                    q_l = row + 1
                    q_r = row + 2
                    c.rect(x, y - cell_h, cell_w, cell_h)
                    c.setFont('Helvetica', 5)
                    c.drawCentredString(x + cell_w / 2, y - cell_h + 3, str(q_l))
                    for i in range(sub + 1):
                        c.rect(x + (i + 1) * cell_w, y - cell_h, cell_w, cell_h)

                    if q_r <= q_count:
                        c.rect(offset_r, y - cell_h, cell_w, cell_h)
                        c.drawCentredString(offset_r + cell_w / 2, y - cell_h + 3,
                                            str(q_r))
                        for i in range(sub + 2):
                            c.rect(offset_r + (i + 1) * cell_w, y - cell_h, cell_w, cell_h)
                    y -= cell_h

                # Grand Total
                c.setFont('Helvetica-Bold', 6)
                c.drawString(offset_r, y - cell_h + 3, 'GRAND TOTAL')
                c.rect(offset_r + (sub + 1) * cell_w, y - cell_h, cell_w * 2, cell_h)
                y -= cell_h

        return y