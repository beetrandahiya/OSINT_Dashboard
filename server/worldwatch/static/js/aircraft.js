// Aircraft from three feeds:
//   near      adsb.fi, 100 nautical miles around Munich, every 10 s
//   military  adsb.lol, worldwide, every 5 min
//   world     OpenSky, every 15 min (the free allowance)
// Every aircraft is drawn where its feed last reported it. Nothing is moved forward between reports,
// so the world view can be up to 15 minutes behind and the card says how old a position is.
import {$, ago, api, esc, local} from './util.js';

let near = [], mil = [], world = [], info = {}, theMap = null, isDark = false;

// ---- icons, drawn here so no image files or icon fonts are needed (pointing north) ----
const PLANE = 'M32 3c2.6 0 3.8 5 3.8 10.5V25l22.7 14.2v5.3L35.8 37.6v14.2l6.7 5.4v4L32 58.2 21.5 61.2v-4l6.7-5.4V37.6L5.5 44.5v-5.3L28.2 25V13.5C28.200 8 29.4 3 32 3z';
const HELI = 'M32 14c4.200 0 7 3.600 7 9v9.500l2 13.500h7v4H16v-4h7l2-13.500V23c0-5.400 2.800-9 7-9zM30.500 46h3v12h-3zM4 20.500h56v3.500H4z';
function icon(path, fill, edge, px) {
  const c = document.createElement('canvas'); c.width = c.height = px;
  const x = c.getContext('2d'), p = new Path2D(path);
  x.scale(px / 64, px / 64);
  x.lineJoin = 'round'; x.lineWidth = 5; x.strokeStyle = edge; x.stroke(p);
  x.fillStyle = fill; x.fill(p);
  return x.getImageData(0, 0, px, px);
}
function icons(map, dark) {
  const edge = dark ? '#1c1c1e' : '#ffffff';
  const set = {'ww-plane': [PLANE, civil.color[+dark]], 'ww-heli': [HELI, civil.color[+dark]],
               'ww-plane-mil': [PLANE, military.color[+dark]], 'ww-heli-mil': [HELI, military.color[+dark]],
               'ww-plane-far': [PLANE, dark ? '#7c7c80' : '#8e8e93']};
  for (const [name, [path, fill]] of Object.entries(set)) {
    const img = icon(path, fill, edge, 64);
    if (map.hasImage(name)) map.updateImage(name, img); else map.addImage(name, img, {pixelRatio: 2});
  }
}

const heli = a => a.category === 'A7';
const feature = (a, kind) => ({type: 'Feature', geometry: {type: 'Point', coordinates: [a.lon, a.lat]},
  properties: {id: a.hex, track: a.track ?? 0, label: a.flight || a.reg || '', icon: (heli(a) ? 'ww-heli' : 'ww-plane') + (kind === 'mil' ? '-mil' : '')}});
const empty = {type: 'FeatureCollection', features: []};

function symbol(id, source, size, extra = {}) {
  return {id, type: 'symbol', source, layout: {'icon-image': ['get', 'icon'], 'icon-size': size, 'icon-rotate': ['get', 'track'],
    'icon-rotation-alignment': 'map', 'icon-allow-overlap': true, 'icon-ignore-placement': true, ...extra}};
}
const label = {'text-field': ['step', ['zoom'], '', 6.5, ['get', 'label']], 'text-font': ['Noto Sans Bold'], 'text-size': 10.5,
  'text-offset': [0, 1.5], 'text-anchor': 'top', 'text-optional': true, 'text-allow-overlap': false};

function find(id) {
  const n = near.find(a => a.hex === id); if (n) return {a: n, from: 'near'};
  const m = mil.find(a => a.hex === id); if (m) return {a: m, from: 'military'};
  const w = world.find(a => a.hex === id); if (w) return {a: w, from: 'world'};
  return null;
}

const ft = v => v == null ? 'not reported' : v === 'ground' ? 'on the ground' : `${Number(v).toLocaleString('en-GB')} ft <span class="soft">(${(v * 0.3048 / 1000).toFixed(1)} km)</span>`;
const kt = v => v == null ? 'not reported' : `${Math.round(v)} kt <span class="soft">(${Math.round(v * 1.852)} km/h)</span>`;
const SOURCES = {near: ['adsb.fi', 'aircraft_near'], military: ['adsb.lol', 'aircraft_military'], world: ['OpenSky Network', 'aircraft_world']};

function detail(id) {
  const hit = find(id);
  if (!hit) return null;
  const {a, from} = hit, f = info[SOURCES[from][1]];
  const isMil = from === 'military' || a.military;
  let rows;
  if (from === 'world') {   // OpenSky reports metric units and fewer fields
    rows = `<dt>Altitude</dt><dd>${a.on_ground ? 'on the ground' : a.alt_m == null ? 'not reported' : ft(Math.round(a.alt_m / 0.3048 / 25) * 25)}</dd>
      <dt>Ground speed</dt><dd>${a.gs_ms == null ? 'not reported' : kt(a.gs_ms / 0.514444)}</dd>
      <dt>Heading</dt><dd>${a.track == null ? 'not reported' : Math.round(a.track) + '°'}</dd>
      <dt>Position reported</dt><dd>${local(a.last_contact)} <span class="soft">(${ago(a.last_contact)})</span></dd>`;
  } else {
    const at = f.data_time - (a.seen_pos_s ?? 0);
    rows = `<dt>Type</dt><dd>${esc(a.type || 'not reported')}${a.reg ? ` <span class="soft">· ${esc(a.reg)}</span>` : ''}</dd>
      <dt>Altitude</dt><dd>${ft(a.alt_ft)}</dd>
      <dt>Ground speed</dt><dd>${kt(a.gs_kt)}</dd>
      <dt>Heading</dt><dd>${a.track == null ? 'not reported' : Math.round(a.track) + '°'}</dd>
      ${a.squawk ? `<dt>Transponder code</dt><dd>${esc(a.squawk)}${{7500: ' (hijack)', 7600: ' (radio failure)', 7700: ' (emergency)'}[a.squawk] || ''}</dd>` : ''}
      <dt>Position reported</dt><dd>${local(at)} <span class="soft">(${ago(at)})</span></dd>`;
  }
  const flags = [isMil && 'Military', a.ladd && 'On the FAA\'s limited-display list', a.pia && 'Privacy address'].filter(Boolean).join(' · ');
  return `<p class="eyebrow">${isMil ? 'Military aircraft' : heli(a) ? 'Helicopter' : 'Aircraft'}</p>
    <h2>${esc(a.flight || a.reg || a.hex.toUpperCase())}</h2>
    <p class="where" id="route" data-callsign="${esc(a.flight || '')}">${a.flight ? 'Looking up the route' : 'No callsign reported'}</p>
    <dl>${rows}<dt>Transponder address</dt><dd>${esc(a.hex.toUpperCase())}</dd></dl>
    ${flags ? `<p class="source">${flags}.</p>` : ''}
    <a class="link" href="https://globe.adsb.fi/?icao=${esc(a.hex)}" target="_blank" rel="noopener">Follow on adsb.fi</a>
    <p class="source">Source: ${SOURCES[from][0]}, fetched ${ago(f.fetched)}. The aircraft is drawn where it last reported; it has kept moving since.${from === 'world' ? ' The world view refreshes every 15 minutes.' : ''}</p>`;
}

// The route comes from a second, crowd-sourced source and is looked up only when a card is opened.
export async function fillRoute() {
  const el = $('#route'); if (!el || !el.dataset.callsign || el.dataset.done) return;
  el.dataset.done = '1';
  const cs = el.dataset.callsign;
  try {
    const r = await api('/api/route/' + encodeURIComponent(cs));
    const now = $('#route'); if (!now || now.dataset.callsign !== cs) return;
    if (!r.route) { now.textContent = 'Route not known to adsbdb'; return; }
    const p = x => `${esc(x.city || x.name)}${x.iata ? ' (' + esc(x.iata) + ')' : ''}`;
    now.innerHTML = `${p(r.route.origin)} to ${p(r.route.destination)}<span class="sub">${esc(r.route.airline || '')}${r.route.airline ? ' · ' : ''}usual route for this callsign, from adsbdb, can be wrong</span>`;
  } catch (e) { const now = $('#route'); if (now) now.textContent = 'Route lookup failed'; }
}

function render(map) {
  const fresh = new Set([...near, ...mil].map(a => a.hex));   // the fresher feeds win over the 15-minute world view
  map.getSource('ww-air-world').setData({type: 'FeatureCollection', features: world.filter(a => !fresh.has(a.hex) && !a.on_ground).map(a => (
    {type: 'Feature', geometry: {type: 'Point', coordinates: [a.lon, a.lat]}, properties: {id: a.hex, track: a.track ?? 0, icon: 'ww-plane-far'}}))});
  const milHex = new Set(mil.map(a => a.hex));
  map.getSource('ww-air-near').setData({type: 'FeatureCollection', features: near.filter(a => !milHex.has(a.hex) && !a.military).map(a => feature(a, 'civil'))});
  map.getSource('ww-air-mil').setData({type: 'FeatureCollection', features: [...mil, ...near.filter(a => a.military && !milHex.has(a.hex))].map(a => feature(a, 'mil'))});
}

export const civil = {
  id: 'aircraft', title: 'Aircraft', color: ['#5856d6', '#7d7aff'], feeds: {aircraft_near: 10, aircraft_world: 120}, layers: ['ww-air-world', 'ww-air-near'],
  addTo(map) {
    theMap = map;
    for (const s of ['ww-air-world', 'ww-air-near', 'ww-air-mil']) map.addSource(s, {type: 'geojson', data: empty});
    map.addLayer(symbol('ww-air-world', 'ww-air-world', ['interpolate', ['linear'], ['zoom'], 1, 0.22, 5, 0.42, 9, 0.6]));
    map.setPaintProperty('ww-air-world', 'icon-opacity', ['interpolate', ['linear'], ['zoom'], 1, 0.55, 5, 0.9]);
    map.addLayer(symbol('ww-air-near', 'ww-air-near', ['interpolate', ['linear'], ['zoom'], 1, 0.3, 5, 0.55, 9, 0.8], label));
  },
  paint(map, dark) {
    isDark = dark; icons(map, dark);
    for (const l of ['ww-air-near', 'ww-air-mil']) if (map.getLayer(l)) {
      map.setPaintProperty(l, 'text-color', dark ? '#e5e5ea' : '#3a3a3c');
      map.setPaintProperty(l, 'text-halo-color', dark ? '#1c1c1e' : '#ffffff');
      map.setPaintProperty(l, 'text-halo-width', 1.2);
    }
  },
  onData(feed, d) { info[feed] = d; if (feed === 'aircraft_near') near = d.payload.aircraft; else world = d.payload.aircraft; },
  render,
  count: () => new Set([...world.filter(a => !a.on_ground), ...near].map(a => a.hex)).size,
  rows: () => [],
  locate(id) { const h = find(id); return h && [h.a.lon, h.a.lat]; },
  ring: () => 15,
  detail,
  owns: id => !!find(id) && !military.owns(id),
};

export const military = {
  id: 'military', title: 'Military', color: ['#af52de', '#da8fff'], feeds: {aircraft_military: 60}, layers: ['ww-air-mil'],
  addTo(map) { map.addLayer(symbol('ww-air-mil', 'ww-air-mil', ['interpolate', ['linear'], ['zoom'], 1, 0.34, 5, 0.6, 9, 0.85], label)); },
  paint(map, dark) { civil.paint(map, dark); },
  onData(feed, d) { info[feed] = d; mil = d.payload.aircraft; },
  render,
  count: () => mil.length,
  rows: () => [],
  locate: id => civil.locate(id),
  ring: () => 16,
  detail,
  owns: id => mil.some(a => a.hex === id) || near.some(a => a.hex === id && a.military),
};
