# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class FacultyDesignation(models.Model):
    _name = 'faculty.designation'
    _description = 'Faculty Designation (Professor, Assistant Prof, etc.)'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'sequence, name'

    name = fields.Char(string='Designation Name', required=True, tracking=True,
                       help='e.g., Professor, Associate Professor, Assistant Professor')
    code = fields.Char(string='Code', required=True)
    sequence = fields.Integer(string='Sequence', default=10)
    active = fields.Boolean(string='Active', default=True)

    # Hierarchy Level
    level = fields.Selection([
        ('professor', 'Professor'),
        ('associate_professor', 'Associate Professor'),
        ('assistant_professor', 'Assistant Professor'),
        ('lecturer', 'Lecturer'),
        ('senior_lecturer', 'Senior Lecturer'),
        ('guest_faculty', 'Guest Faculty'),
        ('visiting_faculty', 'Visiting Faculty'),
        ('lab_assistant', 'Lab Assistant'),
        ('teaching_assistant', 'Teaching Assistant'),
    ], string='Designation Level', required=True)

    # Salary Range
    min_salary = fields.Monetary(string='Minimum Salary', currency_field='currency_id')
    max_salary = fields.Monetary(string='Maximum Salary', currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id)

    # Qualification Requirements
    min_qualification = fields.Selection([
        ('phd', 'Ph.D'),
        ('mphil', 'M.Phil'),
        ('postgraduate', 'Post Graduate'),
        ('graduate', 'Graduate'),
    ], string='Minimum Qualification Required')

    min_experience_years = fields.Integer(string='Minimum Experience (Years)')

    # Workload
    max_teaching_hours = fields.Float(string='Maximum Teaching Hours/Week', default=18.0)

    # Responsibilities
    responsibilities = fields.Html(string='Key Responsibilities')

    # Faculty Count
    faculty_ids = fields.One2many('faculty.faculty', 'designation_id', string='Faculty')
    total_faculty = fields.Integer(string='Total Faculty', compute='_compute_total')

    # Description
    description = fields.Text(string='Description')

    _sql_constraints = [
        ('code_unique', 'unique(code)', 'Designation Code must be unique!'),
    ]

    @api.depends('faculty_ids')
    def _compute_total(self):
        for record in self:
            record.total_faculty = len(record.faculty_ids)

    def action_faculty(self):
        """Open faculty members with this designation."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Faculty',
            'res_model': 'faculty.faculty',
            'view_mode': 'list,kanban,form',
            'domain': [('designation_id', '=', self.id)],
            'context': {
                'default_designation_id': self.id,
                'search_default_designation_id': self.id,
            },
        }


class FacultyQualification(models.Model):
    _name = 'faculty.qualification'
    _description = 'Faculty Qualification Details'
    _order = 'year_of_passing desc'

    faculty_id = fields.Many2one('faculty.faculty', string='Faculty',
                                 required=True, ondelete='cascade')

    degree = fields.Char(string='Degree/Qualification', required=True)
    specialization = fields.Char(string='Specialization/Major')
    institution = fields.Char(string='Institution/University', required=True)
    year_of_passing = fields.Integer(string='Year of Passing', required=True)
    percentage = fields.Float(string='Percentage/CGPA')

    # Certificate
    certificate = fields.Binary(string='Certificate/Document')
    certificate_name = fields.Char(string='File Name')

    is_verified = fields.Boolean(string='Verified')
