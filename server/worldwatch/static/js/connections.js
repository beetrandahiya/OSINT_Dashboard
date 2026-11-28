// Connections: who owns whom. Search a company (or arrive from a ship or aircraft on the map), then the page walks
// up through every owner the registers name, level by level, and shows what each owner holds besides. Every link
// carries the source that states it. Nothing is joined on a name alone; same-name records are shown as candidates.
import {suiteNav} from './suite.js';
import * as CM from './connections-map.js';

const $ = s => document.querySelector(s);
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[c]));
const SRC = s => (s || '').split(' ')[0];            // "Offshore Leaks" -> CSS class "Offshore"
const KIND = {company: 'Company', organisation: 'Organisation', person: 'Person', state: 'State body', intermediary: 'Intermediary', bearer: 'Bearer shares', sanctioned: 'Sanctioned'};
const GLYPH = {company: 'C', organisation: 'O', person: 'P', state: 'S', intermediary: 'I', bearer: 'B', sanctioned: '!'};
const MAX_UP = 12, MAX_FETCH = 60, SIBLINGS = 6, FOCUS_KIDS = 40, ROW = 10;

$('#top').innerHTML = `<div class="suite-title">World Watch</div>${suiteNav('Connections')}
  <div class="suite-search"><input id="q" type="search" placeholder="Search a company, LEI code or Wikidata id" autocomplete="off" spellcheck="false"></div>
  <div class="seg" id="mode" role="group" aria-label="View"><button data-mode="graph" aria-pressed="true">Graph</button><button data-mode="map" aria-pressed="false">On the map</button></div>`;
const GRAPH_LEGEND = `<h4>Who says so</h4>
  <div style="color:var(--src-gleif)"><i></i>GLEIF register</div><div style="color:var(--src-wd)"><i></i>Wikidata</div>
  <div style="color:var(--src-icij)"><i></i>Offshore Leaks (ICIJ)</div><div style="color:var(--src-os)"><i></i>OpenSanctions</div>
  <div><i class="dash"></i>ultimate parent (links between not reported), or same name only</div>
  <h4 style="margin-top:10px">Owner above, holding below</h4>`;
$('#legend').innerHTML = GRAPH_LEGEND;

// ---------------------------------------------------------------- state
const nodes = new Map();      // ref -> {ref, name, kind, country, data (full node when fetched), level, stub}
const edges = new Map();      // owner|asset -> {from, to, label, source, share, ultimate}
let focus = null, selected = null, walkId = 0;

async function api(path) {
  const r = await fetch(path, {cache: 'no-store'});
  const d = await r.json().catch(() => ({error: `HTTP ${r.status}`}));
  if (!r.ok && !d.error) d.error = `HTTP ${r.status}`;
  return d;
}

// ---------------------------------------------------------------- search
let qTimer = 0;
$('#q').addEventListener('input', e => { clearTimeout(qTimer); const v = e.target.value.trim(); if (v.length >= 2) qTimer = setTimeout(() => search(v), 400); });
$('#q').addEventListener('keydown', e => { if (e.key === 'Enter') { clearTimeout(qTimer); search(e.target.value.trim()); } });
async function search(q) {
  if (!q) return;
  history.replaceState(null, '', '?q=' + encodeURIComponent(q));
  $('#panel').innerHTML = `<p class="soft">Searching GLEIF, Wikidata, Offshore Leaks and the sanctions lists for “${esc(q)}”…</p>`;
  const d = await api('/api/connections/search?q=' + encodeURIComponent(q));
  const by = {};
  for (const r of d.results || []) (by[r.source] ||= []).push(r);
  const order = ['GLEIF', 'Wikidata', 'Offshore Leaks', 'OpenSanctions'];
  $('#panel').innerHTML = `<div class="kind">Search</div><h2>${esc(q)}</h2>` +
    (d.results?.length ? '' : '<p class="soft">Nothing found in any source.</p>') +
    order.filter(s => by[s]).map(s => `<div class="res-group"><h3><span class="src src-${SRC(s)}">${s}</span> ${by[s].length}</h3><ul class="rows">${by[s].map(r =>
      `<li data-ref="${esc(r.ref || '')}"><span class="t">${esc(r.name)}</span><span class="faint">${esc(KIND[r.kind] || '')}</span><span class="m">${esc([r.country, r.note].filter(Boolean).join(' · '))}</span></li>`).join('')}</ul></div>`).join('') +
    problems(d.problems) + (d.icij === false ? '<p class="note">Offshore Leaks is not imported yet on this computer (it downloads and imports by itself once; see Sources).</p>' : '') +
    '<p class="note">GLEIF lists companies with an LEI code (banks, listed and large companies, funds, their subsidiaries). Offshore Leaks lists offshore companies, their shareholders, officers and agents from the Panama, Paradise and Pandora Papers and earlier leaks; its people are searchable only through the companies they are linked to.</p>';
}
$('#panel').addEventListener('click', e => {
  const li = e.target.closest('[data-ref]'); if (li?.dataset.ref) return go(li.dataset.ref);
  const b = e.target.closest('[data-act]'); if (!b) return;
  if (b.dataset.act === 'center') go(b.dataset.ref);
  if (b.dataset.act === 'more') moreGleif(b);
  if (b.dataset.act === 'q') { $('#q').value = b.dataset.q; search(b.dataset.q); }
});

// ---------------------------------------------------------------- walking the structure
function go(ref) { history.pushState(null, '', '?ref=' + encodeURIComponent(ref)); start(ref); }
addEventListener('popstate', route);

// one company can arrive under two refs (its Wikidata id first, its LEI once the registers are joined): every alias
// points at the canonical ref the server gave
const alias = new Map();
const R = ref => alias.get(ref) || ref;
function put(ref, info, level) {
  ref = R(ref);
  let n = nodes.get(ref);
  if (!n) { n = {ref, name: info.name || ref, kind: info.kind || 'organisation', country: info.country, level, sanc: false}; nodes.set(ref, n); }
  else if (level !== undefined && (n.level === undefined || (level < 0 && level < n.level))) n.level = level;
  return n;
}
function link(from, to, e) {
  from = R(from); to = R(to);
  if (from === to) return;
  const k = from + '|' + to;
  if (!edges.has(k)) edges.set(k, {from, to, label: e.label, source: e.source, share: e.share, ultimate: !!e.ultimate || !!e.samename});
}

async function start(ref) {
  const id = ++walkId;
  nodes.clear(); edges.clear(); focus = ref; selected = ref;
  $('#stage-empty').textContent = 'Reading the registers…';
  draw(true);
  const first = await fetchNode(ref, 0, id);
  if (id !== walkId) return;
  if (!first || first.error) { $('#panel').innerHTML = `<p class="problems">${esc(first?.error || 'No answer')}</p>`; $('#stage-empty').textContent = ''; return; }
  focus = first.ref; selected = first.ref;
  showPanel(first.ref);
  // holdings of the entity itself
  first.holdings.slice(0, FOCUS_KIDS).forEach(h => { put(h.ref, h, 1); link(first.ref, h.ref, h); });
  if (first.holdings_count > FOCUS_KIDS) stub(first.ref, first.holdings_count - FOCUS_KIDS, 1);
  draw(true);
  // up, level by level; each owner's other holdings beside it
  let frontier = [first], fetched = 1;
  for (let lvl = -1; lvl >= -MAX_UP && frontier.length && fetched < MAX_FETCH; lvl--) {
    const next = [];
    for (const n of frontier) for (const o of n.owners) { put(o.ref, o, lvl); link(o.ref, n.ref, o); if (!nodes.get(R(o.ref)).data && !next.some(x => R(x.ref) === R(o.ref))) next.push(o); }
    draw();
    $('#walk').textContent = `walking up: level ${-lvl}`;
    const got = await pool(next.slice(0, MAX_FETCH - fetched), 3, o => fetchNode(o.ref, lvl, id));
    if (id !== walkId) return;
    fetched += got.length;
    frontier = got.filter(x => x && !x.error);
    for (const n of frontier) {
      let shown = 0;
      for (const h of n.holdings) {
        if (nodes.has(R(h.ref))) { link(n.ref, h.ref, h); continue; }
        if (shown++ >= SIBLINGS) break;
        put(h.ref, h, lvl + 1); link(n.ref, h.ref, h);
      }
      const rest = n.holdings_count - shown - n.holdings.filter(h => nodes.has(R(h.ref))).length;
      if (rest > 0) stub(n.ref, rest, lvl + 1);
      n.exceptions.forEach(x => { const r = 'exc:' + n.ref + ':' + x.level; put(r, {name: x.text, kind: 'exc'}, lvl - 1); nodes.get(r).exc = x; link(r, n.ref, {label: x.level === 'ultimate' ? 'above the top' : 'above it', source: x.source}); });
    }
    draw();
  }
  // exceptions of the entity itself (its own owner withheld)
  first.exceptions.forEach(x => { const r = 'exc:' + first.ref + ':' + x.level; put(r, {name: x.text, kind: 'exc'}, -1); nodes.get(r).exc = x; link(r, first.ref, {label: 'above it', source: x.source}); });
  $('#walk').textContent = fetched >= MAX_FETCH ? `stopped after ${MAX_FETCH} entities` : '';
  if (CM.isOpen()) CM.refresh(true);
  $('#stage-empty').textContent = nodes.size <= 1 && !first.owners.length && !first.holdings.length ? 'No owner or holding is recorded for this entity in the sources read.' : '';
  draw(true);
}

function stub(parent, count, level) {
  const r = 'more:' + parent;
  put(r, {name: `+${count.toLocaleString('en-GB')} more`, kind: 'stub'}, level).stub = parent;
  link(parent, r, {label: '', source: ''});
}

async function fetchNode(ref, level, id) {
  const d = await api('/api/connections/node?ref=' + encodeURIComponent(ref));
  if (id !== undefined && id !== walkId) return null;
  if (d.error) return d;
  const names = new Map([[ref, d.ref], ...(d.refs || []).map(r => [r, d.ref])]);
  for (const e of [...(d.owners || []), ...(d.holdings || [])]) for (const a of e.alias || []) names.set(a, e.ref);
  for (const [a, to] of names) if (a !== to) alias.set(a, to);
  const n = put(d.ref, d, level);
  for (const [a, to] of names) if (a !== to && nodes.has(a)) merge(a, to);       // the same entity under its canonical ref
  Object.assign(n, {name: d.name, kind: d.kind, country: d.country, data: d, sanc: (d.sanctions || []).some(s => !/same name/.test(s.match))});
  return d;
}

function merge(from, to) {
  const old = nodes.get(from), keep = put(to, old, old.level);
  if (old.level !== undefined) keep.level = Math.min(keep.level ?? old.level, old.level);
  nodes.delete(from);
  const moved = [...edges.values()].map(e => ({...e, from: R(e.from === from ? to : e.from), to: R(e.to === from ? to : e.to)}));
  edges.clear();
  for (const e of moved) if (e.from !== e.to && !edges.has(e.from + '|' + e.to)) edges.set(e.from + '|' + e.to, e);
  if (focus === from) focus = to; if (selected === from) selected = to;
}

async function pool(items, k, fn) {
  const out = []; let i = 0;
  await Promise.all(Array.from({length: Math.min(k, items.length)}, async () => { while (i < items.length) { const it = items[i++]; out.push(await fn(it)); } }));
  return out;
}

// ---------------------------------------------------------------- panel
const problems = list => list?.length ? `<p class="problems">${list.map(esc).join('<br>')}</p>` : '';
function edgeRow(e, dirWord) {
  const bits = [e.label, e.share ? `share ${(+e.share * (e.share <= 1 ? 100 : 1)).toFixed(e.share <= 1 ? 1 : 0)} %` : '', e.start ? `from ${e.start}` : '', e.end ? `until ${e.end}` : '', e.leak, e.desc].filter(Boolean);
  const also = (e.also || []).map(a => `${a.label} (${a.source})`).join('; ') + (e.joined ? (e.also?.length ? '; ' : '') + e.joined : '');
  return `<li data-ref="${esc(e.ref)}"><span class="t">${esc(e.name)}</span><span class="src src-${SRC(e.source)}">${esc(e.source)}</span>
    <span class="m">${esc(KIND[e.kind] || e.kind || '')}${e.country ? ' · ' + esc(e.country) : ''} · ${esc(bits.join(' · '))}${also ? ' · also: ' + esc(also) : ''}</span></li>`;
}
async function showPanel(ref) {
  const n = nodes.get(ref);
  if (!n) return;
  if (n.kind === 'stub') return showStub(n);
  if (n.exc) { $('#panel').innerHTML = `<div class="kind">Where the register stops</div><h2>${esc(n.name)}</h2><p class="soft">${esc(n.exc.source)} reason code ${esc(n.exc.code)} (${n.exc.level} parent). The company itself reports this to the register; it is a statement, not a finding.</p>`; return; }
  if (!n.data) { $('#panel').innerHTML = '<p class="soft">Reading…</p>'; await fetchNode(ref); draw(); }
  const d = n.data;
  if (!d || d.error) { $('#panel').innerHTML = `<p class="problems">${esc(d?.error || 'No answer')}</p>`; return; }
  const bySrc = {};
  for (const f of d.facts) (bySrc[f.source] ||= []).push(f);
  const totals = Object.entries(d.holdings_total || {}).filter(([, v]) => v).map(([k, v]) => `${k} ${v.toLocaleString('en-GB')}`).join(', ');
  const gleifMore = (d.holdings_total?.GLEIF || 0) > 50 ? d.refs.find(r => r.startsWith('lei:')) : null;
  $('#panel').innerHTML = `<div class="fade-in">
    <div class="kind">${esc(KIND[d.kind] || d.kind)}${d.country ? ' · ' + esc(d.country) : ''}</div>
    <div class="p-head"><h2>${esc(d.name)}</h2></div>
    <div class="links" style="margin-top:8px">${d.refs.map(r => `<span class="pill">${esc(r)}</span>`).join('')}${d.ref !== focus ? `<button class="btn" data-act="center" data-ref="${esc(d.ref)}">Centre the structure here</button>` : ''}</div>
    ${d.sanctions?.length ? `<div class="sec flag-sanc"><b>On sanctions lists</b>${d.sanctions.map(s => `<div style="margin-top:6px"><a href="${esc(s.url)}" target="_blank" rel="noopener">${esc(s.name)}</a> · ${esc(s.match)}<br><span class="soft">${esc(s.lists.join(', '))}${s.since ? ' · listed since ' + esc(s.since) : ''}</span></div>`).join('')}</div>` : ''}
    ${d.exceptions?.length ? `<div class="sec">${d.exceptions.map(x => `<div class="exc">${x.level === 'ultimate' ? 'Ultimate' : 'Direct'} owner: ${esc(x.text)} <span class="src src-${SRC(x.source)}">${esc(x.source)}</span></div>`).join('')}</div>` : ''}
    <div class="sec"><h3>Owned by <span class="n-count">${d.owners.length || 'none recorded'}</span></h3><ul class="rows">${d.owners.map(e => edgeRow(e)).join('')}</ul></div>
    <div class="sec"><h3>Owns <span class="n-count">${d.holdings_count ? d.holdings_count.toLocaleString('en-GB') : 'none recorded'}${totals ? ' (' + esc(totals) + ')' : ''}</span></h3><ul class="rows" id="hold">${d.holdings.map(e => edgeRow(e)).join('')}</ul>
      ${gleifMore ? `<button class="btn" data-act="more" data-lei="${esc(gleifMore.slice(4))}" data-page="2">Load more subsidiaries from GLEIF</button>` : ''}</div>
    ${d.roles?.length ? `<div class="sec"><h3>People and firms around it <span class="n-count">${d.roles.length}</span></h3><ul class="rows">${d.roles.map(e => edgeRow({...e, label: e.label + ' (' + e.dir + ')'})).join('')}</ul></div>` : ''}
    ${d.related?.length ? `<div class="sec"><h3>Records ICIJ links to it <span class="n-count">${d.related.length}</span></h3><ul class="rows">${d.related.map(e => edgeRow(e)).join('')}</ul></div>` : ''}
    ${Object.entries(bySrc).map(([s, fs]) => `<div class="sec"><h3><span class="src src-${SRC(s)}">${esc(s)}</span></h3><dl class="facts">${fs.map(f => `<dt>${esc(f.label)}</dt><dd>${/^https?:/.test(f.value) ? `<a href="${esc(f.value)}" target="_blank" rel="noopener">${esc(f.value)}</a>` : esc(f.value)}</dd>`).join('')}</dl></div>`).join('')}
    <div class="sec links">${d.links.map(l => `<a href="${esc(l.url)}" target="_blank" rel="noopener">${esc(l.label)}</a>`).join('')}</div>
    ${d.joins?.length ? `<div class="sec"><h3>Joined across registers</h3>${d.joins.map(j => `<p class="soft">${j.refs.map(esc).join(' = ')}: no shared LEI; same name, and ${esc(j.how)}.</p>`).join('')}</div>` : ''}
    ${d.dissolved_left_out?.length ? `<p class="soft">Left out, as Wikidata gives them as dissolved: ${esc(d.dissolved_left_out.join(', '))}.</p>` : ''}
    ${(d.notes || []).map(n => `<p class="soft">${esc(n)}.</p>`).join('')}
    ${problems(d.problems)}
    <p class="note">${d.refs.some(r => r.startsWith('icij:')) ? 'Offshore Leaks records come from leaked files dated 2013-2021; ownership may have changed since. ' : ''}Records from two registers are joined on a shared LEI code, or, where Wikidata lacks it, on the same name when both registers place the company in the same group. Ended and dissolved holdings are left out. Read ${d.cached ? 'from this server\'s copy of ' : ''}${new Date((d.built || Date.now() / 1000) * 1000).toLocaleString('en-GB', {dateStyle: 'medium', timeStyle: 'short'})}.</p>
  </div>`;
}
function showStub(n) {
  const p = nodes.get(n.stub)?.data;
  $('#panel').innerHTML = `<div class="kind">Holdings</div><h2>${esc(p?.name || '')}</h2><p class="soft">${esc(n.name)} not drawn in the structure. All listed holdings:</p><ul class="rows">${(p?.holdings || []).map(e => edgeRow(e)).join('')}</ul>`;
}
async function moreGleif(b) {
  b.disabled = true; b.textContent = 'Loading…';
  const d = await api(`/api/connections/holdings?lei=${b.dataset.lei}&page=${b.dataset.page}`);
  if (d.error) { b.textContent = d.error; return; }
  $('#hold').insertAdjacentHTML('beforeend', d.items.map(e => edgeRow(e)).join(''));
  const page = +b.dataset.page;
  if (page * 50 < d.total) { b.dataset.page = page + 1; b.disabled = false; b.textContent = `Load more (${(d.total - page * 50).toLocaleString('en-GB')} left)`; } else b.remove();
}

// ---------------------------------------------------------------- drawing
const W = 196, H = 50, GX = 28, GY = 96;
let view = {x: 0, y: 0, k: 1}, laid = new Map(), fitPending = true, frame = 0;
function draw(fit) { if (fit) fitPending = true; if (!frame) frame = requestAnimationFrame(() => { frame = 0; layout(); render(); if (fitPending) { fitPending = false; fitView(); } }); }

function layout() {
  // rows by level; levels with many items wrap into several rows of ROW
  const lv = new Map();
  for (const n of nodes.values()) { const l = n.level ?? 0; (lv.get(l) || lv.set(l, []).get(l)).push(n); }
  const levels = [...lv.keys()].sort((a, b) => a - b);
  const pos = new Map();
  // order: parents' x (barycentre) for lower levels; first pass by insertion
  let y = 0;
  for (const l of levels) {
    const row = lv.get(l);
    const bx = n => { const ps = [...edges.values()].filter(e => e.to === n.ref && pos.has(e.from)).map(e => pos.get(e.from).x); const cs = [...edges.values()].filter(e => e.from === n.ref && pos.has(e.to)).map(e => pos.get(e.to).x); const a = ps.length ? ps : cs; return a.length ? a.reduce((s, v) => s + v, 0) / a.length : 0; };
    if (l > levels[0]) row.sort((a, b) => bx(a) - bx(b));
    const fi = row.findIndex(n => n.ref === focus);             // the entity in the middle of its row, siblings either side
    if (fi >= 0 && row.length > 2) { const [f] = row.splice(fi, 1); row.splice(Math.floor(Math.min(row.length, ROW - 1) / 2), 0, f); }
    for (let i = 0; i < row.length; i += ROW) {
      const chunk = row.slice(i, i + ROW), width = chunk.length * (W + GX) - GX;
      chunk.forEach((n, j) => pos.set(n.ref, {x: -width / 2 + j * (W + GX), y}));
      y += GY * (i + ROW < row.length ? 0.72 : 1);
    }
  }
  // second pass: pull owner rows above their children (barycentre from below)
  for (const l of levels.slice(0, -1).reverse()) {
    const row = lv.get(l); if (row.length > ROW) continue;
    const cx = n => { const cs = [...edges.values()].filter(e => e.from === n.ref && pos.has(e.to)).map(e => pos.get(e.to).x); return cs.length ? cs.reduce((s, v) => s + v, 0) / cs.length : pos.get(n.ref).x; };
    const ys = pos.get(row[0].ref).y, want = row.map(n => [n, cx(n)]).sort((a, b) => a[1] - b[1]);
    let last = -Infinity;
    for (const [n, x] of want) { const nx = Math.max(x, last + W + GX); pos.set(n.ref, {x: nx, y: ys}); last = nx; }
  }
  laid = pos;
}

const SHORT = [[/^direct parent/, 'parent'], [/^direct subsidiary/, 'subsidiary'], [/^ultimate parent/, 'ultimate parent'], [/^same name as/, 'same name only'],
  [/^owned by it/, 'owned by it'], [/^names it as parent/, 'parent'], [/^lists it as a subsidiary/, 'parent'], [/^says it owns it/, 'owner']];
function short(l) { l = l || ''; for (const [re, t] of SHORT) if (re.test(l)) return t; return l; }
function trunc(s, n) { s = String(s || ''); return s.length > n ? s.slice(0, n - 1) + '…' : s; }
let chain = new Set(), fan = new Map();
function ancestors() {          // the entity and everything above it
  chain = new Set([focus]); fan = new Map();
  for (const e of edges.values()) fan.set(e.from, (fan.get(e.from) || 0) + 1);
  let grew = true;
  while (grew) { grew = false; for (const e of edges.values()) if (chain.has(e.to) && !chain.has(e.from)) { chain.add(e.from); grew = true; } }
}
function render() {
  ancestors();
  const eg = [], ng = [];
  for (const e of edges.values()) {
    const a = laid.get(e.from), b = laid.get(e.to); if (!a || !b) continue;
    const x1 = a.x + W / 2, y1 = a.y + H, x2 = b.x + W / 2, y2 = b.y, my = (y1 + y2) / 2;
    eg.push(`<path class="e ${SRC(e.source)}${e.ultimate ? ' ult' : ''}" d="M${x1},${y1} C${x1},${my} ${x2},${my} ${x2},${y2}"/>`);
    const lab = [short(e.label), e.share ? `${(+e.share * (e.share <= 1 ? 100 : 1)).toFixed(0)} %` : ''].filter(Boolean).join(' · ');
    // labels only where they can be read (links of the chain to the entity, single links), next to the lower end
    if (lab && (chain.has(e.to) || (fan.get(e.from) || 0) <= 1)) eg.push(`<text class="el" x="${x2}" y="${y2 - 9}">${esc(trunc(lab, 30))}</text>`);
  }
  for (const n of nodes.values()) {
    const p = laid.get(n.ref); if (!p) continue;
    const cls = ['n', 'k-' + n.kind, n.ref === focus ? 'focus' : '', n.ref === selected ? 'sel' : '', n.sanc ? 'sanc' : '', n.kind === 'stub' ? 'stub' : '', n.exc ? 'exc' : ''].filter(Boolean).join(' ');
    const sub = n.exc ? (n.exc.source + ' says') : n.kind === 'stub' ? 'click to list them' : [KIND[n.kind] || '', n.country, n.sanc ? 'SANCTIONED' : ''].filter(Boolean).join(' · ');
    ng.push(`<g class="${cls}" data-ref="${esc(n.ref)}" transform="translate(${p.x},${p.y})">
      <rect class="ring" x="-5" y="-5" width="${W + 10}" height="${H + 10}" rx="17" fill="none"/>
      <rect class="box" width="${W}" height="${H}" rx="13"/>
      ${n.kind !== 'stub' && !n.exc ? `<circle class="k" cx="20" cy="${H / 2}" r="10"/><text class="glyph" x="20" y="${H / 2 + 4}">${GLYPH[n.kind] || '·'}</text>` : ''}
      <text x="${n.kind !== 'stub' && !n.exc ? 38 : 14}" y="21">${esc(trunc(n.name, n.exc ? 30 : 23))}</text>
      <text class="sub" x="${n.kind !== 'stub' && !n.exc ? 38 : 14}" y="37">${esc(trunc(sub, 32))}</text>
      <title>${esc(n.name)}</title></g>`);
  }
  $('#edges').innerHTML = eg.join(''); $('#nodes').innerHTML = ng.join('');
  apply();
}

// pan and zoom
const svg = $('#graph');
function apply() { $('#world').setAttribute('transform', `translate(${view.x},${view.y}) scale(${view.k})`); }
function fitView() {
  if (!laid.size) return;
  const xs = [...laid.values()].map(p => p.x), ys = [...laid.values()].map(p => p.y);
  const minx = Math.min(...xs) - 40, maxx = Math.max(...xs) + W + 40, miny = Math.min(...ys) - 40, maxy = Math.max(...ys) + H + 40;
  const left = innerWidth > 900 ? 500 : 16, availW = innerWidth - left - 290, availH = innerHeight - 140;
  const all = Math.min(availW / (maxx - minx), availH / (maxy - miny));
  if (all >= 0.8) {                                   // everything fits at a readable size
    view.k = Math.min(1.2, all);
    view.x = left + (availW - (maxx - minx) * view.k) / 2 - minx * view.k;
    view.y = 90 + (availH - (maxy - miny) * view.k) / 2 - miny * view.k;
  } else {                                            // too big: readable size, centred on the entity and its owners
    view.k = 0.8;
    const core = [...chain].map(r => laid.get(r)).filter(Boolean);
    const cx = core.length ? (Math.min(...core.map(p => p.x)) + Math.max(...core.map(p => p.x)) + W) / 2 : (minx + maxx) / 2;
    const top = core.length ? Math.min(...core.map(p => p.y)) - 40 : miny;
    view.x = left + availW / 2 - cx * view.k;
    view.y = 100 - top * view.k;
  }
  apply();
}
let drag = null;
svg.addEventListener('pointerdown', e => { drag = {x: e.clientX, y: e.clientY, vx: view.x, vy: view.y, moved: false}; svg.setPointerCapture(e.pointerId); });
svg.addEventListener('pointermove', e => { if (!drag) return; const dx = e.clientX - drag.x, dy = e.clientY - drag.y; if (Math.abs(dx) + Math.abs(dy) > 3) { drag.moved = true; svg.classList.add('drag'); } view.x = drag.vx + dx; view.y = drag.vy + dy; apply(); });
svg.addEventListener('pointerup', e => {
  const was = drag; drag = null; svg.classList.remove('drag');
  if (was && !was.moved) { const g = document.elementFromPoint(e.clientX, e.clientY)?.closest('.n'); if (g) { selected = g.dataset.ref; render(); showPanel(selected); } }
});
svg.addEventListener('dblclick', e => { const g = e.target.closest('.n'); const n = g && nodes.get(g.dataset.ref); if (n && !n.stub && !n.exc) go(n.ref); });
svg.addEventListener('wheel', e => { e.preventDefault(); const k = Math.exp(-e.deltaY * 0.0015), nk = Math.min(3, Math.max(0.1, view.k * k)); view.x = e.clientX - (e.clientX - view.x) * (nk / view.k); view.y = e.clientY - (e.clientY - view.y) * (nk / view.k); view.k = nk; apply(); }, {passive: false});
$('#fit').onclick = fitView;
$('#zin').onclick = () => { view.k = Math.min(3, view.k * 1.25); apply(); };
$('#zout').onclick = () => { view.k = Math.max(0.1, view.k / 1.25); apply(); };

// ---------------------------------------------------------------- assets from the map (?asset=ac:<hex> | imo:<number>)
async function asset(ref) {
  $('#panel').innerHTML = '<p class="soft">Looking up the registered owner…</p>';
  const d = await api('/api/connections/asset?ref=' + encodeURIComponent(ref));
  $('#panel').innerHTML = `<div class="kind">${ref.startsWith('ac:') ? 'Aircraft' : 'Ship'}</div><h2>${esc(d.title || ref)}</h2>
    ${d.facts?.length ? `<div class="sec"><dl class="facts">${d.facts.map(f => `<dt>${esc(f.label)}</dt><dd>${esc(f.value)} <span class="faint">${esc(f.source || '')}</span></dd>`).join('')}</dl></div>` : ''}
    ${(d.sanctions || []).map(s => `<div class="sec flag-sanc"><b>${esc((s.risk || []).join(', '))}</b><br>listed as ${esc(s.name)} · <a href="${esc(s.url)}" target="_blank" rel="noopener">OpenSanctions</a></div>`).join('')}
    ${d.node ? `<div class="sec"><button class="btn primary" data-act="center" data-ref="${esc(d.node)}">Show its ownership structure</button></div>` : ''}
    ${(d.owners || []).map(o => `<div class="sec"><h3>Registered owner: ${esc(o.name)}</h3>${o.note ? `<p class="soft">${esc(o.note)}</p>` : ''}
      ${o.ref ? `<ul class="rows"><li data-ref="${esc(o.ref)}"><span class="t">${esc(o.name)}</span><span class="src src-${SRC(o.source)}">${esc(o.source)}</span><span class="m">${esc(o.label || '')}</span></li></ul>` : ''}
      ${o.candidates?.length ? `<ul class="rows">${o.candidates.filter(c => c.ref).map(c => `<li data-ref="${esc(c.ref)}"><span class="t">${esc(c.name)}</span><span class="src src-${SRC(c.source)}">${esc(c.source)}</span><span class="m">${esc([c.country, c.note].filter(Boolean).join(' · '))}</span></li>`).join('')}</ul>` : ''}</div>`).join('')}
    ${problems(d.problems)}`;
}

// ---------------------------------------------------------------- start
function intro() {
  $('#panel').innerHTML = `<div class="intro"><div class="kind">Connections</div><h2>Who owns whom</h2>
    <p>Search a company. The structure walks up through every owner the registers name, then shows what each owner holds besides. Every line says which register states it.</p>
    <p class="soft">Sources: GLEIF (companies with LEI codes and their parents), Wikidata (owned by, parent, subsidiary), ICIJ Offshore Leaks (offshore companies, shareholders, officers, agents), OpenSanctions (sanctions lists).</p>
    <div class="ex">${['Rosneft', 'Gazprom', 'Glencore', 'Mossack Fonseca', 'Wagner'].map(q => `<button class="btn" data-act="q" data-q="${q}">${q}</button>`).join('')}</div></div>
    <p class="note" id="state"></p>`;
  api('/api/connections/state').then(s => { const el = $('#state'); if (!el) return;
    el.textContent = `Offshore Leaks: ${s.icij?.ready ? 'file of ' + (s.icij.generated || '?').replace(/(\d{4})(\d\d)(\d\d)/, '$1-$2-$3') : 'not imported yet'} · sanctioned companies kept: ${(s.sanctions || 0).toLocaleString('en-GB')} · OpenSanctions key: ${s.opensanctions_key ? 'present' : 'none'}.`; });
}
// ---------------------------------------------------------------- graph or map
let mode = 'graph';
const mapCtx = {
  el: $('#mapview'), api, esc,
  structure: () => ({nodes, edges, focus, selected, alias}),
  setPanel: h => { $('#panel').innerHTML = `<div class="fade-in">${h}</div>`; },
  legend: h => { $('#legend').innerHTML = h; },
  onCompany: async ref => {
    const n = nodes.get(ref);
    if (n && !n.stub && !n.exc) { selected = ref; await showPanel(ref); $('#panel').insertAdjacentHTML('afterbegin', CM.backButton()); return; }
    mapCtx.setPanel(`${CM.backButton()}<div class="kind">Company</div><h2>${esc(ref)}</h2><p class="soft">Not drawn in this structure (it is one level below a company of it).</p>
      <button class="btn primary" data-act="center" data-ref="${esc(ref)}">Open its own structure</button>`);
  },
};
async function setMode(m, push = true) {
  mode = m;
  document.body.classList.toggle('mapmode', m === 'map');
  for (const b of document.querySelectorAll('#mode button')) b.setAttribute('aria-pressed', String(b.dataset.mode === m));
  $('#mapview').hidden = m !== 'map'; $('#map-tools').hidden = m !== 'map';
  if (push) { const u = new URL(location.href); if (m === 'map') u.searchParams.set('view', 'map'); else u.searchParams.delete('view'); history.replaceState(null, '', u); }
  if (m === 'map') {
    if (!focus) { $('#panel').innerHTML = '<p class="soft">Search a company first; its structure is then shown on the map.</p>'; }
    try { await CM.open(mapCtx); } catch (e) { $('#panel').insertAdjacentHTML('afterbegin', `<p class="problems">The map did not load: ${esc(e.message)}</p>`); }
    $('#cx-assets-tb').checked = CM.assetsShown();
  } else {
    CM.close();
    $('#legend').innerHTML = GRAPH_LEGEND;
    if (selected && nodes.get(selected)) showPanel(selected);
    draw(true);
  }
}
$('#mode').addEventListener('click', e => { const b = e.target.closest('[data-mode]'); if (b && b.dataset.mode !== mode) setMode(b.dataset.mode); });
$('#mfit').onclick = () => CM.fit();
$('#cx-assets-tb').addEventListener('change', e => CM.setAssets(e.target.checked));

function route() {
  const u = new URLSearchParams(location.search);
  if (u.get('view') === 'map') setMode('map', false);
  if (u.get('ref')) start(u.get('ref'));
  else if (u.get('asset')) asset(u.get('asset'));
  else if (u.get('q')) { $('#q').value = u.get('q'); search(u.get('q')); }
  else intro();
}
route();
