// Military aircraft flying orbits (surveillance, airborne warning, drones, tankers on their tracks) and tankers in
// the air. Worked out on our server from the positions it received (patterns.py); derived, and said so.
import {every} from './prefs.js';
import {ago, esc, spyPass} from './util.js';
import {planeFlag, flagImg} from './flags.js';
import {liveAt} from './aircraft.js';
const flagOf = a => { const f = planeFlag(a.hex); return f ? ' ' + flagImg(f.cc, f.name) : ''; };

let data = {orbits: [], tankers: [], now: 0, fetched: null}, maps = [];
const dur = s => { const m = Math.round(s / 60); return m < 60 ? `${m} min` : `${Math.floor(m / 60)} h ${String(m % 60).padStart(2, '0')}`; };
const name = a => a.flight || a.reg || a.hex;
const alt = a => typeof a.alt_ft === 'number' ? a.alt_ft.toLocaleString('en-GB') + ' ft' : '—';

async function load() {
  try { data = await fetch('/api/aircraft/patterns', {cache: 'no-store'}).then(r => r.json()); } catch (e) { return; }
  for (const [layer, map] of maps) layer.render(map);
}
let started = false;
function start(layer, map) {
  maps.push([layer, map]);
  if (!started) {
    started = true; load(); every(120, load);
    // the tanker markers follow the aircraft as the aircraft feeds move it (the list itself is a 2-minute snapshot)
    setInterval(() => { for (const [l, m] of maps) if (l === tankers && data.tankers.length && !document.hidden && m.getLayoutProperty('ww-tanker', 'visibility') !== 'none') l.render(m); }, 2000);
  }
}

const SOURCE = `Worked out by this server from military positions published by adsb.fi (every 30 seconds) and kept for 3 hours.`;

export const orbits = {
  id: 'orbits', title: 'Orbits (military)', color: ['#8944ab', '#da8fff'], feeds: {}, local: true,
  layers: ['ww-orbit-path', 'ww-orbit-ring', 'ww-orbit-label'],
  about: () => 'Military aircraft circling or flying racetracks: surveillance, airborne warning, drones, tankers.',
  addTo(map) {
    map.addSource('ww-orbits', {type: 'geojson', data: {type: 'FeatureCollection', features: []}});
    map.addLayer({id: 'ww-orbit-path', type: 'line', source: 'ww-orbits', filter: ['==', ['geometry-type'], 'LineString'], paint: {'line-width': 1.6, 'line-opacity': 0.8}});
    map.addLayer({id: 'ww-orbit-ring', type: 'circle', source: 'ww-orbits', filter: ['==', ['geometry-type'], 'Point'],
      paint: {'circle-radius': 9, 'circle-opacity': 0.18, 'circle-stroke-width': 2}});
    map.addLayer({id: 'ww-orbit-label', type: 'symbol', source: 'ww-orbits', filter: ['==', ['geometry-type'], 'Point'],
      layout: {'text-field': ['get', 'label'], 'text-font': ['Noto Sans Bold'], 'text-size': 11, 'text-offset': [0, 1.3], 'text-anchor': 'top', 'text-optional': true},
      paint: {'text-halo-width': 1.3}});
    start(this, map);
  },
  paint(map, dark) {
    const c = this.color[+dark];
    for (const p of ['circle-color', 'circle-stroke-color']) map.setPaintProperty('ww-orbit-ring', p, ['match', ['get', 'kind'], 'isr', dark ? '#ff6961' : '#d70015', c]);
    map.setPaintProperty('ww-orbit-path', 'line-color', ['match', ['get', 'kind'], 'isr', dark ? '#ff6961' : '#d70015', c]);
    map.setPaintProperty('ww-orbit-label', 'text-color', dark ? '#e5e5ea' : '#3a3a3c');
    map.setPaintProperty('ww-orbit-label', 'text-halo-color', dark ? '#1c1c1e' : '#ffffff');
  },
  onData() {},
  render(map) {
    const f = [];
    for (const o of data.orbits) {
      const props = {id: 'orbit:' + o.hex, kind: o.kind, label: `${name(o)} · ${dur(data.now - o.since)}`};
      f.push({type: 'Feature', geometry: {type: 'LineString', coordinates: o.path}, properties: props});
      f.push({type: 'Feature', geometry: {type: 'Point', coordinates: [o.lon, o.lat]}, properties: props});
    }
    map.getSource('ww-orbits')?.setData({type: 'FeatureCollection', features: f});
  },
  count: () => data.orbits.length,
  rows: () => data.orbits.map(o => ({id: 'orbit:' + o.hex, time: data.now, badge: '◎',
    title: `${name(o)} ${o.role ? '· ' + o.role.split(' (')[0] : '· ' + (o.type || 'military aircraft')} orbiting`,
    meta: `on station ${dur(data.now - o.since)} · ${o.turns} turns within ${Math.round(o.radius_km)} km`})),
  owns: id => String(id).startsWith('orbit:'),
  locate(id) { const o = data.orbits.find(x => 'orbit:' + x.hex === id); return o && [o.lon, o.lat]; },
  ring: () => 16,
  detail(id) {
    const o = data.orbits.find(x => 'orbit:' + x.hex === id);
    if (!o) return null;
    return `<div class="photo" id="photo" data-hex="${esc(o.hex)}"><p class="pic-wait">Looking for a photo…</p></div>
      <p class="eyebrow">Orbit · derived from positions</p><h2>${esc(name(o))}${flagOf(o)}</h2>
      <p class="where">${esc(o.role || (o.type ? 'type ' + o.type : 'military aircraft'))}${o.reg ? ' · ' + esc(o.reg) : ''}</p>
      <dl>
        <dt>Pattern</dt><dd>${o.turns} full turns in the last 2 hours, all within ${o.radius_km} km of one centre</dd>
        <dt>On station</dt><dd>${dur(data.now - o.since)} <span class="soft">(as far back as the 3 hours we keep)</span></dd>
        <dt>Now</dt><dd>${alt(o)}${o.gs_kt ? ', ' + Math.round(o.gs_kt) + ' kt' : ''}</dd>
      </dl>
      ${o.kind === 'isr' ? '<p class="soft">This type is built for surveillance, signals intelligence or airborne warning. Orbiting is how it works; what it watches is not published.</p>' : o.kind === 'tanker' ? '<p class="soft">A tanker flying a track: other aircraft refuel from it there.</p>' : '<p class="soft">The type is not one of the known surveillance or tanker types; training, holding before landing and search patterns look the same.</p>'}
      ${spyPass(o.lat, o.lon)}
      <p class="source">${SOURCE} An orbit is counted when the heading changes add up to at least one and a half turns and every position of the last 2 hours stays within 120 km of their centre. Positions 30 seconds apart. Read ${ago(data.fetched)}.</p>`;
  },
};

export const tankers = {
  id: 'tankers', title: 'Tankers up', color: ['#248a3d', '#30d158'], feeds: {}, local: true,
  layers: ['ww-tanker', 'ww-tanker-label'],
  about: () => 'Military air-to-air refuelling aircraft in the air now.',
  addTo(map) {
    map.addSource('ww-tankers', {type: 'geojson', data: {type: 'FeatureCollection', features: []}});
    map.addLayer({id: 'ww-tanker', type: 'circle', source: 'ww-tankers', paint: {'circle-radius': 7, 'circle-stroke-width': 1.5}});
    map.addLayer({id: 'ww-tanker-label', type: 'symbol', source: 'ww-tankers',
      layout: {'text-field': 'T', 'text-font': ['Noto Sans Bold'], 'text-size': 9, 'text-allow-overlap': true, 'text-ignore-placement': true}, paint: {'text-color': '#ffffff'}});
    start(this, map);
  },
  paint(map, dark) {
    map.setPaintProperty('ww-tanker', 'circle-color', this.color[+dark]);
    map.setPaintProperty('ww-tanker', 'circle-stroke-color', dark ? '#1c1c1e' : '#ffffff');
  },
  onData() {},
  render(map) {
    map.getSource('ww-tankers')?.setData({type: 'FeatureCollection', features: data.tankers.map(t => ({type: 'Feature',
      geometry: {type: 'Point', coordinates: liveAt(t.hex) || [t.lon, t.lat]}, properties: {id: 'tanker:' + t.hex}}))});
  },
  count: () => data.tankers.length,
  rows() {
    // tankers close together are the interesting signal: count the others within 500 km of each
    const near = t => data.tankers.filter(u => u !== t && Math.hypot((u.lon - t.lon) * Math.cos(t.lat * Math.PI / 180), u.lat - t.lat) * 111 < 500).length;
    return data.tankers.map(t => ({id: 'tanker:' + t.hex, time: data.now, badge: 'T', title: `${name(t)} · ${t.role.split(' (')[0]}`,
      meta: `${alt(t)}${near(t) ? ` · ${near(t)} more tankers within 500 km` : ''}`}));
  },
  owns: id => String(id).startsWith('tanker:'),
  moving: true,
  locate(id) { const t = data.tankers.find(x => 'tanker:' + x.hex === id); return t && (liveAt(t.hex) || [t.lon, t.lat]); },
  ring: () => 12,
  detail(id) {
    const t = data.tankers.find(x => 'tanker:' + x.hex === id);
    if (!t) return null;
    const o = data.orbits.find(x => x.hex === t.hex);
    const near = data.tankers.filter(u => u !== t && Math.hypot((u.lon - t.lon) * Math.cos(t.lat * Math.PI / 180), u.lat - t.lat) * 111 < 500);
    return `<div class="photo" id="photo" data-hex="${esc(t.hex)}"><p class="pic-wait">Looking for a photo…</p></div>
      <p class="eyebrow">Tanker in the air</p><h2>${esc(name(t))}${flagOf(t)}</h2><p class="where">${esc(t.role)}${t.reg ? ' · ' + esc(t.reg) : ''}</p>
      <dl><dt>Now</dt><dd>${alt(t)}${t.gs_kt ? ', ' + Math.round(t.gs_kt) + ' kt' : ''}</dd>
        <dt>Flying a track</dt><dd>${o ? `yes, ${o.turns} turns, on station ${dur(data.now - o.since)}` : 'not detected'}</dd>
        <dt>Other tankers within 500 km</dt><dd>${near.length ? near.map(u => esc(name(u))).join(', ') : 'none'}</dd></dl>
      <p class="soft">Several tankers up together over one region usually means fighters or bombers are flying far from base. Many tankers fly without broadcasting a position, so absence here means little.</p>
      <p class="source">${SOURCE} Tanker by type code; the A330 and 767 types are also government transports. Read ${ago(data.fetched)}.</p>`;
  },
};
