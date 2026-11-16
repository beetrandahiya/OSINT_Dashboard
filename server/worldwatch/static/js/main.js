import {$, ago, api, esc, now} from './util.js';
import {loadFlags} from './flags.js';
import {createMap, paintBase, paintSky, setGlobe, setPhoto, set3D, paint3D, is3D} from './map.js';
import news from './news.js';
import navwarn from './navwarn.js';
// import maxarLayer from './maxar.js';   // disaster imagery: off for now, see CHIPS
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
import {countryMatches, loadCountries, openCountry} from './dossier_country.js';
import ships, {warships} from './ships.js';
import gps, {gpsLive} from './gps.js';
import front from './frontline.js';
import {orbits, tankers} from './patterns.js';
import {bases, nuclear} from './sites.js';
import hijacks from './netwatch.js';
import cameras from './cameras.js';
import sdr from './sdr.js';
import hotspots from './hotspots.js';
import sanctioned from './sanctioned.js';
import spikes from './spikes.js';
import * as munichView from './munich.js';
import * as markets from './markets.js';
import {renderLegend} from './legend.js';
import {attachImaged} from './imaged.js';
import {attachModels} from './models3d.js';

// Order = drawing order on the map, bottom first.
const LAYERS = [photo, livephoto, sharp, night, aurora, gps, gpsLive, front, bases, nuclear, airspace, hijacks, cables, fires, ships, warships, cameras, sdr, sanctioned, people, leadersToday, civil, military, orbits, tankers, vip, doomsday, satellites, outages, launches, hazards, navwarn, quakes, unrestSingle, unrest, news, spikes, hotspots, rain, lightning];
const CHIPS = [hotspots, news, spikes, unrest, unrestSingle, front, navwarn, airspace, quakes, hazards, outages, hijacks, bases, nuclear, civil, military, orbits, tankers, vip, doomsday, satellites, launches, ships, warships, sanctioned, cameras, sdr, people, leadersToday, fires, gps, gpsLive, cables, rain, lightning, night, aurora, photo, livephoto, sharp];   // disaster imagery (maxar.js) is off for now at the owner's request; code and feeds kept
const byId = Object.fromEntries(LAYERS.map(l => [l.id, l]));

const SIDEBAR_SPACE = 420;   // the sidebar's width plus its margins; the map centres on what is left
const dark = matchMedia('(prefers-color-scheme: dark)');
const calm = matchMedia('(prefers-reduced-motion: reduce)');
// ---- a thin loading bar while any request to our server takes longer than a moment ----
{
  const bar = document.getElementById('loadbar'), real = window.fetch.bind(window);
  let open = 0, t = null;
  // the bar sits on the top edge of the panel being looked at: an open dossier, else the card, else the sidebar
  const place = () => {
    const vis = el => el && !el.hidden && el.offsetParent !== null && el.getBoundingClientRect().height > 0;
    const t = [document.querySelector('#profile:not([hidden]) .prof-card'), document.getElementById('detail'), document.getElementById('sidebar')].find(vis);
    if (!t) return;
    const r = t.getBoundingClientRect(), inset = 14;            // stay inside the panel's rounded corners
    Object.assign(bar.style, {left: r.left + inset + 'px', top: r.top + 1 + 'px', width: Math.max(0, r.width - inset * 2) + 'px'});
  };
  let tiles = false;                          // picture layers (photo, live photo, sharp photo, rain, lightning) loading tiles
  const show = () => { if (open || tiles) place(); bar.hidden = !(open || tiles); };
  window.fetch = (input, init) => {
    const url = typeof input === 'string' ? input : input?.url || '';
    if (!url.includes('/api/') || url.includes('/api/status')) return real(input, init);   // the status poll is constant; not "loading"
    open++; clearTimeout(t); t = setTimeout(show, 250);
    return real(input, init).finally(() => { open = Math.max(0, open - 1); if (!open) { clearTimeout(t); show(); } });
  };
  // called once the map exists: tiles of raster sources count as loading until the map is idle again
  window.wwWatchTiles = map => {
    let tt = null;
    map.on('dataloading', e => {
      if (e.dataType !== 'source' || !e.tile || !String(e.sourceId).startsWith('ww-')) return;
      const src = map.getSource(e.sourceId);
      if (!src || (src.type !== 'raster' && src.type !== 'image')) return;
      if (!tiles) { clearTimeout(tt); tt = setTimeout(() => { tiles = !map.areTilesLoaded(); show(); }, 250); }
    });
    map.on('idle', () => { clearTimeout(tt); tiles = false; show(); });
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
minimiser('legend-mini', 'legend', 'ww-min-legend');
let detailMin = false; try { detailMin = localStorage.getItem('ww-min-detail') === '1'; } catch (e) { /* ignore */ }

const map = createMap('map', innerWidth > 900 ? SIDEBAR_SPACE : 0);
window.wwMap = map;   // handy in the browser console
window.wwWatchTiles?.(map);
attachImaged(map);

let on = Object.fromEntries(LAYERS.map(l => [l.id, !l.defaultOff]));
try { Object.assign(on, JSON.parse(localStorage.getItem('ww-layers') || '{}')); } catch (e) { /* private window */ }
let ready = false, picked = null, status = null, lastAnswer = 0, got = new Set(LAYERS.filter(l => l.local).map(l => l.id));

const LOW = ['ww-fires', 'ww-cables-hit', 'ww-gps'];
onPhoto(v => { setPhoto(v); if (map.isStyleLoaded()) paintBase(map, dark.matches); });

function repaint() {
  paintBase(map, dark.matches);
  paintSky(map, dark.matches);
  paint3D(map, dark.matches);
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
  attachModels(map);        // 3D aircraft models, above everything else
  repaint();
  loadFlags();
  for (const l of LAYERS) {
    show(l);
    for (const [feed, secs] of Object.entries(l.feeds)) { load(l, feed); setInterval(() => load(l, feed), secs * 1000); }
  }
  const NO_CLICK = ['ww-ship-trail', 'ww-photo', 'ww-live-goesw', 'ww-live-goese', 'ww-live-iodc', 'ww-live-mtg', 'ww-sharp', 'ww-lightning', 'ww-night', 'ww-rain', 'ww-aurora', 'ww-cables', 'ww-iss-track', 'ww-air-route', 'ww-air-trail', 'ww-hazards-track', 'ww-people-label'];
  const hit = LAYERS.flatMap(l => l.layers).filter(id => !NO_CLICK.includes(id));
  map.on('click', e => {
    if (chase && orbitMoved > 4) { orbitMoved = 0; return; }   // the end of a drag around the followed target, not a click
    const f = map.queryRenderedFeatures([[e.point.x - 4, e.point.y - 4], [e.point.x + 4, e.point.y + 4]], {layers: hit.filter(id => map.getLayoutProperty(id, 'visibility') !== 'none')})
      .filter(x => x.properties.id != null || x.properties.qid != null || x.properties.cluster).sort((a, b) => LOW.indexOf(a.layer.id) - LOW.indexOf(b.layer.id))[0];   // markers win over fire dots, cables and hexagons
    if (!f) { for (const l of LAYERS) { const id = on[l.id] && l.hit?.(e.point); if (id) return pick({layer: l.id, id}); } return chase ? undefined : pick(null); }   // a click on empty map does not end a follow
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
  show(l); renderChips(); renderList(); legend();
  if (picked?.layer === l.id && !on[l.id]) pick(null);
});
dark.addEventListener('change', renderChips);
const legend = () => renderLegend($('#legend'), CHIPS, on);
legend(); dark.addEventListener('change', legend);
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
  const r = at ? l.ring(picked.id) : 0;   // a layer that draws its own selection returns 0 (it can still be flown to)
  map.getSource('ww-pick')?.setData({type: 'FeatureCollection', features: at && r ? [{type: 'Feature', geometry: {type: 'Point', coordinates: at}, properties: {r}}] : []});
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
  if (key === detailKey && byId[picked.layer].still) return;   // cards that play video or a stream: redrawing would restart it
  const keep = key === detailKey ? ['#route', '#photo', '#actype', '#tracknote', '#more', '#satwho', '#satabout', '#spypass', '#imaged', '#shippic', '#shipabout', '#mxacq', '#cableabout', '#windycam'].map(q => [q, $(q)?.innerHTML, $(q)?.dataset.done]) : [];
  const chaseable = byId[picked.layer].heading && byId[picked.layer].heading(picked.id) !== undefined;
  const chaseBtn = chaseable ? `<p class="links"><button class="btn" data-chase>${chase && chase.id === picked.id ? 'Stop following' : 'Follow it (chase camera)'}</button></p>` : '';
  el.innerHTML = '<button class="close" id="close" aria-label="Close"></button><button class="mini" id="detail-mini" aria-label="Minimise the card" title="Minimise"></button>' + (chaseBtn && /<\/h2>[\s\S]*?<\/p>/.test(html) ? html.replace(/(<\/h2>[\s\S]*?<\/p>)/, '$1' + chaseBtn) : html + chaseBtn);
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
// a link to an item on another layer: pick it when that layer is on and holds it, otherwise just fly there
addEventListener('ww-try-pick', e => {
  const {layer, id, lon, lat} = e.detail, l = byId[layer];
  if (l && on[layer] && id && l.owns?.(id)) pick({layer, id}, true);
  else map.flyTo({center: [lon, lat], zoom: Math.max(map.getZoom(), 7), duration: calm.matches ? 0 : 1200});
});
addEventListener('ww-fly', e => map.flyTo({...e.detail, duration: calm.matches ? 0 : 1500}));
addEventListener('keydown', e => { if (e.key === 'Escape') { document.activeElement?.blur?.(); pick(null); } });

function shape(globe, save = true) {
  setGlobe(map, globe);
  setTimeout(() => { for (const l of LAYERS) l.shape?.(map); ring(); }, 60);
  $('#flat').setAttribute('aria-pressed', !globe);
  $('#globe').setAttribute('aria-pressed', globe);
  if (save) try { localStorage.setItem('ww-globe', globe ? '1' : ''); } catch (e) { /* private window */ }
}
$('#flat').onclick = () => { if (chase) chase.wasGlobe = false; shape(false); };
$('#globe').onclick = () => { if (chase) chase.wasGlobe = true; else shape(true); };
map.on('load', () => { try { if (localStorage.getItem('ww-globe')) shape(true); } catch (e) { /* private window */ } });
// ---- 3D: terrain and buildings, tilt and turn ----
const on3 = l => !!on[l.id];
let sharpBy3D = false;      // the sharp satellite photo is the ground in 3D; switched off again only if 3D turned it on
function three(want) {
  set3D(map, want, dark.matches);
  const sharp = byId.sharp;
  if (sharp && want && !on3(sharp)) { on[sharp.id] = true; sharpBy3D = true; show(sharp); renderChips(); legend(); }
  if (sharp && !want && sharpBy3D) { on[sharp.id] = false; sharpBy3D = false; show(sharp); renderChips(); legend(); }
  $('#three').setAttribute('aria-pressed', want);
  try { localStorage.setItem('ww-3d', want ? '1' : ''); } catch (e) { /* private window */ }
}
$('#three').onclick = () => three(!is3D());
map.on('load', () => { try { if (localStorage.getItem('ww-3d')) three(true); } catch (e) { /* private window */ } });

// ---- chase camera: lock onto a moving aircraft or ship, tilted, turning with its heading ----
// One animation loop owns the camera while it follows: the first 1.6 s glide from where the camera was to behind the
// target, then the camera centre is the target itself, in the air for an aircraft (the map's centre point is lifted
// to its altitude). The target's own position is already smooth (aircraft.js display()), so the camera never jerks.
// The globe projection ignores a lifted centre below zoom ~12 (measured: a point 10 km up stayed 290 px above the
// centre), so while following on the globe the map uses the flat projection, and goes back to the globe on Stop.
// Looking around: drag to orbit and tilt, the bar's buttons turn 45°, point north, or go back behind it; wheel zooms.
let chase = null;
const ease = u => u < 0.5 ? 4 * u * u * u : 1 - (-2 * u + 2) ** 3 / 2;
const shortest = (a, b) => ((b - a + 540) % 360) - 180;
const globeOn = () => $('#globe').getAttribute('aria-pressed') === 'true';
// the part of the map not covered by the panel on the left and the card on the right: the target is kept in its middle
function freeArea() {
  const cv = map.getCanvas().getBoundingClientRect(), pad = {top: 0, bottom: 0, left: 0, right: 0};
  const side = $('#sidebar'), card = $('#detail');
  if (side && !side.hidden) { const r = side.getBoundingClientRect(); if (r.height > 120) pad.left = Math.max(0, r.right - cv.left); }
  if (card && !card.hidden) { const r = card.getBoundingClientRect(); if (r.height > 120) pad.right = Math.max(0, cv.right - r.left); }
  if (pad.left + pad.right > cv.width - 160) { pad.left = 0; pad.right = 0; }   // too little room: use the whole map
  return pad;
}
function groundAgain(level, padding, then) {
  const go = () => {
    if (chase) return;
    const g = (is3D() && map.queryTerrainElevation?.(map.getCenter())) || 0;
    map.easeTo({elevation: g, padding, ...(level ? {pitch: 0, bearing: 0} : {}), duration: calm.matches ? 0 : 700});
    map.once('moveend', () => { if (chase) return; map.setCenterClampedToGround(true); then?.(); });
  };
  if (map.isMoving()) map.once('moveend', go); else go();
}
function chaseStop(level = true) {
  if (!chase) return;
  cancelAnimationFrame(chase.raf);
  const {padWas, wasGlobe} = chase; chase = null;
  $('#chasebar')?.remove();
  map.scrollZoom.enable();
  map.dragPan.enable();
  groundAgain(level && !is3D(), padWas, wasGlobe ? () => shape(true, false) : null);
  detailKey = ''; renderDetail();
}
function chaseStart() {
  if (!picked) return;
  const layer = byId[picked.layer], id = picked.id;
  const where = () => layer.locate3d?.(id) || (layer.locate(id) && [...layer.locate(id), 0]);
  if (!where()) return;
  chaseStop(false);
  const wasGlobe = globeOn();
  if (wasGlobe) shape(false, false);
  const padWas = map.getPadding();
  const ship = picked.layer === 'ships' || picked.layer === 'warships' || picked.layer === 'sanctioned';
  const c0 = map.getCenter();
  chase = {layer, id, raf: 0, t0: performance.now(), last: performance.now(), wasGlobe,
    from: {lon: c0.lng, lat: c0.lat, alt: map.getCenterElevation() || 0, zoom: map.getZoom(), pitch: map.getPitch(), bearing: map.getBearing()},
    zoom: Math.max(map.getZoom(), ship ? 12 : 10.5), pitch: 62, pitchWant: 62, bearing: layer.heading?.(id) ?? map.getBearing(),
    mode: 'behind', free: 0, intro: calm.matches ? 0 : 1600, padWas, pad: {...padWas}, padAt: 0};
  map.setCenterClampedToGround(false);
  map.scrollZoom.enable({around: 'center'});
  map.dragPan.disable();   // a drag orbits around the target instead (below)
  const bar = document.createElement('div');
  bar.id = 'chasebar'; bar.className = 'glass chasebar';
  bar.innerHTML = `<span>Following</span><b>${esc(document.querySelector('#detail h2')?.textContent || 'it')}</b>
    <button class="btn icon" data-orbit="-45" title="Turn left" aria-label="Turn left">↺</button><button class="btn icon" data-orbit="45" title="Turn right" aria-label="Turn right">↻</button>
    <button class="btn icon" data-orbit="north" title="North up" aria-label="North up">N</button><button class="btn" data-orbit="behind" title="Look the way it is going">Behind it</button>
    <button class="btn" id="chasestop">Stop</button>`;
  bar.title = 'Drag the map to look around it; the wheel zooms';
  document.body.appendChild(bar);
  $('#chasestop').onclick = () => chaseStop();
  detailKey = ''; renderDetail();   // the card's button now reads "Stop following"
  const step = () => {
    if (!chase) return;
    const t = performance.now(), dt = Math.min(0.1, (t - chase.last) / 1000); chase.last = t;
    const p = where();
    if (!p || !picked || picked.id !== chase.id) { chaseStop(); return; }
    const want = chase.mode === 'behind' ? chase.layer.heading?.(chase.id) : chase.free;
    if (want != null) chase.bearing += shortest(chase.bearing, want) * (1 - Math.exp(-dt / (chase.mode === 'behind' && !chase.turning ? 2.5 : 0.25)));
    if (chase.turning && Math.abs(shortest(chase.bearing, want ?? chase.bearing)) < 1) chase.turning = false;
    chase.pitch += (chase.pitchWant - chase.pitch) * (1 - Math.exp(-dt / 0.15));
    const u = chase.intro ? Math.min(1, (t - chase.t0) / chase.intro) : 1, e = ease(u), f = chase.from;
    if (t - chase.padAt > 400) { chase.padAt = t; chase.padWant = freeArea(); }
    for (const k of ['left', 'right', 'top', 'bottom']) chase.pad[k] += (chase.padWant[k] - chase.pad[k]) * (1 - Math.exp(-dt / 0.3));
    let dl = p[0] - f.lon; if (dl > 180) dl -= 360; if (dl < -180) dl += 360;
    map.jumpTo(u < 1 ? {center: [f.lon + dl * e, f.lat + (p[1] - f.lat) * e], elevation: f.alt + (p[2] - f.alt) * e, zoom: f.zoom + (chase.zoom - f.zoom) * e,
        pitch: f.pitch + (chase.pitch - f.pitch) * e, bearing: f.bearing + shortest(f.bearing, chase.bearing) * e, padding: {...chase.pad}}
      : {center: [p[0], p[1]], elevation: p[2], bearing: chase.bearing, pitch: chase.pitch, padding: {...chase.pad}});
    chase.raf = requestAnimationFrame(step);
  };
  chase.raf = requestAnimationFrame(step);
}
// the bar's buttons: turn 45°, north up, back behind it
document.addEventListener('click', e => {
  const b = e.target.closest('[data-orbit]'); if (!b || !chase) return;
  const v = b.dataset.orbit;
  if (v === 'behind') chase.mode = 'behind';
  else { chase.free = v === 'north' ? 0 : (chase.mode === 'free' ? chase.free : chase.bearing) + Number(v); chase.mode = 'free'; }
  chase.turning = true;
});
// dragging while following orbits around the target (sideways turns, up and down tilts) instead of ending the follow
let orbitAt = null;
let orbitMoved = 0;
map.getCanvas().addEventListener('pointerdown', e => { if (chase && e.button === 0) { orbitAt = [e.clientX, e.clientY]; orbitMoved = 0; map.getCanvas().setPointerCapture(e.pointerId); } });
map.getCanvas().addEventListener('pointermove', e => {
  if (!chase || !orbitAt) return;
  const dx = e.clientX - orbitAt[0], dy = e.clientY - orbitAt[1]; orbitAt = [e.clientX, e.clientY]; orbitMoved += Math.abs(dx) + Math.abs(dy);
  if (chase.mode !== 'free') { chase.mode = 'free'; chase.free = chase.bearing; }
  chase.free -= dx * 0.3; chase.turning = true;
  chase.pitchWant = Math.max(0, Math.min(map.getMaxPitch(), chase.pitchWant - dy * 0.25));
});
addEventListener('pointerup', () => { orbitAt = null; });
document.addEventListener('click', e => { if (e.target.closest('[data-chase]')) { e.preventDefault(); chase ? chaseStop() : chaseStart(); } });
// the compass resets to north; while following it points the follow camera north instead
document.addEventListener('click', e => { if (chase && e.target.closest('.maplibregl-ctrl-compass')) { e.stopPropagation(); chase.mode = 'free'; chase.free = 0; chase.turning = true; } }, true);

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
  const lands = () => countryMatches(q).map(c => `<li data-cc="${esc(c.iso)}"><b>${esc(c.name)}</b><span>Country dossier</span></li>`).join('');
  list.innerHTML = lands() + '<li class="empty">Searching people…</li>'; list.hidden = false;   // countries answer at once, people need Wikidata
  findTimer = setTimeout(async () => {
    let people = '';
    try {
      const r = await fetch('/api/people/search?q=' + encodeURIComponent(q), {cache: 'no-store'});
      const d = await r.json();
      people = d.error ? `<li class="empty">${esc(d.error)}</li>` : (d.results || []).map(p => `<li data-qid="${esc(p.qid)}"><b>${esc(p.name)}</b>${p.description ? `<span>${esc(p.description)}</span>` : ''}</li>`).join('');
    } catch (err) { people = '<li class="empty">People search did not answer.</li>'; }
    if ($('#find-q').value.trim() !== q) return;
    list.innerHTML = lands() + people || '<li class="empty">No person or country found.</li>';
    list.hidden = false;
  }, 300);
});
$('#find-q')?.addEventListener('focus', loadCountries, {once: true});
$('#find-list')?.addEventListener('click', e => {
  const li = e.target.closest('li[data-qid], li[data-cc]'); if (!li) return;
  if (li.dataset.cc) openCountry({cc: li.dataset.cc}); else openProfile(li.dataset.qid);
  $('#find-list').hidden = true; $('#find-q').value = '';
});
addEventListener('click', e => { if (!e.target.closest('.find')) $('#find-list')?.setAttribute('hidden', ''); });
