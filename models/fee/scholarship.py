# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class Scholarship(models.Model):
    _name = 'scholarship.scholarship'
    _description = 'Scholarship Management'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name'

    name = fields.Char(string='Scholarship Name', required=True, tracking=True)
    code = fields.Char(string='Scholarship Code', required=True)
    active = fields.Boolean(string='Active', default=True)

    # Scholarship Type
    scholarship_type = fields.Selection([
        ('government', 'Government Scholarship'),
        ('institutional', 'Institutional Scholarship'),
        ('private', 'Private/Corporate Scholarship'),
        ('merit', 'Merit Based'),
        ('need', 'Need Based'),
        ('sports', 'Sports Scholarship'),
        ('minority', 'Minority Scholarship'),
        ('research', 'Research Scholarship'),
    ], string='Scholarship Type', required=True, tracking=True)

    # Sponsor (link to res.partner for companies/organizations)
    sponsor_id = fields.Many2one('res.partner', string='Sponsor/Organization',
                                 domain=[('is_company', '=', True)])
    sponsor_type = fields.Selection([
        ('government', 'Government'),
        ('corporate', 'Corporate'),
        ('ngo', 'NGO'),
        ('alumni', 'Alumni'),
        ('individual', 'Individual'),
    ], string='Sponsor Type')

    # Financial Details
    total_amount = fields.Monetary(string='Total Scholarship Amount',
                                   currency_field='currency_id', required=True)
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id)

    amount_per_student = fields.Monetary(string='Amount per Student',
                                         currency_field='currency_id')

    # Coverage
    coverage_type = fields.Selection([
        ('full', 'Full Tuition Fee'),
        ('partial', 'Partial Coverage'),
        ('fixed', 'Fixed Amount'),
    ], string='Coverage Type', default='partial', required=True)

    coverage_percentage = fields.Float(string='Coverage %')

    # Number of Scholarships
    total_scholarships = fields.Integer(string='Total Scholarships Available', default=1)
    awarded_count = fields.Integer(string='Awarded', compute='_compute_counts')
    available_count = fields.Integer(string='Available', compute='_compute_counts')

    # Eligibility
    eligibility_criteria = fields.Html(string='Eligibility Criteria', required=True)
    min_percentage = fields.Float(string='Minimum Percentage/CGPA Required')
    max_family_income = fields.Monetary(string='Maximum Family Income',
                                        currency_field='currency_id')

    # Academic Year
    academic_year_id = fields.Many2one('university.academic.year', string='Academic Year',
                                       required=True)

    # Applicable Programs
    program_ids = fields.Many2many('university.program', string='Applicable Programs')
    department_ids = fields.Many2many('university.department', string='Applicable Departments')

    # Application Period
    application_start_date = fields.Date(string='Application Start Date', required=True)
    application_end_date = fields.Date(string='Application End Date', required=True)

    # Selection Process
    selection_process = fields.Html(string='Selection Process')
    requires_interview = fields.Boolean(string='Requires Interview')
    requires_test = fields.Boolean(string='Requires Test')

    # Applications
    application_ids = fields.One2many('scholarship.application', 'scholarship_id',
                                      string='Applications')
    total_applications = fields.Integer(string='Total Applications',
                                        compute='_compute_counts')

    # Documents Required
    required_document_types = fields.Many2many('scholarship.document.type',
                                               string='Required Documents')

    # Payment Schedule
    payment_frequency = fields.Selection([
        ('one_time', 'One Time'),
        ('semester', 'Per Semester'),
        ('annual', 'Annual'),
        ('monthly', 'Monthly'),
    ], string='Payment Frequency', default='semester')

    # Terms & Conditions
    terms_conditions = fields.Html(string='Terms & Conditions')

    # Renewal
    is_renewable = fields.Boolean(string='Renewable', default=False)
    renewal_criteria = fields.Html(string='Renewal Criteria')

    # Status
    state = fields.Selection([
        ('draft', 'Draft'),
        ('open', 'Open for Applications'),
        ('closed', 'Applications Closed'),
        ('selection', 'Selection in Progress'),
        ('awarded', 'Scholarships Awarded'),
        ('completed', 'Completed'),
    ], string='Status', default='draft', tracking=True)

    # Description
    description = fields.Html(string='Description')

    _sql_constraints = [
        ('code_unique', 'unique(code)', 'Scholarship Code must be unique!'),
    ]

    @api.depends('application_ids', 'total_scholarships')
    def _compute_counts(self):
        for record in self:
            record.total_applications = len(record.application_ids)
            record.awarded_count = len(record.application_ids.filtered(
                lambda a: a.state == 'awarded'))
            record.available_count = record.total_scholarships - record.awarded_count

    def action_open_applications(self):
        self.write({'state': 'open'})

    def action_close_applications(self):
        self.write({'state': 'closed'})

    def action_start_selection(self):
        self.write({'state': 'selection'})

    def action_complete_awards(self):
        self.write({'state': 'awarded'})


class ScholarshipApplication(models.Model):
    _name = 'scholarship.application'
    _description = 'Scholarship Application'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']
    _order = 'application_date desc'

    name = fields.Char(string='Application Number', required=True, readonly=True,
                       copy=False, default='/')

    # Student
    student_id = fields.Many2one('student.student', string='Student',
                                 required=True, tracking=True, index=True)
    registration_number = fields.Char(related='student_id.registration_number',
                                      string='Registration Number')
    program_id = fields.Many2one(related='student_id.program_id', string='Program', store=True)
    current_cgpa = fields.Float(related='student_id.cgpa', string='Current CGPA')

    # Scholarship
    scholarship_id = fields.Many2one('scholarship.scholarship', string='Scholarship',
                                     required=True, tracking=True, index=True)

    # Application Details
    application_date = fields.Date(string='Application Date', default=fields.Date.today(),
                                   required=True)

    # Reason & Justification
    reason = fields.Html(string='Reason for Application', required=True)
    achievements = fields.Html(string='Academic/Co-curricular Achievements')
    financial_need = fields.Html(string='Statement of Financial Need')

    # Family Details
    family_annual_income = fields.Monetary(string='Family Annual Income',
                                           currency_field='currency_id', required=True)
    family_size = fields.Integer(string='Family Size')
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id)

    # Academic Performance
    previous_year_percentage = fields.Float(string='Previous Year %')
    overall_percentage = fields.Float(string='Overall %')

    # Documents
    document_ids = fields.One2many('scholarship.application.document', 'application_id',
                                   string='Documents')
    documents_verified = fields.Boolean(string='All Documents Verified',
                                        compute='_compute_documents_verified', store=True)

    # Selection Score
    selection_score = fields.Float(string='Selection Score')
    rank = fields.Integer(string='Rank')

    # Interview
    interview_scheduled = fields.Boolean(string='Interview Scheduled')
    interview_date = fields.Datetime(string='Interview Date')
    interview_remarks = fields.Text(string='Interview Remarks')

    # Recommendation
    recommended_by = fields.Many2one('faculty.faculty', string='Recommended By')
    recommendation_letter = fields.Html(string='Recommendation Letter')

    # Award Details
    awarded_amount = fields.Monetary(string='Awarded Amount', currency_field='currency_id')
    award_date = fields.Date(string='Award Date')
    award_certificate = fields.Binary(string='Award Certificate')

    # Status
    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('under_review', 'Under Review'),
        ('shortlisted', 'Shortlisted'),
        ('interview', 'Interview Scheduled'),
        ('approved', 'Approved'),
        ('awarded', 'Awarded'),
        ('rejected', 'Rejected'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', tracking=True)

    # Rejection
    rejection_reason = fields.Text(string='Rejection Reason')

    # Notes
    notes = fields.Text(string='Notes')

    _sql_constraints = [
        ('name_unique', 'unique(name)', 'Application Number must be unique!'),
    ]

    @api.model
    def create(self, vals):
        if vals.get('name', '/') == '/':
            vals['name'] = self.env['ir.sequence'].next_by_code('scholarship.application') or '/'
        return super(ScholarshipApplication, self).create(vals)

    @api.depends('document_ids', 'document_ids.is_verified')
    def _compute_documents_verified(self):
        for record in self:
            if record.document_ids:
                record.documents_verified = all(doc.is_verified for doc in record.document_ids)
            else:
                record.documents_verified = False

    def action_submit(self):
        self.write({'state': 'submitted'})

    def action_review(self):
        self.write({'state': 'under_review'})

    def action_shortlist(self):
        self.write({'state': 'shortlisted'})

    def action_schedule_interview(self):
        self.write({'state': 'interview', 'interview_scheduled': True})

    def action_approve(self):
        self.write({'state': 'approved'})

    def action_award(self):
        self.write({
            'state': 'awarded',
            'award_date': fields.Date.today(),
            'awarded_amount': self.scholarship_id.amount_per_student
        })

    def action_reject(self):
        self.write({'state': 'rejected'})


class ScholarshipDocumentType(models.Model):
    _name = 'scholarship.document.type'
    _description = 'Scholarship Document Type'

    name = fields.Char(string='Document Type', required=True)
    description = fields.Text(string='Description')


class ScholarshipApplicationDocument(models.Model):
    _name = 'scholarship.application.document'
    _description = 'Scholarship Application Document'

    application_id = fields.Many2one('scholarship.application', string='Application',
                                     required=True, ondelete='cascade')
    document_type_id = fields.Many2one('scholarship.document.type', string='Document Type',
                                       required=True)
    attachment_id = fields.Many2one('ir.attachment', string='Attachment', required=True)

    is_verified = fields.Boolean(string='Verified')
    verified_by = fields.Many2one('res.users', string='Verified By', readonly=True)
    verification_date = fields.Date(string='Verification Date', readonly=True)
