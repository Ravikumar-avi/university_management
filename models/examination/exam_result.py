# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class ExaminationResult(models.Model):
    _name = 'examination.result'
    _description = 'Exam Result Entry'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']
    _order = 'examination_id, student_id'

    active = fields.Boolean(string='Active', default=True)
    name = fields.Char(string='Result Number', compute='_compute_name', store=True)

    # Student
    student_id = fields.Many2one('student.student', string='Student',
                                 required=True, tracking=True, index=True)
    registration_number = fields.Char(related='student_id.registration_number',
                                      string='Registration Number')
    program_id = fields.Many2one(related='student_id.program_id', string='Program', store=True)
    department_id = fields.Many2one(related='student_id.department_id',
                                    string='Department', store=True)

    # Examination
    examination_id = fields.Many2one('examination.examination', string='Examination',
                                     required=True, tracking=True, index=True)
    academic_year_id = fields.Many2one(related='examination_id.academic_year_id',
                                       string='Academic Year', store=True)
    semester_id = fields.Many2one(related='examination_id.semester_id',
                                  string='Semester', store=True)

    # Subject & Course
    course_id = fields.Many2one('university.course', string='Course',
                                required=True, tracking=True)
    subject_id = fields.Many2one(related='course_id.subject_id', string='Subject',
                                 store=True, readonly=True)

    # Marks
    max_marks = fields.Integer(string='Maximum Marks', required=True, default=100)
    passing_marks = fields.Integer(string='Passing Marks', required=True, default=40)

    internal_marks = fields.Integer(string='Internal Marks', default=0)
    internal_max = fields.Integer(string='Internal Max', default=30)

    external_marks = fields.Integer(string='External Marks', default=0)
    external_max = fields.Integer(string='External Max', default=70)

    total_marks = fields.Integer(string='Total Marks Obtained',
                                 compute='_compute_total_marks', store=True)

    percentage = fields.Float(string='Percentage', compute='_compute_percentage', store=True)

    # Grade
    grade_id = fields.Many2one('examination.grade.system', string='Grade',
                               compute='_compute_grade', store=True)
    grade_letter = fields.Char(related='grade_id.grade', string='Grade Letter', store=True)
    grade_point = fields.Float(related='grade_id.grade_point', string='Grade Point', store=True)

    # Result
    is_pass = fields.Boolean(string='Pass', compute='_compute_result', store=True)
    result = fields.Selection([
        ('pass', 'Pass'),
        ('fail', 'Fail'),
        ('absent', 'Absent'),
        ('withheld', 'Result Withheld'),
    ], string='Result', compute='_compute_result', store=True, tracking=True)

    # Absence
    is_absent = fields.Boolean(string='Absent', default=False, tracking=True)

    # Evaluation
    evaluated_by = fields.Many2one('faculty.faculty', string='Evaluated By')
    evaluation_date = fields.Date(string='Evaluation Date')

    # Verification
    verified_by = fields.Many2one('res.users', string='Verified By', readonly=True)
    verification_date = fields.Date(string='Verification Date', readonly=True)

    # Status
    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('verified', 'Verified'),
        ('published', 'Published'),
    ], string='Status', default='draft', tracking=True, index=True)

    # Revaluation
    revaluation_requested = fields.Boolean(string='Revaluation Requested')
    revaluation_id = fields.Many2one('examination.revaluation', string='Revaluation')

    # Remarks
    remarks = fields.Text(string='Remarks')

    _sql_constraints = [
        ('unique_result', 'unique(student_id, examination_id, course_id)',
         'Result already exists for this student, examination and course!'),
    ]

    @api.depends('student_id', 'examination_id', 'subject_id')
    def _compute_name(self):
        for record in self:
            record.name = f"{record.student_id.registration_number} - {record.subject_id.name if record.subject_id else ''}"

    @api.depends('internal_marks', 'external_marks')
    def _compute_total_marks(self):
        for record in self:
            record.total_marks = record.internal_marks + record.external_marks

    @api.depends('total_marks', 'max_marks')
    def _compute_percentage(self):
        for record in self:
            if record.max_marks > 0:
                record.percentage = (record.total_marks / record.max_marks) * 100
            else:
                record.percentage = 0.0

    @api.depends('percentage')
    def _compute_grade(self):
        for record in self:
            if not record.is_absent:
                grade = self.env['examination.grade.system'].search([
                    ('min_percentage', '<=', record.percentage),
                    ('max_percentage', '>=', record.percentage)
                ], limit=1)
                record.grade_id = grade.id if grade else False
            else:
                record.grade_id = False

    @api.depends('total_marks', 'passing_marks', 'is_absent', 'internal_marks', 'external_marks')
    def _compute_result(self):
        for record in self:
            if record.is_absent:
                record.result = 'absent'
                record.is_pass = False
            elif record.total_marks >= record.passing_marks:
                # Check if passed in both internal and external
                internal_pass = record.internal_marks >= (record.internal_max * 0.4)
                external_pass = record.external_marks >= (record.external_max * 0.4)

                if internal_pass and external_pass:
                    record.result = 'pass'
                    record.is_pass = True
                else:
                    record.result = 'fail'
                    record.is_pass = False
            else:
                record.result = 'fail'
                record.is_pass = False

    @api.constrains('internal_marks', 'internal_max')
    def _check_internal_marks(self):
        for record in self:
            if record.internal_marks > record.internal_max:
                raise ValidationError(_('Internal marks cannot exceed maximum internal marks!'))

    @api.constrains('external_marks', 'external_max')
    def _check_external_marks(self):
        for record in self:
            if record.external_marks > record.external_max:
                raise ValidationError(_('External marks cannot exceed maximum external marks!'))

    def action_submit(self):
        self.write({'state': 'submitted'})

    def action_verify(self):
        self.write({
            'state': 'verified',
            'verified_by': self.env.user.id,
            'verification_date': fields.Date.today()
        })

    def action_publish(self):
        self.write({'state': 'published'})
        self._send_result_notification()

    def _send_result_notification(self):
        """Send result notification to student"""
        template = self.env.ref('university_management.email_template_result_notification',
                                raise_if_not_found=False)
        if template:
            template.send_mail(self.id, force_send=True)
