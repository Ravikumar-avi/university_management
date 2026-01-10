# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class StudentProject(models.Model):
    _name = 'student.project'
    _description = 'Student Final Year Projects'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']
    _inherits = {'project.project': 'project_id'}  # Integration with project module
    _order = 'create_date desc'

    # Project (inherited from project.project)
    project_id = fields.Many2one('project.project', string='Related Project',
                                 required=True, ondelete='cascade', auto_join=True)

    # Project Code
    project_code = fields.Char(string='Project Code', required=True, readonly=True,
                               copy=False, default='/')

    # Academic Details
    academic_year_id = fields.Many2one('university.academic.year', string='Academic Year',
                                       required=True, tracking=True)
    semester_id = fields.Many2one('university.semester', string='Semester',
                                  required=True, tracking=True)

    program_id = fields.Many2one('university.program', string='Program', required=True)
    department_id = fields.Many2one('university.department', string='Department', required=True)

    # Project Type
    project_type = fields.Selection([
        ('major', 'Major Project'),
        ('minor', 'Minor Project'),
        ('research', 'Research Project'),
        ('internship', 'Internship Project'),
        ('capstone', 'Capstone Project'),
    ], string='Project Type', required=True, default='major', tracking=True)

    # Students (Team Members)
    student_ids = fields.Many2many('student.student', 'project_student_rel',
                                   'project_id', 'student_id',
                                   string='Team Members', required=True)
    team_leader_id = fields.Many2one('student.student', string='Team Leader')
    total_students = fields.Integer(string='Team Size', compute='_compute_team_size')

    # Project Title & Details
    project_title = fields.Char(string='Project Title', required=True, tracking=True)
    project_domain = fields.Selection([
        ('web', 'Web Development'),
        ('mobile', 'Mobile App Development'),
        ('ml', 'Machine Learning/AI'),
        ('iot', 'IoT'),
        ('blockchain', 'Blockchain'),
        ('cloud', 'Cloud Computing'),
        ('cybersecurity', 'Cybersecurity'),
        ('robotics', 'Robotics'),
        ('data_science', 'Data Science'),
        ('ar_vr', 'AR/VR'),
        ('other', 'Other'),
    ], string='Project Domain')

    abstract = fields.Html(string='Abstract', required=True)
    objectives = fields.Html(string='Objectives')
    methodology = fields.Html(string='Methodology')

    # Technology Stack
    technologies_used = fields.Text(string='Technologies/Tools Used')
    programming_languages = fields.Char(string='Programming Languages')

    # Guide
    guide_id = fields.Many2one('faculty.faculty', string='Project Guide',
                               required=True, tracking=True)
    co_guide_id = fields.Many2one('faculty.faculty', string='Co-Guide')

    # External Guide (if industry project)
    has_external_guide = fields.Boolean(string='Has External Guide')
    external_guide_name = fields.Char(string='External Guide Name')
    external_guide_company = fields.Char(string='Company/Organization')
    external_guide_email = fields.Char(string='External Guide Email')

    # Timeline
    start_date = fields.Date(string='Start Date', required=True, tracking=True)
    expected_completion = fields.Date(string='Expected Completion', required=True)
    actual_completion = fields.Date(string='Actual Completion Date', tracking=True)

    # Progress
    progress_percentage = fields.Float(string='Progress %', default=0.0, tracking=True)

    # Milestones (using project.task from project module)
    milestone_ids = fields.One2many('project.task', 'project_id', string='Milestones/Tasks')

    # Documents & Deliverables
    synopsis = fields.Binary(string='Project Synopsis', attachment=True)
    synopsis_filename = fields.Char(string='Synopsis Filename')

    report = fields.Binary(string='Final Report', attachment=True)
    report_filename = fields.Char(string='Report Filename')

    ppt = fields.Binary(string='Presentation (PPT)', attachment=True)
    ppt_filename = fields.Char(string='PPT Filename')

    source_code_url = fields.Char(string='Source Code URL (GitHub/GitLab)')
    demo_url = fields.Char(string='Demo/Live URL')
    demo_video_url = fields.Char(string='Demo Video URL')

    # Evaluation
    evaluation_ids = fields.One2many('project.evaluation', 'project_id', string='Evaluations')

    # Presentation/Viva
    presentation_ids = fields.One2many('project.presentation', 'project_id', string='Presentations')

    # Marks
    internal_marks = fields.Float(string='Internal Marks')
    external_marks = fields.Float(string='External Marks')
    total_marks = fields.Float(string='Total Marks', compute='_compute_total_marks', store=True)
    max_marks = fields.Float(string='Maximum Marks', default=100.0)

    grade = fields.Char(string='Grade')

    # Status
    state = fields.Selection([
        ('draft', 'Draft'),
        ('proposed', 'Proposed'),
        ('approved', 'Approved'),
        ('in_progress', 'In Progress'),
        ('submitted', 'Submitted'),
        ('evaluated', 'Evaluated'),
        ('completed', 'Completed'),
        ('rejected', 'Rejected'),
    ], string='Status', default='draft', tracking=True)

    # Remarks
    remarks = fields.Text(string='Remarks')

    _sql_constraints = [
        ('project_code_unique', 'unique(project_code)', 'Project Code must be unique!'),
    ]

    @api.model
    def create(self, vals):
        if vals.get('project_code', '/') == '/':
            vals['project_code'] = self.env['ir.sequence'].next_by_code('student.project') or '/'
        return super(StudentProject, self).create(vals)

    @api.depends('student_ids')
    def _compute_team_size(self):
        for record in self:
            record.total_students = len(record.student_ids)

    @api.depends('internal_marks', 'external_marks')
    def _compute_total_marks(self):
        for record in self:
            record.total_marks = record.internal_marks + record.external_marks

    def action_propose(self):
        self.write({'state': 'proposed'})

    def action_approve(self):
        self.write({'state': 'approved'})

    def action_start(self):
        self.write({'state': 'in_progress'})

    def action_submit(self):
        self.write({'state': 'submitted'})

    def action_evaluate(self):
        self.write({'state': 'evaluated'})

    def action_complete(self):
        self.write({'state': 'completed', 'actual_completion': fields.Date.today()})

    def action_reject(self):
        self.write({'state': 'rejected'})

    def action_view_milestones(self):
        """Open milestones/tasks for this project."""
        self.ensure_one()
        return {
            'name': _('Project Milestones/Tasks'),
            'type': 'ir.actions.act_window',
            'res_model': 'project.task',
            'view_mode': 'list,form,kanban,calendar,gantt',
            'domain': [('project_id', '=', self.project_id.id)],
            'context': {'default_project_id': self.project_id.id},
        }

    def action_view_evaluations(self):
        """Open evaluations for this project."""
        self.ensure_one()
        return {
            'name': _('Project Evaluations'),
            'type': 'ir.actions.act_window',
            'res_model': 'project.evaluation',
            'view_mode': 'list,form',
            'domain': [('project_id', '=', self.id)],
            'context': {'default_project_id': self.id},
        }

    def action_view_presentations(self):
        """Open presentations/vivas for this project."""
        self.ensure_one()
        return {
            'name': _('Project Presentations'),
            'type': 'ir.actions.act_window',
            'res_model': 'project.presentation',
            'view_mode': 'list,form',
            'domain': [('project_id', '=', self.id)],
            'context': {'default_project_id': self.id},
        }

    def action_view_team(self):
        """Open team members (students) of this project."""
        self.ensure_one()
        return {
            'name': _('Project Team'),
            'type': 'ir.actions.act_window',
            'res_model': 'student.student',
            'view_mode': 'list,form',
            'domain': [('id', 'in', self.student_ids.ids)],
            'context': {},
        }

