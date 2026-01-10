# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
import qrcode
import base64
from io import BytesIO


class StudentIdCard(models.Model):
    _name = 'student.id.card'
    _description = 'Student ID Card Generation'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'issue_date desc'

    name = fields.Char(string='ID Card Number', required=True, readonly=True,
                       copy=False, default='/')

    # Student
    student_id = fields.Many2one('student.student', string='Student',
                                 required=True, tracking=True, index=True)
    registration_number = fields.Char(related='student_id.registration_number',
                                      string='Registration Number')
    student_name = fields.Char(related='student_id.name', string='Student Name')
    student_photo = fields.Binary(related='student_id.student_photo', string='Photo')

    # Academic
    program_id = fields.Many2one(related='student_id.program_id', string='Program', store=True)
    department_id = fields.Many2one(related='student_id.department_id',
                                    string='Department', store=True)
    batch_id = fields.Many2one(related='student_id.batch_id', string='Batch', store=True)

    # Card Details
    card_type = fields.Selection([
        ('regular', 'Regular ID Card'),
        ('temporary', 'Temporary ID Card'),
        ('duplicate', 'Duplicate ID Card'),
    ], string='Card Type', default='regular', required=True, tracking=True)

    # Validity
    issue_date = fields.Date(string='Issue Date', default=fields.Date.today(),
                             required=True, tracking=True)
    expiry_date = fields.Date(string='Expiry Date', required=True, tracking=True)
    is_valid = fields.Boolean(string='Valid', compute='_compute_validity', store=True)

    # QR Code
    qr_code = fields.Binary(string='QR Code', compute='_compute_qr_code', store=True)
    qr_data = fields.Char(string='QR Data', compute='_compute_qr_data', store=True)

    # Barcode
    barcode = fields.Char(string='Barcode')

    # Contact
    emergency_contact = fields.Char(related='student_id.emergency_contact',
                                    string='Emergency Contact')
    blood_group = fields.Selection(related='student_id.blood_group', string='Blood Group')

    # Issue Details
    issued_by = fields.Many2one('res.users', string='Issued By',
                                default=lambda self: self.env.user, readonly=True)

    # Status
    state = fields.Selection([
        ('draft', 'Draft'),
        ('printed', 'Printed'),
        ('issued', 'Issued'),
        ('expired', 'Expired'),
        ('lost', 'Lost/Stolen'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', tracking=True)

    # Lost/Duplicate
    is_duplicate = fields.Boolean(string='Is Duplicate')
    original_card_id = fields.Many2one('student.id.card', string='Original Card')
    lost_date = fields.Date(string='Lost Date')
    lost_reason = fields.Text(string='Lost Reason')

    # Fee for Duplicate
    duplicate_fee = fields.Monetary(string='Duplicate Card Fee', currency_field='currency_id')
    duplicate_fee_paid = fields.Boolean(string='Fee Paid')
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id)

    # Notes
    notes = fields.Text(string='Notes')

    _sql_constraints = [
        ('name_unique', 'unique(name)', 'ID Card Number must be unique!'),
    ]

    @api.model
    def create(self, vals):
        if vals.get('name', '/') == '/':
            vals['name'] = self.env['ir.sequence'].next_by_code('student.id.card') or '/'
        return super(StudentIdCard, self).create(vals)

    @api.depends('expiry_date')
    def _compute_validity(self):
        today = fields.Date.today()
        for record in self:
            record.is_valid = record.expiry_date >= today if record.expiry_date else False

    @api.depends('student_id', 'name', 'issue_date', 'expiry_date')
    def _compute_qr_data(self):
        for record in self:
            if record.student_id:
                qr_data = f"ID:{record.name}|REG:{record.student_id.registration_number}|NAME:{record.student_id.name}|PROGRAM:{record.program_id.name}|VALID:{record.issue_date} to {record.expiry_date}"
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

    def action_print(self):
        """Mark as printed"""
        self.write({'state': 'printed'})
        return self.env.ref('university_management.action_report_student_id_card').report_action(self)

    def action_issue(self):
        """Issue ID card to student"""
        self.write({'state': 'issued'})

    def action_report_lost(self):
        """Report ID card as lost"""
        self.write({
            'state': 'lost',
            'lost_date': fields.Date.today()
        })

    def action_generate_duplicate(self):
        """Generate duplicate ID card"""
        self.ensure_one()

        duplicate = self.copy({
            'card_type': 'duplicate',
            'is_duplicate': True,
            'original_card_id': self.id,
            'state': 'draft',
        })

        return {
            'type': 'ir.actions.act_window',
            'name': _('Duplicate ID Card'),
            'res_model': 'student.id.card',
            'res_id': duplicate.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_cancel(self):
        """Cancel ID card"""
        self.write({'state': 'cancelled'})


class StudentLeave(models.Model):
    _name = 'student.leave'
    _description = 'Student Leave Application'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_from desc'

    name = fields.Char(string='Leave Number', required=True, readonly=True, default='/')

    student_id = fields.Many2one('student.student', string='Student',
                                 required=True, tracking=True, index=True)

    date_from = fields.Date(string='From Date', required=True, tracking=True)
    date_to = fields.Date(string='To Date', required=True, tracking=True)
    number_of_days = fields.Integer(string='Number of Days', compute='_compute_days', store=True)

    leave_type = fields.Selection([
        ('sick', 'Sick Leave'),
        ('casual', 'Casual Leave'),
        ('emergency', 'Emergency Leave'),
        ('other', 'Other'),
    ], string='Leave Type', required=True)

    reason = fields.Text(string='Reason', required=True)

    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ], string='Status', default='draft', tracking=True)

    approved_by = fields.Many2one('res.users', string='Approved By', readonly=True)
    approval_date = fields.Date(string='Approval Date', readonly=True)

    @api.depends('date_from', 'date_to')
    def _compute_days(self):
        for record in self:
            if record.date_from and record.date_to:
                record.number_of_days = (record.date_to - record.date_from).days + 1
            else:
                record.number_of_days = 0
