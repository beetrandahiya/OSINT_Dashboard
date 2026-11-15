// The person dossier: one full-page overlay for a public figure. Opened from the People layer, People search, the
// leaders card, a country dossier, and (for a confirmed identity) the lookup page.
// Two parts, loaded separately: the record (Wikidata, Wikipedia, OpenSanctions; cached a day by the server) and the
// live signals (our own feeds right now: news, leaders today, listed aircraft, the home country). Every block says
// where it comes from. The overlay shell is shared with the country dossier (dossier_country.js).
import {$, ago, esc, local} from './util.js';
import {flagMark} from './flags.js';
import {img} from './news.js';
import './dossier_country.js';   // listens for "Country dossier" buttons and flags, also on the lookup page

let host = null, token = 0;

// ---- the shared overlay ----
export function shell(label) {
  if (!host) {
    host = document.createElement('div');
    host.id = 'profile';
    host.hidden = true;
    host.innerHTML = '<div class="prof-scrim"></div><section class="glass prof-card dos" role="dialog"></section>';
    document.body.appendChild(host);
    host.querySelector('.prof-scrim').onclick = closeShell;
    addEventListener('keydown', e => { if (e.key === 'Escape' && !host.hidden) closeShell(); });
    host.addEventListener('click', e => {
      if (e.target.closest('.dos-close')) return closeShell();
      const p = e.target.closest('[data-pick-layer]');          // "show on the map": close and select it there
      if (p) { e.preventDefault(); closeShell(); dispatchEvent(new CustomEvent('ww-pick', {detail: {layer: p.dataset.pickLayer, id: p.dataset.pickId}})); return; }
      const q = e.target.closest('[data-person]');
      if (q) { e.preventDefault(); openProfile(q.dataset.person); return; }
      const more = e.target.closest('[data-more]');
      if (more) { e.preventDefault(); const box = more.parentElement; box.classList.add('open'); more.remove(); }
    });
  }
  host.hidden = false;
  const card = host.querySelector('.prof-card');
  card.setAttribute('aria-label', label);
  card.scrollTop = 0;
  return {card, token: ++token};
}
export const live = t => t === token && host && !host.hidden;
export function closeShell() { if (host) host.hidden = true; token++; }
export const closeBtn = '<button class="close dos-close" aria-label="Close"></button>';

// ---- small formatting helpers, shared ----
const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
// Wikidata dates carry their precision as zeros: 2020-06-00 is "June 2020", 1946-00-00 is "1946".
export function day(s) {
  if (!s) return '';
  const [y, m, d] = s.split('-');
  if (!m || m === '00') return String(+y);
  return (d && d !== '00' ? +d + ' ' : '') + MONTHS[+m - 1] + ' ' + (+y);
}
export const year = s => s ? String(+s.slice(0, 4)) : '?';
export function big(n, unit = '') {
  if (n == null) return '';
  const a = Math.abs(n), f = (v, s) => (v >= 100 ? Math.round(v) : v.toFixed(1).replace(/\.0$/, '')) + s;
  return (a >= 1e12 ? f(n / 1e12, ' trillion') : a >= 1e9 ? f(n / 1e9, ' billion') : a >= 1e6 ? f(n / 1e6, ' million') : Math.round(n).toLocaleString('en-GB')) + unit;
}
export function feedAge(m) {
  if (!m) return 'not loaded';
  if (m.state === 'missing') return 'feed missing';
  const t = m.data_time || m.fetched;
  return (m.data_label && !m.data_time ? m.data_label + ', fetched ' + ago(m.fetched) : t ? 'data ' + ago(t) : 'not fetched yet') + (m.state === 'failing' ? ' · failing' : m.state === 'late' ? ' · late' : '');
}
// One signal tile: a label, the value, a line of context and its source with age.
export function tile(label, value, sub, src, tone = '') {
  return `<div class="sig${tone ? ' ' + tone : ''}"><span class="sig-k">${label}</span><span class="sig-v">${value}</span>${sub ? `<span class="sig-s">${sub}</span>` : ''}<span class="sig-src">${src}</span></div>`;
}
export const showOn = (layer, id, text = 'Show on map') => `<a href="#" class="dos-show" data-pick-layer="${esc(layer)}" data-pick-id="${esc(id)}">${text}</a>`;
export function block(title, body, source, cls = '') {
  return body ? `<section class="dos-block ${cls}"><h3>${title}</h3>${body}${source ? `<p class="source">${source}</p>` : ''}</section>` : '';
}

// ---- the person dossier ----
export async function openProfile(qid) {
  const {card, token: t} = shell('Person dossier');
  card.innerHTML = closeBtn + '<div class="prof-loading">Building the dossier from public records…</div>';
  try {
    const r = await fetch('/api/people/profile/' + encodeURIComponent(qid), {cache: 'no-store'});
    const d = await r.json();
    if (!live(t)) return;
    if (!r.ok) { card.querySelector('.prof-loading').textContent = d.error || 'Could not build the dossier.'; return; }
    render(card, d);
    signals(d, t);
  } catch (e) { if (live(t)) card.querySelector('.prof-loading').textContent = 'Could not reach the server.'; }
}

const yearsOld = born => born && /^\d{4}-\d\d-\d\d$/.test(born) && !born.endsWith('-00') ? Math.floor((Date.now() - Date.parse(born)) / 3.156e10) : null;
const named = a => a.filter(i => !/^Q\d+$/.test(i.name ?? i));
// The highest offices first: a head of state before a party post.
const TOP = /prime minister|president|chancellor|king|queen|monarch|emperor|emir|sultan|supreme leader|chief minister|premier|governor|mayor|chief executive|chair/i;
// Wikipedia's first two or three sentences, the rest behind "Read more".
function intro(text) {
  if (!text) return '';
  const para = text.split('\n')[0], parts = para.split(/(?<=[.!?])\s+(?=[A-Z"“(])/);
  let short = '', n = 0;
  for (const s of parts) { if (n >= 3 || (n >= 2 && short.length > 260)) break; short += (short ? ' ' : '') + s; n++; }
  const rest = text.slice(short.length).trim();
  return `<div class="dos-intro${rest ? '' : ' open'}"><p>${esc(short)}</p>${rest ? `<div class="dos-rest">${rest.split('\n').filter(Boolean).map(p => `<p>${esc(p)}</p>`).join('')}</div><a href="#" class="link" data-more>Read more</a>` : ''}</div>`;
}
const listOf = (a, max) => { a = named(a); return a.length ? a.slice(0, max).map(esc).join(', ') + (a.length > max ? ` <span class="soft">and ${a.length - max} more</span>` : '') : ''; };

function render(card, d) {
  const roles = (d.current_roles.length ? d.current_roles : []).filter(r => !/^Q\d+$/.test(r.name)).slice().sort((a, b) => TOP.test(b.name) - TOP.test(a.name));
  const past = d.positions.filter(p => p.end && !/^Q\d+$/.test(p.name));
  const age = d.died ? null : yearsOld(d.born);
  const flags = (d.citizenship || []).filter(c => c.iso).map(c => `<a href="#" class="dos-flag" data-dossier="${esc(JSON.stringify({cc: c.iso}))}" title="${esc(c.name)} country dossier">${flagMark(c.iso, c.name)}</a>`).join('');
  const of = name => d.ties.filter(t => t.label === name).map(t => t.name);
  const roleLine = r => `<li><b>${esc(r.name)}</b>${r.of ? ` <span class="soft">of ${esc(r.of)}</span>` : ''}${r.start ? `<span class="soft"> · since ${day(r.start)}</span>` : ''}</li>`;

  const worth = d.net_worth && `${big(d.net_worth.amount)} ${esc(d.net_worth.unit === 'United States dollar' ? 'US dollars' : d.net_worth.unit || '')}${d.net_worth.date ? ` <span class="soft">(as of ${day(d.net_worth.date)})</span>` : ''}`;
  const accounts = [d.official_website && `<a class="link" href="${esc(d.official_website)}" target="_blank" rel="noopener">Official site</a>`,
    ...Object.entries(d.socials).map(([k, v]) => `<a class="link" href="${esc(v)}" target="_blank" rel="noopener">${esc(k.replace(/\.com.*$/, '').replace(/^x$/, 'X'))}</a>`)].filter(Boolean).join(' · ');
  const facts = [
    ['Born', d.born ? `${day(d.born)}${d.birthplace?.length && !/^Q\d+$/.test(d.birthplace[0]) ? ', ' + esc(d.birthplace[0]) : ''}` : ''],
    d.died && ['Died', day(d.died)],
    ['Nationality', named((d.citizenship || []).map(c => c.name)).map(esc).join(', ')],
    ['Party', listOf(d.identity.filter(i => i.label === 'party' && !i.end).map(i => i.name), 3)],
    ['Education', listOf(d.background.filter(b => b.label === 'educated at').map(b => b.name), 4)],
    ['Spouse', named(d.ties.filter(t => t.label === 'spouse')).sort((a, b) => !!a.end - !!b.end).map(t => esc(t.name) + (t.end ? ` <span class="soft">(until ${year(t.end)})</span>` : '')).join(', ')],
    ['Children', listOf(of('child'), 6)],
    ['Parents', listOf([...of('father'), ...of('mother')], 2)],
    ['Languages', listOf(d.languages || [], 6)],
    ['Religion', listOf(d.religion || [], 3)],
    ['Net worth', worth],
    ['Official accounts', accounts],
  ].filter(f => f && f[1]);

  const holdings = named(d.holdings.filter(h => ['founded', 'owned by them', 'chief executive of', 'chair of', 'owns', 'parent org of'].includes(h.label)));
  const members = named(d.ties.filter(t => t.label === 'member of'));
  const awards = named(d.background.filter(b => b.label === 'award'));

  card.innerHTML = closeBtn + `
    <header class="dos-head">
      ${d.image ? `<img class="dos-face" src="${esc(d.image)}" alt="" referrerpolicy="no-referrer">` : '<div class="dos-face blank"></div>'}
      <div class="dos-id">
        <p class="dos-eyebrow">Person dossier · public record</p>
        <h2>${esc(d.name)} ${flags}</h2>
        ${roles.length ? `<ul class="dos-roles">${roles.slice(0, 3).map(roleLine).join('')}${roles.length > 3 ? `<li class="soft">and ${roles.length - 3} more current posts</li>` : ''}</ul>` : '<p class="soft">No current office recorded in Wikidata.</p>'}
        <p class="dos-sub">${[age != null ? `Age ${age}` : null, d.died ? `Died ${day(d.died)}` : null, `<a class="link" href="${esc(d.wikidata)}" target="_blank" rel="noopener">Wikidata ${esc(d.qid)}</a>`, d.wikipedia && `<a class="link" href="${esc(d.wikipedia)}" target="_blank" rel="noopener">Wikipedia</a>`].filter(Boolean).join(' · ')}</p>
      </div>
    </header>
    <section class="dos-signals" id="dos-signals"><h3>Signals</h3><p class="soft">Reading our live feeds…</p></section>
    ${intro(d.intro)}
    <div class="dos-cols">
      ${block('Record', `<dl class="dos-facts">${facts.map(([k, v]) => `<dt>${k}</dt><dd>${v}</dd>`).join('')}</dl>`, 'Wikidata, as it stands; what it does not record is left out.')}
      ${block('Offices', (roles.length ? `<ul class="dos-list">${roles.map(roleLine).join('')}</ul>` : '<p class="soft">None current.</p>') +
        (past.length ? `<div class="dos-fold"><a href="#" class="link" data-more>${past.length} earlier ${past.length === 1 ? 'office' : 'offices'}</a><ol class="tl fold-rest">${past.map(p => `<li><span class="tl-when">${year(p.start)}–${year(p.end)}</span><span class="tl-what">${esc(p.name)}${p.of ? ` <span class="soft">· ${esc(p.of)}</span>` : ''}</span></li>`).join('')}</ol></div>` : ''),
        'Wikidata, with the dates it records.')}
      ${block('Companies and organisations', holdings.length ? `<ul class="dos-list">${holdings.slice(0, 12).map(h => `<li>${esc(h.name)} <span class="soft">· ${esc(h.label)}</span></li>`).join('')}</ul>` : '', 'Ownership, founding and board roles from Wikidata; far from complete.')}
      ${block('Member of', members.length ? listOf(members.map(m => m.name), 10) : '', 'Wikidata.')}
      ${block('Honours', awards.length ? listOf(awards.map(a => a.name), 8) : '', 'Wikidata.')}
    </div>
    ${d.problems.length ? `<p class="source prof-problems">Could not be loaded: ${d.problems.map(esc).join('; ')}.</p>` : ''}
    <p class="source">Record built ${ago(d.built)} from Wikidata, Wikipedia${d.sanctions.length ? ', OpenSanctions' : ''} and GDELT, cached a day; signals are read from this server's feeds now. This is who a person is and what the record shows, never where they are: "reported at" means news placed them there.</p>`;
}

// The live part: what our own feeds say about this person right now.
async function signals(d, t) {
  let s;
  try { s = await fetch('/api/dossier/person/' + d.qid + '?name=' + encodeURIComponent(d.name), {cache: 'no-store'}).then(r => r.json()); }
  catch (e) { if (live(t)) $('#dos-signals').innerHTML = '<h3>Signals</h3><p class="soft">Could not reach the server.</p>'; return; }
  if (!live(t) || !$('#dos-signals')) return;
  const f = s.feeds || {}, n = s.news;
  const keyless = d.problems.some(p => /OpenSanctions key/.test(p)), sancFail = d.problems.find(p => /OpenSanctions/.test(p) && !/key set/.test(p));
  const sanc = d.sanctions.length ? tile('Sanctions and PEP lists', 'Listed', esc(d.sanctions.slice(0, 2).map(x => (x.topics || []).join(', ') || 'listed').join('; ')), 'OpenSanctions match by name and birth date', 'hot')
    : tile('Sanctions and PEP lists', keyless ? 'Not checked' : sancFail ? 'Not checked' : 'Not listed', keyless ? 'no OpenSanctions key in data/' : sancFail ? esc(sancFail) : 'no match by name and birth date', 'OpenSanctions');
  const air = s.aircraft || [], seen = air.filter(a => a.seen), up = seen.filter(a => !a.seen.ground);
  const airVal = !air.length ? 'None listed' : up.length ? `${up.length} airborne` : seen.length ? `${seen.length} on the ground` : 'Not seen now';
  const country = s.country_name ? esc(s.country_name) : 'their country';
  const tiles = [
    tile('In the news, 6 h', n.single_name ? '—' : `${n.outlets} ${n.outlets === 1 ? 'outlet' : 'outlets'}`, n.single_name ? 'a one-word name cannot be matched safely' : n.places.length ? 'most from ' + esc(n.places[0].place.split(',')[0]) : 'not named in any article we hold', 'GDELT people named in articles · ' + feedAge(f.news)),
    s.is_leader ? tile('Reported at', s.reported_at ? esc(s.reported_at.place.split(',')[0]) : 'Nowhere clear', s.reported_at ? `${s.reported_at.headlines} headlines, ${s.reported_at.outlets} outlets${s.reported_at.abroad ? ' · outside their country' : ''}` : 'needs 2+ headlines from 2+ outlets at one place', 'Leaders today (GDELT) · where news placed them, not where they are', s.reported_at?.abroad ? 'warm' : '') : '',
    tile('Aircraft listed with them', airVal, air.length ? `${air.length} in plane-alert-db${seen.length ? `, ${seen.length} in our feeds now` : ''}` : 'no plane in the list carries their name or office', 'plane-alert-db (volunteer list) + live positions · ' + feedAge(f.aircraft_world), up.length ? 'hot' : ''),
    s.unrest ? tile(`Unrest in ${country}, 24 h`, `${s.unrest.total} ${s.unrest.total === 1 ? 'group' : 'groups'}`, `${s.unrest.two_plus} reported by 2+ outlets · ${s.unrest.violent} not protests`, 'GDELT events, machine-coded · ' + feedAge(f.unrest)) : '',
    s.airspace ? tile(`Airspace over ${country}`, s.airspace.length ? `${s.airspace.length} ${s.airspace.length === 1 ? 'warning' : 'warnings'}` : 'No warnings', s.airspace.map(a => `${a.source} ${a.level === 'avoid' || a.level === 'prohibited' ? '(do not fly)' : '(' + a.level + ')'}`).join(', ') || 'none from EASA or the FAA', 'EASA, FAA · ' + feedAge(f.airspace), s.airspace.some(a => a.level === 'avoid' || a.level === 'prohibited') ? 'warm' : '') : '',
    sanc,
  ].filter(Boolean).join('');

  const arts = n.articles.length ? `<ol class="stories">${n.articles.map(a => `<li>${a.image ? `<img src="${esc(img(a.image))}" alt="" loading="lazy" onerror="this.remove()">` : ''}<span class="st">
      <a href="${esc(a.url)}" target="_blank" rel="noopener">${esc(a.title)}</a><span class="by">${esc(a.outlet)} · ${esc(a.place.split(',')[0])} · ${ago(a.time)}${a.lang !== 'eng' ? ' · not in English' : ''}</span></span></li>`).join('')}</ol>` : '';
  const plane = a => `<li><b>${esc(a.reg || a.hex)}</b> <span class="soft">· ${esc(a.type || '')}${a.operator ? ', ' + esc(a.operator) : ''}</span><br>
      <span class="soft">${esc(a.why)} · </span>${a.seen ? `${a.seen.ground ? 'on the ground' : 'airborne' + (a.seen.alt_ft ? ' at ' + a.seen.alt_ft.toLocaleString('en-GB') + ' ft' : '')}${a.seen.over ? ' over ' + flagMark(a.seen.over) + ' ' + esc(a.seen.over) : ' over sea'}, position ${ago(a.seen.time)} · ${showOn(a.layer, a.hex)}` : '<span class="soft">not in our aircraft feeds now</span>'}</li>`;
  // the ones seen now first; the rest of the list folded away
  const planes = air.length ? `<div class="dos-fold"><ul class="dos-list">${air.slice(0, 3).map(plane).join('')}</ul>${air.length > 3 ? `<a href="#" class="link" data-more>${air.length - 3} more listed</a><ul class="dos-list fold-rest">${air.slice(3).map(plane).join('')}</ul>` : ''}</div>` : '';

  $('#dos-signals').innerHTML = `<h3>Signals</h3><div class="sig-grid">${tiles}</div>
    ${planes ? `<div class="dos-sub-block"><h4>Aircraft listed with them</h4>${planes}<p class="source">"Listed" means plane-alert-db's volunteers tagged the aircraft with this person's name or office. It does not mean they are aboard; nobody publishes that. Positions are the newest from adsb.lol, adsb.fi or OpenSky (which can be 20 minutes old).</p></div>` : ''}
    ${arts ? `<div class="dos-sub-block"><h4>Naming them in the headline, last ${n.window_h} hours</h4>${arts}${n.outlets > n.in_headline ? `<p class="source">${n.outlets - n.in_headline} more outlets name them only in the text.</p>` : ''}${n.places.length > 1 ? `<p class="source">Places these articles were pinned to: ${n.places.map(p => `${esc(p.place.split(',')[0])} (${p.outlets})`).join(', ')}.</p>` : ''}</div>` : ''}
    ${s.is_leader && s.reported_at?.also?.length ? `<p class="source">Also placed by the news at: ${s.reported_at.also.map(p => esc(p.split(',')[0])).join(', ')}.</p>` : ''}
    <p class="source">Read from this server's feeds when this dossier opened. Counts are of articles and events our feeds hold; nothing is scored. GDELT finds names and places by machine and makes mistakes.</p>`;
}
