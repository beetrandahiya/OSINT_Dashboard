// GPS interference, as worked out by GPSJAM (gpsjam.org) from the navigation accuracy that aircraft report.
// This is the one layer that is somebody else's analysis rather than raw readings; it shows a whole past day.
import {ago, esc} from './util.js';
import {slot} from './map.js';

// A hexagon that straddles the date line arrives with corners near +180 and -180; drawn as given it would smear across
// the whole map. Moving the western corners past 180 keeps it one small shape (the map draws longitudes beyond 180).
function unwrap(fc) {
  for (const f of fc?.features || []) for (const ring of f.geometry?.type === 'Polygon' ? f.geometry.coordinates : []) {
    const lons = ring.map(p => p[0]);
    if (Math.max(...lons) - Math.min(...lons) > 180) for (const p of ring) if (p[0] < 0) p[0] += 360;
  }
  return fc;
}

let data = null, info = null, cells = new Map();
export default {
  id: 'gps', title: 'GPS', color: ['#d49a00', '#ffd60a'], feeds: {gps: 1800}, layers: ['ww-gps'],
  addTo(map) {
    map.addSource('ww-gps', {type: 'geojson', data: {type: 'FeatureCollection', features: []}, maxzoom: 7});   // hexagons of ~1,700 km²: nothing to gain from finer tiles
    map.addLayer({id: 'ww-gps', type: 'fill', source: 'ww-gps', paint: {'fill-opacity': 0.3}}, slot(map, 'gps'));
  },
  paint(map, dark) {
    map.setPaintProperty('ww-gps', 'fill-color', ['match', ['get', 'level'], 'high', dark ? '#ff453a' : '#ff3b30', dark ? '#ffd60a' : '#f5b800']);
    map.setPaintProperty('ww-gps', 'fill-outline-color', 'rgba(0,0,0,0)');
  },
  onData(feed, d) { data = unwrap(d.payload); info = d; cells = new Map(data.features.map(f => [f.properties.id, f.properties])); },
  render(map) { map.getSource('ww-gps').setData(data); },
  count: () => 0,
  note: () => data ? data.day.slice(8) + '.' + data.day.slice(5, 7) + '.' : '',
  rows: () => [],
  locate: () => null, ring: () => 0,
  owns: id => String(id).startsWith('gps:'),
  about: () => data ? `Red: more than 10 % of aircraft passing through reported poor navigation accuracy on ${data.day}. Yellow: 2 to 10 %. Worked out by GPSJAM; one map per day, so this is yesterday, not now.` : '',
  detail(id) {
    const c = cells.get(id);
    if (!c) return null;
    const total = c.good + c.bad;
    return `<p class="eyebrow">GPS interference</p><h2>${c.level === 'high' ? 'High' : 'Some'}</h2>
      <p class="where">${c.bad} of ${total} aircraft (${Math.round(c.bad / total * 100)} %) reported poor navigation accuracy here</p>
      <dl><dt>Day</dt><dd>${esc(data.day)}, whole day, UTC</dd>
      <dt>Scale</dt><dd>${c.level === 'high' ? 'red: more than 10 %' : 'yellow: 2 to 10 %'} <span class="soft">(GPSJAM's own bands)</span></dd></dl>
      <a class="link" href="https://gpsjam.org" target="_blank" rel="noopener">Open GPSJAM</a>
      <p class="source">Source: GPSJAM, which counts the accuracy figures aircraft broadcast (data from ADS-B Exchange); fetched ${ago(info.fetched)}. Poor accuracy often means jamming or spoofing but can have other causes, and areas with little air traffic cannot be judged: hexagons with fewer than 5 aircraft are not drawn. GPSJAM states no licence for its data; this is private use with credit.</p>`;
  },
};

// GPS interference in the last hour, worked out by World Watch from live aircraft in 15 regions where jamming is
// often reported (adsb.fi, every 10 minutes). Same rule as GPSJAM: the share of aircraft per hexagon whose broadcast
// position accuracy is poor (NACp below 8). The sampled regions are drawn as faint circles so the gaps are visible.
let live = null, liveInfo = null, liveCells = new Map();
const circle = (lon, lat, km) => { const out = []; for (let b = 0; b <= 360; b += 6) { const r = km / 6371, t = b * Math.PI / 180, la = lat * Math.PI / 180;
  const la2 = Math.asin(Math.sin(la) * Math.cos(r) + Math.cos(la) * Math.sin(r) * Math.cos(t)); const lo2 = lon * Math.PI / 180 + Math.atan2(Math.sin(t) * Math.sin(r) * Math.cos(la), Math.cos(r) - Math.sin(la) * Math.sin(la2));
  out.push([lo2 * 180 / Math.PI, la2 * 180 / Math.PI]); } return out; };
export const gpsLive = {
  id: 'gpslive', title: 'GPS, last hour', color: ['#d70015', '#ff6961'], feeds: {gps_live: 300}, layers: ['ww-gpsl-area', 'ww-gpsl', 'ww-gpsl-line'],
  about: () => 'GPS interference in the last hour, worked out by World Watch from live aircraft in 15 sampled regions (faint circles). Derived, not a measurement of jammers.',
  addTo(map) {
    map.addSource('ww-gpsl', {type: 'geojson', data: {type: 'FeatureCollection', features: []}, maxzoom: 7});
    const first = slot(map, 'gps');
    map.addLayer({id: 'ww-gpsl-area', type: 'line', source: 'ww-gpsl', filter: ['==', ['get', 'kind'], 'region'], paint: {'line-width': 1, 'line-dasharray': [2, 3], 'line-opacity': 0.45}}, first);
    map.addLayer({id: 'ww-gpsl', type: 'fill', source: 'ww-gpsl', filter: ['has', 'level'], paint: {'fill-opacity': 0.45}}, first);
    map.addLayer({id: 'ww-gpsl-line', type: 'line', source: 'ww-gpsl', filter: ['has', 'level'], paint: {'line-width': 1.2}}, first);
  },
  paint(map, dark) {
    const col = ['match', ['get', 'level'], 'high', dark ? '#ff453a' : '#ff3b30', dark ? '#ffd60a' : '#f5b800'];
    map.setPaintProperty('ww-gpsl', 'fill-color', col); map.setPaintProperty('ww-gpsl-line', 'line-color', col);
    map.setPaintProperty('ww-gpsl-area', 'line-color', dark ? '#aeaeb2' : '#636366');
  },
  onData(feed, d) { live = unwrap(d.payload); liveInfo = d; liveCells = new Map((live.features || []).map(f => [f.properties.id, f.properties])); },
  render(map) {
    if (!live) return;
    const regions = Object.entries(live.regions || {}).map(([name, [lat, lon]]) => ({type: 'Feature', geometry: {type: 'LineString', coordinates: circle(lon, lat, 463)}, properties: {kind: 'region', name}}));
    map.getSource('ww-gpsl').setData({type: 'FeatureCollection', features: [...regions, ...(live.features || [])]});
  },
  count: () => live?.features?.length || 0,
  rows: () => [],
  locate: () => null, ring: () => 0,
  owns: id => String(id).startsWith('gpsl:'),
  detail(id) {
    const c = liveCells.get(id);
    if (!c) return null;
    const total = c.good + c.bad;
    return `<p class="eyebrow">GPS interference · last hour · derived</p><h2>${c.level === 'high' ? 'High' : 'Some'}</h2>
      <p class="where">${c.bad} of ${total} aircraft (${Math.round(c.bad / total * 100)} %) broadcast poor position accuracy here in the last hour</p>
      <dl><dt>Rule</dt><dd>NACp below 8 (accuracy worse than 93 m) counts as poor; red above 10 %, yellow 2 to 10 % <span class="soft">(GPSJAM's bands)</span></dd>
      <dt>Updated</dt><dd>${ago(liveInfo.fetched)}</dd></dl>
      <p class="source">Worked out by World Watch from adsb.fi's live aircraft in 15 regions where interference is often reported (the faint circles), sampled every 10 minutes; each aircraft counts once per hexagon per hour. Poor accuracy often means jamming or spoofing but can have other causes; hexagons with fewer than 3 aircraft are not drawn. Outside the circles nothing is measured.</p>`;
  },
};
