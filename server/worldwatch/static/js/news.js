// News places from GDELT over the last six hours: each circle is a town or city that articles mention, sized by how
// many different outlets did. That count is the only number shown; nothing is scored or ranked beyond it.
// Pictures are the outlets' own preview images, fetched through our server (/api/news/image) so outlets never see
// the browser. Headlines in other languages are machine-translated: the leading one at once, the rest when a card opens.
import {ago, esc, local, skyShot, utc, spyPass, countryBtn} from './util.js';

const SRC = 'ww-news', LIST_MIN_OUTLETS = 3;
let places = [], sets = {}, langs = {eng: 'English'};
const full = new Map();
let mapRef = null;   // place -> every article, fetched when its card opens

export const img = u => u ? '/api/news/image?u=' + encodeURIComponent(u) : null;

// Two GDELT series feed this layer: English (15 minutes behind at most) and every other language (about an hour
// behind). Places are merged; outlets are counted once.
function merge() {
  const by = new Map();
  for (const feed of ['news', 'news_translated']) for (const p of sets[feed]?.places || []) {
    const m = by.get(p.place) || {place: p.place, lat: p.lat, lon: p.lon, outlets: 0, articles: [], last: 0, seen: new Set()};
    for (const a of p.articles) if (!m.seen.has(a.outlet)) { m.seen.add(a.outlet); m.articles.push(a); }
    m.outlets += p.outlets; m.last = Math.max(m.last, p.last);
    by.set(p.place, m);
  }
  for (const m of by.values()) m.articles.sort((a, b) => (b.lang === 'eng' || !!b.translated) - (a.lang === 'eng' || !!a.translated) || !!b.image - !!a.image || b.time - a.time);
  places = [...by.values()].sort((a, b) => b.outlets - a.outlets);
}
const short = p => p.place.split(',')[0];
const rest = p => p.place.split(',').slice(1).map(s => s.trim()).filter((s, i, a) => s && s !== short(p) && a.indexOf(s) === i).join(', ');

// Many outlets print the same agency story under the same headline: show it once, with the outlets that ran it.
function stories(arts) {
  const groups = new Map();
  for (const a of arts) { const k = a.title.trim().toLowerCase(); groups.set(k, [...(groups.get(k) || []), a]); }
  return [...groups.values()].sort((x, y) => y.length - x.length || y[0].time - x[0].time);
}
// the card's big picture belongs to the first story listed, not to whichever article happened to carry one
const heroOf = arts => stories(arts)[0]?.find(a => a.image)?.image;
const heroHtml = pic => pic ? `<img class="news-hero" src="${esc(img(pic))}" alt="" onerror="this.remove()">` : '';
function storyList(arts) {
  return `<ol class="stories">${stories(arts).map(g => {
    const a = g[0], pic = g.find(x => x.image)?.image;
    const lang = a.lang && a.lang !== 'eng' ? ' · ' + (a.translated ? 'machine-translated from ' : '') + (langs[a.lang] || a.lang) : '';
    return `<li>${pic ? `<img src="${esc(img(pic))}" alt="" loading="lazy" onerror="this.remove()">` : ''}<span class="st">
      <a href="${esc(a.url)}" target="_blank" rel="noopener">${esc(a.title)}</a>${a.translated ? `<span class="orig">${esc(a.title_original)}</span>` : ''}
      <span class="by">${g.slice(0, 3).map(x => `<a href="${esc(x.url)}" target="_blank" rel="noopener">${esc(x.outlet)}</a>`).join(', ')}${g.length > 3 ? ` and ${g.length - 3} more` : ''} · ${ago(a.time)}${lang}</span></span></li>`;
  }).join('')}</ol>`;
}

export default {
  id: 'news', title: 'News', color: ['#ff3b30', '#ff453a'], feeds: {news: 60, news_translated: 120}, layers: ['ww-news-group', 'ww-news-group-label', 'ww-news', 'ww-news-label'],

  addTo(map) {
    mapRef = map;
    // Nearby places merge into one bubble while zoomed out (Apple Maps clusters overlapping points the same way):
    // its number is how many places it holds, its size the outlets they add up to. Zooming in splits it.
    map.addSource(SRC, {type: 'geojson', data: {type: 'FeatureCollection', features: []}, cluster: true, clusterRadius: 34, clusterMaxZoom: 5,
      clusterProperties: {sum: ['+', ['get', 'n']], top: ['max', ['get', 'n']]}});
    const size = ['interpolate', ['linear'], ['sqrt', ['get', 'n']], 1, 2.5, 2, 3, 3, 6, 6, 11, 14, 24];
    map.addLayer({id: 'ww-news-group', type: 'circle', source: SRC, filter: ['has', 'point_count'], layout: {'circle-sort-key': ['get', 'sum']},
      paint: {'circle-radius': ['interpolate', ['linear'], ['sqrt', ['get', 'sum']], 1, 7, 6, 11, 14, 18, 30, 28], 'circle-opacity': 0.28, 'circle-stroke-width': 1.5}});
    map.addLayer({id: 'ww-news-group-label', type: 'symbol', source: SRC, filter: ['has', 'point_count'],
      layout: {'text-field': ['to-string', ['get', 'point_count']], 'text-font': ['Noto Sans Bold'], 'text-size': 10, 'text-allow-overlap': true, 'text-ignore-placement': true}});
    // Single places: one or two outlets are small faint dots; three or more full circles; ten or more carry their number.
    map.addLayer({id: 'ww-news', type: 'circle', source: SRC, filter: ['!', ['has', 'point_count']], layout: {'circle-sort-key': ['get', 'n']},
      paint: {'circle-radius': size, 'circle-opacity': ['case', ['<', ['get', 'n'], 3], 0.4, 0.88], 'circle-stroke-width': ['case', ['<', ['get', 'n'], 3], 0, 1.2]}});
    map.addLayer({id: 'ww-news-label', type: 'symbol', source: SRC, filter: ['all', ['!', ['has', 'point_count']], ['>=', ['get', 'n'], 10]],
      layout: {'text-field': ['to-string', ['get', 'n']], 'text-font': ['Noto Sans Bold'], 'text-size': 10, 'text-allow-overlap': true, 'text-ignore-placement': true},
      paint: {'text-color': '#ffffff'}});
  },
  paint(map, dark) {
    const c = this.color[+dark];
    map.setPaintProperty('ww-news', 'circle-color', c);
    map.setPaintProperty('ww-news', 'circle-stroke-color', dark ? '#1c1c1e' : '#ffffff');
    map.setPaintProperty('ww-news-group', 'circle-color', c);
    map.setPaintProperty('ww-news-group', 'circle-stroke-color', c);
    map.setPaintProperty('ww-news-group-label', 'text-color', dark ? '#ffffff' : '#1c1c1e');
  },
  // A click on a merged bubble zooms in until it splits; it never opens a card of its own.
  pick(props) {
    if (!props.cluster || !mapRef) return true;
    const f = mapRef.querySourceFeatures(SRC, {filter: ['==', ['get', 'cluster_id'], props.cluster_id]})[0];
    mapRef.getSource(SRC).getClusterExpansionZoom(props.cluster_id).then(z => mapRef.easeTo({center: f ? f.geometry.coordinates : mapRef.getCenter(), zoom: Math.min(z + 0.2, 8)}));
    return false;
  },
  onData(feed, d) { sets[feed] = d.payload; if (d.payload?.languages) langs = {...langs, ...d.payload.languages}; merge(); },
  render(map) {
    map.getSource(SRC).setData({type: 'FeatureCollection', features: places.map(p => (
      {type: 'Feature', geometry: {type: 'Point', coordinates: [p.lon, p.lat]}, properties: {id: p.place, n: p.outlets}}))});
  },
  count: () => places.length,
  rows() {
    return places.filter(p => p.outlets >= LIST_MIN_OUTLETS).map(p => ({
      id: p.place, time: p.last, order: p.outlets, badge: String(p.outlets), strong: p.outlets >= 12,
      title: p.articles[0].title, thumb: img(p.articles.find(a => a.image)?.image),
      meta: `${short(p)} · ${p.outlets} outlets · ${local(p.last)}`}));
  },
  locate(id) { const p = places.find(x => x.place === id); return p && [p.lon, p.lat]; },
  ring(id) { const p = places.find(x => x.place === id); return p ? 7 + Math.sqrt(p.outlets) * 3 : 12; },
  detail(id) {
    const p = places.find(x => x.place === id);
    if (!p) return null;
    const arts = full.get(id) || p.articles;
    const e = sets.news, t = sets.news_translated;
    return `<p class="eyebrow">News place · last ${e?.window_h || 6} hours</p>
      <h2>${esc(short(p))}</h2>
      <p class="where">${esc(rest(p))}${rest(p) ? ' · ' : ''}${p.outlets} ${p.outlets === 1 ? 'outlet' : 'outlets'} · newest ${ago(p.last)}</p>
      <div id="newshero">${heroHtml(heroOf(arts))}</div>
      <div id="more">${storyList(arts)}${full.has(id) ? '' : (p.outlets > p.articles.length ? `<p class="source">Loading all ${p.outlets} outlets…</p>` : '')}</div>
      ${countryBtn({lat: p.lat, lon: p.lon})}
      ${skyShot(p.lat, p.lon)}
      ${spyPass(p.lat, p.lon)}
      <p class="source">Source: GDELT, files from the last ${e?.window_h || 6} hours. English: ${e ? `${e.files} files, newest published ${utc(e.newest)} (${ago(e.newest)})` : 'not loaded yet'}. Other languages: ${t ? `${t.files} files, newest ${utc(t.newest)} (${ago(t.newest)}; GDELT releases them about an hour late)` : 'not loaded yet'}. GDELT's software reads each article and picks out place names, so a story can land on a place it only mentions in passing. Identical headlines are shown once. Pictures are each outlet's own preview image. Headlines in other languages are translated by machine (Google Translate) and can be wrong; the original is shown beneath.</p>`;
  },
  async fill(id) {
    const box = document.getElementById('more');
    if (!box || box.dataset.done || full.has(id)) return;
    box.dataset.done = '1';
    try {
      const r = await fetch('/api/news/place?p=' + encodeURIComponent(id), {cache: 'no-store'}).then(r => r.json());
      langs = {...langs, ...r.languages};
      full.set(id, r.articles);
      if (full.size > 40) full.delete(full.keys().next().value);
      const now = document.getElementById('more');
      const hero = document.getElementById('newshero');
      if (hero && now) hero.innerHTML = heroHtml(heroOf(r.articles));
      if (now) now.innerHTML = storyList(r.articles) + (r.untranslated ? `<p class="source">${r.untranslated} headlines could not be translated and stay in their language.</p>` : '');
    } catch (e) { box.dataset.done = ''; }
  },
};
