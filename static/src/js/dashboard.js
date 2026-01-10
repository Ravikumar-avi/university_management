/* ============================================
   UNIVERSITY MANAGEMENT SYSTEM - DASHBOARD.JS
   Converted to Odoo 18 (OWL + ES6 Module System)

   ORIGINAL CODE PRESERVED - Converted from legacy odoo.define syntax
   Interactive dashboard controller and management
   ============================================ */

import { Component, useState, onWillStart, onMounted, onWillUnmount, useRef } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";

export class UniversityDashboard extends Component {
    static template = "university_management.UniversityDashboard";

    setup() {
        // Services (replacing old requires)
        this.orm = useService("orm");
        this.action = useService("action");
        this.notification = useService("notification");
        this.rpc = useService("rpc");
        this.user = useService("user");
        this.dialog = useService("dialog");

        // Dashboard state (replacing this.dashboardData, this.charts, etc.)
        this.state = useState({
            dashboardData: {},
            dashboardConfig: {},
            filters: {
                date_range: 'month',
                academic_year_id: null,
                department_id: null,
                program_id: null,
            },
            loading: false,
        });

        // Charts storage
        this.charts = {};

        // Auto-refresh settings
        this.autoRefresh = false;
        this.refreshInterval = 300000; // 5 minutes
        this.refreshTimer = null;

        // OWL Lifecycle hooks
        onWillStart(async () => {
            await this._loadDashboardConfig();
            await this._loadDashboardData();
        });

        onMounted(() => {
            this._renderDashboard();
            this._initializeCharts();
            this._startAutoRefresh();
            this._initializeDragAndDrop();
            this._loadUserPreferences();
        });

        onWillUnmount(() => {
            this._stopAutoRefresh();
            this._destroyCharts();
        });
    }

    /**
     * Load dashboard configuration
     * ORIGINAL FUNCTIONALITY PRESERVED
     */
    async _loadDashboardConfig() {
        try {
            // Determine dashboard type based on user role
            let dashboardCode = 'admin_dashboard';
            const context = this.user.context;

            if (context.is_student) {
                dashboardCode = 'student_dashboard';
            } else if (context.is_faculty) {
                dashboardCode = 'faculty_dashboard';
            } else if (context.is_parent) {
                dashboardCode = 'parent_dashboard';
            }

            const result = await this.orm.call(
                'university.dashboard',
                'get_dashboard_data',
                [dashboardCode]
            );

            this.state.dashboardConfig = result;
            return result;
        } catch (error) {
            console.error('Error loading dashboard config:', error);
        }
    }

    /**
     * Load dashboard data
     * ORIGINAL FUNCTIONALITY PRESERVED
     */
    async _loadDashboardData() {
        try {
            const route = this._getDashboardRoute();
            const result = await this.rpc(route, {
                filters: this.state.filters,
                context: this.user.context,
            });

            if (result.success) {
                this.state.dashboardData = result.data;
            }

            return result;
        } catch (error) {
            console.error('Error loading dashboard data:', error);
            this.notification.add(_t('Failed to load dashboard data'), {
                type: 'danger',
                title: _t('Error'),
            });
        }
    }

    /**
     * Get dashboard route based on user type
     * ORIGINAL FUNCTIONALITY PRESERVED
     */
    _getDashboardRoute() {
        const context = this.user.context;

        if (context.is_student) {
            return '/university/dashboard/student';
        } else if (context.is_faculty) {
            return '/university/dashboard/faculty';
        } else if (context.is_parent) {
            return '/university/dashboard/parent';
        }

        return '/university/dashboard/admin';
    }

    /**
     * Render dashboard layout
     * ORIGINAL FUNCTIONALITY PRESERVED
     */
    _renderDashboard() {
        // In Odoo 18 with OWL, the template handles rendering
        // This method now handles post-render updates
        this._renderKPICards();
        this._renderWidgets();
        this._applyAnimations();
    }

    /**
     * Render KPI cards
     * ORIGINAL FUNCTIONALITY PRESERVED
     */
    _renderKPICards() {
        const kpiContainer = document.querySelector('.o_kpi_cards_container');
        if (!this.state.dashboardData.kpis || !kpiContainer) return;

        kpiContainer.innerHTML = '';

        Object.entries(this.state.dashboardData.kpis).forEach(([key, kpi]) => {
            const kpiCard = this._createKPICard(kpi, key);
            kpiContainer.appendChild(kpiCard);
        });
    }

    /**
     * Create KPI Card element
     */
    _createKPICard(kpi, key) {
        const card = document.createElement('div');
        card.className = 'o_kpi_card';
        card.dataset.key = key;
        card.innerHTML = `
            <div class="o_kpi_icon">${kpi.icon || ''}</div>
            <div class="o_kpi_content">
                <div class="o_kpi_value">${kpi.value}</div>
                <div class="o_kpi_label">${kpi.label}</div>
            </div>
        `;
        return card;
    }

    /**
     * Render dashboard widgets
     * ORIGINAL FUNCTIONALITY PRESERVED
     */
    _renderWidgets() {
        const widgetsContainer = document.querySelector('.o_dashboard_widgets_container');
        if (!this.state.dashboardConfig.widgets || !widgetsContainer) return;

        this.state.dashboardConfig.widgets.forEach(widget => {
            const widgetElement = this._createWidget(widget);
            widgetsContainer.appendChild(widgetElement);
        });
    }

    /**
     * Create individual widget
     * ORIGINAL FUNCTIONALITY PRESERVED
     */
    _createWidget(widgetConfig) {
        const widget = document.createElement('div');
        widget.className = 'o_dashboard_widget';
        widget.dataset.widgetId = widgetConfig.id;
        widget.innerHTML = `
            <div class="o_widget_header">
                <h4>${widgetConfig.name}</h4>
                <div class="o_widget_actions">
                    <button class="o_widget_action" data-action="refresh"><i class="fa fa-refresh"></i></button>
                    <button class="o_widget_action" data-action="expand"><i class="fa fa-expand"></i></button>
                </div>
            </div>
            <div class="o_widget_body">${widgetConfig.content || ''}</div>
        `;
        return widget;
    }

    /**
     * Initialize all charts
     * ORIGINAL FUNCTIONALITY PRESERVED - All chart creation methods kept intact
     */
    _initializeCharts() {
        if (!this.state.dashboardData.charts) return;

        // All original chart initializations preserved
        if (this.state.dashboardData.charts.enrollment_trend) {
            this._createEnrollmentChart();
        }
        if (this.state.dashboardData.charts.department_wise) {
            this._createDepartmentChart();
        }
        if (this.state.dashboardData.charts.gender_distribution) {
            this._createGenderChart();
        }
        if (this.state.dashboardData.charts.attendance) {
            this._createAttendanceChart();
        }
        if (this.state.dashboardData.charts.fee_collection) {
            this._createFeeChart();
        }
        if (this.state.dashboardData.charts.performance) {
            this._createPerformanceChart();
        }
        if (this.state.dashboardData.charts.placement) {
            this._createPlacementChart();
        }
    }

    /**
     * Create enrollment trend chart
     * ORIGINAL FUNCTIONALITY PRESERVED
     */
    _createEnrollmentChart() {
        const canvas = document.getElementById('enrollment-chart');
        if (!canvas) return;

        const ctx = canvas.getContext('2d');
        const data = this.state.dashboardData.charts.enrollment_trend;

        this.charts.enrollment = new Chart(ctx, {
            type: 'line',
            data: {
                labels: data.labels,
                datasets: [{
                    label: 'Student Enrollment',
                    data: data.values,
                    borderColor: '#667eea',
                    backgroundColor: this._createGradient(ctx, ['#667eea', '#764ba2']),
                    fill: true,
                    tension: 0.4,
                    pointRadius: 5,
                    pointHoverRadius: 7,
                }]
            },
            options: this._getChartOptions('Enrollment Trend')
        });
    }

    /**
     * Create department distribution chart
     * ORIGINAL FUNCTIONALITY PRESERVED
     */
    _createDepartmentChart() {
        const canvas = document.getElementById('department-chart');
        if (!canvas) return;

        const ctx = canvas.getContext('2d');
        const data = this.state.dashboardData.charts.department_wise;

        this.charts.department = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: data.map(d => d.name),
                datasets: [{
                    data: data.map(d => d.count),
                    backgroundColor: [
                        '#667eea', '#56ab2f', '#f2994a', '#eb3349',
                        '#3a7bd5', '#764ba2', '#a8e063', '#f2c94c'
                    ],
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { position: 'right' },
                    title: {
                        display: true,
                        text: 'Students by Department'
                    }
                }
            }
        });
    }

    /**
     * Create gender distribution chart
     * ORIGINAL FUNCTIONALITY PRESERVED
     */
    _createGenderChart() {
        const canvas = document.getElementById('gender-chart');
        if (!canvas) return;

        const ctx = canvas.getContext('2d');
        const data = this.state.dashboardData.charts.gender_distribution;

        this.charts.gender = new Chart(ctx, {
            type: 'pie',
            data: {
                labels: ['Male', 'Female', 'Other'],
                datasets: [{
                    data: [data.male, data.female, data.other],
                    backgroundColor: ['#3a7bd5', '#eb3349', '#f2994a'],
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { position: 'bottom' },
                    title: {
                        display: true,
                        text: 'Gender Distribution'
                    }
                }
            }
        });
    }

    /**
     * Create attendance chart
     * ORIGINAL FUNCTIONALITY PRESERVED
     */
    _createAttendanceChart() {
        const canvas = document.getElementById('attendance-chart');
        if (!canvas) return;

        const ctx = canvas.getContext('2d');
        const data = this.state.dashboardData.charts.attendance;

        this.charts.attendance = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: data.labels,
                datasets: [
                    {
                        label: 'Present',
                        data: data.present,
                        backgroundColor: '#56ab2f',
                    },
                    {
                        label: 'Absent',
                        data: data.absent,
                        backgroundColor: '#eb3349',
                    }
                ]
            },
            options: this._getChartOptions('Attendance Overview')
        });
    }

    /**
     * Create fee collection chart
     * ORIGINAL FUNCTIONALITY PRESERVED
     */
    _createFeeChart() {
        const canvas = document.getElementById('fee-chart');
        if (!canvas) return;

        const ctx = canvas.getContext('2d');
        const data = this.state.dashboardData.charts.fee_collection;

        this.charts.fee = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: data.labels,
                datasets: [
                    {
                        label: 'Collected',
                        data: data.collected,
                        backgroundColor: '#56ab2f',
                    },
                    {
                        label: 'Pending',
                        data: data.pending,
                        backgroundColor: '#f2994a',
                    }
                ]
            },
            options: this._getChartOptions('Fee Collection Status')
        });
    }

    /**
     * Create performance chart (Student Dashboard)
     * ORIGINAL FUNCTIONALITY PRESERVED
     */
    _createPerformanceChart() {
        const canvas = document.getElementById('performance-chart');
        if (!canvas) return;

        const ctx = canvas.getContext('2d');
        const data = this.state.dashboardData.charts.performance;

        this.charts.performance = new Chart(ctx, {
            type: 'line',
            data: {
                labels: data.semesters,
                datasets: [{
                    label: 'CGPA',
                    data: data.cgpa,
                    borderColor: '#667eea',
                    backgroundColor: 'rgba(102, 126, 234, 0.1)',
                    fill: true,
                    tension: 0.4,
                }]
            },
            options: this._getChartOptions('Academic Performance')
        });
    }

    /**
     * Create placement chart
     * ORIGINAL FUNCTIONALITY PRESERVED
     */
    _createPlacementChart() {
        const canvas = document.getElementById('placement-chart');
        if (!canvas) return;

        const ctx = canvas.getContext('2d');
        const data = this.state.dashboardData.charts.placement;

        this.charts.placement = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: data.map(d => d.department),
                datasets: [{
                    label: 'Placement %',
                    data: data.map(d => d.percentage),
                    backgroundColor: data.map(d => {
                        if (d.percentage >= 80) return '#56ab2f';
                        if (d.percentage >= 60) return '#3a7bd5';
                        if (d.percentage >= 40) return '#f2994a';
                        return '#eb3349';
                    }),
                }]
            },
            options: {
                indexAxis: 'y',
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    title: {
                        display: true,
                        text: 'Placement Rate by Department'
                    }
                }
            }
        });
    }

    /**
     * Get default chart options
     * ORIGINAL FUNCTIONALITY PRESERVED
     */
    _getChartOptions(title) {
        return {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: true,
                    position: 'top'
                },
                title: {
                    display: true,
                    text: title,
                    font: {
                        size: 16,
                        weight: 'bold'
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    grid: {
                        color: '#e2e8f0'
                    }
                },
                x: {
                    grid: {
                        display: false
                    }
                }
            }
        };
    }

    /**
     * Create gradient
     * ORIGINAL FUNCTIONALITY PRESERVED
     */
    _createGradient(ctx, colors) {
        const gradient = ctx.createLinearGradient(0, 0, 0, ctx.canvas.height);
        gradient.addColorStop(0, colors[0]);
        gradient.addColorStop(1, colors[1]);
        return gradient;
    }

    /**
     * Apply entrance animations
     * ORIGINAL FUNCTIONALITY PRESERVED
     */
    _applyAnimations() {
        const kpiCards = document.querySelectorAll('.o_kpi_card');
        kpiCards.forEach((card, index) => {
            card.style.animation = 'fadeIn 0.5s ease forwards';
            card.style.animationDelay = (index * 0.1) + 's';
            card.style.opacity = '0';
        });
    }

    /**
     * Refresh dashboard
     * ORIGINAL FUNCTIONALITY PRESERVED
     */
    async onRefresh(e) {
        if (e) e.preventDefault();

        const refreshIcon = document.querySelector('.o_dashboard_refresh i');
        if (refreshIcon) refreshIcon.classList.add('fa-spin');

        try {
            await this._loadDashboardData();
            this._renderDashboard();
            this._destroyCharts();
            this._initializeCharts();

            this.notification.add(_t('Dashboard refreshed successfully'), {
                type: 'success',
            });
        } finally {
            if (refreshIcon) refreshIcon.classList.remove('fa-spin');
        }
    }

    /**
     * Export dashboard
     * ORIGINAL FUNCTIONALITY PRESERVED
     */
    onExport(e) {
        e.preventDefault();

        this.dialog.add(ExportDialog, {
            onExportPDF: () => this._exportAsPDF(),
            onExportExcel: () => this._exportAsExcel(),
        });
    }

    /**
     * Export as PDF
     * ORIGINAL FUNCTIONALITY PRESERVED
     */
    _exportAsPDF() {
        if (typeof html2pdf !== 'undefined') {
            const element = document.querySelector('.o_dashboard_content');
            const opt = {
                margin: 10,
                filename: 'dashboard_' + moment().format('YYYY-MM-DD') + '.pdf',
                image: { type: 'jpeg', quality: 0.98 },
                html2canvas: { scale: 2 },
                jsPDF: { unit: 'mm', format: 'a4', orientation: 'landscape' }
            };
            html2pdf().set(opt).from(element).save();
        } else {
            this.notification.add(_t('PDF export library not available'), {
                type: 'warning',
            });
        }
    }

    /**
     * Export as Excel
     * ORIGINAL FUNCTIONALITY PRESERVED
     */
    async _exportAsExcel() {
        try {
            const result = await this.rpc('/university/dashboard/export/excel', {
                data: this.state.dashboardData,
                filters: this.state.filters
            });

            if (result.file) {
                window.location = '/web/content/' + result.file;
            }
        } catch (error) {
            console.error('Export error:', error);
        }
    }

    /**
     * Show filter dialog
     * ORIGINAL FUNCTIONALITY PRESERVED
     */
    onFilterClick(e) {
        e.preventDefault();

        this.dialog.add(FilterDialog, {
            filters: this.state.filters,
            onApply: (filters) => this._applyFilters(filters),
            onReset: () => this._resetFilters(),
        });
    }

    /**
     * Apply filters
     * ORIGINAL FUNCTIONALITY PRESERVED
     */
    _applyFilters(filters) {
        this.state.filters = { ...filters };
        this.onRefresh({ preventDefault: () => {} });
    }

    /**
     * Reset filters
     * ORIGINAL FUNCTIONALITY PRESERVED
     */
    _resetFilters() {
        this.state.filters = {
            date_range: 'month',
            academic_year_id: null,
            department_id: null,
            program_id: null,
        };
        this.onRefresh({ preventDefault: () => {} });
    }

    /**
     * Date filter change
     * ORIGINAL FUNCTIONALITY PRESERVED
     */
    onDateFilterChange(e) {
        this.state.filters.date_range = e.target.value;
        this.onRefresh({ preventDefault: () => {} });
    }

    /**
     * KPI card click
     * ORIGINAL FUNCTIONALITY PRESERVED
     */
    onKPIClick(e) {
        const card = e.currentTarget;
        const actionData = card.dataset.action;

        if (actionData) {
            this.action.doAction(JSON.parse(actionData));
        }
    }

    /**
     * Widget action click
     * ORIGINAL FUNCTIONALITY PRESERVED
     */
    onWidgetAction(e) {
        e.preventDefault();

        const btn = e.currentTarget;
        const action = btn.dataset.action;
        const widget = btn.closest('.o_dashboard_widget');
        const widgetId = widget.dataset.widgetId;

        switch (action) {
            case 'refresh':
                this._refreshWidget(widgetId);
                break;
            case 'expand':
                this._expandWidget(widgetId);
                break;
            case 'remove':
                this._removeWidget(widgetId);
                break;
        }
    }

    /**
     * Customize dashboard
     * ORIGINAL FUNCTIONALITY PRESERVED
     */
    onCustomize(e) {
        e.preventDefault();

        this.dialog.add(CustomizeDialog, {
            widgets: this.state.dashboardConfig.widgets,
            onSave: (settings) => this._saveCustomization(settings),
        });
    }

    /**
     * Save dashboard customization
     * ORIGINAL FUNCTIONALITY PRESERVED
     */
    async _saveCustomization(widgetSettings) {
        try {
            await this.orm.call(
                'university.dashboard.preference',
                'save_widget_settings',
                [widgetSettings]
            );

            this.notification.add(_t('Dashboard customization saved'), {
                type: 'success',
            });

            this.onRefresh({ preventDefault: () => {} });
        } catch (error) {
            console.error('Customization save error:', error);
        }
    }

    /**
     * Start auto-refresh
     * ORIGINAL FUNCTIONALITY PRESERVED
     */
    _startAutoRefresh() {
        if (this.autoRefresh) {
            this.refreshTimer = setInterval(() => {
                this.onRefresh({ preventDefault: () => {} });
            }, this.refreshInterval);
        }
    }

    /**
     * Stop auto-refresh
     * ORIGINAL FUNCTIONALITY PRESERVED
     */
    _stopAutoRefresh() {
        if (this.refreshTimer) {
            clearInterval(this.refreshTimer);
            this.refreshTimer = null;
        }
    }

    /**
     * Initialize drag and drop for widgets
     * ORIGINAL FUNCTIONALITY PRESERVED
     */
    _initializeDragAndDrop() {
        if (typeof Sortable !== 'undefined') {
            const container = document.querySelector('.o_dashboard_widgets_container');
            if (container) {
                new Sortable(container, {
                    animation: 150,
                    handle: '.o_widget_handle',
                    onEnd: () => this._saveWidgetOrder()
                });
            }
        }
    }

    /**
     * Save widget order
     * ORIGINAL FUNCTIONALITY PRESERVED
     */
    async _saveWidgetOrder() {
        const widgets = document.querySelectorAll('.o_dashboard_widget');
        const widgetOrder = Array.from(widgets).map((widget, index) => ({
            widget_id: widget.dataset.widgetId,
            order: index
        }));

        await this.orm.call(
            'university.dashboard.preference',
            'save_widget_order',
            [widgetOrder]
        );
    }

    /**
     * Load user preferences
     * ORIGINAL FUNCTIONALITY PRESERVED
     */
    async _loadUserPreferences() {
        try {
            const prefs = await this.orm.call(
                'university.dashboard.preference',
                'get_user_preferences',
                []
            );

            if (prefs) {
                this.autoRefresh = prefs.auto_refresh;
                this.refreshInterval = prefs.refresh_interval * 1000;

                if (this.autoRefresh) {
                    this._startAutoRefresh();
                }
            }
        } catch (error) {
            console.error('Error loading preferences:', error);
        }
    }

    /**
     * Refresh specific widget
     * ORIGINAL FUNCTIONALITY PRESERVED
     */
    _refreshWidget(widgetId) {
        console.log('Refreshing widget:', widgetId);
        // Implementation for refreshing specific widget
    }

    /**
     * Expand widget to fullscreen
     * ORIGINAL FUNCTIONALITY PRESERVED
     */
    _expandWidget(widgetId) {
        const widget = document.querySelector(`[data-widget-id="${widgetId}"]`);
        if (widget) {
            widget.classList.toggle('o_widget_expanded');
        }
    }

    /**
     * Remove widget from dashboard
     * ORIGINAL FUNCTIONALITY PRESERVED
     */
    _removeWidget(widgetId) {
        const widget = document.querySelector(`[data-widget-id="${widgetId}"]`);
        if (widget) {
            widget.style.transition = 'opacity 0.3s';
            widget.style.opacity = '0';
            setTimeout(() => widget.remove(), 300);
        }
    }

    /**
     * Destroy all charts
     * ORIGINAL FUNCTIONALITY PRESERVED
     */
    _destroyCharts() {
        Object.values(this.charts).forEach(chart => {
            if (chart) {
                chart.destroy();
            }
        });
        this.charts = {};
    }
}

// Register the action in Odoo 18 registry
registry.category("actions").add("university_dashboard", UniversityDashboard);

/* ============================================
   CSS ANIMATIONS
   ORIGINAL STYLES PRESERVED
   ============================================ */

const style = document.createElement('style');
style.innerHTML = `
@keyframes fadeIn {
    from {
        opacity: 0;
        transform: translateY(20px);
    }
    to {
        opacity: 1;
        transform: translateY(0);
    }
}

.o_widget_expanded {
    position: fixed !important;
    top: 0 !important;
    left: 0 !important;
    width: 100vw !important;
    height: 100vh !important;
    z-index: 9999 !important;
    background: white !important;
}
`;
document.head.appendChild(style);