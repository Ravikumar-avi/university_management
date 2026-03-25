# -*- coding: utf-8 -*-

from odoo import models, fields


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    # ── Fix 1: Missing field from Project module ──────────────────────────
    internal_project_id = fields.Many2one(
        'project.project',
        string='Internal Project',
        help='Project used for internal tasks.',
        config_parameter='project.default_project_id',
    )

    # ── Fix 2: Missing field from project_timesheet_holidays module ───────
    leave_timesheet_task_id = fields.Many2one(
        'project.task',
        string='Leave Timesheet Task',
        help='Task used to record timesheets for employee leaves.',
        config_parameter='project_timesheet_holidays.leave_timesheet_task_id',
    )

    # ── Fix 3: Add missing Jitsi field ────────────────────────────────────
    jitsi_server_domain = fields.Char(
        string='Jitsi Server Domain',
        help="Jitsi server domain (e.g., meet.jit.si)",
        config_parameter='jitsi.server_domain',
    )