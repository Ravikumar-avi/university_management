# -*- coding: utf-8 -*-
{
    'name': 'University Management System',
    'version': '18.0.1.0.1',
    'category': 'Education',
    'summary': 'Complete University/College ERP - Student, Faculty, Exam, Fee, Library, Hostel, Placement',
    'description': """
        Complete University Management System for Indian Universities/Colleges
        ===========================================================================

        Features:
        ---------
        * Student Admission & Registration Management
        * Academic Program, Department, Course Management
        * Faculty & Staff Management
        * Fee Collection & Payment Tracking
        * Examination, Hall Ticket & Result Management
        * Library Management with Book Issue/Return
        * Hostel & Mess Management
        * Transport & Bus Route Management
        * Campus Placement & Training
        * Student Projects & Internships
        * Events, Hackathons & Competitions
        * Alumni Management
        * Timetable & Class Schedule
        * Attendance Tracking (Student & Faculty)
        * Parent Portal Access
        * Automated Fee Reminders
        * ID Card & Hall Ticket Generation
        * Marksheet & Certificate Generation
        * Comprehensive Dashboard & Reports

        Integration with Odoo Core Modules:
        -----------------------------------
        * HR Module - Faculty linked to employees
        * Accounting - Fee payments & invoicing
        * Sale - Fee structure as products
        * Project - Student projects
        * Stock - Library inventory
        * Purchase - Hostel/Mess supplies
        * Contacts - Companies, Alumni, Parents
        * Calendar - Events & Timetables
        * Survey - Student feedback
        * Website - Student/Parent portals
        * Mail - Chatter on all models
    """,

    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'license': 'LGPL-3',

    'depends': [
        'base',
        'mail',
        'web',
        'board',
        'portal',
        'hr',
        'account',
        'sale_management',
        'stock',
        'purchase',
        'contacts',
        'calendar',
        'survey',
        'website',
        'project',
    ],

    'data': [
        # Security
        'security/security.xml',
        'security/ir.model.access.csv',

        # Data
        'data/sequence.xml',
        'data/email_templates.xml',
        'data/sms_templates.xml',
        'data/automated_actions.xml',
        'data/default_data.xml',
        'data/indian_states_data.xml',

        # Views - Academic
        'views/academic/university_batch_views.xml',
        'views/academic/university_program_views.xml',
        'views/academic/university_department_views.xml',
        'views/academic/university_course_views.xml',
        'views/academic/university_subject_views.xml',
        'views/academic/university_semester_views.xml',
        'views/academic/university_academic_year_views.xml',
        'views/academic/university_syllabus_views.xml',
        'views/academic/university_timetable_views.xml',

        # Views - Fee
        'views/fee/fee_structure_views.xml',
        'views/fee/fee_installment_views.xml',
        'views/fee/fee_discount_views.xml',
        'views/fee/scholarship_views.xml',
        'views/fee/fee_payment_views.xml',
        'views/fee/fee_reminder_views.xml',

        # Views - Examination
        'views/examination/exam_timetable_views.xml',
        'views/examination/hall_ticket_views.xml',
        'views/examination/exam_result_views.xml',
        'views/examination/exam_seating_views.xml',
        'views/examination/grade_system_views.xml',
        'views/examination/examination_views.xml',
        'views/examination/marksheet_views.xml',
        'views/examination/revaluation_views.xml',
        'views/examination/exam_evaluation_views.xml',

        # Views - Student
        'views/student/student_attendance_views.xml',
        'views/student/student_document_views.xml',
        'views/student/student_parent_views.xml',
        'views/student/student_admission_views.xml',
        'views/student/student_registration_views.xml',
        'views/student/student_id_card_views.xml',
        'views/student/student_discipline_views.xml',
        'views/student/student_views.xml',

        # Views - Faculty
        'views/faculty/faculty_views.xml',
        'views/faculty/faculty_attendance_views.xml',
        'views/faculty/faculty_salary_views.xml',
        'views/faculty/faculty_designation_views.xml',
        'views/faculty/faculty_leave_views.xml',
        'views/faculty/faculty_workload_views.xml',
        'views/faculty/faculty_evaluation_views.xml',

        # Views - Library
        'views/library/library_book_views.xml',
        'views/library/library_issue_views.xml',
        'views/library/library_member_views.xml',
        'views/library/library_fine_views.xml',
        'views/library/library_category_views.xml',
        'views/library/library_reservation_views.xml',

        # Views - Hostel
        'views/hostel/hostel_views.xml',
        'views/hostel/hostel_room_views.xml',
        'views/hostel/hostel_allocation_views.xml',
        'views/hostel/hostel_attendance_views.xml',
        'views/hostel/hostel_visitor_views.xml',
        'views/hostel/hostel_complaint_views.xml',
        'views/hostel/hostel_mess_views.xml',
        'views/hostel/mess_item_views.xml',
        'views/hostel/mess_menu_views.xml',
        'views/hostel/mess_attendance_views.xml',
        'views/hostel/mess_feedback_views.xml',

        # Views - Transport
        'views/transport/transport_route_views.xml',
        'views/transport/transport_vehicle_views.xml',
        'views/transport/transport_driver_views.xml',
        'views/transport/transport_allocation_views.xml',
        'views/transport/transport_stop_views.xml',
        'views/transport/transport_fee_views.xml',

        # Views - Placement
        'views/placement/placement_drive_views.xml',
        'views/placement/placement_company_views.xml',
        'views/placement/placement_application_views.xml',
        'views/placement/placement_offer_views.xml',
        'views/placement/placement_training_views.xml',
        'views/placement/placement_coordinator_views.xml',

        # Views - Alumni
        'views/alumni/alumni_views.xml',
        'views/alumni/alumni_event_views.xml',
        'views/alumni/alumni_donation_views.xml',
        'views/alumni/alumni_achievement_views.xml',

        # Views - Project
        'views/project/student_project_views.xml',
        'views/project/project_guide_views.xml',
        'views/project/project_evaluation_views.xml',
        'views/project/project_presentation_views.xml',

        # Views - Internship
        'views/internship/internship_views.xml',
        'views/internship/internship_company_views.xml',
        'views/internship/internship_report_views.xml',
        'views/internship/internship_evaluation_views.xml',

        # Views - Events
        'views/events/university_event_views.xml',
        'views/events/event_registration_views.xml',
        'views/events/event_sponsor_views.xml',
        'views/events/hackathon_views.xml',
        'views/events/hackathon_team_views.xml',
        'views/events/hackathon_judge_views.xml',
        'views/events/hackathon_winner_views.xml',

        # Views - Timetable
        'views/timetable/class_timetable_views.xml',
        'views/timetable/faculty_timetable_views.xml',
        'views/timetable/lab_schedule_views.xml',
        'views/timetable/timetable_substitution_views.xml',

        # Views - Dashboard
        'views/dashboard/university_dashboard_views.xml',

        # Wizards (BEFORE reports)
        'wizard/bulk_admission_wizard_views.xml',
        'wizard/bulk_id_card_wizard_views.xml',
        'wizard/bulk_registration_wizard_views.xml',
        'wizard/fee_reminder_wizard_views.xml',
        'wizard/generate_hall_ticket_wizard_views.xml',
        'wizard/promote_student_wizard_views.xml',
        'wizard/publish_result_wizard_views.xml',
        'wizard/attendance_report_wizard_views.xml',
        'wizard/placement_report_wizard_views.xml',

        # Reports
        'report/student_id_card.xml',
        'report/hall_ticket_report.xml',
        'report/fee_receipt.xml',
        'report/marksheet_report.xml',
        'report/salary_slip_report.xml',
        'report/student_report.xml',
        'report/attendance_report.xml',
        'report/placement_report.xml',

        'templates/mains/admission_templates.xml',
        'templates/mains/library_templates.xml',
        'templates/mains/program_templates.xml',
        'templates/mains/department_templates.xml',
        'templates/mains/faculty_templates.xml',
        'templates/mains/placement_templates.xml',
        'templates/mains/document_templates.xml',
        'templates/mains/event_templates.xml',
        'templates/mains/contact_templates.xml',
        'templates/mains/about_templates.xml',
        'templates/mains/home_templates.xml',


        'templates/studentportal/studentdashboard_templates.xml',
        'templates/parentportal/parentdashboard_templates.xml',
        'templates/facultyportal/facultydashboard_templates.xml',

        # Menu
        'views/menu_views.xml',
    ],

    'demo': [
        # 'demo/demo_data.xml',
    ],

    'assets': {
        'web.assets_backend': [
            # Then load CSS
            # 'university_management/static/src/css/dashboard.css',
            # 'university_management/static/src/css/custom.css',

            # Then load JavaScript in correct order
            # 'university_management/static/src/js/charts.js',
            # 'university_management/static/src/js/custom_widgets.js',
            # 'university_management/static/src/js/dashboard.js',

            # Finally load templates
            # 'university_management/static/src/xml/dashboard_templates.xml',
        ],
        'web.assets_frontend': [
            # 'university_management/static/src/css/student_portal.css',
            # 'university_management/static/src/xml/portal_templates.xml',
        ],
    },

    'images': [
        'static/description/banner.png',
        'static/description/icon.png',
    ],

    'installable': True,
    'application': True,
    'auto_install': False,
    'price': 999.00,
    'currency': 'USD',
}

