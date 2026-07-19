/* ============================================
   MKT Helpdesk AI — Frontend Application
   ============================================ */

const API = window.location.origin;
let currentTicketId = null;
let charts = {};
let currentUser = null;  // menyimpan data user yang sedang login

// ─── INIT ────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  checkAuthAndInit();
});

// ─── AUTH: CEK TOKEN SAAT LOAD ───────────────
async function checkAuthAndInit() {
  const token = localStorage.getItem('mkt_token');
  if (!token) { showLoginPage(); return; }

  // Verifikasi token masih valid
  const user = await apiFetch('/api/auth/me', {}, true);
  if (!user || user.detail) { showLoginPage(); return; }

  currentUser = user;
  showDashboard();
}

function showLoginPage() {
  document.getElementById('loginPage').classList.remove('hidden');
  document.getElementById('loginUsername').focus();
}

function showDashboard() {
  document.getElementById('loginPage').classList.add('hidden');
  updateUserUI();
  initNav();
  initClock();
  loadDashboard();
  setInterval(loadDashboard, 30000);
  pollCrewAIStatus();
  setInterval(pollCrewAIStatus, 15000);
}

async function pollCrewAIStatus() {
  const indicator = document.getElementById('crewaiIndicator');
  const text = document.getElementById('crewaiIndicatorText');
  if (!indicator || !text) return;

  try {
    // Bypass backend proxy, ping CrewAI container directly on port 8002
    const crewaiUrl = window.location.protocol + "//" + window.location.hostname + ":8002/api/health";
    const res = await fetch(`${crewaiUrl}?_t=${Date.now()}`);
    if (res.ok) {
      const data = await res.json();
      if (data.status === 'online') {
        indicator.classList.remove('offline');
        indicator.classList.add('online');
        text.textContent = 'CrewAI Online';
        return;
      }
    }
  } catch (e) {
    console.warn("CrewAI status check failed", e);
  }
  
  // Default to offline if error or not online
  indicator.classList.remove('online');
  indicator.classList.add('offline');
  text.textContent = 'CrewAI Offline';
}

function updateUserUI() {
  if (!currentUser) return;
  const initials = (currentUser.full_name || currentUser.username || 'U')[0].toUpperCase();
  document.getElementById('avatarBtn').textContent = initials;
  document.getElementById('dropdownName').textContent = currentUser.full_name || currentUser.username;
  document.getElementById('dropdownRole').textContent = roleLabel(currentUser.role);

  // Tampilkan menu User Management untuk semua user (sesuai request: semua akun bisa CRUD)
  const canManageUsers = true;
  document.getElementById('navUsers').style.display = canManageUsers ? 'flex' : 'none';

  // Sembunyikan tombol "+ Tiket Baru" untuk GUEST
  if (currentUser.role === 'GUEST') {
    document.getElementById('btnNewTicket').style.display = 'none';
  }
}

// ─── AUTH: LOGIN ──────────────────────────────
async function handleLogin(e) {
  e.preventDefault();
  const username = document.getElementById('loginUsername').value.trim();
  const password = document.getElementById('loginPassword').value;
  const btn = document.getElementById('loginBtn');
  const errEl = document.getElementById('loginError');

  if (!username || !password) return;
  btn.textContent = 'Memverifikasi...'; btn.disabled = true;
  errEl.style.display = 'none';

  try {
    const res = await fetch(API + '/api/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: `username=${encodeURIComponent(username)}&password=${encodeURIComponent(password)}`,
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Login gagal');

    localStorage.setItem('mkt_token', data.access_token);
    currentUser = data.user;
    showDashboard();
  } catch (err) {
    errEl.textContent = '❌ ' + err.message;
    errEl.style.display = 'block';
  } finally {
    btn.textContent = 'Masuk'; btn.disabled = false;
  }
}

// ─── AUTH: LOGOUT ────────────────────────────
function handleLogout() {
  localStorage.removeItem('mkt_token');
  currentUser = null;
  document.getElementById('userDropdown').style.display = 'none';
  showLoginPage();
  document.getElementById('loginUsername').value = '';
  document.getElementById('loginPassword').value = '';
}

function toggleUserDropdown() {
  const dd = document.getElementById('userDropdown');
  dd.style.display = dd.style.display === 'none' ? 'block' : 'none';
}
document.addEventListener('click', (e) => {
  if (!document.getElementById('userMenu')?.contains(e.target)) {
    const dd = document.getElementById('userDropdown');
    if (dd) dd.style.display = 'none';
  }
});

// ─── NAVIGATION ──────────────────────────────
function initNav() {
  document.querySelectorAll('.nav-item').forEach(item => {
    item.addEventListener('click', e => {
      e.preventDefault();
      const page = item.dataset.page;
      if (page) navigateTo(page);
    });
  });
  document.querySelectorAll('[data-page]').forEach(el => {
    el.addEventListener('click', e => {
      e.preventDefault();
      navigateTo(el.dataset.page);
    });
  });
  document.getElementById('hamburger').addEventListener('click', () => {
    document.getElementById('sidebar').classList.toggle('open');
  });
}

function navigateTo(page) {
  document.querySelectorAll('.nav-item').forEach(i => i.classList.remove('active'));
  document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
  const navItem = document.querySelector(`.nav-item[data-page="${page}"]`);
  if (navItem) navItem.classList.add('active');
  const pageEl = document.getElementById(`page-${page}`);
  if (pageEl) pageEl.classList.add('active');
  document.getElementById('breadcrumb').textContent = {
    dashboard: 'Dashboard', tickets: 'Tiket', sites: 'Sites',
    devices: 'Perangkat', incidents: 'Incident Memory', audit: 'Audit Log',
    tier1: 'Tier 1 Diagnostic', telegram: 'Telegram Notif',
    workflow: 'Workflow (11 Steps)', zammad: 'Zammad Status',
    users: 'Manajemen User'
  }[page] || page;

  const loaders = {
    tickets: loadTickets, sites: loadSites, devices: loadDevices,
    incidents: loadIncidents, audit: loadAuditLogs,
    tier1: loadTier1Diagnostics, telegram: loadTelegramLogs,
    workflow: loadWorkflowStatus, zammad: loadZammadStatus,
    users: loadUsers,
  };
  if (loaders[page]) loaders[page]();
}

// ─── CLOCK & BADGES ────────────────────────────
function initClock() {
  const el = document.getElementById('topbarTime');
  const update = () => {
    const now = new Date();
    const datePart = now.toLocaleDateString('id-ID', { weekday: 'long', day: '2-digit', month: 'long', year: 'numeric' });
    const timePart = now.toLocaleTimeString('id-ID', { hour: '2-digit', minute: '2-digit' }).replace(/\./g, ':');
    el.textContent = `${datePart} - ${timePart}`;
  };
  update(); setInterval(update, 1000);
  
  // Auto update incident badge every 15 seconds
  updateIncidentBadge();
  setInterval(updateIncidentBadge, 15000);

  // Auto refresh halaman yang sedang dibuka setiap 10 detik
  setInterval(refreshActivePage, 10000);
}

function refreshActivePage() {
  const activePage = document.querySelector('.nav-item.active');
  if (!activePage) return;
  const pageId = activePage.dataset.page;
  
  const loaders = {
    dashboard: loadDashboard, tickets: loadTickets, 
    sites: loadSites, devices: loadDevices,
    incidents: loadIncidents, audit: loadAuditLogs,
    tier1: loadTier1Diagnostics, telegram: loadTelegramLogs,
    workflow: loadWorkflowStatus, zammad: loadZammadStatus,
    users: loadUsers,
  };
  
  if (loaders[pageId]) loaders[pageId]();
}

async function updateIncidentBadge() {
  const data = await apiFetch('/api/incidents/', {}, true);
  if (!data?.incidents) return;
  
  const total = data.incidents.length;
  const lastSeen = parseInt(localStorage.getItem('last_incident_count') || '0', 10);
  const badge = document.getElementById('badge-incidents');
  
  if (badge) {
    const newCount = total - lastSeen;
    if (newCount > 0 && !document.getElementById('page-incidents').classList.contains('active')) {
      badge.textContent = newCount;
      badge.style.display = 'inline-flex';
    } else {
      badge.style.display = 'none';
    }
  }
}

// ─── API HELPER ───────────────────────────────
async function apiFetch(path, opts = {}, skipAuthRedirect = false) {
  try {
    const token = localStorage.getItem('mkt_token');
    const headers = { 'Content-Type': 'application/json' };
    if (token) headers['Authorization'] = `Bearer ${token}`;
    const res = await fetch(API + path, { headers, ...opts });
    if (res.status === 401 && !skipAuthRedirect) {
      localStorage.removeItem('mkt_token');
      showLoginPage();
      return null;
    }
    if (!res.ok) {
      try { return await res.json(); } catch(e) { throw new Error(`HTTP ${res.status}`); }
    }
    return await res.json();
  } catch (e) {
    console.warn('[API]', path, e.message);
    return null;
  }
}

// ─── DASHBOARD ────────────────────────────────
async function loadDashboard() {
  const [overview, severity, category, trend, siteHealth, recent] = await Promise.all([
    apiFetch('/api/dashboard/overview'),
    apiFetch('/api/dashboard/tickets-by-severity'),
    apiFetch('/api/dashboard/tickets-by-category'),
    apiFetch('/api/dashboard/confidence-trend'),
    apiFetch('/api/dashboard/site-health'),
    apiFetch('/api/dashboard/recent-tickets'),
  ]);

  if (overview) {
    document.getElementById('kpi-open').textContent = overview.open_tickets ?? '—';
    document.getElementById('kpi-sla').textContent = overview.sla_breached ?? '—';
    document.getElementById('kpi-auto').textContent = (overview.auto_resolution_rate ?? '—') + '%';
    document.getElementById('kpi-mttr').textContent = overview.mttr_minutes ? overview.mttr_minutes + ' min' : '—';
    document.getElementById('kpi-devices').textContent = `${overview.online_devices ?? '—'}/${overview.total_devices ?? 72}`;
    document.getElementById('kpi-today').textContent = overview.tickets_today ?? '—';
    document.getElementById('kpi-resolved-today').textContent = `${overview.resolved_today ?? 0} diselesaikan`;
    document.getElementById('badge-open').textContent = overview.open_tickets ?? 0;
  }


  if (siteHealth) renderSiteGrid(siteHealth.sites || []);
  if (recent) renderRecentTickets(recent.tickets || []);
}



// ─── SITE GRID ────────────────────────────────
function renderSiteGrid(sites) {
  const grid = document.getElementById('siteGrid');
  if (!sites.length) { grid.innerHTML = '<div class="loading-state">Belum ada data site.</div>'; return; }
  grid.innerHTML = sites.map(s => {
    const pct = s.health_pct || 0;
    const cls = pct >= 75 ? 'health-ok' : pct >= 50 ? 'health-warn' : 'health-bad';
    const color = pct >= 75 ? '#94a3b8' : pct >= 50 ? '#991b1b' : '#dc2626';
    return `<div class="site-card ${cls}">
      <div class="site-card-top">
        <div><div class="site-name">${s.site_name}</div><div class="site-city">📍 ${s.city}</div></div>
        <div class="site-health-pct" style="color:${color}">${pct}%</div>
      </div>
      <div class="site-health-bar"><div class="site-health-fill" style="width:${pct}%;background:${color}"></div></div>
      <div class="site-stats">
        <span>🟢 ${s.online} online</span>
        <span>🔴 ${s.offline} offline</span>
        <span>📦 ${s.total_devices} total</span>
      </div>
    </div>`;
  }).join('');
}

// ─── RECENT TICKETS ───────────────────────────
function renderRecentTickets(tickets) {
  const tbody = document.getElementById('recentTicketsBody');
  if (!tickets.length) { tbody.innerHTML = '<tr><td colspan="7" class="loading-state">Belum ada tiket.</td></tr>'; return; }
  tbody.innerHTML = tickets.map(t => `
    <tr style="cursor:pointer" onclick="openTicketDetail('${t.ticket_id}')">
      <td><code style="color:#dc2626">#${t.zammad_ticket_id || t.ticket_id.slice(0,8)}</code></td>
      <td style="max-width:220px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${t.title}</td>
      <td>${t.site_id ? '📍 Site' : '—'}</td>
      <td>${severityBadge(t.severity)}</td>
      <td>${statusBadge(t.status)}</td>
      <td>${confBar(t.confidence_score)}</td>
      <td style="color:#8892b0;font-size:11px">${timeAgo(t.created_at)}</td>
    </tr>`).join('');
}

// ─── TICKETS PAGE ─────────────────────────────
async function loadTickets() {
  const status = document.getElementById('filterStatus')?.value || '';
  const severity = document.getElementById('filterSeverity')?.value || '';
  const params = new URLSearchParams();
  if (status) params.append('status', status);
  if (severity) params.append('severity', severity);
  const data = await apiFetch('/api/tickets/?' + params);
  const tbody = document.getElementById('ticketsBody');
  if (!data?.tickets?.length) { tbody.innerHTML = '<tr><td colspan="9" class="loading-state">Tidak ada tiket.</td></tr>'; return; }
  tbody.innerHTML = data.tickets.map(t => `
    <tr style="cursor:pointer" onclick="openTicketDetail('${t.ticket_id}')">
      <td><code style="color:#dc2626">#${t.zammad_ticket_id || t.ticket_id.slice(0,8)}</code></td>
      <td style="max-width:200px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${t.title}</td>
      <td>—</td>
      <td>${severityBadge(t.severity)}</td>
      <td>${statusBadge(t.status)}</td>
      <td><span class="badge badge-medium">Tier ${t.tier_level}</span></td>
      <td>${confBar(t.confidence_score)}</td>
      <td style="color:#8892b0;font-size:11px">${timeAgo(t.created_at)}</td>
      <td>
        <button class="btn-info" onclick="event.stopPropagation();triggerAIForTicket('${t.ticket_id}')">🤖 AI</button>
        ${t.live_chat_requested ? `<button class="btn-primary" style="background:#dc2626; border:none; margin-left:4px" onclick="event.stopPropagation();openLiveChat('${t.ticket_id}')">💬 Chat</button>` : ''}
      </td>
    </tr>`).join('');
}

// ─── SITES PAGE ───────────────────────────────
async function loadSites() {
  const data = await apiFetch('/api/sites/');
  const grid = document.getElementById('sitesCards');
  if (!data?.sites?.length) { grid.innerHTML = '<div class="loading-state">Tidak ada site.</div>'; return; }
  grid.innerHTML = data.sites.map(s => {
    // Safely encode JSON for inline HTML attribute
    const escapedSite = JSON.stringify(s).replace(/"/g, '&quot;').replace(/'/g, "\\'");
    const safeName = s.site_name.replace(/'/g, "\\'");
    return `
    <div class="site-detail-card">
      <div class="sdc-header" style="display:flex; justify-content:space-between; width:100%">
        <div style="display:flex; align-items:center; gap:12px;">
          <div class="sdc-icon">🏢</div>
          <div><div class="sdc-name">${s.site_name}</div><div class="sdc-city">📍 ${s.city}</div></div>
        </div>
        <div style="display:flex; gap:8px;">
          <button class="btn-primary" style="padding:4px 8px; font-size:12px" onclick="showEditSiteModal('${s.site_id}', ${escapedSite})">✏️</button>
          <button class="btn-danger" style="padding:4px 8px; font-size:12px" onclick="deleteSite('${s.site_id}', '${safeName}')">🗑️</button>
        </div>
      </div>
      <div class="sdc-info">
        <span>👤 PIC: ${s.pic_primary || '—'}</span>
        <span>📱 ${s.pic_primary_phone || '—'}</span>
        <span>🕐 TZ: ${s.timezone}</span>
        <span>💬 TG: ${s.telegram_group_id || 'Belum dikonfigurasi'}</span>
        <span>📦 Perangkat: ${s.device_count || 0} unit</span>
      </div>
    </div>`;
  }).join('');
}

// ─── SITES CRUD MODAL ─────────────────────────
function showAddSiteModal() {
  document.getElementById('siteIdField').value = '';
  document.getElementById('siteName').value = '';
  document.getElementById('siteCity').value = '';
  document.getElementById('siteTimezone').value = 'Asia/Jakarta';
  document.getElementById('siteTelegram').value = '';
  document.getElementById('sitePicPrimary').value = '';
  document.getElementById('sitePicPhone').value = '';
  document.getElementById('siteModalTitle').textContent = 'Tambah Site';
  document.getElementById('siteModalOverlay').classList.add('show');
  document.getElementById('siteModal').classList.add('show');
}

function showEditSiteModal(siteId, siteObj) {
  document.getElementById('siteIdField').value = siteId;
  document.getElementById('siteName').value = siteObj.site_name || '';
  document.getElementById('siteCity').value = siteObj.city || '';
  document.getElementById('siteTimezone').value = siteObj.timezone || 'Asia/Jakarta';
  document.getElementById('siteTelegram').value = siteObj.telegram_group_id || '';
  document.getElementById('sitePicPrimary').value = siteObj.pic_primary || '';
  document.getElementById('sitePicPhone').value = siteObj.pic_primary_phone || '';
  document.getElementById('siteModalTitle').textContent = 'Edit Site';
  document.getElementById('siteModalOverlay').classList.add('show');
  document.getElementById('siteModal').classList.add('show');
}

function closeSiteModal() {
  document.getElementById('siteModalOverlay').classList.remove('show');
  document.getElementById('siteModal').classList.remove('show');
}

async function saveSite() {
  const siteId = document.getElementById('siteIdField').value;
  const payload = {
    site_name: document.getElementById('siteName').value.trim(),
    city: document.getElementById('siteCity').value.trim(),
    timezone: document.getElementById('siteTimezone').value,
    telegram_group_id: document.getElementById('siteTelegram').value.trim(),
    pic_primary: document.getElementById('sitePicPrimary').value.trim(),
    pic_primary_phone: document.getElementById('sitePicPhone').value.trim()
  };

  if (!payload.site_name || !payload.city) {
    showToast('Nama Site dan Kota wajib diisi!', 'error');
    return;
  }

  const method = siteId ? 'PUT' : 'POST';
  const url = siteId ? `/api/sites/${siteId}` : '/api/sites/';
  
  const res = await apiFetch(url, {
    method,
    body: JSON.stringify(payload)
  });

  if (res && !res.detail) {
    showToast(`Site berhasil di${siteId ? 'perbarui' : 'tambahkan'}!`, 'success');
    closeSiteModal();
    loadSites();
  } else {
    showToast(`Gagal menyimpan site: ${res?.detail || 'Error'}`, 'error');
  }
}

async function deleteSite(siteId, siteName) {
  if (!confirm(`Apakah Anda yakin ingin menghapus site ${siteName}?\nPerangkat yang terhubung harus dipindahkan/dihapus terlebih dahulu.`)) return;
  
  const res = await apiFetch(`/api/sites/${siteId}`, { method: 'DELETE' });
  if (res && !res.detail) {
    showToast('Site berhasil dihapus', 'success');
    loadSites();
  } else {
    showToast(`Gagal menghapus site: ${res?.detail || 'Error'}`, 'error');
  }
}


// ─── DEVICES PAGE ─────────────────────────────
async function loadDevices() {
  const type = document.getElementById('filterDeviceType')?.value || '';
  const status = document.getElementById('filterDeviceStatus')?.value || '';
  const params = new URLSearchParams();
  if (type) params.append('device_type', type);
  if (status) params.append('status', status);
  const data = await apiFetch('/api/devices/?' + params);
  const tbody = document.getElementById('devicesBody');
  if (!data?.devices?.length) { tbody.innerHTML = '<tr><td colspan="9" class="loading-state">Tidak ada perangkat.</td></tr>'; return; }
  tbody.innerHTML = data.devices.map(d => `
    <tr>
      <td>
        <strong>${d.device_name}</strong>
        <div style="font-size:10px; color:#8892b0; font-family:monospace; margin-top:4px;">ID: ${d.device_id}</div>
      </td>
      <td>
        <span style="color:${d.site_name ? '#8892b0' : '#dc2626'}; font-size:12px;">
          📍 ${d.site_name || 'Tanpa Site'}
        </span>
      </td>
      <td><span class="badge badge-medium">${d.device_type}</span></td>
      <td><code style="color:#94a3b8">${d.ip_address || '—'}</code></td>
      <td style="color:#8892b0">${d.operating_system || '—'} ${d.os_version || ''}</td>
      <td>
        <div style="font-size:11px; margin-bottom:4px">CPU: <strong>${d.status === 'OFFLINE' ? '—' : (d.cpu_usage ? d.cpu_usage.toFixed(1) + '%' : '—')}</strong></div>
        <div style="font-size:11px; margin-bottom:4px">RAM: <strong>${d.status === 'OFFLINE' ? '—' : (d.ram_usage ? d.ram_usage.toFixed(1) + '%' : '—')}</strong></div>
        <div style="font-size:11px; margin-bottom:4px">Disk: <strong>${d.status === 'OFFLINE' ? '—' : formatDiskStorage(d.disk_free_gb, d.disk_total_gb)}</strong></div>
        <div style="font-size:11px">Suhu: <strong>${d.status === 'OFFLINE' ? '—' : (d.temperature ? d.temperature.toFixed(1) + '°C' : '—')}</strong></div>
      </td>
      <td>
        <div style="font-size:11px; margin-bottom:4px; max-width:150px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;" title="${d.current_active_app || ''}">App: <span style="color:#a855f7">${d.status === 'OFFLINE' ? '—' : (d.current_active_app || '—')}</span></div>
        <div style="font-size:11px; max-width:150px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;" title="${d.current_active_url || ''}">URL: <span style="color:#dc2626;">${d.status === 'OFFLINE' ? '—' : (d.current_active_url || '—')}</span></div>
      </td>
      <td>${deviceStatusBadge(d.status)}</td>
      <td>
        ${d.unread_port_logs > 0 
          ? `<div style="cursor:pointer; display:inline-flex; align-items:center; gap:5px; background:rgba(239,68,68,0.15); color:#fca5a5; padding:4px 10px; border-radius:20px; font-weight:600; font-size:11px; border:1px solid rgba(239,68,68,0.3); box-shadow:0 0 8px rgba(239,68,68,0.2); white-space:nowrap; transition:all 0.2s ease;" onmouseover="this.style.background='rgba(239,68,68,0.25)'; this.style.boxShadow='0 0 12px rgba(239,68,68,0.4)';" onmouseout="this.style.background='rgba(239,68,68,0.15)'; this.style.boxShadow='0 0 8px rgba(239,68,68,0.2)';" onclick="openPortCheckerModal('${d.device_id}', '${d.device_name.replace(/'/g, "\\'")}')"><span style="font-size:12px;">🚨</span> ${d.unread_port_logs} Terputus</div>` 
          : `<div style="cursor:pointer; display:inline-flex; align-items:center; gap:5px; background:rgba(16,185,129,0.15); color:#6ee7b7; padding:4px 10px; border-radius:20px; font-weight:600; font-size:11px; border:1px solid rgba(16,185,129,0.3); white-space:nowrap; transition:all 0.2s ease;" onmouseover="this.style.background='rgba(16,185,129,0.25)'; this.style.boxShadow='0 0 12px rgba(16,185,129,0.3)';" onmouseout="this.style.background='rgba(16,185,129,0.15)'; this.style.boxShadow='none';" onclick="openPortCheckerModal('${d.device_id}', '${d.device_name.replace(/'/g, "\\'")}')"><span style="font-size:12px;">✅</span> Aman</div>`}
      </td>
      <td style="color:#8892b0;font-size:11px">${d.last_health_check ? timeAgo(d.last_health_check) : (d.last_ping ? timeAgo(d.last_ping) : '—')}</td>
      <td>
        <div class="action-buttons-grid">
          <button class="btn-success" onclick="pingDevice('${d.device_id}', '${d.ip_address || ''}', this)">📡 Ping</button>
          <button class="btn-primary" onclick="openHistoryModal('${d.device_id}', '${d.device_name.replace(/'/g, "\\'")}')">📜 Log</button>
          <button class="btn-primary" onclick="showEditDeviceModal('${d.device_id}', '${d.site_id || ''}', '${d.device_type}')">✏️ Edit</button>
          <button class="btn-danger" onclick="deleteDevice('${d.device_id}', '${d.device_name.replace(/'/g, "\\'")}')">🗑️ Hapus</button>
        </div>
      </td>
    </tr>`).join('');
}

// ─── PING DEVICE ─────────────────────────────
let currentPingSource = null;

function clearPingTerminal() {
  document.getElementById('pingTerminal').innerHTML = 'Menunggu perintah ping...';
}

function closePingTerminal() {
  if (currentPingSource) {
    currentPingSource.close();
  }
  document.getElementById('floatingTerminal').style.display = 'none';
}

async function pingDevice(deviceId, ipAddress, btn) {
  if (!ipAddress) {
    return showToast('IP Address tidak valid/kosong.', 'error');
  }
  
  btn.textContent = '⏳...';
  btn.disabled = true;
  
  // Tampilkan Terminal Mengambang
  const floatingTerm = document.getElementById('floatingTerminal');
  floatingTerm.style.display = 'block';
  
  const terminal = document.getElementById('pingTerminal');
  terminal.innerHTML = `Mulai Real-Time Ping ke ${ipAddress}...\n`;
  
  if (currentPingSource) {
    currentPingSource.close();
  }
  
  // Connect to SSE stream
  const url = `${API}/api/tier1/stream_ping?host=${encodeURIComponent(ipAddress)}`;
  currentPingSource = new EventSource(url);
  
  currentPingSource.onmessage = function(event) {
    if (event.data === "[PROCESS_COMPLETED]") {
      currentPingSource.close();
      btn.textContent = '📡 Ping';
      btn.disabled = false;
      terminal.innerHTML += `\n[Ping selesai]`;
      terminal.scrollTop = terminal.scrollHeight;
      return;
    }
    
    // Add new line to terminal
    terminal.innerHTML += event.data + '\n';
    terminal.scrollTop = terminal.scrollHeight; // Auto-scroll to bottom
  };
  
  currentPingSource.onerror = function() {
    currentPingSource.close();
    btn.textContent = '📡 Ping';
    btn.disabled = false;
    terminal.innerHTML += `\n[Koneksi streaming terputus]`;
  };
  
  // Jalankan juga ping API lama untuk update status DB
  apiFetch(`/api/devices/${deviceId}/ping`, { method: 'POST' }).then(() => {
    loadDevices();
  });
}

// ─── DEVICE CRUD ─────────────────────────────
let editingDeviceId = null;

async function populateSiteDropdowns(selectedSiteId = null, targetSelectId = 'addDeviceSiteId') {
  const selectEl = document.getElementById(targetSelectId);
  if (!selectEl) return;
  selectEl.innerHTML = '<option value="">Memuat daftar site...</option>';
  try {
    const data = await apiFetch('/api/sites/');
    if (data?.sites?.length) {
      selectEl.innerHTML = '<option value="">-- Pilih Site --</option>' + data.sites.map(s => 
        `<option value="${s.site_id}" ${s.site_id === selectedSiteId ? 'selected' : ''}>${s.site_name}</option>`
      ).join('');
    } else {
      selectEl.innerHTML = '<option value="">Belum ada Site terdaftar</option>';
    }
  } catch(e) {
    selectEl.innerHTML = '<option value="">Gagal memuat site</option>';
  }
}

function showNewDeviceModal() {
  document.getElementById('addDeviceSiteId').value = '';
  document.getElementById('addDeviceName').value = '';
  document.getElementById('addDeviceType').value = 'POS_TICKETING';
  document.getElementById('addDeviceIp').value = '';
  document.getElementById('addDeviceOs').value = '';
  
  populateSiteDropdowns(null, 'addDeviceSiteId');
  document.getElementById('newDeviceModal').classList.add('show');
  document.getElementById('modalOverlay').classList.add('show');
}

function showEditDeviceModal(id, site_id, type) {
  editingDeviceId = id;
  populateSiteDropdowns(site_id, 'editDeviceSiteId');
  document.getElementById('editDeviceType').value = type || 'POS_TICKETING';
  
  document.getElementById('editDeviceModal').classList.add('show');
  document.getElementById('modalOverlay').classList.add('show');
}

function closeDeviceModal() {
  document.getElementById('newDeviceModal').classList.remove('show');
  document.getElementById('editDeviceModal').classList.remove('show');
  document.getElementById('modalOverlay').classList.remove('show');
  editingDeviceId = null;
}

async function submitNewDevice() {
  const site_id = document.getElementById('addDeviceSiteId').value;
  const device_name = document.getElementById('addDeviceName').value;
  const device_type = document.getElementById('addDeviceType').value;
  const ip_address = document.getElementById('addDeviceIp').value;
  const operating_system = document.getElementById('addDeviceOs').value;

  if (!site_id || !device_name) return showToast('Site ID dan Nama Device wajib diisi', 'warning');

  const res = await apiFetch('/api/devices/', {
    method: 'POST',
    body: JSON.stringify({ site_id, device_name, device_type, ip_address, operating_system }),
  });

  if (res?.device_id) {
    closeDeviceModal();
    showToast('Perangkat berhasil ditambahkan', 'success');
    loadDevices();
  } else {
    showToast(res?.detail || 'Gagal menambahkan perangkat', 'error');
  }
}

async function submitEditDevice() {
  if (!editingDeviceId) return;
  const site_id = document.getElementById('editDeviceSiteId').value;
  const device_type = document.getElementById('editDeviceType').value;

  const res = await apiFetch(`/api/devices/${editingDeviceId}`, {
    method: 'PUT',
    body: JSON.stringify({ site_id, device_type }),
  });

  if (res?.device_id) {
    closeDeviceModal();
    showToast('Perangkat berhasil diperbarui', 'success');
    loadDevices();
  } else {
    showToast('Gagal memperbarui perangkat', 'error');
  }
}

async function deleteDevice(id, name) {
  if (!confirm(`Yakin ingin menghapus perangkat '${name}'?`)) return;
  const res = await apiFetch(`/api/devices/${id}`, { method: 'DELETE' });
  if (res?.message) {
    showToast('Perangkat berhasil dihapus', 'success');
    loadDevices();
  } else {
    showToast('Gagal menghapus perangkat', 'error');
  }
}

// ─── INCIDENTS PAGE ───────────────────────────
async function loadIncidents() {
  const data = await apiFetch('/api/incidents/');
  const tbody = document.getElementById('incidentsBody');
  const badge = document.getElementById('badge-incidents');
  
  if (data?.incidents) {
    localStorage.setItem('last_incident_count', data.incidents.length);
    if (badge) badge.style.display = 'none';
  }

  if (!data?.incidents?.length) { tbody.innerHTML = '<tr><td colspan="6" class="loading-state">Belum ada incident memory.</td></tr>'; return; }
  tbody.innerHTML = data.incidents.map(i => `
    <tr>
      <td style="font-size:11px;color:#8892b0;white-space:nowrap">${formatLocalTime(i.created_at)}</td>
      <td style="max-width:200px">${i.summary || '—'}</td>
      <td style="max-width:180px;color:#8892b0">${i.root_cause || '—'}</td>
      <td>${i.site_name || '—'}</td>
      <td>${i.category ? `<span class="badge badge-medium">${i.category}</span>` : '—'}</td>
      <td><span class="badge badge-medium">Tier ${i.tier_resolved ?? 0}</span></td>
    </tr>`).join('');
}

// ─── AUDIT LOG PAGE ───────────────────────────
async function loadAuditLogs() {
  const data = await apiFetch('/api/incidents/audit-logs/');
  const tbody = document.getElementById('auditBody');
  if (!data?.logs?.length) { tbody.innerHTML = '<tr><td colspan="6" class="loading-state">Belum ada audit log.</td></tr>'; return; }
  tbody.innerHTML = data.logs.map(l => `
    <tr>
      <td style="font-size:11px;color:#8892b0;white-space:nowrap">${formatLocalTime(l.created_at)}</td>
      <td><code style="color:#a855f7">${l.actor}</code></td>
      <td><code style="color:#dc2626">${l.action}</code></td>
      <td style="color:#8892b0">${l.target || '—'}</td>
      <td>${resultBadge(l.result)}</td>
      <td style="max-width:200px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;color:#8892b0;font-size:11px">${l.detail || '—'}</td>
    </tr>`).join('');
}

// ─── TICKET DETAIL MODAL ──────────────────────
async function openTicketDetail(ticketId) {
  currentTicketId = ticketId;
  const t = await apiFetch(`/api/tickets/${ticketId}`);
  if (!t) { showToast('Gagal memuat detail tiket', 'error'); return; }

  document.getElementById('detailTitle').textContent = `🎫 ${t.title}`;
  document.getElementById('detailBody').innerHTML = `
    <div class="detail-section">
      <h4>Informasi Tiket</h4>
      <div class="detail-grid">
        <div class="detail-item"><label>ID</label><span><code style="color:#dc2626">#${t.zammad_ticket_id || t.ticket_id.slice(0,8)}</code></span></div>
        <div class="detail-item"><label>Status</label><span>${statusBadge(t.status)}</span></div>
        <div class="detail-item"><label>Severity</label><span>${severityBadge(t.severity)}</span></div>
        <div class="detail-item"><label>Kategori</label><span>${t.category || '—'}</span></div>
        <div class="detail-item"><label>Pelapor</label><span>${t.reporter_name || '—'}</span></div>
        <div class="detail-item"><label>Dibuat</label><span style="font-size:11px">${formatLocalTime(t.created_at)}</span></div>
      </div>
    </div>
    <div class="detail-section">
      <h4>Deskripsi Masalah</h4>
      <div class="detail-text">${t.description || '—'}</div>
    </div>
    <div class="detail-section">
      <h4>Analisis AI — Tier ${t.tier_level}</h4>
      <div class="detail-grid" style="margin-bottom:10px">
        <div class="detail-item"><label>Confidence Score</label><span>${confBar(t.confidence_score)}</span></div>
        <div class="detail-item"><label>SOP Reference</label><span style="color:#94a3b8">${t.sop_reference || '—'}</span></div>
        <div class="detail-item"><label>Eskalasi</label><span>${t.escalated ? '✅ Ya' : '❌ Tidak'}</span></div>
        <div class="detail-item"><label>SLA Breached</label><span style="color:${t.sla_breached ? '#dc2626' : '#94a3b8'}">${t.sla_breached ? '⚠️ Ya' : '✅ Tidak'}</span></div>
      </div>
      <div class="detail-text" style="margin-bottom:8px">${t.ai_analysis || 'Belum dianalisis AI.'}</div>
    </div>
    ${t.ai_recommendation ? `<div class="detail-section">
      <h4>Rekomendasi AI</h4>
      <div class="detail-text" style="border-left:3px solid #94a3b8">${t.ai_recommendation}</div>
    </div>` : ''}
    ${t.resolution ? `<div class="detail-section">
      <h4>Resolusi</h4>
      <div class="detail-text" style="border-left:3px solid #dc2626">${t.resolution}</div>
    </div>` : ''}
    ${t.live_chat_requested ? `<div class="detail-section" style="margin-top:15px">
      <button class="btn-primary" style="width:100%; background:#dc2626; border:none; padding:12px; font-size:14px;" onclick="openLiveChat('${t.ticket_id}')">💬 Buka Live Chat</button>
    </div>` : ''}`;

  document.getElementById('modalOverlay').classList.add('show');
  document.getElementById('ticketDetailModal').classList.add('show');
}

function closeDetailModal() {
  document.getElementById('modalOverlay').classList.remove('show');
  document.getElementById('ticketDetailModal').classList.remove('show');
  currentTicketId = null;
}

async function triggerAI() {
  if (!currentTicketId) return;
  await triggerAIForTicket(currentTicketId);
}

async function triggerAIForTicket(ticketId) {
  showToast('🤖 AI processing dimulai...', 'info');
  document.getElementById('btnProcessAI').disabled = true;
  document.getElementById('btnProcessAI').textContent = 'Sedang diproses...';
  const res = await apiFetch(`/api/tickets/${ticketId}/process`, { method: 'POST' });
  if (res) {
    showToast('✅ AI sedang menganalisis...', 'success');
    // Reload ticket details automatically after 4.5s (simulated AI processing delay)
    setTimeout(() => {
      if (currentTicketId === ticketId) {
         openTicketDetail(ticketId);
         loadTickets();
      }
      document.getElementById('btnProcessAI').disabled = false;
      document.getElementById('btnProcessAI').textContent = '🤖 Proses ulang AI';
    }, 4500);
  } else {
    showToast('Gagal memulai AI processing', 'error');
    document.getElementById('btnProcessAI').disabled = false;
    document.getElementById('btnProcessAI').textContent = '🤖 Proses ulang AI';
  }
}

function formatLocalTime(isoStr) {
  if (!isoStr) return '—';
  try {
    const d = new Date(isoStr + (isoStr.endsWith('Z') ? '' : 'Z'));
    return d.toLocaleString('id-ID', { year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' }).replace(/\./g, ':');
  } catch(e) { return isoStr.replace('T',' ').slice(0,16); }
}

// ─── NEW TICKET MODAL ─────────────────────────
function showNewTicketModal() {
  document.getElementById('modalOverlay').classList.add('show');
  document.getElementById('newTicketModal').classList.add('show');
}

function closeModal() {
  document.getElementById('modalOverlay').classList.remove('show');
  document.getElementById('newTicketModal').classList.remove('show');
  document.getElementById('ticketDetailModal').classList.remove('show');
}

async function submitNewTicket() {
  const title = document.getElementById('newTitle').value.trim();
  const desc = document.getElementById('newDesc').value.trim();
  if (!title || !desc) { showToast('Judul dan deskripsi wajib diisi!', 'error'); return; }

  const payload = {
    title, description: desc,
    reporter_name: document.getElementById('newReporter').value,
    severity: document.getElementById('newSeverity').value,
    zammad_ticket_id: document.getElementById('newZammadId').value || null,
  };
  const res = await apiFetch('/api/tickets/', { method: 'POST', body: JSON.stringify(payload) });
  if (res) {
    closeModal();
    showToast('✅ Tiket dibuat & dikirim ke AI Tier 0!', 'success');
    ['newTitle','newDesc','newReporter','newZammadId'].forEach(id => document.getElementById(id).value = '');
    loadDashboard();
  } else showToast('Gagal membuat tiket', 'error');
}

// ─── HELPER FUNCTIONS ─────────────────────────
function severityBadge(s) {
  const map = { CRITICAL:'badge-critical', HIGH:'badge-high', MEDIUM:'badge-medium', LOW:'badge-low' };
  const icons = { CRITICAL:'🔴', HIGH:'🟠', MEDIUM:'🟡', LOW:'🟢' };
  return `<span class="badge ${map[s]||'badge-medium'}">${icons[s]||'⚪'} ${s||'—'}</span>`;
}

function statusBadge(s) {
  const map = {
    NEW:'badge-new', ANALYZING:'badge-analyzing', TIER0_PROCESSING:'badge-analyzing',
    TIER1_PROCESSING:'badge-analyzing', ESCALATED:'badge-escalated',
    WAITING_INFO:'badge-waiting', RESOLVED:'badge-resolved', CLOSED:'badge-resolved'
  };
  const labels = {
    NEW:'Baru', ANALYZING:'Menganalisis', TIER0_PROCESSING:'Klasifikasi Awal',
    TIER1_PROCESSING:'Diproses AI', ESCALATED:'Eskalasi',
    WAITING_INFO:'Menunggu Info', RESOLVED:'Selesai', CLOSED:'Selesai'
  };
  return `<span class="badge ${map[s]||'badge-new'}">${labels[s]||s||'—'}</span>`;
}

function deviceStatusBadge(s) {
  const map = { ONLINE:'badge-online', OFFLINE:'badge-offline', MAINTENANCE:'badge-waiting', UNKNOWN:'badge-unknown' };
  return `<span class="badge ${map[s]||'badge-unknown'}">${s||'UNKNOWN'}</span>`;
}

function resultBadge(r) {
  if (!r) return '—';
  const map = { SUCCESS:'badge-resolved', FAILED:'badge-escalated', ESCALATED:'badge-waiting' };
  return `<span class="badge ${map[r]||'badge-medium'}">${r}</span>`;
}

function confBar(score) {
  const pct = Math.round(score || 0);
  const color = pct >= 85 ? '#94a3b8' : pct >= 60 ? '#991b1b' : '#dc2626';
  return `<div class="conf-bar">
    <div class="conf-track"><div class="conf-fill" style="width:${pct}%;background:${color}"></div></div>
    <span class="conf-label" style="color:${color}">${pct}%</span>
  </div>`;
}

function timeAgo(iso) {
  if (!iso) return '—';
  const d = new Date(iso + (iso.endsWith('Z') ? '' : 'Z'));
  let diff = (Date.now() - d.getTime()) / 1000;
  diff = Math.max(0, diff); // prevent negative if clock skewed
  if (diff < 60) return `${Math.round(diff)} detik lalu`;
  if (diff < 3600) return `${Math.round(diff/60)} mnt lalu`;
  if (diff < 86400) return `${Math.round(diff/3600)} jam lalu`;
  return `${Math.round(diff/86400)} hari lalu`;
}

function formatDiskStorage(freeGb, totalGb) {
  if (totalGb == null || freeGb == null) return '—';
  const usedGb = totalGb - freeGb;
  const pct = totalGb > 0 ? Math.round((usedGb / totalGb) * 100) : 0;
  const formatSize = (gb) => {
    if (gb >= 1024) return (gb / 1024).toFixed(2) + 'TB';
    return Math.round(gb) + 'GB';
  };
  return `${pct}% (${formatSize(usedGb)}/${formatSize(totalGb)})`;
}

function showToast(msg, type = 'info') {
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.className = `toast show ${type}`;
  setTimeout(() => { t.className = 'toast'; }, 3500);
}

function filterTickets() {
  const q = document.getElementById('ticketSearch').value.toLowerCase();
  document.querySelectorAll('#ticketsBody tr').forEach(row => {
    row.style.display = row.textContent.toLowerCase().includes(q) ? '' : 'none';
  });
}

function loadSiteHealth() { loadDashboard(); showToast('Data site diperbarui', 'info'); }

// ─── WORKFLOW STATUS (11 Steps) ───────────────────────────────
async function loadWorkflowStatus() {
  const data = await apiFetch('/api/workflow/status');
  const el = document.getElementById('workflowSteps');
  if (!data?.steps) { el.innerHTML = '<div class="loading-state">Gagal memuat workflow.</div>'; return; }
  el.innerHTML = data.steps.map(s => `
    <div class="workflow-step">
      <div class="step-num">${s.step}</div>
      <div class="step-body">
        <div class="step-title">${s.name}</div>
        <div class="step-desc">${s.description}</div>
        <div class="step-meta">
          <div class="step-count">${s.count}</div>
          <div class="step-count-label">records terkait</div>
          <span class="badge badge-resolved" style="margin-left:auto">✅ Aktif</span>
        </div>
      </div>
    </div>`).join('');
}

// ─── TIER 1 DIAGNOSTIC VIEW ───────────────────────────────────
async function loadTier1Diagnostics() {
  const data = await apiFetch('/api/tier1/active-diagnostics');
  const el = document.getElementById('tier1Cards');
  if (!data?.active_diagnostics?.length) {
    el.innerHTML = '<div class="loading-state">Tidak ada diagnosis Tier 1 aktif saat ini.</div>'; return;
  }
  const diagClass = { PING_OK:'diag-ok', PORT_OPEN:'diag-ok', SSH_CONNECTED:'diag-info',
    LOG_COLLECTING:'diag-warn', PENDING:'diag-pend' };
  el.innerHTML = data.active_diagnostics.map(d => `
    <div class="diag-card">
      <div class="diag-card-top">
        <div>
          <div class="diag-title">🔬 ${d.title}</div>
          <div class="diag-site">📍 ${d.site_name} · Ticket #${d.zammad_ticket_id}</div>
        </div>
        <div>${severityBadge(d.severity)} ${statusBadge(d.status)}</div>
      </div>
      <div style="font-size:12px;color:var(--text-secondary);margin-bottom:10px">
        <strong>Sesuai diagram:</strong> Tier 1 Agent terhubung langsung ke 4 POS devices via SSH/Ping:
      </div>
      <div class="pos-devices-grid">
        ${d.devices.map(dev => `
          <div class="pos-device">
            <div class="pos-device-name">${dev.device_name.split('—')[0].trim()}</div>
            <div class="pos-device-ip">${dev.ip_address}</div>
            <span class="badge ${dev.status === 'ONLINE' ? 'badge-online' : 'badge-offline'}" style="font-size:10px">${dev.status}</span>
            <div style="margin-top:6px">
              <span class="diag-status ${diagClass[dev.diagnostic_status]||'diag-pend'}">${dev.diagnostic_status}</span>
            </div>
          </div>`).join('')}
      </div>
    </div>`).join('');
}

// ─── TELEGRAM NOTIFICATION LOG ────────────────────────────────
async function loadTelegramLogs() {
  const data = await apiFetch('/api/telegram/logs?t=' + Date.now());
  const tbody = document.getElementById('telegramBody');
  if (!data?.logs?.length) { tbody.innerHTML = '<tr><td colspan="8" class="loading-state">Tidak ada log Telegram.</td></tr>'; return; }
  tbody.innerHTML = data.logs.map(l => `
    <tr>
      <td style="font-size:11px;color:#8892b0;white-space:nowrap">${l.sent_at.replace('T',' ').slice(0,16)}</td>
      <td><code style="color:#dc2626">#${l.ticket_id}</code></td>
      <td>${l.site_name}</td>
      <td><code style="font-size:11px;color:#a855f7">${l.telegram_group}</code></td>
      <td>${severityBadge(l.severity)}</td>
      <td><span class="badge ${l.sent_by==='Tier1Agent'?'badge-escalated':'badge-analyzing'}">${l.sent_by}</span></td>
      <td style="max-width:200px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-size:12px">${l.message_preview}</td>
      <td><span class="badge ${l.delivered?'badge-resolved':'badge-escalated'}">${l.delivered?'✅ Terkirim':'❌ Gagal'}</span></td>
    </tr>`).join('');
}

// ─── ZAMMAD STATUS ────────────────────────────────────────────
async function loadZammadStatus() {
  const data = await apiFetch('/api/zammad/status');
  const el = document.getElementById('zammadStatusCard');
  if (!data) { el.innerHTML = '<div class="loading-state">Gagal memuat status Zammad.</div>'; return; }
  const connected = data.connected;
  el.className = 'zammad-status-card';
  el.innerHTML = `
    <div class="zammad-icon">${connected ? '🟢' : '🔴'}</div>
    <div class="zammad-info" style="flex:1">
      <h2>Zammad Framework ${connected ? '— Terhubung' : '— Belum Dikonfigurasi'}</h2>
      <p style="color:var(--text-secondary);font-size:13px">${connected ? 'Terhubung sebagai: '+data.logged_in_as : data.reason}</p>
      <div class="zammad-flow">
        <span class="flow-node">🏢 Site/Customer</span>
        <span class="flow-arrow">⇄</span>
        <span class="flow-node active">🎫 Zammad Framework</span>
        <span class="flow-arrow">→</span>
        <span class="flow-node active">🤖 Agent AI Tier 0</span>
        <span class="flow-arrow">↔</span>
        <span class="flow-node">📚 Knowledge DB</span>
      </div>
      <div style="font-size:12px;color:var(--text-secondary);margin-bottom:8px">
        <strong>Webhook URL:</strong> <code style="color:#94a3b8">${data.webhook_url}</code>
        &nbsp;&nbsp;<strong>Polling:</strong> setiap ${data.polling_interval_seconds || 30}s
      </div>
      ${data.setup_guide ? `
      <div style="font-size:12px;font-weight:700;color:var(--text-secondary);text-transform:uppercase;letter-spacing:.5px;margin-bottom:6px">Panduan Setup:</div>
      <ul class="setup-steps">
        ${data.setup_guide.map(s => `<li><span style="color:var(--accent)">→</span> ${s}</li>`).join('')}
      </ul>` : ''}
    </div>`;
}

async function simulateZammadWebhook() {
  const res = await apiFetch('/api/zammad/webhook', { method: 'POST', body: JSON.stringify({}) });
  const el = document.getElementById('webhookResult');
  if (res) {
    el.innerHTML = `<div style="background:rgba(34,211,160,.1);border:1px solid rgba(34,211,160,.3);border-radius:8px;padding:12px;font-size:13px">
      ✅ <strong>Webhook diterima!</strong> Tiket baru dibuat dengan ID <code style="color:#dc2626">${res.ticket_id?.slice(0,8)}...</code>
      dan dikirim ke AI Tier ${res.ai_tier}.
    </div>`;
    showToast('✅ Simulasi webhook berhasil!', 'success');
    setTimeout(loadDashboard, 1000);
  } else {
    el.innerHTML = `<div style="color:#f87171">❌ Gagal simulasi webhook.</div>`;
  }
}

async function forceSyncZammad() {
  const el = document.getElementById('forceSyncResult');
  el.innerHTML = '<span style="color:var(--accent)">⏳ Memproses sinkronisasi tiket...</span>';
  
  const res = await apiFetch('/api/zammad/sync-pending', { method: 'POST', body: JSON.stringify({}) });
  
  if (res) {
    el.innerHTML = `<div style="background:rgba(34,211,160,.1);border:1px solid rgba(34,211,160,.3);border-radius:8px;padding:12px;font-size:13px">
      ✅ <strong>Sinkronisasi Selesai!</strong><br/>
      Berhasil: <strong>${res.success_count}</strong> tiket<br/>
      Gagal: <strong>${res.failed_count}</strong> tiket<br/>
      <span style="color:var(--text-secondary)">Pesan Sistem: ${res.message}</span>
    </div>`;
    showToast(`✅ Sinkronisasi paksa berhasil!`, 'success');
  } else {
    el.innerHTML = `<div style="color:#f87171">❌ Gagal melakukan sinkronisasi paksa ke server.</div>`;
    showToast('Gagal memanggil endpoint sync', 'error');
  }
}

// ─── USER MANAGEMENT ──────────────────────────
async function loadUsers() {
  const data = await apiFetch('/api/users/');
  const tbody = document.getElementById('usersBody');
  if (!data?.users) { tbody.innerHTML = '<tr><td colspan="7" class="loading-state">Gagal memuat user.</td></tr>'; return; }
  if (!data.users.length) { tbody.innerHTML = '<tr><td colspan="7" class="loading-state">Belum ada user.</td></tr>'; return; }

  const isSuperAdmin = currentUser?.role === 'SUPER_ADMIN';

  tbody.innerHTML = data.users.map(u => `
    <tr>
      <td><strong>${u.username}</strong></td>
      <td>${u.full_name || '—'}</td>
      <td style="font-size:12px;color:#8892b0">${u.email}</td>
      <td>${roleBadge(u.role)}</td>
      <td><span class="badge ${u.is_active ? 'badge-resolved' : 'badge-escalated'}">${u.is_active ? '✅ Aktif' : '❌ Nonaktif'}</span></td>
      <td style="font-size:11px;color:#8892b0">${u.last_login ? u.last_login.replace('T',' ').slice(0,16) : 'Belum pernah'}</td>
      <td>
        ${u.user_id === currentUser?.user_id
          ? `<span style="font-size:12px;color:var(--accent);font-style:italic;margin-right:8px">👤 Akun Anda</span>
             <button class="btn-primary" style="margin-right:4px" onclick="showEditUserModal('${u.user_id}', '${u.username}', '${u.full_name || ''}', '${u.email}', '${u.role}')">✏️</button>`
          : isSuperAdmin 
            ? `<button class="btn-info" style="margin-right:4px" onclick="toggleUserActive('${u.user_id}', ${u.is_active})">
                ${u.is_active ? '🔒 Nonaktifkan' : '✅ Aktifkan'}
               </button>
               <button class="btn-primary" style="margin-right:4px" onclick="showEditUserModal('${u.user_id}', '${u.username}', '${u.full_name || ''}', '${u.email}', '${u.role}')">✏️</button>
               <button class="btn-danger" onclick="deleteUser('${u.user_id}', '${u.username}')">🗑️</button>`
            : `<span style="font-size:12px;color:#8892b0">Tidak ada akses</span>`
        }
      </td>
    </tr>`).join('');
}

function roleBadge(role) {
  const map = {
    SUPER_ADMIN: ['badge-super-admin', '👑 Super Admin'],
    USER_ADMIN:  ['badge-user-admin',  '🛡️ User Admin'],
    OPERATOR:    ['badge-operator',    '⚙️ Operator'],
    GUEST:       ['badge-guest',       '👁️ Guest'],
  };
  const [cls, label] = map[role] || ['badge-medium', role];
  return `<span class="badge ${cls}">${label}</span>`;
}

function roleLabel(role) {
  const map = { SUPER_ADMIN: '👑 Super Admin', USER_ADMIN: '🛡️ User Admin', OPERATOR: '⚙️ Operator', GUEST: '👁️ Guest / View' };
  return map[role] || role;
}

function showAddUserModal() {
  const isSuperAdmin = currentUser?.role === 'SUPER_ADMIN';
  document.getElementById('optUserAdmin').style.display  = isSuperAdmin ? '' : 'none';
  document.getElementById('optSuperAdmin').style.display = isSuperAdmin ? '' : 'none';

  ['addUsername','addFullName','addEmail','addPassword'].forEach(id => document.getElementById(id).value = '');
  document.getElementById('addRole').value = 'OPERATOR';
  document.getElementById('addUserModal').classList.add('show');
  document.getElementById('modalOverlay').classList.add('show');
}

function closeAddUserModal() {
  document.getElementById('addUserModal').classList.remove('show');
  document.getElementById('modalOverlay').classList.remove('show');
}

async function submitAddUser() {
  const username  = document.getElementById('addUsername').value.trim();
  const full_name = document.getElementById('addFullName').value.trim();
  const email     = document.getElementById('addEmail').value.trim();
  const password  = document.getElementById('addPassword').value;
  const role      = document.getElementById('addRole').value;

  if (!username || !email || !password) { showToast('Username, email, dan password wajib diisi!', 'error'); return; }
  if (password.length < 8) { showToast('Password minimal 8 karakter!', 'error'); return; }

  const res = await apiFetch('/api/auth/register', {
    method: 'POST',
    body: JSON.stringify({ username, full_name, email, password, role }),
  });
  if (res?.user) {
    closeAddUserModal();
    showToast(`✅ User '${username}' berhasil dibuat!`, 'success');
    loadUsers();
  } else {
    showToast(res?.detail || 'Gagal membuat user', 'error');
  }
}

// ─── EDIT USER MODAL ───
let editingUserId = null;
function showEditUserModal(id, username, fullName, email, role) {
  editingUserId = id;
  document.getElementById('editUsername').value = username;
  document.getElementById('editFullName').value = fullName;
  document.getElementById('editEmail').value = email;
  document.getElementById('editRole').value = role;
  document.getElementById('editPassword').value = ''; // Reset password field
  
  document.getElementById('editUserModal').classList.add('show');
  document.getElementById('modalOverlay').classList.add('show');
}

function closeEditUserModal() {
  document.getElementById('editUserModal').classList.remove('show');
  document.getElementById('modalOverlay').classList.remove('show');
  editingUserId = null;
}

async function submitEditUser() {
  if (!editingUserId) return;
  const full_name = document.getElementById('editFullName').value;
  const email = document.getElementById('editEmail').value;
  const role = document.getElementById('editRole').value;
  const password = document.getElementById('editPassword').value;

  // 1. Update profil dasar
  const res = await apiFetch(`/api/users/${editingUserId}`, {
    method: 'PUT',
    body: JSON.stringify({ full_name, email, role }),
  });

  if (!res?.user) {
    showToast(res?.detail || 'Gagal memperbarui user', 'error');
    return;
  }

  // 2. Jika password diisi, update passwordnya juga
  if (password.trim() !== '') {
    const pwdRes = await apiFetch(`/api/users/${editingUserId}/reset-password`, {
      method: 'POST',
      body: JSON.stringify({ new_password: password }),
    });
    if (!pwdRes?.message) {
      showToast(pwdRes?.detail || 'Profil terupdate, tapi gagal ganti password', 'warning');
      return;
    }
  }

  closeEditUserModal();
  showToast('✅ Profil & Password berhasil diperbarui!', 'success');
  loadUsers();
}


async function toggleUserActive(userId, isCurrentlyActive) {
  const res = await apiFetch(`/api/users/${userId}`, {
    method: 'PUT',
    body: JSON.stringify({ is_active: !isCurrentlyActive }),
  });
  if (res?.user) {
    showToast(`User berhasil ${!isCurrentlyActive ? 'diaktifkan' : 'dinonaktifkan'}`, 'success');
    loadUsers();
  } else {
    showToast('Gagal mengubah status user', 'error');
  }
}

async function deleteUser(userId, username) {
  if (!confirm(`Yakin ingin menghapus user '${username}'? Aksi ini tidak dapat dibatalkan.`)) return;
  const res = await apiFetch(`/api/users/${userId}`, { method: 'DELETE' });
  if (res?.message) {
    showToast(`✅ User '${username}' berhasil dihapus`, 'success');
    loadUsers();
  } else {
    showToast('Gagal menghapus user', 'error');
  }
}

// ─── LIVE CHAT WEBSOCKET (DASHBOARD) ─────────
let liveChatWs = null;
let currentChatTicketId = null;

async function openLiveChat(ticketId) {
  currentChatTicketId = ticketId;
  document.getElementById('ticketDetailModal').classList.remove('show');
  document.getElementById('modalOverlay').classList.add('show');
  
  const liveChatModal = document.getElementById('liveChatModal');
  liveChatModal.style.display = 'flex';
  // Use a slight timeout to ensure CSS transition works if display was none
  setTimeout(() => liveChatModal.classList.add('show'), 10);
  
  const chatBody = document.getElementById('liveChatBody');
  chatBody.innerHTML = '<div class="loading-state">Memuat riwayat chat...</div>';
  
  // Load history first
  try {
    const history = await apiFetch(`/api/chat/messages/${ticketId}`);
    chatBody.innerHTML = '';
    if (history && history.length > 0) {
        history.forEach(msg => appendChatMessage(msg));
    }
  } catch (e) {
    chatBody.innerHTML = '<div style="text-align:center; color:#dc2626; font-size:12px;">❌ Gagal memuat riwayat.</div>';
  }

  const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const wsUrl = `${wsProtocol}//${window.location.host}/api/chat/ws/${ticketId}`;
  
  if (liveChatWs) liveChatWs.close();
  liveChatWs = new WebSocket(wsUrl);
  
  liveChatWs.onopen = () => {
    const div = document.createElement('div');
    div.innerHTML = '<div style="text-align:center; color:#94a3b8; font-size:12px; margin-bottom:10px;">✅ Terhubung ke Kasir</div>';
    chatBody.appendChild(div);
  };
  
  liveChatWs.onmessage = (event) => {
    const data = JSON.parse(event.data);
    appendChatMessage(data);
  };
  
  liveChatWs.onerror = (error) => {
    chatBody.innerHTML += '<div style="text-align:center; color:#dc2626; font-size:12px;">❌ Koneksi terputus.</div>';
  };
  
  liveChatWs.onclose = () => {
    chatBody.innerHTML += '<div style="text-align:center; color:#8892b0; font-size:12px;">Chat ditutup.</div>';
  };
}

function closeLiveChatModal() {
  const liveChatModal = document.getElementById('liveChatModal');
  liveChatModal.classList.remove('show');
  setTimeout(() => liveChatModal.style.display = 'none', 300); // wait for animation
  
  document.getElementById('modalOverlay').classList.remove('show');
  if (liveChatWs) {
    liveChatWs.close();
    liveChatWs = null;
  }
  currentChatTicketId = null;
}

function appendChatMessage(data) {
  const chatBody = document.getElementById('liveChatBody');
  const isAgent = data.sender === 'AGENT';
  
  const div = document.createElement('div');
  div.style.padding = '10px 15px';
  div.style.borderRadius = '8px';
  div.style.maxWidth = '80%';
  div.style.wordWrap = 'break-word';
  div.style.alignSelf = isAgent ? 'flex-end' : 'flex-start';
  div.style.background = isAgent ? '#dc2626' : '#1e293b';
  div.style.color = isAgent ? '#000' : '#fff';
  div.style.border = isAgent ? 'none' : '1px solid #334155';
  
  const senderLabel = isAgent ? 'Anda (IT Helpdesk)' : 'Kasir';
  const timeLabel = new Date(data.timestamp || Date.now()).toLocaleTimeString('id-ID');
  
  let contentHtml = data.content.replace(/\n/g, '<br>');
  
  // Parse [Lampiran: ...] tag and render it nicely
  const attachRegex = /\[Lampiran:\s*([^\]]+)\]/g;
  contentHtml = contentHtml.replace(attachRegex, (match, url) => {
    if (url.toLowerCase().match(/\.(png|jpe?g|gif)$/i)) {
      return `<br><a href="${url}" target="_blank"><img src="${url}" style="max-width:200px; border-radius:4px; margin-top:5px;"/></a>`;
    }
    return `<br><a href="${url}" target="_blank" style="color: ${isAgent ? '#000' : '#fff'}; text-decoration: underline;">📄 Lampiran</a>`;
  });

  if (data.message_type === 'FILE' && data.content.startsWith('/uploads/')) {
    contentHtml = `<a href="${data.content}" target="_blank"><img src="${data.content}" style="max-width:200px; border-radius:4px; margin-top:5px;"/></a>`;
  }
  
  div.innerHTML = `
    <div style="font-size:10px; opacity:0.7; margin-bottom:4px; display:flex; justify-content:space-between; gap:10px;">
      <b>${senderLabel}</b> <span>${timeLabel}</span>
    </div>
    <div style="font-size:14px; line-height:1.4;">${contentHtml}</div>
  `;
  
  chatBody.appendChild(div);
  chatBody.scrollTop = chatBody.scrollHeight;
}

function sendLiveChatMessage() {
  const input = document.getElementById('liveChatInput');
  const text = input.value.trim();
  if (!text || !liveChatWs || liveChatWs.readyState !== WebSocket.OPEN) return;
  
  const msg = {
    sender: 'AGENT',
    message_type: 'TEXT',
    content: text
  };
  liveChatWs.send(JSON.stringify(msg));
  input.value = '';
}

function downloadChatPdf() {
  if (!currentChatTicketId) return;
  showToast('Mempersiapkan PDF...', 'info');
  window.open(`${API}/api/chat/export-pdf/${currentChatTicketId}`, '_blank');
}

// ─── TELEMETRY HISTORY LOG ──────────────────
let currentHistoryDeviceId = null;
let currentHistoryPage = 1;

function openHistoryModal(deviceId, deviceName) {
  currentHistoryDeviceId = deviceId;
  currentHistoryPage = 1;
  document.getElementById('historyModalTitle').innerText = `📜 Telemetry Log History - ${deviceName}`;
  
  // Set default date to today if empty
  const dp = document.getElementById('historyDatePicker');
  if (!dp.value) {
    dp.value = new Date().toISOString().split('T')[0];
  }
  
  document.getElementById('modalOverlay').classList.add('show');
  const historyModal = document.getElementById('historyModal');
  historyModal.style.display = 'flex';
  setTimeout(() => historyModal.classList.add('show'), 10);
  
  fetchDeviceHistory();
}

function closeHistoryModal() {
  const historyModal = document.getElementById('historyModal');
  historyModal.classList.remove('show');
  setTimeout(() => historyModal.style.display = 'none', 300);
  document.getElementById('modalOverlay').classList.remove('show');
  currentHistoryDeviceId = null;
}

async function fetchDeviceHistory() {
  if (!currentHistoryDeviceId) return;
  const date = document.getElementById('historyDatePicker').value;
  const limit = 100;
  
  try {
    const res = await fetch(`${API}/api/devices/${currentHistoryDeviceId}/history?page=${currentHistoryPage}&limit=${limit}&start_date=${date}&end_date=${date}`);
    if (res.ok) {
      const json = await res.json();
      renderHistoryTable(json.data);
      
      document.getElementById('historyPaginationInfo').innerText = `Menampilkan halaman ${currentHistoryPage} (Terbaru di atas)`;
      document.getElementById('btnPrevHistory').disabled = currentHistoryPage <= 1;
      document.getElementById('btnNextHistory').disabled = json.data.length < limit;
    } else {
      showToast("Gagal memuat histori", "error");
    }
  } catch(e) {
    console.error(e);
  }
}

function renderHistoryTable(data) {
  const tbody = document.getElementById('historyTableBody');
  if (data.length === 0) {
    tbody.innerHTML = `<tr><td colspan="6" style="text-align:center; padding:20px; color:#94a3b8;">Tidak ada aktivitas terekam pada tanggal ini.</td></tr>`;
    return;
  }
  
  tbody.innerHTML = data.map(d => {
    const timeOnly = d.time ? new Date(d.time).toLocaleTimeString('id-ID', {hour12: false}) : '—';
    return `
      <tr>
        <td style="color:#94a3b8">${timeOnly}</td>
        <td><b>${d.cpu_usage ? d.cpu_usage.toFixed(1) + '%' : '—'}</b></td>
        <td><b>${d.ram_usage ? d.ram_usage.toFixed(1) + '%' : '—'}</b></td>
        <td><b>${d.temperature ? d.temperature.toFixed(1) + '°C' : '—'}</b></td>
        <td><span style="color:#a855f7">${d.active_app || '—'}</span></td>
        <td style="max-width:200px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; color:#dc2626;" title="${d.active_url || ''}">
          ${d.active_url || '—'}
        </td>
      </tr>
    `;
  }).join('');
}

function changeHistoryPage(offset) {
  currentHistoryPage += offset;
  if (currentHistoryPage < 1) currentHistoryPage = 1;
  fetchDeviceHistory();
}

function exportHistoryExcel() {
  if (!currentHistoryDeviceId) return;
  const date = document.getElementById('historyDatePicker').value;
  showToast("Menyiapkan File Excel...", "info");
  window.open(`${API}/api/devices/${currentHistoryDeviceId}/history/export?start_date=${date}&end_date=${date}`, '_blank');
}

// ─── PORT CHECKER MODAL ─────────────────────
let currentPortCheckerDeviceId = null;

async function openPortCheckerModal(deviceId, deviceName) {
  currentPortCheckerDeviceId = deviceId;
  document.getElementById('portCheckerModalTitle').innerText = `🔌 Riwayat Port Checker - ${deviceName}`;
  
  const modalOverlay = document.getElementById('portCheckerModalOverlay');
  const modal = document.getElementById('portCheckerModal');
  modalOverlay.classList.add('show');
  modal.style.display = 'block';
  setTimeout(() => modal.classList.add('show'), 10);
  
  // Mark as read in backend
  await apiFetch(`/api/port-checker/mark-read/${deviceId}`, { method: 'POST' });
  
  // Reload devices to clear the badge in the background
  loadDevices();

  fetchPortCheckerHistory();
}

function closePortCheckerModal() {
  const modalOverlay = document.getElementById('portCheckerModalOverlay');
  const modal = document.getElementById('portCheckerModal');
  modal.classList.remove('show');
  setTimeout(() => modal.style.display = 'none', 300);
  modalOverlay.classList.remove('show');
  currentPortCheckerDeviceId = null;
}

async function fetchPortCheckerHistory() {
  if (!currentPortCheckerDeviceId) return;
  const tbody = document.getElementById('portCheckerBody');
  tbody.innerHTML = '<tr><td colspan="4" class="loading-state">Memuat riwayat...</td></tr>';
  
  try {
    const data = await apiFetch(`/api/port-checker/${currentPortCheckerDeviceId}`);
    if (data && data.logs) {
      if (data.logs.length === 0) {
        tbody.innerHTML = `<tr><td colspan="4" style="text-align:center; padding:20px; color:#94a3b8;">Tidak ada catatan putus port.</td></tr>`;
      } else {
        tbody.innerHTML = data.logs.map(log => {
          const wkt = log.created_at ? new Date(log.created_at + 'Z').toLocaleString('id-ID') : '—';
          return `
            <tr>
              <td style="color:#94a3b8">${wkt}</td>
              <td><span class="badge badge-medium">${log.category || '—'}</span></td>
             <td>${(log.hardware_type || '') + ' - ' + (log.hardware_name || '—')}</td>
              <td style="color:#ef4444">${log.summary}</td>
            </tr>
          `;
        }).join('');
      }
    }
  } catch(e) {
    console.error(e);
    tbody.innerHTML = '<tr><td colspan="4" class="loading-state" style="color:red">Gagal memuat histori</td></tr>';
  }
}

function downloadPortCheckerExcel() {
  if (!currentPortCheckerDeviceId) return;
  window.open(`${API}/api/port-checker/export/${currentPortCheckerDeviceId}`, '_blank');
}
