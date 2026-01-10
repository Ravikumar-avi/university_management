# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class FacultyAttendance(models.Model):
    _name = 'faculty.attendance'
    _description = 'Faculty Attendance'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc, faculty_id'

    name = fields.Char(string='Reference', compute='_compute_name', store=True)

    # Faculty
    faculty_id = fields.Many2one('faculty.faculty', string='Faculty',
                                 required=True, tracking=True, index=True)
    employee_id = fields.Many2one(related='faculty_id.employee_id', string='Employee', store=True)
    department_id = fields.Many2one(related='faculty_id.department_id',
                                    string='Department', store=True)

    # Attendance Date & Time
    date = fields.Date(string='Date', required=True, default=fields.Date.today(),
                       tracking=True, index=True)

    check_in = fields.Datetime(string='Check In', tracking=True)
    check_out = fields.Datetime(string='Check Out', tracking=True)

    worked_hours = fields.Float(string='Worked Hours', compute='_compute_worked_hours',
                                store=True)

    # Status
    state = fields.Selection([
        ('present', 'Present'),
        ('absent', 'Absent'),
        ('half_day', 'Half Day'),
        ('on_leave', 'On Leave'),
        ('late', 'Late'),
        ('holiday', 'Holiday'),
        ('week_off', 'Week Off'),
    ], string='Status', required=True, default='present', tracking=True)

    # Leave
    leave_id = fields.Many2one('faculty.leave', string='Leave Application')

    # Late Coming
    is_late = fields.Boolean(string='Late Coming')
    late_minutes = fields.Integer(string='Late By (Minutes)')
    late_reason = fields.Text(string='Reason for Late')

    # Overtime
    is_overtime = fields.Boolean(string='Overtime')
    overtime_hours = fields.Float(string='Overtime Hours')
    overtime_approved = fields.Boolean(string='Overtime Approved')

    # Remarks
    remarks = fields.Text(string='Remarks')

    _sql_constraints = [
        ('unique_attendance', 'unique(faculty_id, date)',
         'Attendance already marked for this faculty on this date!'),
    ]

    @api.depends('faculty_id', 'date')
    def _compute_name(self):
        for record in self:
            record.name = f"{record.faculty_id.name} - {record.date}"

    @api.depends('check_in', 'check_out')
    def _compute_worked_hours(self):
        for record in self:
            if record.check_in and record.check_out:
                delta = record.check_out - record.check_in
                record.worked_hours = delta.total_seconds() / 3600
            else:
                record.worked_hours = 0.0

    @api.constrains('check_in', 'check_out')
    def _check_times(self):
        for record in self:
            if record.check_in and record.check_out:
                if record.check_out <= record.check_in:
                    raise ValidationError(_('Check out time must be after check in time!'))

    @api.constrains('date')
    def _check_date(self):
        for record in self:
            if record.date > fields.Date.today():
                raise ValidationError(_('Cannot mark attendance for future dates!'))
