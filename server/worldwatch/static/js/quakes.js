// Earthquakes, exactly as the USGS feed lists them. Circle size follows magnitude; nothing else is implied.
import {ago, esc, local, utc} from './util.js';

const SRC = 'ww-quakes', LIST_MIN_MAG = 4;   // the list shows these; the map shows every quake in the feed
let quakes = [], info = null;
const mag = q => q.mag == null ? '?' : q.mag.toFixed(1);

export default {
  id: 'quakes', title: 'Earthquakes', color: ['#ff9500', '#ff9f0a'], feeds: {quakes: 30}, layers: ['ww-quakes', 'ww-quakes-label'],

  addTo(map) {
    map.addSource(SRC, {type: 'geojson', data: {type: 'FeatureCollection', features: []}});
    const size = ['interpolate', ['linear'], ['coalesce', ['get', 'mag'], 0], 0, 2.5, 3, 4, 4.5, 9, 6, 13, 7, 18, 8, 25];
    map.addLayer({id: 'ww-quakes', type: 'circle', source: SRC, paint: {'circle-radius': size, 'circle-opacity': 0.9, 'circle-stroke-width': 1.2}});
    // Apple's map guidance allows a short label inside a marker; the stronger quakes carry their magnitude.
    map.addLayer({id: 'ww-quakes-label', type: 'symbol', source: SRC, filter: ['>=', ['coalesce', ['get', 'mag'], 0], 4.5],
      layout: {'text-field': ['number-format', ['get', 'mag'], {'min-fraction-digits': 1, 'max-fraction-digits': 1}],
               'text-font': ['Noto Sans Bold'], 'text-size': ['interpolate', ['linear'], ['get', 'mag'], 4.5, 9, 7, 12],
               'text-allow-overlap': true, 'text-ignore-placement': true},
      paint: {'text-color': '#ffffff'}});
  },
  paint(map, dark) {
    map.setPaintProperty('ww-quakes', 'circle-color', this.color[+dark]);
    map.setPaintProperty('ww-quakes', 'circle-stroke-color', dark ? '#1c1c1e' : '#ffffff');
  },
  onData(feed, d) { quakes = d.payload.quakes; info = d; },
  render(map) {
    map.getSource(SRC).setData({type: 'FeatureCollection', features: quakes.map(q => (
      {type: 'Feature', geometry: {type: 'Point', coordinates: [q.lon, q.lat]}, properties: {id: q.id, mag: q.mag}}))});
  },
  count: () => quakes.length,
  rows() {
    return quakes.filter(q => (q.mag ?? 0) >= LIST_MIN_MAG).map(q => ({
      id: q.id, time: q.time, badge: mag(q), strong: (q.mag ?? 0) >= 5.5,
      title: q.place || 'Unnamed location',
      meta: `Earthquake · ${local(q.time)} · ${ago(q.time)}`}));
  },
  locate(id) { const q = quakes.find(x => x.id === id); return q && [q.lon, q.lat]; },
  ring(id) { const q = quakes.find(x => x.id === id); return q ? 8 + Math.max(0, (q.mag ?? 0) - 2) * 3 : 12; },
  detail(id) {
    const q = quakes.find(x => x.id === id);
    if (!q) return null;
    return `<p class="eyebrow">Earthquake</p>
      <h2>Magnitude ${mag(q)}</h2>
      <p class="where">${esc(q.place || 'Unnamed location')}</p>
      <dl>
        <dt>Time</dt><dd>${local(q.time)} <span class="soft">(${utc(q.time)}, ${ago(q.time)})</span></dd>
        <dt>Depth</dt><dd>${q.depth_km.toFixed(1)} km</dd>
        <dt>Position</dt><dd>${Math.abs(q.lat).toFixed(3)}° ${q.lat >= 0 ? 'N' : 'S'}, ${Math.abs(q.lon).toFixed(3)}° ${q.lon >= 0 ? 'E' : 'W'}</dd>
        <dt>Last revised</dt><dd>${local(q.updated)} <span class="soft">(${ago(q.updated)})</span></dd>
      </dl>
      <a class="link" href="${esc(q.url)}" target="_blank" rel="noopener">Open the USGS event page</a>
      <p class="source">Source: USGS. Their feed was generated at ${utc(info.data_time)}; we fetched it ${ago(info.fetched)}. The list shows magnitude ${LIST_MIN_MAG} and above; the map shows all ${quakes.length}.</p>`;
  },
};
