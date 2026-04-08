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
                // ── existing fields (unchanged) ──────────────────────
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
                // ── new fields from PDF architecture ─────────────────
                today_collection: 0,            // Finance Dashboard – "Today's Fee Collection"
                transaction_count_month: 0,     // count of transactions this month
                payment_mode_breakdown: [],     // PDF section 12 – Payment Mode Analysis
                reconciliation_stats: {         // PDF section 8  – Bank Reconciliation
                    fully_reconciled: 0,
                    partially_reconciled: 0,
                    not_reconciled: 0,
                },
                student_ledger_stats: {         // PDF section 4  – Student Ledger System
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
                total_purchase_value: 0,
                total_book_value: 0,
                pending_requests: 0,
                transfers_this_month: 0,
                disposed_assets: 0,
                assets_under_warranty: 0,
                unverified_assets: 0,
                by_category: [],
                by_condition: [],
                by_department: [],
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
            }, 100);
        }
        this.loadAssetData();
    }

    async loadAssetData() {
        try {
            const today = new Date();
            const firstOfMonth = new Date(today.getFullYear(), today.getMonth(), 1)
                .toISOString().slice(0, 10);

            const [
                totalAssets, activeAssets, underMaintenance, disposedCondemned,
                pendingRequests, transfersMonth, underWarranty, unverified,
                categoryGroups, conditionGroups, departmentGroups,
                recentMaint, recentReq, recentTransfer, valueData,
            ] = await Promise.all([
                this.orm.searchCount('asset.asset', []),
                this.orm.searchCount('asset.asset', [['state', '=', 'active']]),
                this.orm.searchCount('asset.asset', [['state', '=', 'under_maintenance']]),
                this.orm.searchCount('asset.asset', [['state', 'in', ['disposed', 'condemned', 'lost']]]),
                this.orm.searchCount('asset.request', [['state', 'in', ['draft', 'approved', 'pending_purchase']]]),
                this.orm.searchCount('asset.transfer', [
                    ['transfer_date', '>=', firstOfMonth], ['transfer_type', '=', 'transfer'],
                ]),
                this.orm.searchCount('asset.asset', [['is_under_warranty', '=', true]]),
                this.orm.searchCount('asset.asset', [
                    ['is_verified_this_year', '=', false],
                    ['state', 'not in', ['disposed', 'condemned', 'lost']],
                ]),
                this.orm.readGroup('asset.asset', [], ['category_id'],
                    { groupby: ['category_id'], limit: 8 }),
                this.orm.readGroup('asset.asset',
                    [['state', 'not in', ['disposed', 'condemned', 'lost']]],
                    ['condition'], { groupby: ['condition'] }),
                this.orm.readGroup('asset.asset', [], ['department_id'],
                    { groupby: ['department_id'], limit: 8 }),
                this.orm.searchRead('asset.maintenance',
                    [['maintenance_type', '!=', false]],
                    ['name', 'asset_id', 'request_date', 'priority', 'state', 'maintenance_type'],
                    { limit: 5, order: 'request_date desc' }),
                this.orm.searchRead('asset.request', [],
                    ['name', 'requester_id', 'category_id', 'request_date', 'state'],
                    { limit: 5, order: 'request_date desc' }),
                this.orm.searchRead('asset.transfer',
                    [['transfer_type', '=', 'transfer']],
                    ['name', 'asset_id', 'transfer_date', 'from_department_id', 'to_department_id', 'state'],
                    { limit: 5, order: 'transfer_date desc' }),
                this.orm.searchRead('asset.asset', [],
                    ['purchase_cost', 'current_book_value'], { limit: 9999 }),
            ]);

            let totalPurchase = 0, totalBook = 0;
            for (const r of valueData) {
                totalPurchase += r.purchase_cost || 0;
                totalBook += r.current_book_value || 0;
            }

            const conditionLabels = {
                new: 'New', good: 'Good', fair: 'Fair',
                poor: 'Poor', non_functional: 'Non-Functional', condemned: 'Condemned',
            };

            this.state.assets = {
                total_assets: totalAssets,
                active_assets: activeAssets,
                under_maintenance: underMaintenance,
                total_purchase_value: totalPurchase,
                total_book_value: totalBook,
                pending_requests: pendingRequests,
                transfers_this_month: transfersMonth,
                disposed_assets: disposedCondemned,
                assets_under_warranty: underWarranty,
                unverified_assets: unverified,
                by_category: categoryGroups.map(g => ({
                    name: g.category_id ? g.category_id[1] : 'Uncategorized',
                    count: g.category_id_count,
                })),
                by_condition: conditionGroups.map(g => ({
                    name: conditionLabels[g.condition] || g.condition || 'Unknown',
                    count: g.condition_count,
                })),
                by_department: departmentGroups.map(g => ({
                    name: g.department_id ? g.department_id[1] : 'Unassigned',
                    count: g.department_id_count,
                })),
                recent_maintenance: recentMaint,
                recent_requests: recentReq,
                recent_transfers: recentTransfer,
            };

            if (this.state.activeModule === 'assets') {
                setTimeout(() => this._renderAssetCharts(), 150);
            }
        } catch (e) {
            console.error('Asset data load error:', e);
        }
    }

    _renderAssetCharts() {
        if (typeof Chart === 'undefined') return;

        const catCanvas = document.getElementById('uni-asset-category-chart');
        if (catCanvas && !catCanvas._chartInstance) {
            const data = this.state.assets.by_category;
            const COLORS = ['#4A90D9','#27AE60','#E67E22','#8E44AD','#E74C3C','#16A085','#2980B9','#F39C12'];
            catCanvas._chartInstance = new Chart(catCanvas.getContext('2d'), {
                type: 'doughnut',
                data: {
                    labels: data.map(d => d.name),
                    datasets: [{ data: data.map(d => d.count), backgroundColor: COLORS.slice(0, data.length), borderWidth: 2, borderColor: '#fff' }],
                },
                options: { responsive: true, maintainAspectRatio: false,
                    plugins: { legend: { position: 'right', labels: { boxWidth: 12, font: { size: 11 } } } } },
            });
        }

        const condCanvas = document.getElementById('uni-asset-condition-chart');
        if (condCanvas && !condCanvas._chartInstance) {
            const data = this.state.assets.by_condition;
            const COLOR_MAP = { 'New':'#27AE60','Good':'#2ECC71','Fair':'#F39C12',
                'Poor':'#E67E22','Non-Functional':'#E74C3C','Condemned':'#8E44AD' };
            condCanvas._chartInstance = new Chart(condCanvas.getContext('2d'), {
                type: 'bar',
                data: {
                    labels: data.map(d => d.name),
                    datasets: [{ label: 'Assets', data: data.map(d => d.count),
                        backgroundColor: data.map(d => COLOR_MAP[d.name] || '#4A90D9'), borderRadius: 6 }],
                },
                options: { responsive: true, maintainAspectRatio: false,
                    plugins: { legend: { display: false } },
                    scales: { y: { beginAtZero: true, ticks: { stepSize: 1 } }, x: { grid: { display: false } } } },
            });
        }
    }

    formatAssetCurrency(val) {
        if (!val) return '₹ 0';
        if (val >= 10000000) return '₹ ' + (val / 10000000).toFixed(2) + ' Cr';
        if (val >= 100000) return '₹ ' + (val / 100000).toFixed(2) + ' L';
        if (val >= 1000) return '₹ ' + (val / 1000).toFixed(1) + ' K';
        return '₹ ' + val.toFixed(0);
    }

    assetStateClass(state) {
        const map = {
            draft:'warning', active:'success', audited:'info', under_maintenance:'warning',
            transferred:'primary', condemned:'danger', disposed:'danger', lost:'danger',
            completed:'success', in_progress:'warning', assigned:'info',
            approved:'info', pending_purchase:'warning', rejected:'danger', fulfilled:'success',
        };
        return map[state] || 'secondary';
    }

    assetStateLabel(state) {
        return (state || '').replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
    }

    openAssets() { this.navigateTo('university_management.action_asset_asset'); }
    openAssetRequests() { this.navigateTo('university_management.action_asset_request'); }
    openAssetMaintenance() { this.navigateTo('university_management.action_asset_maintenance'); }
    openAssetTransfers() { this.navigateTo('university_management.action_asset_transfer'); }

    updateState(data) {
        this.state.overview = { ...this.state.overview, ...data.overview };
        this.state.students = { ...this.state.students, ...data.students };
        this.state.faculty = { ...this.state.faculty, ...data.faculty };
        this.state.fees = { ...this.state.fees, ...data.fees };
        this.state.exams = { ...this.state.exams, ...data.exams };
        this.state.hostel = { ...this.state.hostel, ...data.hostel };
        this.state.library = { ...this.state.library, ...data.library };

        this.state.recentAdmissions = data.recent_admissions || [];
        this.state.recentPayments = data.recent_payments || [];
        this.state.departmentStats = data.department_stats || [];
        this.state.feeCollectionMonthly = data.fee_monthly || [];
        this.state.semesterAdmissions = data.semester_admissions || [];
    }

    setActiveModule(module) {
        this.state.activeModule = module;

        const content = document.querySelector('.uni-main-content');
        if (content) {
            content.scrollTo({
                top: 0,
                behavior: 'smooth'
            });
        }

        setTimeout(() => {
            UniversityCharts.renderForModule(module, this.state);
            if (module === 'assets') {
                const c1 = document.getElementById('uni-asset-category-chart');
                const c2 = document.getElementById('uni-asset-condition-chart');
                if (c1) delete c1._chartInstance;
                if (c2) delete c2._chartInstance;
                this._renderAssetCharts();
            }
        }, 150);
    }

    // Navigation methods
    navigateTo(actionName) {
        this.action.doAction(actionName);
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