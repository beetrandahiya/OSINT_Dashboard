// Satellites and launches.
// Satellite positions are calculated in the browser from CelesTrak's published orbit data with the standard
// SGP4 model (the same maths every tracker uses). The card shows how old the orbit data is.
// Launches come from Launch Library 2 and are drawn at their pads. No flight paths: none are published.
import {eyeImages, eyeSwap, addEye} from './eyeicons.js';
import {json2satrec} from '../vendor/satellite/io.js';
import {propagate, gstime} from '../vendor/satellite/propagation.js';
import {eciToGeodetic, degreesLat, degreesLong, eciToEcf, ecfToLookAngles} from '../vendor/satellite/transforms.js';
import {ago, esc, local, now, utc} from './util.js';
import {satFlags, flagText, flagsHtml} from './flags.js';

const ISS = 25544, EARTH_KM = 6371;
let baseIds = new Set();   // satellites from the main CelesTrak feed (the rest came with the spy-satellite feed)
const span = d => d < 2 ? Math.round(d * 24) + ' hours' : Math.round(d) + ' days';
let sats = [], baseOmm = [], reconOmm = [], purposes = {}, reconInfo = null, catInfo = null, satInfo = null, launchList = [], launchInfo = null, shown = true, theMap = null, sel = null, following = false, cv = null;

function where(rec, t) {
  const d = new Date(t * 1000), pv = propagate(rec, d);
  if (!pv || !pv.position) return null;
  const g = eciToGeodetic(pv.position, gstime(d)), v = pv.velocity;
  return {lon: degreesLong(g.longitude), lat: degreesLat(g.latitude), km: g.height, kms: v ? Math.hypot(v.x, v.y, v.z) : null};
}
const epoch = s => Date.parse(s.omm.EPOCH + 'Z') / 1000;
const period = s => 1440 / s.omm.MEAN_MOTION;                      // minutes for one orbit
const byId = id => satById.get(id) || sats.find(x => 'sat:' + x.id === id);
// The usual names for orbits, by the standard definitions: height, the time for one orbit, and how stretched it is.
function orbit(s) {
  const P = period(s), e = s.omm.ECCENTRICITY, inc = s.omm.INCLINATION, a = Math.cbrt(398600.4418 * (P * 60 / (2 * Math.PI)) ** 2), mean = a - EARTH_KM;
  if (e > 0.25) return ['Highly elliptical orbit', `swings between ${Math.round(a * (1 - e) - EARTH_KM).toLocaleString('en-GB')} and ${Math.round(a * (1 + e) - EARTH_KM).toLocaleString('en-GB')} km`];
  if (Math.abs(P - 1436.1) < 30) return inc < 3 ? ['Geostationary orbit', 'stays over one spot on the equator, 35,786 km up'] : ['Geosynchronous orbit', 'one orbit per day, but tilted, so it drifts north and south'];
  if (mean < 2000) return ['Low Earth orbit', inc > 96 && inc < 100 ? 'sun-synchronous: passes each place at the same local time' : inc > 80 ? 'polar: passes near both poles' : 'below 2,000 km'];
  if (mean < 35786) return ['Medium Earth orbit', 'between 2,000 and 35,786 km, where navigation satellites fly'];
  return ['High Earth orbit', 'above the geostationary belt'];
}

// The part of the Earth a satellite can see at this moment: everything out to its horizon.
const R2D = 180 / Math.PI;
const horizon = km => Math.acos(EARTH_KM / (EARTH_KM + km));       // angle from the point beneath it, in radians

// ---- the globe: satellites in real 3D ----
// On the globe every satellite is drawn at its true point in space, to the same scale as the Earth, on a
// canvas laid over the map. The positions come from the map engine's own camera matrices (captured by an
// invisible custom layer on every frame), so they are exact at every zoom. The flat map shows plain dots.
const CLASS = {LEO: ['Low Earth orbit', '#28a745', '#30d158'], MEO: ['Medium Earth orbit', '#c98a00', '#ffc857'], GEO: ['Geostationary', '#007aff', '#7db7ff'], HEO: ['Highly elliptical', '#d6336c', '#ff7ab6']};
const classOf = s => { const P = period(s), e = s.omm.ECCENTRICITY, a = Math.cbrt(398600.4418 * (P * 60 / (2 * Math.PI)) ** 2); return e > 0.25 ? 'HEO' : Math.abs(P - 1436.1) < 30 ? 'GEO' : a - EARTH_KM < 2000 ? 'LEO' : a - EARTH_KM < 35786 ? 'MEO' : 'HEO'; };
// What a satellite does (UCS Satellite Database), one word each, with a letter drawn beside it on the globe.
const WHAT = {imaging: ['I', 'Imaging (cameras)'], radar: ['R', 'Radar imaging'], signals: ['S', 'Signals intelligence'], warning: ['W', 'Missile early warning'],
  weather: ['M', 'Weather'], navigation: ['N', 'Navigation'], comms: ['C', 'Communications'], science: ['X', 'Science'], technology: ['T', 'Technology test'], other: ['?', 'Other']};
const flagsOf = s => satFlags(s.omm.OWNER, purposes[s.id]?.[2]);
const what = s => purposes[s.id] || (s.source === 'amateur observers' ? ['classified', true] : null);
const isSpy = s => { const w = what(s); return !!w && (w[0] === 'classified' || (w[1] && ['imaging', 'radar', 'signals', 'warning'].includes(w[0]))); };
// What each satellite is, worked out once when the data arrives instead of on every frame.
const satById = new Map();
let issSat = null, usedCls = [], anySpy = false;
function annotate() {
  satById.clear();
  for (const s of sats) { s.w = what(s); s.spy = isSpy(s); s.flags = flagText(flagsOf(s)); satById.set('sat:' + s.id, s); }
  issSat = satById.get('sat:' + ISS) || null; usedCls = [...new Set(sats.map(s => s.cls))].filter(c => CLASS[c]); anySpy = sats.some(s => s.spy);
}
document.addEventListener('ww-flags', () => annotate());
const isGlobe = () => theMap?.getProjection?.()?.type === 'globe';
const darkQ = matchMedia('(prefers-color-scheme: dark)');
const tint = (s, dark = darkQ.matches) => CLASS[s.cls][1 + dark];   // the per-frame drawing passes `dark` (matchMedia per satellite per frame was measurable)
let M = null, view = null, drawn = [], cleared = true;

// The globe in the engine's own frame: the Earth is the unit sphere around the origin, a point at a height h lies at
// (1 + h / R) x (cos lat sin lon, sin lat, cos lat cos lon) (MapLibre's globe getMatrixForModel: rotate by longitude,
// by latitude, move out along z), and mainMatrix takes that frame straight to clip space. Computing the point directly
// spares a 4x4 matrix per satellite per frame.
const R_KM = 6371.0088;   // the engine's Earth radius
function world(lon, lat, km) {
  const la = lat / R2D, lo = lon / R2D, m = 1 + km / R_KM, c = Math.cos(la);
  return [m * c * Math.sin(lo), m * Math.sin(la), m * c * Math.cos(lo)];
}
// Once per frame: where the camera is, in the same frame. It is the one point clip space puts at x = y = w = 0, so it
// solves three rows of the camera matrix (Cramer's rule). Exact at any tilt and turn; the old estimate assumed the camera
// straight above the map centre and drew satellites through the Earth (and hid visible ones) whenever the map was tilted.
const cross = (u, v) => [u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0]];
function camera() {
  if (theMap.transform.isGlobeRendering === false) return null;   // zoomed in so far that the globe is drawn flat
  const a0 = [M[0], M[4], M[8]], a1 = [M[1], M[5], M[9]], a2 = [M[3], M[7], M[11]], b = [-M[12], -M[13], -M[15]];
  const c12 = cross(a1, a2), c20 = cross(a2, a0), c01 = cross(a0, a1), D = a0[0] * c12[0] + a0[1] * c12[1] + a0[2] * c12[2];
  if (!D) return null;
  const c = [0, 1, 2].map(k => (b[0] * c12[k] + b[1] * c20[k] + b[2] * c01[k]) / D), box = theMap.getContainer();
  return {c, cc: c[0] * c[0] + c[1] * c[1] + c[2] * c[2], w: box.clientWidth, h: box.clientHeight};
}
// A point at a height -> its place on screen, or null when the Earth is in the way or it is behind the camera.
function place(lon, lat, km) {
  const p = world(lon, lat, km), w = M[3] * p[0] + M[7] * p[1] + M[11] * p[2] + M[15];
  if (!(w > 0)) return null;
  // the line from the camera to the point: does it meet the Earth (unit sphere) before it gets there?
  const c = view.c, dx = p[0] - c[0], dy = p[1] - c[1], dz = p[2] - c[2], a = dx * dx + dy * dy + dz * dz, bb = 2 * (c[0] * dx + c[1] * dy + c[2] * dz), disc = bb * bb - 4 * a * (view.cc - 1);
  if (disc > 0) { const t = (-bb - Math.sqrt(disc)) / (2 * a); if (t > 0 && t < 0.9995) return null; }
  return [((M[0] * p[0] + M[4] * p[1] + M[8] * p[2] + M[12]) / w + 1) / 2 * view.w, (1 - (M[1] * p[0] + M[5] * p[1] + M[9] * p[2] + M[13]) / w) / 2 * view.h];
}
// One whole orbit as a ring in space, frozen at this instant (the Earth turns beneath it as time passes).
function ringOf(s, t) {
  const g = gstime(new Date(t * 1000)), P = period(s) * 60, pts = [];
  for (let i = 0; i <= 96; i++) { const pv = propagate(s.rec, new Date((t + i / 96 * P) * 1000)); if (!pv?.position) continue;
    const gd = eciToGeodetic(pv.position, g); pts.push([degreesLong(gd.longitude), degreesLat(gd.latitude), gd.height]); }
  return pts;
}
function stroke(x, pts, color, width, alpha) {   // a 3D line: drawn where it is in view, broken where the Earth hides it
  x.strokeStyle = color; x.lineWidth = width; x.globalAlpha = alpha; x.beginPath();
  let pen = false;
  for (const p of pts) { const q = place(p[0], p[1], p[2]); if (!q) { pen = false; continue; } if (pen) x.lineTo(q[0], q[1]); else x.moveTo(q[0], q[1]); pen = true; }
  x.stroke(); x.globalAlpha = 1;
}
// Points as 3D vectors in Earth radii (x toward 0°E on the equator, z toward the north pole), and back.
const vec = (lon, lat, km) => { const r = 1 + km / EARTH_KM, la = lat / R2D, lo = lon / R2D; return [r * Math.cos(la) * Math.cos(lo), r * Math.cos(la) * Math.sin(lo), r * Math.sin(la)]; };
const geo = v => { const r = Math.hypot(v[0], v[1], v[2]); return [Math.atan2(v[1], v[0]) * R2D, Math.asin(v[2] / r) * R2D, (r - 1) * EARTH_KM]; };
const mix = (a, b, f) => [a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f, a[2] + (b[2] - a[2]) * f];
// A point on the ground at angular distance `ang` and bearing `brg` from (lo, la), in radians.
function around(lo, la, ang, brg) {
  const la2 = Math.asin(Math.sin(la) * Math.cos(ang) + Math.cos(la) * Math.sin(ang) * Math.cos(brg));
  return [(lo + Math.atan2(Math.sin(brg) * Math.sin(ang) * Math.cos(la), Math.cos(ang) - Math.sin(la) * Math.sin(la2))) * R2D, la2 * R2D];
}
// Fill a grid of 3D points as small quads, each only where all its corners are in view. That way the Earth
// hides whatever is behind it, the same way it hides the satellites themselves.
function mesh(x, grid, alphaOf, col) {
  x.fillStyle = col;
  for (let i = 0; i < grid.length - 1; i++) for (let j = 0; j < grid[i].length; j++) {
    const k = (j + 1) % grid[i].length, a = grid[i][j], b = grid[i][k], c = grid[i + 1][k], d = grid[i + 1][j];
    if (!a || !b || !c || !d) continue;
    x.globalAlpha = alphaOf(i);
    x.beginPath(); x.moveTo(a[0], a[1]); x.lineTo(b[0], b[1]); x.lineTo(c[0], c[1]); x.lineTo(d[0], d[1]); x.closePath(); x.fill();
  }
  x.globalAlpha = 1;
}
const SPOKES = 48, RINGS = 6, STEPS = 9;
function spotlight(x, s, dark) {   // the beam from the selected satellite and the patch of ground it can see
  const ang = horizon(s.pos.km), lo = s.pos.lon / R2D, la = s.pos.lat / R2D, col = tint(s, dark), top = vec(s.pos.lon, s.pos.lat, s.pos.km);
  const rim = Array.from({length: SPOKES}, (_, j) => around(lo, la, ang, j / SPOKES * 2 * Math.PI));
  // the lit patch: rings from the point beneath the satellite out to its horizon, brighter in the middle
  const patch = [];
  for (let i = 0; i <= RINGS; i++) {
    const f = i / RINGS;
    patch.push(i === 0 ? Array(SPOKES).fill(place(s.pos.lon, s.pos.lat, 0)) : rim.map((_, j) => { const g = around(lo, la, ang * f, j / SPOKES * 2 * Math.PI); return place(g[0], g[1], 0); }));
  }
  mesh(x, patch, i => 0.34 - i * 0.04, col);
  // the beam: straight lines from the satellite to every point of the horizon, sampled along their length
  const beam = [];
  for (let i = 0; i <= STEPS; i++) {
    const f = i / STEPS;
    beam.push(rim.map(g => { const p = geo(mix(top, vec(g[0], g[1], 0), f)); return place(p[0], p[1], p[2]); }));
  }
  mesh(x, beam, i => 0.11 - i * 0.008, col);
  // the horizon line, broken where it goes round the back of the Earth
  stroke(x, [...rim, rim[0]].map(g => [g[0], g[1], 0]), col, 1.5, 0.9);
}
// The stretch of the map between the sidebar and the card (whichever are open), in map pixels.
function freeArea(box) {
  const m = box.getBoundingClientRect(), vis = el => el && !el.hidden && el.offsetParent !== null && !el.classList.contains('min');
  const side = document.getElementById('sidebar'), card = document.getElementById('detail');
  let l = 0, r = m.width;
  if (vis(side)) { const b = side.getBoundingClientRect(); if (b.left - m.left < m.width / 2) l = Math.max(l, b.right - m.left); }
  if (vis(card)) { const b = card.getBoundingClientRect(); if (b.left - m.left > m.width / 2) r = Math.min(r, b.left - m.left); else l = Math.max(l, b.right - m.left); }
  return r - l > 200 ? [l, r] : [0, m.width];
}
function drawHeights() {
  if (!cv || !theMap) return;
  const box = theMap.getContainer(), dpr = Math.min(devicePixelRatio || 1, 2);
  if (cv.width !== Math.round(box.clientWidth * dpr) || cv.height !== Math.round(box.clientHeight * dpr)) { cv.width = Math.round(box.clientWidth * dpr); cv.height = Math.round(box.clientHeight * dpr); }
  const x = cv.getContext('2d');
  const live = shown && isGlobe() && M && (view = camera());
  if (!live && cleared) return;                      // nothing drawn last frame either: no work while the layer is off
  x.setTransform(dpr, 0, 0, dpr, 0, 0); x.clearRect(0, 0, box.clientWidth, box.clientHeight);
  drawn = []; cleared = !live;
  if (!live) return;
  const dark = darkQ.matches, edge = dark ? '#1c1c1e' : '#ffffff', ink = dark ? '#f2f2f7' : '#1c1c1e', red = dark ? '#ff453a' : '#ff3b30', picked = sel && byId(sel), t = now();
  if (picked?.pos && !following) spotlight(x, picked, dark);
  for (const s of [issSat, picked].filter((v, i, a) => v && a.indexOf(v) === i)) {
    if (!s.ring || t - s.ringAt > 20) { s.ring = ringOf(s, t); s.ringAt = t; }
    stroke(x, s.ring, tint(s, dark), s === picked ? 2 : 1.2, s === picked ? 0.95 : 0.55);
  }
  for (const s of sats) {
    if (!s.pos) continue;
    const up = place(s.pos.lon, s.pos.lat, s.pos.km); if (!up || up[0] < -20 || up[1] < -20 || up[0] > box.clientWidth + 20 || up[1] > box.clientHeight + 20) continue;
    const big = s.id === ISS || s === picked, col = CLASS[s.cls][1 + dark];
    if (big) { x.setLineDash([2, 3]); stroke(x, Array.from({length: 13}, (_, i) => [s.pos.lon, s.pos.lat, s.pos.km * i / 12]), col, 1, 0.6); x.setLineDash([]); }
    if (s.spy && !big) {                          // military imaging / radar / signals: a small red diamond
      x.fillStyle = red; x.strokeStyle = edge; x.lineWidth = 0.6;
      x.beginPath(); x.moveTo(up[0], up[1] - 3); x.lineTo(up[0] + 3, up[1]); x.lineTo(up[0], up[1] + 3); x.lineTo(up[0] - 3, up[1]); x.closePath(); x.fill(); x.stroke();
    } else {
      x.fillStyle = col; x.strokeStyle = edge; x.lineWidth = big ? 1.2 : 0.4;
      x.beginPath(); x.arc(up[0], up[1], big ? 4 : 1.5, 0, 7); x.fill(); x.stroke();
    }
    if (s === picked) { x.strokeStyle = ink; x.lineWidth = 2; x.beginPath(); x.arc(up[0], up[1], 9, 0, 7); x.stroke(); }
    if (big) { x.font = '600 11px "SF Pro", -apple-system, system-ui, sans-serif'; x.lineWidth = 3; x.strokeStyle = edge; const name = s.id === ISS ? 'ISS' : s.name; x.strokeText(name, up[0] + 12, up[1] + 4); x.fillStyle = ink; x.fillText(name, up[0] + 12, up[1] + 4); }
    drawn.push([up[0], up[1], 'sat:' + s.id, big, s.spy]);
  }
  // what each one does, as a letter beside it, once few enough are in view to read
  if (drawn.length && drawn.length < 160) {
    x.font = '600 9px "SF Pro", -apple-system, system-ui, sans-serif'; x.lineWidth = 2.5;
    for (const [px, py, id] of drawn) {
      const sat = satById.get(id); if (!sat) continue;
      const w = sat.w, L = w ? (w[0] === 'classified' ? 'S?' : WHAT[w[0]]?.[0]) : null;
      if (L) { x.font = '600 9px "SF Pro", -apple-system, system-ui, sans-serif'; x.strokeStyle = edge; x.strokeText(L, px + 5, py - 4); x.fillStyle = sat.spy ? red : ink; x.fillText(L, px + 5, py - 4); }
    }
  }
  // which colour is which orbit, top of the map, centred over the part of the map no panel covers
  x.font = '500 12px "SF Pro", -apple-system, system-ui, sans-serif';
  // in rows that fit between the panels (one row ran under the card)
  const items = [...(anySpy ? [['spy', 'Military imaging or signals']] : []), ...usedCls.map(c => [c, CLASS[c][0]])].map(([k, t2]) => [k, t2, x.measureText(t2).width + 9]);
  const free = freeArea(box), room = free[1] - free[0] - 24, rows = [[]];
  let used = -25;
  for (const it of items) { if (used + it[2] + 25 > room && rows[rows.length - 1].length) { rows.push([]); used = -25; } rows[rows.length - 1].push(it); used += it[2] + 25; }
  x.lineWidth = 3; x.strokeStyle = edge;
  rows.forEach((row, i) => {
    const w = row.reduce((n, it) => n + it[2] + 25, -25), ly = 34 + i * 18;
    let lx = Math.max(free[0] + 16, (free[0] + free[1] - w) / 2) + 4;
    for (const [k, t2, wd] of row) {
      x.fillStyle = k === 'spy' ? red : CLASS[k][1 + dark]; x.beginPath();
      if (k === 'spy') { x.moveTo(lx, ly - 8); x.lineTo(lx + 4, ly - 4); x.lineTo(lx, ly); x.lineTo(lx - 4, ly - 4); x.closePath(); } else x.arc(lx, ly - 4, 4, 0, 7);
      x.fill(); x.strokeText(t2, lx + 9, ly); x.fillStyle = ink; x.fillText(t2, lx + 9, ly); lx += wd + 25;
    }
  });
}

// "Look down from it": put the map's camera at the satellite's own point in space, facing straight down, north up.
// The camera's distance from the map centre is fixed in pixels, so in Earth radii it scales with cos(latitude) / 2^zoom
// (the globe is drawn at the Mercator scale of its centre): solve the zoom that puts it at the satellite's height.
function sitAt(s, jump) {
  const v = M && camera(); if (!v) return;
  const c = theMap.getCenter(), g = world(c.lng, c.lat, 0), d = Math.hypot(v.c[0] - g[0], v.c[1] - g[1], v.c[2] - g[2]);
  const cos = la => Math.max(0.02, Math.cos(la / R2D));
  const z = theMap.getZoom() + Math.log2(d * R_KM / Math.max(120, s.pos.km)) + Math.log2(cos(s.pos.lat) / cos(c.lat));
  theMap[jump ? 'jumpTo' : 'easeTo']({center: [s.pos.lon, s.pos.lat], zoom: z, pitch: 0, bearing: 0, ...(jump ? {} : {duration: 1900, easing: v2 => v2})});
}

let flatSent = false;
function tick(map) {
  const src = map.getSource('ww-sats');
  if (!src || !shown) return;                       // nothing to work out while the layer is off
  const t = now(), flat = !isGlobe(), feats = [];
  for (const s of sats) {
    const p = where(s.rec, t); if (!p) continue;
    s.pos = p;
    if (flat) feats.push({type: 'Feature', geometry: {type: 'Point', coordinates: [p.lon, p.lat]}, properties: {id: 'sat:' + s.id, iss: s.id === ISS, cls: s.cls, spy: !!s.spy, label: s.id === ISS ? 'ISS' : ''}});
  }
  // dots on the flat map only; on the globe the canvas draws them, so the source is emptied once, not every tick
  if (flat || flatSent) { src.setData({type: 'FeatureCollection', features: feats}); flatSent = flat; }
  const picked = sel && byId(sel);
  if (following && picked?.pos) sitAt(picked, false);
  map.triggerRepaint();
}

export const satellites = {
  id: 'satellites', title: 'Satellites', color: ['#28a745', '#30d158'], feeds: {satellites: 600, recon_sats: 1800, sat_catalog: 21600}, layers: ['ww-sats', 'ww-sats-label'],
  addTo(map) {
    theMap = map;
    map.addSource('ww-sats', {type: 'geojson', data: {type: 'FeatureCollection', features: []}});
    map.addLayer({id: 'ww-sats', type: 'circle', source: 'ww-sats', layout: {'circle-sort-key': ['case', ['==', ['get', 'iss'], true], 1, 0]},
      paint: {'circle-radius': ['case', ['==', ['get', 'iss'], true], 4.5, ['==', ['get', 'spy'], true], 2.4, 1.5], 'circle-stroke-width': ['case', ['==', ['get', 'iss'], true], 1.2, 0.4], 'circle-opacity': ['case', ['==', ['get', 'iss'], true], 1, 0.85]}});
    map.addLayer({id: 'ww-sats-label', type: 'symbol', source: 'ww-sats', filter: ['get', 'iss'],
      layout: {'text-field': ['get', 'label'], 'text-font': ['Noto Sans Bold'], 'text-size': 11, 'text-offset': [0, 1], 'text-anchor': 'top', 'text-allow-overlap': true}});
    cv = document.createElement('canvas');
    cv.style.cssText = 'position:absolute;inset:0;width:100%;height:100%;pointer-events:none;z-index:1';
    map.getContainer().appendChild(cv);
    // an invisible layer whose only job is to hand us the engine's camera matrix on every frame
    map.addLayer({id: 'ww-sat-3d', type: 'custom', renderingMode: '3d', render(gl, args) { M = args.defaultProjectionData?.mainMatrix || null; drawHeights(); }});
    // a drag, turn or tilt by hand while riding hands the camera back where the owner put it (no flying back, card kept);
    // the engine fires rotatestart / pitchstart for our own easeTo too, so only events from the mouse or touch count
    const takeOver = e => { if (following && e.originalEvent) { following = false; ride = null; refresh?.(); } };
    for (const ev of ['dragstart', 'rotatestart', 'pitchstart']) map.on(ev, takeOver);
    setInterval(() => { if (!document.hidden) tick(map); }, 2000);   // not in a hidden tab
  },
  paint(map, dark) {
    const edge = dark ? '#1c1c1e' : '#ffffff';
    map.setPaintProperty('ww-sats', 'circle-color', ['case', ['==', ['get', 'spy'], true], dark ? '#ff453a' : '#ff3b30', ['match', ['get', 'cls'], 'MEO', CLASS.MEO[1 + dark], 'GEO', CLASS.GEO[1 + dark], 'HEO', CLASS.HEO[1 + dark], CLASS.LEO[1 + dark]]]);
    map.setPaintProperty('ww-sats', 'circle-stroke-color', edge);
    map.setPaintProperty('ww-sats-label', 'text-color', dark ? '#e5e5ea' : '#1c3d24');
    map.setPaintProperty('ww-sats-label', 'text-halo-color', edge); map.setPaintProperty('ww-sats-label', 'text-halo-width', 1.2);
  },
  shape(map) { if (!isGlobe() && following) stopFollowing(); tick(map); },   // called when the map switches between flat and globe
  onData(feed, d) {
    if (feed === 'sat_catalog') { catInfo = d; purposes = d.payload.purpose || {}; annotate(); return; }
    if (feed === 'recon_sats') { reconInfo = d; reconOmm = d.payload.omm || []; } else { satInfo = d; baseOmm = d.payload.omm || []; baseIds = new Set(baseOmm.map(o => o.NORAD_CAT_ID)); }
    const keep = new Map(sats.map(s => [s.id, s])), seen = new Set();
    sats = [...baseOmm, ...reconOmm].filter(o => !seen.has(o.NORAD_CAT_ID) && seen.add(o.NORAD_CAT_ID)).map(o => {
      try { const s = {id: o.NORAD_CAT_ID, name: o.OBJECT_NAME, omm: o, rec: json2satrec(o), source: o.SOURCE || 'CelesTrak'}; s.cls = classOf(s); s.pos = keep.get(s.id)?.pos; return s; } catch (e) { return null; }
    }).filter(Boolean);
    annotate();
  },
  render(map) { tick(map); },
  visible(on) { shown = on; if (!on && following) stopFollowing(); if (theMap?.getSource('ww-sats')) tick(theMap); },
  select(id) {
    const mine = id && String(id).startsWith('sat:') ? id : null; if (mine !== sel && following) stopFollowing(); sel = mine;
    // on the globe the list cannot fly to it through locate() (the ring is drawn at height): bring it into view when it
    // is not on screen, e.g. a manoeuvre row for a satellite on the far side
    const s = mine && isGlobe() && shown && byId(mine);
    if (s?.pos && !drawn.some(d => d[2] === mine)) theMap.easeTo({center: [s.pos.lon, s.pos.lat], duration: calmQ.matches ? 0 : 900});
    theMap?.triggerRepaint();
  },
  hit(point) {   // a click on a satellite drawn above the globe: 6 px around a dot, 12 around the ISS or the selected one;
    // when more than 300 are on screen the plain dots cover much of the globe, so only the ISS and spy diamonds answer
    let best = null, d2 = Infinity; const crowd = drawn.length > 300;
    for (const [x, y, id, big, spy] of drawn) {
      if (crowd && !big && !spy) continue;
      const q = (x - point.x) ** 2 + (y - point.y) ** 2, r = big ? 12 : 6;
      if (q < r * r && q < d2) { d2 = q; best = id; }
    }
    return best;
  },
  act(name, map) {
    const s = sel && byId(sel); if (!s?.pos) return;
    if (name === 'follow') {
      if (following) return stopFollowing();
      ride = {restore: {center: map.getCenter(), zoom: map.getZoom(), pitch: map.getPitch(), bearing: map.getBearing()}, wasFlat: !isGlobe()};
      // the view from a point in space needs the globe: switched for the ride only, the saved choice stays as it was
      if (ride.wasFlat) document.dispatchEvent(new CustomEvent('ww-shape', {detail: {globe: true}}));
      following = true;
      setTimeout(() => { if (following) { map.triggerRepaint(); setTimeout(() => following && sitAt(s, false), 120); } }, ride.wasFlat ? 400 : 0);
    }
  },
  async fill(id) {
    const box = document.getElementById('satwho'); if (!box || box.dataset.done) return;
    box.dataset.done = '1';
    const norad = box.dataset.norad;
    let r = satCards.get(norad);
    if (!r) { try { r = await fetch('/api/satellite/' + norad + '?name=' + encodeURIComponent(box.dataset.name || '')).then(x => x.json()); satCards.set(norad, r); } catch (e) { box.dataset.done = ''; return; } }
    const top = document.getElementById('satwho'), about = document.getElementById('satabout');
    if (!top || top.dataset.norad !== norad) return;
    const wd = r.wikidata || {}, u = r.ucs;
    top.innerHTML = wd.image ? `<div class="photo"><a href="${esc(wd.image_link || 'https://www.wikidata.org/wiki/' + (wd.qid || wd.family_qid || ''))}" target="_blank" rel="noopener"><img src="${esc(wd.image)}" alt="Picture" loading="lazy" onerror="this.closest('.photo').outerHTML='<p class=pic-wait>The picture could not be loaded.</p>'"></a><span>${wd.image_link ? esc(wd.image_of) + ', NASA Image Library (may show the type or a sister satellite)' : 'Picture of ' + esc(wd.image_of || 'this satellite') + ', from Wikimedia Commons via Wikidata. Often an artist\'s impression.'}</span></div>`
      : `<p class="pic-wait">${r.problem ? esc(r.problem) + '; no picture this time.' : 'No picture of this satellite or its type on Wikidata or in NASA\'s image library.'}</p>`;
    const rowsHtml = [
      wd.description && `<p class="prof-intro">${esc(wd.description[0].toUpperCase() + wd.description.slice(1))}.</p>`,
      u && `<dt>Does</dt><dd>${esc(u.purpose || '')}${u.detail ? ' · ' + esc(u.detail) : ''}</dd>`,
      u?.users && `<dt>Used by</dt><dd>${esc(u.users)}</dd>`,
      (u?.operator || wd.operators?.length) && `<dt>Operator</dt><dd>${esc(u?.operator || wd.operators.join(', '))}${u?.country ? ` <span class="soft">· ${esc(u.country)}</span>` : ''}</dd>`,
      wd.kinds?.length && `<dt>Kind</dt><dd>${wd.kinds.map(esc).join(', ')}</dd>`,
      (u?.contractor || wd.makers?.length) && `<dt>Built by</dt><dd>${esc(u?.contractor || wd.makers.join(', '))}</dd>`,
      u?.launched && `<dt>Launched</dt><dd>${esc(u.launched)}</dd>`,
    ].filter(Boolean);
    if (about) about.dataset.done = '1';
    if (about) about.innerHTML = rowsHtml.length ? `<section class="pz"><h3>What it is</h3>${rowsHtml.filter(x => x.startsWith('<p')).join('')}<dl>${rowsHtml.filter(x => !x.startsWith('<p')).join('')}</dl>
      ${wd.wikipedia ? `<a class="link" href="${esc(wd.wikipedia)}" target="_blank" rel="noopener">Wikipedia</a>` : ''}
      <p class="source">From ${[u && 'the UCS Satellite Database (last updated May 2023)', r.wikidata && Object.keys(wd).length && 'Wikidata'].filter(Boolean).join(' and ')}.</p></section>`
      : `<p class="source">No entry for catalogue number ${esc(norad)} in the UCS database or Wikidata.</p>`;
  },
  count: () => sats.length,
  // manoeuvres of spy satellites seen in the last 7 days (worked out on the server from the orbit history it keeps)
  rows: () => (reconInfo?.payload.manoeuvres || []).filter(m => m.to > Date.now() / 1000 - 7 * 86400 && byId('sat:' + m.norad)).map(m => ({
    id: 'sat:' + m.norad, time: m.to, badge: '⇅',
    title: `${m.name || 'Satellite ' + m.norad} ${m.kinds.map(k => k === 'raised' ? 'raised its orbit' : k === 'lowered' ? 'lowered its orbit' : 'changed its orbital plane').join(' and ')}`,
    meta: `perigee ${m.perigee[0]} → ${m.perigee[1]} km, apogee ${m.apogee[0]} → ${m.apogee[1]} km · orbits ${span(m.days)} apart${m.amateur ? ' · amateur-tracked orbit' : ''}`})),
  locate(id) { const s = byId(id); return s?.pos && !isGlobe() ? [s.pos.lon, s.pos.lat] : null; },   // on the globe the ring is drawn at height by the canvas
  ring: id => id === 'sat:' + ISS ? 11 : 8,
  moving: true,
  owns: id => String(id).startsWith('sat:'),
  about: () => 'Satellites where they are right now, coloured by orbit: low (green), medium (amber), geostationary (blue). On the globe they are at their real height, to scale; select one for its orbit and the area it can see.',
  detail(id) {
    const s = byId(id);
    if (!s || !s.pos) return null;
    const e = epoch(s), p = s.pos, rad = horizon(p.km), wide = 2 * rad * EARTH_KM, o = orbit(s);
    const w = what(s);
    return `<div id="satwho" data-norad="${s.id}" data-name="${esc(s.name)}"><p class="pic-wait">Looking for a picture…</p></div>
      <p class="eyebrow">${w ? (w[0] === 'classified' ? 'Classified US satellite' : (w[1] ? 'Military · ' : '') + WHAT[w[0]][1]) : 'Satellite'}</p>
      <h2>${esc(s.id === ISS ? 'International Space Station' : s.name)}${flagsOf(s) ? ' ' + flagsHtml(flagsOf(s)) : ''}</h2>
      <p class="where"><span class="swatch" style="background:${tint(s)}"></span>${o[0]} <span class="sub">${o[1]}; tilted ${s.omm.INCLINATION.toFixed(1)}° to the equator</span></p>
      <dl>
        ${(() => { const f = flagsOf(s); return f && (f.ccs.length || f.name) ? `<dt>Owner</dt><dd>${flagsHtml(f)} ${esc(f.name || 'per the UCS database')}</dd>` : ''; })()}
        <dt>Over</dt><dd>${Math.abs(p.lat).toFixed(2)}° ${p.lat >= 0 ? 'N' : 'S'}, ${Math.abs(p.lon).toFixed(2)}° ${p.lon >= 0 ? 'E' : 'W'}</dd>
        <dt>Height</dt><dd>${Math.round(p.km).toLocaleString('en-GB')} km</dd>
        <dt>Speed</dt><dd>${p.kms ? (p.kms * 3600).toLocaleString('en-GB', {maximumFractionDigits: 0}) + ' km/h' : 'not available'}</dd>
        <dt>One orbit takes</dt><dd>${period(s) < 180 ? period(s).toFixed(1) + ' min' : (period(s) / 60).toFixed(1) + ' h'}</dd>
        <dt>Can see from up there</dt><dd>a circle ${Math.round(wide / 10) * 10 > 999 ? (Math.round(wide / 100) * 100).toLocaleString('en-GB') : Math.round(wide / 10) * 10} km across <span class="soft">(${(100 * (1 - Math.cos(rad)) / 2).toFixed(1)} % of the Earth)</span></dd>
        <dt>Orbit data from</dt><dd>${local(e)} <span class="soft">(${ago(e)})</span></dd>
        <dt>Catalogue number</dt><dd>${s.id}${s.omm.OBJECT_ID ? ' <span class="soft">· launched ' + esc(s.omm.OBJECT_ID.slice(0, 4)) + '</span>' : ''}</dd>
      </dl>
      ${(() => {
        const mv = (reconInfo?.payload.manoeuvres || []).filter(m => m.norad === s.id);
        const kept = reconInfo?.payload.history_days;
        if (!reconOmm.some(o => o.NORAD_CAT_ID === s.id)) return '';
        const am = s.source === 'amateur observers', high = period(s) > 225;   // the same limits as satinfo.limits() on the server
        const rule = am ? `rise over 5 km, drop over 10 km plus 1 km a day, plane change over 0.2°${high ? ' plus 0.0025° a day' : ''} (amateur orbits are rougher)`
          : high ? 'rise or drop over 3 km, plane change over 0.03° plus 0.0025° a day (in high orbits the Sun and Moon tilt the plane by up to 0.85° a year and the Earth\'s uneven gravity moves the orbit by a few km)'
          : 'rise over 0.8 km, drop over 3 km plus 1 km a day, plane change over 0.03° plus 0.0005° a day';
        return `<section class="pz"><h3>Orbit changes</h3>${mv.length ? `<ul class="dos-list">${mv.map(m => `<li><b>${m.kinds.join(', ')}</b> between the orbits of ${local(m.from)} and ${local(m.to)} <span class="soft">(${span(m.days)} apart)</span><br><span class="soft">perigee ${m.perigee[0]} → ${m.perigee[1]} km · apogee ${m.apogee[0]} → ${m.apogee[1]} km · inclination ${m.inclination[0]}° → ${m.inclination[1]}°</span></li>`).join('')}</ul>`
          : `<p class="soft">None seen in the orbits this server has collected${kept != null ? ` since it started keeping them ${span(kept)} ago` : ''} (up to 45 days; the first orbit kept can be older than that).</p>`}
          <p class="source">Worked out here by comparing each new published orbit with the one before. Air drag only lowers an orbit, slowly, so a rise, a drop much faster than drag, or a change of plane beyond natural drift means the satellite fired its engine. Limits for this one: ${rule}. The longer two orbits lie apart, the more natural change is allowed.</p></section>`;
      })()}
      <div id="satabout"></div>
      ${s.source === 'amateur observers' ? `<p class="source">Its orbit is not published by its owner. These elements come from amateur observers who track it by eye and camera (Mike McCants' list, from the SeeSat-L community), dated ${local(e)}; they can be off by tens of kilometres.</p>` : ''}
      <button class="btn" data-act="follow">${following ? 'Leave the satellite' : 'Look down from it'}</button>
      <p class="links"><a class="link" href="https://celestrak.org/satcat/table-satcat.php?CATNR=${s.id}" target="_blank" rel="noopener">CelesTrak catalogue entry</a>
      <a class="link" href="https://www.watched.earth" target="_blank" rel="noopener">watched.earth: which satellites passed over a place, and their pictures</a></p>
      <p class="source">Calculated here, now, from ${s.source === 'amateur observers' ? 'the amateur observers\' orbit data' : 'CelesTrak\'s orbit data'} (fetched ${(i => i ? ago(i.fetched) : 'at an unknown time')(baseIds.has(s.id) ? satInfo : reconInfo)}) with the standard SGP4 model; the older the orbit data, the less exact. On the globe: the ring is its orbit at this moment, the lit patch is everything it has in line of sight, the cone joins the two. That is geometry: where a camera on board points is not published. "Look down from it" puts the map's camera at the satellite's own point in space, facing straight down with north up, and rides along (drag the map to take the camera back; "Leave the satellite" returns to your view); the picture is our map through a 37° lens, not a live image. The flat map shows a dot at the point beneath it.</p>`;
  },
};
let ride = null;           // while riding: the view to go back to, and whether the map was flat before
const satCards = new Map(), calmQ = matchMedia('(prefers-reduced-motion: reduce)');
function stopFollowing() {
  following = false;
  const r = ride; ride = null;
  if (r) {
    if (r.wasFlat && isGlobe()) { document.dispatchEvent(new CustomEvent('ww-shape', {detail: {globe: false}})); theMap.jumpTo(r.restore); }
    else theMap.easeTo({...r.restore, duration: calmQ.matches ? 0 : 700});
  }
  refresh?.();
}
let refresh = null;
export const onSatChange = fn => { refresh = fn; };

const net = l => Date.parse(l.net) / 1000;

// ---- launch corridors: the official hazard areas published for a launch, joined to its pad ----
// A US flight restriction of type SPACE OPERATIONS within 150 km of the pad whose dates name the launch day, and
// navy rocket / space-debris warnings within 4,000 km whose own date-time groups include the launch day (UTC,
// one day either side for slips). Nothing is drawn from a guess: no area, no corridor.
let airInfo = null, navInfo = null;
const MON = ['JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN', 'JUL', 'AUG', 'SEP', 'OCT', 'NOV', 'DEC'];
const MONTH = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];
const kmApart = (a, b) => { const r = Math.PI / 180, x = Math.sin((b[1] - a[1]) * r / 2) ** 2 + Math.cos(a[1] * r) * Math.cos(b[1] * r) * Math.sin((b[0] - a[0]) * r / 2) ** 2; return 12742 * Math.asin(Math.sqrt(x)); };
const ringMid = rings => { let x = 0, y = 0, n = 0; for (const r of rings || []) for (const p of r) { x += p[0]; y += p[1]; n++; } return n ? [x / n, y / n] : null; };   // null: no shape to place
function launchDays(l) { const d = new Date(Date.parse(l.net)); return [-1, 0, 1].map(k => new Date(d.getTime() + k * 86400000)); }
function corridor(l) {
  if (l.lat == null) return null;
  const pad = [l.lon, l.lat], days = launchDays(l), areas = [];
  for (const t of airInfo?.payload.tfrs || []) {
    if (!/SPACE/i.test(t.type || '')) continue;
    const mid = ringMid(t.polys);
    if (!mid || kmApart(pad, mid) > 150) continue;
    if (!days.some(d => (t.where || '').includes(`${MONTH[d.getUTCMonth()]} ${d.getUTCDate()},`))) continue;
    areas.push({kind: 'US flight restriction', ref: 'NOTAM ' + t.notam, rings: t.polys, mid});
  }
  for (const w of navInfo?.payload.warnings || []) {
    if (w.kind !== 'rocket') continue;
    const rings = w.geoms.filter(g => g.type === 'Polygon').map(g => g.coordinates[0]);
    if (!rings.length) continue;
    const mid = ringMid(rings);
    if (!mid || kmApart(pad, mid) > 4000) continue;
    const text = w.text.toUpperCase();
    const named = days.some(d => new RegExp(`\\b${String(d.getUTCDate()).padStart(2, '0')}\\d{4}Z(?:\\s+TO\\s+\\d{6}Z)?\\s+${MON[d.getUTCMonth()]}\\b`).test(text) ||
      new RegExp(`\\b${d.getUTCDate()}\\s+(?:THRU|TO|AND|-)?\\s*\\d*\\s*${MON[d.getUTCMonth()]}\\b`).test(text));
    if (!named) continue;
    areas.push({kind: 'Navy rocket warning', ref: w.ref, rings, mid});
  }
  if (!areas.length) return null;
  areas.sort((a, b) => kmApart(pad, a.mid) - kmApart(pad, b.mid));
  return {pad, areas, line: [pad, ...areas.map(a => a.mid)]};
}
export const launches = {
  id: 'launches', title: 'Launches', color: ['#00a3b4', '#40c8e0'], feeds: {launches: 300, airspace: 900, navwarn: 600},
  layers: ['ww-corridor-fill', 'ww-corridor-line', 'ww-launches', 'ww-launches-label', 'ww-launches-eye'],
  addTo(map) {
    map.addSource('ww-corridor', {type: 'geojson', data: {type: 'FeatureCollection', features: []}});
    map.addLayer({id: 'ww-corridor-fill', type: 'fill', source: 'ww-corridor', filter: ['==', ['geometry-type'], 'Polygon'], paint: {'fill-opacity': 0.18}});
    map.addLayer({id: 'ww-corridor-line', type: 'line', source: 'ww-corridor', paint: {'line-width': 1.6, 'line-dasharray': [3, 2]}});
    map.addSource('ww-launches', {type: 'geojson', data: {type: 'FeatureCollection', features: []}});
    map.addLayer({id: 'ww-launches', type: 'circle', source: 'ww-launches', paint: {'circle-radius': 9, 'circle-opacity': 0.95, 'circle-stroke-width': 1.2}});
    map.addLayer({id: 'ww-launches-label', type: 'symbol', source: 'ww-launches',
      layout: {'text-field': ['get', 'n'], 'text-font': ['Noto Sans Bold'], 'text-size': 10, 'text-allow-overlap': true, 'text-ignore-placement': true}, paint: {'text-color': '#ffffff'}});
  },
  paint(map, dark) {
    map.setPaintProperty('ww-launches', 'circle-color', this.color[+dark]);
    map.setPaintProperty('ww-corridor-fill', 'fill-color', this.color[+dark]);
    map.setPaintProperty('ww-corridor-line', 'line-color', this.color[+dark]);
    map.setPaintProperty('ww-launches', 'circle-stroke-color', dark ? '#1c1c1e' : '#ffffff');
    if (!map.getLayer('ww-launches-eye')) addEye(map, 'ww-launches-eye', 'ww-launches', 'eye-launch', 0.62);
    eyeImages(map, dark); eyeSwap(map, ['ww-launches-eye'], ['ww-launches', 'ww-launches-label']);
  },
  onData(feed, d) { if (feed === 'airspace') airInfo = d; else if (feed === 'navwarn') navInfo = d; else { launchInfo = d; launchList = d.payload.launches; } },
  render(map) {
    const feats = [], t0 = now();
    for (const l of launchList) {
      if (net(l) > t0 + 4 * 86400 || net(l) < t0 - 6 * 3600) continue;    // corridors for the next four days only
      const c = corridor(l); if (!c) continue;
      for (const a of c.areas) for (const r of a.rings) feats.push({type: 'Feature', geometry: {type: 'Polygon', coordinates: [r]}, properties: {id: l.id}});
      feats.push({type: 'Feature', geometry: {type: 'LineString', coordinates: c.line}, properties: {id: l.id}});
    }
    map.getSource('ww-corridor').setData({type: 'FeatureCollection', features: feats});
    const sites = new Map();   // several launches can share a site: one marker, labelled with how many
    for (const l of launchList) if (l.lat != null) { const k = l.site; sites.set(k, {l: sites.get(k)?.l ?? l, n: (sites.get(k)?.n ?? 0) + 1}); }
    map.getSource('ww-launches').setData({type: 'FeatureCollection', features: [...sites.values()].map(({l, n}) => (
      {type: 'Feature', geometry: {type: 'Point', coordinates: [l.lon, l.lat]}, properties: {id: l.id, n: String(n)}}))});
  },
  count: () => launchList.length,
  rows() {
    const t = now();
    return launchList.filter(l => net(l) < t + 7 * 86400).map(l => ({id: l.id, time: net(l), badge: '↑',
      title: l.name, meta: `Launch · ${local(net(l))} · ${ago(net(l))} · ${l.status}`}));
  },
  locate(id) { const l = launchList.find(x => x.id === id); return l && l.lat != null ? [l.lon, l.lat] : null; },
  ring: () => 15,
  detail(id) {
    const l = launchList.find(x => x.id === id);
    if (!l) return null;
    const same = launchList.filter(x => x.site === l.site && x.id !== l.id);
    return `<p class="eyebrow">Rocket launch</p>
      <h2>${esc(l.name)}</h2>
      <p class="where">${esc(l.provider || '')}</p>
      <dl>
        <dt>Planned time</dt><dd>${local(net(l))} <span class="soft">(${utc(net(l))}, ${ago(net(l))})</span></dd>
        <dt>Status</dt><dd>${esc(l.status || 'not given')}</dd>
        <dt>Pad</dt><dd>${esc(l.pad || 'not given')}</dd>
        <dt>Site</dt><dd>${esc(l.site || 'not given')}</dd>
        ${l.orbit ? `<dt>Target orbit</dt><dd>${esc(l.orbit)}</dd>` : ''}
      </dl>
      ${l.mission ? `<p class="prof-intro">${esc(l.mission)}</p>` : ''}
      ${(() => { const c = corridor(l); return c ? `<section class="pz"><h3>Official hazard areas for this launch</h3><ul class="pz-list">${c.areas.map(a => `<li>${esc(a.kind)} <span class="soft">· ${esc(a.ref)} · ${Math.round(kmApart(c.pad, a.mid)).toLocaleString('en-GB')} km from the pad</span></li>`).join('')}</ul>
        <p class="source">Drawn on the map with a dashed line from the pad through them, nearest first. The line only joins published areas: it shows the direction the rocket is expected to fly, not its path or height.</p></section>`
        : `<p class="source">No published hazard area matched this launch yet (US flight restrictions near the pad, navy rocket warnings naming the launch day).</p>`; })()}
      ${same.length ? `<p class="source">Also listed from this site: ${same.map(x => esc(x.name)).join('; ')}.</p>` : ''}
      <p class="source">Source: Launch Library 2 (The Space Devs). This entry was last edited ${l.updated ? ago(Date.parse(l.updated) / 1000) : 'at an unknown time'}; we fetched the list ${ago(launchInfo.fetched)}. Launch times slip often. The flight path itself is not published by anyone, so it is not drawn.</p>`;
  },
};

// ---- which spy satellites passed over a place in the last 24 hours ----
// For every military imaging, radar or signals satellite we have an orbit for, its position every minute over the
// last day, and its elevation as seen from the place. A pass counts when it rose above 30 degrees: high enough that
// its sensors could have been pointed at the place. Whether they were is not published.
// Coarse to fine, so the page does not freeze (it took over a second in one go): every 150 seconds first, then every
// 30 seconds wherever a satellite was more than 5 degrees up. A pass that climbs past 30 degrees stays above 5 degrees for
// at least 260 seconds even at 180 km (geometry), so no coarse gap can miss one; the peak is found more exactly than the
// old one-minute steps. A few satellites at a time, with a pause for the page in between.
const COARSE = 150, FINE = 30, LOOK = 5;
async function passes(lat, lon, hours = 24) {
  const obs = {latitude: lat / R2D, longitude: lon / R2D, height: 0}, t1 = Date.now() / 1000, t0 = t1 - hours * 3600, out = [];
  const elev = (s, t) => { const d = new Date(t * 1000), pv = propagate(s.rec, d); return pv?.position ? ecfToLookAngles(obs, eciToEcf(pv.position, gstime(d))).elevation * R2D : -90; };
  const list = sats.filter(s => isSpy(s) && period(s) <= 225);   // low orbits only: high ones watch half the Earth all day, "passing over" means nothing there
  for (let i = 0; i < list.length; i++) {
    if (i && i % 12 === 0) await new Promise(r => setTimeout(r, 0));
    const s = list[i], spans = [];
    for (let t = t0; t <= t1; t += COARSE) if (elev(s, t) >= LOOK) {
      const a = Math.max(t0, t - COARSE), b = Math.min(t1, t + COARSE), last = spans[spans.length - 1];
      if (last && a <= last[1]) last[1] = b; else spans.push([a, b]);
    }
    for (const [a, b] of spans) {
      let cur = null;
      for (let t = a; t <= b + 0.1; t += FINE) {
        const el = elev(s, t);
        if (el >= 30) { if (!cur || el > cur.el) cur = {t, el}; }
        else if (cur) { out.push({s, ...cur}); cur = null; }
      }
      if (cur) out.push({s, ...cur});
    }
  }
  return out.sort((a, b) => b.t - a.t);
}
document.addEventListener('click', e => {
  const b = e.target.closest('[data-spypass]'); if (!b) return;
  let box = b.closest('.spypass'); const lat = +box.dataset.lat, lon = +box.dataset.lon;
  b.disabled = true; b.textContent = 'Working it out…'; box.dataset.done = 'wait';   // a redraw keeps the box as it is
  setTimeout(async () => {
    const list = await passes(lat, lon), n = new Set(list.map(p => p.s.id)).size;
    // the card may have been redrawn meanwhile (feeds refresh it): write into the box that is there now, same place
    const now2 = [...document.querySelectorAll('.spypass')].find(x => +x.dataset.lat === lat && +x.dataset.lon === lon);
    if (!now2) return;
    box = now2;
    box.dataset.done = '1';
    box.innerHTML = `<h3>Spy satellites overhead, last 24 hours</h3>${list.length ? `<ul class="pz-list">${list.slice(0, 25).map(p => {
      const w = what(p.s), kind = w[0] === 'classified' ? 'classified US satellite' : WHAT[w[0]][1].toLowerCase();
      return `<li><a href="#" data-satpick="${p.s.id}">${esc(p.s.name)}</a> <span class="soft">· ${esc(kind)} · ${now() - p.t < 120 ? 'overhead now' : local(p.t) + ' (' + ago(p.t) + ')'} · ${Math.round(p.el)}° up</span></li>`; }).join('')}</ul>` : '<p>None rose above 30° here.</p>'}
      <p class="source">${list.length} passes by ${n} of the ${sats.filter(x => isSpy(x) && period(x) <= 225).length} military imaging, radar and signals satellites in low orbit we have orbits for (public orbits from CelesTrak, classified US ones from amateur observers). Counted when the satellite was more than 30° above the horizon here, at its highest moment. That says it could have looked, not that it did. Satellites in high orbits (early warning, some signals satellites) watch half the Earth at once and are left out. Many military satellites are missing from public lists.</p>`;
  }, 30);
});
document.addEventListener('click', e => {
  const a = e.target.closest('[data-satpick]'); if (!a) return;
  e.preventDefault(); window.dispatchEvent(new CustomEvent('ww-pick', {detail: {layer: 'satellites', id: 'sat:' + a.dataset.satpick}}));
});
// for checking the geometry from the browser console: place(lon, lat, km) as the last frame drew it
export const satDebug = {view: () => view, passes: (lat, lon) => passes(lat, lon), spies: () => sats.filter(s => isSpy(s) && period(s) <= 225), place: (lon, lat, km) => (M && view ? place(lon, lat, km) : undefined)};
