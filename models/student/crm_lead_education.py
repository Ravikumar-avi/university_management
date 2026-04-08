# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class CrmLeadEducation(models.Model):
    """
    Extends crm.lead with education-specific fields for Sir MV Institutions.

    Why _inherit and not a new model:
    - crm.lead already has: partner_name, email_from, mobile, phone,
      user_id (counsellor), team_id (admission team), stage_id (pipeline),
      priority (hot/warm/cold), source_id (UTM), campaign_id, tag_ids,
      activity scheduling, calendar integration, built-in reporting,
      website form integration, and email alias support.

    All of the above come for FREE. We only add the 20 education-specific
    fields that crm.lead doesn't know about.

    Field mapping — CRM standard → Education meaning:
        name            → Enquiry title (auto: "Program - Applicant Name")
        partner_name    → Applicant full name
        email_from      → Applicant email
        mobile          → Applicant mobile
        user_id         → Assigned counsellor
        team_id         → Admission team
        stage_id        → Pipeline stage (seeded in data file)
        priority        → 0=Normal, 1=Hot, 2=Very Hot
        expected_revenue→ Estimated fee / token amount
        date_deadline   → Seat / follow-up deadline
        source_id       → Lead source (UTM: website, fair, referral…)
        campaign_id     → Marketing campaign
        description     → Counsellor notes (existing field, relabelled in view)
        probability     → Conversion probability (AI-assisted in Odoo 18)
    """
    _inherit = 'crm.lead'

    # ── Education-specific fields ────────────────────────────────────

    # Program interest
    edu_program_id = fields.Many2one(
        'university.program',
        string='Program of Interest',
        tracking=True,
        index=True,
        help='Primary program the applicant is interested in.',
    )
    edu_department_id = fields.Many2one(
        related='edu_program_id.department_id',
        string='Department',
        store=True,
    )
    edu_alternate_program_id = fields.Many2one(
        'university.program',
        string='Alternate Program',
        help='Second-choice program if the primary program is full.',
    )
    edu_academic_year_id = fields.Many2one(
        'university.academic.year',
        string='Target Academic Year',
        tracking=True,
        help='The academic year the applicant is targeting for admission.',
    )

    # Personal details (partner_name/email_from/mobile already on crm.lead)
    edu_date_of_birth = fields.Date(string='Date of Birth')
    edu_gender = fields.Selection([
        ('male', 'Male'),
        ('female', 'Female'),
        ('other', 'Other'),
    ], string='Gender')
    edu_city = fields.Char(string='City / Town')
    edu_state_id = fields.Many2one(
        'res.country.state',
        string='State',
        domain="[('country_id.code', '=', 'IN')]",
    )

    # Academic background
    edu_previous_qualification = fields.Selection([
        ('10th', '10th / SSLC'),
        ('12th', '12th / PUC / HSC'),
        ('diploma', 'Diploma'),
        ('ug', 'Under Graduate'),
        ('pg', 'Post Graduate'),
        ('other', 'Other'),
    ], string='Current Qualification')
    edu_previous_school = fields.Char(
        string='School / College',
        help='Most recent institution attended.',
    )
    edu_previous_percentage = fields.Float(string='Percentage / CGPA')
    edu_previous_year = fields.Integer(string='Year of Passing')

    # Entrance exams
    edu_entrance_exam_taken = fields.Boolean(string='Entrance Exam Taken')
    edu_entrance_exam_name = fields.Char(
        string='Exam Name',
        help='e.g. JEE Main, KCET, COMEDK, NEET',
    )
    edu_entrance_exam_score = fields.Float(string='Score')
    edu_entrance_exam_rank = fields.Integer(string='Rank')
    edu_entrance_exam_percentile = fields.Float(string='Percentile')

    # Counselling session
    edu_counselling_date = fields.Datetime(
        string='Counselling Scheduled On',
        tracking=True,
    )
    edu_counselling_mode = fields.Selection([
        ('in_person', 'In Person'),
        ('phone', 'Phone'),
        ('video', 'Video Call'),
        ('whatsapp', 'WhatsApp'),
    ], string='Counselling Mode')
    edu_counselling_done_date = fields.Date(
        string='Counselling Done On',
        readonly=True,
    )

    # Referral
    edu_referral_name = fields.Char(
        string='Referred By',
        help='Name of the student or person who referred this enquiry.',
    )

    # Linked records (created on conversion)
    edu_seat_blocking_id = fields.Many2one(
        'student.seat.blocking',
        string='Seat Blocking',
        readonly=True,
        help='Created when this lead is converted to a seat blocking.',
    )
    edu_admission_id = fields.Many2one(
        'student.admission',
        string='Admission Application',
        readonly=True,
        help='Created when this lead is converted to a full admission.',
    )

    # Sessions
    edu_session_ids = fields.One2many(
        'student.counselling.session',
        'lead_id',
        string='Counselling Sessions',
    )
    edu_session_count = fields.Integer(
        string='Sessions',
        compute='_compute_edu_session_count',
        store=True,
    )
    edu_completed_session_count = fields.Integer(
        string='Completed Sessions',
        compute='_compute_edu_session_count',
        store=True,
    )

    # Computed
    edu_is_converted = fields.Boolean(
        string='Converted',
        compute='_compute_edu_is_converted',
        store=True,
    )

    # ── Computed ──────────────────────────────────────────────────────

    @api.depends('edu_seat_blocking_id', 'edu_admission_id')
    def _compute_edu_is_converted(self):
        for rec in self:
            rec.edu_is_converted = bool(
                rec.edu_seat_blocking_id or rec.edu_admission_id
            )

    @api.depends('edu_session_ids', 'edu_session_ids.state')
    def _compute_edu_session_count(self):
        for rec in self:
            sessions = rec.edu_session_ids
            rec.edu_session_count = len(sessions)
            rec.edu_completed_session_count = len(
                sessions.filtered(lambda s: s.state == 'completed')
            )

    # ── Onchange ──────────────────────────────────────────────────────

    @api.onchange('partner_name', 'edu_program_id')
    def _onchange_edu_set_name(self):
        """Auto-set lead name from program + applicant name."""
        parts = []
        if self.edu_program_id:
            parts.append(self.edu_program_id.name)
        if self.partner_name:
            parts.append(self.partner_name)
        if parts:
            self.name = ' — '.join(parts)

    @api.onchange('edu_previous_percentage', 'edu_program_id', 'edu_entrance_exam_taken')
    def _onchange_edu_probability(self):
        """
        Suggest a probability based on academic profile.
        Counsellor can always override. This is a starting hint, not a rule.
        """
        score = 10  # base
        if self.edu_program_id:
            score += 20
        if self.email_from:
            score += 10
        if self.edu_entrance_exam_taken:
            score += 15
        pct = self.edu_previous_percentage or 0
        if pct >= 85:
            score += 35
        elif pct >= 75:
            score += 25
        elif pct >= 60:
            score += 15
        # Only suggest — don't overwrite if counsellor manually set it
        if not self.probability or self.probability == 0:
            self.probability = min(score, 95)

    @api.onchange('mobile')
    def _onchange_edu_whatsapp(self):
        """phone field on crm.lead — pre-fill from mobile."""
        if self.mobile and not self.phone:
            self.phone = self.mobile

    # ── Business Actions ──────────────────────────────────────────────

    def action_edu_mark_counselled(self):
        """Mark counselling session as completed."""
        self.ensure_one()
        self.write({
            'edu_counselling_done_date': fields.Date.today(),
        })
        self.message_post(
            body=_('Counselling session completed on %s via %s.') % (
                fields.Date.today(),
                dict(self._fields['edu_counselling_mode'].selection).get(
                    self.edu_counselling_mode or '', 'in person'),
            )
        )

    def action_edu_convert_to_seat_blocking(self):
        """
        Convert this CRM lead to a Seat Blocking record.

        Uses all education fields already captured on the lead.
        Marks the lead as won (CRM convention) with stage set to
        the 'Seat Blocked' stage. The CRM opportunity is kept open
        until the full admission is confirmed.
        """
        self.ensure_one()

        if self.edu_seat_blocking_id:
            raise ValidationError(_(
                'A seat blocking (%s) already exists for this lead.'
            ) % self.edu_seat_blocking_id.name)
        if not self.edu_program_id:
            raise ValidationError(_(
                'Please select a Program of Interest before blocking a seat.'
            ))
        if not self.edu_academic_year_id:
            raise ValidationError(_(
                'Please select a Target Academic Year before blocking a seat.'
            ))

        notes_parts = []
        if self.source_id:
            notes_parts.append(f'Lead Source: {self.source_id.name}')
        if self.edu_referral_name:
            notes_parts.append(f'Referred By: {self.edu_referral_name}')
        if self.description:
            notes_parts.append(f'Counsellor Notes: {self.description}')
        if self.campaign_id:
            notes_parts.append(f'Campaign: {self.campaign_id.name}')

        from datetime import timedelta
        blocking_vals = {
            'applicant_name': self.partner_name or '',
            'email': self.email_from or '',
            'mobile': self.mobile or self.phone or '',
            'date_of_birth': self.edu_date_of_birth,
            'gender': self.edu_gender,
            'program_id': self.edu_program_id.id,
            'academic_year_id': self.edu_academic_year_id.id,
            'counsellor_id': self.user_id.id if self.user_id else False,
            'counsellor_notes': '\n'.join(notes_parts),
            'entrance_exam_name': self.edu_entrance_exam_name,
            'entrance_exam_score': self.edu_entrance_exam_score,
            'blocking_date': fields.Date.today(),
            'seat_expiry_date': fields.Date.today() + timedelta(days=30),
            'token_amount': self.expected_revenue or 1.0,
        }

        blocking = self.env['student.seat.blocking'].create(blocking_vals)

        # Move CRM lead to 'Seat Blocked' stage
        seat_blocked_stage = self.env['crm.stage'].search([
            ('name', 'ilike', 'seat blocked'),
        ], limit=1)

        write_vals = {'edu_seat_blocking_id': blocking.id}
        if seat_blocked_stage:
            write_vals['stage_id'] = seat_blocked_stage.id

        self.write(write_vals)
        self.message_post(
            body=_(
                'Lead converted to seat blocking <b>%s</b> for %s in %s.'
            ) % (blocking.name, self.edu_program_id.name,
                 self.edu_academic_year_id.name)
        )

        return {
            'type': 'ir.actions.act_window',
            'name': _('Seat Blocking'),
            'res_model': 'student.seat.blocking',
            'res_id': blocking.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_edu_convert_to_admission(self):
        """
        Convert this CRM lead directly to a student.admission application.

        Used for walk-in students who skip seat blocking and apply immediately.
        Marks the CRM lead as Won.
        """
        self.ensure_one()

        if self.edu_admission_id:
            raise ValidationError(_(
                'An admission application (%s) already exists for this lead.'
            ) % self.edu_admission_id.name)
        if not self.edu_program_id:
            raise ValidationError(_(
                'Please select a Program of Interest before creating an admission.'
            ))
        if not self.edu_academic_year_id:
            raise ValidationError(_(
                'Please select a Target Academic Year before creating an admission.'
            ))

        notes_parts = []
        if self.source_id:
            notes_parts.append(f'Lead Source: {self.source_id.name}')
        if self.edu_referral_name:
            notes_parts.append(f'Referred By: {self.edu_referral_name}')
        if self.description:
            notes_parts.append(f'Counsellor Notes: {self.description}')
        if self.campaign_id:
            notes_parts.append(f'Campaign: {self.campaign_id.name}')
        if self.team_id:
            notes_parts.append(f'Admission Team: {self.team_id.name}')

        admission_vals = {
            'applicant_name': self.partner_name or '',
            'email': self.email_from or f'{self.mobile}@noemail.com',
            'mobile': self.mobile or self.phone or '',
            'date_of_birth': self.edu_date_of_birth or fields.Date.today(),
            'gender': self.edu_gender or 'male',
            'program_id': self.edu_program_id.id,
            'academic_year_id': self.edu_academic_year_id.id,
            'admission_category': 'general',
            'previous_qualification': self.edu_previous_school or '',
            'previous_school': self.edu_previous_school or '',
            'previous_board': '',
            'previous_percentage': self.edu_previous_percentage or 0.0,
            'previous_year': self.edu_previous_year or fields.Date.today().year,
            'entrance_exam_taken': self.edu_entrance_exam_taken,
            'entrance_exam_name': self.edu_entrance_exam_name,
            'entrance_exam_score': self.edu_entrance_exam_score,
            'entrance_exam_percentile': self.edu_entrance_exam_percentile,
            'entrance_exam_rank': self.edu_entrance_exam_rank,
            'current_address': self.edu_city or '',
            'permanent_address': self.edu_city or '',
            'father_name': '',
            'mother_name': '',
            'state_id': self.edu_state_id.id if self.edu_state_id else False,
            'internal_notes': '\n'.join(notes_parts),
            'state': 'draft',
        }

        admission = self.env['student.admission'].create(admission_vals)

        # Mark CRM lead as Won
        won_stage = self.env['crm.stage'].search([
            ('name', 'ilike', 'won'),
        ], limit=1)
        write_vals = {
            'edu_admission_id': admission.id,
            'probability': 100,
        }
        if won_stage:
            write_vals['stage_id'] = won_stage.id

        self.write(write_vals)
        self.action_set_won()  # CRM standard won action

        self.message_post(
            body=_(
                'Lead converted to admission application <b>%s</b>.'
            ) % admission.name
        )

        return {
            'type': 'ir.actions.act_window',
            'name': _('Admission Application'),
            'res_model': 'student.admission',
            'res_id': admission.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_edu_view_seat_blocking(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Seat Blocking'),
            'res_model': 'student.seat.blocking',
            'res_id': self.edu_seat_blocking_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_edu_view_admission(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Admission Application'),
            'res_model': 'student.admission',
            'res_id': self.edu_admission_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_edu_view_sessions(self):
        """Open all counselling sessions for this lead."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Counselling Sessions — %s') % (
                self.partner_name or self.name),
            'res_model': 'student.counselling.session',
            'view_mode': 'list,form,calendar',
            'domain': [('lead_id', '=', self.id)],
            'context': {
                'default_lead_id': self.id,
                'default_counsellor_id': self.user_id.id,
                'default_program_discussed_id': self.edu_program_id.id
                    if self.edu_program_id else False,
            },
        }

    def action_edu_new_session(self):
        """Open a new counselling session form pre-linked to this lead."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('New Counselling Session'),
            'res_model': 'student.counselling.session',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_lead_id': self.id,
                'default_counsellor_id': self.user_id.id,
                'default_program_discussed_id': self.edu_program_id.id
                    if self.edu_program_id else False,
                'default_qualification_discussed':
                    self.edu_previous_qualification,
                'default_percentage_discussed':
                    self.edu_previous_percentage,
                'default_entrance_exam_name':
                    self.edu_entrance_exam_name,
                'default_entrance_exam_score':
                    self.edu_entrance_exam_score,
            },
        }