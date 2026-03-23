let map = null;
let routeLines = [];
let markers = [];

let tsStart = null, tsGoal = null, tsMode = null;

let currentLimit = 6;
let avoidSelected = new Set();
let airlineSelected = new Set();

let liveSearchTimer = null;

function queueLiveSearch() {
  clearTimeout(liveSearchTimer);
  liveSearchTimer = setTimeout(() => {
    const start = $('#start')?.value;
    const goal = $('#goal')?.value;
    if (!start || !goal) return;
    search(true);
  }, 180);
}

const $ = (sel) => document.querySelector(sel);

function makeTomSelect(selector, opts) {
  const el = $(selector);
  if (!el) return null;
  return new TomSelect(el, opts);
}

function initTomSelect() {
  const common = {
    create: false,
    persist: false,
    maxOptions: 9999,
    closeAfterSelect: true,
    allowEmptyOption: true,
    searchField: ['text', 'value'],
    sortField: [{ field: '$score', direction: 'desc' }],
  };

  tsStart = makeTomSelect('#start', common);
  tsGoal = makeTomSelect('#goal', common);

  tsMode = makeTomSelect('#mode', {
    create: false,
    persist: false,
    closeAfterSelect: true,
    searchField: [],
  });
}

function initSlider() {
  const slider = $('#max_hops');
  const out = $('#maxHopsVal');
  if (!slider || !out) return;

  out.textContent = slider.value;

  slider.addEventListener('input', () => {
    out.textContent = slider.value;
    queueLiveSearch();
  });

  slider.addEventListener('change', () => {
    out.textContent = slider.value;
    queueLiveSearch();
  });
}

function initMap() {
  const mapEl = $('#map');
  if (!mapEl) return;

  map = L.map('map', { zoomControl: true }).setView([1.35, 103.82], 3);

  L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png', {
    attribution: '&copy; OpenStreetMap & CartoDB',
  }).addTo(map);
}

function clearMap(resetView = false) {
  if (!map) return;

  routeLines.forEach(line => map.removeLayer(line));
  routeLines = [];

  markers.forEach(marker => map.removeLayer(marker));
  markers = [];

  if (resetView) {
    map.setView([1.35, 103.82], 3);
  }
}

function airportSymbol(role) {
  if (role === 'start') return '✈';
  if (role === 'end') return '⚑';
  return '●';
}

function airportMarkerClass(role) {
  if (role === 'start') return 'airport-marker airport-marker-start';
  if (role === 'end') return 'airport-marker airport-marker-end';
  return 'airport-marker airport-marker-layover';
}

function makeAirportIcon(role) {
  return L.divIcon({
    className: 'airport-marker-wrapper',
    html: `
      <div class="${airportMarkerClass(role)}">
        <span>${airportSymbol(role)}</span>
      </div>
    `,
    iconSize: [28, 28],
    iconAnchor: [14, 14],
    popupAnchor: [0, -14],
    tooltipAnchor: [0, -16],
  });
}

function drawRoute(option) {
  if (!map) return;
  clearMap(false);

  const airports = window.__AIRPORTS__ || [];
  const byCode = {};
  airports.forEach(a => {
    byCode[a.code] = a;
  });

  const path = option.path || [];
  const legs = option.legs || [];

  const points = path
    .filter(code => byCode[code])
    .map(code => ({
      code,
      label: byCode[code].label,
      name: byCode[code].name || byCode[code].label,
      city: byCode[code].city || '',
      country: byCode[code].country || '',
      lat: byCode[code].lat,
      lon: byCode[code].lon,
    }));

  if (points.length < 2) {
    clearMap(true);
    return;
  }

  const bounds = L.latLngBounds(points.map(p => [p.lat, p.lon]));
  map.fitBounds(bounds, { padding: [30, 30] });

  legs.forEach((leg) => {
    const fromAirport = byCode[leg.from_code];
    const toAirport = byCode[leg.to_code];
    if (!fromAirport || !toAirport) return;

    const coords = [
      [fromAirport.lat, fromAirport.lon],
      [toAirport.lat, toAirport.lon]
    ];

    const airlineCodes = (leg.airlines || [])
      .map(a => a.code)
      .filter(Boolean)
      .join(', ') || '—';

    const airlineNames = (leg.airlines || [])
      .map(a => a.name)
      .filter(Boolean)
      .join(', ') || 'Unknown';

    const hoverText = `
  <div class="mapTooltipTitle">${leg.from_code} → ${leg.to_code}</div>
  <div class="mapTooltipSub">${fmtDuration(leg.minutes)}</div>
`;

    const popupText = `
  <div class="mapPopup">
    <div class="mapPopupTitle">${leg.from_code} → ${leg.to_code}</div>
    <div class="mapPopupSub">${airlineCodes} • ${fmtDuration(leg.minutes)}</div>

    <div class="mapPopupGrid">
      <div class="mapPopupItem">
        <div class="mapPopupLabel">Airline</div>
        <div class="mapPopupValue">${airlineNames}</div>
      </div>
      <div class="mapPopupItem">
        <div class="mapPopupLabel">Price</div>
        <div class="mapPopupValue">SGD ${Number(leg.price || 0).toFixed(2)}</div>
      </div>
      <div class="mapPopupItem">
        <div class="mapPopupLabel">Distance</div>
        <div class="mapPopupValue">${Math.round(Number(leg.km || 0))} km</div>
      </div>
      <div class="mapPopupItem">
        <div class="mapPopupLabel">Departures</div>
        <div class="mapPopupValue">${(leg.departures && leg.departures.length) ? leg.departures.slice(0, 3).join(', ') : '—'}</div>
      </div>
    </div>
  </div>
`;

    const line = L.polyline(coords, {
      color: '#2563eb',
      weight: 7,
      opacity: 0.95,
      interactive: true
    }).addTo(map);

    line.bindTooltip(hoverText, {
      sticky: true,
      direction: 'top',
      opacity: 0.95
    });

    line.bindPopup(popupText);

    line.on('mouseover', function () {
      this.openTooltip();
    });

    line.on('mouseout', function () {
      this.closeTooltip();
    });

    routeLines.push(line);
  });

  points.forEach((p, idx) => {
    const isStart = idx === 0;
    const isEnd = idx === points.length - 1;

    const roleKey = isStart ? 'start' : isEnd ? 'end' : 'layover';
    const roleLabel = isStart ? 'Start airport' : isEnd ? 'Destination airport' : `Layover ${idx}`;

    const marker = L.marker([p.lat, p.lon], {
      icon: makeAirportIcon(roleKey),
      interactive: true
    }).addTo(map);

    const airportTitle = p.name && p.name !== p.label ? p.name : p.label;
    const airportSub = [p.city, p.country].filter(Boolean).join(', ');

    marker.bindTooltip(
      `<div><b>${p.code}</b>${airportSub ? ` — ${airportSub}` : ''}</div>`,
      {
        sticky: true,
        direction: 'top',
        opacity: 0.95
      }
    );

    marker.bindPopup(`
  <div class="mapPopup mapPopupCompact">
    <div class="mapPopupTitle">${airportTitle}</div>

    <div class="mapPopupList">
      <div class="mapPopupRow">
        <span class="mapPopupRowLabel">Code</span>
        <span class="mapPopupRowValue">${p.code}</span>
      </div>
      <div class="mapPopupRow">
        <span class="mapPopupRowLabel">Role</span>
        <span class="mapPopupRowValue">${roleLabel}</span>
      </div>
    </div>
  </div>
`);

    marker.on('mouseover', function () {
      this.openTooltip();
    });

    marker.on('mouseout', function () {
      this.closeTooltip();
    });

    markers.push(marker);
  });

  setTimeout(() => map.invalidateSize(), 0);
}

function setViewMoreVisible(show) {
  const btn = $('#viewMoreBtn');
  if (!btn) return;
  btn.style.display = show ? 'inline-flex' : 'none';
}

function renderEmptyState(message = 'No routes found for the current filters.') {
  const wrap = $('#options');
  const details = $('#details');
  if (wrap) {
    wrap.innerHTML = `<div class="emptyState">${message}</div>`;
  }
  if (details) {
    details.innerHTML = `<p class="detailsSub">${message}</p>`;
  }
  clearMap(true);
}

function renderOptions(options) {
  const wrap = $('#options');
  if (!wrap) return;
  wrap.innerHTML = '';

  if (!options || options.length === 0) {
    renderEmptyState();
    return;
  }

  options.forEach((o, idx) => {
    const div = document.createElement('div');
    div.className = 'card' + (idx === 0 ? ' selected' : '');
    div.dataset.id = String(o.id);

    div.innerHTML = `
      <div style="font-weight:900;">Option ${o.id}</div>
      <div class="route">${o.path.join(' → ')}</div>
      <div class="pills">
        <div class="pill"><div class="k">Price</div><div class="v">SGD ${o.price.toFixed(2)}</div></div>
        <div class="pill"><div class="k">Time</div><div class="v">${fmtDuration(o.minutes)}</div></div>
        <div class="pill"><div class="k">Distance</div><div class="v">${Math.round(o.km)} km</div></div>
        <div class="pill"><div class="k">Connections</div><div class="v">${o.hops}</div></div>
      </div>
    `;

    div.addEventListener('click', () => selectOption(o));
    wrap.appendChild(div);
  });

  selectOption(options[0]);
}

function selectOption(option) {
  document.querySelectorAll('.card').forEach(c => c.classList.remove('selected'));
  const card = document.querySelector(`.card[data-id="${option.id}"]`);
  if (card) card.classList.add('selected');

  drawRoute(option);
  renderDetails(option);
}

function fmtDuration(mins) {
  const m = Math.max(0, Number(mins || 0));
  const h = Math.floor(m / 60);
  const r = m % 60;
  if (h <= 0) return `${r}m`;
  if (r === 0) return `${h}h`;
  return `${h}h ${r}m`;
}

function addMinutesToHHMM(hhmm, addMin) {
  if (!hhmm || !/^\d{2}:\d{2}$/.test(hhmm)) return null;
  const [hh, mm] = hhmm.split(':').map(Number);
  const total = hh * 60 + mm + Number(addMin || 0);
  const wrapped = ((total % 1440) + 1440) % 1440;
  const nh = String(Math.floor(wrapped / 60)).padStart(2, '0');
  const nm = String(wrapped % 60).padStart(2, '0');
  return `${nh}:${nm}`;
}

function airlinesSummary(airlines) {
  if (!airlines || airlines.length === 0) return { names: 'Unknown', codes: '—' };
  const names = airlines.map(a => a.name).filter(Boolean).join(', ') || 'Unknown';
  const codes = airlines.map(a => a.code).filter(Boolean).join(', ') || '—';
  return { names, codes };
}

function renderDetails(option) {
  const d = $('#details');
  if (!d) return;

  const start = $('#start')?.value || '';
  const goal = $('#goal')?.value || '';
  const mode = $('#mode')?.value || '';
  const max_hops = $('#max_hops')?.value || '4';

  const params = new URLSearchParams({
    id: option.id,
    start,
    goal,
    mode,
    max_hops,
    limit: String(currentLimit),
    blocked: Array.from(avoidSelected).join(','),
    allowed: Array.from(airlineSelected).join(','),
  }).toString();

  const legsHtml = (option.legs || []).map((leg) => {
    const a = airlinesSummary(leg.airlines);
    const depart = (leg.departures && leg.departures.length) ? leg.departures[0] : '—';
    const arrive = depart !== '—' ? (addMinutesToHHMM(depart, leg.minutes) || '—') : '—';

    return `
      <div class="legRow">
        <div class="legTop">
          <div class="legLeft">
            <div class="legTime">${depart}</div>
            <div class="legCode">${leg.from_code}</div>
          </div>

          <div class="legMid">
            <div class="legCenterLine">
              <div class="legDash"></div>
              <div class="legPlane">✈</div>
              <div class="legDash"></div>
            </div>
            <div class="legDuration">${fmtDuration(leg.minutes)} • ${a.codes}</div>
          </div>

          <div class="legRight">
            <div class="legTime">${arrive}</div>
            <div class="legCode">${leg.to_code}</div>
          </div>
        </div>

        <div class="legSubLine">
          <div><b>${leg.from_name}</b> — ${leg.from_city}, ${leg.from_country}</div>
          <div><b>${leg.to_name}</b> — ${leg.to_city}, ${leg.to_country}</div>
        </div>

        <div class="legSubLine">
          <div><b>Airlines:</b> ${a.names}</div>
          <div><b>Departures:</b> ${(leg.departures && leg.departures.length) ? leg.departures.slice(0, 6).join(', ') : '—'}</div>
        </div>

        <div class="legBadges">
          <div class="legBadge">SGD ${Number(leg.price).toFixed(2)}</div>
          <div class="legBadge">${Math.round(Number(leg.km || 0))} km</div>
          <div class="legBadge">${fmtDuration(leg.minutes)}</div>
        </div>
      </div>
    `;
  }).join('');

  d.innerHTML = `
    <p class="detailsTitle">Selected route</p>
    <p class="detailsSub">${option.path.join(' → ')}</p>

    <div class="detailGrid">
      <div class="detailBox"><div class="k">Total price</div><div class="v">SGD ${option.price.toFixed(2)}</div></div>
      <div class="detailBox"><div class="k">Total time</div><div class="v">${fmtDuration(option.minutes)}</div></div>
      <div class="detailBox"><div class="k">Distance</div><div class="v">${Math.round(option.km)} km</div></div>
      <div class="detailBox"><div class="k">Connections</div><div class="v">${option.hops}</div></div>
    </div>

    <div class="divider"></div>

    <div style="display:flex; gap:10px; flex-wrap:wrap;">
      <a class="primary" href="/print?${params}" target="_blank" style="text-decoration:none;">Print itinerary</a>
    </div>

    <div class="divider"></div>

    <p class="detailsTitle">Leg details</p>
    <p class="detailsSub">Each leg is one clean row</p>
    ${legsHtml}
  `;
}

function buildList(containerId, items, getKey, getMain, getSub, selectedSet) {
  const container = $(containerId);
  if (!container) return;

  const frag = document.createDocumentFragment();

  items.forEach(item => {
    const key = getKey(item);

    const row = document.createElement('div');
    row.className = 'checkItem';

    const cb = document.createElement('input');
    cb.type = 'checkbox';
    cb.checked = selectedSet.has(key);
    cb.addEventListener('change', () => {
      if (cb.checked) selectedSet.add(key);
      else selectedSet.delete(key);
    });

    const text = document.createElement('div');
    const main = document.createElement('div');
    main.className = 'checkLabel';
    main.textContent = getMain(item);

    const sub = document.createElement('div');
    sub.className = 'checkSub';
    sub.textContent = getSub(item);

    text.appendChild(main);
    text.appendChild(sub);

    row.appendChild(cb);
    row.appendChild(text);
    frag.appendChild(row);
  });

  container.innerHTML = '';
  container.appendChild(frag);
}

function initFilterLists() {
  const airports = window.__AIRPORTS__ || [];
  const carriers = window.__CARRIER_CODES__ || [];

  const avoidSearch = $('#avoidSearch');
  const airlineSearch = $('#airlineSearch');

  const renderAvoid = () => {
    const q = (avoidSearch?.value || '').trim().toLowerCase();
    const filtered = !q ? airports : airports.filter(a =>
      (a.code || '').toLowerCase().includes(q) ||
      (a.label || '').toLowerCase().includes(q)
    );
    buildList(
      '#avoidList',
      filtered,
      (a) => a.code,
      (a) => `${a.code} — ${a.label.split('—').slice(1).join('—').trim() || a.label}`,
      (a) => a.label,
      avoidSelected
    );
  };

  const renderAirlines = () => {
    const q = (airlineSearch?.value || '').trim().toLowerCase();
    const filtered = !q ? carriers : carriers.filter(c => (c || '').toLowerCase().includes(q));
    buildList(
      '#airlinesList',
      filtered.map(c => ({ code: c })),
      (x) => x.code,
      (x) => x.code,
      () => 'Airline code',
      airlineSelected
    );
  };

  avoidSearch?.addEventListener('input', renderAvoid);
  airlineSearch?.addEventListener('input', renderAirlines);

  $('#clearAvoid')?.addEventListener('click', () => { avoidSelected.clear(); renderAvoid(); });
  $('#clearAirlines')?.addEventListener('click', () => { airlineSelected.clear(); renderAirlines(); });

  renderAvoid();
  renderAirlines();
}

async function search(resetLimit = false) {
  if (resetLimit) currentLimit = window.__DEFAULT_LIMIT__ || 6;

  const start = $('#start')?.value;
  const goal = $('#goal')?.value;
  const mode = $('#mode')?.value || 'Shortest';
  const max_hops = Number($('#max_hops')?.value || 4);

  const blocked = Array.from(avoidSelected);
  const allowed = Array.from(airlineSelected);

  if (!start || !goal) {
    alert('Please select both a start and destination airport.');
    return;
  }

  const res = await fetch('/api/search', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      start, goal, mode, max_hops, limit: currentLimit, blocked, allowed,
    })
  });

  const data = await res.json();
  if (!res.ok) {
    alert(data.error || 'Search failed');
    return;
  }

  setViewMoreVisible(!!data.has_more);
  renderOptions(data.options || []);
}

function initCollapsibles() {
  document.querySelectorAll('[data-collapse]').forEach((btn) => {
    const sel = btn.getAttribute('data-collapse');
    const body = sel ? document.querySelector(sel) : null;
    if (!body) return;

    const setOpen = (open) => {
      body.classList.toggle('is-collapsed', !open);
      btn.setAttribute('aria-expanded', String(open));
      btn.textContent = open ? 'Hide' : 'Show';
    };

    setOpen(true);

    btn.addEventListener('click', () => {
      const isOpen = !body.classList.contains('is-collapsed');
      setOpen(!isOpen);
    });
  });
}

window.addEventListener('DOMContentLoaded', () => {
  currentLimit = window.__DEFAULT_LIMIT__ || 6;

  initTomSelect();
  initSlider();
  initMap();
  initFilterLists();
  initCollapsibles();

  $('#searchBtn')?.addEventListener('click', () => search(true));

  $('#viewMoreBtn')?.addEventListener('click', () => {
    currentLimit = Math.min(currentLimit + 6, 60);
    search(false);
  });
});