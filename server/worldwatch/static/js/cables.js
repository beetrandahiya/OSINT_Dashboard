// Undersea internet cables; the ones named in fault or repair news are drawn in red
// (SubTel Forum's fault category and our news window, matched to TeleGeography's cable names; see cablefaults.py).
// Routes from TeleGeography's Submarine Cable Map (CC BY-NC-SA: private, non-commercial use), drawn schematically.
import {ago, esc} from './util.js';
import {slot} from './map.js';

let data = null, info = null, faults = {}, faultInfo = null, names = new Map(), theMap = null;
const day = t => new Date(t * 1000).toLocaleDateString('en-GB', {day: 'numeric', month: 'short'});

export default {
  id: 'cables', title: 'Cables', color: ['#d70015', '#ff453a'], feeds: {cables: 21600, cable_faults: 1800}, layers: ['ww-cables', 'ww-cables-hit'],
  about: () => 'Undersea internet cables; red where fault or repair news named them in the last 60 days.',
  addTo(map) {
    theMap = map;
    map.addSource('ww-cables', {type: 'geojson', data: {type: 'FeatureCollection', features: []}});
    const first = slot(map, 'area');   // over the photos, sky pictures and GPS hexagons, under the place names
    map.addLayer({id: 'ww-cables', type: 'line', source: 'ww-cables',
      layout: {'line-sort-key': ['match', ['get', 'state'], 'problem', 2, 'restored', 1, 0]},
      paint: {'line-width': ['interpolate', ['linear'], ['zoom'], 1, ['match', ['get', 'state'], 'problem', 1.8, 'restored', 1.2, 0.6], 6, ['match', ['get', 'state'], 'problem', 3.2, 'restored', 2.2, 1.6]],
        'line-opacity': ['interpolate', ['linear'], ['zoom'], 1, ['match', ['get', 'state'], 'problem', 0.95, 'restored', 0.8, 0.4], 5, ['match', ['get', 'state'], 'problem', 0.95, 'restored', 0.8, 0.75]]}}, first);
    map.addLayer({id: 'ww-cables-hit', type: 'line', source: 'ww-cables', paint: {'line-width': 12, 'line-opacity': 0}}, first);   // a wider invisible line, easier to click
  },
  paint(map, dark) { map.setPaintProperty('ww-cables', 'line-color', ['match', ['get', 'state'], 'problem', dark ? '#ff453a' : '#d70015', 'restored', dark ? '#30d158' : '#248a3d', dark ? '#7d8a99' : '#6b7a8c']); },
  onData(feed, d) {
    if (feed === 'cable_faults') { faults = d.payload.cables || {}; faultInfo = d; }
    else { data = d.payload; info = d; names = new Map(data.features.map(f => [f.properties.id, f.properties.name])); }
  },
  render(map) {
    if (!data) return;
    const feats = data.features.map(f => ({...f, properties: {...f.properties, state: faults[f.properties.id.slice(6)]?.state || 'ok'}}));
    map.getSource('ww-cables').setData({type: 'FeatureCollection', features: feats});
  },
  count: () => Object.values(faults).filter(c => c.state === 'problem').length,   // the chip counts the red ones
  rows: () => Object.entries(faults).map(([id, c]) => ({id: 'cable:' + id, time: c.items[0].time, badge: c.state === 'restored' ? '✓' : '⚡',
    title: `${c.name}: ${c.items[0].title}`, meta: `${c.state === 'restored' ? 'Restored' : 'Fault or repair'} · ${esc(c.items[0].source)}, ${day(c.items[0].time)}`})),
  locate(id) {
    const f = data?.features.find(x => x.properties.id === id); if (!f) return null;
    const g = f.geometry, line = g.type === 'MultiLineString' ? g.coordinates[0] : g.coordinates;
    return line[Math.floor(line.length / 2)];
  },
  ring: () => 0,
  async fill() {
    const box = document.getElementById('cableabout'); if (!box || box.dataset.done) return;
    box.dataset.done = '1';
    let c; try { c = await fetch('/api/cable/' + box.dataset.cid).then(r => r.json()); } catch (e) { c = {error: 'no answer'}; }
    if (document.getElementById('cableabout') !== box) return;
    if (c.error) { box.innerHTML = `<p class="pic-wait">${esc(c.error)}</p>`; box.dataset.done = ''; return; }
    const lp = c.landing_points || [];
    box.innerHTML = `<dl>
      ${c.owners ? `<dt>Owners</dt><dd>${esc(c.owners)}</dd>` : ''}
      ${c.length ? `<dt>Length</dt><dd>${esc(c.length)}</dd>` : ''}
      ${c.rfs ? `<dt>In service since</dt><dd>${esc(c.rfs)}${c.is_planned ? ' <span class="soft">(planned)</span>' : ''}</dd>` : ''}
      ${c.suppliers ? `<dt>Built by</dt><dd>${esc(c.suppliers)}</dd>` : ''}
      ${lp.length ? `<dt>Lands at</dt><dd>${lp.map(p => esc(p.name)).join(' · ')} <span class="soft">(${lp.length} landing points, ${new Set(lp.map(p => p.country)).size} countries)</span></dd>` : ''}
      ${c.url ? `<dt>Website</dt><dd><a class="link" href="${esc(c.url)}" target="_blank" rel="noopener">${esc(c.url.replace(/^https?:\/\//, ''))}</a></dd>` : ''}
    </dl>`;
  },
  owns: id => String(id).startsWith('cable:'),
  detail(id) {
    if (!names.has(id)) return null;
    const c = faults[id.slice(6)];
    return `<p class="eyebrow">Undersea cable${c ? ' · ' + (c.state === 'restored' ? 'reported restored' : 'fault or repair reported') : ''}</p><h2>${esc(names.get(id))}</h2>
      ${c ? `<ol class="stories">${c.items.map(i => `<li><span class="st"><a href="${esc(i.url)}" target="_blank" rel="noopener">${esc(i.title)}</a><span class="by">${esc(i.source)} · ${day(i.time)}</span></span></li>`).join('')}</ol>` : ''}
      <div id="cableabout" data-cid="${esc(id.slice(6))}"><p class="pic-wait">Reading owners and landing points…</p></div>
      <a class="link" href="https://www.submarinecablemap.com/submarine-cable/${esc(id.slice(6))}" target="_blank" rel="noopener">This cable on the Submarine Cable Map</a>
      <p class="source">Marked because a headline names this cable together with a word like fault, cut, damage, repair or outage (SubTel Forum's fault and maintenance news, last 60 days, and our 6-hour news window), matched by name or acronym; read ${ago(faultInfo?.fetched)}. "Restored" when the newest headline says so. No free source states where along a cable the fault is, so the whole route is drawn; TeleGeography draws routes schematically. Cables with no such news are grey; that does not mean they are known to be working.</p>`;
  },
};
