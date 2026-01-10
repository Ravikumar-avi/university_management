# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class FacultyLeave(models.Model):
    _name = 'faculty.leave'
    _description = 'Faculty Leave Management'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_from desc'

    name = fields.Char(string='Leave Number', required=True, readonly=True,
                       copy=False, default='/')

    # Faculty
    faculty_id = fields.Many2one('faculty.faculty', string='Faculty',
                                 required=True, tracking=True, index=True)
    employee_id = fields.Many2one(related='faculty_id.employee_id', string='Employee', store=True)
    department_id = fields.Many2one(related='faculty_id.department_id',
                                    string='Department', store=True)

    # Leave Type
    leave_type = fields.Selection([
        ('casual', 'Casual Leave'),
        ('sick', 'Sick Leave'),
        ('earned', 'Earned Leave'),
        ('maternity', 'Maternity Leave'),
        ('paternity', 'Paternity Leave'),
        ('compensatory', 'Compensatory Off'),
        ('unpaid', 'Leave Without Pay'),
        ('sabbatical', 'Sabbatical Leave'),
        ('study', 'Study Leave'),
        ('emergency', 'Emergency Leave'),
    ], string='Leave Type', required=True, tracking=True)

    # Duration
    date_from = fields.Date(string='From Date', required=True, tracking=True)
    date_to = fields.Date(string='To Date', required=True, tracking=True)
    number_of_days = fields.Float(string='Number of Days', compute='_compute_days',
                                  store=True)

    half_day = fields.Boolean(string='Half Day')
    half_day_type = fields.Selection([
        ('first_half', 'First Half'),
        ('second_half', 'Second Half'),
    ], string='Half Day Type')

    # Reason
    reason = fields.Text(string='Reason', required=True)

    # Supporting Documents
    attachment_ids = fields.Many2many('ir.attachment', string='Supporting Documents')

    # Substitute Arrangement
    substitute_required = fields.Boolean(string='Substitute Required', default=True)
    substitute_faculty_id = fields.Many2one('faculty.faculty', string='Substitute Faculty')
    substitute_arrangement = fields.Text(string='Substitute Arrangement Details')

    # Approval Workflow
    approved_by_hod = fields.Many2one('res.users', string='Approved by HOD', readonly=True)
    hod_approval_date = fields.Date(string='HOD Approval Date', readonly=True)

    approved_by_principal = fields.Many2one('res.users', string='Approved by Principal',
                                            readonly=True)
    principal_approval_date = fields.Date(string='Principal Approval Date', readonly=True)

    # Status
    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('hod_approved', 'HOD Approved'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', tracking=True)

    # Rejection
    rejection_reason = fields.Text(string='Rejection Reason')

    # Notes
    notes = fields.Text(string='Notes')

    _sql_constraints = [
        ('name_unique', 'unique(name)', 'Leave Number must be unique!'),
    ]

    @api.model
    def create(self, vals):
        if vals.get('name', '/') == '/':
            vals['name'] = self.env['ir.sequence'].next_by_code('faculty.leave') or '/'
        return super(FacultyLeave, self).create(vals)

    @api.depends('date_from', 'date_to', 'half_day')
    def _compute_days(self):
        for record in self:
            if record.date_from and record.date_to:
                days = (record.date_to - record.date_from).days + 1
                record.number_of_days = days / 2 if record.half_day else days
            else:
                record.number_of_days = 0

    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        for record in self:
            if record.date_from > record.date_to:
                raise ValidationError(_('To Date must be after From Date!'))

    def action_submit(self):
        self.write({'state': 'submitted'})

    def action_hod_approve(self):
        self.write({
            'state': 'hod_approved',
            'approved_by_hod': self.env.user.id,
            'hod_approval_date': fields.Date.today()
        })

    def action_approve(self):
        self.write({
            'state': 'approved',
            'approved_by_principal': self.env.user.id,
            'principal_approval_date': fields.Date.today()
        })
        self._create_attendance_records()

    def action_reject(self):
        self.write({'state': 'rejected'})

    def action_cancel(self):
        self.write({'state': 'cancelled'})

    def _create_attendance_records(self):
        """Create attendance records for approved leave"""
        AttendanceObj = self.env['faculty.attendance']
        current_date = self.date_from

        while current_date <= self.date_to:
            AttendanceObj.create({
                'faculty_id': self.faculty_id.id,
                'date': current_date,
                'state': 'on_leave',
                'leave_id': self.id,
            })
            current_date = current_date + fields.Date.from_string('1')
