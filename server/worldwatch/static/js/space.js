// Satellites and launches.
// Satellite positions are calculated in the browser from CelesTrak's published orbit data with the standard
// SGP4 model (the same maths every tracker uses). The card shows how old the orbit data is.
// Launches come from Launch Library 2 and are drawn at their pads. No flight paths: none are published.
import {json2satrec} from '/static/vendor/satellite/io.js';
import {propagate, gstime} from '/static/vendor/satellite/propagation.js';
import {eciToGeodetic, degreesLat, degreesLong} from '/static/vendor/satellite/transforms.js';
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

// ---- true height on the globe ----
// On the globe each satellite is drawn at its real height above the surface, to the same scale as the Earth.
// MapLibre only draws on the surface, so the heights go on a canvas laid over the map: we work out the
// globe's camera from two points the map can place for us, then put each satellite where that camera sees it.
const isGlobe = () => theMap?.getProjection?.()?.type === 'globe';
let cam = null, drawn = [];
function camera() {
  const m = theMap, c = m.getCenter(), o = m.project(c), r = Math.PI / 180;
  const off = deg => { const p = m.project([c.lng + deg / Math.max(0.2, Math.cos(c.lat * r)), c.lat]); return Math.hypot(p.x - o.x, p.y - o.y); };
  const t1 = 4 * r, t2 = 24 * r, s1 = off(4), s2 = off(24);
  if (!(s1 > 0 && s2 > 0)) return null;
  const rho = s2 * Math.sin(t1) / (s1 * Math.sin(t2)), d = (Math.cos(t1) - rho * Math.cos(t2)) / (1 - rho);
  if (!isFinite(d) || d <= 1) return null;
  return {o, d, k: s1 * (d - Math.cos(t1)) / Math.sin(t1), lat0: c.lat * r, lon0: c.lng * r};
}
function place(lon, lat, km) {   // screen position of a point at a height, or null when the Earth hides it
  const r = Math.PI / 180, la = lat * r, dl = lon * r - cam.lon0, m = 1 + km / EARTH_KM;
  const x = m * Math.cos(la) * Math.sin(dl), y = m * (Math.cos(cam.lat0) * Math.sin(la) - Math.sin(cam.lat0) * Math.cos(la) * Math.cos(dl));
  const z = m * (Math.sin(cam.lat0) * Math.sin(la) + Math.cos(cam.lat0) * Math.cos(la) * Math.cos(dl));
  if (z >= cam.d - 0.05) return null;                                  // behind the camera
  const vx = x, vy = y, vz = z - cam.d, a = vx * vx + vy * vy + vz * vz, b = 2 * cam.d * vz, c = cam.d * cam.d - 1, disc = b * b - 4 * a * c;
  if (disc > 0) { const t = (-b - Math.sqrt(disc)) / (2 * a); if (t > 0 && t < 0.999) return null; }   // the line of sight meets the Earth first
  return [cam.o.x + cam.k * x / (cam.d - z), cam.o.y - cam.k * y / (cam.d - z)];
}
function drawHeights() {
  if (!cv) return;
  const m = theMap, box = m.getContainer(), dpr = Math.min(devicePixelRatio || 1, 2);
  if (cv.width !== box.clientWidth * dpr || cv.height !== box.clientHeight * dpr) { cv.width = box.clientWidth * dpr; cv.height = box.clientHeight * dpr; }
  const x = cv.getContext('2d'); x.setTransform(dpr, 0, 0, dpr, 0, 0); x.clearRect(0, 0, box.clientWidth, box.clientHeight);
  drawn = [];
  if (!shown || !isGlobe() || !(cam = camera())) return;
  const dark = matchMedia('(prefers-color-scheme: dark)').matches, col = satellites.color[+dark], edge = dark ? '#1c1c1e' : '#ffffff';
  for (const s of sats) {
    if (!s.pos) continue;
    const up = place(s.pos.lon, s.pos.lat, s.pos.km); if (!up) continue;
    const down = place(s.pos.lon, s.pos.lat, 0), big = s.id === ISS || 'sat:' + s.id === sel;
    if (down) { x.strokeStyle = col; x.globalAlpha = big ? 0.8 : 0.35; x.lineWidth = big ? 1.2 : 0.7; x.beginPath(); x.moveTo(down[0], down[1]); x.lineTo(up[0], up[1]); x.stroke(); }
    x.globalAlpha = 1; x.fillStyle = col; x.strokeStyle = edge; x.lineWidth = 1;
    x.beginPath(); x.arc(up[0], up[1], big ? 4 : 2, 0, 7); x.fill(); x.stroke();
    if ('sat:' + s.id === sel) { x.strokeStyle = dark ? '#ffffff' : '#000000'; x.lineWidth = 2; x.beginPath(); x.arc(up[0], up[1], 9, 0, 7); x.stroke(); }
    if (s.id === ISS) { x.font = '600 11px -apple-system, "SF Pro", system-ui, sans-serif'; x.fillStyle = dark ? '#e5e5ea' : '#1c3d24'; x.fillText('ISS', up[0] + 7, up[1] + 4); }
    drawn.push([up[0], up[1], 'sat:' + s.id]);
  }
}

function tick(map) {
  if (!map.getSource('ww-sats')) return;
  const t = now(), feats = [];
  for (const s of sats) {
    const p = where(s.rec, t); if (!p) continue;
    s.pos = p;
    feats.push({type: 'Feature', geometry: {type: 'Point', coordinates: [p.lon, p.lat]}, properties: {id: 'sat:' + s.id, iss: s.id === ISS, label: s.id === ISS ? 'ISS' : ''}});
  }
  map.getSource('ww-sats').setData({type: 'FeatureCollection', features: shown ? feats : []});
  // ground tracks: always the ISS, plus whichever satellite is selected; and the selected one's horizon circle
  const picked = sel && byId(sel), tracks = [];
  for (const s of [sats.find(x => x.id === ISS), picked].filter((v, i, a) => v && a.indexOf(v) === i)) tracks.push(track(s, t));
  map.getSource('ww-iss-track').setData({type: 'FeatureCollection', features: shown ? tracks : []});
  map.getSource('ww-sat-foot').setData({type: 'FeatureCollection', features: shown && picked?.pos ? [footprint(picked.pos)] : []});
  if (following && picked?.pos) map.easeTo({center: [picked.pos.lon, picked.pos.lat], duration: 1900, easing: x => x});
  drawHeights();
}

export const satellites = {
  id: 'satellites', title: 'Satellites', color: ['#28a745', '#30d158'], feeds: {satellites: 600}, layers: ['ww-iss-track', 'ww-sat-foot', 'ww-sats', 'ww-sats-label'],
  addTo(map) {
    theMap = map;
    for (const id of ['ww-sats', 'ww-iss-track', 'ww-sat-foot']) map.addSource(id, {type: 'geojson', data: {type: 'FeatureCollection', features: []}});
    map.addLayer({id: 'ww-iss-track', type: 'line', source: 'ww-iss-track', paint: {'line-width': 1.5, 'line-dasharray': [2, 2], 'line-opacity': 0.8}});
    map.addLayer({id: 'ww-sat-foot', type: 'line', source: 'ww-sat-foot', paint: {'line-width': 1.5, 'line-opacity': 0.9}});
    // On the flat map a satellite is a small dot at the point beneath it. On the globe that dot becomes a faint
    // ground mark and the satellite itself is drawn above it, at its real height.
    map.addLayer({id: 'ww-sats', type: 'circle', source: 'ww-sats', layout: {'circle-sort-key': ['case', ['get', 'iss'], 1, 0]},
      paint: {'circle-radius': ['case', ['get', 'iss'], 5, 2], 'circle-stroke-width': ['case', ['get', 'iss'], 1.2, 0.6]}});
    map.addLayer({id: 'ww-sats-label', type: 'symbol', source: 'ww-sats', filter: ['get', 'iss'],
      layout: {'text-field': ['get', 'label'], 'text-font': ['Noto Sans Bold'], 'text-size': 11, 'text-offset': [0, 1], 'text-anchor': 'top', 'text-allow-overlap': true}});
    cv = document.createElement('canvas');
    cv.style.cssText = 'position:absolute;inset:0;width:100%;height:100%;pointer-events:none;z-index:1';
    map.getContainer().appendChild(cv);
    map.on('move', drawHeights);
    map.on('dragstart', () => { if (following) { following = false; refresh?.(); } });
    setInterval(() => tick(map), 2000);
  },
  paint(map, dark) {
    const c = this.color[+dark], edge = dark ? '#1c1c1e' : '#ffffff';
    map.setPaintProperty('ww-sats', 'circle-color', c); map.setPaintProperty('ww-sats', 'circle-stroke-color', edge);
    map.setPaintProperty('ww-iss-track', 'line-color', c); map.setPaintProperty('ww-sat-foot', 'line-color', c);
    map.setPaintProperty('ww-sats-label', 'text-color', dark ? '#e5e5ea' : '#1c3d24');
    map.setPaintProperty('ww-sats-label', 'text-halo-color', edge); map.setPaintProperty('ww-sats-label', 'text-halo-width', 1.2);
    this.shape(map);
  },
  // called when the map switches between flat and globe
  shape(map) {
    const g = isGlobe();
    map.setPaintProperty('ww-sats', 'circle-opacity', g ? 0.25 : ['case', ['get', 'iss'], 1, 0.8]);
    map.setPaintProperty('ww-sats', 'circle-stroke-opacity', g ? 0 : 1);
    map.setPaintProperty('ww-sats-label', 'text-opacity', g ? 0 : 1);   // on the globe the label is drawn with the satellite, at height
    drawHeights();
  },
  onData(feed, d) {
    satInfo = d;
    sats = d.payload.omm.map(o => { try { return {id: o.NORAD_CAT_ID, name: o.OBJECT_NAME, omm: o, rec: json2satrec(o)}; } catch (e) { return null; } }).filter(Boolean);
  },
  render(map) { tick(map); },
  visible(on) { shown = on; if (theMap?.getSource('ww-sats')) { tick(theMap); this.shape(theMap); } },
  select(id) { const mine = id && String(id).startsWith('sat:') ? id : null; if (mine !== sel) following = false; sel = mine; if (theMap?.getSource('ww-sats')) tick(theMap); },
  hit(point) {   // a click on a satellite drawn above the globe
    let best = null, d2 = 100;
    for (const [x, y, id] of drawn) { const q = (x - point.x) ** 2 + (y - point.y) ** 2; if (q < d2) { d2 = q; best = id; } }
    return best;
  },
  act(name, map) {
    const s = sel && byId(sel); if (!s?.pos) return;
    if (name === 'follow') {
      following = !following;
      if (following) { const deg = horizon(s.pos.km) * 180 / Math.PI; map.easeTo({center: [s.pos.lon, s.pos.lat], zoom: Math.max(1, Math.min(6.5, Math.log2(360 / (2.8 * deg)))), duration: 900}); }
    }
  },
  count: () => sats.length,
  rows: () => [],
  locate(id) { const s = byId(id); return s?.pos && !isGlobe() ? [s.pos.lon, s.pos.lat] : null; },   // on the globe the canvas draws the ring at height
  ring: id => id === 'sat:' + ISS ? 11 : 8,
  moving: true,
  owns: id => String(id).startsWith('sat:'),
  about: () => 'The brightest satellites, each where it is right now. On the globe they are drawn at their real height, to scale. Select one for its path and the area it can see.',
  detail(id) {
    const s = byId(id);
    if (!s || !s.pos) return null;
    const e = epoch(s), p = s.pos, rad = horizon(p.km), wide = 2 * rad * EARTH_KM;
    return `<p class="eyebrow">Satellite</p>
      <h2>${esc(s.id === ISS ? 'International Space Station' : s.name)}</h2>
      <p class="where">Catalogue number ${s.id}${s.omm.OBJECT_ID ? ' · launched ' + esc(s.omm.OBJECT_ID.slice(0, 4)) : ''}</p>
      <dl>
        <dt>Over</dt><dd>${Math.abs(p.lat).toFixed(2)}° ${p.lat >= 0 ? 'N' : 'S'}, ${Math.abs(p.lon).toFixed(2)}° ${p.lon >= 0 ? 'E' : 'W'}</dd>
        <dt>Height</dt><dd>${Math.round(p.km).toLocaleString('en-GB')} km</dd>
        <dt>Speed</dt><dd>${p.kms ? (p.kms * 3600).toLocaleString('en-GB', {maximumFractionDigits: 0}) + ' km/h' : 'not available'}</dd>
        <dt>One orbit takes</dt><dd>${period(s) < 180 ? period(s).toFixed(1) + ' min' : (period(s) / 60).toFixed(1) + ' h'}</dd>
        <dt>Can see from up there</dt><dd>a circle ${Math.round(wide / 10) * 10 > 999 ? (Math.round(wide / 100) * 100).toLocaleString('en-GB') : Math.round(wide / 10) * 10} km across <span class="soft">(${(100 * (1 - Math.cos(rad)) / 2).toFixed(1)} % of the Earth)</span></dd>
        <dt>Orbit data from</dt><dd>${local(e)} <span class="soft">(${ago(e)})</span></dd>
      </dl>
      <button class="btn" data-act="follow">${following ? 'Stop following' : 'Look down from it'}</button>
      <p class="links"><a class="link" href="https://celestrak.org/satcat/table-satcat.php?CATNR=${s.id}" target="_blank" rel="noopener">CelesTrak catalogue entry</a>
      <a class="link" href="https://www.watched.earth" target="_blank" rel="noopener">watched.earth: which satellites passed over a place, and their pictures</a></p>
      <p class="source">Calculated here, now, from CelesTrak's orbit data (fetched ${ago(satInfo.fetched)}) with the standard SGP4 model; the older the orbit data, the less exact. Dashed line: its path over the ground, half an orbit back and one ahead. Solid circle: its horizon, the area it has in line of sight. That is geometry, not what a camera on board is pointed at, which nobody publishes. "Look down from it" centres the map beneath the satellite and follows it; the picture is the map, not a live view. Shown: CelesTrak's list of the ${sats.length} brightest satellites.</p>`;
  },
};
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
