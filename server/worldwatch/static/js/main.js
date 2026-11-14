import {$, ago, api, esc, now} from './util.js';
import {createMap, paintBase, paintSky, setGlobe} from './map.js';
import * as quakes from './quakes.js';

const SIDEBAR_SPACE = 420;   // the sidebar's width plus its margins; the map centres on what is left
const dark = matchMedia('(prefers-color-scheme: dark)');
const map = createMap('map', innerWidth > 900 ? SIDEBAR_SPACE : 0);

let data = {quakes: null}, feedInfo = {}, picked = null, status = null, lastAnswer = 0;

function repaint() {
  paintBase(map, dark.matches);
  paintSky(map, dark.matches);
  quakes.paint(map, dark.matches);
}

map.on('load', () => {
  quakes.addTo(map, pick);
  repaint();
  loadQuakes();
  setInterval(loadQuakes, 30000);
});
dark.addEventListener('change', repaint);
map.on('click', e => { if (!map.queryRenderedFeatures(e.point, {layers: ['ww-quakes']}).length) pick(null); });

async function loadQuakes() {
  try {
    const d = await api('/api/data/quakes');
    if (!d.payload) return;
    data.quakes = d.payload.quakes;
    feedInfo.quakes = d;
    quakes.setData(map, data.quakes);
    renderList();
    if (picked) renderDetail();
  } catch (e) { /* the banner reports a server that stopped answering */ }
}

function renderList() {
  if (!data.quakes) return;
  const rows = quakes.rows(data.quakes);
  $('#list-count').textContent = quakes.listNote(rows.length);
  $('#list').innerHTML = rows.map(r => `<li role="option" tabindex="0" data-id="${esc(r.id)}" aria-selected="${r.id === picked}">
      <span class="badge${r.strong ? ' strong' : ''}">${esc(r.badge)}</span>
      <span class="row-text"><span class="row-title">${esc(r.title)}</span><span class="row-meta">${esc(r.meta)}</span></span></li>`).join('')
    || '<li class="empty">No earthquakes of this size in the feed right now.</li>';
}

function pick(id, fly = false) {
  picked = id;
  quakes.mark(map, id);
  document.querySelectorAll('#list li').forEach(li => li.setAttribute('aria-selected', li.dataset.id === id));
  renderDetail();
  const q = id && data.quakes.find(x => x.id === id);
  if (q && fly) map.easeTo({center: [q.lon, q.lat], zoom: Math.max(map.getZoom(), 3.2), duration: matchMedia('(prefers-reduced-motion: reduce)').matches ? 0 : 900});
  if (q && !fly) document.querySelector(`#list li[data-id="${CSS.escape(id)}"]`)?.scrollIntoView({block: 'nearest', behavior: 'smooth'});
}

function renderDetail() {
  const q = picked && data.quakes?.find(x => x.id === picked), el = $('#detail');
  el.hidden = !q;
  if (q) el.innerHTML = '<button class="close" id="close" aria-label="Close"></button>' + quakes.detail(q, feedInfo.quakes);
}

$('#list').addEventListener('click', e => { const li = e.target.closest('li[data-id]'); if (li) pick(li.dataset.id, true); });
$('#list').addEventListener('keydown', e => {
  const li = e.target.closest('li[data-id]'); if (!li) return;
  if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); pick(li.dataset.id, true); }
  if (e.key === 'ArrowDown' || e.key === 'ArrowUp') { e.preventDefault(); (e.key === 'ArrowDown' ? li.nextElementSibling : li.previousElementSibling)?.focus(); }
});
$('#detail').addEventListener('click', e => { if (e.target.id === 'close') pick(null); });
addEventListener('keydown', e => { if (e.key === 'Escape') pick(null); });

function shape(globe) {
  setGlobe(map, globe);
  $('#flat').setAttribute('aria-pressed', !globe);
  $('#globe').setAttribute('aria-pressed', globe);
  try { localStorage.setItem('ww-globe', globe ? '1' : ''); } catch (e) { /* private window */ }
}
$('#flat').onclick = () => shape(false);
$('#globe').onclick = () => shape(true);
map.on('load', () => { try { if (localStorage.getItem('ww-globe')) shape(true); } catch (e) { /* private window */ } });

// ---- the feeds card: one honest line when closed, every feed when open ----
async function loadStatus() {
  try { status = await api('/api/status'); lastAnswer = Date.now(); } catch (e) { /* shown by the banner */ }
  renderFeeds();
}
function renderFeeds() {
  const down = Date.now() - lastAnswer > 12000;
  $('#banner').hidden = !down;
  if (down) $('#banner').textContent = lastAnswer ? `The World Watch server stopped answering ${ago(lastAnswer / 1000, Date.now() / 1000)}. Everything on screen is from before that.` : 'The World Watch server is not answering.';
  if (!status) return;
  const f = status.feeds, bad = f.filter(x => x.state === 'failing'), late = f.filter(x => x.state === 'late'), wait = f.filter(x => x.state === 'waiting');
  const ok = f.length - bad.length - late.length - wait.length;
  $('#feeds-dot').className = 'dot ' + (down || bad.length ? 'bad' : late.length ? 'warn' : wait.length ? 'idle' : 'good');
  $('#feeds-sum').textContent = down ? 'Server not answering'
    : bad.length ? `${bad.length} of ${f.length} feeds failing` + (late.length ? `, ${late.length} late` : '')
    : late.length ? `${late.length} of ${f.length} feeds late`
    : wait.length ? `${ok} of ${f.length} feeds in, ${wait.length} starting` : `All ${f.length} feeds current`;
  if ($('#feeds-body').hidden) return;
  const n = now();
  $('#feeds-body').innerHTML = '<ul>' + f.map(x => {
    const age = x.data_label ? esc(x.data_label.replace('reference rates of ', 'rates of ')) : x.data_time ? 'data ' + ago(x.data_time, n) : x.fetched ? 'fetched ' + ago(x.fetched, n) : 'not fetched yet';
    return `<li><span class="dot ${ {ok: 'good', late: 'warn', failing: 'bad', waiting: 'idle'}[x.state] }"></span>
      <span class="row-text"><span class="row-title">${esc(x.layer)}</span><span class="row-meta">${esc(x.source)}${x.error ? ' · ' + esc(x.error) : ''}</span></span>
      <span class="age">${age}</span></li>`; }).join('') + '</ul><a class="link" href="/feeds">Full feed report</a>';
}
$('#feeds-toggle').onclick = () => {
  const body = $('#feeds-body'); body.hidden = !body.hidden;
  $('#feeds-toggle').setAttribute('aria-expanded', !body.hidden);
  renderFeeds();
};
loadStatus();
setInterval(loadStatus, 5000);
setInterval(() => { renderFeeds(); if (!$('#list').contains(document.activeElement)) renderList(); }, 15000);   // keep the "x min ago" texts moving
