// Earthquakes, exactly as the USGS feed lists them. Circle size follows magnitude; nothing else is implied.
import {ago, esc, local, utc} from './util.js';
import {nearTestSite} from './sites.js';
import {eyeOn, eyeImages, eyeSwap} from './eyeicons.js';
// God's eye: three sizes, a quake within 50 km of a nuclear test site, and USGS's own explosion types
const quakeEye = q => 'eye-' + (/explosion/.test(q.type || '') ? 'explosion' : nearTestSite(q.lon, q.lat) ? 'quake_test' : (q.mag ?? 0) >= 6 ? 'quake_l' : (q.mag ?? 0) >= 4.5 ? 'quake_m' : 'quake_s');

const SRC = 'ww-quakes', LIST_MIN_MAG = 4;   // the list shows these; the map shows every quake in the feed
let quakes = [], info = null;
const mag = q => q.mag == null ? '?' : q.mag.toFixed(1);

export default {
  id: 'quakes', title: 'Earthquakes', color: ['#ff9500', '#ff9f0a'], feeds: {quakes: 30}, layers: ['ww-quakes', 'ww-quakes-eye', 'ww-quakes-label'],

  addTo(map) {
    map.addSource(SRC, {type: 'geojson', data: {type: 'FeatureCollection', features: []}});
    const size = ['interpolate', ['linear'], ['coalesce', ['get', 'mag'], 0], 0, 2.5, 3, 4, 4.5, 9, 6, 13, 7, 18, 8, 25];
    map.addLayer({id: 'ww-quakes', type: 'circle', source: SRC, paint: {'circle-radius': size, 'circle-opacity': 0.9, 'circle-stroke-width': 1.2}});
    map.addLayer({id: 'ww-quakes-eye', type: 'symbol', source: SRC, layout: {'icon-image': ['get', 'eye'],
      'icon-size': ['interpolate', ['linear'], ['coalesce', ['get', 'mag'], 0], 0, 0.22, 3, 0.3, 4.5, 0.48, 6, 0.66, 7, 0.82, 8, 1], 'icon-allow-overlap': true, 'icon-ignore-placement': true}});
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
    eyeImages(map, dark);
    const eye = eyeOn();     // God's eye: the symbol instead of the circle; the magnitude moves below it
    eyeSwap(map, ['ww-quakes-eye'], ['ww-quakes']);
    map.setLayoutProperty('ww-quakes-label', 'text-offset', eye ? [0, 1.5] : [0, 0]);
    map.setPaintProperty('ww-quakes-label', 'text-color', eye ? (dark ? '#e8f1f6' : '#0b141b') : '#ffffff');
    map.setPaintProperty('ww-quakes-label', 'text-halo-color', eye ? (dark ? '#05080c' : '#ffffff') : 'rgba(0,0,0,0)'); map.setPaintProperty('ww-quakes-label', 'text-halo-width', eye ? 1.2 : 0);
    if (map.getSource(SRC)) this.render(map);
  },
  onData(feed, d) { quakes = d.payload.quakes; info = d; },
  render(map) {
    // smallest first, so the strong ones are drawn on top. (A sort key did the same but cost one draw call per distinct
    // magnitude, ~250 a frame for this layer alone.)
    map.getSource(SRC).setData({type: 'FeatureCollection', features: [...quakes].sort((a, b) => (a.mag ?? 0) - (b.mag ?? 0)).map(q => (
      {type: 'Feature', geometry: {type: 'Point', coordinates: [q.lon, q.lat]}, properties: {id: q.id, mag: q.mag, eye: quakeEye(q)}}))});
  },
  count: () => quakes.length,
  rows() {
    // a quake near a nuclear test site is listed whatever its size, with the site named
    return quakes.filter(q => (q.mag ?? 0) >= LIST_MIN_MAG || nearTestSite(q.lon, q.lat)).map(q => ({
      id: q.id, time: q.time, badge: mag(q), strong: (q.mag ?? 0) >= 5.5,
      title: q.place || 'Unnamed location',
      // plain text: the list escapes it (escaping here too showed &amp; for a type with an ampersand)
      meta: (t => t ? `☢ ${t.km} km from ${t.name} nuclear test site · ` : '')(nearTestSite(q.lon, q.lat)) + `${q.type && q.type !== 'earthquake' ? q.type[0].toUpperCase() + q.type.slice(1) : 'Earthquake'} · ${local(q.time)} · ${ago(q.time)}`}));
  },
  owns: id => quakes.some(q => q.id === id),   // lets links from other cards (hotspots) open a quake's card
  locate(id) { const q = quakes.find(x => x.id === id); return q && [q.lon, q.lat]; },
  ring(id) { const q = quakes.find(x => x.id === id); return q ? 8 + Math.max(0, (q.mag ?? 0) - 2) * 3 : 12; },
  detail(id) {
    const q = quakes.find(x => x.id === id);
    if (!q) return null;
    const kind = q.type && q.type !== 'earthquake' ? q.type[0].toUpperCase() + q.type.slice(1) : 'Earthquake';
    return `<p class="eyebrow">${esc(kind)}${q.type && q.type !== 'earthquake' ? ' <span class="soft">(as USGS classifies it)</span>' : ''}</p>
      <h2>Magnitude ${mag(q)}</h2>
      <p class="where">${esc(q.place || 'Unnamed location')}</p>
      <dl>
        <dt>Time</dt><dd>${local(q.time)} <span class="soft">(${utc(q.time)}, ${ago(q.time)})</span></dd>
        <dt>Depth</dt><dd>${q.depth_km.toFixed(1)} km</dd>
        <dt>Position</dt><dd>${Math.abs(q.lat).toFixed(3)}° ${q.lat >= 0 ? 'N' : 'S'}, ${Math.abs(q.lon).toFixed(3)}° ${q.lon >= 0 ? 'E' : 'W'}</dd>
        <dt>Last revised</dt><dd>${local(q.updated)} <span class="soft">(${ago(q.updated)})</span></dd>
      </dl>
      ${(t => t ? `<section class="pz"><h3>☢ Near a nuclear test site</h3><p>${t.km} km from <b>${esc(t.name)}</b> (tested there: ${esc(t.by)}).</p>
        <p class="soft">This says only where it is. An earthquake near a test site is usually an earthquake; an explosion is told apart by seismologists from its shallow depth (often listed as 0 km) and the shape of its waves, and announced by the USGS, the CTBTO or the country. USGS lists this one as: <b>${esc(q.type || 'not stated')}</b>.</p></section>` : '')(nearTestSite(q.lon, q.lat))}
      <a class="link" href="${esc(q.url)}" target="_blank" rel="noopener">Open the USGS event page</a>
      <p class="source">Source: USGS. Their feed was generated at ${utc(info.data_time)}; we fetched it ${ago(info.fetched)}. The list shows magnitude ${LIST_MIN_MAG} and above; the map shows all ${quakes.length}.</p>`;
  },
};
