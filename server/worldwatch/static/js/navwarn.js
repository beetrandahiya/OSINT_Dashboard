// Navy warnings at sea that report activity: weapons firing, missile and rocket launches and their debris zones,
// military exercises, security threats, GPS interference. Official notices from NGA (US, worldwide series) and
// UKHO (UK). Areas are drawn only where the notice states them (a circle "within n miles of" a point, or an
// "area bound by" listed points); otherwise the points it names are marked.
import {eyeImages, eyeSwap, addEye} from './eyeicons.js';
import {ago, esc, spyPass} from './util.js';

const SRC = 'ww-navwarn';
const KIND = {rocket: ['R', 'Rocket or space debris'], missile: ['M', 'Missile firing'], weapons: ['W', 'Weapons firing or explosives'],
  exercise: ['X', 'Military exercise'], security: ['S', 'Security threat'], gnss: ['G', 'GPS / GNSS interference']};
let warns = [], info = null;

export default {
  id: 'navwarn', title: 'Navy warnings', color: ['#c9a400', '#ffd60a'], feeds: {navwarn: 600},
  layers: ['ww-navwarn-fill', 'ww-navwarn-line', 'ww-navwarn-dot', 'ww-navwarn-label', 'ww-navwarn-eye'],
  about: () => 'Official warnings at sea (NGA, UKHO): firings, launches, exercises, threats.',

  addTo(map) {
    map.addSource(SRC, {type: 'geojson', data: {type: 'FeatureCollection', features: []}});
    map.addLayer({id: 'ww-navwarn-fill', type: 'fill', source: SRC, filter: ['==', ['geometry-type'], 'Polygon'], paint: {'fill-opacity': 0.16}});
    map.addLayer({id: 'ww-navwarn-line', type: 'line', source: SRC, filter: ['==', ['geometry-type'], 'Polygon'], paint: {'line-width': 1.4, 'line-dasharray': [3, 2]}});
    map.addLayer({id: 'ww-navwarn-dot', type: 'circle', source: SRC, filter: ['==', ['get', 'marker'], true], paint: {'circle-radius': 8, 'circle-stroke-width': 1.2}});
    map.addLayer({id: 'ww-navwarn-label', type: 'symbol', source: SRC, filter: ['==', ['get', 'marker'], true],
      layout: {'text-field': ['get', 'k'], 'text-font': ['Noto Sans Bold'], 'text-size': 10, 'text-allow-overlap': true, 'text-ignore-placement': true}});
  },
  paint(map, dark) {
    const c = this.color[+dark];
    map.setPaintProperty('ww-navwarn-fill', 'fill-color', c);
    map.setPaintProperty('ww-navwarn-line', 'line-color', c);
    map.setPaintProperty('ww-navwarn-dot', 'circle-color', c);
    map.setPaintProperty('ww-navwarn-dot', 'circle-stroke-color', dark ? '#1c1c1e' : '#ffffff');
    map.setPaintProperty('ww-navwarn-label', 'text-color', '#1c1c1e');
    if (!map.getLayer('ww-navwarn-eye')) addEye(map, 'ww-navwarn-eye', SRC, ['match', ['get', 'k'], 'R', 'eye-nw_rocket', 'M', 'eye-nw_missile', 'W', 'eye-nw_weapons',
      'X', 'eye-nw_exercise', 'S', 'eye-nw_security', 'G', 'eye-nw_gnss', 'eye-nw_weapons'], 0.55, {filter: ['==', ['get', 'marker'], true]});
    eyeImages(map, dark); eyeSwap(map, ['ww-navwarn-eye'], ['ww-navwarn-dot', 'ww-navwarn-label']);
  },
  onData(feed, d) { warns = d.payload.warnings || []; info = d; },
  render(map) {
    const feats = [];
    for (const w of warns) {
      const props = {id: w.id, k: KIND[w.kind]?.[0] || '?'};
      for (const g of w.geoms) {
        if (g.type === 'Polygon') feats.push({type: 'Feature', geometry: g, properties: props});
        else for (const c of g.coordinates) feats.push({type: 'Feature', geometry: {type: 'Point', coordinates: c}, properties: {...props, marker: true}});
      }
      if (w.lon != null && w.geoms.some(g => g.type === 'Polygon')) feats.push({type: 'Feature', geometry: {type: 'Point', coordinates: [w.lon, w.lat]}, properties: {...props, marker: true}});
    }
    map.getSource(SRC).setData({type: 'FeatureCollection', features: feats});
  },
  count: () => warns.filter(w => w.lon != null).length,
  owns: id => warns.some(w => w.id === id),
  rows() {
    return warns.filter(w => w.lon != null && ['rocket', 'missile', 'weapons', 'security'].includes(w.kind)).map(w => ({
      id: w.id, time: w.issued_t || info?.fetched || 0, badge: KIND[w.kind]?.[0] || '?',
      title: `${KIND[w.kind]?.[1]}: ${w.text.replace(/\s+/g, ' ').slice(0, 90)}`, meta: `${w.ref} · ${w.source} · in force`}));
  },
  locate(id) { const w = warns.find(x => x.id === id); return w && w.lon != null ? [w.lon, w.lat] : null; },
  ring: () => 14,
  detail(id) {
    const w = warns.find(x => x.id === id);
    if (!w) return null;
    const how = {circles: 'the circle the notice states', areas: 'the area the notice bounds', points: 'the points the notice names'};
    return `<p class="eyebrow">Navy warning · ${esc(w.source)}</p>
      <h2>${esc(KIND[w.kind]?.[1] || w.kind)}</h2>
      <p class="where">${esc(w.ref)}${w.area ? ' · ' + esc(w.area) : ''}${w.issued ? ' · issued ' + esc(w.issued) : ''}</p>
      <pre class="notice">${esc(w.text)}</pre>
      <dl>
        <dt>On the map</dt><dd>${w.how ? w.how.split('+').map(h => how[h]).join(' and ') : 'no position could be read'}</dd>
        ${w.authority ? `<dt>Issued by</dt><dd>${esc(w.authority)}</dd>` : ''}
      </dl>
      ${w.lat != null ? spyPass(w.lat, w.lon) : ''}
      <a class="link" href="${esc(w.link)}" target="_blank" rel="noopener">Open the official list</a>
      <p class="source">Source: ${w.source === 'NGA' ? 'US National Geospatial-Intelligence Agency, Maritime Safety Information' : 'UK Hydrographic Office, NAVAREA I'}; list fetched ${ago(info?.fetched)}. The kind is chosen from words in the notice (for example FIRING, MISSILE, ROCKET). Times inside the notice are in its own format, usually UTC. Read the notice itself before relying on the shape.</p>`;
  },
};
