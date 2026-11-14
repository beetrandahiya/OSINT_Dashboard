// The lookup page: your identifiers in the middle, everything found about them around, as a graph.
import {$, ago, esc, local} from './util.js';

const KIND = {account: ['Account', 'light-dark(#5856d6, #7d7aff)'], breach: ['Breach', 'light-dark(#ff3b30, #ff453a)'], exposure: ['Malware exposure', 'light-dark(#ff9500, #ff9f0a)'],
  registered: ['Registered with this address', 'light-dark(#af52de, #da8fff)'], profile: ['Profile', 'light-dark(#28a745, #30d158)'], key: ['Public key', 'light-dark(#00a3b4, #40c8e0)'],
  code: ['Code', 'light-dark(#8e8e93, #98989d)'], host: ['Host name', 'light-dark(#00a3b4, #40c8e0)'], email: ['Email address found', 'light-dark(#ff2d55, #ff375f)'],
  registration: ['Registration record', 'light-dark(#a2845e, #c4a57b)'], phone: ['Phone number', 'light-dark(#28a745, #30d158)'], mention: ['Web mention', 'light-dark(#8e8e93, #98989d)'],
  url: ['Web address', 'light-dark(#8e8e93, #98989d)'], note: ['Note', 'light-dark(#c7c7cc, #48484a)']};
const kindOf = k => KIND[k] || KIND.code;

// Several tools often find the same page. Those findings become one dot that lists every tool that found it.
const norm = u => (u || '').toLowerCase().replace(/^https?:\/\/(www\.)?/, '').replace(/[/?#]+$/, '');
function grouped() {
  const groups = new Map();
  for (const f of S.findings) {
    const key = f.identifier + '|' + (f.kind === 'account' && f.url ? norm(f.url) : f.tool + '|' + f.key);
    const g = groups.get(key) || {id: f.id, items: [], identifier: f.identifier};
    g.items.push(f); groups.set(key, g);
  }
  return [...groups.values()].map(g => {
    const best = g.items.slice().sort((a, b) => Object.keys(b.detail || {}).length - Object.keys(a.detail || {}).length)[0];
    return {...best, id: g.id, ids: g.items.map(x => x.id), tools: [...new Set(g.items.map(x => x.tool))], not_me: g.items.every(x => x.not_me),
            first_seen: Math.min(...g.items.map(x => x.first_seen)), last_seen: Math.max(...g.items.map(x => x.last_seen))};
  });
}
let G = [];
let S = null, picked = null, showHidden = false, view = {x: 0, y: 0, k: 1}, sheetOpen = false, chosen = null;
try { chosen = JSON.parse(localStorage.getItem('ww-lookup-run') || 'null'); } catch (e) { /* private window */ }

async function call(path, method = 'GET', body) {
  const r = await fetch(path, {method, cache: 'no-store', headers: body ? {'Content-Type': 'application/json'} : {}, body: body ? JSON.stringify(body) : undefined});
  const d = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(d.error || 'The server answered ' + r.status);
  return d;
}
async function load() { try { S = await call('/api/lookup/state'); G = grouped(); render(); } catch (e) { $('#empty').hidden = false; $('#empty').textContent = e.message; } }

// ---- left panel ----
function render() {
  const busy = !!S.job.running;
  $('#kind').innerHTML ||= Object.entries(S.kinds).map(([k, v]) => `<option value="${k}">${v}</option>`).join('');
  $('#ids').innerHTML = S.identifiers.map(i => `<li><small>${esc(S.kinds[i.kind])}</small><span>${esc(i.value)}</span><button data-id="${i.id}" aria-label="Remove">✕</button></li>`).join('')
    || '<li><span style="color:var(--text-2)">Nothing yet. Add a username or an email address of yours.</span></li>';
  const t = S.selftest;
  $('#test').textContent = t ? `Tested ${ago(t.tested)}: ${t.trusted} of ${t.total} sites give a correct answer from this computer and will be used. ${t.blind} are skipped (blocked, slow or changed)${t.false_alarm ? `, ${t.false_alarm} of them because they claim a made-up name exists` : ''}.`
    : 'Not tested on this computer yet. The test asks every site about an account known to exist and about a made-up name, and keeps only the sites that get both right. It takes about a minute.';
  $('#run-test').disabled = busy; $('#plan').disabled = busy || !S.identifiers.length; $('#wipe').disabled = busy;
  const ls = S.last_scan;
  $('#scan-line').textContent = ls ? `Last scan ${ago(ls.finished)}: ${ls.summary.findings ?? (ls.summary.usernames + ls.summary.emails)} findings from ${(ls.summary.checks || []).length || 'the'} checks.` : 'No scan yet.';
  $('#progress').hidden = !busy;
  if (busy) { $('#bar').style.width = S.job.total ? Math.round(S.job.done / S.job.total * 100) + '%' : '8%'; $('#step').textContent = S.job.step + (S.job.total ? ` (${S.job.done} of ${S.job.total})` : ''); }
  $('#problems').innerHTML = (busy ? S.job.problems : ls?.summary.problems || S.job.problems || []).map(p => `<li>${esc(p)}</li>`).join('');
  $('#stored').textContent = `${S.identifiers.length} identifiers, ${S.findings.length} findings (${G.length} after joining the same page found by several tools).`;
  if (sheetOpen) renderSheet();
  draw(); renderDetail(); legend();
}
function renderSheet() {
  const p = S.plan, el = $('#sheet');
  if (!chosen) chosen = Object.fromEntries(p.checks.map(c => [c.id, true]));
  for (const c of p.checks) if (!(c.id in chosen)) chosen[c.id] = true;
  el.hidden = false;
  el.innerHTML = `<b>Choose what runs</b>` + (p.checks.length ? p.checks.map(c => `<label class="pick"><input type="checkbox" data-run="${c.id}" ${chosen[c.id] ? 'checked' : ''}${c.id === 'wmn' && p.needs_test ? ' disabled' : ''}>
        <span><strong>${esc(c.name)}</strong> on ${c.count} ${esc(S.kinds[c.for].toLowerCase())}${c.count > 1 && !/s$/.test(S.kinds[c.for]) ? 's' : ''}<br>Sends ${esc(c.id === 'wmn' && p.trusted_sites ? 'the username to ' + p.trusted_sites + ' websites that passed the test' : c.sends)}.${c.note ? ' <em>Downloads ' + esc(c.note) + '.</em>' : ''}${c.id === 'wmn' && p.needs_test ? ' <em>Needs "Test the checker" first.</em>' : ''}</span></label>`).join('')
      + Object.entries(p.options).filter(([k]) => p.checks.some(c => k.startsWith(c.id))).map(([k, v]) => `<label class="pick opt"><input type="checkbox" data-run="${k}" ${chosen[k] ? 'checked' : ''}><span>${esc(v)}</span></label>`).join('')
      : '<p class="line">Add an identifier first.</p>') +
    `<p class="src" style="margin:8px 0 10px">Maigret, Sherlock, Holehe and theHarvester are the standard open-source tools, run unchanged as separate programs. They are downloaded on first use.</p>
    <button class="btn primary" id="go" ${p.checks.length ? '' : 'disabled'}>Start</button><button class="btn" id="cancel">Cancel</button>`;
}
// ---- graph: you in the middle, identifiers around you, findings fanned out behind each identifier ----
function layout() {
  const ids = S.identifiers, nodes = [{id: 'me', x: 0, y: 0, r: 16, label: 'You', big: true, color: 'var(--text)'}], links = [];
  const n = Math.max(ids.length, 1), R1 = ids.length > 1 ? 150 : 0;
  ids.forEach((it, i) => {
    const a0 = -Math.PI / 2 + i * 2 * Math.PI / n, ix = R1 * Math.cos(a0), iy = R1 * Math.sin(a0);
    const idNode = {id: 'i' + it.id, x: ix, y: iy, r: 11, label: it.value, sub: S.kinds[it.kind], big: true, color: 'var(--accent)', ident: it};
    if (ids.length > 1) { nodes.push(idNode); links.push(['me', idNode.id]); } else { nodes[0] = {...idNode, id: 'me', r: 16}; }
    const mine = G.filter(f => f.identifier === it.id && (showHidden || !f.not_me)).sort((a, b) => a.kind.localeCompare(b.kind) || b.tools.length - a.tools.length);
    const sector = ids.length > 1 ? Math.min(2 * Math.PI / n, Math.PI) * 0.92 : 2 * Math.PI;
    let k = 0, ring = 0;
    while (k < mine.length) {
      const R = R1 + 150 + ring * 150, room = Math.max(1, Math.floor(sector * R / 26)), take = mine.slice(k, k + room);
      take.forEach((f, j) => {
        const a = a0 + (take.length === 1 ? 0 : (j / (ids.length > 1 ? take.length - 1 : take.length) - (ids.length > 1 ? 0.5 : 0)) * sector);
        nodes.push({id: 'f' + f.id, x: R * Math.cos(a), y: R * Math.sin(a), r: 4.5 + Math.min(3, f.tools.length) * 1.2, a,
          label: f.kind === 'account' ? f.key.split(':')[0] : f.title, color: kindOf(f.kind)[1], finding: f, dim: !!f.not_me});
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
  $('#empty').hidden = S.identifiers.length > 0 && G.length > 0;
  if (!$('#empty').hidden) $('#empty').textContent = S.identifiers.length ? 'Nothing found yet. Run a scan to see what public sources show about these identifiers.' : 'Add your usernames and email addresses on the left, then scan. What is found will be drawn here, linked to the identifier it belongs to.';
  svg.innerHTML = `<g transform="translate(${cx},${cy}) scale(${view.k})">` +
    links.map(([a, b]) => `<line x1="${by[a].x}" y1="${by[a].y}" x2="${by[b].x}" y2="${by[b].y}"/>`).join('') +
    nodes.map(n => {
      const deg = n.a == null ? 0 : n.a * 180 / Math.PI, flip = Math.cos(n.a ?? 0) < 0;
      const text = n.big ? `<text class="big" x="${n.x}" y="${n.y + n.r + 15}" text-anchor="middle">${esc(n.label)}</text>${n.sub ? `<text x="${n.x}" y="${n.y + n.r + 29}" text-anchor="middle" style="fill:var(--text-2)">${esc(n.sub)}</text>` : ''}`
        : `<text transform="translate(${n.x},${n.y}) rotate(${flip ? deg + 180 : deg})" x="${flip ? -11 : 11}" y="4" text-anchor="${flip ? 'end' : 'start'}">${esc(n.label.length > 26 ? n.label.slice(0, 25) + '…' : n.label)}</text>`;
      return `<g class="${n.dim ? 'dim' : ''}"><circle data-node="${n.id}" class="${picked === n.id ? 'sel' : ''}" cx="${n.x}" cy="${n.y}" r="${n.r}" style="fill:${n.color}"/>${text}</g>`;
    }).join('') + '</g>';
}
function legend() {
  const hidden = G.filter(f => f.not_me).length, used = [...new Set(G.map(f => f.kind))];
  $('#legend').hidden = !G.length;
  $('#legend').innerHTML = used.map(k => `<span><i style="background:${kindOf(k)[1]}"></i>${kindOf(k)[0]}</span>`).join('') + '<span style="color:var(--text-2)">larger dot: found by more tools</span>' +
    (hidden ? `<button class="btn" id="toggle-hidden">${showHidden ? 'Hide' : 'Show'} ${hidden} marked not me</button>` : '');
}
const nice = k => k.replace(/_/g, ' ').replace(/^./, c => c.toUpperCase());
function renderDetail() {
  const el = $('#detail'), f = picked && G.find(x => 'f' + x.id === picked);
  el.hidden = !f; if (!f) return;
  const ident = S.identifiers.find(i => i.id === f.identifier), d = f.detail || {};
  const rows = Object.entries(d).filter(([k, v]) => v != null && v !== '' && !['what', 'image'].includes(k) && typeof v !== 'object').map(([k, v]) => `<dt>${esc(nice(k))}</dt><dd>${esc(v)}</dd>`).join('');
  const lists = Object.entries(d).filter(([, v]) => v && typeof v === 'object').map(([k, v]) => `<p class="source">${esc(nice(k))}: ${(Array.isArray(v) ? v : [v]).map(x => esc(typeof x === 'object' ? Object.values(x).filter(Boolean).join(', ') : x)).join('; ')}</p>`).join('');
  const key = f.id + '|' + f.last_seen + '|' + f.not_me, y = el.dataset.key === key ? el.scrollTop : 0;
  el.dataset.key = key;
  el.innerHTML = `<button class="close" id="close" aria-label="Close"></button>
    ${d.image && /^https:\/\//.test(d.image) ? `<img class="face" src="${esc(d.image)}" alt="Picture shown on that profile" referrerpolicy="no-referrer" loading="lazy">` : ''}
    <p class="eyebrow">${esc(kindOf(f.kind)[0])}</p><h2>${esc(f.title)}</h2>
    <p class="where">Found for ${esc((S.kinds[ident?.kind] || '').toLowerCase())} ${esc(ident?.value || '')}</p>
    ${d.what ? `<p class="source" style="margin:0 0 12px;font-size:13px;line-height:16px">${esc(d.what)}</p>` : ''}
    ${rows ? `<dl>${rows}</dl>` : ''}${lists}
    ${f.url ? `<a class="link" href="${esc(f.url)}" target="_blank" rel="noopener noreferrer">Open the page</a>` : ''}
    <p class="source">Found by: ${f.tools.map(esc).join(', ')}. First seen ${local(f.first_seen)}, last confirmed ${ago(f.last_seen)}.</p>
    <button class="btn not-me" id="not-me">${f.not_me ? 'This is me after all' : 'Not me'}</button>`;
  el.scrollTop = y;
}

// ---- actions ----
const act = async (fn) => { $('#err').hidden = true; try { await fn(); } catch (e) { $('#err').hidden = false; $('#err').textContent = e.message; } await load(); };
$('#add').addEventListener('submit', e => { e.preventDefault(); act(async () => { await call('/api/lookup/identifiers', 'POST', {kind: $('#kind').value, value: $('#value').value}); $('#value').value = ''; }); });
$('#ids').addEventListener('click', e => { const b = e.target.closest('button[data-id]'); if (b) act(() => call('/api/lookup/identifiers/' + b.dataset.id, 'DELETE')); });
$('#run-test').onclick = () => act(() => call('/api/lookup/run/selftest', 'POST'));
$('#plan').onclick = () => { sheetOpen = true; renderSheet(); };
$('#sheet').addEventListener('change', e => { const k = e.target.dataset.run; if (k) { chosen[k] = e.target.checked; try { localStorage.setItem('ww-lookup-run', JSON.stringify(chosen)); } catch (err) { /* private window */ } } });
$('#sheet').addEventListener('click', e => {
  if (e.target.id === 'cancel') { sheetOpen = false; $('#sheet').hidden = true; }
  if (e.target.id === 'go') { sheetOpen = false; $('#sheet').hidden = true; act(() => call('/api/lookup/run/scan', 'POST', {run: Object.keys(chosen).filter(k => chosen[k] && !(k === 'wmn' && S.plan.needs_test))})); }
});
let armed = 0;
$('#wipe').onclick = () => {   // two clicks within five seconds: the page cannot show a system confirm box everywhere
  if (Date.now() - armed < 5000) { armed = 0; $('#wipe').textContent = 'Delete everything'; picked = null; act(() => call('/api/lookup/wipe', 'POST')); }
  else { armed = Date.now(); $('#wipe').textContent = 'Click again to delete everything'; setTimeout(() => { if (armed) { armed = 0; $('#wipe').textContent = 'Delete everything'; } }, 5000); }
};
$('#detail').addEventListener('click', e => {
  if (e.target.id === 'close') { picked = null; render(); }
  if (e.target.id === 'not-me') { const f = G.find(x => 'f' + x.id === picked), to = !f.not_me; act(async () => { for (const id of f.ids) await call('/api/lookup/mark', 'POST', {id, not_me: to}); }); if (to && !showHidden) picked = null; }
});
$('#legend').addEventListener('click', e => { if (e.target.id === 'toggle-hidden') { showHidden = !showHidden; render(); } });

// pan with drag, zoom with the wheel or a pinch
const svg = $('#graph'); let drag = null;
svg.addEventListener('pointerdown', e => { const n = e.target.dataset?.node; if (n) { picked = n.startsWith('f') ? n : null; render(); return; } drag = {x: e.clientX - view.x, y: e.clientY - view.y}; svg.setPointerCapture(e.pointerId); });
svg.addEventListener('pointermove', e => { if (drag) { view.x = e.clientX - drag.x; view.y = e.clientY - drag.y; draw(); } });
svg.addEventListener('pointerup', () => { drag = null; });
svg.addEventListener('wheel', e => { e.preventDefault(); view.k = Math.min(4, Math.max(0.2, view.k * (e.deltaY < 0 ? 1.1 : 1 / 1.1))); draw(); }, {passive: false});
addEventListener('resize', () => S && draw());
addEventListener('keydown', e => { if (e.key === 'Escape') { picked = null; render(); } });

load();
setInterval(() => { if (S?.job.running || document.visibilityState === 'visible') load(); }, 2000);
