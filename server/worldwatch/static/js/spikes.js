// Breaking-news spikes: places where many outlets suddenly reported in the newest hour, compared with the same place's
// own rate in the hours before. Worked out on our server from the GDELT news windows (news.spikes); said so.
import {every} from './prefs.js';
import {ago, esc, skyShot, spyPass, countryBtn} from './util.js';
import {img} from './news.js';

let d = {spikes: []}, maps = [];
// ids come from the server (series + place), so a reload that reorders the list never swaps an open card
const sid = (s, i) => s.id || 'spike:' + i, get = id => d.spikes.find((s, i) => sid(s, i) === id);
async function load() {
  try { d = await fetch('/api/news/spikes', {cache: 'no-store'}).then(r => r.json()); } catch (e) { return; }
  for (const [l, m] of maps) l.render(m);
}

export default {
  id: 'spikes', title: 'Breaking', color: ['#d70015', '#ff453a'], feeds: {}, local: true,
  layers: ['ww-spike-halo', 'ww-spike'],
  about: () => 'Places where the news suddenly picked up in the last hour, compared with the hours before.',
  addTo(map) {
    map.addSource('ww-spikes', {type: 'geojson', data: {type: 'FeatureCollection', features: []}});
    map.addLayer({id: 'ww-spike-halo', type: 'circle', source: 'ww-spikes', paint: {'circle-radius': ['interpolate', ['linear'], ['get', 'n'], 4, 16, 20, 30], 'circle-opacity': 0.18}});
    map.addLayer({id: 'ww-spike', type: 'circle', source: 'ww-spikes', paint: {'circle-radius': 7, 'circle-stroke-width': 2}});
    maps.push([this, map]);
    if (maps.length === 1) { load(); every(120, load); }
  },
  paint(map, dark) {
    const c = this.color[+dark];
    map.setPaintProperty('ww-spike-halo', 'circle-color', c);
    map.setPaintProperty('ww-spike', 'circle-color', c);
    map.setPaintProperty('ww-spike', 'circle-stroke-color', dark ? '#1c1c1e' : '#ffffff');
  },
  onData() {},
  render(map) {
    map.getSource('ww-spikes')?.setData({type: 'FeatureCollection', features: d.spikes.map((s, i) => ({type: 'Feature', geometry: {type: 'Point', coordinates: [s.lon, s.lat]}, properties: {id: sid(s, i), n: s.headlines}}))});
  },
  count: () => d.spikes.length,
  rows: () => d.spikes.map((s, i) => ({id: sid(s, i), time: d.newest || s.first, badge: '!', strong: true, title: `Breaking: ${s.place.split(',')[0]} · ${s.articles[0]?.title || ''}`,
    thumb: img(s.articles.find(a => a.image)?.image), meta: `${s.story_headlines || s.headlines} headlines from ${s.story_outlets || s.outlets} outlets on one story${s.story_words ? ' (“' + s.story_words.join(' ') + '”)' : ''}, ${s.times}× the usual rate`})),
  owns: id => !!get(id),
  locate(id) { const s = get(id); return s && [s.lon, s.lat]; },
  ring: () => 16,
  detail(id) {
    const s = get(id); if (!s) return null;
    return `<p class="eyebrow">Breaking · news picked up</p><h2>${esc(s.place.split(',')[0])}</h2><p class="where">${esc(s.place)}</p>
      <dl><dt>Last hour</dt><dd>${s.headlines} different headlines from ${s.outlets} outlets</dd>
        <dt>Before</dt><dd>${s.rate_before} different headlines an hour over the previous ${d.baseline_h} hours <span class="soft">(${s.times}× now)</span></dd>
        ${s.story_words ? `<dt>Shared story</dt><dd>${s.story_headlines} headlines from ${s.story_outlets} outlets share “${s.story_words.map(esc).join('” and “')}”; they are listed first</dd>` : ''}</dl>
      <ol class="stories">${s.articles.map(a => `<li>${a.image ? `<img src="${esc(img(a.image))}" alt="" loading="lazy" onerror="this.remove()">` : ''}<span class="st">
        <a href="${esc(a.url)}" target="_blank" rel="noopener">${esc(a.title)}</a><span class="by">${esc(a.outlet)} · ${ago(a.time)}${a.lang !== 'eng' ? ' · not in English' : ''}</span></span></li>`).join('')}</ol>
      ${countryBtn({lat: s.lat, lon: s.lon})} ${spyPass(s.lat, s.lon)}
      <p class="source">Worked out by this server from GDELT's news of the last 6 hours: ${esc(d.rule || '')}. Copies of one agency story count once. A spike says many outlets started reporting about this place, not what happened; read the headlines. The place is where GDELT pinned the articles.</p>`;
  },
};
