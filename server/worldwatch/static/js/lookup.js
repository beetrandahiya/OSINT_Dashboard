// The lookup page: your identifiers in the middle, everything found about them around, as a graph.
import {$, ago, esc, local} from './util.js';

const KIND = {account: ['Account', 'light-dark(#5856d6, #7d7aff)'], breach: ['Breach', 'light-dark(#ff3b30, #ff453a)'], exposure: ['Malware exposure', 'light-dark(#ff9500, #ff9f0a)'],
  profile: ['Profile', 'light-dark(#28a745, #30d158)'], key: ['Public key', 'light-dark(#00a3b4, #40c8e0)'], code: ['Code', 'light-dark(#8e8e93, #98989d)']};
let S = null, picked = null, showHidden = false, view = {x: 0, y: 0, k: 1}, sheetOpen = false;

async function call(path, method = 'GET', body) {
  const r = await fetch(path, {method, cache: 'no-store', headers: body ? {'Content-Type': 'application/json'} : {}, body: body ? JSON.stringify(body) : undefined});
  const d = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(d.error || 'The server answered ' + r.status);
  return d;
}
async function load() { try { S = await call('/api/lookup/state'); render(); } catch (e) { $('#empty').hidden = false; $('#empty').textContent = e.message; } }

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
  $('#scan-line').textContent = ls ? `Last scan ${ago(ls.finished)}: ${ls.summary.usernames} profile pages and ${ls.summary.emails} email findings.` : 'No scan yet.';
  $('#progress').hidden = !busy;
  if (busy) { $('#bar').style.width = S.job.total ? Math.round(S.job.done / S.job.total * 100) + '%' : '8%'; $('#step').textContent = S.job.step + (S.job.total ? ` (${S.job.done} of ${S.job.total})` : ''); }
  $('#problems').innerHTML = (busy ? S.job.problems : ls?.summary.problems || S.job.problems || []).map(p => `<li>${esc(p)}</li>`).join('');
  $('#stored').textContent = `${S.identifiers.length} identifiers, ${S.findings.length} findings.`;
  if (sheetOpen) renderSheet();
  draw(); renderDetail(); legend();
}
function renderSheet() {
  const p = S.plan, el = $('#sheet');
  el.hidden = false;
  el.innerHTML = `<b>This scan will send</b><ul>${p.steps.map(s => `<li>${esc(s.what)} to ${esc(s.to)}. Sent: ${esc(s.sends)}.</li>`).join('') || '<li>Nothing: add a username or an email address first.</li>'}</ul>
    ${p.not_yet.length ? `<p class="src" style="margin:0 0 10px">Not checked yet (not built): ${p.not_yet.map(esc).join(', ')}.</p>` : ''}
    ${p.needs_test ? '<p class="err" style="margin:0 0 10px">Test the checker first; usernames cannot be scanned before that.</p>' : ''}
    <button class="btn primary" id="go" ${p.needs_test || !p.steps.length ? 'disabled' : ''}>Start</button><button class="btn" id="cancel">Cancel</button>`;
}

// ---- graph: you in the middle, identifiers around you, findings fanned out behind each identifier ----
function layout() {
  const ids = S.identifiers, nodes = [{id: 'me', x: 0, y: 0, r: 16, label: 'You', big: true, color: 'var(--text)'}], links = [];
  const n = Math.max(ids.length, 1), R1 = ids.length > 1 ? 150 : 0;
  ids.forEach((it, i) => {
    const a0 = -Math.PI / 2 + i * 2 * Math.PI / n, ix = R1 * Math.cos(a0), iy = R1 * Math.sin(a0);
    const idNode = {id: 'i' + it.id, x: ix, y: iy, r: 11, label: it.value, sub: S.kinds[it.kind], big: true, color: 'var(--accent)', ident: it};
    if (ids.length > 1) { nodes.push(idNode); links.push(['me', idNode.id]); } else { nodes[0] = {...idNode, id: 'me', r: 16}; }
    const mine = S.findings.filter(f => f.identifier === it.id && (showHidden || !f.not_me));
    const sector = ids.length > 1 ? Math.min(2 * Math.PI / n, Math.PI) * 0.92 : 2 * Math.PI;
    let k = 0, ring = 0;
    while (k < mine.length) {
      const R = R1 + 150 + ring * 150, room = Math.max(1, Math.floor(sector * R / 26)), take = mine.slice(k, k + room);
      take.forEach((f, j) => {
        const a = a0 + (take.length === 1 ? 0 : (j / (ids.length > 1 ? take.length - 1 : take.length) - (ids.length > 1 ? 0.5 : 0)) * sector);
        nodes.push({id: 'f' + f.id, x: R * Math.cos(a), y: R * Math.sin(a), r: f.kind === 'breach' || f.kind === 'exposure' ? 7 : 5.5, a,
          label: f.kind === 'account' ? f.key : f.title, color: (KIND[f.kind] || KIND.code)[1], finding: f, dim: !!f.not_me});
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
  $('#empty').hidden = S.identifiers.length > 0 && S.findings.length > 0;
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
  const hidden = S.findings.filter(f => f.not_me).length;
  const used = [...new Set(S.findings.map(f => f.kind))];
  $('#legend').hidden = !S.findings.length;
  $('#legend').innerHTML = used.map(k => `<span><i style="background:${(KIND[k] || KIND.code)[1]}"></i>${(KIND[k] || KIND.code)[0]}</span>`).join('') +
    (hidden ? `<button class="btn" id="toggle-hidden">${showHidden ? 'Hide' : 'Show'} ${hidden} marked not me</button>` : '');
}
function renderDetail() {
  const el = $('#detail'), f = picked && S.findings.find(x => 'f' + x.id === picked);
  el.hidden = !f; if (!f) return;
  const ident = S.identifiers.find(i => i.id === f.identifier), d = f.detail || {};
  const rows = Object.entries(d).filter(([k, v]) => v != null && v !== '' && k !== 'what' && typeof v !== 'object').map(([k, v]) => `<dt>${esc(k.replace(/_/g, ' ').replace(/^./, c => c.toUpperCase()))}</dt><dd>${esc(v)}</dd>`).join('');
  const lists = Object.entries(d).filter(([, v]) => Array.isArray(v)).map(([k, v]) => `<p class="source">${esc(k.replace(/^./, c => c.toUpperCase()))}: ${v.map(x => esc(typeof x === 'object' ? Object.values(x).filter(Boolean).join(', ') : x)).join('; ')}</p>`).join('');
  el.innerHTML = `<button class="close" id="close" aria-label="Close"></button><p class="eyebrow">${esc((KIND[f.kind] || KIND.code)[0])}</p><h2>${esc(f.title)}</h2>
    <p class="where">Found for ${esc(S.kinds[ident?.kind] || '')} ${esc(ident?.value || '')}</p>
    ${d.what ? `<p class="source" style="margin:0 0 12px;font-size:13px;line-height:16px">${esc(d.what)}</p>` : ''}
    ${rows ? `<dl>${rows}</dl>` : ''}${lists}
    ${f.url ? `<a class="link" href="${esc(f.url)}" target="_blank" rel="noopener">Open the page</a>` : ''}
    <p class="source">Source: ${esc(f.tool)}. First seen ${local(f.first_seen)}, last confirmed ${ago(f.last_seen)}.</p>
    <button class="btn not-me" id="not-me">${f.not_me ? 'This is me after all' : 'Not me'}</button>`;
}

// ---- actions ----
const act = async (fn) => { $('#err').hidden = true; try { await fn(); } catch (e) { $('#err').hidden = false; $('#err').textContent = e.message; } await load(); };
$('#add').addEventListener('submit', e => { e.preventDefault(); act(async () => { await call('/api/lookup/identifiers', 'POST', {kind: $('#kind').value, value: $('#value').value}); $('#value').value = ''; }); });
$('#ids').addEventListener('click', e => { const b = e.target.closest('button[data-id]'); if (b) act(() => call('/api/lookup/identifiers/' + b.dataset.id, 'DELETE')); });
$('#run-test').onclick = () => act(() => call('/api/lookup/run/selftest', 'POST'));
$('#plan').onclick = () => { sheetOpen = true; renderSheet(); };
$('#sheet').addEventListener('click', e => {
  if (e.target.id === 'cancel') { sheetOpen = false; $('#sheet').hidden = true; }
  if (e.target.id === 'go') { sheetOpen = false; $('#sheet').hidden = true; act(() => call('/api/lookup/run/scan', 'POST')); }
});
let armed = 0;
$('#wipe').onclick = () => {   // two clicks within five seconds: the page cannot show a system confirm box everywhere
  if (Date.now() - armed < 5000) { armed = 0; $('#wipe').textContent = 'Delete everything'; picked = null; act(() => call('/api/lookup/wipe', 'POST')); }
  else { armed = Date.now(); $('#wipe').textContent = 'Click again to delete everything'; setTimeout(() => { if (armed) { armed = 0; $('#wipe').textContent = 'Delete everything'; } }, 5000); }
};
$('#detail').addEventListener('click', e => {
  if (e.target.id === 'close') { picked = null; render(); }
  if (e.target.id === 'not-me') { const f = S.findings.find(x => 'f' + x.id === picked); act(() => call('/api/lookup/mark', 'POST', {id: f.id, not_me: !f.not_me})); if (!f.not_me && !showHidden) picked = null; }
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
