import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, onMounted, onWillUnmount, useState } from "@odoo/owl";
import { UniversityCharts } from "./charts";

class UniversityDashboard extends Component {
    static template = "university_management.DashboardMain";

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.notification = useService("notification");

        // Check for saved theme preference
        const savedTheme = localStorage.getItem('university_theme') || 'light';

        this.state = useState({
            activeModule: "overview",
            isLoading: true,
            theme: savedTheme,
            overview: {
                total_students: 0,
                total_faculty: 0,
                avg_cgpa: 0,
                new_admissions_this_month: 0,
                placement_rate: 0,
                students_placed: 0,
                active_placement_drives: 0,
                recruiting_companies: 0,
                highest_package: 'N/A',
                total_vehicles: 0,
                active_routes: 0,
                transport_students: 0,
            },
            students: {
                total_enrolled: 0,
                new_this_year: 0,
                pending_admissions: 0,
                low_attendance: 0,
                program_distribution: [],
            },
            faculty: {
                total: 0,
                present_today: 0,
                on_leave: 0,
                avg_rating: 0,
            },
            fees: {
                total_collected: 0,
                monthly_collection: 0,
                total_pending: 0,
                late_payments: 0,
                invoices_count: 0,
                journal_entries: 0,
                posted_payments: 0,
                pending_verification: 0,
                scholarships_applied: 0,
                by_program: [],
                today_collection: 0,
                transaction_count_month: 0,
                payment_mode_breakdown: [],
                reconciliation_stats: {
                    fully_reconciled: 0,
                    partially_reconciled: 0,
                    not_reconciled: 0,
                },
                student_ledger_stats: {
                    total_students_with_dues: 0,
                    total_outstanding_fmt: '0',
                    avg_outstanding_fmt: '0',
                },
            },
            exams: {
                active_exams: 0,
                hall_tickets: 0,
                results_published: 0,
                revaluations: 0,
            },
            hostel: {
                total_rooms: 0,
                occupied_rooms: 0,
                pending_complaints: 0,
                occupancy_rate: 0,
            },
            library: {
                total_books: 0,
                books_issued: 0,
                overdue: 0,
                fines_collected: 0,
            },
            assets: {
                total_assets: 0,
                available: 0,
                maintenance_due: 0,
                pending_requests: 0,
                low_stock_alerts: 0,
                pending_handovers: 0,
            },
            assetPurchaseRequests: [],
            assetHandovers: [],
            recentAdmissions: [],
            recentPayments: [],
            departmentStats: [],
            feeCollectionMonthly: [],
            semesterAdmissions: [],
            lastUpdated: null,
            batches: [],
            selectedBatch: null,
            departments: [],
            feeTrendBatch: null,
            feeTrendDept: null,
        });

        // Apply theme on mount
        onMounted(() => {
            this.applyTheme(this.state.theme);
            this.loadDashboardData();

            // Listen for system theme changes
            window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
                if (!localStorage.getItem('university_theme')) {
                    this.setTheme(e.matches ? 'dark' : 'light');
                }
            });
        });

        onWillUnmount(() => {
            UniversityCharts.destroyAll();
        });
    }

    // Theme management
    setTheme(theme) {
        this.state.theme = theme;
        localStorage.setItem('university_theme', theme);
        this.applyTheme(theme);

        setTimeout(() => {
            UniversityCharts.renderAll(
                this.state,
                (deptId, deptName, count) => this.drillDownDepartment(deptId, deptName, count),
                (progId, progName, count) => this.drillDownProgram(progId, progName, count),
                (label, ds, de) => this.drillDownFeeTrend(label, ds, de)
            );
        }, 100);

        // Show theme change notification
        this.notification.add(
            `${theme === 'dark' ? '🌙' : '☀️'} ${theme.charAt(0).toUpperCase() + theme.slice(1)} mode activated`,
            { type: 'info', sticky: false }
        );
    }

    applyTheme(theme) {
        document.documentElement.setAttribute('data-theme', theme);

        // Update chart colors if needed
        if (UniversityCharts.instances) {
            Object.values(UniversityCharts.instances).forEach(chart => {
                if (chart && chart.update) {
                    chart.update();
                }
            });
        }
    }

    toggleTheme() {
        const newTheme = this.state.theme === 'light' ? 'dark' : 'light';
        this.setTheme(newTheme);
    }

    async loadDashboardData() {
        this.state.isLoading = true;

        try {
            const [data, batches, departments] = await Promise.all([
                this.orm.call("university.dashboard", "get_dashboard_data", []),
                this.orm.call("university.dashboard", "get_batches", []),
                this.orm.call("university.dashboard", "get_departments", []),
            ]);

            this.updateState(data);
            this.state.batches = batches;
            this.state.departments = departments;
            this.state.lastUpdated = new Date();

        } catch (error) {
            console.error("Failed to load dashboard data:", error);
            this.notification.add(
                "Unable to load dashboard data. Please try again.",
                { type: "danger" }
            );
        } finally {
            this.state.isLoading = false;

            setTimeout(() => {
                UniversityCharts.renderAll(
                    this.state,
                    (deptId, deptName, count) => this.drillDownDepartment(deptId, deptName, count),
                    (progId, progName, count) => this.drillDownProgram(progId, progName, count),
                    (label, ds, de) => this.drillDownFeeTrend(label, ds, de)
                );
            }, 100);
        }
    }

    updateState(data) {
        this.state.overview = { ...this.state.overview, ...(data.overview || {}) };

        this.state.students = {
            ...this.state.students,
            ...(data.students || {}),
            total_enrolled: (data.students && (
                data.students.total_enrolled ??
                data.students.total_active
            )) || this.state.students.total_enrolled || 0,
        };

        this.state.faculty = { ...this.state.faculty, ...(data.faculty || {}) };
        this.state.fees = { ...this.state.fees, ...(data.fees || {}) };
        this.state.exams = { ...this.state.exams, ...(data.exams || {}) };
        this.state.hostel = { ...this.state.hostel, ...(data.hostel || {}) };
        this.state.library = { ...this.state.library, ...(data.library || {}) };

        if (data.assets) {
            this.state.assets = { ...this.state.assets, ...data.assets };
        }
        this.state.assetPurchaseRequests = data.asset_purchase_requests || [];
        this.state.assetHandovers = data.asset_handovers || [];

        this.state.recentAdmissions = data.recent_admissions || [];
        this.state.recentPayments = data.recent_payments || [];
        this.state.departmentStats = data.department_stats || [];
        this.state.feeCollectionMonthly = data.fee_monthly || [];
        this.state.semesterAdmissions = data.semester_admissions || [];
    }

    setActiveModule(moduleKey) {
        this.state.activeModule = moduleKey;

        setTimeout(() => {
            UniversityCharts.renderForModule(
                moduleKey,
                this.state,
                (deptId, deptName, count) => this.drillDownDepartment(deptId, deptName, count),
                (progId, progName, count) => this.drillDownProgram(progId, progName, count),
                (label, ds, de) => this.drillDownFeeTrend(label, ds, de)
            );
        }, 150);
    }

    async filterDeptByBatch(ev) {
        const batchId = ev.target.value ? parseInt(ev.target.value) : null;
        this.state.selectedBatch = batchId;
        try {
            const stats = await this.orm.call(
                "university.dashboard",
                "get_department_stats_by_batch",
                [batchId]
            );
            this.state.departmentStats = stats;
            setTimeout(() => {
                UniversityCharts.renderDepartmentDistribution(stats, (deptId, deptName, count) => {
                    this.drillDownDepartment(deptId, deptName, count);
                });
            }, 50);
        } catch (e) {
            console.error("Batch filter error:", e);
        }
    }

    async filterFeeTrend(ev) {
        const field = ev.target.dataset.field;
        const value = ev.target.value ? parseInt(ev.target.value) : null;
        if (field === 'batch') this.state.feeTrendBatch = value;
        if (field === 'dept') this.state.feeTrendDept = value;

        try {
            const trend = await this.orm.call(
                "university.dashboard",
                "get_fee_trend_filtered",
                [this.state.feeTrendBatch, this.state.feeTrendDept]
            );
            this.state.feeCollectionMonthly = trend;
            setTimeout(() => {
                UniversityCharts.renderFeeTrend(trend, (label, ds, de) => this.drillDownFeeTrend(label, ds, de));
            }, 50);
        } catch (e) {
            console.error("Fee trend filter error:", e);
        }
    }

    // ── Navigation helpers ──────────────────────────────────────────────────
    // FIX 3: Wrap all navigateTo calls in try/catch so missing actions
    // don't throw an uncaught OwlError ("Invalid handler: undefined").
    navigateTo(actionXmlId) {
        try {
            this.action.doAction(actionXmlId);
        } catch (e) {
            console.warn("Navigation not available:", actionXmlId, e);
        }
    }

    drillDownFeeTrend(monthLabel, dateStart, dateEnd) {
        try {
            // Show ALL fee payments related to this month:
            // 1. Payments actually received in this month (payment_date in range)
            // 2. Fees that were DUE in this month (due_date in range) — including
            //    those paid late (after the month) or still unpaid
            this.action.doAction({
                type: 'ir.actions.act_window',
                name: `Fee Collection — ${monthLabel} (due or paid this month)`,
                res_model: 'fee.payment',
                view_mode: 'list,form',
                views: [[false, 'list'], [false, 'form']],
                domain: [
                    '|',
                    // Paid/received in this calendar month
                    '&',
                        ['payment_date', '>=', dateStart],
                        ['payment_date', '<=', dateEnd],
                    // Due in this calendar month (regardless of when paid)
                    '&',
                        ['due_date', '>=', dateStart],
                        ['due_date', '<=', dateEnd],
                ],
                context: {
                    search_default_group_by_state: 1,
                },
            });
        } catch (e) {
            console.warn('drillDownFeeTrend failed:', e);
        }
    }

    drillDownProgram(progId, progName, studentCount) {
        try {
            this.action.doAction({
                type: 'ir.actions.act_window',
                name: `${progName} — Students (${studentCount})`,
                res_model: 'student.student',
                view_mode: 'list,form',
                views: [[false, 'list'], [false, 'form']],
                domain: [
                    ['program_id', '=', progId],
                    ['state', 'in', ['active', 'enrolled', 'admitted']],
                ],
                context: {
                    search_default_program_id: progId,
                },
            });
        } catch (e) {
            console.warn('drillDownProgram failed:', e);
        }
    }

    drillDownDepartment(deptId, deptName, studentCount) {
        try {
            this.action.doAction({
                type: 'ir.actions.act_window',
                name: `${deptName} — Students (${studentCount})`,
                res_model: 'student.student',
                view_mode: 'list,form',
                views: [[false, 'list'], [false, 'form']],
                domain: [
                    ['department_id', '=', deptId],
                    ['state', 'in', ['active', 'enrolled', 'admitted']],
                ],
                context: {
                    search_default_department_id: deptId,
                },
            });
        } catch (e) {
            console.warn('drillDownDepartment failed:', e);
            // Fallback: navigate to all students filtered
            this.notification.add(
                `Showing students for ${deptName}`,
                { type: 'info', sticky: false }
            );
        }
    }

    openStudents() { this.navigateTo("university_management.action_student"); }
    openAdmissions() { this.navigateTo("university_management.action_student_admission"); }
    openFaculty() { this.navigateTo("university_management.action_faculty"); }
    openFeePayments() { this.navigateTo("university_management.action_fee_payment"); }
    openFeeStructures() { this.navigateTo("university_management.action_fee_structure"); }

    openFeeOverdue() {
        try {
            this.action.doAction({
                type: "ir.actions.act_window",
                name: "Fee Payments",
                res_model: "fee.payment",
                view_mode: "kanban,list,form",
                views: [[false, "kanban"], [false, "list"], [false, "form"]],
                domain: [["state", "in", ["draft", "invoiced", "pending", "partial", "verified"]]],
                context: {
                    search_default_group_by_state: 1,
                },
            });
        } catch (e) {
            console.warn("openFeeOverdue failed:", e);
        }
    }
    openExaminations() { this.navigateTo("university_management.action_examination"); }
    openHallTickets() { this.navigateTo("university_management.action_examination_hall_ticket"); }
    openExamResults() { this.navigateTo("university_management.action_exam_result"); }
    openHostel() { this.navigateTo("university_management.action_hostel_hostel"); }
    openHostelComplaints() { this.navigateTo("university_management.action_hostel_complaint"); }
    openLibrary() { this.navigateTo("university_management.action_library_book"); }
    openLibraryIssues() { this.navigateTo("university_management.action_library_issue"); }
    openPlacement() { this.navigateTo("university_management.action_placement_drive"); }
    openTransport() { this.navigateTo("university_management.action_transport_vehicle"); }
    openAssets() { this.navigateTo("university_management.action_asset_asset"); }
    openPurchaseRequests() { this.navigateTo("university_management.action_asset_purchase_request"); }
    openHandoverRequests() { this.navigateTo("university_management.action_asset_handover"); }

    // Utility methods
    formatNumber(num) {
        if (!num && num !== 0) return '0';
        if (num >= 10000000) return (num / 10000000).toFixed(1) + 'Cr';
        if (num >= 100000) return (num / 100000).toFixed(1) + 'L';
        if (num >= 1000) return (num / 1000).toFixed(1) + 'K';
        return num.toString();
    }

    formatCurrency(amount) {
        if (!amount) return '₹0';
        return '₹' + this.formatNumber(amount);
    }

    getCurrentDate() {
        return new Date().toLocaleDateString('en-IN', {
            weekday: 'long',
            year: 'numeric',
            month: 'long',
            day: 'numeric'
        });
    }

    getGreeting() {
        const hour = new Date().getHours();
        if (hour < 12) return 'Good morning';
        if (hour < 17) return 'Good afternoon';
        if (hour < 20) return 'Good evening';
        return 'Good night';
    }

    get navModules() {
        return [
            { key: "overview", label: "Overview", icon: "fa-tachometer", badge: null },
            { key: "students", label: "Students", icon: "fa-graduation-cap", badge: this.state.students?.pending_admissions || 0 },
            { key: "faculty", label: "Faculty", icon: "fa-users", badge: null },
            { key: "fees", label: "Fees", icon: "fa-money", badge: this.state.fees?.pending_verification || 0 },
            { key: "exams", label: "Exams", icon: "fa-file-text", badge: this.state.exams?.active_exams || 0 },
            { key: "hostel", label: "Hostel", icon: "fa-building", badge: this.state.hostel?.pending_complaints || 0 },
            { key: "library", label: "Library", icon: "fa-book", badge: this.state.library?.overdue || 0 },
            { key: "placement", label: "Placement", icon: "fa-briefcase", badge: this.state.overview?.active_placement_drives || 0 },
            { key: "transport", label: "Transport", icon: "fa-bus", badge: null },
            { key: "assets", label: "Assets", icon: "fa-cubes", badge: this.state.assets?.pending_requests || 0 },
        ];
    }
}

registry.category("actions").add("university_dashboard_main", UniversityDashboard);
export { UniversityDashboard };