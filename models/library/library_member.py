# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class LibraryMember(models.Model):
    _name = 'library.member'
    _description = 'Library Membership'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'membership_date desc'

    name = fields.Char(string='Membership Number', required=True, readonly=True,
                       copy=False, default='/')

    # Member (can be student or faculty)
    member_type = fields.Selection([
        ('student', 'Student'),
        ('faculty', 'Faculty'),
        ('staff', 'Staff'),
        ('external', 'External Member'),
    ], string='Member Type', required=True, tracking=True)

    student_id = fields.Many2one('student.student', string='Student')
    faculty_id = fields.Many2one('faculty.faculty', string='Faculty')
    partner_id = fields.Many2one('res.partner', string='External Member')

    member_name = fields.Char(string='Member Name', compute='_compute_member_name', store=True)
    member_email = fields.Char(string='Email', compute='_compute_member_details')
    member_phone = fields.Char(string='Phone', compute='_compute_member_details')

    # Membership Details
    membership_date = fields.Date(string='Membership Date', default=fields.Date.today(),
                                  required=True, tracking=True)
    expiry_date = fields.Date(string='Expiry Date', tracking=True, store=True)
    is_active = fields.Boolean(string='Active Membership', compute='_compute_active', store=True)

    # Card
    card_number = fields.Char(string='Library Card Number')
    card_issued_date = fields.Date(string='Card Issue Date')

    # Limits
    max_books_allowed = fields.Integer(string='Max Books Allowed', default=3)
    max_issue_days = fields.Integer(string='Max Issue Days', default=14)

    # Issue History
    issue_ids = fields.One2many('library.issue', 'member_id', string='Issue History')
    current_issues = fields.Integer(string='Current Issues', compute='_compute_issues', store=True)
    total_issues = fields.Integer(string='Total Issues', compute='_compute_issues')

    # Reservations
    reservation_ids = fields.One2many('library.reservation', 'member_id', string='Reservations')

    # Fines
    fine_ids = fields.One2many('library.fine', 'member_id', string='Fines')
    total_fine = fields.Monetary(string='Total Fine', compute='_compute_fines',
                                 currency_field='currency_id')
    pending_fine = fields.Monetary(string='Pending Fine', compute='_compute_fines',
                                   currency_field='currency_id', store=True)

    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id)

    # Status
    state = fields.Selection([
        ('active', 'Active'),
        ('expired', 'Expired'),
        ('suspended', 'Suspended'),
        ('blocked', 'Blocked'),
    ], string='Status', default='active', tracking=True)

    # Notes
    notes = fields.Text(string='Notes')

    _sql_constraints = [
        ('name_unique', 'unique(name)', 'Membership Number must be unique!'),
    ]

    @api.model
    def create(self, vals):
        if vals.get('name', '/') == '/':
            vals['name'] = self.env['ir.sequence'].next_by_code('library.member') or '/'
        return super(LibraryMember, self).create(vals)

    @api.depends('member_type', 'student_id', 'faculty_id', 'partner_id')
    def _compute_member_name(self):
        for record in self:
            if record.member_type == 'student' and record.student_id:
                record.member_name = record.student_id.name
            elif record.member_type == 'faculty' and record.faculty_id:
                record.member_name = record.faculty_id.name
            elif record.partner_id:
                record.member_name = record.partner_id.name
            else:
                record.member_name = ''

    @api.depends('member_type', 'student_id', 'faculty_id', 'partner_id')
    def _compute_member_details(self):
        for record in self:
            if record.member_type == 'student' and record.student_id:
                record.member_email = record.student_id.email
                record.member_phone = record.student_id.mobile
            elif record.member_type == 'faculty' and record.faculty_id:
                record.member_email = record.faculty_id.work_email
                record.member_phone = record.faculty_id.work_mobile
            elif record.partner_id:
                record.member_email = record.partner_id.email
                record.member_phone = record.partner_id.phone
            else:
                record.member_email = ''
                record.member_phone = ''

    @api.depends('expiry_date')
    def _compute_active(self):
        today = fields.Date.today()
        for record in self:
            record.is_active = record.expiry_date >= today if record.expiry_date else True

    @api.depends('issue_ids', 'issue_ids.state')
    def _compute_issues(self):
        for record in self:
            record.current_issues = len(record.issue_ids.filtered(
                lambda i: i.state in ['issued', 'overdue']))
            record.total_issues = len(record.issue_ids)

    @api.depends('fine_ids', 'fine_ids.state', 'fine_ids.amount')
    def _compute_fines(self):
        for record in self:
            record.total_fine = sum(record.fine_ids.mapped('amount'))
            record.pending_fine = sum(record.fine_ids.filtered(
                lambda f: f.state == 'pending').mapped('amount'))
