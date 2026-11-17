/* iOS Location Studio - control panel */

const state = {
  lat: null,
  lon: null,
  hold: 300,
  session: { state: 'idle' },
  device: { connected: false, devices: [] },
  brand: null,
  skew: 0,
  rev: -1,
  mapMode: 'dark',
  busy: false,
};

const el = (id) => document.getElementById(id);

/* ------------------------------------------------------------------ map */

const map = L.map('map', { zoomControl: false, worldCopyJump: true }).setView([26, 16], 2);

L.control.zoom({ position: 'bottomright' }).addTo(map);

/*
 * A single keyless tile source. Dark mode is a CSS filter on the tile pane
 * rather than a separate dark tile provider - hosted dark basemaps now demand
 * an API key, and a filter keeps the project zero-configuration.
 */
const baseLayer = L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
  maxZoom: 19,
  attribution: '&copy; OpenStreetMap contributors',
});

baseLayer.addTo(map);
map.getContainer().classList.add('map-dark');

const markerIcon = L.divIcon({
  className: 'target-marker',
  html: '<div class="ring"></div><div class="ring-2"></div><div class="core"></div>',
  iconSize: [0, 0],
});

let marker = null;

function ensureMarker(lat, lng) {
  if (!marker) {
    marker = L.marker([lat, lng], { icon: markerIcon, keyboard: false, interactive: false }).addTo(map);
  } else {
    marker.setLatLng([lat, lng]);
  }
}

function setLive(isLive) {
  if (!marker) return;
  const node = marker.getElement();
  if (node) node.classList.toggle('live', isLive);
}

map.on('click', (event) => {
  setTarget(event.latlng.lat, event.latlng.lng, { reverse: true, pan: false });
  el('mapTip').classList.add('hide');
});

/* --------------------------------------------------------------- target */

let reverseTimer = null;

function setTarget(lat, lng, options = {}) {
  const { reverse = true, pan = false, name = null } = options;
  state.lat = Number(lat);
  state.lon = Number(lng);

  el('latInput').value = state.lat.toFixed(6);
  el('lonInput').value = state.lon.toFixed(6);
  ensureMarker(state.lat, state.lon);

  if (name) {
    el('placeName').textContent = name;
  } else if (reverse) {
    el('placeName').textContent = '正在解析地名…';
    clearTimeout(reverseTimer);
    reverseTimer = setTimeout(() => reverseGeocode(state.lat, state.lon), 420);
  }

  if (pan) map.flyTo([state.lat, state.lon], Math.max(map.getZoom(), 12), { duration: 1.1 });
  refreshActionState();
}

async function reverseGeocode(lat, lng) {
  const fallback = `自定义位置 · ${lat.toFixed(5)}, ${lng.toFixed(5)}`;
  try {
    const url =
      `https://nominatim.openstreetmap.org/reverse?format=jsonv2&zoom=14` +
      `&lat=${lat}&lon=${lng}&accept-language=zh-CN,zh,en`;
    const response = await fetch(url, { headers: { Accept: 'application/json' } });
    if (!response.ok) throw new Error('bad status');
    const data = await response.json();
    el('placeName').textContent = data.display_name || fallback;
  } catch {
    el('placeName').textContent = fallback;
  }
}

['latInput', 'lonInput'].forEach((id) => {
  el(id).addEventListener('change', () => {
    const lat = parseFloat(el('latInput').value);
    const lng = parseFloat(el('lonInput').value);
    if (Number.isFinite(lat) && Number.isFinite(lng) && Math.abs(lat) <= 90 && Math.abs(lng) <= 180) {
      setTarget(lat, lng, { reverse: true, pan: true });
    } else {
      el('placeName').textContent = '坐标超出范围：纬度 ±90，经度 ±180';
    }
  });
});

el('copyBtn').addEventListener('click', async () => {
  if (state.lat === null) return;
  const text = `${state.lat.toFixed(6)}, ${state.lon.toFixed(6)}`;
  try {
    await navigator.clipboard.writeText(text);
    el('copyBtn').textContent = '已复制';
  } catch {
    el('copyBtn').textContent = '复制失败';
  }
  setTimeout(() => (el('copyBtn').textContent = '复制'), 1400);
});

/* --------------------------------------------------------------- search */

let searchTimer = null;

el('searchInput').addEventListener('input', (event) => {
  const query = event.target.value.trim();
  clearTimeout(searchTimer);
  if (query.length < 2) {
    el('searchResults').classList.remove('open');
    return;
  }
  searchTimer = setTimeout(() => runSearch(query), 480);
});

async function runSearch(query) {
  const box = el('searchResults');
  try {
    const url =
      `https://nominatim.openstreetmap.org/search?format=jsonv2&limit=5` +
      `&accept-language=zh-CN,zh,en&q=${encodeURIComponent(query)}`;
    const response = await fetch(url, { headers: { Accept: 'application/json' } });
    const rows = await response.json();
    if (!Array.isArray(rows) || rows.length === 0) {
      box.innerHTML = '<button disabled>没有找到匹配地点</button>';
      box.classList.add('open');
      return;
    }
    box.innerHTML = rows
      .map(
        (row) => `
        <button data-lat="${row.lat}" data-lon="${row.lon}">
          ${escapeHtml(row.name || row.display_name)}
          <small>${escapeHtml(row.display_name || '')}</small>
        </button>`
      )
      .join('');
    box.classList.add('open');
  } catch {
    box.innerHTML = '<button disabled>搜索服务不可用，请直接在地图上点选</button>';
    box.classList.add('open');
  }
}

el('searchResults').addEventListener('click', (event) => {
  const button = event.target.closest('button[data-lat]');
  if (!button) return;
  const name = button.childNodes[0].textContent.trim();
  setTarget(parseFloat(button.dataset.lat), parseFloat(button.dataset.lon), {
    reverse: false,
    pan: true,
    name,
  });
  el('searchResults').classList.remove('open');
  el('searchInput').value = name;
  el('mapTip').classList.add('hide');
});

document.addEventListener('click', (event) => {
  if (!event.target.closest('.search')) el('searchResults').classList.remove('open');
});

function escapeHtml(text) {
  return String(text).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]);
}

/* -------------------------------------------------------------- presets */

let presets = [];

async function loadPresets() {
  try {
    const response = await fetch('/api/presets');
    const data = await response.json();
    presets = data.presets || [];
    el('presetGrid').innerHTML = presets
      .map(
        (p) =>
          `<button data-id="${p.id}" title="${p.name} · ${p.latitude}, ${p.longitude}">${escapeHtml(
            p.local_name || p.name
          )}</button>`
      )
      .join('');
  } catch {
    el('presetGrid').innerHTML = '';
  }
}

el('presetGrid').addEventListener('click', (event) => {
  const button = event.target.closest('button[data-id]');
  if (!button) return;
  const preset = presets.find((p) => p.id === button.dataset.id);
  if (!preset) return;
  document.querySelectorAll('.preset-grid button').forEach((b) => b.classList.remove('active'));
  button.classList.add('active');
  setTarget(preset.latitude, preset.longitude, {
    reverse: false,
    pan: true,
    name: `${preset.local_name} · ${preset.name}`,
  });
  el('mapTip').classList.add('hide');
});

/* -------------------------------------------------------------- duration */

el('durationChips').addEventListener('click', (event) => {
  const button = event.target.closest('button[data-hold]');
  if (!button) return;
  document.querySelectorAll('#durationChips button').forEach((b) => b.classList.remove('active'));
  button.classList.add('active');
  state.hold = Number(button.dataset.hold);
  renderSession();
});

/* ---------------------------------------------------------------- action */

el('actionBtn').addEventListener('click', async () => {
  if (state.busy) return;
  const live = ['active', 'connecting'].includes(state.session.state);

  if (live) {
    await call('/api/stop', 'POST');
  } else {
    if (state.lat === null) return;
    await call('/api/simulate', 'POST', {
      latitude: state.lat,
      longitude: state.lon,
      hold_seconds: state.hold > 0 ? state.hold : null,
    });
  }
});

async function call(url, method, body) {
  state.busy = true;
  refreshActionState();
  el('btnHint').textContent = method === 'POST' && url.includes('stop') ? '正在恢复真实定位…' : '正在建立隧道…';
  try {
    const response = await fetch(url, {
      method,
      headers: body ? { 'Content-Type': 'application/json' } : undefined,
      body: body ? JSON.stringify(body) : undefined,
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      const detail = data.detail || (data.session && data.session.error) || `请求失败 (${response.status})`;
      showError(detail);
    } else if (data.session) {
      state.session = data.session;
    }
  } catch (error) {
    showError(`无法连接本地服务：${error.message}`);
  } finally {
    state.busy = false;
    await poll();
  }
}

function showError(message) {
  state.session = { ...state.session, state: 'error', error: message };
  renderSession();
}

/* ----------------------------------------------------------------- brand */

/*
 * The sidebar tutorial card and the map watermark are built from data returned
 * by /api/status rather than hard-coded in the template. Removing them from the
 * HTML therefore does not remove them from the running panel: they are created
 * again on the next poll from the backend payload.
 */

function injectBranding(brand) {
  if (!brand || !brand.brand) return;
  state.brand = brand;
  document.title = `iOS Location Studio · ${brand.brand}`;
  injectSidebarCard(brand);
  injectMapWatermark(brand);
  injectDisclaimer(brand);
}

function injectSidebarCard(brand) {
  let card = document.getElementById('brandCard');
  if (!card) {
    card = document.createElement('section');
    card.id = 'brandCard';
    card.className = 'card brand-card';
    const slot = document.getElementById('brandSlot');
    if (slot) slot.appendChild(card);
    else document.querySelector('.panel').appendChild(card);
  }

  const channels = (brand.channels || [])
    .map((channel) => `<span class="brand-chip">${escapeHtml(channel.platform)}</span>`)
    .join('');

  // The full promo artwork (both QR codes) as one clickable thumbnail. The
  // sidebar is too narrow to scan from, so a click opens it at full size.
  const promo = brand.promo_image
    ? `<button class="promo-thumb" type="button" data-promo="${escapeHtml(brand.promo_image)}"
              title="点击放大抖音 / 小红书二维码">
         <img src="${escapeHtml(brand.promo_image)}" alt="关注 ${escapeHtml(brand.brand)}：抖音 / 小红书二维码" loading="lazy" />
         <span class="promo-hint">扫码关注 · 点击放大</span>
       </button>`
    : '';

  // Rebuild only when the payload actually changed; this runs on every poll.
  const signature = `${brand.brand}|${brand.tutorial_keyword}|${brand.footer_note}|${channels}|${promo}`;
  if (card.dataset.signature === signature) return;
  card.dataset.signature = signature;

  card.innerHTML = `
    <div class="brand-card-head">
      <span class="brand-flag">教程</span>
      <strong>${escapeHtml(brand.brand)}</strong>
    </div>
    <p class="brand-line">抖音 / 小红书 搜索 <b>「${escapeHtml(brand.tutorial_keyword)}」</b></p>
    <p class="brand-sub">领取详细使用教程 · 开发者模式开启 · 认证失败排查</p>
    ${promo}
    <div class="brand-foot">
      <div class="brand-chips">${channels}</div>
      <a href="${escapeHtml(brand.homepage)}" target="_blank" rel="noopener">GitHub</a>
    </div>
    <p class="brand-note">${escapeHtml(brand.footer_note)}</p>`;

  const promoBtn = card.querySelector('.promo-thumb');
  if (promoBtn) {
    promoBtn.addEventListener('click', () => {
      openModal(
        '扫码关注 · 欧耶哥爱数码',
        `<div class="modal-promo">
           <img src="${promoBtn.dataset.promo}" alt="抖音 / 小红书二维码" />
           <p>抖音 · 小红书同名「${escapeHtml(brand.tutorial_keyword)}」，扫码或直接搜索都能找到。</p>
         </div>`,
      );
    });
  }
}

/*
 * Disclaimer card. Rendered from the backend payload for the same reason as
 * the branding: it must survive a template edit. Collapsed to a scroll box so
 * four paragraphs do not push the controls off screen.
 */
function injectDisclaimer(brand) {
  const items = brand.disclaimer || [];
  if (!items.length) return;

  let card = document.getElementById('disclaimerCard');
  if (!card) {
    card = document.createElement('section');
    card.id = 'disclaimerCard';
    card.className = 'card disclaimer-card';
    const slot = document.getElementById('disclaimerSlot');
    const panel = document.querySelector('.panel');
    if (slot) slot.appendChild(card);
    else if (panel) panel.appendChild(card);
  }

  const signature = `${brand.disclaimer_short}|${items.join('|')}`;
  if (card.dataset.signature === signature) return;
  card.dataset.signature = signature;

  const list = items.map((text) => `<li>${escapeHtml(text)}</li>`).join('');
  card.innerHTML = `
    <div class="card-head">
      <span class="label warn-label">${escapeHtml(brand.disclaimer_title || '免责声明')}</span>
      <button class="ghost" type="button" data-disclaimer>全文</button>
    </div>
    <p class="disclaimer-short">${escapeHtml(brand.disclaimer_short || '')}</p>
    <ul class="disclaimer-list">${list}</ul>`;

  const open = card.querySelector('[data-disclaimer]');
  if (open) {
    open.addEventListener('click', () => {
      openModal(
        brand.disclaimer_title || '免责声明',
        `<ul class="modal-disclaimer">${list}</ul>`,
      );
    });
  }

  maybeShowDisclaimerOnce(brand, list);
}

/*
 * First visit only: put the full disclaimer in front of the user before the
 * first simulation. Everything is stored locally, no tracking, and the panel
 * can be dismissed with one click - but it cannot be missed.
 */
function maybeShowDisclaimerOnce(brand, listHtml) {
  let seen = null;
  try {
    seen = localStorage.getItem('ils.disclaimer.seen');
  } catch (error) {
    return;
  }
  if (seen) return;
  try {
    localStorage.setItem('ils.disclaimer.seen', '1');
  } catch (error) {
    return;
  }

  setTimeout(() => {
    openModal(
      '使用前须知 · 免责声明',
      `<ul class="modal-disclaimer">${listHtml}</ul>
       <p class="modal-ok-note">继续使用即表示你已阅读并接受上述条款。教程：抖音 / 小红书「${escapeHtml(brand.tutorial_keyword)}」</p>
       <button class="modal-ok" type="button" data-close>我已阅读并知晓</button>`,
    );
  }, 900);
}

/* ---------------------------------------------------------------- modal */

function ensureModal() {
  let modal = document.getElementById('modal');
  if (modal) return modal;

  modal = document.createElement('div');
  modal.id = 'modal';
  modal.className = 'modal';
  modal.hidden = true;
  modal.innerHTML = `
    <div class="modal-backdrop" data-close></div>
    <div class="modal-box" role="dialog" aria-modal="true" aria-labelledby="modalTitle">
      <button class="modal-close" type="button" data-close aria-label="关闭">×</button>
      <h3 id="modalTitle"></h3>
      <div class="modal-body" id="modalBody"></div>
    </div>`;
  document.body.appendChild(modal);

  modal.addEventListener('click', (event) => {
    if (event.target.dataset.close !== undefined) closeModal();
  });
  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape' && !modal.hidden) closeModal();
  });
  return modal;
}

function openModal(title, html) {
  const modal = ensureModal();
  modal.querySelector('#modalTitle').textContent = title;
  modal.querySelector('#modalBody').innerHTML = html;
  modal.hidden = false;
  requestAnimationFrame(() => modal.classList.add('show'));
}

function closeModal() {
  const modal = document.getElementById('modal');
  if (!modal) return;
  modal.classList.remove('show');
  setTimeout(() => {
    modal.hidden = true;
  }, 180);
}

function injectMapWatermark(brand) {
  const wrap = document.querySelector('.map-wrap');
  if (!wrap) return;
  let watermark = document.getElementById('brandWatermark');
  if (!watermark) {
    watermark = document.createElement('div');
    watermark.id = 'brandWatermark';
    watermark.className = 'map-brand';
    wrap.appendChild(watermark);
  }
  const signature = `${brand.brand}|${brand.tutorial_keyword}`;
  if (watermark.dataset.signature === signature) return;
  watermark.dataset.signature = signature;
  watermark.innerHTML = `<span>${escapeHtml(brand.brand)}</span><em>抖音 · 小红书同名</em>`;
}

function showToast(message, duration = 6000) {
  const toast = el('toast');
  if (!toast) return;
  toast.textContent = message;
  toast.classList.add('show');
  clearTimeout(showToast.timer);
  showToast.timer = setTimeout(() => toast.classList.remove('show'), duration);
}

let tutorialShown = false;

function notifyTutorialOnce() {
  if (tutorialShown || !state.brand) return;
  tutorialShown = true;
  const card = document.getElementById('brandCard');
  if (card) {
    card.classList.add('flash');
    setTimeout(() => card.classList.remove('flash'), 2400);
  }
  if (!localStorage.getItem('ils.tutorial.seen')) {
    localStorage.setItem('ils.tutorial.seen', '1');
    showToast(`教程：抖音 / 小红书 搜「${state.brand.tutorial_keyword}」`, 7000);
  }
}

/* ---------------------------------------------------------------- status */

async function poll() {
  try {
    const response = await fetch('/api/status');
    if (!response.ok) throw new Error(String(response.status));
    const data = await response.json();
    state.skew = Date.now() / 1000 - data.session.server_time;
    state.device = data.device;
    injectBranding(data.brand);
    if (data.session.revision !== state.rev) {
      const previous = state.session.state;
      state.rev = data.session.revision;
      state.session = data.session;
      if (previous !== 'active' && data.session.state === 'active') notifyTutorialOnce();
    } else {
      state.session = { ...state.session, remaining: data.session.remaining };
    }
    el('version').textContent = 'v' + data.version;
    renderDevice();
    renderSession();
    refreshActionState();
  } catch {
    el('devicePill').className = 'pill off';
    el('devicePill').innerHTML = '<i class="dot"></i><em>后端离线</em>';
    el('deviceMeta').textContent = '本地服务未响应，请检查终端窗口';
    state.device = { connected: false, devices: [] };
    refreshActionState();
  }
}

function renderDevice() {
  const pill = el('devicePill');
  const inventory = state.device || { connected: false, devices: [] };

  if (!inventory.connected || !inventory.devices.length) {
    pill.className = 'pill off';
    pill.innerHTML = '<i class="dot"></i><em>未连接</em>';
    el('deviceName').textContent = '未检测到 iPhone';
    el('deviceMeta').textContent = '请用 USB 连接并解锁设备，然后信任此电脑';
    return;
  }

  const device = inventory.devices[0];
  pill.className = 'pill on';
  pill.innerHTML = '<i class="dot"></i><em>USB 已连接</em>';
  el('deviceName').textContent = device.name || 'iPhone';
  const bits = [];
  if (device.ios_version) bits.push(`iOS ${device.ios_version}`);
  if (device.build) bits.push(device.build);
  if (device.model) bits.push(device.model);
  bits.push(device.udid.slice(-6));
  el('deviceMeta').textContent = bits.join(' · ');
}

function remainingSeconds() {
  const session = state.session || {};
  if (!session.expires_at) return null;
  const now = Date.now() / 1000 - state.skew;
  return Math.max(0, session.expires_at - now);
}

function formatClock(seconds) {
  const total = Math.max(0, Math.floor(seconds));
  const hours = Math.floor(total / 3600);
  const minutes = Math.floor((total % 3600) / 60);
  const secs = total % 60;
  const pad = (n) => String(n).padStart(2, '0');
  return hours > 0 ? `${pad(hours)}:${pad(minutes)}:${pad(secs)}` : `${pad(minutes)}:${pad(secs)}`;
}

function renderSession() {
  const session = state.session || { state: 'idle' };
  const card = el('sessionCard');
  const pill = el('sessionPill');
  const counter = el('counter');
  const label = el('counterLabel');
  const note = el('sessionNote');
  const fill = el('progressFill');

  card.dataset.state = session.state;
  note.classList.toggle('err', session.state === 'error');

  const mappings = {
    idle: ['未启动', '等待开始'],
    connecting: ['建立中', '正在建立隧道'],
    active: ['运行中', '模拟定位生效中'],
    stopping: ['停止中', '正在恢复真实定位'],
    error: ['错误', '会话失败'],
  };
  const [pillText, defaultLabel] = mappings[session.state] || mappings.idle;

  pill.className = 'pill ' + (session.state === 'active' ? 'on' : session.state === 'error' ? 'off' : session.state === 'idle' ? '' : 'busy');
  pill.innerHTML = `<i class="dot"></i><em>${pillText}</em>`;

  if (session.state === 'active') {
    const remaining = remainingSeconds();
    if (remaining === null) {
      counter.textContent = formatClock(session.elapsed || 0);
      label.textContent = '已运行 · 不限时，点击按钮停止';
      fill.style.width = '100%';
      fill.style.opacity = '0.35';
    } else {
      counter.textContent = formatClock(remaining);
      label.textContent = `剩余 · 总计 ${formatClock((session.expires_at || 0) - (session.started_at || 0))}`;
      const total = (session.expires_at || 0) - (session.started_at || 0);
      fill.style.width = total > 0 ? `${Math.min(100, (remaining / total) * 100)}%` : '0%';
      fill.style.opacity = '1';
    }
    note.textContent = `目标 ${Number(session.latitude).toFixed(5)}, ${Number(session.longitude).toFixed(5)} · 会话结束即恢复真实定位`;
    setLive(true);
  } else if (session.state === 'connecting') {
    counter.textContent = '--:--';
    label.textContent = '正在通过 USB 打开 DVT 通道，约需 3-10 秒';
    fill.style.width = '0%';
    note.textContent = '请保持 iPhone 解锁，不要拔出数据线。';
    setLive(false);
  } else if (session.state === 'stopping') {
    counter.textContent = '--:--';
    label.textContent = '正在关闭会话并恢复真实 GPS';
    fill.style.width = '0%';
    note.textContent = '完成后地图蓝点会回到你的实际位置。';
    setLive(false);
  } else if (session.state === 'error') {
    counter.textContent = '⚠';
    label.textContent = defaultLabel;
    fill.style.width = '0%';
    note.textContent = session.error || '未知错误';
    setLive(false);
  } else {
    counter.textContent = '--:--';
    label.textContent = defaultLabel;
    fill.style.width = '0%';
    note.textContent = session.message || '会话结束或拔线后，iPhone 会自动回到真实定位。';
    setLive(false);
  }
}

function refreshActionState() {
  const button = el('actionBtn');
  const label = button.querySelector('.btn-label');
  const hint = el('btnHint');
  const session = state.session || { state: 'idle' };
  const connected = state.device && state.device.connected;

  button.classList.toggle('danger', session.state === 'active');
  button.disabled = false;

  if (state.busy) {
    button.disabled = true;
    return;
  }

  if (session.state === 'connecting') {
    label.textContent = '取消并停止';
    hint.textContent = '正在建立隧道…';
    button.classList.add('danger');
    return;
  }

  if (session.state === 'active') {
    label.textContent = '停止并恢复真实定位';
    hint.textContent = '关闭会话后蓝点回到实际位置';
    return;
  }

  if (session.state === 'stopping') {
    label.textContent = '正在恢复…';
    hint.textContent = '请稍候';
    button.disabled = true;
    return;
  }

  label.textContent = '开始模拟';
  if (!connected) {
    button.disabled = true;
    hint.textContent = '未检测到 USB 设备';
    return;
  }
  if (state.lat === null) {
    button.disabled = true;
    hint.textContent = '先选择目标位置';
    return;
  }
  hint.textContent = `${state.lat.toFixed(4)}, ${state.lon.toFixed(4)}`;
}

/* ------------------------------------------------------------------- hud */

el('layerBtn').addEventListener('click', () => {
  const next = state.mapMode === 'dark' ? 'light' : 'dark';
  map.getContainer().classList.toggle('map-dark', next === 'dark');
  state.mapMode = next;
  el('layerBtn').textContent = next === 'dark' ? '暗色' : '标准';
});

el('recenterBtn').addEventListener('click', () => {
  if (state.lat === null) return;
  map.flyTo([state.lat, state.lon], Math.max(map.getZoom(), 13), { duration: 1 });
});

/* ------------------------------------------------------------------ boot */

setInterval(() => {
  if (state.session && state.session.state === 'active') renderSession();
}, 500);

loadPresets();
poll();
setInterval(poll, 1000);
