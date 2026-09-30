/**
 * SmartWasteX Chart.js Dashboard Visualizations
 */

document.addEventListener('DOMContentLoaded', () => {
    if (!window.SMARTWASTE_CHART_DATA) return;
    const data = window.SMARTWASTE_CHART_DATA;

    // Common Chart Defaults
    Chart.defaults.font.family = "'Inter', sans-serif";
    Chart.defaults.color = '#64748b';

    // 1. Waste Category Distribution (Doughnut)
    const catCanvas = document.getElementById('categoryDistributionChart');
    if (catCanvas && data.category_distribution) {
        new Chart(catCanvas, {
            type: 'doughnut',
            data: {
                labels: data.category_distribution.labels,
                datasets: [{
                    data: data.category_distribution.data,
                    backgroundColor: ['#3b82f6', '#10b981', '#ef4444'],
                    borderWidth: 2,
                    borderColor: '#ffffff',
                    hoverOffset: 6
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: { boxWidth: 12, padding: 15, font: { weight: '600' } }
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                return ` ${context.label}: ${context.raw} kg diverted`;
                            }
                        }
                    }
                },
                cutout: '70%'
            }
        });
    }

    // 2. Bin Capacity Telemetry (Horizontal Bar)
    const binCanvas = document.getElementById('binCapacityChart');
    if (binCanvas && data.bin_capacity) {
        const bgColors = data.bin_capacity.data.map(val => {
            if (val >= 100) return '#dc2626';
            if (val >= 85) return '#ea580c';
            if (val >= 70) return '#f59e0b';
            return '#10b981';
        });

        new Chart(binCanvas, {
            type: 'bar',
            data: {
                labels: data.bin_capacity.labels,
                datasets: [{
                    label: 'Fill Level (%)',
                    data: data.bin_capacity.data,
                    backgroundColor: bgColors,
                    borderRadius: 6,
                    barThickness: 20
                }]
            },
            options: {
                indexAxis: 'y',
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    x: {
                        min: 0,
                        max: 100,
                        ticks: { callback: v => v + '%' },
                        grid: { color: '#f1f5f9' }
                    },
                    y: {
                        grid: { display: false }
                    }
                },
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        callbacks: {
                            afterLabel: function(ctx) {
                                if (ctx.raw >= 85) return '⚠️ Collection Recommended!';
                                return 'Status: Normal';
                            }
                        }
                    }
                }
            }
        });
    }

    // 3. Waste Processed Over Time (Stacked Area / Multi-line)
    const trendCanvas = document.getElementById('wasteTrendChart');
    if (trendCanvas && data.waste_trend) {
        new Chart(trendCanvas, {
            type: 'line',
            data: {
                labels: data.waste_trend.labels,
                datasets: [
                    {
                        label: 'Dry Recyclables (kg)',
                        data: data.waste_trend.dry,
                        borderColor: '#3b82f6',
                        backgroundColor: 'rgba(59, 130, 246, 0.1)',
                        fill: true,
                        tension: 0.35,
                        borderWidth: 2
                    },
                    {
                        label: 'Biodegradable (kg)',
                        data: data.waste_trend.bio,
                        borderColor: '#10b981',
                        backgroundColor: 'rgba(16, 185, 129, 0.1)',
                        fill: true,
                        tension: 0.35,
                        borderWidth: 2
                    },
                    {
                        label: 'E-Waste (kg)',
                        data: data.waste_trend.ewaste,
                        borderColor: '#ef4444',
                        backgroundColor: 'rgba(239, 68, 68, 0.1)',
                        fill: true,
                        tension: 0.35,
                        borderWidth: 2
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: { mode: 'index', intersect: false },
                scales: {
                    y: {
                        beginAtZero: true,
                        grid: { color: '#f1f5f9' }
                    },
                    x: {
                        grid: { display: false }
                    }
                },
                plugins: {
                    legend: {
                        position: 'top',
                        labels: { boxWidth: 12, padding: 12, font: { weight: '600' } }
                    }
                }
            }
        });
    }

    // 4. Green Credits Activity (Bar)
    const creditsCanvas = document.getElementById('creditsActivityChart');
    if (creditsCanvas && data.credits_activity) {
        new Chart(creditsCanvas, {
            type: 'bar',
            data: {
                labels: data.credits_activity.labels,
                datasets: [{
                    label: 'Green Credits Earned',
                    data: data.credits_activity.credits,
                    backgroundColor: 'rgba(5, 150, 105, 0.85)',
                    hoverBackgroundColor: '#047857',
                    borderRadius: 6
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: { beginAtZero: true, grid: { color: '#f1f5f9' } },
                    x: { grid: { display: false } }
                },
                plugins: {
                    legend: { display: false }
                }
            }
        });
    }
});
