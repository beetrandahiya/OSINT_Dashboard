// Three layers that colour the map rather than add markers: rain radar, night, and the aurora zone.
import {$, ago, esc, local, now, utc} from './util.js';

// ---- rain radar: pictures from RainViewer, drawn as they come ----
let frame = null, radarInfo = null, radarMap = null, radarOn = true;
export const rain = {
  id: 'rain', title: 'Rain', color: ['#0a84ff', '#409cff'], feeds: {radar: 120}, layers: ['ww-rain'],
  addTo(map) { radarMap = map; },
  paint() {},
  onData(feed, d) { radarInfo = d; frame = d.payload; },
  render(map) {
    if (!frame) return;
    const url = `${frame.host}${frame.path}/256/{z}/{x}/{y}/2/1_1.png`;
    if (map.getSource('ww-rain')?.tiles?.[0] === url) return;
    if (map.getLayer('ww-rain')) map.removeLayer('ww-rain');
    if (map.getSource('ww-rain')) map.removeSource('ww-rain');
    map.addSource('ww-rain', {type: 'raster', tiles: [url], tileSize: 256, maxzoom: 7, attribution: 'Rain radar: RainViewer'});
    // under every marker layer of ours, over the base map
    const first = map.getStyle().layers.find(l => l.id.startsWith('ww-') && l.id !== 'ww-night')?.id;
    map.addLayer({id: 'ww-rain', type: 'raster', source: 'ww-rain', paint: {'raster-opacity': 0.65, 'raster-fade-duration': 0}, layout: {visibility: radarOn ? 'visible' : 'none'}}, first);
  },
  visible(on) { radarOn = on; },
  count: () => 0,
  note: () => frame ? local(frame.time) : '',
  rows: () => [],
  locate: () => null, ring: () => 0, detail: () => null,
  about: () => frame ? `Rain radar picture of ${utc(frame.time)} (${ago(frame.time)}), from RainViewer, which stitches together national weather radars. Places without radar coverage stay blank, which does not mean it is dry there.` : '',
};

// ---- night: where the sun is below the horizon right now (astronomy, not a feed) ----
function sun(t) {   // the point on Earth directly under the sun
  const d = t / 86400 - 10957.5;                                   // days since 1 Jan 2000, 12:00 UTC
  const g = (357.529 + 0.98560028 * d) * Math.PI / 180, q = 280.459 + 0.98564736 * d;
  const L = (q + 1.915 * Math.sin(g) + 0.020 * Math.sin(2 * g)) * Math.PI / 180, e = (23.439 - 0.00000036 * d) * Math.PI / 180;
  const ra = Math.atan2(Math.cos(e) * Math.sin(L), Math.cos(L)), dec = Math.asin(Math.sin(e) * Math.sin(L));
  const gmst = (18.697374558 + 24.06570982441908 * d) % 24;
  let lon = (ra * 12 / Math.PI - gmst) * 15; lon = ((lon + 540) % 360) - 180;
  return {lon, lat: dec * 180 / Math.PI};
}
function nightShape(t) {
  const s = sun(t), dec = s.lat * Math.PI / 180, ring = [];
  for (let lon = -180; lon <= 180; lon += 2) ring.push([lon, Math.atan(-Math.cos((lon - s.lon) * Math.PI / 180) / Math.tan(dec)) * 180 / Math.PI]);
  const pole = s.lat > 0 ? -89.9 : 89.9;                           // the dark pole closes the shape
  return {type: 'Feature', geometry: {type: 'Polygon', coordinates: [[...ring, [180, pole], [-180, pole], ring[0]]]}, properties: {}};
}
export const night = {
  id: 'night', title: 'Night', color: ['#1c1c1e', '#8e8e93'], feeds: {}, layers: ['ww-night'],
  addTo(map) {
    map.addSource('ww-night', {type: 'geojson', data: nightShape(now())});
    map.addLayer({id: 'ww-night', type: 'fill', source: 'ww-night', paint: {'fill-color': '#000814', 'fill-opacity': 0.22}}, map.getStyle().layers.find(l => l.id.startsWith('ww-'))?.id);
    setInterval(() => map.getSource('ww-night')?.setData(nightShape(now())), 60000);
  },
  paint(map, dark) { map.setPaintProperty('ww-night', 'fill-opacity', dark ? 0.38 : 0.2); },
  onData() {}, render() {},
  count: () => 0, note: () => '', rows: () => [], locate: () => null, ring: () => 0, detail: () => null, local: true,
  about: () => 'The shaded side of the map is where the sun is below the horizon right now. Calculated from the date and time; not a feed.',
};

// ---- aurora: NOAA's forecast of where aurora is likely, plus the K index in the bottom strip ----
let sw = null, swInfo = null;
const G = kp => kp >= 9 ? 'G5, extreme storm' : kp >= 8 ? 'G4, severe storm' : kp >= 7 ? 'G3, strong storm' : kp >= 6 ? 'G2, moderate storm' : kp >= 5 ? 'G1, minor storm' : kp >= 4 ? 'active' : 'quiet';
export const aurora = {
  id: 'aurora', title: 'Aurora', color: ['#00a878', '#63e6be'], feeds: {space_weather: 300}, layers: ['ww-aurora'],
  addTo(map) {
    map.addSource('ww-aurora', {type: 'geojson', data: {type: 'FeatureCollection', features: []}});
    map.addLayer({id: 'ww-aurora', type: 'circle', source: 'ww-aurora',
      paint: {'circle-radius': ['interpolate', ['exponential', 2], ['zoom'], 0, 1.2, 6, 76], 'circle-blur': 0.9, 'circle-pitch-alignment': 'map',
              'circle-opacity': ['interpolate', ['linear'], ['get', 'p'], 10, 0.12, 50, 0.5, 100, 0.8]}}, map.getStyle().layers.find(l => l.id.startsWith('ww-') && !['ww-night', 'ww-rain'].includes(l.id))?.id);
  },
  paint(map, dark) { map.setPaintProperty('ww-aurora', 'circle-color', this.color[+dark]); },
  onData(feed, d) { sw = d.payload; swInfo = d; },
  render(map) {
    map.getSource('ww-aurora').setData({type: 'FeatureCollection', features: sw.aurora.map(c => ({type: 'Feature', geometry: {type: 'Point', coordinates: [c[0], c[1]]}, properties: {p: c[2]}}))});
    const el = $('#spaceweather');
    if (el) el.innerHTML = `<span class="quote" title="NOAA's planetary K index: how disturbed Earth's magnetic field is, from 0 to 9. From 5 up NOAA calls it a geomagnetic storm (G1 to G5), and aurora reaches lower latitudes."><b>Kp</b>${sw.kp.toFixed(1)} <span class="${sw.kp >= 5 ? 'down' : ''}">${G(sw.kp)}</span><i>${ago(sw.kp_time + 3 * 3600)}</i></span>`;
  },
  count: () => 0,
  note: () => sw ? 'Kp ' + sw.kp.toFixed(1) : '',
  rows() {   // only when NOAA's own scale calls it a storm
    return sw && sw.kp >= 5 ? [{id: 'kp', time: sw.kp_time + 3 * 3600, badge: 'Kp', strong: true, title: `Geomagnetic storm, ${G(sw.kp)}`, meta: `Space weather · Kp ${sw.kp.toFixed(1)} · NOAA`}] : [];
  },
  locate: () => null, ring: () => 0,
  detail(id) {
    if (id !== 'kp' || !sw) return null;
    return `<p class="eyebrow">Space weather</p><h2>Kp ${sw.kp.toFixed(1)}</h2><p class="where">${G(sw.kp)}</p>
      <dl><dt>Three-hour period ending</dt><dd>${local(sw.kp_time + 3 * 3600)} <span class="soft">(${ago(sw.kp_time + 3 * 3600)})</span></dd>
      <dt>Aurora picture observed</dt><dd>${local(sw.aurora_observed)} <span class="soft">(${ago(sw.aurora_observed)})</span></dd></dl>
      <a class="link" href="https://www.swpc.noaa.gov/products/planetary-k-index" target="_blank" rel="noopener">Open NOAA's K index page</a>
      <p class="source">Source: NOAA Space Weather Prediction Center, fetched ${ago(swInfo.fetched)}. The storm names (G1 to G5) are NOAA's own scale.</p>`;
  },
  about: () => sw ? `Green glow: where NOAA's model gives aurora a 10 % chance or more, from the observation of ${utc(sw.aurora_observed)} (${ago(sw.aurora_observed)}). Being in the zone does not mean you will see it: it needs darkness and clear sky.` : '',
};
