# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import random
import logging

_logger = logging.getLogger(__name__)


class QuestionPaper(models.Model):
    """
    Auto-generated question paper from one or more theory question banks.
    The system picks questions according to the configured rules
    (unit coverage, marks distribution, RBT mix, etc.).
    """
    _name = 'exam.question.paper'
    _description = 'Question Paper'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char(string='Paper Title', required=True, tracking=True)
    code = fields.Char(
        string='Paper Code', required=True, copy=False,
        default=lambda self: self.env['ir.sequence'].next_by_code('exam.question.paper') or 'NEW',
    )

    # Linkage
    examination_id = fields.Many2one('examination.examination', string='Examination',
                                     tracking=True)
    subject_id = fields.Many2one('university.subject', string='Subject',
                                 required=True, tracking=True, index=True)
    department_id = fields.Many2one('university.department', string='Department')
    semester_id = fields.Many2one('university.semester', string='Semester')
    regulation = fields.Char(string='Regulation')

    # Source banks
    bank_ids = fields.Many2many('exam.theory.question.bank',
                                'question_paper_bank_rel',
                                'paper_id', 'bank_id',
                                string='Source Question Banks')

    # Paper configuration
    total_marks = fields.Integer(string='Total Marks', required=True, default=70)
    duration_minutes = fields.Integer(string='Duration (minutes)', default=180)
    number_of_questions = fields.Integer(string='Number of Questions', default=10)

    paper_pattern = fields.Selection([
        ('r20', 'R20 - Part A (Objective) + Part B (Descriptive)'),
        ('r22', 'R22 - 10 Questions (Either/Or)'),
        ('custom', 'Custom Pattern'),
    ], string='Paper Pattern', default='r22', required=True)

    # Part-A config (R20 style)
    part_a_questions = fields.Integer(string='Part-A Questions', default=10,
                                      help='Short-answer / objective questions')
    part_a_marks_each = fields.Integer(string='Part-A Marks Each', default=2)
    # Part-B config
    part_b_questions = fields.Integer(string='Part-B Questions', default=5,
                                      help='Long-answer descriptive questions')
    part_b_marks_each = fields.Integer(string='Part-B Marks Each', default=10)

    # Generated questions
    paper_question_ids = fields.One2many('exam.question.paper.line', 'paper_id',
                                        string='Paper Questions')

    # PDF output
    paper_pdf = fields.Binary(string='Question Paper PDF', attachment=True)
    paper_pdf_filename = fields.Char(string='PDF Filename')

    # Status
    state = fields.Selection([
        ('draft', 'Draft'),
        ('generated', 'Generated'),
        ('approved', 'Approved'),
        ('locked', 'Locked / Printed'),
    ], string='Status', default='draft', tracking=True)

    instructions = fields.Html(string='Instructions to Candidates')

    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)

    _sql_constraints = [
        ('code_unique', 'unique(code)', 'Paper Code must be unique!'),
    ]

    # ------------------------------------------------------------------
    # Auto-generation logic
    # ------------------------------------------------------------------
    def action_generate_paper(self):
        """
        Auto-pick questions from linked banks based on pattern,
        ensuring unit coverage and marks distribution.
        """
        self.ensure_one()
        if not self.bank_ids:
            raise ValidationError(_('Please select at least one source question bank.'))

        all_questions = self.env['exam.theory.question'].search([
            ('bank_id', 'in', self.bank_ids.ids),
        ])
        if not all_questions:
            raise ValidationError(_('No questions found in the selected banks.'))

        # Clear existing lines
        self.paper_question_ids.unlink()

        lines = []
        if self.paper_pattern == 'r22':
            lines = self._generate_r22(all_questions)
        elif self.paper_pattern == 'r20':
            lines = self._generate_r20(all_questions)
        else:
            lines = self._generate_custom(all_questions)

        for seq, line_vals in enumerate(lines, 1):
            line_vals.update({
                'paper_id': self.id,
                'sequence': seq,
            })
            self.env['exam.question.paper.line'].create(line_vals)

        # Increment usage count
        used_q_ids = [l['question_id'] for l in lines if l.get('question_id')]
        self.env['exam.theory.question'].browse(used_q_ids).write(
            {'used_count': fields.Integer.add(1)}  # handled below
        )
        for q in self.env['exam.theory.question'].browse(used_q_ids):
            q.used_count += 1

        self.state = 'generated'

    def _generate_r22(self, questions):
        """R22 pattern: 5 units × 2 questions each = 10 questions (either/or)."""
        units = list(set(questions.mapped('unit')))
        units = [u for u in units if u]  # filter empty
        units.sort()

        lines = []
        q_no = 1
        for unit in units[:5]:
            unit_qs = questions.filtered(lambda q: q.unit == unit)
            if len(unit_qs) < 2:
                picked = list(unit_qs)
                while len(picked) < 2:
                    picked.append(picked[0] if picked else unit_qs[0])
            else:
                picked = random.sample(list(unit_qs), 2)

            # Question pair (either/or)
            lines.append({
                'question_number': str(q_no),
                'sub_part': 'A',
                'question_id': picked[0].id,
                'marks': picked[0].marks,
                'part': 'main',
            })
            lines.append({
                'question_number': str(q_no),
                'sub_part': 'B (OR)',
                'question_id': picked[1].id,
                'marks': picked[1].marks,
                'part': 'main',
            })
            q_no += 1

        return lines

    def _generate_r20(self, questions):
        """R20 pattern: Part-A short + Part-B long descriptive."""
        lines = []
        short_qs = questions.filtered(lambda q: q.marks <= self.part_a_marks_each)
        long_qs = questions.filtered(lambda q: q.marks > self.part_a_marks_each)

        # Part-A
        if short_qs:
            picked_a = random.sample(list(short_qs), min(self.part_a_questions, len(short_qs)))
        else:
            picked_a = random.sample(list(questions), min(self.part_a_questions, len(questions)))

        for i, q in enumerate(picked_a, 1):
            lines.append({
                'question_number': str(i),
                'sub_part': '',
                'question_id': q.id,
                'marks': self.part_a_marks_each,
                'part': 'part_a',
            })

        # Part-B
        if long_qs:
            picked_b = random.sample(list(long_qs), min(self.part_b_questions * 2, len(long_qs)))
        else:
            picked_b = random.sample(list(questions), min(self.part_b_questions * 2, len(questions)))

        q_no = 1
        for i in range(0, len(picked_b), 2):
            lines.append({
                'question_number': str(q_no),
                'sub_part': 'A',
                'question_id': picked_b[i].id,
                'marks': self.part_b_marks_each,
                'part': 'part_b',
            })
            if i + 1 < len(picked_b):
                lines.append({
                    'question_number': str(q_no),
                    'sub_part': 'B (OR)',
                    'question_id': picked_b[i + 1].id,
                    'marks': self.part_b_marks_each,
                    'part': 'part_b',
                })
            q_no += 1

        return lines

    def _generate_custom(self, questions):
        """Custom: just pick N random questions up to total marks."""
        picked = random.sample(list(questions),
                               min(self.number_of_questions, len(questions)))
        lines = []
        for i, q in enumerate(picked, 1):
            lines.append({
                'question_number': str(i),
                'sub_part': '',
                'question_id': q.id,
                'marks': q.marks,
                'part': 'main',
            })
        return lines

    def action_approve(self):
        self.write({'state': 'approved'})

    def action_lock(self):
        self.write({'state': 'locked'})

    def action_reset_draft(self):
        self.write({'state': 'draft'})


class QuestionPaperLine(models.Model):
    _name = 'exam.question.paper.line'
    _description = 'Question Paper Line'
    _order = 'part, sequence'

    paper_id = fields.Many2one('exam.question.paper', ondelete='cascade',
                               required=True, index=True)
    sequence = fields.Integer(default=10)

    question_number = fields.Char(string='Q.No')
    sub_part = fields.Char(string='Sub Part')

    question_id = fields.Many2one('exam.theory.question', string='Question')
    question_text = fields.Text(related='question_id.question_text',
                                string='Question Text')

    marks = fields.Integer(string='Marks')
    co_level = fields.Char(related='question_id.co_level', string='CO')
    rbt_level = fields.Selection(related='question_id.rbt_level', string='RBT')
    unit = fields.Char(related='question_id.unit', string='Unit')

    part = fields.Selection([
        ('part_a', 'Part A'),
        ('part_b', 'Part B'),
        ('main', 'Main'),
    ], string='Part', default='main')