// The front line in Ukraine from DeepState: occupied and contested areas, Russian unit positions, attack
// directions, airfields and headquarters as they mark them, and the advances logged in the last 7 days.
import {ago, esc, spyPass} from './util.js';

const SRC = 'ww-front';
const KIND = {unit: ['U', 'Russian unit position'], attack: ['➜', 'Direction of attack'], airfield: ['A', 'Airfield'], hq: ['H', 'Headquarters']};
const AREA = {occupied: 'Occupied by Russia', contested: 'Status unknown (contested)', held: 'Held by Russia-backed authorities'};
let d = null, info = null, byKey = new Map();
// ids from the item itself, not its list position: a refresh with more or fewer changes must not turn an open card into
// another item (the server's hotspot signals use the same change id)
const r4 = x => Math.round(x * 1e4) / 1e4;
const keyOf = {a: a => `front:a${a.kind}|${a.name}|${a.rings[0]?.[0]?.map(r4).join(',')}`, p: p => `front:p${p.kind}|${r4(p.lon)},${r4(p.lat)}`, c: c => `front:c${c.id}|${c.place}`};
// polygon centroid of the outer ring (the first vertex can be far from the area)
function centroid(r) {
  let a = 0, x = 0, y = 0;
  for (let i = 0, j = r.length - 1; i < r.length; j = i++) { const f = r[j][0] * r[i][1] - r[i][0] * r[j][1]; a += f; x += (r[j][0] + r[i][0]) * f; y += (r[j][1] + r[i][1]) * f; }
  return a ? [x / (3 * a), y / (3 * a)] : r[0];
}
const day = t => new Date(t * 1000).toLocaleDateString('en-GB', {day: 'numeric', month: 'short'});

export default {
  id: 'front', title: 'Front line, Ukraine', color: ['#d70015', '#ff6961'], feeds: {front_ukraine: 1800},
  layers: ['ww-front-fill', 'ww-front-line', 'ww-front-dot', 'ww-front-label', 'ww-front-change'],
  about: () => "DeepState's daily map of the war in Ukraine: occupied and contested areas, units, advances.",

  addTo(map) {
    map.addSource(SRC, {type: 'geojson', data: {type: 'FeatureCollection', features: []}});
    map.addLayer({id: 'ww-front-fill', type: 'fill', source: SRC, filter: ['==', ['geometry-type'], 'Polygon'],
      paint: {'fill-opacity': ['match', ['get', 'kind'], 'occupied', 0.22, 'contested', 0.18, 0.1]}});
    map.addLayer({id: 'ww-front-line', type: 'line', source: SRC, filter: ['==', ['geometry-type'], 'Polygon'],
      paint: {'line-width': ['match', ['get', 'kind'], 'occupied', 1.4, 0.8], 'line-opacity': 0.8}});
    // units and the rest only from zoom 6: at country scale the 400 markers are a smear
    map.addLayer({id: 'ww-front-dot', type: 'circle', source: SRC, minzoom: 6, filter: ['all', ['==', ['geometry-type'], 'Point'], ['has', 'k']],
      paint: {'circle-radius': ['interpolate', ['exponential', 1.6], ['zoom'], 6, ['match', ['get', 'kind'], 'unit', 4, 5], 9, ['match', ['get', 'kind'], 'unit', 7, 8], 13, ['match', ['get', 'kind'], 'unit', 12, 14]], 'circle-stroke-width': 1.2}});
    map.addLayer({id: 'ww-front-label', type: 'symbol', source: SRC, minzoom: 6, filter: ['all', ['==', ['geometry-type'], 'Point'], ['has', 'k']],
      layout: {'text-field': ['get', 'k'], 'text-font': ['Noto Sans Bold'], 'text-size': 9, 'text-allow-overlap': true, 'text-ignore-placement': true}});
    map.addLayer({id: 'ww-front-change', type: 'circle', source: SRC, filter: ['==', ['get', 'change'], true],
      paint: {'circle-radius': ['interpolate', ['exponential', 1.6], ['zoom'], 3, 3, 6, 7, 9, 13, 13, 26], 'circle-color': 'transparent', 'circle-stroke-width': ['interpolate', ['linear'], ['zoom'], 3, 1.2, 9, 2.5]}});
  },
  paint(map, dark) {
    const c = this.color[+dark];
    map.setPaintProperty('ww-front-fill', 'fill-color', ['match', ['get', 'kind'], 'occupied', c, 'contested', dark ? '#aeaeb2' : '#8e8e93', c]);
    map.setPaintProperty('ww-front-line', 'line-color', ['match', ['get', 'kind'], 'occupied', c, dark ? '#aeaeb2' : '#8e8e93']);
    map.setPaintProperty('ww-front-dot', 'circle-color', ['match', ['get', 'kind'], 'unit', c, 'attack', dark ? '#ff9f0a' : '#c93400', dark ? '#636366' : '#3a3a3c']);
    map.setPaintProperty('ww-front-dot', 'circle-stroke-color', dark ? '#1c1c1e' : '#ffffff');
    map.setPaintProperty('ww-front-label', 'text-color', '#ffffff');
    map.setPaintProperty('ww-front-change', 'circle-stroke-color', dark ? '#ffd60a' : '#b25000');
  },
  onData(feed, x) {
    d = x.payload; info = x; byKey = new Map();
    for (const k of ['a', 'p', 'c']) for (const it of d[{a: 'areas', p: 'points', c: 'changes'}[k]] || []) byKey.set(keyOf[k](it), [k, it]);
  },
  render(map) {
    if (!d) return;
    const feats = [];
    d.areas.forEach(a => feats.push({type: 'Feature', geometry: {type: 'Polygon', coordinates: a.rings}, properties: {id: keyOf.a(a), kind: a.kind}}));
    d.points.forEach(p => feats.push({type: 'Feature', geometry: {type: 'Point', coordinates: [p.lon, p.lat]}, properties: {id: keyOf.p(p), kind: p.kind, k: KIND[p.kind]?.[0] || '?'}}));
    d.changes.forEach(c => feats.push({type: 'Feature', geometry: {type: 'Point', coordinates: [c.lon, c.lat]}, properties: {id: keyOf.c(c), change: true}}));
    map.getSource(SRC).setData({type: 'FeatureCollection', features: feats});
  },
  count: () => d ? d.changes.length : 0,
  rows() {
    if (!d) return [];
    return d.changes.map(c => ({id: keyOf.c(c), time: c.time, badge: '⚔', title: c.text.slice(0, 110),
      meta: `${c.place} · DeepState, ${day(c.time)}`}));     // the list escapes meta itself
  },
  owns: id => String(id).startsWith('front:'),
  locate(id) {
    const [k, it] = byKey.get(id) || [];
    if (!it) return null;
    return k === 'a' ? (it.rings[0] ? centroid(it.rings[0]) : null) : [it.lon, it.lat];
  },
  ring: () => 12,
  detail(id) {
    if (!d) return null;
    const [k, it] = byKey.get(id) || [];
    if (!it) return '<p class="eyebrow">Front line</p><h2>No longer in the feed</h2><p class="soft">DeepState\'s newest update no longer has this item.</p>';
    const wk = d.week ? d.occupied_km2 - d.week.occupied_km2 : null;
    const src = `<p class="source">Source: DeepState (deepstatemap.live), a Ukrainian open-source team that maps the war from geolocated footage and official statements; their update of ${day(d.update.time)}, read ${ago(info?.fetched)}. One side's assessment, published hours to a day after the fact. Occupied area summed by us from their shapes: ${d.occupied_km2.toLocaleString('en-GB')} km²${wk != null ? ` (${wk >= 0 ? '+' : ''}${wk.toLocaleString('en-GB')} km² since ${day(d.week.time)})` : ''}.</p>`;
    if (k === 'c') {
      const c = it;
      const same = d.changes.filter(x => x.id === c.id && x !== c).map(x => x.place);
      return `<p class="eyebrow">Front line · change</p><h2>${esc(c.place)}</h2>
        <p class="where">${new Date(c.time * 1000).toLocaleString('en-GB', {day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit'})}</p>
        <p>${esc(c.text)}</p>${same.length ? `<p class="soft">Same update also names ${same.map(esc).join(', ')}.</p>` : ''}
        ${spyPass(c.lat, c.lon)}${src}`;
    }
    if (k === 'p') {
      const p = it;
      return `<p class="eyebrow">Front line · ${esc(KIND[p.kind]?.[1] || p.kind)}</p><h2>${esc(p.name)}</h2>
        ${p.note ? `<p>${esc(p.note)}</p>` : ''}
        ${p.kind === 'attack' ? '<p class="soft">DeepState draws these as arrows; the direction is in their picture, which we do not read, so only the place is marked.</p>' : ''}
        ${p.kind === 'unit' ? '<p class="soft">Where DeepState places this Russian unit. Positions of units are their reading of reports and footage.</p>' : ''}
        ${spyPass(p.lat, p.lon)}${src}`;
    }
    const a = it;
    return `<p class="eyebrow">Front line · area</p><h2>${esc(AREA[a.kind])}</h2><p class="where">${esc(a.name)}</p>
      <p>Occupied: ${d.occupied_km2.toLocaleString('en-GB')} km² in total${wk != null ? `, ${wk >= 0 ? '+' : ''}${wk.toLocaleString('en-GB')} km² in the week to ${day(d.update.time)}` : ''}. ${d.changes.length} changes logged in the last 7 days.</p>
      ${d.update.text ? `<p class="soft">Latest update: ${esc(d.update.text)}</p>` : ''}${src}`;
  },
};
