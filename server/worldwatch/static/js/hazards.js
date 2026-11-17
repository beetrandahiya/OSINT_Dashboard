// Disasters: alerts from GDACS (the UN and EU alert system) and open events from NASA's EONET.
// Each marker carries a two-letter code for the kind of event; the alert level is GDACS's own.
import {ago, esc, local, skyShot, utc, spyPass} from './util.js';

const SRC = 'ww-hazards';
let sets = {}, info = {}, events = [];
const LETTER = {TC: 'C', FL: 'F', VO: 'V', DR: 'D', WF: 'W', IC: 'I', LS: 'L', DH: 'H'};
const when = e => e.modified;

export default {
  id: 'hazards', title: 'Disasters', color: ['#ff2d55', '#ff375f'], feeds: {gdacs: 300, eonet: 600}, layers: ['ww-hazards-track', 'ww-hazards', 'ww-hazards-label'],

  addTo(map) {
    map.addSource(SRC, {type: 'geojson', data: {type: 'FeatureCollection', features: []}});
    map.addLayer({id: 'ww-hazards-track', type: 'line', source: SRC, filter: ['==', ['geometry-type'], 'LineString'], paint: {'line-width': 1.5, 'line-opacity': 0.6}});
    map.addLayer({id: 'ww-hazards', type: 'circle', source: SRC, filter: ['==', ['geometry-type'], 'Point'],
      paint: {'circle-radius': ['match', ['get', 'level'], 'Red', 12, 'Orange', 10, 8], 'circle-opacity': 0.95, 'circle-stroke-width': 1.2}});
    map.addLayer({id: 'ww-hazards-label', type: 'symbol', source: SRC, filter: ['==', ['geometry-type'], 'Point'],
      layout: {'text-field': ['get', 'letter'], 'text-font': ['Noto Sans Bold'], 'text-size': 10, 'text-allow-overlap': true, 'text-ignore-placement': true}, paint: {'text-color': '#ffffff'}});
  },
  paint(map, dark) {
    const c = this.color[+dark];
    map.setPaintProperty('ww-hazards', 'circle-color', c); map.setPaintProperty('ww-hazards', 'circle-stroke-color', dark ? '#1c1c1e' : '#ffffff');
    map.setPaintProperty('ww-hazards-track', 'line-color', c);
  },
  onData(feed, d) { sets[feed] = d.payload.events; info[feed] = d; events = [...(sets.gdacs || []), ...(sets.eonet || [])]; },
  render(map) {
    const feats = [];
    for (const e of events) {
      if (e.track) feats.push({type: 'Feature', geometry: {type: 'LineString', coordinates: e.track}, properties: {}});   // where a storm has been, as reported
      feats.push({type: 'Feature', geometry: {type: 'Point', coordinates: [e.lon, e.lat]}, properties: {id: e.id, level: e.level || '', letter: LETTER[e.code] || '?'}});
    }
    map.getSource(SRC).setData({type: 'FeatureCollection', features: feats});
  },
  count: () => events.length,
  owns: id => events.some(e => e.id === id),
  rows() {
    return events.map(e => ({id: e.id, time: when(e), badge: LETTER[e.code] || '?', strong: e.level === 'Red' || e.level === 'Orange',
      title: e.name, meta: `${e.kind}${e.level ? ' · ' + e.level.toLowerCase() + ' alert' : ''} · updated ${ago(when(e))}`}));
  },
  locate(id) { const e = events.find(x => x.id === id); return e && [e.lon, e.lat]; },
  ring: () => 16,
  detail(id) {
    const e = events.find(x => x.id === id);
    if (!e) return null;
    const f = info[e.source === 'GDACS' ? 'gdacs' : 'eonet'];
    return `<p class="eyebrow">${esc(e.kind)}</p>
      <h2>${esc(e.name)}</h2>
      <p class="where">${esc(e.countries || (e.title !== e.name ? e.title : '') || '')}</p>
      <dl>
        ${e.level ? `<dt>GDACS alert level</dt><dd>${esc(e.level)} <span class="soft">(green, orange or red by expected humanitarian impact)</span></dd>` : ''}
        ${e.severity ? `<dt>${e.source === 'GDACS' ? 'Severity, as GDACS puts it' : 'Latest strength'}</dt><dd>${esc(e.severity)}</dd>` : ''}
        <dt>Began</dt><dd>${local(e.from)} <span class="soft">(${ago(e.from)})</span></dd>
        ${e.to ? `<dt>Alert runs to</dt><dd>${local(e.to)} <span class="soft">(${ago(e.to)})</span></dd>` : ''}
        <dt>Last update</dt><dd>${local(e.modified)} <span class="soft">(${utc(e.modified)}, ${ago(e.modified)})</span></dd>
      </dl>
      ${skyShot(e.lat, e.lon)}
      ${spyPass(e.lat, e.lon)}
      ${e.url ? `<a class="link" href="${esc(e.url)}" target="_blank" rel="noopener">Open the ${e.source === 'GDACS' ? 'GDACS report' : 'source report'}</a>` : ''}
      <p class="source">Source: ${esc(e.source)}, fetched ${ago(f.fetched)}. ${e.source === 'GDACS' ? 'The marker is the centre point GDACS gives for the event; large events such as droughts cover far more than a point. Orange and red alerts stay listed for a week after their end date, green ones for three days.' : 'The marker is the latest position NASA lists' + (e.track ? '; the line joins the earlier reported positions.' : '.')}</p>`;
  },
};
