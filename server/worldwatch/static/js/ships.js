// Ships: Finland's open feed (northern Baltic, no key) plus aisstream.io worldwide once its free key is set.
// A ship is drawn where it last reported; nothing is moved forward.
import {ago, esc, local} from './util.js';

const HULL = 'M32 4c7 9 10 17 10 26v24c0 3-2 5-5 5H27c-3 0-5-2-5-5V30c0-9 3-17 10-26z';
const STATUS = {0: 'Under way', 1: 'At anchor', 2: 'Not under command', 3: 'Restricted in manoeuvring', 4: 'Constrained by draught', 5: 'Moored', 6: 'Aground', 7: 'Fishing', 8: 'Under sail'};
let list = [], info = null;

function icon(fill, edge) {
  const c = document.createElement('canvas'); c.width = c.height = 64;
  const x = c.getContext('2d'), p = new Path2D(HULL);
  x.lineJoin = 'round'; x.lineWidth = 5; x.strokeStyle = edge; x.stroke(p); x.fillStyle = fill; x.fill(p);
  return x.getImageData(0, 0, 64, 64);
}

const pics = new Map();
async function fillShip() {
  const box = document.getElementById('shippic'); if (!box || box.dataset.done) return;
  box.dataset.done = '1';
  const q = new URLSearchParams({mmsi: box.dataset.mmsi, imo: box.dataset.imo, name: box.dataset.name, mil: box.dataset.mil}).toString();
  let r = pics.get(q);
  if (!r) { try { r = await fetch('/api/ship/about?' + q).then(x => x.json()); pics.set(q, r); } catch (e) { box.dataset.done = ''; return; } }
  const top = document.getElementById('shippic'), about = document.getElementById('shipabout');
  if (!top || top.dataset.mmsi !== box.dataset.mmsi) return;
  if (r.image) top.innerHTML = `<div class="photo"><a href="${esc(r.commons || 'https://www.wikidata.org/wiki/' + r.qid)}" target="_blank" rel="noopener"><img src="${esc(r.image.replace('http://', 'https://'))}${r.commons ? '' : '?width=640'}" alt="Picture of this ship" loading="lazy"></a><span>Picture: Wikimedia Commons${r.commons ? ', filed under its IMO number' : ', via Wikidata'}${r.by === 'name' ? ' (matched by name; check it is this ship)' : ''}</span></div>`;
  if (about) { about.dataset.done = '1'; about.innerHTML = r.qid ? `<section class="pz"><h3>${esc(r.name || 'On Wikidata')}</h3>${r.description ? `<p>${esc(r.description[0].toUpperCase() + r.description.slice(1))}.</p>` : ''}<dl>${r.kinds?.length ? `<dt>Kind</dt><dd>${r.kinds.map(esc).join(', ')}</dd>` : ''}${r.operator ? `<dt>Operator</dt><dd>${esc(r.operator)}</dd>` : ''}${r.country ? `<dt>Flag</dt><dd>${esc(r.country)}</dd>` : ''}${r.built ? `<dt>In service since</dt><dd>${esc(r.built)}</dd>` : ''}</dl>${r.wikipedia ? `<a class="link" href="${esc(r.wikipedia)}" target="_blank" rel="noopener">Wikipedia</a>` : ''}<p class="source">Wikidata, matched by ${r.by === 'imo' ? 'IMO number' : r.by === 'mmsi' ? 'MMSI' : 'name, so it may be another ship of the same name'}.</p></section>` : r.commons ? '' : `<p class="source">No picture found: this ship is not on Wikidata or Wikimedia Commons under its IMO number${box.dataset.mil ? ' or name' : ''}.</p>`; }
}

const shipsLayer = {
  id: 'ships', title: 'Ships', color: ['#a2845e', '#c4a57b'], feeds: {ships: 60}, layers: ['ww-ships'],
  addTo(map) {
    map.addSource('ww-ships', {type: 'geojson', data: {type: 'FeatureCollection', features: []}});
    map.addLayer({id: 'ww-ships', type: 'symbol', source: 'ww-ships', layout: {'icon-image': 'ww-ship', 'icon-rotate': ['get', 'dir'], 'icon-rotation-alignment': 'map',
      'icon-size': ['interpolate', ['linear'], ['zoom'], 1, 0.16, 5, 0.3, 9, 0.5, 13, 0.75], 'icon-allow-overlap': true, 'icon-ignore-placement': true,
      'text-field': ['step', ['zoom'], '', 8.5, ['get', 'label']], 'text-font': ['Noto Sans Bold'], 'text-size': 10.5, 'text-offset': [0, 1.4], 'text-anchor': 'top', 'text-optional': true}});
  },
  paint(map, dark) {
    const img = icon(this.color[+dark], dark ? '#1c1c1e' : '#ffffff');
    if (map.hasImage('ww-ship')) map.updateImage('ww-ship', img); else map.addImage('ww-ship', img, {pixelRatio: 2});
    map.setPaintProperty('ww-ships', 'text-color', dark ? '#e5e5ea' : '#3a3a3c'); map.setPaintProperty('ww-ships', 'text-halo-color', dark ? '#1c1c1e' : '#ffffff'); map.setPaintProperty('ww-ships', 'text-halo-width', 1.3);
  },
  onData(feed, d) { list = d.payload.ships; info = d; },
  render(map) {
    map.getSource('ww-ships').setData({type: 'FeatureCollection', features: list.map(s => ({type: 'Feature', geometry: {type: 'Point', coordinates: [s.lon, s.lat]},
      properties: {id: 'ship:' + s.mmsi, dir: s.heading ?? s.course ?? 0, label: s.name || ''}}))});
  },
  count: () => list.length,
  rows: () => [],
  locate(id) { const s = list.find(x => 'ship:' + x.mmsi === id); return s && [s.lon, s.lat]; },
  ring: () => 13,
  owns: id => String(id).startsWith('ship:') && !list.find(x => 'ship:' + x.mmsi === id && x.kind === 'Military vessel'),
  fill: fillShip,
  about: () => info?.payload?.world?.key ? `Ships worldwide from aisstream.io (volunteer receivers: dense near coasts, thin mid-ocean) plus Finland's open feed.` : 'Ships in the northern Baltic only, from Finland\'s open data. For the rest of the world, register a free key at aisstream.io and put it in data/aisstream-key.txt.',
  detail(id) {
    const s = list.find(x => 'ship:' + x.mmsi === id);
    if (!s) return null;
    return `<div id="shippic" data-mmsi="${s.mmsi}" data-imo="${s.imo || ''}" data-name="${esc(s.name || '')}" data-mil="${s.kind === 'Military vessel' ? 1 : ''}"></div>
      <p class="eyebrow">${esc(s.kind || 'Ship')}</p><h2>${esc(s.name || 'MMSI ' + s.mmsi)}</h2>
      <p class="where">${s.destination ? 'Destination as entered by the crew: ' + esc(s.destination) : 'No destination entered'}</p>
      <dl><dt>Status</dt><dd>${esc(STATUS[s.status] || 'Not stated')}</dd>
      <dt>Speed</dt><dd>${s.speed_kn == null ? 'not reported' : s.speed_kn.toFixed(1) + ' kn <span class="soft">(' + Math.round(s.speed_kn * 1.852) + ' km/h)</span>'}</dd>
      <dt>Course</dt><dd>${s.course == null ? 'not reported' : Math.round(s.course) + '°'}</dd>
      ${s.length_m ? `<dt>Length</dt><dd>${s.length_m} m</dd>` : ''}
      ${s.draught_m ? `<dt>Draught</dt><dd>${(+s.draught_m).toFixed(1)} m</dd>` : ''}
      <dt>Position reported</dt><dd>${local(s.time)} <span class="soft">(${ago(s.time)})</span></dd>
      <dt>Identifiers</dt><dd>MMSI ${s.mmsi}${s.imo ? ' · IMO ' + s.imo : ''}${s.callsign ? ' · ' + esc(s.callsign) : ''}</dd></dl>
      <div id="shipabout"></div>
      <a class="link" href="https://www.marinetraffic.com/en/ais/details/ships/mmsi:${s.mmsi}" target="_blank" rel="noopener">Look this ship up on MarineTraffic</a>
      ${s.length_m ? '' : ''}<p class="source">Source: ${s.source === 'aisstream.io' ? 'aisstream.io (AIS relayed by volunteer receivers)' : "Digitraffic (Fintraffic, Finland's open maritime data, CC BY 4.0)"}, fetched ${ago(info.fetched)}. Ships broadcast these values themselves; name, type and destination are typed in by the crew and can be out of date. Drawn where it last reported.</p>`;
  },
};

// Warships: ships that broadcast themselves as military (AIS type 35). Many navies switch AIS off; those that leave
// it on show up here, larger and labelled at every zoom.
export const warships = {
  id: 'warships', title: 'Warships', color: ['#636366', '#c7c7cc'], feeds: {ships: 60}, layers: ['ww-warships'],
  about: () => 'Ships broadcasting as military (AIS type 35) on the worldwide stream and Finland\'s feed. Navies often switch AIS off; what is here chose to be seen.',
  addTo(map) {
    map.addSource('ww-warships', {type: 'geojson', data: {type: 'FeatureCollection', features: []}});
    map.addLayer({id: 'ww-warships', type: 'symbol', source: 'ww-warships', layout: {'icon-image': 'ww-warship', 'icon-rotate': ['get', 'dir'], 'icon-rotation-alignment': 'map',
      'icon-size': ['interpolate', ['linear'], ['zoom'], 1, 0.3, 5, 0.45, 9, 0.7], 'icon-allow-overlap': true, 'icon-ignore-placement': true,
      'text-field': ['step', ['zoom'], '', 3.5, ['get', 'label']], 'text-font': ['Noto Sans Bold'], 'text-size': 10.5, 'text-offset': [0, 1.6], 'text-anchor': 'top', 'text-optional': true}});
  },
  paint(map, dark) {
    const img = icon(dark ? '#c7c7cc' : '#48484a', dark ? '#1c1c1e' : '#ffffff');
    if (map.hasImage('ww-warship')) map.updateImage('ww-warship', img); else map.addImage('ww-warship', img, {pixelRatio: 2});
    map.setPaintProperty('ww-warships', 'text-color', dark ? '#e5e5ea' : '#1c1c1e'); map.setPaintProperty('ww-warships', 'text-halo-color', dark ? '#1c1c1e' : '#ffffff'); map.setPaintProperty('ww-warships', 'text-halo-width', 1.3);
  },
  onData() {},
  render(map) {
    map.getSource('ww-warships').setData({type: 'FeatureCollection', features: list.filter(s => s.kind === 'Military vessel').map(s => ({type: 'Feature', geometry: {type: 'Point', coordinates: [s.lon, s.lat]},
      properties: {id: 'ship:' + s.mmsi, dir: s.heading ?? s.course ?? 0, label: s.name || ''}}))});
  },
  count: () => list.filter(s => s.kind === 'Military vessel').length,
  rows: () => [],
  locate(id) { const s = list.find(x => 'ship:' + x.mmsi === id); return s && [s.lon, s.lat]; },
  ring: () => 15,
  owns: id => !!list.find(x => 'ship:' + x.mmsi === id && x.kind === 'Military vessel'),
  fill: fillShip,
  detail(id) { return shipsLayer.detail(id); },
};

export default shipsLayer;
