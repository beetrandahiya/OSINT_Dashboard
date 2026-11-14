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

export default {
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
  owns: id => String(id).startsWith('ship:'),
  about: () => info?.payload?.world?.key ? `Ships worldwide from aisstream.io (volunteer receivers: dense near coasts, thin mid-ocean) plus Finland's open feed.` : 'Ships in the northern Baltic only, from Finland\'s open data. For the rest of the world, register a free key at aisstream.io and put it in data/aisstream-key.txt.',
  detail(id) {
    const s = list.find(x => 'ship:' + x.mmsi === id);
    if (!s) return null;
    return `<p class="eyebrow">${esc(s.kind || 'Ship')}</p><h2>${esc(s.name || 'MMSI ' + s.mmsi)}</h2>
      <p class="where">${s.destination ? 'Destination as entered by the crew: ' + esc(s.destination) : 'No destination entered'}</p>
      <dl><dt>Status</dt><dd>${esc(STATUS[s.status] || 'Not stated')}</dd>
      <dt>Speed</dt><dd>${s.speed_kn == null ? 'not reported' : s.speed_kn.toFixed(1) + ' kn <span class="soft">(' + Math.round(s.speed_kn * 1.852) + ' km/h)</span>'}</dd>
      <dt>Course</dt><dd>${s.course == null ? 'not reported' : Math.round(s.course) + '°'}</dd>
      ${s.length_m ? `<dt>Length</dt><dd>${s.length_m} m</dd>` : ''}
      ${s.draught_m ? `<dt>Draught</dt><dd>${(+s.draught_m).toFixed(1)} m</dd>` : ''}
      <dt>Position reported</dt><dd>${local(s.time)} <span class="soft">(${ago(s.time)})</span></dd>
      <dt>Identifiers</dt><dd>MMSI ${s.mmsi}${s.imo ? ' · IMO ' + s.imo : ''}${s.callsign ? ' · ' + esc(s.callsign) : ''}</dd></dl>
      <a class="link" href="https://www.marinetraffic.com/en/ais/details/ships/mmsi:${s.mmsi}" target="_blank" rel="noopener">Look this ship up on MarineTraffic</a>
      ${s.length_m ? '' : ''}<p class="source">Source: ${s.source === 'aisstream.io' ? 'aisstream.io (AIS relayed by volunteer receivers)' : "Digitraffic (Fintraffic, Finland's open maritime data, CC BY 4.0)"}, fetched ${ago(info.fetched)}. Ships broadcast these values themselves; name, type and destination are typed in by the crew and can be out of date. Drawn where it last reported.</p>`;
  },
};
