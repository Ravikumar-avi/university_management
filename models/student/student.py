# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import re


class Student(models.Model):
    _name = 'student.student'
    _description = 'University Student Master'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']
    _inherits = {'res.partner': 'partner_id'}
    _order = 'registration_number'

    # Partner (inherited from res.partner)
    partner_id = fields.Many2one('res.partner', string='Related Partner',
                                 required=True, ondelete='cascade', auto_join=True)

    # Student Details
    student_code = fields.Char(string='Student Code', readonly=True, copy=False, default='/')
    registration_number = fields.Char(string='Registration Number', readonly=True,
                                      copy=False, tracking=True)
    admission_number = fields.Char(string='Admission Number', tracking=True)

    # Personal Information
    student_photo = fields.Binary(string='Photo', attachment=True)
    date_of_birth = fields.Date(string='Date of Birth', required=True, tracking=True)
    age = fields.Integer(string='Age', compute='_compute_age')
    gender = fields.Selection([
        ('male', 'Male'),
        ('female', 'Female'),
        ('other', 'Other'),
    ], string='Gender', required=True, tracking=True)
    blood_group = fields.Selection([
        ('a+', 'A+'), ('a-', 'A-'),
        ('b+', 'B+'), ('b-', 'B-'),
        ('o+', 'O+'), ('o-', 'O-'),
        ('ab+', 'AB+'), ('ab-', 'AB-'),
    ], string='Blood Group')

    # Contact
    personal_email = fields.Char(string='Personal Email')
    personal_mobile = fields.Char(string='Personal Mobile')
    emergency_contact = fields.Char(string='Emergency Contact')
    emergency_contact_name = fields.Char(string='Emergency Contact Name')

    # Address
    current_address = fields.Text(string='Current Address')
    permanent_address = fields.Text(string='Permanent Address')

    # Academic Details
    program_id = fields.Many2one('university.program', string='Program',
                                 required=True, tracking=True, index=True)
    department_id = fields.Many2one('university.department', string='Department',
                                    required=True, tracking=True, index=True)
    batch_id = fields.Many2one('university.batch', string='Batch', tracking=True)
    current_semester = fields.Integer(string='Current Semester', default=1)
    academic_year_id = fields.Many2one('university.academic.year', string='Academic Year')

    # Admission
    admission_id = fields.Many2one('student.admission', string='Admission Record')
    admission_date = fields.Date(string='Admission Date', tracking=True)
    admission_category = fields.Selection([
        ('general', 'General'),
        ('obc', 'OBC'),
        ('sc', 'SC'),
        ('st', 'ST'),
        ('ews', 'EWS'),
    ], string='Category')

    # Previous Education
    previous_qualification = fields.Char(string='Previous Qualification')
    previous_institution = fields.Char(string='Previous Institution')
    previous_percentage = fields.Float(string='Previous Percentage')
    previous_year = fields.Integer(string='Year of Passing')

    # Courses
    enrolled_course_ids = fields.Many2many('university.course', 'student_course_rel',
                                           'student_id', 'course_id',
                                           string='Enrolled Courses')

    # Registration
    registration_ids = fields.One2many('student.registration', 'student_id',
                                       string='Course Registrations')

    # Attendance
    attendance_ids = fields.One2many('student.attendance', 'student_id',
                                     string='Attendance Records')
    attendance_percentage = fields.Float(string='Attendance %', compute='_compute_attendance', store=True)

    # Documents
    document_ids = fields.One2many('student.document', 'student_id', string='Documents')
    documents_verified = fields.Boolean(string='Documents Verified', compute='_compute_documents', store=True)

    # ID Card
    id_card_ids = fields.One2many('student.id.card', 'student_id', string='ID Cards')

    # Parents/Guardians
    parent_ids = fields.One2many('student.parent', 'student_id', string='Parents/Guardians')

    # Discipline
    discipline_ids = fields.One2many('student.discipline', 'student_id',
                                     string='Discipline Records')

    # Fee
    fee_payment_ids = fields.One2many('fee.payment', 'student_id', string='Fee Payments')
    total_fee_due = fields.Monetary(string='Total Fee Due', compute='_compute_fees', store=True)
    total_fee_paid = fields.Monetary(string='Total Fee Paid', compute='_compute_fees')

    currency_id = fields.Many2one('res.currency', string='Currency',
                                  default=lambda self: self.env.company.currency_id)

    # Examination
    exam_result_ids = fields.One2many('examination.result', 'student_id', string='Exam Results')
    cgpa = fields.Float(string='CGPA', compute='_compute_academic_performance', store=True)
    sgpa = fields.Float(string='SGPA (Current)', compute='_compute_academic_performance')

    # Hostel
    hostel_allocation_id = fields.Many2one('hostel.allocation', string='Hostel Allocation')
    is_hosteller = fields.Boolean(string='Hosteller')

    # Transport
    transport_allocation_id = fields.Many2one('transport.allocation',
                                              string='Transport Allocation')
    uses_transport = fields.Boolean(string='Uses Transport')

    # Library
    library_member_id = fields.Many2one('library.member', string='Library Member')

    # Portal Access
    user_id = fields.Many2one('res.users', string='Portal User')

    # Status
    state = fields.Selection([
        ('draft', 'Draft'),
        ('admitted', 'Admitted'),
        ('enrolled', 'Enrolled'),
        ('active', 'Active'),
        ('suspended', 'Suspended'),
        ('graduated', 'Graduated'),
        ('dropped', 'Dropped Out'),
        ('expelled', 'Expelled'),
    ], string='Status', default='draft', tracking=True)

    active = fields.Boolean(string='Active', default=True)

    # Nationality
    nationality_id = fields.Many2one('res.country', string='Nationality')
    is_international = fields.Boolean(string='International Student')

    # Religion & Caste
    religion = fields.Char(string='Religion')
    caste = fields.Char(string='Caste')

    # Bank Details (for scholarships)
    bank_account_number = fields.Char(string='Bank Account Number')
    bank_name = fields.Char(string='Bank Name')
    bank_branch = fields.Char(string='Branch')
    ifsc_code = fields.Char(string='IFSC Code')

    # Government IDs
    aadhar_number = fields.Char(string='Aadhar Number')
    pan_number = fields.Char(string='PAN Number')

    _sql_constraints = [
        ('registration_number_unique', 'unique(registration_number)',
         'Registration Number must be unique!'),
        ('aadhar_unique', 'unique(aadhar_number)',
         'Aadhar Number must be unique!'),
    ]

    @api.model
    def create(self, vals):
        if vals.get('student_code', '/') == '/':
            vals['student_code'] = self.env['ir.sequence'].next_by_code('student.student') or '/'
        if vals.get('registration_number', '/') == '/':
            vals['registration_number'] = self.env['ir.sequence'].next_by_code('student.registration') or '/'

        # Create partner if not exists
        if not vals.get('partner_id'):
            partner_vals = {
                'name': vals.get('name'),
                'email': vals.get('email'),
                'phone': vals.get('mobile'),
                'is_company': False,
                'customer_rank': 0,
            }
            partner = self.env['res.partner'].create(partner_vals)
            vals['partner_id'] = partner.id

        return super(Student, self).create(vals)

    @api.depends('date_of_birth')
    def _compute_age(self):
        from datetime import date
        for record in self:
            if record.date_of_birth:
                today = date.today()
                record.age = today.year - record.date_of_birth.year - (
                        (today.month, today.day) < (record.date_of_birth.month, record.date_of_birth.day)
                )
            else:
                record.age = 0

    @api.depends('attendance_ids')
    def _compute_attendance(self):
        for record in self:
            total = len(record.attendance_ids)
            present = len(record.attendance_ids.filtered(lambda a: a.state == 'present'))
            record.attendance_percentage = (present / total * 100) if total > 0 else 0.0

    @api.depends('document_ids', 'document_ids.is_verified')
    def _compute_documents(self):
        for record in self:
            if record.document_ids:
                record.documents_verified = all(doc.is_verified for doc in record.document_ids)
            else:
                record.documents_verified = False

    @api.depends('fee_payment_ids')
    def _compute_fees(self):
        for record in self:
            # This should be linked to fee.structure
            record.total_fee_paid = sum(record.fee_payment_ids.filtered(
                lambda p: p.state == 'paid').mapped('amount'))
            record.total_fee_due = 0.0  # Calculate from fee structure

    @api.depends('exam_result_ids')
    def _compute_academic_performance(self):
        for record in self:
            results = record.exam_result_ids.filtered(lambda r: r.state == 'published')
            if results:
                record.cgpa = sum(results.mapped('grade_point')) / len(results)
                current_sem_results = results.filtered(
                    lambda r: r.semester_id.semester_number == record.current_semester
                )
                if current_sem_results:
                    record.sgpa = sum(current_sem_results.mapped('grade_point')) / len(current_sem_results)
                else:
                    record.sgpa = 0.0
            else:
                record.cgpa = 0.0
                record.sgpa = 0.0

    @api.constrains('aadhar_number')
    def _check_aadhar(self):
        for record in self:
            if record.aadhar_number:
                if not re.match(r'^\d{12}$', record.aadhar_number):
                    raise ValidationError(_('Aadhar number must be 12 digits!'))

    def action_admit(self):
        self.write({'state': 'admitted', 'admission_date': fields.Date.today()})

    def action_enroll(self):
        self.write({'state': 'enrolled'})

    def action_activate(self):
        self.write({'state': 'active'})

    def action_suspend(self):
        self.write({'state': 'suspended'})

    def action_graduate(self):
        self.write({'state': 'graduated'})

    def action_create_portal_user(self):
        """Create portal user for student"""
        if not self.user_id and self.email:
            user = self.env['res.users'].create({
                'name': self.name,
                'login': self.email,
                'email': self.email,
                'partner_id': self.partner_id.id,
                'groups_id': [(6, 0, [self.env.ref('base.group_portal').id])],
            })
            self.user_id = user.id

    def action_student_attendance(self):
        """Open student attendance records"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Student Attendance',
            'res_model': 'student.attendance',
            'view_mode': 'list,kanban,form,calendar,pivot,graph',
            'domain': [('student_id', '=', self.id)],
            'context': {
                'default_student_id': self.id,
                'search_default_student_id': self.id,
            },
        }

    def action_fee_payment(self):
        """Open fee payment records"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Fee Payments',
            'res_model': 'fee.payment',
            'view_mode': 'list,form',
            'domain': [('student_id', '=', self.id)],
            'context': {'default_student_id': self.id},
        }

    def action_exam_result(self):
        """Open exam result records"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Exam Results',
            'res_model': 'examination.result',
            'view_mode': 'list,form',
            'domain': [('student_id', '=', self.id)],
            'context': {'default_student_id': self.id},
        }

    def action_student_document(self):
        """Open student document records"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Documents',
            'res_model': 'student.document',
            'view_mode': 'list,form',
            'domain': [('student_id', '=', self.id)],
            'context': {'default_student_id': self.id},
        }

