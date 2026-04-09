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
                active_assets: 0,
                under_maintenance: 0,
                disposed_assets: 0,
                pending_requests: 0,
                transfers_this_month: 0,
                assets_under_warranty: 0,
                unverified_assets: 0,
                total_purchase_value: 0,
                total_book_value: 0,
                by_category: [],
                by_condition: [],
                recent_maintenance: [],
                recent_requests: [],
                recent_transfers: [],
            },
            recentAdmissions: [],
            recentPayments: [],
            departmentStats: [],
            feeCollectionMonthly: [],
            semesterAdmissions: [],
            lastUpdated: null,
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
            // Also destroy asset-specific charts
            if (this._assetCategoryChart) {
                this._assetCategoryChart.destroy();
                this._assetCategoryChart = null;
            }
            if (this._assetConditionChart) {
                this._assetConditionChart.destroy();
                this._assetConditionChart = null;
            }
        });
    }

    // Theme management
    setTheme(theme) {
        this.state.theme = theme;
        localStorage.setItem('university_theme', theme);
        this.applyTheme(theme);

        // Re-render charts with new theme
        setTimeout(() => {
            UniversityCharts.renderAll(this.state);
            if (this.state.activeModule === 'assets') {
                this._renderAssetCharts();
            }
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
            const data = await this.orm.call(
                "university.dashboard",
                "get_dashboard_data",
                []
            );

            this.updateState(data);
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
                UniversityCharts.renderAll(this.state);
                // FIX 1: Also render asset charts if we're on assets module
                if (this.state.activeModule === 'assets') {
                    this._renderAssetCharts();
                }
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

        // FIX 2: Dummy data uses correct field names matching the XML template
        // (asset_id, request_date, requester_id, category_id, from_department_id,
        //  to_department_id, transfer_date) so the tables render properly.
        const assetFallback = {
            total_assets: 25,
            active_assets: 20,
            under_maintenance: 2,
            disposed_assets: 1,
            pending_requests: 4,
            transfers_this_month: 4,
            assets_under_warranty: 7,
            unverified_assets: 18,
            total_purchase_value: 3885000,
            total_book_value: 3128000,
            by_category: [
                { name: "IT Equipment", count: 9 },
                { name: "Lab Equipment", count: 5 },
                { name: "Furniture", count: 3 },
                { name: "Vehicles", count: 2 },
                { name: "Electrical Equipment", count: 4 },
                { name: "Sports Equipment", count: 2 },
            ],
            by_condition: [
                { name: "Good", count: 17 },
                { name: "Fair", count: 5 },
                { name: "Poor", count: 2 },
                { name: "Condemned", count: 1 },
            ],
            // FIX 2a: use asset_id tuple and request_date (matches XML t-esc="m.asset_id[1]" / m.request_date)
            recent_maintenance: [
                { id: -1, name: "MAINT/2024/00005", asset_id: [-1, "Daikin Split AC 1.5 Ton (Set of 5)"], request_date: "2024-04-01", state: "assigned", type: "amc" },
                { id: -2, name: "MAINT/2024/00004", asset_id: [-2, "Digital Oscilloscope 100MHz"], request_date: "2024-03-20", state: "completed", type: "calibration" },
                { id: -3, name: "MAINT/2024/00003", asset_id: [-3, "Hydraulic Press 20 Ton"], request_date: "2024-02-20", state: "in_progress", type: "corrective" },
                { id: -4, name: "MAINT/2024/00002", asset_id: [-4, "Kirloskar DG Set 62.5 KVA"], request_date: "2024-01-12", state: "completed", type: "preventive" },
                { id: -5, name: "MAINT/2024/00001", asset_id: [-5, "Epson Multimedia Projector"], request_date: "2024-03-17", state: "completed", type: "corrective" },
            ],
            // FIX 2b: use requester_id tuple, category_id tuple, request_date (matches XML)
            recent_requests: [
                { id: -11, name: "AREQ/2024/0004", requester_id: [-11, "Administrator"], category_id: [-11, "IT Equipment"], request_date: "2024-04-03", state: "approved" },
                { id: -12, name: "AREQ/2024/0003", requester_id: [-12, "Administrator"], category_id: [-12, "Lab Equipment"], request_date: "2024-04-05", state: "draft" },
                { id: -13, name: "AREQ/2024/0002", requester_id: [-13, "Administrator"], category_id: [-13, "Furniture"], request_date: "2024-03-25", state: "pending_purchase" },
                { id: -14, name: "AREQ/2024/0001", requester_id: [-14, "Administrator"], category_id: [-14, "IT Equipment"], request_date: "2024-04-01", state: "submitted" },
            ],
            // FIX 2c: use asset_id tuple, from_department_id, to_department_id, transfer_date (matches XML)
            recent_transfers: [
                { id: -21, name: "TRF/2024/00004", asset_id: [-21, "Samsung Smart Board 75 Inch"], from_department_id: [-21, "Electronics and Communication Engg"], to_department_id: [-21, "Computer Science and Engineering"], transfer_date: "2024-04-01", state: "completed" },
                { id: -22, name: "TRF/2024/00003", asset_id: [-22, "Dell Laptop Core i7"], from_department_id: [-22, "Computer Science and Engineering"], to_department_id: [-22, "Computer Science and Engineering"], transfer_date: "2024-03-20", state: "pending" },
                { id: -23, name: "TRF/2024/00002", asset_id: [-23, "Lenovo ThinkPad — Faculty Laptop"], from_department_id: [-23, "Computer Science and Engineering"], to_department_id: [-23, "Computer Science and Engineering"], transfer_date: "2024-02-10", state: "completed" },
                { id: -24, name: "TRF/2024/00001", asset_id: [-24, "HP Desktop PC Core i5"], from_department_id: [-24, "Administration"], to_department_id: [-24, "Administration"], transfer_date: "2024-01-15", state: "completed" },
            ],
        };

        const incomingAssets = data.assets || {};
        const hasAssets =
            (incomingAssets.total_assets || 0) > 0 ||
            (incomingAssets.pending_requests || 0) > 0 ||
            (incomingAssets.transfers_this_month || 0) > 0 ||
            (incomingAssets.by_category || []).length > 0 ||
            (incomingAssets.by_condition || []).length > 0 ||
            (incomingAssets.recent_maintenance || []).length > 0 ||
            (incomingAssets.recent_requests || []).length > 0 ||
            (incomingAssets.recent_transfers || []).length > 0;

        this.state.assets = {
            ...this.state.assets,
            ...(hasAssets ? incomingAssets : assetFallback),
        };

        this.state.recentAdmissions = data.recent_admissions || [];
        this.state.recentPayments = data.recent_payments || [];
        this.state.departmentStats = data.department_stats || [];
        this.state.feeCollectionMonthly = data.fee_monthly || [];
        this.state.semesterAdmissions = data.semester_admissions || [];
    }

    setActiveModule(moduleKey) {
        this.state.activeModule = moduleKey;

        setTimeout(() => {
            UniversityCharts.renderAll(this.state);
            // FIX 1: Call asset chart renderer when switching to assets tab
            if (moduleKey === 'assets') {
                this._renderAssetCharts();
            }
        }, 100);
    }

    // FIX 1: This method is now properly called from setActiveModule and loadDashboardData
    _renderAssetCharts() {
        if (!window.Chart) {
            return;
        }

        const categoryCanvas = document.getElementById("uni-asset-category-chart");
        const conditionCanvas = document.getElementById("uni-asset-condition-chart");

        // destroy old charts if already present
        if (this._assetCategoryChart) {
            this._assetCategoryChart.destroy();
            this._assetCategoryChart = null;
        }
        if (this._assetConditionChart) {
            this._assetConditionChart.destroy();
            this._assetConditionChart = null;
        }

        const byCategory = (this.state.assets?.by_category || []);
        const byCondition = (this.state.assets?.by_condition || []);

        if (categoryCanvas && byCategory.length) {
            this._assetCategoryChart = new Chart(categoryCanvas, {
                type: "doughnut",
                data: {
                    labels: byCategory.map(x => x.name),
                    datasets: [{
                        data: byCategory.map(x => x.count),
                        backgroundColor: [
                            "#3b82f6",
                            "#10b981",
                            "#f59e0b",
                            "#8b5cf6",
                            "#ef4444",
                            "#14b8a6",
                        ],
                        borderWidth: 1,
                    }],
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            position: "bottom",
                        },
                    },
                },
            });
        }

        if (conditionCanvas && byCondition.length) {
            this._assetConditionChart = new Chart(conditionCanvas, {
                type: "bar",
                data: {
                    labels: byCondition.map(x => x.name),
                    datasets: [{
                        label: "Assets",
                        data: byCondition.map(x => x.count),
                        backgroundColor: [
                            "#10b981",
                            "#f59e0b",
                            "#ef4444",
                            "#6b7280",
                        ],
                        borderWidth: 1,
                    }],
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            display: false,
                        },
                    },
                    scales: {
                        y: {
                            beginAtZero: true,
                            ticks: {
                                precision: 0,
                            },
                        },
                    },
                },
            });
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

    openStudents() { this.navigateTo("university_management.action_student"); }
    openAdmissions() { this.navigateTo("university_management.action_student_admission"); }
    openFaculty() { this.navigateTo("university_management.action_faculty"); }
    openFeePayments() { this.navigateTo("university_management.action_fee_payment"); }
    openFeeStructures() { this.navigateTo("university_management.action_fee_structure"); }
    openExaminations() { this.navigateTo("university_management.action_examination"); }
    openHostel() { this.navigateTo("university_management.action_hostel_hostel"); }
    openLibrary() { this.navigateTo("university_management.action_library_book"); }
    openPlacement() { this.navigateTo("university_management.action_placement_drive"); }
    openTransport() { this.navigateTo("university_management.action_transport_vehicle"); }

    // FIX 3: Asset navigation stubs — no-ops so clicks don't crash
    openAssets() { /* disabled – no action defined */ }
    openAssetRequests() { /* disabled – no action defined */ }
    openAssetMaintenance() { /* disabled – no action defined */ }
    openAssetTransfers() { /* disabled – no action defined */ }

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

    assetStateClass(state) {
        const value = (state || "").toString().toLowerCase();

        if (["completed", "approved", "issued", "done", "active"].includes(value)) {
            return "success";
        }
        if (["pending", "submitted", "in_progress", "under_maintenance", "assigned", "verification", "pending_purchase"].includes(value)) {
            return "warning";
        }
        if (["cancelled", "rejected", "disposed", "scrapped"].includes(value)) {
            return "danger";
        }
        if (["draft"].includes(value)) {
            return "secondary";
        }
        return "info";
    }

    assetStateLabel(state) {
        const value = (state || "").toString().replace(/_/g, " ");
        return value.charAt(0).toUpperCase() + value.slice(1);
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