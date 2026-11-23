/**
 * AquaSense IoT & ML Water Quality Detection System
 * Real-time WebSocket streaming, Chart.js telemetry waveforms, AI diagnostics & alerts.
 */

// Global State
const state = {
  ws: null,
  wsConnected: false,
  streamActive: true,
  audioMuted: false,
  currentScenario: 'municipal_tap',
  history: [],
  maxHistoryPoints: 30,
  alerts: []
};

// Audio Synthesizer for Critical Contamination Alarms (Web Audio API)
let audioCtx = null;
function playAlarmSound() {
  if (state.audioMuted) return;
  try {
    if (!audioCtx) {
      audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    }
    if (audioCtx.state === 'suspended') {
      audioCtx.resume();
    }
    const osc = audioCtx.createOscillator();
    const gain = audioCtx.createGain();
    osc.type = 'triangle';
    osc.frequency.setValueAtTime(880, audioCtx.currentTime); // A5 note
    osc.frequency.exponentialRampToValueAtTime(440, audioCtx.currentTime + 0.3);
    gain.gain.setValueAtTime(0.2, audioCtx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.01, audioCtx.currentTime + 0.3);
    osc.connect(gain);
    gain.connect(audioCtx.destination);
    osc.start();
    osc.stop(audioCtx.currentTime + 0.3);
  } catch (e) {
    console.warn('Audio alert error:', e);
  }
}

// ---------------- CHARTS SETUP ----------------
let timelineChart = null;
let radarChart = null;

function initCharts() {
  // 1. Live Multi-Probe Timeline Chart
  const ctxTimeline = document.getElementById('liveTimelineChart').getContext('2d');
  timelineChart = new Chart(ctxTimeline, {
    type: 'line',
    data: {
      labels: [],
      datasets: [
        {
          label: 'pH',
          data: [],
          borderColor: '#22d3ee',
          backgroundColor: 'rgba(34, 211, 238, 0.1)',
          tension: 0.35,
          borderWidth: 2,
          pointRadius: 0,
          yAxisID: 'y'
        },
        {
          label: 'Turbidity (NTU)',
          data: [],
          borderColor: '#60a5fa',
          backgroundColor: 'rgba(96, 165, 250, 0.1)',
          tension: 0.35,
          borderWidth: 2,
          pointRadius: 0,
          yAxisID: 'y'
        },
        {
          label: 'Dissolved O₂ (mg/L)',
          data: [],
          borderColor: '#34d399',
          backgroundColor: 'rgba(52, 211, 153, 0.1)',
          tension: 0.35,
          borderWidth: 2,
          pointRadius: 0,
          yAxisID: 'y'
        },
        {
          label: 'TDS (ppm / 50)',
          data: [],
          borderColor: '#fbbf24',
          backgroundColor: 'rgba(251, 191, 36, 0.1)',
          tension: 0.35,
          borderWidth: 2,
          pointRadius: 0,
          yAxisID: 'y'
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      animation: { duration: 400 },
      interaction: { mode: 'index', intersect: false },
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: '#0f172a',
          titleColor: '#f1f5f9',
          bodyColor: '#cbd5e1',
          borderColor: '#334155',
          borderWidth: 1,
          padding: 8
        }
      },
      scales: {
        x: {
          grid: { color: 'rgba(51, 65, 85, 0.25)' },
          ticks: { color: '#64748b', font: { family: 'JetBrains Mono', size: 10 } }
        },
        y: {
          min: 0,
          max: 18,
          grid: { color: 'rgba(51, 65, 85, 0.25)' },
          ticks: { color: '#64748b', font: { family: 'JetBrains Mono', size: 10 } }
        }
      }
    }
  });

  // 2. Radar Benchmark Chart
  const ctxRadar = document.getElementById('radarBenchmarkChart').getContext('2d');
  radarChart = new Chart(ctxRadar, {
    type: 'radar',
    data: {
      labels: ['pH Safety', 'Clarity (Turb)', 'Mineral Purity (TDS)', 'Oxygenation', 'Ionic Balance (Cond)'],
      datasets: [
        {
          label: 'Ideal Standard (100%)',
          data: [100, 100, 100, 100, 100],
          borderColor: 'rgba(148, 163, 184, 0.4)',
          backgroundColor: 'transparent',
          borderDash: [4, 4],
          borderWidth: 1.5,
          pointRadius: 0
        },
        {
          label: 'Current Water Sample',
          data: [85, 90, 80, 85, 85],
          borderColor: '#06b6d4',
          backgroundColor: 'rgba(6, 182, 212, 0.25)',
          borderWidth: 2,
          pointBackgroundColor: '#22d3ee',
          pointBorderColor: '#fff',
          pointHoverRadius: 5
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: '#0f172a',
          borderColor: '#334155',
          borderWidth: 1
        }
      },
      scales: {
        r: {
          min: 0,
          max: 100,
          ticks: { display: false, stepSize: 25 },
          grid: { color: 'rgba(51, 65, 85, 0.35)' },
          angleLines: { color: 'rgba(51, 65, 85, 0.35)' },
          pointLabels: {
            color: '#94a3b8',
            font: { size: 10, weight: '600' }
          }
        }
      }
    }
  });
}

// ---------------- UI UPDATE LOGIC ----------------
function updateDashboardUI(payload) {
  const telemetry = payload.telemetry;
  const inference = payload.inference;
  const timestamp = payload.timestamp || new Date().toLocaleTimeString();
  const timeLabel = timestamp.split(' ')[1] || timestamp;

  // Header badges
  if (telemetry.signal_rssi_dbm) {
    document.getElementById('header-rssi').innerText = `${telemetry.signal_rssi_dbm} dBm`;
  }
  if (telemetry.battery_percent) {
    document.getElementById('header-battery').innerText = `${telemetry.battery_percent}%`;
  }
  if (payload.device_id) {
    document.getElementById('header-device-id').innerText = payload.device_id;
  }

  // 1. ML Potability Card
  const potCard = document.getElementById('potability-card');
  const potBadge = document.getElementById('potability-badge');
  const potText = document.getElementById('potability-text');
  const potConf = document.getElementById('potability-confidence');
  const potBar = document.getElementById('potability-bar');

  if (inference.is_potable) {
    potCard.className = 'bg-cardBg border rounded-2xl p-5 shadow-xl relative overflow-hidden transition-all duration-300 potable-safe';
    potBadge.className = 'inline-flex items-center gap-2 px-3.5 py-2 rounded-xl text-base font-extrabold tracking-wide uppercase bg-emerald-950 border border-emerald-500/40 text-emerald-400 shadow-lg shadow-emerald-900/20';
    potText.innerText = 'POTABLE (SAFE TO DRINK)';
    potBar.className = 'bg-emerald-500 h-1.5 rounded-full transition-all duration-500';
  } else {
    potCard.className = 'bg-cardBg border rounded-2xl p-5 shadow-xl relative overflow-hidden transition-all duration-300 potable-unsafe glow-alert';
    potBadge.className = 'inline-flex items-center gap-2 px-3.5 py-2 rounded-xl text-base font-extrabold tracking-wide uppercase bg-rose-950 border border-rose-500/50 text-rose-400 shadow-lg shadow-rose-900/30';
    potText.innerText = 'NON-POTABLE (UNSAFE)';
    potBar.className = 'bg-rose-500 h-1.5 rounded-full transition-all duration-500';
    playAlarmSound();
  }
  potConf.innerText = `${inference.confidence}%`;
  potBar.style.width = `${inference.confidence}%`;

  // 2. WQI Card
  const wqiData = inference.wqi;
  const wqiScoreEl = document.getElementById('wqi-score');
  const wqiTagEl = document.getElementById('wqi-category-tag');
  const wqiSummaryEl = document.getElementById('wqi-status-summary');

  wqiScoreEl.innerText = wqiData.wqi.toFixed(1);
  wqiScoreEl.style.color = wqiData.color;
  wqiTagEl.innerText = wqiData.category.toUpperCase();
  wqiTagEl.style.color = wqiData.color;
  wqiSummaryEl.innerText = wqiData.status;

  // 3. Compliance Card
  const diag = inference.diagnostics;
  const breachCountEl = document.getElementById('breach-count-text');
  const complianceStatusEl = document.getElementById('compliance-status-badge');
  const primaryHazardEl = document.getElementById('primary-hazard-text');

  breachCountEl.innerText = diag.breach_count;
  if (diag.breach_count === 0) {
    breachCountEl.className = 'text-4xl font-extrabold font-mono text-emerald-400 tracking-tight';
    complianceStatusEl.innerText = 'WHO / EPA Compliant';
    complianceStatusEl.className = 'text-xs font-semibold px-2 py-0.5 rounded bg-emerald-950 text-emerald-400 border border-emerald-800';
    primaryHazardEl.innerText = 'All 6 physical and chemical indicators within safe limits.';
  } else {
    breachCountEl.className = 'text-4xl font-extrabold font-mono text-rose-400 tracking-tight';
    complianceStatusEl.innerText = `${diag.breach_count} Breaches Active`;
    complianceStatusEl.className = 'text-xs font-semibold px-2 py-0.5 rounded bg-rose-950 text-rose-400 border border-rose-800';
    primaryHazardEl.innerText = diag.breaches[0]?.issue || 'Contamination thresholds breached.';
  }

  // 4. Sensor Gauge Values
  document.getElementById('val-ph').innerText = telemetry.ph.toFixed(2);
  document.getElementById('val-ph-diff').innerText = `${(telemetry.ph - 7.0 > 0 ? '+' : '')}${(telemetry.ph - 7.0).toFixed(2)}`;
  document.getElementById('bar-ph').style.width = `${Math.min(100, Math.max(5, (telemetry.ph / 14.0) * 100))}%`;
  document.getElementById('ph-eval').innerText = telemetry.ph < 6.5 ? 'Acidic' : (telemetry.ph > 8.5 ? 'Alkaline' : 'Optimal');

  document.getElementById('val-turb').innerText = telemetry.turbidity.toFixed(2);
  document.getElementById('bar-turb').style.width = `${Math.min(100, (telemetry.turbidity / 30.0) * 100)}%`;
  document.getElementById('turb-eval').innerText = telemetry.turbidity > 5.0 ? 'Turbid / Risk' : 'Clear';

  document.getElementById('val-tds').innerText = Math.round(telemetry.tds);
  document.getElementById('bar-tds').style.width = `${Math.min(100, (telemetry.tds / 1200.0) * 100)}%`;
  document.getElementById('tds-eval').innerText = telemetry.tds > 500 ? 'Elevated' : 'Desirable';

  document.getElementById('val-do').innerText = telemetry.dissolved_oxygen.toFixed(2);
  document.getElementById('bar-do').style.width = `${Math.min(100, (telemetry.dissolved_oxygen / 12.0) * 100)}%`;
  document.getElementById('do-eval').innerText = telemetry.dissolved_oxygen < 5.0 ? 'Hypoxic' : 'Healthy';

  document.getElementById('val-temp').innerText = telemetry.temperature.toFixed(1);
  document.getElementById('bar-temp').style.width = `${Math.min(100, (telemetry.temperature / 45.0) * 100)}%`;

  document.getElementById('val-cond').innerText = Math.round(telemetry.conductivity);
  document.getElementById('bar-cond').style.width = `${Math.min(100, (telemetry.conductivity / 2000.0) * 100)}%`;

  // 5. Update AI Diagnostic Checklist & Recommendations
  renderComplianceList(telemetry, diag);
  renderRemediationList(diag.recommendations);

  // 6. Push to Chart.js Waveform
  if (timelineChart) {
    if (timelineChart.data.labels.length > state.maxHistoryPoints) {
      timelineChart.data.labels.shift();
      timelineChart.data.datasets.forEach(ds => ds.data.shift());
    }
    timelineChart.data.labels.push(timeLabel);
    timelineChart.data.datasets[0].data.push(telemetry.ph);
    timelineChart.data.datasets[1].data.push(telemetry.turbidity);
    timelineChart.data.datasets[2].data.push(telemetry.dissolved_oxygen);
    timelineChart.data.datasets[3].data.push(telemetry.tds / 50.0);
    timelineChart.update('none'); // fast update without full reflow
  }

  // 7. Update Radar Chart
  if (radarChart && wqiData.sub_indices) {
    radarChart.data.datasets[1].data = [
      wqiData.sub_indices.ph_quality,
      wqiData.sub_indices.turbidity_quality,
      wqiData.sub_indices.tds_quality,
      wqiData.sub_indices.do_quality,
      wqiData.sub_indices.conductivity_quality
    ];
    radarChart.update('none');
  }

  // Refresh summary stats and alerts table periodically
  loadSummaryStats();
  loadAlerts();
}

// Render Parameter Compliance Checklist
function renderComplianceList(telemetry, diag) {
  const container = document.getElementById('compliance-checklist');
  if (!container) return;

  const checks = [
    { name: 'pH Balance', val: telemetry.ph.toFixed(2), safe: telemetry.ph >= 6.5 && telemetry.ph <= 8.5, target: '6.5 - 8.5' },
    { name: 'Turbidity Clarity', val: `${telemetry.turbidity.toFixed(1)} NTU`, safe: telemetry.turbidity <= 5.0, target: '< 5.0 NTU' },
    { name: 'Total Dissolved Solids', val: `${Math.round(telemetry.tds)} ppm`, safe: telemetry.tds <= 500, target: '< 500 ppm' },
    { name: 'Dissolved Oxygen', val: `${telemetry.dissolved_oxygen.toFixed(2)} mg/L`, safe: telemetry.dissolved_oxygen >= 6.0, target: '> 6.0 mg/L' },
    { name: 'Electrical Conductivity', val: `${Math.round(telemetry.conductivity)} µS/cm`, safe: telemetry.conductivity <= 800, target: '< 800 µS/cm' }
  ];

  let html = '';
  checks.forEach(c => {
    html += `
      <div class="flex items-center justify-between p-2 rounded-lg bg-slate-900/50 border border-slate-800">
        <div class="flex items-center gap-2">
          <span class="w-2 h-2 rounded-full ${c.safe ? 'bg-emerald-400' : 'bg-rose-400'}"></span>
          <span class="font-medium text-slate-300">${c.name}</span>
        </div>
        <div class="flex items-center gap-3 font-mono">
          <span class="text-slate-400 text-[11px]">EPA: ${c.target}</span>
          <span class="font-bold ${c.safe ? 'text-emerald-400' : 'text-rose-400'}">${c.val}</span>
        </div>
      </div>
    `;
  });
  container.innerHTML = html;
}

// Render Remediation Action List
function renderRemediationList(recs) {
  const container = document.getElementById('remediation-list');
  if (!container) return;
  if (!recs || recs.length === 0) {
    container.innerHTML = '<li class="text-slate-400">No remediation actions required.</li>';
    return;
  }
  let html = '';
  recs.forEach(r => {
    html += `
      <li class="flex items-start gap-2 p-1.5 rounded bg-slate-900/40">
        <i data-lucide="check-circle" class="w-3.5 h-3.5 text-cyan-400 mt-0.5 shrink-0"></i>
        <span>${r}</span>
      </li>
    `;
  });
  container.innerHTML = html;
  lucide.createIcons();
}

// ---------------- ALERTS & STATS ----------------
async function loadSummaryStats() {
  try {
    const res = await fetch('/api/stats');
    if (!res.ok) return;
    const stats = await res.json();
    document.getElementById('total-samples-count').innerText = stats.total_readings;
    document.getElementById('overall-safe-percent').innerText = `${stats.safe_percentage}%`;
    document.getElementById('overall-avg-wqi').innerText = stats.avg_wqi;
    document.getElementById('active-alert-counter').innerText = stats.active_alerts;
  } catch (e) {
    // ignore polling error
  }
}

async function loadAlerts() {
  try {
    const res = await fetch('/api/alerts?limit=25');
    if (!res.ok) return;
    const data = await res.json();
    const tbody = document.getElementById('alerts-table-body');
    if (!data.alerts || data.alerts.length === 0) {
      tbody.innerHTML = `<tr><td colspan="6" class="py-4 text-center text-slate-500">No active contamination breaches detected. Water system is operating nominally.</td></tr>`;
      return;
    }

    let rows = '';
    data.alerts.forEach(a => {
      const isCrit = a.severity === 'CRITICAL';
      const sevBadge = isCrit 
        ? '<span class="px-2 py-0.5 rounded text-[10px] font-bold bg-rose-950 text-rose-400 border border-rose-800">CRITICAL</span>'
        : '<span class="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-950 text-amber-400 border border-amber-800">WARNING</span>';
      
      const ackBtn = a.acknowledged 
        ? '<span class="text-slate-500 text-[11px]">Resolved</span>'
        : `<button onclick="ackAlert(${a.id})" class="px-2 py-1 rounded bg-slate-800 hover:bg-slate-700 text-[11px] text-cyan-300 transition">Dismiss</button>`;

      rows += `
        <tr class="hover:bg-slate-900/40 transition">
          <td class="py-2.5 px-3 font-mono text-[11px] text-slate-400">${a.timestamp}</td>
          <td class="py-2.5 px-3">${sevBadge}</td>
          <td class="py-2.5 px-3 font-semibold text-slate-200">${a.parameter}</td>
          <td class="py-2.5 px-3 font-mono text-cyan-300">${a.value}</td>
          <td class="py-2.5 px-3 text-slate-300 max-w-xs truncate">${a.message}</td>
          <td class="py-2.5 px-3 text-right">${ackBtn}</td>
        </tr>
      `;
    });
    tbody.innerHTML = rows;
  } catch (e) {
    // ignore
  }
}

async function ackAlert(id) {
  try {
    await fetch(`/api/alerts/${id}/ack`, { method: 'POST' });
    loadAlerts();
    loadSummaryStats();
  } catch (e) {
    console.error('Error acknowledging alert:', e);
  }
}

async function ackAllAlerts() {
  try {
    await fetch('/api/alerts/ack-all', { method: 'POST' });
    loadAlerts();
    loadSummaryStats();
  } catch (e) {
    console.error('Error acknowledging alerts:', e);
  }
}

// ---------------- WEBSOCKET CLIENT ----------------
function initWebSocket() {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const wsUrl = `${protocol}//${window.location.host}/ws/live`;
  const badge = document.getElementById('ws-status-badge');
  const badgeText = document.getElementById('ws-status-text');

  state.ws = new WebSocket(wsUrl);

  state.ws.onopen = () => {
    state.wsConnected = true;
    badge.className = 'flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-medium bg-emerald-950/60 border border-emerald-500/30 text-emerald-400 shadow-sm';
    badgeText.innerText = 'WS CONNECTED';
  };

  state.ws.onmessage = (event) => {
    try {
      const payload = JSON.parse(event.data);
      if (payload.event === 'telemetry_update') {
        updateDashboardUI(payload);
      } else if (payload.event === 'connected') {
        if (payload.simulator) {
          highlightScenarioButton(payload.simulator.scenario);
        }
      }
    } catch (e) {
      console.error('WS parse error:', e);
    }
  };

  state.ws.onclose = () => {
    state.wsConnected = false;
    badge.className = 'flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-medium bg-rose-950/60 border border-rose-500/30 text-rose-400 shadow-sm';
    badgeText.innerText = 'WS RECONNECTING...';
    setTimeout(initWebSocket, 3000);
  };

  state.ws.onerror = (err) => {
    state.ws.close();
  };
}

// ---------------- SCENARIO & CONTROLS ----------------
function highlightScenarioButton(key) {
  document.querySelectorAll('.scenario-btn').forEach(btn => {
    if (btn.getAttribute('data-scenario') === key) {
      btn.classList.add('active');
    } else {
      btn.classList.remove('active');
    }
  });
}

async function setScenario(scenarioKey) {
  highlightScenarioButton(scenarioKey);
  try {
    await fetch('/api/simulator/scenario', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ scenario_key: scenarioKey })
    });
  } catch (e) {
    console.error('Error setting scenario:', e);
  }
}

async function injectAnomaly(anomalyType) {
  try {
    await fetch('/api/simulator/anomaly', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ anomaly_type: anomalyType, duration_ticks: 12 })
    });
  } catch (e) {
    console.error('Error injecting anomaly:', e);
  }
}

async function toggleStream() {
  try {
    const res = await fetch('/api/simulator/toggle', { method: 'POST' });
    const data = await res.json();
    state.streamActive = data.is_running;
    const btnText = document.getElementById('stream-btn-text');
    const btnIcon = document.getElementById('stream-btn-icon');
    if (state.streamActive) {
      btnText.innerText = 'Streaming Live';
      btnIcon.setAttribute('data-lucide', 'pause');
    } else {
      btnText.innerText = 'Stream Paused';
      btnIcon.setAttribute('data-lucide', 'play');
    }
    lucide.createIcons();
  } catch (e) {
    console.error('Error toggling stream:', e);
  }
}

// ---------------- INTERACTIVE "WHAT-IF" LAB ----------------
function initLabCalculator() {
  const inputs = [
    { id: 'calc-ph', valId: 'calc-val-ph', unit: '' },
    { id: 'calc-turb', valId: 'calc-val-turb', unit: ' NTU' },
    { id: 'calc-tds', valId: 'calc-val-tds', unit: ' ppm' },
    { id: 'calc-temp', valId: 'calc-val-temp', unit: ' °C' },
    { id: 'calc-do', valId: 'calc-val-do', unit: ' mg/L' },
    { id: 'calc-cond', valId: 'calc-val-cond', unit: ' µS' }
  ];

  inputs.forEach(inp => {
    const slider = document.getElementById(inp.id);
    const label = document.getElementById(inp.valId);
    slider.addEventListener('input', () => {
      label.innerText = `${slider.value}${inp.unit}`;
    });
  });

  document.getElementById('calc-run-btn').addEventListener('click', runLabPrediction);
  document.getElementById('calc-reset-btn').addEventListener('click', resetLabCalculator);
}

async function runLabPrediction() {
  const sample = {
    ph: parseFloat(document.getElementById('calc-ph').value),
    turbidity: parseFloat(document.getElementById('calc-turb').value),
    tds: parseFloat(document.getElementById('calc-tds').value),
    temperature: parseFloat(document.getElementById('calc-temp').value),
    dissolved_oxygen: parseFloat(document.getElementById('calc-do').value),
    conductivity: parseFloat(document.getElementById('calc-cond').value)
  };

  try {
    const res = await fetch('/api/predict', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(sample)
    });
    const result = await res.json();

    const pill = document.getElementById('calc-res-pill');
    const title = document.getElementById('calc-res-title');
    const desc = document.getElementById('calc-res-desc');
    const wqi = document.getElementById('calc-res-wqi');

    if (result.is_potable) {
      pill.className = 'px-3 py-1.5 rounded-lg font-bold uppercase bg-emerald-950 text-emerald-400 border border-emerald-800';
      pill.innerText = 'SAFE';
      title.innerText = 'Water Sample is Safe for Drinking';
    } else {
      pill.className = 'px-3 py-1.5 rounded-lg font-bold uppercase bg-rose-950 text-rose-400 border border-rose-800';
      pill.innerText = 'UNSAFE';
      title.innerText = 'Water Sample is Contaminated / Non-Potable';
    }

    desc.innerText = `WQI Score: ${result.wqi.wqi} (${result.wqi.category}) | ML Confidence: ${result.confidence}%`;
    wqi.innerText = `WQI: ${result.wqi.wqi}`;
    wqi.style.color = result.wqi.color;
  } catch (e) {
    console.error('Error running lab prediction:', e);
  }
}

function resetLabCalculator() {
  document.getElementById('calc-ph').value = 7.2;
  document.getElementById('calc-val-ph').innerText = '7.2';

  document.getElementById('calc-turb').value = 1.2;
  document.getElementById('calc-val-turb').innerText = '1.2 NTU';

  document.getElementById('calc-tds').value = 220;
  document.getElementById('calc-val-tds').innerText = '220 ppm';

  document.getElementById('calc-temp').value = 19.0;
  document.getElementById('calc-val-temp').innerText = '19.0 °C';

  document.getElementById('calc-do').value = 8.0;
  document.getElementById('calc-val-do').innerText = '8.0 mg/L';

  document.getElementById('calc-cond').value = 340;
  document.getElementById('calc-val-cond').innerText = '340 µS';

  runLabPrediction();
}

// ---------------- EXPORT CSV ----------------
async function exportCsv() {
  try {
    const res = await fetch('/api/telemetry/history?limit=300');
    const data = await res.json();
    if (!data.history || data.history.length === 0) {
      alert('No telemetry records available to export.');
      return;
    }
    const headers = ['Timestamp', 'Device', 'Scenario', 'pH', 'Turbidity_NTU', 'TDS_ppm', 'Temp_C', 'DO_mgL', 'Conductivity_uS', 'Potability', 'WQI', 'Category'];
    const rows = data.history.map(r => [
      r.timestamp, r.device_id, `"${r.scenario}"`, r.ph, r.turbidity, r.tds, r.temperature, r.dissolved_oxygen, r.conductivity, r.potability, r.wqi, r.wqi_category
    ]);

    const csvContent = 'data:text/csv;charset=utf-8,' + [headers.join(','), ...rows.map(e => e.join(','))].join('\n');
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement('a');
    link.setAttribute('href', encodedUri);
    link.setAttribute('download', `aquasense_telemetry_${Date.now()}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  } catch (e) {
    console.error('Error exporting CSV:', e);
  }
}

// ---------------- INITIALIZATION ----------------
document.addEventListener('DOMContentLoaded', () => {
  lucide.createIcons();
  initCharts();
  initWebSocket();
  initLabCalculator();
  loadSummaryStats();
  loadAlerts();

  // Clock
  setInterval(() => {
    const clock = document.getElementById('clock-display');
    if (clock) clock.innerText = new Date().toLocaleTimeString();
  }, 1000);

  // Scenario Buttons
  document.querySelectorAll('.scenario-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      setScenario(btn.getAttribute('data-scenario'));
    });
  });

  // Anomaly Buttons
  document.getElementById('inject-acid-btn').addEventListener('click', () => injectAnomaly('acid_spike'));
  document.getElementById('inject-turb-btn').addEventListener('click', () => injectAnomaly('turbidity_surge'));
  document.getElementById('inject-chem-btn').addEventListener('click', () => injectAnomaly('chemical_leak'));

  // Stream Toggle
  document.getElementById('toggle-stream-btn').addEventListener('click', toggleStream);

  // Audio Toggle
  document.getElementById('toggle-audio-btn').addEventListener('click', () => {
    state.audioMuted = !state.audioMuted;
    const btn = document.getElementById('toggle-audio-btn');
    btn.innerHTML = state.audioMuted 
      ? '<i data-lucide="volume-x" class="w-4 h-4 text-slate-500"></i>' 
      : '<i data-lucide="volume-2" class="w-4 h-4 text-cyan-400"></i>';
    lucide.createIcons();
  });

  // Alert Actions
  document.getElementById('ack-all-alerts-btn').addEventListener('click', ackAllAlerts);
  document.getElementById('export-csv-btn').addEventListener('click', exportCsv);
});
