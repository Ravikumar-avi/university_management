# -*- coding: utf-8 -*-
from odoo import http, _, fields
from odoo.http import request
from odoo.exceptions import AccessError, MissingError
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager
import base64
import logging

_logger = logging.getLogger(__name__)


class FacultyPortalController(CustomerPortal):
    """Faculty Portal Controller"""

    def _get_faculty(self):
        """Get faculty record for current user"""
        return request.env['faculty.faculty'].search([('user_id', '=', request.env.uid)], limit=1)

    # ==================== FACULTY DASHBOARD ====================
    @http.route(['/my/faculty/dashboard'], type='http', auth="user", website=True)
    def faculty_dashboard(self, **kw):
        """Faculty Dashboard"""
        faculty = self._get_faculty()

        if not faculty:
            return request.redirect('/my')

        # Get today's classes
        today = fields.Date.today()
        today_classes = request.env['university.timetable'].search([
            ('faculty_id', '=', faculty.id),
            ('active', '=', True),
        ])

        # Get attendance summary
        attendance_today = request.env['student.attendance'].search_count([
            ('faculty_id', '=', faculty.id),
            ('date', '=', today)
        ])

        values = {
            'faculty': faculty,
            'today_classes': today_classes,
            'attendance_today': attendance_today,
            'page_name': 'faculty_dashboard',
        }

        return request.render("university_management.faculty_dashboard", values)

    # ==================== MY CLASSES ====================
    @http.route(['/my/faculty/classes'], type='http', auth="user", website=True)
    def faculty_classes(self, **kw):
        """View assigned classes"""
        faculty = self._get_faculty()

        if not faculty:
            return request.redirect('/my')

        # Get timetable
        timetable = request.env['university.timetable'].search([
            ('faculty_id', '=', faculty.id),
            ('active', '=', True)
        ], order='day_of_week, start_time')

        # Group by day
        timetable_by_day = {}
        for tt in timetable:
            if tt.day_of_week not in timetable_by_day:
                timetable_by_day[tt.day_of_week] = []
            timetable_by_day[tt.day_of_week].append(tt)

        # Get subjects
        subjects = request.env['university.subject'].search([
            ('faculty_ids', 'in', [faculty.id])
        ])

        values = {
            'faculty': faculty,
            'timetable_by_day': timetable_by_day,
            'subjects': subjects,
            'page_name': 'faculty_classes',
        }

        return request.render("university_management.faculty_classes", values)

    # ==================== ATTENDANCE ====================
    @http.route(['/my/faculty/attendance'], type='http', auth="user", website=True)
    def faculty_attendance(self, date=None, subject=None, batch=None, **kw):
        """Mark and view attendance"""
        faculty = self._get_faculty()

        if not faculty:
            return request.redirect('/my')

        if not date:
            date = fields.Date.today()

        # Get subjects taught by faculty
        subjects = request.env['university.subject'].search([
            ('faculty_ids', 'in', [faculty.id])
        ])

        # Get batches
        batches = request.env['student.batch'].search([
            ('active', '=', True)
        ])

        # Get attendance records
        domain = [('faculty_id', '=', faculty.id)]
        if date:
            domain += [('date', '=', date)]
        if subject:
            domain += [('subject_id', '=', int(subject))]
        if batch:
            domain += [('batch_id', '=', int(batch))]

        attendance_records = request.env['student.attendance'].search(domain, order='student_id')

        values = {
            'faculty': faculty,
            'subjects': subjects,
            'batches': batches,
            'attendance_records': attendance_records,
            'selected_date': date,
            'selected_subject': int(subject) if subject else None,
            'selected_batch': int(batch) if batch else None,
            'page_name': 'faculty_attendance',
        }

        return request.render("university_management.faculty_attendance", values)

    @http.route(['/my/faculty/attendance/mark'], type='http', auth="user", methods=['POST'], website=True, csrf=True)
    def faculty_attendance_mark(self, **post):
        """Mark attendance for students"""
        faculty = self._get_faculty()

        if not faculty:
            return request.redirect('/my')

        try:
            date = post.get('date')
            subject_id = int(post.get('subject_id'))
            batch_id = int(post.get('batch_id'))

            # Get students
            students = request.env['student.student'].search([
                ('batch_id', '=', batch_id),
                ('state', '=', 'enrolled')
            ])

            # Mark attendance
            for student in students:
                status = post.get(f'attendance_{student.id}', 'absent')

                # Check if attendance already exists
                existing = request.env['student.attendance'].search([
                    ('student_id', '=', student.id),
                    ('subject_id', '=', subject_id),
                    ('date', '=', date),
                    ('faculty_id', '=', faculty.id)
                ])

                if existing:
                    existing.write({'state': status})
                else:
                    request.env['student.attendance'].create({
                        'student_id': student.id,
                        'subject_id': subject_id,
                        'batch_id': batch_id,
                        'date': date,
                        'faculty_id': faculty.id,
                        'state': status,
                    })

            return request.redirect(
                f'/my/faculty/attendance?date={date}&subject={subject_id}&batch={batch_id}&success=1')
        except Exception as e:
            _logger.error("Error marking attendance: %s", str(e))
            return request.redirect('/my/faculty/attendance?error=1')

    # ==================== STUDENTS ====================
    @http.route(['/my/faculty/students'], type='http', auth="user", website=True)
    def faculty_students(self, batch=None, **kw):
        """View students"""
        faculty = self._get_faculty()

        if not faculty:
            return request.redirect('/my')

        # Get batches assigned to faculty
        batches = request.env['student.batch'].search([
            ('class_coordinator_id', '=', faculty.id)
        ])

        # Get students
        domain = [('state', '=', 'enrolled')]
        if batch:
            domain += [('batch_id', '=', int(batch))]
        elif batches:
            domain += [('batch_id', 'in', batches.ids)]

        students = request.env['student.student'].search(domain, order='name')

        values = {
            'faculty': faculty,
            'students': students,
            'batches': batches,
            'selected_batch': int(batch) if batch else None,
            'page_name': 'faculty_students',
        }

        return request.render("university_management.faculty_students", values)

    @http.route(['/my/faculty/student/<int:student_id>'], type='http', auth="user", website=True)
    def faculty_student_detail(self, student_id, **kw):
        """View student detail"""
        faculty = self._get_faculty()
        student = request.env['student.student'].browse(student_id)

        if not faculty or not student.exists():
            return request.redirect('/my/faculty/students')

        # Get student's attendance in faculty's subjects
        attendance = request.env['student.attendance'].search([
            ('student_id', '=', student_id),
            ('faculty_id', '=', faculty.id)
        ], order='date desc', limit=20)

        values = {
            'faculty': faculty,
            'student': student,
            'attendance': attendance,
            'page_name': 'student_detail',
        }

        return request.render("university_management.faculty_student_detail", values)

    # ==================== LEAVE REQUESTS ====================
    @http.route(['/my/faculty/leave'], type='http', auth="user", website=True)
    def faculty_leave(self, **kw):
        """View and request leave"""
        faculty = self._get_faculty()

        if not faculty:
            return request.redirect('/my')

        leave_requests = request.env['faculty.leave'].search([
            ('faculty_id', '=', faculty.id)
        ], order='from_date desc')

        values = {
            'faculty': faculty,
            'leave_requests': leave_requests,
            'page_name': 'faculty_leave',
        }

        return request.render("university_management.faculty_leave", values)

    @http.route(['/my/faculty/leave/request'], type='http', auth="user", methods=['POST'], website=True, csrf=True)
    def faculty_leave_request(self, **post):
        """Submit leave request"""
        faculty = self._get_faculty()

        if not faculty:
            return request.redirect('/my')

        try:
            leave_vals = {
                'faculty_id': faculty.id,
                'from_date': post.get('from_date'),
                'to_date': post.get('to_date'),
                'leave_type': post.get('leave_type'),
                'reason': post.get('reason'),
            }

            request.env['faculty.leave'].create(leave_vals)

            return request.redirect('/my/faculty/leave?success=1')
        except Exception as e:
            _logger.error("Error submitting leave request: %s", str(e))
            return request.redirect('/my/faculty/leave?error=1')

    # ==================== PROFILE ====================
    @http.route(['/my/faculty/profile'], type='http', auth="user", website=True)
    def faculty_profile(self, **kw):
        """View and update profile"""
        faculty = self._get_faculty()

        if not faculty:
            return request.redirect('/my')

        values = {
            'faculty': faculty,
            'page_name': 'faculty_profile',
        }

        return request.render("university_management.faculty_profile", values)

    @http.route(['/my/faculty/profile/update'], type='http', auth="user", methods=['POST'], website=True, csrf=True)
    def faculty_profile_update(self, **post):
        """Update faculty profile"""
        faculty = self._get_faculty()

        if not faculty:
            return request.redirect('/my')

        try:
            update_vals = {
                'mobile': post.get('mobile'),
                'email': post.get('email'),
                'current_address': post.get('current_address'),
                'qualification': post.get('qualification'),
                'specialization': post.get('specialization'),
                'bio': post.get('bio'),
            }

            # Handle photo upload
            if post.get('photo'):
                update_vals['photo'] = base64.b64encode(post.get('photo').read())

            faculty.write(update_vals)

            return request.redirect('/my/faculty/profile?success=1')
        except Exception as e:
            _logger.error("Error updating faculty profile: %s", str(e))
            return request.redirect('/my/faculty/profile?error=1')
