// Protests and clashes from GDELT's machine coding of news (last 24 hours). Each marker is one kind of event at one
// place on one day, grouped from every article GDELT coded that way; the number is how many different outlets wrote
// about it. Protests are drawn as rings, violent events as filled dots, each with a letter (no meaning by colour alone).
// Groups seen by one outlet only live in a second chip, off by default: those are where false alarms gather.
import {ago, esc, local, skyShot, utc, spyPass, countryBtn} from './util.js';
import {img} from './news.js';
import {eyeOn, eyeImages, eyeSwap, setEyeOpacity} from './eyeicons.js';

// God's eye: one symbol per CAMEO action as GDELT words it (the icon set's conflict group); the category when the
// action is not in the table
const ACT_EYE = {'use of conventional military force': 'clash', 'fighting with small arms': 'smallarms', 'fighting with small arms and light weapons': 'smallarms',
  'fighting with artillery and tanks': 'artillery', 'aerial weapons (air strike, drone)': 'aerial', 'occupation of territory': 'occupy',
  'blockade or restricted movement': 'blockade', 'physical assault': 'attack', 'killing by physical assault': 'attack', 'sexual assault': 'attack', 'torture': 'attack',
  'unconventional violence': 'attack', 'bombing': 'bombing', 'abduction or hijacking': 'abduct', 'assassination': 'assassin', 'mass killings': 'mass',
  'demonstration or rally': 'protest', 'protest': 'protest', 'strike or boycott': 'strike', 'blockade or obstruction': 'obstruct', 'violent protest or riot': 'riot'};
const CAT_EYE = {protest: 'protest', riot: 'riot', attack: 'attack', clash: 'clash', 'mass violence': 'mass'};
const eyeOf = g => 'eye-' + (ACT_EYE[g.action] || CAT_EYE[g.cat] || 'clash');

const KIND = {protest: ['P', 'Protest'], riot: ['R', 'Riot'], attack: ['A', 'Attack'], clash: ['C', 'Armed clash'], 'mass violence': ['M', 'Mass violence']};
let groups = [], info = null;

// An article we have no headline for is shown by the words in its address, and says so.
const slug = u => { try { const p = new URL(u).pathname.split('/').filter(Boolean).sort((a, b) => b.length - a.length)[0] || ''; return p.replace(/\.[a-z]+$/, '').replace(/[-_]+/g, ' ').replace(/\b\d{5,}\b/g, '').trim(); } catch (e) { return ''; } };

function make(single) {
  const SRC = single ? 'ww-unrest1' : 'ww-unrest', mine = () => groups.filter(g => single ? g.outlets < 2 : g.outlets >= 2);
  return {
    id: single ? 'unrest1' : 'unrest', title: single ? 'Unrest, one outlet' : 'Protests and clashes', color: ['#a2845e', '#ac8e68'],
    feeds: {unrest: 120}, layers: [SRC + '-dot', SRC + '-label', SRC + '-eye'], defaultOff: single,
    about: () => single ? 'Events only one outlet reported. Most false alarms are here.' : 'Machine-coded from news by GDELT; reported by two or more outlets.',

    addTo(map) {
      map.addSource(SRC, {type: 'geojson', data: {type: 'FeatureCollection', features: []}});
      const size = ['interpolate', ['linear'], ['sqrt', ['get', 'n']], 1, 7, 3, 9, 6, 13, 12, 20];
      map.addLayer({id: SRC + '-dot', type: 'circle', source: SRC, layout: {'circle-sort-key': ['get', 'n']},
        paint: {'circle-radius': size, 'circle-stroke-width': ['case', ['==', ['get', 'ring'], true], 2.5, 1.2], 'circle-opacity': single ? 0.55 : 0.92, 'circle-stroke-opacity': single ? 0.7 : 1}});
      map.addLayer({id: SRC + '-label', type: 'symbol', source: SRC,
        layout: {'text-field': ['get', 'k'], 'text-font': ['Noto Sans Bold'], 'text-size': 10, 'text-allow-overlap': true, 'text-ignore-placement': true}});
      // God's eye symbols, sized by the number of outlets like the dots (shown instead of dot and letter in that theme)
      map.addLayer({id: SRC + '-eye', type: 'symbol', source: SRC, layout: {'icon-image': ['get', 'eye'], 'symbol-sort-key': ['get', 'n'],
        'icon-size': ['interpolate', ['linear'], ['sqrt', ['get', 'n']], 1, 0.42, 3, 0.52, 6, 0.7, 12, 0.95], 'icon-allow-overlap': true, 'icon-ignore-placement': true},
        paint: {'icon-opacity': single ? 0.6 : 1}});
      setEyeOpacity(SRC + '-eye', single ? 0.6 : 1);
    },
    paint(map, dark) {
      const c = this.color[+dark], bg = dark ? '#1c1c1e' : '#ffffff';
      map.setPaintProperty(SRC + '-dot', 'circle-color', ['case', ['==', ['get', 'ring'], true], bg, c]);
      map.setPaintProperty(SRC + '-dot', 'circle-stroke-color', ['case', ['==', ['get', 'ring'], true], c, bg]);
      map.setPaintProperty(SRC + '-label', 'text-color', ['case', ['==', ['get', 'ring'], true], c, '#ffffff']);
      eyeImages(map, dark);
      eyeSwap(map, [SRC + '-eye'], [SRC + '-dot', SRC + '-label']);
    },
    onData(feed, d) { groups = d.payload.groups || []; info = d; },
    render(map) {
      map.getSource(SRC).setData({type: 'FeatureCollection', features: mine().map(g => (
        {type: 'Feature', geometry: {type: 'Point', coordinates: [g.lon, g.lat]},
         properties: {id: g.id, n: g.outlets, k: KIND[g.cat]?.[0] || '?', ring: g.cat === 'protest', eye: eyeOf(g)}}))});
    },
    count: () => mine().length,
    owns: id => mine().some(g => g.id === id),     // hotspot links pick through this
    rows() {
      if (single) return [];
      return mine().filter(g => g.outlets >= 3).map(g => {
        const a = g.articles.find(x => x.title);
        return {id: g.id, time: g.last, order: g.outlets, badge: KIND[g.cat]?.[0] || '?', strong: g.cat !== 'protest',
          title: `${KIND[g.cat]?.[1] || g.cat}: ${g.place.split(',')[0]}${a ? ' · ' + a.title : ''}`, thumb: img(g.articles.find(x => x.image)?.image),
          meta: `${g.action} · ${g.outlets} outlets · ${local(g.last)}`};
      });
    },
    locate(id) { const g = groups.find(x => x.id === id); return g && [g.lon, g.lat]; },
    ring(id) { const g = groups.find(x => x.id === id); return g ? 10 + Math.sqrt(g.outlets) * 2.6 : 14; },
    detail(id) {
      const g = groups.find(x => x.id === id);
      if (!g) return null;
      const hero = g.articles.find(a => a.image);
      const acts = Object.entries(g.actions).sort((a, b) => b[1] - a[1]);
      const day = `${g.day.slice(0, 4)}-${g.day.slice(4, 6)}-${g.day.slice(6, 8)}`;
      return `<p class="eyebrow">${esc(KIND[g.cat]?.[1] || g.cat)} · reported, not verified</p>
        <h2>${esc(g.place.split(',')[0])}</h2>
        <p class="where">${esc(g.place.split(',').slice(1).join(',').trim())} · ${g.outlets} ${g.outlets === 1 ? 'outlet' : 'outlets'} · ${day} (UTC)</p>
        ${hero ? `<img class="news-hero" src="${esc(img(hero.image))}" alt="" onerror="this.remove()">` : ''}
        <dl>
          <dt>Coded as</dt><dd>${acts.map(([a, n]) => `${esc(a)}${acts.length > 1 ? ` <span class="soft">×${n}</span>` : ''}`).join('<br>')}</dd>
          ${g.actors.length ? `<dt>Named in the coding</dt><dd>${g.actors.map(esc).join(', ')}</dd>` : ''}
          <dt>In GDELT's files</dt><dd>${local(g.first)} – ${local(g.last)} <span class="soft">(${ago(g.last)})</span></dd>
        </dl>
        ${g.country ? countryBtn({fips: g.country}) : ''}
        ${skyShot(g.lat, g.lon)}
        ${spyPass(g.lat, g.lon)}
        <ol class="stories">${g.articles.map(a => `<li>${a.image ? `<img src="${esc(img(a.image))}" alt="" loading="lazy" onerror="this.remove()">` : ''}<span class="st">
          <a href="${esc(a.url)}" target="_blank" rel="noopener">${esc(a.title || slug(a.url) || a.url)}</a>
          <span class="by">${esc(a.outlet)} · ${ago(a.time)}${a.title ? '' : ' · headline not available, words from the address'}</span></span></li>`).join('')}</ol>
        ${g.outlets > g.articles.length ? `<p class="source">Showing ${g.articles.length} of ${g.outlets} outlets.</p>` : ''}
        <p class="source">Source: GDELT Events 2.0, ${info?.payload.files ?? '?'} event files and ${info?.payload.mention_files ?? '?'} mention files of the last 24 hours; fetched ${ago(info?.fetched)}. GDELT's software reads articles and codes who did what where (the CAMEO scheme). That is automatic and makes mistakes: a figure of speech can be coded as violence, and the place can be where a story was written rather than where it happened. To cut false alarms, only each article's leading event, city-level places and armed actors (for the vague military codes) are kept, sports and entertainment pages are left out, a group is dropped when every article we can match is, by GDELT's own topic tags, about something else${g.themes_checked ? ` (${g.themes_checked} of these articles checked)` : ''}, and one outlet alone is not enough to show it by default. Open the articles before relying on it.</p>`;
    },
  };
}

export const unrest = make(false), unrestSingle = make(true);
