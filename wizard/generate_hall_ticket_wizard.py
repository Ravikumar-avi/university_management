# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging
_logger = logging.getLogger(__name__)

class GenerateHallTicketWizard(models.TransientModel):
    """
    Wizard for bulk hall ticket generation
    """
    _name = 'generate.hall.ticket.wizard'
    _description = 'Generate Hall Ticket Wizard'

    examination_id = fields.Many2one('examination.examination', string='Examination', required=True,
                                     domain=[('state', 'in', ['scheduled', 'ongoing'])])
    program_id = fields.Many2one('university.program', string='Program')
    department_id = fields.Many2one('university.department', string='Department')
    batch_id = fields.Many2one('university.batch', string='Batch')
    semester = fields.Selection([
        ('1', 'Semester 1'),
        ('2', 'Semester 2'),
        ('3', 'Semester 3'),
        ('4', 'Semester 4'),
        ('5', 'Semester 5'),
        ('6', 'Semester 6'),
        ('7', 'Semester 7'),
        ('8', 'Semester 8'),
    ], string='Semester', required=True)

    student_ids = fields.Many2many('student.student', string='Students')

    hall_ticket_template_id = fields.Many2one('hall.ticket.template', string='Hall Ticket Template')

    check_eligibility = fields.Boolean(string='Check Eligibility Criteria', default=True)
    min_attendance = fields.Float(string='Minimum Attendance %', default=75.0)
    check_fee_payment = fields.Boolean(string='Check Fee Payment', default=True)
    check_documents = fields.Boolean(string='Check Document Verification', default=False)

    auto_print = fields.Boolean(string='Auto Print After Generation', default=False)
    send_email = fields.Boolean(string='Send Email to Students', default=True)

    preview_lines = fields.One2many('generate.hall.ticket.wizard.line', 'wizard_id',
                                    string='Students Preview', compute='_compute_preview_lines')

    @api.depends('examination_id', 'program_id', 'department_id', 'batch_id', 'semester', 'student_ids')
    def _compute_preview_lines(self):
        """Compute preview of students and their eligibility"""
        for wizard in self:
            students = wizard.student_ids if wizard.student_ids else wizard._get_students()

            lines = []
            for student in students:
                eligible, reason = wizard._check_student_eligibility(student)
                lines.append((0, 0, {
                    'student_id': student.id,
                    'eligible': eligible,
                    'reason': reason
                }))

            wizard.preview_lines = lines

    def _get_students(self):
        """Get students based on filters"""
        domain = [
            ('state', '=', 'enrolled'),
            ('current_semester', '=', self.semester)
        ]

        if self.program_id:
            domain.append(('program_id', '=', self.program_id.id))
        if self.department_id:
            domain.append(('department_id', '=', self.department_id.id))
        if self.batch_id:
            domain.append(('batch_id', '=', self.batch_id.id))

        return self.env['student.student'].search(domain)

    def _check_student_eligibility(self, student):
        """Check if student is eligible for hall ticket"""
        if not self.check_eligibility:
            return True, 'No eligibility check'

        reasons = []

        # Check attendance
        attendance_percentage = self._get_student_attendance(student)
        if attendance_percentage < self.min_attendance:
            return False, f'Low attendance: {attendance_percentage:.1f}%'
        reasons.append(f'Attendance: {attendance_percentage:.1f}%')

        # Check fee payment
        if self.check_fee_payment:
            fee_status = self._check_fee_status(student)
            if not fee_status:
                return False, 'Fee payment pending'
            reasons.append('Fee paid')

        # Check documents
        if self.check_documents:
            docs_verified = self._check_documents(student)
            if not docs_verified:
                return False, 'Documents not verified'
            reasons.append('Documents verified')

        return True, ', '.join(reasons)

    def _get_student_attendance(self, student):
        """Calculate student attendance percentage"""
        Attendance = self.env['student.attendance']

        total = Attendance.search_count([
            ('student_id', '=', student.id),
            ('semester', '=', self.semester)
        ])

        present = Attendance.search_count([
            ('student_id', '=', student.id),
            ('semester', '=', self.semester),
            ('state', '=', 'present')
        ])

        return (present / total * 100) if total > 0 else 0.0

    def _check_fee_status(self, student):
        """Check if student has paid required fees"""
        pending_fees = self.env['fee.payment'].search_count([
            ('student_id', '=', student.id),
            ('semester', '=', self.semester),
            ('state', '=', 'pending'),
            ('due_date', '<', fields.Date.today())
        ])

        return pending_fees == 0

    def _check_documents(self, student):
        """Check if student documents are verified"""
        unverified = self.env['student.document'].search_count([
            ('student_id', '=', student.id),
            ('verification_status', '!=', 'verified'),
            ('is_mandatory', '=', True)
        ])

        return unverified == 0

    def action_generate_hall_tickets(self):
        """Generate hall tickets for eligible students"""
        self.ensure_one()

        # Get eligible students
        eligible_lines = self.preview_lines.filtered(lambda l: l.eligible)

        if not eligible_lines:
            raise UserError(_('No eligible students found for hall ticket generation.'))

        HallTicket = self.env['hall.ticket']
        generated_tickets = self.env['hall.ticket']

        for line in eligible_lines:
            student = line.student_id

            # Check if hall ticket already exists
            existing = HallTicket.search([
                ('student_id', '=', student.id),
                ('examination_id', '=', self.examination_id.id)
            ], limit=1)

            if existing:
                if existing.state == 'cancelled':
                    existing.write({'state': 'generated'})
                    generated_tickets |= existing
                continue

            # Generate hall ticket
            ticket_vals = {
                'student_id': student.id,
                'examination_id': self.examination_id.id,
                'hall_ticket_number': self._generate_hall_ticket_number(student),
                'program_id': student.program_id.id,
                'department_id': student.department_id.id,
                'semester': self.semester,
                'batch_id': student.batch_id.id,
                'issue_date': fields.Date.today(),
                'exam_center': self.examination_id.exam_center if hasattr(self.examination_id, 'exam_center') else '',
                'template_id': self.hall_ticket_template_id.id if self.hall_ticket_template_id else False,
                'state': 'generated'
            }

            ticket = HallTicket.create(ticket_vals)
            generated_tickets |= ticket

            # Update student record
            student.write({'hall_ticket_id': ticket.id})

            # Send email
            if self.send_email and student.email:
                self._send_hall_ticket_email(ticket)

        # Auto print if enabled
        if self.auto_print and generated_tickets:
            return self.env.ref('university_management.action_report_hall_ticket').report_action(generated_tickets)

        # Show result
        return {
            'name': _('Generated Hall Tickets'),
            'type': 'ir.actions.act_window',
            'res_model': 'hall.ticket',
            'view_mode': 'list,form',
            'domain': [('id', 'in', generated_tickets.ids)],
            'target': 'current',
        }

    def _generate_hall_ticket_number(self, student):
        """Generate unique hall ticket number"""
        exam_code = self.examination_id.code if hasattr(self.examination_id, 'code') else 'EX'
        reg_no = student.registration_number or student.id
        return f"HT-{exam_code}-{reg_no}-{fields.Date.today().year}"

    def _send_hall_ticket_email(self, hall_ticket):
        """Send hall ticket via email"""
        try:
            template = self.env.ref('university_management.email_template_hall_ticket',
                                    raise_if_not_found=False)
            if template:
                template.send_mail(hall_ticket.id, force_send=True)
                return True
            return False
        except Exception as e:
            _logger.error(f"Hall ticket email error: {str(e)}")
            return False


class GenerateHallTicketWizardLine(models.TransientModel):
    """Preview lines for hall ticket generation"""
    _name = 'generate.hall.ticket.wizard.line'
    _description = 'Generate Hall Ticket Wizard Line'

    wizard_id = fields.Many2one('generate.hall.ticket.wizard', string='Wizard', ondelete='cascade')
    student_id = fields.Many2one('student.student', string='Student', readonly=True)
    eligible = fields.Boolean(string='Eligible', readonly=True)
    reason = fields.Char(string='Reason/Status', readonly=True)
