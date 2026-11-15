// Aircraft. All of them look the same on the map; what differs is how fresh their position is:
//   view      adsb.fi, for the part of the map you are zoomed in on (up to 250 nautical miles across the
//             centre), fetched about every 10 seconds while you look
//   military  adsb.lol, worldwide, every 5 minutes
//   world     OpenSky, everything else, every 20 minutes (the free allowance)
// The card of each aircraft says where its position came from and how old it is.
import {$, ago, api, esc, local, now} from './util.js';
import {planeFlag, emoji} from './flags.js';

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

// ---- icons, drawn here so no image files or icon fonts are needed (all pointing north) ----
// The shape follows the category the aircraft itself broadcasts. The 20-minute world feed carries no
// category, so aircraft known only from it get the plain airliner shape.
const SHAPES = {
  jet:     'M32 3c2.6 0 3.8 5 3.8 10.5V25l22.7 14.2v5.3L35.8 37.6v14.2l6.7 5.4v4L32 58.2 21.5 61.2v-4l6.7-5.4V37.6L5.5 44.5v-5.3L28.2 25V13.5C28.2 8 29.4 3 32 3z',
  heavy:   'M32 2c3.2 0 4.6 5 4.6 11v9.5L62 42v6l-25.4-8V51l8.4 6.2v4.3L32 58 19 61.5v-4.3l8.4-6.2V40L2 48v-6l25.4-19.5V13c0-6 1.4-11 4.6-11zM44 24.5h4v8h-4zM52 30.5h4v8h-4zM16 24.5h4v8h-4zM8 30.5h4v8h-4z',
  prop:    'M32 7c1.900 0 2.900 3 2.900 7v6.500h22.600v7l-22.600 3v14.500l7.500 3.500v4L32 51l-10.400 1.500v-4l7.500-3.500V30.500l-22.600-3v-7h22.600V14c0-4 1-7 2.900-7zM27 4.500h10v2.500H27z',
  fighter: 'M32 3c1.600 0 2.600 4.500 3.200 10l1.300 12L55 46.500v5l-17-3.500.4 6.500 6.100 4v3.500L32 58.500 19.500 62v-3.500l6.100-4 .4-6.500-17 3.500v-5L27.500 25l1.300-12C29.400 7.500 30.400 3 32 3z',
  heli:    'M32 12c5 0 8 5 8 11 0 6-3 10-5.5 12L33.5 54h-3L29.5 35C27 33 24 29 24 23c0-6 3-11 8-11zM25 50h14v3.5H25zM11.9 5.1L14.1 2.9 52.1 40.9 49.9 43.1zM49.9 2.9L52.1 5.1 14.1 43.1 11.9 40.9z',
  glider:  'M32 9c1.300 0 2 3 2 6v8.500h28v4.200l-28 2.300v17l6.500 2.500v3.200L32 51l-8.500 1.700v-3.200L30 47V30L2 27.700v-4.200h28V15c0-3 .7-6 2-6z',
  balloon: 'M32 5a20 20 0 0 1 20 20c0 9.500-7.500 15.500-12.500 21h-15C19.500 40.500 12 34.500 12 25A20 20 0 0 1 32 5zM27 49h10v9H27z',
  drone:   'M32 4c3.6 0 5.2 3.200 5.2 7 0 3.200-1.400 5.600-3 7.200L33.8 54h-3.600L29.800 18.200c-1.600-1.600-3-4-3-7.200 0-3.800 1.600-7 5.200-7zM3 28h58v3.600L34 34.500h-4L3 31.600zM32 46l10 8v3.400L32 53l-10 4.400V54z',
  ground:  'M22 20h20a3 3 0 0 1 3 3v18a3 3 0 0 1-3 3H22a3 3 0 0 1-3-3V23a3 3 0 0 1 3-3z',
};
// category -> [shape, relative size, plain name]
const KINDS = {A1: ['prop', 0.8, 'Light aircraft'], A2: ['jet', 0.8, 'Small aircraft'], A3: ['jet', 1, 'Airliner'], A4: ['jet', 1.1, 'Large airliner'],
  A5: ['heavy', 1.25, 'Heavy jet'], A6: ['fighter', 0.95, 'High-performance jet'], A7: ['heli', 0.95, 'Helicopter'],
  B1: ['glider', 0.9, 'Glider'], B2: ['balloon', 0.9, 'Balloon or airship'], B4: ['prop', 0.7, 'Ultralight'], B6: ['drone', 0.8, 'Drone'],
  C1: ['ground', 0.6, 'Ground vehicle'], C2: ['ground', 0.6, 'Ground vehicle'], C3: ['ground', 0.6, 'Ground obstacle']};
const kind = a => KINDS[a.category] || ['jet', 1, 'Aircraft'];
const STILL = new Set(['balloon', 'ground']);   // shapes that have no nose, so they are not turned to the heading
function icon(path, fill, edge, px) {
  const c = document.createElement('canvas'); c.width = c.height = px;
  // A shape can be several pieces (body, rotor, engines). Each piece is drawn on its own, outlines first, so
  // pieces that overlap join into one silhouette instead of cutting holes in each other.
  const x = c.getContext('2d'), parts = path.split(/(?=M)/).map(d => new Path2D(d));
  x.scale(px / 64, px / 64);
  x.lineJoin = 'round'; x.lineWidth = 5; x.strokeStyle = edge;
  for (const p of parts) x.stroke(p);
  x.fillStyle = fill;
  for (const p of parts) x.fill(p);
  return x.getImageData(0, 0, px, px);
}
function icons(map, dark) {
  const edge = dark ? '#1c1c1e' : '#ffffff';
  for (const [shape, path] of Object.entries(SHAPES)) for (const [suffix, fill] of [['', civil.color[+dark]], ['-mil', military.color[+dark]]]) {
    const name = 'ww-' + shape + suffix, img = icon(path, fill, edge, 64);
    if (map.hasImage(name)) map.updateImage(name, img); else map.addImage(name, img, {pixelRatio: 2});
  }
}

const feature = (a, cls, at) => { const [shape, size] = kind(a); return {type: 'Feature', geometry: {type: 'Point', coordinates: at || [a.lon, a.lat]},
  properties: {id: a.hex, track: STILL.has(shape) ? 0 : a.track ?? 0, label: a.flight || a.reg || '', s: size, icon: 'ww-' + shape + (cls === 'mil' ? '-mil' : ''), cc: planeFlag(a.hex)?.cc || ''}}; };
const empty = {type: 'FeatureCollection', features: []};
const SIZE = ['interpolate', ['linear'], ['zoom'], 1, ['*', 0.22, ['get', 's']], 5, ['*', 0.46, ['get', 's']], 9, ['*', 0.8, ['get', 's']]];
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
  const h = find(sel), last = flown.points[flown.points.length - 1];
  el.textContent = flown.points.length > 1 ? `Solid line: the path it has flown, from ${flown.source}.` + (h && last && posTime(h) < last[0] ? ` That path is newer than the position the symbol shows (${ago(posTime(h))}); its newest point, from ${local(last[0])}, is marked.` : '') : `No flown path to draw${flown.note ? ' (' + flown.note + ')' : ''}.`;
}
function drawExtras() {
  const map = theMap; if (!map?.getSource('ww-air-extra')) return;
  const feats = [], hit = sel && find(sel), at = hit && position(hit);
  if (hit && flown && flown.hex === sel && flown.points.length > 1) {
    const pts = flown.points.map(p => [p[1], p[2]]), last = flown.points[flown.points.length - 1];
    // Join the path to the symbol only when the symbol's position is the newer one. The world snapshot can be
    // 20 minutes old while OpenSky's path runs up to now: joining those drew a line that ran ahead and turned
    // back to the older symbol. Then the path's own newest point is marked with its time instead.
    if (posTime(hit) >= last[0]) pts.push(at);
    else feats.push({type: 'Feature', geometry: {type: 'Point', coordinates: [last[1], last[2]]}, properties: {kind: 'airport', label: 'newest ' + local(last[0])}});
    feats.push({type: 'Feature', geometry: {type: 'MultiLineString', coordinates: split(pts)}, properties: {kind: 'trail'}});
  }
  if (hit && route && route.for === sel && route.fits) {
    const o = route.origin, d = route.destination;
    feats.push({type: 'Feature', geometry: {type: 'MultiLineString', coordinates: arc(at, [d.lon, d.lat])}, properties: {kind: 'route'}});
    for (const p of [o, d]) feats.push({type: 'Feature', geometry: {type: 'Point', coordinates: [p.lon, p.lat]}, properties: {kind: 'airport', label: p.iata || p.city || ''}});
  }
  map.getSource('ww-air-extra').setData({type: 'FeatureCollection', features: feats});
}
function posTime(h) {   // when the position the symbol is drawn at was reported
  if (h.from === 'view') return reportedAt(h.a);
  if (h.from === 'military') return (info.aircraft_military?.data_time ?? 0) - (h.a.seen_pos_s ?? 0);
  return h.a.last_contact ?? 0;
}
export function select(id) {
  if (id !== sel) { flown = null; route = null; }
  sel = id; drawExtras(); loadTrack();
}

// ---- the card ----
const ft = v => v == null ? 'not reported' : v === 'ground' ? 'on the ground' : `${Number(v).toLocaleString('en-GB')} ft <span class="soft">(${(v * 0.3048 / 1000).toFixed(1)} km)</span>`;
const kt = v => v == null ? 'not reported' : `${Math.round(v)} kt <span class="soft">(${Math.round(v * 1.852)} km/h)</span>`;
const ACCURACY = {11: 'within 3 m', 10: 'within 10 m', 9: 'within 30 m', 8: 'within 93 m', 7: 'within 185 m', 6: 'within 556 m', 5: 'within 926 m', 4: 'within 1.9 km', 3: 'within 3.7 km', 2: 'within 7.4 km', 1: 'within 18.5 km', 0: 'not stated'};
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
      <dt>Position reported</dt><dd>${local(at)} <span class="soft">(${ago(at)})</span></dd>
      ${a.nac_p != null ? `<dt>Position accuracy it reports</dt><dd>${ACCURACY[a.nac_p] || 'unknown'} <span class="soft">(NACp ${a.nac_p})</span></dd>` : ''}`;
  }
  const flags = [isMil && 'Military', a.ladd && 'On the FAA\'s limited-display list', a.pia && 'Privacy address'].filter(Boolean).join(' · ');
  const fresh = from === 'view' ? `Between reports it is drawn moving on along its last heading and speed, at most ${GLIDE_MAX} seconds ahead; that part is an estimate.`
    : from === 'military' ? 'This feed refreshes every 5 minutes; the aircraft is drawn where it last reported and has kept moving since. Zoom in on it for live positions.'
    : 'The world view refreshes every 20 minutes; the aircraft is drawn where it last reported and has kept moving since. Zoom in on it for live positions.';
  const v = vipList[a.hex];
  const role = v?.category === 'Doomsday' ? DOOM_ROLE.find(([re]) => re.test(v.type || ''))?.[1] : null;
  const vipBlock = v ? `<section class="pz vip"><h3>${esc(VIP_NAME[v.category] || v.category)}</h3>${role ? `<p>${esc(role)}</p>` : ''}
      <p><b>${esc(v.operator || 'Operator not listed')}</b>${v.type ? ' · ' + esc(v.type) : ''}${v.reg ? ' · ' + esc(v.reg) : ''}</p>
      ${v.tags.length ? `<p class="soft">Listed as: ${v.tags.map(esc).join(' · ')}</p>` : ''}
      ${v.link ? `<a class="link" href="${esc(v.link)}" target="_blank" rel="noopener">The list's reference</a>` : ''}
      <p class="source">From plane-alert-db, a volunteer-kept list of notable aircraft (ODbL). Its tags are the volunteers' words; a listed aircraft can be flying without the person named on board.</p></section>` : '';
  return `<div class="photo" id="photo" data-hex="${esc(a.hex)}"></div>
    <p class="eyebrow">${v ? 'Government or VIP aircraft' : isMil ? 'Military ' + kind(a)[2].toLowerCase() : kind(a)[2]}</p>
    <h2>${esc(a.flight || a.reg || a.hex.toUpperCase())}${planeFlag(a.hex) ? ` <span class="flag" title="${esc(planeFlag(a.hex).name)}">${emoji(planeFlag(a.hex).cc)}</span>` : ''}</h2>
    <p class="where" id="route" data-callsign="${esc(a.flight || '')}">${a.flight ? 'Looking up the route' : 'No callsign reported'}</p>
    ${vipBlock}
    <dl>${(() => { const fl = planeFlag(a.hex); return fl ? `<dt>Registered in</dt><dd>${emoji(fl.cc)} ${esc(fl.name)} <span class="soft">(from its transponder address block)</span></dd>` : ''; })()}${rows}<dt>Transponder address</dt><dd>${esc(a.hex.toUpperCase())}</dd></dl>
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

// ---- government and VIP aircraft, by transponder address, from plane-alert-db ----
let vipList = {}, vipInfo = null;
const VIP_NAME = {Doomsday: 'Doomsday plane: airborne nuclear command post', 'Dictator Alert': 'Autocrat\'s aircraft (the list\'s "Dictator Alert")', Governments: 'Government aircraft', Radiohead: 'Head of state',
  "Don't you know who I am?": 'Celebrity or tycoon', 'Royal Aircraft': 'Royal flight'};
function vipNow(doom = false) {
  const seen = new Map();
  for (const a of world) if (vipList[a.hex]) seen.set(a.hex, {a, at: [a.lon, a.lat], ground: a.on_ground});
  for (const a of mil) if (vipList[a.hex]) seen.set(a.hex, {a, at: [a.lon, a.lat], ground: a.alt_ft === 'ground'});
  for (const a of view) if (vipList[a.hex]) seen.set(a.hex, {a, at: shownAt(a), ground: a.alt_ft === 'ground'});
  return [...seen.values()].filter(h => (vipList[h.a.hex].category === 'Doomsday') === !!doom);
}
const vipLabel = h => { const v = vipList[h.a.hex]; return (v.category === 'Dictator Alert' || v.category === 'Governments' || v.category === 'Radiohead') && v.tags[1] && !/^government$/i.test(v.tags[1]) ? v.tags[1] : v.tags[0] === 'Air Force One' ? 'Air Force One' : v.operator; };
export const vip = {
  id: 'vip', title: 'VIP jets', color: ['#c69200', '#ffd426'], feeds: {vip_aircraft: 3600}, layers: ['ww-vip-halo', 'ww-vip-label'],
  about: () => 'Government, head-of-state and VIP aircraft from plane-alert-db, wherever our aircraft feeds see them.',
  addTo(map) {
    map.addSource('ww-air-vip', {type: 'geojson', data: empty});
    map.addLayer({id: 'ww-vip-halo', type: 'circle', source: 'ww-air-vip', paint: {'circle-radius': ['interpolate', ['linear'], ['zoom'], 1, 7, 6, 13], 'circle-opacity': 0.18, 'circle-stroke-width': 2}});
    map.addLayer({id: 'ww-vip-label', type: 'symbol', source: 'ww-air-vip',
      layout: {'text-field': ['get', 'label'], 'text-font': ['Noto Sans Bold'], 'text-size': 11, 'text-offset': [0, 1.3], 'text-anchor': 'top', 'text-optional': true}, paint: {'text-halo-width': 1.3}});
    setInterval(() => { if (!document.hidden && vipInfo) this.render(map); }, 2000);
  },
  paint(map, dark) {
    const c = this.color[+dark];
    map.setPaintProperty('ww-vip-halo', 'circle-color', c); map.setPaintProperty('ww-vip-halo', 'circle-stroke-color', c);
    map.setPaintProperty('ww-vip-label', 'text-color', dark ? '#ffd426' : '#7a5a00'); map.setPaintProperty('ww-vip-label', 'text-halo-color', dark ? '#1c1c1e' : '#ffffff');
  },
  onData(feed, d) { vipInfo = d; vipList = d.payload.aircraft || {}; },
  render(map) {
    map.getSource('ww-air-vip').setData({type: 'FeatureCollection', features: vipNow().map(h => ({type: 'Feature', geometry: {type: 'Point', coordinates: h.at},
      properties: {id: h.a.hex, cc: planeFlag(h.a.hex)?.cc || '', label: vipLabel(h) + (h.ground ? ' (on the ground)' : '')}}))});
  },
  count: () => vipNow().length,
  rows: () => vipNow().filter(h => !h.ground && vipList[h.a.hex].category !== "Don't you know who I am?").map(h => ({id: h.a.hex, time: vipInfo?.fetched || 0, badge: '◆',
    title: `${vipLabel(h)}: ${vipList[h.a.hex].type || 'aircraft'} airborne`, meta: `${VIP_NAME[vipList[h.a.hex].category] || vipList[h.a.hex].category} · ${h.a.flight || vipList[h.a.hex].reg || h.a.hex.toUpperCase()}`})),
  owns: id => !!vipList[id] && vipList[id].category !== 'Doomsday' && !!find(id),
  locate: id => civil.locate(id),
  ring: () => 18,
  moving: true,
  detail,
};

// What each kind of doomsday plane is for, by its type (public descriptions of these fleets).
const DOOM_ROLE = [
  [/E-4B/i, 'US National Airborne Operations Center ("Nightwatch"): a flying command post for the President, the Secretary of Defense and the Joint Chiefs if ground command centres are lost. One is always on alert; it also flies the Secretary of Defense on trips.'],
  [/E-6B/i, 'US Navy E-6B Mercury: TACAMO ("take charge and move out") relays orders to submarines carrying nuclear missiles, and as "Looking Glass" can control the land-based missile fields. They fly routine training and relay flights every day.'],
  [/IL-?86|IL-?76/i, 'Russian airborne command post (VKP): a flying headquarters for Russia\'s leadership and nuclear command in a crisis.'],
  [/Tu-214SR/i, 'Russian Tu-214SR: a communications relay aircraft that flies alongside the president\'s plane.'],
];
export const doomsday = {
  id: 'doomsday', title: 'Doomsday planes', color: ['#d70015', '#ff6961'], feeds: {vip_aircraft: 3600}, layers: ['ww-doom-halo', 'ww-doom-label'],
  about: () => 'Airborne nuclear command posts (US E-4B and E-6B, Russian Il-86/Il-76 VKP, Tu-214SR) when an aircraft feed sees them.',
  addTo(map) {
    map.addSource('ww-air-doom', {type: 'geojson', data: empty});
    map.addLayer({id: 'ww-doom-halo', type: 'circle', source: 'ww-air-doom', paint: {'circle-radius': ['interpolate', ['linear'], ['zoom'], 1, 9, 6, 16], 'circle-opacity': 0.15, 'circle-stroke-width': 2.5}});
    map.addLayer({id: 'ww-doom-label', type: 'symbol', source: 'ww-air-doom',
      layout: {'text-field': ['get', 'label'], 'text-font': ['Noto Sans Bold'], 'text-size': 11.5, 'text-offset': [0, 1.5], 'text-anchor': 'top', 'text-allow-overlap': true}, paint: {'text-halo-width': 1.4}});
    setInterval(() => { if (!document.hidden && vipInfo) this.render(map); }, 2000);
  },
  paint(map, dark) {
    const c = this.color[+dark];
    map.setPaintProperty('ww-doom-halo', 'circle-color', c); map.setPaintProperty('ww-doom-halo', 'circle-stroke-color', c);
    map.setPaintProperty('ww-doom-label', 'text-color', c); map.setPaintProperty('ww-doom-label', 'text-halo-color', dark ? '#1c1c1e' : '#ffffff');
  },
  onData(feed, d) { vipInfo = d; vipList = d.payload.aircraft || {}; },
  render(map) {
    map.getSource('ww-air-doom').setData({type: 'FeatureCollection', features: vipNow(true).map(h => ({type: 'Feature', geometry: {type: 'Point', coordinates: h.at},
      properties: {id: h.a.hex, label: (vipList[h.a.hex].type || 'Doomsday plane').replace(/^Boeing |^Ilyushin |^Tupolev /, '') + (h.ground ? ' (on the ground)' : '')}}))});
  },
  count: () => vipNow(true).length,
  rows: () => vipNow(true).filter(h => !h.ground).map(h => ({id: h.a.hex, time: now(), badge: '!', strong: true,
    title: `${(vipList[h.a.hex].type || 'Doomsday plane')} airborne`, meta: `${vipList[h.a.hex].operator || ''} · ${h.a.flight || vipList[h.a.hex].reg || h.a.hex.toUpperCase()}`})),
  owns: id => vipList[id]?.category === 'Doomsday' && !!find(id),
  locate: id => civil.locate(id),
  ring: () => 20,
  moving: true,
  detail,
};
