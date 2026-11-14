// Satellites and launches.
// Satellite positions are calculated in the browser from CelesTrak's published orbit data with the standard
// SGP4 model (the same maths every tracker uses). The card shows how old the orbit data is.
// Launches come from Launch Library 2 and are drawn at their pads. No flight paths: none are published.
import {json2satrec} from '/static/vendor/satellite/io.js';
import {propagate, gstime} from '/static/vendor/satellite/propagation.js';
import {eciToGeodetic, degreesLat, degreesLong} from '/static/vendor/satellite/transforms.js';
import {ago, esc, local, now, utc} from './util.js';

const ISS = 25544;
let sats = [], satInfo = null, launchList = [], launchInfo = null, timer = null, shown = true;

function where(rec, t) {
  const d = new Date(t * 1000), pv = propagate(rec, d);
  if (!pv || !pv.position) return null;
  const g = eciToGeodetic(pv.position, gstime(d)), v = pv.velocity;
  return {lon: degreesLong(g.longitude), lat: degreesLat(g.latitude), km: g.height, kms: v ? Math.hypot(v.x, v.y, v.z) : null};
}
const epoch = s => Date.parse(s.omm.EPOCH + 'Z') / 1000;

function track(rec, t) {   // the ISS's ground track from 45 minutes ago to 45 minutes ahead, split where it crosses the date line
  const lines = [[]];
  let last = null;
  for (let m = -45; m <= 45; m += 1) {
    const p = where(rec, t + m * 60); if (!p) continue;
    if (last !== null && Math.abs(p.lon - last) > 180) lines.push([]);
    lines[lines.length - 1].push([p.lon, p.lat]); last = p.lon;
  }
  return {type: 'Feature', geometry: {type: 'MultiLineString', coordinates: lines.filter(l => l.length > 1)}, properties: {}};
}

function tick(map) {
  if (!shown || !map.getSource('ww-sats')) return;
  const t = now(), feats = [];
  for (const s of sats) {
    const p = where(s.rec, t); if (!p) continue;
    s.pos = p;
    feats.push({type: 'Feature', geometry: {type: 'Point', coordinates: [p.lon, p.lat]}, properties: {id: 'sat:' + s.id, iss: s.id === ISS, label: s.id === ISS ? 'ISS' : ''}});
  }
  map.getSource('ww-sats').setData({type: 'FeatureCollection', features: feats});
  const iss = sats.find(s => s.id === ISS);
  map.getSource('ww-iss-track').setData({type: 'FeatureCollection', features: iss ? [track(iss.rec, t)] : []});
}

export const satellites = {
  id: 'satellites', title: 'Satellites', color: ['#28a745', '#30d158'], feeds: {satellites: 600}, layers: ['ww-iss-track', 'ww-sats', 'ww-sats-label'],
  addTo(map) {
    map.addSource('ww-sats', {type: 'geojson', data: {type: 'FeatureCollection', features: []}});
    map.addSource('ww-iss-track', {type: 'geojson', data: {type: 'FeatureCollection', features: []}});
    map.addLayer({id: 'ww-iss-track', type: 'line', source: 'ww-iss-track', paint: {'line-width': 1.5, 'line-dasharray': [2, 2], 'line-opacity': 0.8}});
    map.addLayer({id: 'ww-sats', type: 'circle', source: 'ww-sats', layout: {'circle-sort-key': ['case', ['get', 'iss'], 1, 0]},
      paint: {'circle-radius': ['case', ['get', 'iss'], 7, 3], 'circle-stroke-width': ['case', ['get', 'iss'], 1.5, 0.8], 'circle-opacity': ['case', ['get', 'iss'], 1, 0.75]}});
    map.addLayer({id: 'ww-sats-label', type: 'symbol', source: 'ww-sats', filter: ['get', 'iss'],
      layout: {'text-field': ['get', 'label'], 'text-font': ['Noto Sans Bold'], 'text-size': 11, 'text-offset': [0, 1.1], 'text-anchor': 'top', 'text-allow-overlap': true}});
    timer = setInterval(() => tick(map), 2000);
  },
  paint(map, dark) {
    const c = this.color[+dark], edge = dark ? '#1c1c1e' : '#ffffff';
    map.setPaintProperty('ww-sats', 'circle-color', c); map.setPaintProperty('ww-sats', 'circle-stroke-color', edge);
    map.setPaintProperty('ww-iss-track', 'line-color', c);
    map.setPaintProperty('ww-sats-label', 'text-color', dark ? '#e5e5ea' : '#1c3d24');
    map.setPaintProperty('ww-sats-label', 'text-halo-color', edge); map.setPaintProperty('ww-sats-label', 'text-halo-width', 1.2);
  },
  onData(feed, d) {
    satInfo = d;
    sats = d.payload.omm.map(o => { try { return {id: o.NORAD_CAT_ID, name: o.OBJECT_NAME, omm: o, rec: json2satrec(o)}; } catch (e) { return null; } }).filter(Boolean);
  },
  render(map) { tick(map); },
  visible(on) { shown = on; },
  count: () => sats.length,
  rows: () => [],
  locate(id) { const s = sats.find(x => 'sat:' + x.id === id); return s?.pos ? [s.pos.lon, s.pos.lat] : null; },
  ring: id => id === 'sat:' + ISS ? 14 : 10,
  moving: true,
  owns: id => String(id).startsWith('sat:'),
  detail(id) {
    const s = sats.find(x => 'sat:' + x.id === id);
    if (!s || !s.pos) return null;
    const e = epoch(s), p = s.pos;
    return `<p class="eyebrow">Satellite</p>
      <h2>${esc(s.id === ISS ? 'International Space Station' : s.name)}</h2>
      <p class="where">Catalogue number ${s.id}${s.omm.OBJECT_ID ? ' · launched ' + esc(s.omm.OBJECT_ID.slice(0, 4)) : ''}</p>
      <dl>
        <dt>Over</dt><dd>${Math.abs(p.lat).toFixed(2)}° ${p.lat >= 0 ? 'N' : 'S'}, ${Math.abs(p.lon).toFixed(2)}° ${p.lon >= 0 ? 'E' : 'W'}</dd>
        <dt>Height</dt><dd>${Math.round(p.km).toLocaleString('en-GB')} km</dd>
        <dt>Speed</dt><dd>${p.kms ? (p.kms * 3600).toLocaleString('en-GB', {maximumFractionDigits: 0}) + ' km/h' : 'not available'}</dd>
        <dt>One orbit takes</dt><dd>${(1440 / s.omm.MEAN_MOTION).toFixed(1)} min</dd>
        <dt>Orbit data from</dt><dd>${local(e)} <span class="soft">(${ago(e)})</span></dd>
      </dl>
      <a class="link" href="https://celestrak.org/satcat/table-satcat.php?CATNR=${s.id}" target="_blank" rel="noopener">Open the CelesTrak catalogue entry</a>
      <p class="source">Calculated here, now, from CelesTrak's orbit data (fetched ${ago(satInfo.fetched)}) using the standard SGP4 model. The older the orbit data, the less exact the position; a few days is normally fine. Shown: CelesTrak's list of the ${sats.length} brightest satellites.${s.id === ISS ? ' The dashed line is the ground track from 45 minutes ago to 45 minutes ahead.' : ''}</p>`;
  },
};

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
