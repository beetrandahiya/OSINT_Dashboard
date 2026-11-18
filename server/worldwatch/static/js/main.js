import {$, ago, api, esc, now} from './util.js';
import {rate, statusEvery, listRows} from './prefs.js';
import {loadFlags} from './flags.js';
import {createMap, paintBase, paintSky, setGlobe, setPhoto, set3D, paint3D, is3D, setGround} from './map.js';
import {look, ground, openSettings, closeSettings} from './look.js';
import * as dense from './dense.js';
import {eyeOn, glyphSvg, themeHidden} from './eyeicons.js';
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
  // while it shows, it follows the panel (a card or dossier can open or close during a request)
  // placed when it appears and when the page's panels change (resize, card opened or closed: 'ww-place'); a 200 ms
  // timer that measured the panels forced a page layout five times a second while tiles loaded
  const show = () => {
    const vis = !!(open || tiles);
    if (vis && bar.hidden) place();
    if (bar.hidden === vis) bar.hidden = !vis;
  };
  addEventListener('resize', () => { if (!bar.hidden) place(); });
  document.addEventListener('ww-place', () => { if (!bar.hidden) requestAnimationFrame(place); });
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
      if (tiles || e.dataType !== 'source' || !e.tile || !String(e.sourceId).startsWith('ww-') || String(e.sourceId).startsWith('ww-ground')) return;   // the ground is not "loading": it is always there
      const src = map.getSource(e.sourceId);
      if (!src || (src.type !== 'raster' && src.type !== 'image')) return;
      if (!tiles) { clearTimeout(tt); tt = setTimeout(() => { tiles = !map.areTilesLoaded(); show(); }, 250); }
    });
    map.on('idle', () => { clearTimeout(tt); tiles = false; show(); });
  };
}
// ---- every panel can be minimised; the choice is remembered on this computer ----
function minimiser(btnId, panelId, key, then) {
  const b = document.getElementById(btnId), p = document.getElementById(panelId); if (!b || !p) return;
  let on = false; try { on = localStorage.getItem(key) === '1'; } catch (e) { /* private window */ }
  const set = v => { on = v; p.classList.toggle('min', v); b.setAttribute('aria-expanded', !v); try { localStorage.setItem(key, v ? '1' : ''); } catch (e) { /* ignore */ } then?.(v); };
  set(on); b.addEventListener('click', e => { e.stopPropagation(); set(!on); });
}
// the map centres on the part the sidebar leaves free; a minimised sidebar is only its header, so it leaves all of it
const sidePad = () => innerWidth > 900 && !$('#sidebar').classList.contains('min') && !eyeOn() ? SIDEBAR_SPACE : 0;
// God's eye (Dense layout): the column is on the right; the map centres on what is left of it
const DENSE_COL = 536;
const rightPad = () => innerWidth > 900 && eyeOn() && !$('#sidebar').classList.contains('min') ? DENSE_COL : 0;
const repad = () => { if (mapRef && !chase) mapRef.easeTo({padding: {...mapRef.getPadding(), left: sidePad(), right: rightPad()}, duration: calm.matches ? 0 : 250}); };
let mapRef = null;
minimiser('side-mini', 'sidebar', 'ww-min-side', () => repad());
minimiser('markets-mini', 'marketsbar', 'ww-min-markets');
minimiser('legend-mini', 'legend', 'ww-min-legend');
let detailMin = false; try { detailMin = localStorage.getItem('ww-min-detail') === '1'; } catch (e) { /* ignore */ }

const map = createMap('map', sidePad());
mapRef = map;
if (rightPad()) map.setPadding({left: sidePad(), top: 0, bottom: 0, right: rightPad()});
window.wwMap = map;   // handy in the browser console
window.wwWatchTiles?.(map);
attachImaged(map);

let on = Object.fromEntries(LAYERS.map(l => [l.id, !l.defaultOff]));
try { Object.assign(on, JSON.parse(localStorage.getItem('ww-layers') || '{}')); } catch (e) { /* private window */ }
let ready = false, picked = null, status = null, lastAnswer = 0, got = new Set(LAYERS.filter(l => l.local).map(l => l.id));

const LOW = ['ww-fires', 'ww-cables', 'ww-gps'];
// The place names change colour over a photo. isStyleLoaded() is false while any tiles load (page start, 3D turning the
// sharp photo on), so it is not the test: before, the recolour was skipped then and the names stayed dark over the photo
// (setPaintProperty only needs the style itself; before that the load handler's repaint() paints with the new state)
onPhoto(v => {
  setPhoto(v);
  const go = () => { try { paintBase(map, dark.matches); } catch (e) { /* style not there yet */ } };
  go();
  if (!map.isStyleLoaded()) map.once('idle', go);
});

function repaint() {
  setGround(map, ground(), look.theme, dark.matches);
  paintBase(map, dark.matches);
  paintSky(map, dark.matches);
  paint3D(map, dark.matches);
  for (const l of LAYERS) l.paint(map, dark.matches);
  map.setPaintProperty('ww-pick', 'circle-stroke-color', eyeOn() ? '#ff3b5c' : dark.matches ? '#ffffff' : '#000000');
  map.setPaintProperty('ww-pick', 'circle-stroke-width', eyeOn() ? 1.3 : 2.5);
}

function show(layer) {
  for (const id of layer.layers) if (map.getLayer(id)) map.setLayoutProperty(id, 'visibility', on[layer.id] && !themeHidden.has(id) ? 'visible' : 'none');
  layer.visible?.(on[layer.id]);
}

// One request per feed, handed to every layer that uses it (ships and warships share "ships", VIP jets and doomsday
// planes "vip_aircraft", ...). What to ask is decided from /api/status, which the page polls anyway: it carries each
// feed's fetch time and the version of its payload (a hash of its bytes; the same data fetched again keeps it). A feed is
// downloaded only when its version moved, and only for layers that are switched on; a refetch that brought back the same
// data only moves the feed's age (its state fields are copied into the answer the layers hold, so every "x min ago"
// stays true without a download). Never more often than the layer asks for (its `feeds` seconds x prefs rate), never
// while the tab is hidden. A layer that is off keeps its chip count from a slow refresh (every 15 min at most);
// layers off by default (cameras, bases, listening stations...) are not downloaded at all until switched on.
// Chips, list and card are redrawn at most once per frame, however many feeds answer.
const users = {};                 // feed -> {layers, secs}
for (const l of LAYERS) for (const [feed, secs] of Object.entries(l.feeds)) {
  const u = users[feed] ||= {layers: [], secs};
  u.layers.push(l); u.secs = Math.min(u.secs, secs);
}
const LIVE = new Set(['ships']);  // merged with the live AIS stream on every request: asked on a timer, not by version
const VIEW_OF = {sites_nuclear: 'sites'};   // a part of another feed (web.py VIEWS): its status is that feed's
const OFF_SECS = 900;
const busy = new Set(), changed = new Set(), fetchedAt = {}, versionAt = {}, loadedAt = {}, held = {};
async function load(feed) {
  if (busy.has(feed)) return;
  busy.add(feed); loadedAt[feed] = performance.now();
  try {
    // `since`: a server that has not fetched the feed again answers {unchanged: true} without the payload
    // live feeds (ships, merged per request) answer {unchanged} when the version `v` the page holds is still current
    const q = LIVE.has(feed) ? (versionAt[feed] ? '?v=' + versionAt[feed] : '') : fetchedAt[feed] ? '?since=' + fetchedAt[feed] : '';
    const d = await api('/api/data/' + feed + q);
    if (d.unchanged) return;
    if (!d.payload) return;   // the server has not fetched this feed yet: the status poll asks again once it has
    if (d.fetched) fetchedAt[feed] = d.fetched;
    versionAt[feed] = d.version; held[feed] = d;
    for (const l of users[feed].layers) {
      try { l.onData(feed, d); got.add(l.id); if (on[l.id]) l.render(map); changed.add(l.id); }   // a switched-off layer is drawn when switched on (toggleLayer), not re-tiled while hidden
      catch (e) { console.error(`layer ${l.id} could not take feed ${feed}:`, e); }   // one layer's fault must not stop the others
    }
    redraw();
  } catch (e) { /* the banner reports a server that stopped answering; one bad answer must not stop the rest */ }
  finally { busy.delete(feed); }
}
// which feeds to ask now, from the status answer (and when a chip is switched on)
const STATE = ['state', 'fetched', 'from_disk', 'data_time', 'data_label', 'items', 'note', 'tried', 'error', 'ok_count', 'fail_count', 'next_at'];
function schedule() {
  if (!ready || document.hidden) return;
  const feeds = Object.fromEntries((status?.feeds || []).map(f => [f.name, f])), t = performance.now();
  for (const [feed, u] of Object.entries(users)) {
    const shown = u.layers.some(l => on[l.id]), wanted = shown || u.layers.some(l => !l.defaultOff);
    if (!wanted) continue;
    const gap = (shown ? u.secs : Math.max(OFF_SECS, u.secs)) * 1000 * rate(), since = t - (loadedAt[feed] ?? -Infinity);
    const s = feeds[VIEW_OF[feed] || feed];
    if (!held[feed]) { if (since > 5000 && (!status || s?.fetched)) load(feed); continue; }   // first load (or the server has it now)
    if (LIVE.has(feed)) { if (shown && since >= gap) load(feed); continue; }
    if (!s || !s.fetched || s.fetched === fetchedAt[feed]) continue;
    if (s.version && s.version === versionAt[feed]) {        // fetched again, same data: only the age moves
      Object.assign(held[feed], Object.fromEntries(STATE.filter(k => k in s).map(k => [k, s[k]])));
      fetchedAt[feed] = s.fetched;
      for (const l of u.layers) changed.add(l.id);
      redraw();
      continue;
    }
    if (since >= gap) load(feed);
  }
}
document.addEventListener('visibilitychange', () => { if (!document.hidden && ready) loadStatus(); });
let frame = 0;
function redraw() {
  if (frame) return;
  frame = requestAnimationFrame(() => {
    frame = 0;
    renderChips(); renderList();
    if (picked && changed.has(picked.layer)) refreshPick();   // other layers' answers leave the open card alone
    changed.clear();
  });
}

map.on('load', () => {
  for (const l of LAYERS) l.addTo(map);
  // one ring for whatever is selected: Apple's guidance asks for an outline as well as a colour change
  map.addSource('ww-pick', {type: 'geojson', data: {type: 'FeatureCollection', features: []}});
  map.addLayer({id: 'ww-pick', type: 'circle', source: 'ww-pick', paint: {'circle-radius': ['get', 'r'], 'circle-color': 'transparent', 'circle-stroke-width': 2.5}});
  attachModels(map);        // 3D aircraft models, above everything else
  repaint();
  loadFlags();
  for (const l of LAYERS) show(l);
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
  // the hand cursor over something clickable: at most once per frame, never while the map moves or a button is held
  // (searching every visible layer on every mouse event was the largest steady cost while the mouse was on the map)
  let hover = null, cursor = '';
  map.on('mousemove', e => {
    if (hover || e.originalEvent.buttons || map.isMoving()) return;
    hover = requestAnimationFrame(() => {
      hover = null;
      const ids = hit.filter(id => map.getLayer(id) && map.getLayoutProperty(id, 'visibility') !== 'none');
      const c = ids.length && map.queryRenderedFeatures([[e.point.x - 2, e.point.y - 2], [e.point.x + 2, e.point.y + 2]], {layers: ids}).some(x => x.properties.id != null || x.properties.cluster) ? 'pointer' : '';
      if (c !== cursor) { cursor = c; map.getCanvas().style.cursor = c; }
    });
  });
  setInterval(() => { if (picked && byId[picked.layer].moving && !document.hidden) ring(); }, 200);
  ready = true;
  dense.init({map, CHIPS, on, toggle: id => toggleLayer(id), ensureOn: id => toggleLayer(id, true), status: () => status, dark: () => dark.matches, shape: g => shape(g), repad});
  renderChips();
  schedule();   // first downloads (status may not have answered yet: then every feed a switched-on layer uses)
});
dark.addEventListener('change', () => ready && repaint());
// Settings sheet: theme, ground, palette, motion (look.js); a change of look repaints the map's ground and colours
$('#settings-btn').onclick = () => openSettings();
document.addEventListener('ww-look', () => { dense.apply(); chipsHtml = null; if (ready) repaint(); renderChips(); legend(); });

// ---- layer chips: each one shows and hides a layer, and says how many items it holds ----
let chipsHtml = '';
const chipCount = l => l.note ? l.note() : got.has(l.id) ? l.count().toLocaleString('en-GB') : '';
function renderChips() {
  if (eyeOn() && chipsHtml != null && dense.patchTiles(chipCount, $('#chips'))) return;   // same tiles: counts and ages patched
  const html = eyeOn() ? dense.tiles(chipCount) : CHIPS.map(l => `<button class="chip" data-id="${l.id}" aria-pressed="${on[l.id]}" style="--c:${l.color[+dark.matches]}"${l.about ? ` title="${esc(l.about())}"` : ''}>
    <span class="swatch"></span>${l.title}<span class="n">${l.note ? l.note() : got.has(l.id) ? l.count().toLocaleString('en-GB') : ''}</span></button>`).join('');
  if (html !== chipsHtml) { $('#chips').innerHTML = html; chipsHtml = html; $('#chips').dataset.look = dense.lookKey(); }
}
$('#chips').addEventListener('click', e => {
  const b = e.target.closest('.chip'); if (!b) return;
  toggleLayer(b.dataset.id);
});
function toggleLayer(id, want) {
  const l = byId[id]; if (!l) return;
  if (want !== undefined && !!on[l.id] === want) return;
  on[l.id] = !on[l.id];
  try { localStorage.setItem('ww-layers', JSON.stringify(on)); } catch (err) { /* private window */ }
  show(l);
  if (on[l.id] && got.has(l.id)) try { l.render(map); } catch (err) { console.error(err); }
  if (on[l.id]) for (const feed of Object.keys(l.feeds)) if (!held[feed] || (status && status.feeds.find(f => f.name === (VIEW_OF[feed] || feed))?.version !== versionAt[feed])) { loadedAt[feed] = -Infinity; }
  if (on[l.id]) schedule();
  renderChips(); renderList(); legend(); dense.refreshSheet();
  if (picked?.layer === l.id && !on[l.id]) pick(null);
}
dark.addEventListener('change', renderChips);
const legend = () => renderLegend($('#legend'), CHIPS, on);
legend(); dark.addEventListener('change', legend);
document.addEventListener('ww-chips', redraw);
document.addEventListener('ww-detail', () => renderDetail(true));
document.addEventListener('ww-flags', () => { if (ready) renderDetail(true); });

// ---- the list: what is coming up first, then the newest things across the layers that are switched on ----
function renderList() {
  const t = now(), rows = [];
  for (const l of CHIPS) if (on[l.id] && got.has(l.id)) for (const r of l.rows()) rows.push({...r, layer: l});
  const coming = rows.filter(r => r.time > t).sort((a, b) => a.time - b.time);
  const past = rows.filter(r => r.time <= t).sort((a, b) => b.time - a.time || (b.order ?? 0) - (a.order ?? 0));
  const li = r => `<li role="option" tabindex="0" data-layer="${r.layer.id}" data-id="${esc(r.id)}" aria-selected="${picked?.layer === r.layer.id && picked.id === r.id}" style="--c:${r.layer.color[+dark.matches]}">
      <span class="badge${r.strong ? ' strong' : ''}">${esc(r.badge)}</span>
      <span class="row-text"><span class="row-title">${esc(r.title)}</span><span class="row-meta">${esc(r.meta)}</span></span>${r.thumb ? `<img class="row-thumb" src="${esc(r.thumb)}" alt="" loading="lazy" onerror="this.remove()">` : ''}</li>`;
  // only the first rows are drawn (prefs.js listRows, 150): all ~1,400 made ~9,000 page elements, rebuilt at every
  // update, and nobody reads row 1,400. "Show all" draws the rest until the page is reloaded.
  const cap = listAll ? Infinity : listRows(), total = coming.length + past.length;
  const c1 = coming.slice(0, cap), p1 = past.slice(0, Math.max(0, cap - c1.length)), more = total - c1.length - p1.length;
  const parts = [...(c1.length ? ['<li class="group">Coming up</li>', ...c1.map(li), '<li class="group">Latest</li>'] : []), ...p1.map(li),
    ...(more ? [`<li class="more"><button class="btn" data-more>Show all ${total.toLocaleString('en-GB')} (${more.toLocaleString('en-GB')} more)</button></li>`] : [])];
  const html = parts.join('');
  const list = $('#list');
  if (html === listHtml) return;
  if (list.contains(document.activeElement) && listHtml != null) return;   // don't pull the list from under the keyboard
  // the same rows with a few changed (a count, an age): only those rows are replaced, not the whole list (its pictures
  // would load and decode again)
  if (listParts && parts.length && parts.length === listParts.length && list.children.length === parts.length) {
    for (let i = 0; i < parts.length; i++) if (parts[i] !== listParts[i]) { const t = document.createElement('template'); t.innerHTML = parts[i]; list.children[i].replaceWith(t.content); }
  } else list.innerHTML = html || '<li class="empty">Nothing to list for the layers that are switched on.</li>';
  listHtml = html; listParts = parts;
}
let listHtml = null, listParts = null, listAll = false;

function ring() {
  const l = picked && byId[picked.layer], at = l?.locate(picked.id);
  const r = at ? l.ring(picked.id) : 0;   // a layer that draws its own selection returns 0 (it can still be flown to)
  const px = 360 / (512 * 2 ** map.getZoom());   // one screen pixel in degrees: a moving item's ring is re-sent only when it moved a pixel
  const key = at && r ? Math.round(at[0] / px) + ',' + Math.round(at[1] / px) + ',' + r : '';
  if (key !== ringKey) { ringKey = key; map.getSource('ww-pick')?.setData({type: 'FeatureCollection', features: key ? [{type: 'Feature', geometry: {type: 'Point', coordinates: at}, properties: {r}}] : []}); }   // asked every 200 ms for moving items: sent only when it moved
  return at;
}
let ringKey = null;

function pick(p, fly = false) {
  if (p && !byId[p.layer]) return;   // a link to a layer that is not loaded (e.g. the disaster imagery, switched off)
  picked = p;
  selectAircraft(p && (p.layer === 'aircraft' || p.layer === 'military' || p.layer === 'vip' || p.layer === 'doomsday') ? p.id : null);
  for (const l of LAYERS) l.select?.(p && p.layer === l.id ? p.id : null);
  document.querySelectorAll('#list li[data-id]').forEach(li => li.setAttribute('aria-selected', !!p && li.dataset.layer === p.layer && li.dataset.id === String(p.id)));
  renderDetail();
  document.dispatchEvent(new Event('ww-place'));
  const at = ring();
  if (at && fly) map.easeTo({center: at, zoom: Math.max(map.getZoom(), 3.2), offset: chase ? [0, 0] : freeOffset(), duration: calm.matches ? 0 : 900});   // into the part no panel covers
  if (p && !fly) document.querySelector(`#list li[data-layer="${p.layer}"][data-id="${CSS.escape(String(p.id))}"]`)?.scrollIntoView({block: 'nearest', behavior: calm.matches ? 'auto' : 'smooth'});
}

// The open card. A new item is drawn from scratch; the same item drawn again is patched: only the parts whose HTML the
// layer changed are touched in the page, so a picture already loaded, a section filled in after drawing, a button the
// user pressed (the satellite picture's day), focus, scroll and the element under the mouse all stay as they are.
let detailKey = '', detailHtml = '', detailWait = false, pressing = false;
const KEEP = ['#route', '#photo', '#actype', '#tracknote', '#more', '#satwho', '#satabout', '#spypass', '#imaged', '#shippic', '#shipabout', '#mxacq', '#cableabout', '#windycam'];
const parse = html => { const t = document.createElement('template'); t.innerHTML = html; return t.content; };
// bring `live` (in the page) from `prev` (what it was drawn from) to `next`; false when the children do not line up
function patch(live, prev, next) {
  const a = live.childNodes, p = prev.childNodes, n = next.childNodes;
  if (a.length !== p.length || p.length !== n.length) return false;
  for (let i = 0; i < n.length; i++) {
    const ai = a[i], pi = p[i], ni = n[i];
    if (pi.isEqualNode(ni)) continue;                                  // unchanged by the layer: leave the page's version alone
    if (pi.nodeType === 3 && ni.nodeType === 3 && ai.nodeType === 3) { ai.nodeValue = ni.nodeValue; continue; }
    if (pi.nodeType === 1 && ni.nodeType === 1 && ai.nodeType === 1 && pi.tagName === ni.tagName && ai.tagName === ni.tagName) {
      for (const {name} of [...pi.attributes]) if (!ni.hasAttribute(name)) ai.removeAttribute(name);
      for (const {name, value} of [...ni.attributes]) if (pi.getAttribute(name) !== value) ai.setAttribute(name, value);
      if (patch(ai, pi, ni)) continue;
    }
    ai.replaceWith(document.importNode(ni, true));
  }
  return true;
}
function renderDetail(force = false) {
  const el = $('#detail'), html = picked && byId[picked.layer].detail(picked.id);
  if (picked && html == null) {   // the item left its feed (a plane landed, a quake aged out): say so, don't keep a ghost
    el.hidden = false;
    el.innerHTML = '<button class="close" id="close" aria-label="Close"></button><p class="eyebrow">No longer in the feed</p><p class="where">This item is not in the latest data any more.</p>';
    detailKey = ''; detailHtml = ''; return;
  }
  el.hidden = !picked;
  if (!picked) { detailKey = ''; detailHtml = ''; return; }
  const key = picked.layer + '|' + picked.id, same = key === detailKey;
  if (same && !force && byId[picked.layer].still) return;   // cards that play video or a stream: redrawing would restart it
  if (same && pressing) { detailWait = true; return; }     // never swap the page under a click; done when the button is let go
  const chaseable = byId[picked.layer].heading && byId[picked.layer].heading(picked.id) !== undefined;
  const chaseBtn = chaseable ? `<p class="links"><button class="btn" data-chase>${chase && chase.id === picked.id ? 'Stop following' : 'Follow it (chase camera)'}</button></p>` : '';
  const full = '<button class="close" id="close" aria-label="Close"></button><button class="mini" id="detail-mini" aria-label="Minimise the card" title="Minimise"></button>' + (chaseBtn && /<\/h2>[\s\S]*?<\/p>/.test(html) ? html.replace(/(<\/h2>[\s\S]*?<\/p>)/, '$1' + chaseBtn) : html + chaseBtn);
  el.classList.toggle('min', detailMin);
  if (same && full === detailHtml) return;                  // nothing changed: touch nothing
  if (same) {
    const prev = parse(detailHtml), next = parse(full);
    // sections filled in after drawing (photo, route, spy passes...) survive whenever the layer left their placeholder as it was
    const keep = KEEP.map(q => [q, $(q)?.innerHTML, $(q)?.dataset.done, prev.querySelector(q)?.outerHTML === next.querySelector(q)?.outerHTML]);
    const scroll = el.scrollTop;
    if (!patch(el, prev, next)) el.innerHTML = full;
    for (const [q, inner, done, untouched] of keep) {
      const x = $(q); if (!x || !untouched || inner == null || x.innerHTML === inner) continue;
      if (done) { x.innerHTML = inner; x.dataset.done = '1'; } else if (q === '#tracknote' && inner) x.innerHTML = inner;
    }
    el.scrollTop = scroll;
  } else {
    el.innerHTML = full;
    el.scrollTop = 0;
  }
  detailKey = key; detailHtml = full;
  fillRoute();
  byId[picked.layer].fill?.(picked.id);   // a layer can fetch more for its card after it is drawn
}
const el0 = () => $('#detail');
function refreshPick() { if (picked) { renderDetail(); ring(); } }
$('#detail').addEventListener('pointerdown', () => { pressing = true; });
for (const ev of ['pointerup', 'pointercancel']) addEventListener(ev, () => { if (!pressing) return; pressing = false; if (detailWait) { detailWait = false; setTimeout(() => renderDetail(), 0); } });

$('#list').addEventListener('click', e => {
  if (e.target.closest('[data-more]')) { listAll = true; listHtml = null; renderList(); return; }
  const li = e.target.closest('li[data-id]'); if (li) pick({layer: li.dataset.layer, id: li.dataset.id}, true);
});
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
  if (a && picked) { byId[picked.layer].act?.(a.dataset.act, map); renderDetail(true); }
});
onSatChange(() => renderDetail(true));
addEventListener('ww-pick', e => pick(e.detail, true));
// a link to an item on another layer: pick it when that layer is on and holds it, otherwise just fly there
addEventListener('ww-try-pick', e => {
  const {layer, id, lon, lat} = e.detail, l = byId[layer];
  if (l && on[layer] && id && l.owns?.(id)) pick({layer, id}, true);
  else map.flyTo({center: [lon, lat], zoom: Math.max(map.getZoom(), 7), duration: calm.matches ? 0 : 1200});
});
addEventListener('ww-fly', e => map.flyTo({...e.detail, duration: calm.matches ? 0 : 1500}));
// Escape closes the top-most thing only: the search list, else the dossier (profile.js closes it), else the card
addEventListener('keydown', e => {
  if (e.key !== 'Escape') return;
  if (closeSettings() || dense.closeSheet()) { e.stopImmediatePropagation(); return; }
  const fl = $('#find-list');
  if (fl && !fl.hidden) { fl.hidden = true; document.activeElement?.blur?.(); e.stopImmediatePropagation(); return; }
  if (document.querySelector('#profile:not([hidden])')) return;
  document.activeElement?.blur?.(); pick(null);
});

// The projection the user chose (Globe / Map buttons, remembered) and the one drawn are kept apart: while the chase
// camera follows something the map is drawn flat (see there). What is drawn is always worked out from the two in
// project(), so no sequence of follows, stops and button presses can lose the choice. The buttons show the choice.
let userGlobe = false, lent = false;   // lent: a layer has the globe for a moment (satellites' "Look down" from the flat map)
function project() {
  const want = (userGlobe || lent) && !chase;
  $('#flat').setAttribute('aria-pressed', !userGlobe);
  $('#globe').setAttribute('aria-pressed', userGlobe);
  $('#globe').title = chase && userGlobe ? 'The globe comes back when you stop following' : '';
  if (want === (map.getProjection?.()?.type === 'globe')) return;
  setGlobe(map, want);
  setTimeout(() => { for (const l of LAYERS) l.shape?.(map); ring(); }, 60);
}
function shape(globe, save = true) {
  userGlobe = globe; lent = false;
  if (save) try { localStorage.setItem('ww-globe', globe ? '1' : ''); } catch (e) { /* private window */ }
  project();
}
$('#flat').onclick = () => shape(false);
$('#globe').onclick = () => shape(true);
// a layer borrowing the globe for a moment (satellites' "Look down") and handing it back: never the user's choice, never saved
document.addEventListener('ww-shape', e => { lent = !!e.detail?.globe && !userGlobe; project(); });
map.on('load', () => { try { if (localStorage.getItem('ww-globe')) shape(true); } catch (e) { /* private window */ } });
// ---- 3D: terrain and buildings, tilt and turn ----
const on3 = l => !!on[l.id];
let sharpBy3D = false;      // the sharp satellite photo is the ground in 3D; switched off again only if 3D turned it on
function three(want) {
  set3D(map, want, dark.matches);
  const sharp = byId.sharp;
  // the sharp photo is the 3D ground, unless the ground already is that photo (Photo and Mono use the same Esri pictures
  // when zoomed in: two identical picture layers draped on the terrain)
  if (sharp && want && !on3(sharp) && !['photo', 'mono'].includes(ground())) { on[sharp.id] = true; sharpBy3D = true; show(sharp); renderChips(); legend(); }
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
// centre), so while following the map is drawn flat, and goes back to the globe on Stop if that is the user's choice
// (project() above).
// Looking around: drag to orbit and tilt, the bar's buttons turn 45°, point north, or go back behind it; wheel zooms.
let chase = null;
const ease = u => u < 0.5 ? 4 * u * u * u : 1 - (-2 * u + 2) ** 3 / 2;
const shortest = (a, b) => ((b - a + 540) % 360) - 180;
// the part of the map no panel covers: the target is kept in its middle. The panel on the left and the card on the
// right take their side; every other panel over the map (legend, markets strip, the follow bar, zoom and compass) that
// reaches into what is left is cut off from whichever edge leaves the most room. On a short window the legend sat in
// the middle of the map, over the followed aircraft, and took its mouse wheel.
const visibleEl = el => el && !el.hidden && el.getClientRects().length > 0;
function freeArea() {
  const cv = map.getCanvas().getBoundingClientRect(), pad = {top: 0, bottom: 0, left: 0, right: 0};
  const side = $('#sidebar'), card = $('#detail');
  // a panel on the left half takes the left side, one on the right half the right side (Apple Maps: sidebar left, card
  // right; God's eye: both in the column on the right)
  for (const el of [side, card]) {
    if (!visibleEl(el)) continue;
    const r = el.getBoundingClientRect(); if (r.height <= 120) continue;
    if (r.left + r.width / 2 < cv.left + cv.width / 2) pad.left = Math.max(pad.left, r.right - cv.left); else pad.right = Math.max(pad.right, cv.right - r.left);
  }
  if (pad.left + pad.right > cv.width - 160) { pad.left = 0; pad.right = 0; }   // too little room: use the whole map
  for (const el of document.querySelectorAll('#legend, #marketsbar, #chasebar, .maplibregl-ctrl-group')) {
    if (!visibleEl(el) || el === side || el === card) continue;
    const r = el.getBoundingClientRect();
    if (!r.width || !r.height || r.right <= cv.left + pad.left || r.left >= cv.right - pad.right || r.bottom <= cv.top + pad.top || r.top >= cv.bottom - pad.bottom) continue;
    const cut = {left: r.right - cv.left, right: cv.right - r.left, top: r.bottom - cv.top, bottom: cv.bottom - r.top};
    let best = null, area = -1;
    for (const k of ['left', 'right', 'top', 'bottom']) {
      const p = {...pad, [k]: Math.max(pad[k], cut[k])}, a = Math.max(0, cv.width - p.left - p.right) * Math.max(0, cv.height - p.top - p.bottom);
      if (a > area) { area = a; best = p; }
    }
    if (best.left + best.right <= cv.width - 160 && best.top + best.bottom <= cv.height - 120) Object.assign(pad, best);
  }
  return pad;
}
// how far a target must sit from the middle of the map's padded area to be in the middle of the free area (easeTo offset)
function freeOffset() {
  const f = freeArea(), p = map.getPadding();
  return [((f.left - f.right) - (p.left - p.right)) / 2, ((f.top - f.bottom) - (p.top - p.bottom)) / 2];
}
function groundAgain(level, padding, then) {
  const go = () => {
    if (chase) return;
    const g = (is3D() && map.queryTerrainElevation?.(map.getCenter())) || 0;
    // listening first: with Reduce Motion the move is instant and its moveend fires inside easeTo
    map.once('moveend', () => { if (chase) return; map.setCenterClampedToGround(true); then?.(); });
    map.easeTo({elevation: g, padding, ...(level ? {pitch: 0, bearing: 0} : {}), duration: calm.matches ? 0 : 700});
  };
  if (map.isMoving()) map.once('moveend', go); else go();
}
function chaseStop(level = true, after = null) {   // after: called once the camera is back on the ground
  if (!chase) return;
  cancelAnimationFrame(chase.raf);
  const {padWas} = chase; chase = null;
  $('#chasebar')?.remove();
  map.scrollZoom.enable();
  map.dragPan.enable();
  project();   // the buttons' title; the globe itself comes back once the camera is on the ground again
  groundAgain(level && !is3D(), padWas, () => { project(); after?.(); });
  renderDetail(true);
}
function chaseStart() {
  if (!picked) return;
  const layer = byId[picked.layer], id = picked.id;
  const where = () => layer.locate3d?.(id) || (layer.locate(id) && [...layer.locate(id), 0]);
  if (!where()) return;
  chaseStop(false);
  const padWas = map.getPadding();
  const ship = picked.layer === 'ships' || picked.layer === 'warships' || picked.layer === 'sanctioned';
  const c0 = map.getCenter();
  chase = {layer, id, raf: 0, t0: performance.now(), last: performance.now(),
    from: {lon: c0.lng, lat: c0.lat, alt: map.getCenterElevation() || 0, zoom: map.getZoom(), pitch: map.getPitch(), bearing: map.getBearing()},
    zoom: Math.max(map.getZoom(), ship ? 12 : 10.5), pitch: 62, pitchWant: 62, bearing: layer.heading?.(id) ?? map.getBearing(),
    mode: 'behind', free: 0, intro: calm.matches ? 0 : 1600, padWas, pad: {...padWas}, padAt: 0, landed: false};
  lent = false; project();   // drawn flat while following (a borrowed globe is not given back afterwards)
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
  renderDetail(true);   // the card's button now reads "Stop following"
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
    const to = u < 1 ? {center: [f.lon + dl * e, f.lat + (p[1] - f.lat) * e], elevation: f.alt + (p[2] - f.alt) * e, zoom: f.zoom + (chase.zoom - f.zoom) * e,
        pitch: f.pitch + (chase.pitch - f.pitch) * e, bearing: f.bearing + shortest(f.bearing, chase.bearing) * e, padding: {...chase.pad}}
      : {center: [p[0], p[1]], elevation: p[2], bearing: chase.bearing, pitch: chase.pitch, padding: {...chase.pad}};
    // the glide in ends exactly at its zoom even when the last frames of it were dropped (afterwards the wheel owns the zoom)
    if (u >= 1 && !chase.landed) { chase.landed = true; if (chase.intro) to.zoom = chase.zoom; }
    map.jumpTo(to);
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
let fixed = null;
async function loadStatus() {
  if (document.hidden) return;   // nothing is asked while the tab is hidden; it asks at once when it shows again
  try {
    // the full answer once and while the feeds list is open; otherwise the light one, with the fixed fields kept from before
    const full = !fixed || !$('#feeds-body').hidden;
    const s = await api('/api/status' + (full ? '' : '?lite=1'));
    if (full) fixed = Object.fromEntries(s.feeds.map(f => [f.name, f]));
    else s.feeds = s.feeds.map(f => ({...fixed[f.name], ...f}));
    status = s; lastAnswer = Date.now();
  } catch (e) { /* shown by the banner */ }
  renderFeeds();
  schedule();
}
function renderFeeds() {
  const down = Date.now() - lastAnswer > 7000 + statusEvery() * 1.5;   // a missed poll or two is not "down"
  if ($('#banner').hidden !== !down) $('#banner').hidden = !down;
  if (down) $('#banner').textContent = lastAnswer ? `The World Watch server stopped answering ${ago(lastAnswer / 1000, Date.now() / 1000)}. Everything on screen is from before that.` : 'The World Watch server is not answering.';
  if (!status) return;
  const f = status.feeds, bad = f.filter(x => x.state === 'failing'), late = f.filter(x => x.state === 'late'), wait = f.filter(x => x.state === 'waiting');
  const unset = wait.filter(x => /^not set up/.test(x.note || '')).length;   // optional keys the owner has not added: they will never "start"
  const ok = f.length - bad.length - late.length - wait.length;
  const dotCls = 'dot ' + (down || bad.length ? 'bad' : late.length ? 'warn' : wait.length > unset ? 'idle' : 'good');
  if ($('#feeds-dot').className !== dotCls) $('#feeds-dot').className = dotCls;
  const sum = down ? 'Server not answering'
    : bad.length ? `${bad.length} of ${f.length} feeds failing` + (late.length ? `, ${late.length} late` : '')
    : late.length ? `${late.length} of ${f.length} feeds late`
    : wait.length > unset ? `${ok} of ${f.length} feeds in, ${wait.length - unset} starting` + (unset ? `, ${unset} not set up` : '')
    : unset ? `${ok} of ${f.length} feeds current, ${unset} not set up` : `All ${f.length} feeds current`;
  if ($('#feeds-sum').textContent !== sum) $('#feeds-sum').textContent = sum;
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
let worldView = null, where = 'world';
function place(to) {
  if (to === where) return;          // pressing Munich again must not overwrite the saved world view with Munich
  where = to;
  const m = to === 'munich';
  $('#world').setAttribute('aria-pressed', !m); $('#home').setAttribute('aria-pressed', m);
  $('#list').hidden = m; $('#munich').hidden = !m;
  munich.show(m);
  const ease = {duration: calm.matches ? 0 : 1200};
  // the world view to come back to is the map as it was before a follow, not the chase camera's close, tilted view
  const f = chase?.from, before = f && {center: [f.lon, f.lat], zoom: f.zoom, bearing: f.bearing, pitch: f.pitch};
  const fly = () => {
    if (m) { worldView = before || {center: map.getCenter(), zoom: map.getZoom(), bearing: map.getBearing(), pitch: map.getPitch()}; const h = munich.home(); map.easeTo({center: [h.lon, h.lat], zoom: 8.3, bearing: 0, pitch: 0, ...ease}); }
    else if (worldView) map.easeTo({...worldView, ...ease});
  };
  // a running chase camera moves the map every frame and would override the flight: stop it, fly once it has landed
  if (chase) chaseStop(false, fly); else fly();
}
$('#world').onclick = () => place('world');
$('#home').onclick = () => place('munich');

renderChips();
loadStatus();
markets.start();
(function statusLoop() { setTimeout(() => { loadStatus().finally(statusLoop); }, statusEvery()); })();   // 5 s, 30 s in low power (prefs.js)
setInterval(() => { if (document.hidden) return; renderFeeds(); renderList(); refreshPick(); }, 20000);   // keep the "x min ago" texts moving (the card is patched, not redrawn)

// ---- find a person (header search) ----
let findTimer = null;
$('#find-q')?.addEventListener('input', e => {
  clearTimeout(findTimer); const q = e.target.value.trim(); const list = $('#find-list');
  if (q.length < 2) { list.hidden = true; return; }
  const lands = () => countryMatches(q).map(c => `<li data-cc="${esc(c.iso)}"><b>${esc(c.name)}</b><span>Country dossier</span></li>`).join('');
  // things on the map now: rows of the layers that are on whose title holds every word typed
  const words = q.toLowerCase().split(/\s+/), items = [];
  for (const l of CHIPS) { if (!on[l.id] || !got.has(l.id)) continue; for (const r of l.rows()) { const t = String(r.title).toLowerCase(); if (words.every(w => t.includes(w))) items.push({l, r}); } if (items.length > 40) break; }
  const onMap = items.slice(0, 6).map(({l, r}) => `<li data-layer="${l.id}" data-id="${esc(r.id)}">${eyeOn() && dense.ICON[l.id] ? glyphSvg(dense.ICON[l.id], 20, dark.matches, l.id === 'military' ? 'mil' : null) : ''}<b>${esc(r.title)}</b><span>${esc(l.title)} · ${esc(r.meta || '')}</span></li>`).join('');
  list.innerHTML = (lands() ? '<li class="group">Countries</li>' + lands() : '') + (onMap ? '<li class="group">On the map now</li>' + onMap : '') + '<li class="group">People</li><li class="empty" id="find-people">Searching people…</li>'; list.hidden = false;   // countries answer at once, people need Wikidata
  findTimer = setTimeout(async () => {
    let people = '';
    try {
      const r = await fetch('/api/people/search?q=' + encodeURIComponent(q), {cache: 'no-store'});
      const d = await r.json();
      people = d.error ? `<li class="empty">${esc(d.error)}</li>` : (d.results || []).map(p => `<li data-qid="${esc(p.qid)}"><b>${esc(p.name)}</b>${p.description ? `<span>${esc(p.description)}</span>` : ''}</li>`).join('');
    } catch (err) { people = '<li class="empty">People search did not answer.</li>'; }
    if ($('#find-q').value.trim() !== q) return;
    // replace only the people placeholder: the country rows stay the same nodes, so a click on one is never lost
    const ph = $('#find-people');
    if (ph) ph.outerHTML = people || '<li class="empty">No person found on Wikidata.</li>';
    list.hidden = false;
  }, 300);
});
$('#find-q')?.addEventListener('focus', loadCountries, {once: true});
$('#find-list')?.addEventListener('click', e => {
  const li = e.target.closest('li[data-qid], li[data-cc], li[data-layer]'); if (!li) return;
  if (li.dataset.layer) pick({layer: li.dataset.layer, id: li.dataset.id}, true);
  else if (li.dataset.cc) openCountry({cc: li.dataset.cc}); else openProfile(li.dataset.qid);
  $('#find-list').hidden = true; $('#find-q').value = '';
});
addEventListener('click', e => { if (!e.target.closest('.find')) $('#find-list')?.setAttribute('hidden', ''); });
