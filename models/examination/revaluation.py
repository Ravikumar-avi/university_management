# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class ExaminationRevaluation(models.Model):
    _name = 'examination.revaluation'
    _description = 'Re-evaluation Requests'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']
    _order = 'application_date desc'

    name = fields.Char(string='Revaluation Number', required=True, readonly=True,
                       copy=False, default='/')

    # Student
    student_id = fields.Many2one('student.student', string='Student',
                                 required=True, tracking=True, index=True)
    registration_number = fields.Char(related='student_id.registration_number',
                                      string='Registration Number')

    # Result
    result_id = fields.Many2one('examination.result', string='Exam Result',
                                required=True, tracking=True,
                                domain="[('student_id', '=', student_id), ('state', '=', 'published')]")
    examination_id = fields.Many2one(related='result_id.examination_id',
                                     string='Examination', store=True)
    subject_id = fields.Many2one(related='result_id.subject_id', string='Subject', store=True)

    # Original Marks
    original_marks = fields.Integer(related='result_id.total_marks',
                                    string='Original Marks', readonly=True)
    original_grade = fields.Char(related='result_id.grade_letter',
                                 string='Original Grade', readonly=True)

    # Application Details
    application_date = fields.Date(string='Application Date', default=fields.Date.today(),
                                   required=True, tracking=True)

    # Reason
    reason = fields.Html(string='Reason for Revaluation', required=True)

    # Revaluation Type
    revaluation_type = fields.Selection([
        ('rechecking', 'Rechecking'),
        ('revaluation', 'Revaluation'),
        ('photocopy', 'Photocopy of Answer Sheet'),
    ], string='Type', required=True, default='revaluation', tracking=True)

    # Fee
    revaluation_fee = fields.Monetary(string='Revaluation Fee', required=True,
                                      currency_field='currency_id', default=500.0)
    fee_paid = fields.Boolean(string='Fee Paid', tracking=True)
    payment_reference = fields.Char(string='Payment Reference')
    payment_date = fields.Date(string='Payment Date')

    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id)

    # Revaluation Result
    revaluated_by = fields.Many2one('faculty.faculty', string='Revaluated By')
    revaluation_date = fields.Date(string='Revaluation Date')

    revaluated_marks = fields.Integer(string='Revaluated Marks')
    revaluated_grade = fields.Char(string='Revaluated Grade')

    marks_difference = fields.Integer(string='Marks Difference',
                                      compute='_compute_difference', store=True)
    marks_changed = fields.Boolean(string='Marks Changed', compute='_compute_difference')

    # Outcome
    outcome = fields.Selection([
        ('increased', 'Marks Increased'),
        ('decreased', 'Marks Decreased'),
        ('no_change', 'No Change'),
    ], string='Outcome', compute='_compute_outcome', store=True)

    # Status
    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Application Submitted'),
        ('under_review', 'Under Review'),
        ('revaluation_in_progress', 'Revaluation in Progress'),
        ('completed', 'Completed'),
        ('rejected', 'Rejected'),
    ], string='Status', default='draft', tracking=True)

    # Rejection
    rejection_reason = fields.Text(string='Rejection Reason')

    # Remarks
    remarks = fields.Text(string='Remarks')
    revaluation_notes = fields.Text(string='Revaluation Notes')

    _sql_constraints = [
        ('name_unique', 'unique(name)', 'Revaluation Number must be unique!'),
    ]

    @api.model
    def create(self, vals):
        if vals.get('name', '/') == '/':
            vals['name'] = self.env['ir.sequence'].next_by_code('examination.revaluation') or '/'
        return super(ExaminationRevaluation, self).create(vals)

    @api.depends('original_marks', 'revaluated_marks')
    def _compute_difference(self):
        for record in self:
            if record.revaluated_marks:
                record.marks_difference = record.revaluated_marks - record.original_marks
                record.marks_changed = record.marks_difference != 0
            else:
                record.marks_difference = 0
                record.marks_changed = False

    @api.depends('marks_difference')
    def _compute_outcome(self):
        for record in self:
            if record.marks_difference > 0:
                record.outcome = 'increased'
            elif record.marks_difference < 0:
                record.outcome = 'decreased'
            else:
                record.outcome = 'no_change'

    def action_submit(self):
        if not self.fee_paid:
            raise ValidationError(_('Revaluation fee must be paid before submission!'))
        self.write({'state': 'submitted'})

    def action_review(self):
        self.write({'state': 'under_review'})

    def action_start_revaluation(self):
        self.write({'state': 'revaluation_in_progress'})

    def action_complete(self):
        self.write({
            'state': 'completed',
            'revaluation_date': fields.Date.today()
        })

        # Update original result if marks changed
        if self.marks_changed:
            self.result_id.write({
                'total_marks': self.revaluated_marks,
                'remarks': f"Revaluation: Original {self.original_marks}, Changed to {self.revaluated_marks}"
            })

    def action_reject(self):
        self.write({'state': 'rejected'})
