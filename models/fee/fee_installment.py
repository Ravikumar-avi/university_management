# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class FeeInstallment(models.Model):
    _name = 'fee.installment'
    _description = 'Fee Installment Plans'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'due_date'

    name = fields.Char(string='Installment Number', compute='_compute_name', store=True)

    # Student
    student_id = fields.Many2one('student.student', string='Student',
                                 required=True, tracking=True, index=True)

    # Fee Structure
    fee_structure_id = fields.Many2one('fee.structure', string='Fee Structure',
                                       required=True, tracking=True)

    # Installment Details
    installment_number = fields.Integer(string='Installment #', required=True)
    installment_amount = fields.Monetary(string='Installment Amount', required=True,
                                         currency_field='currency_id')
    due_date = fields.Date(string='Due Date', required=True, tracking=True)

    # Payment
    payment_id = fields.Many2one('fee.payment', string='Payment')
    paid_amount = fields.Monetary(string='Paid Amount', currency_field='currency_id')
    paid_date = fields.Date(string='Paid Date')
    balance_amount = fields.Monetary(string='Balance', compute='_compute_balance',
                                     store=True, currency_field='currency_id')

    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id)

    # Late Fee
    is_overdue = fields.Boolean(string='Overdue', compute='_compute_overdue', store=True)
    days_overdue = fields.Integer(string='Days Overdue', compute='_compute_overdue', store=True)
    late_fee = fields.Monetary(string='Late Fee', currency_field='currency_id')

    # Status
    state = fields.Selection([
        ('pending', 'Pending'),
        ('partial', 'Partially Paid'),
        ('paid', 'Paid'),
        ('overdue', 'Overdue'),
    ], string='Status', default='pending', tracking=True, compute='_compute_state', store=True)

    # Notes
    notes = fields.Text(string='Notes')

    @api.depends('student_id', 'installment_number')
    def _compute_name(self):
        for record in self:
            record.name = f"{record.student_id.name} - Installment {record.installment_number}"

    @api.depends('installment_amount', 'paid_amount')
    def _compute_balance(self):
        for record in self:
            record.balance_amount = record.installment_amount - record.paid_amount

    @api.depends('due_date', 'state')
    def _compute_overdue(self):
        today = fields.Date.today()
        for record in self:
            if record.due_date:
                record.is_overdue = record.due_date < today and record.state != 'paid'
                if record.is_overdue:
                    record.days_overdue = (today - record.due_date).days
                else:
                    record.days_overdue = 0
            else:
                record.is_overdue = False
                record.days_overdue = 0

    @api.depends('balance_amount', 'is_overdue')
    def _compute_state(self):
        for record in self:
            if record.balance_amount <= 0:
                record.state = 'paid'
            elif record.paid_amount > 0:
                record.state = 'partial'
            elif record.is_overdue:
                record.state = 'overdue'
            else:
                record.state = 'pending'

    def action_mark_paid(self):
        """Mark installment as paid"""
        for record in self:
            record.write({
                'paid_amount': record.installment_amount,
                'paid_date': fields.Date.today(),
                'state': 'paid'
            })
