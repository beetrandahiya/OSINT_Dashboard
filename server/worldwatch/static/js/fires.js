// Fire detections from NASA FIRMS: every hot spot the MODIS satellite instruments saw in the last 24 hours.
// A detection is a 1 km pixel that looked hot. It can be a wildfire, a farm burn, a gas flare or a volcano.
import {ago, esc, local, utc} from './util.js';
import {slot} from './map.js';

let pts = [], info = null;
export default {
  id: 'fires', title: 'Fires', color: ['#ff5e3a', '#ff6a4d'], feeds: {fires: 900}, layers: ['ww-fires'],
  addTo(map) {
    map.addSource('ww-fires', {type: 'geojson', data: {type: 'FeatureCollection', features: []}});
    const first = slot(map, 'area');   // over the photos, sky pictures and GPS hexagons, under the place names
    map.addLayer({id: 'ww-fires', type: 'circle', source: 'ww-fires',
      paint: {'circle-radius': ['interpolate', ['linear'], ['zoom'], 1, 1.3, 5, 2.6, 9, 5], 'circle-opacity': ['interpolate', ['linear'], ['zoom'], 1, 0.55, 6, 0.85]}}, first);
  },
  paint(map, dark) { map.setPaintProperty('ww-fires', 'circle-color', this.color[+dark]); },
  onData(feed, d) { pts = d.payload.points; info = d; },
  render(map) {
    map.getSource('ww-fires').setData({type: 'FeatureCollection', features: pts.map((p, i) => ({type: 'Feature', geometry: {type: 'Point', coordinates: [p[0], p[1]]}, properties: {id: 'fire:' + i}}))});
  },
  count: () => pts.length,
  rows: () => [],
  locate(id) { const p = pts[+String(id).slice(5)]; return p && [p[0], p[1]]; },
  ring: () => 10,
  owns: id => String(id).startsWith('fire:'),
  about: () => 'Each dot is a hot spot a NASA satellite saw in the last 24 hours. Not every dot is a wildfire: farm burns, gas flares and volcanoes show up too.',
  detail(id) {
    const p = pts[+String(id).slice(5)];
    if (!p) return null;
    return `<p class="eyebrow">Fire detection</p><h2>Hot spot</h2>
      <p class="where">${Math.abs(p[1]).toFixed(3)}° ${p[1] >= 0 ? 'N' : 'S'}, ${Math.abs(p[0]).toFixed(3)}° ${p[0] >= 0 ? 'E' : 'W'}</p>
      <dl><dt>Seen by satellite</dt><dd>${local(p[4])} <span class="soft">(${utc(p[4])}, ${ago(p[4])})</span></dd>
      <dt>Radiated power</dt><dd>${p[2]} MW</dd>
      <dt>Detection confidence</dt><dd>${p[3]} % <span class="soft">(NASA's own figure)</span></dd>
      <dt>Satellite</dt><dd>${p[5] === 'T' ? 'Terra' : p[5] === 'A' ? 'Aqua' : esc(p[5])}, ${p[6] === 'D' ? 'daytime' : 'night-time'} pass</dd></dl>
      <a class="link" href="https://firms.modaps.eosdis.nasa.gov/map/#d:24hrs;@${p[0]},${p[1]},10z" target="_blank" rel="noopener">Open NASA's fire map here</a>
      <p class="source">Source: NASA FIRMS, MODIS instrument, file rebuilt ${ago(info.payload.published)}; fetched ${ago(info.fetched)}. One dot is one 1 km pixel that looked hot when a satellite passed, a few times a day. It can be a wildfire, a farm burn, a gas flare or a volcano, and fires under cloud are missed.</p>`;
  },
};
