# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import base64
import xlrd
import csv
import io
import logging

_logger = logging.getLogger(__name__)


class BulkAdmissionWizard(models.TransientModel):
    """
    Wizard for bulk student admission import from Excel/CSV
    """
    _name = 'bulk.admission.wizard'
    _description = 'Bulk Admission Wizard'

    import_file = fields.Binary(string='Import File', required=True, help='Upload Excel (.xls, .xlsx) or CSV file')
    filename = fields.Char(string='Filename')
    file_type = fields.Selection([
        ('excel', 'Excel'),
        ('csv', 'CSV')
    ], string='File Type', default='excel', required=True)

    program_id = fields.Many2one('university.program', string='Program', required=True)
    department_id = fields.Many2one('university.department', string='Department', required=True)
    batch_id = fields.Many2one('university.batch', string='Batch', required=True)
    academic_year_id = fields.Many2one('university.academic.year', string='Academic Year', required=True)
    admission_date = fields.Date(string='Admission Date', default=fields.Date.today, required=True)

    auto_generate_registration = fields.Boolean(string='Auto Generate Registration Number', default=True)
    auto_approve = fields.Boolean(string='Auto Approve Admissions', default=False)
    send_email = fields.Boolean(string='Send Email Notification', default=True)
    send_sms = fields.Boolean(string='Send SMS Notification', default=False)

    sample_file_url = fields.Char(string='Sample File',
                                  default='/university_management/static/src/samples/bulk_admission_sample.xlsx',
                                  readonly=True)

    def action_download_sample(self):
        """Download sample template file"""
        return {
            'type': 'ir.actions.act_url',
            'url': self.sample_file_url,
            'target': 'new',
        }

    def action_import_admissions(self):
        """Process bulk admission import"""
        self.ensure_one()

        if not self.import_file:
            raise UserError(_('Please upload a file to import.'))

        try:
            if self.file_type == 'excel':
                records = self._parse_excel_file()
            else:
                records = self._parse_csv_file()

            if not records:
                raise UserError(_('No valid records found in the file.'))

            # Process admissions
            created_admissions = self._create_admissions(records)

            # Show result
            return self._show_result(created_admissions)

        except Exception as e:
            _logger.error(f"Bulk admission import error: {str(e)}")
            raise UserError(_('Import failed: %s') % str(e))

    def _parse_excel_file(self):
        """Parse Excel file and return list of records"""
        file_data = base64.b64decode(self.import_file)
        workbook = xlrd.open_workbook(file_contents=file_data)
        sheet = workbook.sheet_by_index(0)

        records = []
        headers = [str(cell.value).strip().lower() for cell in sheet.row(0)]

        for row_idx in range(1, sheet.nrows):
            row_data = {}
            for col_idx, header in enumerate(headers):
                cell = sheet.cell(row_idx, col_idx)
                row_data[header] = cell.value

            if row_data.get('name') or row_data.get('student_name'):
                records.append(row_data)

        return records

    def _parse_csv_file(self):
        """Parse CSV file and return list of records"""
        file_data = base64.b64decode(self.import_file)
        csv_data = io.StringIO(file_data.decode('utf-8'))
        csv_reader = csv.DictReader(csv_data)

        records = []
        for row in csv_reader:
            # Convert keys to lowercase
            row_data = {k.strip().lower(): v for k, v in row.items()}
            if row_data.get('name') or row_data.get('student_name'):
                records.append(row_data)

        return records

    def _create_admissions(self, records):
        """Create admission records from parsed data"""
        Admission = self.env['student.admission']
        Student = self.env['student.student']

        created_admissions = []
        errors = []

        for idx, record in enumerate(records, start=2):
            try:
                # Prepare admission data
                admission_vals = self._prepare_admission_vals(record)

                # Create admission
                admission = Admission.create(admission_vals)
                created_admissions.append(admission)

                # Auto approve if enabled
                if self.auto_approve:
                    admission.action_approve()

                # Send notifications
                if self.send_email and admission.student_id.email:
                    self._send_admission_email(admission)

                if self.send_sms and admission.student_id.mobile:
                    self._send_admission_sms(admission)

            except Exception as e:
                error_msg = f"Row {idx}: {str(e)}"
                errors.append(error_msg)
                _logger.error(error_msg)

        if errors:
            # Log errors but continue
            error_log = "\n".join(errors)
            _logger.warning(f"Bulk admission errors:\n{error_log}")

        return created_admissions

    def _prepare_admission_vals(self, record):
        """Prepare admission values from record data"""
        # Get or create student
        student_vals = {
            'name': record.get('name') or record.get('student_name'),
            'email': record.get('email'),
            'mobile': record.get('mobile') or record.get('phone'),
            'date_of_birth': self._parse_date(record.get('date_of_birth') or record.get('dob')),
            'gender': self._parse_gender(record.get('gender')),
            'blood_group': record.get('blood_group'),
            'aadhar_number': record.get('aadhar_number') or record.get('aadhar'),
            'address': record.get('address'),
            'city': record.get('city'),
            'state': record.get('state'),
            'pincode': record.get('pincode') or record.get('pin_code'),
            'father_name': record.get('father_name'),
            'mother_name': record.get('mother_name'),
            'guardian_mobile': record.get('guardian_mobile') or record.get('parent_mobile'),
        }

        student = self.env['student.student'].create(student_vals)

        # Prepare admission values
        admission_vals = {
            'student_id': student.id,
            'program_id': self.program_id.id,
            'department_id': self.department_id.id,
            'batch_id': self.batch_id.id,
            'academic_year_id': self.academic_year_id.id,
            'admission_date': self.admission_date,
            'admission_type': record.get('admission_type', 'regular'),
            'category': record.get('category', 'general'),
            'quota': record.get('quota', 'merit'),
            'previous_school': record.get('previous_school'),
            'previous_percentage': float(record.get('previous_percentage', 0)),
        }

        return admission_vals

    def _parse_date(self, date_str):
        """Parse date from various formats"""
        if not date_str:
            return False

        try:
            # Try different date formats
            from dateutil import parser
            return parser.parse(str(date_str)).date()
        except:
            return False

    def _parse_gender(self, gender_str):
        """Parse gender value"""
        if not gender_str:
            return 'other'

        gender_lower = str(gender_str).lower().strip()
        if gender_lower in ['m', 'male']:
            return 'male'
        elif gender_lower in ['f', 'female']:
            return 'female'
        else:
            return 'other'

    def _send_admission_email(self, admission):
        """Send admission confirmation email"""
        template = self.env.ref('university_management.email_template_admission_confirmation',
                                raise_if_not_found=False)
        if template:
            template.send_mail(admission.id, force_send=True)

    def _send_admission_sms(self, admission):
        """Send admission confirmation SMS"""
        # Implement SMS sending logic
        pass

    def _show_result(self, created_admissions):
        """Show import result to user"""
        return {
            'name': _('Bulk Admission Result'),
            'type': 'ir.actions.act_window',
            'res_model': 'student.admission',
            'view_mode': 'list,form',
            'domain': [('id', 'in', created_admissions.ids)],
            'context': {'create': False},
            'target': 'current',
        }
