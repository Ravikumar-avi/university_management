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
        Encode the OMR's serial number only. This is the actual physical
        lookup key printed under the barcode on the real sheet (SI No.),
        and keeping it short is what keeps the printed barcode narrow —
        encoding the full REG|NAME|SUBCODE|EXAMID|SERIAL|HALLTICKET string
        here is what was stretching the barcode across the page.
        Full student/exam context is still looked up from serial_number
        on scan — nothing else needs to be embedded in the symbol.
        """
        for rec in self:
            if rec.student_id and rec.examination_id and rec.subject_id:
                rec.barcode_data = rec.serial_number or ''
            else:
                rec.barcode_data = False

    @api.depends('barcode_data')
    def _compute_barcode_image(self):
        """Best-effort PNG preview for the form-view thumbnail only.
        Rendering to PNG needs reportlab's renderPM backend, which isn't
        always available on every server — the actual printed PDF does
        NOT depend on this field, it draws the barcode as vector shapes
        directly (see _draw_hall_ticket_strip), so a failure here never
        affects the generated sheet."""
        for rec in self:
            if rec.barcode_data and HAS_REPORTLAB:
                try:
                    from reportlab.graphics import renderPM
                    barcode_drawing = createBarcodeDrawing(
                        'Code128', value=rec.barcode_data,
                        barHeight=9 * mm,
                        humanReadable=False,
                    )
                    buf = io.BytesIO()
                    renderPM.drawToFile(barcode_drawing, buf, fmt='PNG')
                    rec.barcode_image = base64.b64encode(buf.getvalue())
                except Exception as e:
                    _logger.info('Barcode preview image skipped for OMR %s: %s',
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
    PAGE_W = 595
    PAGE_H = 950
    MARGIN = 22
    STRIP_W = 14          # left tear-off strip width
    RIGHT_COL_W = 150     # "For Office Use" / bubble-panel column width
    BUNDLE_COL_W = 20     # far-right "Control Bundle Number" strip

    def _render_omr_pdf(self):
        """Build a single-page OMR sheet PDF replicating the printed
        LENDI OMR bundle: tear-off hall-ticket strip on top, followed by
        one bordered valuation section per copy — each with its own
        PART-A/PART-B grid, Total-Marks bubble column, SI-No-of-Answer-
        Book bubble column and Control-Bundle-Number strip, exactly like
        the physical sheet."""
        buf = io.BytesIO()
        c = canvas.Canvas(buf, pagesize=(self.PAGE_W, self.PAGE_H))
        width, height = self.PAGE_W, self.PAGE_H

        grid_config = self.omr_template_id.get_grid_config()
        inst = self.omr_template_id.institution_name or 'INSTITUTION NAME'
        subtitle = self.omr_template_id.institution_subtitle or ''
        accreditation = self.omr_template_id.institution_accreditation or ''
        company_logo = self.omr_template_id.company_id.logo

        section_top = height - self.MARGIN
        section_top = self._draw_hall_ticket_strip(c, section_top, inst, subtitle,
                                                     accreditation, company_logo)

        for copy_num in range(1, grid_config['valuation_copies'] + 1):
            self._draw_cut_line(c, section_top + 6)
            section_top = self._draw_valuation_section(
                c, section_top, copy_num, grid_config, inst, company_logo)

        c.save()
        return buf.getvalue()

    # ------------------------------------------------------------------
    # Small drawing helpers
    # ------------------------------------------------------------------
    def _wrap_text(self, c, text, font, size, max_width):
        """Word-wrap text to fit within max_width, returns list of lines."""
        if not text:
            return ['']
        words = text.split()
        lines, cur = [], ''
        for wd in words:
            trial = (cur + ' ' + wd).strip()
            if c.stringWidth(trial, font, size) > max_width and cur:
                lines.append(cur)
                cur = wd
            else:
                cur = trial
        if cur:
            lines.append(cur)
        return lines or ['']

    def _draw_vtext(self, c, x, y, text, font='Helvetica-Bold', size=7):
        c.saveState()
        c.translate(x, y)
        c.rotate(90)
        c.setFont(font, size)
        c.drawCentredString(0, 0, text)
        c.restoreState()

    def _draw_tear_strip(self, c, x, y_top, y_bottom, label):
        """Left tear-off strip: dashed cut line + rotated label, like the
        perforated edge on the printed bundle."""
        c.setDash(2, 2)
        c.setLineWidth(0.6)
        c.line(x + self.STRIP_W, y_top, x + self.STRIP_W, y_bottom)
        c.setDash()
        c.rect(x, y_bottom, self.STRIP_W, y_top - y_bottom)
        if label:
            self._draw_vtext(c, x + self.STRIP_W / 2, y_top - 15, label, size=8)

    def _draw_cut_line(self, c, y):
        """Horizontal perforation between bundle copies: a dashed rule
        broken by a scissors mark, matching the physical tear line
        between each carbon copy on the printed sheet."""
        x_left = self.MARGIN
        x_right = self.PAGE_W - self.MARGIN
        scissors_x = x_left + 60
        c.saveState()
        c.setDash(3, 3)
        c.setLineWidth(0.7)
        c.line(x_left, y, scissors_x - 8, y)
        c.line(scissors_x + 8, y, x_right, y)
        c.setDash()
        c.setFont('Helvetica', 9)
        c.drawCentredString(scissors_x, y - 3, '\u2702')
        c.restoreState()

    def _draw_reg_square(self, c, x, y, size=6):
        """Small solid black registration/cut-alignment square, printed
        in pairs at the top and bottom corners of every section on the
        original sheet."""
        c.saveState()
        c.setFillColor(colors.black)
        c.rect(x, y, size, size, fill=1, stroke=0)
        c.restoreState()

    def _draw_signature_box(self, c, x, y, w, h, label):
        c.setLineWidth(0.6)
        c.rect(x, y, w, h)
        c.setFont('Helvetica', 6.5)
        c.drawCentredString(x + w / 2, y + 4, label)

    def _draw_bubble_panel(self, c, x, y_top, w, title, cols=2, rows=10):
        """Draw a titled column of circled digits 0-9 (repeated 'cols'
        times side by side) — used for 'Total Marks' and 'SI No of
        Answer Book in the Bundle', which the previous version omitted
        entirely."""
        c.setLineWidth(0.6)
        header_h = 22
        cell = min(16, (w - 2) / cols)
        c.rect(x, y_top - header_h, w, header_h)
        c.setFont('Helvetica-Bold', 6)
        title_lines = title.split(' ', 1)
        ty = y_top - 9
        for word in [title]:
            pass
        # wrap title into up to 2 lines to fit narrow column
        words = title.split()
        lines, cur = [], ''
        for wd in words:
            trial = (cur + ' ' + wd).strip()
            if c.stringWidth(trial, 'Helvetica-Bold', 6) > w - 4 and cur:
                lines.append(cur)
                cur = wd
            else:
                cur = trial
        if cur:
            lines.append(cur)
        ty = y_top - 8
        for ln in lines[:3]:
            c.drawCentredString(x + w / 2, ty, ln)
            ty -= 7

        grid_top = y_top - header_h
        for r in range(rows):
            ry = grid_top - (r + 1) * cell
            for col in range(cols):
                cx = x + col * cell + cell / 2
                cy = ry + cell / 2
                c.circle(cx, cy, cell / 2 - 2)
                c.setFont('Helvetica', 6)
                c.drawCentredString(cx, cy - 2, str(r))
        c.rect(x, grid_top - rows * cell, w, rows * cell)
        for col in range(1, cols):
            c.line(x + col * cell, grid_top, x + col * cell, grid_top - rows * cell)
        return grid_top - rows * cell

    def _draw_h_barcode(self, c, x_left, x_right, y, height=24):
        """Full-width horizontal Code128 barcode, drawn as vector bars
        scaled to fill (x_left, x_right), same approach used on the hall
        ticket strip. Encodes self.barcode_data — same value everywhere
        on the page."""
        if not self.barcode_data:
            return
        try:
            target_width = x_right - x_left
            probe = code128.Code128(self.barcode_data, barWidth=1.0,
                                    barHeight=height, humanReadable=False)
            bar_width = 1.0 * target_width / probe.width if probe.width else 1.0
            barcode_obj = code128.Code128(self.barcode_data, barWidth=bar_width,
                                          barHeight=height, humanReadable=False)
            barcode_obj.drawOn(c, x_left, y)
        except Exception as e:
            _logger.warning('Horizontal barcode render failed for OMR %s: %s',
                            self.serial_number, e)

    def _draw_left_text_strip(self, c, x, y_top, y_bottom, label):
        """Narrow vertical column on the far-left edge of a valuation
        section: bordered box containing ONLY a rotated caption — e.g.
        'Bundle Number for Office use only' / 'Sl No of Answer Book in
        the Bundle'. The original sheet has NO barcode on this strip."""
        w = self.STRIP_W + 3
        c.setLineWidth(0.6)
        c.rect(x, y_bottom, w, y_top - y_bottom)
        if label:
            self._draw_vtext(c, x + w / 2, (y_top + y_bottom) / 2, label,
                              font='Helvetica-Bold', size=6.5)

    # ------------------------------------------------------------------
    # Hall-ticket (tear-off) strip
    # ------------------------------------------------------------------
    def _draw_hall_ticket_strip(self, c, y_top, inst, subtitle, accreditation, company_logo):
        section_h = 250
        y_bottom = y_top - section_h
        x_left = self.MARGIN
        x_right = self.PAGE_W - self.MARGIN

        c.setLineWidth(0.8)
        c.rect(x_left, y_bottom, x_right - x_left, section_h)
        self._draw_tear_strip(c, x_left, y_top, y_bottom, 'R20')
        # NOTE: Section 1 has NO registration mark at its bottom-right
        # corner on the original physical sheet — do not draw one here.

        content_x = x_left + self.STRIP_W + 10
        right_col_x = x_right - self.RIGHT_COL_W
        y = y_top - 14

        # ----- Logo -----
        if company_logo:
            try:
                logo_bytes = base64.b64decode(company_logo)
                logo_img = ImageReader(io.BytesIO(logo_bytes))
                c.drawImage(logo_img, content_x, y - 40, width=45, height=45,
                            preserveAspectRatio=True, anchor='c', mask='auto')
            except Exception as e:
                _logger.warning('Logo render failed for OMR %s: %s', self.serial_number, e)

        # ----- Title + accreditation / address lines -----
        # Spans the FULL width of the strip, including the area above
        # where the photo sits — not just up to the right-hand column.
        title_center = (x_left + x_right) / 2
        c.setFont('Helvetica-Bold', 12)
        c.drawCentredString(title_center, y, inst)
        y -= 13
        c.setFont('Helvetica', 7.5)
        if subtitle:
            c.drawCentredString(title_center, y, subtitle)
            y -= 10
        for line in [ln.strip() for ln in (accreditation or '').splitlines() if ln.strip()]:
            c.drawCentredString(title_center, y, line)
            y -= 10

        # ----- SI No + barcode -----
        si_row_y = y  # remember this row's y — the photo aligns with it
        y -= 12
        c.setFont('Helvetica-Bold', 10)
        c.drawString(content_x, y, f"SI No.: {self.serial_number}")
        target_width = 130  # points, ≈ the barcode size on the original sheet
        barcode_x = content_x + 90
        if self.barcode_data:
            try:
                # Drawn as vector bars (no PNG rendering / renderPM needed)
                # and scaled to a fixed target width — this is what keeps
                # the barcode a consistent, compact size on the printed
                # sheet regardless of how many digits the serial number
                # has, instead of stretching across the page.
                probe = code128.Code128(self.barcode_data, barWidth=1.0,
                                        barHeight=22, humanReadable=False)
                bar_width = 1.0 * target_width / probe.width if probe.width else 1.0
                barcode_obj = code128.Code128(self.barcode_data, barWidth=bar_width,
                                              barHeight=22, humanReadable=False)
                # Positioned ON the section's top border, straddling it,
                # instead of sitting inside the content area.
                barcode_obj.drawOn(c, barcode_x, y_top - 11)
            except Exception as e:
                _logger.warning('Barcode render failed for OMR %s: %s',
                                self.serial_number, e)

        # ----- Student photo — below the header, roughly aligned with the
        # SI No./barcode row, sitting to the right of the barcode within
        # the main content area (not in a separate "For Office Use"
        # column) -----
        photo_w, photo_h = 82, 98
        barcode_end_x = barcode_x + target_width
        photo_x = barcode_end_x + (x_right - 10 - barcode_end_x - photo_w) / 2
        photo_y = si_row_y + 6 - photo_h
        if self.student_photo:
            try:
                photo_bytes = base64.b64decode(self.student_photo)
                photo_img = ImageReader(io.BytesIO(photo_bytes))
                c.drawImage(photo_img, photo_x, photo_y, width=photo_w, height=photo_h,
                            preserveAspectRatio=True, anchor='c', mask='auto')
            except Exception as e:
                _logger.warning('Photo render failed for OMR %s: %s', self.serial_number, e)
        c.setLineWidth(0.8)
        c.rect(photo_x, photo_y, photo_w, photo_h)

        # ----- Rotated label column (Examination:/Sub Code:/Sub Name:) -----
        # Lives OUTSIDE the main content column — in the narrow gap between
        # the "R20" tear-off strip and where the info rows start — so it no
        # longer eats into the content area's width.
        label_col_x = x_left + self.STRIP_W
        label_col_w = content_x - label_col_x
        info_top = y - 36
        info_bottom = y_bottom + 8
        rot_labels = ['Examination:', 'Sub Code:', 'Sub Name:']
        seg_h = (info_top - info_bottom) / len(rot_labels)
        for i, txt in enumerate(rot_labels):
            cy = info_top - seg_h * (i + 0.5)
            self._draw_vtext(c, label_col_x + label_col_w / 2, cy, txt,
                              font='Helvetica-Bold', size=6.5)

        # ----- Hall ticket info rows -----
        y -= 36
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
            c.drawString(content_x, y, label)
            c.setFont('Helvetica', 8)
            c.drawString(content_x + 100, y, val)
            y -= 13

        # ----- "For Office Use" — plain text label, no bordered panel -----
        c.setFont('Helvetica-Bold', 7)
        c.drawCentredString(right_col_x + self.RIGHT_COL_W / 2, photo_y - 12, 'For Office Use')

        # ----- Signature areas — right-aligned text labels with a
        # horizontal underline rule for signing, no boxes -----
        sig_top = photo_y - 24
        sig_h = (sig_top - (y_bottom + 8)) / 3
        c.setFont('Helvetica', 6.5)
        c.setLineWidth(0.6)
        for i, lbl in enumerate(['Signature of the Controller of Exams',
                                  'Signature of the Student with date',
                                  'Signature of the Invigilator with date']):
            line_y = sig_top - i * sig_h
            c.line(right_col_x, line_y, x_right, line_y)
            c.drawRightString(x_right, line_y - 9, lbl)

        return y_bottom - 12

    # ------------------------------------------------------------------
    # One valuation / re-valuation section
    # ------------------------------------------------------------------
    def _draw_valuation_section(self, c, y_top, copy_num, grid_config, inst, company_logo):
        section_h = 300
        y_bottom = y_top - section_h
        x_left = self.MARGIN
        x_right = self.PAGE_W - self.MARGIN

        c.setLineWidth(0.8)
        c.rect(x_left, y_bottom, x_right - x_left, section_h)
        self._draw_reg_square(c, x_left + 3, y_top + 3)
        self._draw_reg_square(c, x_right - 10, y_top + 3)
        self._draw_reg_square(c, x_right - 10, y_bottom - 9)
        self._draw_reg_square(c, x_left + 3, y_bottom - 9)

        # ----- Left-edge vertical strip: barcode + rotated caption -----
        # Distinct per copy — Part II uses "Bundle Number for Office use
        # only", Part III uses "SI No of Answer Book in the Bundle".
        left_strip_w = self.STRIP_W + 3
        left_caption = ('SI No of Answer Book in the Bundle' if copy_num == 2
                         else 'Bundle Number for Office use only')
        self._draw_left_text_strip(c, x_left, y_top, y_bottom, left_caption)

        content_x = x_left + left_strip_w + 8
        bundle_x = x_right - self.BUNDLE_COL_W
        panel_x = bundle_x - self.RIGHT_COL_W - 6
        left_col_right = panel_x - 10

        # NOTE: the original has NO separate logo box or standalone "LENDI"
        # text here — the top of the section is just the registration
        # squares (drawn above) flanking the institution name header.

        # ----- PART label + Valuation/Re-Valuation + circled copy number -----
        # Sits directly under the LENDI logo box, spanning the full width
        # of the bubble-panel column below it, so it never overlaps the
        # "Total Marks" / "SI No of Answer Book" panels underneath.
        part_label = f"PART - {'III' if copy_num == 2 else 'II'}"
        val_label = 'Re-Valuation' if copy_num == 2 else 'Valuation'
        panel_center_x = (panel_x + bundle_x) / 2
        c.setLineWidth(0.6)
        c.rect(panel_x, y_top - 50, self.RIGHT_COL_W, 30)
        c.setFont('Helvetica-Bold', 8)
        c.drawCentredString(panel_center_x, y_top - 30, part_label)
        c.drawCentredString(panel_center_x, y_top - 42, val_label)
        c.setFont('Helvetica-Bold', 11)
        c.setLineWidth(0.8)
        c.circle(panel_center_x, y_top - 61, 9)
        c.drawCentredString(panel_center_x, y_top - 64, str(copy_num))

        # ----- Section header (institution name) -----
        y = y_top - 12
        c.setFont('Helvetica-Bold', 9)
        c.drawCentredString((content_x + left_col_right) / 2, y, inst)
        y -= 10
        header_y = y

        # Narrow left column (mini info + Serial No. box) sits BESIDE the
        # barcode/grid, not stacked above it — matches the physical sheet,
        # where "Examination:/Month-Year:/.../Date of Exam" is a slim
        # column on the left and the barcode + PART-A/PART-B grid occupy
        # the wider area to its right, starting at the same y.
        mini_col_w = 130
        grid_x = content_x + mini_col_w + 10

        # ----- Horizontal barcode across the top of the grid area -----
        # Same width as the marks-grid columns (grid_x .. left_col_right),
        # same barcode_data as everywhere else on the page.
        by = header_y - 4
        self._draw_h_barcode(c, grid_x, left_col_right, by - 22, height=22)
        grid_top_y = by - 30

        # ----- Mini student info (narrow left column) -----
        mini_info = [
            ('Examination:', self.examination_id.name or ''),
            ('Month-Year:', self.exam_month_year or ''),
            ('Branch:', self.branch_name or ''),
            ('Sub Code:', self.subject_code or ''),
            ('Sub Name:', self.subject_name or ''),
            ('Date of Exam:', str(self.exam_date) if self.exam_date else ''),
        ]
        my = header_y
        for label, val in mini_info:
            c.setFont('Helvetica-Bold', 5.5)
            c.drawString(content_x, my, label)
            my -= 8
            c.setFont('Helvetica', 5.5)
            for line in self._wrap_text(c, val, 'Helvetica', 5.5, mini_col_w):
                c.drawString(content_x, my, line)
                my -= 8
            my -= 2

        # ----- "Serial No. of Last Page Written" box (below mini info,
        # still in the narrow left column) -----
        my -= 4
        serial_box_w, serial_box_h = mini_col_w, 40
        self._draw_signature_box(c, content_x, my - serial_box_h, serial_box_w,
                                  serial_box_h, '')
        c.setFont('Helvetica-Bold', 6)
        c.drawString(content_x + 3, my - 10, 'Serial No. of')
        c.drawString(content_x + 3, my - 19, 'Last Page')
        c.drawString(content_x + 3, my - 28, 'Written')
        c.setLineWidth(0.4)
        c.line(content_x + 3, my - serial_box_h + 8,
               content_x + serial_box_w - 3, my - serial_box_h + 8)
        my -= serial_box_h + 8

        # ----- Marks grid (PART-A + PART-B / main) — starts under the
        # barcode, to the right of the mini-info/Serial No. column -----
        grid_bottom = self._draw_marks_grid(c, grid_x, grid_top_y - 8,
                                             left_col_right - grid_x, grid_config)

        # Examiner / Scrutinizer bordered signature boxes span the FULL
        # width, below whichever column (mini-info+serial, or grid) ends
        # lower.
        gy = min(grid_bottom, my) - 12
        sig_box_w = (left_col_right - content_x - 6) / 2
        sig_box_h = 22
        self._draw_signature_box(c, content_x, gy - sig_box_h, sig_box_w, sig_box_h,
                                  "Examiner's Name & Signature")
        self._draw_signature_box(c, content_x + sig_box_w + 6, gy - sig_box_h, sig_box_w,
                                  sig_box_h, "Scrutinizer's Name & Signature")

        # ----- Right-hand bubble panels: Total Marks | SI No of Answer Book -----
        panel_w = (self.RIGHT_COL_W - 4) / 2
        bubbles_top = y_top - 72  # below the LENDI box + PART/Valuation box
        p1_bottom = self._draw_bubble_panel(c, panel_x, bubbles_top, panel_w, 'Total Marks')
        p2_bottom = self._draw_bubble_panel(c, panel_x + panel_w + 4, bubbles_top, panel_w,
                                             'Sl No of Answer Book in the Bundle')
        bubble_bottom = min(p1_bottom, p2_bottom)

        # "Marks in Words" box — 3-row layout: top row = "Marks in Words"
        # spanning the full width; bottom row split into "Tens Place"
        # (left) and "Units Place" (right).
        mw_top = bubble_bottom - 4
        mw_h = 28
        header_row_h = mw_h / 2
        c.setLineWidth(0.6)
        c.rect(panel_x, mw_top - mw_h, self.RIGHT_COL_W, mw_h)
        c.line(panel_x, mw_top - header_row_h, panel_x + self.RIGHT_COL_W,
               mw_top - header_row_h)
        c.line(panel_x + self.RIGHT_COL_W / 2, mw_top - header_row_h,
               panel_x + self.RIGHT_COL_W / 2, mw_top - mw_h)
        c.setFont('Helvetica-Bold', 6)
        c.drawCentredString(panel_x + self.RIGHT_COL_W / 2, mw_top - 9, 'Marks in Words')
        c.drawCentredString(panel_x + self.RIGHT_COL_W / 4, mw_top - header_row_h - 10,
                             'Tens Place')
        c.drawCentredString(panel_x + 3 * self.RIGHT_COL_W / 4, mw_top - header_row_h - 10,
                             'Units Place')

        # ----- Control Bundle Number strip (far right edge) -----
        c.setLineWidth(0.6)
        c.rect(bundle_x, y_bottom, self.BUNDLE_COL_W, section_h - 55)
        self._draw_vtext(c, bundle_x + self.BUNDLE_COL_W / 2, y_bottom + 30,
                          'Control Bundle Number', size=6.5)

        return y_bottom - 14

    def _draw_marks_grid(self, c, x, y, avail_width, grid_config):
        """Draw the question marks grid. Returns the new y position.

        PART-A (Q.No/A-J bubble table) is now always drawn, regardless of
        format type — even when the template's grid config doesn't define
        one, a default PART-A is synthesized so every format matches the
        original sheet's layout."""
        cell_w = 14
        cell_h = 14
        fmt = grid_config['format']
        parts = grid_config['parts']

        has_part_a = any(p['name'] == 'part_a' for p in parts)
        if not has_part_a:
            parts = [{'name': 'part_a', 'label': 'PART-A', 'columns': 10, 'rows': 1}] + list(parts)

        if fmt == 'r20':
            # Part-A header
            for part in parts:
                if part['name'] == 'part_a':
                    c.setFont('Helvetica-Bold', 7)
                    c.drawString(x, y, part.get('label', 'PART'))
                    y -= 4

                    # Columns: Q.No, A, B, C, D, E, F, G, H, I, J, Total
                    cols = part.get('columns', 10)
                    headers = ['Q.No'] + [chr(65 + i) for i in range(cols)] + ['Total']
                    for i, h in enumerate(headers):
                        cx = x + i * cell_w
                        c.rect(cx, y - cell_h, cell_w, cell_h)
                        c.setFont('Helvetica-Bold', 5)
                        c.drawCentredString(cx + cell_w / 2, y - cell_h + 3, h)
                    y -= cell_h
                    # One row for question 1 — options drawn as bubbles,
                    # like the actual objective-answer row on the sheet
                    for row in range(part.get('rows', 1)):
                        c.rect(x, y - cell_h, cell_w, cell_h)
                        c.setFont('Helvetica', 5)
                        c.drawCentredString(x + cell_w / 2, y - cell_h + 3, str(row + 1))
                        for i in range(cols):
                            cx = x + (i + 1) * cell_w
                            c.rect(cx, y - cell_h, cell_w, cell_h)
                            c.setLineWidth(0.4)
                            c.circle(cx + cell_w / 2, y - cell_h / 2, cell_w / 2 - 3)
                            c.setLineWidth(0.6)
                        # Total cell
                        c.rect(x + (cols + 1) * cell_w, y - cell_h, cell_w, cell_h)
                        y -= cell_h
                    y -= 6

                elif part['name'] in ('part_b', 'main'):
                    # "PART-B" label header above the Q.No/a/b/c/d grid
                    c.setFont('Helvetica-Bold', 7)
                    c.drawString(x, y, 'PART-B')
                    y -= 10
                    y = self._draw_qa_block(c, x, y, cell_w, cell_h, part)

        else:
            # R22 or custom — single grid with Q.No, a, b, c, d, Total pairs
            for part in parts:
                if part['name'] == 'part_a':
                    c.setFont('Helvetica-Bold', 7)
                    c.drawString(x, y, part.get('label', 'PART-A'))
                    y -= 4
                    cols = part.get('columns', 10)
                    headers = ['Q.No'] + [chr(65 + i) for i in range(cols)] + ['Total']
                    for i, h in enumerate(headers):
                        cx = x + i * cell_w
                        c.rect(cx, y - cell_h, cell_w, cell_h)
                        c.setFont('Helvetica-Bold', 5)
                        c.drawCentredString(cx + cell_w / 2, y - cell_h + 3, h)
                    y -= cell_h
                    for row in range(part.get('rows', 1)):
                        c.rect(x, y - cell_h, cell_w, cell_h)
                        c.setFont('Helvetica', 5)
                        c.drawCentredString(x + cell_w / 2, y - cell_h + 3, str(row + 1))
                        for i in range(cols + 1):
                            c.rect(x + (i + 1) * cell_w, y - cell_h, cell_w, cell_h)
                        y -= cell_h
                    y -= 6
                else:
                    c.setFont('Helvetica-Bold', 7)
                    c.drawString(x, y, 'PART-B')
                    y -= 10
                    y = self._draw_qa_block(c, x, y, cell_w, cell_h, part)

        return y

    def _draw_qa_block(self, c, x, y, cell_w, cell_h, part):
        """Shared Q.No/a/b/c/d/Total (+BEST) paired-column block used by
        both PART-B (R20) and the main grid (R22/custom)."""
        sub = part.get('sub_parts', 4)
        # The original sheet always has 12 questions in 6 paired rows
        # (1/2 … 11/12) — never fewer, regardless of template config.
        q_count = max(part.get('questions', 12), 12)
        sub_labels = [chr(97 + i) for i in range(sub)]

        headers_left = ['Q.No'] + sub_labels + ['Total']
        headers_right = ['Q.No'] + sub_labels + ['Total', 'BEST']
        col_count_left = len(headers_left)

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

        for row in range(0, q_count, 2):
            q_left = row + 1
            q_right = row + 2
            c.rect(x, y - cell_h, cell_w, cell_h)
            c.setFont('Helvetica', 5)
            c.drawCentredString(x + cell_w / 2, y - cell_h + 3, str(q_left))
            for i in range(sub + 1):
                cx = x + (i + 1) * cell_w
                c.rect(cx, y - cell_h, cell_w, cell_h)
            if q_right <= q_count:
                c.rect(offset_right, y - cell_h, cell_w, cell_h)
                c.drawCentredString(offset_right + cell_w / 2, y - cell_h + 3, str(q_right))
                for i in range(sub + 2):
                    cx = offset_right + (i + 1) * cell_w
                    c.rect(cx, y - cell_h, cell_w, cell_h)
            y -= cell_h

        c.setFont('Helvetica-Bold', 6)
        c.drawString(offset_right, y - cell_h + 3, 'GRAND TOTAL (PART A + PART B)')
        c.rect(offset_right + (sub + 1) * cell_w, y - cell_h, cell_w * 2, cell_h)
        y -= cell_h
        return y