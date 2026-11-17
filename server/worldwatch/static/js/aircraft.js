// Aircraft. All of them look the same on the map; what differs is how fresh their position is:
//   view      adsb.fi, for the part of the map you are zoomed in on (up to 250 nautical miles across the
//             centre), fetched about every 10 seconds while you look
//   military  adsb.lol, worldwide, every 5 minutes
//   world     OpenSky, everything else, every 20 minutes (the free allowance)
// The card of each aircraft says where its position came from and how old it is.
import {$, ago, api, esc, local, now} from './util.js';
import {addModelProvider, addPathProvider, hitModel, isOn, onReady, MODEL_ZOOM} from './models3d.js';
import {planeFlag, flagImg} from './flags.js';

let view = [], viewInfo = null, mil = [], world = [], info = {}, theMap = null, shown = {aircraft: true, military: true, vip: false, doomsday: false};
let worldVer = 0;            // counts world snapshots, so the 6,000 world icons are re-sent only when something about them changed
const VIEW_MIN_ZOOM = 5.2;   // below this the screen holds more than adsb.fi's 250-mile circle, so only the world feed is used

// ---- playback (the owner's decision of 16 Nov 2026, after studying God's Eye View) ----
// Live aircraft are drawn a few seconds behind real time, moving between two real reports: at any moment the aircraft
// is where it really was then, joined smoothly between reports, never guessed ahead. Between two reports the path is
// a curve that leaves and arrives with the speed and heading the aircraft itself reported (a Hermite curve), so it
// does not kink at every report. When no newer report has come in yet, it waits at its last one.
// Aircraft in the live area feed (a report every ~5 s) run DELAY seconds behind; ones known only from the military
// feed (every 30 s) run DELAY_SLOW behind, so they keep moving between its reports too.
export const DELAY = 15, DELAY_SLOW = 40;
const VIEW_POLL = 5000;
const hist = new Map();                // hex -> real reports [{t, lon, lat, alt, track, gs}], oldest first; .view = when the area feed last had it
function record(list, dataTime, fromView) {
  const now0 = now();
  for (const a of list) {
    if (a.lat == null || a.lon == null || !a.hex) continue;
    const t = (dataTime ?? now0) - (a.seen_pos_s ?? 0);
    let h = hist.get(a.hex);
    if (!h) hist.set(a.hex, h = []);
    if (fromView) h.view = now0;
    h.seen = now0;
    if (h.length && t <= h[h.length - 1].t + 0.5) continue;           // the same report again
    h.push({t, lon: a.lon, lat: a.lat, alt: a.alt_ft === 'ground' ? 0 : a.alt_ft, track: a.track, gs: a.gs_kt});
    while (h.length > 16 || (h.length > 2 && h[0].t < t - 300)) h.shift();
  }
  if (hist.size > 4000) for (const [k, h] of hist) if (now0 - h.seen > 300) { hist.delete(k); disp.delete(k); }
}
const delayOf = hex => { const h = hist.get(hex); return h && h.view && now() - h.view < 20 ? DELAY : DELAY_SLOW; };
const lerpDeg = (a, b, f) => a == null ? b : b == null ? a : a + ((((b - a) % 360) + 540) % 360 - 180) * f;
const KT = 0.514444, DEG = 111320;
// where an aircraft was at time T, from its real reports: {lon, lat, alt (ft), track, held}
export function playback(a, T = now() - delayOf(a.hex)) {
  const h = hist.get(a.hex);
  if (!h || !h.length) return {lon: a.lon, lat: a.lat, alt: a.alt_ft === 'ground' ? 0 : a.alt_ft, track: a.track, held: true, t: T};
  // before its first report (an aircraft that has just come into view): it waits there until the playback reaches it
  if (T <= h[0].t) { const f = h[0]; return {lon: f.lon, lat: f.lat, alt: f.alt, track: f.track, held: true, wait: true, t: T}; }
  const L = h[h.length - 1];
  if (T >= L.t) return {lon: L.lon, lat: L.lat, alt: L.alt, track: L.track, held: true, t: T};
  let i = h.length - 2; while (i > 0 && h[i].t > T) i--;
  const p = h[i], q = h[i + 1], dt = q.t - p.t || 1, f = (T - p.t) / dt;
  let dl = q.lon - p.lon; if (dl > 180) dl -= 360; if (dl < -180) dl += 360;
  const cos = Math.cos(p.lat * Math.PI / 180);
  // straight line by default; the curve when both reports carry speed and heading that agree with the distance flown
  let x = dl * f, y = (q.lat - p.lat) * f;
  if (p.gs != null && q.gs != null && p.track != null && q.track != null && dt < 40) {
    const chord = Math.hypot(dl * cos * DEG, (q.lat - p.lat) * DEG), sp = (p.gs + q.gs) / 2 * KT * dt;
    if (sp > 0 && chord > 0.6 * sp && chord < 1.5 * sp) {
      const r = Math.PI / 180, v = (g, tr) => [g * KT * Math.sin(tr * r) / (DEG * cos) * dt, g * KT * Math.cos(tr * r) / DEG * dt];
      const [ax, ay] = v(p.gs, p.track), [bx, by] = v(q.gs, q.track);
      const h10 = f ** 3 - 2 * f ** 2 + f, h01 = -2 * f ** 3 + 3 * f ** 2, h11 = f ** 3 - f ** 2;
      x = h10 * ax + h01 * dl + h11 * bx; y = h10 * ay + h01 * (q.lat - p.lat) + h11 * by;
    }
  }
  return {lon: p.lon + x, lat: p.lat + y, alt: p.alt == null || q.alt == null ? (q.alt ?? p.alt) : p.alt + (q.alt - p.alt) * f,
    track: lerpDeg(p.track, q.track, f), held: false, t: T};
}
// What is drawn: the playback position, smoothed on screen so nothing ever jumps (a late report, a switch between
// feeds), and the nose turning at most 60 degrees a second (God's Eye View's rule). Everything that shows an
// aircraft (model, icon, ring, path, chase camera) asks this one function, so they always agree.
const disp = new Map();
// One clock per animation frame (the frame's own timestamp), so the camera, the model and the ring, which all ask
// within the same frame, get exactly the same position.
const frameT = () => (document.timeline?.currentTime ?? performance.now()) / 1000;
// Playback runs on the frame clock, which never steps. Its offset to real (server) time is taken from now() once and
// afterwards only slewed, at most 10 ms per second, when now() moves (a better clock estimate, a clock adjusted):
// playback time then runs at 0.99-1.01 of real speed and never jumps or goes backwards.
let pbBase = null, pbAt = 0;
function frameNow() {
  const t = frameT(), target = now() - performance.now() / 1000;
  if (pbBase == null || Math.abs(target - pbBase) > 30) pbBase = target;          // the start, or a clock off by more than half a minute
  else if (t > pbAt) { const s = (t - pbAt) * 0.01; pbBase += Math.max(-s, Math.min(s, target - pbBase)); }
  if (t > pbAt) pbAt = t;
  return pbBase + t;
}
export function display(a) {
  const t = frameT();
  let d = disp.get(a.hex);
  const want = delayOf(a.hex);
  if (!d || t - d.wall > 3) {
    const p = playback(a, frameNow() - want);
    d = {...p, delay: want, wall: t}; disp.set(a.hex, d); return d;
  }
  const dt = t - d.wall; if (dt <= 0) return d;
  d.delay += Math.max(-dt * 0.5, Math.min(dt * 0.5, want - d.delay));   // a change of delay is eased in, never jumped
  const p = playback(a, frameNow() - d.delay), k = 1 - Math.exp(-dt / 0.3);
  let dl = p.lon - d.lon; if (dl > 180) dl -= 360; if (dl < -180) dl += 360;
  if (Math.abs(dl) > 2 || Math.abs(p.lat - d.lat) > 2) { Object.assign(d, p); d.wall = t; return d; }
  d.lon += dl * k; d.lat += (p.lat - d.lat) * k;
  d.alt = p.alt == null ? d.alt : d.alt == null ? p.alt : d.alt + (p.alt - d.alt) * k;
  if (p.track != null) {
    if (d.track == null) d.track = p.track;
    else { const dh = ((p.track - d.track + 540) % 360) - 180, st = Math.max(-60 * dt, Math.min(60 * dt, dh * Math.min(1, k * 2))); d.track = (d.track + st + 360) % 360; }
  }
  d.held = p.held; d.wait = p.wait; d.t = p.t; d.wall = t;
  return d;
}
const shownAt = a => { const p = display(a); return [p.lon, p.lat]; };
// where an aircraft known to the live or military feed is drawn right now, for layers that mark aircraft from their own
// snapshots (tankers, sanctioned aircraft): their markers then sit on the moving aircraft instead of falling behind it
export function liveAt(hex) {
  const a = view.find(x => x.hex === hex) || mil.find(x => x.hex === hex);
  return a ? shownAt(a) : null;
}

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
  properties: {id: a.hex, track: STILL.has(shape) ? 0 : (at && hist.has(a.hex) ? display(a).track : a.track) ?? 0, label: a.flight || a.reg || '', s: size, icon: 'ww-' + shape + (cls === 'mil' ? '-mil' : ''), cc: planeFlag(a.hex)?.cc || ''}}; };
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
// The one place that says where an aircraft is drawn: {lon, lat, altM, track, t (the time that position is from)}.
// Live and military aircraft: the smoothed playback. World-feed aircraft: their 20-minute snapshot, except the
// selected one when the path OpenSky gives for it is newer: then it sits at that path's newest point.
function where(h) {
  if (h.from !== 'world') { const d = display(h.a); return {lon: d.lon, lat: d.lat, altM: d.alt == null ? null : d.alt * 0.3048, track: d.track, t: d.t, held: d.held}; }
  const a = h.a, last = flown && flown.hex === a.hex && flown.points.length ? flown.points[flown.points.length - 1] : null;
  if (last && last[0] > (a.last_contact ?? 0)) {
    const prev = flown.points[flown.points.length - 2];
    return {lon: last[1], lat: last[2], altM: last[3] ?? a.alt_m, track: prev ? bearing(prev[1], prev[2], last[1], last[2]) : a.track, t: last[0], fromPath: true};
  }
  return {lon: a.lon, lat: a.lat, altM: a.on_ground ? 0 : a.alt_m, track: a.track, t: a.last_contact ?? 0};
}
function bearing(lo1, la1, lo2, la2) {
  const r = Math.PI / 180, y = Math.sin((lo2 - lo1) * r) * Math.cos(la2 * r), x = Math.cos(la1 * r) * Math.sin(la2 * r) - Math.sin(la1 * r) * Math.cos(la2 * r) * Math.cos((lo2 - lo1) * r);
  return (Math.atan2(y, x) / r + 360) % 360;
}
const position = h => { const w = where(h); return [w.lon, w.lat]; };

// ---- drawing ----
// The ~6,000 world aircraft change only when a new snapshot arrives (or the live circle moves): they are sent to the map
// then. The few hundred live ones on screen glide, and only they are re-sent every 200 ms, in their own small source,
// and only when one of them moved. Zoomed in (MODEL_ZOOM and closer) the 3D models draw every aircraft and the icon
// layers are hidden by their zoom range, so nothing is sent to them at all until the map is zoomed out again.
// (Re-sending everything five times a second kept the map's workers busy for good: 3D terrain tiles never got decoded.)
const sent = {live: null, mil: null, world: '', extra: ''};
function changed(key, feats) {   // true when these features differ from what was last sent to that source
  const prev = sent[key];
  sent[key] = feats;
  if (!prev || prev.length !== feats.length) return true;
  for (let i = 0; i < feats.length; i++) {
    const a = prev[i], b = feats[i], pa = a.geometry.coordinates, pb = b.geometry.coordinates;
    if (a.properties.id !== b.properties.id || Math.abs(pa[0] - pb[0]) > 1e-7 || Math.abs(pa[1] - pb[1]) > 1e-7 || Math.abs(a.properties.track - b.properties.track) > 0.05 || a.properties.icon !== b.properties.icon) return true;
  }
  return false;
}
function glide(full = false) {
  const map = theMap; if (!map || !map.getSource('ww-air')) return;
  if (full) map.triggerRepaint();             // new reports: the models (which stop asking for frames when nothing moves) move again
  if (isOn()) { if (full) drawExtras(true); return; }
  const milHex = new Set(mil.map(a => a.hex)), viewHex = new Set(view.map(a => a.hex));
  if (shown.aircraft) {
    const live = view.filter(a => !milHex.has(a.hex) && !a.military).map(a => feature(a, 'civil', shownAt(a)));
    if (changed('live', live)) map.getSource('ww-air-live').setData({type: 'FeatureCollection', features: live});
    const s0 = sel && world.find(a => a.hex === sel), wk = worldVer + '|' + (view.length && viewInfo ? [viewInfo.lat, viewInfo.lon, viewInfo.radius_nm] : '') + '|' + (s0 ? sel + position({a: s0, from: 'world'}) : '') + '|' + view.length + '|' + mil.length;
    if (wk !== sent.world) {
      sent.world = wk;
      const feats = [];
      for (const a of world) if (!viewHex.has(a.hex) && !milHex.has(a.hex) && !a.on_ground && !inLive(a)) feats.push(feature(a, 'civil', a.hex === sel ? position({a, from: 'world'}) : undefined));
      map.getSource('ww-air').setData({type: 'FeatureCollection', features: feats});
    }
  }
  if (shown.military) {
    const m = [...mil.filter(a => !viewHex.has(a.hex)).map(a => feature(a, 'mil', shownAt(a))), ...view.filter(a => a.military || milHex.has(a.hex)).map(a => feature(a, 'mil', shownAt(a)))];
    if (changed('mil', m)) map.getSource('ww-air-mil').setData({type: 'FeatureCollection', features: m});
  }
  drawExtras(full);
}

// Inside the circle the live feed covers, it is the only source: a 20-minute-old world position there is a ghost
// (often an aircraft that has landed since), so the world feed is not drawn inside it.
function inLive(a) {
  const v = viewInfo; if (!v || !view.length) return false;
  const r = Math.PI / 180, x = Math.sin((a.lat - v.lat) * r / 2) ** 2 + Math.cos(a.lat * r) * Math.cos(v.lat * r) * Math.sin((a.lon - v.lon) * r / 2) ** 2;
  return 12742 * Math.asin(Math.min(1, Math.sqrt(x))) < v.radius_nm * 1.852;
}
// ---- a live feed that stops answering is shown as such (hard rule: a dead feed is shown as dead) ----
// When the area feed has given nothing new for STALE seconds its aircraft stop where they last reported (playback
// holds them there), turn grey and are labelled "last known"; the card says how old the position is and why. After
// DROP seconds they are taken off and the world / military positions take over again.
const STALE = 30, DROP = 120;
let viewErr = null, wasStale = false, selFrom;
const viewAge = () => viewInfo ? now() - viewInfo.data_time : 0;
export const liveStale = () => !!view.length && viewAge() > STALE;
function checkLive() {
  const st = liveStale();
  if (st && viewAge() > DROP) { view = []; viewInfo = null; glide(true); }
  const st2 = liveStale();
  if (st2 !== wasStale) {
    wasStale = st2;
    if (theMap?.getLayer('ww-air-live')) theMap.setPaintProperty('ww-air-live', 'icon-opacity', st2 ? 0.45 : 1);
    theMap?.triggerRepaint();
  }
}
// The open card's live numbers, updated in place on every new report and every second (the latest report's values;
// the drawn aircraft is a few seconds behind them, which the "fresh" line says)
function liveCard() {
  checkLive();
  if (!sel) return;
  const h = find(sel), from = h?.from || null;
  if (from !== selFrom) { const was = selFrom; selFrom = from; if (was !== undefined && $('#photo')?.dataset.hex === sel) { document.dispatchEvent(new Event('ww-detail')); return; } }   // it moved between feeds (live feed lost or back): the card is redrawn
  const el = $('#ac-alt'); if (!el || !h || h.from === 'world') return;
  const a = h.a, f = h.from === 'view' ? viewInfo : info.aircraft_military, at = (f?.data_time ?? now()) - (a.seen_pos_s ?? 0);
  el.innerHTML = ft(a.alt_ft);
  $('#ac-gs') && ($('#ac-gs').innerHTML = kt(a.gs_kt));
  $('#ac-trk') && ($('#ac-trk').textContent = a.track == null ? 'not reported' : Math.round(a.track) + '°');
  $('#ac-at') && ($('#ac-at').innerHTML = `${local(at)} <span class="soft">(${ago(at)})</span>`);
  $('#ac-fresh') && ($('#ac-fresh').textContent = freshText(h));
}
setInterval(liveCard, 1000);   // keeps "n s ago" counting
// what the card says about how the drawn position relates to the reports
function freshText(h) {
  if (h.from === 'world') return 'The world view refreshes every 20 minutes; the aircraft is drawn where it last reported and has kept moving since. Zoom in on it for live positions.';
  const d = display(h.a), r = hist.get(h.a.hex), age = r?.length ? Math.round(now() - r[r.length - 1].t) : null;
  if (h.from === 'view' && liveStale()) return `No new position for ${Math.round(viewAge())} s: the live feed (adsb.fi) is not answering${viewErr ? ' (' + viewErr + ')' : ''}. Shown grey where it last reported; it is not moving on the map.`;
  if (d.wait) return `Just came into view: drawn ${Math.round(d.delay)} seconds behind real time, so it waits at its first report until the playback reaches it, then moves between its real reports.`;
  if (d.held) return `Drawn ${Math.round(d.delay)} seconds behind real time; no newer report has come in yet, so it waits at its last one${age != null ? ` (${age} s old)` : ''}.`;
  return `Drawn ${Math.round(d.delay)} seconds behind real time, moving between its real reports (no guessing ahead).`;
}
// ---- live aircraft for the area on screen ----
let asking = false;
async function loadView() {
  const map = theMap;
  if (!map || asking || document.hidden || !(shown.aircraft || shown.military)) return;
  if (map.getZoom() < VIEW_MIN_ZOOM) { if (view.length) { view = []; viewInfo = null; glide(true); } return; }
  const c = map.getCenter(), b = map.getBounds();
  const km = 111.2 * Math.hypot(b.getNorth() - c.lat, (b.getEast() - c.lng) * Math.cos(c.lat * Math.PI / 180));
  asking = true;
  try {
    const d = await api(`/api/aircraft/area?lat=${c.lat.toFixed(3)}&lon=${c.lng.toFixed(3)}&r=${Math.min(250, Math.ceil(km / 1.852))}`);
    viewInfo = d; view = d.aircraft; viewErr = null; record(view, d.data_time, true); glide(true);
    liveCard();
  } catch (e) { viewErr = /answered (\d+)/.exec(e.message)?.[0] || 'no answer'; liveCard(); }   // the feeds card shows it too; checkLive greys the aircraft
  asking = false;
}

// ---- for the selected aircraft: the path it has flown, and a line to where it is going ----
let sel = null, route = null, flown = null;
async function loadTrack() {
  const id = sel; if (!id) return;
  try { const r = await api('/api/track/' + encodeURIComponent(id)); if (sel === id) { flown = {hex: id, ...r}; glide(true); noteTrack(); } } catch (e) { /* the line stays as it was */ }
}
setInterval(loadTrack, 45000);
function noteTrack() {
  const el = $('#tracknote'); if (!el || !flown || flown.hex !== sel) return;
  const h = find(sel), w = h && where(h);
  el.textContent = flown.points.length > 1 ? `Solid line: the path it has flown, from ${flown.source}, up to where it is drawn.` + (w?.fromPath ? ` That path is newer than the 20-minute snapshot, so the aircraft is drawn at its newest point (${local(w.t)}, ${ago(w.t)}).` : '') : `No flown path to draw${flown.note ? ' (' + flown.note + ')' : ''}.`;
}
// The flown path up to the moment the aircraft is drawn at, joined to it: [[lon, lat, alt m], ...]. OpenSky's path
// runs up to now while a live aircraft is drawn a few seconds behind, so the newer end is cut off; otherwise the line
// would run ahead of the aircraft.
function flownLine(h, w) {
  if (!flown || flown.hex !== h.a.hex || flown.points.length < 2) return null;
  const out = [];
  let lastAlt = null;
  for (const p of flown.points) { if (p[3] != null) lastAlt = p[3]; if (p[0] < w.t - 0.5) out.push([p[1], p[2], p[3] ?? lastAlt]); }
  for (const p of out) if (p[2] == null) p[2] = w.altM ?? 0;
  out.push([w.lon, w.lat, w.altM ?? lastAlt ?? 0]);
  return out.length > 1 ? out : null;
}
function routeLine(w) {
  if (!route || route.for !== sel || !route.fits) return null;
  const d = route.destination, alt = w.altM ?? 0, out = [];
  for (const line of arc([w.lon, w.lat], [d.lon, d.lat])) for (const p of line) out.push(p);
  return out.map((p, i) => [p[0], p[1], alt * (1 - i / (out.length - 1))]);
}
// The selected aircraft's flown path and route as flat lines (below MODEL_ZOOM; above it models3d draws them in the air)
// and its two airports' labels. Sent only when the selection, its data or its drawn position changed.
function drawExtras(force = false) {
  const map = theMap; if (!map?.getSource('ww-air-extra')) return;
  const hit = sel && find(sel), w = hit && where(hit), at = w && [w.lon, w.lat];
  const key = (sel || '') + '|' + (flown?.hex === sel ? flown.points.length : '') + '|' + (route?.for === sel ? route.fits : '') + '|' + (isOn() ? '3d' : at ? at[0].toFixed(5) + ',' + at[1].toFixed(5) : '');
  if ((!force || !sel) && key === sent.extra) return;
  sent.extra = key;
  const feats = [];
  const line = hit && flownLine(hit, w);
  if (line) feats.push({type: 'Feature', geometry: {type: 'MultiLineString', coordinates: split(line.map(p => [p[0], p[1]]))}, properties: {kind: 'trail'}});
  if (hit && route && route.for === sel && route.fits) {
    const o = route.origin, d = route.destination;
    feats.push({type: 'Feature', geometry: {type: 'MultiLineString', coordinates: arc(at, [d.lon, d.lat])}, properties: {kind: 'route'}});
    for (const p of [o, d]) feats.push({type: 'Feature', geometry: {type: 'Point', coordinates: [p.lon, p.lat]}, properties: {kind: 'airport', label: p.iata || p.city || ''}});
  }
  map.getSource('ww-air-extra').setData({type: 'FeatureCollection', features: feats});
}
function posTime(h) {   // when the position the symbol is drawn at was reported
  return where(h).t;
}
export function select(id) {
  if (id !== sel) { flown = null; route = null; clearTimeout(routeAgain); routeAgain = 0; selFrom = undefined; }
  sel = id; drawExtras(true); loadTrack(); theMap?.triggerRepaint();
}

// ---- the card ----
const ft = v => v == null ? 'not reported' : v === 'ground' ? 'on the ground' : `${Number(v).toLocaleString('en-GB')} ft <span class="soft">(${(v * 0.3048 / 1000).toFixed(1)} km)</span>`;
const kt = v => v == null ? 'not reported' : `${Math.round(v)} kt <span class="soft">(${Math.round(v * 1.852)} km/h)</span>`;
const ACCURACY = {11: 'within 3 m', 10: 'within 10 m', 9: 'within 30 m', 8: 'within 93 m', 7: 'within 185 m', 6: 'within 556 m', 5: 'within 926 m', 4: 'within 1.9 km', 3: 'within 3.7 km', 2: 'within 7.4 km', 1: 'within 18.5 km', 0: 'not stated'};
const SOURCE = {view: 'adsb.fi', military: 'adsb.fi', world: 'OpenSky Network'};

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
    rows = `<dt>Altitude</dt><dd id="ac-alt">${ft(a.alt_ft)}</dd>
      <dt>Ground speed</dt><dd id="ac-gs">${kt(a.gs_kt)}</dd>
      <dt>Heading</dt><dd id="ac-trk">${a.track == null ? 'not reported' : Math.round(a.track) + '°'}</dd>
      ${a.squawk ? `<dt>Transponder code</dt><dd>${esc(a.squawk)}${{7500: ' (hijack)', 7600: ' (radio failure)', 7700: ' (emergency)'}[a.squawk] || ''}</dd>` : ''}
      <dt>Latest report</dt><dd id="ac-at">${local(at)} <span class="soft">(${ago(at)})</span></dd>
      ${a.nac_p != null ? `<dt>Position accuracy it reports</dt><dd>${ACCURACY[a.nac_p] || 'unknown'} <span class="soft">(NACp ${a.nac_p})</span></dd>` : ''}`;
  }
  const flags = [isMil && 'Military', a.ladd && 'On the FAA\'s limited-display list', a.pia && 'Privacy address'].filter(Boolean).join(' · ');
  const fresh = `<span id="ac-fresh">${esc(freshText(hit))}</span>`;
  const v = vipList[a.hex];
  const role = v?.category === 'Doomsday' ? DOOM_ROLE.find(([re]) => re.test(v.type || ''))?.[1] : null;
  const vipBlock = v ? `<section class="pz vip"><h3>${esc(VIP_NAME[v.category] || v.category)}</h3>${role ? `<p>${esc(role)}</p>` : ''}
      <p><b>${esc(v.operator || 'Operator not listed')}</b>${v.type ? ' · ' + esc(v.type) : ''}${v.reg ? ' · ' + esc(v.reg) : ''}</p>
      ${v.tags.length ? `<p class="soft">Listed as: ${v.tags.map(esc).join(' · ')}</p>` : ''}
      ${v.link ? `<a class="link" href="${esc(v.link)}" target="_blank" rel="noopener">The list's reference</a>` : ''}
      <p class="source">From plane-alert-db, a volunteer-kept list of notable aircraft (ODbL). Its tags are the volunteers' words; a listed aircraft can be flying without the person named on board.</p></section>` : '';
  return `<div class="photo" id="photo" data-hex="${esc(a.hex)}"></div>
    <p class="eyebrow">${v ? 'Government or VIP aircraft' : isMil ? 'Military ' + kind(a)[2].toLowerCase() : kind(a)[2]}</p>
    <h2>${esc(a.flight || a.reg || a.hex.toUpperCase())}${planeFlag(a.hex) ? ' ' + flagImg(planeFlag(a.hex).cc, planeFlag(a.hex).name) : ''}</h2>
    <p class="where" id="route" data-callsign="${esc(a.flight || '')}">${a.flight ? 'Looking up the route' : 'No callsign reported'}</p>
    ${vipBlock}
    <dl><dt>Aircraft</dt><dd id="actype" data-hex="${esc(a.hex)}" data-code="${esc(a.type || '')}" data-reg="${esc(a.reg || '')}" data-vip="${esc(v?.type || '')}">${a.type ? esc(a.type) + ' <span class="soft">(type code it broadcasts; looking it up…)</span>' : 'Looking it up…'}</dd>${(() => { const fl = planeFlag(a.hex); return fl ? `<dt>Registered in</dt><dd>${flagImg(fl.cc, fl.name)} ${esc(fl.name)} <span class="soft">(from its transponder address block)</span></dd>` : ''; })()}${rows}<dt>Transponder address</dt><dd>${esc(a.hex.toUpperCase())}</dd></dl>
    ${flags ? `<p class="source">${flags}.</p>` : ''}
    <a class="link" href="https://globe.adsb.fi/?icao=${esc(a.hex)}" target="_blank" rel="noopener">Follow on adsb.fi</a>
    <p class="source">Position: ${SOURCE[from]}, fetched ${ago(f.fetched)}. ${fresh}</p>
    <p class="source" id="tracknote"></p>`;
}

// Route and photo come from two more sources and are looked up only when a card is opened.
let routeAgain = 0;
export async function fillRoute() {
  noteTrack();
  fillPhoto();
  fillType();
  const el = $('#route'); if (!el || !el.dataset.callsign || el.dataset.done) return;
  el.dataset.done = '1';
  const cs = el.dataset.callsign, id = sel, hit = find(id), at = hit && position(hit);
  try {
    const r = await api(`/api/route/${encodeURIComponent(cs)}` + (at ? `?lat=${at[1].toFixed(3)}&lon=${at[0].toFixed(3)}${hit.a.track != null ? '&track=' + Math.round(hit.a.track) : ''}` : ''));
    const now2 = $('#route'); if (!now2 || now2.dataset.callsign !== cs || sel !== id) return;
    if (!r.route) { now2.textContent = military.owns(id) ? 'No published route, as usual for military flights' : 'Route not known to adsbdb'; return; }
    const p = x => `${esc(x.city || x.name)}${x.iata ? ' (' + esc(x.iata) + ')' : ''}`;
    if (r.fits === false) {
      now2.innerHTML = `Route unknown<span class="sub">adsbdb lists ${p(r.route.origin)} to ${p(r.route.destination)} for this callsign, but ${esc(r.why)}, so it is not shown as the route. Checked again every 3 minutes while this card is open.</span>`;
      routeAgain = setTimeout(() => { routeAgain = 0; const e2 = $('#route'); if (sel === id && e2 && e2.dataset.callsign === cs) { delete e2.dataset.done; fillRoute(); } }, 180000);   // a departure turn can point away from the destination for a while
      return;
    }
    now2.innerHTML = `${p(r.route.origin)} to ${p(r.route.destination)}<span class="sub">${esc(r.route.airline || '')}${r.route.airline ? ' · ' : ''}usual route for this callsign, from adsbdb. Dashed line: straight to the destination, not the planned path.</span>`;
    route = {...r.route, fits: true, for: id}; drawExtras();
  } catch (e) { const now2 = $('#route'); if (now2) now2.textContent = 'Route lookup failed'; }
}
// Maker and model: the free aircraft registers behind adsbdb / hexdb, by transponder address. When they do not know it,
// the best we have is the type code the aircraft broadcasts (adsb.fi) or the model plane-alert-db lists.
const abouts = new Map();
async function fillType() {
  const el = $('#actype'); if (!el || el.dataset.done) return;
  el.dataset.done = '1';
  const hex = el.dataset.hex;
  if (!abouts.has(hex)) { try { abouts.set(hex, (await api('/api/aircraft/about/' + hex)).about || null); } catch (e) { abouts.set(hex, null); } }
  const ab = abouts.get(hex), now2 = $('#actype');
  if (!now2 || now2.dataset.hex !== hex) return;
  const code = now2.dataset.code, reg = now2.dataset.reg, vipType = now2.dataset.vip;
  if (ab && (ab.model || ab.maker)) {
    const name = [ab.maker, ab.model].filter(Boolean).join(' ');
    const extra = [ab.code, ab.reg && 'registration ' + ab.reg, ab.owner].filter(Boolean).map(esc).join(' · ');
    const clash = code && ab.code && code.toUpperCase() !== ab.code.toUpperCase();
    now2.innerHTML = `<b>${esc(name)}</b>${extra ? `<br><span class="soft">${extra}</span>` : ''}<br><span class="soft">From the aircraft register kept by ${esc(ab.source)}, by its transponder address${clash ? `; the aircraft itself broadcasts type code ${esc(code)}, which differs, so treat this as an estimate` : ''}.</span>`;
  } else if (vipType) {
    now2.innerHTML = `${esc(vipType)}<br><span class="soft">As plane-alert-db lists it; not in the free registers.</span>`;
  } else if (code) {
    now2.innerHTML = `Type code ${esc(code)}${reg ? ' · ' + esc(reg) : ''}<br><span class="soft">The ICAO type code the aircraft broadcasts; the free registers do not know this address.</span>`;
  } else {
    now2.innerHTML = '<span class="soft">Not known: the free registers do not list this transponder address and the aircraft broadcasts no type.</span>';
  }
}
const photos = new Map();
async function fillPhoto() {
  const el = $('#photo'); if (!el || el.dataset.done) return;
  el.dataset.done = '1';
  const hex = el.dataset.hex;
  // only real answers are remembered: "photos not set up" and a failed lookup are said as such and asked again next time
  let ph = photos.get(hex), why = null;
  if (ph === undefined) {
    try {
      const r = await api('/api/photo/' + hex);
      if (r.off) why = 'Photos are not set up: they need a contact address in data/contact.txt (see the README).';
      else if (r.error) why = `Photo lookup failed: ${r.error}.`;
      else photos.set(hex, ph = r.photo || null);
    } catch (e) { why = 'Photo lookup failed: this server did not answer.'; }
  }
  const now2 = $('#photo');
  if (!now2 || now2.dataset.hex !== hex) return;
  if (why) { now2.innerHTML = `<p class="pic-wait">${esc(why)}</p>`; return; }
  if (!ph) { now2.innerHTML = '<p class="pic-wait">No photo of this aircraft on planespotters.net.</p>'; return; }
  if (ph.rejected) { now2.innerHTML = `<p class="pic-wait">planespotters.net files a photo under this transponder address, but it shows another aircraft (${esc(ph.rejected)}), so it is left out.</p>`; return; }
  now2.innerHTML = `<a href="${esc(ph.link)}" target="_blank" rel="noopener"><img src="${esc(ph.src)}" alt="Photo of this aircraft" loading="lazy"></a><span>Photo: ${esc(ph.photographer)}, planespotters.net</span>`;
}

export const civil = {
  id: 'aircraft', title: 'Aircraft', color: ['#5856d6', '#7d7aff'], feeds: {aircraft_world: 120}, layers: ['ww-air', 'ww-air-live'],
  addTo(map) {
    theMap = map;
    for (const s of ['ww-air', 'ww-air-live', 'ww-air-mil', 'ww-air-extra']) map.addSource(s, {type: 'geojson', data: empty});
    map.addLayer({id: 'ww-air-route', type: 'line', source: 'ww-air-extra', filter: ['==', ['get', 'kind'], 'route'], paint: {'line-width': 2, 'line-dasharray': [2.5, 2.5], 'line-opacity': 0.9}});
    map.addLayer({id: 'ww-air-trail', type: 'line', source: 'ww-air-extra', filter: ['==', ['get', 'kind'], 'trail'], layout: {'line-cap': 'round', 'line-join': 'round'}, paint: {'line-width': 2.5}});
    map.addLayer({id: 'ww-air-airport', type: 'symbol', source: 'ww-air-extra', filter: ['==', ['get', 'kind'], 'airport'],
      layout: {'text-field': ['get', 'label'], 'text-font': ['Noto Sans Bold'], 'text-size': 11, 'text-allow-overlap': true}});
    map.addLayer(symbol('ww-air', 'ww-air'));
    map.addLayer(symbol('ww-air-live', 'ww-air-live'));
    // zoomed in, the 3D models take over: flat icons, ground ring and ground lines stop at MODEL_ZOOM (once the models are loaded)
    onReady(() => setTimeout(() => { for (const l of ['ww-air', 'ww-air-live', 'ww-air-mil', 'ww-air-route', 'ww-air-trail', 'ww-vip-halo', 'ww-vip-label', 'ww-doom-halo', 'ww-doom-label']) if (map.getLayer(l)) map.setLayerZoomRange(l, 0, MODEL_ZOOM); }, 0));   // after the military and VIP layers exist
    setInterval(() => { if (!document.hidden && (shown.aircraft || shown.military) && (view.length || mil.length)) glide(); }, 200);
    setInterval(loadView, VIEW_POLL);
    let t = null;
    map.on('moveend', () => { clearTimeout(t); t = setTimeout(loadView, 600); });   // a moment after the map stops moving
  },
  paint(map, dark) {
    icons(map, dark);
    const ink = dark ? '#e5e5ea' : '#3a3a3c', halo = dark ? '#1c1c1e' : '#ffffff';
    for (const l of ['ww-air', 'ww-air-live', 'ww-air-mil', 'ww-air-airport']) if (map.getLayer(l)) {
      map.setPaintProperty(l, 'text-color', ink); map.setPaintProperty(l, 'text-halo-color', halo); map.setPaintProperty(l, 'text-halo-width', 1.3);
    }
    if (map.getLayer('ww-air-route')) for (const l of ['ww-air-route', 'ww-air-trail']) map.setPaintProperty(l, 'line-color', civil.color[+dark]);
  },
  onData(feed, d) { info[feed] = d; world = d.payload.aircraft; worldVer++; },
  render: () => glide(true),
  visible(on) { shown.aircraft = on; if (on) loadView(); theMap?.triggerRepaint(); },
  count: () => new Set([...world.filter(a => !a.on_ground), ...view].map(a => a.hex)).size,
  rows: () => [],
  locate(id) { const h = find(id); return h && position(h); },
  locate3d(id) { const h = find(id); if (!h) return null; const w = where(h); return [w.lon, w.lat, w.altM ?? 0]; },
  // undefined = nothing to follow (main.js then offers no chase camera): an aircraft on the ground is not followed
  heading(id) { const h = find(id); if (!h || (h.from === 'world' ? h.a.on_ground : h.a.alt_ft === 'ground')) return undefined; return where(h).track ?? null; },
  ring: () => isOn() ? 0 : 15,   // zoomed in, the model layer draws the ring around the aircraft in the air
  moving: true,
  detail,
  owns: id => !!find(id) && !military.owns(id),
};

export const military = {
  id: 'military', title: 'Military', color: ['#af52de', '#da8fff'], feeds: {aircraft_military: 30}, layers: ['ww-air-mil'],
  addTo(map) { map.addLayer(symbol('ww-air-mil', 'ww-air-mil')); },
  paint(map, dark) { civil.paint(map, dark); },
  onData(feed, d) { info[feed] = d; mil = d.payload.aircraft; record(mil, d.data_time, false); liveCard(); },
  render: () => glide(true),
  visible(on) { shown.military = on; if (on) loadView(); theMap?.triggerRepaint(); },
  count: () => mil.length,
  rows: () => [],
  locate: id => civil.locate(id),
  locate3d: id => civil.locate3d(id),
  heading: id => civil.heading(id),
  ring: () => isOn() ? 0 : 16,
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
  visible(on) { shown.vip = on; theMap?.triggerRepaint(); },
  render(map) {
    map.getSource('ww-air-vip').setData({type: 'FeatureCollection', features: vipNow().map(h => ({type: 'Feature', geometry: {type: 'Point', coordinates: h.at},
      properties: {id: h.a.hex, cc: planeFlag(h.a.hex)?.cc || '', label: vipLabel(h) + (h.ground ? ' (on the ground)' : '')}}))});
  },
  count: () => vipNow().length,
  rows: () => vipNow().filter(h => !h.ground && vipList[h.a.hex].category !== "Don't you know who I am?").map(h => ({id: h.a.hex, time: vipInfo?.fetched || 0, badge: '◆',
    title: `${vipLabel(h)}: ${vipList[h.a.hex].type || 'aircraft'} airborne`, meta: `${VIP_NAME[vipList[h.a.hex].category] || vipList[h.a.hex].category} · ${h.a.flight || vipList[h.a.hex].reg || h.a.hex.toUpperCase()}`})),
  owns: id => !!vipList[id] && vipList[id].category !== 'Doomsday' && !!find(id),
  locate: id => civil.locate(id),
  locate3d: id => civil.locate3d(id),
  heading: id => civil.heading(id),
  ring: () => isOn() ? 0 : 18,
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
  visible(on) { shown.doomsday = on; theMap?.triggerRepaint(); },
  render(map) {
    map.getSource('ww-air-doom').setData({type: 'FeatureCollection', features: vipNow(true).map(h => ({type: 'Feature', geometry: {type: 'Point', coordinates: h.at},
      properties: {id: h.a.hex, label: (vipList[h.a.hex].type || 'Doomsday plane').replace(/^Boeing |^Ilyushin |^Tupolev /, '') + (h.ground ? ' (on the ground)' : '')}}))});
  },
  count: () => vipNow(true).length,
  rows: () => vipNow(true).filter(h => !h.ground).map(h => ({id: h.a.hex, time: now(), badge: '!', strong: true,
    title: `${(vipList[h.a.hex].type || 'Doomsday plane')} airborne`, meta: `${vipList[h.a.hex].operator || ''} · ${h.a.flight || vipList[h.a.hex].reg || h.a.hex.toUpperCase()}`})),
  owns: id => vipList[id]?.category === 'Doomsday' && !!find(id),
  locate: id => civil.locate(id),
  locate3d: id => civil.locate3d(id),
  heading: id => civil.heading(id),
  ring: () => isOn() ? 0 : 20,
  moving: true,
  detail,
};

// every aircraft on screen for the 3D models (models3d.js), where display() puts it. Called every frame: the output
// objects are reused (no garbage per frame) and the cheap on-screen test comes before anything else.
// VIP and doomsday aircraft are drawn whenever their own chip is on, whatever the Aircraft / Military chips say (their
// flat halo stops at MODEL_ZOOM because the model takes over).
const TINTS = {civil: ['#5856d6', '#eef0ff'], mil: ['#af52de', '#dcb8ff'], world: ['#8e8e93', '#aeb2bb'], vip: ['#c69200', '#ffd426'], doom: ['#d70015', '#ff6961']};
const pool = [], seen = new Set();
let milSet = new Set(), milSetFor = null;
addModelProvider((inView, out) => {
  const dark = matchMedia('(prefers-color-scheme: dark)').matches, stale = liveStale();
  if (milSetFor !== mil) { milSet = new Set(mil.map(a => a.hex)); milSetFor = mil; }
  seen.clear();
  let n = 0;
  const add = (a, from, isMil) => {
    if (seen.has(a.hex)) return;
    seen.add(a.hex);
    const v = vipList[a.hex], forced = v && (v.category === 'Doomsday' ? shown.doomsday : shown.vip);
    if (!forced && (isMil ? !shown.military : !shown.aircraft)) return;
    if (from === 'world' ? a.on_ground : a.alt_ft === 'ground') return;
    if (!inView(a.lon, a.lat)) return;
    if (from === 'world' && a.hex !== sel && inLive(a)) return;   // inside the live circle a 20-minute-old world position is a ghost
    let lon, lat, altM, track;
    if (from === 'world') { const w = where({a, from}); lon = w.lon; lat = w.lat; altM = w.altM; track = w.track; }
    else { const d = display(a); lon = d.lon; lat = d.lat; altM = d.alt == null ? null : d.alt * 0.3048; track = d.track; }
    const last = from === 'view' && stale;
    // the same colours as the flat icons (light) / near-white (dark), so a model stands out on either base map;
    // grey, and "last known", when the live feed has stopped answering
    const tint = (v?.category === 'Doomsday' ? TINTS.doom : v ? TINTS.vip : last ? TINTS.world : isMil ? TINTS.mil : from === 'world' ? TINTS.world : TINTS.civil)[+dark];
    const it = pool[n] || (pool[n] = {});
    n++;
    it.id = a.hex; it.layer = isMil ? 'military' : 'aircraft'; it.lon = lon; it.lat = lat; it.altM = altM; it.heading = track; it.type = a.type; it.category = a.category;
    it.tint = tint; it.label = (v ? vipLabel({a}) : a.flight || a.reg || '') + (last ? ' (last known)' : ''); it.sel = a.hex === sel;
    it.wait = from !== 'world' && !last && !!disp.get(a.hex)?.wait;
    out.push(it);
  };
  for (const a of view) add(a, 'view', a.military || milSet.has(a.hex));
  for (const a of mil) add(a, 'military', true);
  for (const a of world) add(a, 'world', false);
});
// the selected aircraft's flown path and route line, in the air with it
addPathProvider(() => {
  const h = sel && find(sel); if (!h) return null;
  const w = where(h);
  return {trail: flownLine(h, w), route: routeLine(w), color: matchMedia('(prefers-color-scheme: dark)').matches ? civil.color[1] : civil.color[0]};
});
civil.hit = point => { const d = hitModel(point); return d && d.layer === 'aircraft' ? d.id : null; };
military.hit = point => { const d = hitModel(point); return d && d.layer === 'military' ? d.id : null; };
// VIP and doomsday models answer clicks under their own chip too (they are drawn when the Aircraft chip is off)
vip.hit = point => { const d = hitModel(point); return d && vipList[d.id] && vipList[d.id].category !== 'Doomsday' ? d.id : null; };
doomsday.hit = point => { const d = hitModel(point); return d && vipList[d.id]?.category === 'Doomsday' ? d.id : null; };
