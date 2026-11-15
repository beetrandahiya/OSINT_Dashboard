// News places from GDELT over the last six hours: each circle is a town or city that articles mention, sized by how
// many different outlets did. That count is the only number shown; nothing is scored or ranked beyond it.
// Pictures are the outlets' own preview images, fetched through our server (/api/news/image) so outlets never see
// the browser. Headlines in other languages are machine-translated: the leading one at once, the rest when a card opens.
import {ago, esc, local, utc} from './util.js';

const SRC = 'ww-news', LIST_MIN_OUTLETS = 3;
let places = [], sets = {}, langs = {eng: 'English'};
const full = new Map();   // place -> every article, fetched when its card opens

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
  id: 'news', title: 'News', color: ['#ff3b30', '#ff453a'], feeds: {news: 60, news_translated: 120}, layers: ['ww-news', 'ww-news-label'],

  addTo(map) {
    map.addSource(SRC, {type: 'geojson', data: {type: 'FeatureCollection', features: []}});
    const size = ['interpolate', ['linear'], ['sqrt', ['get', 'n']], 1, 3, 2, 5.5, 4, 10, 8, 17, 14, 26];
    map.addLayer({id: 'ww-news', type: 'circle', source: SRC, layout: {'circle-sort-key': ['get', 'n']},
      paint: {'circle-radius': size, 'circle-opacity': 0.86, 'circle-stroke-width': 1.2}});
    map.addLayer({id: 'ww-news-label', type: 'symbol', source: SRC, filter: ['>=', ['get', 'n'], 6],
      layout: {'text-field': ['to-string', ['get', 'n']], 'text-font': ['Noto Sans Bold'], 'text-size': 10, 'text-allow-overlap': true, 'text-ignore-placement': true},
      paint: {'text-color': '#ffffff'}});
  },
  paint(map, dark) {
    map.setPaintProperty('ww-news', 'circle-color', this.color[+dark]);
    map.setPaintProperty('ww-news', 'circle-stroke-color', dark ? '#1c1c1e' : '#ffffff');
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
    const arts = full.get(id) || p.articles, hero = arts.find(a => a.image);
    const e = sets.news, t = sets.news_translated;
    return `<p class="eyebrow">News place · last ${e?.window_h || 6} hours</p>
      <h2>${esc(short(p))}</h2>
      <p class="where">${esc(rest(p))}${rest(p) ? ' · ' : ''}${p.outlets} ${p.outlets === 1 ? 'outlet' : 'outlets'} · newest ${ago(p.last)}</p>
      ${hero ? `<img class="news-hero" src="${esc(img(hero.image))}" alt="" onerror="this.remove()">` : ''}
      <div id="more">${storyList(arts)}${full.has(id) ? '' : (p.outlets > p.articles.length ? `<p class="source">Loading all ${p.outlets} outlets…</p>` : '')}</div>
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
      if (now) now.innerHTML = storyList(r.articles) + (r.untranslated ? `<p class="source">${r.untranslated} headlines could not be translated and stay in their language.</p>` : '');
    } catch (e) { box.dataset.done = ''; }
  },
};
