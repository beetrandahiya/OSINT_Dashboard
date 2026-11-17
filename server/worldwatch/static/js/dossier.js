// The dossier: everything a scan found, read and arranged into one document.
// Every line says where it came from. Nothing is scored or guessed: a name or picture is listed with the
// pages that show it, and a page that could not be opened says so.
import {esc} from './util.js';

const host = u => { try { return new URL(u).hostname.replace(/^www\./, ''); } catch (e) { return u; } };
const siteOf = f => f.kind === 'account' ? f.key.split(':')[0] : (f.page?.site || host(f.url || '') || f.title);
const yr = s => s ? String(s).slice(0, 10) : '';
const isImg = u => typeof u === 'string' && /^https:\/\//.test(u);
// Every link and picture here comes from strangers' pages and tools' output: only plain web addresses become
// links (no javascript:, data:, vbscript:...). Anything else is shown as text, or not at all.
export const safeUrl = u => typeof u === 'string' && /^https?:\/\/[^\s]/i.test(u) ? u : null;
const ext = (u, inner, cls = '') => safeUrl(u) ? `<a${cls ? ` class="${cls}"` : ''} href="${esc(u)}" target="_blank" rel="noopener noreferrer">${inner}</a>` : inner;

// The same value seen on several pages becomes one line, with all the pages that show it.
function tally(items) {
  const m = new Map();
  for (const [value, site, url] of items) {
    if (!value) continue;
    const k = String(value).trim().toLowerCase(); if (!k || k.length > 120) continue;
    const e = m.get(k) || {value: String(value).trim(), seen: []};
    if (!e.seen.some(s => s.site === site)) e.seen.push({site, url});
    m.set(k, e);
  }
  return [...m.values()].sort((a, b) => b.seen.length - a.seen.length);
}
const seenOn = e => e.seen.slice(0, 6).map(s => ext(s.url, esc(s.site))).join(', ') + (e.seen.length > 6 ? ` and ${e.seen.length - 6} more` : '');

// GitHub and others give a website as "example.com": a bare domain name is a web address too
const web = v => typeof v === 'string' && /^[a-z0-9-]+(\.[a-z0-9-]+)*\.[a-z]{2,}(\/\S*)?$/i.test(v.trim()) ? 'https://' + v.trim() : v;

// Did an email check run on every email address after it was added, without that service failing? Otherwise
// "0" or "none found" would be a claim nobody checked.
function emailChecked(S, service) {
  const mails = S.identifiers.filter(i => i.kind === 'email'), run = (S.checks_run || {}).services;
  if (!mails.length) return 'no email address';
  if (!run || mails.some(i => i.added > run.started)) return 'not checked';
  return run.problems.some(p => p.startsWith(service + ':')) ? 'failed' : 'ok';
}

export function render(S, G, kinds, figures = {}, figNote = '') {
  const live = G.filter(f => !f.not_me);
  const pages = live.filter(f => f.url && ['account', 'profile', 'code', 'registered', 'mention'].includes(f.kind));
  const ok = pages.filter(f => f.page?.alive === true), dead = pages.filter(f => f.page?.alive === false),
        unsure = pages.filter(f => f.page && f.page.alive == null), unread = pages.filter(f => !f.page);
  const breaches = live.filter(f => f.kind === 'breach'), exposure = live.filter(f => f.kind === 'exposure');
  const hosts = live.filter(f => f.kind === 'host'), regs = live.filter(f => f.kind === 'registration');
  const codeMail = live.filter(f => f.kind === 'email' || (f.kind === 'code' && !f.url)), keys = live.filter(f => f.kind === 'key');
  const shown = [...ok, ...unsure];   // pages that are, or may be, there; dead ones are left out of the picture below

  // ---- as the internet shows you ----
  const d = f => f.detail || {}, p = f => f.page || {};
  const names = tally(shown.flatMap(f => [[d(f).fullname, siteOf(f), f.url], [d(f).name, siteOf(f), f.url], [p(f).name, siteOf(f), f.url], [p(f).alternate_name, siteOf(f), f.url]]));
  const pics = tally(shown.flatMap(f => [[isImg(d(f).image) && d(f).image, siteOf(f), f.url], [isImg(d(f).photo) && d(f).photo, siteOf(f), f.url], [isImg(p(f).image) && p(f).image, siteOf(f), f.url]]))
    .filter(e => !/logo|favicon|default|placeholder|og-image|social-card|banner|share/i.test(e.value)).slice(0, 24);
  const places = tally(shown.flatMap(f => [[d(f).location, siteOf(f), f.url], [d(f).city, siteOf(f), f.url], [d(f).country, siteOf(f), f.url], [p(f).location, siteOf(f), f.url]]));
  const bios = tally(shown.flatMap(f => [[d(f).bio, siteOf(f), f.url], [d(f).about, siteOf(f), f.url], [f.kind === 'account' && p(f).description, siteOf(f), f.url]])).slice(0, 8);
  const work = tally(shown.flatMap(f => [[d(f).company, siteOf(f), f.url], [p(f).works_for, siteOf(f), f.url]]));
  const sites = tally(shown.flatMap(f => [[web(d(f).website), siteOf(f), f.url], [web(d(f).blog), siteOf(f), f.url], ...[].concat(p(f).same_as || []).map(u => [u, siteOf(f), f.url])])).filter(e => /^https?:/.test(e.value));

  // ---- timeline: only dated facts, oldest first ----
  const ev = [];
  const add = (date, what, src, url) => { const t = String(date || '').slice(0, 10); if (/^\d{4}/.test(t)) ev.push({t, what, src, url}); };
  for (const f of breaches) add(d(f).year, `Your address appears in the ${f.title} breach`, 'XposedOrNot', f.url);
  for (const f of exposure) for (const i of d(f).infections || []) add(i.date, `A computer using your address was infected by password-stealing malware${i.computer ? ` (${i.computer})` : ''}`, 'Hudson Rock', f.url);
  for (const f of shown) {
    add(d(f).created_at, `${siteOf(f)} account created`, f.tools[0], f.url);
    add(p(f).created, `${siteOf(f)} profile created, as the page states`, siteOf(f), f.url);
    if (f.archive?.first) add(f.archive.first, `Earliest archived copy of your ${siteOf(f)} page`, 'Internet Archive', f.archive.snapshot);
    add(d(f).latest_activity_at, `Latest activity on ${siteOf(f)}`, f.tools[0], f.url);
  }
  for (const f of regs) add(d(f).registered, `Domain registered`, 'Domain registry', f.url);
  ev.sort((a, b) => a.t.localeCompare(b.t));

  const sec = (title, body, note) => body ? `<section class="ds"><h2>${title}</h2>${body}${note ? `<p class="source">${note}</p>` : ''}</section>` : '';
  const rows = list => `<ul class="ds-tally">` + list.map(e => `<li><b>${esc(e.value)}</b><span>on ${seenOn(e)}</span></li>`).join('') + `</ul>`;
  const card = f => `<li class="ds-acc" data-fid="${f.id}">
      ${isImg(p(f).image || d(f).image) ? `<img src="${esc(p(f).image || d(f).image)}" alt="" loading="lazy" referrerpolicy="no-referrer" onerror="this.replaceWith(Object.assign(document.createElement('span'),{className:'ds-dot',textContent:'·'}))">` : `<span class="ds-dot">${esc(siteOf(f).slice(0, 1).toUpperCase())}</span>`}
      <span class="ds-acc-t">${ext(f.url, `<b>${esc(siteOf(f))}</b>`)}
        <span>${esc(p(f).title && p(f).title !== siteOf(f) ? p(f).title : f.title)}</span>
        ${p(f).description ? `<span class="soft">${esc(p(f).description.slice(0, 140))}</span>` : ''}
        <span class="soft">${f.page?.alive === true ? 'opened and read' : f.page ? esc(f.page.why || 'could not be checked') : 'not read yet'}${f.archive?.first ? ` · archived since ${yr(f.archive.first)}` : ''} · found by ${esc(f.tools.join(', '))}</span></span></li>`;

  const ids = S.identifiers.map(i => `<span class="ds-id"><i>${esc(kinds[i.kind])}</i>${esc(i.value)}</span>`).join('');
  const ls = S.last_scan, xon = emailChecked(S, 'XposedOrNot'), hr = emailChecked(S, 'Hudson Rock');
  const figs = Object.entries(figures).filter(([, l]) => l.length);
  const figHtml = (figNote ? `<p class="source">${esc(figNote)}</p>` : '') + (figs.length ? `<section class="ds ds-figs"><h2>Public figure record</h2>
      <p class="source" style="margin:0 0 10px">A full name you entered matches people on Wikidata. For a public figure, the full record (offices held with dates, companies, family and ties, sanctions lists, recent news) is in their profile; the sweeps below only find accounts and web pages.</p>
      <ul class="ds-accs">` + figs.flatMap(([name, list]) => list.map(x => `<li class="ds-acc ds-fig" data-qid="${esc(x.qid)}"><span class="ds-dot">${esc(x.name.slice(0, 1))}</span>
        <span class="ds-acc-t"><b>${esc(x.name)}</b><span class="soft">${esc(x.description)}</span><span class="link">Open the full profile</span></span></li>`)).join('') + `</ul></section>` : '');
  return `<header class="ds-head"><p class="eyebrow">Dossier</p><h1>What public sources show</h1>
      <div class="ds-ids">${ids}</div>
      <dl class="ds-stats">
        <div><dt>Live pages</dt><dd>${ok.length}</dd></div><div><dt>Could not check</dt><dd>${unsure.length + unread.length}</dd></div>
        <div><dt>Dead links dropped</dt><dd>${dead.length}</dd></div><div><dt>Breaches</dt><dd>${breaches.length || (xon === 'ok' ? 0 : `<small>${xon}</small>`)}</dd></div>
        <div><dt>Malware exposure</dt><dd>${exposure.length ? 'yes' : hr === 'ok' ? 'none found' : `<small>${hr}</small>`}</dd></div><div><dt>Host names</dt><dd>${hosts.length}</dd></div>
      </dl>
      <p class="source">${ls ? `Last scan ${new Date(ls.finished * 1000).toLocaleString('en-GB')}.` : 'No scan yet.'} ${unread.length ? `${unread.length} pages have not been read yet: run a scan with “Open every page found” ticked, or press “Read the pages”.` : ''} Items you marked “Not me” are left out.</p></header>${figHtml}
    ${sec('As the internet shows you', [
      names.length && `<h3>Names shown</h3>` + rows(names.slice(0, 10)),
      pics.length && `<h3>Pictures shown</h3><div class="ds-pics">` + pics.map(e => `<a href="${esc(safeUrl(e.seen[0].url) || e.value)}" target="_blank" rel="noopener noreferrer" title="On ${esc(e.seen.map(s => s.site).join(', '))}"><img src="${esc(e.value)}" alt="" loading="lazy" referrerpolicy="no-referrer" onerror="this.parentElement.remove()"><span>${esc(e.seen[0].site)}</span></a>`).join('') + `</div>`,
      places.length && `<h3>Places given</h3>` + rows(places.slice(0, 8)),
      work.length && `<h3>Work given</h3>` + rows(work.slice(0, 6)),
      bios.length && `<h3>How you describe yourself</h3>` + rows(bios),
      sites.length && `<h3>Links to your other pages</h3>` + rows(sites.slice(0, 12)),
    ].filter(Boolean).join('') || null, 'Read from the pages themselves: what each one shows to any visitor. A name or picture on many pages is more likely yours; a stranger with your username shows up here too until you mark it “Not me”.')}
    ${sec(`Accounts and pages (${ok.length} live${unsure.length + unread.length ? `, ${unsure.length + unread.length} unchecked` : ''})`, ok.length + unsure.length + unread.length ? `<ul class="ds-accs">` + [...ok, ...unsure, ...unread].map(card).join('') + `</ul>` : null,
      'A page counts as live only when it opened and showed the account. Some sites refuse automated visits; those are listed as unchecked, not as proof either way.')}
    ${dead.length ? `<details class="ds-dead"><summary>${dead.length} dead links left out</summary><ul>` + dead.map(f => `<li>${esc(siteOf(f))}: ${esc(f.page.why)}</li>`).join('') + `</ul></details>` : ''}
    ${sec('Exposure', [
      breaches.length && `<h3>Breaches that list your address</h3><table class="ds-tab"><thead><tr><th>Breach</th><th>Year</th><th>What leaked</th></tr></thead><tbody>` +
        breaches.map(f => `<tr><td>${ext(f.url, esc(f.title))}</td><td>${esc(d(f).year || '')}</td><td>${esc(String(d(f).leaked || '').replace(/;/g, ', '))}</td></tr>`).join('') + `</tbody></table>`,
      exposure.length && `<h3>Password-stealing malware</h3>` + exposure.map(f => `<p>${esc(d(f).what || f.title)}</p>`).join(''),
      keys.length && `<h3>Public encryption keys</h3>` + keys.map(f => `<p>${ext(f.url, esc(f.title))}</p>`).join(''),
      codeMail.length && `<h3>Your address in public code</h3><ul class="ds-plain">` + codeMail.map(f => `<li>${ext(f.url, esc(f.title))}</li>`).join('') + `</ul>`,
    ].filter(Boolean).join('') || null, 'Breaches from XposedOrNot, malware records from Hudson Rock, keys from keys.openpgp.org, code from GitHub. No leaked passwords or files are downloaded, only what kind of data leaked.')}
    ${sec('Domains', [regs.map(f => `<p><b>${esc(f.title)}</b> · registered ${esc(d(f).registered || '?')}, expires ${esc(d(f).expires || '?')} · contacts shown: ${esc(d(f).listed_contacts || 'none')}</p>`).join(''),
      hosts.length && `<h3>${hosts.length} host names in public records</h3><p class="ds-hosts">` + hosts.slice(0, 120).map(f => esc(f.title)).join(' · ') + `</p>`].filter(Boolean).join('') || null,
      'From the domain registry and public certificate logs.')}
    ${sec('Timeline', ev.length ? `<ol class="ds-tl">` + ev.map(e => `<li><span class="ds-t">${esc(e.t)}</span><span>${esc(e.what)} <span class="soft">· ${ext(e.url, esc(e.src))}</span></span></li>`).join('') + `</ol>` : null,
      'Only facts that carry a date: breach years, account creation dates the sites publish, and the Internet Archive\'s oldest copy of each page (proof the page existed at least since then).')}`;
}
