// The country dossier: everything our feeds hold about one country right now, plus its basic record from Wikidata.
// Opened from "Find a person or country", from the "Country dossier" button in cards, and from flags in a person
// dossier. Counts and lists only; no scores. Each block names its feed and that feed's age. There is no history
// store, so "what changed since yesterday" is not shown and the page says so.
import {ago, esc, local, spyPass} from './util.js';
import {flagMark} from './flags.js';
import {img} from './news.js';
import {shell, live, closeBtn, day, big, feedAge, tile, showOn, block, openProfile} from './profile.js';

let list = null, loadingList = null;
export function loadCountries() {
  if (!loadingList) loadingList = fetch('/api/dossier/countries').then(r => r.json()).then(d => { list = d.countries || []; }).catch(() => { loadingList = null; });
  return loadingList;
}
const fold = s => s.normalize('NFKD').replace(/[̀-ͯ]/g, '').toLowerCase();
// Countries whose name starts with (or has a word starting with) what was typed; for the search box.
export function countryMatches(q, max = 3) {
  if (!list) { loadCountries(); return []; }
  q = fold(q.trim());
  if (q.length < 2) return [];
  const code = q.toUpperCase();
  const score = c => (c.codes || []).includes(code) ? 0 : Math.min(...c.names.map(n => { n = fold(n); return n === q ? 0 : n.startsWith(q) ? 1 : n.split(/[\s(.]+/).some(w => w.startsWith(q)) ? 2 : 9; }));
  return list.map(c => [score(c), c]).filter(([s]) => s < 9).sort((a, b) => a[0] - b[0] || a[1].name.localeCompare(b[1].name)).slice(0, max).map(([, c]) => c);
}

document.addEventListener('click', e => {
  const b = e.target.closest('[data-dossier]'); if (!b) return;
  e.preventDefault();
  try { openCountry(JSON.parse(b.dataset.dossier)); } catch (err) { /* malformed button */ }
});

const KIND = {protest: 'Protest', riot: 'Riot', attack: 'Attack', clash: 'Armed clash', 'mass violence': 'Mass violence'};
const US_LEVEL = ['', 'Exercise normal precautions', 'Exercise increased caution', 'Reconsider travel', 'Do not travel'];
const plural = (n, one, many = one + 's') => `${n.toLocaleString('en-GB')} ${n === 1 ? one : many}`;
const stamp = t => t ? new Date(t * 1000).toISOString().slice(0, 10) : '';

export async function openCountry(o) {
  const {card, token} = shell('Country dossier');
  card.innerHTML = closeBtn + '<div class="prof-loading">Putting the country dossier together from our feeds…</div>';
  try {
    const r = await fetch('/api/dossier/country?' + new URLSearchParams(o), {cache: 'no-store'});
    const d = await r.json();
    if (!live(token)) return;
    if (!r.ok) { card.querySelector('.prof-loading').textContent = r.status === 404 ? 'That place is not in a country we know (it may be at sea or in a disputed area).' : d.error || 'Could not build the dossier.'; return; }
    render(card, d);
  } catch (e) { if (live(token)) card.querySelector('.prof-loading').textContent = 'Could not reach the server.'; }
}

function render(card, d) {
  const F = d.facts, f = d.feeds, g = d.geo, iso = d.iso;
  const cap = F?.capital?.[0], capAt = cap?.lat != null ? cap : null;
  const pop = F?.population ? `${big(+F.population.value)}${F.population.date ? ` <span class="soft">(${day(F.population.date)})</span>` : ''}`
    : g.pop ? `${big(g.pop)} <span class="soft">(Natural Earth estimate, ${g.pop_year})</span>` : '';
  const gov = F?.government?.map(x => esc(x.label)).join(', ');
  const heads = F ? [...(F.head_of_state || []).map(h => ({...h, role: 'Head of state'})), ...(F.head_of_government || []).map(h => ({...h, role: 'Head of government'}))] : (d.heads || []);
  const headsHtml = heads.length ? `<ul class="dos-heads">${heads.map(h => `<li><a href="#" data-person="${esc(h.qid)}"><b>${esc(h.label)}</b></a><span class="soft">${h.role}${h.since ? ' · since ' + day(h.since) : ''}</span></li>`).join('')}</ul>` : '';

  // travel advice, each office in its own words
  const us = d.travel.us, de = d.travel.de;
  const advice = [
    ...us.map(a => `<li><span class="lvl lvl${a.level}">${a.level}</span><span><b>US State Department:</b> Level ${a.level}, ${US_LEVEL[a.level].toLowerCase()}${us.length > 1 || a.area !== d.name ? ` <span class="soft">(${esc(a.area)})</span>` : ''}<br><span class="soft">issued ${stamp(a.issued)} · <a class="link" href="${esc(a.link)}" target="_blank" rel="noopener">read</a></span></span></li>`),
    ...de.map(a => `<li><span class="lvl ${a.kinds.length ? 'lvlw' : 'lvl1'}">${a.kinds.length ? '!' : '–'}</span><span><b>German Foreign Office:</b> ${a.kinds.length ? esc(a.kinds.join('; ')) : 'no warning, safety advice only'}<br><span class="soft">changed ${stamp(a.changed)} · <a class="link" href="${esc(a.link)}" target="_blank" rel="noopener">open data</a></span></span></li>`),
  ];

  const u = d.unrest, air = d.aircraft, sh = d.ships, nw = d.navwarn.items, q = d.quakes;
  const avoid = d.airspace.filter(a => a.level === 'avoid' || a.level === 'prohibited');
  const tiles = [
    tile('Protests and clashes, 24 h', plural(u.total, 'group'), u.total ? `${u.two_plus} reported by 2+ outlets · ${Object.entries(u.by_kind).map(([k, v]) => `${v.groups} ${(KIND[k] || k).toLowerCase()}`).join(', ')}` : 'none coded here', 'GDELT events · ' + feedAge(f.unrest), u.by_kind.clash || u.by_kind['mass violence'] ? 'hot' : ''),
    tile('Airspace warnings', d.airspace.length ? plural(d.airspace.length, 'warning') : 'None', d.airspace.length ? (avoid.length ? `${avoid.length} say do not fly (in part or all)` : 'caution only') : 'none from EASA or the FAA' + (iso === 'US' ? '' : ''), 'EASA, FAA · ' + feedAge(f.airspace), avoid.length ? 'warm' : ''),
    iso === 'US' ? tile('US flight restrictions', plural(d.tfrs.total, 'TFR'), esc(d.tfrs.kinds.slice(0, 4).join(', ').toLowerCase()), 'FAA TFR list · ' + feedAge(f.airspace)) : '',
    tile('Navy warnings near its coast', nw.length ? plural(nw.length, 'warning') : 'None', `within 300 km · from ${esc(d.navwarn.sources.join(' and ') || 'no source')}`, 'NGA, UKHO · ' + feedAge(f.navwarn) + (d.navwarn.problems.length ? ' · NGA not answering' : '')),
    tile('Internet outages, 24 h', d.outages.length ? plural(d.outages.length, 'signal') : 'None', d.outages.length ? 'country-level drops IODA measured' : 'no country-level signal', 'IODA · ' + feedAge(f.outages), d.outages.length ? 'warm' : ''),
    tile('Earthquakes, 24 h', q.total ? plural(q.total, 'quake') : 'None', q.total ? `strongest M${q.top[0].mag?.toFixed(1)} · in or within 100 km` : 'in or within 100 km', 'USGS · ' + feedAge(f.quakes), q.top[0]?.mag >= 5 ? 'warm' : ''),
    tile('Disaster alerts', d.hazards.length ? plural(d.hazards.length, 'alert') : 'None', d.hazards.length ? esc(d.hazards.map(h => h.kind.toLowerCase()).join(', ')) : 'none open', 'GDACS, NASA EONET · ' + feedAge(f.gdacs), d.hazards.some(h => /red|orange/i.test(h.level || '')) ? 'warm' : ''),
    tile('Government and VIP aircraft over it', air.vip_total ? plural(air.vip_total, 'aircraft', 'aircraft') : 'None seen', air.vip_total ? `${air.vip.filter(a => !a.ground).length} airborne` : 'none of the listed government or VIP aircraft', 'plane-alert-db + positions · ' + feedAge(f.aircraft_world), air.vip.some(a => a.layer === 'doomsday') ? 'hot' : ''),
    tile('Military aircraft over it', plural(air.military, 'aircraft', 'aircraft'), `${air.military_airborne} airborne · broadcasting only`, 'adsb.lol military list · ' + feedAge(f.aircraft_military)),
    tile('Warships near it', sh.warships_total + sh.carriers.length ? plural(sh.warships_total + sh.carriers.length, 'ship') : 'None seen', `${sh.carriers.length} US carriers or amphibs (USNI) · ${sh.warships_total} by AIS${sh.ais_world === 'off' ? ' (Baltic only: no world AIS key)' : ''}`, 'AIS, USNI Fleet Tracker · ' + feedAge(f.usni_fleet)),
    tile('Leaders reported here today', d.leaders_today.length ? plural(d.leaders_today.length, 'leader') : 'None', d.leaders_today.length ? esc(d.leaders_today.slice(0, 3).map(l => l.name).join(', ')) : 'no head of state or government placed here', 'GDELT, last 6 h · where news placed them'),
    tile('News, 6 h', plural(d.news.outlets, 'outlet'), `${plural(d.news.places, 'place')} in the country`, 'GDELT, all languages · ' + feedAge(f.news)),
  ].filter(Boolean).join('');

  const li = (main, sub, pick) => `<li>${main}${sub ? `<br><span class="soft">${sub}</span>` : ''}${pick ? ' · ' + pick : ''}</li>`;
  const now = [
    block('Protests and clashes', u.top.length ? `<ul class="dos-list">${u.top.map(x => li(`<b>${esc(KIND[x.cat] || x.cat)}</b>, ${esc(x.place.split(',')[0])}${x.title ? ` <span class="soft">· ${esc(x.title)}</span>` : ''}`,
      `${esc(x.action)} · ${plural(x.outlets, 'outlet')} · ${ago(x.last)}`, showOn(x.layer, x.id))).join('')}</ul>` : '', `GDELT Events, last 24 hours, by GDELT's own country code. Machine-coded from news, not verified; single-outlet groups included here.`),
    block('Airspace', d.airspace.length ? `<ul class="dos-list">${d.airspace.map(a => li(`<b>${esc(a.source)}${a.number ? ' ' + esc(a.number) : ''}</b> · ${a.level === 'avoid' ? 'do not operate (in part or all)' : a.level === 'prohibited' ? 'US flights prohibited or restricted' : esc(a.level || 'notice')}`,
      esc(a.affected || a.docs.join('; ') || a.title) + (a.valid_until ? ` · valid until ${esc(a.valid_until)}` : ''), a.pick ? showOn('airspace', a.pick) : '')).join('')}</ul>` : '', 'EASA conflict-zone bulletins and the FAA prohibitions page, matched by flight-region prefix or country name.'),
    block('Navy warnings', nw.length ? `<ul class="dos-list">${nw.map(w => li(`<b>${esc(w.ref)}</b> · ${esc(w.kind)} · ${w.km ? w.km + ' km off' : 'at the coast'}`, esc(w.text), showOn('navwarn', w.id))).join('')}</ul>` : '', ''),
    block('Internet', d.outages.length ? `<ul class="dos-list">${d.outages.map(o => li(`<b>${esc(o.signal)}</b> signal dropped`, `from ${local(o.start)} (${ago(o.start)}) for ${Math.round(o.duration_s / 3600)} h`, showOn('outages', o.id))).join('')}</ul>` : '', ''),
    block('Earthquakes and disasters', q.top.length || d.hazards.length ? `<ul class="dos-list">${q.top.map(x => li(`<b>M${x.mag?.toFixed(1)}</b> ${esc(x.place)}`, `${ago(x.time)} · depth ${Math.round(x.depth_km)} km${x.km ? ` · ${x.km} km outside` : ''}`, showOn('quakes', x.id))).join('')}${d.hazards.map(h => li(`<b>${esc(h.kind)}</b> ${esc(h.name)}`, `${esc(h.source)}${h.level ? ' · ' + esc(h.level) + ' alert' : ''}${h.severity ? ' · ' + esc(h.severity) : ''}`, showOn('hazards', h.id))).join('')}</ul>` : '', 'USGS quakes in or within 100 km of the outline; GDACS alerts naming the country; EONET events in it.'),
  ].join('');

  const who = [
    block('Aircraft over it now', air.vip.length || air.military_top.length ? `<ul class="dos-list">${air.vip.map(a => li(`<b>${esc(a.reg || a.hex)}</b> ${a.layer === 'doomsday' ? '<span class="tag hot">doomsday plane</span>' : ''} <span class="soft">· ${esc(a.type || '')}</span>`,
      `${esc(a.operator || '')}${a.tags?.length ? ' · tagged ' + esc(a.tags.slice(0, 2).join(', ')) : ''} · ${a.ground ? 'on the ground' : 'airborne'}, ${ago(a.time)}`, showOn(a.layer, a.hex))).join('')}
      ${air.military_top.map(a => li(`<b>${esc(a.flight || a.hex)}</b> <span class="soft">· military</span>`, `${a.ground ? 'on the ground' : 'airborne' + (a.alt_ft ? ' at ' + a.alt_ft.toLocaleString('en-GB') + ' ft' : '')}, ${ago(a.time)}`, showOn('military', a.hex))).join('')}</ul>` : '',
      'Inside the outline now, from adsb.lol, adsb.fi and OpenSky (world positions can be 20 minutes old). Only aircraft that broadcast their position appear; many military flights do not.'),
    block('Warships near it', sh.warships.length || sh.carriers.length ? `<ul class="dos-list">${sh.carriers.map(s => li(`<b>${esc(s.name)}</b> (${esc(s.hull)}) <span class="soft">· ${esc(s.kind)}</span>`, `${esc(s.port || s.region || '')} · placed ${s.placed === 'port' ? 'at its port' : 'by region, approximate'}${s.km ? ` · about ${s.km} km away` : ''} · USNI ${stamp(sh.usni_published)}`, showOn('warships', s.id))).join('')}
      ${sh.warships.map(s => li(`<b>${esc(s.name || 'Unnamed')}</b> <span class="soft">· AIS military vessel</span>`, `${s.km ? s.km + ' km off' : 'in its waters'} · ${ago(s.time)}`, showOn('warships', s.id))).join('')}</ul>` : '',
      `AIS ships of type "military" within 200 km; US carriers and amphibious ships from USNI's Fleet Tracker within 600 km${sh.usni_published ? ` (edition of ${stamp(sh.usni_published)}, ${ago(sh.usni_published)})` : ''}. Warships often switch AIS off.`),
    block('Leaders reported here', d.leaders_today.length ? `<ul class="dos-list">${d.leaders_today.map(l => li(`<a href="#" data-person="${esc(l.qid)}"><b>${esc(l.name)}</b></a> <span class="soft">· ${esc(l.role)}, ${esc(l.country)}</span>`, `${esc(l.place.split(',')[0])} · ${l.headlines} headlines, ${l.outlets} outlets`, showOn('leaders', 'today:' + l.qid))).join('')}</ul>` : '', 'Where the last 6 hours of news placed heads of state and government; not where they are.'),
  ].join('');

  const news = d.news.top.length ? `<ol class="stories dos-news">${d.news.top.map(p => { const a = p.articles[0], pic = p.articles.find(x => x.image); return `<li>${pic ? `<img src="${esc(img(pic.image))}" alt="" loading="lazy" onerror="this.remove()">` : ''}<span class="st">
      <a href="${esc(a.url)}" target="_blank" rel="noopener">${esc(a.title)}</a><span class="by"><b>${esc(p.place.split(',')[0])}</b> · ${plural(p.outlets, 'outlet')} · ${esc(a.outlet)} · ${ago(p.last)}${a.lang !== 'eng' && !a.translated ? ' · not in English' : ''} · ${showOn('news', p.place)}</span></span></li>`; }).join('')}</ol>` : '';

  const above = (capAt || g.label) ? `<div class="dos-above">${spyPass(capAt ? capAt.lat : g.label[1], capAt ? capAt.lon : g.label[0]).replace(' id="spypass"', '')}
      <p class="source">Over ${capAt ? 'the capital, ' + esc(cap.label) : 'the middle of the country (no capital position from Wikidata)'}, computed in this browser from public orbits.</p></div>` : '';
  const maxar = d.maxar.length ? `<ul class="dos-list">${d.maxar.map(m => li(`<b>${esc(m.title)}</b>`, `${(m.start || '').slice(0, 10)} – ${(m.end || '').slice(0, 10)} · ${plural(m.acquisitions || 0, 'satellite pass', 'satellite passes')}`, showOn('maxar', m.id, 'Open the pictures'))).join('')}</ul>` : '<p class="soft">Maxar has published no free disaster imagery for this country.</p>';

  const extra = [
    ['Official languages', F?.languages?.map(x => esc(x.label)).join(', ')],
    ['Currency', F?.currency?.map(x => esc(x.label)).join(', ')],
    ['Area', F?.area ? `${big(+F.area.value)} ${F.area.unit === 'square kilometre' ? 'km²' : esc(F.area.unit || '')}` : ''],
    ['GDP (nominal)', F?.gdp ? `${big(+F.gdp.value)} ${F.gdp.unit === 'United States dollar' ? 'US dollars' : esc(F.gdp.unit || '')}${F.gdp.date ? ` <span class="soft">(${day(F.gdp.date)})</span>` : ''}` : ''],
    ['Member of', F?.member_of?.length ? `<span class="dos-fold">${F.member_of.slice(0, 8).map(x => esc(x.label)).join(', ')}${F.member_of.length > 8 ? ` <a href="#" class="link" data-more>and ${F.member_of.length - 8} more</a><span class="fold-rest">, ${F.member_of.slice(8).map(x => esc(x.label)).join(', ')}</span>` : ''}</span>` : ''],
    ['Codes', `ISO ${esc(iso)}${g.iso3 ? ' / ' + esc(g.iso3) : ''}${g.fips?.length ? ` · FIPS ${esc(g.fips.join(', '))} (GDELT, US government)` : ''}`],
  ].filter(x => x[1]);

  card.innerHTML = closeBtn + `
    <header class="dos-head">
      <div class="dos-face flagbox">${flagMark(iso, d.name) || ''}</div>
      <div class="dos-id">
        <p class="dos-eyebrow">Country dossier · ${esc(g.region || g.continent || '')}</p>
        <h2>${esc(d.name)}</h2>
        <p class="dos-sub">${[cap && `Capital <b>${esc(cap.label)}</b>`, pop && `Population ${pop}`, gov && esc(F.government.map(x => x.label).join(', '))].filter(Boolean).join(' · ')}</p>
        ${headsHtml}
      </div>
    </header>
    ${advice.length ? `<ul class="dos-advice">${advice.join('')}</ul>` : '<p class="soft">Neither the US State Department nor the German Foreign Office lists travel advice for this country.</p>'}
    <section class="dos-signals"><h3>Right now</h3><div class="sig-grid">${tiles}</div></section>
    <div class="dos-cols">${now}${who}</div>
    ${block('In the news, last 6 hours', news, `The places in ${esc(d.name)} with the most outlets, from GDELT's English and translated files; one headline each.`)}
    <div class="dos-cols">
      ${block('From above', above + maxar, 'Spy passes: military imaging, radar and signals satellites in low orbit above 30° over the point in the last 24 hours (could have looked, not that it did). Maxar: free disaster imagery whose area lies in the country.')}
      ${block('Record', `<dl class="dos-facts">${extra.map(([k, v]) => `<dt>${k}</dt><dd>${v}</dd>`).join('')}</dl>`, d.facts ? `Wikidata${d.facts.via ? ', read from ' + esc(d.facts.via) : ''}, current statements only; fetched ${ago(d.facts_fetched)}, kept 30 days.` : `Wikidata could not be asked: ${esc(d.facts_problem || 'unknown')}. Population here is Natural Earth's estimate${d.heads?.length ? '; leaders from the cached Wikidata leaders list' : ''}.`)}
    </div>
    <p class="source dos-foot">What changed since yesterday is not shown: World Watch keeps no history yet, only what each feed holds now.
      Countries are matched to items by the source's own code (GDELT FIPS, IODA ISO, flight-region prefix), by name (GDACS, FAA, EASA), or by position inside Natural Earth's 1:50m outline (accurate to a few km; coastal places get 25 km of slack).
      Read ${ago(d.now)}. Travel advice: ${feedAge(f.travel_advice)}.</p>`;
}
