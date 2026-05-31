function parseChartConfig(scriptId) {
  const script = document.getElementById(scriptId);
  if (!script) {
    return null;
  }
  return JSON.parse(script.textContent);
}

function buildDataset(type, config) {
  const palette = config.colors || [
    '#0f4c81', '#12b981', '#f59e0b', '#ef4444', '#8b5cf6', '#06b6d4', '#14b8a6', '#f97316', '#22c55e', '#3b82f6'
  ];
  const colors = config.colors || palette;
  if (type === 'line') {
    return {
      labels: config.labels || config.trend_labels || [],
      datasets: [{
        label: config.title,
        data: config.values || config.trend_values || [],
        borderColor: config.borderColor || '#0f4c81',
        backgroundColor: 'rgba(15, 76, 129, 0.08)',
        tension: 0.32,
        fill: true,
        pointRadius: 3,
      }],
    };
  }
  return {
    labels: config.labels || config.trend_labels || [],
    datasets: [{
      label: config.title,
      data: config.values || config.trend_values || [],
      backgroundColor: colors.slice(0, config.values.length),
      borderWidth: 1,
    }],
  };
}

function renderChart(canvasId, scriptId, type, configOverrides = {}) {
  const canvas = document.getElementById(canvasId);
  if (!canvas) {
    return;
  }
  const config = { ...parseChartConfig(scriptId), ...configOverrides };
  if (!config || !config.labels) {
    return;
  }
  const chartConfig = {
    type,
    data: buildDataset(type, config),
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { position: type === 'line' ? 'top' : 'bottom' },
      },
      scales: type === 'line' || type === 'bar' ? {
        y: { beginAtZero: true, ticks: { precision: 0 } },
      } : {},
    },
  };

  new Chart(canvas, chartConfig);
}

function autoRenderCharts() {
  const chartDefinitions = [
    ['dashboardExpenseChart', 'dashboardExpenseChartData', 'doughnut'],
    ['dashboardIncomeChart', 'dashboardIncomeChartData', 'pie'],
    ['expensePie', 'expensePieData', 'pie'],
    ['incomePie', 'incomePieData', 'pie'],
    ['expenseDoughnut', 'expenseDoughnutData', 'doughnut'],
    ['incomeDoughnut', 'incomeDoughnutData', 'doughnut'],
    ['expenseBar', 'expenseBarData', 'bar'],
    ['incomeBar', 'incomeBarData', 'bar'],
    ['expenseLine', 'expenseLineData', 'line'],
    ['incomeLine', 'incomeLineData', 'line'],
  ];

  chartDefinitions.forEach(([canvasId, scriptId, type]) => renderChart(canvasId, scriptId, type));
}

document.addEventListener('DOMContentLoaded', autoRenderCharts);

window.FinTrackCharts = { renderChart, autoRenderCharts };
