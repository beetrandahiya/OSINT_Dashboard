import {$, ago, api, esc, now} from './util.js';
import {createMap, paintBase, paintSky, setGlobe} from './map.js';
import news from './news.js';
import quakes from './quakes.js';
import outages from './outages.js';
import {civil, military, fillRoute, select as selectAircraft} from './aircraft.js';
import {satellites, launches} from './space.js';
import hazards from './hazards.js';
import cables from './cables.js';
import {rain, night, aurora} from './sky.js';
import * as markets from './markets.js';

// Order = drawing order on the map, bottom first.
const LAYERS = [night, aurora, cables, civil, military, satellites, outages, launches, hazards, quakes, news, rain];
const CHIPS = [news, quakes, hazards, outages, civil, military, satellites, launches, cables, rain, night, aurora];
const byId = Object.fromEntries(LAYERS.map(l => [l.id, l]));

const SIDEBAR_SPACE = 420;   // the sidebar's width plus its margins; the map centres on what is left
const dark = matchMedia('(prefers-color-scheme: dark)');
const calm = matchMedia('(prefers-reduced-motion: reduce)');
const map = createMap('map', innerWidth > 900 ? SIDEBAR_SPACE : 0);

let on = Object.fromEntries(LAYERS.map(l => [l.id, true]));
try { Object.assign(on, JSON.parse(localStorage.getItem('ww-layers') || '{}')); } catch (e) { /* private window */ }
let ready = false, picked = null, status = null, lastAnswer = 0, got = new Set(LAYERS.filter(l => l.local).map(l => l.id));

function repaint() {
  paintBase(map, dark.matches);
  paintSky(map, dark.matches);
  for (const l of LAYERS) l.paint(map, dark.matches);
  map.setPaintProperty('ww-pick', 'circle-stroke-color', dark.matches ? '#ffffff' : '#000000');
}

function show(layer) {
  for (const id of layer.layers) if (map.getLayer(id)) map.setLayoutProperty(id, 'visibility', on[layer.id] ? 'visible' : 'none');
  layer.visible?.(on[layer.id]);
}

async function load(layer, feed) {
  try {
    const d = await api('/api/data/' + feed);
    if (!d.payload) return;
    layer.onData(feed, d);
    got.add(layer.id);
    layer.render(map);
    renderChips(); renderList(); refreshPick();
  } catch (e) { /* the banner reports a server that stopped answering; one bad answer must not stop the rest */ }
}

map.on('load', () => {
  for (const l of LAYERS) l.addTo(map);
  // one ring for whatever is selected: Apple's guidance asks for an outline as well as a colour change
  map.addSource('ww-pick', {type: 'geojson', data: {type: 'FeatureCollection', features: []}});
  map.addLayer({id: 'ww-pick', type: 'circle', source: 'ww-pick', paint: {'circle-radius': ['get', 'r'], 'circle-color': 'transparent', 'circle-stroke-width': 2.5}});
  repaint();
  for (const l of LAYERS) {
    show(l);
    for (const [feed, secs] of Object.entries(l.feeds)) { load(l, feed); setInterval(() => load(l, feed), secs * 1000); }
  }
  const NO_CLICK = ['ww-night', 'ww-rain', 'ww-aurora', 'ww-cables', 'ww-iss-track', 'ww-air-route', 'ww-air-trail', 'ww-hazards-track'];
  const hit = LAYERS.flatMap(l => l.layers).filter(id => !NO_CLICK.includes(id));
  map.on('click', e => {
    const f = map.queryRenderedFeatures([[e.point.x - 4, e.point.y - 4], [e.point.x + 4, e.point.y + 4]], {layers: hit.filter(id => map.getLayoutProperty(id, 'visibility') !== 'none')})
      .filter(x => x.properties.id != null).sort((a, b) => (a.layer.id === 'ww-cables-hit') - (b.layer.id === 'ww-cables-hit'))[0];   // markers win over cables
    if (!f) return pick(null);
    const layer = LAYERS.find(l => l.layers.includes(f.layer.id) && (!l.owns || l.owns(f.properties.id))) || LAYERS.find(l => l.layers.includes(f.layer.id));
    pick({layer: layer.id, id: f.properties.id});
  });
  map.on('mousemove', e => { map.getCanvas().style.cursor = map.queryRenderedFeatures(e.point, {layers: hit.filter(id => map.getLayer(id) && map.getLayoutProperty(id, 'visibility') !== 'none')}).some(x => x.properties.id != null) ? 'pointer' : ''; });
  setInterval(() => { if (picked && byId[picked.layer].moving && !document.hidden) ring(); }, 200);
  ready = true;
});
dark.addEventListener('change', () => ready && repaint());

// ---- layer chips: each one shows and hides a layer, and says how many items it holds ----
function renderChips() {
  $('#chips').innerHTML = CHIPS.map(l => `<button class="chip" data-id="${l.id}" aria-pressed="${on[l.id]}" style="--c:${l.color[+dark.matches]}"${l.about ? ` title="${esc(l.about())}"` : ''}>
    <span class="swatch"></span>${l.title}<span class="n">${l.note ? l.note() : got.has(l.id) ? l.count().toLocaleString('en-GB') : ''}</span></button>`).join('');
}
$('#chips').addEventListener('click', e => {
  const b = e.target.closest('.chip'); if (!b) return;
  const l = byId[b.dataset.id];
  on[l.id] = !on[l.id];
  try { localStorage.setItem('ww-layers', JSON.stringify(on)); } catch (err) { /* private window */ }
  show(l); renderChips(); renderList();
  if (picked?.layer === l.id && !on[l.id]) pick(null);
});
dark.addEventListener('change', renderChips);

// ---- the list: what is coming up first, then the newest things across the layers that are switched on ----
function renderList() {
  const t = now(), rows = [];
  for (const l of CHIPS) if (on[l.id] && got.has(l.id)) for (const r of l.rows()) rows.push({...r, layer: l});
  const coming = rows.filter(r => r.time > t).sort((a, b) => a.time - b.time);
  const past = rows.filter(r => r.time <= t).sort((a, b) => b.time - a.time || (b.order ?? 0) - (a.order ?? 0));
  const li = r => `<li role="option" tabindex="0" data-layer="${r.layer.id}" data-id="${esc(r.id)}" aria-selected="${picked?.layer === r.layer.id && picked.id === r.id}" style="--c:${r.layer.color[+dark.matches]}">
      <span class="badge${r.strong ? ' strong' : ''}">${esc(r.badge)}</span>
      <span class="row-text"><span class="row-title">${esc(r.title)}</span><span class="row-meta">${esc(r.meta)}</span></span></li>`;
  const html = (coming.length ? `<li class="group">Coming up</li>${coming.map(li).join('')}<li class="group">Latest</li>` : '') + past.map(li).join('');
  const list = $('#list');
  if (list.contains(document.activeElement) && list.dataset.html) return;   // don't pull the list from under the keyboard
  if (list.dataset.html !== html) { list.innerHTML = html || '<li class="empty">Nothing to list for the layers that are switched on.</li>'; list.dataset.html = html; }
}

function ring() {
  const l = picked && byId[picked.layer], at = l?.locate(picked.id);
  map.getSource('ww-pick')?.setData({type: 'FeatureCollection', features: at ? [{type: 'Feature', geometry: {type: 'Point', coordinates: at}, properties: {r: l.ring(picked.id)}}] : []});
  return at;
}

function pick(p, fly = false) {
  picked = p;
  selectAircraft(p && (p.layer === 'aircraft' || p.layer === 'military') ? p.id : null);
  document.querySelectorAll('#list li[data-id]').forEach(li => li.setAttribute('aria-selected', !!p && li.dataset.layer === p.layer && li.dataset.id === String(p.id)));
  renderDetail();
  const at = ring();
  if (at && fly) map.easeTo({center: at, zoom: Math.max(map.getZoom(), 3.2), duration: calm.matches ? 0 : 900});
  if (p && !fly) document.querySelector(`#list li[data-layer="${p.layer}"][data-id="${CSS.escape(String(p.id))}"]`)?.scrollIntoView({block: 'nearest', behavior: calm.matches ? 'auto' : 'smooth'});
}

let detailKey = '';
function renderDetail() {
  const el = $('#detail'), html = picked && byId[picked.layer].detail(picked.id);
  if (picked && html == null) {   // the item left its feed (a plane landed, a quake aged out): say so, don't keep a ghost
    el.hidden = false;
    el.innerHTML = '<button class="close" id="close" aria-label="Close"></button><p class="eyebrow">No longer in the feed</p><p class="where">This item is not in the latest data any more.</p>';
    detailKey = ''; return;
  }
  el.hidden = !picked;
  if (!picked) { detailKey = ''; return; }
  const key = picked.layer + '|' + picked.id, scroll = el.scrollTop;
  const route = key === detailKey ? $('#route')?.innerHTML : null, done = key === detailKey && $('#route')?.dataset.done;
  el.innerHTML = '<button class="close" id="close" aria-label="Close"></button>' + html;
  if (route != null && done) { $('#route').innerHTML = route; $('#route').dataset.done = '1'; }
  el.scrollTop = key === detailKey ? scroll : 0;
  detailKey = key;
  fillRoute();
}
function refreshPick() { if (picked && !$('#detail').matches(':hover')) { renderDetail(); ring(); } }

$('#list').addEventListener('click', e => { const li = e.target.closest('li[data-id]'); if (li) pick({layer: li.dataset.layer, id: li.dataset.id}, true); });
$('#list').addEventListener('keydown', e => {
  const li = e.target.closest('li[data-id]'); if (!li) return;
  if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); pick({layer: li.dataset.layer, id: li.dataset.id}, true); }
  if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
    e.preventDefault();
    let n = li; do { n = e.key === 'ArrowDown' ? n.nextElementSibling : n.previousElementSibling; } while (n && !n.dataset.id);
    n?.focus();
  }
});
$('#detail').addEventListener('click', e => { if (e.target.id === 'close') pick(null); });
addEventListener('keydown', e => { if (e.key === 'Escape') { document.activeElement?.blur?.(); pick(null); } });

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
window.ww = {map, pick, layers: byId};   // handy in the browser console when something looks wrong
renderChips();
loadStatus();
markets.start();
setInterval(loadStatus, 5000);
setInterval(() => { renderFeeds(); renderList(); }, 20000);   // keep the "x min ago" texts moving
