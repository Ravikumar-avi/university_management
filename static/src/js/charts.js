/* ============================================================
   UNIVERSITY MANAGEMENT SYSTEM - CHARTS.JS
   Enhanced with animations and interactive features
   ============================================================ */

const UniversityCharts = {

    instances: {},

    palette: {
        blue:   '#3b82f6',
        blueDark: '#2563eb',
        green:  '#10b981',
        greenDark: '#059669',
        amber:  '#f59e0b',
        amberDark: '#d97706',
        red:    '#ef4444',
        redDark: '#dc2626',
        purple: '#8b5cf6',
        purpleDark: '#7c3aed',
        teal:   '#14b8a6',
        tealDark: '#0d9488',
        navy:   '#1e293b',
        orange: '#f97316',
        orangeDark: '#ea580c',
        pink:   '#ec4899',
        pinkDark: '#db2777',
        indigo: '#6366f1',
        indigoDark: '#4f46e5',
        cyan:   '#06b6d4',
        cyanDark: '#0891b2',
    },

    multiColors: [
        '#3b82f6', '#10b981', '#f59e0b', '#ef4444',
        '#8b5cf6', '#14b8a6', '#f97316', '#1e293b',
        '#ec4899', '#6366f1', '#06b6d4',
    ],

    // ─────────────────────────────────────────────────────────────
    // INTERNAL HELPERS
    // ─────────────────────────────────────────────────────────────

    _destroy(id) {
        if (this.instances[id]) {
            this.instances[id].destroy();
            delete this.instances[id];
        }
    },

    _canvas(id) {
        return document.getElementById(id);
    },

    _gradient(ctx, color1, color2, direction = 'vertical') {
        if (direction === 'vertical') {
            const g = ctx.createLinearGradient(0, 0, 0, ctx.canvas.height);
            g.addColorStop(0, color1);
            g.addColorStop(0.6, color2 || color1);
            g.addColorStop(1, color2 ? color2 + 'dd' : color1 + 'dd');
            return g;
        } else {
            const g = ctx.createLinearGradient(0, 0, ctx.canvas.width, 0);
            g.addColorStop(0, color1);
            g.addColorStop(1, color2 || color1);
            return g;
        }
    },

    _initDefaults() {
        if (typeof Chart === 'undefined') {
            console.warn('[UniversityCharts] Chart.js not loaded yet.');
            return false;
        }
        Chart.defaults.font.family = "'Inter', 'Segoe UI', 'Roboto', Arial, sans-serif";
        Chart.defaults.color = '#64748b';
        Chart.defaults.plugins.legend.labels.boxWidth = 12;
        Chart.defaults.plugins.legend.labels.padding = 12;
        Chart.defaults.plugins.legend.labels.font = { size: 12, weight: '500' };
        Chart.defaults.plugins.tooltip.backgroundColor = 'rgba(30,41,59,0.95)';
        Chart.defaults.plugins.tooltip.padding = 12;
        Chart.defaults.plugins.tooltip.cornerRadius = 8;
        Chart.defaults.plugins.tooltip.titleFont = { size: 13, weight: '600' };
        Chart.defaults.plugins.tooltip.bodyFont  = { size: 12 };
        Chart.defaults.plugins.tooltip.boxPadding = 4;
        Chart.defaults.plugins.tooltip.usePointStyle = true;
        Chart.defaults.responsive = true;
        Chart.defaults.maintainAspectRatio = false;
        return true;
    },

    // ─────────────────────────────────────────────────────────────
    // 1. MONTHLY FEE COLLECTION TREND (Bar with animation)
    // ─────────────────────────────────────────────────────────────
    renderFeeTrend(feeMonthly) {
        const id = 'uni-fee-trend-chart';
        const canvas = this._canvas(id);
        if (!canvas || !feeMonthly.length) return;

        this._destroy(id);
        const ctx = canvas.getContext('2d');

        const labels = feeMonthly.map(m => m.label);
        const values = feeMonthly.map(m => m.value);

        this.instances[id] = new Chart(ctx, {
            type: 'bar',
            data: {
                labels,
                datasets: [{
                    label: 'Fee Collection',
                    data: values,
                    backgroundColor: (context) => {
                        const chart = context.chart;
                        const {ctx, chartArea} = chart;
                        if (!chartArea) return this.palette.green;
                        return this._gradient(ctx, this.palette.green, this.palette.teal);
                    },
                    borderColor: this.palette.greenDark,
                    borderWidth: 0,
                    borderRadius: 8,
                    barPercentage: 0.7,
                    categoryPercentage: 0.8,
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                animation: {
                    duration: 2000,
                    easing: 'easeInOutQuart',
                },
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        callbacks: {
                            label: (ctx) => {
                                let value = ctx.parsed.y;
                                if (value >= 10000000) return '₹ ' + (value/10000000).toFixed(2) + ' Cr';
                                if (value >= 100000) return '₹ ' + (value/100000).toFixed(2) + ' L';
                                if (value >= 1000) return '₹ ' + (value/1000).toFixed(2) + ' K';
                                return '₹ ' + value;
                            }
                        }
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        grid: { color: '#e2e8f0', drawBorder: false },
                        ticks: {
                            callback: (value) => {
                                if (value >= 10000000) return '₹' + (value/10000000).toFixed(1) + 'Cr';
                                if (value >= 100000) return '₹' + (value/100000).toFixed(1) + 'L';
                                if (value >= 1000) return '₹' + (value/1000).toFixed(1) + 'K';
                                return '₹' + value;
                            }
                        }
                    },
                    x: {
                        grid: { display: false },
                        ticks: { font: { size: 11, weight: '500' } }
                    }
                },
                onClick: (event, item) => {
                    if (item.length > 0) {
                        const index = item[0].index;
                        console.log('Month clicked:', labels[index], values[index]);
                    }
                }
            }
        });
    },

    // ─────────────────────────────────────────────────────────────
    // 2. SEMESTER ADMISSIONS TREND (Bar)
    // ─────────────────────────────────────────────────────────────
    renderSemesterAdmissions(semData) {
        const id = 'uni-semester-chart';
        const canvas = this._canvas(id);
        if (!canvas || !semData.length) return;

        this._destroy(id);
        const ctx = canvas.getContext('2d');

        this.instances[id] = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: semData.map(s => s.label),
                datasets: [{
                    label: 'Student Registrations',
                    data: semData.map(s => s.value),
                    backgroundColor: (context) => {
                        const chart = context.chart;
                        const {ctx, chartArea} = chart;
                        if (!chartArea) return this.palette.blue;
                        return this._gradient(ctx, this.palette.blue, this.palette.indigo);
                    },
                    borderColor: this.palette.blueDark,
                    borderWidth: 0,
                    borderRadius: 8,
                    barPercentage: 0.7,
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                animation: {
                    duration: 2000,
                    easing: 'easeInOutQuart',
                },
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        callbacks: {
                            label: (ctx) => `${ctx.parsed.y} students`
                        }
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        grid: { color: '#e2e8f0' },
                        ticks: { stepSize: 1 }
                    },
                    x: { grid: { display: false } }
                }
            }
        });
    },

    // ─────────────────────────────────────────────────────────────
    // 3. DEPARTMENT STUDENT DISTRIBUTION (Doughnut with animation)
    // ─────────────────────────────────────────────────────────────
    renderDepartmentDistribution(deptStats) {
        const id = 'uni-department-chart';
        const canvas = this._canvas(id);
        if (!canvas || !deptStats.length) return;

        this._destroy(id);
        const ctx = canvas.getContext('2d');

        this.instances[id] = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: deptStats.map(d => d.name),
                datasets: [{
                    data: deptStats.map(d => d.students),
                    backgroundColor: this.multiColors.slice(0, deptStats.length),
                    borderWidth: 3,
                    borderColor: '#ffffff',
                    hoverOffset: 15,
                    spacing: 4,
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                cutout: '65%',
                animation: {
                    animateRotate: true,
                    animateScale: true,
                    duration: 2000,
                    easing: 'easeInOutQuart',
                },
                plugins: {
                    legend: {
                        position: 'right',
                        labels: {
                            padding: 16,
                            usePointStyle: true,
                            pointStyle: 'circle',
                            generateLabels(chart) {
                                const data = chart.data;
                                const total = data.datasets[0].data.reduce((a, b) => a + b, 0);
                                return data.labels.map((label, i) => ({
                                    text: `${label} (${data.datasets[0].data[i]})`,
                                    fillStyle: data.datasets[0].backgroundColor[i],
                                    strokeStyle: '#fff',
                                    lineWidth: 2,
                                    hidden: false,
                                    index: i,
                                    pointStyle: 'circle',
                                }));
                            }
                        }
                    },
                    tooltip: {
                        callbacks: {
                            label: (ctx) => {
                                const total = ctx.dataset.data.reduce((a, b) => a + b, 0);
                                const value = ctx.parsed;
                                const percentage = ((value / total) * 100).toFixed(1);
                                return `${ctx.label}: ${value} students (${percentage}%)`;
                            }
                        }
                    }
                }
            }
        });
    },

    // ─────────────────────────────────────────────────────────────
    // 4. DEPARTMENT PLACEMENT % (Horizontal Bar)
    // ─────────────────────────────────────────────────────────────
    renderPlacementChart(deptStats) {
        const id = 'uni-placement-chart';
        const canvas = this._canvas(id);
        if (!canvas || !deptStats.length) return;

        this._destroy(id);
        const ctx = canvas.getContext('2d');

        this.instances[id] = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: deptStats.map(d => d.name),
                datasets: [{
                    label: 'Placement Rate',
                    data: deptStats.map(d => d.placement_rate),
                    backgroundColor: (context) => {
                        const value = context.raw;
                        if (value >= 80) return this.palette.green;
                        if (value >= 60) return this.palette.blue;
                        if (value >= 40) return this.palette.amber;
                        if (value >= 20) return this.palette.orange;
                        return this.palette.red;
                    },
                    borderRadius: 8,
                    barPercentage: 0.8,
                    categoryPercentage: 0.9,
                }]
            },
            options: {
                indexAxis: 'y',
                responsive: true,
                maintainAspectRatio: false,
                animation: {
                    duration: 2000,
                    easing: 'easeInOutQuart',
                },
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        callbacks: {
                            label: (ctx) => `${ctx.parsed.x}% placement rate`
                        }
                    }
                },
                scales: {
                    x: {
                        beginAtZero: true,
                        max: 100,
                        grid: { color: '#e2e8f0' },
                        ticks: {
                            callback: (v) => v + '%',
                            stepSize: 20
                        }
                    },
                    y: {
                        grid: { display: false },
                        ticks: { font: { weight: '600' } }
                    }
                }
            }
        });
    },

    // ─────────────────────────────────────────────────────────────
    // 5. PROGRAM DISTRIBUTION (Pie)
    // ─────────────────────────────────────────────────────────────
    renderProgramChart(programDist) {
        const id = 'uni-program-chart';
        const canvas = this._canvas(id);
        if (!canvas || !programDist || !programDist.length) return;

        this._destroy(id);
        const ctx = canvas.getContext('2d');

        this.instances[id] = new Chart(ctx, {
            type: 'pie',
            data: {
                labels: programDist.map(p => p.name),
                datasets: [{
                    data: programDist.map(p => p.count),
                    backgroundColor: this.multiColors.slice(0, programDist.length),
                    borderWidth: 3,
                    borderColor: '#ffffff',
                    hoverOffset: 15,
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                animation: {
                    animateRotate: true,
                    animateScale: true,
                    duration: 2000,
                },
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: {
                            padding: 16,
                            usePointStyle: true,
                            pointStyle: 'circle',
                        }
                    },
                    tooltip: {
                        callbacks: {
                            label: (ctx) => {
                                const total = ctx.dataset.data.reduce((a, b) => a + b, 0);
                                const percentage = ((ctx.parsed / total) * 100).toFixed(1);
                                return `${ctx.label}: ${ctx.parsed} students (${percentage}%)`;
                            }
                        }
                    }
                }
            }
        });
    },

    // ─────────────────────────────────────────────────────────────
    // 6. FACULTY STATUS (Doughnut)
    // ─────────────────────────────────────────────────────────────
    renderFacultyStatus(faculty) {
        const id = 'uni-faculty-status-chart';
        const canvas = this._canvas(id);
        if (!canvas) return;

        this._destroy(id);
        const ctx = canvas.getContext('2d');

        const present = faculty.present_today || 0;
        const onLeave = faculty.on_leave || 0;
        const total   = faculty.total || 0;
        const absent  = Math.max(0, total - present - onLeave);

        this.instances[id] = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: ['Present', 'On Leave', 'Absent'],
                datasets: [{
                    data: [present, onLeave, absent],
                    backgroundColor: [this.palette.green, this.palette.amber, this.palette.red],
                    borderWidth: 3,
                    borderColor: '#ffffff',
                    hoverOffset: 10,
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                cutout: '70%',
                animation: {
                    animateRotate: true,
                    animateScale: true,
                    duration: 2000,
                },
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: {
                            padding: 16,
                            usePointStyle: true,
                            pointStyle: 'circle',
                        }
                    },
                    tooltip: {
                        callbacks: {
                            label: (ctx) => `${ctx.label}: ${ctx.parsed} faculty`
                        }
                    }
                }
            }
        });
    },

    // ─────────────────────────────────────────────────────────────
    // 7. HOSTEL OCCUPANCY (Doughnut)
    // ─────────────────────────────────────────────────────────────
    renderHostelOccupancy(hostel) {
        const id = 'uni-hostel-chart';
        const canvas = this._canvas(id);
        if (!canvas) return;

        this._destroy(id);
        const ctx = canvas.getContext('2d');

        const occupied = hostel.occupied_rooms || 0;
        const vacant   = Math.max(0, (hostel.total_rooms || 0) - occupied);

        this.instances[id] = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: ['Occupied', 'Vacant'],
                datasets: [{
                    data: [occupied, vacant],
                    backgroundColor: [this.palette.teal, this.palette.navy + '20'],
                    borderWidth: 3,
                    borderColor: '#ffffff',
                    hoverOffset: 10,
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                cutout: '70%',
                animation: {
                    animateRotate: true,
                    animateScale: true,
                    duration: 2000,
                },
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: {
                            padding: 16,
                            usePointStyle: true,
                            pointStyle: 'circle',
                        }
                    },
                    tooltip: {
                        callbacks: {
                            label: (ctx) => `${ctx.label}: ${ctx.parsed} rooms`
                        }
                    }
                }
            }
        });
    },

    // ─────────────────────────────────────────────────────────────
    // 8. LIBRARY ACTIVITY (Bar)
    // ─────────────────────────────────────────────────────────────
    renderLibraryChart(library) {
        const id = 'uni-library-chart';
        const canvas = this._canvas(id);
        if (!canvas) return;

        this._destroy(id);
        const ctx = canvas.getContext('2d');

        this.instances[id] = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: ['Total Books', 'Currently Issued', 'Overdue'],
                datasets: [{
                    label: 'Books',
                    data: [
                        library.total_books  || 0,
                        library.books_issued || 0,
                        library.overdue      || 0,
                    ],
                    backgroundColor: [
                        this.palette.blue,
                        this.palette.green,
                        this.palette.red,
                    ],
                    borderRadius: 8,
                    barPercentage: 0.6,
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                animation: {
                    duration: 2000,
                    easing: 'easeInOutQuart',
                },
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        callbacks: {
                            label: (ctx) => `${ctx.parsed.y} books`
                        }
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        grid: { color: '#e2e8f0' },
                        ticks: { stepSize: 1 }
                    },
                    x: { grid: { display: false } }
                }
            }
        });
    },

    // ─────────────────────────────────────────────────────────────
    // MASTER RENDER
    // ─────────────────────────────────────────────────────────────
    renderAll(state) {
        if (!this._initDefaults()) return;

        // Fee trend
        if (state.feeCollectionMonthly && state.feeCollectionMonthly.length) {
            this.renderFeeTrend(state.feeCollectionMonthly);
        }

        // Semester admissions
        if (state.semesterAdmissions && state.semesterAdmissions.length) {
            this.renderSemesterAdmissions(state.semesterAdmissions);
        }

        // Department charts
        if (state.departmentStats && state.departmentStats.length) {
            this.renderDepartmentDistribution(state.departmentStats);
            this.renderPlacementChart(state.departmentStats);
        }

        // Program pie
        if (state.students && state.students.program_distribution) {
            this.renderProgramChart(state.students.program_distribution);
        }

        // Faculty doughnut
        if (state.faculty && state.faculty.total) {
            this.renderFacultyStatus(state.faculty);
        }

        // Hostel doughnut
        if (state.hostel && state.hostel.total_rooms) {
            this.renderHostelOccupancy(state.hostel);
        }

        // Library bar
        if (state.library) {
            this.renderLibraryChart(state.library);
        }
    },

    // ─────────────────────────────────────────────────────────────
    // Re-render only charts visible in the active module
    // ─────────────────────────────────────────────────────────────
    renderForModule(module, state) {
        if (!this._initDefaults()) return;

        setTimeout(() => {
            switch (module) {
                case 'overview':
                    if (state.feeCollectionMonthly?.length)
                        this.renderFeeTrend(state.feeCollectionMonthly);
                    if (state.departmentStats?.length)
                        this.renderDepartmentDistribution(state.departmentStats);
                    break;

                case 'students':
                    if (state.semesterAdmissions?.length)
                        this.renderSemesterAdmissions(state.semesterAdmissions);
                    if (state.students?.program_distribution)
                        this.renderProgramChart(state.students.program_distribution);
                    break;

                case 'faculty':
                    if (state.faculty?.total)
                        this.renderFacultyStatus(state.faculty);
                    break;

                case 'fees':
                    if (state.feeCollectionMonthly?.length)
                        this.renderFeeTrend(state.feeCollectionMonthly);
                    break;

                case 'hostel':
                    if (state.hostel?.total_rooms)
                        this.renderHostelOccupancy(state.hostel);
                    break;

                case 'library':
                    if (state.library)
                        this.renderLibraryChart(state.library);
                    break;

                case 'placement':
                    if (state.departmentStats?.length)
                        this.renderPlacementChart(state.departmentStats);
                    break;
            }
        }, 100);
    },

    destroyAll() {
        Object.keys(this.instances).forEach(id => this._destroy(id));
    },

    exportChart(chartId, filename) {
        const chart = this.instances[chartId];
        if (chart) {
            const a = document.createElement('a');
            a.href = chart.toBase64Image();
            a.download = filename || chartId + '.png';
            a.click();
        }
    },
};

export { UniversityCharts };