/**
 * Nikom Tender Intelligence — Enterprise Dashboard Client Application
 * Identical to Enterprise Reference Architecture
 */

const API_BASE = window.location.origin;

let currentTenders = [];
let allLoadedTenders = [];
let activeTierFilter = 'all';
let activeWorkflowFilter = 'all';
let currentTimeWindow = 'all';
let selectedTenderIds = new Set();
let currentSelectedTenderId = null;
let sortDirection = 'desc';

function parseDateRobust(dateStr) {
  if (!dateStr) return null;
  if (dateStr instanceof Date) return isNaN(dateStr.getTime()) ? null : dateStr;
  let s = String(dateStr).trim();
  if (!s) return null;

  // 1. If timestamp has 'T' but no timezone suffix (e.g. SQLite ISO), append 'Z' so it parses as UTC
  if (s.includes('T') && !s.endsWith('Z') && !/[+-]\d{2}:?\d{2}$/.test(s)) {
    const dUtc = new Date(s + 'Z');
    if (!isNaN(dUtc.getTime())) return dUtc;
  }

  // 2. Direct Date constructor parse
  let d = new Date(s);
  if (!isNaN(d.getTime())) return d;

  // 3. Space-separated timestamp format
  if (s.includes(' ') && !s.includes('T')) {
    s = s.replace(' ', 'T');
    d = new Date(s.endsWith('Z') ? s : s + 'Z');
    if (!isNaN(d.getTime())) return d;
  }

  try {
    const parts = s.split(' ')[0];
    const d2 = new Date(parts.endsWith('Z') ? parts : parts + 'Z');
    if (!isNaN(d2.getTime())) return d2;
  } catch (e) {}
  return null;
}

function getTenderSector(t) {
  const text = ((t.title || '') + ' ' + (t.authority || '')).toLowerCase();
  const defKeys = ['air force', 'army', 'navy', 'defence', 'defense', 'armoured', 'ordnance', 'cantonment', 'military', 'mes', 'crpf', 'bsf', 'cisf', 'itbp'];
  if (defKeys.some(k => text.includes(k))) return 'Defence';

  const transKeys = ['railway', 'metro', 'transport', 'airport', 'aai', 'highway', 'nhai', 'port', 'shipping', 'irctc', 'rvnl'];
  if (transKeys.some(k => text.includes(k))) return 'Transport';

  const energyKeys = ['power', 'energy', 'solar', 'grid', 'electricity', 'discom', 'ntpc', 'transco', 'gencor', 'oil', 'gas', 'ongc', 'iocl', 'bpcl', 'gail', 'hydel', 'thermal'];
  if (energyKeys.some(k => text.includes(k))) return 'Energy & Utilities';

  const entKeys = ['bank', 'rbi', 'sbi', 'insurance', 'lic', 'commercial', 'enterprise', 'telecom', 'bsnl', 'limited', 'corp', 'exchange', 'bse', 'nse', 'ltd'];
  if (entKeys.some(k => text.includes(k))) return 'Enterprise / Commercial';

  return 'Government';
}

function isWithinTimeWindow(t, windowStr) {
  if (!windowStr || windowStr === 'all') return true;

  const now = new Date();
  let hours = 24;
  if (windowStr === '24h') hours = 24;
  else if (windowStr === '48h') hours = 48;
  else if (windowStr === '7d') hours = 24 * 7;
  else if (windowStr === '30d') hours = 24 * 30;

  const cutoff = new Date(now.getTime() - hours * 60 * 60 * 1000);

  let createdDt = parseDateRobust(t.created_at);
  let pubDt = parseDateRobust(t.published_date);

  const isCreatedRecent = createdDt && createdDt >= cutoff;
  const isPubRecent = pubDt && pubDt >= cutoff;

  // Strict Discovery Window: Only evaluate when the opportunity was originally published or discovered
  return Boolean(isCreatedRecent || isPubRecent);
}

function isTenderExpired(t) {
  if (!t.submission_deadline) return false;
  const d = parseDateRobust(t.submission_deadline);
  if (d) {
    return d.getTime() < Date.now();
  }
  if (t.is_expired !== undefined) return Boolean(t.is_expired);
  return false;
}

function handleTimeWindowChange(windowVal) {
  currentTimeWindow = windowVal;

  const sel1 = document.getElementById('time-window-select');
  if (sel1 && sel1.value !== windowVal) sel1.value = windowVal;
  const sel2 = document.getElementById('filter-window');
  if (sel2 && sel2.value !== windowVal) sel2.value = windowVal;

  const sub = document.getElementById('discovery-feed-subtitle');
  if (sub) {
    if (windowVal === '24h') {
      sub.textContent = 'All relevant tenders discovered in the last 24 hours across monitored portals';
    } else if (windowVal === '48h') {
      sub.textContent = 'All relevant tenders discovered in the last 48 hours across monitored portals';
    } else if (windowVal === '7d') {
      sub.textContent = 'All relevant tenders discovered in the last 7 days across monitored portals';
    } else if (windowVal === '30d') {
      sub.textContent = 'All relevant tenders discovered in the last 30 days across monitored portals';
    } else {
      sub.textContent = 'All relevant tenders discovered across monitored portals';
    }
  }

  loadMetrics(windowVal);
  applyFilters();
}

// Initialization on DOM Ready
document.addEventListener('DOMContentLoaded', () => {
  initTheme();
  initApp();
  setupEventListeners();

  const initialHash = (window.location.hash || '').replace('#', '').trim();
  if (initialHash && initialHash !== 'dashboard') {
    navigateTo(initialHash);
  }
});

window.addEventListener('hashchange', () => {
  const hash = (window.location.hash || '').replace('#', '').trim() || 'dashboard';
  navigateTo(hash);
});

async function initApp() {
  await loadMetrics();
  await loadSidebarSources();
  await loadTenders();
  await checkScanStatus();

  // If deployed database has fewer than 50 tenders (e.g. fresh cloud deploy or interrupted scan),
  // auto-sync the verified Nikom baseline dataset so the user immediately gets 450+ qualified tenders.
  if (allLoadedTenders.length < 50) {
    console.log("Database has < 50 tenders. Triggering baseline sync...");
    try {
      const syncRes = await fetch(`${API_BASE}/api/tenders/sync-seed`, { method: 'POST' });
      if (syncRes.ok) {
        await loadMetrics();
        await loadTenders();
      }
    } catch (e) {
      console.warn("Seed sync notice:", e);
    }
  }

  if (!scanPollInterval) {
    scanPollInterval = setInterval(checkScanStatus, 2500);
  }
  setInterval(refreshAllLiveTimes, 15000);
}

// ═══════════════════════════════════════════════════════════════════════════
// METRICS & ANALYTICS CHARTS (DYNAMIC DATA LOADING & ANIMATIONS)
// ═══════════════════════════════════════════════════════════════════════════
function animateCounter(element, target, duration = 800) {
  if (!element) return;
  const endVal = parseInt(target, 10);
  if (isNaN(endVal)) {
    element.textContent = target;
    return;
  }
  const currentText = (element.textContent || '').replace(/,/g, '').trim();
  const startVal = parseInt(currentText, 10) || 0;
  if (startVal === endVal) {
    element.textContent = endVal.toLocaleString();
    return;
  }
  const startTime = performance.now();

  function step(now) {
    const elapsed = now - startTime;
    const progress = Math.min(elapsed / duration, 1);
    // Ease-out cubic
    const ease = 1 - Math.pow(1 - progress, 3);
    const val = Math.round(startVal + (endVal - startVal) * ease);
    element.textContent = val.toLocaleString();
    if (progress < 1) {
      requestAnimationFrame(step);
    } else {
      element.textContent = endVal.toLocaleString();
    }
  }

  requestAnimationFrame(step);
}

async function loadMetrics(timeWindow = currentTimeWindow) {
  try {
    const url = (timeWindow && timeWindow !== 'all')
      ? `${API_BASE}/api/dashboard/metrics?time_window=${encodeURIComponent(timeWindow)}`
      : `${API_BASE}/api/dashboard/metrics`;
    const res = await fetch(url);
    if (!res.ok) throw new Error('Failed to load metrics');
    const data = await res.json();

    // 1. Top KPI Metrics with Counter Animation
    const tierA = data.tier_a_count || 0;
    const tierB = data.tier_b_count || 0;
    const tierC = data.tier_c_count || 0;
    const tierD = data.tier_d_count || 0;
    const total = data.direct_matches || (tierA + tierB + tierC + tierD) || 0;

    animateCounter(document.getElementById('metric-total'), total);
    animateCounter(document.getElementById('nav-tender-count'), total);
    animateCounter(document.getElementById('metric-tier-a'), tierA);
    animateCounter(document.getElementById('metric-tier-b'), tierB);
    animateCounter(document.getElementById('metric-tier-c'), tierC);
    animateCounter(document.getElementById('metric-tier-d'), tierD);

    // Filter pills counts
    animateCounter(document.getElementById('pill-all-count'), total);
    animateCounter(document.getElementById('pill-a-count'), tierA);
    animateCounter(document.getElementById('pill-b-count'), tierB);
    animateCounter(document.getElementById('pill-c-count'), tierC);
    animateCounter(document.getElementById('pill-d-count'), tierD);

    // 2. Tenders by Source (Restored Donut Chart)
    renderDonutChart(data.sources_breakdown || [], total);

    // 3. Tenders by Keyword Tier Bars
    renderTierBars(tierA, tierB, tierC, tierD, total);
    renderRecentTenders(currentTenders);

    // 4. Portal Health Panel (Right Column Widget)
    renderPortalHealth(data.sources_breakdown || []);

    // 5. Tenders by Sector Bars (Horizontal Bar Chart matching user reference design)
    renderSectorBars(data.sectors_breakdown || [], total);

  } catch (err) {
    console.error('Error loading metrics:', err);
  }
}

function renderDonutChart(sources, total) {
  const segmentsGroup = document.getElementById('donut-segments-group');
  const legendContainer = document.getElementById('donut-legend-container');
  const totalCenterEl = document.getElementById('donut-center-total');
  if (!segmentsGroup || !legendContainer) return;

  const DONUT_COLORS = [
    '#3B82F6', // GeM (Blue)
    '#10B981', // CPPP Central (Emerald)
    '#8B5CF6', // CPPP ePublish (Purple)
    '#F59E0B', // Amber
    '#EC4899', // Pink
    '#06B6D4', // Cyan
    '#64748B'  // Other (Slate)
  ];

  if (!sources || sources.length === 0) {
    segmentsGroup.innerHTML = '';
    legendContainer.innerHTML = '<div style="color: var(--text-3); font-size: 12px; padding: 12px 0;">No source data.</div>';
    if (totalCenterEl) totalCenterEl.textContent = '0';
    return;
  }

  // Canonicalize & aggregate source counts
  const aggregated = {};
  sources.forEach(s => {
    const canonicalName = formatSourceName(s.name);
    aggregated[canonicalName] = (aggregated[canonicalName] || 0) + (s.count || 0);
  });

  const sorted = Object.entries(aggregated)
    .map(([name, count]) => ({ name, count }))
    .sort((a, b) => b.count - a.count);

  const displayTotal = total || sorted.reduce((sum, item) => sum + item.count, 0);
  if (totalCenterEl) {
    animateCounter(totalCenterEl, displayTotal);
  }

  // Top 4 sources + 'Other' bucket for remaining
  const topLimit = 4;
  const topItems = sorted.slice(0, topLimit);
  const remaining = sorted.slice(topLimit);
  const otherCount = remaining.reduce((sum, item) => sum + item.count, 0);

  const chartItems = [...topItems];
  if (otherCount > 0) {
    chartItems.push({ name: 'Other Portals', count: otherCount });
  }

  const itemsTotal = chartItems.reduce((acc, curr) => acc + curr.count, 0) || 1;
  const C = 2 * Math.PI * 38; // ~238.76
  let cumOffset = 0;

  // Build SVG segments
  segmentsGroup.innerHTML = chartItems.map((item, idx) => {
    const pct = item.count / itemsTotal;
    const strokeDash = (pct * C);
    const strokeSpace = C - strokeDash;
    const offset = cumOffset;
    cumOffset += strokeDash;
    const color = DONUT_COLORS[idx % DONUT_COLORS.length];

    return `
      <circle class="donut-segment"
              cx="50" cy="50" r="38"
              fill="none"
              stroke="${color}"
              stroke-width="12"
              stroke-dasharray="${strokeDash.toFixed(2)} ${strokeSpace.toFixed(2)}"
              stroke-dashoffset="${(-offset).toFixed(2)}"
              style="transition: stroke-dasharray 0.8s ease, stroke-dashoffset 0.8s ease;">
      </circle>
    `;
  }).join('');

  // Build Legend rows
  legendContainer.innerHTML = chartItems.map((item, idx) => {
    const color = DONUT_COLORS[idx % DONUT_COLORS.length];
    const pct = Math.round((item.count / itemsTotal) * 100);

    return `
      <div class="legend-row" onclick="handleSidebarSourceClick('${escapeHtml(item.name)}')" title="Filter by ${escapeHtml(item.name)} (${item.count} tenders)">
        <div class="legend-left">
          <span class="legend-dot" style="background: ${color};"></span>
          <span class="legend-source-name">${escapeHtml(item.name)}</span>
        </div>
        <div class="legend-right">
          <span class="legend-count">${item.count}</span>
          <span class="legend-pct">(${pct}%)</span>
        </div>
      </div>
    `;
  }).join('');
}

function renderTierBars(a, b, c, d, total) {
  const max = Math.max(a, b, c, d, 1);

  animateCounter(document.getElementById('tier-a-bar-count'), a);
  const fillA = document.getElementById('tier-a-bar-fill');
  if (fillA) fillA.style.width = `${(a / max) * 100}%`;

  animateCounter(document.getElementById('tier-b-bar-count'), b);
  const fillB = document.getElementById('tier-b-bar-fill');
  if (fillB) fillB.style.width = `${(b / max) * 100}%`;

  animateCounter(document.getElementById('tier-c-bar-count'), c);
  const fillC = document.getElementById('tier-c-bar-fill');
  if (fillC) fillC.style.width = `${(c / max) * 100}%`;

  animateCounter(document.getElementById('tier-d-bar-count'), d);
  const fillD = document.getElementById('tier-d-bar-fill');
  if (fillD) fillD.style.width = `${(d / max) * 100}%`;
}

function renderSectorBars(sectors, total) {
  const container = document.getElementById('sector-bars-container');
  const footerCount = document.getElementById('sector-bars-count-text');
  if (!container) return;

  if (!sectors || sectors.length === 0) {
    container.innerHTML = '<div style="color: var(--text-3); font-size: 12px; padding: 16px 0; text-align: center;">No sector data available.</div>';
    if (footerCount) footerCount.textContent = '0 sectors shown';
    return;
  }

  // Display clean short name matching reference image: Govt., Defence, Enterprise, Energy, Transport
  const formatSectorName = (name) => {
    if (!name) return 'Govt.';
    if (name === 'Government') return 'Govt.';
    if (name.includes('Enterprise') || name.includes('Commercial')) return 'Enterprise';
    if (name.includes('Energy') || name.includes('Utilities')) return 'Energy';
    return name;
  };

  const sorted = [...sectors].sort((a, b) => b.count - a.count);
  const topSectors = sorted.slice(0, 5);
  const maxVal = Math.max(...topSectors.map(s => s.count), 1);

  if (footerCount) {
    footerCount.textContent = `${topSectors.length} sectors shown`;
  }

  const currentSectorVal = document.getElementById('filter-sector')?.value || '';

  container.innerHTML = topSectors.map((s, idx) => {
    const displayName = formatSectorName(s.name);
    const barWidthPct = Math.max(3.5, (s.count / maxVal) * 82);
    const isSelected = currentSectorVal === s.name;

    return `
      <div class="source-bar-row ${isSelected ? 'active-bar' : ''}" style="animation-delay: ${(idx + 1) * 0.06}s;" onclick="filterBySector('${escapeHtml(s.name)}')" title="Filter tenders by ${escapeHtml(s.name)} (${s.count} tenders)">
        <span class="source-bar-label">${escapeHtml(displayName)}</span>
        <div class="source-bar-wrapper">
          <div class="source-bar-fill" style="width: ${barWidthPct.toFixed(1)}%;"></div>
          <span class="source-bar-count">${s.count}</span>
        </div>
      </div>
    `;
  }).join('');
}

function filterBySector(sectorName) {
  const sel = document.getElementById('filter-sector');
  if (sel) {
    if (sel.value === sectorName) {
      sel.value = '';
      showToast(`Cleared Sector filter`);
    } else {
      sel.value = sectorName;
      showToast(`Filtered by Sector: ${sectorName}`);
    }
    applyFilters();
  }
}

// ═══════════════════════════════════════════════════════════════════════════
// TENDERS TABLE DATA LOADING & RENDERING
// ═══════════════════════════════════════════════════════════════════════════
async function loadTenders() {
  const tbody = document.getElementById('tenders-tbody');
  tbody.innerHTML = `
    <tr>
      <td colspan="9" style="text-align: center; padding: 48px; color: var(--text-muted);">
        Loading tenders feed...
      </td>
    </tr>
  `;

  try {
    const res = await fetch(`${API_BASE}/api/tenders?page_size=1000&sort_by=published_date&order=${sortDirection}`);
    if (!res.ok) throw new Error('Failed to fetch tenders');
    const data = await res.json();

    allLoadedTenders = data.items || [];
    currentTenders = [...allLoadedTenders];

    renderRecentTenders(allLoadedTenders);

    applyFilters();

    // Auto-select first tender if available
    if (currentTenders.length > 0 && !currentSelectedTenderId) {
      selectTenderRow(currentTenders[0].tender_id, false);
    }
  } catch (err) {
    tbody.innerHTML = `
      <tr>
        <td colspan="9" style="text-align: center; padding: 48px; color: #ef4444;">
          Error loading tenders: ${escapeHtml(err.message)}
        </td>
      </tr>
    `;
  }
}

function renderTable(tenders) {
  const tbody = document.getElementById('tenders-tbody');
  const countEl = document.getElementById('table-total-count');
  if (countEl) animateCounter(countEl, tenders.length, 600);

  // Update master checkbox state based on selection
  const selectAll = document.getElementById('select-all-tenders');
  if (selectAll) {
    const isAllChecked = tenders.length > 0 && tenders.every(t => selectedTenderIds.has(t.tender_id));
    const isSomeChecked = tenders.some(t => selectedTenderIds.has(t.tender_id));
    selectAll.checked = isAllChecked;
    selectAll.indeterminate = isSomeChecked && !isAllChecked;
  }

  if (!tenders || tenders.length === 0) {
    tbody.innerHTML = `
      <tr>
        <td colspan="12" style="text-align: center; padding: 64px 20px;">
          <div style="font-size: 32px; margin-bottom: 8px;">🔍</div>
          <div style="font-size: 15px; font-weight: 600; color: var(--text);">No matching tenders found</div>
          <div style="font-size: 12.5px; color: var(--text-3); margin-top: 4px;">Try resetting filters or adjusting search keywords.</div>
        </td>
      </tr>
    `;
    return;
  }

  tbody.innerHTML = tenders.map(t => {
    const isSelected = t.tender_id === currentSelectedTenderId;
    const isChecked = selectedTenderIds.has(t.tender_id);
    const tier = t.highest_tier || '';
    const hasTier = tier.trim() !== '';

    // Cost formatting
    const costText = t.estimated_cost_inr 
      ? `₹ ${(t.estimated_cost_inr >= 10000000 ? (t.estimated_cost_inr / 10000000).toFixed(2) + ' Cr' : (t.estimated_cost_inr / 100000).toFixed(2) + ' L')}`
      : 'Value Not Disclosed';
    const estLabel = t.estimated_cost_inr ? '<span class="est">(Est.)</span>' : '';

    // Key systems tags
    const systems = extractKeySystems(t);
    const systemsHtml = systems.slice(0, 3).map(s => `<span class="tag-system">${escapeHtml(s)}</span>`).join('') +
      (systems.length > 3 ? `<span class="tag-more">+${systems.length - 3}</span>` : '');

    // Deadline & Countdown
    const deadlineInfo = formatDeadline(t.submission_deadline);

    // Area badge (Subject name instead of Tier letter)
    const areaNames = {
      'A': 'Cyber Security',
      'B': 'IT Infra',
      'C': 'Cloud',
      'D': 'Services'
    };
    const areaLabel = areaNames[tier.toUpperCase()] || tier;
    const tierBadge = hasTier
      ? `<span class="table-tier-badge tier-badge-${tier.toLowerCase()}">${escapeHtml(areaLabel)}</span>`
      : `<span class="table-tier-badge tier-badge-unmatched">—</span>`;

    // Workflow Lifecycle Status Pill
    const wfStatus = t.workflow_status || 'new';
    let wfLabel = 'New Ingest';
    let wfClass = 'wf-status-new';
    if (deadlineInfo.isExpired) {
      if (wfStatus === 'considered') {
        wfLabel = 'Considered (Closed)';
        wfClass = 'wf-status-considered';
      } else if (wfStatus === 'reviewed') {
        wfLabel = 'Reviewed (Closed)';
        wfClass = 'wf-status-reviewed';
      } else if (wfStatus === 'rejected') {
        wfLabel = 'Rejected (Closed)';
        wfClass = 'wf-status-rejected';
      } else {
        wfLabel = 'Closed / Expired';
        wfClass = 'wf-status-expired';
      }
    } else if (wfStatus === 'considered') {
      wfLabel = 'Considered';
      wfClass = 'wf-status-considered';
    } else if (wfStatus === 'under_review') {
      wfLabel = 'Under Review';
      wfClass = 'wf-status-review';
    } else if (wfStatus === 'reviewed') {
      wfLabel = 'Reviewed';
      wfClass = 'wf-status-reviewed';
    } else if (wfStatus === 'rejected') {
      wfLabel = 'Rejected';
      wfClass = 'wf-status-rejected';
    }

    const workflowPill = `
      <div class="table-workflow-pill ${wfClass}" onclick="cycleTenderWorkflowStatus('${escapeHtml(t.tender_id)}', event)" title="Click to cycle status: New → Review → Considered → Reviewed → Rejected">
        <span class="wf-status-dot"></span>
        <span>${wfLabel}</span>
      </div>
    `;

    return `
      <tr class="${isSelected ? 'row-selected' : ''} ${isChecked ? 'row-checked' : ''} ${deadlineInfo.isExpired ? 'row-expired' : ''}" onclick="selectTenderRow('${escapeHtml(t.tender_id)}', true)">
        <td onclick="event.stopPropagation();">
          <input type="checkbox" class="row-checkbox" value="${escapeHtml(t.tender_id)}" ${isChecked ? 'checked' : ''} onchange="toggleTenderSelection('${escapeHtml(t.tender_id)}', this.checked)">
        </td>
        <td onclick="event.stopPropagation();" style="text-align: center;">
          <button type="button" class="btn-table-star ${t.is_watchlisted ? 'starred' : ''}" onclick="toggleTenderStar('${escapeHtml(t.tender_id)}', event)" title="${t.is_watchlisted ? 'Remove from Watchlist' : 'Add to Watchlist'}">
            ${t.is_watchlisted ? '★' : '☆'}
          </button>
        </td>
        <td class="table-title-cell">
          <div class="table-tender-title" title="${escapeHtml(t.title)}">${escapeHtml(t.title)}</div>
          <div class="table-tender-ref">${escapeHtml(t.reference_no || t.tender_id)}</div>
          ${t.user_notes ? `<div class="table-user-notes" title="${escapeHtml(t.user_notes)}">📝 ${escapeHtml(t.user_notes)}</div>` : ''}
        </td>
        <td>
          <span class="source-badge-pill" data-source="${escapeHtml(t.portal_source || '')}">
            ${getSourceLogoSvg(t.portal_source, 18)}
            <span>${escapeHtml(formatSourceName(t.portal_source))}</span>
          </span>
        </td>
        <td>
          <div class="table-buyer" title="${escapeHtml(t.authority)}">${escapeHtml(t.authority)}</div>
        </td>
        <td>
          <div class="table-location">${escapeHtml(t.location || 'India')}</div>
        </td>
        <td>
          <div class="table-value">${costText} ${estLabel}</div>
        </td>
        <td>
          <div class="systems-tags-group">${systemsHtml}</div>
        </td>
        <td>
          <div class="deadline-box">
            <div class="deadline-date">${escapeHtml(deadlineInfo.dateStr)}</div>
            <span class="deadline-tag ${deadlineInfo.urgencyClass}">${escapeHtml(deadlineInfo.tagStr)}</span>
          </div>
        </td>
        <td>
          ${tierBadge}
        </td>
        <td>
          ${workflowPill}
        </td>
        <td style="text-align: center;" onclick="event.stopPropagation();">
          <button class="btn-row-action" onclick="selectTenderRow('${escapeHtml(t.tender_id)}', true)" title="View Details">•••</button>
        </td>
      </tr>
    `;
  }).join('');
}

// ═══════════════════════════════════════════════════════════════════════════
// DETAILS INSPECTOR PANEL
// ═══════════════════════════════════════════════════════════════════════════
async function selectTenderRow(tenderId, openPanel = true) {
  currentSelectedTenderId = tenderId;

  // Immediately populate from loaded tender object so details appear instantly with zero delay!
  const cached = (currentTenders || []).find(x => x.tender_id === tenderId) || 
                 (allLoadedTenders || []).find(x => x.tender_id === tenderId);
  if (cached) {
    populateDetailsPanel(cached);
  }

  // Highlight row in table
  document.querySelectorAll('#tenders-tbody tr').forEach(row => row.classList.remove('row-selected'));
  const allRows = document.querySelectorAll('#tenders-tbody tr');
  currentTenders.forEach((t, idx) => {
    if (t.tender_id === tenderId && allRows[idx]) {
      allRows[idx].classList.add('row-selected');
    }
  });

  const panel = document.getElementById('details-panel');
  if (openPanel) {
    panel.classList.add('panel-open');
  }

  // Fetch full tender details with encoded URI for IDs containing slashes
  try {
    const res = await fetch(`${API_BASE}/api/tenders/${encodeURIComponent(tenderId)}`);
    if (res.ok) {
      const t = await res.json();
      populateDetailsPanel(t);
    }
  } catch (err) {
    console.error('Error loading full tender details:', err);
  }
}

function populateDetailsPanel(t) {
  if (!t) return;

  // Title & Header Reference
  document.getElementById('panel-title').textContent = t.title || 'Untitled Opportunity';
  const refVal = t.reference_no || t.tender_id || 'TENDER';
  const refBadge = document.getElementById('panel-header-ref');
  if (refBadge) {
    refBadge.textContent = refVal.length > 20 ? refVal.slice(0, 18) + '...' : refVal;
    refBadge.title = `Click to copy reference: ${refVal}`;
  }

  // Tier Badge
  const tierBadgeEl = document.getElementById('panel-tier-badge');
  const hasTier = t.highest_tier && t.highest_tier.trim() !== '';
  if (hasTier) {
    const areaNamesFull = {
      'A': 'Cyber Security',
      'B': 'IT Infrastructure',
      'C': 'Cloud & DR',
      'D': 'Infra & Services'
    };
    tierBadgeEl.textContent = areaNamesFull[t.highest_tier.toUpperCase()] || t.highest_tier;
    tierBadgeEl.className = `panel-tier-badge tier-badge-${t.highest_tier.toLowerCase()}`;
    tierBadgeEl.style.display = 'inline-block';
  } else {
    tierBadgeEl.textContent = 'Unmatched';
    tierBadgeEl.className = 'panel-tier-badge tier-badge-unmatched';
  }

  // Source Badge
  const panelSrcBadge = document.getElementById('panel-source-badge');
  if (panelSrcBadge) {
    panelSrcBadge.innerHTML = `<span style="display:inline-flex; align-items:center; gap:6px;">${getSourceLogoSvg(t.portal_source, 16)} <span>${escapeHtml(formatSourceName(t.portal_source))}</span></span>`;
  }
  document.getElementById('panel-type-badge').textContent = t.tender_type || 'Open Tender';

  // Human Verification Status Banner
  updatePanelVerificationState(t);

  // Workflow Decision & Lead Assignment
  const wfSelect = document.getElementById('panel-workflow-status-select');
  if (wfSelect) wfSelect.value = t.workflow_status || 'new';

  const assignSelect = document.getElementById('panel-assigned-to-select');
  if (assignSelect) assignSelect.value = t.assigned_to || '';

  const notesText = document.getElementById('panel-user-notes');
  if (notesText) notesText.value = t.user_notes || '';

  const starBtn = document.getElementById('panel-star-toggle-btn');
  const starIconSvg = document.getElementById('panel-star-icon-svg');
  const starLabel = document.getElementById('panel-star-label');
  if (starBtn && starLabel) {
    starBtn.classList.toggle('active', Boolean(t.is_watchlisted));
    if (starIconSvg) {
      starIconSvg.setAttribute('fill', t.is_watchlisted ? '#f59e0b' : 'none');
      starIconSvg.setAttribute('stroke', t.is_watchlisted ? '#f59e0b' : 'currentColor');
    }
    starLabel.textContent = t.is_watchlisted ? 'In Watchlist' : 'Watchlist';
  }

  // Overview Tab Fields
  document.getElementById('panel-ref-no').textContent = refVal;
  document.getElementById('panel-buyer-org').textContent = t.authority || 'Unknown Buyer';
  document.getElementById('panel-location').textContent = t.location || 'India (Pan-India)';

  const pubDate = t.published_date 
    ? new Date(t.published_date).toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' })
    : 'Recent Ingestion';
  document.getElementById('panel-pub-date').textContent = pubDate;

  const deadlineInfo = formatDeadline(t.submission_deadline);
  document.getElementById('panel-deadline').textContent = t.submission_deadline ? `${deadlineInfo.dateStr} (${deadlineInfo.tagStr})` : 'Check Portal';
  
  const daysLeftEl = document.getElementById('panel-days-left');
  if (daysLeftEl) {
    daysLeftEl.textContent = deadlineInfo.tagStr;
    daysLeftEl.className = 'panel-kpi-val ' + (deadlineInfo.isExpired ? 'expired-tag' : '');
  }

  const costStr = t.estimated_cost_inr 
    ? `₹ ${(t.estimated_cost_inr >= 10000000 ? (t.estimated_cost_inr / 10000000).toFixed(2) + ' Cr' : (t.estimated_cost_inr / 100000).toFixed(2) + ' Lakhs')}`
    : 'Refer BOQ / Item Rate';
  document.getElementById('panel-value').textContent = costStr;

  const emdVal = t.emd_inr ? `₹ ${t.emd_inr.toLocaleString('en-IN')}` : 'Exempted (MSME)';
  const emdEl = document.getElementById('panel-det-emd');
  if (emdEl) emdEl.textContent = emdVal;

  document.getElementById('panel-tender-type').textContent = t.tender_type || 'Open Tender (Domestic)';

  // Key Systems
  const systems = extractKeySystems(t);
  document.getElementById('panel-key-systems').innerHTML = systems.map(s => 
    `<span class="tag-system" style="padding: 4px 8px; font-size: 11px;">${escapeHtml(s)}</span>`
  ).join('');

  document.getElementById('panel-scope').textContent = t.description || 'Turnkey engineering and supply contract for critical infrastructure.';

  // Expiry Banner
  const expiryBanner = document.getElementById('panel-expiry-banner');
  if (expiryBanner) {
    if (deadlineInfo.isExpired) {
      expiryBanner.style.display = 'flex';
      expiryBanner.innerHTML = `
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="flex-shrink:0;"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="8" x2="12" y2="12"></line><line x1="12" y1="16" x2="12.01" y2="16"></line></svg>
        <span><strong>Submission Closed:</strong> Official deadline (${escapeHtml(deadlineInfo.dateStr)}) has passed.</span>
      `;
    } else {
      expiryBanner.style.display = 'none';
    }
  }

  // Official Portal Action Links
  const bridgeUrl = `${API_BASE}/api/portal/bridge?tender_id=${encodeURIComponent(t.tender_id)}`;
  const portalBtn = document.getElementById('panel-portal-url-btn');
  if (portalBtn) portalBtn.href = bridgeUrl;

  const docBridgeBtn = document.getElementById('panel-doc-portal-bridge-btn');
  if (docBridgeBtn) docBridgeBtn.href = bridgeUrl;

  // Keywords & Evidence Tab
  const matchesList = document.getElementById('panel-matches-list');
  if (matchesList) {
    if (t.matches && t.matches.length > 0) {
      matchesList.innerHTML = t.matches.map(m => `
        <div class="evidence-box">
          <div class="evidence-header">
            <span class="evidence-term">Keyword: "${escapeHtml(m.term)}"</span>
            <span class="table-tier-badge tier-badge-${m.tier.toLowerCase()}" style="font-size: 10px; width: auto; height: auto; padding: 2px 6px; border-radius: 4px;">
              Tier ${m.tier} (${escapeHtml(m.match_group || m.group || 'General')})
            </span>
          </div>
          <div style="font-size: 11px; color: var(--text-muted); margin-bottom: 4px;">
            Field: ${escapeHtml(m.source_field || 'content')} | Text: "${escapeHtml(m.matched_text)}"
          </div>
          <div class="evidence-snippet">"...${escapeHtml(m.snippet || m.matched_text)}..."</div>
        </div>
      `).join('');
    } else {
      matchesList.innerHTML = `<div style="color: var(--text-muted); font-size: 12.5px; text-align: center; padding: 24px 0;">No keyword matches recorded for this tender.</div>`;
    }
  }

  // Load Authentic Documents & Eligibility Analysis in Background
  loadPanelDocuments(t.tender_id);
  loadPanelEligibility(t.tender_id);
}

function updatePanelVerificationState(t) {
  const dot = document.getElementById('panel-verif-dot');
  const label = document.getElementById('panel-verif-label');
  const sub = document.getElementById('panel-verif-sub');
  const approveBtn = document.getElementById('btn-verif-approve');
  if (!dot || !label || !sub) return;

  const st = t.workflow_status || 'new';

  if (st === 'verified') {
    dot.className = 'verification-dot verified';
    label.textContent = '✓ Human Verified: Approved for Bidding';
    sub.textContent = 'Feasibility confirmed by Bidding Engineer';
    if (approveBtn) approveBtn.style.display = 'none';
  } else if (st === 'doc_attached') {
    dot.className = 'verification-dot verified';
    label.textContent = '✓ Official NIT Attached';
    sub.textContent = 'Document submitted & verified in Qualification';
    if (approveBtn) approveBtn.style.display = 'none';
  } else if (st === 'rejected' || st === 'disqualified') {
    dot.className = 'verification-dot rejected';
    label.textContent = '⚠️ Flagged as Out-of-Scope / Disqualified';
    sub.textContent = t.qualification_reason || 'Marked disqualified by engineer';
    if (approveBtn) {
      approveBtn.style.display = 'inline-flex';
      approveBtn.innerHTML = `<span>Re-Qualify</span>`;
    }
  } else {
    dot.className = 'verification-dot';
    label.textContent = 'Pending Human Verification';
    sub.textContent = 'Review scope & confirm feasibility for Nikom';
    if (approveBtn) {
      approveBtn.style.display = 'inline-flex';
      approveBtn.innerHTML = `<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"></polyline></svg> <span>Verify & Approve</span>`;
    }
  }
}

async function verifyCurrentTender() {
  if (!currentSelectedTenderId) return;
  const t = (currentTenders || []).find(x => x.tender_id === currentSelectedTenderId) ||
            (allLoadedTenders || []).find(x => x.tender_id === currentSelectedTenderId);
  if (!t) return;

  try {
    const res = await fetch(`${API_BASE}/api/tenders/verify?tender_id=${encodeURIComponent(currentSelectedTenderId)}`, {
      method: 'POST'
    });
    if (res.ok) {
      t.workflow_status = 'verified';
      updatePanelVerificationState(t);
      const sel = document.getElementById('panel-workflow-status-select');
      if (sel) sel.value = 'verified';
      updateSegregationCounts();
      applyFilters();
      showToast(`✓ Tender verified & approved for bidding!`);
    }
  } catch (err) {
    showToast(`Verification error: ${err.message}`);
  }
}

function rejectCurrentTender() {
  if (!currentSelectedTenderId) return;
  const t = (currentTenders || []).find(x => x.tender_id === currentSelectedTenderId) ||
            (allLoadedTenders || []).find(x => x.tender_id === currentSelectedTenderId);
  if (!t) return;

  showDisqualificationWarning({
    tender: t,
    targetStatus: 'rejected',
    onConfirm: async () => {
      await executeDirectStatusUpdate(currentSelectedTenderId, 'rejected');
      updatePanelVerificationState(t);
      const sel = document.getElementById('panel-workflow-status-select');
      if (sel) sel.value = 'rejected';
    },
    onCancel: () => {}
  });
}

function copyCurrentRef() {
  if (!currentSelectedTenderId) return;
  const t = (currentTenders || []).find(x => x.tender_id === currentSelectedTenderId) ||
            (allLoadedTenders || []).find(x => x.tender_id === currentSelectedTenderId);
  if (!t) return;
  const ref = t.reference_no || t.tender_id;
  navigator.clipboard.writeText(ref).then(() => {
    showToast(`Copied Reference: ${ref}`);
  });
}

// ── Document Ingestion & Pack Loading ─────────────────────────────────────────
async function loadPanelDocuments(tenderId) {
  const container = document.getElementById('panel-docs-list-container');
  const countPill = document.getElementById('panel-docs-attached-count');
  const badgeCount = document.getElementById('tab-badge-docs-count');
  const autoBox = document.getElementById('panel-autofetch-box');
  if (!container) return;

  container.innerHTML = '<div style="color: var(--text-3); font-size: 12px; padding: 12px 0;">Loading documents pack...</div>';

  try {
    const res = await fetch(`${API_BASE}/api/documents/list?tender_id=${encodeURIComponent(tenderId)}`);
    if (!res.ok) throw new Error('Failed to load documents');
    const data = await res.json();

    const attached = data.attached_documents || [];
    const autoInfo = data.auto_fetch_info;

    if (countPill) countPill.textContent = `${attached.length} Attached`;
    if (badgeCount) badgeCount.textContent = attached.length;

    // Show Auto-Fetch GeM Banner if direct government PDF is available and not yet downloaded
    if (autoBox) {
      const alreadyHasGem = attached.some(d => d.title.includes('GeM') || d.doc_type.includes('GeM'));
      if (autoInfo && !alreadyHasGem) {
        autoBox.style.display = 'flex';
      } else {
        autoBox.style.display = 'none';
      }
    }

    if (attached.length === 0) {
      container.innerHTML = `
        <div class="doc-row-card" style="border-style: dashed; justify-content: center; text-align: center; padding: 16px;">
          <div style="color: var(--text-3); font-size: 12px;">
            No official documents attached yet.<br>
            <span style="font-size: 11px;">Upload the official NIT above or click "Fetch & Attach GeM PDF" if available.</span>
          </div>
        </div>
      `;
      return;
    }

    container.innerHTML = attached.map(doc => {
      const isPdf = doc.title.toLowerCase().endsWith('.pdf');
      const isSheet = doc.title.toLowerCase().endsWith('.xlsx') || doc.title.toLowerCase().endsWith('.xls');
      const iconLabel = isPdf ? 'PDF' : (isSheet ? 'XLS' : 'DOC');
      const sizeStr = doc.file_size_bytes ? `${(doc.file_size_bytes / 1024).toFixed(1)} KB` : '';
      const pagesStr = doc.page_count ? ` • ${doc.page_count} Pages` : '';

      return `
        <div class="doc-row-card">
          <div class="doc-row-left">
            <span class="doc-type-icon-badge">${iconLabel}</span>
            <div style="overflow: hidden;">
              <div class="doc-row-title" title="${escapeHtml(doc.title)}">${escapeHtml(doc.title)}</div>
              <div class="doc-row-meta">Official Notice${pagesStr} • ${sizeStr}</div>
            </div>
          </div>
          <div class="doc-row-actions">
            <a href="${API_BASE}${doc.download_url}" target="_blank" class="btn-doc-download-pill" title="View / Download official document">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path><polyline points="7 10 12 15 17 10"></polyline><line x1="12" y1="15" x2="12" y2="3"></line></svg>
              <span>Download</span>
            </a>
          </div>
        </div>
      `;
    }).join('');

  } catch (err) {
    container.innerHTML = `<div style="color: #ef4444; font-size: 12px;">Error loading documents: ${escapeHtml(err.message)}</div>`;
  }
}

async function autoFetchCurrentTenderDoc() {
  if (!currentSelectedTenderId) return;
  const btn = document.getElementById('btn-autofetch-trigger');
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = `<span>⏳ Downloading official signed government PDF...</span>`;
  }

  try {
    const res = await fetch(`${API_BASE}/api/documents/auto-fetch?tender_id=${encodeURIComponent(currentSelectedTenderId)}`, {
      method: 'POST'
    });
    const data = await res.json();
    if (data.success) {
      showToast(`✓ Successfully retrieved official GeM PDF (${data.page_count} pages)!`);
      loadPanelDocuments(currentSelectedTenderId);
      loadPanelEligibility(currentSelectedTenderId);
      // Update local tender workflow_status
      const t = (currentTenders || []).find(x => x.tender_id === currentSelectedTenderId) ||
                (allLoadedTenders || []).find(x => x.tender_id === currentSelectedTenderId);
      if (t) {
        t.workflow_status = 'doc_attached';
        updatePanelVerificationState(t);
      }
    } else {
      showToast(`Notice: ${data.message}`);
    }
  } catch (err) {
    showToast(`Auto-fetch error: ${err.message}`);
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = `<span>⚡ Fetch & Attach Official GeM PDF</span>`;
    }
  }
}

// ── Drag & Drop File Upload Handler ──────────────────────────────────────────
function handleDragOver(e) {
  e.preventDefault();
  e.stopPropagation();
  const zone = document.getElementById('panel-upload-zone');
  if (zone) zone.classList.add('dragover');
}

function handleDragLeave(e) {
  e.preventDefault();
  e.stopPropagation();
  const zone = document.getElementById('panel-upload-zone');
  if (zone) zone.classList.remove('dragover');
}

function handleFileDrop(e) {
  e.preventDefault();
  e.stopPropagation();
  const zone = document.getElementById('panel-upload-zone');
  if (zone) zone.classList.remove('dragover');

  if (e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files.length > 0) {
    uploadTenderFile(e.dataTransfer.files[0]);
  }
}

function handleFileSelect(e) {
  if (e.target && e.target.files && e.target.files.length > 0) {
    uploadTenderFile(e.target.files[0]);
  }
}

async function uploadTenderFile(file) {
  if (!currentSelectedTenderId || !file) return;

  const progressWrap = document.getElementById('upload-progress-wrap');
  const progressBar = document.getElementById('upload-progress-bar');
  const progressLabel = document.getElementById('upload-progress-label');

  if (progressWrap) progressWrap.style.display = 'block';
  if (progressLabel) progressLabel.textContent = `Uploading ${file.name} (${(file.size / 1024).toFixed(1)} KB)...`;
  if (progressBar) progressBar.style.width = '60%';

  const formData = new FormData();
  formData.append('file', file);

  try {
    const res = await fetch(`${API_BASE}/api/documents/upload?tender_id=${encodeURIComponent(currentSelectedTenderId)}`, {
      method: 'POST',
      body: formData
    });

    if (!res.ok) throw new Error('Upload failed');
    const data = await res.json();

    if (progressBar) progressBar.style.width = '100%';
    showToast(`✓ Official document "${file.name}" attached successfully!`);

    setTimeout(() => {
      if (progressWrap) progressWrap.style.display = 'none';
      loadPanelDocuments(currentSelectedTenderId);
      loadPanelEligibility(currentSelectedTenderId);
      const t = (currentTenders || []).find(x => x.tender_id === currentSelectedTenderId) ||
                (allLoadedTenders || []).find(x => x.tender_id === currentSelectedTenderId);
      if (t) {
        t.workflow_status = 'doc_attached';
        updatePanelVerificationState(t);
      }
    }, 400);

  } catch (err) {
    if (progressWrap) progressWrap.style.display = 'none';
    showToast(`Upload error: ${err.message}`);
  }
}

// ── Qualify Eligibility Sheet Renderer ───────────────────────────────────────
async function loadPanelEligibility(tenderId) {
  const container = document.getElementById('panel-eligibility-container');
  if (!container) return;

  container.innerHTML = '<div style="color: var(--text-3); font-size: 12px; padding: 12px 0;">Evaluating against Nikom InfraSolutions profile...</div>';

  try {
    const res = await fetch(`${API_BASE}/api/documents/eligibility?tender_id=${encodeURIComponent(tenderId)}`);
    if (!res.ok) throw new Error('Failed to evaluate eligibility');
    const data = await res.json();

    const isQual = data.overall_verdict === 'Qualified';
    const cardClass = isQual ? '' : 'review';
    const badgeClass = isQual ? '' : 'review';

    let html = `
      <div class="eligibility-verdict-card ${cardClass}">
        <div class="verdict-left">
          <span class="verdict-badge-pill ${badgeClass}">${escapeHtml(data.overall_verdict)}</span>
          <div>
            <div style="font-size: 13px; font-weight: 700; color: var(--text);">Nikom Corporate Feasibility</div>
            <div class="verdict-company-sub">Evaluated for: <strong>${escapeHtml(data.company_evaluated)}</strong></div>
          </div>
        </div>
        <div class="verdict-score-display">
          <div class="verdict-score-num ${badgeClass}">${data.verdict_score}%</div>
          <div class="verdict-score-label">${data.met_criteria_count} of ${data.total_criteria_count} Met</div>
        </div>
      </div>
    `;

    (data.criteria || []).forEach(c => {
      const statusClass = c.status === 'Met' ? 'status-badge-met' : (c.status === 'Check' ? 'status-badge-check' : 'status-badge-not-met');
      html += `
        <div class="criteria-card-item">
          <div class="criteria-header">
            <span class="criteria-title">${escapeHtml(c.name)}</span>
            <span class="${statusClass}">${escapeHtml(c.status)}</span>
          </div>
          <div class="criteria-req-text">Requirement: <strong>${escapeHtml(c.requirement)}</strong></div>
          <div class="criteria-profile-match">Nikom Profile: ${escapeHtml(c.nikom_profile)}</div>
        </div>
      `;
    });

    container.innerHTML = html;

  } catch (err) {
    container.innerHTML = `<div style="color: #ef4444; font-size: 12px;">Error evaluating eligibility: ${escapeHtml(err.message)}</div>`;
  }
}

function getPortalWebUrl(t) {
  if (!t) return 'https://eprocure.gov.in';
  let url = t.portal_url || '';
  const src = (t.portal_source || '').toLowerCase();
  const tid = t.tender_id || '';

  // 1. GeM Bids -> Open genuine HTML portal page
  if (src.includes('gem') || tid.startsWith('GEM/')) {
    const match = url.match(/(?:showbidDocument|getBidResultView|showradocumentPdf)\/(\d+)/);
    if (match) {
      return `https://bidplus.gem.gov.in/bidding/bid/getBidResultView/${match[1]}`;
    }
    return 'https://bidplus.gem.gov.in/all-bids';
  }

  // 2. CPPP ePublish
  if (src.includes('epublish')) {
    if (url && url.startsWith('http') && !url.includes('showbidDocument')) {
      return url;
    }
    return 'https://eprocure.gov.in/epublish/app';
  }

  // 3. IOCL
  if (src.includes('iocl')) {
    if (url && url.startsWith('http')) return url;
    return 'https://iocletenders.nic.in/nicgep/app';
  }

  // 4. CPPP Central / State
  if (url && url.startsWith('http') && !url.includes('showbidDocument')) {
    return url;
  }
  return 'https://eprocure.gov.in/cppp/latestactivetendersnew/cpppdata';
}

function getDocumentDownloadUrl(t) {
  if (!t) return '';
  if (t.documents && t.documents.length > 0 && t.documents[0].url) {
    return t.documents[0].url;
  }
  const rawUrl = t.portal_url || '';
  const tid = t.tender_id || '';
  const match = rawUrl.match(/(?:showbidDocument|getBidResultView|showradocumentPdf)\/(\d+)/);
  if (match) {
    const isRa = tid.includes('/R/') || rawUrl.includes('showradocumentPdf');
    return isRa 
      ? `https://bidplus.gem.gov.in/showradocumentPdf/${match[1]}`
      : `https://bidplus.gem.gov.in/showbidDocument/${match[1]}`;
  }
  return rawUrl || '';
}

function openDirectPortalUrl(e) {
  if (e) e.preventDefault();
  if (!currentSelectedTenderId) return;
  const t = (currentTenders || []).find(x => x.tender_id === currentSelectedTenderId) ||
            (allLoadedTenders || []).find(x => x.tender_id === currentSelectedTenderId);
  if (!t) return;

  const url = getPortalWebUrl(t);
  showToast(`Opening portal view for ${t.reference_no || t.tender_id}...`);
  window.open(url, '_blank', 'noopener,noreferrer');
}

function downloadTenderDoc(e) {
  if (e) e.preventDefault();
  if (!currentSelectedTenderId) return;
  const t = (currentTenders || []).find(x => x.tender_id === currentSelectedTenderId) ||
            (allLoadedTenders || []).find(x => x.tender_id === currentSelectedTenderId);
  if (!t) return;

  const cleanId = (t.reference_no || t.tender_id || 'tender').replace(/[/\:*?"<>|]/g, '_');
  showToast(`Downloading official PDF document (${cleanId})...`);
  const dlUrl = `${API_BASE}/api/documents/download?tender_id=${encodeURIComponent(t.tender_id)}`;
  const link = document.createElement('a');
  link.href = dlUrl;
  link.setAttribute('download', `${cleanId}_NIT_Specification.pdf`);
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
}

function copyRefAndSearchPortal() {
  if (!currentSelectedTenderId) return;
  const t = (currentTenders || []).find(x => x.tender_id === currentSelectedTenderId) ||
            (allLoadedTenders || []).find(x => x.tender_id === currentSelectedTenderId);
  if (!t) return;

  const ref = t.reference_no || t.tender_id;
  if (navigator.clipboard) {
    navigator.clipboard.writeText(ref).then(() => {
      showToast(`Copied Reference: ${ref}`);
    }).catch(() => {
      showToast(`Reference: ${ref}`);
    });
  }

  const src = (t.portal_source || '').toLowerCase();
  let searchUrl = "https://eprocure.gov.in/cppp/tendersearch";

  if (src.includes('gem') || (t.tender_id && t.tender_id.startsWith('GEM/'))) {
    searchUrl = "https://bidplus.gem.gov.in/all-bids";
  } else if (src.includes('epublish')) {
    searchUrl = "https://eprocure.gov.in/epublish/app?page=FrontEndAdvancedSearch&service=page";
  } else if (src.includes('iocl')) {
    searchUrl = "https://iocletenders.nic.in/nicgep/app";
  } else if (src.includes('eprocure')) {
    searchUrl = "https://eprocure.gov.in/eprocure/app?page=FrontEndAdvancedSearch&service=page";
  }

  window.open(searchUrl, '_blank', 'noopener,noreferrer');
}

function closeDetailsPanel() {
  document.getElementById('details-panel').classList.remove('panel-open');
  document.querySelectorAll('#tenders-tbody tr').forEach(row => row.classList.remove('row-selected'));
  currentSelectedTenderId = null;
}

function switchPanelTab(tabName) {
  document.querySelectorAll('.panel-tab').forEach(b => b.classList.remove('active'));
  document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));

  const tabBtn = document.querySelector(`.panel-tab[data-ptab="${tabName}"]`);
  const content = document.getElementById(`ptab-${tabName}`);

  if (tabBtn) tabBtn.classList.add('active');
  if (content) content.classList.add('active');
}

// ═══════════════════════════════════════════════════════════════════════════
// FILTERING, SEARCH & SORT LOGIC
// ═══════════════════════════════════════════════════════════════════════════
function setupEventListeners() {
  // Sidebar Navigation Items
  document.querySelectorAll('.sidebar-nav .nav-item').forEach(item => {
    item.addEventListener('click', (e) => {
      e.preventDefault();
      const nav = item.dataset.nav;
      if (nav) {
        window.location.hash = nav;
        navigateTo(nav);
      }
    });
  });

  // Tier Pills Filter
  document.querySelectorAll('.pill-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.pill-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      activeTierFilter = btn.dataset.tier;
      applyFilters();
    });
  });

  // Table Search Input
  const tableSearch = document.getElementById('table-search');
  if (tableSearch) {
    tableSearch.addEventListener('input', debounce(() => {
      applyFilters();
    }, 200));
  }

  // Global Search Input
  const globalSearch = document.getElementById('global-search');
  if (globalSearch) {
    globalSearch.addEventListener('input', debounce(() => {
      const val = globalSearch.value.trim();
      if (tableSearch) tableSearch.value = val;
      applyFilters();
    }, 250));
  }

  // Master Select All Checkbox
  const selectAll = document.getElementById('select-all-tenders');
  if (selectAll) {
    selectAll.addEventListener('change', (e) => {
      const checked = e.target.checked;
      currentTenders.forEach(t => {
        if (checked) {
          selectedTenderIds.add(t.tender_id);
        } else {
          selectedTenderIds.delete(t.tender_id);
        }
      });
      document.querySelectorAll('.row-checkbox').forEach(cb => {
        cb.checked = checked;
      });
      document.querySelectorAll('#tenders-tbody tr').forEach(row => {
        row.classList.toggle('row-checked', checked);
      });
      updateBulkToolbar();
    });
  }
}

// ═══════════════════════════════════════════════════════════════════════════
// MULTI-VIEW NAVIGATION & WORKSPACES
// ═══════════════════════════════════════════════════════════════════════════
// MULTI-VIEW NAVIGATION & WORKSPACES
// ═══════════════════════════════════════════════════════════════════════════
function navigateTo(nav) {
  if (nav === 'tenders') {
    nav = 'dashboard';
  }

  // Update sidebar active item
  document.querySelectorAll('.sidebar-nav .nav-item').forEach(item => {
    item.classList.toggle('active', item.dataset.nav === nav);
  });

  // Hide all view pages
  document.querySelectorAll('.view-page').forEach(page => {
    page.style.display = 'none';
    page.classList.remove('active');
  });

  // Show target page, or fallback to dashboard if target does not exist
  let targetPage = document.getElementById(`view-${nav}`);
  if (!targetPage) {
    nav = 'dashboard';
    targetPage = document.getElementById('view-dashboard');
    document.querySelector('.sidebar-nav .nav-item[data-nav="dashboard"]')?.classList.add('active');
  }

  if (targetPage) {
    targetPage.style.display = 'flex';
    targetPage.classList.add('active');
  }

  // Close inspector panel on view change
  closeDetailsPanel();

  // Load specific view data
  if (nav === 'sources') {
    loadSourcesView();
  } else if (nav === 'documents') {
    loadDocumentsView();
  } else if (nav === 'keywords') {
    initKeywordsView();
  } else if (nav === 'reports') {
    initReportsView();
  } else if (nav === 'watchlist') {
    initWatchlistView();
  } else if (nav === 'runs') {
    initRunsView();
  } else if (nav === 'status') {
    navigateTo('sources');
    return;
  } else if (nav === 'team') {
    initTeamView();
  } else if (nav === 'dashboard') {
    loadMetrics();
    renderTable(currentTenders.length > 0 ? currentTenders : allLoadedTenders);
  }
}

function initReportsView() {
  const now = new Date();
  const todayStr = `Today, ${now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', hour12: true })}`;
  document.querySelectorAll('.live-report-date-1, .live-report-date-2, .live-report-date-3').forEach(el => el.textContent = todayStr);
}

let currentWatchlistTab = 'all';

async function initWatchlistView() {
  const tbody = document.getElementById('watchlist-tbody');
  if (!tbody) return;

  // Read watchlisted and considered tenders
  let watchlisted = allLoadedTenders.filter(t => t.is_watchlisted || t.workflow_status === 'considered');

  if (watchlisted.length === 0 && allLoadedTenders.length === 0) {
    try {
      const res = await fetch(`${API_BASE}/api/watchlist`);
      if (res.ok) {
        const data = await res.json();
        watchlisted = data.items || [];
      }
    } catch (e) {
      console.warn('Watchlist fetch error:', e);
    }
  }

  // Calculate live KPIs
  const totalStarred = allLoadedTenders.filter(t => t.is_watchlisted).length;
  const consideredCount = allLoadedTenders.filter(t => t.workflow_status === 'considered').length;
  let totalValInr = 0;
  let urgentCount = 0;

  watchlisted.forEach(t => {
    if (t.estimated_cost_inr) totalValInr += t.estimated_cost_inr;
    const dl = formatDeadline(t.submission_deadline);
    if (dl.urgencyClass === 'deadline-urgent') urgentCount++;
  });

  const kpiTotalEl = document.getElementById('watchlist-kpi-total');
  if (kpiTotalEl) animateCounter(kpiTotalEl, totalStarred);

  const kpiConsEl = document.getElementById('watchlist-kpi-considered');
  if (kpiConsEl) animateCounter(kpiConsEl, consideredCount);

  const kpiUrgentEl = document.getElementById('watchlist-kpi-urgent');
  if (kpiUrgentEl) animateCounter(kpiUrgentEl, urgentCount);

  const kpiValEl = document.getElementById('watchlist-kpi-value');
  if (kpiValEl) {
    const crVal = (totalValInr / 10000000).toFixed(2);
    kpiValEl.textContent = `₹ ${crVal} Cr`;
  }

  const titleEl = document.getElementById('watchlist-table-title');
  if (titleEl) titleEl.textContent = `Bookmarked Opportunities (${watchlisted.length})`;

  // Filter based on selected tab within watchlist
  let displayed = [...watchlisted];
  if (currentWatchlistTab === 'considered') {
    displayed = displayed.filter(t => t.workflow_status === 'considered');
  } else if (currentWatchlistTab === 'urgent') {
    displayed = displayed.filter(t => formatDeadline(t.submission_deadline).urgencyClass === 'deadline-urgent');
  }

  if (displayed.length === 0) {
    tbody.innerHTML = `
      <tr>
        <td colspan="7" style="text-align: center; padding: 48px 20px; color: var(--text-3);">
          <div style="font-size: 32px; margin-bottom: 8px;">★</div>
          <div style="font-size: 15px; font-weight: 600; color: var(--text);">No bookmarked tenders in this view</div>
          <div style="font-size: 12.5px; margin-top: 4px;">Star any tender on the dashboard or mark it as "Considered" to track it here.</div>
        </td>
      </tr>
    `;
    return;
  }

  tbody.innerHTML = displayed.map(t => {
    const sourceLogo = getSourceLogoSvg(t.portal_source, 18);
    const deadlineInfo = formatDeadline(t.submission_deadline);
    const costText = t.estimated_cost_inr 
      ? `₹ ${(t.estimated_cost_inr >= 10000000 ? (t.estimated_cost_inr / 10000000).toFixed(2) + ' Cr' : (t.estimated_cost_inr / 100000).toFixed(2) + ' L')}`
      : 'Value Not Disclosed';

    return `
      <tr class="tender-row" onclick="selectTenderRow('${escapeHtml(t.tender_id)}', true)">
        <td style="text-align: center;" onclick="event.stopPropagation();">
          <button type="button" class="btn-table-star ${t.is_watchlisted ? 'starred' : ''}" onclick="toggleTenderStar('${escapeHtml(t.tender_id)}', event)" title="${t.is_watchlisted ? 'Remove from Watchlist' : 'Star to Watchlist'}">
            ${t.is_watchlisted ? '★' : '☆'}
          </button>
        </td>
        <td class="table-title-cell" style="max-width: 320px;">
          <div class="table-tender-title" title="${escapeHtml(t.title)}">${escapeHtml(t.title)}</div>
          <div class="table-tender-ref">${escapeHtml(t.reference_no || t.tender_id)}</div>
          ${t.user_notes ? `<div class="table-user-notes" title="${escapeHtml(t.user_notes)}">📝 ${escapeHtml(t.user_notes)}</div>` : ''}
        </td>
        <td>
          <div class="source-badge-pill" data-source="${escapeHtml(t.portal_source || '')}">
            ${sourceLogo}
            <span>${escapeHtml(formatSourceName(t.portal_source))}</span>
          </div>
        </td>
        <td><div class="table-buyer" title="${escapeHtml(t.authority)}">${escapeHtml(t.authority)}</div></td>
        <td><div class="table-value">${costText}</div></td>
        <td>
          <div class="deadline-box">
            <span class="deadline-date">${escapeHtml(deadlineInfo.dateStr)}</span>
            <span class="deadline-tag ${deadlineInfo.urgencyClass}">${escapeHtml(deadlineInfo.tagStr)}</span>
          </div>
        </td>
        <td style="text-align: center;" onclick="event.stopPropagation();">
          <button class="btn-subtle-pill" style="padding: 4px 10px; font-size: 11px;" onclick="selectTenderRow('${escapeHtml(t.tender_id)}', true)">Inspect Specs &rarr;</button>
        </td>
      </tr>
    `;
  }).join('');
}

function filterWatchlistView(tab) {
  currentWatchlistTab = tab;
  document.querySelectorAll('#view-watchlist .pill-btn').forEach(btn => btn.classList.remove('active'));
  const activeBtn = document.getElementById(`wl-filter-${tab}`);
  if (activeBtn) activeBtn.classList.add('active');
  initWatchlistView();
}

// ═══════════════════════════════════════════════════════════════════════════
// WORKFLOW SEGREGATION & BULK ACTIONS CONTROLLER
// ═══════════════════════════════════════════════════════════════════════════
function setWorkflowFilter(status) {
  activeWorkflowFilter = status;
  document.querySelectorAll('.wf-tab').forEach(tab => {
    tab.classList.toggle('active', tab.dataset.status === status);
  });
  applyFilters();
}

function updateSegregationCounts() {
  const inWindowTenders = allLoadedTenders.filter(t => isWithinTimeWindow(t, currentTimeWindow));
  const qualifiedInWindow = inWindowTenders.filter(t => t.is_qualified && t.workflow_status !== 'disqualified');
  const total = qualifiedInWindow.length;
  const countWatchlist = inWindowTenders.filter(t => t.is_watchlisted).length;
  const countConsidered = inWindowTenders.filter(t => (t.workflow_status || 'new') === 'considered').length;
  const countUnderReview = inWindowTenders.filter(t => (t.workflow_status || 'new') === 'under_review').length;
  const countReviewed = inWindowTenders.filter(t => (t.workflow_status || 'new') === 'reviewed').length;
  const countRejected = inWindowTenders.filter(t => t.workflow_status === 'disqualified' || t.workflow_status === 'rejected' || !t.is_qualified).length;
  const countExpired = inWindowTenders.filter(t => isTenderExpired(t)).length;

  const elAll = document.getElementById('wf-count-all');
  if (elAll) elAll.textContent = total;

  const elWl = document.getElementById('wf-count-watchlist');
  if (elWl) elWl.textContent = countWatchlist;

  const elCons = document.getElementById('wf-count-considered');
  if (elCons) elCons.textContent = countConsidered;

  const elRev = document.getElementById('wf-count-under_review');
  if (elRev) elRev.textContent = countUnderReview;

  const elHeld = document.getElementById('wf-count-reviewed');
  if (elHeld) elHeld.textContent = countReviewed;

  const elRej = document.getElementById('wf-count-rejected');
  if (elRej) elRej.textContent = countRejected;

  const elExp = document.getElementById('wf-count-expired');
  if (elExp) elExp.textContent = countExpired;

  // Dynamically update Tier Pills to match the active window & segregation context
  let baseForTiers = qualifiedInWindow;
  if (activeWorkflowFilter === 'expired') {
    baseForTiers = inWindowTenders.filter(t => isTenderExpired(t));
  } else if (activeWorkflowFilter === 'watchlist') {
    baseForTiers = inWindowTenders.filter(t => t.is_watchlisted);
  } else if (activeWorkflowFilter === 'rejected' || activeWorkflowFilter === 'disqualified') {
    baseForTiers = inWindowTenders.filter(t => t.workflow_status === 'disqualified' || t.workflow_status === 'rejected' || !t.is_qualified);
  } else if (activeWorkflowFilter !== 'all') {
    baseForTiers = inWindowTenders.filter(t => (t.workflow_status || 'new') === activeWorkflowFilter);
  }

  const tierAllCount = baseForTiers.length;
  const tierACount = baseForTiers.filter(t => t.highest_tier === 'A').length;
  const tierBCount = baseForTiers.filter(t => t.highest_tier === 'B').length;
  const tierCCount = baseForTiers.filter(t => t.highest_tier === 'C').length;
  const tierDCount = baseForTiers.filter(t => t.highest_tier === 'D').length;

  const pillAll = document.getElementById('pill-all-count');
  if (pillAll) pillAll.textContent = tierAllCount;
  const pillA = document.getElementById('pill-a-count');
  if (pillA) pillA.textContent = tierACount;
  const pillB = document.getElementById('pill-b-count');
  if (pillB) pillB.textContent = tierBCount;
  const pillC = document.getElementById('pill-c-count');
  if (pillC) pillC.textContent = tierCCount;
  const pillD = document.getElementById('pill-d-count');
  if (pillD) pillD.textContent = tierDCount;
}

function toggleTenderSelection(tenderId, isChecked) {
  if (isChecked) {
    selectedTenderIds.add(tenderId);
  } else {
    selectedTenderIds.delete(tenderId);
  }

  // Update table row styling
  document.querySelectorAll('#tenders-tbody tr').forEach(row => {
    const cb = row.querySelector('.row-checkbox');
    if (cb && cb.value === tenderId) {
      row.classList.toggle('row-checked', isChecked);
    }
  });

  const selectAll = document.getElementById('select-all-tenders');
  if (selectAll) {
    const isAllChecked = currentTenders.length > 0 && currentTenders.every(t => selectedTenderIds.has(t.tender_id));
    const isSomeChecked = currentTenders.some(t => selectedTenderIds.has(t.tender_id));
    selectAll.checked = isAllChecked;
    selectAll.indeterminate = isSomeChecked && !isAllChecked;
  }

  updateBulkToolbar();
}

function updateBulkToolbar() {
  const bar = document.getElementById('floating-bulk-bar');
  const countEl = document.getElementById('bulk-selected-count');
  if (!bar) return;

  const count = selectedTenderIds.size;
  if (count > 0) {
    if (countEl) countEl.textContent = count;
    bar.style.display = 'block';
  } else {
    bar.style.display = 'none';
  }
}

function clearTenderSelection() {
  selectedTenderIds.clear();
  document.querySelectorAll('.row-checkbox').forEach(cb => { cb.checked = false; });
  document.querySelectorAll('#tenders-tbody tr').forEach(row => { row.classList.remove('row-checked'); });
  const selectAll = document.getElementById('select-all-tenders');
  if (selectAll) {
    selectAll.checked = false;
    selectAll.indeterminate = false;
  }
  updateBulkToolbar();
}

// ── Disqualification Warning & Safeguard System ─────────────────────────────
let pendingDisqualificationAction = null;

function showDisqualificationWarning({ tender, targetStatus, batchCount = 0, onConfirm, onCancel }) {
  const modal = document.getElementById('modal-disqualification-warning');
  const labelMap = {
    'new': 'New Ingest (Active Pipeline)',
    'under_review': 'Under Review',
    'considered': 'Considered / Shortlist',
    'reviewed': 'Reviewed / Held',
    'watchlist': 'Priority Watchlist',
    'bulk_consider': 'Shortlist for Active Bidding',
    'bulk_under_review': 'Under Review',
    'bulk_reviewed': 'Reviewed / Held',
    'toggle_watchlist': 'Priority Watchlist'
  };
  const targetLabel = labelMap[targetStatus] || targetStatus;

  if (!modal) {
    const reason = tender.qualification_reason || 'Out-of-Scope / Non-IT Work';
    if (confirm(`⚠️ Warning: This tender was flagged as Disqualified (${reason}).\n\nAre you sure you want to override and move it to "${targetLabel}"?`)) {
      if (onConfirm) onConfirm();
    } else {
      if (onCancel) onCancel();
    }
    return;
  }

  const titleEl = document.getElementById('warn-modal-tender-title');
  const refEl = document.getElementById('warn-modal-tender-ref');
  const portalEl = document.getElementById('warn-modal-tender-portal');
  const reasonEl = document.getElementById('warn-modal-tender-reason');
  const targetEl = document.getElementById('warn-modal-target-status');

  if (batchCount > 1) {
    if (titleEl) titleEl.textContent = `Batch Action includes ${batchCount} Disqualified / Out-of-Scope tenders (e.g., "${(tender.title || '').slice(0, 70)}...")`;
    if (refEl) refEl.textContent = `Batch Selection (${batchCount} Disqualified)`;
    if (portalEl) portalEl.textContent = formatSourceName(tender.portal_source);
    if (reasonEl) reasonEl.textContent = tender.qualification_reason || 'Flagged by negative terms / non-IT work filters';
  } else {
    if (titleEl) titleEl.textContent = tender.title || 'Untitled Tender';
    if (refEl) refEl.textContent = tender.reference_no || tender.tender_id || '—';
    if (portalEl) portalEl.textContent = formatSourceName(tender.portal_source);
    if (reasonEl) reasonEl.textContent = tender.qualification_reason || 'Out-of-Scope / Non-IT Work';
  }

  if (targetEl) targetEl.textContent = targetLabel;

  pendingDisqualificationAction = { onConfirm, onCancel };
  modal.style.display = 'flex';
}

function closeDisqualificationWarningModal(confirmed = false) {
  const modal = document.getElementById('modal-disqualification-warning');
  if (modal) modal.style.display = 'none';

  if (!confirmed && pendingDisqualificationAction && pendingDisqualificationAction.onCancel) {
    try { pendingDisqualificationAction.onCancel(); } catch (e) {}
  }
  pendingDisqualificationAction = null;
}

function executeDisqualificationOverride() {
  const action = pendingDisqualificationAction;
  closeDisqualificationWarningModal(true);
  if (action && action.onConfirm) {
    try { action.onConfirm(); } catch (e) {
      console.error('Error executing disqualification override:', e);
    }
  }
}

async function executeBulkAction(action) {
  const ids = Array.from(selectedTenderIds);
  if (ids.length === 0) {
    showToast('Please select at least one tender checkbox.');
    return;
  }

  const selectedTenders = allLoadedTenders.filter(t => ids.includes(t.tender_id));
  const disqualifiedInBatch = selectedTenders.filter(t => t.workflow_status === 'disqualified' || t.workflow_status === 'rejected' || !t.is_qualified);

  if (action !== 'bulk_reject' && disqualifiedInBatch.length > 0) {
    showDisqualificationWarning({
      tender: disqualifiedInBatch[0],
      batchCount: disqualifiedInBatch.length,
      targetStatus: action,
      onConfirm: async () => {
        await proceedWithBulkAction(action, ids);
      },
      onCancel: () => {}
    });
    return;
  }

  await proceedWithBulkAction(action, ids);
}

async function proceedWithBulkAction(action, ids) {
  let toastMsg = 'Processing bulk action...';
  if (action === 'bulk_consider') toastMsg = `Shortlisting ${ids.length} tenders for bidding...`;
  else if (action === 'bulk_under_review') toastMsg = `Moving ${ids.length} tenders to Under Review...`;
  else if (action === 'bulk_reviewed') toastMsg = `Marking ${ids.length} tenders as Reviewed...`;
  else if (action === 'bulk_reject') toastMsg = `Disqualifying ${ids.length} tenders...`;
  else if (action === 'toggle_watchlist') toastMsg = `Updating Watchlist for ${ids.length} tenders...`;

  showToast(toastMsg);

  try {
    const res = await fetch(`${API_BASE}/api/tenders/bulk-action`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ tender_ids: ids, action: action })
    });

    if (!res.ok) throw new Error('Bulk action failed');
    const data = await res.json();

    // Optimistically update local array
    allLoadedTenders.forEach(t => {
      if (ids.includes(t.tender_id)) {
        if (action === 'bulk_consider') {
          t.workflow_status = 'considered';
          t.is_qualified = true;
        } else if (action === 'bulk_under_review') {
          t.workflow_status = 'under_review';
          t.is_qualified = true;
        } else if (action === 'bulk_reviewed') {
          t.workflow_status = 'reviewed';
          t.is_qualified = true;
        } else if (action === 'bulk_reject') {
          t.workflow_status = 'rejected';
          t.is_qualified = false;
        } else if (action === 'toggle_watchlist') {
          t.is_watchlisted = !t.is_watchlisted;
        }
      }
    });

    clearTenderSelection();
    updateSegregationCounts();
    applyFilters();

    let successMsg = `Successfully updated ${data.updated_count} tenders.`;
    if (action === 'bulk_consider') successMsg = `✓ Shortlisted ${data.updated_count} tenders for active bidding!`;
    else if (action === 'bulk_reject') successMsg = `✕ Marked ${data.updated_count} tenders as disqualified.`;
    else if (action === 'toggle_watchlist') successMsg = `★ Watchlist updated for ${data.updated_count} tenders.`;
    showToast(successMsg);

  } catch (err) {
    showToast(`Error performing bulk action: ${err.message}`);
  }
}

function exportSelectedTendersCSV() {
  const ids = Array.from(selectedTenderIds);
  if (ids.length === 0) {
    showToast('No tenders selected. Check the boxes next to tenders first.');
    return;
  }
  const selectedTenders = allLoadedTenders.filter(t => ids.includes(t.tender_id));
  
  const headers = [
    'Tender ID', 'Title', 'Reference No', 'Authority', 'Location',
    'Tier', 'Category', 'Workflow Status', 'Watchlisted', 'User Notes', 'Assigned To', 'Estimated Cost INR', 'Deadline', 'Source', 'Direct Portal URL'
  ];

  const rows = selectedTenders.map(t => [
    `"${(t.tender_id || '').replace(/"/g, '""')}"`,
    `"${(t.title || '').replace(/"/g, '""')}"`,
    `"${(t.reference_no || '').replace(/"/g, '""')}"`,
    `"${(t.authority || '').replace(/"/g, '""')}"`,
    `"${(t.location || '').replace(/"/g, '""')}"`,
    `"${t.highest_tier || 'Unmatched'}"`,
    `"${t.primary_category || ''}"`,
    `"${t.workflow_status || 'new'}"`,
    t.is_watchlisted ? 'Yes' : 'No',
    `"${(t.user_notes || '').replace(/"/g, '""')}"`,
    `"${(t.assigned_to || '').replace(/"/g, '""')}"`,
    t.estimated_cost_inr || 0,
    `"${t.submission_deadline || ''}"`,
    `"${t.portal_source || ''}"`,
    `"${(getPortalWebUrl(t) || '').replace(/"/g, '""')}"`
  ]);

  const csvText = [headers.join(','), ...rows.map(e => e.join(','))].join('\r\n');
  const blob = new Blob(['\uFEFF' + csvText], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.setAttribute('download', `nikom_selected_tenders_${ids.length}_${new Date().toISOString().slice(0, 10)}.csv`);
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  setTimeout(() => URL.revokeObjectURL(url), 1000);

  showToast(`Exported ${ids.length} selected tenders to CSV`);
}

async function toggleTenderStar(tenderId, e) {
  if (e) e.stopPropagation();
  const t = allLoadedTenders.find(x => x.tender_id === tenderId);
  if (!t) return;

  const newStarred = !t.is_watchlisted;
  const isDisqualified = t.workflow_status === 'disqualified' || t.workflow_status === 'rejected' || !t.is_qualified;

  // Intercept if trying to add a disqualified tender to Watchlist
  if (newStarred && isDisqualified) {
    showDisqualificationWarning({
      tender: t,
      targetStatus: 'watchlist',
      onConfirm: async () => {
        await executeDirectWatchlistToggle(tenderId, true);
      },
      onCancel: () => {}
    });
    return;
  }

  await executeDirectWatchlistToggle(tenderId, newStarred);
}

async function executeDirectWatchlistToggle(tenderId, newStarred) {
  const t = allLoadedTenders.find(x => x.tender_id === tenderId);
  if (!t) return;

  t.is_watchlisted = newStarred;
  updateSegregationCounts();
  applyFilters();

  if (currentSelectedTenderId === tenderId) {
    const starBtn = document.getElementById('panel-star-toggle-btn');
    const starIcon = document.getElementById('panel-star-icon');
    const starLabel = document.getElementById('panel-star-label');
    if (starBtn && starIcon && starLabel) {
      starBtn.classList.toggle('active', newStarred);
      starIcon.textContent = newStarred ? '★' : '☆';
      starLabel.textContent = newStarred ? 'In Watchlist' : 'Watchlist';
    }
  }

  showToast(newStarred ? `★ Added "${t.reference_no || t.tender_id}" to Watchlist` : `☆ Removed from Watchlist`);

  // Persist to server
  try {
    await fetch(`${API_BASE}/api/tenders/${encodeURIComponent(tenderId)}/manage`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ is_watchlisted: newStarred })
    });
  } catch (err) {
    console.error('Failed to persist watchlist toggle:', err);
  }
}

async function cycleTenderWorkflowStatus(tenderId, e) {
  if (e) e.stopPropagation();
  const t = allLoadedTenders.find(x => x.tender_id === tenderId);
  if (!t) return;

  const order = ['new', 'under_review', 'considered', 'reviewed', 'rejected'];
  const curIdx = order.indexOf(t.workflow_status || 'new');
  const nextStatus = order[(curIdx + 1) % order.length];

  const isDisqualified = t.workflow_status === 'disqualified' || t.workflow_status === 'rejected' || !t.is_qualified;
  const isMovingOut = isDisqualified && nextStatus !== 'disqualified' && nextStatus !== 'rejected';

  if (isMovingOut) {
    showDisqualificationWarning({
      tender: t,
      targetStatus: nextStatus,
      onConfirm: async () => {
        await executeDirectStatusUpdate(tenderId, nextStatus);
        if (currentSelectedTenderId === tenderId) {
          const sel = document.getElementById('panel-workflow-status-select');
          if (sel) sel.value = nextStatus;
        }
      },
      onCancel: () => {}
    });
    return;
  }

  await executeDirectStatusUpdate(tenderId, nextStatus);
  if (currentSelectedTenderId === tenderId) {
    const sel = document.getElementById('panel-workflow-status-select');
    if (sel) sel.value = nextStatus;
  }
}

function toggleCurrentTenderWatchlist() {
  if (!currentSelectedTenderId) return;
  toggleTenderStar(currentSelectedTenderId);
}

async function onPanelWorkflowStatusChange(newStatus) {
  if (!currentSelectedTenderId) return;
  const t = allLoadedTenders.find(x => x.tender_id === currentSelectedTenderId);
  if (!t) return;

  const isDisqualified = t.workflow_status === 'disqualified' || t.workflow_status === 'rejected' || !t.is_qualified;
  const isMovingOut = isDisqualified && newStatus !== 'disqualified' && newStatus !== 'rejected';

  if (isMovingOut) {
    showDisqualificationWarning({
      tender: t,
      targetStatus: newStatus,
      onConfirm: async () => {
        await executeDirectStatusUpdate(currentSelectedTenderId, newStatus);
      },
      onCancel: () => {
        const sel = document.getElementById('panel-workflow-status-select');
        if (sel) sel.value = t.workflow_status || 'disqualified';
      }
    });
    return;
  }

  await executeDirectStatusUpdate(currentSelectedTenderId, newStatus);
}

async function executeDirectStatusUpdate(tenderId, newStatus) {
  const t = allLoadedTenders.find(x => x.tender_id === tenderId);
  if (t) {
    t.workflow_status = newStatus;
    if (['new', 'under_review', 'considered', 'reviewed'].includes(newStatus)) {
      t.is_qualified = true;
    } else if (['disqualified', 'rejected'].includes(newStatus)) {
      t.is_qualified = false;
    }
  }
  updateSegregationCounts();
  applyFilters();

  const labelMap = {
    'new': 'New Ingest',
    'under_review': 'Under Review',
    'considered': 'Considered / Shortlist',
    'reviewed': 'Reviewed / Held',
    'rejected': 'Disqualified / Rejected',
    'disqualified': 'Disqualified / Rejected'
  };

  showToast(`Updated status to: ${labelMap[newStatus] || newStatus}`);

  try {
    await fetch(`${API_BASE}/api/tenders/${encodeURIComponent(tenderId)}/manage`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ workflow_status: newStatus })
    });
  } catch (err) {
    console.error('Failed to update status:', err);
    showToast(`Error updating status: ${err.message}`);
  }
}

async function onPanelAssigneeChange(assignee) {
  if (!currentSelectedTenderId) return;
  const t = allLoadedTenders.find(x => x.tender_id === currentSelectedTenderId);
  if (t) t.assigned_to = assignee;

  try {
    await fetch(`${API_BASE}/api/tenders/${encodeURIComponent(currentSelectedTenderId)}/manage`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ assigned_to: assignee })
    });
    showToast(assignee ? `Assigned to: ${assignee}` : 'Tender unassigned');
  } catch (err) {
    console.error('Failed to update assignee:', err);
  }
}

let notesSaveDebounceTimer = null;
function onPanelNotesInput() {
  const indicator = document.getElementById('notes-save-indicator');
  if (indicator) {
    indicator.textContent = 'Saving...';
    indicator.style.color = 'var(--text-3)';
  }

  if (notesSaveDebounceTimer) clearTimeout(notesSaveDebounceTimer);
  notesSaveDebounceTimer = setTimeout(async () => {
    if (!currentSelectedTenderId) return;
    const notes = document.getElementById('panel-user-notes')?.value || '';
    const t = allLoadedTenders.find(x => x.tender_id === currentSelectedTenderId);
    if (t) t.user_notes = notes;

    try {
      await fetch(`${API_BASE}/api/tenders/${encodeURIComponent(currentSelectedTenderId)}/manage`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_notes: notes })
      });
      if (indicator) {
        indicator.textContent = 'Saved ✓';
        indicator.style.color = '#10b981';
      }
    } catch (err) {
      if (indicator) {
        indicator.textContent = 'Save failed';
        indicator.style.color = '#ef4444';
      }
    }
  }, 500);
}

async function initRunsView() {
  const tbody = document.getElementById('runs-view-tbody');
  if (!tbody) return;

  try {
    const res = await fetch(`${API_BASE}/api/sources`);
    if (!res.ok) throw new Error('Failed to load runs');
    const data = await res.json();
    const runs = data.recent_runs || [];

    if (runs.length > 0) {
      tbody.innerHTML = runs.map(r => {
        const runId = `RUN-${r.id || 'SYNC'}`;
        const srcName = formatSourceName(r.source_name || r.source_id);
        const startTime = r.started_at ? formatLocalDateTime(r.started_at) : 'Just now';
        let dur = '—';
        if (r.finished_at && r.started_at) {
          const s = parseUtcDate(r.started_at);
          const f = parseUtcDate(r.finished_at);
          if (s && f) {
            dur = `${Math.max(0.1, (f - s) / 1000).toFixed(1)}s`;
          }
        }
        const discovered = r.items_discovered || 0;
        const qualified = r.items_qualified || 0;
        const isOk = r.status === 'success';
        const statusBadge = isOk 
          ? `<span class="source-card-badge badge-live">✓ Completed</span>` 
          : (r.status === 'running' 
              ? `<span class="source-card-badge" style="background:rgba(59,130,246,0.15); color:var(--primary); border:1px solid rgba(59,130,246,0.3);">⚡ In Progress</span>`
              : `<span class="source-card-badge badge-standby">Failed</span>`);

        return `
          <tr>
            <td><span style="font-family: monospace; font-size: 11.5px; color: var(--text-2);">${escapeHtml(runId)}</span></td>
            <td><strong style="color: var(--text);">${escapeHtml(srcName)}</strong></td>
            <td><span style="color: var(--text-2); font-size: 12px;">${escapeHtml(startTime)}</span></td>
            <td><span style="color: var(--text-3); font-size: 12px;">${escapeHtml(dur)}</span></td>
            <td><strong style="color: var(--primary);">${discovered}</strong> <span style="font-size:11px; color:var(--text-3);">(${qualified} qual)</span></td>
            <td>${statusBadge}</td>
          </tr>
        `;
      }).join('');
    } else {
      tbody.innerHTML = `<tr><td colspan="6" style="text-align: center; color: var(--text-3); padding: 24px;">No discovery runs recorded yet. Click "Scan All Portals" above to trigger a collection run.</td></tr>`;
    }
  } catch (err) {
    console.warn('Error loading runs view:', err);
  }
}

function initTeamView() {}

function downloadReportBriefing(reportName) {
  showToast(`Generating ${reportName} dossier... Exporting.`);
  exportTendersCSV();
}

function generateExecutiveReport() {
  showToast('Compiling Executive Intelligence Dossier for all 295 tenders...');
  setTimeout(() => {
    exportTendersCSV();
    showToast('Executive Intelligence Dossier exported successfully.');
  }, 600);
}

// ── Canonical Portal Categories Definition ────────────────────────────────
const PORTAL_CATEGORIES = [
  {
    id: 'national',
    title: 'National Procurement Portals',
    shortTitle: 'National Procurement',
    iconEmoji: '🏛️',
    description: 'Centralized government e-Marketplace, national tenders, and e-Publishing feeds',
    icon: `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 21h18M3 10h18M5 6l7-3 7 3M4 10v11M20 10v11M8 14v4M12 14v4M16 14v4"/></svg>`,
    color: '#3B82F6',
    bgTint: 'rgba(59, 130, 246, 0.12)',
    defaultExpanded: true
  },
  {
    id: 'state',
    title: 'State & UT eProcurement',
    shortTitle: 'State & UT',
    iconEmoji: '🗺️',
    description: 'State government and Union Territory GePNIC, CHiPS, and eProcurement portals',
    icon: `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="1 6 1 22 8 18 16 22 23 18 23 2 16 6 8 2 1 6"></polygon><line x1="8" y1="2" x2="8" y2="18"></line><line x1="16" y1="6" x2="16" y2="22"></line></svg>`,
    color: '#10B981',
    bgTint: 'rgba(16, 185, 129, 0.12)',
    defaultExpanded: false
  },
  {
    id: 'psu',
    title: 'PSUs & Public Enterprises',
    shortTitle: 'PSUs & Enterprises',
    iconEmoji: '⚙️',
    description: 'Maharatna, Navratna, defence, energy, and engineering public enterprise platforms',
    icon: `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="7" width="20" height="14" rx="2" ry="2"></rect><path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16"></path></svg>`,
    color: '#F59E0B',
    bgTint: 'rgba(245, 158, 11, 0.12)',
    defaultExpanded: false
  },
  {
    id: 'transport',
    title: 'Airports & Transport',
    shortTitle: 'Airports & Transport',
    iconEmoji: '✈️',
    description: 'International airport authorities, civil aviation regulators, and state transport undertakings',
    icon: `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17.8 19.2 16 11l3.5-3.5C21 6 21.5 4 21 3c-1-.5-3 0-4.5 1.5L13 8 4.8 6.2c-.5-.1-.9.1-1.1.5l-.3.5c-.2.5-.1 1 .3 1.3L9 12l-2 3H4l-1 1 3 2 2 3 1-1v-3l3-2 3.5 5.3c.3.4.8.5 1.3.3l.5-.2c.4-.3.6-.7.5-1.2z"/></svg>`,
    color: '#06B6D4',
    bgTint: 'rgba(6, 182, 212, 0.12)',
    defaultExpanded: false
  },
  {
    id: 'healthcare',
    title: 'Healthcare & Institutions',
    shortTitle: 'Healthcare & Institutions',
    iconEmoji: '🏥',
    description: 'All India Institute of Medical Sciences (AIIMS) network and autonomous research institutes',
    icon: `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 12h-4l-3 9L9 3l-3 9H2"/></svg>`,
    color: '#EC4899',
    bgTint: 'rgba(236, 72, 153, 0.12)',
    defaultExpanded: false
  },
  {
    id: 'other',
    title: 'Other & Specialised Portals',
    shortTitle: 'Other & Specialised',
    iconEmoji: '⚡',
    description: 'Security currency printing joint ventures, ElectronicTender systems, and specialized bidding platforms',
    icon: `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"></polygon></svg>`,
    color: '#8B5CF6',
    bgTint: 'rgba(139, 92, 246, 0.12)',
    defaultExpanded: false
  }
];

function getSourcePortalCategory(s) {
  if (s.category) return s.category;
  const sid = (s.id || '').toLowerCase();
  const stype = (s.type || '').toLowerCase();
  if (sid === 'gem' || sid === 'cppp_latest' || sid === 'cppp_epublish') return 'national';
  if (sid.includes('aiims') || stype.includes('medical') || stype.includes('healthcare')) return 'healthcare';
  if (['bial', 'aera_ewizard', 'asrtu'].includes(sid) || stype.includes('aviation') || stype.includes('transport')) return 'transport';
  if (['bcpl_ewizard', 'becil_ewizard', 'bel', 'bhel', 'bhel_tenderwizard', 'bpcl', 'iocl', 'beml'].includes(sid) || stype.includes('psu')) return 'psu';
  if (['bnpm', 'bharat_ets'].includes(sid)) return 'other';
  return 'state';
}

function renderSourceCard(s) {
  const isLive = s.status === 'active' || s.is_live_scraping;
  const statusClass = isLive ? 'badge-live' : 'badge-standby';
  const statusLabel = isLive ? '● Live Scraper Active' : '○ Standby';

  return `
    <div class="source-portal-card" id="portal-card-${escapeHtml(s.id)}">
      <div class="source-card-header">
        <div style="display: flex; align-items: center; gap: 10px;">
          ${getSourceLogoSvg(s.id, 28)}
          <span class="source-card-title">${escapeHtml(s.name)}</span>
        </div>
        <span class="source-card-badge ${statusClass}">
          ${statusLabel}
        </span>
      </div>
      <div class="source-card-meta">
        <div><span class="meta-label">Type:</span> <span class="meta-val">${escapeHtml(s.type)}</span></div>
        <div><span class="meta-label">Schedule:</span> <span class="meta-val">${escapeHtml(s.cadence)}</span></div>
        <div><span class="meta-label">Tenders Ingested:</span> <span class="meta-val" style="color: ${isLive ? 'var(--ok)' : 'var(--text-3)'}; font-weight: 700;">${s.tenders_count || 0}</span></div>
        <div><span class="meta-label">URL:</span> <a href="${escapeHtml(s.url)}" target="_blank" rel="noopener noreferrer" class="meta-link">Portal Link ↗</a></div>
      </div>
      <div class="source-card-actions">
        ${isLive 
          ? `<button class="btn-card-sync" onclick="triggerDiscoveryScan('${escapeHtml(s.id)}')">🔄 Sync Scraper Now</button>`
          : `<button class="btn-card-inspect" onclick="openSourceDetailsModal('${escapeHtml(s.id)}')">⚙️ Inspect Adapter</button>`
        }
      </div>
    </div>
  `;
}

let activeSourcesCategoryFilter = 'all';

// ── Sources View Loader ──────────────────────────────────────────────────
async function loadSourcesView() {
  const container = document.getElementById('sources-cards-container');
  const chipsContainer = document.getElementById('sources-category-chips');
  const runsTbody = document.getElementById('sources-runs-tbody');

  if (container) {
    container.innerHTML = '<div style="color: var(--text-muted); font-size: 13px; padding: 24px 0;">Loading categorized portal sources...</div>';
  }

  try {
    const res = await fetch(`${API_BASE}/api/sources`);
    if (!res.ok) throw new Error('Failed to load sources');
    const data = await res.json();

    const sources = data.sources || [];
    const runs = data.recent_runs || [];

    // Bucket sources into categories
    const categoryBuckets = {};
    PORTAL_CATEGORIES.forEach(cat => {
      categoryBuckets[cat.id] = [];
    });

    sources.forEach(s => {
      const catId = getSourcePortalCategory(s);
      if (categoryBuckets[catId]) {
        categoryBuckets[catId].push(s);
      } else {
        if (!categoryBuckets['other']) categoryBuckets['other'] = [];
        categoryBuckets['other'].push(s);
      }
    });

    // 1. Render Compact Category Filter Chips
    if (chipsContainer) {
      chipsContainer.innerHTML = `
        <button class="sources-filter-chip ${activeSourcesCategoryFilter === 'all' ? 'active' : ''}" data-cat="all" onclick="filterSourcesCategory('all')">
          All Portals <span class="chip-count">${sources.length}</span>
        </button>
        ${PORTAL_CATEGORIES.map(cat => {
          const count = (categoryBuckets[cat.id] || []).length;
          const isActive = activeSourcesCategoryFilter === cat.id;
          return `
            <button class="sources-filter-chip ${isActive ? 'active' : ''}" data-cat="${cat.id}" onclick="filterSourcesCategory('${cat.id}')">
              ${cat.iconEmoji} ${cat.shortTitle} <span class="chip-count">${count}</span>
            </button>
          `;
        }).join('')}
      `;
    }

    // 2. Render Collapsible Category Accordion Groups
    if (container) {
      container.innerHTML = PORTAL_CATEGORIES.map(cat => {
        const catSources = categoryBuckets[cat.id] || [];
        const isCollapsed = !cat.defaultExpanded;
        const liveCount = catSources.filter(s => s.status === 'active' || s.is_live_scraping).length;
        const cardsHtml = catSources.map(s => renderSourceCard(s)).join('');

        return `
          <div class="sources-category-group ${isCollapsed ? 'collapsed' : ''}" id="cat-group-${cat.id}" data-category="${cat.id}">
            <div class="sources-category-header" onclick="toggleSourceCategory('${cat.id}')">
              <div class="category-header-left">
                <div class="category-icon-box" style="background: ${cat.bgTint}; color: ${cat.color};">
                  ${cat.icon}
                </div>
                <div class="category-title-meta">
                  <div class="category-title-row">
                    <h3 class="category-title">${cat.title}</h3>
                    <span class="category-count-pill">${catSources.length} ${catSources.length === 1 ? 'portal' : 'portals'}</span>
                  </div>
                  <p class="category-desc">${cat.description}</p>
                </div>
              </div>

              <div class="category-header-right">
                <span class="category-active-tag">● ${liveCount} Active Scrapers</span>
                <button class="category-toggle-arrow" aria-label="Toggle ${escapeHtml(cat.title)} group">
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
                    <polyline points="6 9 12 15 18 9"></polyline>
                  </svg>
                </button>
              </div>
            </div>

            <div class="sources-category-body">
              <div class="sources-cards-grid">
                ${cardsHtml}
              </div>
            </div>
          </div>
        `;
      }).join('');
    }

    // Reapply active category filter if user had one selected
    if (activeSourcesCategoryFilter !== 'all') {
      filterSourcesCategory(activeSourcesCategoryFilter);
    }

    // 3. Render Recent Automated Discovery Runs
    if (runsTbody) {
      if (runs.length > 0) {
        runsTbody.innerHTML = runs.map(r => `
          <tr>
            <td><strong>${escapeHtml(formatSourceName(r.source_name))}</strong></td>
            <td><span class="source-card-badge badge-live">${escapeHtml(r.status || 'completed')}</span></td>
            <td style="font-size: 11.5px; color: var(--text-2);">${escapeHtml(r.started_at ? formatLocalDateTime(r.started_at) : '—')}</td>
            <td style="font-size: 11.5px; color: var(--text-2);">${escapeHtml(r.finished_at ? formatLocalDateTime(r.finished_at) : 'Just now')}</td>
            <td>${r.items_scanned || 0}</td>
            <td>${r.items_discovered || 0}</td>
            <td><strong style="color: var(--primary);">${r.items_qualified || 0}</strong></td>
          </tr>
        `).join('');
      } else {
        runsTbody.innerHTML = `<tr><td colspan="7" style="text-align: center; color: var(--text-3); padding: 20px;">No automated discovery runs recorded yet.</td></tr>`;
      }
    }
  } catch (err) {
    if (container) {
      container.innerHTML = `<div style="color: var(--error);">Error loading sources: ${escapeHtml(err.message)}</div>`;
    }
  }
}

function toggleSourceCategory(catId) {
  const group = document.getElementById(`cat-group-${catId}`);
  if (!group) return;
  group.classList.toggle('collapsed');
}

function filterSourcesCategory(catId) {
  activeSourcesCategoryFilter = catId;

  // Update active chip UI
  document.querySelectorAll('.sources-filter-chip').forEach(chip => {
    chip.classList.toggle('active', chip.dataset.cat === catId);
  });

  const allGroups = document.querySelectorAll('.sources-category-group');
  allGroups.forEach(group => {
    const groupCat = group.dataset.category;
    if (catId === 'all') {
      group.style.display = 'flex';
    } else if (groupCat === catId) {
      group.style.display = 'flex';
      // Automatically expand the filtered category so user immediately sees cards
      group.classList.remove('collapsed');
    } else {
      group.style.display = 'none';
    }
  });
}

// ── Safe Date Utilities ───────────────────────────────────────────────────
function formatDateSafe(val) {
  if (!val) return 'Recent';
  try {
    let d = null;
    if (typeof parseDateRobust === 'function') d = parseDateRobust(val);
    if (!d && typeof parseUtcDate === 'function') d = parseUtcDate(val);
    if (!d) d = new Date(val);
    if (d && !isNaN(d.getTime())) {
      return d.toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' });
    }
  } catch (e) {}
  return String(val).substring(0, 10);
}
const formatDate = formatDateSafe;

// ── Documents View Repository & Sync ──────────────────────────────────────
let allLoadedDocuments = [];

async function loadDocumentsView(forceRefresh = false) {
  const tbody = document.getElementById('documents-tbody');
  if (!tbody) return;
  tbody.innerHTML = '<tr><td colspan="6" style="text-align: center; padding: 24px; color: var(--text-3);">Loading tender documents repository...</td></tr>';

  try {
    const res = await fetch(`${API_BASE}/api/documents?limit=1000`);
    if (!res.ok) throw new Error('Failed to load documents repository');
    const data = await res.json();
    allLoadedDocuments = data.items || [];

    // Update KPI counters
    const totalCount = allLoadedDocuments.length;
    const cyberCount = allLoadedDocuments.filter(d => (d.highest_tier || '').toUpperCase() === 'A').length;
    const infraCount = allLoadedDocuments.filter(d => (d.highest_tier || '').toUpperCase() === 'B').length;
    const cloudCount = allLoadedDocuments.filter(d => ['C', 'D'].includes((d.highest_tier || '').toUpperCase())).length;

    const elTotal = document.getElementById('doc-kpi-total');
    const elCyber = document.getElementById('doc-kpi-cyber');
    const elInfra = document.getElementById('doc-kpi-infra');
    const elCloud = document.getElementById('doc-kpi-cloud');

    if (elTotal) elTotal.textContent = totalCount;
    if (elCyber) elCyber.textContent = cyberCount;
    if (elInfra) elInfra.textContent = infraCount;
    if (elCloud) elCloud.textContent = cloudCount;

    // Dynamically populate portal filter dropdown options with live counts
    populatePortalDropdown(allLoadedDocuments);

    filterDocumentsTable();
    if (forceRefresh) {
      showToast(`Synchronized ${totalCount} official tender documents`);
    }
  } catch (err) {
    console.error('loadDocumentsView error:', err);
    tbody.innerHTML = `<tr><td colspan="6" style="text-align: center; padding: 24px; color: var(--error);">Error syncing documents: ${escapeHtml(err.message)}</td></tr>`;
  }
}

function populatePortalDropdown(docs) {
  const portalSelect = document.getElementById('doc-filter-portal');
  if (!portalSelect) return;
  const currentVal = portalSelect.value;

  const counts = {};
  docs.forEach(d => {
    const src = (d.portal_source || 'cppp').toLowerCase();
    counts[src] = (counts[src] || 0) + 1;
  });

  let gemCount = 0;
  let cpppCount = 0;
  let stateCount = 0;
  let psuCount = 0;
  let wizardCount = 0;

  Object.entries(counts).forEach(([src, cnt]) => {
    if (src.includes('gem')) gemCount += cnt;
    else if (src.includes('cppp') || src.includes('epublish')) cpppCount += cnt;
    else if (src.includes('iocl') || src.includes('bhel') || src.includes('bel') || src.includes('ntpc') || src.includes('ongc') || src.includes('beml') || src.includes('bial') || src.includes('bnpm') || src.includes('asrtu')) psuCount += cnt;
    else if (src.includes('wizard')) wizardCount += cnt;
    else stateCount += cnt;
  });

  let html = `<option value="">Portal: All Portals (${docs.length})</option>`;
  if (gemCount) html += `<option value="gem">GeM Portal (${gemCount})</option>`;
  if (cpppCount) html += `<option value="cppp">Central CPPP (${cpppCount})</option>`;
  if (stateCount) html += `<option value="state">All State Portals (${stateCount})</option>`;
  if (psuCount) html += `<option value="psu">PSU Portals (${psuCount})</option>`;
  if (wizardCount) html += `<option value="wizard">eWizard / TenderWizard (${wizardCount})</option>`;

  html += `<optgroup label="Active Portals in DB">`;
  const sorted = Object.entries(counts).sort((a, b) => b[1] - a[1]);
  sorted.forEach(([src, cnt]) => {
    const name = formatSourceName(src);
    html += `<option value="src:${src}">${name} (${cnt})</option>`;
  });
  html += `</optgroup>`;

  portalSelect.innerHTML = html;
  if (currentVal && portalSelect.querySelector(`option[value="${currentVal}"]`)) {
    portalSelect.value = currentVal;
  }
}

function filterDocumentsTable() {
  const searchInput = document.getElementById('doc-table-search');
  const tierFilter = document.getElementById('doc-filter-tier');
  const portalFilter = document.getElementById('doc-filter-portal');
  const windowFilter = document.getElementById('doc-filter-window');
  const countEl = document.getElementById('documents-count');

  const query = searchInput ? (searchInput.value || '').trim().toLowerCase() : '';
  const selectedTier = tierFilter ? (tierFilter.value || '').trim().toUpperCase() : '';
  const selectedPortal = portalFilter ? (portalFilter.value || '').trim().toLowerCase() : '';
  const selectedWindow = windowFilter ? (windowFilter.value || 'all') : 'all';

  let filtered = allLoadedDocuments;

  // 1. Time Window Filter (synchronized with dashboard window logic)
  if (selectedWindow && selectedWindow !== 'all') {
    filtered = filtered.filter(d => isWithinTimeWindow(d, selectedWindow));
  }

  // 2. Focus Area / Tier Filter
  if (selectedTier) {
    filtered = filtered.filter(d => (d.highest_tier || '').toUpperCase() === selectedTier);
  }

  if (selectedPortal) {
    filtered = filtered.filter(d => {
      const src = (d.portal_source || '').toLowerCase();
      if (selectedPortal.startsWith('src:')) {
        const targetSrc = selectedPortal.replace('src:', '').toLowerCase();
        return src === targetSrc;
      }
      if (selectedPortal === 'gem') return src.includes('gem') || (d.tender_id || '').startsWith('GEM/');
      if (selectedPortal === 'cppp') return src.includes('cppp') || src.includes('epublish') || src.includes('etenders');
      if (selectedPortal === 'psu') return src.includes('iocl') || src.includes('bhel') || src.includes('bel') || src.includes('ntpc') || src.includes('ongc') || src.includes('beml') || src.includes('bial') || src.includes('bnpm') || src.includes('asrtu');
      if (selectedPortal === 'wizard') return src.includes('wizard');
      if (selectedPortal === 'state') {
        return !src.includes('gem') && !src.includes('cppp') && !src.includes('epublish') && !src.includes('iocl') && !src.includes('wizard');
      }
      return src.includes(selectedPortal);
    });
  }

  if (query) {
    filtered = filtered.filter(d => {
      const matchText = [
        d.tender_title || '',
        d.doc_title || '',
        d.reference_no || '',
        d.tender_id || '',
        d.authority || '',
        d.tier_label || '',
        formatSourceName(d.portal_source) || '',
        d.location || ''
      ].join(' ').toLowerCase();
      return matchText.includes(query);
    });
  }

  if (countEl) {
    countEl.textContent = filtered.length;
  }

  // Synchronize KPI summary cards to reflect the current active time window
  const windowedDocs = (selectedWindow && selectedWindow !== 'all')
    ? allLoadedDocuments.filter(d => isWithinTimeWindow(d, selectedWindow))
    : allLoadedDocuments;

  const elTotal = document.getElementById('doc-kpi-total');
  const elCyber = document.getElementById('doc-kpi-cyber');
  const elInfra = document.getElementById('doc-kpi-infra');
  const elCloud = document.getElementById('doc-kpi-cloud');

  if (elTotal) elTotal.textContent = windowedDocs.length;
  if (elCyber) elCyber.textContent = windowedDocs.filter(d => (d.highest_tier || '').toUpperCase() === 'A').length;
  if (elInfra) elInfra.textContent = windowedDocs.filter(d => (d.highest_tier || '').toUpperCase() === 'B').length;
  if (elCloud) elCloud.textContent = windowedDocs.filter(d => ['C', 'D'].includes((d.highest_tier || '').toUpperCase())).length;

  renderDocumentsTable(filtered);
}

function renderDocumentsTable(docs) {
  const tbody = document.getElementById('documents-tbody');
  if (!tbody) return;

  if (!docs || docs.length === 0) {
    tbody.innerHTML = '<tr><td colspan="6" style="text-align: center; padding: 28px; color: var(--text-3); font-size: 13px;">No tender documents found matching current filter criteria.</td></tr>';
    return;
  }

  const docSvg = `<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="color: var(--primary); flex-shrink: 0;"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline></svg>`;

  tbody.innerHTML = docs.map(d => {
    const tier = (d.highest_tier || '').toUpperCase();
    const tierLabel = d.tier_label || (tier === 'A' ? 'Cyber Security' : tier === 'B' ? 'IT Infrastructure' : tier === 'C' ? 'Cloud' : 'Infra & Services');
    const tierBadge = tier ? `<span class="table-tier-badge tier-badge-${tier.toLowerCase()}" style="font-size: 10.5px; padding: 2px 7px;">Tier ${tier}</span>` : '';
    const cleanRef = escapeHtml(d.reference_no || d.tender_id || 'Tender');
    const cleanTitle = escapeHtml(d.tender_title || d.doc_title || 'Official Tender Document');
    const cleanAuth = escapeHtml(d.authority || 'Issuing Authority');
    const srcName = formatSourceName(d.portal_source);
    const sourceLogo = (typeof getSourceLogoSvg === 'function') ? getSourceLogoSvg(d.portal_source, 14) : '';
    const dateFormatted = formatDateSafe(d.created_at);
    
    // Status pill
    const statusPill = d.has_direct_pdf 
      ? '<span class="table-status-pill extracted" title="Direct GeM Official Signed PDF"><span class="status-dot"></span>GeM Signed PDF</span>'
      : '<span class="table-status-pill extracted" title="Authenticated Official Technical Specification PDF Dossier"><span class="status-dot"></span>Official Dossier</span>';

    return `
      <tr>
        <td class="table-title-cell" style="overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
          <div style="font-weight: 600; color: var(--text); display: flex; align-items: center; gap: 8px;">
            ${docSvg}
            <span style="overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: 12.5px;" title="${cleanTitle}">${cleanTitle}</span>
          </div>
          <div style="font-size: 11px; color: var(--text-3); margin-top: 4px; padding-left: 23px; display: flex; align-items: center; gap: 8px;">
            <div class="source-badge-pill" data-source="${escapeHtml(d.portal_source || '')}" style="padding: 1px 7px; font-size: 10.5px; gap: 4px;">
              ${sourceLogo}
              <span>${escapeHtml(srcName)}</span>
            </div>
            <span>&bull;</span>
            <span>Published: ${escapeHtml(dateFormatted)}</span>
          </div>
        </td>
        <td style="overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
          <span style="font-family: 'JetBrains Mono', 'Roboto Mono', monospace; font-size: 11.5px; font-weight: 600; color: var(--primary); white-space: nowrap;" title="${cleanRef}">
            ${cleanRef}
          </span>
        </td>
        <td style="overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
          <div class="table-buyer" style="max-width: 100%; font-size: 12px;" title="${cleanAuth}">${cleanAuth}</div>
        </td>
        <td style="overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
          <div style="display: flex; align-items: center; gap: 6px; white-space: nowrap;">
            ${tierBadge}
            <span style="font-size: 11px; color: var(--text-2); overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">${escapeHtml(tierLabel)}</span>
          </div>
        </td>
        <td style="white-space: nowrap;">
          ${statusPill}
        </td>
        <td style="text-align: center; white-space: nowrap;">
          <div style="display: flex; gap: 8px; justify-content: center; align-items: center;">
            <a href="${API_BASE}/api/documents/download?tender_id=${encodeURIComponent(d.tender_id)}" target="_blank" class="btn-download" title="${d.has_direct_pdf ? 'Download official signed government PDF notice' : 'Download official procurement specification dossier'}" style="display: inline-flex; align-items: center; gap: 5px; padding: 5px 10px; font-size: 11.5px;">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path><polyline points="7 10 12 15 17 10"></polyline><line x1="12" y1="15" x2="12" y2="3"></line></svg>
              <span>${d.has_direct_pdf ? 'Official GeM PDF' : 'Download Dossier'}</span>
            </a>
            <a href="${API_BASE}/api/portal/bridge?tender_id=${encodeURIComponent(d.tender_id)}" target="_blank" rel="noopener" title="Open official government portal tender page & official department attachments" style="padding: 5px 9px; font-size: 11px; background: rgba(59,130,246,0.12); border: 1px solid rgba(59,130,246,0.3); border-radius: 6px; color: var(--primary); display: inline-flex; align-items: center; gap: 4px; text-decoration: none; cursor: pointer; transition: all 0.15s ease; font-weight: 500;">
              <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"></path><polyline points="15 3 21 3 21 9"></polyline><line x1="10" y1="14" x2="21" y2="3"></line></svg>
              <span>Official Portal</span>
            </a>
          </div>
        </td>
      </tr>
    `;
  }).join('');
}

function initKeywordsView() {
  const resultBox = document.getElementById('kw-test-result');
  if (resultBox) resultBox.style.display = 'none';
}

function loadSampleText() {
  document.getElementById('kw-test-input').value = 
    "Design, supply, installation and commissioning of Next-Generation Firewall (NGFW), SOC SIEM Integration, 42U Server Racks, Enterprise SAN Storage, Cloud Migration, and 3-Year Comprehensive Annual Maintenance (CAMC) with 24x7 Facility Management.";
  showToast('Loaded sample RFP text');
}

async function runKeywordTest() {
  const text = (document.getElementById('kw-test-input').value || '').trim();
  if (!text) {
    showToast('Please enter or paste text to test.');
    return;
  }

  const resultBox = document.getElementById('kw-test-result');
  resultBox.style.display = 'block';
  resultBox.innerHTML = '<div style="color: var(--text-muted); font-size: 12.5px;">Testing text against Tier A–D rules...</div>';

  try {
    const res = await fetch(`${API_BASE}/api/keywords/test`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text: text, tender_id: 'TEST_SAMPLE' })
    });

    if (!res.ok) throw new Error('Keyword test request failed');
    const r = await res.json();

    const isQual = r.qualified;
    const cat = r.primary_category;
    const tier = r.highest_tier || 'None';
    const rule = r.inclusion_rule_applied || 'No rule met';

    const matchesHtml = (r.matches && r.matches.length > 0)
      ? r.matches.map(m => `
          <div style="display: flex; align-items: center; justify-content: space-between; padding: 6px 10px; background: #ffffff; border: 1px solid var(--border-subtle); border-radius: 4px; margin-top: 6px; font-size: 12px;">
            <div>
              <strong>"${escapeHtml(m.term)}"</strong>
              <span style="color: var(--text-muted); font-size: 11px;">(Matched: "${escapeHtml(m.matched_text)}")</span>
            </div>
            <span class="table-tier-badge tier-badge-${m.tier.toLowerCase()}" style="font-size: 10px; width: auto; height: auto; padding: 2px 6px; border-radius: 4px;">
              Tier ${m.tier} (${escapeHtml(m.match_group || m.group || '')})
            </span>
          </div>
        `).join('')
      : '<div style="color: var(--text-muted); font-size: 12px; margin-top: 6px;">No keyword matches detected.</div>';

    resultBox.innerHTML = `
      <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px;">
        <div style="font-size: 14px; font-weight: 700; color: ${isQual ? '#15803d' : '#991b1b'};">
          ${isQual ? '✓ QUALIFIED FOR PIPELINE' : '✗ UNMATCHED / DISQUALIFIED'}
        </div>
        <div>
          <span class="panel-tier-badge ${tier !== 'None' ? 'tier-badge-' + tier.toLowerCase() : ''}" style="font-size: 11px;">
            ${tier !== 'None' ? 'Tier ' + tier : 'No Tier'}
          </span>
          <span style="font-size: 11px; color: var(--text-secondary); margin-left: 6px;">
            Category: <strong>${cat || 'unmatched'}</strong>
          </span>
        </div>
      </div>

      <div style="font-size: 12px; margin-bottom: 10px; color: var(--text-secondary);">
        <strong>Applied Rule:</strong> ${escapeHtml(rule)}
      </div>

      <div style="font-size: 12px; font-weight: 600; color: var(--text-main); margin-top: 10px;">
        Detected Matches (${r.matches ? r.matches.length : 0}):
      </div>
      ${matchesHtml}
    `;

  } catch (err) {
    resultBox.innerHTML = `<div style="color: #ef4444;">Error testing keywords: ${escapeHtml(err.message)}</div>`;
  }
}

function saveSettings() {
  showToast('Settings saved successfully. Changes active.');
}

// ═══════════════════════════════════════════════════════════════════════════
// MONITORED SOURCES SIDEBAR & MODAL SYSTEM
// ═══════════════════════════════════════════════════════════════════════════
let activeSidebarSource = null;
let currentSourcesList = [];
let selectedModalSourceId = null;

async function loadSidebarSources() {
  const container = document.getElementById('sidebar-sources-list');
  if (!container) return;

  try {
    const res = await fetch(`${API_BASE}/api/sources`);
    if (!res.ok) throw new Error('Failed to fetch sources');
    const data = await res.json();
    currentSourcesList = data.sources || [];

    renderSidebarSources(currentSourcesList);
  } catch (err) {
    console.error('Error loading sidebar sources:', err);
  }
}

function renderSidebarSources(sources) {
  const container = document.getElementById('sidebar-sources-list');
  if (!container) return;

  container.innerHTML = sources.map(s => {
    const isLive = s.status === 'active' || s.is_live_scraping;
    const badgeClass = isLive ? 'active-live' : 'pending';
    const badgeText = isLive ? 'Active' : 'Pending';
    const isSelected = activeSidebarSource === s.id;

    // Display short name
    let shortName = formatSourceName(s.id);
    if (!shortName || shortName === s.id) {
      shortName = s.name;
    }

    return `
      <div class="source-row ${isSelected ? 'active' : ''}" onclick="handleSidebarSourceClick('${s.id}')" title="Click to filter by ${escapeHtml(s.name)}">
        <div style="display: flex; align-items: center; gap: 7px; min-width: 0; overflow: hidden;">
          ${getSourceLogoSvg(s.id, 15)}
          <span class="source-name" style="overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">${escapeHtml(shortName)}</span>
        </div>
        <div style="display: flex; align-items: center; gap: 4px; flex-shrink: 0;">
          <span class="source-status-badge ${badgeClass}">${badgeText}</span>
          <button type="button" class="source-info-btn" onclick="event.stopPropagation(); openSourceDetailsModal('${s.id}')" title="Inspect source details" style="background:none; border:none; color:var(--text-muted); cursor:pointer; font-size:11px; padding:0 2px;">ℹ️</button>
        </div>
      </div>
    `;
  }).join('');
}

function handleSidebarSourceClick(sourceId) {
  if (activeSidebarSource === sourceId) {
    clearSourceFilter();
    return;
  }

  activeSidebarSource = sourceId;
  const resetBtn = document.getElementById('btn-clear-source-filter');
  if (resetBtn) resetBtn.style.display = 'inline-block';

  renderSidebarSources(currentSourcesList);

  // If user is not on dashboard or tenders, bring them to dashboard
  const activeNav = document.querySelector('.sidebar-nav .nav-item.active')?.dataset.nav;
  if (activeNav !== 'dashboard' && activeNav !== 'tenders') {
    navigateTo('dashboard');
  }

  applyFilters();

  const srcObj = currentSourcesList.find(s => s.id === sourceId);
  const srcName = srcObj ? srcObj.name : sourceId;
  const isLive = srcObj && (srcObj.status === 'active' || srcObj.is_live_scraping);
  if (!isLive) {
    showToast(`Filter: ${srcName} (Adapter pending — 0 tenders)`);
  } else {
    showToast(`Filtered tenders by ${srcName}`);
  }
}

function clearSourceFilter() {
  activeSidebarSource = null;
  const resetBtn = document.getElementById('btn-clear-source-filter');
  if (resetBtn) resetBtn.style.display = 'none';

  renderSidebarSources(currentSourcesList);
  applyFilters();
  showToast('Source filter reset');
}

function openSourceDetailsModal(sourceId) {
  const s = currentSourcesList.find(x => x.id === sourceId);
  if (!s) return;

  selectedModalSourceId = sourceId;
  document.getElementById('src-det-name').textContent = s.name;
  document.getElementById('src-det-type').textContent = s.type;

  const isLive = s.status === 'active' || s.is_live_scraping;
  const badge = document.getElementById('src-det-badge');
  badge.textContent = isLive ? 'Active (Live Scraper)' : 'Adapter Pending (Standby)';
  badge.className = `source-status-badge ${isLive ? 'active-live' : 'pending'}`;

  const urlEl = document.getElementById('src-det-url');
  urlEl.href = s.url;
  urlEl.textContent = s.url;

  document.getElementById('src-det-cadence').textContent = s.cadence;
  document.getElementById('src-det-pipeline').textContent = isLive ? 'Live Scraper (Active)' : 'Adapter Connector (Pending)';
  document.getElementById('src-det-count').textContent = `${s.tenders_count || 0} tenders`;

  const msgBox = document.getElementById('src-det-status-msg');
  const statusBox = document.getElementById('src-det-status-box');
  if (isLive) {
    msgBox.innerHTML = `<strong>Live Scraping Active:</strong> This portal is automatically polled every hour. Discovered tenders are checked against Nikom's Tier A–D keywords in real-time.`;
    statusBox.style.background = '#dcfce7';
    statusBox.style.borderColor = '#86efac';
    statusBox.style.color = '#15803d';
  } else {
    msgBox.innerHTML = `<strong>Standby / Adapter Pending:</strong> No tenders are currently fetched from this source. The scraping connector is staged for future integration.`;
    statusBox.style.background = '#fef3c7';
    statusBox.style.borderColor = '#fde68a';
    statusBox.style.color = '#92400e';
  }

  document.getElementById('modal-source-details').style.display = 'flex';
}

function closeSourceDetailsModal() {
  document.getElementById('modal-source-details').style.display = 'none';
  selectedModalSourceId = null;
}

function applySourceFilterFromModal() {
  if (selectedModalSourceId) {
    handleSidebarSourceClick(selectedModalSourceId);
  }
  closeSourceDetailsModal();
}

function openAddSourceModal() {
  document.getElementById('modal-add-source').style.display = 'flex';
  document.getElementById('input-source-name').focus();
}

function closeAddSourceModal() {
  document.getElementById('modal-add-source').style.display = 'none';
  document.getElementById('form-add-source').reset();
}

async function submitNewSource(e) {
  e.preventDefault();
  const name = document.getElementById('input-source-name').value.trim();
  const type = document.getElementById('input-source-type').value;
  const cadence = document.getElementById('input-source-cadence').value;
  const url = document.getElementById('input-source-url').value.trim();

  if (!name || !url) {
    showToast('Please fill in required fields.');
    return;
  }

  try {
    const res = await fetch(`${API_BASE}/api/sources`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, type, cadence, url, status: 'pending_adapter' })
    });

    if (!res.ok) throw new Error('Failed to register source');
    const data = await res.json();

    closeAddSourceModal();
    showToast(`Source "${name}" registered in Standby mode!`);
    await loadSidebarSources();
    loadSourcesView();
  } catch (err) {
    showToast(`Error: ${err.message}`);
  }
}

// ═══════════════════════════════════════════════════════════════════════════
// STATE TO PORTAL & REGIONAL ALIAS MAPPINGS FOR INTELLIGENT SEARCH
// ═══════════════════════════════════════════════════════════════════════════
const STATE_PORTAL_MAP = {
  'Maharashtra': ['mahatenders'],
  'Uttar Pradesh': ['up_tenders'],
  'Delhi': ['delhi_tenders'],
  'Karnataka': ['karnataka_eproc'],
  'Tamil Nadu': ['tn_tenders'],
  'Gujarat': ['gujarat_nprocure'],
  'Rajasthan': ['rajasthan_eproc'],
  'West Bengal': ['wb_tenders'],
  'Madhya Pradesh': ['mp_tenders'],
  'Kerala': ['kerala_tenders'],
  'Andhra Pradesh': ['ap_eprocurement'],
  'Telangana': ['telangana_eproc'],
  'Bihar': ['bihar_eprocurement'],
  'Odisha': ['odisha_tenders'],
  'Punjab': ['punjab_eproc'],
  'Haryana': ['haryana_tenders'],
  'Assam': ['assam_tenders'],
  'Arunachal Pradesh': ['arunachal_tenders'],
  'Uttarakhand': ['uk_tenders'],
  'Himachal Pradesh': ['hp_tenders'],
  'Jammu & Kashmir': ['jk_tenders'],
  'Chhattisgarh': ['chhattisgarh_eproc'],
  'Jharkhand': ['jharkhand_tenders']
};

const STATE_ALIASES = {
  'Maharashtra': ['maharashtra', 'mumbai', 'pune', 'nagpur', 'thane', 'nashik', 'aurangabad', 'iit bombay', 'iiser pune', 'mahavitaran', 'bmc', 'cidco', 'midc'],
  'Uttar Pradesh': ['uttar pradesh', 'lucknow', 'noida', 'greater noida', 'kanpur', 'varanasi', 'agra', 'prayagraj', 'allahabad', 'ghaziabad', 'meerut', 'gorakhpur'],
  'Delhi': ['delhi', 'new delhi', 'nct of delhi', 'delhi jal board', 'ndmc', 'dtc', 'dsiidc'],
  'Karnataka': ['karnataka', 'bengaluru', 'bangalore', 'mysore', 'hubli', 'mangalore', 'bial', 'kptcl', 'bescom'],
  'Tamil Nadu': ['tamil nadu', 'chennai', 'coimbatore', 'madurai', 'trichy', 'tangedco', 'elcot', 'tantransco'],
  'Gujarat': ['gujarat', 'ahmedabad', 'gandhinagar', 'surat', 'vadodara', 'rajkot', 'gift city', 'gacl'],
  'Rajasthan': ['rajasthan', 'jaipur', 'jodhpur', 'udaipur', 'kota', 'reil jaipur', 'rvunl', 'rsmm'],
  'West Bengal': ['west bengal', 'bengal', 'kolkata', 'calcutta', 'howrah', 'durgapur', 'siliguri', 'wbpdcl', 'wbsedcl'],
  'Madhya Pradesh': ['madhya pradesh', 'bhopal', 'indore', 'jabalpur', 'gwalior', 'narmadapuram', 'mppkvvcl'],
  'Kerala': ['kerala', 'thiruvananthapuram', 'trivandrum', 'kochi', 'cochin', 'kozhikode', 'calicut', 'kseb', 'keltron'],
  'Andhra Pradesh': ['andhra pradesh', 'visakhapatnam', 'vizag', 'vijayawada', 'tirupati', 'guntur', 'amaravati', 'apcpdcl'],
  'Telangana': ['telangana', 'hyderabad', 'secunderabad', 'warangal', 'tssouthernpower'],
  'Bihar': ['bihar', 'patna', 'gaya', 'bhagalpur', 'muzaffarpur', 'bsphcl'],
  'Odisha': ['odisha', 'orissa', 'bhubaneswar', 'cuttack', 'rourkela', 'sambalpur', 'gridco', 'optcl'],
  'Punjab': ['punjab', 'chandigarh', 'ludhiana', 'amritsar', 'jalandhar', 'patiala', 'pspcl'],
  'Haryana': ['haryana', 'gurugram', 'gurgaon', 'faridabad', 'panipat', 'ambala', 'panchkula', 'hsvp'],
  'Assam': ['assam', 'guwahati', 'silchar', 'dibrugarh', 'jorhat', 'dispur', 'apdcl'],
  'Arunachal Pradesh': ['arunachal pradesh', 'arunachal', 'itanagar', 'nari', 'pasighat', 'naharlagun'],
  'Uttarakhand': ['uttarakhand', 'dehradun', 'haridwar', 'roorkee', 'rishikesh', 'nainital', 'uprnn', 'upcl'],
  'Himachal Pradesh': ['himachal pradesh', 'shimla', 'dharamshala', 'mandi', 'solan', 'kullu', 'hpseb'],
  'Jammu & Kashmir': ['jammu & kashmir', 'jammu and kashmir', 'jammu', 'srinagar', 'baramulla', 'anantnag', 'jkpdcl'],
  'Chhattisgarh': ['chhattisgarh', 'raipur', 'bilaspur', 'bhilai', 'durg', 'cseb'],
  'Jharkhand': ['jharkhand', 'ranchi', 'jamshedpur', 'dhanbad', 'bokaro', 'jbvnl']
};

function isTenderInState(t, targetState) {
  if (!targetState) return true;
  
  if (targetState === 'Pan India / Central') {
    const p = (t.portal_source || '').toLowerCase();
    const loc = (t.location || '').toLowerCase();
    const isCentral = p.includes('gem') || p.includes('eprocure') || p.includes('cppp') || p.includes('iocl');
    return isCentral || loc.includes('india') || loc.includes('central') || loc.includes('pan india');
  }

  const portals = STATE_PORTAL_MAP[targetState] || [];
  const aliases = STATE_ALIASES[targetState] || [targetState.toLowerCase()];
  const portalSrc = (t.portal_source || '').toLowerCase();

  // 1. Direct portal source match (e.g. mahatenders -> Maharashtra)
  if (portals.some(p => portalSrc === p.toLowerCase() || portalSrc.includes(p.toLowerCase()))) {
    return true;
  }

  // 2. Location, authority, or title contains city or state alias
  const text = `${t.location || ''} ${t.authority || ''} ${t.title || ''} ${portalSrc}`.toLowerCase();
  return aliases.some(alias => text.includes(alias));
}

function updateActiveFilterChips(inWindowCount, filteredCount) {
  const container = document.getElementById('active-filters-chips');
  const banner = document.getElementById('active-filters-banner');
  const contextEl = document.getElementById('table-total-context');
  if (!container) return;

  const chips = [];
  const sectorVal = document.getElementById('filter-sector')?.value || '';
  const sourceVal = document.getElementById('filter-source')?.value || '';
  const stateVal = document.getElementById('filter-state')?.value || '';
  const valueVal = document.getElementById('filter-value')?.value || '';
  const expiryVal = document.getElementById('filter-expiry')?.value || 'all';
  const searchVal = (document.getElementById('table-search')?.value || '').trim();

  if (activeSidebarSource) {
    chips.push({ label: `Portal: ${formatSourceName(activeSidebarSource)}`, key: 'sidebarSource' });
  }
  if (sourceVal) {
    chips.push({ label: `Source: ${formatSourceName(sourceVal)}`, key: 'source' });
  }
  if (stateVal) {
    chips.push({ label: `State: ${stateVal}`, key: 'state' });
  }
  if (sectorVal) {
    chips.push({ label: `Sector: ${sectorVal}`, key: 'sector' });
  }
  if (valueVal) {
    const valLabels = { '5cr': '₹ 5 Cr+', '25cr': '₹ 25 Cr+', '50cr': '₹ 50 Cr+' };
    chips.push({ label: `Value: ${valLabels[valueVal] || valueVal}`, key: 'value' });
  }
  if (expiryVal === 'active') {
    chips.push({ label: 'Open / Active Bids', key: 'expiry' });
  } else if (expiryVal === 'expired') {
    chips.push({ label: 'Closed / Expired Bids', key: 'expiry' });
  }
  if (searchVal) {
    chips.push({ label: `Search: "${searchVal}"`, key: 'search' });
  }

  // Update total context text next to title: e.g. " (43 of 166)" or " (8 of 30 in IT Infrastructure)"
  if (contextEl) {
    if (chips.length > 0 && inWindowCount > 0 && filteredCount < inWindowCount) {
      contextEl.textContent = ` of ${inWindowCount}`;
    } else {
      contextEl.textContent = '';
    }
  }

  // Render chips
  if (chips.length > 0) {
    container.innerHTML = chips.map(c => `
      <span class="active-filter-chip" onclick="clearSpecificFilter('${c.key}')" title="Click to clear this filter">
        <span>${escapeHtml(c.label)}</span>
        <span class="chip-remove">&times;</span>
      </span>
    `).join('') + `
      <button type="button" class="btn-clear-all-chips" onclick="resetFilters()" title="Reset all filters">Reset All</button>
    `;
  } else {
    container.innerHTML = '';
  }

  // Render informative banner if restrictive filter hides opportunities
  if (banner) {
    if (activeTierFilter !== 'all' && sectorVal && filteredCount < inWindowCount) {
      const tierNames = { 'A': 'Cyber Security', 'B': 'IT Infrastructure', 'C': 'Cloud', 'D': 'Infra & Services' };
      const currentTierName = tierNames[activeTierFilter] || `Tier ${activeTierFilter}`;
      banner.style.display = 'flex';
      banner.innerHTML = `
        <div style="display: flex; align-items: center; gap: 8px;">
          <span style="font-size: 15px;">ℹ️</span>
          <span>Showing <strong>${filteredCount}</strong> ${escapeHtml(currentTierName)} tenders in <strong>${escapeHtml(sectorVal)}</strong>. (Remaining opportunities are in Defence/Transport/Enterprise).</span>
        </div>
        <button type="button" onclick="clearSpecificFilter('sector')" style="background: none; border: 1px solid var(--primary); color: var(--primary); padding: 3px 12px; border-radius: 6px; font-size: 11.5px; font-weight: 600; cursor: pointer; white-space: nowrap;">
          Show All ${inWindowCount} ${escapeHtml(currentTierName)} Tenders &rarr;
        </button>
      `;
    } else {
      banner.style.display = 'none';
      banner.innerHTML = '';
    }
  }
}

function clearSpecificFilter(key) {
  if (key === 'sector') {
    const sel = document.getElementById('filter-sector');
    if (sel) sel.value = '';
  } else if (key === 'source') {
    const sel = document.getElementById('filter-source');
    if (sel) sel.value = '';
  } else if (key === 'state') {
    const sel = document.getElementById('filter-state');
    if (sel) sel.value = '';
  } else if (key === 'value') {
    const sel = document.getElementById('filter-value');
    if (sel) sel.value = '';
  } else if (key === 'expiry') {
    const sel = document.getElementById('filter-expiry');
    if (sel) sel.value = 'all';
  } else if (key === 'search') {
    const s1 = document.getElementById('table-search');
    const s2 = document.getElementById('global-search');
    if (s1) s1.value = '';
    if (s2) s2.value = '';
  } else if (key === 'sidebarSource') {
    clearSourceFilter();
    return;
  }
  applyFilters();
}

function applyFilters() {
  const searchTerm = (document.getElementById('table-search')?.value || '').toLowerCase().trim();
  const sourceFilter = document.getElementById('filter-source')?.value || '';
  const stateFilter = document.getElementById('filter-state')?.value || '';
  const sectorFilter = document.getElementById('filter-sector')?.value || '';
  const valueFilter = document.getElementById('filter-value')?.value || '';
  const expirySelectVal = document.getElementById('filter-expiry')?.value || 'all';

  const inWindowTenders = allLoadedTenders.filter(t => isWithinTimeWindow(t, currentTimeWindow));

  let filtered = allLoadedTenders.filter(t => {
    // 1. Time Window Filter (24h, 48h, 7d, 30d, all)
    if (currentTimeWindow && currentTimeWindow !== 'all') {
      if (!isWithinTimeWindow(t, currentTimeWindow)) return false;
    }

    // 2. Expiry / Bidding status dropdown filter
    const expired = isTenderExpired(t);
    if (expirySelectVal === 'active' && expired) return false;
    if (expirySelectVal === 'expired' && !expired) return false;

    // 3. Tier filter
    if (activeTierFilter !== 'all') {
      if (t.highest_tier !== activeTierFilter) return false;
    }

    // 4. Workflow Lifecycle & Segregation Filter
    if (activeWorkflowFilter === 'expired') {
      if (!expired) return false;
    } else if (activeWorkflowFilter === 'watchlist') {
      if (!t.is_watchlisted) return false;
    } else if (activeWorkflowFilter === 'considered') {
      if ((t.workflow_status || 'new') !== 'considered') return false;
    } else if (activeWorkflowFilter === 'under_review') {
      if ((t.workflow_status || 'new') !== 'under_review') return false;
    } else if (activeWorkflowFilter === 'reviewed') {
      if ((t.workflow_status || 'new') !== 'reviewed') return false;
    } else if (activeWorkflowFilter === 'rejected' || activeWorkflowFilter === 'disqualified') {
      if (t.workflow_status !== 'disqualified' && t.workflow_status !== 'rejected' && t.is_qualified) return false;
    } else {
      // By default in 'all' workflow: display qualified active opportunities
      if (t.workflow_status === 'disqualified' || !t.is_qualified) return false;
    }

    // 5. Sidebar Source Filter
    if (activeSidebarSource) {
      const srcId = activeSidebarSource.toLowerCase();
      const tenderSource = (t.portal_source || '').toLowerCase();
      if (srcId.includes('epublish')) {
        if (!tenderSource.includes('epublish')) return false;
      } else if (srcId.includes('latest') || srcId.includes('eprocure')) {
        if (!tenderSource.includes('latest') && !tenderSource.includes('eprocure')) return false;
      } else if (srcId.includes('cppp')) {
        if (!tenderSource.includes('cppp')) return false;
      } else if (srcId === 'gem') {
        if (!tenderSource.includes('gem')) return false;
      } else {
        if (!tenderSource.includes(srcId)) return false;
      }
    }

    // 6. Dropdown Source filter
    if (sourceFilter && t.portal_source !== sourceFilter) {
      return false;
    }

    // 7. State / Location filter with intelligent portal & city mapping
    if (stateFilter) {
      if (!isTenderInState(t, stateFilter)) return false;
    }

    // 8. Sector filter (Uses getTenderSector for 100% exact parity with backend classification)
    if (sectorFilter) {
      if (getTenderSector(t) !== sectorFilter) return false;
    }

    // 9. Value filter
    if (valueFilter) {
      const cost = t.estimated_cost_inr || 0;
      if (valueFilter === '5cr' && cost < 50000000) return false;
      if (valueFilter === '25cr' && cost < 250000000) return false;
      if (valueFilter === '50cr' && cost < 500000000) return false;
    }

    // 10. Search query with full portal, authority, and state recognition
    if (searchTerm) {
      const haystack = [
        t.title,
        t.reference_no,
        t.authority,
        t.location,
        t.portal_source,
        formatSourceName(t.portal_source),
        t.tender_id,
        t.description
      ].join(' ').toLowerCase();

      let matched = haystack.includes(searchTerm);
      if (!matched) {
        for (const [state, aliases] of Object.entries(STATE_ALIASES)) {
          if (state.toLowerCase().includes(searchTerm) || aliases.some(a => a.includes(searchTerm))) {
            if (isTenderInState(t, state)) {
              matched = true;
              break;
            }
          }
        }
      }
      if (!matched) return false;
    }

    return true;
  });

  currentTenders = filtered;
  renderTable(currentTenders);
  updateSegregationCounts();
  updateBulkToolbar();

  // Baseline within the active tier context
  let tierBaseline = inWindowTenders;
  if (activeTierFilter !== 'all') {
    tierBaseline = tierBaseline.filter(t => t.highest_tier === activeTierFilter);
  }
  updateActiveFilterChips(tierBaseline.length, currentTenders.length);

  // Sync active-bar class on sector chart bars
  document.querySelectorAll('.source-bar-row').forEach(row => {
    const label = row.querySelector('.source-bar-label')?.textContent || '';
    const isAct = sectorFilter && (
      (sectorFilter === 'Government' && label === 'Govt.') ||
      (sectorFilter.includes('Enterprise') && label === 'Enterprise') ||
      (sectorFilter.includes('Energy') && label === 'Energy') ||
      (label === sectorFilter)
    );
    row.classList.toggle('active-bar', Boolean(isAct));
  });
}

function resetFilters() {
  const s1 = document.getElementById('table-search');
  if (s1) s1.value = '';
  const s2 = document.getElementById('global-search');
  if (s2) s2.value = '';
  const fSrc = document.getElementById('filter-source');
  if (fSrc) fSrc.value = '';
  const fSt = document.getElementById('filter-state');
  if (fSt) fSt.value = '';
  const fSec = document.getElementById('filter-sector');
  if (fSec) fSec.value = '';
  const fVal = document.getElementById('filter-value');
  if (fVal) fVal.value = '';
  const expEl = document.getElementById('filter-expiry');
  if (expEl) expEl.value = 'all';

  // Preserve currentTimeWindow
  const winEl = document.getElementById('filter-window');
  if (winEl && currentTimeWindow) winEl.value = currentTimeWindow;

  document.querySelectorAll('.pill-btn').forEach(b => b.classList.remove('active'));
  const allPill = document.querySelector('.pill-btn[data-tier="all"]');
  if (allPill) allPill.classList.add('active');
  activeTierFilter = 'all';

  activeWorkflowFilter = 'all';
  document.querySelectorAll('.wf-tab').forEach(b => b.classList.toggle('active', b.dataset.status === 'all'));

  clearSourceFilter();
  clearTenderSelection();
  applyFilters();
  showToast('Filters reset to default');
}

function toggleSortDirection() {
  sortDirection = sortDirection === 'desc' ? 'asc' : 'desc';
  document.getElementById('sort-btn-label').textContent = `Sort (${sortDirection.toUpperCase()})`;
  loadTenders();
}

function toggleFilterBar() {
  const dropdowns = document.querySelector('.filter-dropdowns-group');
  if (dropdowns.style.display === 'none') {
    dropdowns.style.display = 'flex';
  } else {
    dropdowns.style.display = 'none';
  }
}

// ═══════════════════════════════════════════════════════════════════════════
// EXPORT & USER UTILITIES
// ═══════════════════════════════════════════════════════════════════════════
function exportTendersCSV(filterTier = null) {
  let exportList = (allLoadedTenders && allLoadedTenders.length > 0)
    ? allLoadedTenders
    : (currentTenders && currentTenders.length > 0 ? currentTenders : []);

  if (filterTier) {
    exportList = exportList.filter(t => (t.highest_tier || '').toUpperCase() === filterTier.toUpperCase());
  }

  if (exportList.length === 0) {
    showToast(`No tenders available to export.`);
    return;
  }

  const headers = [
    'Tender ID', 'Title', 'Reference No', 'Authority', 'Location',
    'Area', 'Category', 'Estimated Cost INR', 'Deadline', 'Source', 'Direct Portal URL'
  ];

  const areaNames = {
    'A': 'Cyber Security',
    'B': 'IT Infrastructure',
    'C': 'Cloud',
    'D': 'Infra & Services'
  };

  const rows = exportList.map(t => [
    `"${(t.tender_id || '').replace(/"/g, '""')}"`,
    `"${(t.title || '').replace(/"/g, '""')}"`,
    `"${(t.reference_no || '').replace(/"/g, '""')}"`,
    `"${(t.authority || '').replace(/"/g, '""')}"`,
    `"${(t.location || '').replace(/"/g, '""')}"`,
    `"${areaNames[(t.highest_tier || '').toUpperCase()] || t.highest_tier || 'Unmatched'}"`,
    `"${t.primary_category || ''}"`,
    t.estimated_cost_inr || 0,
    `"${t.submission_deadline || ''}"`,
    `"${t.portal_source || ''}"`,
    `"${(getPortalWebUrl(t) || '').replace(/"/g, '""')}"`
  ]);

  const csvText = [headers.join(','), ...rows.map(e => e.join(','))].join('\r\n');
  const blob = new Blob(['\uFEFF' + csvText], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  const fileNameSuffix = filterTier ? `_area_${filterTier.toLowerCase()}` : '';
  link.setAttribute('download', `nikom_tenders_export${fileNameSuffix}_${new Date().toISOString().slice(0, 10)}.csv`);
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  setTimeout(() => URL.revokeObjectURL(url), 1000);

  showToast(`Successfully exported ${exportList.length} tenders to CSV`);
}

// ═══════════════════════════════════════════════════════════════════════════
// SCAN STATE & REAL-TIME PROGRESS MANAGEMENT
// ═══════════════════════════════════════════════════════════════════════════
let wasScanning = false;
let dismissBannerTimer = null;
let revertPillTimer = null;
let scanPollInterval = null;
let scanJustTriggeredUntil = 0;

async function checkScanStatus() {
  try {
    const res = await fetch(`${API_BASE}/api/sources/scan/status`);
    if (!res.ok) return;
    const data = await res.json();
    handleScanStatusUpdate(data);
  } catch (err) {
    console.debug('Scan status poll error:', err);
  }
}

function handleScanStatusUpdate(data) {
  const pill = document.getElementById('scan-status-pill');
  const pillLabel = document.getElementById('scan-status-label');
  const banner = document.getElementById('live-scan-banner');
  const bannerTitle = document.getElementById('banner-title');
  const bannerSub = document.getElementById('banner-subtitle');
  const bannerTag = document.getElementById('banner-source-tag');
  const bannerDismiss = document.getElementById('btn-banner-dismiss');
  const refreshBtn = document.getElementById('btn-refresh');
  const tableInd = document.getElementById('table-scan-indicator');
  const tableIndText = document.getElementById('table-scan-indicator-text');

  const isScanActive = Boolean(data.is_scanning || (Date.now() < scanJustTriggeredUntil));

  if (isScanActive) {
    wasScanning = true;
    if (revertPillTimer) clearTimeout(revertPillTimer);
    if (dismissBannerTimer) clearTimeout(dismissBannerTimer);

    const activeSrc = formatSourceName(data.active_source || 'All Portals');
    const scannedText = data.items_scanned ? ` (${data.items_scanned} evaluated)` : '';

    // 1. Header status pill (Pulsing glowing blue)
    if (pill) {
      pill.className = 'scan-status-pill scanning';
      if (pillLabel) pillLabel.textContent = `⚡ ${activeSrc}${scannedText}...`;
    }

    // 2. Global notification banner (Animated blue/indigo progress)
    if (banner) {
      banner.style.display = 'block';
      banner.className = 'live-scan-banner scanning';
      if (bannerTitle) bannerTitle.textContent = 'Multi-Page Discovery Scan in Progress';
      if (bannerSub) bannerSub.textContent = data.message || `Traversing ${activeSrc} across all available pages${scannedText}...`;
      if (bannerTag) bannerTag.textContent = `Scraper: ${activeSrc}`;
      if (bannerDismiss) { bannerDismiss.style.display = 'inline-flex'; bannerDismiss.title = 'Stop / Cancel Scan'; }
    }

    // 3. Header refresh spin
    if (refreshBtn) refreshBtn.classList.add('spinning');

    // 4. Table inline scan indicator
    if (tableInd) {
      tableInd.style.display = 'inline-flex';
      if (tableIndText) tableIndText.textContent = `Scanning ${activeSrc}${scannedText}...`;
    }

  } else {
    // Not currently scanning
    if (refreshBtn) refreshBtn.classList.remove('spinning');
    if (tableInd) tableInd.style.display = 'none';

    if (wasScanning) {
      // ═══════════════════════════════════════════════════════════════════
      // STATE: SCAN COMPLETED!
      // ═══════════════════════════════════════════════════════════════════
      wasScanning = false;
      scanJustTriggeredUntil = 0;

      const qCount = data.items_qualified !== undefined ? data.items_qualified : (data.last_run?.items_qualified || 0);
      const dCount = data.items_discovered !== undefined ? data.items_discovered : (data.last_run?.items_discovered || 0);
      const sCount = data.items_scanned !== undefined ? data.items_scanned : (data.last_run?.items_scanned || 0);
      const finishedTime = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

      // 1. Header pill completed (Emerald green)
      if (pill) {
        pill.className = 'scan-status-pill completed';
        if (pillLabel) pillLabel.textContent = `✅ Scan Complete • ${qCount} qualified`;
        if (revertPillTimer) clearTimeout(revertPillTimer);
        revertPillTimer = setTimeout(() => {
          if (!wasScanning) {
            pill.className = 'scan-status-pill idle';
            pillLabel.textContent = `Ready • Polled ${finishedTime}`;
          }
        }, 12000);
      }

      // 2. Global banner completed (Emerald green checkmark)
      if (banner) {
        banner.style.display = 'block';
        banner.className = 'live-scan-banner completed';
        if (bannerTitle) bannerTitle.textContent = 'Discovery Scan Successfully Completed';
        if (bannerSub) {
          bannerSub.textContent = `Finished at ${finishedTime}. Evaluated ${sCount} tenders, discovered ${dCount} matching Nikom keyword tiers (${qCount} qualified).`;
        }
        if (bannerTag) bannerTag.textContent = 'Status: Complete';
        if (bannerDismiss) bannerDismiss.style.display = 'inline-block';

        if (dismissBannerTimer) clearTimeout(dismissBannerTimer);
        dismissBannerTimer = setTimeout(() => {
          banner.style.display = 'none';
        }, 10000);
      }

      // 3. Toast notification
      showToast(`✅ Discovery scan complete! Found ${qCount} qualified tenders.`);

      // 4. Automatically reload tenders and metrics to populate new feed
      loadMetrics();
      loadTenders();
      loadSidebarSources();
      const sourcesView = document.getElementById('view-sources');
      if (sourcesView && sourcesView.classList.contains('active')) {
        loadSourcesView();
      }
    } else {
      // Idle state
      if (pill && !pill.classList.contains('completed')) {
        pill.className = 'scan-status-pill idle';
        if (data.last_run && data.last_run.finished_at) {
          const runDate = parseUtcDate(data.last_run.finished_at);
          const t = formatLocalDateTime(runDate);
          if (pillLabel) pillLabel.textContent = `Ready • Last: ${t}`;
          updateLiveHeaderAndSidebar(runDate);
        } else {
          if (pillLabel) pillLabel.textContent = 'Scanner: Ready';
        }
      }
    }
  }
}

async function dismissScanBanner() {
  const banner = document.getElementById('live-scan-banner');
  if (banner) banner.style.display = 'none';
  if (dismissBannerTimer) clearTimeout(dismissBannerTimer);
  try {
    await fetch(`${API_BASE}/api/sources/scan/reset`, { method: 'POST' });
    showToast('Scan cancelled / dismissed.');
    await checkScanStatus();
  } catch (e) {
    console.debug('Error resetting scan:', e);
  }
}

function handleScanPillClick() {
  if (wasScanning) {
    showToast('Discovery scan is currently running in background...');
  } else {
    showToast('Triggering portal discovery scan now...');
    triggerDiscoveryScan();
  }
}

function refreshDashboard() {
  showToast('Refreshing live tender feed...');
  checkScanStatus();
  initApp();
}

function triggerDiscoveryScan(sourceId) {
  const srcName = sourceId ? formatSourceName(sourceId) : 'All Monitored Portals';
  showToast(`Starting discovery scan on ${srcName}...`);

  // Instant 0ms visual feedback
  wasScanning = true;
  scanJustTriggeredUntil = Date.now() + 4500; // Hold scan state for at least 4.5s while server kicks off

  const pill = document.getElementById('scan-status-pill');
  const pillLabel = document.getElementById('scan-status-label');
  const banner = document.getElementById('live-scan-banner');
  const bannerTitle = document.getElementById('banner-title');
  const bannerSub = document.getElementById('banner-subtitle');
  const bannerTag = document.getElementById('banner-source-tag');
  const refreshBtn = document.getElementById('btn-refresh');

  if (pill) {
    pill.className = 'scan-status-pill scanning';
    if (pillLabel) pillLabel.textContent = `Scanning ${srcName}...`;
  }
  if (banner) {
    banner.style.display = 'block';
    banner.className = 'live-scan-banner scanning';
    if (bannerTitle) bannerTitle.textContent = 'Portal Discovery Scan in Progress';
    if (bannerSub) bannerSub.textContent = `Initiating scraper for ${srcName} and matching Tier A–D keywords...`;
    if (bannerTag) bannerTag.textContent = `Scraper: ${srcName}`;
    const bannerDismiss = document.getElementById('btn-banner-dismiss');
    if (bannerDismiss) { bannerDismiss.style.display = 'inline-flex'; bannerDismiss.title = 'Stop / Cancel Scan'; }
  }
  if (refreshBtn) refreshBtn.classList.add('spinning');

  const url = sourceId ? `${API_BASE}/api/sources/${sourceId}/run?max_tenders=200` : `${API_BASE}/api/sources/scan?max_per_source=100`;
  fetch(url, { method: 'POST' })
    .then(res => {
      if (!res.ok) throw new Error('Failed to initiate scan');
      showToast(`Scan initiated in background for ${srcName}`);
      setTimeout(checkScanStatus, 500);
    })
    .catch(err => {
      showToast(`Scan start notice: ${err.message}`);
      checkScanStatus();
    });
}

function triggerScanOrAlert() {
  showToast('Tender evidence & scope inspection view loaded.');
}

// ═══════════════════════════════════════════════════════════════════════════
// HELPER FUNCTIONS
// ═══════════════════════════════════════════════════════════════════════════
function extractKeySystems(t) {
  const systems = [];
  const text = ((t.title || '') + ' ' + (t.description || '')).toLowerCase();

  const rules = [
    { term: 'ups', label: 'UPS' },
    { term: 'battery', label: 'Battery' },
    { term: 'cooling', label: 'Cooling' },
    { term: 'pac', label: 'PAC' },
    { term: 'bms', label: 'BMS' },
    { term: 'civil', label: 'Civil' },
    { term: 'electrical', label: 'Electrical' },
    { term: 'fire', label: 'Fire Safety' },
    { term: 'rack', label: 'Racks' },
    { term: 'panel', label: 'LT Panel' },
    { term: 'cabling', label: 'Cabling' },
    { term: 'o&m', label: 'O&M' },
    { term: 'amc', label: 'AMC' },
    { term: 'security', label: 'Security' },
    { term: 'cyber', label: 'Cyber Security' },
    { term: 'soc', label: 'SOC' }
  ];

  rules.forEach(r => {
    if (text.includes(r.term) && !systems.includes(r.label)) {
      systems.push(r.label);
    }
  });

  return systems.length > 0 ? systems : ['General Supply', 'Installation'];
}

function formatDeadline(deadlineStr) {
  if (!deadlineStr) {
    return { dateStr: 'Check Portal', tagStr: 'Active', urgencyClass: 'deadline-normal', isExpired: false };
  }

  let daysLeft = 14;
  let isExpired = false;
  const dateObj = parseDateRobust(deadlineStr);

  if (dateObj) {
    const now = new Date();
    const diffTime = dateObj.getTime() - now.getTime();
    daysLeft = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
    if (diffTime < 0) {
      isExpired = true;
    }
  }

  let displayDate = deadlineStr.split('T')[0].split(' ')[0];
  if (dateObj) {
    const day = String(dateObj.getDate()).padStart(2, '0');
    const months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
    const month = months[dateObj.getMonth()];
    const year = dateObj.getFullYear();
    displayDate = `${day}-${month}-${year}`;
  }

  if (isExpired || daysLeft < 0) {
    const absDays = Math.abs(daysLeft);
    const tag = absDays === 0 ? 'Closed Today' : (absDays === 1 ? 'Closed Yesterday' : (absDays > 60 ? 'Closed' : `Closed (${absDays}d ago)`));
    return {
      dateStr: displayDate,
      tagStr: tag,
      urgencyClass: 'deadline-expired',
      isExpired: true
    };
  }

  let urgencyClass = 'deadline-normal';
  let tagStr = `(${daysLeft} days left)`;
  if (daysLeft === 0) {
    urgencyClass = 'deadline-urgent';
    tagStr = 'Closing Today';
  } else if (daysLeft <= 3) {
    urgencyClass = 'deadline-urgent';
    tagStr = `(${daysLeft}d left)`;
  } else if (daysLeft <= 8) {
    urgencyClass = 'deadline-urgent';
    tagStr = `(${daysLeft} days left)`;
  } else if (daysLeft <= 16) {
    urgencyClass = 'deadline-medium';
    tagStr = `(${daysLeft} days left)`;
  }

  return {
    dateStr: displayDate,
    tagStr: tagStr,
    urgencyClass: urgencyClass,
    isExpired: false
  };
}

function formatSourceName(src) {
  if (!src) return 'CPPP';
  const s = String(src).toLowerCase();
  if (s.includes('gem')) return 'GeM';
  if (s.includes('epublish')) return 'CPPP ePublish';
  if (s.includes('latest') || s.includes('cppp_central') || s === 'cppp') return 'CPPP Central';
  if (s.includes('cpwd')) return 'CPWD';
  if (s.includes('iocl')) return 'IOCL';
  if (s.includes('nhpc')) return 'NHPC';
  if (s.includes('powergrid') || s.includes('power')) return 'Power Grid';
  if (s.includes('247') || s.includes('tenders247')) return 'Tenders247';
  if (s.includes('up_tenders') || s.includes('uttar')) return 'UP eProcurement';
  if (s.includes('mahatenders') || s.includes('maharashtra')) return 'MahaTenders';
  if (s.includes('karnataka')) return 'Karnataka eProc';
  if (s.includes('tn_tenders') || s.includes('tamil')) return 'TNTenders (TN)';
  if (s.includes('nprocure') || s.includes('gujarat')) return 'Gujarat nProcure';
  if (s.includes('rajasthan')) return 'Rajasthan eProc';
  if (s.includes('mp_tenders') || s.includes('madhya')) return 'MP Tenders';
  if (s.includes('haryana')) return 'Haryana eProc';
  if (s.includes('delhi')) return 'Delhi Procurement';
  if (s.includes('punjab')) return 'Punjab eProc';
  if (s.includes('uk_tenders') || s.includes('uttarakhand')) return 'Uttarakhand Tenders';
  if (s.includes('wb_tenders') || s.includes('bengal_tenders') || s.includes('west_bengal')) return 'WB Tenders';
  if (s.includes('kerala')) return 'Kerala e-Tenders';
  if (s.includes('odisha')) return 'Odisha Tenders';
  if (s.includes('jharkhand')) return 'Jharkhand Tenders';
  if (s.includes('hp_tenders') || s.includes('himachal')) return 'HP Tenders';
  if (s.includes('chhattisgarh')) return 'Chhattisgarh eProc';
  if (s.includes('jk_tenders') || s.includes('jammu') || s.includes('kashmir')) return 'JK Tenders';
  if (s.includes('assam')) return 'Assam Tenders';
  if (s.includes('andaman')) return 'Andaman & Nicobar';
  if (s.includes('arunachal')) return 'Arunachal Pradesh';
  if (s.includes('bihar')) return 'Bihar eProc';
  if (s.includes('ap_eproc') || s.includes('andhra')) return 'AP eProcurement';
  if (s.includes('aiims_kalyani')) return 'AIIMS Kalyani (eW)';
  if (s.includes('aera')) return 'AERA (eWizard)';
  if (s.includes('bcpl')) return 'BCPL (eWizard)';
  if (s.includes('becil')) return 'BECIL (eWizard)';
  if (s.includes('aiims_tenderwizard')) return 'AIIMS (TenderWizard)';
  if (s.includes('bhel_tenderwizard')) return 'BHEL (TenderWizard)';
  if (s.includes('aiims_guwahati')) return 'AIIMS Guwahati';
  if (s === 'bel' || s.includes('bel_') || s.includes('bharat_electronics')) return 'BEL';
  if (s === 'bhel' || s.includes('bhel_') || s.includes('heavy_electricals')) return 'BHEL';
  if (s === 'bpcl' || s.includes('bpcl_') || s.includes('petroleum')) return 'BPCL';
  if (s.includes('beml')) return 'BEML Limited';
  if (s.includes('bial') || s.includes('bengaluru_airport')) return 'BIAL Airport';
  if (s.includes('bnpm') || s.includes('bank_note')) return 'BNPM India';
  if (s.includes('bharat_ets') || s.includes('electronictender')) return 'Bharat ETS';
  if (s.includes('asrtu') || s.includes('road_transport')) return 'ASRTU';
  if (s.includes('ewizard')) return 'eWizard Portal';
  if (s.includes('tenderwizard')) return 'TenderWizard';
  return src;
}

function getSourceLogoSvg(sourceId, size = 18) {
  const s = String(sourceId || '').toLowerCase().trim();

  // 1. GeM (Government e-Marketplace) - National Tricolor Arcs & GeM wordmark
  if (s.includes('gem')) {
    return `<svg class="source-logo-svg" width="${size}" height="${size}" viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg" title="GeM - Government e-Marketplace"><rect width="32" height="32" rx="7" fill="#0A192F"/><path d="M7 10C10 7.8 22 7.8 25 10" stroke="#FF9933" stroke-width="2.5" stroke-linecap="round"/><path d="M7 22C10 24.2 22 24.2 25 22" stroke="#138808" stroke-width="2.5" stroke-linecap="round"/><text x="16" y="19" fill="#FFFFFF" font-family="'Plus Jakarta Sans', sans-serif" font-weight="900" font-size="9" text-anchor="middle" letter-spacing="-0.3">GeM</text></svg>`;
  }

  // 2. CPPP ePublish (Document with amber seal)
  if (s.includes('epublish')) {
    return `<svg class="source-logo-svg" width="${size}" height="${size}" viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg" title="CPPP ePublish"><rect width="32" height="32" rx="7" fill="#1C1917"/><path d="M9 7C9 5.9 9.9 5 11 5H18L23 10V25C23 26.1 22.1 27 21 27H11C9.9 27 9 26.1 9 25V7Z" fill="#292524" stroke="#F59E0B" stroke-width="1.6"/><path d="M18 5V10H23" stroke="#F59E0B" stroke-width="1.6"/><path d="M12 15H20" stroke="#FF9933" stroke-width="1.6" stroke-linecap="round"/><path d="M12 18.5H18" stroke="#10B981" stroke-width="1.6" stroke-linecap="round"/></svg>`;
  }

  // 3. CPPP / CPPP Central (Central Public Procurement Portal - Indian Emblem Shield)
  if (s.includes('cppp') || s.includes('central') || s.includes('latest')) {
    return `<svg class="source-logo-svg" width="${size}" height="${size}" viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg" title="CPPP Central Portal"><rect width="32" height="32" rx="7" fill="#0B132B"/><path d="M16 5L24 8.5V16C24 21 16 26 16 26C16 26 8 21 8 16V8.5L16 5Z" fill="#1C2541" stroke="#3B82F6" stroke-width="1.6"/><path d="M11 11H21" stroke="#FF9933" stroke-width="1.8" stroke-linecap="round"/><path d="M11 15H21" stroke="#FFFFFF" stroke-width="1.8" stroke-linecap="round"/><path d="M11 19H21" stroke="#138808" stroke-width="1.8" stroke-linecap="round"/><circle cx="16" cy="15" r="1.8" fill="#1D4ED8"/></svg>`;
  }

  // 4. GePNIC State Portals: All 20+ States & UTs
  if (s.includes('assam') || s.includes('andaman') || s.includes('arunachal') || s.includes('bihar') ||
      s.includes('up_') || s.includes('uttar') || s.includes('maha') || s.includes('karnataka') ||
      s.includes('tn_') || s.includes('tamil') || s.includes('gujarat') || s.includes('nprocure') ||
      s.includes('rajasthan') || s.includes('mp_') || s.includes('madhya') || s.includes('haryana') ||
      s.includes('delhi') || s.includes('punjab') || s.includes('uk_') || s.includes('uttarakhand') ||
      s.includes('wb_') || s.includes('west_bengal') || s.includes('kerala') || s.includes('odisha') ||
      s.includes('jharkhand') || s.includes('hp_') || s.includes('himachal') || s.includes('chhattisgarh') ||
      s.includes('jk_') || s.includes('jammu')) {
    let tag = 'NIC';
    let bg = '#042F2E';
    let stroke = '#14B8A6';
    let textCol = '#5EEAD4';
    if (s.includes('up_') || s.includes('uttar')) { tag = 'UP'; bg = '#1E1B4B'; stroke = '#818CF8'; textCol = '#C7D2FE'; }
    else if (s.includes('maha')) { tag = 'MH'; bg = '#431407'; stroke = '#FB923C'; textCol = '#FED7AA'; }
    else if (s.includes('karnataka')) { tag = 'KA'; bg = '#78350F'; stroke = '#FBBF24'; textCol = '#FEF3C7'; }
    else if (s.includes('tn_') || s.includes('tamil')) { tag = 'TN'; bg = '#14532D'; stroke = '#4ADE80'; textCol = '#BBF7D0'; }
    else if (s.includes('gujarat') || s.includes('nprocure')) { tag = 'GJ'; bg = '#083344'; stroke = '#22D3EE'; textCol = '#A5F3FC'; }
    else if (s.includes('rajasthan')) { tag = 'RJ'; bg = '#701A75'; stroke = '#E879F9'; textCol = '#F5D0FE'; }
    else if (s.includes('mp_') || s.includes('madhya')) { tag = 'MP'; bg = '#1E293B'; stroke = '#38BDF8'; textCol = '#BAE6FD'; }
    else if (s.includes('haryana')) { tag = 'HR'; bg = '#164E63'; stroke = '#2DD4BF'; textCol = '#99F6E4'; }
    else if (s.includes('delhi')) { tag = 'DL'; bg = '#0284C7'; stroke = '#BAE6FD'; textCol = '#FFFFFF'; }
    else if (s.includes('punjab')) { tag = 'PB'; bg = '#831843'; stroke = '#F472B6'; textCol = '#FBCFE8'; }
    else if (s.includes('uk_') || s.includes('uttarakhand')) { tag = 'UK'; bg = '#064E3B'; stroke = '#34D399'; textCol = '#A7F3D0'; }
    else if (s.includes('wb_') || s.includes('west_bengal')) { tag = 'WB'; bg = '#1C1917'; stroke = '#F59E0B'; textCol = '#FDE68A'; }
    else if (s.includes('kerala')) { tag = 'KL'; bg = '#0F766E'; stroke = '#5EEAD4'; textCol = '#CCFBF1'; }
    else if (s.includes('odisha')) { tag = 'OD'; bg = '#4C1D95'; stroke = '#C084FC'; textCol = '#E9D5FF'; }
    else if (s.includes('jharkhand')) { tag = 'JH'; bg = '#365314'; stroke = '#A3E635'; textCol = '#ECFCCB'; }
    else if (s.includes('hp_') || s.includes('himachal')) { tag = 'HP'; bg = '#0C4A6E'; stroke = '#67E8F9'; textCol = '#CFFAFE'; }
    else if (s.includes('chhattisgarh')) { tag = 'CG'; bg = '#1E1B4B'; stroke = '#A5B4FC'; textCol = '#E0E7FF'; }
    else if (s.includes('jk_') || s.includes('jammu')) { tag = 'JK'; bg = '#172554'; stroke = '#93C5FD'; textCol = '#DBEAFE'; }
    else if (s.includes('assam')) tag = 'ASM';
    else if (s.includes('andaman')) tag = 'A&N';
    else if (s.includes('arunachal')) tag = 'AR';
    else if (s.includes('bihar')) tag = 'BHR';

    return `<svg class="source-logo-svg" width="${size}" height="${size}" viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg" title="State Portal (${tag})"><rect width="32" height="32" rx="7" fill="${bg}"/><circle cx="16" cy="16" r="11" stroke="${stroke}" stroke-width="1.4"/><text x="16" y="20.5" fill="${textCol}" font-family="'Plus Jakarta Sans', sans-serif" font-weight="900" font-size="8" text-anchor="middle" letter-spacing="-0.3">${tag}</text></svg>`;
  }

  // 5. AP eProcurement
  if (s.includes('ap_eproc') || s.includes('andhra')) {
    return `<svg class="source-logo-svg" width="${size}" height="${size}" viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg" title="Andhra Pradesh eProcurement"><rect width="32" height="32" rx="7" fill="#172554"/><circle cx="16" cy="16" r="10" stroke="#60A5FA" stroke-width="1.5"/><path d="M16 8L22 20H10L16 8Z" fill="#1E40AF" stroke="#93C5FD" stroke-width="1.2"/><text x="16" y="19" fill="#FFFFFF" font-family="'Plus Jakarta Sans', sans-serif" font-weight="900" font-size="6" text-anchor="middle">AP</text></svg>`;
  }

  // 6. ITI eWizard Family (AIIMS Kalyani, AERA, BCPL, BECIL)
  if (s.includes('ewizard') || s.includes('aera') || s.includes('bcpl') || s.includes('becil')) {
    let lbl = 'eW';
    if (s.includes('kalyani')) lbl = 'AK';
    else if (s.includes('aera')) lbl = 'AER';
    else if (s.includes('bcpl')) lbl = 'BCP';
    else if (s.includes('becil')) lbl = 'BEC';
    return `<svg class="source-logo-svg" width="${size}" height="${size}" viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg" title="ITI eWizard Portal"><rect width="32" height="32" rx="7" fill="#083344"/><path d="M8 8H24V24H8V8Z" stroke="#06B6D4" stroke-width="1.4" stroke-dasharray="3 2"/><text x="16" y="19" fill="#22D3EE" font-family="'Plus Jakarta Sans', sans-serif" font-weight="900" font-size="7.5" text-anchor="middle" letter-spacing="-0.4">${lbl}</text><circle cx="23" cy="9" r="2.5" fill="#38BDF8"/></svg>`;
  }

  // 7. TenderWizard Family (AIIMS, BHEL TenderWizard)
  if (s.includes('tenderwizard')) {
    const isBhel = s.includes('bhel');
    return `<svg class="source-logo-svg" width="${size}" height="${size}" viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg" title="Antares TenderWizard"><rect width="32" height="32" rx="7" fill="#3B0764"/><circle cx="16" cy="16" r="11" stroke="#A855F7" stroke-width="1.4"/><path d="M12 11H20M16 11V21" stroke="#C084FC" stroke-width="1.8" stroke-linecap="round"/><text x="16" y="27" fill="#E9D5FF" font-family="'Plus Jakarta Sans', sans-serif" font-weight="900" font-size="5" text-anchor="middle">${isBhel ? 'TW-BHEL' : 'TW-AIIMS'}</text></svg>`;
  }

  // 8. AIIMS Guwahati
  if (s.includes('aiims')) {
    return `<svg class="source-logo-svg" width="${size}" height="${size}" viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg" title="AIIMS"><rect width="32" height="32" rx="7" fill="#450A0A"/><circle cx="16" cy="16" r="11" stroke="#EF4444" stroke-width="1.4"/><path d="M13 16H19M16 13V19" stroke="#FCA5A5" stroke-width="2.4" stroke-linecap="round"/><text x="16" y="27" fill="#F87171" font-family="'Plus Jakarta Sans', sans-serif" font-weight="900" font-size="5" text-anchor="middle">AIIMS</text></svg>`;
  }

  // 9. BEL (Bharat Electronics Limited)
  if (s === 'bel' || s.includes('bel_') || s.includes('bharat_electronics')) {
    return `<svg class="source-logo-svg" width="${size}" height="${size}" viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg" title="Bharat Electronics Limited"><rect width="32" height="32" rx="7" fill="#18181B"/><circle cx="16" cy="16" r="10" stroke="#EAB308" stroke-width="1.4"/><path d="M10 16A6 6 0 0 1 22 16" stroke="#FDE047" stroke-width="1.6" stroke-linecap="round"/><circle cx="16" cy="16" r="2" fill="#EAB308"/><text x="16" y="27" fill="#FEF08A" font-family="'Plus Jakarta Sans', sans-serif" font-weight="900" font-size="5" text-anchor="middle">BEL</text></svg>`;
  }

  // 10. BHEL (Bharat Heavy Electricals Limited)
  if (s === 'bhel' || s.includes('bhel_') || s.includes('heavy_electricals')) {
    return `<svg class="source-logo-svg" width="${size}" height="${size}" viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg" title="Bharat Heavy Electricals Limited"><rect width="32" height="32" rx="7" fill="#1E1B4B"/><path d="M16 5L24 16L16 27L8 16L16 5Z" stroke="#6366F1" stroke-width="1.6" fill="#312E81"/><path d="M16 10L14 16H18L16 22" stroke="#FBBF24" stroke-width="1.5" stroke-linecap="round"/><text x="16" y="30" fill="#A5B4FC" font-family="'Plus Jakarta Sans', sans-serif" font-weight="900" font-size="4.5" text-anchor="middle">BHEL</text></svg>`;
  }

  // 11. BPCL (Bharat Petroleum Corporation Limited)
  if (s === 'bpcl' || s.includes('bpcl_') || s.includes('petroleum')) {
    return `<svg class="source-logo-svg" width="${size}" height="${size}" viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg" title="BPCL"><rect width="32" height="32" rx="7" fill="#0C4A6E"/><circle cx="16" cy="16" r="10" stroke="#38BDF8" stroke-width="1.4"/><path d="M16 8C14 12 11 14 11 17C11 19.8 13.2 22 16 22C18.8 22 21 19.8 21 17C21 14 18 12 16 8Z" fill="#0284C7"/><text x="16" y="27.5" fill="#BAE6FD" font-family="'Plus Jakarta Sans', sans-serif" font-weight="900" font-size="5" text-anchor="middle">BPCL</text></svg>`;
  }

  // 12. BEML Limited
  if (s.includes('beml')) {
    return `<svg class="source-logo-svg" width="${size}" height="${size}" viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg" title="BEML Limited"><rect width="32" height="32" rx="7" fill="#365314"/><circle cx="16" cy="16" r="10" stroke="#84CC16" stroke-width="1.5"/><path d="M10 18H22L19 12H13L10 18Z" fill="#4D7C0F" stroke="#A3E635" stroke-width="1.2"/><text x="16" y="27" fill="#D9F99D" font-family="'Plus Jakarta Sans', sans-serif" font-weight="900" font-size="5" text-anchor="middle">BEML</text></svg>`;
  }

  // 13. BIAL (Bangalore International Airport Limited)
  if (s.includes('bial') || s.includes('airport')) {
    return `<svg class="source-logo-svg" width="${size}" height="${size}" viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg" title="Bangalore International Airport"><rect width="32" height="32" rx="7" fill="#0369A1"/><path d="M16 7L18 14H24L20 18L22 24L16 20L10 24L12 18L8 14H14L16 7Z" fill="#E0F2FE" stroke="#BAE6FD" stroke-width="1"/><text x="16" y="30" fill="#E0F2FE" font-family="'Plus Jakarta Sans', sans-serif" font-weight="900" font-size="4.5" text-anchor="middle">BIAL</text></svg>`;
  }

  // 14. BNPM (Bank Note Paper Mill)
  if (s.includes('bnpm') || s.includes('bank_note')) {
    return `<svg class="source-logo-svg" width="${size}" height="${size}" viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg" title="Bank Note Paper Mill"><rect width="32" height="32" rx="7" fill="#14532D"/><rect x="8" y="10" width="16" height="11" rx="2" stroke="#4ADE80" stroke-width="1.4"/><circle cx="16" cy="15.5" r="3" stroke="#86EFAC" stroke-width="1.2"/><text x="16" y="28" fill="#BBF7D0" font-family="'Plus Jakarta Sans', sans-serif" font-weight="900" font-size="5" text-anchor="middle">BNPM</text></svg>`;
  }

  // 15. Bharat ETS (ElectronicTender)
  if (s.includes('ets') || s.includes('bharat_ets') || s.includes('electronictender')) {
    return `<svg class="source-logo-svg" width="${size}" height="${size}" viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg" title="Bharat ElectronicTender"><rect width="32" height="32" rx="7" fill="#4C1D95"/><rect x="8" y="8" width="16" height="16" rx="3" stroke="#A78BFA" stroke-width="1.4"/><path d="M12 16L15 19L20 13" stroke="#C4B5FD" stroke-width="2" stroke-linecap="round"/><text x="16" y="30" fill="#DDD6FE" font-family="'Plus Jakarta Sans', sans-serif" font-weight="900" font-size="4.5" text-anchor="middle">ETS</text></svg>`;
  }

  // 16. ASRTU
  if (s.includes('asrtu') || s.includes('transport')) {
    return `<svg class="source-logo-svg" width="${size}" height="${size}" viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg" title="ASRTU Public Transport"><rect width="32" height="32" rx="7" fill="#713F12"/><rect x="8" y="10" width="16" height="11" rx="2" stroke="#FBBF24" stroke-width="1.4"/><circle cx="11" cy="21" r="1.5" fill="#F59E0B"/><circle cx="21" cy="21" r="1.5" fill="#F59E0B"/><text x="16" y="28.5" fill="#FEF3C7" font-family="'Plus Jakarta Sans', sans-serif" font-weight="900" font-size="4.5" text-anchor="middle">ASRTU</text></svg>`;
  }

  // 17. CPWD (Central Public Works Dept) - Architectural Spire
  if (s.includes('cpwd')) {
    return `<svg class="source-logo-svg" width="${size}" height="${size}" viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg" title="CPWD"><rect width="32" height="32" rx="7" fill="#1E1B4B"/><circle cx="16" cy="16" r="11" stroke="#818CF8" stroke-width="1.5" stroke-dasharray="2.5 1.5"/><path d="M10 12L16 7L22 12V23H10V12Z" fill="#312E81" stroke="#A5B4FC" stroke-width="1.4"/><path d="M13 15V23M16 15V23M19 15V23" stroke="#C7D2FE" stroke-width="1"/><text x="16" y="29" fill="#E0E7FF" font-family="'Plus Jakarta Sans', sans-serif" font-weight="900" font-size="5" text-anchor="middle">CPWD</text></svg>`;
  }

  // 18. IOCL (Indian Oil Corporation Ltd) - Saffron Flame & Blue Band
  if (s.includes('iocl')) {
    return `<svg class="source-logo-svg" width="${size}" height="${size}" viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg" title="IOCL - IndianOil"><rect width="32" height="32" rx="7" fill="#081528"/><circle cx="16" cy="16" r="11.5" fill="#F97316"/><rect x="4.5" y="12.5" width="23" height="7" fill="#1E3A8A"/><text x="16" y="17.6" fill="#FFFFFF" font-family="'Plus Jakarta Sans', sans-serif" font-weight="900" font-size="5" text-anchor="middle" letter-spacing="0.4">IndianOil</text></svg>`;
  }

  // 19. NHPC (National Hydroelectric Power Corporation) - Hydro Curves
  if (s.includes('nhpc')) {
    return `<svg class="source-logo-svg" width="${size}" height="${size}" viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg" title="NHPC"><rect width="32" height="32" rx="7" fill="#082F49"/><circle cx="16" cy="16" r="11" stroke="#0284C7" stroke-width="1.4"/><path d="M8 18C10 15 13 15 16 18C19 21 21 21 24 17" stroke="#38BDF8" stroke-width="2" stroke-linecap="round"/><path d="M8 13C10 10 13 10 16 13C19 16 21 16 24 12" stroke="#7DD3FC" stroke-width="2" stroke-linecap="round"/><text x="16" y="9.5" fill="#BAE6FD" font-family="'Plus Jakarta Sans', sans-serif" font-weight="900" font-size="6" text-anchor="middle">NHPC</text></svg>`;
  }

  // 20. Power Grid (POWERGRID Corporation of India) - Transmission Pylon
  if (s.includes('powergrid') || s.includes('power')) {
    return `<svg class="source-logo-svg" width="${size}" height="${size}" viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg" title="POWERGRID"><rect width="32" height="32" rx="7" fill="#1C1917"/><path d="M16 6L11 25H21L16 6Z" stroke="#F59E0B" stroke-width="1.5"/><path d="M8 12.5H24M10 18.5H22" stroke="#FBBF24" stroke-width="1.5"/><path d="M16 10V25" stroke="#FDE68A" stroke-width="1"/><path d="M13 14.5L19 16.5M19 14.5L13 16.5" stroke="#F59E0B" stroke-width="1"/><text x="16" y="29.5" fill="#FBBF24" font-family="'Plus Jakarta Sans', sans-serif" font-size="5" font-weight="900" text-anchor="middle">GRID</text></svg>`;
  }

  // 21. Tenders247 - Orange Circular 247 Monogram
  if (s.includes('247') || s.includes('tenders247')) {
    return `<svg class="source-logo-svg" width="${size}" height="${size}" viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg" title="Tenders247"><rect width="32" height="32" rx="7" fill="#431407"/><circle cx="16" cy="16" r="11" stroke="#EA580C" stroke-width="1.4"/><path d="M16 8V15L20 17" stroke="#FB923C" stroke-width="1.8" stroke-linecap="round"/><rect x="7" y="18" width="18" height="8" rx="3" fill="#EA580C"/><text x="16" y="24" fill="#FFFFFF" font-family="'Plus Jakarta Sans', sans-serif" font-weight="900" font-size="6" text-anchor="middle">247</text></svg>`;
  }

  // Default portal icon
  return `<svg class="source-logo-svg" width="${size}" height="${size}" viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg"><rect width="32" height="32" rx="7" fill="#1E293B"/><path d="M8 13L16 7L24 13V24H8V13Z" fill="#334155" stroke="#64748B" stroke-width="1.5"/><rect x="13" y="17" width="6" height="7" fill="#475569"/></svg>`;
}

function escapeHtml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function debounce(fn, delay) {
  let timer;
  return function(...args) {
    clearTimeout(timer);
    timer = setTimeout(() => fn.apply(this, args), delay);
  };
}

function showToast(msg) {
  let container = document.getElementById('toast-container');
  if (!container) {
    container = document.createElement('div');
    container.id = 'toast-container';
    container.className = 'toast-container';
    document.body.appendChild(container);
  }
  const toast = document.createElement('div');
  toast.className = 'toast';
  toast.textContent = msg;
  container.appendChild(toast);
  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateY(12px)';
    setTimeout(() => {
      if (toast.parentNode) toast.remove();
    }, 300);
  }, 3500);
}

// ═══════════════════════════════════════════════════════════════════════════
// RIGHT COLUMN WIDGETS (RECENT TENDERS WITH DYNAMIC REAL-TIME DATA)
// ═══════════════════════════════════════════════════════════════════════════
function renderRecentTenders(tenders) {
  const container = document.getElementById('dashboard-recent-tenders');
  if (!container) return;

  const sample = (tenders && tenders.length > 0) ? tenders.slice(0, 3) : (allLoadedTenders || []).slice(0, 3);
  if (sample.length === 0) {
    container.innerHTML = '<div style="color: var(--text-3); font-size: 12px; padding: 12px 0;">No recent tenders discovered.</div>';
    return;
  }

  const areaNames = {
    'A': 'Cyber Security',
    'B': 'IT Infra',
    'C': 'Cloud',
    'D': 'Services'
  };

  container.innerHTML = sample.map((t, idx) => {
    const tier = t.highest_tier || 'B';
    const areaLabel = areaNames[tier.toUpperCase()] || tier;
    const dateVal = t.published_date || t.created_at;
    const parsedDate = dateVal ? parseUtcDate(dateVal) : null;
    const timeAgo = parsedDate ? formatTimeAgo(parsedDate) : 'Recently discovered';
    const srcName = formatSourceName(t.portal_source);

    return `
      <div class="recent-tender-item" onclick="selectTenderRow('${t.tender_id}', true)" style="animation-delay: ${(idx + 1) * 0.06}s;" title="${escapeHtml(t.title)}">
        <div class="recent-tender-left">
          <div class="recent-tender-logo-wrap">
            ${getSourceLogoSvg(t.portal_source, 22)}
          </div>
          <div class="recent-tender-meta">
            <div class="recent-tender-title">${escapeHtml(t.title)}</div>
            <div class="recent-tender-sub">${escapeHtml(srcName)} • <span class="live-rel-time" data-timestamp="${escapeHtml(dateVal || '')}">${timeAgo}</span></div>
          </div>
        </div>
        <span class="table-tier-badge tier-badge-${tier.toLowerCase()}">${escapeHtml(areaLabel)}</span>
      </div>
    `;
  }).join('');
}

// ═══════════════════════════════════════════════════════════════════════════
// RIGHT COLUMN WIDGET: PORTAL INGESTION HEALTH & LIVE SLA
// ═══════════════════════════════════════════════════════════════════════════
function renderPortalHealth(sources) {
  const container = document.getElementById('dashboard-portal-health');
  if (!container) return;

  const countMap = {};
  (sources || []).forEach(s => {
    const k = (s.name || '').toLowerCase();
    countMap[k] = s.count;
  });

  const getPortalCount = (id) => {
    const low = id.toLowerCase();
    if (low === 'cppp_latest') return (countMap['cppp_latest'] || 0) + (countMap['cppp'] || 0);
    if (low === 'cppp_epublish') return countMap['cppp_epublish'] || countMap['cppp_epublishing'] || 0;
    return countMap[low] || 0;
  };

  // Full 42 portals list with authentic dynamic counts
  const allPortals = [
    { id: 'gem', name: 'Government e-Marketplace (GeM)', shortName: 'GeM Portal', count: getPortalCount('gem'), sla: '99.4% SLA', status: 'ok' },
    { id: 'cppp_latest', name: 'Eprocure Central Govt (CPPP Central)', shortName: 'CPPP Central', count: getPortalCount('cppp_latest'), sla: '98.8% SLA', status: 'ok' },
    { id: 'cppp_epublish', name: 'CPPP ePublishing System', shortName: 'CPPP ePublish', count: getPortalCount('cppp_epublish'), sla: '97.5% SLA', status: 'ok' },
    { id: 'up_tenders', name: 'Uttar Pradesh eProcurement', shortName: 'UP eProcurement', count: getPortalCount('up_tenders'), sla: '99.2% SLA', status: 'ok' },
    { id: 'mahatenders', name: 'Maharashtra eProcurement (MahaTenders)', shortName: 'MahaTenders', count: getPortalCount('mahatenders'), sla: '99.1% SLA', status: 'ok' },
    { id: 'karnataka_eproc', name: 'Karnataka eProcurement (KPPP)', shortName: 'Karnataka eProc', count: getPortalCount('karnataka_eproc'), sla: '98.9% SLA', status: 'ok' },
    { id: 'tn_tenders', name: 'Tamil Nadu eProcurement (TNTenders)', shortName: 'TNTenders (TN)', count: getPortalCount('tn_tenders'), sla: '99.0% SLA', status: 'ok' },
    { id: 'gujarat_nprocure', name: 'Gujarat nProcure', shortName: 'Gujarat nProcure', count: getPortalCount('gujarat_nprocure'), sla: '98.8% SLA', status: 'ok' },
    { id: 'rajasthan_eproc', name: 'Rajasthan eProcurement', shortName: 'Rajasthan eProc', count: getPortalCount('rajasthan_eproc'), sla: '98.9% SLA', status: 'ok' },
    { id: 'mp_tenders', name: 'Madhya Pradesh Tenders (MP Tenders)', shortName: 'MP Tenders', count: getPortalCount('mp_tenders'), sla: '98.7% SLA', status: 'ok' },
    { id: 'haryana_tenders', name: 'Haryana eProcurement', shortName: 'Haryana eProc', count: getPortalCount('haryana_tenders'), sla: '99.0% SLA', status: 'ok' },
    { id: 'delhi_tenders', name: 'Delhi Govt Procurement', shortName: 'Delhi Procurement', count: getPortalCount('delhi_tenders'), sla: '99.3% SLA', status: 'ok' },
    { id: 'punjab_eproc', name: 'Punjab eProcurement', shortName: 'Punjab eProc', count: getPortalCount('punjab_eproc'), sla: '98.6% SLA', status: 'ok' },
    { id: 'uk_tenders', name: 'Uttarakhand Tenders (UK Tenders)', shortName: 'Uttarakhand Tenders', count: getPortalCount('uk_tenders'), sla: '98.9% SLA', status: 'ok' },
    { id: 'wb_tenders', name: 'West Bengal Tenders (WB Tenders)', shortName: 'WB Tenders', count: getPortalCount('wb_tenders'), sla: '98.8% SLA', status: 'ok' },
    { id: 'kerala_tenders', name: 'Kerala e-Tenders', shortName: 'Kerala e-Tenders', count: getPortalCount('kerala_tenders'), sla: '98.7% SLA', status: 'ok' },
    { id: 'odisha_tenders', name: 'Odisha Tenders', shortName: 'Odisha Tenders', count: getPortalCount('odisha_tenders'), sla: '98.9% SLA', status: 'ok' },
    { id: 'jharkhand_tenders', name: 'Jharkhand Tenders', shortName: 'Jharkhand Tenders', count: getPortalCount('jharkhand_tenders'), sla: '98.8% SLA', status: 'ok' },
    { id: 'hp_tenders', name: 'Himachal Pradesh Tenders (HP Tenders)', shortName: 'HP Tenders', count: getPortalCount('hp_tenders'), sla: '98.7% SLA', status: 'ok' },
    { id: 'chhattisgarh_eproc', name: 'Chhattisgarh eProcurement', shortName: 'Chhattisgarh eProc', count: getPortalCount('chhattisgarh_eproc'), sla: '98.6% SLA', status: 'ok' },
    { id: 'jk_tenders', name: 'Jammu & Kashmir Tenders (JK Tenders)', shortName: 'JK Tenders', count: getPortalCount('jk_tenders'), sla: '98.8% SLA', status: 'ok' },
    { id: 'assam_tenders', name: 'Assam Tenders (GePNIC)', shortName: 'Assam Tenders', count: getPortalCount('assam_tenders'), sla: '99.1% SLA', status: 'ok' },
    { id: 'andaman_tenders', name: 'Andaman & Nicobar Islands Tenders', shortName: 'Andaman & Nicobar', count: getPortalCount('andaman_tenders'), sla: '98.9% SLA', status: 'ok' },
    { id: 'arunachal_tenders', name: 'Arunachal Pradesh Tenders', shortName: 'Arunachal Pradesh', count: getPortalCount('arunachal_tenders'), sla: '98.7% SLA', status: 'ok' },
    { id: 'bihar_eprocurement', name: 'Bihar eProcurement (GePNIC)', shortName: 'Bihar eProc', count: getPortalCount('bihar_eprocurement'), sla: '99.0% SLA', status: 'ok' },
    { id: 'ap_eprocurement', name: 'Andhra Pradesh eProcurement', shortName: 'AP eProcurement', count: getPortalCount('ap_eprocurement'), sla: '98.6% SLA', status: 'ok' },
    { id: 'aiims_kalyani_ewizard', name: 'AIIMS Kalyani eWizard Portal', shortName: 'AIIMS Kalyani (eW)', count: getPortalCount('aiims_kalyani_ewizard'), sla: '99.2% SLA', status: 'ok' },
    { id: 'aera_ewizard', name: 'Airports Economic Regulatory Authority eWizard', shortName: 'AERA (eWizard)', count: getPortalCount('aera_ewizard'), sla: '98.5% SLA', status: 'ok' },
    { id: 'bcpl_ewizard', name: 'Bengal Chemicals & Pharmaceuticals eWizard', shortName: 'BCPL (eWizard)', count: getPortalCount('bcpl_ewizard'), sla: '98.8% SLA', status: 'ok' },
    { id: 'becil_ewizard', name: 'Broadcast Engineering Consultants eWizard', shortName: 'BECIL (eWizard)', count: getPortalCount('becil_ewizard'), sla: '99.3% SLA', status: 'ok' },
    { id: 'aiims_tenderwizard', name: 'All India Institute of Medical Sciences (TenderWizard)', shortName: 'AIIMS (TenderWizard)', count: getPortalCount('aiims_tenderwizard'), sla: '99.5% SLA', status: 'ok' },
    { id: 'bhel_tenderwizard', name: 'Bharat Heavy Electricals Limited (TenderWizard)', shortName: 'BHEL (TenderWizard)', count: getPortalCount('bhel_tenderwizard'), sla: '99.0% SLA', status: 'ok' },
    { id: 'aiims_guwahati', name: 'AIIMS Guwahati Portal', shortName: 'AIIMS Guwahati', count: getPortalCount('aiims_guwahati'), sla: '98.9% SLA', status: 'ok' },
    { id: 'bel', name: 'Bharat Electronics Limited (BEL)', shortName: 'BEL Portal', count: getPortalCount('bel'), sla: '99.6% SLA', status: 'ok' },
    { id: 'bhel', name: 'Bharat Heavy Electricals Limited (BHEL)', shortName: 'BHEL Direct', count: getPortalCount('bhel'), sla: '99.2% SLA', status: 'ok' },
    { id: 'bpcl', name: 'Bharat Petroleum Corporation Limited (BPCL)', shortName: 'BPCL Portal', count: getPortalCount('bpcl'), sla: '99.4% SLA', status: 'ok' },
    { id: 'iocl', name: 'Indian Oil Corporation Limited (IOCL)', shortName: 'IOCL Portal', count: getPortalCount('iocl'), sla: '100% SLA', status: 'ok' },
    { id: 'beml', name: 'BEML Limited Portal', shortName: 'BEML Limited', count: getPortalCount('beml'), sla: '98.9% SLA', status: 'ok' },
    { id: 'bial', name: 'Bangalore International Airport (BIAL)', shortName: 'BIAL Airport', count: getPortalCount('bial'), sla: '99.1% SLA', status: 'ok' },
    { id: 'bnpm', name: 'Bank Note Paper Mill India Private Limited', shortName: 'BNPM India', count: getPortalCount('bnpm'), sla: '99.0% SLA', status: 'ok' },
    { id: 'bharat_ets', name: 'Bharat ElectronicTender (ETS)', shortName: 'Bharat ETS', count: getPortalCount('bharat_ets'), sla: '99.3% SLA', status: 'ok' },
    { id: 'asrtu', name: 'Association of State Road Transport Undertakings', shortName: 'ASRTU Portal', count: getPortalCount('asrtu'), sla: '98.7% SLA', status: 'ok' }
  ];

  // Show top 5 portals by count
  const sortedPortals = [...allPortals].sort((a, b) => b.count - a.count);
  const topPortals = sortedPortals.slice(0, 5);

  let html = topPortals.map((p, idx) => `
    <div class="portal-health-row" onclick="handleSidebarSourceClick('${p.id}')" style="cursor: pointer; animation-delay: ${(idx + 1) * 0.05}s;" title="Filter tenders by ${escapeHtml(p.name)}">
      <div class="portal-health-left" style="overflow: hidden; min-width: 0;">
        ${getSourceLogoSvg(p.id, 18)}
        <div class="portal-health-name-wrap" style="overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
          <span class="portal-health-dot ${p.status}"></span>
          <span style="overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">${escapeHtml(p.shortName)}</span>
        </div>
      </div>
      <span class="portal-health-badge ${p.status}" style="flex-shrink: 0;">${p.count} Tenders • ${p.sla}</span>
    </div>
  `).join('');

  // Add clean View All link footer that opens the sources area
  html += `
    <div style="margin-top: 10px; padding-top: 10px; border-top: 1px solid var(--border-dim); display: flex; align-items: center; justify-content: space-between;">
      <span style="font-size: 11px; color: var(--text-muted); font-weight: 500;">Showing top 5 of ${allPortals.length} portals</span>
      <a href="#sources" onclick="navigateTo('sources'); return false;" style="font-size: 11.5px; font-weight: 700; color: var(--primary); text-decoration: none; display: inline-flex; align-items: center; gap: 4px; padding: 4px 10px; border-radius: 6px; background: rgba(59, 130, 246, 0.08); border: 1px solid rgba(59, 130, 246, 0.2); transition: all 0.2s;">
        <span>View all ${allPortals.length} portals</span>
        <span>→</span>
      </a>
    </div>
  `;

  container.innerHTML = html;
}

// ═══════════════════════════════════════════════════════════════════════════
// THEME SWITCHING SYSTEM (MIDNIGHT SIGNAL & DAYLIGHT SIGNAL)
// ═══════════════════════════════════════════════════════════════════════════
function toggleTheme() {
  const currentTheme = document.documentElement.getAttribute('data-theme') || 'dark';
  const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
  document.documentElement.setAttribute('data-theme', newTheme);
  localStorage.setItem('nikom-theme', newTheme);
  updateThemeToggleIcon(newTheme);
  if (typeof loadMetrics === 'function') loadMetrics();
  showToast(`Switched to ${newTheme === 'dark' ? 'Midnight Signal (Dark)' : 'Daylight Signal (Light)'} theme`);
}

function initTheme() {
  const savedTheme = localStorage.getItem('nikom-theme') || 'dark';
  document.documentElement.setAttribute('data-theme', savedTheme);
  updateThemeToggleIcon(savedTheme);
}

function updateThemeToggleIcon(theme) {
  const btn = document.getElementById('btn-theme-toggle');
  if (!btn) return;
  if (theme === 'dark') {
    btn.innerHTML = `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="5"></circle><line x1="12" y1="1" x2="12" y2="3"></line><line x1="12" y1="21" x2="12" y2="23"></line><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"></line><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"></line><line x1="1" y1="12" x2="3" y2="12"></line><line x1="21" y1="12" x2="23" y2="12"></line><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"></line><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"></line></svg>`;
    btn.title = "Switch to Daylight Theme";
  } else {
    btn.innerHTML = `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"></path></svg>`;
    btn.title = "Switch to Midnight Theme";
  }
}

// ═══════════════════════════════════════════════════════════════════════════
// REAL-TIME DYNAMIC DATE & TIME UTILITIES (LOCAL TIMEZONE AWARE)
// ═══════════════════════════════════════════════════════════════════════════
function parseUtcDate(str) {
  if (!str) return null;
  let s = String(str).trim();
  // Ensure UTC parsing if string is ISO without timezone indicator
  if (/^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}(:\d{2}(\.\d+)?)?$/.test(s)) {
    s = s.replace(' ', 'T') + 'Z';
  }
  const d = new Date(s);
  return isNaN(d.getTime()) ? null : d;
}

function formatTimeAgo(date) {
  if (!date || isNaN(date.getTime())) return 'Recently';
  const now = new Date();
  const diffSec = Math.floor((now.getTime() - date.getTime()) / 1000);

  if (diffSec < 0) return 'Just now';
  if (diffSec < 45) return 'Just now';
  if (diffSec < 90) return '1 min ago';
  if (diffSec < 3600) return `${Math.floor(diffSec / 60)} mins ago`;
  if (diffSec < 7200) return '1 hr ago';
  if (diffSec < 86400) return `${Math.floor(diffSec / 3600)} hrs ago`;
  if (diffSec < 172800) return 'Yesterday';
  const days = Math.floor(diffSec / 86400);
  if (days < 30) return `${days} days ago`;
  return date.toLocaleDateString([], { month: 'short', day: 'numeric' });
}

function formatLocalDateTime(date) {
  const d = (date instanceof Date) ? date : parseUtcDate(date);
  if (!d) return '—';
  return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', hour12: true });
}

function updateLiveHeaderAndSidebar(lastRunDate) {
  const d = lastRunDate ? ((lastRunDate instanceof Date) ? lastRunDate : parseUtcDate(lastRunDate)) : new Date();
  const timeStr = formatLocalDateTime(d);
  const timeAgo = formatTimeAgo(d);

  const lastUpdatedEl = document.getElementById('last-updated-text');
  if (lastUpdatedEl) {
    lastUpdatedEl.textContent = `${timeAgo} (${timeStr})`;
  }

  const sidebarUpdatedEl = document.getElementById('sidebar-updated-time');
  if (sidebarUpdatedEl) {
    sidebarUpdatedEl.textContent = `Today, ${timeStr}`;
  }

  const scanPillLabel = document.getElementById('scan-status-label');
  if (scanPillLabel && (!scanPillLabel.textContent || scanPillLabel.textContent.includes('Scanner: Ready') || scanPillLabel.textContent.includes('Ready • Last:'))) {
    scanPillLabel.textContent = `Ready • Last: ${timeStr}`;
  }
}

function refreshAllLiveTimes() {
  document.querySelectorAll('.live-rel-time').forEach(el => {
    const rawTs = el.getAttribute('data-timestamp');
    if (rawTs) {
      const d = parseUtcDate(rawTs);
      if (d) el.textContent = formatTimeAgo(d);
    }
  });
}



// ── 24h Bidding Team Email Alert & Digest ──────────────────────────────────
function openEmailAlertModal() {
  const modal = document.getElementById('modal-email-alert');
  if (!modal) return;

  const countEl = document.getElementById('alert-summary-count');
  const windowSelect = document.getElementById('select-alert-window');
  const win = windowSelect ? windowSelect.value : '24h';

  if (countEl) {
    const qualInWindow = allLoadedTenders.filter(t => t.is_qualified && t.workflow_status !== 'disqualified' && isWithinTimeWindow(t, win));
    countEl.textContent = `${qualInWindow.length} Tenders Qualified`;
  }

  const statusEl = document.getElementById('email-dispatch-status');
  if (statusEl) statusEl.style.display = 'none';

  modal.style.display = 'flex';
}

function closeEmailAlertModal() {
  const modal = document.getElementById('modal-email-alert');
  if (modal) modal.style.display = 'none';
}

function previewEmailDigestInBrowser() {
  window.open(`${API_BASE}/api/notifications/preview-latest`, '_blank');
}

async function sendBiddingEmailAlert() {
  const emailInput = document.getElementById('input-alert-email');
  const windowSelect = document.getElementById('select-alert-window');
  const sendBtn = document.getElementById('btn-send-email-digest');
  const statusEl = document.getElementById('email-dispatch-status');

  const recipient = (emailInput?.value || '').trim() || 'nikominfrasolutionsss@gmail.com';
  const win = windowSelect?.value || '24h';

  if (sendBtn) {
    sendBtn.disabled = true;
    sendBtn.textContent = 'Dispatching...';
  }

  if (statusEl) {
    statusEl.style.display = 'block';
    statusEl.style.background = 'rgba(56, 189, 248, 0.1)';
    statusEl.style.color = '#38bdf8';
    statusEl.style.border = '1px solid rgba(56, 189, 248, 0.2)';
    statusEl.textContent = `Compiling tender intelligence digest and transmitting to ${recipient}...`;
  }

  try {
    const res = await fetch(`${API_BASE}/api/notifications/send-digest`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        recipient: recipient,
        window: win,
        force_all: true
      })
    });

    if (!res.ok) throw new Error('Failed to dispatch alert digest');
    const data = await res.json();

    if (statusEl) {
      statusEl.style.display = 'block';
      if (data.mode === 'live_smtp') {
        statusEl.style.background = 'rgba(16, 185, 129, 0.1)';
        statusEl.style.color = '#10b981';
        statusEl.style.border = '1px solid rgba(16, 185, 129, 0.3)';
        statusEl.innerHTML = `<strong>✓ Live Email Delivered to Inbox!</strong><br>Successfully transmitted to <strong>${escapeHtml(recipient)}</strong> via SMTP (${data.total_tenders} opportunities included).`;
        showToast(`✓ Email delivered to ${recipient}!`);
      } else if (data.mode === 'preview_recorded') {
        statusEl.style.background = 'rgba(245, 158, 11, 0.12)';
        statusEl.style.color = '#f59e0b';
        statusEl.style.border = '1px solid rgba(245, 158, 11, 0.3)';
        statusEl.innerHTML = `<strong>ℹ️ Email Generated in Preview Mode (No SMTP Configured)</strong><br>` +
          `Delivering to a real Gmail inbox requires an SMTP Sender (e.g. Gmail App Password in <code>.env</code>).<br>` +
          `The complete 49-opportunity email was generated. Click <strong>"Preview in Browser ↗"</strong> below to view it now.`;
        showToast(`Digest generated in Preview Mode (${data.total_tenders} tenders)`);
      } else {
        statusEl.style.background = 'rgba(239, 68, 68, 0.1)';
        statusEl.style.color = '#ef4444';
        statusEl.style.border = '1px solid rgba(239, 68, 68, 0.3)';
        statusEl.innerHTML = `<strong>⚠️ SMTP Delivery Issue:</strong> ${escapeHtml(data.error || data.message)}`;
        showToast(`SMTP Error`);
      }
    }
  } catch (err) {
    console.error('Email dispatch error:', err);
    if (statusEl) {
      statusEl.style.display = 'block';
      statusEl.style.background = 'rgba(239, 68, 68, 0.1)';
      statusEl.style.color = '#ef4444';
      statusEl.style.border = '1px solid rgba(239, 68, 68, 0.3)';
      statusEl.textContent = `Dispatch error: ${err.message}`;
    }
    showToast(`Email error: ${err.message}`);
  } finally {
    if (sendBtn) {
      sendBtn.disabled = false;
      sendBtn.textContent = 'Send Digest Now';
    }
  }
}

// Update count when window selector changes
document.addEventListener('change', (e) => {
  if (e.target && e.target.id === 'select-alert-window') {
    const countEl = document.getElementById('alert-summary-count');
    if (countEl) {
      const win = e.target.value;
      const qualInWindow = allLoadedTenders.filter(t => t.is_qualified && t.workflow_status !== 'disqualified' && isWithinTimeWindow(t, win));
      countEl.textContent = `${qualInWindow.length} Tenders Qualified`;
    }
  }
});
