# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
import base64
import io
import logging

_logger = logging.getLogger(__name__)


class TheoryQuestionBank(models.Model):
    """
    Theory / Descriptive Question Bank.
    Faculty upload questions organised by subject, unit, CO and RBT level.
    The system can then auto-generate question papers from these banks.
    """
    _name = 'exam.theory.question.bank'
    _description = 'Theory / Descriptive Question Bank'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name'

    name = fields.Char(string='Bank Name', required=True, tracking=True)
    code = fields.Char(
        string='Bank Code', required=True, copy=False,
        default=lambda self: self.env['ir.sequence'].next_by_code('exam.theory.question.bank') or 'NEW',
    )
    active = fields.Boolean(default=True)
    description = fields.Text(string='Description')

    # Academic linkage
    subject_id = fields.Many2one('university.subject', string='Subject',
                                 required=True, index=True, tracking=True)
    department_id = fields.Many2one('university.department', string='Department',
                                   index=True, tracking=True)
    program_id = fields.Many2one('university.program', string='Program')
    semester_id = fields.Many2one('university.semester', string='Semester')
    regulation = fields.Char(string='Regulation', help='e.g. R20, R22')

    # Faculty who created / owns the bank
    faculty_id = fields.Many2one('faculty.faculty', string='Created By (Faculty)',
                                 tracking=True)

    # Questions
    question_ids = fields.One2many('exam.theory.question', 'bank_id',
                                   string='Questions')
    question_count = fields.Integer(compute='_compute_question_count',
                                    string='Total Questions', store=True)

    # Upload helper
    import_file = fields.Binary(string='Import Questions (.docx / .csv)',
                                attachment=False)
    import_filename = fields.Char(string='Import Filename')

    # Status
    state = fields.Selection([
        ('draft', 'Draft'),
        ('review', 'Under Review'),
        ('approved', 'Approved'),
    ], string='Status', default='draft', tracking=True)

    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)

    _sql_constraints = [
        ('code_unique', 'unique(code)',
         'Question Bank Code must be unique!'),
    ]

    @api.depends('question_ids')
    def _compute_question_count(self):
        for rec in self:
            rec.question_count = len(rec.question_ids)

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------
    def action_submit_review(self):
        self.write({'state': 'review'})

    def action_approve(self):
        self.write({'state': 'approved'})

    def action_reset_draft(self):
        self.write({'state': 'draft'})

    def action_view_questions(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Questions'),
            'res_model': 'exam.theory.question',
            'view_mode': 'list,form',
            'domain': [('bank_id', '=', self.id)],
            'context': {'default_bank_id': self.id},
        }


class TheoryQuestion(models.Model):
    """Individual theory / descriptive question inside a question bank."""
    _name = 'exam.theory.question'
    _description = 'Theory / Descriptive Question'
    _order = 'unit, sequence, id'

    bank_id = fields.Many2one('exam.theory.question.bank', string='Question Bank',
                              required=True, ondelete='cascade', index=True)

    sequence = fields.Integer(string='Sequence', default=10)
    question_number = fields.Char(string='Q. No')
    sub_part = fields.Char(string='Sub Part', help='e.g. A, B, C …')

    question_text = fields.Text(string='Question', required=True)
    question_image = fields.Binary(string='Question Image')

    # Classification
    unit = fields.Char(string='Unit', help='e.g. UNIT-1, UNIT-2')
    marks = fields.Integer(string='Marks', required=True, default=7)
    co_level = fields.Char(string='CO Level', help='e.g. CO1, CO2')

    rbt_level = fields.Selection([
        ('remembering', 'Remembering'),
        ('understanding', 'Understanding'),
        ('applying', 'Applying'),
        ('analyzing', 'Analyzing'),
        ('evaluating', 'Evaluating'),
        ('creating', 'Creating'),
    ], string='RBT Level', default='understanding')

    difficulty = fields.Selection([
        ('easy', 'Easy'),
        ('medium', 'Medium'),
        ('hard', 'Hard'),
    ], string='Difficulty', default='medium')

    # Subject (inherited from bank for convenience filtering)
    subject_id = fields.Many2one(related='bank_id.subject_id', store=True,
                                 string='Subject')

    # Whether this question has been used before
    used_count = fields.Integer(string='Times Used', default=0)

    # Expected answer / solution (for evaluator reference)
    model_answer = fields.Html(string='Model Answer / Key Points')

    @api.constrains('marks')
    def _check_marks(self):
        for rec in self:
            if rec.marks <= 0:
                raise ValidationError(_('Marks must be greater than zero.'))