# -*- coding: utf-8 -*-

from odoo import http, fields, _
from odoo.http import request, Response
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import json
import logging
import base64
from collections import defaultdict
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tools import date_utils

_logger = logging.getLogger(__name__)


class UniversityDashboardController(http.Controller):
    """
    University Management System Dashboard Controller
    Handles all dashboard routes and aggregates data from multiple modules
    """

    @http.route('/university/dashboard', type='http', auth='user', website=False)
    def university_dashboard(self, **kwargs):
        """
        Main dashboard view route
        """
        return request.render('university_management.university_dashboard_template', {})

    @http.route('/university/dashboard/data', type='json', auth='user')
    def get_dashboard_data(self, **kwargs):
        """
        Get complete dashboard statistics from all modules
        Returns comprehensive JSON data for dashboard widgets
        """
        try:
            data = {
                'overview': self._get_overview_statistics(),
                'academic': self._get_academic_statistics(),
                'student': self._get_student_statistics(),
                'faculty': self._get_faculty_statistics(),
                'examination': self._get_examination_statistics(),
                'fee': self._get_fee_statistics(),
                'library': self._get_library_statistics(),
                'hostel': self._get_hostel_statistics(),
                'transport': self._get_transport_statistics(),
                'placement': self._get_placement_statistics(),
                'attendance': self._get_attendance_statistics(),
                'recent_activities': self._get_recent_activities(),
                'upcoming_events': self._get_upcoming_events(),
                'alerts': self._get_alerts_notifications(),
            }
            return {'status': 'success', 'data': data}
        except Exception as e:
            _logger.error(f"Dashboard data error: {str(e)}")
            return {'status': 'error', 'message': str(e)}

    # ==================== OVERVIEW STATISTICS ====================

    def _get_overview_statistics(self):
        """
        Get overall university statistics
        """
        today = fields.Date.today()

        return {
            'total_students': request.env['student.student'].search_count([('state', '=', 'enrolled')]),
            'total_faculty': request.env['faculty.faculty'].search_count([('state', '=', 'active')]),
            'total_programs': request.env['university.program'].search_count([('active', '=', True)]),
            'total_departments': request.env['university.department'].search_count([('active', '=', True)]),
            'total_courses': request.env['university.course'].search_count([('active', '=', True)]),
            'active_batches': request.env['university.batch'].search_count([('state', '=', 'active')]),
            'library_books': request.env['library.book'].search_count([]),
            'hostel_capacity': self._get_hostel_capacity(),
            'transport_vehicles': request.env['transport.vehicle'].search_count([('state', '=', 'active')]),
        }

    # ==================== ACADEMIC STATISTICS ====================

    def _get_academic_statistics(self):
        """
        Get academic module statistics
        """
        AcademicYear = request.env['university.academic.year']
        Program = request.env['university.program']
        Department = request.env['university.department']
        Course = request.env['university.course']
        Batch = request.env['university.batch']

        # Current academic year
        current_academic_year = AcademicYear.search([('state', '=', 'active')], limit=1)

        # Programs breakdown
        programs = Program.search([('active', '=', True)])
        program_data = []
        for program in programs:
            student_count = request.env['student.student'].search_count([
                ('program_id', '=', program.id),
                ('state', '=', 'enrolled')
            ])
            program_data.append({
                'name': program.name,
                'code': program.code,
                'student_count': student_count,
                'duration': program.duration,
                'type': program.program_type
            })

        # Departments breakdown
        departments = Department.search([('active', '=', True)])
        department_data = []
        for dept in departments:
            student_count = request.env['student.student'].search_count([
                ('department_id', '=', dept.id),
                ('state', '=', 'enrolled')
            ])
            faculty_count = request.env['faculty.faculty'].search_count([
                ('department_id', '=', dept.id),
                ('state', '=', 'active')
            ])
            department_data.append({
                'name': dept.name,
                'code': dept.code,
                'hod': dept.hod_id.name if dept.hod_id else '',
                'student_count': student_count,
                'faculty_count': faculty_count
            })

        # Course statistics
        total_courses = Course.search_count([('active', '=', True)])
        theory_courses = Course.search_count([('course_type', '=', 'theory')])
        practical_courses = Course.search_count([('course_type', '=', 'practical')])

        # Batch statistics
        active_batches = Batch.search_count([('state', '=', 'active')])
        total_batches = Batch.search_count([])

        return {
            'current_academic_year': current_academic_year.name if current_academic_year else 'N/A',
            'programs': program_data,
            'departments': department_data,
            'courses': {
                'total': total_courses,
                'theory': theory_courses,
                'practical': practical_courses
            },
            'batches': {
                'active': active_batches,
                'total': total_batches
            }
        }

    # ==================== STUDENT STATISTICS ====================

    def _get_student_statistics(self):
        """
        Get student module statistics
        """
        Student = request.env['student.student']
        Admission = request.env['student.admission']

        today = fields.Date.today()
        current_month_start = today.replace(day=1)

        # Student counts by state
        total_students = Student.search_count([])
        enrolled_students = Student.search_count([('state', '=', 'enrolled')])
        graduated_students = Student.search_count([('state', '=', 'graduated')])
        suspended_students = Student.search_count([('state', '=', 'suspended')])

        # Gender distribution
        male_count = Student.search_count([('gender', '=', 'male'), ('state', '=', 'enrolled')])
        female_count = Student.search_count([('gender', '=', 'female'), ('state', '=', 'enrolled')])
        other_count = Student.search_count([('gender', '=', 'other'), ('state', '=', 'enrolled')])

        # Admission statistics
        pending_admissions = Admission.search_count([('state', '=', 'pending')])
        approved_admissions = Admission.search_count([
            ('state', '=', 'approved'),
            ('admission_date', '>=', current_month_start)
        ])
        rejected_admissions = Admission.search_count([
            ('state', '=', 'rejected'),
            ('admission_date', '>=', current_month_start)
        ])

        # New admissions this month
        new_admissions_month = Admission.search_count([
            ('state', '=', 'approved'),
            ('admission_date', '>=', current_month_start)
        ])

        # Students by year/semester
        students_by_year = []
        for year in range(1, 5):
            count = Student.search_count([
                ('current_year', '=', str(year)),
                ('state', '=', 'enrolled')
            ])
            students_by_year.append({'year': year, 'count': count})

        # Document verification status
        documents_pending = request.env['student.document'].search_count([
            ('verification_status', '=', 'pending')
        ])
        documents_verified = request.env['student.document'].search_count([
            ('verification_status', '=', 'verified')
        ])

        return {
            'total': total_students,
            'enrolled': enrolled_students,
            'graduated': graduated_students,
            'suspended': suspended_students,
            'gender_distribution': {
                'male': male_count,
                'female': female_count,
                'other': other_count
            },
            'admissions': {
                'pending': pending_admissions,
                'approved_this_month': approved_admissions,
                'rejected_this_month': rejected_admissions,
                'new_this_month': new_admissions_month
            },
            'by_year': students_by_year,
            'documents': {
                'pending': documents_pending,
                'verified': documents_verified
            }
        }

    # ==================== FACULTY STATISTICS ====================

    def _get_faculty_statistics(self):
        """
        Get faculty module statistics
        """
        Faculty = request.env['faculty.faculty']
        FacultyAttendance = request.env['faculty.attendance']
        FacultyLeave = request.env['faculty.leave']

        today = fields.Date.today()
        current_month_start = today.replace(day=1)

        # Faculty counts
        total_faculty = Faculty.search_count([])
        active_faculty = Faculty.search_count([('state', '=', 'active')])
        inactive_faculty = Faculty.search_count([('state', '=', 'inactive')])

        # Employment type breakdown
        full_time = Faculty.search_count([('employment_type', '=', 'full_time'), ('state', '=', 'active')])
        part_time = Faculty.search_count([('employment_type', '=', 'part_time'), ('state', '=', 'active')])
        contract = Faculty.search_count([('employment_type', '=', 'contract'), ('state', '=', 'active')])

        # Designation breakdown
        designations = request.env['faculty.designation'].search([('active', '=', True)])
        designation_data = []
        for designation in designations:
            count = Faculty.search_count([
                ('designation_id', '=', designation.id),
                ('state', '=', 'active')
            ])
            if count > 0:
                designation_data.append({
                    'name': designation.name,
                    'count': count
                })

        # Attendance statistics (current month)
        total_attendance = FacultyAttendance.search_count([
            ('date', '>=', current_month_start),
            ('date', '<=', today)
        ])
        present_count = FacultyAttendance.search_count([
            ('date', '>=', current_month_start),
            ('date', '<=', today),
            ('state', '=', 'present')
        ])
        absent_count = FacultyAttendance.search_count([
            ('date', '>=', current_month_start),
            ('date', '<=', today),
            ('state', '=', 'absent')
        ])

        # Leave statistics
        pending_leaves = FacultyLeave.search_count([('state', '=', 'submitted')])
        approved_leaves_month = FacultyLeave.search_count([
            ('state', '=', 'approved'),
            ('date_from', '>=', current_month_start)
        ])

        # Today's attendance
        today_present = FacultyAttendance.search_count([
            ('date', '=', today),
            ('state', '=', 'present')
        ])
        today_absent = FacultyAttendance.search_count([
            ('date', '=', today),
            ('state', '=', 'absent')
        ])

        return {
            'total': total_faculty,
            'active': active_faculty,
            'inactive': inactive_faculty,
            'employment_types': {
                'full_time': full_time,
                'part_time': part_time,
                'contract': contract
            },
            'by_designation': designation_data,
            'attendance_month': {
                'total': total_attendance,
                'present': present_count,
                'absent': absent_count,
                'percentage': round((present_count / total_attendance * 100) if total_attendance > 0 else 0, 2)
            },
            'leaves': {
                'pending': pending_leaves,
                'approved_this_month': approved_leaves_month
            },
            'today_attendance': {
                'present': today_present,
                'absent': today_absent
            }
        }

    # ==================== EXAMINATION STATISTICS ====================

    def _get_examination_statistics(self):
        """
        Get examination module statistics
        """
        Examination = request.env['examination.examination']
        ExamResult = request.env['exam.result']
        HallTicket = request.env['hall.ticket']
        Revaluation = request.env['revaluation.revaluation']

        today = fields.Date.today()

        # Upcoming exams (next 30 days)
        upcoming_exams = Examination.search_count([
            ('start_date', '>=', today),
            ('start_date', '<=', today + timedelta(days=30)),
            ('state', '=', 'scheduled')
        ])

        # Ongoing exams
        ongoing_exams = Examination.search_count([
            ('start_date', '<=', today),
            ('end_date', '>=', today),
            ('state', '=', 'ongoing')
        ])

        # Completed exams (current year)
        year_start = today.replace(month=1, day=1)
        completed_exams = Examination.search_count([
            ('end_date', '>=', year_start),
            ('state', '=', 'completed')
        ])

        # Hall tickets generated
        hall_tickets_generated = HallTicket.search_count([
            ('exam_id.start_date', '>=', today),
            ('state', '=', 'generated')
        ])

        # Results statistics
        results_published = ExamResult.search_count([
            ('state', '=', 'published'),
            ('publish_date', '>=', year_start)
        ])
        results_pending = ExamResult.search_count([
            ('state', 'in', ['draft', 'evaluated'])
        ])

        # Pass/Fail statistics (current year)
        passed_students = ExamResult.search_count([
            ('result', '=', 'pass'),
            ('publish_date', '>=', year_start)
        ])
        failed_students = ExamResult.search_count([
            ('result', '=', 'fail'),
            ('publish_date', '>=', year_start)
        ])

        # Revaluation requests
        pending_revaluations = Revaluation.search_count([('state', '=', 'pending')])
        completed_revaluations = Revaluation.search_count([
            ('state', '=', 'completed'),
            ('request_date', '>=', today.replace(day=1))
        ])

        return {
            'upcoming_exams': upcoming_exams,
            'ongoing_exams': ongoing_exams,
            'completed_exams': completed_exams,
            'hall_tickets': {
                'generated': hall_tickets_generated
            },
            'results': {
                'published': results_published,
                'pending': results_pending,
                'passed': passed_students,
                'failed': failed_students,
                'pass_percentage': round((passed_students / (passed_students + failed_students) * 100)
                                         if (passed_students + failed_students) > 0 else 0, 2)
            },
            'revaluations': {
                'pending': pending_revaluations,
                'completed_this_month': completed_revaluations
            }
        }

    # ==================== FEE STATISTICS ====================

    def _get_fee_statistics(self):
        """
        Get fee module statistics
        """
        FeePayment = request.env['fee.payment']
        FeeStructure = request.env['fee.structure']
        Scholarship = request.env['scholarship.scholarship']

        today = fields.Date.today()
        current_month_start = today.replace(day=1)
        current_year_start = today.replace(month=4, day=1)  # Academic year April start

        # Fee collection statistics
        total_fee_collected = sum(FeePayment.search([
            ('state', '=', 'paid'),
            ('payment_date', '>=', current_year_start)
        ]).mapped('amount'))

        monthly_collection = sum(FeePayment.search([
            ('state', '=', 'paid'),
            ('payment_date', '>=', current_month_start)
        ]).mapped('amount'))

        # Pending payments
        pending_payments = FeePayment.search_count([('state', '=', 'pending')])
        overdue_payments = FeePayment.search_count([
            ('state', '=', 'pending'),
            ('due_date', '<', today)
        ])

        # Payment modes
        cash_payments = FeePayment.search_count([
            ('payment_mode', '=', 'cash'),
            ('payment_date', '>=', current_month_start)
        ])
        online_payments = FeePayment.search_count([
            ('payment_mode', '=', 'online'),
            ('payment_date', '>=', current_month_start)
        ])
        cheque_payments = FeePayment.search_count([
            ('payment_mode', '=', 'cheque'),
            ('payment_date', '>=', current_month_start)
        ])

        # Scholarships
        active_scholarships = Scholarship.search_count([('state', '=', 'active')])
        scholarship_amount = sum(Scholarship.search([
            ('state', '=', 'active'),
            ('academic_year_id.state', '=', 'active')
        ]).mapped('amount'))

        # Fee defaulters
        fee_defaulters = request.env['student.student'].search_count([
            ('fee_status', '=', 'defaulter'),
            ('state', '=', 'enrolled')
        ])

        return {
            'total_collected_year': total_fee_collected,
            'monthly_collection': monthly_collection,
            'pending_payments': pending_payments,
            'overdue_payments': overdue_payments,
            'payment_modes': {
                'cash': cash_payments,
                'online': online_payments,
                'cheque': cheque_payments
            },
            'scholarships': {
                'active': active_scholarships,
                'total_amount': scholarship_amount
            },
            'defaulters': fee_defaulters
        }

    # ==================== LIBRARY STATISTICS ====================

    def _get_library_statistics(self):
        """
        Get library module statistics
        """
        LibraryBook = request.env['library.book']
        LibraryIssue = request.env['library.issue']
        LibraryFine = request.env['library.fine']

        today = fields.Date.today()

        # Book statistics
        total_books = LibraryBook.search_count([])
        available_books = LibraryBook.search_count([('state', '=', 'available')])
        issued_books = LibraryBook.search_count([('state', '=', 'issued')])
        damaged_books = LibraryBook.search_count([('state', '=', 'damaged')])

        # Books by category
        categories = request.env['library.category'].search([])
        category_data = []
        for category in categories:
            count = LibraryBook.search_count([('category_id', '=', category.id)])
            if count > 0:
                category_data.append({
                    'name': category.name,
                    'count': count
                })

        # Issue/Return statistics
        current_month_start = today.replace(day=1)
        books_issued_month = LibraryIssue.search_count([
            ('issue_date', '>=', current_month_start),
            ('issue_date', '<=', today)
        ])
        books_returned_month = LibraryIssue.search_count([
            ('return_date', '>=', current_month_start),
            ('return_date', '<=', today),
            ('state', '=', 'returned')
        ])

        # Overdue books
        overdue_books = LibraryIssue.search_count([
            ('due_date', '<', today),
            ('state', '=', 'issued')
        ])

        # Fine statistics
        total_fines = sum(LibraryFine.search([
            ('fine_date', '>=', current_month_start)
        ]).mapped('amount'))
        pending_fines = sum(LibraryFine.search([
            ('state', '=', 'unpaid')
        ]).mapped('amount'))

        return {
            'total_books': total_books,
            'available': available_books,
            'issued': issued_books,
            'damaged': damaged_books,
            'by_category': category_data,
            'monthly_activity': {
                'issued': books_issued_month,
                'returned': books_returned_month
            },
            'overdue': overdue_books,
            'fines': {
                'total_this_month': total_fines,
                'pending': pending_fines
            }
        }

    # ==================== HOSTEL STATISTICS ====================

    def _get_hostel_statistics(self):
        """
        Get hostel module statistics
        """
        Hostel = request.env['hostel.hostel']
        HostelRoom = request.env['hostel.room']
        HostelAllocation = request.env['hostel.allocation']
        HostelComplaint = request.env['hostel.complaint']
        MessAttendance = request.env['mess.attendance']

        today = fields.Date.today()

        # Hostel capacity
        total_capacity = sum(Hostel.search([('active', '=', True)]).mapped('total_capacity'))
        allocated_beds = HostelAllocation.search_count([('state', '=', 'allocated')])
        available_beds = total_capacity - allocated_beds

        # Hostel wise occupancy
        hostels = Hostel.search([('active', '=', True)])
        hostel_data = []
        for hostel in hostels:
            allocated = HostelAllocation.search_count([
                ('hostel_id', '=', hostel.id),
                ('state', '=', 'allocated')
            ])
            hostel_data.append({
                'name': hostel.name,
                'type': hostel.hostel_type,
                'capacity': hostel.total_capacity,
                'allocated': allocated,
                'available': hostel.total_capacity - allocated,
                'occupancy_percentage': round(
                    (allocated / hostel.total_capacity * 100) if hostel.total_capacity > 0 else 0, 2)
            })

        # Room statistics
        total_rooms = HostelRoom.search_count([])
        occupied_rooms = HostelRoom.search_count([('status', '=', 'occupied')])
        available_rooms = HostelRoom.search_count([('status', '=', 'available')])
        maintenance_rooms = HostelRoom.search_count([('status', '=', 'maintenance')])

        # Complaints
        pending_complaints = HostelComplaint.search_count([('state', '=', 'pending')])
        resolved_complaints = HostelComplaint.search_count([
            ('state', '=', 'resolved'),
            ('complaint_date', '>=', today.replace(day=1))
        ])

        # Mess attendance today
        mess_attendance_today = MessAttendance.search_count([
            ('date', '=', today),
            ('present', '=', True)
        ])

        return {
            'capacity': {
                'total': total_capacity,
                'allocated': allocated_beds,
                'available': available_beds,
                'occupancy_percentage': round((allocated_beds / total_capacity * 100) if total_capacity > 0 else 0, 2)
            },
            'hostels': hostel_data,
            'rooms': {
                'total': total_rooms,
                'occupied': occupied_rooms,
                'available': available_rooms,
                'maintenance': maintenance_rooms
            },
            'complaints': {
                'pending': pending_complaints,
                'resolved_this_month': resolved_complaints
            },
            'mess_attendance_today': mess_attendance_today
        }

    def _get_hostel_capacity(self):
        """Helper method for hostel capacity"""
        Hostel = request.env['hostel.hostel']
        total_capacity = sum(Hostel.search([('active', '=', True)]).mapped('total_capacity'))
        return total_capacity

    # ==================== TRANSPORT STATISTICS ====================

    def _get_transport_statistics(self):
        """
        Get transport module statistics
        """
        TransportRoute = request.env['transport.route']
        TransportVehicle = request.env['transport.vehicle']
        TransportAllocation = request.env['transport.allocation']

        # Vehicle statistics
        total_vehicles = TransportVehicle.search_count([])
        active_vehicles = TransportVehicle.search_count([('state', '=', 'active')])
        maintenance_vehicles = TransportVehicle.search_count([('state', '=', 'maintenance')])

        # Route statistics
        total_routes = TransportRoute.search_count([('active', '=', True)])

        # Route wise allocation
        routes = TransportRoute.search([('active', '=', True)])
        route_data = []
        for route in routes:
            student_count = TransportAllocation.search_count([
                ('route_id', '=', route.id),
                ('state', '=', 'active')
            ])
            route_data.append({
                'name': route.name,
                'route_code': route.code,
                'vehicle': route.vehicle_id.name if route.vehicle_id else 'Not Assigned',
                'student_count': student_count,
                'capacity': route.vehicle_id.capacity if route.vehicle_id else 0
            })

        # Student allocations
        total_allocations = TransportAllocation.search_count([('state', '=', 'active')])

        return {
            'vehicles': {
                'total': total_vehicles,
                'active': active_vehicles,
                'maintenance': maintenance_vehicles
            },
            'routes': {
                'total': total_routes,
                'details': route_data
            },
            'student_allocations': total_allocations
        }

    # ==================== PLACEMENT STATISTICS ====================

    def _get_placement_statistics(self):
        """
        Get placement module statistics
        """
        PlacementDrive = request.env['placement.drive']
        PlacementCompany = request.env['placement.company']
        PlacementApplication = request.env['placement.application']
        PlacementOffer = request.env['placement.offer']

        today = fields.Date.today()
        current_year_start = today.replace(month=4, day=1)

        # Placement drives
        upcoming_drives = PlacementDrive.search_count([
            ('drive_date', '>=', today),
            ('state', '=', 'scheduled')
        ])
        completed_drives = PlacementDrive.search_count([
            ('drive_date', '>=', current_year_start),
            ('state', '=', 'completed')
        ])

        # Companies
        registered_companies = PlacementCompany.search_count([('active', '=', True)])
        companies_visited = PlacementCompany.search([
            ('visit_date', '>=', current_year_start)
        ]).ids

        # Applications
        total_applications = PlacementApplication.search_count([
            ('create_date', '>=', current_year_start)
        ])
        shortlisted = PlacementApplication.search_count([
            ('state', '=', 'shortlisted'),
            ('create_date', '>=', current_year_start)
        ])

        # Offers
        total_offers = PlacementOffer.search_count([
            ('offer_date', '>=', current_year_start),
            ('state', '=', 'accepted')
        ])

        # Average package
        offers = PlacementOffer.search([
            ('offer_date', '>=', current_year_start),
            ('state', '=', 'accepted')
        ])
        avg_package = sum(offers.mapped('package_amount')) / len(offers) if offers else 0
        highest_package = max(offers.mapped('package_amount')) if offers else 0

        # Placement percentage (final year students)
        final_year_students = request.env['student.student'].search_count([
            ('current_year', '=', '4'),
            ('state', '=', 'enrolled')
        ])
        placed_students = PlacementOffer.search_count([
            ('offer_date', '>=', current_year_start),
            ('state', '=', 'accepted')
        ])
        placement_percentage = round((placed_students / final_year_students * 100) if final_year_students > 0 else 0, 2)

        return {
            'drives': {
                'upcoming': upcoming_drives,
                'completed': completed_drives
            },
            'companies': {
                'registered': registered_companies,
                'visited_this_year': len(companies_visited)
            },
            'applications': {
                'total': total_applications,
                'shortlisted': shortlisted
            },
            'offers': {
                'total': total_offers,
                'average_package': round(avg_package, 2),
                'highest_package': highest_package
            },
            'placement_stats': {
                'total_students': final_year_students,
                'placed': placed_students,
                'placement_percentage': placement_percentage
            }
        }

    # ==================== ATTENDANCE STATISTICS ====================

    def _get_attendance_statistics(self):
        """
        Get overall attendance statistics (Student + Faculty)
        """
        StudentAttendance = request.env['student.attendance']
        FacultyAttendance = request.env['faculty.attendance']

        today = fields.Date.today()

        # Student attendance today
        student_present_today = StudentAttendance.search_count([
            ('date', '=', today),
            ('state', '=', 'present')
        ])
        student_absent_today = StudentAttendance.search_count([
            ('date', '=', today),
            ('state', '=', 'absent')
        ])

        # Faculty attendance today
        faculty_present_today = FacultyAttendance.search_count([
            ('date', '=', today),
            ('state', '=', 'present')
        ])
        faculty_absent_today = FacultyAttendance.search_count([
            ('date', '=', today),
            ('state', '=', 'absent')
        ])

        # Weekly attendance trend (last 7 days)
        weekly_trend = []
        for i in range(6, -1, -1):
            date = today - timedelta(days=i)
            student_present = StudentAttendance.search_count([
                ('date', '=', date),
                ('state', '=', 'present')
            ])
            faculty_present = FacultyAttendance.search_count([
                ('date', '=', date),
                ('state', '=', 'present')
            ])
            weekly_trend.append({
                'date': date.strftime('%Y-%m-%d'),
                'day': date.strftime('%a'),
                'student_present': student_present,
                'faculty_present': faculty_present
            })

        return {
            'today': {
                'student': {
                    'present': student_present_today,
                    'absent': student_absent_today
                },
                'faculty': {
                    'present': faculty_present_today,
                    'absent': faculty_absent_today
                }
            },
            'weekly_trend': weekly_trend
        }

    # ==================== RECENT ACTIVITIES ====================

    def _get_recent_activities(self):
        """
        Get recent activities across all modules
        """
        activities = []

        # Recent admissions
        recent_admissions = request.env['student.admission'].search([
            ('state', '=', 'approved')
        ], order='admission_date desc', limit=5)

        for admission in recent_admissions:
            activities.append({
                'type': 'admission',
                'title': f"New Admission: {admission.student_id.name}",
                'description': f"Admitted to {admission.program_id.name}",
                'date': admission.admission_date.strftime('%Y-%m-%d %H:%M:%S'),
                'icon': 'fa-user-plus',
                'color': 'success'
            })

        # Recent examinations
        recent_exams = request.env['examination.examination'].search([
            ('state', 'in', ['scheduled', 'ongoing'])
        ], order='start_date desc', limit=3)

        for exam in recent_exams:
            activities.append({
                'type': 'examination',
                'title': f"Exam: {exam.name}",
                'description': f"Starting on {exam.start_date}",
                'date': exam.create_date.strftime('%Y-%m-%d %H:%M:%S'),
                'icon': 'fa-file-text',
                'color': 'warning'
            })

        # Recent placements
        recent_offers = request.env['placement.offer'].search([
            ('state', '=', 'accepted')
        ], order='offer_date desc', limit=3)

        for offer in recent_offers:
            activities.append({
                'type': 'placement',
                'title': f"Placement: {offer.student_id.name}",
                'description': f"Placed at {offer.company_id.name}",
                'date': offer.offer_date.strftime('%Y-%m-%d %H:%M:%S'),
                'icon': 'fa-briefcase',
                'color': 'primary'
            })

        # Sort by date
        activities.sort(key=lambda x: x['date'], reverse=True)

        return activities[:10]

    # ==================== UPCOMING EVENTS ====================

    def _get_upcoming_events(self):
        """
        Get upcoming events across all modules
        """
        events = []
        today = fields.Date.today()
        next_30_days = today + timedelta(days=30)

        # Upcoming exams
        upcoming_exams = request.env['examination.examination'].search([
            ('start_date', '>=', today),
            ('start_date', '<=', next_30_days),
            ('state', '=', 'scheduled')
        ], order='start_date asc', limit=5)

        for exam in upcoming_exams:
            events.append({
                'type': 'examination',
                'title': exam.name,
                'date': exam.start_date.strftime('%Y-%m-%d'),
                'time': '',
                'location': exam.exam_center if hasattr(exam, 'exam_center') else '',
                'icon': 'fa-file-text',
                'color': 'danger'
            })

        # Upcoming placement drives
        upcoming_drives = request.env['placement.drive'].search([
            ('drive_date', '>=', today),
            ('drive_date', '<=', next_30_days),
            ('state', '=', 'scheduled')
        ], order='drive_date asc', limit=5)

        for drive in upcoming_drives:
            events.append({
                'type': 'placement',
                'title': f"Placement Drive - {drive.company_id.name}",
                'date': drive.drive_date.strftime('%Y-%m-%d'),
                'time': drive.drive_time if hasattr(drive, 'drive_time') else '',
                'location': drive.venue if hasattr(drive, 'venue') else '',
                'icon': 'fa-briefcase',
                'color': 'success'
            })

        # Upcoming university events
        upcoming_uni_events = request.env['university.event'].search([
            ('event_date', '>=', today),
            ('event_date', '<=', next_30_days),
            ('state', '=', 'confirmed')
        ], order='event_date asc', limit=5)

        for event in upcoming_uni_events:
            events.append({
                'type': 'event',
                'title': event.name,
                'date': event.event_date.strftime('%Y-%m-%d'),
                'time': event.start_time if hasattr(event, 'start_time') else '',
                'location': event.venue if hasattr(event, 'venue') else '',
                'icon': 'fa-calendar',
                'color': 'info'
            })

        # Sort by date
        events.sort(key=lambda x: x['date'])

        return events[:10]

    # ==================== ALERTS & NOTIFICATIONS ====================

    def _get_alerts_notifications(self):
        """
        Get system alerts and notifications
        """
        alerts = []
        today = fields.Date.today()

        # Fee defaulters alert
        fee_defaulters = request.env['student.student'].search_count([
            ('fee_status', '=', 'defaulter'),
            ('state', '=', 'enrolled')
        ])
        if fee_defaulters > 0:
            alerts.append({
                'type': 'warning',
                'title': 'Fee Defaulters',
                'message': f"{fee_defaulters} students have pending fee payments",
                'icon': 'fa-exclamation-triangle',
                'action_url': '/web#model=student.student&view_type=list&filter=fee_defaulters'
            })

        # Pending admissions
        pending_admissions = request.env['student.admission'].search_count([('state', '=', 'pending')])
        if pending_admissions > 0:
            alerts.append({
                'type': 'info',
                'title': 'Pending Admissions',
                'message': f"{pending_admissions} admission applications awaiting approval",
                'icon': 'fa-user-plus',
                'action_url': '/web#model=student.admission&view_type=list&filter=pending'
            })

        # Pending leave requests
        pending_leaves = request.env['faculty.leave'].search_count([('state', '=', 'submitted')])
        if pending_leaves > 0:
            alerts.append({
                'type': 'info',
                'title': 'Pending Leave Requests',
                'message': f"{pending_leaves} faculty leave requests pending approval",
                'icon': 'fa-calendar-times-o',
                'action_url': '/web#model=faculty.leave&view_type=list&filter=pending'
            })

        # Overdue library books
        overdue_books = request.env['library.issue'].search_count([
            ('due_date', '<', today),
            ('state', '=', 'issued')
        ])
        if overdue_books > 0:
            alerts.append({
                'type': 'danger',
                'title': 'Overdue Library Books',
                'message': f"{overdue_books} books are overdue for return",
                'icon': 'fa-book',
                'action_url': '/web#model=library.issue&view_type=list&filter=overdue'
            })

        # Upcoming exams (within 7 days)
        upcoming_exams = request.env['examination.examination'].search_count([
            ('start_date', '>=', today),
            ('start_date', '<=', today + timedelta(days=7)),
            ('state', '=', 'scheduled')
        ])
        if upcoming_exams > 0:
            alerts.append({
                'type': 'warning',
                'title': 'Upcoming Examinations',
                'message': f"{upcoming_exams} exams scheduled in the next 7 days",
                'icon': 'fa-file-text',
                'action_url': '/web#model=examination.examination&view_type=calendar'
            })

        # Hostel complaints pending
        pending_complaints = request.env['hostel.complaint'].search_count([('state', '=', 'pending')])
        if pending_complaints > 10:
            alerts.append({
                'type': 'warning',
                'title': 'Hostel Complaints',
                'message': f"{pending_complaints} hostel complaints need attention",
                'icon': 'fa-home',
                'action_url': '/web#model=hostel.complaint&view_type=list&filter=pending'
            })

        return alerts

    # ==================== ADDITIONAL ROUTES ====================

    @http.route('/university/dashboard/chart/<string:chart_type>', type='json', auth='user')
    def get_chart_data(self, chart_type, **kwargs):
        """
        Get specific chart data for dashboard
        """
        try:
            if chart_type == 'student_enrollment':
                return self._get_student_enrollment_chart()
            elif chart_type == 'fee_collection':
                return self._get_fee_collection_chart()
            elif chart_type == 'attendance_trend':
                return self._get_attendance_trend_chart()
            elif chart_type == 'department_wise':
                return self._get_department_wise_chart()
            elif chart_type == 'placement_trend':
                return self._get_placement_trend_chart()
            else:
                return {'status': 'error', 'message': 'Invalid chart type'}
        except Exception as e:
            _logger.error(f"Chart data error: {str(e)}")
            return {'status': 'error', 'message': str(e)}

    def _get_student_enrollment_chart(self):
        """Get student enrollment trend data"""
        Student = request.env['student.student']
        today = fields.Date.today()

        data = []
        labels = []

        for i in range(11, -1, -1):
            month_date = today - relativedelta(months=i)
            month_start = month_date.replace(day=1)
            month_end = (month_start + relativedelta(months=1)) - timedelta(days=1)

            count = Student.search_count([
                ('admission_date', '>=', month_start),
                ('admission_date', '<=', month_end)
            ])

            data.append(count)
            labels.append(month_date.strftime('%b %Y'))

        return {
            'labels': labels,
            'datasets': [{
                'label': 'New Enrollments',
                'data': data,
                'backgroundColor': 'rgba(54, 162, 235, 0.2)',
                'borderColor': 'rgba(54, 162, 235, 1)',
                'borderWidth': 2
            }]
        }

    def _get_fee_collection_chart(self):
        """Get fee collection trend data"""
        FeePayment = request.env['fee.payment']
        today = fields.Date.today()

        data = []
        labels = []

        for i in range(11, -1, -1):
            month_date = today - relativedelta(months=i)
            month_start = month_date.replace(day=1)
            month_end = (month_start + relativedelta(months=1)) - timedelta(days=1)

            total = sum(FeePayment.search([
                ('payment_date', '>=', month_start),
                ('payment_date', '<=', month_end),
                ('state', '=', 'paid')
            ]).mapped('amount'))

            data.append(total)
            labels.append(month_date.strftime('%b %Y'))

        return {
            'labels': labels,
            'datasets': [{
                'label': 'Fee Collection (₹)',
                'data': data,
                'backgroundColor': 'rgba(75, 192, 192, 0.2)',
                'borderColor': 'rgba(75, 192, 192, 1)',
                'borderWidth': 2
            }]
        }

    def _get_attendance_trend_chart(self):
        """Get attendance trend for last 30 days"""
        StudentAttendance = request.env['student.attendance']
        today = fields.Date.today()

        present_data = []
        absent_data = []
        labels = []

        for i in range(29, -1, -1):
            date = today - timedelta(days=i)

            present = StudentAttendance.search_count([
                ('date', '=', date),
                ('state', '=', 'present')
            ])
            absent = StudentAttendance.search_count([
                ('date', '=', date),
                ('state', '=', 'absent')
            ])

            present_data.append(present)
            absent_data.append(absent)
            labels.append(date.strftime('%d %b'))

        return {
            'labels': labels,
            'datasets': [
                {
                    'label': 'Present',
                    'data': present_data,
                    'backgroundColor': 'rgba(75, 192, 192, 0.5)',
                    'borderColor': 'rgba(75, 192, 192, 1)'
                },
                {
                    'label': 'Absent',
                    'data': absent_data,
                    'backgroundColor': 'rgba(255, 99, 132, 0.5)',
                    'borderColor': 'rgba(255, 99, 132, 1)'
                }
            ]
        }

    def _get_department_wise_chart(self):
        """Get department-wise student distribution"""
        Department = request.env['university.department']
        Student = request.env['student.student']

        departments = Department.search([('active', '=', True)])
        data = []
        labels = []

        for dept in departments:
            count = Student.search_count([
                ('department_id', '=', dept.id),
                ('state', '=', 'enrolled')
            ])
            data.append(count)
            labels.append(dept.code)

        return {
            'labels': labels,
            'datasets': [{
                'label': 'Students by Department',
                'data': data,
                'backgroundColor': [
                    'rgba(255, 99, 132, 0.6)',
                    'rgba(54, 162, 235, 0.6)',
                    'rgba(255, 206, 86, 0.6)',
                    'rgba(75, 192, 192, 0.6)',
                    'rgba(153, 102, 255, 0.6)',
                    'rgba(255, 159, 64, 0.6)'
                ]
            }]
        }

    def _get_placement_trend_chart(self):
        """Get placement trend over years"""
        PlacementOffer = request.env['placement.offer']

        data = []
        labels = []
        current_year = fields.Date.today().year

        for year in range(current_year - 4, current_year + 1):
            year_start = fields.Date.from_string(f'{year}-04-01')
            year_end = fields.Date.from_string(f'{year + 1}-03-31')

            count = PlacementOffer.search_count([
                ('offer_date', '>=', year_start),
                ('offer_date', '<=', year_end),
                ('state', '=', 'accepted')
            ])

            data.append(count)
            labels.append(f'{year}-{str(year + 1)[2:]}')

        return {
            'labels': labels,
            'datasets': [{
                'label': 'Students Placed',
                'data': data,
                'backgroundColor': 'rgba(153, 102, 255, 0.2)',
                'borderColor': 'rgba(153, 102, 255, 1)',
                'borderWidth': 2,
                'fill': True
            }]
        }

    @http.route('/university/dashboard/export', type='http', auth='user')
    def export_dashboard_data(self, **kwargs):
        """
        Export dashboard data as JSON/CSV
        """
        try:
            data = self.get_dashboard_data()

            # Return as JSON file
            response = request.make_response(
                json.dumps(data, indent=2, default=str),
                headers=[
                    ('Content-Type', 'application/json'),
                    ('Content-Disposition', f'attachment; filename="dashboard_data_{fields.Date.today()}.json"')
                ]
            )
            return response
        except Exception as e:
            return request.make_response(f"Error: {str(e)}", status=500)

    @http.route('/dashboard', type='http', auth='user', website=True)
    def dashboard_main(self, **kwargs):
        """Main dashboard page"""
        try:
            user = request.env.user

            # Determine user type and redirect to appropriate dashboard
            if user.has_group('university_management.group_university_admin'):
                return request.redirect('/dashboard/admin')
            elif user.has_group('university_management.group_university_student'):
                return request.redirect('/dashboard/student')
            elif user.has_group('university_management.group_university_faculty'):
                return request.redirect('/dashboard/faculty')
            elif user.has_group('university_management.group_university_parent'):
                return request.redirect('/dashboard/parent')
            else:
                return request.redirect('/dashboard/general')

        except Exception as e:
            _logger.error(f"Error loading dashboard: {str(e)}")
            return request.render('university_management.dashboard_error', {
                'error_message': str(e)
            })

    @http.route('/dashboard/admin', type='http', auth='user', website=True)
    def dashboard_admin(self, **kwargs):
        """Admin dashboard"""
        try:
            if not request.env.user.has_group('university_management.group_university_admin'):
                return request.render('university_management.access_denied')

            values = self._get_admin_dashboard_values()
            return request.render('university_management.dashboard_admin', values)

        except Exception as e:
            _logger.error(f"Error loading admin dashboard: {str(e)}")
            return request.render('university_management.dashboard_error', {
                'error_message': str(e)
            })

    @http.route('/dashboard/student', type='http', auth='user', website=True)
    def dashboard_student(self, **kwargs):
        """Student dashboard"""
        try:
            if not request.env.user.has_group('university_management.group_university_student'):
                return request.render('university_management.access_denied')

            values = self._get_student_dashboard_values()
            return request.render('university_management.dashboard_student', values)

        except Exception as e:
            _logger.error(f"Error loading student dashboard: {str(e)}")
            return request.render('university_management.dashboard_error', {
                'error_message': str(e)
            })

    @http.route('/dashboard/faculty', type='http', auth='user', website=True)
    def dashboard_faculty(self, **kwargs):
        """Faculty dashboard"""
        try:
            if not request.env.user.has_group('university_management.group_university_faculty'):
                return request.render('university_management.access_denied')

            values = self._get_faculty_dashboard_values()
            return request.render('university_management.dashboard_faculty', values)

        except Exception as e:
            _logger.error(f"Error loading faculty dashboard: {str(e)}")
            return request.render('university_management.dashboard_error', {
                'error_message': str(e)
            })

    @http.route('/dashboard/parent', type='http', auth='user', website=True)
    def dashboard_parent(self, **kwargs):
        """Parent dashboard"""
        try:
            if not request.env.user.has_group('university_management.group_university_parent'):
                return request.render('university_management.access_denied')

            values = self._get_parent_dashboard_values()
            return request.render('university_management.dashboard_parent', values)

        except Exception as e:
            _logger.error(f"Error loading parent dashboard: {str(e)}")
            return request.render('university_management.dashboard_error', {
                'error_message': str(e)
            })

    # ============================================
    # API ENDPOINTS - DASHBOARD DATA
    # ============================================

    @http.route('/dashboard/api/get_dashboard_data', type='json', auth='user', methods=['POST'], csrf=True)
    def api_get_dashboard_data(self, dashboard_code=None, filters=None, date_range=None, **kwargs):
        """Get dashboard data with widgets"""
        try:
            dashboard_model = request.env['university.dashboard']

            # Get dashboard data
            dashboard_data = dashboard_model.sudo().get_dashboard_data(dashboard_code)

            if not dashboard_data or 'error' in dashboard_data:
                return {
                    'error': dashboard_data.get('error', 'Dashboard not found'),
                    'status': 'error'
                }

            # Apply filters if provided
            if filters:
                dashboard_data = self._apply_filters(dashboard_data, filters)

            # Apply date range if provided
            if date_range:
                dashboard_data = self._apply_date_range(dashboard_data, date_range)

            return {
                'status': 'success',
                'dashboard': dashboard_data.get('dashboard'),
                'widgets': dashboard_data.get('widgets'),
                'preference': dashboard_data.get('preference'),
            }

        except Exception as e:
            _logger.error(f"Error getting dashboard data: {str(e)}")
            return {
                'error': str(e),
                'status': 'error'
            }

    @http.route('/dashboard/api/get_widget_data', type='json', auth='user', methods=['POST'], csrf=True)
    def api_get_widget_data(self, widget_id=None, filters=None, date_range=None, **kwargs):
        """Get individual widget data"""
        try:
            if not widget_id:
                return {'error': 'Widget ID is required', 'status': 'error'}

            widget = request.env['university.dashboard.widget'].sudo().browse(widget_id)

            if not widget.exists():
                return {'error': 'Widget not found', 'status': 'error'}

            # Check access
            if widget.group_ids:
                user_groups = request.env.user.groups_id
                if not bool(user_groups & widget.group_ids):
                    return {'error': 'Access denied', 'status': 'error'}

            widget_data = widget.get_widget_data()

            return {
                'status': 'success',
                'data': widget_data
            }

        except Exception as e:
            _logger.error(f"Error getting widget data: {str(e)}")
            return {
                'error': str(e),
                'status': 'error'
            }

    @http.route('/dashboard/api/refresh_widget', type='json', auth='user', methods=['POST'], csrf=True)
    def api_refresh_widget(self, widget_id=None, **kwargs):
        """Refresh single widget data"""
        try:
            if not widget_id:
                return {'error': 'Widget ID is required', 'status': 'error'}

            widget = request.env['university.dashboard.widget'].sudo().browse(widget_id)

            if not widget.exists():
                return {'error': 'Widget not found', 'status': 'error'}

            # Clear cache for this widget
            cache_key = f'widget_{widget_id}'
            request.env.registry.clear_cache()

            widget_data = widget.get_widget_data()

            return {
                'status': 'success',
                'data': widget_data,
                'refreshed_at': fields.Datetime.now().isoformat()
            }

        except Exception as e:
            _logger.error(f"Error refreshing widget: {str(e)}")
            return {
                'error': str(e),
                'status': 'error'
            }

    # ============================================
    # API ENDPOINTS - KPI DATA
    # ============================================

    @http.route('/dashboard/api/get_kpi_data', type='json', auth='user', methods=['POST'], csrf=True)
    def api_get_kpi_data(self, kpi_id=None, kpi_code=None, **kwargs):
        """Get KPI data"""
        try:
            kpi_model = request.env['university.dashboard.kpi'].sudo()

            if kpi_id:
                kpi = kpi_model.browse(kpi_id)
            elif kpi_code:
                kpi = kpi_model.search([('code', '=', kpi_code)], limit=1)
            else:
                return {'error': 'KPI ID or Code is required', 'status': 'error'}

            if not kpi.exists():
                return {'error': 'KPI not found', 'status': 'error'}

            # Calculate KPI
            value = kpi.calculate_kpi()
            status = kpi.get_kpi_status()

            return {
                'status': 'success',
                'kpi': {
                    'id': kpi.id,
                    'name': kpi.name,
                    'code': kpi.code,
                    'value': value,
                    'unit': kpi.unit,
                    'prefix': kpi.prefix,
                    'suffix': kpi.suffix,
                    'target': kpi.target_value,
                    'status': status,
                    'color': kpi.color,
                    'icon': kpi.icon,
                    'last_calculated': kpi.last_calculated.isoformat() if kpi.last_calculated else None,
                }
            }

        except Exception as e:
            _logger.error(f"Error getting KPI data: {str(e)}")
            return {
                'error': str(e),
                'status': 'error'
            }

    @http.route('/dashboard/api/get_all_kpis', type='json', auth='user', methods=['POST'], csrf=True)
    def api_get_all_kpis(self, category=None, **kwargs):
        """Get all KPIs"""
        try:
            kpi_model = request.env['university.dashboard.kpi'].sudo()

            domain = [('active', '=', True)]
            if category:
                domain.append(('category', '=', category))

            kpis = kpi_model.search(domain)

            kpi_list = []
            for kpi in kpis:
                kpi.calculate_kpi()
                kpi_list.append({
                    'id': kpi.id,
                    'name': kpi.name,
                    'code': kpi.code,
                    'value': kpi.last_value,
                    'unit': kpi.unit,
                    'prefix': kpi.prefix,
                    'suffix': kpi.suffix,
                    'target': kpi.target_value,
                    'status': kpi.get_kpi_status(),
                    'color': kpi.color,
                    'icon': kpi.icon,
                    'category': kpi.category,
                })

            return {
                'status': 'success',
                'kpis': kpi_list
            }

        except Exception as e:
            _logger.error(f"Error getting all KPIs: {str(e)}")
            return {
                'error': str(e),
                'status': 'error'
            }

    # ============================================
    # API ENDPOINTS - USER PREFERENCES
    # ============================================

    @http.route('/dashboard/api/get_user_preferences', type='json', auth='user', methods=['GET', 'POST'], csrf=True)
    def api_get_user_preferences(self, **kwargs):
        """Get user dashboard preferences"""
        try:
            user = request.env.user
            preference_model = request.env['university.dashboard.preference']

            # Get or create user preference
            dashboard = request.env['university.dashboard'].sudo().search([
                ('user_type', '=', self._get_user_type()),
                ('is_default', '=', True)
            ], limit=1)

            if not dashboard:
                return {'error': 'No default dashboard found', 'status': 'error'}

            preference = preference_model.sudo().get_user_preference(dashboard.id)

            return {
                'status': 'success',
                'preference': {
                    'id': preference.id,
                    'theme': preference.theme,
                    'refresh_interval': preference.refresh_interval,
                    'date_range': preference.date_range,
                    'visible_widgets': json.loads(preference.visible_widgets or '[]'),
                    'widget_positions': json.loads(preference.widget_positions or '{}'),
                    'custom_filters': json.loads(preference.custom_filters or '{}'),
                }
            }

        except Exception as e:
            _logger.error(f"Error getting user preferences: {str(e)}")
            return {
                'error': str(e),
                'status': 'error'
            }

    @http.route('/dashboard/api/save_user_preference', type='json', auth='user', methods=['POST'], csrf=True)
    def api_save_user_preference(self, key=None, value=None, **kwargs):
        """Save user preference"""
        try:
            if not key:
                return {'error': 'Key is required', 'status': 'error'}

            preference_model = request.env['university.dashboard.preference']

            dashboard = request.env['university.dashboard'].sudo().search([
                ('user_type', '=', self._get_user_type()),
                ('is_default', '=', True)
            ], limit=1)

            if not dashboard:
                return {'error': 'No default dashboard found', 'status': 'error'}

            preference = preference_model.sudo().get_user_preference(dashboard.id)

            # Update preference
            update_vals = {}
            if key in ['theme', 'refresh_interval', 'date_range']:
                update_vals[key] = value
            elif key == 'visible_widgets':
                update_vals['visible_widgets'] = json.dumps(value)
            elif key == 'widget_positions':
                update_vals['widget_positions'] = json.dumps(value)
            elif key == 'custom_filters':
                update_vals['custom_filters'] = json.dumps(value)

            if update_vals:
                preference.sudo().write(update_vals)

            return {
                'status': 'success',
                'message': 'Preference saved successfully'
            }

        except Exception as e:
            _logger.error(f"Error saving user preference: {str(e)}")
            return {
                'error': str(e),
                'status': 'error'
            }

    @http.route('/dashboard/api/save_widget_positions', type='json', auth='user', methods=['POST'], csrf=True)
    def api_save_widget_positions(self, positions=None, **kwargs):
        """Save widget positions"""
        try:
            if not positions:
                return {'error': 'Positions data is required', 'status': 'error'}

            preference_model = request.env['university.dashboard.preference']

            dashboard = request.env['university.dashboard'].sudo().search([
                ('user_type', '=', self._get_user_type()),
                ('is_default', '=', True)
            ], limit=1)

            if not dashboard:
                return {'error': 'No default dashboard found', 'status': 'error'}

            preference = preference_model.sudo().get_user_preference(dashboard.id)
            preference.sudo().write({
                'widget_positions': json.dumps(positions)
            })

            return {
                'status': 'success',
                'message': 'Widget positions saved successfully'
            }

        except Exception as e:
            _logger.error(f"Error saving widget positions: {str(e)}")
            return {
                'error': str(e),
                'status': 'error'
            }

    # ============================================
    # API ENDPOINTS - ALERTS
    # ============================================

    @http.route('/dashboard/api/get_alerts', type='json', auth='user', methods=['POST'], csrf=True)
    def api_get_alerts(self, state=None, limit=10, **kwargs):
        """Get dashboard alerts"""
        try:
            alert_model = request.env['university.dashboard.alert'].sudo()
            user = request.env.user

            domain = [
                ('active', '=', True),
                '|',
                ('user_ids', 'in', user.id),
                ('group_ids', 'in', user.groups_id.ids)
            ]

            if state:
                domain.append(('state', '=', state))
            else:
                domain.append(('state', 'in', ['new', 'acknowledged']))

            alerts = alert_model.search(domain, limit=limit, order='priority desc, create_date desc')

            alert_list = []
            for alert in alerts:
                alert_list.append({
                    'id': alert.id,
                    'name': alert.name,
                    'message': alert.message,
                    'type': alert.alert_type,
                    'priority': alert.priority,
                    'state': alert.state,
                    'action_url': alert.action_url,
                    'action_label': alert.action_label,
                    'create_date': alert.create_date.isoformat() if alert.create_date else None,
                    'expiry_date': alert.expiry_date.isoformat() if alert.expiry_date else None,
                })

            return {
                'status': 'success',
                'alerts': alert_list,
                'count': len(alert_list)
            }

        except Exception as e:
            _logger.error(f"Error getting alerts: {str(e)}")
            return {
                'error': str(e),
                'status': 'error'
            }

    @http.route('/dashboard/api/acknowledge_alert', type='json', auth='user', methods=['POST'], csrf=True)
    def api_acknowledge_alert(self, alert_id=None, **kwargs):
        """Acknowledge an alert"""
        try:
            if not alert_id:
                return {'error': 'Alert ID is required', 'status': 'error'}

            alert = request.env['university.dashboard.alert'].sudo().browse(alert_id)

            if not alert.exists():
                return {'error': 'Alert not found', 'status': 'error'}

            alert.action_acknowledge()

            return {
                'status': 'success',
                'message': 'Alert acknowledged successfully'
            }

        except Exception as e:
            _logger.error(f"Error acknowledging alert: {str(e)}")
            return {
                'error': str(e),
                'status': 'error'
            }

    @http.route('/dashboard/api/dismiss_alert', type='json', auth='user', methods=['POST'], csrf=True)
    def api_dismiss_alert(self, alert_id=None, **kwargs):
        """Dismiss an alert"""
        try:
            if not alert_id:
                return {'error': 'Alert ID is required', 'status': 'error'}

            alert = request.env['university.dashboard.alert'].sudo().browse(alert_id)

            if not alert.exists():
                return {'error': 'Alert not found', 'status': 'error'}

            alert.action_dismiss()

            return {
                'status': 'success',
                'message': 'Alert dismissed successfully'
            }

        except Exception as e:
            _logger.error(f"Error dismissing alert: {str(e)}")
            return {
                'error': str(e),
                'status': 'error'
            }

    # ============================================
    # API ENDPOINTS - ANALYTICS
    # ============================================

    @http.route('/dashboard/api/get_analytics', type='json', auth='user', methods=['POST'], csrf=True)
    def api_get_analytics(self, analytics_code=None, date_from=None, date_to=None, filters=None, **kwargs):
        """Get analytics data"""
        try:
            analytics_model = request.env['university.dashboard.analytics'].sudo()

            if not analytics_code:
                return {'error': 'Analytics code is required', 'status': 'error'}

            analytics = analytics_model.search([('code', '=', analytics_code)], limit=1)

            if not analytics.exists():
                return {'error': 'Analytics not found', 'status': 'error'}

            # Check access
            if not analytics.is_public and analytics.group_ids:
                user_groups = request.env.user.groups_id
                if not bool(user_groups & analytics.group_ids):
                    return {'error': 'Access denied', 'status': 'error'}

            # Parse dates
            date_from_obj = datetime.fromisoformat(date_from) if date_from else None
            date_to_obj = datetime.fromisoformat(date_to) if date_to else None

            # Get analytics data
            data = analytics.get_analytics_data(date_from_obj, date_to_obj, filters)

            return {
                'status': 'success',
                'analytics': {
                    'id': analytics.id,
                    'name': analytics.name,
                    'code': analytics.code,
                    'category': analytics.category,
                    'chart_type': analytics.chart_type,
                },
                'data': data
            }

        except Exception as e:
            _logger.error(f"Error getting analytics: {str(e)}")
            return {
                'error': str(e),
                'status': 'error'
            }

    # ============================================
    # API ENDPOINTS - EXPORT
    # ============================================

    @http.route('/dashboard/api/export_dashboard', type='http', auth='user', methods=['POST'], csrf=True)
    def api_export_dashboard(self, format='pdf', dashboard_id=None, **kwargs):
        """Export dashboard"""
        try:
            if not dashboard_id:
                return Response(
                    json.dumps({'error': 'Dashboard ID is required'}),
                    content_type='application/json',
                    status=400
                )

            dashboard = request.env['university.dashboard'].sudo().browse(int(dashboard_id))

            if not dashboard.exists():
                return Response(
                    json.dumps({'error': 'Dashboard not found'}),
                    content_type='application/json',
                    status=404
                )

            if format == 'pdf':
                return self._export_dashboard_pdf(dashboard)
            elif format == 'excel':
                return self._export_dashboard_excel(dashboard)
            elif format == 'csv':
                return self._export_dashboard_csv(dashboard)
            else:
                return Response(
                    json.dumps({'error': 'Invalid format'}),
                    content_type='application/json',
                    status=400
                )

        except Exception as e:
            _logger.error(f"Error exporting dashboard: {str(e)}")
            return Response(
                json.dumps({'error': str(e)}),
                content_type='application/json',
                status=500
            )

    @http.route('/dashboard/api/export_widget', type='http', auth='user', methods=['POST'], csrf=True)
    def api_export_widget(self, widget_id=None, format='png', **kwargs):
        """Export widget"""
        try:
            if not widget_id:
                return Response(
                    json.dumps({'error': 'Widget ID is required'}),
                    content_type='application/json',
                    status=400
                )

            widget = request.env['university.dashboard.widget'].sudo().browse(int(widget_id))

            if not widget.exists():
                return Response(
                    json.dumps({'error': 'Widget not found'}),
                    content_type='application/json',
                    status=404
                )

            # Export logic would go here
            return Response(
                json.dumps({'status': 'success', 'message': 'Widget export not yet implemented'}),
                content_type='application/json'
            )

        except Exception as e:
            _logger.error(f"Error exporting widget: {str(e)}")
            return Response(
                json.dumps({'error': str(e)}),
                content_type='application/json',
                status=500
            )

    # ============================================
    # API ENDPOINTS - SNAPSHOTS
    # ============================================

    @http.route('/dashboard/api/create_snapshot', type='json', auth='user', methods=['POST'], csrf=True)
    def api_create_snapshot(self, dashboard_id=None, snapshot_name=None, **kwargs):
        """Create dashboard snapshot"""
        try:
            if not dashboard_id:
                return {'error': 'Dashboard ID is required', 'status': 'error'}

            snapshot_model = request.env['university.dashboard.snapshot']
            snapshot = snapshot_model.sudo().create_snapshot(dashboard_id, snapshot_name)

            return {
                'status': 'success',
                'snapshot': {
                    'id': snapshot.id,
                    'name': snapshot.name,
                    'snapshot_date': snapshot.snapshot_date.isoformat(),
                }
            }

        except Exception as e:
            _logger.error(f"Error creating snapshot: {str(e)}")
            return {
                'error': str(e),
                'status': 'error'
            }

    @http.route('/dashboard/api/get_snapshots', type='json', auth='user', methods=['POST'], csrf=True)
    def api_get_snapshots(self, dashboard_id=None, limit=10, **kwargs):
        """Get dashboard snapshots"""
        try:
            snapshot_model = request.env['university.dashboard.snapshot'].sudo()

            domain = []
            if dashboard_id:
                domain.append(('dashboard_id', '=', dashboard_id))

            snapshots = snapshot_model.search(domain, limit=limit, order='snapshot_date desc')

            snapshot_list = []
            for snapshot in snapshots:
                snapshot_list.append({
                    'id': snapshot.id,
                    'name': snapshot.name,
                    'dashboard_id': snapshot.dashboard_id.id,
                    'dashboard_name': snapshot.dashboard_id.name,
                    'snapshot_date': snapshot.snapshot_date.isoformat(),
                    'created_by': snapshot.created_by.name,
                })

            return {
                'status': 'success',
                'snapshots': snapshot_list
            }

        except Exception as e:
            _logger.error(f"Error getting snapshots: {str(e)}")
            return {
                'error': str(e),
                'status': 'error'
            }

    # ============================================
    # HELPER METHODS
    # ============================================

    def _get_user_type(self):
        """Get current user type"""
        user = request.env.user
        if user.has_group('university_management.group_university_admin'):
            return 'admin'
        elif user.has_group('university_management.group_university_student'):
            return 'student'
        elif user.has_group('university_management.group_university_faculty'):
            return 'faculty'
        elif user.has_group('university_management.group_university_parent'):
            return 'parent'
        else:
            return 'general'

    def _get_admin_dashboard_values(self):
        """Get admin dashboard values"""
        values = {
            'total_users': request.env['res.users'].sudo().search_count([]),
            'total_students': request.env['student.student'].sudo().search_count([('state', '=', 'active')]),
            'total_departments': request.env['university.department'].sudo().search_count([]),
            'pending_approvals': 0,  # Implement based on your requirements
        }
        return values

    def _get_student_dashboard_values(self):
        """Get student dashboard values"""
        user = request.env.user
        student = request.env['student.student'].sudo().search([('user_id', '=', user.id)], limit=1)

        if not student:
            return {'error': 'Student record not found'}

        values = {
            'student_name': student.name,
            'enrollment_count': len(student.enrollment_ids) if hasattr(student, 'enrollment_ids') else 0,
            'cgpa': student.cgpa if hasattr(student, 'cgpa') else 0.0,
            'attendance_percentage': 85.5,  # Calculate based on attendance records
            'pending_assignments': 3,  # Calculate based on assignments
        }
        return values

    def _get_faculty_dashboard_values(self):
        """Get faculty dashboard values"""
        user = request.env.user
        faculty = request.env['university.faculty'].sudo().search([('user_id', '=', user.id)], limit=1)

        if not faculty:
            return {'error': 'Faculty record not found'}

        values = {
            'faculty_name': faculty.name,
            'courses_teaching': 0,  # Calculate based on course assignments
            'total_students': 0,  # Calculate from enrolled students
            'pending_assignments': 0,  # Calculate pending grading
            'upcoming_classes': 0,  # Calculate from timetable
        }
        return values

    def _get_parent_dashboard_values(self):
        """Get parent dashboard values"""
        user = request.env.user

        # Get student linked to parent
        student = request.env['student.student'].sudo().search([
            '|',
            ('father_id.user_id', '=', user.id),
            ('mother_id.user_id', '=', user.id)
        ], limit=1)

        if not student:
            return {'error': 'Student record not found'}

        values = {
            'student_name': student.name,
            'cgpa': student.cgpa if hasattr(student, 'cgpa') else 0.0,
            'attendance_percentage': 85.5,  # Calculate based on attendance
            'notifications_count': 5,  # Calculate unread messages
        }
        return values

    def _apply_filters(self, dashboard_data, filters):
        """Apply filters to dashboard data"""
        # Implement filter logic based on your requirements
        return dashboard_data

    def _apply_date_range(self, dashboard_data, date_range):
        """Apply date range to dashboard data"""
        # Calculate date range
        today = fields.Date.today()

        if date_range == 'today':
            date_from = today
            date_to = today
        elif date_range == 'week':
            date_from = today - timedelta(days=today.weekday())
            date_to = date_from + timedelta(days=6)
        elif date_range == 'month':
            date_from = today.replace(day=1)
            date_to = date_utils.end_of(today, 'month')
        elif date_range == 'quarter':
            date_from = date_utils.start_of(today, 'quarter')
            date_to = date_utils.end_of(today, 'quarter')
        elif date_range == 'year':
            date_from = today.replace(month=1, day=1)
            date_to = today.replace(month=12, day=31)
        else:
            return dashboard_data

        # Store date range for widget filtering
        dashboard_data['date_range'] = {
            'from': date_from.isoformat(),
            'to': date_to.isoformat(),
        }

        return dashboard_data

    def _export_dashboard_pdf(self, dashboard):
        """Export dashboard as PDF"""
        try:
            # Generate PDF using report engine
            report = request.env.ref('university_management.report_dashboard_pdf')
            pdf_content, content_type = report.sudo()._render_qweb_pdf([dashboard.id])

            filename = f"dashboard_{dashboard.code}_{fields.Date.today()}.pdf"

            return request.make_response(
                pdf_content,
                headers=[
                    ('Content-Type', content_type),
                    ('Content-Disposition', f'attachment; filename="{filename}"'),
                ]
            )

        except Exception as e:
            _logger.error(f"Error generating PDF: {str(e)}")
            return Response(
                json.dumps({'error': str(e)}),
                content_type='application/json',
                status=500
            )

    def _export_dashboard_excel(self, dashboard):
        """Export dashboard as Excel"""
        try:
            # This would require xlsxwriter or similar
            # For now, return a simple message
            return Response(
                json.dumps({'status': 'success', 'message': 'Excel export not yet implemented'}),
                content_type='application/json'
            )

        except Exception as e:
            _logger.error(f"Error generating Excel: {str(e)}")
            return Response(
                json.dumps({'error': str(e)}),
                content_type='application/json',
                status=500
            )

    def _export_dashboard_csv(self, dashboard):
        """Export dashboard as CSV"""
        try:
            # Generate CSV content
            import csv
            import io

            output = io.StringIO()
            writer = csv.writer(output)

            # Write headers
            writer.writerow(['Dashboard', dashboard.name])
            writer.writerow(['Code', dashboard.code])
            writer.writerow(['Generated', fields.Datetime.now().isoformat()])
            writer.writerow([])

            # Write widget data
            writer.writerow(['Widget', 'Type', 'Value'])
            for widget in dashboard.widget_ids:
                writer.writerow([widget.name, widget.widget_type, ''])

            csv_content = output.getvalue()
            output.close()

            filename = f"dashboard_{dashboard.code}_{fields.Date.today()}.csv"

            return request.make_response(
                csv_content,
                headers=[
                    ('Content-Type', 'text/csv'),
                    ('Content-Disposition', f'attachment; filename="{filename}"'),
                ]
            )

        except Exception as e:
            _logger.error(f"Error generating CSV: {str(e)}")
            return Response(
                json.dumps({'error': str(e)}),
                content_type='application/json',
                status=500
            )


class DashboardReportController(http.Controller):
    """Dashboard Report Controller"""

    @http.route('/dashboard/report/<int:dashboard_id>', type='http', auth='user')
    def dashboard_report(self, dashboard_id=None, **kwargs):
        """Generate dashboard report"""
        try:
            if not dashboard_id:
                return request.not_found()

            dashboard = request.env['university.dashboard'].sudo().browse(dashboard_id)

            if not dashboard.exists():
                return request.not_found()

            # Render report template
            return request.render('university_management.dashboard_report_template', {
                'dashboard': dashboard,
                'generate_date': fields.Datetime.now(),
            })

        except Exception as e:
            _logger.error(f"Error generating dashboard report: {str(e)}")
            return request.render('university_management.dashboard_error', {
                'error_message': str(e)
            })

    @http.route('/dashboard/report/print/<int:dashboard_id>', type='http', auth='user')
    def dashboard_report_print(self, dashboard_id=None, **kwargs):
        """Print dashboard report"""
        try:
            if not dashboard_id:
                return request.not_found()

            dashboard = request.env['university.dashboard'].sudo().browse(dashboard_id)

            if not dashboard.exists():
                return request.not_found()

            report = request.env.ref('university_management.report_dashboard_pdf')
            pdf_content, content_type = report.sudo()._render_qweb_pdf([dashboard_id])

            return request.make_response(
                pdf_content,
                headers=[
                    ('Content-Type', content_type),
                    ('Content-Disposition', 'inline'),
                ]
            )

        except Exception as e:
            _logger.error(f"Error printing dashboard: {str(e)}")
            return request.render('university_management.dashboard_error', {
                'error_message': str(e)
            })
