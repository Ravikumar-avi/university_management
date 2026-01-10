# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class HostelAttendance(models.Model):
    _name = 'hostel.attendance'
    _description = 'Hostel Student Attendance'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc, hostel_id'

    name = fields.Char(string='Reference', compute='_compute_name', store=True)

    # Student
    student_id = fields.Many2one('student.student', string='Student',
                                 required=True, index=True)
    allocation_id = fields.Many2one('hostel.allocation', string='Allocation')

    # Hostel & Room
    hostel_id = fields.Many2one(related='allocation_id.hostel_id', string='Hostel', store=True)
    room_id = fields.Many2one(related='allocation_id.room_id', string='Room', store=True)

    # Attendance Date
    date = fields.Date(string='Date', default=fields.Date.today(), required=True, index=True)

    # Status
    state = fields.Selection([
        ('present', 'Present'),
        ('absent', 'Absent'),
        ('out', 'Out with Permission'),
        ('leave', 'On Leave'),
    ], string='Status', default='present', required=True, tracking=True)

    # Out Pass Details
    out_time = fields.Datetime(string='Out Time')
    expected_return = fields.Datetime(string='Expected Return')
    actual_return = fields.Datetime(string='Actual Return')

    # Remarks
    remarks = fields.Text(string='Remarks')

    _sql_constraints = [
        ('unique_attendance', 'unique(student_id, date)',
         'Attendance already marked for this student on this date!'),
    ]

    @api.depends('student_id', 'date')
    def _compute_name(self):
        for record in self:
            record.name = f"{record.student_id.name} - {record.date}"