// The Investigate page (/lookup): cases with their consent records, identifiers, scans that pivot from what they
// find, same-person evidence, and the views: accounts (the main view), leads, timeline, dossier and a graph.
// Boundaries: public sources only; no face recognition or face search; nothing that infers where a person lives,
// is or goes; no breach contents; nothing past a login or bot shield; no scan without a consent record.
import './look.js';                       // the app's look (God's eye by default); light and dark follow the system
import {$, ago, esc, local} from './util.js';
import {render as dossier, safeUrl} from './dossier.js';
import {openProfile} from './profile.js';
import {renderList, renderLeads, renderTimeline, chips, proxied, picOf, siteOf} from './investigate-views.js';
import {fingerprintAll} from './investigate-hash.js';

const KIND = {account: ['Account', 'light-dark(#5856d6, #7d7aff)'], breach: ['Breach', 'light-dark(#ff3b30, #ff453a)'], exposure: ['Malware exposure', 'light-dark(#c2334f, #ff6b6b)'],
  registered: ['Registered with this address', 'light-dark(#af52de, #da8fff)'], profile: ['Profile', 'light-dark(#28a745, #30d158)'], key: ['Public key', 'light-dark(#00a3b4, #40c8e0)'],
  code: ['Code', 'light-dark(#8e8e93, #98989d)'], host: ['Host name', 'light-dark(#00a3b4, #40c8e0)'], email: ['Email address found', 'light-dark(#ff2d55, #ff375f)'],
  registration: ['Registration record', 'light-dark(#a2845e, #c4a57b)'], phone: ['Phone number', 'light-dark(#28a745, #30d158)'], mention: ['Web mention', 'light-dark(#8e8e93, #98989d)'],
  url: ['Web address', 'light-dark(#8e8e93, #98989d)'], note: ['Note', 'light-dark(#c7c7cc, #48484a)'], website: ['Website', 'light-dark(#0a6d99, #8fdcff)'],
  record: ['Research record', 'light-dark(#6b7782, #9aa3a9)']};
const kindOf = k => KIND[k] || KIND.code;
const ACCOUNTISH = ['account', 'profile', 'website'];

// The same page found by several tools, or under several identifiers of the case, becomes one item listing them all.
const norm = u => (u || '').toLowerCase().replace(/^https?:\/\/(www\.)?/, '').replace(/[/?#]+$/, '');
let S = null, G = [], gOf = new Map();
function grouped() {
  const groups = new Map();
  for (const f of S.findings) {
    const key = ACCOUNTISH.includes(f.kind) && f.url ? 'u|' + norm(f.url) : f.identifier + '|' + f.tool + '|' + f.key;
    const g = groups.get(key) || {id: f.id, items: []};
    g.items.push(f); groups.set(key, g);
  }
  gOf = new Map();
  return [...groups.values()].map(g => {
    const best = g.items.slice().sort((a, b) => Object.keys(b.detail || {}).length - Object.keys(a.detail || {}).length)[0];
    const withPage = g.items.find(x => x.page?.alive === true) || g.items.find(x => x.page) || best;
    const ev = [], seen = new Set();
    for (const x of g.items) for (const c of S.evidence?.[x.id] || []) if (!seen.has(c.text)) { seen.add(c.text); ev.push(c); }
    const tools = [...new Set(g.items.map(x => x.tool))];
    if (tools.length > 1) ev.push({code: 'tools', text: `Found by ${tools.length} tools`});
    for (const x of g.items) gOf.set(x.id, g.id);
    return {...best, page: withPage.page, archive: g.items.find(x => x.archive?.first)?.archive || withPage.archive, history: g.items.find(x => x.history)?.history,
            id: g.id, ids: g.items.map(x => x.id), tools, identifier: g.items[0].identifier, identifiers: [...new Set(g.items.map(x => x.identifier))],
            not_me: g.items.every(x => x.not_me), confirmed: g.items.some(x => x.confirmed), bound: g.items.some(x => x.detail?.bound), evidence: ev,
            first_seen: Math.min(...g.items.map(x => x.first_seen)), last_seen: Math.max(...g.items.map(x => x.last_seen))};
  });
}

const store = (k, v) => { try { v === undefined ? localStorage.removeItem(k) : localStorage.setItem(k, typeof v === 'string' ? v : JSON.stringify(v)); } catch (e) { /* private window */ } };
const read = (k, d) => { try { const v = localStorage.getItem(k); return v == null ? d : v; } catch (e) { return d; } };
let tab = read('ww-investigate-tab', 'list'), filter = 'all', tlConfirmed = false, caseId = read('ww-investigate-case', null);
let picked = null, showHidden = false, view = {x: 0, y: 0, k: 1}, sheetOpen = false, chosen = null, onlyNew = false;
try { chosen = JSON.parse(read('ww-lookup-run', 'null')); } catch (e) { chosen = null; }

// Changes go out as JSON with the X-WW header: the server refuses anything else, so other websites cannot drive this API.
async function call(path, method = 'GET', body) {
  if (method === 'POST') body = body || {};
  const r = await fetch(path, {method, cache: 'no-store', headers: method === 'GET' ? {} : {'X-WW': '1', ...(body ? {'Content-Type': 'application/json'} : {})},
    body: body ? JSON.stringify(body) : undefined});
  const d = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(d.error || 'The server answered ' + r.status);
  return d;
}
const sid = () => S?.subject?.id;

// The state is asked for on load, after every action, when the tab comes back, and every 2 s only while a scan
// runs. An answer equal to the last one redraws nothing (a rebuilt card would lose a text selection).
let lastSig = '', pollTimer = 0, wasRunning = false;
async function load() {
  try {
    const d = await call('/api/lookup/state' + (caseId ? '?subject=' + encodeURIComponent(caseId) : '')), sig = JSON.stringify({...d, now: 0});
    if (d.subject && String(d.subject.id) !== String(caseId)) { caseId = String(d.subject.id); store('ww-investigate-case', caseId); }
    if (sig !== lastSig) { lastSig = sig; S = d; G = S.subject ? grouped() : []; render(); }
  } catch (e) { $('#empty').hidden = false; $('#empty').textContent = e.message; }
  clearTimeout(pollTimer);
  const running = !!S?.job.running;
  if (running) pollTimer = setTimeout(load, 2000);
  if (S?.subject && !running && (wasRunning || !fpTried.has(S.subject.id))) {   // pictures of the case without a fingerprint: compare them once a scan is done
    fpTried.add(S.subject.id);
    fingerprintAll(S, (s, items) => call('/api/lookup/fingerprints', 'POST', {subject: s, items})).then(n => { if (n) load(); }).catch(() => {});
  }
  wasRunning = running;
}
const fpTried = new Set();

// ---- left panel ----
function render() {
  const busy = !!S.job.running, sub = S.subject;
  renderCases();
  $('#case-body').hidden = !sub;
  $('.tabs').hidden = !sub; $('.lk-export').hidden = !sub;
  if (!sub) {
    $('#main').innerHTML = `<header class="ds-head"><p class="eyebrow">Investigate</p><h1>Start with a case</h1></header>
      <p class="lk-empty">Every look-up belongs to a case, and a case starts with its consent record: yourself (a self-test), or a person who agreed to be looked up, with who agreed, when, how and to what. Press “New case” on the left.</p>`;
    $('#main').hidden = false; $('#graph').setAttribute('hidden', ''); $('#detail').hidden = true; $('#legend').hidden = true;
    return;
  }
  $('#kind').innerHTML ||= Object.entries(S.kinds).map(([k, v]) => `<option value="${k}">${v}</option>`).join('');
  const ids = S.identifiers.map(i => {
    const pic = i.kind === 'picture';
    return `<li><small>${esc(S.kinds[i.kind])}</small><span>${pic ? `<img class="seedpic" src="/api/lookup/picture/${esc(i.value)}?s=${sub.id}" alt="">${esc(i.detail?.name || i.value.slice(0, 12) + '…')}`
      + (i.detail?.location_meta ? `<em class="warn">This picture carries location metadata. It was not read and is never shown.</em>` : '') : esc(i.value)}`
      + `${i.source === 'pivot' ? `<em>from a lead, step ${i.hop}</em>` : ''}${!i.scanned && !pic ? '<em>not scanned yet</em>' : ''}</span>`
      + `<button data-id="${i.id}" aria-label="Remove"${busy ? ' disabled title="Wait for the scan to finish"' : ''}>✕</button></li>`;
  }).join('') || `<li><span class="soft">Nothing yet. Add a username, an email address, a full name or a picture file${sub.is_self ? ' of yours' : ''}.</span></li>`;
  if ($('#ids').dataset.html !== ids) { $('#ids').innerHTML = ids; $('#ids').dataset.html = ids; }
  times();
  const consent = sub.consent_ok;
  $('#run-test').disabled = busy; $('#plan').disabled = busy || !S.identifiers.length || !consent; $('#wipe').disabled = busy;
  $('#gate').hidden = consent;
  $('#progress').hidden = !busy;
  if (busy) {
    const other = S.job.subject && S.job.subject !== sub.id ? ` (case “${(S.subjects.find(s => s.id === S.job.subject) || {}).label || '?'}”)` : '';
    $('#bar').style.width = S.job.total ? Math.round(S.job.done / S.job.total * 100) + '%' : '8%';
    $('#step').textContent = S.job.step + (S.job.total ? ` (${S.job.done} of ${S.job.total})` : '') + other;
  }
  const ls = S.last_scan;
  $('#problems').innerHTML = (busy ? S.job.problems : ls?.summary.problems || []).map(p => `<li>${esc(p)}</li>`).join('');
  const followed = !busy && ls?.summary.followed?.length ? `<p class="note">Followed in the last scan: ${esc(ls.summary.followed.join(', '))}.</p>` : '';
  $('#followed').innerHTML = followed;
  $('#stored').textContent = `${S.identifiers.length} identifiers, ${S.findings.length} findings (${G.length} after joining the same page found by several tools), ${(S.leads || []).length} leads.`;
  $('#read-pages').disabled = busy || !S.findings.length || !consent;
  if (sheetOpen) renderSheet();
  $('#n-leads').textContent = (S.leads || []).filter(l => l.state === 'new').length || '';
  $('#exp-json').href = `/api/lookup/subjects/${sub.id}/export.json`; $('#exp-html').href = `/api/lookup/subjects/${sub.id}/case-file`;
  for (const b of document.querySelectorAll('.tabs [data-tab]')) b.setAttribute('aria-pressed', b.dataset.tab === tab);
  renderMain();
  renderDetail(); legend();
}

function renderCases() {
  const sub = S.subject;
  const html = (S.subjects || []).map(s => `<li data-case="${s.id}"${sub && s.id === sub.id ? ' aria-selected="true"' : ''}><b>${esc(s.label)}</b>
      <span>${!s.consent_ok ? '<em class="bad">no consent record</em>' : s.is_self ? 'Self-test' : esc(S.how[s.consent_how])} · ${s.n_identifiers} identifiers, ${s.n_confirmed} confirmed${s.n_leads ? `, ${s.n_leads} leads` : ''}</span></li>`).join('')
    || '<li class="soft">No cases yet.</li>';
  if ($('#cases').dataset.html !== html) { $('#cases').innerHTML = html; $('#cases').dataset.html = html; }
  const info = !sub ? '' : `<p class="consent${sub.consent_ok ? '' : ' bad'}">${sub.is_self ? `<b>Self-test.</b> The owner looks up his own public footprint.`
      : sub.consent_ok ? `<b>Consent:</b> ${esc(S.how[sub.consent_how])} from ${esc(sub.consent_by)} on ${esc(sub.consent_at)}. <b>Scope:</b> ${esc(sub.consent_scope)}`
      : '<b>No complete consent record.</b> Nothing can be checked for this case.'}</p>${sub.note ? `<p class="src">${esc(sub.note)}</p>` : ''}
    <button class="btn danger sm" id="del-case">${armedCase === sub.id ? 'Click again: delete this case and everything in it' : 'Delete this case'}</button>`;
  if ($('#case-info').dataset.html !== info) { $('#case-info').innerHTML = info; $('#case-info').dataset.html = info; }
}

function renderMain() {
  const m = $('#main');
  $('#graph').toggleAttribute('hidden', tab !== 'graph');   // SVG has no .hidden property, only the attribute
  m.hidden = tab === 'graph';
  if (tab === 'graph') { $('#empty').hidden = true; draw(); return; }
  $('#empty').hidden = true;
  findFigures();
  const html = tab === 'leads' ? renderLeads(S) : tab === 'timeline' ? renderTimeline(S, tlConfirmed) : tab === 'dossier' ? dossier(S, G, S.kinds, figures, figNote) : renderList(S, G, filter, picked);
  const y = m.scrollTop;
  if (m.dataset.html !== html || m.dataset.tab !== tab) { m.innerHTML = html; m.dataset.html = html; m.scrollTop = m.dataset.tab === tab ? y : 0; m.dataset.tab = tab; }
}

// the texts with an age in them; refreshed on their own, since the state is not polled while nothing runs
function times() {
  if (!S?.subject) return;
  const t = S.selftest;
  $('#test').textContent = t ? `Tested ${ago(t.tested)}: ${t.trusted} of ${t.total} sites give a correct answer from this computer and will be used. ${t.blind} are skipped (blocked, slow or changed)${t.false_alarm ? `, ${t.false_alarm} of them because they claim a made-up name exists` : ''}.`
    : 'Not tested on this computer yet. The test asks every site about an account known to exist and about a made-up name, and keeps only the sites that get both right. It takes about a minute.';
  const ls = S.last_scan;
  $('#scan-line').textContent = !ls ? 'No scan yet for this case.' : !(ls.summary.checks || []).length && ls.summary.pages_read != null ? `Pages read ${ago(ls.finished)}: ${ls.summary.pages_read} opened, ${ls.summary.pages_dead} dead.`
    : `Last scan ${ago(ls.finished)}: ${ls.summary.findings ?? 0} findings from ${(ls.summary.checks || []).length} checks${ls.summary.pages_read != null ? `, ${ls.summary.pages_read} pages read` : ''}.`;
}
setInterval(times, 30000);

// A full name may belong to a public figure. Their real record (offices, companies, ties) is in the People
// profile, not in username sweeps; offer it at the top of the dossier.
const figures = {}, asked = new Set();
let figNote = '';
function findFigures() {
  if (tab !== 'dossier') return;
  for (const i of S.identifiers.filter(i => i.kind === 'name')) {
    if (asked.has(i.value)) continue;
    asked.add(i.value);
    fetch('/api/people/search?q=' + encodeURIComponent(i.value), {cache: 'no-store'})
      .then(async r => { const d = await r.json().catch(() => ({})); if (!r.ok) throw new Error(d.error || 'Wikidata search failed (' + r.status + ')'); return d; })
      .then(d => { figures[i.value] = (d.results || []).filter(x => x.description).slice(0, 3); figNote = ''; render(); })
      .catch(e => {   // Wikidata often limits requests for a minute: say so and ask again, instead of never showing the record
        figNote = `Public figure record: ${e.message}. Asking again in a minute.`; render();
        setTimeout(() => { asked.delete(i.value); if (S) render(); }, 60000);
      });
  }
  for (const k of Object.keys(figures)) if (!S.identifiers.some(i => i.kind === 'name' && i.value === k)) { delete figures[k]; asked.delete(k); }
}
function setTab(t) { tab = t; store('ww-investigate-tab', t); render(); }

function renderSheet() {
  const p = S.plan, el = $('#sheet');
  if (!chosen) chosen = Object.fromEntries(p.checks.map(c => [c.id, true]));
  for (const k of ['read_pages', 'follow_strong', 'history']) if (!(k in chosen)) chosen[k] = true;
  for (const c of p.checks) if (!(c.id in chosen)) chosen[c.id] = true;
  el.hidden = false;
  const off = c => (c.id === 'wmn' && p.needs_test) || c.needs;
  el.innerHTML = `<b>Choose what runs for “${esc(S.subject.label)}”</b>` + (p.checks.length ? p.checks.map(c => `<label class="pick"><input type="checkbox" data-run="${c.id}" ${chosen[c.id] && !off(c) ? 'checked' : ''}${off(c) ? ' disabled' : ''}>
        <span><strong>${esc(c.name)}</strong> on ${c.count} identifier${c.count > 1 ? 's' : ''}<br>Sends ${esc(c.id === 'wmn' && p.trusted_sites ? 'the username to ' + p.trusted_sites + ' websites that passed the test' : c.sends)}.${c.note ? ' <em>Downloads ' + esc(c.note) + '.</em>' : ''}${c.id === 'wmn' && p.needs_test ? ' <em>Needs "Test the checker" first.</em>' : ''}${c.needs ? ' <em>Needs ' + esc(c.needs) + '.</em>' : ''}</span></label>`).join('')
      + Object.entries(p.options).filter(([k]) => ['read_pages', 'follow_strong', 'history'].includes(k) || p.checks.some(c => k.startsWith(c.id))).map(([k, v]) => `<label class="pick opt"><input type="checkbox" data-run="${k}" ${chosen[k] ? 'checked' : ''}><span>${esc(v)}</span></label>`).join('')
      + (p.unscanned ? `<label class="pick opt"><input type="checkbox" id="only-new" ${onlyNew ? 'checked' : ''}><span>Only the ${p.unscanned} identifiers not scanned yet</span></label>` : '')
      : '<p class="line">Add an identifier first.</p>') +
    `<p class="src" style="margin:8px 0 10px">Maigret, Sherlock, Holehe and theHarvester are the standard open-source tools, run unchanged as separate programs. They are downloaded on first use. Picture files are not sent anywhere: they are compared as files, in this browser.</p>
    <button class="btn primary" id="go" ${p.checks.length ? '' : 'disabled'}>Start</button><button class="btn" id="cancel">Cancel</button>`;
}

// ---- graph: the subject in the middle, identifiers around, findings fanned out behind their identifier ----
// Labels only for the identifiers, confirmed accounts and the dot under the pointer, so a large case stays readable.
function layout() {
  const ids = S.identifiers.filter(i => i.kind !== 'picture'), center = S.subject.is_self ? 'You' : S.subject.label;
  const nodes = [{id: 'me', x: 0, y: 0, r: 16, label: center, big: true, color: 'var(--text)'}], links = [];
  const n = Math.max(ids.length, 1), R1 = ids.length > 1 ? 150 : 0;
  ids.forEach((it, i) => {
    const a0 = -Math.PI / 2 + i * 2 * Math.PI / n, ix = R1 * Math.cos(a0), iy = R1 * Math.sin(a0);
    const idNode = {id: 'i' + it.id, x: ix, y: iy, r: 11, label: it.value, sub: S.kinds[it.kind], big: true, color: 'var(--accent)', ident: it};
    if (ids.length > 1) { nodes.push(idNode); links.push(['me', idNode.id]); } else { nodes[0] = {...idNode, id: 'me', r: 16}; }
    const mine = G.filter(f => f.identifier === it.id && (showHidden || !f.not_me)).sort((a, b) => (b.confirmed || b.bound) - (a.confirmed || a.bound) || a.kind.localeCompare(b.kind) || b.tools.length - a.tools.length);
    const sector = ids.length > 1 ? Math.min(2 * Math.PI / n, Math.PI) * 0.92 : 2 * Math.PI;
    let k = 0, ring = 0;
    while (k < mine.length) {
      const R = R1 + 150 + ring * 110, room = Math.max(1, Math.floor(sector * R / 22)), take = mine.slice(k, k + room);
      take.forEach((f, j) => {
        const a = a0 + (take.length === 1 ? 0 : (j / (ids.length > 1 ? take.length - 1 : take.length) - (ids.length > 1 ? 0.5 : 0)) * sector);
        nodes.push({id: 'f' + f.id, x: R * Math.cos(a), y: R * Math.sin(a), r: 4 + Math.min(3, f.tools.length) * 1.1, a, anchor: f.confirmed || f.bound,
          label: ACCOUNTISH.includes(f.kind) ? siteOf(f) : f.title, color: kindOf(f.kind)[1], finding: f, dim: !!f.not_me});
        links.push([ids.length > 1 ? idNode.id : 'me', 'f' + f.id]);
      });
      k += room; ring++;
    }
  });
  return {nodes, links};
}
function draw() {
  const svg = $('#graph'), {nodes, links} = layout(), by = Object.fromEntries(nodes.map(n => [n.id, n]));
  const w = svg.clientWidth, h = svg.clientHeight, cx = (w + 380) / 2 + view.x, cy = h / 2 + view.y;
  $('#empty').hidden = G.length > 0;
  if (!$('#empty').hidden) $('#empty').textContent = S.identifiers.length ? 'Nothing found yet. Run a scan to see what public sources show about these identifiers.' : 'Add identifiers on the left, then scan. What is found will be drawn here, linked to the identifier it belongs to.';
  const html = `<g transform="translate(${cx},${cy}) scale(${view.k})">` +
    links.map(([a, b]) => `<line x1="${by[a].x}" y1="${by[a].y}" x2="${by[b].x}" y2="${by[b].y}"/>`).join('') +
    nodes.map(n => {
      const deg = n.a == null ? 0 : n.a * 180 / Math.PI, flip = Math.cos(n.a ?? 0) < 0, show = n.big || n.anchor || picked === n.finding?.id;
      const text = n.big ? `<text class="big" x="${n.x}" y="${n.y + n.r + 15}" text-anchor="middle">${esc(n.label)}</text>${n.sub ? `<text x="${n.x}" y="${n.y + n.r + 29}" text-anchor="middle" style="fill:var(--text-2)">${esc(n.sub)}</text>` : ''}`
        : `<text class="${show ? '' : 'lbl'}" transform="translate(${n.x},${n.y}) rotate(${flip ? deg + 180 : deg})" x="${flip ? -11 : 11}" y="4" text-anchor="${flip ? 'end' : 'start'}">${esc(n.label.length > 30 ? n.label.slice(0, 29) + '…' : n.label)}</text>`;
      return `<g class="${n.dim ? 'dim' : ''}"><circle data-node="${n.id}" class="${picked === n.finding?.id ? 'sel' : ''}${n.anchor ? ' anchor' : ''}" cx="${n.x}" cy="${n.y}" r="${n.r}" style="fill:${n.color}"/>${text}</g>`;
    }).join('') + '</g>';
  if (svg.dataset.html !== html) { svg.innerHTML = html; svg.dataset.html = html; }
}
function legend() {
  const hidden = G.filter(f => f.not_me).length, used = [...new Set(G.map(f => f.kind))];
  $('#legend').hidden = !G.length || tab !== 'graph';
  const html = used.map(k => `<span><i style="background:${kindOf(k)[1]}"></i>${kindOf(k)[0]}</span>`).join('') + '<span class="soft">ring: confirmed · larger: found by more tools · labels: confirmed, selected or under the pointer</span>' +
    (hidden ? `<button class="btn" id="toggle-hidden">${showHidden ? 'Hide' : 'Show'} ${hidden} marked not me</button>` : '');
  if ($('#legend').dataset.html !== html) { $('#legend').innerHTML = html; $('#legend').dataset.html = html; }
}

const nice = k => k.replace(/_/g, ' ').replace(/^./, c => c.toUpperCase());
const SKIP = ['what', 'image', 'photo', 'bound', 'email_verified_by', 'linked_from', 'via_account'];
function renderDetail() {
  const el = $('#detail'), f = picked != null && G.find(x => x.id === picked);
  el.hidden = !f; if (!f) return;
  const d = f.detail || {}, idents = f.identifiers.map(id => S.identifiers.find(i => i.id === id)).filter(Boolean);
  const rows = Object.entries(d).filter(([k, v]) => v != null && v !== '' && !SKIP.includes(k) && typeof v !== 'object').map(([k, v]) => `<dt>${esc(nice(k))}</dt><dd>${esc(v)}</dd>`).join('');
  const lists = Object.entries(d).filter(([k, v]) => v && typeof v === 'object' && !SKIP.includes(k)).map(([k, v]) => `<p class="source">${esc(nice(k))}: ${(Array.isArray(v) ? v : [v]).map(x => esc(typeof x === 'object' ? Object.values(x).filter(Boolean).join(', ') : x)).join('; ')}</p>`).join('');
  const pic = picOf(f), fp = pic && S.fingerprints?.[pic];
  const hist = f.history ? `<p class="source">Internet Archive: ${f.history.first ? `oldest copy ${esc(f.history.first)}` : 'no copy found'}${f.history.last && f.history.last !== f.history.first ? `, newest ${esc(f.history.last)}` : ''}.
      ${f.history.bio_then ? `Its description then: “${esc(f.history.bio_then)}”${f.page?.description ? `; now: “${esc(f.page.description)}”` : ''}.` : f.history.bio_note ? esc(f.history.bio_note) + '.' : ''}</p>` : '';
  const html = `<button class="close" id="close" aria-label="Close"></button>
    ${pic ? `<img class="face" src="${esc(proxied(S, pic))}" alt="Picture shown on that page" loading="lazy">` : ''}
    <p class="eyebrow">${esc(kindOf(f.kind)[0])}${f.confirmed ? ' · confirmed' : f.bound ? ' · tied to the case' : f.not_me ? ' · not me' : ''}</p><h2>${esc(ACCOUNTISH.includes(f.kind) ? siteOf(f) : f.title)}</h2>
    <p class="where">${ACCOUNTISH.includes(f.kind) ? esc(f.title) + '<br>' : ''}Found for ${idents.map(i => esc(S.kinds[i.kind].toLowerCase() + ' ' + (i.kind === 'picture' ? 'file' : i.value))).join(', ') || '?'}</p>
    ${f.evidence.length ? `<div class="evs detail-ev">${chips(f.evidence, 20)}</div>` : ACCOUNTISH.includes(f.kind) ? '<p class="source">No evidence ties this to the subject yet; it was found because an identifier matched.</p>' : ''}
    ${d.what ? `<p class="source" style="margin:8px 0 12px;font-size:13px;line-height:16px">${esc(d.what)}</p>` : ''}
    ${rows ? `<dl>${rows}</dl>` : ''}${lists}${hist}
    ${fp ? `<p class="source">${fp.hash ? `Picture fingerprint ${esc(fp.hash)} (compared as a file, not as a face).` : 'The picture could not be read for comparison.'}${fp.location_meta ? ' This picture carries location metadata; it was not read.' : ''}</p>` : ''}
    ${safeUrl(f.url) ? `<a class="link" href="${esc(f.url)}" target="_blank" rel="noopener noreferrer">Open the page</a>` : ''}
    <p class="source">Found by: ${f.tools.map(esc).join(', ')}. First seen ${local(f.first_seen)}, last confirmed ${ago(f.last_seen)}.</p>
    <div class="dbtns">${f.not_me ? `<button class="btn" data-act="undo-notme">This is them after all</button>` : f.confirmed ? `<button class="btn" data-act="unconfirm">Unconfirm</button>`
      : `${f.bound ? '' : `<button class="btn ok" data-act="confirm">Confirmed: same person</button>`}<button class="btn" data-act="notme">Not me</button>`}</div>`;
  if (el.dataset.html === html) return;           // unchanged: keep the card as it is, selection and scroll included
  const y = el.dataset.fid === String(f.id) ? el.scrollTop : 0;
  el.innerHTML = html; el.dataset.html = html; el.dataset.fid = f.id; el.scrollTop = y;
}

// ---- actions ----
const act = async (fn) => { $('#err').hidden = true; $('#note').hidden = true; try { await fn(); } catch (e) { $('#err').hidden = false; $('#err').textContent = e.message; } await load(); };
async function markGroup(g, what) {
  const body = {subject: sid(), ids: g.ids};
  if (what === 'confirm') body.confirmed = true; else if (what === 'unconfirm') body.confirmed = false;
  else if (what === 'notme') body.not_me = true; else body.not_me = false;
  await call('/api/lookup/mark', 'POST', body);
  if (what === 'notme' && picked === g.id) picked = null;
}
function onAct(e) {
  const b = e.target.closest('button[data-act]'); if (!b) return false;
  const fidEl = e.target.closest('[data-fid]'), g = G.find(x => x.id === (fidEl ? +fidEl.dataset.fid : picked));
  if (g) act(() => markGroup(g, b.dataset.act));
  return true;
}
function goto(e) {
  const c = e.target.closest('[data-goto]'); if (!c) return false;
  const g = gOf.get(+c.dataset.goto); if (g != null) { picked = g; render(); }
  return true;
}

$('#add').addEventListener('submit', e => {
  e.preventDefault();
  act(async () => {
    const kind = $('#kind').value;
    if (kind === 'picture') {
      const file = $('#file').files[0];
      if (!file) throw new Error('Choose a picture file first.');
      if (file.size > 5e6) throw new Error('The picture is larger than 5 MB.');
      const data = await new Promise((res, rej) => { const r = new FileReader(); r.onload = () => res(String(r.result).split(',')[1] || ''); r.onerror = () => rej(new Error('The file could not be read.')); r.readAsDataURL(file); });
      const d = await call('/api/lookup/identifiers', 'POST', {subject: sid(), kind, data, name: file.name});
      $('#file').value = ''; fpTried.delete(sid());
      if (d.location_meta) { $('#note').hidden = false; $('#note').textContent = 'This picture carries location metadata. It was not read, is not shown and is never sent anywhere.'; }
      return;
    }
    await call('/api/lookup/identifiers', 'POST', {subject: sid(), kind, value: $('#value').value}); $('#value').value = '';
  });
});
$('#kind').addEventListener('change', () => { const pic = $('#kind').value === 'picture'; $('#value').hidden = pic; $('#file').hidden = !pic; });
$('#ids').addEventListener('click', e => { const b = e.target.closest('button[data-id]'); if (b) act(() => call('/api/lookup/identifiers/' + b.dataset.id, 'DELETE')); });
$('#run-test').onclick = () => act(() => call('/api/lookup/run/selftest', 'POST'));
$('#read-pages').onclick = () => act(async () => { const d = await call('/api/lookup/run/read', 'POST', {subject: sid()}); $('#note').hidden = !d.note; $('#note').textContent = d.note || ''; });
document.querySelector('.tabs').addEventListener('click', e => { const b = e.target.closest('[data-tab]'); if (b) setTab(b.dataset.tab); });
$('#main').addEventListener('click', e => {
  const fig = e.target.closest('[data-qid]'); if (fig) { openProfile(fig.dataset.qid); return; }
  const fb = e.target.closest('[data-filter]'); if (fb) { filter = fb.dataset.filter; render(); return; }
  const tb = e.target.closest('[data-tl]'); if (tb) { tlConfirmed = tb.dataset.tl === 'confirmed'; render(); return; }
  const lb = e.target.closest('button[data-lact]');
  if (lb) { const id = lb.closest('[data-lead]').dataset.lead; act(() => call('/api/lookup/leads/' + id, 'POST', {subject: sid(), action: lb.dataset.lact})); return; }
  if (onAct(e) || goto(e) || e.target.closest('a')) return;
  const c = e.target.closest('[data-fid]'); if (!c) return;
  picked = gOf.get(+c.dataset.fid) ?? +c.dataset.fid; render();
});
$('#plan').onclick = () => { sheetOpen = true; renderSheet(); };
$('#sheet').addEventListener('change', e => {
  if (e.target.id === 'only-new') { onlyNew = e.target.checked; return; }
  const k = e.target.dataset.run; if (k) { chosen[k] = e.target.checked; store('ww-lookup-run', chosen); }
});
$('#sheet').addEventListener('click', e => {
  if (e.target.id === 'cancel') { sheetOpen = false; $('#sheet').hidden = true; }
  if (e.target.id === 'go') {
    sheetOpen = false; $('#sheet').hidden = true;
    const run = Object.keys(chosen).filter(k => chosen[k] && !S.plan.checks.some(c => c.id === k && ((k === 'wmn' && S.plan.needs_test) || c.needs)));
    act(() => call('/api/lookup/run/scan', 'POST', {subject: sid(), run, only_new: onlyNew && !!S.plan.unscanned}));
  }
});
let armed = 0, armedCase = null;
$('#wipe').onclick = () => {   // two clicks within five seconds: the page cannot show a system confirm box everywhere
  if (Date.now() - armed < 5000) { armed = 0; $('#wipe').textContent = 'Delete all cases'; picked = null; act(() => call('/api/lookup/wipe', 'POST')); }
  else { armed = Date.now(); $('#wipe').textContent = 'Click again to delete every case'; setTimeout(() => { if (armed) { armed = 0; $('#wipe').textContent = 'Delete all cases'; } }, 5000); }
};
$('#case-info').addEventListener('click', e => {
  if (e.target.id !== 'del-case') return;
  const id = sid();
  if (armedCase === id) { armedCase = null; picked = null; act(async () => { await call('/api/lookup/subjects/' + id, 'DELETE'); caseId = null; store('ww-investigate-case'); }); }
  else { armedCase = id; renderCases(); setTimeout(() => { if (armedCase === id) { armedCase = null; if (S) renderCases(); } }, 5000); }
});
$('#cases').addEventListener('click', e => {
  const li = e.target.closest('[data-case]'); if (!li) return;
  caseId = li.dataset.case; store('ww-investigate-case', caseId); picked = null; sheetOpen = false; $('#sheet').hidden = true; lastSig = ''; load();
});
// the new-case sheet: a case exists only with its consent record
$('#new-case').onclick = () => {
  const hasSelf = (S?.subjects || []).some(s => s.is_self);
  $('#cf-self').checked = false; $('#cf-self').disabled = hasSelf; $('#cf-self-note').textContent = hasSelf ? 'There is already a self-test case.' : '';
  $('#cf-at').value = new Date().toISOString().slice(0, 10); $('#cf-at').max = $('#cf-at').value;
  $('#case-err').hidden = true; selfToggle(); $('#case-sheet').hidden = false; $('#cf-label').focus();
};
function selfToggle() { const me = $('#cf-self').checked; $('#cf-consent').disabled = me; $('#cf-consent').classList.toggle('dim', me); }
$('#cf-self').addEventListener('change', selfToggle);
$('#cf-cancel').onclick = () => { $('#case-sheet').hidden = true; };
$('#case-form').addEventListener('submit', async e => {
  e.preventDefault();
  try {
    const d = await call('/api/lookup/subjects', 'POST', {label: $('#cf-label').value, self: $('#cf-self').checked, consent_by: $('#cf-by').value, consent_at: $('#cf-at').value,
      consent_how: $('#cf-how').value, consent_scope: $('#cf-scope').value, note: $('#cf-note').value});
    $('#case-sheet').hidden = true; $('#case-form').reset();
    caseId = String(d.id); store('ww-investigate-case', caseId); picked = null; lastSig = ''; load();
  } catch (err) { $('#case-err').hidden = false; $('#case-err').textContent = err.message; }
});
$('#detail').addEventListener('click', e => {
  if (e.target.id === 'close') { picked = null; render(); return; }
  if (goto(e)) return;
  onAct(e);
});
$('#legend').addEventListener('click', e => { if (e.target.id === 'toggle-hidden') { showHidden = !showHidden; render(); } });

// pan with drag, zoom with the wheel or a pinch; a dot's hidden label shows under the pointer (CSS only, no redraw)
const svg = $('#graph'); let drag = null;
svg.addEventListener('pointerdown', e => { const n = e.target.dataset?.node; if (n) { picked = n.startsWith('f') ? gOf.get(+n.slice(1)) ?? +n.slice(1) : null; render(); return; } drag = {x: e.clientX - view.x, y: e.clientY - view.y}; svg.setPointerCapture(e.pointerId); });
svg.addEventListener('pointermove', e => { if (drag) { view.x = e.clientX - drag.x; view.y = e.clientY - drag.y; draw(); } });
svg.addEventListener('pointerup', () => { drag = null; });
svg.addEventListener('wheel', e => { e.preventDefault(); view.k = Math.min(4, Math.max(0.2, view.k * (e.deltaY < 0 ? 1.1 : 1 / 1.1))); draw(); }, {passive: false});
addEventListener('resize', () => S?.subject && tab === 'graph' && draw());
addEventListener('keydown', e => {
  if (e.key !== 'Escape') return;
  if (!$('#case-sheet').hidden) { $('#case-sheet').hidden = true; return; }
  if (document.getElementById('profile') && !document.getElementById('profile').hidden) return;
  if (picked != null) { picked = null; render(); }
});

load();
document.addEventListener('visibilitychange', () => { if (document.visibilityState === 'visible') load(); });
addEventListener('focus', () => load());
