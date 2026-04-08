# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class StudentCounsellingSession(models.Model):
    """
    Counselling Session — one record per session between counsellor and prospect.

    Linked to crm.lead (Many2one) so one lead can have many sessions.
    This solves the key gap: crm.lead only has ONE counselling date,
    but in reality a student may visit 2-4 times before deciding.

    Each session captures:
      - Who counselled, when, how long, what mode
      - Which program was discussed and seats checked
      - Eligibility decision made in that session
      - Academic profile as discussed (may differ from lead's stored values)
      - Outcome + next action + follow-up date

    The crm.lead keeps the big-picture pipeline view.
    The sessions give the complete audit trail per applicant.

    State machine:  scheduled  →  completed
                        ↓
                    cancelled
    """
    _name = 'student.counselling.session'
    _description = 'Counselling Session'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'session_date desc, id desc'
    _rec_name = 'display_name'

    # ── Identity ─────────────────────────────────────────────────────
    display_name = fields.Char(
        string='Session',
        compute='_compute_display_name',
        store=True,
    )

    # ── Parent Lead ───────────────────────────────────────────────────
    lead_id = fields.Many2one(
        'crm.lead',
        string='Enquiry / Lead',
        required=True,
        ondelete='cascade',
        index=True,
        tracking=True,
    )

    # Pulled from lead for convenience (read-only, for reporting)
    applicant_name = fields.Char(
        related='lead_id.partner_name',
        string='Applicant',
        store=True,
    )
    lead_program_id = fields.Many2one(
        related='lead_id.edu_program_id',
        string='Lead Program',
        store=True,
    )
    lead_stage_id = fields.Many2one(
        related='lead_id.stage_id',
        string='Lead Stage',
        store=True,
    )

    # ── Session Details ───────────────────────────────────────────────
    session_number = fields.Integer(
        string='Session #',
        compute='_compute_session_number',
        store=True,
        help='Sequential number of this session for this lead.',
    )
    counsellor_id = fields.Many2one(
        'res.users',
        string='Counsellor',
        required=True,
        default=lambda self: self.env.user,
        tracking=True,
        index=True,
    )
    session_date = fields.Datetime(
        string='Session Date & Time',
        required=True,
        default=fields.Datetime.now,
        tracking=True,
    )
    duration = fields.Float(
        string='Duration (hrs)',
        default=0.5,
        help='Duration of the session in hours. e.g. 0.5 = 30 minutes.',
    )
    session_mode = fields.Selection([
        ('in_person', 'In Person'),
        ('phone', 'Phone'),
        ('video', 'Video Call'),
        ('whatsapp', 'WhatsApp'),
        ('email', 'Email'),
    ], string='Mode', required=True, default='in_person', tracking=True)

    # ── Program Discussed ─────────────────────────────────────────────
    program_discussed_id = fields.Many2one(
        'university.program',
        string='Program Discussed',
        tracking=True,
        help='Program focused on in this specific session. '
             'May differ from lead\'s primary program if student is reconsidering.',
    )
    alternate_program_discussed_id = fields.Many2one(
        'university.program',
        string='Alternate Program Discussed',
    )
    seats_available_snapshot = fields.Integer(
        string='Seats Available (at session)',
        help='Live seat count in the discussed program at the time of this session. '
             'Captured automatically when program is selected.',
        readonly=True,
    )

    # ── Eligibility Assessment ────────────────────────────────────────
    eligibility_status = fields.Selection([
        ('pending', 'Pending Assessment'),
        ('eligible', 'Eligible'),
        ('conditional', 'Conditionally Eligible'),
        ('not_eligible', 'Not Eligible'),
    ], string='Eligibility', default='pending', tracking=True)
    eligibility_notes = fields.Text(
        string='Eligibility Notes',
        help='Reason for eligibility decision, conditions if conditional, '
             'or alternative suggestion if not eligible.',
    )

    # ── Academic Profile (as discussed in this session) ───────────────
    qualification_discussed = fields.Selection([
        ('10th', '10th / SSLC'),
        ('12th', '12th / PUC / HSC'),
        ('diploma', 'Diploma'),
        ('ug', 'Under Graduate'),
        ('pg', 'Post Graduate'),
        ('other', 'Other'),
    ], string='Qualification')
    percentage_discussed = fields.Float(string='Percentage / CGPA')
    entrance_exam_name = fields.Char(string='Entrance Exam')
    entrance_exam_score = fields.Float(string='Score')
    entrance_exam_rank = fields.Integer(string='Rank')

    # ── Fee Discussion ────────────────────────────────────────────────
    fee_discussed = fields.Boolean(
        string='Fee Structure Discussed',
        default=False,
    )
    fee_concerns = fields.Text(
        string='Fee Concerns / Notes',
        help='Any concerns raised by the student or parent about fee structure, '
             'scholarship eligibility, or payment mode.',
        invisible=True,
    )
    scholarship_discussed = fields.Boolean(
        string='Scholarship Discussed',
        default=False,
    )

    # ── Session Notes ─────────────────────────────────────────────────
    discussion_notes = fields.Text(
        string='Discussion Notes',
        help='What was discussed in detail — program features, career scope, '
             'hostel/transport, placement record, etc.',
    )

    # ── Outcome ───────────────────────────────────────────────────────
    outcome = fields.Selection([
        ('interested', 'Interested — Will Proceed'),
        ('needs_follow_up', 'Needs Follow-up'),
        ('considering', 'Still Considering'),
        ('seat_blocked', 'Seat Blocked in This Session'),
        ('applied', 'Applied in This Session'),
        ('not_interested', 'Not Interested'),
        ('chose_competitor', 'Chose Another College'),
    ], string='Session Outcome', tracking=True)

    next_action = fields.Text(
        string='Next Action',
        help='What the counsellor will do next — e.g. '
             '"Send fee structure PDF", "Call after entrance results", '
             '"Schedule parent meeting".',
    )
    follow_up_date = fields.Date(
        string='Follow-up Date',
        tracking=True,
    )

    # ── Calendar Link ─────────────────────────────────────────────────
    calendar_event_id = fields.Many2one(
        'calendar.event',
        string='Calendar Event',
        readonly=True,
        help='Linked calendar entry if session was scheduled via calendar.',
    )

    # ── Status ────────────────────────────────────────────────────────
    state = fields.Selection([
        ('scheduled', 'Scheduled'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('no_show', 'No Show'),
    ], string='Status', default='scheduled', tracking=True, index=True)

    # ── SQL Constraints ───────────────────────────────────────────────
    _sql_constraints = [
        ('duration_positive', 'CHECK(duration > 0)',
         'Session duration must be greater than zero.'),
    ]

    # ── Computed ──────────────────────────────────────────────────────

    @api.depends('lead_id', 'lead_id.partner_name', 'session_number')
    def _compute_display_name(self):
        for rec in self:
            lead_name = rec.lead_id.partner_name or rec.lead_id.name or 'Lead'
            rec.display_name = f'Session {rec.session_number} — {lead_name}'

    @api.depends('lead_id', 'session_date')
    def _compute_session_number(self):
        """
        Sequential number within the same lead, ordered by session_date.
        Session 1 = earliest, Session N = latest.
        """
        for rec in self:
            if not rec.lead_id:
                rec.session_number = 1
                continue
            earlier = self.search([
                ('lead_id', '=', rec.lead_id.id),
                ('session_date', '<=', rec.session_date or fields.Datetime.now()),
                ('id', '!=', rec.id if rec.id else 0),
            ])
            rec.session_number = len(earlier) + 1

    # ── Onchange ──────────────────────────────────────────────────────

    @api.onchange('program_discussed_id')
    def _onchange_program_seats(self):
        """Snapshot seats available when program is selected."""
        if self.program_discussed_id:
            self.seats_available_snapshot = (
                self.program_discussed_id.available_seats
            )

    @api.onchange('lead_id')
    def _onchange_lead_prefill(self):
        """Pre-fill academic fields from the lead when lead is selected."""
        if self.lead_id:
            self.program_discussed_id = self.lead_id.edu_program_id
            self.counsellor_id = self.lead_id.user_id or self.env.user
            self.qualification_discussed = self.lead_id.edu_previous_qualification
            self.percentage_discussed = self.lead_id.edu_previous_percentage
            self.entrance_exam_name = self.lead_id.edu_entrance_exam_name
            self.entrance_exam_score = self.lead_id.edu_entrance_exam_score
            self.entrance_exam_rank = self.lead_id.edu_entrance_exam_rank

    @api.onchange('fee_discussed')
    def _onchange_fee_discussed(self):
        if not self.fee_discussed:
            self.fee_concerns = False

    # ── Constraints ───────────────────────────────────────────────────

    @api.constrains('session_date', 'lead_id')
    def _check_session_date_not_future_for_completion(self):
        """Completed sessions cannot have a future date."""
        for rec in self:
            if (rec.state == 'completed'
                    and rec.session_date
                    and rec.session_date > fields.Datetime.now()):
                raise ValidationError(_(
                    'A completed session cannot have a future date.'
                ))

    # ── Business Actions ──────────────────────────────────────────────

    def action_complete(self):
        """Mark session as completed and update lead counselling info."""
        self.ensure_one()
        if self.state != 'scheduled':
            raise ValidationError(_('Only scheduled sessions can be completed.'))

        self.write({
            'state': 'completed',
        })

        # Update the parent lead's counselling done date
        if self.lead_id:
            update_vals = {
                'edu_counselling_done_date': fields.Date.today(),
            }
            # Update follow-up on lead if this session has a follow-up
            if self.follow_up_date:
                update_vals['date_deadline'] = self.follow_up_date
            # Sync program if discussed program differs
            if self.program_discussed_id:
                update_vals['edu_program_id'] = self.program_discussed_id.id
            self.lead_id.write(update_vals)

            # Move lead stage forward based on outcome
            self._sync_lead_stage_from_outcome()

        self.message_post(
            body=_(
                'Session completed. Outcome: <b>%s</b>. '
                'Duration: %s hr(s). Mode: %s.'
            ) % (
                dict(self._fields['outcome'].selection).get(
                    self.outcome or '', 'Not recorded'),
                self.duration,
                dict(self._fields['session_mode'].selection).get(
                    self.session_mode, ''),
            )
        )

    def action_no_show(self):
        """Mark as no-show — applicant did not attend."""
        self.ensure_one()
        if self.state != 'scheduled':
            raise ValidationError(_('Only scheduled sessions can be marked as no-show.'))
        self.write({'state': 'no_show'})
        self.message_post(body=_('Applicant did not attend the scheduled session.'))

    def action_cancel(self):
        """Cancel this session."""
        self.ensure_one()
        if self.state == 'completed':
            raise ValidationError(_('Completed sessions cannot be cancelled.'))
        self.write({'state': 'cancelled'})
        self.message_post(body=_('Session cancelled.'))

    def action_reschedule(self):
        """Reset to scheduled (for rescheduling after no-show/cancel)."""
        self.ensure_one()
        if self.state not in ('no_show', 'cancelled'):
            raise ValidationError(_(
                'Only no-show or cancelled sessions can be rescheduled.'
            ))
        self.write({'state': 'scheduled'})
        self.message_post(body=_('Session rescheduled.'))

    def action_schedule_calendar_event(self):
        """
        Create a calendar.event for this session and link it.
        Opens the calendar event form pre-populated.
        """
        self.ensure_one()
        if not self.session_date:
            raise ValidationError(_('Please set a session date before creating a calendar event.'))

        from datetime import timedelta
        duration_td = timedelta(hours=self.duration or 0.5)

        event_vals = {
            'name': f'Counselling — {self.lead_id.partner_name or self.lead_id.name}',
            'start': self.session_date,
            'stop': fields.Datetime.to_string(
                fields.Datetime.from_string(
                    fields.Datetime.to_string(self.session_date)
                ) + duration_td
            ),
            'description': f'Lead: {self.lead_id.name}\n'
                           f'Program: {self.program_discussed_id.name if self.program_discussed_id else "-"}',
            'user_id': self.counsellor_id.id,
        }
        event = self.env['calendar.event'].create(event_vals)
        self.write({'calendar_event_id': event.id})

        return {
            'type': 'ir.actions.act_window',
            'name': _('Calendar Event'),
            'res_model': 'calendar.event',
            'res_id': event.id,
            'view_mode': 'form',
            'target': 'new',
        }

    # ── Private Helpers ───────────────────────────────────────────────

    def _sync_lead_stage_from_outcome(self):
        """
        Move the parent CRM lead to the appropriate stage based on session outcome.
        Only moves forward — never moves back.
        """
        self.ensure_one()
        if not self.outcome or not self.lead_id:
            return

        stage_name_map = {
            'interested': 'Interested',
            'needs_follow_up': 'Counselled',
            'considering': 'Counselled',
            'seat_blocked': 'Seat Blocked',
            'applied': 'Admitted',
            'not_interested': None,   # CRM mark as lost
            'chose_competitor': None,  # CRM mark as lost
        }

        target_stage_name = stage_name_map.get(self.outcome)

        if target_stage_name:
            stage = self.env['crm.stage'].search([
                ('name', 'ilike', target_stage_name),
            ], limit=1)
            if stage:
                self.lead_id.write({'stage_id': stage.id})
        elif self.outcome in ('not_interested', 'chose_competitor'):
            # Mark lead as lost in CRM with reason
            self.lead_id.action_set_lost(
                lost_reason_id=False,
            )

    # ── Scheduled Action ──────────────────────────────────────────────

    @api.model
    def _cron_remind_follow_ups(self):
        """
        Daily cron: post chatter reminder on sessions whose
        follow_up_date is today and are completed.
        """
        today = fields.Date.today()
        due = self.search([
            ('follow_up_date', '=', today),
            ('state', '=', 'completed'),
        ])
        for session in due:
            session.lead_id.message_post(
                body=_(
                    'Follow-up due today for session %s with <b>%s</b>. '
                    'Next action: %s'
                ) % (
                    session.session_number,
                    session.applicant_name,
                    session.next_action or 'Not specified',
                )
            )
        return f'{len(due)} follow-up reminder(s) posted.'