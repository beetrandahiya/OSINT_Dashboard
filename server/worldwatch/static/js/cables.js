// Undersea internet cables, from TeleGeography's Submarine Cable Map (CC BY-NC-SA: private, non-commercial use).
// Routes on that map are drawn schematically by TeleGeography; they are not surveyed positions.
import {ago, esc} from './util.js';

let data = null, info = null, names = new Map();
export default {
  id: 'cables', title: 'Cables', color: ['#8e8e93', '#98989d'], feeds: {cables: 3600}, layers: ['ww-cables', 'ww-cables-hit'],
  addTo(map) {
    map.addSource('ww-cables', {type: 'geojson', data: {type: 'FeatureCollection', features: []}});
    const first = map.getStyle().layers.find(l => l.id.startsWith('ww-') && !['ww-night', 'ww-rain', 'ww-aurora'].includes(l.id))?.id;
    map.addLayer({id: 'ww-cables', type: 'line', source: 'ww-cables', paint: {'line-width': ['interpolate', ['linear'], ['zoom'], 1, 0.6, 6, 1.6], 'line-opacity': ['interpolate', ['linear'], ['zoom'], 1, 0.4, 5, 0.75]}}, first);
    map.addLayer({id: 'ww-cables-hit', type: 'line', source: 'ww-cables', paint: {'line-width': 10, 'line-opacity': 0}}, first);   // a wider invisible line, easier to click
  },
  paint(map, dark) { map.setPaintProperty('ww-cables', 'line-color', dark ? '#7d8a99' : '#6b7a8c'); },
  onData(feed, d) { data = d.payload; info = d; names = new Map(data.features.map(f => [f.properties.id, f.properties.name])); },
  render(map) { map.getSource('ww-cables').setData(data); },
  count: () => names.size,
  rows: () => [],
  locate: () => null, ring: () => 0,
  owns: id => String(id).startsWith('cable:'),
  detail(id) {
    if (!names.has(id)) return null;
    return `<p class="eyebrow">Undersea cable</p><h2>${esc(names.get(id))}</h2><p class="where">Submarine internet cable</p>
      <a class="link" href="https://www.submarinecablemap.com/submarine-cable/${esc(id.slice(6))}" target="_blank" rel="noopener">Owners, length and landing points on the Submarine Cable Map</a>
      <p class="source">Source: TeleGeography's Submarine Cable Map (licence CC BY-NC-SA), fetched ${ago(info.fetched)}; we refresh it once a week. The routes are drawn schematically by TeleGeography and are not exact positions. The map does not show whether a cable is working.</p>`;
  },
};
