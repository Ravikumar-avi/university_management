# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class FeeStructure(models.Model):
    _name = 'fee.structure'
    _description = 'Fee Structure (Tuition, Lab, Hostel, etc.)'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'academic_year_id desc, program_id'

    name = fields.Char(string='Fee Structure Name', required=True, tracking=True)
    code = fields.Char(string='Code', required=True)
    active = fields.Boolean(string='Active', default=True)

    # Academic
    program_id = fields.Many2one('university.program', string='Program',
                                 required=True, tracking=True, index=True)
    department_id = fields.Many2one(related='program_id.department_id',
                                    string='Department', store=True)
    academic_year_id = fields.Many2one('university.academic.year', string='Academic Year',
                                       required=True, tracking=True)
    semester_id = fields.Many2one('university.semester', string='Semester')

    # Fee Category (Link to sale.product)
    product_id = fields.Many2one('product.product', string='Fee Product',
                                 domain=[('can_be_expensed', '=', False)],
                                 help='Link to product for invoicing')

    # Fee Components
    fee_line_ids = fields.One2many('fee.structure.line', 'fee_structure_id',
                                   string='Fee Components')

    # Total Amount
    total_amount = fields.Monetary(string='Total Fee', compute='_compute_total', store=True,
                                   currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id)

    # Payment Terms
    payment_term = fields.Selection([
        ('one_time', 'One Time Payment'),
        ('semester', 'Per Semester'),
        ('installment', 'Installments'),
    ], string='Payment Term', default='semester', required=True)

    # Installments
    number_of_installments = fields.Integer(string='Number of Installments', default=1)
    installment_ids = fields.One2many('fee.installment.config', 'fee_structure_id',
                                      string='Installment Configuration')

    # Due Date
    due_date = fields.Date(string='Fee Due Date', tracking=True)

    # Late Fee
    has_late_fee = fields.Boolean(string='Charge Late Fee', default=True)
    late_fee_amount = fields.Monetary(string='Late Fee Amount', currency_field='currency_id')
    late_fee_percentage = fields.Float(string='Late Fee %')
    grace_period_days = fields.Integer(string='Grace Period (Days)', default=0)

    # Discounts
    discount_ids = fields.One2many('fee.discount', 'fee_structure_id', string='Discounts')

    # Status
    state = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('archived', 'Archived'),
    ], string='Status', default='draft', tracking=True)

    # Description
    description = fields.Html(string='Description')

    _sql_constraints = [
        ('code_unique', 'unique(code, academic_year_id)',
         'Fee Structure Code must be unique per academic year!'),
    ]

    @api.depends('fee_line_ids', 'fee_line_ids.amount')
    def _compute_total(self):
        for record in self:
            record.total_amount = sum(record.fee_line_ids.mapped('amount'))

    def action_activate(self):
        self.write({'state': 'active'})

    def action_archive(self):
        self.write({'state': 'archived'})


class FeeStructureLine(models.Model):
    _name = 'fee.structure.line'
    _description = 'Fee Structure Line'
    _order = 'sequence, name'

    sequence = fields.Integer(string='Sequence', default=10)
    fee_structure_id = fields.Many2one('fee.structure', string='Fee Structure',
                                       required=True, ondelete='cascade')

    name = fields.Char(string='Fee Component', required=True)
    fee_type = fields.Selection([
        ('tuition', 'Tuition Fee'),
        ('lab', 'Lab Fee'),
        ('library', 'Library Fee'),
        ('exam', 'Examination Fee'),
        ('development', 'Development Fee'),
        ('sports', 'Sports Fee'),
        ('transport', 'Transport Fee'),
        ('hostel', 'Hostel Fee'),
        ('caution_deposit', 'Caution Deposit'),
        ('registration', 'Registration Fee'),
        ('other', 'Other'),
    ], string='Fee Type', required=True)

    amount = fields.Monetary(string='Amount', required=True, currency_field='currency_id')
    currency_id = fields.Many2one(related='fee_structure_id.currency_id', string='Currency')

    is_mandatory = fields.Boolean(string='Mandatory', default=True)
    is_refundable = fields.Boolean(string='Refundable', default=False)

    description = fields.Text(string='Description')


class FeeInstallmentConfig(models.Model):
    _name = 'fee.installment.config'
    _description = 'Fee Installment Configuration'
    _order = 'sequence, due_date'

    sequence = fields.Integer(string='Sequence', default=10)
    fee_structure_id = fields.Many2one('fee.structure', string='Fee Structure',
                                       required=True, ondelete='cascade')

    name = fields.Char(string='Installment Name', required=True)
    installment_number = fields.Integer(string='Installment Number', required=True)

    amount = fields.Monetary(string='Amount', required=True, currency_field='currency_id')
    percentage = fields.Float(string='Percentage of Total', compute='_compute_percentage')
    currency_id = fields.Many2one(related='fee_structure_id.currency_id')

    due_date = fields.Date(string='Due Date', required=True)

    description = fields.Text(string='Description')

    @api.depends('amount', 'fee_structure_id.total_amount')
    def _compute_percentage(self):
        for record in self:
            if record.fee_structure_id.total_amount:
                record.percentage = (record.amount / record.fee_structure_id.total_amount) * 100
            else:
                record.percentage = 0.0
