// Satellites and launches.
// Satellite positions are calculated in the browser from CelesTrak's published orbit data with the standard
// SGP4 model (the same maths every tracker uses). The card shows how old the orbit data is.
// Launches come from Launch Library 2 and are drawn at their pads. No flight paths: none are published.
import {json2satrec} from '../vendor/satellite/io.js';
import {propagate, gstime} from '../vendor/satellite/propagation.js';
import {eciToGeodetic, degreesLat, degreesLong} from '../vendor/satellite/transforms.js';
import {ago, esc, local, now, utc} from './util.js';

const ISS = 25544, EARTH_KM = 6371;
let sats = [], satInfo = null, launchList = [], launchInfo = null, shown = true, theMap = null, sel = null, following = false, cv = null;

function where(rec, t) {
  const d = new Date(t * 1000), pv = propagate(rec, d);
  if (!pv || !pv.position) return null;
  const g = eciToGeodetic(pv.position, gstime(d)), v = pv.velocity;
  return {lon: degreesLong(g.longitude), lat: degreesLat(g.latitude), km: g.height, kms: v ? Math.hypot(v.x, v.y, v.z) : null};
}
const epoch = s => Date.parse(s.omm.EPOCH + 'Z') / 1000;
const period = s => 1440 / s.omm.MEAN_MOTION;                      // minutes for one orbit
const byId = id => sats.find(x => 'sat:' + x.id === id);
// The usual names for orbits, by the standard definitions: height, the time for one orbit, and how stretched it is.
function orbit(s) {
  const P = period(s), e = s.omm.ECCENTRICITY, inc = s.omm.INCLINATION, a = Math.cbrt(398600.4418 * (P * 60 / (2 * Math.PI)) ** 2), mean = a - EARTH_KM;
  if (e > 0.25) return ['Highly elliptical orbit', `swings between ${Math.round(a * (1 - e) - EARTH_KM).toLocaleString('en-GB')} and ${Math.round(a * (1 + e) - EARTH_KM).toLocaleString('en-GB')} km`];
  if (Math.abs(P - 1436.1) < 30) return inc < 3 ? ['Geostationary orbit', 'stays over one spot on the equator, 35,786 km up'] : ['Geosynchronous orbit', 'one orbit per day, but tilted, so it drifts north and south'];
  if (mean < 2000) return ['Low Earth orbit', inc > 96 && inc < 100 ? 'sun-synchronous: passes each place at the same local time' : inc > 80 ? 'polar: passes near both poles' : 'below 2,000 km'];
  if (mean < 35786) return ['Medium Earth orbit', 'between 2,000 and 35,786 km, where navigation satellites fly'];
  return ['High Earth orbit', 'above the geostationary belt'];
}

function lines(points) {   // a path as map lines, split where it crosses the date line
  const out = [[]]; let last = null;
  for (const [lon, lat] of points) { if (last !== null && Math.abs(lon - last) > 180) out.push([]); out[out.length - 1].push([lon, lat]); last = lon; }
  return out.filter(l => l.length > 1);
}
// Where the satellite passes over the ground: half an orbit back and one orbit ahead (at most 3 hours each way).
function track(s, t) {
  const back = Math.min(period(s) / 2, 180), fwd = Math.min(period(s), 180), step = Math.max(0.5, (back + fwd) / 240), pts = [];
  for (let m = -back; m <= fwd; m += step) { const p = where(s.rec, t + m * 60); if (p) pts.push([p.lon, p.lat]); }
  return {type: 'Feature', geometry: {type: 'MultiLineString', coordinates: lines(pts)}, properties: {}};
}
// The part of the Earth a satellite can see at this moment: everything out to its horizon.
const horizon = km => Math.acos(EARTH_KM / (EARTH_KM + km));       // angle from the point beneath it, in radians
function footprint(p) {
  const d = horizon(p.km), la = p.lat * Math.PI / 180, lo = p.lon * Math.PI / 180, pts = [];
  for (let b = 0; b <= 360; b += 3) {
    const th = b * Math.PI / 180, la2 = Math.asin(Math.sin(la) * Math.cos(d) + Math.cos(la) * Math.sin(d) * Math.cos(th));
    const lo2 = lo + Math.atan2(Math.sin(th) * Math.sin(d) * Math.cos(la), Math.cos(d) - Math.sin(la) * Math.sin(la2));
    pts.push([((lo2 * 180 / Math.PI + 540) % 360) - 180, la2 * 180 / Math.PI]);
  }
  return {type: 'Feature', geometry: {type: 'MultiLineString', coordinates: lines(pts)}, properties: {}};
}

// ---- the globe: satellites in real 3D ----
// On the globe every satellite is drawn at its true point in space, to the same scale as the Earth, on a
// canvas laid over the map. The positions come from the map engine's own camera matrices (captured by an
// invisible custom layer on every frame), so they are exact at every zoom. The flat map shows plain dots.
const CLASS = {LEO: ['Low Earth orbit', '#28a745', '#30d158'], MEO: ['Medium Earth orbit', '#c98a00', '#ffc857'], GEO: ['Geostationary', '#007aff', '#7db7ff'], HEO: ['Highly elliptical', '#d6336c', '#ff7ab6']};
const classOf = s => { const P = period(s), e = s.omm.ECCENTRICITY, a = Math.cbrt(398600.4418 * (P * 60 / (2 * Math.PI)) ** 2); return e > 0.25 ? 'HEO' : Math.abs(P - 1436.1) < 30 ? 'GEO' : a - EARTH_KM < 2000 ? 'LEO' : a - EARTH_KM < 35786 ? 'MEO' : 'HEO'; };
const isGlobe = () => theMap?.getProjection?.()?.type === 'globe';
const isDark = () => matchMedia('(prefers-color-scheme: dark)').matches;
const tint = s => CLASS[s.cls][1 + isDark()];
let M = null, view = null, drawn = [];

const mul = (A, B) => { const o = new Float64Array(16); for (let c = 0; c < 4; c++) for (let r = 0; r < 4; r++) { let v = 0; for (let k = 0; k < 4; k++) v += A[k * 4 + r] * B[c * 4 + k]; o[c * 4 + r] = v; } return o; };
function clip(lon, lat, km) { const P = mul(M, theMap.transform.getMatrixForModel([lon, lat], km * 1000)); return [P[12], P[13], P[15]]; }
// Once per frame: where the camera is. It sits straight above the map's centre; its distance from the Earth's
// centre (in Earth radii) follows from how the engine's depth value changes between the ground and one radius up.
function camera() {
  const c = theMap.getCenter(), w0 = clip(c.lng, c.lat, 0)[2], w1 = clip(c.lng, c.lat, EARTH_KM)[2], box = theMap.getContainer();
  if (!(w0 - w1 > 0)) return null;
  return {d: w0 / (w0 - w1) + 1, lon0: c.lng * Math.PI / 180, lat0: c.lat * Math.PI / 180, w: box.clientWidth, h: box.clientHeight};
}
// A point at a height -> its place on screen, or null when the Earth is in the way or it is behind the camera.
function place(lon, lat, km) {
  const r = Math.PI / 180, la = lat * r, dl = lon * r - view.lon0, m = 1 + km / EARTH_KM;
  const x = m * Math.cos(la) * Math.sin(dl), y = m * (Math.cos(view.lat0) * Math.sin(la) - Math.sin(view.lat0) * Math.cos(la) * Math.cos(dl));
  const z = m * (Math.sin(view.lat0) * Math.sin(la) + Math.cos(view.lat0) * Math.cos(la) * Math.cos(dl));
  if (z >= view.d - 0.02) return null;
  const vz = z - view.d, a = x * x + y * y + vz * vz, b = 2 * view.d * vz, cc = view.d * view.d - 1, disc = b * b - 4 * a * cc;
  if (disc > 0) { const t = (-b - Math.sqrt(disc)) / (2 * a); if (t > 0 && t < 0.9995) return null; }
  const p = clip(lon, lat, km);
  return [(p[0] / p[2] + 1) / 2 * view.w, (1 - p[1] / p[2]) / 2 * view.h];
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
function spotlight(x, s) {   // the area the selected satellite can see, lit on the ground, and the cone down to it
  const d = horizon(s.pos.km), la = s.pos.lat * Math.PI / 180, lo = s.pos.lon * Math.PI / 180, edge = [], col = tint(s);
  for (let b = 0; b < 360; b += 4) {
    const th = b * Math.PI / 180, la2 = Math.asin(Math.sin(la) * Math.cos(d) + Math.cos(la) * Math.sin(d) * Math.cos(th));
    const lo2 = lo + Math.atan2(Math.sin(th) * Math.sin(d) * Math.cos(la), Math.cos(d) - Math.sin(la) * Math.sin(la2));
    const q = place(lo2 * 180 / Math.PI, la2 * 180 / Math.PI, 0); if (q) edge.push(q);
  }
  const up = place(s.pos.lon, s.pos.lat, s.pos.km), down = place(s.pos.lon, s.pos.lat, 0);
  if (edge.length > 8) {
    const cx = down ? down[0] : edge.reduce((a, q) => a + q[0], 0) / edge.length, cy = down ? down[1] : edge.reduce((a, q) => a + q[1], 0) / edge.length;
    const rad = Math.max(...edge.map(q => Math.hypot(q[0] - cx, q[1] - cy)));
    const g = x.createRadialGradient(cx, cy, 0, cx, cy, rad); g.addColorStop(0, col + '66'); g.addColorStop(0.75, col + '2e'); g.addColorStop(1, col + '14');
    x.beginPath(); edge.forEach((q, i) => i ? x.lineTo(q[0], q[1]) : x.moveTo(q[0], q[1])); x.closePath(); x.fillStyle = g; x.fill();
    x.strokeStyle = col; x.lineWidth = 1.5; x.globalAlpha = 0.9; x.stroke(); x.globalAlpha = 1;
    if (up && Math.hypot(up[0] - cx, up[1] - cy) > rad * 0.95) {   // the cone, when seen from the side: from the satellite to the two edge points furthest apart as seen from it
      let lo3 = null, hi3 = null, base = Math.atan2(cy - up[1], cx - up[0]);
      for (const q of edge) { let a = Math.atan2(q[1] - up[1], q[0] - up[0]) - base; a = Math.atan2(Math.sin(a), Math.cos(a)); if (!lo3 || a < lo3[0]) lo3 = [a, q]; if (!hi3 || a > hi3[0]) hi3 = [a, q]; }
      const cg = x.createLinearGradient(up[0], up[1], cx, cy); cg.addColorStop(0, col + '55'); cg.addColorStop(1, col + '05');
      x.beginPath(); x.moveTo(up[0], up[1]); x.lineTo(lo3[1][0], lo3[1][1]); x.lineTo(hi3[1][0], hi3[1][1]); x.closePath(); x.fillStyle = cg; x.fill();
    }
  }
}
function drawHeights() {
  if (!cv || !theMap) return;
  const box = theMap.getContainer(), dpr = Math.min(devicePixelRatio || 1, 2);
  if (cv.width !== Math.round(box.clientWidth * dpr) || cv.height !== Math.round(box.clientHeight * dpr)) { cv.width = Math.round(box.clientWidth * dpr); cv.height = Math.round(box.clientHeight * dpr); }
  const x = cv.getContext('2d'); x.setTransform(dpr, 0, 0, dpr, 0, 0); x.clearRect(0, 0, box.clientWidth, box.clientHeight);
  drawn = [];
  if (!shown || !isGlobe() || !M || !(view = camera())) return;
  const dark = isDark(), edge = dark ? '#1c1c1e' : '#ffffff', ink = dark ? '#f2f2f7' : '#1c1c1e', picked = sel && byId(sel), t = now();
  if (picked?.pos && !following) spotlight(x, picked);
  const iss = sats.find(s => s.id === ISS);
  for (const s of [iss, picked].filter((v, i, a) => v && a.indexOf(v) === i)) {
    if (!s.ring || t - s.ringAt > 20) { s.ring = ringOf(s, t); s.ringAt = t; }
    stroke(x, s.ring, tint(s), s === picked ? 2 : 1.2, s === picked ? 0.95 : 0.55);
  }
  for (const s of sats) {
    if (!s.pos) continue;
    const up = place(s.pos.lon, s.pos.lat, s.pos.km); if (!up) continue;
    const big = s.id === ISS || s === picked, col = tint(s);
    if (big) { const down = place(s.pos.lon, s.pos.lat, 0); if (down) { x.strokeStyle = col; x.globalAlpha = 0.6; x.lineWidth = 1; x.setLineDash([2, 3]); x.beginPath(); x.moveTo(down[0], down[1]); x.lineTo(up[0], up[1]); x.stroke(); x.setLineDash([]); x.globalAlpha = 1; } }
    x.fillStyle = col; x.strokeStyle = edge; x.lineWidth = big ? 1.2 : 0.6;
    x.beginPath(); x.arc(up[0], up[1], big ? 4.5 : 2, 0, 7); x.fill(); x.stroke();
    if (s === picked) { x.strokeStyle = ink; x.lineWidth = 2; x.beginPath(); x.arc(up[0], up[1], 9, 0, 7); x.stroke(); }
    if (big) { x.font = '600 11px "SF Pro", -apple-system, system-ui, sans-serif'; x.lineWidth = 3; x.strokeStyle = edge; const name = s.id === ISS ? 'ISS' : s.name; x.strokeText(name, up[0] + 12, up[1] + 4); x.fillStyle = ink; x.fillText(name, up[0] + 12, up[1] + 4); }
    drawn.push([up[0], up[1], 'sat:' + s.id]);
  }
  // which colour is which orbit, top of the map
  const used = [...new Set(sats.map(s => s.cls))].filter(c => CLASS[c]); let lx = (box.clientWidth + 420 - 340) / 2 - used.length * 62, ly = 34;
  x.font = '500 12px "SF Pro", -apple-system, system-ui, sans-serif';
  for (const c of used) { x.fillStyle = CLASS[c][1 + dark]; x.beginPath(); x.arc(lx, ly - 4, 4, 0, 7); x.fill(); x.lineWidth = 3; x.strokeStyle = edge; x.strokeText(CLASS[c][0], lx + 9, ly); x.fillStyle = ink; x.fillText(CLASS[c][0], lx + 9, ly); lx += x.measureText(CLASS[c][0]).width + 34; }
}

// "Look down from it": put the map's camera at the satellite's own point in space, facing straight down.
function sitAt(s, jump) {
  if (!view) return;
  const have = (view.d - 1) * EARTH_KM, z = theMap.getZoom() + Math.log2(have / Math.max(120, s.pos.km));
  theMap[jump ? 'jumpTo' : 'easeTo']({center: [s.pos.lon, s.pos.lat], zoom: z, ...(jump ? {} : {duration: 1900, easing: v => v})});
}

function tick(map) {
  if (!map.getSource('ww-sats')) return;
  const t = now(), feats = [];
  for (const s of sats) {
    const p = where(s.rec, t); if (!p) continue;
    s.pos = p;
    feats.push({type: 'Feature', geometry: {type: 'Point', coordinates: [p.lon, p.lat]}, properties: {id: 'sat:' + s.id, iss: s.id === ISS, cls: s.cls, label: s.id === ISS ? 'ISS' : ''}});
  }
  map.getSource('ww-sats').setData({type: 'FeatureCollection', features: shown && !isGlobe() ? feats : []});   // dots on the flat map only
  const picked = sel && byId(sel);
  if (following && picked?.pos) sitAt(picked, false);
  map.triggerRepaint();
}

export const satellites = {
  id: 'satellites', title: 'Satellites', color: ['#28a745', '#30d158'], feeds: {satellites: 600}, layers: ['ww-sats', 'ww-sats-label'],
  addTo(map) {
    theMap = map;
    map.addSource('ww-sats', {type: 'geojson', data: {type: 'FeatureCollection', features: []}});
    map.addLayer({id: 'ww-sats', type: 'circle', source: 'ww-sats', layout: {'circle-sort-key': ['case', ['get', 'iss'], 1, 0]},
      paint: {'circle-radius': ['case', ['get', 'iss'], 5, 2], 'circle-stroke-width': ['case', ['get', 'iss'], 1.2, 0.6], 'circle-opacity': ['case', ['get', 'iss'], 1, 0.85]}});
    map.addLayer({id: 'ww-sats-label', type: 'symbol', source: 'ww-sats', filter: ['get', 'iss'],
      layout: {'text-field': ['get', 'label'], 'text-font': ['Noto Sans Bold'], 'text-size': 11, 'text-offset': [0, 1], 'text-anchor': 'top', 'text-allow-overlap': true}});
    cv = document.createElement('canvas');
    cv.style.cssText = 'position:absolute;inset:0;width:100%;height:100%;pointer-events:none;z-index:1';
    map.getContainer().appendChild(cv);
    // an invisible layer whose only job is to hand us the engine's camera matrix on every frame
    map.addLayer({id: 'ww-sat-3d', type: 'custom', renderingMode: '3d', render(gl, args) { M = args.defaultProjectionData?.mainMatrix || null; drawHeights(); }});
    map.on('dragstart', () => { if (following) stopFollowing(); });
    setInterval(() => tick(map), 2000);
  },
  paint(map, dark) {
    const edge = dark ? '#1c1c1e' : '#ffffff';
    map.setPaintProperty('ww-sats', 'circle-color', ['match', ['get', 'cls'], 'MEO', CLASS.MEO[1 + dark], 'GEO', CLASS.GEO[1 + dark], 'HEO', CLASS.HEO[1 + dark], CLASS.LEO[1 + dark]]);
    map.setPaintProperty('ww-sats', 'circle-stroke-color', edge);
    map.setPaintProperty('ww-sats-label', 'text-color', dark ? '#e5e5ea' : '#1c3d24');
    map.setPaintProperty('ww-sats-label', 'text-halo-color', edge); map.setPaintProperty('ww-sats-label', 'text-halo-width', 1.2);
  },
  shape(map) { if (!isGlobe() && following) stopFollowing(); tick(map); },   // called when the map switches between flat and globe
  onData(feed, d) {
    satInfo = d;
    const keep = new Map(sats.map(s => [s.id, s]));
    sats = d.payload.omm.map(o => { try { const s = {id: o.NORAD_CAT_ID, name: o.OBJECT_NAME, omm: o, rec: json2satrec(o)}; s.cls = classOf(s); s.pos = keep.get(s.id)?.pos; return s; } catch (e) { return null; } }).filter(Boolean);
  },
  render(map) { tick(map); },
  visible(on) { shown = on; if (!on && following) stopFollowing(); if (theMap?.getSource('ww-sats')) tick(theMap); },
  select(id) { const mine = id && String(id).startsWith('sat:') ? id : null; if (mine !== sel && following) stopFollowing(); sel = mine; theMap?.triggerRepaint(); },
  hit(point) {   // a click on a satellite drawn above the globe
    let best = null, d2 = 144;
    for (const [x, y, id] of drawn) { const q = (x - point.x) ** 2 + (y - point.y) ** 2; if (q < d2) { d2 = q; best = id; } }
    return best;
  },
  act(name, map) {
    const s = sel && byId(sel); if (!s?.pos) return;
    if (name === 'follow') {
      if (following) return stopFollowing();
      if (!isGlobe()) document.getElementById('globe')?.click();          // the view from a point in space needs the globe
      following = true; restore = {center: map.getCenter(), zoom: map.getZoom()};
      map.setMinZoom(-2);
      setTimeout(() => { if (following) { map.triggerRepaint(); setTimeout(() => following && sitAt(s, true), 120); } }, isGlobe() ? 0 : 400);
    }
  },
  count: () => sats.length,
  rows: () => [],
  locate(id) { const s = byId(id); return s?.pos && !isGlobe() ? [s.pos.lon, s.pos.lat] : null; },   // on the globe the ring is drawn at height by the canvas
  ring: id => id === 'sat:' + ISS ? 11 : 8,
  moving: true,
  owns: id => String(id).startsWith('sat:'),
  about: () => 'Satellites where they are right now, coloured by orbit: low (green), medium (amber), geostationary (blue). On the globe they are at their real height, to scale; select one for its orbit and the area it can see.',
  detail(id) {
    const s = byId(id);
    if (!s || !s.pos) return null;
    const e = epoch(s), p = s.pos, rad = horizon(p.km), wide = 2 * rad * EARTH_KM, o = orbit(s);
    return `<p class="eyebrow">Satellite</p>
      <h2>${esc(s.id === ISS ? 'International Space Station' : s.name)}</h2>
      <p class="where"><span class="swatch" style="background:${tint(s)}"></span>${o[0]} <span class="sub">${o[1]}; tilted ${s.omm.INCLINATION.toFixed(1)}° to the equator</span></p>
      <dl>
        <dt>Over</dt><dd>${Math.abs(p.lat).toFixed(2)}° ${p.lat >= 0 ? 'N' : 'S'}, ${Math.abs(p.lon).toFixed(2)}° ${p.lon >= 0 ? 'E' : 'W'}</dd>
        <dt>Height</dt><dd>${Math.round(p.km).toLocaleString('en-GB')} km</dd>
        <dt>Speed</dt><dd>${p.kms ? (p.kms * 3600).toLocaleString('en-GB', {maximumFractionDigits: 0}) + ' km/h' : 'not available'}</dd>
        <dt>One orbit takes</dt><dd>${period(s) < 180 ? period(s).toFixed(1) + ' min' : (period(s) / 60).toFixed(1) + ' h'}</dd>
        <dt>Can see from up there</dt><dd>a circle ${Math.round(wide / 10) * 10 > 999 ? (Math.round(wide / 100) * 100).toLocaleString('en-GB') : Math.round(wide / 10) * 10} km across <span class="soft">(${(100 * (1 - Math.cos(rad)) / 2).toFixed(1)} % of the Earth)</span></dd>
        <dt>Orbit data from</dt><dd>${local(e)} <span class="soft">(${ago(e)})</span></dd>
        <dt>Catalogue number</dt><dd>${s.id}${s.omm.OBJECT_ID ? ' <span class="soft">· launched ' + esc(s.omm.OBJECT_ID.slice(0, 4)) + '</span>' : ''}</dd>
      </dl>
      <button class="btn" data-act="follow">${following ? 'Leave the satellite' : 'Look down from it'}</button>
      <p class="links"><a class="link" href="https://celestrak.org/satcat/table-satcat.php?CATNR=${s.id}" target="_blank" rel="noopener">CelesTrak catalogue entry</a>
      <a class="link" href="https://www.watched.earth" target="_blank" rel="noopener">watched.earth: which satellites passed over a place, and their pictures</a></p>
      <p class="source">Calculated here, now, from CelesTrak's orbit data (fetched ${ago(satInfo.fetched)}) with the standard SGP4 model; the older the orbit data, the less exact. On the globe: the ring is its orbit at this moment, the lit patch is everything it has in line of sight, the cone joins the two. That is geometry: where a camera on board points is not published. "Look down from it" puts the map's camera at the satellite's own point in space, facing straight down, and rides along; the picture is our map through a 37° lens, not a live image. The flat map shows a dot at the point beneath it.</p>`;
  },
};
let restore = null;
function stopFollowing() {
  following = false;
  theMap.setMinZoom(0.3);
  if (restore) theMap.easeTo({...restore, duration: 700});
  restore = null; refresh?.();
}
let refresh = null;
export const onSatChange = fn => { refresh = fn; };

const net = l => Date.parse(l.net) / 1000;
export const launches = {
  id: 'launches', title: 'Launches', color: ['#00a3b4', '#40c8e0'], feeds: {launches: 300}, layers: ['ww-launches', 'ww-launches-label'],
  addTo(map) {
    map.addSource('ww-launches', {type: 'geojson', data: {type: 'FeatureCollection', features: []}});
    map.addLayer({id: 'ww-launches', type: 'circle', source: 'ww-launches', paint: {'circle-radius': 9, 'circle-opacity': 0.95, 'circle-stroke-width': 1.2}});
    map.addLayer({id: 'ww-launches-label', type: 'symbol', source: 'ww-launches',
      layout: {'text-field': ['get', 'n'], 'text-font': ['Noto Sans Bold'], 'text-size': 10, 'text-allow-overlap': true, 'text-ignore-placement': true}, paint: {'text-color': '#ffffff'}});
  },
  paint(map, dark) {
    map.setPaintProperty('ww-launches', 'circle-color', this.color[+dark]);
    map.setPaintProperty('ww-launches', 'circle-stroke-color', dark ? '#1c1c1e' : '#ffffff');
  },
  onData(feed, d) { launchInfo = d; launchList = d.payload.launches; },
  render(map) {
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
      </dl>
      ${same.length ? `<p class="source">Also listed from this site: ${same.map(x => esc(x.name)).join('; ')}.</p>` : ''}
      <p class="source">Source: Launch Library 2 (The Space Devs). This entry was last edited ${l.updated ? ago(Date.parse(l.updated) / 1000) : 'at an unknown time'}; we fetched the list ${ago(launchInfo.fetched)}. Launch times slip often. No flight path is drawn because none is published.</p>`;
  },
};
