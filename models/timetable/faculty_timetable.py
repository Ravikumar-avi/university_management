# -*- coding: utf-8 -*-

from odoo import models, fields, api, tools


class FacultyTimetable(models.Model):
    _name = 'faculty.timetable'
    _description = 'Faculty Timetable View'
    _auto = False  # This is a SQL VIEW

    faculty_id = fields.Many2one('faculty.faculty', string='Faculty', readonly=True)
    day_of_week = fields.Selection([
        ('monday', 'Monday'),
        ('tuesday', 'Tuesday'),
        ('wednesday', 'Wednesday'),
        ('thursday', 'Thursday'),
        ('friday', 'Friday'),
        ('saturday', 'Saturday'),
    ], string='Day', readonly=True)

    start_time = fields.Float(string='Start Time', readonly=True)
    end_time = fields.Float(string='End Time', readonly=True)
    duration = fields.Float(string='Duration', readonly=True)

    subject_id = fields.Many2one('university.subject', string='Subject', readonly=True)
    batch_id = fields.Many2one('university.batch', string='Batch', readonly=True)
    room_number = fields.Char(string='Room', readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW faculty_timetable AS (
                SELECT
                    ROW_NUMBER() OVER() as id,
                    faculty_id,
                    day_of_week,
                    start_time,
                    end_time,
                    (end_time - start_time) as duration,
                    subject_id,
                    batch_id,
                    room_number
                FROM class_timetable
                WHERE active = true
            )
        """)
