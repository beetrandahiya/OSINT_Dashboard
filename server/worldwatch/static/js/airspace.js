// Airspace warnings and closures. Conflict-zone bulletins (EASA) and FAA prohibitions and notices are drawn on the
// flight regions they name (outlines from VATSpy, community-drawn, approximate); a region covered by several warnings
// is drawn once, in its strongest level, and its card lists them all. US temporary flight restrictions have exact shapes.
import {ago, esc, local, countryBtn} from './util.js';

const SRC = 'ww-airspace';
let zones = [], tfrs = [], firs = new Map(), info = null;
const STRONG = new Set(['avoid', 'prohibited']);
const dmy = s => { if (!s) return null; const [d, m, y] = s.split('/'); return Date.UTC(+y, m - 1, +d) / 1000; };

function index() {
  firs = new Map();
  for (const z of zones) for (const [code, rings] of Object.entries(z.shapes || {})) {
    const f = firs.get(code) || {code, rings, zones: [], strong: false};
    f.zones.push(z); f.strong ||= STRONG.has(z.level);
    firs.set(code, f);
  }
}
const centre = rings => { let x = 0, y = 0, n = 0; for (const r of rings) for (const p of r) { x += p[0]; y += p[1]; n++; } return n ? [x / n, y / n] : null; };

export default {
  id: 'airspace', title: 'Airspace', color: ['#d70015', '#ff6961'], feeds: {airspace: 900},
  layers: ['ww-airspace-fill', 'ww-airspace-line'],
  about: () => 'Conflict-zone warnings (EASA, FAA) on flight regions, and US temporary flight restrictions.',

  addTo(map) {
    map.addSource(SRC, {type: 'geojson', data: {type: 'FeatureCollection', features: []}});
    map.addLayer({id: 'ww-airspace-fill', type: 'fill', source: SRC, paint: {'fill-opacity': ['case', ['==', ['get', 'strong'], true], 0.07, 0.03]}});
    map.addLayer({id: 'ww-airspace-line', type: 'line', source: SRC, paint: {'line-width': 1.2, 'line-opacity': 0.7}});
  },
  paint(map, dark) {
    const c = this.color[+dark];
    map.setPaintProperty('ww-airspace-fill', 'fill-color', c);
    map.setPaintProperty('ww-airspace-line', 'line-color', c);
  },
  onData(feed, d) { zones = d.payload.zones || []; tfrs = d.payload.tfrs || []; info = d; index(); },
  render(map) {
    const feats = [];
    for (const f of firs.values()) for (const r of f.rings) feats.push({type: 'Feature', geometry: {type: 'Polygon', coordinates: [r]}, properties: {id: 'FIR:' + f.code, strong: f.strong}});
    for (const t of tfrs) for (const p of t.polys) feats.push({type: 'Feature', geometry: {type: 'Polygon', coordinates: [p]}, properties: {id: t.id, strong: true, tfr: true}});
    map.getSource(SRC).setData({type: 'FeatureCollection', features: feats});
  },
  count: () => firs.size + tfrs.length,
  owns: id => /^(FIR|TFR):/.test(String(id)),
  rows() {   // only bulletins revised in the last week; standing warnings would crowd the list for months
    const week = Date.now() / 1000 - 7 * 86400;
    return zones.filter(z => z.source === 'EASA' && dmy(z.revised || z.issued) > week && Object.keys(z.shapes).length).map(z => ({
      id: 'FIR:' + Object.keys(z.shapes)[0], time: dmy(z.revised || z.issued), badge: '✈︎', title: `${z.title}: ${z.level === 'avoid' ? 'do not operate (in part or all)' : 'caution'}`,
      meta: `EASA ${z.number} · revised ${z.revised || z.issued}`}));
  },
  locate(id) {
    if (id.startsWith('FIR:')) return centre(firs.get(id.slice(4))?.rings || []);
    const t = tfrs.find(x => x.id === id); return t && centre(t.polys);
  },
  ring: () => 16,
  detail(id) {
    if (id.startsWith('TFR:')) {
      const t = tfrs.find(x => x.id === id);
      if (!t) return null;
      return `<p class="eyebrow">US temporary flight restriction</p><h2>${esc(t.type || 'Restriction')}</h2>
        <p class="where">${esc(t.where || '')} · NOTAM ${esc(t.notam)}</p>
        ${t.text ? `<pre class="notice">${esc(t.text)}</pre>` : ''}
        <a class="link" href="https://tfr.faa.gov/tfr3/?page=detail_${esc(t.notam.replace('/', '_'))}" target="_blank" rel="noopener">Open at the FAA</a>
        <p class="source">Source: FAA TFR list, fetched ${ago(info?.fetched)}. The shape is the FAA's own.</p>`;
    }
    const f = firs.get(id.slice(4));
    if (!f) return null;
    return `<p class="eyebrow">Airspace warning · flight region ${esc(f.code)}</p>
      <h2>${esc(f.zones.find(z => z.source === 'EASA')?.title || f.zones[0].title)}</h2>
      <p class="where">${f.strong ? 'Airlines told not to fly here, in part or all' : 'Airlines told to take care'}</p>
      ${countryBtn({icao: f.code})}
      ${f.zones.map(z => z.source === 'EASA' ? `<section class="pz"><h3>EASA ${esc(z.number)} · ${z.level === 'avoid' ? 'do not operate (in part or all)' : 'caution'}</h3>
          <p class="soft">Issued ${esc(z.issued)}${z.revised ? ', revised ' + esc(z.revised) : ''}${z.valid_until ? ', valid until ' + esc(z.valid_until) : ''}</p>
          ${z.affected ? `<p><b>Affected airspace:</b> ${esc(z.affected)}</p>` : ''}
          ${z.advice ? `<pre class="notice">${esc(z.advice)}</pre>` : ''}
          <a class="link" href="${esc(z.link)}" target="_blank" rel="noopener">Read the bulletin</a></section>`
        : `<section class="pz"><h3>FAA · ${z.level === 'prohibited' ? 'US flights prohibited (SFAR) or restricted' : 'security notice'}</h3>
          <ul class="pz-list">${z.docs.map(d => `<li><a class="link" href="${esc(d.url)}" target="_blank" rel="noopener">${esc(d.title)}</a></li>`).join('')}</ul></section>`).join('')}
      <p class="source">Sources: EASA Conflict Zone Information Bulletins and the FAA's Prohibitions, Restrictions and Notices page; fetched ${ago(info?.fetched)}. The outline is the whole flight region ${esc(f.code)} from VATSpy (VATSIM community data, CC BY-SA 4.0), close to the official one but drawn by volunteers. A warning often covers only part of a region (below a flight level, or west of a longitude): the text above is what counts.</p>`;
  },
};
