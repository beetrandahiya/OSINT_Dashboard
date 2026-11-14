// GPS interference, as worked out by GPSJAM (gpsjam.org) from the navigation accuracy that aircraft report.
// This is the one layer that is somebody else's analysis rather than raw readings; it shows a whole past day.
import {ago, esc} from './util.js';

let data = null, info = null, cells = new Map();
export default {
  id: 'gps', title: 'GPS', color: ['#d49a00', '#ffd60a'], feeds: {gps: 1800}, layers: ['ww-gps'],
  addTo(map) {
    map.addSource('ww-gps', {type: 'geojson', data: {type: 'FeatureCollection', features: []}});
    const first = map.getStyle().layers.find(l => l.id.startsWith('ww-') && !['ww-night', 'ww-rain', 'ww-aurora'].includes(l.id))?.id;
    map.addLayer({id: 'ww-gps', type: 'fill', source: 'ww-gps', paint: {'fill-opacity': 0.3}}, first);
  },
  paint(map, dark) {
    map.setPaintProperty('ww-gps', 'fill-color', ['match', ['get', 'level'], 'high', dark ? '#ff453a' : '#ff3b30', dark ? '#ffd60a' : '#f5b800']);
    map.setPaintProperty('ww-gps', 'fill-outline-color', 'rgba(0,0,0,0)');
  },
  onData(feed, d) { data = d.payload; info = d; cells = new Map(data.features.map(f => [f.properties.id, f.properties])); },
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
