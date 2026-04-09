# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from datetime import date
import logging

_logger = logging.getLogger(__name__)


class UniversityDashboard(models.TransientModel):
    _name = 'university.dashboard'
    _description = 'University Dashboard Data Provider'

    @api.model
    def get_dashboard_data(self):
        return {
            'overview': self._get_overview_data(),
            'students': self._get_students_data(),
            'faculty': self._get_faculty_data(),
            'fees': self._get_fees_data(),
            'exams': self._get_exams_data(),
            'hostel': self._get_hostel_data(),
            'library': self._get_library_data(),
            'recent_admissions': self._get_recent_admissions(),
            'recent_payments': self._get_recent_payments(),
            'department_stats': self._get_department_stats(),
            'fee_monthly': self._get_fee_monthly_trend(),
            'semester_admissions': self._get_semester_admissions(),
            'assets': self._get_asset_dummy_data(),
        }

    def _student_active_domain(self):
        """Central place for student live/active states."""
        return [('state', 'in', ['active', 'enrolled', 'admitted'])]

    def _get_overview_data(self):
        env = self.env
        today = date.today()

        total_students = 0
        try:
            total_students = env['student.student'].search_count(self._student_active_domain())
        except Exception:
            pass

        total_faculty = 0
        try:
            total_faculty = env['faculty.faculty'].search_count([('active', '=', True)])
        except Exception:
            pass

        avg_cgpa = 0.0
        try:
            results = env['examination.result'].search([('state', '=', 'published')])
            if results:
                cgpa_vals = [r.grade_point for r in results if r.grade_point]
                avg_cgpa = sum(cgpa_vals) / len(cgpa_vals) if cgpa_vals else 0.0
        except Exception:
            pass

        month_start = today.replace(day=1)
        new_admissions_this_month = 0
        try:
            new_admissions_this_month = env['student.admission'].search_count([
                ('state', '=', 'approved'),
                ('application_date', '>=', month_start.strftime('%Y-%m-%d')),
            ])
        except Exception:
            pass

        students_placed = 0
        total_eligible = 0
        active_placement_drives = 0
        recruiting_companies = 0
        highest_package = 'N/A'
        try:
            students_placed = env['placement.offer'].search_count([('state', '=', 'accepted')])
            total_eligible = env['student.student'].search_count(
                self._student_active_domain()
            )
            active_placement_drives = env['placement.drive'].search_count([
                ('state', 'in', ['registration_open', 'registration_closed', 'scheduled', 'ongoing'])
            ])
            recruiting_companies = env['placement.company'].search_count([('active', '=', True)])
        except Exception:
            pass

        placement_rate = round((students_placed / total_eligible * 100) if total_eligible else 0, 1)

        total_vehicles = 0
        active_routes = 0
        transport_students = 0
        try:
            total_vehicles = env['transport.vehicle'].search_count([('active', '=', True)])
            active_routes = env['transport.route'].search_count([('active', '=', True)])
            transport_students = env['transport.allocation'].search_count([('state', '=', 'active')])
        except Exception:
            pass

        return {
            'total_students': total_students,
            'total_faculty': total_faculty,
            'avg_cgpa': round(avg_cgpa, 2),
            'new_admissions_this_month': new_admissions_this_month,
            'placement_rate': placement_rate,
            'students_placed': students_placed,
            'active_placement_drives': active_placement_drives,
            'recruiting_companies': recruiting_companies,
            'highest_package': highest_package,
            'total_vehicles': total_vehicles,
            'active_routes': active_routes,
            'transport_students': transport_students,
        }

    def _get_students_data(self):
        env = self.env
        today = date.today()
        year_start = today.replace(month=1, day=1)

        total_active = 0
        new_this_year = 0
        pending_admissions = 0
        try:
            total_active = env['student.student'].search_count(self._student_active_domain())
            new_this_year = env['student.admission'].search_count([
                ('state', 'in', ['approved', 'admitted']),
                ('application_date', '>=', year_start.strftime('%Y-%m-%d')),
            ])
            pending_admissions = env['student.admission'].search_count([
                ('state', 'in', ['submitted', 'under_review'])
            ])
        except Exception:
            pass

        low_attendance = 0
        try:
            students = env['student.student'].search(self._student_active_domain())
            for student in students:
                att_records = env['student.attendance'].search([
                    ('student_id', '=', student.id),
                    ('date', '>=', year_start.strftime('%Y-%m-%d')),
                ])
                if att_records:
                    present = len(att_records.filtered(lambda r: r.state == 'present'))
                    pct = present / len(att_records) * 100
                    if pct < 75:
                        low_attendance += 1
        except Exception:
            pass

        program_distribution = []
        try:
            programs = env['university.program'].search([])
            total = max(total_active, 1)
            for prog in programs:
                count = env['student.student'].search_count(
                    [('program_id', '=', prog.id)] + self._student_active_domain()
                )
                if count:
                    program_distribution.append({
                        'name': prog.name,
                        'count': count,
                        'percentage': round(count / total * 100, 1),
                    })
        except Exception:
            pass

        return {
            'total_active': total_active,
            'new_this_year': new_this_year,
            'pending_admissions': pending_admissions,
            'low_attendance': low_attendance,
            'program_distribution': program_distribution,
        }

    def _get_faculty_data(self):
        env = self.env
        today = date.today()
        today_str = today.strftime('%Y-%m-%d')

        total = 0
        present_today = 0
        on_leave = 0
        avg_rating = 0.0

        try:
            total = env['faculty.faculty'].search_count([('active', '=', True)])
        except Exception:
            pass

        try:
            present_today = env['faculty.attendance'].search_count([
                ('date', '=', today_str),
                ('state', '=', 'present'),
            ])
        except Exception:
            pass

        try:
            on_leave = env['faculty.leave'].search_count([
                ('date_from', '<=', today_str),
                ('date_to', '>=', today_str),
                ('state', '=', 'approved'),
            ])
        except Exception:
            pass

        try:
            evals = env['faculty.evaluation'].search([('state', '=', 'done')])
            if evals:
                avg_rating = sum(e.overall_rating for e in evals if e.overall_rating) / len(evals)
        except Exception:
            pass

        return {
            'total': total,
            'present_today': present_today,
            'on_leave': on_leave,
            'avg_rating': round(avg_rating, 1),
        }

    def _get_fees_data(self):
        env = self.env
        today = date.today()
        month_start = today.replace(day=1)

        # ── Core collection figures ────────────────────────────────────
        total_collected = 0.0
        monthly_collection = 0.0
        today_collection = 0.0
        total_pending = 0.0
        late_payments = 0
        transaction_count_month = 0

        # ── Accounting figures ─────────────────────────────────────────
        invoices_count = 0
        journal_entries = 0
        posted_payments = 0
        pending_verification = 0
        scholarships_applied = 0

        # ── New: extended analytics ────────────────────────────────────
        by_program = []
        payment_mode_breakdown = []
        reconciliation_stats = {
            'fully_reconciled': 0,
            'partially_reconciled': 0,
            'not_reconciled': 0,
        }
        student_ledger_stats = {
            'total_students_with_dues': 0,
            'total_outstanding_fmt': '0',
            'avg_outstanding_fmt': '0',
        }

        try:
            # Total ever collected
            all_payments = env['fee.payment'].search([('state', 'in', ['paid', 'partial'])])
            total_collected = sum(all_payments.mapped('total_amount'))

            # This month's collection
            monthly_payments = env['fee.payment'].search([
                ('state', 'in', ['paid', 'partial']),
                ('payment_date', '>=', month_start.strftime('%Y-%m-%d')),
            ])
            monthly_collection = sum(monthly_payments.mapped('total_amount'))
            transaction_count_month = len(monthly_payments)

            # Today's collection  (PDF Finance Dashboard – "Today's Fee Collection")
            today_payments = env['fee.payment'].search([
                ('state', 'in', ['paid', 'partial']),
                ('payment_date', '=', today.strftime('%Y-%m-%d')),
            ])
            today_collection = sum(today_payments.mapped('total_amount'))

            # Outstanding / pending  (PDF Student Ledger – "Outstanding Balance")
            pending_payments = env['fee.payment'].search([
                ('state', 'in', ['draft', 'pending', 'verified', 'invoiced'])
            ])
            total_pending = sum(pending_payments.mapped('total_amount'))

            # Late payments
            fp_fields = env['fee.payment'].fields_get(allfields=['is_late_payment'])
            if 'is_late_payment' in fp_fields:
                late_payments = env['fee.payment'].search_count([
                    ('is_late_payment', '=', True),
                    ('state', 'not in', ['cancelled']),
                ])

            # Accounting counters
            invoices_count = env['fee.payment'].search_count([('invoice_id', '!=', False)])
            journal_entries = env['fee.payment'].search_count([('account_move_id', '!=', False)])
            posted_payments = env['fee.payment'].search_count([('state', 'in', ['paid', 'partial'])])
            pending_verification = env['fee.payment'].search_count([('state', '=', 'pending')])

            # ── Payment Mode Breakdown  (PDF section 12 – "Payment Mode Analysis")
            # Uses the existing computed field `payment_method` on fee.payment
            all_settled = env['fee.payment'].search([('state', 'in', ['paid', 'partial'])])
            mode_totals = {}
            for pmt in all_settled:
                mode_label = pmt.payment_method or 'Unspecified'
                if mode_label not in mode_totals:
                    mode_totals[mode_label] = {'count': 0, 'amount': 0.0}
                mode_totals[mode_label]['count'] += 1
                mode_totals[mode_label]['amount'] += pmt.total_amount

            for label, vals in sorted(mode_totals.items(), key=lambda x: -x[1]['amount']):
                payment_mode_breakdown.append({
                    'label': label,
                    'count': vals['count'],
                    'amount': vals['amount'],
                    'amount_fmt': self._format_amount(vals['amount']),
                })

            # ── Bank Reconciliation Stats  (PDF section 8 – "Bank Reconciliation")
            # Uses the existing `reconciliation_status` computed field
            reconciliation_stats['fully_reconciled'] = env['fee.payment'].search_count([
                ('state', 'in', ['paid', 'partial']),
                ('reconciliation_status', '=', 'fully_reconciled'),
            ])
            reconciliation_stats['partially_reconciled'] = env['fee.payment'].search_count([
                ('state', 'in', ['paid', 'partial']),
                ('reconciliation_status', '=', 'partially_reconciled'),
            ])
            reconciliation_stats['not_reconciled'] = env['fee.payment'].search_count([
                ('state', 'in', ['paid', 'partial']),
                ('reconciliation_status', '=', 'not_reconciled'),
            ])

            # ── Student Ledger Stats  (PDF section 4 – "Student Ledger System")
            # Uses existing `outstanding_amount` and `amount_paid` computed fields
            pending_recs = env['fee.payment'].search([
                ('state', 'in', ['draft', 'pending', 'verified', 'invoiced'])
            ])
            student_ids_with_dues = list(set(pending_recs.mapped('student_id').ids))
            total_outstanding = sum(pending_recs.mapped('outstanding_amount'))
            avg_outstanding = (
                total_outstanding / len(student_ids_with_dues)
                if student_ids_with_dues else 0.0
            )
            student_ledger_stats = {
                'total_students_with_dues': len(student_ids_with_dues),
                'total_outstanding_fmt': self._format_amount(total_outstanding),
                'avg_outstanding_fmt': self._format_amount(avg_outstanding),
            }

        except Exception as e:
            _logger.warning("Fee data fetch error: %s", e)

        try:
            scholarships_applied = env['scholarship.application'].search_count([('state', '=', 'approved')])
        except Exception:
            pass

        # ── Fee Collection by Program ──────────────────────────────────
        try:
            programs = env['university.program'].search([])
            for prog in programs:
                prog_students = env['student.student'].search(
                    [('program_id', '=', prog.id)] + self._student_active_domain()
                )
                if not prog_students:
                    continue

                student_ids = prog_students.ids

                payments = env['fee.payment'].search([
                    ('student_id', 'in', student_ids),
                    ('state', 'in', ['paid', 'partial']),
                ])
                collected = sum(payments.mapped('total_amount'))

                pending = env['fee.payment'].search([
                    ('student_id', 'in', student_ids),
                    ('state', 'in', ['draft', 'pending', 'verified', 'invoiced']),
                ])
                pending_amt = sum(pending.mapped('total_amount'))

                total = collected + pending_amt
                pct = round(collected / total * 100, 1) if total else 0

                by_program.append({
                    'name': prog.name,
                    'students': len(prog_students),
                    'collected': collected,
                    'collected_fmt': self._format_amount(collected),
                    'pending': pending_amt,
                    'pending_fmt': self._format_amount(pending_amt),
                    'collection_pct': pct,
                })
        except Exception as e:
            _logger.warning("Fee by_program fetch error: %s", e)

        return {
            # Existing fields – untouched
            'total_collected': total_collected,
            'monthly_collection': monthly_collection,
            'total_pending': total_pending,
            'late_payments': late_payments,
            'invoices_count': invoices_count,
            'journal_entries': journal_entries,
            'posted_payments': posted_payments,
            'pending_verification': pending_verification,
            'scholarships_applied': scholarships_applied,
            'by_program': by_program,
            # New fields from PDF
            'today_collection': today_collection,
            'transaction_count_month': transaction_count_month,
            'payment_mode_breakdown': payment_mode_breakdown,
            'reconciliation_stats': reconciliation_stats,
            'student_ledger_stats': student_ledger_stats,
        }

    def _get_exams_data(self):
        env = self.env
        active_exams = 0
        hall_tickets = 0
        results_published = 0
        revaluations = 0

        try:
            active_exams = env['examination.examination'].search_count([])
        except Exception:
            pass
        try:
            hall_tickets = env['examination.hall.ticket'].search_count([
                ('state', 'in', ['generated', 'issued', 'printed'])
            ])
        except Exception:
            pass
        try:
            results_published = env['examination.result'].search_count([('state', '=', 'published')])
        except Exception:
            pass
        try:
            revaluations = env['examination.revaluation'].search_count([
                ('state', 'in', ['submitted', 'under_review', 'revaluation_in_progress', 'completed'])
            ])
        except Exception:
            pass

        return {
            'active_exams': active_exams,
            'hall_tickets': hall_tickets,
            'results_published': results_published,
            'revaluations': revaluations,
        }

    def _get_hostel_data(self):
        env = self.env
        total_rooms = 0
        occupied_rooms = 0
        pending_complaints = 0

        try:
            total_rooms = env['hostel.room'].search_count([('active', '=', True)])
        except Exception:
            pass
        try:
            occupied_rooms = env['hostel.allocation'].search_count([
                ('state', 'in', ['active', 'allocated', 'occupied'])
            ])
        except Exception:
            pass
        try:
            pending_complaints = env['hostel.complaint'].search_count([
                ('state', 'in', ['open', 'in_progress'])
            ])
        except Exception:
            pass

        occupancy_rate = round(occupied_rooms / total_rooms * 100, 1) if total_rooms else 0

        return {
            'total_rooms': total_rooms,
            'occupied_rooms': occupied_rooms,
            'pending_complaints': pending_complaints,
            'occupancy_rate': occupancy_rate,
        }

    def _get_library_data(self):
        env = self.env
        total_books = 0
        books_issued = 0
        overdue = 0
        fines_collected = 0.0

        try:
            total_books = env['library.book'].search_count([])
        except Exception:
            pass
        try:
            books_issued = env['library.issue'].search_count([('state', '=', 'issued')])
        except Exception:
            pass
        try:
            overdue = env['library.issue'].search_count([('state', '=', 'overdue')])
        except Exception:
            pass
        try:
            fines = env['library.fine'].search([('state', '=', 'paid')])
            fines_collected = sum(fines.mapped('amount'))
        except Exception:
            pass

        return {
            'total_books': total_books,
            'books_issued': books_issued,
            'overdue': overdue,
            'fines_collected': fines_collected,
        }

    def _get_recent_admissions(self):
        result = []
        try:
            admissions = self.env['student.admission'].search(
                [('state', 'not in', ['cancelled'])],
                order='application_date desc',
                limit=8,
            )
            state_selection = dict(
                admissions.fields_get(['state'])['state']['selection']
            ) if admissions else {}

            for adm in admissions:
                result.append({
                    'id': adm.id,
                    'name': adm.applicant_name or 'Unknown',
                    'program': adm.program_id.name if adm.program_id else '',
                    'date': adm.application_date.strftime('%d %b %Y') if adm.application_date else '',
                    'state': adm.state,
                    'state_label': state_selection.get(adm.state, adm.state),
                })
        except Exception as e:
            _logger.warning("Recent admissions fetch error: %s", e)

        return result

    def _get_recent_payments(self):
        result = []
        try:
            payments = self.env['fee.payment'].search(
                [('state', 'not in', ['cancelled'])],
                order='payment_date desc',
                limit=8,
            )

            for pmt in payments:
                result.append({
                    'id': pmt.id,
                    'student': pmt.student_id.name if pmt.student_id else 'Unknown',
                    'amount': self._format_amount(pmt.total_amount),
                    'method': pmt.payment_method or '',
                    'state': pmt.state,
                })
        except Exception as e:
            _logger.warning("Recent payments fetch error: %s", e)

        return result

    def _get_department_stats(self):
        result = []
        try:
            departments = self.env['university.department'].search([])
            for dept in departments:
                students = self.env['student.student'].search_count(
                    [('department_id', '=', dept.id)] + self._student_active_domain()
                )
                if not students:
                    continue

                btech = self.env['student.student'].search_count(
                    [
                        ('department_id', '=', dept.id),
                        '|',
                        ('program_id.name', 'ilike', 'B.Tech'),
                        ('program_id.name', 'ilike', 'Bachelor of Technology'),
                    ] + self._student_active_domain()
                )

                placed = 0
                try:
                    dept_student_ids = self.env['student.student'].search([
                        ('department_id', '=', dept.id),
                    ]).ids
                    placed = self.env['placement.offer'].search_count([
                        ('student_id', 'in', dept_student_ids),
                        ('state', '=', 'accepted'),
                    ])
                except Exception:
                    pass

                placement_rate = round(placed / students * 100, 1) if students else 0

                avg_cgpa = 0.0
                try:
                    results = self.env['examination.result'].search([
                        ('student_id.department_id', '=', dept.id),
                        ('state', '=', 'published'),
                    ])
                    if results:
                        vals = [r.grade_point for r in results if r.grade_point]
                        avg_cgpa = round(sum(vals) / len(vals), 1) if vals else 0.0
                except Exception:
                    pass

                result.append({
                    'name': dept.name,
                    'students': students,
                    'btech_students': btech,
                    'placement_rate': placement_rate,
                    'avg_cgpa': avg_cgpa,
                })
        except Exception as e:
            _logger.warning("Department stats fetch error: %s", e)

        return result[:6]

    def _get_fee_monthly_trend(self):
        from calendar import monthrange
        today = date.today()
        result = []
        monthly_vals = []

        try:
            for i in range(7, -1, -1):
                year = today.year
                month = today.month - i
                while month <= 0:
                    month += 12
                    year -= 1
                _, last_day = monthrange(year, month)
                start = date(year, month, 1).strftime('%Y-%m-%d')
                end = date(year, month, last_day).strftime('%Y-%m-%d')
                payments = self.env['fee.payment'].search([
                    ('state', 'in', ['paid', 'partial']),
                    ('payment_date', '>=', start),
                    ('payment_date', '<=', end),
                ])
                total = sum(payments.mapped('total_amount'))
                label = date(year, month, 1).strftime('%b')
                monthly_vals.append({'label': label, 'value': total})
        except Exception as e:
            _logger.warning("Fee monthly trend fetch error: %s", e)

        max_val = max((mv['value'] for mv in monthly_vals), default=1) or 1
        for mv in monthly_vals:
            result.append({
                'label': mv['label'],
                'value': mv['value'],
                'height': round(mv['value'] / max_val * 100),
            })

        return result

    def _get_semester_admissions(self):
        result = []
        vals = []

        try:
            semesters = self.env['university.semester'].search([], order='name', limit=8)
            for sem in semesters:
                count = self.env['student.registration'].search_count([
                    ('semester_id', '=', sem.id),
                ])
                vals.append({'label': sem.name, 'value': count})
        except Exception as e:
            _logger.warning("Semester admissions fetch error: %s", e)

        max_val = max((v['value'] for v in vals), default=1) or 1
        for v in vals:
            result.append({
                'label': v['label'],
                'value': v['value'],
                'height': round(v['value'] / max_val * 100),
            })

        return result

    def _get_asset_dummy_data(self):
        return {
            'total_assets': 25,
            'active_assets': 20,
            'under_maintenance': 2,
            'disposed_assets': 1,
            'pending_requests': 4,
            'transfers_this_month': 4,
            'assets_under_warranty': 7,
            'unverified_assets': 18,
            'total_purchase_value': 3885000.0,
            'total_book_value': 3128000.0,
            'by_category': [
                {'name': 'IT Equipment', 'count': 9},
                {'name': 'Lab Equipment', 'count': 5},
                {'name': 'Furniture', 'count': 3},
                {'name': 'Vehicles', 'count': 2},
                {'name': 'Electrical Equipment', 'count': 4},
                {'name': 'Sports Equipment', 'count': 2},
            ],
            'by_condition': [
                {'name': 'Good', 'count': 17},
                {'name': 'Fair', 'count': 5},
                {'name': 'Poor', 'count': 2},
                {'name': 'Condemned', 'count': 1},
            ],
            'recent_maintenance': [
                {
                    'id': -1,
                    'name': 'MAINT/2024/00005',
                    'asset': 'Daikin Split AC 1.5 Ton (Set of 5)',
                    'date': '2024-04-01',
                    'state': 'assigned',
                    'type': 'amc',
                },
                {
                    'id': -2,
                    'name': 'MAINT/2024/00004',
                    'asset': 'Digital Oscilloscope 100MHz',
                    'date': '2024-03-20',
                    'state': 'completed',
                    'type': 'calibration',
                },
                {
                    'id': -3,
                    'name': 'MAINT/2024/00003',
                    'asset': 'Hydraulic Press 20 Ton',
                    'date': '2024-02-20',
                    'state': 'in_progress',
                    'type': 'corrective',
                },
                {
                    'id': -4,
                    'name': 'MAINT/2024/00002',
                    'asset': 'Kirloskar DG Set 62.5 KVA',
                    'date': '2024-01-12',
                    'state': 'completed',
                    'type': 'preventive',
                },
                {
                    'id': -5,
                    'name': 'MAINT/2024/00001',
                    'asset': 'Epson Multimedia Projector',
                    'date': '2024-03-17',
                    'state': 'completed',
                    'type': 'corrective',
                },
            ],
            'recent_requests': [
                {
                    'id': -11,
                    'name': 'AREQ/2024/0004',
                    'requester': 'Administrator',
                    'category': 'IT Equipment',
                    'date': '2024-04-03',
                    'state': 'approved',
                },
                {
                    'id': -12,
                    'name': 'AREQ/2024/0003',
                    'requester': 'Administrator',
                    'category': 'Lab Equipment',
                    'date': '2024-04-05',
                    'state': 'draft',
                },
                {
                    'id': -13,
                    'name': 'AREQ/2024/0002',
                    'requester': 'Administrator',
                    'category': 'Furniture',
                    'date': '2024-03-25',
                    'state': 'pending_purchase',
                },
                {
                    'id': -14,
                    'name': 'AREQ/2024/0001',
                    'requester': 'Administrator',
                    'category': 'IT Equipment',
                    'date': '2024-04-01',
                    'state': 'submitted',
                },
            ],
            'recent_transfers': [
                {
                    'id': -21,
                    'name': 'TRF/2024/00004',
                    'asset': 'Samsung Smart Board 75 Inch',
                    'from_dept': 'Electronics and Communication Engg',
                    'to_dept': 'Computer Science and Engineering',
                    'date': '2024-04-01',
                    'state': 'completed',
                },
                {
                    'id': -22,
                    'name': 'TRF/2024/00003',
                    'asset': 'Dell Laptop Core i7',
                    'from_dept': 'Computer Science and Engineering',
                    'to_dept': 'Computer Science and Engineering',
                    'date': '2024-03-20',
                    'state': 'pending',
                },
                {
                    'id': -23,
                    'name': 'TRF/2024/00002',
                    'asset': 'Lenovo ThinkPad — Faculty Laptop',
                    'from_dept': 'Computer Science and Engineering',
                    'to_dept': 'Computer Science and Engineering',
                    'date': '2024-02-10',
                    'state': 'completed',
                },
                {
                    'id': -24,
                    'name': 'TRF/2024/00001',
                    'asset': 'HP Desktop PC Core i5',
                    'from_dept': 'Administration',
                    'to_dept': 'Administration',
                    'date': '2024-01-15',
                    'state': 'completed',
                },
            ],
        }

    @staticmethod
    def _format_amount(amount):
        if not amount:
            return '0'
        if amount >= 100000:
            return f"{amount / 100000:.1f}L"
        if amount >= 1000:
            return f"{amount / 1000:.1f}K"
        return str(round(amount))