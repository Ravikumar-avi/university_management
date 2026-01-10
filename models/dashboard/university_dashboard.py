# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from datetime import datetime, timedelta
import json
import logging

_logger = logging.getLogger(__name__)


class UniversityDashboard(models.Model):
    """Main Dashboard Configuration"""
    _name = 'university.dashboard'
    _description = 'University Dashboard'
    _order = 'sequence, name'

    name = fields.Char(string='Dashboard Name', required=True)
    code = fields.Char(string='Dashboard Code', required=True)
    sequence = fields.Integer(string='Sequence', default=10)
    description = fields.Text(string='Description')
    user_type = fields.Selection([
        ('admin', 'Administrator'),
        ('student', 'Student'),
        ('faculty', 'Faculty'),
        ('parent', 'Parent'),
        ('hod', 'Head of Department'),
        ('principal', 'Principal'),
        ('librarian', 'Librarian'),
        ('accountant', 'Accountant'),
    ], string='User Type', required=True)

    widget_ids = fields.One2many('university.dashboard.widget', 'dashboard_id', string='Widgets')
    layout = fields.Selection([
        ('grid', 'Grid Layout'),
        ('list', 'List Layout'),
        ('custom', 'Custom Layout'),
    ], string='Layout Type', default='grid')

    is_default = fields.Boolean(string='Default Dashboard')
    active = fields.Boolean(string='Active', default=True)

    # Access Control
    group_ids = fields.Many2many('res.groups', string='Access Groups')

    # Customization
    allow_customization = fields.Boolean(string='Allow User Customization', default=True)
    refresh_interval = fields.Integer(string='Auto Refresh Interval (seconds)', default=300)

    _sql_constraints = [
        ('code_unique', 'UNIQUE(code)', 'Dashboard code must be unique!'),
    ]

    @api.model
    def get_dashboard_data(self, dashboard_code=None):
        """Get dashboard data for current user"""
        user = self.env.user

        # Determine dashboard based on user type
        if not dashboard_code:
            if user.has_group('university_management.group_university_admin'):
                dashboard_code = 'admin_dashboard'
            elif user.has_group('university_management.group_university_student'):
                dashboard_code = 'student_dashboard'
            elif user.has_group('university_management.group_university_faculty'):
                dashboard_code = 'faculty_dashboard'
            elif user.has_group('university_management.group_university_parent'):
                dashboard_code = 'parent_dashboard'
            else:
                dashboard_code = 'general_dashboard'

        dashboard = self.search([('code', '=', dashboard_code), ('active', '=', True)], limit=1)

        if not dashboard:
            return {'error': 'Dashboard not found'}

            # Get widget data
        widgets_data = []
        for widget in dashboard.widget_ids.filtered(lambda w: w.active):
            widget_data = widget.get_widget_data()
            widgets_data.append(widget_data)

        return {
            'dashboard': {
                'name': dashboard.name,
                'code': dashboard.code,
                'layout': dashboard.layout,
            },
            'widgets': widgets_data,
        }


class DashboardWidget(models.Model):
    """Dashboard Widgets"""
    _name = 'university.dashboard.widget'
    _description = 'Dashboard Widget'
    _order = 'sequence, name'

    name = fields.Char(string='Widget Name', required=True)
    code = fields.Char(string='Widget Code', required=True)
    dashboard_id = fields.Many2one('university.dashboard', string='Dashboard', required=True, ondelete='cascade')
    sequence = fields.Integer(string='Sequence', default=10)

    widget_type = fields.Selection([
        ('kpi', 'KPI Card'),
        ('chart', 'Chart'),
        ('table', 'Data Table'),
        ('list', 'List View'),
        ('calendar', 'Calendar'),
        ('progress', 'Progress Bar'),
        ('counter', 'Counter'),
        ('graph', 'Graph'),
        ('pie', 'Pie Chart'),
        ('bar', 'Bar Chart'),
        ('line', 'Line Chart'),
        ('donut', 'Donut Chart'),
        ('custom', 'Custom Widget'),
    ], string='Widget Type', required=True, default='kpi')

    # Layout
    width = fields.Selection([
        ('3', '25% Width (3/12)'),
        ('4', '33% Width (4/12)'),
        ('6', '50% Width (6/12)'),
        ('8', '66% Width (8/12)'),
        ('12', '100% Width (12/12)'),
    ], string='Width', default='6')
    height = fields.Integer(string='Height (pixels)', default=300)

    # Data Source
    model_name = fields.Char(string='Model Name')
    domain = fields.Char(string='Domain', default='[]')
    data_method = fields.Char(string='Data Method', help='Python method to call for data')

    # Display
    icon = fields.Char(string='Icon Class', help='Font Awesome icon class')
    color = fields.Char(string='Color', default='#3498db')
    background_color = fields.Char(string='Background Color')

    # Configuration
    config = fields.Text(string='Widget Configuration (JSON)')

    active = fields.Boolean(string='Active', default=True)

    # Permissions
    group_ids = fields.Many2many('res.groups', string='Visible to Groups')

    def get_widget_data(self):
        """Get widget data"""
        self.ensure_one()

        data = {
            'id': self.id,
            'name': self.name,
            'code': self.code,
            'type': self.widget_type,
            'width': self.width,
            'height': self.height,
            'icon': self.icon,
            'color': self.color,
            'background_color': self.background_color,
            'sequence': self.sequence,
        }

        # Get widget-specific data
        if self.data_method:
            try:
                method = getattr(self, self.data_method)
                widget_data = method()
                data['data'] = widget_data
            except Exception as e:
                _logger.error(f"Error getting widget data for {self.name}: {str(e)}")
                data['data'] = {'error': str(e)}
        elif self.widget_type in ['kpi', 'counter']:
            data['data'] = self._get_kpi_data()
        elif self.widget_type in ['chart', 'bar', 'line', 'pie', 'donut']:
            data['data'] = self._get_chart_data()
        elif self.widget_type == 'table':
            data['data'] = self._get_table_data()
        elif self.widget_type == 'list':
            data['data'] = self._get_list_data()

        return data

    def _get_kpi_data(self):
        """Get KPI data"""
        if not self.model_name:
            return {}

        try:
            domain = eval(self.domain or '[]')
            count = self.env[self.model_name].search_count(domain)
            return {
                'value': count,
                'label': self.name,
            }
        except Exception as e:
            _logger.error(f"Error calculating KPI: {str(e)}")
            return {'value': 0, 'label': self.name, 'error': str(e)}

    def _get_chart_data(self):
        """Get chart data"""
        # Placeholder - implement based on specific requirements
        return {
            'labels': [],
            'datasets': [],
        }

    def _get_table_data(self):
        """Get table data"""
        # Placeholder - implement based on specific requirements
        return {
            'headers': [],
            'rows': [],
        }

    def _get_list_data(self):
        """Get list data"""
        # Placeholder - implement based on specific requirements
        return {
            'items': [],
        }


class DashboardKPI(models.Model):
    """Dashboard KPI Definitions"""
    _name = 'university.dashboard.kpi'
    _description = 'Dashboard KPI'
    _order = 'sequence, name'

    name = fields.Char(string='KPI Name', required=True)
    code = fields.Char(string='KPI Code', required=True)
    sequence = fields.Integer(string='Sequence', default=10)
    description = fields.Text(string='Description')

    category = fields.Selection([
        ('academic', 'Academic'),
        ('financial', 'Financial'),
        ('library', 'Library'),
        ('hostel', 'Hostel'),
        ('placement', 'Placement'),
        ('hr', 'Human Resources'),
        ('general', 'General'),
    ], string='Category', required=True)

    # Calculation
    model_name = fields.Char(string='Model Name')
    domain = fields.Char(string='Domain', default='[]')
    field_name = fields.Char(string='Field to Aggregate')
    aggregation = fields.Selection([
        ('count', 'Count'),
        ('sum', 'Sum'),
        ('avg', 'Average'),
        ('min', 'Minimum'),
        ('max', 'Maximum'),
    ], string='Aggregation Method', default='count')

    # Target & Thresholds
    target_value = fields.Float(string='Target Value')
    warning_threshold = fields.Float(string='Warning Threshold (%)', default=80.0)
    critical_threshold = fields.Float(string='Critical Threshold (%)', default=60.0)

    # Display
    icon = fields.Char(string='Icon')
    color = fields.Char(string='Color', default='#3498db')
    unit = fields.Char(string='Unit', help='e.g., %, Rs, Students')
    prefix = fields.Char(string='Prefix', help='e.g., Rs, $')
    suffix = fields.Char(string='Suffix', help='e.g., %, LPA')

    # Data refresh
    cache_duration = fields.Integer(string='Cache Duration (minutes)', default=15)
    last_calculated = fields.Datetime(string='Last Calculated')
    last_value = fields.Float(string='Last Calculated Value')
    currency_id = fields.Many2one('res.currency', string='Currency',
                                  default=lambda self: self.env.company.currency_id)

    active = fields.Boolean(string='Active', default=True)

    _sql_constraints = [
        ('code_unique', 'UNIQUE(code)', 'KPI code must be unique!'),
    ]

    def calculate_kpi(self):
        """Calculate KPI value"""
        self.ensure_one()

        try:
            if not self.model_name:
                return 0.0

            domain = eval(self.domain or '[]')
            records = self.env[self.model_name].search(domain)

            if self.aggregation == 'count':
                value = len(records)
            elif self.aggregation == 'sum' and self.field_name:
                value = sum(records.mapped(self.field_name))
            elif self.aggregation == 'avg' and self.field_name:
                values = records.mapped(self.field_name)
                value = sum(values) / len(values) if values else 0.0
            elif self.aggregation == 'min' and self.field_name:
                values = records.mapped(self.field_name)
                value = min(values) if values else 0.0
            elif self.aggregation == 'max' and self.field_name:
                values = records.mapped(self.field_name)
                value = max(values) if values else 0.0
            else:
                value = 0.0

                # Update cache
            self.write({
                'last_calculated': fields.Datetime.now(),
                'last_value': value,
            })

            return value

        except Exception as e:
            _logger.error(f"Error calculating KPI {self.name}: {str(e)}")
            return 0.0

    def get_kpi_status(self):
        """Get KPI status (success/warning/critical)"""
        self.ensure_one()

        if not self.target_value:
            return 'neutral'

        percentage = (self.last_value / self.target_value * 100) if self.target_value else 0

        if percentage >= self.warning_threshold:
            return 'success'
        elif percentage >= self.critical_threshold:
            return 'warning'
        else:
            return 'critical'

    @api.model
    def cron_calculate_all_kpis(self):
        """Cron job to calculate all active KPIs"""
        kpis = self.search([('active', '=', True)])
        for kpi in kpis:
            kpi.calculate_kpi()


class DashboardUserPreference(models.Model):
    """User Dashboard Preferences"""
    _name = 'university.dashboard.preference'
    _description = 'Dashboard User Preference'

    user_id = fields.Many2one('res.users', string='User', required=True, ondelete='cascade')
    dashboard_id = fields.Many2one('university.dashboard', string='Dashboard', required=True)

    # Layout customization
    widget_positions = fields.Text(string='Widget Positions (JSON)', help='Custom widget layout')
    visible_widgets = fields.Char(string='Visible Widget IDs (comma-separated)')

    # Display preferences
    theme = fields.Selection([
        ('light', 'Light'),
        ('dark', 'Dark'),
        ('auto', 'Auto'),
    ], string='Theme', default='light')

    refresh_interval = fields.Integer(string='Refresh Interval (seconds)', default=300)

    # Filters
    date_range = fields.Selection([
        ('today', 'Today'),
        ('week', 'This Week'),
        ('month', 'This Month'),
        ('quarter', 'This Quarter'),
        ('year', 'This Year'),
        ('custom', 'Custom Range'),
    ], string='Default Date Range', default='month')

    custom_filters = fields.Text(string='Custom Filters (JSON)')

    _sql_constraints = [
        ('user_dashboard_unique', 'UNIQUE(user_id, dashboard_id)', 'User can have only one preference per dashboard!'),
    ]


class DashboardAnalytics(models.Model):
    """Dashboard Analytics and Reports"""
    _name = 'university.dashboard.analytics'
    _description = 'Dashboard Analytics'

    name = fields.Char(string='Analytics Name', required=True)
    code = fields.Char(string='Code', required=True)
    category = fields.Selection([
        ('student', 'Student Analytics'),
        ('academic', 'Academic Performance'),
        ('financial', 'Financial Analytics'),
        ('hr', 'HR Analytics'),
        ('library', 'Library Analytics'),
        ('placement', 'Placement Analytics'),
        ('attendance', 'Attendance Analytics'),
    ], string='Category', required=True)

    description = fields.Text(string='Description')

    # Data Configuration
    model_name = fields.Char(string='Model Name')
    query = fields.Text(string='SQL Query', help='Custom SQL query for complex analytics')

    # Visualization
    chart_type = fields.Selection([
        ('bar', 'Bar Chart'),
        ('line', 'Line Chart'),
        ('pie', 'Pie Chart'),
        ('donut', 'Donut Chart'),
        ('area', 'Area Chart'),
        ('scatter', 'Scatter Plot'),
        ('radar', 'Radar Chart'),
        ('bubble', 'Bubble Chart'),
    ], string='Chart Type', default='bar')

    # Access
    group_ids = fields.Many2many('res.groups', string='Access Groups')
    is_public = fields.Boolean(string='Public Analytics')

    active = fields.Boolean(string='Active', default=True)

    _sql_constraints = [
        ('code_unique', 'UNIQUE(code)', 'Analytics code must be unique!'),
    ]

    def get_analytics_data(self, date_from=None, date_to=None, filters=None):
        """Get analytics data"""
        self.ensure_one()

        if self.query:
            # Execute custom SQL query
            return self._execute_custom_query(date_from, date_to, filters)
        else:
            # Use model-based approach
            return self._get_model_analytics(date_from, date_to, filters)

    def _execute_custom_query(self, date_from, date_to, filters):
        """Execute custom SQL query"""
        # Implement custom query execution with proper sanitization
        return {}

    def _get_model_analytics(self, date_from, date_to, filters):
        """Get analytics from model"""
        # Implement model-based analytics
        return {}


class DashboardSnapshot(models.Model):
    """Dashboard Snapshots for Historical Data"""
    _name = 'university.dashboard.snapshot'
    _description = 'Dashboard Snapshot'
    _order = 'snapshot_date desc'

    name = fields.Char(string='Snapshot Name', required=True)
    snapshot_date = fields.Datetime(string='Snapshot Date', required=True, default=fields.Datetime.now)
    dashboard_id = fields.Many2one('university.dashboard', string='Dashboard')

    # Snapshot Data
    kpi_data = fields.Text(string='KPI Data (JSON)')
    analytics_data = fields.Text(string='Analytics Data (JSON)')

    # Metadata
    created_by = fields.Many2one('res.users', string='Created By', default=lambda self: self.env.user)
    notes = fields.Text(string='Notes')

    @api.model
    def create_snapshot(self, dashboard_id):
        """Create a snapshot of current dashboard state"""
        dashboard = self.env['university.dashboard'].browse(dashboard_id)

        if not dashboard.exists():
            raise ValidationError(_('Dashboard not found'))

            # Collect KPI data
        kpis = self.env['university.dashboard.kpi'].search([('active', '=', True)])
        kpi_data = {}
        for kpi in kpis:
            kpi_data[kpi.code] = {
                'name': kpi.name,
                'value': kpi.calculate_kpi(),
                'unit': kpi.unit,
            }

            # Create snapshot
        snapshot = self.create({
            'name': f'{dashboard.name} - {fields.Datetime.now()}',
            'dashboard_id': dashboard_id,
            'kpi_data': json.dumps(kpi_data),
            'snapshot_date': fields.Datetime.now(),
        })

        return snapshot

    @api.model
    def cron_create_daily_snapshots(self):
        """Cron job to create daily snapshots"""
        dashboards = self.env['university.dashboard'].search([('active', '=', True)])
        for dashboard in dashboards:
            self.create_snapshot(dashboard.id)


class DashboardAlert(models.Model):
    """Dashboard Alerts and Notifications"""
    _name = 'university.dashboard.alert'
    _description = 'Dashboard Alert'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char(string='Alert Title', required=True)
    alert_type = fields.Selection([
        ('info', 'Information'),
        ('warning', 'Warning'),
        ('error', 'Error'),
        ('success', 'Success'),
    ], string='Alert Type', required=True, default='info', tracking=True)

    message = fields.Text(string='Alert Message', required=True)

    # Trigger
    kpi_id = fields.Many2one('university.dashboard.kpi', string='Related KPI')
    threshold_breached = fields.Boolean(string='Threshold Breached')

    # Recipients
    user_ids = fields.Many2many('res.users', string='Notify Users')
    group_ids = fields.Many2many('res.groups', string='Notify Groups')

    # Status
    state = fields.Selection([
        ('new', 'New'),
        ('acknowledged', 'Acknowledged'),
        ('resolved', 'Resolved'),
        ('dismissed', 'Dismissed'),
    ], string='Status', default='new', tracking=True)

    acknowledged_by = fields.Many2one('res.users', string='Acknowledged By')
    acknowledged_date = fields.Datetime(string='Acknowledged Date')

    resolved_by = fields.Many2one('res.users', string='Resolved By')
    resolved_date = fields.Datetime(string='Resolved Date')

    # Actions
    action_url = fields.Char(string='Action URL')
    action_label = fields.Char(string='Action Label')

    # Expiry
    expiry_date = fields.Datetime(string='Expiry Date')
    is_expired = fields.Boolean(string='Is Expired', compute='_compute_is_expired', store=True)

    active = fields.Boolean(string='Active', default=True)

    @api.depends('expiry_date')
    def _compute_is_expired(self):
        now = fields.Datetime.now()
        for alert in self:
            alert.is_expired = alert.expiry_date and alert.expiry_date < now

    def action_acknowledge(self):
        """Acknowledge alert"""
        self.write({
            'state': 'acknowledged',
            'acknowledged_by': self.env.user.id,
            'acknowledged_date': fields.Datetime.now(),
        })

    def action_resolve(self):
        """Resolve alert"""
        self.write({
            'state': 'resolved',
            'resolved_by': self.env.user.id,
            'resolved_date': fields.Datetime.now(),
        })

    def action_dismiss(self):
        """Dismiss alert"""
        self.write({'state': 'dismissed'})

    @api.model
    def create_alert(self, title, message, alert_type='info', users=None, groups=None):
        """Helper method to create alerts"""
        vals = {
            'name': title,
            'message': message,
            'alert_type': alert_type,
        }

        if users:
            vals['user_ids'] = [(6, 0, users)]
        if groups:
            vals['group_ids'] = [(6, 0, groups)]

        return self.create(vals)