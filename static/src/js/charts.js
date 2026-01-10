/* ============================================
   UNIVERSITY MANAGEMENT SYSTEM - CHARTS.JS   Dashboard charts and data visualization   ============================================ */
odoo.define('university_management.charts', function (require) {
'use strict';

var AbstractAction = require('web.AbstractAction');
var core = require('web.core');
var rpc = require('web.rpc');
var QWeb = core.qweb;

/**
 * University Dashboard Charts Manager */var UniversityCharts = {

    // Chart instances storage
    chartInstances: {},

    // Default chart colors
    colors: {
        primary: '#667eea',
        secondary: '#764ba2',
        success: '#56ab2f',
        warning: '#f2994a',
        danger: '#eb3349',
        info: '#3a7bd5',
        light: '#f7fafc',
        dark: '#2d3748',
    },

    // Gradient definitions
    gradients: {
        primary: ['#667eea', '#764ba2'],
        success: ['#56ab2f', '#a8e063'],
        warning: ['#f2994a', '#f2c94c'],
        danger: ['#eb3349', '#f45c43'],
        info: ['#3a7bd5', '#00d2ff'],
    },

    /**
     * Initialize Chart.js defaults     */    initChartDefaults: function() {
        if (typeof Chart !== 'undefined') {
            Chart.defaults.font.family = "'Roboto', 'Segoe UI', Arial, sans-serif";
            Chart.defaults.color = '#718096';
            Chart.defaults.plugins.legend.display = true;
            Chart.defaults.plugins.legend.position = 'bottom';
            Chart.defaults.plugins.tooltip.backgroundColor = 'rgba(45, 55, 72, 0.9)';
            Chart.defaults.plugins.tooltip.padding = 12;
            Chart.defaults.plugins.tooltip.cornerRadius = 8;
            Chart.defaults.plugins.tooltip.titleFont.size = 14;
            Chart.defaults.plugins.tooltip.bodyFont.size = 13;
        }
    },

    /**
     * Create gradient for canvas     */    createGradient: function(ctx, colors, horizontal = false) {
        var gradient;
        if (horizontal) {
            gradient = ctx.createLinearGradient(0, 0, ctx.canvas.width, 0);
        } else {
            gradient = ctx.createLinearGradient(0, 0, 0, ctx.canvas.height);
        }

        if (colors.length === 2) {
            gradient.addColorStop(0, colors[0]);
            gradient.addColorStop(1, colors[1]);
        } else {
            var step = 1 / (colors.length - 1);
            colors.forEach(function(color, index) {
                gradient.addColorStop(step * index, color);
            });
        }

        return gradient;
    },

    /**
     * Destroy chart instance     */    destroyChart: function(chartId) {
        if (this.chartInstances[chartId]) {
            this.chartInstances[chartId].destroy();
            delete this.chartInstances[chartId];
        }
    },

    /**
     * Create Student Enrollment Chart (Line Chart)     */    createEnrollmentChart: function(canvasId, data) {
        var self = this;
        var canvas = document.getElementById(canvasId);
        if (!canvas) return;

        var ctx = canvas.getContext('2d');
        var gradient = this.createGradient(ctx, this.gradients.primary);

        this.destroyChart(canvasId);

        this.chartInstances[canvasId] = new Chart(ctx, {
            type: 'line',
            data: {
                labels: data.labels || [],
                datasets: [{
                    label: 'Student Enrollment',
                    data: data.values || [],
                    backgroundColor: gradient,
                    borderColor: this.colors.primary,
                    borderWidth: 3,
                    fill: true,
                    tension: 0.4,
                    pointRadius: 5,
                    pointHoverRadius: 7,
                    pointBackgroundColor: '#fff',
                    pointBorderWidth: 2,
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    },
                    title: {
                        display: true,
                        text: 'Monthly Student Enrollment Trend',
                        font: { size: 16, weight: 'bold' },
                        color: '#2d3748'
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        grid: {
                            color: '#e2e8f0',
                            drawBorder: false
                        },
                        ticks: {
                            stepSize: 10
                        }
                    },
                    x: {
                        grid: {
                            display: false
                        }
                    }
                }
            }
        });
    },

    /**
     * Create Department Distribution Chart (Pie Chart)     */    createDepartmentChart: function(canvasId, data) {
        var self = this;
        var canvas = document.getElementById(canvasId);
        if (!canvas) return;

        var ctx = canvas.getContext('2d');

        this.destroyChart(canvasId);

        this.chartInstances[canvasId] = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: data.labels || [],
                datasets: [{
                    data: data.values || [],
                    backgroundColor: [
                        '#667eea',
                        '#56ab2f',
                        '#f2994a',
                        '#eb3349',
                        '#3a7bd5',
                        '#764ba2',
                        '#a8e063',
                        '#f2c94c'
                    ],
                    borderWidth: 2,
                    borderColor: '#fff',
                    hoverOffset: 10
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'right',
                        labels: {
                            padding: 15,
                            font: { size: 12 },
                            generateLabels: function(chart) {
                                const data = chart.data;
                                if (data.labels.length && data.datasets.length) {
                                    return data.labels.map((label, i) => {
                                        const value = data.datasets[0].data[i];
                                        const total = data.datasets[0].data.reduce((a, b) => a + b, 0);
                                        const percentage = ((value / total) * 100).toFixed(1);
                                        return {
                                            text: `${label} (${percentage}%)`,
                                            fillStyle: data.datasets[0].backgroundColor[i],
                                            index: i
                                        };
                                    });
                                }
                                return [];
                            }
                        }
                    },
                    title: {
                        display: true,
                        text: 'Students by Department',
                        font: { size: 16, weight: 'bold' },
                        color: '#2d3748'
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                let label = context.label || '';
                                let value = context.parsed;
                                let total = context.dataset.data.reduce((a, b) => a + b, 0);
                                let percentage = ((value / total) * 100).toFixed(1);
                                return `${label}: ${value} (${percentage}%)`;
                            }
                        }
                    }
                }
            }
        });
    },

    /**
     * Create Attendance Overview Chart (Bar Chart)     */    createAttendanceChart: function(canvasId, data) {
        var self = this;
        var canvas = document.getElementById(canvasId);
        if (!canvas) return;

        var ctx = canvas.getContext('2d');

        this.destroyChart(canvasId);

        this.chartInstances[canvasId] = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: data.labels || [],
                datasets: [
                    {
                        label: 'Present',
                        data: data.present || [],
                        backgroundColor: this.colors.success,
                        borderRadius: 8,
                        barThickness: 20
                    },
                    {
                        label: 'Absent',
                        data: data.absent || [],
                        backgroundColor: this.colors.danger,
                        borderRadius: 8,
                        barThickness: 20
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: true,
                        position: 'top'
                    },
                    title: {
                        display: true,
                        text: 'Attendance Overview',
                        font: { size: 16, weight: 'bold' },
                        color: '#2d3748'
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        stacked: false,
                        grid: {
                            color: '#e2e8f0'
                        }
                    },
                    x: {
                        stacked: false,
                        grid: {
                            display: false
                        }
                    }
                }
            }
        });
    },

    /**
     * Create Fee Collection Chart (Mixed Chart)     */    createFeeChart: function(canvasId, data) {
        var self = this;
        var canvas = document.getElementById(canvasId);
        if (!canvas) return;

        var ctx = canvas.getContext('2d');

        this.destroyChart(canvasId);

        this.chartInstances[canvasId] = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: data.labels || [],
                datasets: [
                    {
                        type: 'bar',
                        label: 'Collected',
                        data: data.collected || [],
                        backgroundColor: this.colors.success,
                        borderRadius: 8,
                        order: 2
                    },
                    {
                        type: 'bar',
                        label: 'Pending',
                        data: data.pending || [],
                        backgroundColor: this.colors.warning,
                        borderRadius: 8,
                        order: 2
                    },
                    {
                        type: 'line',
                        label: 'Target',
                        data: data.target || [],
                        borderColor: this.colors.primary,
                        borderWidth: 3,
                        borderDash: [5, 5],
                        fill: false,
                        pointRadius: 5,
                        order: 1
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: true,
                        position: 'top'
                    },
                    title: {
                        display: true,
                        text: 'Fee Collection Status',
                        font: { size: 16, weight: 'bold' },
                        color: '#2d3748'
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        grid: {
                            color: '#e2e8f0'
                        },
                        ticks: {
                            callback: function(value) {
                                return '₹' + value.toLocaleString();
                            }
                        }
                    },
                    x: {
                        grid: {
                            display: false
                        }
                    }
                }
            }
        });
    },

    /**
     * Create Performance Chart (Radar Chart)     */    createPerformanceChart: function(canvasId, data) {
        var self = this;
        var canvas = document.getElementById(canvasId);
        if (!canvas) return;

        var ctx = canvas.getContext('2d');

        this.destroyChart(canvasId);

        this.chartInstances[canvasId] = new Chart(ctx, {
            type: 'radar',
            data: {
                labels: data.labels || [],
                datasets: [{
                    label: 'Student Performance',
                    data: data.values || [],
                    backgroundColor: 'rgba(102, 126, 234, 0.2)',
                    borderColor: this.colors.primary,
                    borderWidth: 2,
                    pointBackgroundColor: this.colors.primary,
                    pointBorderColor: '#fff',
                    pointHoverBackgroundColor: '#fff',
                    pointHoverBorderColor: this.colors.primary,
                    pointRadius: 5,
                    pointHoverRadius: 7
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    },
                    title: {
                        display: true,
                        text: 'Academic Performance Analysis',
                        font: { size: 16, weight: 'bold' },
                        color: '#2d3748'
                    }
                },
                scales: {
                    r: {
                        beginAtZero: true,
                        max: 100,
                        ticks: {
                            stepSize: 20
                        },
                        grid: {
                            color: '#e2e8f0'
                        },
                        pointLabels: {
                            font: { size: 12 }
                        }
                    }
                }
            }
        });
    },

    /**
     * Create Placement Statistics Chart (Horizontal Bar)     */    createPlacementChart: function(canvasId, data) {
        var self = this;
        var canvas = document.getElementById(canvasId);
        if (!canvas) return;

        var ctx = canvas.getContext('2d');

        this.destroyChart(canvasId);

        this.chartInstances[canvasId] = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: data.labels || [],
                datasets: [{
                    label: 'Placement Percentage',
                    data: data.values || [],
                    backgroundColor: function(context) {
                        const value = context.parsed.x;
                        if (value >= 80) return self.colors.success;
                        if (value >= 60) return self.colors.info;
                        if (value >= 40) return self.colors.warning;
                        return self.colors.danger;
                    },
                    borderRadius: 8,
                    barThickness: 25
                }]
            },
            options: {
                indexAxis: 'y',
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    },
                    title: {
                        display: true,
                        text: 'Department-wise Placement Rate',
                        font: { size: 16, weight: 'bold' },
                        color: '#2d3748'
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                return context.parsed.x + '%';
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        beginAtZero: true,
                        max: 100,
                        grid: {
                            color: '#e2e8f0'
                        },
                        ticks: {
                            callback: function(value) {
                                return value + '%';
                            }
                        }
                    },
                    y: {
                        grid: {
                            display: false
                        }
                    }
                }
            }
        });
    },

    /**
     * Create Gender Distribution Chart (Pie Chart)     */    createGenderChart: function(canvasId, data) {
        var self = this;
        var canvas = document.getElementById(canvasId);
        if (!canvas) return;

        var ctx = canvas.getContext('2d');

        this.destroyChart(canvasId);

        this.chartInstances[canvasId] = new Chart(ctx, {
            type: 'pie',
            data: {
                labels: ['Male', 'Female', 'Other'],
                datasets: [{
                    data: [data.male || 0, data.female || 0, data.other || 0],
                    backgroundColor: [
                        this.colors.info,
                        this.colors.danger,
                        this.colors.warning
                    ],
                    borderWidth: 2,
                    borderColor: '#fff'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom'
                    },
                    title: {
                        display: true,
                        text: 'Gender Distribution',
                        font: { size: 16, weight: 'bold' },
                        color: '#2d3748'
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                let label = context.label || '';
                                let value = context.parsed;
                                let total = context.dataset.data.reduce((a, b) => a + b, 0);
                                let percentage = ((value / total) * 100).toFixed(1);
                                return `${label}: ${value} (${percentage}%)`;
                            }
                        }
                    }
                }
            }
        });
    },

    /**
     * Create Library Statistics Chart (Line Chart)     */    createLibraryChart: function(canvasId, data) {
        var self = this;
        var canvas = document.getElementById(canvasId);
        if (!canvas) return;

        var ctx = canvas.getContext('2d');

        this.destroyChart(canvasId);

        this.chartInstances[canvasId] = new Chart(ctx, {
            type: 'line',
            data: {
                labels: data.labels || [],
                datasets: [
                    {
                        label: 'Books Issued',
                        data: data.issued || [],
                        borderColor: this.colors.primary,
                        backgroundColor: 'rgba(102, 126, 234, 0.1)',
                        borderWidth: 2,
                        tension: 0.4,
                        fill: true
                    },
                    {
                        label: 'Books Returned',
                        data: data.returned || [],
                        borderColor: this.colors.success,
                        backgroundColor: 'rgba(86, 171, 47, 0.1)',
                        borderWidth: 2,
                        tension: 0.4,
                        fill: true
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: true,
                        position: 'top'
                    },
                    title: {
                        display: true,
                        text: 'Library Activity',
                        font: { size: 16, weight: 'bold' },
                        color: '#2d3748'
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
            }
        });
    },

    /**
     * Create Exam Results Distribution (Bar Chart)     */    createExamResultsChart: function(canvasId, data) {
        var self = this;
        var canvas = document.getElementById(canvasId);
        if (!canvas) return;

        var ctx = canvas.getContext('2d');

        this.destroyChart(canvasId);

        this.chartInstances[canvasId] = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: ['0-40', '41-50', '51-60', '61-70', '71-80', '81-90', '91-100'],
                datasets: [{
                    label: 'Number of Students',
                    data: data.distribution || [],
                    backgroundColor: [
                        this.colors.danger,
                        this.colors.warning,
                        '#f2c94c',
                        this.colors.info,
                        this.colors.primary,
                        '#a8e063',
                        this.colors.success
                    ],
                    borderRadius: 8
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    },
                    title: {
                        display: true,
                        text: 'Marks Distribution',
                        font: { size: 16, weight: 'bold' },
                        color: '#2d3748'
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        grid: {
                            color: '#e2e8f0'
                        },
                        ticks: {
                            stepSize: 5
                        }
                    },
                    x: {
                        grid: {
                            display: false
                        }
                    }
                }
            }
        });
    },

    /**
     * Load dashboard data from server     */    loadDashboardData: function(dashboardType) {
        var self = this;
        return rpc.query({
            route: '/university/dashboard/' + dashboardType,
            params: {}
        }).then(function(result) {
            if (result.success) {
                return result.data;
            }
            return null;
        });
    },

    /**
     * Update all charts     */    updateAllCharts: function(dashboardType) {
        var self = this;
        this.loadDashboardData(dashboardType).then(function(data) {
            if (data) {
                // Update each chart based on available data
                if (data.enrollment) {
                    self.createEnrollmentChart('enrollment-chart', data.enrollment);
                }
                if (data.departments) {
                    self.createDepartmentChart('department-chart', data.departments);
                }
                if (data.attendance) {
                    self.createAttendanceChart('attendance-chart', data.attendance);
                }
                if (data.fees) {
                    self.createFeeChart('fee-chart', data.fees);
                }
                if (data.performance) {
                    self.createPerformanceChart('performance-chart', data.performance);
                }
                if (data.placement) {
                    self.createPlacementChart('placement-chart', data.placement);
                }
                if (data.gender) {
                    self.createGenderChart('gender-chart', data.gender);
                }
                if (data.library) {
                    self.createLibraryChart('library-chart', data.library);
                }
                if (data.examResults) {
                    self.createExamResultsChart('exam-results-chart', data.examResults);
                }
            }
        });
    },

    /**
     * Export chart as image     */    exportChart: function(chartId, filename) {
        var chart = this.chartInstances[chartId];
        if (chart) {
            var url = chart.toBase64Image();
            var a = document.createElement('a');
            a.href = url;
            a.download = filename || 'chart.png';
            a.click();
        }
    },

    /**
     * Refresh specific chart     */    refreshChart: function(chartId, data) {
        var canvas = document.getElementById(chartId);
        if (!canvas) return;

        var chartType = canvas.dataset.chartType;

        switch(chartType) {
            case 'enrollment':
                this.createEnrollmentChart(chartId, data);
                break;
            case 'department':
                this.createDepartmentChart(chartId, data);
                break;
            case 'attendance':
                this.createAttendanceChart(chartId, data);
                break;
            case 'fee':
                this.createFeeChart(chartId, data);
                break;
            case 'performance':
                this.createPerformanceChart(chartId, data);
                break;
            case 'placement':
                this.createPlacementChart(chartId, data);
                break;
            case 'gender':
                this.createGenderChart(chartId, data);
                break;
            case 'library':
                this.createLibraryChart(chartId, data);
                break;
            case 'examResults':
                this.createExamResultsChart(chartId, data);
                break;
        }
    },

    /**
     * Initialize responsive chart resizing     */    initResponsiveCharts: function() {
        var self = this;
        window.addEventListener('resize', _.debounce(function() {
            Object.keys(self.chartInstances).forEach(function(chartId) {
                if (self.chartInstances[chartId]) {
                    self.chartInstances[chartId].resize();
                }
            });
        }, 300));
    },

    /**
     * Initialize all charts     */    init: function() {
        this.initChartDefaults();
        this.initResponsiveCharts();
        console.log('University Charts initialized');
    }
};

// Initialize charts when document is ready
$(document).ready(function() {
    UniversityCharts.init();
});

return UniversityCharts;

});


/* ============================================
   VANILLA JS VERSION (For Portal/Website)   Can be used without Odoo framework   ============================================ */
var UniversityChartsVanilla = (function() {
    'use strict';

    var chartInstances = {};

    var colors = {
        primary: '#667eea',
        secondary: '#764ba2',
        success: '#56ab2f',
        warning: '#f2994a',
        danger: '#eb3349',
        info: '#3a7bd5',
    };

    function createGradient(ctx, colors, horizontal) {
        var gradient;
        if (horizontal) {
            gradient = ctx.createLinearGradient(0, 0, ctx.canvas.width, 0);
        } else {
            gradient = ctx.createLinearGradient(0, 0, 0, ctx.canvas.height);
        }
        gradient.addColorStop(0, colors[0]);
        gradient.addColorStop(1, colors[1]);
        return gradient;
    }

    function destroyChart(chartId) {
        if (chartInstances[chartId]) {
            chartInstances[chartId].destroy();
            delete chartInstances[chartId];
        }
    }

    function createStudentProgressChart(canvasId, data) {
        var canvas = document.getElementById(canvasId);
        if (!canvas) return;

        var ctx = canvas.getContext('2d');
        destroyChart(canvasId);

        chartInstances[canvasId] = new Chart(ctx, {
            type: 'line',
            data: {
                labels: data.semesters,
                datasets: [{
                    label: 'CGPA',
                    data: data.cgpa,
                    borderColor: colors.primary,
                    backgroundColor: createGradient(ctx, [colors.primary, colors.secondary]),
                    fill: true,
                    tension: 0.4,
                    pointRadius: 6,
                    pointHoverRadius: 8
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    title: {
                        display: true,
                        text: 'Academic Progress',
                        font: { size: 18, weight: 'bold' }
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        max: 10,
                        ticks: { stepSize: 1 }
                    }
                }
            }
        });
    }

    function createAttendanceOverviewChart(canvasId, data) {
        var canvas = document.getElementById(canvasId);
        if (!canvas) return;

        var ctx = canvas.getContext('2d');
        destroyChart(canvasId);

        chartInstances[canvasId] = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: ['Present', 'Absent', 'Leave'],
                datasets: [{
                    data: [data.present, data.absent, data.leave],
                    backgroundColor: [colors.success, colors.danger, colors.warning],
                    borderWidth: 2,
                    borderColor: '#fff'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { position: 'bottom' },
                    title: {
                        display: true,
                        text: 'Attendance Overview',
                        font: { size: 18, weight: 'bold' }
                    }
                }
            }
        });
    }

    function loadChartData(url) {
        return fetch(url)
            .then(response => response.json())
            .catch(error => {
                console.error('Error loading chart data:', error);
                return null;
            });
    }

    return {
        createStudentProgressChart: createStudentProgressChart,
        createAttendanceOverviewChart: createAttendanceOverviewChart,
        loadChartData: loadChartData,
        destroyChart: destroyChart,
        chartInstances: chartInstances
    };
})();

// Auto-initialize charts on page load
if (typeof Chart !== 'undefined') {
    document.addEventListener('DOMContentLoaded', function() {
        console.log('University Charts (Vanilla) initialized');
    });
}