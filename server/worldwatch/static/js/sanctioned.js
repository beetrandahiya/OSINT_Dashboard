// Sanctioned and shadow-fleet ships, and sanctioned aircraft, that our feeds see right now: OpenSanctions' lists
// matched by IMO number / MMSI (ships) and registration / transponder address (aircraft). See sanctions.py.
import {eyeImages, eyeSwap, addEye} from './eyeicons.js';
import {every} from './prefs.js';
import {ago, esc, spyPass} from './util.js';
import {flagImg, shipFlag, planeFlag} from './flags.js';
import {fillShip, still} from './ships.js';
import {liveAt} from './aircraft.js';

let d = {ships: [], aircraft: []}, maps = [];
const all = () => [...d.ships, ...d.aircraft];
const at = x => (x.kind !== 'ship' && x.hex && liveAt(x.hex)) || [x.lon, x.lat];   // an aircraft sits where the aircraft feeds draw it now
async function load() {
  try { d = await fetch('/api/sanctioned/live', {cache: 'no-store'}).then(r => r.json()); } catch (e) { return; }
  for (const [l, m] of maps) l.render(m);
}

export default {
  id: 'sanctioned', title: 'Sanctioned ships & aircraft', color: ['#d70015', '#ff453a'], feeds: {}, local: true,
  layers: ['ww-sanc-ring', 'ww-sanc-k', 'ww-sanc-eye'],
  about: () => 'Ships and aircraft on sanctions or shadow-fleet lists (OpenSanctions) that our feeds see right now.',
  addTo(map) {
    map.addSource('ww-sanc', {type: 'geojson', data: {type: 'FeatureCollection', features: []}});
    map.addLayer({id: 'ww-sanc-ring', type: 'circle', source: 'ww-sanc', paint: {'circle-radius': 9, 'circle-opacity': 0.85, 'circle-stroke-width': 2}});
    map.addLayer({id: 'ww-sanc-k', type: 'symbol', source: 'ww-sanc',
      layout: {'text-field': ['get', 'k'], 'text-font': ['Noto Sans Bold'], 'text-size': 10, 'text-allow-overlap': true, 'text-ignore-placement': true}, paint: {'text-color': '#ffffff'}});
    maps.push([this, map]);
    if (maps.length === 1) {
      load(); every(60, load);
      setInterval(() => { if (d.aircraft.length && !document.hidden && map.getLayoutProperty('ww-sanc-ring', 'visibility') !== 'none') this.render(map); }, 2000);
    }
  },
  paint(map, dark) {
    map.setPaintProperty('ww-sanc-ring', 'circle-color', this.color[+dark]);
    map.setPaintProperty('ww-sanc-ring', 'circle-stroke-color', dark ? '#1c1c1e' : '#ffffff');
    if (!map.getLayer('ww-sanc-eye')) addEye(map, 'ww-sanc-eye', 'ww-sanc', ['match', ['get', 'k'], 'S', 'eye-sanctioned', 'eye-mil_generic'], 0.6);
    eyeImages(map, dark); eyeSwap(map, ['ww-sanc-eye'], ['ww-sanc-ring', 'ww-sanc-k']);
  },
  onData() {},
  render(map) {
    map.getSource('ww-sanc')?.setData({type: 'FeatureCollection', features: all().map(x => ({type: 'Feature', geometry: {type: 'Point', coordinates: at(x)},
      properties: {id: x.id, k: x.kind === 'ship' ? 'S' : 'A'}}))});
  },
  count: () => all().length,
  rows: () => all().map(x => ({id: x.id, time: x.time || 0, badge: x.kind === 'ship' ? 'S' : 'A', strong: true,
    title: `${x.name}${x.kind === 'ship' ? (x.ship_kind ? ' · ' + x.ship_kind : '') : (x.type ? ' · ' + x.type : '')}`,
    meta: x.kind === 'ship' ? `${(x.risk || []).join(', ')} · matched by ${x.matched_by}` : `sanctioned aircraft · matched by ${x.matched_by}`})),
  owns: id => /^s(ship|plane):/.test(String(id)),
  moving: true,
  locate(id) { const x = all().find(v => v.id === id); return x && at(x); },
  heading(id) {   // undefined (no chase camera) for a ship at rest or an aircraft on the ground
    const x = all().find(v => v.id === id);
    if (!x || (x.kind === 'ship' ? still(x) : x.alt_ft === 'ground')) return undefined;
    return x.heading ?? x.course ?? x.track ?? null;
  },
  ring: () => 13,
  fill(id) { if (String(id).startsWith('sship:')) fillShip(); },   // aircraft photos are filled by main.js for every card
  detail(id) {
    const x = all().find(v => v.id === id); if (!x) return null;
    const src = `<p class="source">Lists: OpenSanctions bulk data (non-commercial use), read ${ago(d.lists_read)}. Position: our ${x.kind === 'ship' ? 'ship feeds (aisstream.io, Digitraffic)' : 'aircraft feeds'}, ${ago(x.time)}. A match means this ${x.kind === 'ship' ? 'IMO / MMSI number' : 'registration / transponder address'} is on the list; ships change names and flags, so the listed name can differ.</p>`;
    if (x.kind === 'ship') {
      const fl = shipFlag(x.mmsi);
      return `<div id="shippic" data-mmsi="${x.mmsi}" data-imo="${esc(x.imo || '')}" data-name="${esc(x.name || '')}" data-mil=""><p class="pic-wait">Looking for a picture of this ship…</p></div>
        <p class="eyebrow">Ship on a sanctions list</p><h2>${esc(x.name)}${fl ? ' ' + flagImg(fl.cc, fl.name) : ''}</h2>
        <p class="where">${esc(x.ship_kind || 'Ship')}${x.speed_kn != null && x.speed_kn < 102.25 ? ` · ${x.speed_kn} kn` : ''}${x.destination ? ' · bound for ' + esc(x.destination) : ''}</p>
        <dl><dt>Listed as</dt><dd>${esc(x.listed_as)}${x.flag_listed ? ` <span class="soft">(flag on the list: ${esc(x.flag_listed)})</span>` : ''}</dd>
          <dt>Why</dt><dd>${(x.risk || []).map(esc).join('; ')}</dd>
          <dt>Matched by</dt><dd>${esc(x.matched_by)} ${esc(x.matched_by === 'IMO' ? x.imo : String(x.mmsi))}</dd>
          ${fl ? `<dt>Flying the flag of</dt><dd>${flagImg(fl.cc, fl.name)} ${esc(fl.name)} <span class="soft">(from its MMSI)</span></dd>` : ''}</dl>
        <section class="pz"><h3>On these lists</h3><ul class="dos-list">${(x.lists || []).map(l => `<li>${esc(l.title)}${l.publisher || l.country ? ` <span class="soft">· ${esc([l.publisher, l.country].filter(Boolean).join(', '))}</span>` : ''}</li>`).join('')}</ul></section>
        <a class="link" href="${esc(x.url)}" target="_blank" rel="noopener">OpenSanctions entry</a>
        ${spyPass(x.lat, x.lon)}${src}`;
    }
    const fl = planeFlag(x.hex);
    return `<div class="photo" id="photo" data-hex="${esc(x.hex)}"><p class="pic-wait">Looking for a photo…</p></div>
      <p class="eyebrow">Aircraft on a sanctions list</p><h2>${esc(x.name)}${fl ? ' ' + flagImg(fl.cc, fl.name) : ''}</h2>
      <p class="where">${esc(x.type || 'Aircraft')}${typeof x.alt_ft === 'number' ? ' · ' + x.alt_ft.toLocaleString('en-GB') + ' ft' : x.alt_ft === 'ground' ? ' · on the ground' : ''}</p>
      <dl><dt>Listed as</dt><dd>${esc(x.listed_as)}</dd><dt>Matched by</dt><dd>${esc(x.matched_by)}</dd>
        ${x.sanctions ? `<dt>Programme</dt><dd>${esc(x.sanctions)}</dd>` : ''}</dl>
      <section class="pz"><h3>On these lists</h3><ul class="dos-list">${(x.lists || []).map(l => `<li>${esc(l)}</li>`).join('')}</ul></section>
      <a class="link" href="${esc(x.url)}" target="_blank" rel="noopener">OpenSanctions entry</a>${src}`;
  },
};
