# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class FacultySalary(models.Model):
    _name = 'faculty.salary'
    _description = 'Faculty Salary Management'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'payment_date desc'

    name = fields.Char(string='Salary Slip Number', required=True, readonly=True,
                       copy=False, default='/')

    # Faculty
    faculty_id = fields.Many2one('faculty.faculty', string='Faculty',
                                 required=True, tracking=True, index=True)
    employee_id = fields.Many2one(related='faculty_id.employee_id', string='Employee', store=True)
    department_id = fields.Many2one(related='faculty_id.department_id',
                                    string='Department', store=True)
    designation_id = fields.Many2one(related='faculty_id.designation_id',
                                     string='Designation', store=True)

    # Salary Period
    month = fields.Selection([
        ('1', 'January'), ('2', 'February'), ('3', 'March'),
        ('4', 'April'), ('5', 'May'), ('6', 'June'),
        ('7', 'July'), ('8', 'August'), ('9', 'September'),
        ('10', 'October'), ('11', 'November'), ('12', 'December'),
    ], string='Month', required=True)
    year = fields.Integer(string='Year', required=True, default=lambda self: fields.Date.today().year)

    # Payment Date
    payment_date = fields.Date(string='Payment Date', tracking=True)

    # Salary Components - Earnings
    basic_salary = fields.Monetary(string='Basic Salary', required=True,
                                   currency_field='currency_id')
    hra = fields.Monetary(string='HRA', currency_field='currency_id')
    da = fields.Monetary(string='DA (Dearness Allowance)', currency_field='currency_id')
    special_allowance = fields.Monetary(string='Special Allowance', currency_field='currency_id')
    transport_allowance = fields.Monetary(string='Transport Allowance', currency_field='currency_id')
    medical_allowance = fields.Monetary(string='Medical Allowance', currency_field='currency_id')
    other_allowances = fields.Monetary(string='Other Allowances', currency_field='currency_id')

    # Bonus & Incentives
    performance_bonus = fields.Monetary(string='Performance Bonus', currency_field='currency_id')
    overtime_pay = fields.Monetary(string='Overtime Pay', currency_field='currency_id')

    # Total Earnings
    total_earnings = fields.Monetary(string='Total Earnings', compute='_compute_totals',
                                     store=True, currency_field='currency_id')

    # Deductions
    pf = fields.Monetary(string='PF (Provident Fund)', currency_field='currency_id')
    esi = fields.Monetary(string='ESI', currency_field='currency_id')
    professional_tax = fields.Monetary(string='Professional Tax', currency_field='currency_id')
    income_tax = fields.Monetary(string='Income Tax (TDS)', currency_field='currency_id')
    advance_deduction = fields.Monetary(string='Advance Deduction', currency_field='currency_id')
    loan_deduction = fields.Monetary(string='Loan Deduction', currency_field='currency_id')
    other_deductions = fields.Monetary(string='Other Deductions', currency_field='currency_id')

    # Leave Deductions
    leave_without_pay_days = fields.Float(string='LWP Days')
    leave_deduction = fields.Monetary(string='Leave Deduction', compute='_compute_leave_deduction',
                                      store=True, currency_field='currency_id')

    # Total Deductions
    total_deductions = fields.Monetary(string='Total Deductions', compute='_compute_totals',
                                       store=True, currency_field='currency_id')

    # Net Salary
    net_salary = fields.Monetary(string='Net Salary', compute='_compute_totals',
                                 store=True, currency_field='currency_id')

    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id)

    # Payment Method
    payment_method = fields.Selection([
        ('bank_transfer', 'Bank Transfer'),
        ('cheque', 'Cheque'),
        ('cash', 'Cash'),
    ], string='Payment Method', default='bank_transfer')

    payment_reference = fields.Char(string='Payment Reference')

    # Bank Details
    bank_account_number = fields.Char(related='faculty_id.bank_account_number',
                                      string='Bank Account')
    bank_name = fields.Char(related='faculty_id.bank_name', string='Bank Name')

    # Status
    state = fields.Selection([
        ('draft', 'Draft'),
        ('verified', 'Verified'),
        ('approved', 'Approved'),
        ('paid', 'Paid'),
    ], string='Status', default='draft', tracking=True)

    # Notes
    notes = fields.Text(string='Notes')

    _sql_constraints = [
        ('name_unique', 'unique(name)', 'Salary Slip Number must be unique!'),
        ('unique_salary', 'unique(faculty_id, month, year)',
         'Salary already generated for this faculty in this month!'),
    ]

    @api.model
    def create(self, vals):
        if vals.get('name', '/') == '/':
            vals['name'] = self.env['ir.sequence'].next_by_code('faculty.salary') or '/'
        return super(FacultySalary, self).create(vals)

    @api.depends('basic_salary', 'hra', 'da', 'special_allowance', 'transport_allowance',
                 'medical_allowance', 'other_allowances', 'performance_bonus', 'overtime_pay',
                 'pf', 'esi', 'professional_tax', 'income_tax', 'advance_deduction',
                 'loan_deduction', 'other_deductions', 'leave_deduction')
    def _compute_totals(self):
        for record in self:
            record.total_earnings = (record.basic_salary + record.hra + record.da +
                                     record.special_allowance + record.transport_allowance +
                                     record.medical_allowance + record.other_allowances +
                                     record.performance_bonus + record.overtime_pay)

            record.total_deductions = (record.pf + record.esi + record.professional_tax +
                                       record.income_tax + record.advance_deduction +
                                       record.loan_deduction + record.other_deductions +
                                       record.leave_deduction)

            record.net_salary = record.total_earnings - record.total_deductions

    @api.depends('basic_salary', 'leave_without_pay_days')
    def _compute_leave_deduction(self):
        for record in self:
            if record.leave_without_pay_days > 0:
                # Assuming 30 days in a month
                per_day_salary = record.basic_salary / 30
                record.leave_deduction = per_day_salary * record.leave_without_pay_days
            else:
                record.leave_deduction = 0.0

    def action_verify(self):
        self.write({'state': 'verified'})

    def action_approve(self):
        self.write({'state': 'approved'})

    def action_mark_paid(self):
        self.write({'state': 'paid', 'payment_date': fields.Date.today()})

    def action_print_salary_slip(self):
        return self.env.ref('university_management.action_report_salary_slip').report_action(self)
