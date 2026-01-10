# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class FeeDiscount(models.Model):
    _name = 'fee.discount'
    _description = 'Fee Concession/Discount'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name'

    name = fields.Char(string='Discount Name', required=True, tracking=True)
    code = fields.Char(string='Discount Code', required=True)
    active = fields.Boolean(string='Active', default=True)

    # Discount Type
    discount_type = fields.Selection([
        ('merit', 'Merit Based'),
        ('sports', 'Sports Quota'),
        ('economically_weak', 'Economically Weaker Section'),
        ('sibling', 'Sibling Discount'),
        ('staff_ward', 'Staff Ward'),
        ('category', 'Category Based (SC/ST/OBC)'),
        ('special', 'Special Circumstance'),
        ('early_bird', 'Early Payment'),
        ('other', 'Other'),
    ], string='Discount Type', required=True, tracking=True)

    # Fee Structure
    fee_structure_id = fields.Many2one('fee.structure', string='Applicable to Fee Structure')
    program_ids = fields.Many2many('university.program', string='Applicable Programs')

    # Discount Value
    discount_method = fields.Selection([
        ('percentage', 'Percentage'),
        ('fixed', 'Fixed Amount'),
    ], string='Discount Method', required=True, default='percentage')

    discount_percentage = fields.Float(string='Discount %')
    discount_amount = fields.Monetary(string='Discount Amount', currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id)

    # Eligibility
    eligibility_criteria = fields.Html(string='Eligibility Criteria')
    min_percentage = fields.Float(string='Minimum Percentage Required')
    max_income = fields.Monetary(string='Maximum Family Income', currency_field='currency_id')

    # Validity
    start_date = fields.Date(string='Valid From')
    end_date = fields.Date(string='Valid Till')

    # Approval
    requires_approval = fields.Boolean(string='Requires Approval', default=True)

    # Applications
    application_ids = fields.One2many('fee.discount.application', 'discount_id',
                                      string='Applications')
    total_applications = fields.Integer(string='Total Applications',
                                        compute='_compute_applications')

    # Description
    description = fields.Html(string='Description')
    terms_conditions = fields.Html(string='Terms & Conditions')

    _sql_constraints = [
        ('code_unique', 'unique(code)', 'Discount Code must be unique!'),
    ]

    @api.depends('application_ids')
    def _compute_applications(self):
        for record in self:
            record.total_applications = len(record.application_ids)

    @api.constrains('discount_percentage')
    def _check_percentage(self):
        for record in self:
            if record.discount_method == 'percentage':
                if record.discount_percentage < 0 or record.discount_percentage > 100:
                    raise ValidationError(_('Discount percentage must be between 0 and 100!'))


class FeeDiscountApplication(models.Model):
    _name = 'fee.discount.application'
    _description = 'Fee Discount Application'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'application_date desc'

    name = fields.Char(string='Application Number', required=True, readonly=True,
                       copy=False, default='/')

    student_id = fields.Many2one('student.student', string='Student',
                                 required=True, tracking=True)
    discount_id = fields.Many2one('fee.discount', string='Discount',
                                  required=True, tracking=True)

    application_date = fields.Date(string='Application Date', default=fields.Date.today(),
                                   required=True)

    reason = fields.Html(string='Reason for Application', required=True)

    # Supporting Documents
    document_ids = fields.Many2many('ir.attachment', string='Supporting Documents')

    # Calculated Discount
    applicable_amount = fields.Monetary(string='Applicable Discount Amount',
                                        compute='_compute_discount', store=True,
                                        currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id)

    # Status
    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ], string='Status', default='draft', tracking=True)

    approved_by = fields.Many2one('res.users', string='Approved By', readonly=True)
    approval_date = fields.Date(string='Approval Date', readonly=True)
    rejection_reason = fields.Text(string='Rejection Reason')

    @api.model
    def create(self, vals):
        if vals.get('name', '/') == '/':
            vals['name'] = self.env['ir.sequence'].next_by_code('fee.discount.application') or '/'
        return super(FeeDiscountApplication, self).create(vals)

    @api.depends('discount_id', 'student_id')
    def _compute_discount(self):
        for record in self:
            if record.discount_id and record.student_id:
                # Get fee structure
                fee_structure = self.env['fee.structure'].search([
                    ('program_id', '=', record.student_id.program_id.id),
                    ('state', '=', 'active')
                ], limit=1)

                if fee_structure:
                    if record.discount_id.discount_method == 'percentage':
                        record.applicable_amount = (fee_structure.total_amount *
                                                    record.discount_id.discount_percentage) / 100
                    else:
                        record.applicable_amount = record.discount_id.discount_amount
                else:
                    record.applicable_amount = 0.0
            else:
                record.applicable_amount = 0.0

    def action_submit(self):
        self.write({'state': 'submitted'})

    def action_approve(self):
        self.write({
            'state': 'approved',
            'approved_by': self.env.user.id,
            'approval_date': fields.Date.today()
        })

    def action_reject(self):
        self.write({'state': 'rejected'})
