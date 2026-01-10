# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import timedelta
import logging

_logger = logging.getLogger(__name__)


class FeeReminder(models.Model):
    _name = 'fee.reminder'
    _description = 'Automatic Fee Reminders to Parents'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'reminder_date desc'

    name = fields.Char(string='Reminder Number', required=True, readonly=True,
                       copy=False, default='/')

    # Student
    student_id = fields.Many2one('student.student', string='Student',
                                 required=True, tracking=True, index=True)
    student_name = fields.Char(related='student_id.name', string='Student Name')
    registration_number = fields.Char(related='student_id.registration_number',
                                      string='Registration Number')

    # Fee Structure
    fee_structure_id = fields.Many2one('fee.structure', string='Fee Structure',
                                       required=True, tracking=True)
    total_fee = fields.Monetary(related='fee_structure_id.total_amount',
                                string='Total Fee', currency_field='currency_id')
    due_date = fields.Date(related='fee_structure_id.due_date', string='Due Date')

    # Reminder Details
    reminder_date = fields.Date(string='Reminder Date', default=fields.Date.today(),
                                required=True, tracking=True)
    reminder_type = fields.Selection([
        ('before_due', 'Before Due Date'),
        ('on_due', 'On Due Date'),
        ('after_due', 'After Due Date - First Reminder'),
        ('second', 'Second Reminder'),
        ('final', 'Final Notice'),
    ], string='Reminder Type', required=True, default='before_due', tracking=True)

    # Days
    days_before_due = fields.Integer(string='Days Before Due')
    days_after_due = fields.Integer(string='Days After Due')

    # Outstanding Amount
    outstanding_amount = fields.Monetary(string='Outstanding Amount',
                                         currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id)

    # Communication
    send_email = fields.Boolean(string='Send Email', default=True)
    send_sms = fields.Boolean(string='Send SMS', default=True)

    email_sent = fields.Boolean(string='Email Sent', readonly=True)
    email_sent_date = fields.Datetime(string='Email Sent Date', readonly=True)

    sms_sent = fields.Boolean(string='SMS Sent', readonly=True)
    sms_sent_date = fields.Datetime(string='SMS Sent Date', readonly=True)

    # Recipients
    parent_ids = fields.Many2many('student.parent', string='Parents',
                                  compute='_compute_parents', store=True)
    recipient_emails = fields.Char(string='Recipient Emails', compute='_compute_recipients')
    recipient_phones = fields.Char(string='Recipient Phones', compute='_compute_recipients')

    # Status
    state = fields.Selection([
        ('draft', 'Draft'),
        ('scheduled', 'Scheduled'),
        ('sent', 'Sent'),
        ('failed', 'Failed'),
    ], string='Status', default='draft', tracking=True)

    # Message Content
    email_subject = fields.Char(string='Email Subject', compute='_compute_message_content')
    email_body = fields.Html(string='Email Body', compute='_compute_message_content')
    sms_body = fields.Text(string='SMS Body', compute='_compute_message_content')

    # Notes
    notes = fields.Text(string='Notes')

    _sql_constraints = [
        ('name_unique', 'unique(name)', 'Reminder Number must be unique!'),
    ]

    @api.model
    def create(self, vals):
        if vals.get('name', '/') == '/':
            vals['name'] = self.env['ir.sequence'].next_by_code('fee.reminder') or '/'
        return super(FeeReminder, self).create(vals)

    @api.depends('student_id')
    def _compute_parents(self):
        for record in self:
            record.parent_ids = record.student_id.parent_ids

    @api.depends('parent_ids')
    def _compute_recipients(self):
        for record in self:
            emails = record.parent_ids.filtered(lambda p: p.email).mapped('email')
            record.recipient_emails = ', '.join(emails) if emails else ''

            phones = record.parent_ids.filtered(lambda p: p.phone).mapped('phone')
            record.recipient_phones = ', '.join(phones) if phones else ''

    @api.depends('student_id', 'fee_structure_id', 'reminder_type', 'outstanding_amount')
    def _compute_message_content(self):
        for record in self:
            # Email Subject
            record.email_subject = f"Fee Payment Reminder - {record.student_id.name}"

            # Email Body
            record.email_body = f"""
                <p>Dear Parent,</p>
                <p>This is a reminder regarding the fee payment for your ward <strong>{record.student_id.name}</strong> 
                (Registration: {record.student_id.registration_number}).</p>

                <p><strong>Fee Details:</strong></p>
                <ul>
                    <li>Total Fee: {record.total_fee} {record.currency_id.symbol}</li>
                    <li>Outstanding Amount: {record.outstanding_amount} {record.currency_id.symbol}</li>
                    <li>Due Date: {record.due_date}</li>
                </ul>

                <p>Please make the payment at the earliest to avoid late fees.</p>

                <p>Best Regards,<br/>
                University Administration</p>
            """

            # SMS Body
            record.sms_body = f"Fee Reminder: {record.student_id.name} has pending fee of Rs.{record.outstanding_amount}. Due: {record.due_date}. Please pay soon. -University"

    def action_schedule(self):
        """Schedule reminder for sending"""
        for record in self:
            if not record.parent_ids:
                raise ValidationError(_(
                    'No parent contact details found for this student. '
                    'Please update parent information before scheduling reminders.'
                ))
            record.write({'state': 'scheduled'})
        return True

    def action_send_reminder(self):
        """Send reminder via email and SMS"""
        for record in self:
            if not record.parent_ids:
                raise ValidationError(_(
                    'No parent contact details found for this student. '
                    'Please update parent information before sending reminders.'
                ))

            success = True

            try:
                if record.send_email:
                    record._send_email_reminder()

                if record.send_sms:
                    record._send_sms_reminder()

                record.write({'state': 'sent'})
            except Exception as e:
                _logger.error(f"Failed to send reminder {record.name}: {str(e)}")
                record.write({'state': 'failed'})
                success = False

        return True

    def action_resend(self):
        """Resend reminder"""
        for record in self:
            record.write({
                'email_sent': False,
                'email_sent_date': False,
                'sms_sent': False,
                'sms_sent_date': False,
                'state': 'scheduled'
            })
            record.action_send_reminder()
        return True

    def _send_email_reminder(self):
        """Send email reminder"""
        template = self.env.ref('university_management.email_template_fee_reminder',
                                raise_if_not_found=False)
        if template:
            template.send_mail(self.id, force_send=True)
            self.write({
                'email_sent': True,
                'email_sent_date': fields.Datetime.now()
            })

    def _send_sms_reminder(self):
        """Send SMS reminder"""
        # Implement SMS sending logic here
        # This would integrate with SMS gateway
        self.write({
            'sms_sent': True,
            'sms_sent_date': fields.Datetime.now()
        })

    @api.model
    def _cron_generate_reminders(self):
        """Scheduled action to generate automatic reminders"""
        today = fields.Date.today()

        # Get all active fee structures
        fee_structures = self.env['fee.structure'].search([('state', '=', 'active')])

        for fee_structure in fee_structures:
            if not fee_structure.due_date:
                continue

            # Get students with this fee structure
            students = self.env['student.student'].search([
                ('program_id', '=', fee_structure.program_id.id),
                ('state', 'in', ['enrolled', 'active'])
            ])

            for student in students:
                # Check if fee is paid
                paid_amount = sum(self.env['fee.payment'].search([
                    ('student_id', '=', student.id),
                    ('fee_structure_id', '=', fee_structure.id),
                    ('state', '=', 'paid')
                ]).mapped('amount'))

                outstanding = fee_structure.total_amount - paid_amount

                if outstanding > 0:
                    # Generate reminders based on due date
                    days_diff = (fee_structure.due_date - today).days

                    # Before due date (7 days before)
                    if days_diff == 7:
                        self._create_reminder(student, fee_structure, 'before_due', outstanding)

                    # On due date
                    elif days_diff == 0:
                        self._create_reminder(student, fee_structure, 'on_due', outstanding)

                    # After due date
                    elif days_diff < 0:
                        days_overdue = abs(days_diff)
                        if days_overdue == 7:
                            self._create_reminder(student, fee_structure, 'after_due', outstanding)
                        elif days_overdue == 14:
                            self._create_reminder(student, fee_structure, 'second', outstanding)
                        elif days_overdue == 30:
                            self._create_reminder(student, fee_structure, 'final', outstanding)

    def _create_reminder(self, student, fee_structure, reminder_type, outstanding):
        """Create and send reminder"""
        existing = self.search([
            ('student_id', '=', student.id),
            ('fee_structure_id', '=', fee_structure.id),
            ('reminder_type', '=', reminder_type),
            ('reminder_date', '=', fields.Date.today())
        ])

        if not existing:
            reminder = self.create({
                'student_id': student.id,
                'fee_structure_id': fee_structure.id,
                'reminder_type': reminder_type,
                'outstanding_amount': outstanding,
                'state': 'scheduled'
            })
            reminder.action_send_reminder()
