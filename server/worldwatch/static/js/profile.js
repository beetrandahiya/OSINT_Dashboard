// The public-figure profile: a large overlay built from public records. Opened from the People map layer,
// from People search, and (for a confirmed identity) from the lookup graph. Every section names its source.
import {$, ago, esc, local} from './util.js';

let host = null, current = null;

function el() {
  if (host) return host;
  host = document.createElement('div');
  host.id = 'profile';
  host.hidden = true;
  host.innerHTML = '<div class="prof-scrim"></div><section class="glass prof-card" role="dialog" aria-label="Profile"></section>';
  document.body.appendChild(host);
  host.querySelector('.prof-scrim').onclick = close;
  addEventListener('keydown', e => { if (e.key === 'Escape' && !host.hidden) close(); });
  return host;
}
function close() { if (host) host.hidden = true; current = null; }

export async function openProfile(qid) {
  const h = el(); h.hidden = false;
  current = qid;
  card().innerHTML = `<button class="close" id="prof-close" aria-label="Close"></button><div class="prof-loading">Building the profile from public records…</div>`;
  $('#prof-close').onclick = close;
  try {
    const r = await fetch('/api/people/profile/' + encodeURIComponent(qid), {cache: 'no-store'});
    const d = await r.json();
    if (current !== qid) return;
    if (!r.ok) { card().querySelector('.prof-loading').textContent = d.error || 'Could not build the profile.'; return; }
    render(d);
  } catch (e) { if (current === qid) card().querySelector('.prof-loading').textContent = 'Could not reach the server.'; }
}
const card = () => host.querySelector('.prof-card');

const when = (s, e) => `${s ? s.slice(0, 4) : '?'} – ${e ? e.slice(0, 4) : 'now'}`;
const yearsOld = born => born ? Math.floor((Date.now() - Date.parse(born)) / 3.156e10) : null;

function group(items, label) {
  const g = items.filter(i => i.label === label);
  return g.length ? g.map(i => esc(i.name)).join(', ') : null;
}

function render(d) {
  const named = a => a.filter(i => !/^Q\d+$/.test(i.name));
  const capList = (label, src, max) => { const g = named(src.filter(i => i.label === label)); return g.length ? g.slice(0, max).map(i => esc(i.name)).join(', ') + (g.length > max ? ` and ${g.length - max} more` : '') : null; };
  const roles = d.current_roles.length ? d.current_roles : d.positions.slice(0, 1);
  const age = yearsOld(d.born);
  const past = d.positions.filter(p => p.end);
  const holdings = named(d.holdings.filter(h => ['founded', 'owned by them', 'chief executive of', 'chair of', 'owns', 'parent org of'].includes(h.label)));
  const family = named(d.ties.filter(t => ['spouse', 'child', 'father', 'mother', 'sibling'].includes(t.label)));
  const memberships = named(d.ties.filter(t => t.label === 'member of'));
  const sct = (title, body, note) => body ? `<section class="pz"><h3>${title}</h3>${body}${note ? `<p class="source">${note}</p>` : ''}</section>` : '';

  const roleLine = roles.map(r => esc(r.name) + (r.of ? ' of ' + esc(r.of) : '')).join(' · ');
  const timeline = d.positions.length ? `<ol class="tl">` + d.positions.map(p => `<li><span class="tl-when">${when(p.start, p.end)}</span><span class="tl-what">${esc(p.name)}${p.of ? ` <span class="soft">· ${esc(p.of)}</span>` : ''}</span></li>`).join('') + `</ol>` : null;

  const links = [d.official_website && `<a class="link" href="${esc(d.official_website)}" target="_blank" rel="noopener">Official site</a>`,
    ...Object.entries(d.socials).map(([k, v]) => `<a class="link" href="${esc(v)}" target="_blank" rel="noopener">${esc(k.replace(/[/@].*$/, '').replace('.com', ''))}</a>`),
    d.wikipedia && `<a class="link" href="${esc(d.wikipedia)}" target="_blank" rel="noopener">Wikipedia</a>`,
    `<a class="link" href="${esc(d.wikidata)}" target="_blank" rel="noopener">Wikidata</a>`].filter(Boolean).join('');

  card().innerHTML = `<button class="close" id="prof-close" aria-label="Close"></button>
    <header class="prof-head">
      ${d.image ? `<img class="prof-face" src="${esc(d.image)}" alt="" referrerpolicy="no-referrer" loading="lazy">` : '<div class="prof-face blank"></div>'}
      <div class="prof-id"><h2>${esc(d.name)}</h2>
        ${roleLine ? `<p class="prof-role">${roleLine}</p>` : ''}
        <p class="prof-sub">${[d.born ? `Born ${local ? d.born : d.born}${age != null ? `, age ${age}` : ''}` : null, d.died ? `died ${d.died}` : null, group(d.identity, 'party')].filter(Boolean).join(' · ')}</p>
        <div class="prof-links">${links}</div>
      </div>
    </header>
    ${d.intro ? `<p class="prof-intro">${esc(d.intro)}</p>` : ''}
    <div class="prof-cols">
      ${sct('Offices held', timeline, 'From Wikidata, with the dates it records.')}
      ${sct('Companies and organisations', holdings.length ? '<ul class="pz-list">' + holdings.map(h => `<li>${esc(h.name)} <span class="soft">· ${esc(h.label)}</span></li>`).join('') + '</ul>' : null, 'Ownership, founding and board roles from Wikidata. Far from complete, and strongest for well-documented figures.')}
      ${sct('Family and close ties', family.length ? '<ul class="pz-list">' + family.map(f => `<li>${esc(f.name)} <span class="soft">· ${esc(f.label)}</span></li>`).join('') + '</ul>' : null, 'From Wikidata.')}
      ${sct('Member of', memberships.length ? memberships.map(m => esc(m.name)).join(', ') : null, 'From Wikidata.')}
      ${sct('Education and honours', [capList('educated at', d.background, 6) && '<b>Educated at:</b> ' + capList('educated at', d.background, 6), capList('award', d.background, 10) && '<b>Awards:</b> ' + capList('award', d.background, 10)].filter(Boolean).join('<br>') || null, 'From Wikidata.')}
      ${sct('Sanctions and exposed-person lists', d.sanctions.length ? '<ul class="pz-list">' + d.sanctions.map(s => `<li><a class="link" href="${esc(s.url)}" target="_blank" rel="noopener">${esc(s.name)}</a> <span class="soft">· ${esc((s.topics || []).join(', ') || 'listed')}</span><br><span class="soft">on: ${esc((s.listed_on || []).slice(0, 4).join(', '))}</span></li>`).join('') + '</ul>' : null, 'From OpenSanctions. A match here means the name (and birth date, where known) matches a listed person; confirm it is the same person before trusting it.')}
      ${sct('Reported in the news', d.news.length ? '<ul class="pz-news">' + d.news.slice(0, 12).map(n => `<li><a class="link" href="${esc(n.url)}" target="_blank" rel="noopener">${esc(n.title)}</a><span class="soft">${esc(n.outlet || '')}${n.country ? ' · ' + esc(n.country) : ''}</span></li>`).join('') + '</ul>' : null, 'Recent articles naming this person, from GDELT.')}
    </div>
    ${d.problems.length ? `<p class="source prof-problems">Some parts could not be loaded: ${d.problems.map(esc).join('; ')}.</p>` : ''}
    <p class="source">Built from public records on ${new Date(d.built * 1000).toISOString().slice(0, 16).replace('T', ' ')} UTC, cached for a day. Sources: Wikidata, Wikipedia, OpenSanctions, GDELT. This is who a person is and what the record shows, not where they are now.</p>`;
  $('#prof-close').onclick = close;
}
