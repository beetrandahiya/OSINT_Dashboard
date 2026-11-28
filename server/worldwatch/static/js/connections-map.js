// Connections, on the map: the companies of the structure at the place the registers give (headquarters from
// Wikidata, else the postal code or town of the GLEIF address: connections/places.py), the ownership lines between
// them coloured by the register that states them, and, with the switch "Their aircraft and ships now", the
// companies' live aircraft and ships (connections/assets.py): solid line = registered owner (or Wikidata owner for a
// ship), dashed = flight number only (or Wikidata operator). Where Wikidata contradicts itself the link stays, flagged.
// MapLibre (and this module's map) load only when the view is first opened, so the graph view stays light.
import {createMap, paintBase, setGround, paintSky, setGlobe} from './map.js';
import {look, ground} from './look.js';
import {eyeImages, aircraftSymbol} from './eyeicons.js';

const SHIP_EYE = {'Cargo ship': 'cargo', 'Tanker': 'tanker_s', 'Passenger ship': 'passenger', 'Tug': 'tug', 'Port tender': 'tug', 'Dredger': 'tug',
  'Pilot vessel': 'sar', 'Search and rescue vessel': 'sar', 'Military vessel': 'warship_s', 'Sailing vessel': 'sailing', 'Pleasure craft': 'pleasure',
  'High-speed craft': 'hsc', 'Fishing vessel': 'fishing', 'Fishing': 'fishing'};
const dark = matchMedia('(prefers-color-scheme: dark)');
const EMPTY = {type: 'FeatureCollection', features: []};
let map = null, ready = null, ctx = null, shown = false;
let placesData = {places: {}, unplaced: {}, problems: []}, placesKey = '', assetsData = null, assetsErr = null, timer = 0, sel = null;
let assetsOn = (() => { try { return localStorage.getItem('cx-assets') === '1'; } catch (e) { return false; } })();

const col = () => dark.matches
  ? {GLEIF: '#8fdcff', Wikidata: '#c7b8ff', Offshore: '#ff8fa3', OpenSanctions: '#ffe066', place: '#f2f4f6', focus: '#8fdcff', ink: '#0d1216', label: '#f2f4f6', halo: 'rgba(0,0,0,0.8)', link: '#f2f4f6'}
  : {GLEIF: '#0a6d99', Wikidata: '#5b4bb7', Offshore: '#b4304f', OpenSanctions: '#8f7420', place: '#0b141b', focus: '#0a6d99', ink: '#ffffff', label: '#0b141b', halo: 'rgba(255,255,255,0.9)', link: '#1d2a33'};

function loadLib() {
  if (window.maplibregl) return Promise.resolve();
  return new Promise((res, rej) => {
    const css = document.createElement('link'); css.rel = 'stylesheet'; css.href = new URL('../vendor/maplibre-gl.css', import.meta.url).href; document.head.append(css);
    const s = document.createElement('script'); s.src = new URL('../vendor/maplibre-gl.js', import.meta.url).href; s.onload = res; s.onerror = () => rej(new Error('the map engine did not load')); document.head.append(s);
  });
}
const panelPad = () => innerWidth > 900 ? 492 : 0;

// ctx: {el, structure() -> {nodes, edges, focus, selected}, api, esc, setPanel(html), onCompany(ref), legend(html)}
export async function open(c) {
  ctx = c; shown = true;
  if (!ready) ready = (async () => {
    await loadLib();
    map = createMap(c.el, panelPad());
    window.cxMap = map;                       // for looking at it from the browser console
    await new Promise(r => map.once('style.load', r));
    theme();
    setGlobe(map, true);
    layers();
    map.on('click', click);
    map.on('mousemove', e => { const f = hits(e.point); map.getCanvas().style.cursor = f ? 'pointer' : ''; });
    dark.addEventListener('change', () => { theme(); recolour(); draw(); });
    addEventListener('resize', () => map.setPadding({left: panelPad(), top: 0, right: 0, bottom: 0}));
  })();
  await ready;
  map.resize();
  ctx.legend(legend());
  await refresh(true);
  schedule();
}
export function close() { shown = false; clearTimeout(timer); }
export const isOpen = () => shown;

function theme() {
  setGround(map, ground(), look.theme, dark.matches);
  paintBase(map, dark.matches);
  paintSky(map, dark.matches);
  eyeImages(map, dark.matches);
}

function layers() {
  for (const id of ['cx-arcs', 'cx-places', 'cx-alines', 'cx-assets', 'cx-sel']) map.addSource(id, {type: 'geojson', data: EMPTY});
  const c = col();
  map.addLayer({id: 'cx-arcs', type: 'line', source: 'cx-arcs', filter: ['!', ['get', 'dash']], layout: {'line-cap': 'round'}, paint: {'line-width': 1.6, 'line-opacity': 0.9}});
  map.addLayer({id: 'cx-arcs-d', type: 'line', source: 'cx-arcs', filter: ['get', 'dash'], paint: {'line-width': 1.4, 'line-opacity': 0.85, 'line-dasharray': [3, 2]}});
  map.addLayer({id: 'cx-alines', type: 'line', source: 'cx-alines', filter: ['==', ['get', 'how'], 'owner'], paint: {'line-width': 0.9, 'line-opacity': 0.4}});
  map.addLayer({id: 'cx-alines-d', type: 'line', source: 'cx-alines', filter: ['!=', ['get', 'how'], 'owner'], paint: {'line-width': 1, 'line-opacity': 0.55, 'line-dasharray': [2, 2]}});
  map.addLayer({id: 'cx-assets', type: 'symbol', source: 'cx-assets', layout: {'icon-image': ['get', 'icon'], 'icon-size': ['interpolate', ['linear'], ['zoom'], 1, 0.34, 5, 0.5, 9, 0.7],
    'icon-rotate': ['get', 'rot'], 'icon-rotation-alignment': 'map', 'icon-allow-overlap': true, 'icon-ignore-placement': true}, paint: {'icon-opacity': ['case', ['get', 'old'], 0.5, 1]}});
  map.addLayer({id: 'cx-assets-l', type: 'symbol', source: 'cx-assets', minzoom: 4.5, layout: {'text-field': ['get', 'label'], 'text-font': ['Noto Sans Bold'], 'text-size': 10.5,
    'text-offset': [0, 1.3], 'text-anchor': 'top', 'text-optional': true}, paint: {'text-halo-width': 1.2}});
  map.addLayer({id: 'cx-places-c', type: 'circle', source: 'cx-places', paint: {'circle-radius': ['+', 5, ['*', 2, ['sqrt', ['get', 'n']]]], 'circle-stroke-width': 2}});
  map.addLayer({id: 'cx-places-n', type: 'symbol', source: 'cx-places', filter: ['>', ['get', 'n'], 1], layout: {'text-field': ['to-string', ['get', 'n']], 'text-font': ['Noto Sans Bold'],
    'text-size': 10, 'text-allow-overlap': true, 'text-ignore-placement': true}});
  map.addLayer({id: 'cx-places-l', type: 'symbol', source: 'cx-places', layout: {'text-field': ['step', ['zoom'], ['case', ['get', 'core'], ['get', 'label'], ''], 4.5, ['get', 'label']], 'text-font': ['Noto Sans Bold'], 'text-size': 11.5,
    'text-anchor': 'left', 'text-offset': [1.2, 0], 'text-optional': true, 'text-max-width': 22, 'symbol-sort-key': ['case', ['get', 'focus'], 0, 1]}, paint: {'text-halo-width': 1.4}});
  map.addLayer({id: 'cx-sel', type: 'circle', source: 'cx-sel', paint: {'circle-radius': ['get', 'r'], 'circle-color': 'transparent', 'circle-stroke-color': '#ff3b5c', 'circle-stroke-width': 1.5}});
  recolour();
}
function recolour() {
  const c = col();
  const src = ['match', ['get', 'src'], 'GLEIF', c.GLEIF, 'Wikidata', c.Wikidata, 'Offshore Leaks', c.Offshore, 'OpenSanctions', c.OpenSanctions, c.place];
  map.setPaintProperty('cx-arcs', 'line-color', src); map.setPaintProperty('cx-arcs-d', 'line-color', src);
  map.setPaintProperty('cx-alines', 'line-color', c.link); map.setPaintProperty('cx-alines-d', 'line-color', c.link);
  map.setPaintProperty('cx-places-c', 'circle-color', ['case', ['get', 'focus'], c.focus, ['get', 'extra'], 'rgba(0,0,0,0)', c.place]);
  map.setPaintProperty('cx-places-c', 'circle-stroke-color', ['case', ['get', 'extra'], c.place, c.halo]);
  map.setPaintProperty('cx-places-n', 'text-color', c.ink);
  for (const id of ['cx-places-l', 'cx-assets-l']) { map.setPaintProperty(id, 'text-color', c.label); map.setPaintProperty(id, 'text-halo-color', c.halo); }
}

// ---------------------------------------------------------------- data
function refs() {
  const {nodes, focus} = ctx.structure();
  const all = [...nodes.values()].filter(n => !n.stub && !n.exc && /^(lei|wd|icij|os):/.test(n.ref)).map(n => n.ref);
  return [focus, ...all.filter(r => r !== focus)].filter(Boolean).slice(0, 120);
}
export async function refresh(fit) {
  if (!shown || !map) return;
  const r = refs();
  const key = [...r].sort().join(',');
  if (key && key !== placesKey) {
    placesKey = key;
    ctx.setPanel(listHtml(true));
    placesData = await ctx.api('/api/connections/places?refs=' + encodeURIComponent(r.join(',')));
    placesData.places ||= {}; placesData.unplaced ||= {};
    if (fit) fitAll();
  }
  if (assetsOn) await loadAssets(); else { assetsData = null; assetsErr = null; }
  draw();
  ctx.setPanel(listHtml());
}
async function loadAssets() {
  const {nodes, alias} = ctx.structure();
  const same = [...(alias || new Map()).entries()].filter(([a, c]) => a.startsWith('wd:') && nodes.has(c)).map(([a, c]) => a + '>' + c).slice(0, 200);
  const d = await ctx.api('/api/connections/assets?refs=' + encodeURIComponent(refs().join(',')) + (same.length ? '&same=' + encodeURIComponent(same.join(',')) : ''));
  if (d.error) { assetsErr = d.error; return; }
  assetsErr = null; assetsData = d;
}
function schedule() {
  clearTimeout(timer);
  if (!shown || !assetsOn) return;
  timer = setTimeout(async () => { if (!document.hidden) { await loadAssets(); draw(); if (!sel || sel.kind !== 'asset') ctx.setPanel(listHtml()); } schedule(); },
    assetsData?.pending ? 20000 : 60000);       // registers still being looked up: ask again sooner
}
export function setAssets(on) {
  assetsOn = on;
  for (const id of ['cx-assets-tb', 'cx-assets-sw']) { const el = document.getElementById(id); if (el) el.checked = on; }
  try { localStorage.setItem('cx-assets', on ? '1' : '0'); } catch (e) { /* private window */ }
  ctx.legend(legend());
  refresh().then(() => schedule());
}
export const assetsShown = () => assetsOn;

// places of companies: the page's structure, plus companies only the asset answer knows (one level below, e.g. an airline's
// own airline subsidiary) when they have aircraft or ships now
function placeOf(ref) {
  return placesData.places[ref] || assetsData?.companies?.[ref]?.place || null;
}
function nameOf(ref) {
  return ctx.structure().nodes.get(ref)?.name || assetsData?.companies?.[ref]?.name || ref;
}
function km(a, b) {
  const r = Math.PI / 180, dl = (b[1] - a[1]) * r, dn = (b[0] - a[0]) * r;
  return 12742 * Math.asin(Math.sqrt(Math.sin(dl / 2) ** 2 + Math.cos(a[1] * r) * Math.cos(b[1] * r) * Math.sin(dn / 2) ** 2));
}
function gc(a, b, n = 48) {      // great-circle points, longitudes unwrapped so a line never jumps across the map
  const r = Math.PI / 180, [lo1, la1, lo2, la2] = [a[0] * r, a[1] * r, b[0] * r, b[1] * r];
  const d = 2 * Math.asin(Math.sqrt(Math.sin((la2 - la1) / 2) ** 2 + Math.cos(la1) * Math.cos(la2) * Math.sin((lo2 - lo1) / 2) ** 2));
  if (d < 1e-6) return null;
  const out = [];
  let prev = null, off = 0;
  for (let i = 0; i <= n; i++) {
    const f = i / n, A = Math.sin((1 - f) * d) / Math.sin(d), B = Math.sin(f * d) / Math.sin(d);
    const x = A * Math.cos(la1) * Math.cos(lo1) + B * Math.cos(la2) * Math.cos(lo2), y = A * Math.cos(la1) * Math.sin(lo1) + B * Math.cos(la2) * Math.sin(lo2), z = A * Math.sin(la1) + B * Math.sin(la2);
    let lon = Math.atan2(y, x) / r;
    const lat = Math.atan2(z, Math.hypot(x, y)) / r;
    if (prev !== null) { if (lon + off - prev > 180) off -= 360; else if (lon + off - prev < -180) off += 360; }
    lon += off; prev = lon;
    out.push([lon, lat]);
  }
  return out;
}
function draw() {
  if (!map || !map.getSource('cx-places')) return;
  const {nodes, edges, focus} = ctx.structure();
  // places: one dot per place, the companies there listed
  const groups = new Map();
  const add = (ref, extra) => {
    const p = placeOf(ref); if (!p) return;
    const k = p.lat.toFixed(3) + ',' + p.lon.toFixed(3);
    const g = groups.get(k) || groups.set(k, {p, refs: [], extra: true}).get(k);
    if (!g.refs.includes(ref)) g.refs.push(ref);
    if (!extra) g.extra = false;
  };
  for (const n of nodes.values()) if (!n.stub && !n.exc) add(n.ref, false);
  if (assetsData) for (const [ref, c] of Object.entries(assetsData.companies || {})) if (!c.in_graph && (c.owns || c.flies || c.ships)) add(ref, true);
  const core = new Set([focus]);
  for (const e of edges.values()) { if (e.from === focus) core.add(e.to); if (e.to === focus) core.add(e.from); }
  const pf = [];
  for (const g of groups.values()) {
    const isFocus = g.refs.includes(focus), first = isFocus ? focus : (g.refs.find(r => core.has(r)) || g.refs[0]);
    pf.push({type: 'Feature', geometry: {type: 'Point', coordinates: [g.p.lon, g.p.lat]},
      properties: {refs: g.refs.join(' '), n: g.refs.length, focus: isFocus, extra: g.extra, core: g.refs.some(r => core.has(r)) || g.extra, label: `${nameOf(first)}${g.refs.length > 1 ? ` +${g.refs.length - 1}` : ''}`}});
  }
  pf.sort((a, b) => a.properties.n - b.properties.n);
  map.getSource('cx-places').setData({type: 'FeatureCollection', features: pf});
  // ownership lines between placed companies
  const af = [];
  for (const e of edges.values()) {
    const a = placeOf(e.from), b = placeOf(e.to); if (!a || !b) continue;
    const pts = gc([a.lon, a.lat], [b.lon, b.lat]); if (!pts) continue;
    af.push({type: 'Feature', geometry: {type: 'LineString', coordinates: pts}, properties: {src: e.source || '', dash: !!e.ultimate}});
  }
  map.getSource('cx-arcs').setData({type: 'FeatureCollection', features: af});
  // aircraft and ships
  const sf = [], lf = [];
  for (const a of (assetsOn && assetsData?.assets) || []) {
    const ship = a.kind === 'ship';
    const icon = ship ? 'eye-' + (SHIP_EYE[a.ship_kind] || 'cargo') : 'eye-' + aircraftSymbol({type: a.type, category: a.category}, a.military) + (a.military ? '-mil' : '');
    const rot = ship ? (a.heading != null && a.heading < 360 ? a.heading : a.course || 0) : (a.track || 0);
    const old = (assetsData.now - (a.time || 0)) > (ship ? 3600 : 1800);
    sf.push({type: 'Feature', geometry: {type: 'Point', coordinates: [a.lon, a.lat]}, properties: {key: a.kind + ':' + a.id, icon, rot, label: a.label || '', old}});
    const p = placeOf(a.link.ref);
    if (p) { const pts = gc([a.lon, a.lat], [p.lon, p.lat], 24); if (pts) lf.push({type: 'Feature', geometry: {type: 'LineString', coordinates: pts}, properties: {how: a.link.how}}); }
  }
  map.getSource('cx-assets').setData({type: 'FeatureCollection', features: sf});
  map.getSource('cx-alines').setData({type: 'FeatureCollection', features: lf});
  ring();
}
function ring() {
  let at = null, r = 14;
  if (sel?.kind === 'company') { const p = placeOf(sel.ref); if (p) at = [p.lon, p.lat]; }
  if (sel?.kind === 'asset') { const a = (assetsData?.assets || []).find(x => x.kind + ':' + x.id === sel.key); if (a) { at = [a.lon, a.lat]; r = 15; } }
  map.getSource('cx-sel').setData(at ? {type: 'FeatureCollection', features: [{type: 'Feature', geometry: {type: 'Point', coordinates: at}, properties: {r}}]} : EMPTY);
}
function fitAll() {
  // the opened company with its direct owners and holdings (siblings far away, and aircraft all over the world, would
  // otherwise swing the globe away from it); one point or a spread over half the world: centre on it instead
  const {nodes, edges, focus} = ctx.structure();
  const core = new Set([focus]);
  for (const e of edges.values()) { if (e.from === focus) core.add(e.to); if (e.to === focus) core.add(e.from); }
  let pts = [...core].map(placeOf).filter(Boolean).map(p => [p.lon, p.lat]);
  if (!pts.length) for (const n of nodes.values()) { const p = placeOf(n.ref); if (p) pts.push([p.lon, p.lat]); }
  if (!pts.length) return;
  const at = placeOf(focus) ? [placeOf(focus).lon, placeOf(focus).lat] : pts[0];
  pts = pts.filter(p => km(p, at) < 3000);              // far holdings stay on the globe, outside the first view
  const lons = pts.map(p => p[0]), lats = pts.map(p => p[1]);
  const pad = {left: panelPad() + 40, right: 300, top: 110, bottom: 90};
  if (pts.length < 2 || Math.max(...lons) - Math.min(...lons) > 150 || Math.max(...lats) - Math.min(...lats) > 70)
    return map.easeTo({center: at, zoom: pts.length < 2 ? 4 : 2.2, padding: pad, duration: 600});
  map.fitBounds([[Math.min(...lons), Math.min(...lats)], [Math.max(...lons), Math.max(...lats)]], {padding: pad, maxZoom: 7, duration: 600});
}
export const fit = () => { if (map) fitAll(); };

function hits(point) {
  return map.queryRenderedFeatures(point, {layers: ['cx-assets', 'cx-places-c']})[0] || null;
}
function click(e) {
  const f = hits(e.point);
  if (!f) return;
  if (f.layer.id === 'cx-assets') return showAsset(f.properties.key);
  const rs = f.properties.refs.split(' ');
  if (rs.length === 1) return company(rs[0]);
  sel = null; ring();
  ctx.setPanel(placeHtml(rs));
}
async function company(ref) {
  sel = {kind: 'company', ref}; ring();
  await ctx.onCompany(ref);
}
function showAsset(key) {
  const a = (assetsData?.assets || []).find(x => x.kind + ':' + x.id === key);
  if (!a) return;
  sel = {kind: 'asset', key}; ring();
  ctx.setPanel(assetHtml(a));
}

// ---------------------------------------------------------------- panel
const E = s => ctx.esc(s);
const ago = t => { if (!t) return ''; const s = Math.max(0, Date.now() / 1000 - t); return s < 90 ? `${Math.round(s)} s ago` : s < 5400 ? `${Math.round(s / 60)} min ago` : s < 172800 ? `${Math.round(s / 3600)} h ago` : `${Math.round(s / 86400)} days ago`; };
const hhmm = t => t ? new Date(t * 1000).toISOString().slice(11, 16) + ' UTC' : '';
function listHtml(loading) {
  const {nodes, focus} = ctx.structure();
  const comps = [...nodes.values()].filter(n => !n.stub && !n.exc);
  const placed = comps.filter(n => placesData.places[n.ref]);
  const byPlace = new Map();
  for (const n of placed) { const p = placesData.places[n.ref]; const k = p.place || `${p.lat.toFixed(2)}, ${p.lon.toFixed(2)}`; (byPlace.get(k) || byPlace.set(k, []).get(k)).push(n); }
  const unplaced = comps.filter(n => !placesData.places[n.ref]);
  let h = `<div class="kind">On the map</div><h2>${E(nodes.get(focus)?.name || '')}</h2>
    <p class="soft">${loading ? 'Finding where the companies sit…' : `${placed.length} of ${comps.length} companies placed.`} A dot is a headquarters or registered address, not where a company works.</p>
    <label class="cx-switch"><input type="checkbox" id="cx-assets-sw"${assetsOn ? ' checked' : ''}><span>Their aircraft and ships now</span></label>`;
  if (assetsOn) h += assetsHtml();
  h += `<div class="sec"><h3>Where they sit <span class="n-count">${placed.length}</span></h3>${[...byPlace.entries()].sort((a, b) => b[1].length - a[1].length).map(([k, ns]) =>
    `<div class="cx-place"><b>${E(k)}</b><ul class="rows">${ns.map(n => { const p = placesData.places[n.ref];
      return `<li data-cx-company="${E(n.ref)}"><span class="t">${E(n.name)}${n.ref === focus ? ' <span class="pill">opened</span>' : ''}</span><span class="faint">${E(p.source)}</span><span class="m">${E(p.how)}</span></li>`; }).join('')}</ul></div>`).join('')}</div>`;
  if (unplaced.length) h += `<div class="sec"><h3>Not placed <span class="n-count">${unplaced.length}</span></h3><ul class="rows">${unplaced.map(n =>
    `<li data-cx-company="${E(n.ref)}"><span class="t">${E(n.name)}</span><span class="m">${E(placesData.unplaced[n.ref] || 'no location in the sources')}</span></li>`).join('')}</ul></div>`;
  if (placesData.problems?.length) h += `<p class="problems">${placesData.problems.map(E).join('<br>')}</p>`;
  h += `<p class="note">Places: Wikidata headquarters, else the postal code or town of the GLEIF address (GeoNames postal codes, CC BY 4.0)${placesData.postal === false ? ' (the postal table is still being built on this computer)' : ''}. Lines: who owns whom, coloured by the register that says so.</p>`;
  return h;
}
function assetsHtml() {
  if (assetsErr) return `<p class="problems">${E(assetsErr)}</p>`;
  if (!assetsData) return '<p class="soft">Reading the live aircraft and ships…</p>';
  const A = assetsData.assets || [], comps = Object.values(assetsData.companies || {});
  const air = A.filter(a => a.kind === 'aircraft'), ships = A.filter(a => a.kind === 'ship');
  const owned = air.filter(a => a.link.how === 'owner').length, flightOnly = air.length - owned;
  const outside = air.filter(a => a.owner?.outside).length, notYet = air.filter(a => a.register === 'not looked up yet').length;
  const rows = comps.filter(c => c.owns || c.flies || c.ships).sort((a, b) => (b.owns + b.flies + b.ships) - (a.owns + a.flies + a.ships));
  const flagged = comps.filter(c => c.flags?.length && (c.owns || c.flies || c.ships));
  let h = `<div class="sec cx-assets"><h3>Their aircraft and ships now <span class="n-count">${A.length}</span></h3>
    <div class="cx-steps">
      <div><b>${air.length}</b><span>aircraft: ${owned} registered to a company here (solid line), ${flightOnly} by flight number only (dashed)${outside ? `, of which ${outside} registered to someone outside` : ''}${notYet ? `, ${notYet} not looked up yet` : ''}</span></div>
      <div><b>${ships.length}</b><span>ships Wikidata names a company here as owner (solid) or operator (dashed), found by IMO number</span></div></div>
    ${notYet ? `<p class="soft">Looking up ${assetsData.pending} more register entries, one a second; this list fills in by itself.</p>` : ''}
    ${rows.length ? `<table class="cx-table"><thead><tr><th>Company</th><th>Owns</th><th>Flies</th><th>Ships</th></tr></thead><tbody>${rows.map(c =>
      `<tr data-cx-company="${E(c.ref)}"><td>${E(c.name)}${c.via ? `<small>under ${E(c.via)}</small>` : ''}${c.flags?.length ? ' <span class="cx-flag" title="' + E(c.flags.join('; ')) + '">flagged</span>' : ''}</td><td>${c.owns || '–'}</td><td>${c.flies || '–'}</td><td>${c.ships || '–'}</td></tr>`).join('')}</tbody></table>` : '<p class="soft">None of these companies has an aircraft or ship in our feeds right now.</p>'}
    ${flagged.length ? `<div class="cx-flags"><h4>Where the registers disagree</h4>${flagged.map(c => `<p><b>${E(c.name)}</b>: ${E(c.flags.join('; '))}.</p>`).join('')}</div>` : ''}
    ${A.length ? `<ul class="rows cx-alist">${A.slice(0, 120).map(a => `<li data-cx-asset="${E(a.kind + ':' + a.id)}"><span class="t">${E(a.label)}</span><span class="faint">${a.kind === 'ship' ? 'ship' : E(a.type || 'aircraft')}</span>
      <span class="m">${E(a.link.how === 'owner' ? '' : a.link.how === 'flight' ? 'flight number only · ' : 'operator · ')}${E(nameOf(a.link.ref))}${a.owner?.outside ? ' · registered to ' + E(a.owner.name) : ''} · ${E(ago(a.time))}</span></li>`).join('')}</ul>
      ${A.length > 120 ? `<p class="soft">${A.length - 120} more on the map.</p>` : ''}` : ''}
    <p class="note">Positions: ${Object.entries(assetsData.feeds || {}).map(([k, t]) => `${E(k)} ${E(hhmm(t))}`).join(' · ') || 'no feed has answered yet'}. ${assetsData.aircraft_seen?.toLocaleString('en-GB') || 0} aircraft and ${assetsData.ships_seen?.toLocaleString('en-GB') || 0} ships with an IMO number checked. Registered owners: the free registers behind adsbdb and hexdb.io. Never matched on similar names, paint or routes.</p>
    ${assetsData.problems?.length ? `<p class="problems">${assetsData.problems.map(E).join('<br>')}</p>` : ''}</div>`;
  return h;
}
function placeHtml(rs) {
  const p = placeOf(rs[0]);
  return `<button class="btn cx-back" data-cx-back>← The map list</button><div class="kind">Place</div><h2>${E(p?.place || '')}</h2>
    <ul class="rows">${rs.map(r => `<li data-cx-company="${E(r)}"><span class="t">${E(nameOf(r))}</span><span class="m">${E(placeOf(r)?.how || '')} · ${E(placeOf(r)?.source || '')}</span></li>`).join('')}</ul>`;
}
function assetHtml(a) {
  const c = assetsData.companies[a.link.ref] || {}, fc = a.flight_ref && a.flight_ref !== a.link.ref ? assetsData.companies[a.flight_ref] : null;
  const ship = a.kind === 'ship';
  const facts = ship
    ? [['IMO', a.imo], ['Kind (AIS)', a.ship_kind], ['Speed', a.speed_kn != null ? `${a.speed_kn} kn` : null], ['Course', a.course != null ? `${Math.round(a.course)}°` : null], ['Position', `${ago(a.time)} · ${a.src}`]]
    : [['Aircraft', a.model || a.type], ['Registration', a.reg], ['Altitude', a.ground ? 'on the ground' : a.alt_ft != null ? `${Math.round(a.alt_ft).toLocaleString('en-GB')} ft` : null],
       ['Speed', a.gs_kt != null ? `${Math.round(a.gs_kt)} kt` : null], ['Position', `${ago(a.time)} · ${a.src}`]];
  const links = [];
  if (a.link.how === 'owner') links.push(['solid', a.link.words]);
  else links.push(['dashed', a.link.words + (a.owner?.outside ? `; registered to ${a.owner.name} (${a.owner.src}${a.owner.code ? ', code ' + a.owner.code : ''}), which is not in this structure`
    : a.register === 'not looked up yet' ? '; its register entry is being looked up' : !ship ? '; the free registers name no owner' : '')]);
  if (fc) links.push(['dashed', `flies under ${fc.name}${/s$/.test(fc.name) ? "'" : "'s"} code`]);
  return `<button class="btn cx-back" data-cx-back>← The map list</button><div class="kind">${ship ? 'Ship' : 'Aircraft'}</div><h2>${E(a.label)}</h2>
    <dl class="facts">${facts.filter(f => f[1]).map(f => `<dt>${E(f[0])}</dt><dd>${E(f[1])}</dd>`).join('')}</dl>
    <div class="sec"><h3>Why it is here</h3>${links.map(([k, w]) => `<div class="cx-link"><i class="${k}"></i><span>${E(w)}</span></div>`).join('')}</div>
    ${c.flags?.length ? `<div class="sec cx-flags"><h4>Flagged</h4>${c.flags.map(f => `<p>${E(f)}.</p>`).join('')}</div>` : ''}
    <div class="sec"><button class="btn" data-cx-company="${E(a.link.ref)}">${E(c.name || nameOf(a.link.ref))}</button>${a.wd ? ` <a class="btn" href="https://www.wikidata.org/wiki/${E(a.wd)}" target="_blank" rel="noopener">Ship in Wikidata</a>` : ''}</div>`;
}
function legend() {
  const c = col();
  return `<h4>On the map</h4><div><span class="cx-dot"></span>headquarters or registered address; number = companies there</div>
    <h4 style="margin-top:8px">Who owns whom</h4><div style="color:${c.GLEIF}"><i></i>GLEIF</div><div style="color:${c.Wikidata}"><i></i>Wikidata</div><div style="color:${c.Offshore}"><i></i>Offshore Leaks</div>
    <div><i class="dash"></i>ultimate parent, or same name only</div>
    ${assetsOn ? `<h4 style="margin-top:8px">Their aircraft and ships</h4><div><i></i>registered owner (Wikidata owner for ships)</div><div><i class="dash"></i>flight number only (Wikidata operator)</div>` : ''}`;
}

// clicks inside the panel that belong to the map view
document.getElementById('panel').addEventListener('click', e => {
  if (!shown) return;
  if (e.target.id === 'cx-assets-sw') return setAssets(e.target.checked);
  const b = e.target.closest('[data-cx-back]'); if (b) { sel = null; ring(); ctx.setPanel(listHtml()); return; }
  const a = e.target.closest('[data-cx-asset]');
  if (a) { const x = (assetsData?.assets || []).find(y => y.kind + ':' + y.id === a.dataset.cxAsset); if (x) { map.easeTo({center: [x.lon, x.lat], zoom: Math.max(map.getZoom(), 5), duration: 500}); showAsset(a.dataset.cxAsset); } return; }
  const co = e.target.closest('[data-cx-company]');
  if (co) { const p = placeOf(co.dataset.cxCompany); if (p) map.easeTo({center: [p.lon, p.lat], zoom: Math.max(map.getZoom(), 4), duration: 500}); company(co.dataset.cxCompany); }
});
export const backButton = () => '<button class="btn cx-back" data-cx-back>← The map list</button>';
