# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class FeePayment(models.Model):
    _name = 'fee.payment'
    _description = 'Fee Payment Records'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']
    _order = 'payment_date desc'

    name = fields.Char(string='Payment Receipt Number', required=True, readonly=True,
                       copy=False, default='/')

    # Student
    student_id = fields.Many2one('student.student', string='Student',
                                 required=True, tracking=True, index=True)
    registration_number = fields.Char(related='student_id.registration_number',
                                      string='Registration Number')
    program_id = fields.Many2one(related='student_id.program_id', string='Program', store=True)
    department_id = fields.Many2one(related='student_id.department_id',
                                    string='Department', store=True)

    # Fee Structure
    fee_structure_id = fields.Many2one('fee.structure', string='Fee Structure',
                                       required=True, tracking=True)
    academic_year_id = fields.Many2one(related='fee_structure_id.academic_year_id',
                                       string='Academic Year', store=True)
    semester_id = fields.Many2one(related='fee_structure_id.semester_id',
                                  string='Semester', store=True)

    # Payment Details
    payment_date = fields.Date(string='Payment Date', default=fields.Date.today(),
                               required=True, tracking=True, index=True)
    due_date = fields.Date(string='Due Date', tracking=True)

    # Amount
    amount = fields.Monetary(string='Amount Paid', required=True, tracking=True,
                             currency_field='currency_id')
    late_fee = fields.Monetary(string='Late Fee', currency_field='currency_id')
    discount_amount = fields.Monetary(string='Discount', currency_field='currency_id')
    total_amount = fields.Monetary(string='Total Amount', compute='_compute_total',
                                   store=True, currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id)

    # Payment Method
    payment_method = fields.Selection([
        ('cash', 'Cash'),
        ('bank_transfer', 'Bank Transfer'),
        ('cheque', 'Cheque'),
        ('dd', 'Demand Draft'),
        ('online', 'Online Payment'),
        ('upi', 'UPI'),
        ('credit_card', 'Credit Card'),
        ('debit_card', 'Debit Card'),
        ('netbanking', 'Net Banking'),
    ], string='Payment Method', required=True, default='cash', tracking=True)

    # Payment Reference
    payment_reference = fields.Char(string='Payment Reference/Transaction ID', tracking=True)
    cheque_number = fields.Char(string='Cheque/DD Number')
    cheque_date = fields.Date(string='Cheque/DD Date')
    bank_name = fields.Char(string='Bank Name')

    # Installment
    installment_id = fields.Many2one('fee.installment', string='Installment')

    # Discount
    discount_id = fields.Many2one('fee.discount', string='Applied Discount')

    # Scholarship
    scholarship_id = fields.Many2one('scholarship.scholarship', string='Scholarship Applied')

    # Account Invoice (Integration with account module)
    invoice_id = fields.Many2one('account.move', string='Invoice', readonly=True)
    invoice_status = fields.Selection(related='invoice_id.state', string='Invoice Status')

    # Payment Status
    state = fields.Selection([
        ('draft', 'Draft'),
        ('pending', 'Pending Verification'),
        ('verified', 'Verified'),
        ('paid', 'Paid'),
        ('bounced', 'Cheque Bounced'),
        ('refunded', 'Refunded'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', tracking=True, index=True)

    # Verification
    verified_by = fields.Many2one('res.users', string='Verified By', readonly=True)
    verification_date = fields.Date(string='Verification Date', readonly=True)

    # Receipt
    receipt_printed = fields.Boolean(string='Receipt Printed')
    receipt_sent = fields.Boolean(string='Receipt Sent to Parent')

    # Collected By
    collected_by = fields.Many2one('res.users', string='Collected By',
                                   default=lambda self: self.env.user, tracking=True)

    # Refund
    refund_reason = fields.Text(string='Refund Reason')
    refund_date = fields.Date(string='Refund Date')
    refund_amount = fields.Monetary(string='Refund Amount', currency_field='currency_id')

    # Notes
    notes = fields.Text(string='Notes')

    _sql_constraints = [
        ('name_unique', 'unique(name)', 'Payment Receipt Number must be unique!'),
    ]

    @api.model
    def create(self, vals):
        if vals.get('name', '/') == '/':
            vals['name'] = self.env['ir.sequence'].next_by_code('fee.payment') or '/'
        return super(FeePayment, self).create(vals)

    @api.depends('amount', 'late_fee', 'discount_amount')
    def _compute_total(self):
        for record in self:
            record.total_amount = record.amount + record.late_fee - record.discount_amount

    @api.onchange('student_id', 'fee_structure_id')
    def _onchange_fee_structure(self):
        if self.student_id and self.fee_structure_id:
            self.amount = self.fee_structure_id.total_amount
            self.due_date = self.fee_structure_id.due_date

            # Calculate late fee if overdue
            if self.due_date and fields.Date.today() > self.due_date:
                days_late = (fields.Date.today() - self.due_date).days
                grace_period = self.fee_structure_id.grace_period_days or 0

                if days_late > grace_period and self.fee_structure_id.has_late_fee:
                    if self.fee_structure_id.late_fee_amount:
                        self.late_fee = self.fee_structure_id.late_fee_amount
                    elif self.fee_structure_id.late_fee_percentage:
                        self.late_fee = (self.amount * self.fee_structure_id.late_fee_percentage) / 100

    def action_verify(self):
        """Verify payment"""
        self.write({
            'state': 'verified',
            'verified_by': self.env.user.id,
            'verification_date': fields.Date.today()
        })

    def action_confirm_payment(self):
        """Confirm payment and create invoice"""
        self.write({'state': 'paid'})
        self._create_invoice()
        self._send_receipt()

    def action_mark_bounced(self):
        """Mark cheque as bounced"""
        self.write({'state': 'bounced'})

    def action_refund(self):
        """Process refund"""
        self.write({
            'state': 'refunded',
            'refund_date': fields.Date.today()
        })

    def action_cancel(self):
        """Cancel payment"""
        self.write({'state': 'cancelled'})

    def action_print_receipt(self):
        """Print fee receipt"""
        self.write({'receipt_printed': True})
        return self.env.ref('university_management.action_report_fee_receipt').report_action(self)

    def _create_invoice(self):
        """Create account invoice for payment"""
        if not self.invoice_id:
            invoice_lines = []

            # Fee lines from structure
            for line in self.fee_structure_id.fee_line_ids:
                invoice_lines.append((0, 0, {
                    'name': line.name,
                    'quantity': 1,
                    'price_unit': line.amount,
                    'product_id': self.fee_structure_id.product_id.id if self.fee_structure_id.product_id else False,
                }))

            # Late fee
            if self.late_fee > 0:
                invoice_lines.append((0, 0, {
                    'name': 'Late Fee',
                    'quantity': 1,
                    'price_unit': self.late_fee,
                }))

            # Discount
            if self.discount_amount > 0:
                invoice_lines.append((0, 0, {
                    'name': 'Discount',
                    'quantity': 1,
                    'price_unit': -self.discount_amount,
                }))

            invoice_vals = {
                'move_type': 'out_invoice',
                'partner_id': self.student_id.partner_id.id,
                'invoice_date': self.payment_date,
                'invoice_line_ids': invoice_lines,
                'payment_reference': self.payment_reference,
            }

            invoice = self.env['account.move'].create(invoice_vals)
            invoice.action_post()
            self.invoice_id = invoice.id

    def _send_receipt(self):
        """Send receipt via email"""
        self.write({'receipt_sent': True})
        template = self.env.ref('university_management.email_template_fee_receipt',
                                raise_if_not_found=False)
        if template:
            template.send_mail(self.id, force_send=True)
