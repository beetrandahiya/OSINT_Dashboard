// News places from GDELT: each circle is a town or city that articles in the newest 15-minute file mention,
// sized by how many different outlets did. That count is the only number shown; nothing is scored or ranked beyond it.
import {ago, esc, local, utc} from './util.js';

const SRC = 'ww-news', LIST_MIN_OUTLETS = 3;
let places = [], info = null, published = 0, articles = 0;
const short = p => p.place.split(',')[0];
const rest = p => p.place.split(',').slice(1).map(s => s.trim()).filter((s, i, a) => s && s !== short(p) && a.indexOf(s) === i).join(', ');

// Many outlets print the same agency story under the same headline: show it once, with the outlets that ran it.
function stories(p) {
  const groups = new Map();
  for (const a of p.articles) { const k = a.title.trim().toLowerCase(); groups.set(k, [...(groups.get(k) || []), a]); }
  return [...groups.values()].sort((x, y) => y.length - x.length);
}

export default {
  id: 'news', title: 'News', color: ['#ff3b30', '#ff453a'], feeds: {news: 60}, layers: ['ww-news', 'ww-news-label'],

  addTo(map) {
    map.addSource(SRC, {type: 'geojson', data: {type: 'FeatureCollection', features: []}});
    const size = ['interpolate', ['linear'], ['sqrt', ['get', 'n']], 1, 3.5, 2, 7, 4, 13, 7, 22];
    map.addLayer({id: 'ww-news', type: 'circle', source: SRC, layout: {'circle-sort-key': ['get', 'n']},
      paint: {'circle-radius': size, 'circle-opacity': 0.86, 'circle-stroke-width': 1.2}});
    map.addLayer({id: 'ww-news-label', type: 'symbol', source: SRC, filter: ['>=', ['get', 'n'], 4],
      layout: {'text-field': ['to-string', ['get', 'n']], 'text-font': ['Noto Sans Bold'], 'text-size': 10, 'text-allow-overlap': true, 'text-ignore-placement': true},
      paint: {'text-color': '#ffffff'}});
  },
  paint(map, dark) {
    map.setPaintProperty('ww-news', 'circle-color', this.color[+dark]);
    map.setPaintProperty('ww-news', 'circle-stroke-color', dark ? '#1c1c1e' : '#ffffff');
  },
  onData(feed, d) { places = d.payload.places; articles = d.payload.articles; published = d.payload.published; info = d; },
  render(map) {
    map.getSource(SRC).setData({type: 'FeatureCollection', features: places.map(p => (
      {type: 'Feature', geometry: {type: 'Point', coordinates: [p.lon, p.lat]}, properties: {id: p.place, n: p.outlets}}))});
  },
  count: () => places.length,
  rows() {
    return places.filter(p => p.outlets >= LIST_MIN_OUTLETS).map(p => ({
      id: p.place, time: published, order: p.outlets, badge: String(p.outlets), strong: p.outlets >= 8,
      title: p.articles[0].title,
      meta: `${short(p)} · ${p.outlets} outlets · ${local(published)}`}));
  },
  locate(id) { const p = places.find(x => x.place === id); return p && [p.lon, p.lat]; },
  ring(id) { const p = places.find(x => x.place === id); return p ? 7 + Math.sqrt(p.outlets) * 3.4 : 12; },
  detail(id) {
    const p = places.find(x => x.place === id);
    if (!p) return null;
    return `<p class="eyebrow">News place</p>
      <h2>${esc(short(p))}</h2>
      <p class="where">${esc(rest(p))}${rest(p) ? ' · ' : ''}${p.outlets} ${p.outlets === 1 ? 'outlet' : 'outlets'}</p>
      <ol class="links">${stories(p).map(g => `<li><a href="${esc(g[0].url)}" target="_blank" rel="noopener">${esc(g[0].title)}</a>
        <span>${g.slice(0, 4).map(a => `<a class="outlet" href="${esc(a.url)}" target="_blank" rel="noopener">${esc(a.outlet)}</a>`).join(', ')}${g.length > 4 ? ` and ${g.length - 4} more` : ''}</span></li>`).join('')}</ol>
      ${p.outlets > p.articles.length ? `<p class="source">Showing ${p.articles.length} of ${p.outlets} outlets.</p>` : ''}
      <p class="source">Source: GDELT, file published ${utc(published)} (${ago(published)}), ${articles} articles in it. GDELT's software reads each article and picks out place names, so a story can land on a place it only mentions in passing. Identical headlines are shown once.</p>`;
  },
};
