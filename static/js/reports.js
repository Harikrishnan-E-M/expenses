(function () {
  const periodInput = document.getElementById('period-input');
  const rangeInput = document.getElementById('range-value-input');
  const rangeSelect = document.getElementById('range-select');
  const rangeSpinner = document.getElementById('range-spinner');
  const pdfBtn = document.getElementById('pdf-download-btn');
  const periodBtns = document.querySelectorAll('.period-btn');

  if (!periodInput || !rangeInput || !rangeSelect || !pdfBtn || !periodBtns.length) {
    return;
  }

  let currentPeriod = periodInput.value || 'month';
  let currentRange = rangeInput.value || '';

  function updatePdfLink() {
    const url = new URL(pdfBtn.getAttribute('href'), window.location.origin);
    url.searchParams.set('period', currentPeriod);
    url.searchParams.set('range_value', currentRange);
    pdfBtn.setAttribute('href', url.toString());
  }

  async function loadRanges(period, selectValue) {
    if (rangeSpinner) {
      rangeSpinner.classList.add('visible');
    }
    rangeSelect.style.display = 'none';
    try {
      const response = await fetch(`/reports/ranges?period=${encodeURIComponent(period)}`);
      const items = await response.json();
      rangeSelect.innerHTML = '';
      items.forEach((item) => {
        const option = document.createElement('option');
        option.value = item.value;
        option.textContent = item.label;
        if (item.value === selectValue) {
          option.selected = true;
        }
        rangeSelect.appendChild(option);
      });
      if (!rangeSelect.value && items.length) {
        rangeSelect.value = items[0].value;
      }
      currentRange = rangeSelect.value;
      rangeInput.value = currentRange;
      updatePdfLink();
    } catch (error) {
      console.error('Failed to load ranges', error);
    } finally {
      if (rangeSpinner) {
        rangeSpinner.classList.remove('visible');
      }
      rangeSelect.style.display = '';
    }
  }

  periodBtns.forEach((button) => {
    button.addEventListener('click', () => {
      periodBtns.forEach((item) => item.classList.remove('active'));
      button.classList.add('active');
      currentPeriod = button.dataset.period;
      periodInput.value = currentPeriod;
      loadRanges(currentPeriod, '');
    });
  });

  rangeSelect.addEventListener('change', () => {
    currentRange = rangeSelect.value;
    rangeInput.value = currentRange;
    updatePdfLink();
  });

  updatePdfLink();

  const INCOME_COLOR = 'rgba(52, 211, 153, 0.85)';
  const EXPENSE_COLOR = 'rgba(248, 113, 113, 0.85)';
  const PALETTE = [
    '#6366f1', '#8b5cf6', '#ec4899', '#f59e0b', '#10b981',
    '#06b6d4', '#f97316', '#14b8a6', '#3b82f6', '#22c55e',
  ];

  const amountLabelPlugin = {
    id: 'amountLabels',
    afterDatasetsDraw(chart) {
      const { ctx } = chart;
      chart.data.datasets.forEach((dataset, datasetIndex) => {
        const meta = chart.getDatasetMeta(datasetIndex);
        meta.data.forEach((element, index) => {
          const value = dataset.data[index];
          if (!value) {
            return;
          }
          const label = `₹${Number(value).toLocaleString('en-IN', { maximumFractionDigits: 0 })}`;
          ctx.save();
          ctx.fillStyle = '#fff';
          ctx.font = 'bold 11px Plus Jakarta Sans, sans-serif';
          ctx.textAlign = 'center';
          ctx.textBaseline = 'middle';

          if (chart.config.type === 'bar') {
            const { x, y, height } = element;
            if (height > 24) {
              ctx.fillText(label, x, y + height / 2);
            } else {
              ctx.fillStyle = '#cbd5e1';
              ctx.fillText(label, x, y - 8);
            }
          } else {
            const { x, y } = element.tooltipPosition();
            ctx.fillText(label, x, y);
          }
          ctx.restore();
        });
      });
    },
  };

  if (window.Chart && typeof window.Chart.register === 'function') {
    window.Chart.register(amountLabelPlugin);
  }

  function makeBarChart(canvasId, scriptId, color) {
    const canvas = document.getElementById(canvasId);
    const scriptEl = document.getElementById(scriptId);
    if (!canvas || !scriptEl) {
      return;
    }
    const existingChart = window.Chart && typeof window.Chart.getChart === 'function' ? window.Chart.getChart(canvas) : null;
    if (existingChart) {
      existingChart.destroy();
    }
    const data = JSON.parse(scriptEl.textContent || '{}');
    const hasAnyValue = Array.isArray(data.values) && data.values.some((value) => Number(value) > 0);
    if (!hasAnyValue) {
      const card = canvas.closest('.ft-chart-card');
      if (card && !card.querySelector('.report-empty-state')) {
        const emptyState = document.createElement('div');
        emptyState.className = 'report-empty-state ft-soft text-center mt-3';
        emptyState.style.fontSize = '.9rem';
        emptyState.style.padding = '.85rem 1rem';
        emptyState.style.border = '1px dashed rgba(255,255,255,0.18)';
        emptyState.style.borderRadius = '12px';
        emptyState.textContent = 'No transactions recorded in this range yet.';
        card.appendChild(emptyState);
      }
    }
    if (!data.labels || !data.labels.length) {
      const card = canvas.closest('.ft-chart-card');
      if (card) {
        card.insertAdjacentHTML('beforeend', '<p class="ft-soft text-center mt-3" style="font-size:.85rem;">No data for this period.</p>');
      }
      canvas.remove();
      return;
    }
    new window.Chart(canvas, {
      type: 'bar',
      data: {
        labels: data.labels,
        datasets: [{
          label: 'Amount (₹)',
          data: data.values,
          backgroundColor: color,
          borderRadius: 6,
          borderSkipped: false,
          minBarLength: 4,
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: {
              label: (context) => ` ₹${Number(context.raw).toLocaleString('en-IN', { minimumFractionDigits: 2 })}`,
            },
          },
        },
        scales: {
          x: { grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: '#9aa3b8', maxRotation: 45 } },
          y: { beginAtZero: true, grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: '#9aa3b8', callback: (value) => `₹${Number(value).toLocaleString('en-IN')}` } },
        },
      },
    });
  }

  function makePieChart(canvasId, scriptId, type) {
    const canvas = document.getElementById(canvasId);
    const scriptEl = document.getElementById(scriptId);
    if (!canvas || !scriptEl) {
      return;
    }
    const existingChart = window.Chart && typeof window.Chart.getChart === 'function' ? window.Chart.getChart(canvas) : null;
    if (existingChart) {
      existingChart.destroy();
    }
    const data = JSON.parse(scriptEl.textContent || '{}');
    if (!data.labels || !data.labels.length) {
      const card = canvas.closest('.ft-chart-card');
      if (card) {
        card.insertAdjacentHTML('beforeend', '<p class="ft-soft text-center mt-3" style="font-size:.85rem;">No data for this period.</p>');
      }
      canvas.remove();
      return;
    }
    new window.Chart(canvas, {
      type,
      data: {
        labels: data.labels,
        datasets: [{
          data: data.values,
          backgroundColor: PALETTE.slice(0, data.labels.length),
          borderWidth: 1,
          borderColor: 'rgba(255,255,255,0.08)',
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { position: 'bottom', labels: { color: '#cbd5e1', padding: 14, font: { size: 11 } } },
          tooltip: {
            callbacks: {
              label: (context) => ` ${context.label}: ₹${Number(context.raw).toLocaleString('en-IN', { minimumFractionDigits: 2 })}`,
            },
          },
        },
      },
    });
  }

  function renderPeriodCharts() {
    const periodDataEl = document.getElementById('reportPeriodData');
    const periodData = JSON.parse(periodDataEl ? periodDataEl.textContent || '{}' : '{}');
    Object.keys(periodData).forEach((key) => {
      makeBarChart(`income_${key}_bar`, `income_${key}_barData`, INCOME_COLOR);
      makeBarChart(`expense_${key}_bar`, `expense_${key}_barData`, EXPENSE_COLOR);
    });
  }

  function renderStaticCharts() {
    makePieChart('incomePie', 'incomePieData', 'pie');
    makePieChart('expensePie', 'expensePieData', 'pie');
  }

  document.addEventListener('DOMContentLoaded', () => {
    renderStaticCharts();
    renderPeriodCharts();
  });

  window.FinTrackReports = {
    loadRanges,
    updatePdfLink,
  };
})();