// Undersea internet cables with a reported problem: only cables named in fault or repair news are drawn
// (SubTel Forum's fault category and our news window, matched to TeleGeography's cable names; see cablefaults.py).
// Routes from TeleGeography's Submarine Cable Map (CC BY-NC-SA: private, non-commercial use), drawn schematically.
import {ago, esc} from './util.js';

let data = null, info = null, faults = {}, faultInfo = null, names = new Map(), theMap = null;
const day = t => new Date(t * 1000).toLocaleDateString('en-GB', {day: 'numeric', month: 'short'});

export default {
  id: 'cables', title: 'Cable problems', color: ['#c93400', '#ff9f0a'], feeds: {cables: 21600, cable_faults: 1800}, layers: ['ww-cables', 'ww-cables-hit'],
  about: () => 'Undersea cables named in fault or repair news in the last 60 days.',
  addTo(map) {
    theMap = map;
    map.addSource('ww-cables', {type: 'geojson', data: {type: 'FeatureCollection', features: []}});
    const first = map.getStyle().layers.find(l => l.id.startsWith('ww-') && !['ww-night', 'ww-rain', 'ww-aurora'].includes(l.id))?.id;
    map.addLayer({id: 'ww-cables', type: 'line', source: 'ww-cables',
      paint: {'line-width': ['interpolate', ['linear'], ['zoom'], 1, 1.6, 6, 3], 'line-opacity': ['match', ['get', 'state'], 'restored', 0.45, 0.95],
        'line-dasharray': ['match', ['get', 'state'], 'restored', ['literal', [2, 2]], ['literal', [1, 0]]]}}, first);
    map.addLayer({id: 'ww-cables-hit', type: 'line', source: 'ww-cables', paint: {'line-width': 12, 'line-opacity': 0}}, first);   // a wider invisible line, easier to click
  },
  paint(map, dark) { map.setPaintProperty('ww-cables', 'line-color', ['match', ['get', 'state'], 'restored', dark ? '#30d158' : '#248a3d', this.color[+dark]]); },
  onData(feed, d) {
    if (feed === 'cable_faults') { faults = d.payload.cables || {}; faultInfo = d; }
    else { data = d.payload; info = d; names = new Map(data.features.map(f => [f.properties.id, f.properties.name])); }
  },
  render(map) {
    if (!data) return;
    const feats = data.features.filter(f => faults[f.properties.id.slice(6)]).map(f => ({...f, properties: {...f.properties, state: faults[f.properties.id.slice(6)].state}}));
    map.getSource('ww-cables').setData({type: 'FeatureCollection', features: feats});
  },
  count: () => Object.values(faults).filter(c => c.state === 'problem').length,
  rows: () => Object.entries(faults).map(([id, c]) => ({id: 'cable:' + id, time: c.items[0].time, badge: c.state === 'restored' ? '✓' : '⚡',
    title: `${c.name}: ${c.items[0].title}`, meta: `${c.state === 'restored' ? 'Restored' : 'Fault or repair'} · ${esc(c.items[0].source)}, ${day(c.items[0].time)}`})),
  locate(id) {
    const f = data?.features.find(x => x.properties.id === id); if (!f) return null;
    const g = f.geometry, line = g.type === 'MultiLineString' ? g.coordinates[0] : g.coordinates;
    return line[Math.floor(line.length / 2)];
  },
  ring: () => 0,
  owns: id => String(id).startsWith('cable:'),
  detail(id) {
    if (!names.has(id)) return null;
    const c = faults[id.slice(6)];
    return `<p class="eyebrow">Undersea cable${c ? ' · ' + (c.state === 'restored' ? 'reported restored' : 'fault or repair reported') : ''}</p><h2>${esc(names.get(id))}</h2>
      ${c ? `<ol class="stories">${c.items.map(i => `<li><span class="st"><a href="${esc(i.url)}" target="_blank" rel="noopener">${esc(i.title)}</a><span class="by">${esc(i.source)} · ${day(i.time)}</span></span></li>`).join('')}</ol>` : ''}
      <a class="link" href="https://www.submarinecablemap.com/submarine-cable/${esc(id.slice(6))}" target="_blank" rel="noopener">Owners, length and landing points on the Submarine Cable Map</a>
      <p class="source">Marked because a headline names this cable together with a word like fault, cut, damage, repair or outage (SubTel Forum's fault and maintenance news, last 60 days, and our 6-hour news window), matched by name or acronym; read ${ago(faultInfo?.fetched)}. "Restored" when the newest headline says so. No free source states where along a cable the fault is, so the whole route is drawn; TeleGeography draws routes schematically. Cables nobody reported on are not shown.</p>`;
  },
};
