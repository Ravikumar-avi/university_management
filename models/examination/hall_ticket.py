# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
import qrcode
import base64
from io import BytesIO


class ExaminationHallTicket(models.Model):
    _name = 'examination.hall.ticket'
    _description = 'Hall Ticket Generation'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']
    _order = 'issue_date desc'

    name = fields.Char(string='Hall Ticket Number', required=True, readonly=True,
                       copy=False, default='/')

    # Student
    student_id = fields.Many2one('student.student', string='Student',
                                 required=True, tracking=True, index=True)
    registration_number = fields.Char(related='student_id.registration_number',
                                      string='Registration Number')
    student_name = fields.Char(related='student_id.name', string='Student Name')
    student_photo = fields.Binary(related='student_id.student_photo', string='Photo')

    # Academic Details
    program_id = fields.Many2one(related='student_id.program_id', string='Program', store=True)
    department_id = fields.Many2one(related='student_id.department_id',
                                    string='Department', store=True)
    batch_id = fields.Many2one(related='student_id.batch_id', string='Batch', store=True)

    # Examination
    examination_id = fields.Many2one('examination.examination', string='Examination',
                                     required=True, tracking=True, index=True)
    academic_year_id = fields.Many2one(related='examination_id.academic_year_id',
                                       string='Academic Year', store=True)
    semester_id = fields.Many2one(related='examination_id.semester_id',
                                  string='Semester', store=True)

    # Exam Subjects
    exam_timetable_ids = fields.Many2many('examination.timetable',
                                          'hall_ticket_timetable_rel',
                                          'hall_ticket_id', 'timetable_id',
                                          string='Exam Schedule')

    # Issue Details
    issue_date = fields.Date(string='Issue Date', default=fields.Date.today(),
                             tracking=True)
    issued_by = fields.Many2one('res.users', string='Issued By',
                                default=lambda self: self.env.user, readonly=True)

    # QR Code
    qr_code = fields.Binary(string='QR Code', compute='_compute_qr_code', store=True)
    qr_data = fields.Char(string='QR Data', compute='_compute_qr_data', store=True)

    # Instructions
    instructions = fields.Html(related='examination_id.instructions',
                               string='Exam Instructions')

    # Eligibility
    is_eligible = fields.Boolean(string='Eligible', default=True, tracking=True)
    ineligibility_reason = fields.Text(string='Ineligibility Reason')

    # Status
    state = fields.Selection([
        ('draft', 'Draft'),
        ('issued', 'Issued'),
        ('downloaded', 'Downloaded'),
        ('printed', 'Printed'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', tracking=True)

    # Download Info
    download_count = fields.Integer(string='Download Count', default=0)
    last_downloaded = fields.Datetime(string='Last Downloaded')

    # Notes
    notes = fields.Text(string='Notes')

    _sql_constraints = [
        ('name_unique', 'unique(name)', 'Hall Ticket Number must be unique!'),
        ('unique_hall_ticket', 'unique(student_id, examination_id)',
         'Hall ticket already generated for this student and examination!'),
    ]

    @api.model
    def create(self, vals):
        if vals.get('name', '/') == '/':
            vals['name'] = self.env['ir.sequence'].next_by_code('examination.hall.ticket') or '/'
        return super(ExaminationHallTicket, self).create(vals)

    @api.depends('student_id', 'name', 'examination_id')
    def _compute_qr_data(self):
        for record in self:
            if record.student_id and record.examination_id:
                qr_data = (f"HALL_TICKET:{record.name}|"
                           f"REG:{record.student_id.registration_number}|"
                           f"NAME:{record.student_id.name}|"
                           f"EXAM:{record.examination_id.name}")
                record.qr_data = qr_data
            else:
                record.qr_data = False

    @api.depends('qr_data')
    def _compute_qr_code(self):
        for record in self:
            if record.qr_data:
                qr = qrcode.QRCode(version=1, box_size=10, border=5)
                qr.add_data(record.qr_data)
                qr.make(fit=True)

                img = qr.make_image(fill_color="black", back_color="white")
                buffer = BytesIO()
                img.save(buffer, format='PNG')
                record.qr_code = base64.b64encode(buffer.getvalue())
            else:
                record.qr_code = False

    def action_issue(self):
        """Issue hall ticket"""
        self.write({'state': 'issued'})
        self._send_hall_ticket()

    def action_print(self):
        """Print hall ticket"""
        self.write({'state': 'printed'})
        return self.env.ref('university_management.action_report_hall_ticket').report_action(self)

    def action_download(self):
        """Mark as downloaded"""
        self.write({
            'state': 'downloaded',
            'download_count': self.download_count + 1,
            'last_downloaded': fields.Datetime.now()
        })

    def action_cancel(self):
        """Cancel hall ticket"""
        self.write({'state': 'cancelled'})

    def _send_hall_ticket(self):
        """Send hall ticket via email"""
        template = self.env.ref('university_management.email_template_hall_ticket',
                                raise_if_not_found=False)
        if template:
            template.send_mail(self.id, force_send=True)

    @api.model
    def _check_eligibility(self, student_id, examination_id):
        """Check if student is eligible for examination"""
        student = self.env['student.student'].browse(student_id)

        # Check attendance
        if student.attendance_percentage < 75:
            return False, "Attendance below 75%"

        # Check fee payment
        if student.total_fee_due > 0:
            return False, "Fee dues pending"

        # Check discipline issues
        major_disciplines = self.env['student.discipline'].search([
            ('student_id', '=', student_id),
            ('severity', 'in', ['major', 'critical']),
            ('state', '!=', 'closed')
        ])
        if major_disciplines:
            return False, "Pending discipline issues"

        return True, ""
