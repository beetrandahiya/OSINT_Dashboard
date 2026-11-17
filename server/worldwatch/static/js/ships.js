// Ships: Finland's open feed (northern Baltic, no key) plus aisstream.io worldwide once its free key is set.
// A ship is drawn where it last reported; nothing is moved forward.
import {ago, esc, local} from './util.js';
import {shipFlag, flagImg} from './flags.js';

const HULL = 'M32 4c7 9 10 17 10 26v24c0 3-2 5-5 5H27c-3 0-5-2-5-5V30c0-9 3-17 10-26z';
const RING_KM = {region: 400, port: 10};   // how far "in the Arabian Sea" or "in port at Sasebo" can mean, drawn to scale
const STATUS = {0: 'Under way', 1: 'At anchor', 2: 'Not under command', 3: 'Restricted in manoeuvring', 4: 'Constrained by draught', 5: 'Moored', 6: 'Aground', 7: 'Fishing', 8: 'Under sail'};
let list = [], info = null;
// a ship at anchor, moored, aground, or making under half a knot: the card offers no chase camera for it
export const still = s => s.status === 1 || s.status === 5 || s.status === 6 || (knots(s.speed_kn) != null && s.speed_kn < 0.5);
const knots = v => v == null || v >= 102.25 ? null : v;   // AIS 102.3 = "not available" (payloads stored before the server filtered it)

function icon(fill, edge) {
  const c = document.createElement('canvas'); c.width = c.height = 64;
  const x = c.getContext('2d'), p = new Path2D(HULL);
  x.lineJoin = 'round'; x.lineWidth = 5; x.strokeStyle = edge; x.stroke(p); x.fillStyle = fill; x.fill(p);
  return x.getImageData(0, 0, 64, 64);
}

const pics = new Map();
// ---- the selected ship's path: the positions the worldwide stream heard from it (server memory, up to 30 points) ----
let trailMap = null, trailFor = {ships: null, warships: null}, trailPts = [];
async function loadTrail() {
  const id = trailFor.ships || trailFor.warships;
  const m = id && String(id).match(/^ship:(\d+)$/);
  if (!m) { trailPts = []; drawTrail(); return; }
  try { const r = await fetch('/api/ship/trail/' + m[1]).then(x => x.json()); if ((trailFor.ships || trailFor.warships) === id) { trailPts = r.points || []; drawTrail(); } } catch (e) { /* keep */ }
}
function drawTrail() {
  if (!trailMap?.getSource('ww-ship-trail')) return;
  const id = trailFor.ships || trailFor.warships, s = list.find(x => 'ship:' + x.mmsi === id);
  const pts = trailPts.map(p => [p[0], p[1]]);
  if (s && pts.length) pts.push([s.lon, s.lat]);
  trailMap.getSource('ww-ship-trail').setData({type: 'FeatureCollection', features: pts.length > 1 ? [{type: 'Feature', geometry: {type: 'LineString', coordinates: pts}, properties: {}}] : []});
}
setInterval(() => { if (trailFor.ships || trailFor.warships) loadTrail(); }, 60000);
export async function fillShip() {
  const box = document.getElementById('shippic'); if (!box || box.dataset.done) return;
  box.dataset.done = '1';
  const q = new URLSearchParams({mmsi: box.dataset.mmsi, imo: box.dataset.imo, name: box.dataset.name, mil: box.dataset.mil}).toString();
  let r = pics.get(q);
  if (!r) { try { r = await fetch('/api/ship/about?' + q).then(x => x.json()); pics.set(q, r); } catch (e) { box.dataset.done = ''; return; } }
  const top = document.getElementById('shippic'), about = document.getElementById('shipabout');
  if (!top || top.dataset.mmsi !== box.dataset.mmsi) return;
  // the photo sites (ShipSpotting, MarineTraffic, VesselFinder) hold photographers' pictures and forbid automated copying,
  // so the card links to the same searches a person would do
  const nm = box.dataset.name, imo = box.dataset.imo;
  const sq = encodeURIComponent(imo ? `"${nm}" IMO ${imo}` : `"${nm}" ship`);
  const more = `<p class="links"><a class="link" href="https://www.google.com/search?tbm=isch&q=${sq}" target="_blank" rel="noopener">Search photos of it</a>
    ${imo ? `<a class="link" href="https://www.shipspotting.com/photos/gallery?imo=${encodeURIComponent(imo)}" target="_blank" rel="noopener">ShipSpotting photos (IMO ${esc(imo)})</a>` : ''}</p>`;
  if (!r.image) {
    top.innerHTML = `<p class="pic-wait">No free picture on Wikimedia; looking on VesselFinder…</p>`;
    let w = null;
    try { w = await fetch(`/api/ship/photos?name=${encodeURIComponent(nm)}&imo=${encodeURIComponent(imo || '')}`).then(x => x.json()); } catch (e) { /* links below */ }
    const now2 = document.getElementById('shippic'); if (!now2 || now2.dataset.mmsi !== box.dataset.mmsi) return;
    if (w?.photos?.length) {
      const ph = w.photos[0];
      now2.innerHTML = `<div class="photo"><a href="${esc(ph.page)}" target="_blank" rel="noopener" title="${esc(ph.title || '')}"><img src="${esc(ph.thumb)}" alt="Photo of this ship" loading="lazy" onerror="this.closest('.photo').outerHTML='<p class=pic-wait>The photo could not be loaded.</p>'"></a><span>Photo: VesselFinder (found by Brave Search; the picture belongs to its photographer, links to VesselFinder's page)</span></div>${more}`;
    } else {
      now2.innerHTML = `<p class="pic-wait">${w?.error && !/not set up/.test(w.error) ? esc(w.error) + '. ' : ''}No free picture of this ship on Wikimedia${w?.photos ? ' and none found on VesselFinder' : ''}.</p>${more}`;
    }
  }
  if (r.image) top.innerHTML = `<div class="photo"><a href="${esc(r.commons || 'https://www.wikidata.org/wiki/' + r.qid)}" target="_blank" rel="noopener"><img src="${esc(r.image.replace('http://', 'https://'))}${r.commons ? '' : '?width=640'}" alt="Picture of this ship" loading="lazy" onerror="this.closest('.photo').outerHTML='<p class=pic-wait>The picture could not be loaded.</p>'"></a><span>Picture: Wikimedia Commons${r.commons ? ', filed under its IMO number' : ', via Wikidata'}${r.by === 'name' ? ' (matched by name; check it is this ship)' : ''}</span></div>${more}`;
  if (about) { about.dataset.done = '1'; about.innerHTML = r.qid ? `<section class="pz"><h3>${esc(r.name || 'On Wikidata')}</h3>${r.description ? `<p>${esc(r.description[0].toUpperCase() + r.description.slice(1))}.</p>` : ''}<dl>${r.kinds?.length ? `<dt>Kind</dt><dd>${r.kinds.map(esc).join(', ')}</dd>` : ''}${r.operator ? `<dt>Operator</dt><dd>${esc(r.operator)}</dd>` : ''}${r.country ? `<dt>Flag</dt><dd>${esc(r.country)}</dd>` : ''}${r.built ? `<dt>In service since</dt><dd>${esc(r.built)}</dd>` : ''}</dl>${r.wikipedia ? `<a class="link" href="${esc(r.wikipedia)}" target="_blank" rel="noopener">Wikipedia</a>` : ''}<p class="source">Wikidata, matched by ${r.by === 'imo' ? 'IMO number' : r.by === 'mmsi' ? 'MMSI' : 'name, so it may be another ship of the same name'}.</p></section>` : r.commons ? '' : `<p class="source">Looked on Wikidata (by IMO number, MMSI${box.dataset.mil ? ' and name' : ''}) and on Wikimedia Commons (by IMO number); many ships, and most warships, have neither.</p>`; }
}

const shipsLayer = {
  id: 'ships', title: 'Ships', color: ['#a2845e', '#c4a57b'], feeds: {ships: 60}, layers: ['ww-ships'],
  addTo(map) {
    map.addSource('ww-ship-trail', {type: 'geojson', data: {type: 'FeatureCollection', features: []}});
    map.addLayer({id: 'ww-ship-trail', type: 'line', source: 'ww-ship-trail', layout: {'line-cap': 'round', 'line-join': 'round'}, paint: {'line-width': 2.5, 'line-opacity': 0.85}});
    trailMap = map;
    map.addSource('ww-ships', {type: 'geojson', data: {type: 'FeatureCollection', features: []}});
    map.addLayer({id: 'ww-ships', type: 'symbol', source: 'ww-ships', layout: {'icon-image': 'ww-ship', 'icon-rotate': ['get', 'dir'], 'icon-rotation-alignment': 'map',
      'icon-size': ['interpolate', ['linear'], ['zoom'], 1, 0.16, 5, 0.3, 9, 0.5, 13, 0.75], 'icon-allow-overlap': true, 'icon-ignore-placement': true,
      'text-field': ['step', ['zoom'], '', 8.5, ['get', 'label']], 'text-font': ['Noto Sans Bold'], 'text-size': 10.5, 'text-offset': [0, 1.4], 'text-anchor': 'top', 'text-optional': true}});
  },
  paint(map, dark) {
    const img = icon(this.color[+dark], dark ? '#1c1c1e' : '#ffffff');
    if (map.hasImage('ww-ship')) map.updateImage('ww-ship', img); else map.addImage('ww-ship', img, {pixelRatio: 2});
    map.setPaintProperty('ww-ship-trail', 'line-color', this.color[+dark]);
    map.setPaintProperty('ww-ships', 'text-color', dark ? '#e5e5ea' : '#3a3a3c'); map.setPaintProperty('ww-ships', 'text-halo-color', dark ? '#1c1c1e' : '#ffffff'); map.setPaintProperty('ww-ships', 'text-halo-width', 1.3);
  },
  onData(feed, d) { list = d.payload.ships; info = d; },
  render(map) {
    map.getSource('ww-ships').setData({type: 'FeatureCollection', features: list.map(s => ({type: 'Feature', geometry: {type: 'Point', coordinates: [s.lon, s.lat]},
      properties: {id: 'ship:' + s.mmsi, dir: s.heading ?? s.course ?? 0, label: s.name || '', cc: shipFlag(s.mmsi)?.cc || ''}}))});
  },
  count: () => list.length,
  rows: () => [],
  locate(id) { const s = list.find(x => 'ship:' + x.mmsi === id); return s && [s.lon, s.lat]; },
  heading(id) { const s = list.find(x => 'ship:' + x.mmsi === id); return s && !still(s) ? (s.heading ?? s.course ?? null) : undefined; },   // nothing to follow on a ship at rest
  ring: () => 13,
  owns: id => String(id).startsWith('ship:') && !list.find(x => 'ship:' + x.mmsi === id && x.kind === 'Military vessel'),
  fill: fillShip,
  select(id) { trailFor.ships = id; loadTrail(); },
  about: () => info?.payload?.world?.key ? `Ships worldwide from aisstream.io plus Finland's open feed. aisstream relays volunteer receivers on shore: dense near Europe, North America and East Asia, thin or empty in the Indian Ocean and mid-ocean (no free satellite AIS exists). A ship stays listed two hours after its last report, so the count moves as receivers come and go.` : 'Ships in the northern Baltic only, from Finland\'s open data. For the rest of the world, register a free key at aisstream.io and put it in data/aisstream-key.txt.',
  detail(id) {
    const s = list.find(x => 'ship:' + x.mmsi === id);
    if (!s) return null;
    return `<div id="shippic" data-mmsi="${s.mmsi}" data-imo="${s.imo || ''}" data-name="${esc(s.name || '')}" data-mil="${s.kind === 'Military vessel' ? 1 : ''}"><p class="pic-wait">Looking for a picture of this ship…</p></div>
      <p class="eyebrow">${esc(s.kind || 'Ship')}</p><h2>${esc(s.name || 'MMSI ' + s.mmsi)}${shipFlag(s.mmsi)?.cc ? ' ' + flagImg(shipFlag(s.mmsi).cc, shipFlag(s.mmsi).name) : ''}</h2>
      <p class="where">${s.destination ? 'Destination as entered by the crew: ' + esc(s.destination) : 'No destination entered'}</p>
      <dl>${(() => { const fl = shipFlag(s.mmsi); return fl ? `<dt>Flag</dt><dd>${flagImg(fl.cc, fl.name)} ${esc(fl.name)} <span class="soft">(from its MMSI)</span></dd>` : ''; })()}<dt>Status</dt><dd>${esc(STATUS[s.status] || 'Not stated')}</dd>
      <dt>Speed</dt><dd>${knots(s.speed_kn) == null ? 'not reported' : s.speed_kn.toFixed(1) + ' kn <span class="soft">(' + Math.round(s.speed_kn * 1.852) + ' km/h)</span>'}</dd>
      <dt>Course</dt><dd>${s.course == null ? 'not reported' : Math.round(s.course) + '°'}</dd>
      ${s.length_m ? `<dt>Length</dt><dd>${s.length_m} m</dd>` : ''}
      ${s.draught_m ? `<dt>Draught</dt><dd>${(+s.draught_m).toFixed(1)} m</dd>` : ''}
      <dt>Position reported</dt><dd>${local(s.time)} <span class="soft">(${ago(s.time)})</span></dd>
      ${s.source === 'aisstream.io' ? `<dt>Path</dt><dd>${trailPts.length > 1 ? `the line shows ${trailPts.length} positions heard since ${local(trailPts[0][2])}` : 'only one position heard so far'}</dd>` : ''}
      <dt>Identifiers</dt><dd>MMSI ${s.mmsi}${s.imo ? ' · IMO ' + s.imo : ''}${s.callsign ? ' · ' + esc(s.callsign) : ''}</dd></dl>
      <div id="shipabout"></div>
      <a class="link" href="https://www.marinetraffic.com/en/ais/details/ships/mmsi:${s.mmsi}" target="_blank" rel="noopener">Look this ship up on MarineTraffic</a>
      ${s.length_m ? '' : ''}<p class="source">Source: ${s.source === 'aisstream.io' ? 'aisstream.io (AIS relayed by volunteer receivers)' : "Digitraffic (Fintraffic, Finland's open maritime data, CC BY 4.0)"}, fetched ${ago(info.fetched)}. Ships broadcast these values themselves; name, type and destination are typed in by the crew and can be out of date. Drawn where it last reported.</p>`;
  },
};

// Warships: ships that broadcast themselves as military (AIS type 35). Many navies switch AIS off; those that leave
// it on show up here, larger and labelled at every zoom.
// US carriers and amphibious assault ships from USNI News' weekly Fleet Tracker: placed by region or port, so the
// marker sits inside a wide dashed ring (a region) or a small one (a port), never as an exact position.
let fleet = null;
const fleetShips = () => (fleet?.ships || []).filter(x => x.lat != null);
function fleetFeatures() {
  const seen = {}, out = [];
  for (const x of fleetShips()) {
    const k = x.lat + ',' + x.lon, n = seen[k] = (seen[k] || 0) + 1;     // ships in the same region are spread a little so each can be clicked
    const lon = x.lon + (n - 1) * 1.6, lat = x.lat - (n - 1) * 0.8;
    out.push({type: 'Feature', geometry: {type: 'Point', coordinates: [lon, lat]}, properties: {id: 'usni:' + x.hull, label: x.name.replace('USS ', '') + ' (' + x.hull + ')', carrier: x.hull.startsWith('CVN'),
      // ring radius in pixels at zoom 0 for a real distance (Web Mercator, 512-pixel world): it then doubles with each zoom step
      r0: (x.placed === 'port' ? RING_KM.port : RING_KM.region) * 1000 / (78271.517 * Math.cos(lat * Math.PI / 180))}});
  }
  return out;
}
document.addEventListener('click', e => {
  const b = e.target.closest('[data-sharpat]'); if (!b) return;
  const [lon, lat] = b.dataset.sharpat.split(',').map(Number);
  const chip = document.querySelector('.chip[data-id=sharp]'); if (chip && chip.getAttribute('aria-pressed') !== 'true') chip.click();
  window.dispatchEvent(new CustomEvent('ww-fly', {detail: {center: [lon, lat], zoom: 14.5}}));
});

export const warships = {
  id: 'warships', title: 'Warships', color: ['#636366', '#c7c7cc'], feeds: {ships: 60, usni_fleet: 3600}, layers: ['ww-usni-ring', 'ww-usni', 'ww-warships'],
  about: () => 'Ships broadcasting as military (AIS type 35) on the worldwide stream and Finland\'s feed. Navies often switch AIS off; what is here chose to be seen.',
  addTo(map) {
    map.addSource('ww-warships', {type: 'geojson', data: {type: 'FeatureCollection', features: []}});
    map.addSource('ww-usni', {type: 'geojson', data: {type: 'FeatureCollection', features: []}});
    map.addLayer({id: 'ww-usni-ring', type: 'circle', source: 'ww-usni', paint: {'circle-radius': ['interpolate', ['exponential', 2], ['zoom'], 0, ['get', 'r0'], 20, ['*', ['get', 'r0'], 1048576]], 'circle-opacity': 0.06, 'circle-stroke-width': 1.2, 'circle-stroke-opacity': 0.6}});
    map.addLayer({id: 'ww-usni', type: 'symbol', source: 'ww-usni', layout: {'icon-image': 'ww-warship', 'icon-size': ['case', ['==', ['get', 'carrier'], true], 0.75, 0.6], 'icon-allow-overlap': true,
      'text-field': ['get', 'label'], 'text-font': ['Noto Sans Bold'], 'text-size': 10.5, 'text-offset': [0, 1.8], 'text-anchor': 'top', 'text-optional': true}});
    map.addLayer({id: 'ww-warships', type: 'symbol', source: 'ww-warships', layout: {'icon-image': 'ww-warship', 'icon-rotate': ['get', 'dir'], 'icon-rotation-alignment': 'map',
      'icon-size': ['interpolate', ['linear'], ['zoom'], 1, 0.3, 5, 0.45, 9, 0.7], 'icon-allow-overlap': true, 'icon-ignore-placement': true,
      'text-field': ['step', ['zoom'], '', 3.5, ['get', 'label']], 'text-font': ['Noto Sans Bold'], 'text-size': 10.5, 'text-offset': [0, 1.6], 'text-anchor': 'top', 'text-optional': true}});
  },
  paint(map, dark) {
    const img = icon(dark ? '#c7c7cc' : '#48484a', dark ? '#1c1c1e' : '#ffffff');
    if (map.hasImage('ww-warship')) map.updateImage('ww-warship', img); else map.addImage('ww-warship', img, {pixelRatio: 2});
    map.setPaintProperty('ww-warships', 'text-color', dark ? '#e5e5ea' : '#1c1c1e');
    for (const p of [['ww-usni-ring', 'circle-color'], ['ww-usni-ring', 'circle-stroke-color']]) map.setPaintProperty(...p, dark ? '#c7c7cc' : '#48484a');
    map.setPaintProperty('ww-usni', 'text-color', dark ? '#e5e5ea' : '#1c1c1e'); map.setPaintProperty('ww-usni', 'text-halo-color', dark ? '#1c1c1e' : '#ffffff'); map.setPaintProperty('ww-usni', 'text-halo-width', 1.3); map.setPaintProperty('ww-warships', 'text-halo-color', dark ? '#1c1c1e' : '#ffffff'); map.setPaintProperty('ww-warships', 'text-halo-width', 1.3);
  },
  onData(feed, d) { if (feed === 'usni_fleet') fleet = {...d.payload, fetched: d.fetched}; },
  render(map) {
    map.getSource('ww-usni').setData({type: 'FeatureCollection', features: fleetFeatures()});
    map.getSource('ww-warships').setData({type: 'FeatureCollection', features: list.filter(s => s.kind === 'Military vessel').map(s => ({type: 'Feature', geometry: {type: 'Point', coordinates: [s.lon, s.lat]},
      properties: {id: 'ship:' + s.mmsi, dir: s.heading ?? s.course ?? 0, label: s.name || '', cc: shipFlag(s.mmsi)?.cc || ''}}))});
  },
  count: () => list.filter(s => s.kind === 'Military vessel').length + fleetShips().length,
  rows: () => [],
  locate(id) {
    if (String(id).startsWith('usni:')) { const f = fleetFeatures().find(x => x.properties.id === id); return f?.geometry.coordinates; }
    const s = list.find(x => 'ship:' + x.mmsi === id); return s && [s.lon, s.lat];
  },
  heading(id) { const s = list.find(x => 'ship:' + x.mmsi === id); return s && !still(s) ? (s.heading ?? s.course ?? null) : undefined; },   // nothing to follow on a ship at rest
  ring: () => 15,
  owns: id => String(id).startsWith('usni:') || !!list.find(x => 'ship:' + x.mmsi === id && x.kind === 'Military vessel'),
  fill: fillShip,
  select(id) { trailFor.warships = id; loadTrail(); },
  detail(id) {
    if (!String(id).startsWith('usni:')) return shipsLayer.detail(id);
    const x = fleetShips().find(v => 'usni:' + v.hull === id);
    if (!x) return null;
    return `<div id="shippic" data-mmsi="${esc(x.hull)}" data-imo="" data-name="${esc(x.name)}" data-mil="1"><p class="pic-wait">Looking for a picture of this ship…</p></div>
      <p class="eyebrow">US Navy ${esc(x.kind)} · USNI Fleet Tracker</p><h2>${esc(x.name)} <span class="soft">${esc(x.hull)}</span> ${flagImg('us', 'United States')}</h2>
      <p class="where">${x.placed === 'port' ? 'In port: ' + esc(x.port) : 'Somewhere in ' + esc(x.region) + ' (the marker is the middle of that region, not its position; the ring is drawn ' + RING_KM.region + ' km around it as a reminder, not as a boundary)'}</p>
      ${x.said.length ? `<section class="pz"><h3>What USNI reported</h3>${x.said.map(t => `<p>${esc(t)}</p>`).join('')}</section>` : ''}
      ${x.placed === 'port' ? `<button class="btn" data-sharpat="${x.lon},${x.lat}">Look at the port in the sharp photo</button><p class="source">The sharp photo is not live: it is from the date shown on its chip, so this ship may or may not be in it. Nobody publishes current pictures of warships for free.</p>` : ''}
      ${fleet.graphic ? `<a href="${esc(fleet.link)}" target="_blank" rel="noopener"><img class="news-hero" src="/api/news/image?u=${encodeURIComponent(fleet.graphic)}" alt="USNI's map of the fleet" onerror="this.remove()"></a>` : ''}
      <div id="shipabout"></div>
      <a class="link" href="${esc(fleet.link)}" target="_blank" rel="noopener">Read USNI's Fleet Tracker</a>
      <p class="source">Source: ${esc(fleet.title)}, published ${local(fleet.published)} (${ago(fleet.published)}). USNI compiles it weekly from Navy and public reports and gives regions, not positions; ships move hundreds of kilometres a day. Fetched ${ago(fleet.fetched)}.</p>`;
  },
};

export default shipsLayer;
