// People layer: current heads of state and government at their countries. Click one for a full profile.
// Profiles come from public records (Wikidata, Wikipedia, GDELT, optional OpenSanctions) via our server.
import {ago, esc, countryBtn} from './util.js';
import {openProfile} from './profile.js';

let leaders = [], info = null;
export default {
  id: 'people', title: 'People', color: ['#ff9f0a', '#ffb340'], feeds: {}, layers: ['ww-people', 'ww-people-label'], defaultOff: true, local: true,
  addTo(map) {
    map.addSource('ww-people', {type: 'geojson', data: {type: 'FeatureCollection', features: []}});
    map.addLayer({id: 'ww-people', type: 'circle', source: 'ww-people',
      paint: {'circle-radius': 6, 'circle-opacity': 0.95, 'circle-stroke-width': 1.5}});
    map.addLayer({id: 'ww-people-label', type: 'symbol', source: 'ww-people', minzoom: 2.4,
      layout: {'text-field': ['get', 'name'], 'text-font': ['Noto Sans Bold'], 'text-size': 11, 'text-offset': [0, 1], 'text-anchor': 'top', 'text-optional': true},
      paint: {'text-halo-width': 1.3}});
    this.load(map);
  },
  async load(map) {
    try {
      const r = await fetch('/api/people/leaders', {cache: 'no-store'});
      const d = await r.json();
      if (!d.leaders) { setTimeout(() => this.load(map), 30000); return; }   // Wikidata busy: ask again in half a minute
      info = d; leaders = d.leaders;
      // several leaders share a country point (a monarch and a prime minister); nudge the second onto a ring
      const at = {};
      const feats = leaders.map(l => {
        const k = l.lon + ',' + l.lat, n = at[k] = (at[k] || 0);  at[k]++;
        const a = n * 2.4, r2 = n ? 0.8 + n * 0.15 : 0;
        return {type: 'Feature', geometry: {type: 'Point', coordinates: [l.lon + Math.cos(a) * r2, l.lat + Math.sin(a) * r2]},
          properties: {qid: l.qid, name: l.name, role: l.role}};
      });
      map.getSource('ww-people').setData({type: 'FeatureCollection', features: feats});
    } catch (e) { setTimeout(() => this.load(map), 30000); }
  },
  paint(map, dark) {
    map.setPaintProperty('ww-people', 'circle-color', this.color[+dark]);
    map.setPaintProperty('ww-people', 'circle-stroke-color', dark ? '#1c1c1e' : '#ffffff');
    map.setPaintProperty('ww-people-label', 'text-color', dark ? '#e5e5ea' : '#3a3a3c');
    map.setPaintProperty('ww-people-label', 'text-halo-color', dark ? '#1c1c1e' : '#ffffff');
  },
  onData() {}, render() {},
  count: () => leaders.length,
  rows: () => [],
  locate(id) { const l = leaders.find(x => 'person:' + x.qid === id); return l && [l.lon, l.lat]; },
  ring: () => 11,
  owns: id => String(id).startsWith('person:'),
  about: () => 'Current heads of state and government at their countries, from Wikidata' + (info?.note ? ' (' + info.note + ')' : '') + '. Click one for a full public-records profile.',
  pick(featureProps) { openProfile(featureProps.qid); return false; },   // handled by the profile overlay, not the normal card
  detail: () => null,
};

// Leaders today: where the news placed each head of state or government in the last six hours. The place is the
// one the articles naming them were pinned to (usually the dateline), counted by distinct outlets: "reported at",
// never "is at". A thin line joins it to their own country when the two are far apart.
import {img} from './news.js';
let today = [], todayInfo = null, chosen = null;
const km = (a, b) => { const r = Math.PI / 180, x = Math.sin((b[1] - a[1]) * r / 2) ** 2 + Math.cos(a[1] * r) * Math.cos(b[1] * r) * Math.sin((b[0] - a[0]) * r / 2) ** 2; return 12742 * Math.asin(Math.sqrt(x)); };
export const leadersToday = {
  id: 'leaders', title: 'Leaders today', color: ['#ff9f0a', '#ffb340'], feeds: {}, local: true,
  layers: ['ww-leaders-line', 'ww-leaders', 'ww-leaders-label'],
  about: () => 'Where the news placed heads of state and government in the last 6 hours (GDELT), not where they are.',
  addTo(map) {
    map.addSource('ww-leaders', {type: 'geojson', data: {type: 'FeatureCollection', features: []}});
    map.addLayer({id: 'ww-leaders-line', type: 'line', source: 'ww-leaders', filter: ['==', ['geometry-type'], 'LineString'],
      paint: {'line-width': 1.2, 'line-dasharray': [2, 2], 'line-opacity': 0.7}});
    map.addLayer({id: 'ww-leaders', type: 'circle', source: 'ww-leaders', filter: ['==', ['geometry-type'], 'Point'],
      paint: {'circle-radius': ['interpolate', ['linear'], ['sqrt', ['get', 'n']], 1, 5, 4, 8, 8, 12], 'circle-stroke-width': 2, 'circle-opacity': 0.95}});
    map.addLayer({id: 'ww-leaders-label', type: 'symbol', source: 'ww-leaders', filter: ['==', ['geometry-type'], 'Point'],
      layout: {'text-field': ['get', 'name'], 'text-font': ['Noto Sans Bold'], 'text-size': 11, 'text-offset': [0, 1.1], 'text-anchor': 'top', 'text-optional': true,
        'symbol-sort-key': ['-', 0, ['get', 'n']]}, paint: {'text-halo-width': 1.3}});
    this.map = map; this.load();
    setInterval(() => this.load(), 600000);
  },
  async load() {
    try {
      const d = await fetch('/api/people/today', {cache: 'no-store'}).then(r => r.json());
      todayInfo = d; today = d.today || [];
      // One marker per place: leaders reported at the same city share it (they used to sit exactly on top of each
      // other, so a click opened whichever was drawn first).
      const feats = [], byPlace = new Map();
      for (const t of today) { const k = t.place.place; byPlace.set(k, [...(byPlace.get(k) || []), t]); }
      for (const [place, ts] of byPlace) {
        const at = [ts[0].place.lon, ts[0].place.lat];
        feats.push({type: 'Feature', geometry: {type: 'Point', coordinates: at}, properties: {id: 'todayp:' + place, name: ts.map(t => t.name).join('\n'), n: ts.reduce((a, t) => a + t.outlets, 0)}});
        for (const t of ts) if (t.abroad) feats.push({type: 'Feature', geometry: {type: 'LineString', coordinates: [t.home, at]}, properties: {id: 'todayp:' + place}});
      }
      this.map.getSource('ww-leaders').setData({type: 'FeatureCollection', features: feats});
      if (!today.length) setTimeout(() => this.load(), 60000);
    } catch (e) { setTimeout(() => this.load(), 60000); }
  },
  paint(map, dark) {
    const c = this.color[+dark];
    map.setPaintProperty('ww-leaders', 'circle-color', dark ? '#1c1c1e' : '#ffffff');
    map.setPaintProperty('ww-leaders', 'circle-stroke-color', c);
    map.setPaintProperty('ww-leaders-line', 'line-color', c);
    map.setPaintProperty('ww-leaders-label', 'text-color', dark ? '#e5e5ea' : '#3a3a3c');
    map.setPaintProperty('ww-leaders-label', 'text-halo-color', dark ? '#1c1c1e' : '#ffffff');
  },
  onData() {}, render() {},
  count: () => today.length,
  rows: () => today.filter(t => t.abroad).map(t => ({
    id: 'todayp:' + t.place.place, time: t.place.last, badge: '★', title: `${t.name} reported in ${t.place.place.split(',')[0]}`,
    thumb: img(t.articles.find(a => a.image)?.image), meta: `${t.role}, ${t.country} · ${t.place.outlets} outlets`})),
  owns: id => String(id).startsWith('todayp:'),
  locate(id) { const t = today.find(x => 'todayp:' + x.place.place === id); return t && [t.place.lon, t.place.lat]; },
  ring: () => 13,
  act(name) { if (name.startsWith('profile:')) openProfile(name.slice(8)); },
  detail(id) {
    const here = today.filter(x => 'todayp:' + x.place.place === id);
    if (!here.length) return null;
    if (here.length > 1) return `<p class="eyebrow">Leaders in the news · last ${todayInfo?.window_h || 6} hours</p>
      <h2>${esc(here[0].place.place.split(',')[0])}</h2><p class="where">${here.length} leaders reported here</p>
      ${here.map(t => `<section class="pz"><h3>${esc(t.name)}</h3><p class="soft">${esc(t.role)}, ${esc(t.country)} · ${t.place.headlines} headlines, ${t.place.outlets} outlets${t.abroad ? ' · outside their country' : ''}</p>
        ${t.articles[0] ? `<p><a class="link" href="${esc(t.articles[0].url)}" target="_blank" rel="noopener">${esc(t.articles[0].title)}</a></p>` : ''}
        <button class="btn" data-act="profile:${esc(t.qid)}">Open the full profile</button></section>`).join('')}
      <p class="source">Source: GDELT news of the last ${todayInfo?.window_h || 6} hours. Each article's place is the city mentioned nearest to the leader's name. Where the news reported them, not where they are.</p>`;
    const t = here[0];
    const abroad = t.abroad;
    return `<p class="eyebrow">Leader in the news · last ${todayInfo?.window_h || 6} hours</p>
      <h2>${esc(t.name)}</h2>
      <p class="where">${esc(t.role)}, ${esc(t.country)}</p>
      <dl>
        <dt>Reported at</dt><dd>${esc(t.place.place)} <span class="soft">· ${t.place.headlines} different headlines, ${t.place.outlets} outlets${abroad ? ' · outside their country' : ''}</span></dd>
        ${t.places.length > 1 ? `<dt>Also placed at</dt><dd>${t.places.slice(1).map(p => `${esc(p.place.split(',')[0])} <span class="soft">(${p.outlets})</span>`).join(', ')}</dd>` : ''}
        <dt>Articles naming them</dt><dd>${t.outlets} outlets</dd>
      </dl>
      <button class="btn" data-act="profile:${esc(t.qid)}">Open the dossier</button> ${countryBtn({name: t.country}, 'Dossier of ' + esc(t.country))}
      <ol class="stories">${t.articles.map(a => `<li>${a.image ? `<img src="${esc(img(a.image))}" alt="" loading="lazy" onerror="this.remove()">` : ''}<span class="st">
        <a href="${esc(a.url)}" target="_blank" rel="noopener">${esc(a.title)}</a><span class="by">${esc(a.outlet)} · ${esc(a.place.split(',')[0])} · ${ago(a.time)}</span></span></li>`).join('')}</ol>
      <p class="source">Source: GDELT news of the last ${todayInfo?.window_h || 6} hours and Wikidata's list of current leaders. An article counts when GDELT found the leader's name in it; its place is the city mentioned nearest to the name in the text (GDELT records where each name and place appears). Copies of one agency story count as one headline, and a place needs two different headlines. So this is where the news reported them, not where they are, and it can still be wrong when a name and a city sit close together by chance.</p>`;
  },
};
