// Aircraft from three feeds:
//   near      adsb.fi, 100 nautical miles around Munich, every 10 s
//   military  adsb.lol, worldwide, every 5 min
//   world     OpenSky, every 15 min (the free allowance)
// Every aircraft is drawn where its feed last reported it. Nothing is moved forward between reports,
// so the world view can be up to 15 minutes behind and the card says how old a position is.
import {$, ago, api, esc, local, now} from './util.js';

let near = [], mil = [], world = [], info = {}, theMap = null, isDark = false, shown = {aircraft: true};

// ---- gliding (the owner's decision of 14 Nov 2026, the one place where something is drawn ahead of its data) ----
// Between two reports, a nearby aircraft is drawn moving on along its last reported heading at its last
// reported ground speed. Never more than GLIDE_MAX seconds ahead; after that it stops where it is.
const GLIDE_MAX = 30;
function ahead(a, reportedAt, t) {
  const dt = Math.min(GLIDE_MAX, Math.max(0, t - reportedAt));
  if (!dt || a.gs_kt == null || a.track == null || a.alt_ft === 'ground') return [a.lon, a.lat];
  const d = a.gs_kt * 0.514444 * dt / 6371000, th = a.track * Math.PI / 180, la = a.lat * Math.PI / 180;
  const la2 = Math.asin(Math.sin(la) * Math.cos(d) + Math.cos(la) * Math.sin(d) * Math.cos(th));
  const lo2 = a.lon * Math.PI / 180 + Math.atan2(Math.sin(th) * Math.sin(d) * Math.cos(la), Math.cos(d) - Math.sin(la) * Math.sin(la2));
  return [lo2 * 180 / Math.PI, la2 * 180 / Math.PI];
}
const reportedAt = a => (info.aircraft_near?.data_time ?? 0) - (a.seen_pos_s ?? 0);
const shownAt = a => ahead(a, reportedAt(a), now());

// A great-circle line between two points, split where it crosses the date line.
function arc(a, b, n = 64) {
  const r = Math.PI / 180, [l1, p1, l2, p2] = [a[0] * r, a[1] * r, b[0] * r, b[1] * r];
  const d = 2 * Math.asin(Math.sqrt(Math.sin((p2 - p1) / 2) ** 2 + Math.cos(p1) * Math.cos(p2) * Math.sin((l2 - l1) / 2) ** 2));
  if (!d) return [];
  const lines = [[]]; let last = null;
  for (let i = 0; i <= n; i++) {
    const f = i / n, A = Math.sin((1 - f) * d) / Math.sin(d), B = Math.sin(f * d) / Math.sin(d);
    const x = A * Math.cos(p1) * Math.cos(l1) + B * Math.cos(p2) * Math.cos(l2), y = A * Math.cos(p1) * Math.sin(l1) + B * Math.cos(p2) * Math.sin(l2), z = A * Math.sin(p1) + B * Math.sin(p2);
    const lon = Math.atan2(y, x) / r, lat = Math.atan2(z, Math.hypot(x, y)) / r;
    if (last !== null && Math.abs(lon - last) > 180) lines.push([]);
    lines[lines.length - 1].push([lon, lat]); last = lon;
  }
  return lines.filter(l => l.length > 1);
}

// ---- icons, drawn here so no image files or icon fonts are needed (pointing north) ----
const PLANE = 'M32 3c2.6 0 3.8 5 3.8 10.5V25l22.7 14.2v5.3L35.8 37.6v14.2l6.7 5.4v4L32 58.2 21.5 61.2v-4l6.7-5.4V37.6L5.5 44.5v-5.3L28.2 25V13.5C28.200 8 29.4 3 32 3z';
const HELI = 'M32 14c4.200 0 7 3.600 7 9v9.500l2 13.500h7v4H16v-4h7l2-13.500V23c0-5.400 2.800-9 7-9zM30.500 46h3v12h-3zM4 20.500h56v3.500H4z';
function icon(path, fill, edge, px) {
  const c = document.createElement('canvas'); c.width = c.height = px;
  const x = c.getContext('2d'), p = new Path2D(path);
  x.scale(px / 64, px / 64);
  x.lineJoin = 'round'; x.lineWidth = 5; x.strokeStyle = edge; x.stroke(p);
  x.fillStyle = fill; x.fill(p);
  return x.getImageData(0, 0, px, px);
}
function icons(map, dark) {
  const edge = dark ? '#1c1c1e' : '#ffffff';
  const set = {'ww-plane': [PLANE, civil.color[+dark]], 'ww-heli': [HELI, civil.color[+dark]],
               'ww-plane-mil': [PLANE, military.color[+dark]], 'ww-heli-mil': [HELI, military.color[+dark]],
               'ww-plane-far': [PLANE, dark ? '#7c7c80' : '#8e8e93']};
  for (const [name, [path, fill]] of Object.entries(set)) {
    const img = icon(path, fill, edge, 64);
    if (map.hasImage(name)) map.updateImage(name, img); else map.addImage(name, img, {pixelRatio: 2});
  }
}

const heli = a => a.category === 'A7';
const feature = (a, kind, at) => ({type: 'Feature', geometry: {type: 'Point', coordinates: at || [a.lon, a.lat]},
  properties: {id: a.hex, track: a.track ?? 0, label: a.flight || a.reg || '', icon: (heli(a) ? 'ww-heli' : 'ww-plane') + (kind === 'mil' ? '-mil' : '')}});
const empty = {type: 'FeatureCollection', features: []};

function symbol(id, source, size, extra = {}) {
  return {id, type: 'symbol', source, layout: {'icon-image': ['get', 'icon'], 'icon-size': size, 'icon-rotate': ['get', 'track'],
    'icon-rotation-alignment': 'map', 'icon-allow-overlap': true, 'icon-ignore-placement': true, ...extra}};
}
const label = {'text-field': ['step', ['zoom'], '', 6.5, ['get', 'label']], 'text-font': ['Noto Sans Bold'], 'text-size': 10.5,
  'text-offset': [0, 1.5], 'text-anchor': 'top', 'text-optional': true, 'text-allow-overlap': false};

function find(id) {
  const n = near.find(a => a.hex === id); if (n) return {a: n, from: 'near'};
  const m = mil.find(a => a.hex === id); if (m) return {a: m, from: 'military'};
  const w = world.find(a => a.hex === id); if (w) return {a: w, from: 'world'};
  return null;
}

const ft = v => v == null ? 'not reported' : v === 'ground' ? 'on the ground' : `${Number(v).toLocaleString('en-GB')} ft <span class="soft">(${(v * 0.3048 / 1000).toFixed(1)} km)</span>`;
const kt = v => v == null ? 'not reported' : `${Math.round(v)} kt <span class="soft">(${Math.round(v * 1.852)} km/h)</span>`;
const SOURCES = {near: ['adsb.fi', 'aircraft_near'], military: ['adsb.lol', 'aircraft_military'], world: ['OpenSky Network', 'aircraft_world']};

function detail(id) {
  const hit = find(id);
  if (!hit) return null;
  const {a, from} = hit, f = info[SOURCES[from][1]];
  const isMil = from === 'military' || a.military;
  let rows;
  if (from === 'world') {   // OpenSky reports metric units and fewer fields
    rows = `<dt>Altitude</dt><dd>${a.on_ground ? 'on the ground' : a.alt_m == null ? 'not reported' : ft(Math.round(a.alt_m / 0.3048 / 25) * 25)}</dd>
      <dt>Ground speed</dt><dd>${a.gs_ms == null ? 'not reported' : kt(a.gs_ms / 0.514444)}</dd>
      <dt>Heading</dt><dd>${a.track == null ? 'not reported' : Math.round(a.track) + '°'}</dd>
      <dt>Position reported</dt><dd>${local(a.last_contact)} <span class="soft">(${ago(a.last_contact)})</span></dd>`;
  } else {
    const at = f.data_time - (a.seen_pos_s ?? 0);
    rows = `<dt>Type</dt><dd>${esc(a.type || 'not reported')}${a.reg ? ` <span class="soft">· ${esc(a.reg)}</span>` : ''}</dd>
      <dt>Altitude</dt><dd>${ft(a.alt_ft)}</dd>
      <dt>Ground speed</dt><dd>${kt(a.gs_kt)}</dd>
      <dt>Heading</dt><dd>${a.track == null ? 'not reported' : Math.round(a.track) + '°'}</dd>
      ${a.squawk ? `<dt>Transponder code</dt><dd>${esc(a.squawk)}${{7500: ' (hijack)', 7600: ' (radio failure)', 7700: ' (emergency)'}[a.squawk] || ''}</dd>` : ''}
      <dt>Position reported</dt><dd>${local(at)} <span class="soft">(${ago(at)})</span></dd>`;
  }
  const flags = [isMil && 'Military', a.ladd && 'On the FAA\'s limited-display list', a.pia && 'Privacy address'].filter(Boolean).join(' · ');
  return `<p class="eyebrow">${isMil ? 'Military aircraft' : heli(a) ? 'Helicopter' : 'Aircraft'}</p>
    <h2>${esc(a.flight || a.reg || a.hex.toUpperCase())}</h2>
    <p class="where" id="route" data-callsign="${esc(a.flight || '')}">${a.flight ? 'Looking up the route' : 'No callsign reported'}</p>
    <dl>${rows}<dt>Transponder address</dt><dd>${esc(a.hex.toUpperCase())}</dd></dl>
    ${flags ? `<p class="source">${flags}.</p>` : ''}
    <a class="link" href="https://globe.adsb.fi/?icao=${esc(a.hex)}" target="_blank" rel="noopener">Follow on adsb.fi</a>
    <p class="source">Source: ${SOURCES[from][0]}, fetched ${ago(f.fetched)}. ${from === 'near' ? `Between reports it is drawn moving on along its last heading and speed, at most ${GLIDE_MAX} seconds ahead; that part is an estimate. ` : 'The aircraft is drawn where it last reported; it has kept moving since. '}${from !== 'world' ? 'The solid line joins the positions we received for it in the last 3 hours' + (from === 'military' ? ' (one every 5 minutes, so it cuts corners)' : '') + '. A dashed line, when there is one, joins the two airports of its usual route and is not its actual path.' : ''}${from === 'world' ? ' The world view refreshes every 15 minutes.' : ''}</p>`;
}

// The route comes from a second, crowd-sourced source and is looked up only when a card is opened.
export async function fillRoute() {
  const el = $('#route'); if (!el || !el.dataset.callsign || el.dataset.done) return;
  el.dataset.done = '1';
  const cs = el.dataset.callsign;
  try {
    const r = await api('/api/route/' + encodeURIComponent(cs));
    const el2 = $('#route'); if (!el2 || el2.dataset.callsign !== cs) return;
    if (!r.route) { el2.textContent = military.owns(sel) ? 'No published route, as usual for military flights' : 'Route not known to adsbdb'; return; }
    const p = x => `${esc(x.city || x.name)}${x.iata ? ' (' + esc(x.iata) + ')' : ''}`;
    el2.innerHTML = `${p(r.route.origin)} to ${p(r.route.destination)}<span class="sub">${esc(r.route.airline || '')}${r.route.airline ? ' · ' : ''}usual route for this callsign, from adsbdb, can be wrong</span>`;
    if (r.route.origin.lat != null && r.route.destination.lat != null) { route = {...r.route, for: sel}; drawExtras(); }
  } catch (e) { const el2 = $('#route'); if (el2) el2.textContent = 'Route lookup failed'; }
}

function render(map) {
  const fresh = new Set([...near, ...mil].map(a => a.hex));   // the fresher feeds win over the 15-minute world view
  map.getSource('ww-air-world').setData({type: 'FeatureCollection', features: world.filter(a => !fresh.has(a.hex) && !a.on_ground).map(a => (
    {type: 'Feature', geometry: {type: 'Point', coordinates: [a.lon, a.lat]}, properties: {id: a.hex, track: a.track ?? 0, icon: 'ww-plane-far'}}))});
  glide();
  drawExtras();
}

function glide() {
  const map = theMap; if (!map || !map.getSource('ww-air-near')) return;
  const milHex = new Set(mil.map(a => a.hex));
  map.getSource('ww-air-near').setData({type: 'FeatureCollection', features: near.filter(a => !milHex.has(a.hex) && !a.military).map(a => feature(a, 'civil', shownAt(a)))});
  map.getSource('ww-air-mil').setData({type: 'FeatureCollection', features: [...mil.map(a => feature(a, 'mil')), ...near.filter(a => a.military && !milHex.has(a.hex)).map(a => feature(a, 'mil', shownAt(a)))]});
}

// ---- for the selected aircraft: the path we saw it fly, and its usual route ----
let sel = null, route = null, seen = null;   // seen: the positions the server received for the selected aircraft, last 3 hours
async function loadTrail() {
  const id = sel; if (!id) return;
  try { const r = await api('/api/trail/' + encodeURIComponent(id)); if (sel === id) { seen = {hex: id, points: r.points}; drawExtras(); } } catch (e) { /* the line just stays as it was */ }
}
setInterval(loadTrail, 15000);
function drawExtras() {
  const map = theMap; if (!map?.getSource('ww-air-extra')) return;
  const feats = [];
  if (seen && seen.hex === sel && seen.points.length > 1) {
    const lines = [[]]; let last = null;                     // split where the path crosses the date line
    for (const [, lon, lat] of seen.points) { if (last !== null && Math.abs(lon - last) > 180) lines.push([]); lines[lines.length - 1].push([lon, lat]); last = lon; }
    feats.push({type: 'Feature', geometry: {type: 'MultiLineString', coordinates: lines.filter(l => l.length > 1)}, properties: {kind: 'trail'}});
  }
  if (route && route.for === sel) {
    const o = route.origin, d = route.destination;
    feats.push({type: 'Feature', geometry: {type: 'MultiLineString', coordinates: arc([o.lon, o.lat], [d.lon, d.lat])}, properties: {kind: 'route'}});
    for (const p of [o, d]) feats.push({type: 'Feature', geometry: {type: 'Point', coordinates: [p.lon, p.lat]}, properties: {kind: 'airport', label: p.iata || p.city || ''}});
  }
  map.getSource('ww-air-extra').setData({type: 'FeatureCollection', features: feats});
}
export function select(id) { if (id !== sel) seen = null; sel = id; if (route && route.for !== id) route = null; drawExtras(); loadTrail(); }

export const civil = {
  id: 'aircraft', title: 'Aircraft', color: ['#5856d6', '#7d7aff'], feeds: {aircraft_near: 10, aircraft_world: 120}, layers: ['ww-air-world', 'ww-air-route', 'ww-air-trail', 'ww-air-airport', 'ww-air-near'],
  addTo(map) {
    theMap = map;
    for (const s of ['ww-air-world', 'ww-air-near', 'ww-air-mil']) map.addSource(s, {type: 'geojson', data: empty});
    map.addLayer(symbol('ww-air-world', 'ww-air-world', ['interpolate', ['linear'], ['zoom'], 1, 0.22, 5, 0.42, 9, 0.6]));
    map.setPaintProperty('ww-air-world', 'icon-opacity', ['interpolate', ['linear'], ['zoom'], 1, 0.55, 5, 0.9]);
    map.addSource('ww-air-extra', {type: 'geojson', data: empty});
    map.addLayer({id: 'ww-air-route', type: 'line', source: 'ww-air-extra', filter: ['==', ['get', 'kind'], 'route'], paint: {'line-width': 2, 'line-dasharray': [2.5, 2.5], 'line-opacity': 0.9}});
    map.addLayer({id: 'ww-air-trail', type: 'line', source: 'ww-air-extra', filter: ['==', ['get', 'kind'], 'trail'], layout: {'line-cap': 'round', 'line-join': 'round'}, paint: {'line-width': 2.5}});
    map.addLayer({id: 'ww-air-airport', type: 'symbol', source: 'ww-air-extra', filter: ['==', ['get', 'kind'], 'airport'],
      layout: {'text-field': ['get', 'label'], 'text-font': ['Noto Sans Bold'], 'text-size': 11, 'text-allow-overlap': true}});
    map.addLayer(symbol('ww-air-near', 'ww-air-near', ['interpolate', ['linear'], ['zoom'], 1, 0.22, 5, 0.46, 9, 0.8], label));
    setInterval(() => { if (!document.hidden && (shown.aircraft || shown.military)) glide(); }, 200);
  },
  paint(map, dark) {
    isDark = dark; icons(map, dark);
    if (map.getLayer('ww-air-route')) {
      map.setPaintProperty('ww-air-route', 'line-color', civil.color[+dark]); map.setPaintProperty('ww-air-trail', 'line-color', civil.color[+dark]);
      map.setPaintProperty('ww-air-airport', 'text-color', dark ? '#e5e5ea' : '#3a3a3c'); map.setPaintProperty('ww-air-airport', 'text-halo-color', dark ? '#1c1c1e' : '#ffffff'); map.setPaintProperty('ww-air-airport', 'text-halo-width', 1.5);
    }
    for (const l of ['ww-air-near', 'ww-air-mil']) if (map.getLayer(l)) {
      map.setPaintProperty(l, 'text-color', dark ? '#e5e5ea' : '#3a3a3c');
      map.setPaintProperty(l, 'text-halo-color', dark ? '#1c1c1e' : '#ffffff');
      map.setPaintProperty(l, 'text-halo-width', 1.2);
    }
  },
  onData(feed, d) {
    info[feed] = d;
    if (feed !== 'aircraft_near') { world = d.payload.aircraft; return; }
    near = d.payload.aircraft;
  },
  visible(on) { shown.aircraft = on; },
  render,
  count: () => new Set([...world.filter(a => !a.on_ground), ...near].map(a => a.hex)).size,
  rows: () => [],
  locate(id) { const h = find(id); return h && (h.from === 'near' ? shownAt(h.a) : [h.a.lon, h.a.lat]); },
  ring: () => 15,
  moving: true,
  detail,
  owns: id => !!find(id) && !military.owns(id),
};

export const military = {
  id: 'military', title: 'Military', color: ['#af52de', '#da8fff'], feeds: {aircraft_military: 60}, layers: ['ww-air-mil'],
  addTo(map) { map.addLayer(symbol('ww-air-mil', 'ww-air-mil', ['interpolate', ['linear'], ['zoom'], 1, 0.34, 5, 0.6, 9, 0.85], label)); },
  paint(map, dark) { civil.paint(map, dark); },
  onData(feed, d) { info[feed] = d; mil = d.payload.aircraft; },
  visible(on) { shown.military = on; },
  moving: true,
  render,
  count: () => mil.length,
  rows: () => [],
  locate: id => civil.locate(id),
  ring: () => 16,
  detail,
  owns: id => mil.some(a => a.hex === id) || near.some(a => a.hex === id && a.military),
};
