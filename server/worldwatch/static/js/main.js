import {$, ago, api, esc, now} from './util.js';
import {loadFlags} from './flags.js';
import {createMap, paintBase, paintSky, setGlobe, setPhoto} from './map.js';
import news from './news.js';
import navwarn from './navwarn.js';
import maxarLayer from './maxar.js';
import airspace from './airspace.js';
import {unrest, unrestSingle} from './unrest.js';
import quakes from './quakes.js';
import outages from './outages.js';
import {civil, military, vip, doomsday, fillRoute, select as selectAircraft} from './aircraft.js';
import {satellites, launches, onSatChange} from './space.js';
import hazards from './hazards.js';
import cables from './cables.js';
import {rain, night, aurora, photo, onPhoto, lightning, sharp, livephoto} from './sky.js';
import fires from './fires.js';
import people, {leadersToday} from './people.js';
import {openProfile} from './profile.js';
import ships, {warships} from './ships.js';
import gps, {gpsLive} from './gps.js';
import * as munichView from './munich.js';
import * as markets from './markets.js';

// Order = drawing order on the map, bottom first.
const LAYERS = [photo, livephoto, sharp, maxarLayer, night, aurora, gps, gpsLive, airspace, cables, fires, ships, warships, people, leadersToday, civil, military, vip, doomsday, satellites, outages, launches, hazards, navwarn, quakes, unrestSingle, unrest, news, rain, lightning];
const CHIPS = [news, unrest, unrestSingle, navwarn, airspace, quakes, hazards, outages, civil, military, vip, doomsday, satellites, launches, ships, warships, people, leadersToday, fires, gps, gpsLive, cables, rain, lightning, night, aurora, photo, livephoto, sharp, maxarLayer];
const byId = Object.fromEntries(LAYERS.map(l => [l.id, l]));

const SIDEBAR_SPACE = 420;   // the sidebar's width plus its margins; the map centres on what is left
const dark = matchMedia('(prefers-color-scheme: dark)');
const calm = matchMedia('(prefers-reduced-motion: reduce)');
// ---- a thin loading bar while any request to our server takes longer than a moment ----
{
  const bar = document.getElementById('loadbar'), real = window.fetch.bind(window);
  let open = 0, t = null;
  const show = () => { bar.hidden = open === 0; };
  window.fetch = (input, init) => {
    const url = typeof input === 'string' ? input : input?.url || '';
    if (!url.includes('/api/') || url.includes('/api/status')) return real(input, init);   // the status poll is constant; not "loading"
    open++; clearTimeout(t); t = setTimeout(show, 250);
    return real(input, init).finally(() => { open = Math.max(0, open - 1); if (!open) { clearTimeout(t); bar.hidden = true; } });
  };
}
// ---- every panel can be minimised; the choice is remembered on this computer ----
function minimiser(btnId, panelId, key) {
  const b = document.getElementById(btnId), p = document.getElementById(panelId); if (!b || !p) return;
  let on = false; try { on = localStorage.getItem(key) === '1'; } catch (e) { /* private window */ }
  const set = v => { on = v; p.classList.toggle('min', v); b.setAttribute('aria-expanded', !v); try { localStorage.setItem(key, v ? '1' : ''); } catch (e) { /* ignore */ } };
  set(on); b.addEventListener('click', e => { e.stopPropagation(); set(!on); });
}
minimiser('side-mini', 'sidebar', 'ww-min-side');
minimiser('markets-mini', 'marketsbar', 'ww-min-markets');
let detailMin = false; try { detailMin = localStorage.getItem('ww-min-detail') === '1'; } catch (e) { /* ignore */ }

const map = createMap('map', innerWidth > 900 ? SIDEBAR_SPACE : 0);

let on = Object.fromEntries(LAYERS.map(l => [l.id, !l.defaultOff]));
try { Object.assign(on, JSON.parse(localStorage.getItem('ww-layers') || '{}')); } catch (e) { /* private window */ }
let ready = false, picked = null, status = null, lastAnswer = 0, got = new Set(LAYERS.filter(l => l.local).map(l => l.id));

const LOW = ['ww-fires', 'ww-cables-hit', 'ww-gps'];
onPhoto(v => { setPhoto(v); if (map.isStyleLoaded()) paintBase(map, dark.matches); });

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
    if (!d.payload) { setTimeout(() => load(layer, feed), 5000); return; }   // the server has not fetched this feed yet: ask again shortly
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
  loadFlags();
  for (const l of LAYERS) {
    show(l);
    for (const [feed, secs] of Object.entries(l.feeds)) { load(l, feed); setInterval(() => load(l, feed), secs * 1000); }
  }
  const NO_CLICK = ['ww-ship-trail', 'ww-photo', 'ww-live-goesw', 'ww-live-goese', 'ww-live-iodc', 'ww-live-mtg', 'ww-sharp', 'ww-lightning', 'ww-night', 'ww-rain', 'ww-aurora', 'ww-cables', 'ww-iss-track', 'ww-air-route', 'ww-air-trail', 'ww-hazards-track', 'ww-people-label'];
  const hit = LAYERS.flatMap(l => l.layers).filter(id => !NO_CLICK.includes(id));
  map.on('click', e => {
    const f = map.queryRenderedFeatures([[e.point.x - 4, e.point.y - 4], [e.point.x + 4, e.point.y + 4]], {layers: hit.filter(id => map.getLayoutProperty(id, 'visibility') !== 'none')})
      .filter(x => x.properties.id != null || x.properties.qid != null || x.properties.cluster).sort((a, b) => LOW.indexOf(a.layer.id) - LOW.indexOf(b.layer.id))[0];   // markers win over fire dots, cables and hexagons
    if (!f) { for (const l of LAYERS) { const id = on[l.id] && l.hit?.(e.point); if (id) return pick({layer: l.id, id}); } return pick(null); }
    const layer = LAYERS.find(l => l.layers.includes(f.layer.id) && (!l.owns || l.owns(f.properties.id))) || LAYERS.find(l => l.layers.includes(f.layer.id));
    if (layer.pick && layer.pick(f.properties) === false) return;
    pick({layer: layer.id, id: f.properties.id});
  });
  map.on('mousemove', e => { map.getCanvas().style.cursor = map.queryRenderedFeatures(e.point, {layers: hit.filter(id => map.getLayer(id) && map.getLayoutProperty(id, 'visibility') !== 'none')}).some(x => x.properties.id != null || x.properties.cluster) ? 'pointer' : ''; });
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
document.addEventListener('ww-chips', renderChips);
document.addEventListener('ww-detail', () => { detailKey = ''; renderDetail(); });
document.addEventListener('ww-flags', () => { if (ready) { detailKey = ''; renderDetail(); } });

// ---- the list: what is coming up first, then the newest things across the layers that are switched on ----
function renderList() {
  const t = now(), rows = [];
  for (const l of CHIPS) if (on[l.id] && got.has(l.id)) for (const r of l.rows()) rows.push({...r, layer: l});
  const coming = rows.filter(r => r.time > t).sort((a, b) => a.time - b.time);
  const past = rows.filter(r => r.time <= t).sort((a, b) => b.time - a.time || (b.order ?? 0) - (a.order ?? 0));
  const li = r => `<li role="option" tabindex="0" data-layer="${r.layer.id}" data-id="${esc(r.id)}" aria-selected="${picked?.layer === r.layer.id && picked.id === r.id}" style="--c:${r.layer.color[+dark.matches]}">
      <span class="badge${r.strong ? ' strong' : ''}">${esc(r.badge)}</span>
      <span class="row-text"><span class="row-title">${esc(r.title)}</span><span class="row-meta">${esc(r.meta)}</span></span>${r.thumb ? `<img class="row-thumb" src="${esc(r.thumb)}" alt="" loading="lazy" onerror="this.remove()">` : ''}</li>`;
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
  selectAircraft(p && (p.layer === 'aircraft' || p.layer === 'military' || p.layer === 'vip' || p.layer === 'doomsday') ? p.id : null);
  for (const l of LAYERS) l.select?.(p && p.layer === l.id ? p.id : null);
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
  const keep = key === detailKey ? ['#route', '#photo', '#tracknote', '#more', '#satwho', '#satabout', '#spypass', '#shippic', '#shipabout', '#mxacq'].map(q => [q, $(q)?.innerHTML, $(q)?.dataset.done]) : [];
  el.innerHTML = '<button class="close" id="close" aria-label="Close"></button><button class="mini" id="detail-mini" aria-label="Minimise the card" title="Minimise"></button>' + html;
  el.classList.toggle('min', detailMin);
  for (const [q, inner, done] of keep) if (done && $(q)) { $(q).innerHTML = inner; $(q).dataset.done = '1'; } else if (q === '#tracknote' && inner && $(q)) $(q).innerHTML = inner;
  el.scrollTop = key === detailKey ? scroll : 0;
  detailKey = key;
  fillRoute();
  byId[picked.layer].fill?.(picked.id);   // a layer can fetch more for its card after it is drawn
}
const el0 = () => $('#detail');
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
$('#detail').addEventListener('click', e => {
  if (e.target.id === 'close') return pick(null);
  if (e.target.id === 'detail-mini') { detailMin = !detailMin; el0().classList.toggle('min', detailMin); try { localStorage.setItem('ww-min-detail', detailMin ? '1' : ''); } catch (err) { /* ignore */ } return; }
  const a = e.target.closest('[data-act]');
  if (a && picked) { byId[picked.layer].act?.(a.dataset.act, map); detailKey = ''; renderDetail(); }
});
onSatChange(() => { detailKey = ''; renderDetail(); });
addEventListener('ww-pick', e => pick(e.detail, true));
addEventListener('ww-fly', e => map.flyTo({...e.detail, duration: calm.matches ? 0 : 1500}));
addEventListener('keydown', e => { if (e.key === 'Escape') { document.activeElement?.blur?.(); pick(null); } });

function shape(globe) {
  setGlobe(map, globe);
  setTimeout(() => { for (const l of LAYERS) l.shape?.(map); ring(); }, 60);
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
// ---- World / Munich ----
const munich = munichView.start(hex => pick({layer: military.owns(hex) ? 'military' : 'aircraft', id: hex}));
let worldView = null;
function place(where) {
  const m = where === 'munich';
  $('#world').setAttribute('aria-pressed', !m); $('#home').setAttribute('aria-pressed', m);
  $('#list').hidden = m; $('#munich').hidden = !m;
  munich.show(m);
  const ease = {duration: calm.matches ? 0 : 1200};
  if (m) { worldView = {center: map.getCenter(), zoom: map.getZoom()}; const h = munich.home(); map.easeTo({center: [h.lon, h.lat], zoom: 8.3, ...ease}); }
  else if (worldView) map.easeTo({...worldView, ...ease});
}
$('#world').onclick = () => place('world');
$('#home').onclick = () => place('munich');

renderChips();
loadStatus();
markets.start();
setInterval(loadStatus, 5000);
setInterval(() => { renderFeeds(); renderList(); }, 20000);   // keep the "x min ago" texts moving

// ---- find a person (header search) ----
let findTimer = null;
$('#find-q')?.addEventListener('input', e => {
  clearTimeout(findTimer); const q = e.target.value.trim(); const list = $('#find-list');
  if (q.length < 2) { list.hidden = true; return; }
  findTimer = setTimeout(async () => {
    try {
      const r = await fetch('/api/people/search?q=' + encodeURIComponent(q), {cache: 'no-store'});
      const d = await r.json(); if ($('#find-q').value.trim() !== q) return;
      list.innerHTML = (d.results || []).map(p => `<li data-qid="${esc(p.qid)}"><b>${esc(p.name)}</b>${p.description ? `<span>${esc(p.description)}</span>` : ''}</li>`).join('') || '<li class="empty">No person found.</li>';
      list.hidden = false;
    } catch (err) { /* ignore */ }
  }, 300);
});
$('#find-list')?.addEventListener('click', e => { const li = e.target.closest('li[data-qid]'); if (li) { openProfile(li.dataset.qid); $('#find-list').hidden = true; $('#find-q').value = ''; } });
addEventListener('click', e => { if (!e.target.closest('.find')) $('#find-list')?.setAttribute('hidden', ''); });
