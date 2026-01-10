# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class PlacementOffer(models.Model):
    _name = 'placement.offer'
    _description = 'Placement Offer Letters'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']
    _order = 'offer_date desc'

    name = fields.Char(string='Offer Letter Number', required=True, readonly=True,
                       copy=False, default='/')

    # Student
    student_id = fields.Many2one('student.student', string='Student',
                                 required=True, tracking=True, index=True)
    registration_number = fields.Char(related='student_id.registration_number',
                                      string='Registration Number')

    # Placement Drive
    drive_id = fields.Many2one('placement.drive', string='Placement Drive',
                               required=True, tracking=True, index=True)
    company_id = fields.Many2one(related='drive_id.company_id', string='Company', store=True)
    application_id = fields.Many2one('placement.application', string='Application')

    # Offer Details
    offer_date = fields.Date(string='Offer Date', default=fields.Date.today(),
                             required=True, tracking=True)

    job_title = fields.Char(string='Job Title', required=True)
    job_location = fields.Char(string='Job Location')

    # Salary Package
    ctc = fields.Monetary(string='CTC (Per Annum)', required=True, currency_field='currency_id')
    fixed_component = fields.Monetary(string='Fixed Component', currency_field='currency_id')
    variable_component = fields.Monetary(string='Variable Component', currency_field='currency_id')

    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id)

    # Joining Details
    joining_date = fields.Date(string='Expected Joining Date', tracking=True)
    joining_location = fields.Char(string='Joining Location')

    # Bond Details
    has_bond = fields.Boolean(string='Service Bond')
    bond_duration = fields.Integer(string='Bond Duration (Months)')
    bond_amount = fields.Monetary(string='Bond Amount', currency_field='currency_id')

    # Offer Letter
    offer_letter = fields.Binary(string='Offer Letter', attachment=True)
    offer_letter_filename = fields.Char(string='Filename')

    # Acceptance
    acceptance_deadline = fields.Date(string='Acceptance Deadline')
    acceptance_date = fields.Date(string='Acceptance Date')

    # Status
    state = fields.Selection([
        ('draft', 'Draft'),
        ('offered', 'Offered'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
        ('withdrawn', 'Withdrawn'),
    ], string='Status', default='draft', tracking=True)

    # Rejection Reason
    rejection_reason = fields.Text(string='Rejection Reason')

    # Remarks
    remarks = fields.Text(string='Remarks')

    _sql_constraints = [
        ('name_unique', 'unique(name)', 'Offer Letter Number must be unique!'),
    ]

    @api.model
    def create(self, vals):
        if vals.get('name', '/') == '/':
            vals['name'] = self.env['ir.sequence'].next_by_code('placement.offer') or '/'
        return super(PlacementOffer, self).create(vals)

    def action_send_offer(self):
        """Send offer letter to student"""
        self.write({'state': 'offered'})
        template = self.env.ref('university_management.email_template_placement_offer',
                                raise_if_not_found=False)
        if template:
            template.send_mail(self.id, force_send=True)

    def action_accept(self):
        self.write({
            'state': 'accepted',
            'acceptance_date': fields.Date.today()
        })

    def action_reject(self):
        self.write({'state': 'rejected'})

    def action_withdraw(self):
        self.write({'state': 'withdrawn'})
