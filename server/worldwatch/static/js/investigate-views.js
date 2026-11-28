// The Investigate page's main views: accounts grouped by the evidence that ties them to the subject, the leads
// queue, and the timeline. Nothing here is scored: an account is grouped by the kind of reason a source states,
// and every reason is listed as written. Only http(s) addresses become links.
import {esc} from './util.js';
import {safeUrl} from './dossier.js';

const ext = (u, inner, cls = '') => safeUrl(u) ? `<a${cls ? ` class="${cls}"` : ''} href="${esc(u)}" target="_blank" rel="noopener noreferrer">${inner}</a>` : inner;
const host = u => { try { return new URL(u).hostname.replace(/^www\./, ''); } catch (e) { return u || ''; } };
export const siteOf = f => f.site || (f.kind === 'account' ? f.key.split(':')[0] : (f.page?.site || host(f.url || '') || f.title));
export const proxied = (S, u) => typeof u === 'string' && /^https?:\/\//.test(u) ? `/api/lookup/img?s=${S.subject.id}&u=${encodeURIComponent(u)}` : null;
export const picOf = f => [f.page?.image, f.detail?.image, f.detail?.photo].find(u => typeof u === 'string' && /^https?:\/\//.test(u) && !/logo|favicon|placeholder|banner/i.test(u));

const STRONG = new Set(['confirmed', 'bound', 'reciprocal', 'rel_me', 'keybase_proof', 'same_gravatar', 'same_email']);
export const strongChip = c => STRONG.has(c.code) || (c.code === 'same_picture' && c.distance === 0);
export function chips(list, max = 6) {
  return list.slice(0, max).map(c => `<span class="ev${strongChip(c) ? ' strong' : ''}"${c.fid ? ` data-goto="${c.fid}"` : ''} title="${esc(c.text)}">${esc(c.text)}</span>`).join('')
    + (list.length > max ? `<span class="ev more">and ${list.length - max} more</span>` : '');
}

// which evidence group an account belongs to (the headings say what each group means)
export function band(g) {
  if (g.not_me) return 'notme';
  if (g.confirmed || g.bound) return 'confirmed';
  if (g.evidence.some(strongChip)) return 'strong';
  if (g.evidence.length) return 'some';
  return 'none';
}
const BANDS = [
  ['confirmed', 'Confirmed', 'You confirmed these, or they are an identifier of this case itself (the GitHub account entered, the Gravatar of an address entered, an account that signed a proof for one).'],
  ['strong', 'Tied by a stated reason', 'Not confirmed yet, but a source states a reason that ties each one to a confirmed account: links both ways, a signed proof, the same address, an identical picture file.'],
  ['some', 'Some evidence', 'One-way links, the same display name or website, a similar picture, or found by several tools. Namesakes can share all of these.'],
  ['none', 'No evidence yet', 'Found only because the username matched. Each may well belong to someone else.'],
  ['notme', 'Marked “not me”', 'Left out of everything else.'],
];

export function renderList(S, G, filter, picked) {
  const accounts = G.filter(g => ['account', 'profile', 'website'].includes(g.kind) && g.url);
  const others = G.filter(g => !accounts.includes(g) && !g.not_me && g.kind !== 'note');
  const want = b => filter === 'all' ? b !== 'notme' : filter === 'confirmed' ? b === 'confirmed' : filter === 'unconfirmed' ? ['strong', 'some', 'none'].includes(b) : b === 'notme';
  const n = b => accounts.filter(g => band(g) === b).length;
  const seg = `<div class="seg lk-filter" role="group" aria-label="Filter">` + [['all', 'All', accounts.length - n('notme')], ['confirmed', 'Confirmed', n('confirmed')],
    ['unconfirmed', 'Unconfirmed', n('strong') + n('some') + n('none')], ['notme', 'Not me', n('notme')]]
    .map(([k, t, c]) => `<button data-filter="${k}" aria-pressed="${filter === k}">${t} <small>${c}</small></button>`).join('') + `</div>`;
  const row = g => {
    const pic = picOf(g), p = g.page || {};
    const status = p.alive === true ? 'opened and read' : p.alive === false ? 'dead: ' + (p.why || '') : g.page ? (p.why || 'could not be checked') : 'not read yet';
    return `<li class="acc${picked === g.id ? ' sel' : ''}" data-fid="${g.id}">
      ${pic ? `<img src="${esc(proxied(S, pic))}" alt="" loading="lazy" onerror="this.replaceWith(Object.assign(document.createElement('span'),{className:'ds-dot',textContent:'·'}))">` : `<span class="ds-dot">${esc(siteOf(g).slice(0, 1).toUpperCase())}</span>`}
      <div class="acc-t"><div class="acc-h">${ext(g.url, `<b>${esc(siteOf(g))}</b>`)}<span class="soft">${esc(p.title && p.title !== siteOf(g) ? p.title : g.title)}</span></div>
        ${p.description || g.detail?.bio ? `<span class="soft clip">${esc(String(p.description || g.detail.bio).slice(0, 160))}</span>` : ''}
        ${g.evidence.length ? `<div class="evs">${chips(g.evidence, 4)}</div>` : ''}
        <span class="meta">${esc(status)}${g.archive?.first || g.history?.first ? ` · archived since ${esc((g.history?.first || g.archive.first).slice(0, 10))}` : ''} · found by ${esc(g.tools.join(', '))}</span></div>
      <div class="acc-b">${g.not_me ? `<button class="btn sm" data-act="undo-notme">Undo</button>` : g.confirmed ? `<button class="btn sm" data-act="unconfirm">Unconfirm</button>`
        : `${g.bound ? '' : `<button class="btn sm ok" data-act="confirm">Confirm</button>`}<button class="btn sm" data-act="notme">Not me</button>`}</div></li>`;
  };
  const groups = BANDS.filter(([b]) => want(b)).map(([b, title, note]) => {
    const list = accounts.filter(g => band(g) === b);
    return list.length ? `<section class="ds"><h2>${title} <small>${list.length}</small></h2><p class="source band-note">${esc(note)}</p><ul class="accs">${list.map(row).join('')}</ul></section>` : '';
  }).join('');
  const OK = {breach: 'Breaches (names and kinds of data only)', exposure: 'Malware exposure', key: 'Public keys', code: 'Address in public code', email: 'Email addresses found',
    host: 'Host names', registration: 'Domain records', record: 'Research records (name search; namesakes are common)', mention: 'Web pages from searches', registered: 'Registered with the address',
    phone: 'Phone number plan', url: 'Web addresses'};
  const byKind = {};
  for (const g of others) (byKind[g.kind] = byKind[g.kind] || []).push(g);
  const other = filter === 'all' && others.length ? `<section class="ds"><h2>Other findings <small>${others.length}</small></h2>` + Object.entries(byKind).map(([k, list]) =>
    `<details class="other"${list.length <= 6 ? ' open' : ''}><summary>${esc(OK[k] || k)} <small>${list.length}</small></summary><ul class="olist">` + list.slice(0, 200).map(g =>
      `<li data-fid="${g.id}"${picked === g.id ? ' class="sel"' : ''}><b>${esc(g.title)}</b> <span class="soft">${esc(g.tools.join(', '))}</span>${g.evidence.length ? `<div class="evs">${chips(g.evidence, 3)}</div>` : ''}</li>`).join('')
      + (list.length > 200 ? `<li class="soft">and ${list.length - 200} more (all in the JSON export)</li>` : '') + `</ul></details>`).join('') + `</section>` : '';
  const empty = !accounts.length && !others.length ? `<p class="lk-empty">${S.identifiers.length ? 'Nothing found yet. Run a scan to see what public sources show about these identifiers.'
    : 'Add identifiers on the left (a username, an email address, a full name, a picture file...), then scan.'}</p>` : '';
  return `<header class="ds-head"><p class="eyebrow">Accounts</p><h1>${esc(S.subject.label)}</h1>${seg}</header>${empty}${groups || (accounts.length && !empty ? '<p class="lk-empty">Nothing in this filter.</p>' : '')}${other}`;
}

const KIND_WORD = {username: 'Username', email: 'Email address', name: 'Full name', domain: 'Domain', github: 'GitHub account'};
export function renderLeads(S) {
  const L = S.leads || [], fresh = L.filter(l => l.state === 'new');
  const strong = fresh.filter(l => l.strength === 'strong'), weak = fresh.filter(l => l.strength === 'weak'), done = L.filter(l => l.state !== 'new');
  const card = l => `<li class="lead" data-lead="${l.id}">
      <div class="lead-h"><span class="tag ${l.strength}">${l.strength}</span><b>${esc(KIND_WORD[l.kind] || l.kind)}: ${esc(l.value)}</b><span class="soft">step ${l.hop} from what was entered</span></div>
      <ul class="lead-ev">${l.evidence.map(e => `<li${e.strong ? ' class="strong"' : ''}>${ext(e.url, esc(e.text))}</li>`).join('')}</ul>
      <div class="lead-b">${l.state === 'new' ? `<button class="btn sm ok" data-lact="approve">${l.strength === 'strong' ? 'Add now' : 'Approve'}</button><button class="btn sm" data-lact="reject">Reject</button>`
        : l.state === 'rejected' ? `<span class="soft">Rejected: never proposed again.</span><button class="btn sm" data-lact="undo">Undo</button>`
        : `<span class="soft">${l.state === 'followed' ? 'Followed automatically' : 'Approved'}: now an identifier of this case.</span>`}</div></li>`;
  const sec = (title, note, list) => list.length ? `<section class="ds"><h2>${title} <small>${list.length}</small></h2><p class="source band-note">${note}</p><ul class="leads">${list.map(card).join('')}</ul></section>` : '';
  return `<header class="ds-head"><p class="eyebrow">Leads</p><h1>What else may belong to ${esc(S.subject.label)}</h1>
      <p class="source">Leads come only from confirmed accounts and from searches, never from unconfirmed pages. Strong leads are followed at the next scan (at most 2 steps from what you entered); weak ones wait for you. Rejected leads are remembered and never proposed again.${S.plan?.unscanned ? ` <b>${S.plan.unscanned} identifiers are not scanned yet</b>: use “Scan” on the left with “Only identifiers not scanned yet”.` : ''}</p></header>`
    + (L.length ? '' : `<p class="lk-empty">No leads yet. They appear after a scan, and when you confirm an account whose page links elsewhere.</p>`)
    + sec('Strong, waiting', 'Each has a stated reason that ties it to an identifier or a confirmed account of this case. Followed automatically at the next scan; reject any you do not want followed.', strong)
    + sec('Weak, waiting for you', 'Display names, one-way links, similar usernames and search results. Namesakes are common: approve only what you can tell is the same person.', weak)
    + (done.length ? `<details class="ds done"><summary>Decided <small>${done.length}</small></summary><ul class="leads">${done.map(card).join('')}</ul></details>` : '');
}

export function renderTimeline(S, onlyConfirmed) {
  const ev = (S.timeline || []).filter(e => !onlyConfirmed || e.confirmed);
  return `<header class="ds-head"><p class="eyebrow">Timeline</p><h1>Dated facts</h1>
      <div class="seg lk-filter" role="group"><button data-tl="all" aria-pressed="${!onlyConfirmed}">Everything</button><button data-tl="confirmed" aria-pressed="${onlyConfirmed}">Confirmed accounts only</button></div>
      <p class="source">Only facts that carry a date: account creation dates the sites publish, the Internet Archive's oldest and newest copies, breach years, domain registrations. Nothing is estimated.</p></header>`
    + (ev.length ? `<ol class="ds-tl">` + ev.map(e => `<li data-fid="${e.fid}"${e.confirmed ? '' : ' class="unconf"'}><span class="ds-t">${esc(e.t)}</span><span>${esc(e.what)}${e.confirmed ? '' : ' <span class="soft">(not confirmed)</span>'} <span class="soft">· ${ext(e.url, esc(e.src))}</span></span></li>`).join('') + `</ol>`
      : `<p class="lk-empty">No dated facts yet.</p>`);
}
