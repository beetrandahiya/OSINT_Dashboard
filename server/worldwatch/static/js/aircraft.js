// Aircraft. All of them look the same on the map; what differs is how fresh their position is:
//   view      adsb.fi, for the part of the map you are zoomed in on (up to 250 nautical miles across the
//             centre), fetched about every 10 seconds while you look
//   military  adsb.lol, worldwide, every 5 minutes
//   world     OpenSky, everything else, every 20 minutes (the free allowance)
// The card of each aircraft says where its position came from and how old it is.
import {$, ago, api, esc, local, now} from './util.js';

let view = [], viewInfo = null, mil = [], world = [], info = {}, theMap = null, shown = {aircraft: true, military: true};
const VIEW_MIN_ZOOM = 5.2;   // below this the screen holds more than adsb.fi's 250-mile circle, so only the world feed is used

// ---- gliding (the owner's decision of 14 Nov 2026, the one place where something is drawn ahead of its data) ----
// Between two reports, an aircraft from the 10-second feed is drawn moving on along its last reported heading at
// its last reported ground speed. Never more than GLIDE_MAX seconds ahead; after that it stops where it is.
const GLIDE_MAX = 30;
function ahead(a, reportedAt, t) {
  const dt = Math.min(GLIDE_MAX, Math.max(0, t - reportedAt));
  if (!dt || a.gs_kt == null || a.track == null || a.alt_ft === 'ground') return [a.lon, a.lat];
  const d = a.gs_kt * 0.514444 * dt / 6371000, th = a.track * Math.PI / 180, la = a.lat * Math.PI / 180;
  const la2 = Math.asin(Math.sin(la) * Math.cos(d) + Math.cos(la) * Math.sin(d) * Math.cos(th));
  const lo2 = a.lon * Math.PI / 180 + Math.atan2(Math.sin(th) * Math.sin(d) * Math.cos(la), Math.cos(d) - Math.sin(la) * Math.sin(la2));
  return [lo2 * 180 / Math.PI, la2 * 180 / Math.PI];
}
const reportedAt = a => (viewInfo?.data_time ?? 0) - (a.seen_pos_s ?? 0);
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
function split(points) {   // a flown path as map lines, split at the date line
  const lines = [[]]; let last = null;
  for (const [lon, lat] of points) { if (last !== null && Math.abs(lon - last) > 180) lines.push([]); lines[lines.length - 1].push([lon, lat]); last = lon; }
  return lines.filter(l => l.length > 1);
}

// ---- icons, drawn here so no image files or icon fonts are needed (pointing north) ----
const PLANE = 'M32 3c2.6 0 3.8 5 3.8 10.5V25l22.7 14.2v5.3L35.8 37.6v14.2l6.7 5.4v4L32 58.2 21.5 61.2v-4l6.7-5.4V37.6L5.5 44.5v-5.3L28.2 25V13.5C28.2 8 29.4 3 32 3z';
const HELI = 'M32 14c4.2 0 7 3.6 7 9v9.5l2 13.5h7v4H16v-4h7l2-13.5V23c0-5.4 2.8-9 7-9zM30.5 46h3v12h-3zM4 20.5h56v3.5H4z';
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
               'ww-plane-mil': [PLANE, military.color[+dark]], 'ww-heli-mil': [HELI, military.color[+dark]]};
  for (const [name, [path, fill]] of Object.entries(set)) {
    const img = icon(path, fill, edge, 64);
    if (map.hasImage(name)) map.updateImage(name, img); else map.addImage(name, img, {pixelRatio: 2});
  }
}

const heli = a => a.category === 'A7';
const feature = (a, kind, at) => ({type: 'Feature', geometry: {type: 'Point', coordinates: at || [a.lon, a.lat]},
  properties: {id: a.hex, track: a.track ?? 0, label: a.flight || a.reg || '', icon: (heli(a) ? 'ww-heli' : 'ww-plane') + (kind === 'mil' ? '-mil' : '')}});
const empty = {type: 'FeatureCollection', features: []};
const SIZE = ['interpolate', ['linear'], ['zoom'], 1, 0.22, 5, 0.46, 9, 0.8];
const label = {'text-field': ['step', ['zoom'], '', 6.5, ['get', 'label']], 'text-font': ['Noto Sans Bold'], 'text-size': 10.5,
  'text-offset': [0, 1.5], 'text-anchor': 'top', 'text-optional': true, 'text-allow-overlap': false};
const symbol = (id, source) => ({id, type: 'symbol', source, layout: {'icon-image': ['get', 'icon'], 'icon-size': SIZE, 'icon-rotate': ['get', 'track'],
  'icon-rotation-alignment': 'map', 'icon-allow-overlap': true, 'icon-ignore-placement': true, ...label}});

function find(id) {
  const v = view.find(a => a.hex === id); if (v) return {a: v, from: 'view'};
  const m = mil.find(a => a.hex === id); if (m) return {a: m, from: 'military'};
  const w = world.find(a => a.hex === id); if (w) return {a: w, from: 'world'};
  return null;
}
const position = h => h.from === 'view' ? shownAt(h.a) : [h.a.lon, h.a.lat];

// ---- drawing ----
function glide() {
  const map = theMap; if (!map || !map.getSource('ww-air')) return;
  const milHex = new Set(mil.map(a => a.hex)), viewHex = new Set(view.map(a => a.hex));
  const feats = view.filter(a => !milHex.has(a.hex) && !a.military).map(a => feature(a, 'civil', shownAt(a)));
  for (const a of world) if (!viewHex.has(a.hex) && !milHex.has(a.hex) && !a.on_ground) feats.push(feature(a, 'civil'));
  map.getSource('ww-air').setData({type: 'FeatureCollection', features: feats});
  map.getSource('ww-air-mil').setData({type: 'FeatureCollection', features: [...mil.filter(a => !viewHex.has(a.hex)).map(a => feature(a, 'mil')),
    ...view.filter(a => a.military || milHex.has(a.hex)).map(a => feature(a, 'mil', shownAt(a)))]});
  drawExtras();
}

// ---- live aircraft for the area on screen ----
let asking = false;
async function loadView() {
  const map = theMap;
  if (!map || asking || document.hidden || !(shown.aircraft || shown.military)) return;
  if (map.getZoom() < VIEW_MIN_ZOOM) { if (view.length) { view = []; viewInfo = null; glide(); } return; }
  const c = map.getCenter(), b = map.getBounds();
  const km = 111.2 * Math.hypot(b.getNorth() - c.lat, (b.getEast() - c.lng) * Math.cos(c.lat * Math.PI / 180));
  asking = true;
  try {
    const d = await api(`/api/aircraft/area?lat=${c.lat.toFixed(3)}&lon=${c.lng.toFixed(3)}&r=${Math.min(250, Math.ceil(km / 1.852))}`);
    viewInfo = d; view = d.aircraft; glide();
  } catch (e) { /* the feeds card shows adsb.fi failing; the world positions stay on screen */ }
  asking = false;
}

// ---- for the selected aircraft: the path it has flown, and a line to where it is going ----
let sel = null, route = null, flown = null;
async function loadTrack() {
  const id = sel; if (!id) return;
  try { const r = await api('/api/track/' + encodeURIComponent(id)); if (sel === id) { flown = {hex: id, ...r}; drawExtras(); noteTrack(); } } catch (e) { /* the line stays as it was */ }
}
setInterval(loadTrack, 45000);
function noteTrack() {
  const el = $('#tracknote'); if (!el || !flown || flown.hex !== sel) return;
  el.textContent = flown.points.length > 1 ? `Solid line: the path it has flown, from ${flown.source}.` : `No flown path to draw${flown.note ? ' (' + flown.note + ')' : ''}.`;
}
function drawExtras() {
  const map = theMap; if (!map?.getSource('ww-air-extra')) return;
  const feats = [], hit = sel && find(sel), at = hit && position(hit);
  if (hit && flown && flown.hex === sel && flown.points.length > 1) {
    const pts = flown.points.map(p => [p[1], p[2]]);
    pts.push(at);                                             // join the path to where the aircraft is drawn now
    feats.push({type: 'Feature', geometry: {type: 'MultiLineString', coordinates: split(pts)}, properties: {kind: 'trail'}});
  }
  if (hit && route && route.for === sel && route.fits) {
    const o = route.origin, d = route.destination;
    feats.push({type: 'Feature', geometry: {type: 'MultiLineString', coordinates: arc(at, [d.lon, d.lat])}, properties: {kind: 'route'}});
    for (const p of [o, d]) feats.push({type: 'Feature', geometry: {type: 'Point', coordinates: [p.lon, p.lat]}, properties: {kind: 'airport', label: p.iata || p.city || ''}});
  }
  map.getSource('ww-air-extra').setData({type: 'FeatureCollection', features: feats});
}
export function select(id) {
  if (id !== sel) { flown = null; route = null; }
  sel = id; drawExtras(); loadTrack();
}

// ---- the card ----
const ft = v => v == null ? 'not reported' : v === 'ground' ? 'on the ground' : `${Number(v).toLocaleString('en-GB')} ft <span class="soft">(${(v * 0.3048 / 1000).toFixed(1)} km)</span>`;
const kt = v => v == null ? 'not reported' : `${Math.round(v)} kt <span class="soft">(${Math.round(v * 1.852)} km/h)</span>`;
const SOURCE = {view: 'adsb.fi', military: 'adsb.lol', world: 'OpenSky Network'};

function detail(id) {
  const hit = find(id);
  if (!hit) return null;
  const {a, from} = hit, f = from === 'view' ? viewInfo : info[from === 'military' ? 'aircraft_military' : 'aircraft_world'];
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
  const fresh = from === 'view' ? `Between reports it is drawn moving on along its last heading and speed, at most ${GLIDE_MAX} seconds ahead; that part is an estimate.`
    : from === 'military' ? 'This feed refreshes every 5 minutes; the aircraft is drawn where it last reported and has kept moving since. Zoom in on it for live positions.'
    : 'The world view refreshes every 20 minutes; the aircraft is drawn where it last reported and has kept moving since. Zoom in on it for live positions.';
  return `<div class="photo" id="photo" data-hex="${esc(a.hex)}"></div>
    <p class="eyebrow">${isMil ? 'Military aircraft' : heli(a) ? 'Helicopter' : 'Aircraft'}</p>
    <h2>${esc(a.flight || a.reg || a.hex.toUpperCase())}</h2>
    <p class="where" id="route" data-callsign="${esc(a.flight || '')}">${a.flight ? 'Looking up the route' : 'No callsign reported'}</p>
    <dl>${rows}<dt>Transponder address</dt><dd>${esc(a.hex.toUpperCase())}</dd></dl>
    ${flags ? `<p class="source">${flags}.</p>` : ''}
    <a class="link" href="https://globe.adsb.fi/?icao=${esc(a.hex)}" target="_blank" rel="noopener">Follow on adsb.fi</a>
    <p class="source">Position: ${SOURCE[from]}, fetched ${ago(f.fetched)}. ${fresh}</p>
    <p class="source" id="tracknote"></p>`;
}

// Route and photo come from two more sources and are looked up only when a card is opened.
export async function fillRoute() {
  noteTrack();
  fillPhoto();
  const el = $('#route'); if (!el || !el.dataset.callsign || el.dataset.done) return;
  el.dataset.done = '1';
  const cs = el.dataset.callsign, id = sel, hit = find(id), at = hit && position(hit);
  try {
    const r = await api(`/api/route/${encodeURIComponent(cs)}` + (at ? `?lat=${at[1].toFixed(3)}&lon=${at[0].toFixed(3)}${hit.a.track != null ? '&track=' + Math.round(hit.a.track) : ''}` : ''));
    const now2 = $('#route'); if (!now2 || now2.dataset.callsign !== cs || sel !== id) return;
    if (!r.route) { now2.textContent = military.owns(id) ? 'No published route, as usual for military flights' : 'Route not known to adsbdb'; return; }
    const p = x => `${esc(x.city || x.name)}${x.iata ? ' (' + esc(x.iata) + ')' : ''}`;
    if (r.fits === false) {
      now2.innerHTML = `Route unknown<span class="sub">adsbdb lists ${p(r.route.origin)} to ${p(r.route.destination)} for this callsign, but ${esc(r.why)}, so it is not shown as the route.</span>`;
      return;
    }
    now2.innerHTML = `${p(r.route.origin)} to ${p(r.route.destination)}<span class="sub">${esc(r.route.airline || '')}${r.route.airline ? ' · ' : ''}usual route for this callsign, from adsbdb. Dashed line: straight to the destination, not the planned path.</span>`;
    route = {...r.route, fits: true, for: id}; drawExtras();
  } catch (e) { const now2 = $('#route'); if (now2) now2.textContent = 'Route lookup failed'; }
}
const photos = new Map();
async function fillPhoto() {
  const el = $('#photo'); if (!el || el.dataset.done) return;
  el.dataset.done = '1';
  const hex = el.dataset.hex;
  if (!photos.has(hex)) { try { photos.set(hex, (await api('/api/photo/' + hex)).photo || null); } catch (e) { return; } }
  const ph = photos.get(hex), now2 = $('#photo');
  if (!ph || !now2 || now2.dataset.hex !== hex) return;
  now2.innerHTML = `<a href="${esc(ph.link)}" target="_blank" rel="noopener"><img src="${esc(ph.src)}" alt="Photo of this aircraft" loading="lazy"></a><span>Photo: ${esc(ph.photographer)}, planespotters.net</span>`;
}

export const civil = {
  id: 'aircraft', title: 'Aircraft', color: ['#5856d6', '#7d7aff'], feeds: {aircraft_world: 120}, layers: ['ww-air'],
  addTo(map) {
    theMap = map;
    for (const s of ['ww-air', 'ww-air-mil', 'ww-air-extra']) map.addSource(s, {type: 'geojson', data: empty});
    map.addLayer({id: 'ww-air-route', type: 'line', source: 'ww-air-extra', filter: ['==', ['get', 'kind'], 'route'], paint: {'line-width': 2, 'line-dasharray': [2.5, 2.5], 'line-opacity': 0.9}});
    map.addLayer({id: 'ww-air-trail', type: 'line', source: 'ww-air-extra', filter: ['==', ['get', 'kind'], 'trail'], layout: {'line-cap': 'round', 'line-join': 'round'}, paint: {'line-width': 2.5}});
    map.addLayer({id: 'ww-air-airport', type: 'symbol', source: 'ww-air-extra', filter: ['==', ['get', 'kind'], 'airport'],
      layout: {'text-field': ['get', 'label'], 'text-font': ['Noto Sans Bold'], 'text-size': 11, 'text-allow-overlap': true}});
    map.addLayer(symbol('ww-air', 'ww-air'));
    setInterval(() => { if (!document.hidden && (shown.aircraft || shown.military) && view.length) glide(); }, 200);
    setInterval(loadView, 10000);
    let t = null;
    map.on('moveend', () => { clearTimeout(t); t = setTimeout(loadView, 600); });   // a moment after the map stops moving
  },
  paint(map, dark) {
    icons(map, dark);
    const ink = dark ? '#e5e5ea' : '#3a3a3c', halo = dark ? '#1c1c1e' : '#ffffff';
    for (const l of ['ww-air', 'ww-air-mil', 'ww-air-airport']) if (map.getLayer(l)) {
      map.setPaintProperty(l, 'text-color', ink); map.setPaintProperty(l, 'text-halo-color', halo); map.setPaintProperty(l, 'text-halo-width', 1.3);
    }
    if (map.getLayer('ww-air-route')) for (const l of ['ww-air-route', 'ww-air-trail']) map.setPaintProperty(l, 'line-color', civil.color[+dark]);
  },
  onData(feed, d) { info[feed] = d; world = d.payload.aircraft; },
  render: glide,
  visible(on) { shown.aircraft = on; if (on) loadView(); },
  count: () => new Set([...world.filter(a => !a.on_ground), ...view].map(a => a.hex)).size,
  rows: () => [],
  locate(id) { const h = find(id); return h && position(h); },
  ring: () => 15,
  moving: true,
  detail,
  owns: id => !!find(id) && !military.owns(id),
};

export const military = {
  id: 'military', title: 'Military', color: ['#af52de', '#da8fff'], feeds: {aircraft_military: 60}, layers: ['ww-air-mil'],
  addTo(map) { map.addLayer(symbol('ww-air-mil', 'ww-air-mil')); },
  paint(map, dark) { civil.paint(map, dark); },
  onData(feed, d) { info[feed] = d; mil = d.payload.aircraft; },
  render: glide,
  visible(on) { shown.military = on; if (on) loadView(); },
  count: () => mil.length,
  rows: () => [],
  locate: id => civil.locate(id),
  ring: () => 16,
  moving: true,
  detail,
  owns: id => mil.some(a => a.hex === id) || view.some(a => a.hex === id && a.military),
};
