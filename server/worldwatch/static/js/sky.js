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
// A picture laid over the whole map (Web Mercator, reaching to 89 degrees so the globe's poles are covered too).
// fn(lon, lat) gives the opacity 0..1.
const TOP = 89, YMAX = Math.asinh(Math.tan(TOP * Math.PI / 180)), EDGE = [[-180, TOP], [180, TOP], [180, -TOP], [-180, -TOP]];
function picture(size, rgb, fn) {
  const c = document.createElement('canvas'); c.width = c.height = size;
  const x = c.getContext('2d'), img = x.createImageData(size, size), d = img.data;
  for (let j = 0; j < size; j++) {
    const lat = Math.atan(Math.sinh(YMAX * (1 - 2 * (j + 0.5) / size))) * 180 / Math.PI;
    for (let i = 0; i < size; i++) {
      const o = (j * size + i) * 4;
      d[o] = rgb[0]; d[o + 1] = rgb[1]; d[o + 2] = rgb[2]; d[o + 3] = 255 * fn((i + 0.5) / size * 360 - 180, lat);
    }
  }
  x.putImageData(img, 0, 0);
  return c.toDataURL();
}
function overlay(map, id, url, before) {
  if (map.getSource(id)) { map.getSource(id).updateImage({url, coordinates: EDGE}); return; }
  map.addSource(id, {type: 'image', url, coordinates: EDGE});
  map.addLayer({id, type: 'raster', source: id, paint: {'raster-fade-duration': 0, 'raster-resampling': 'linear'}}, before);
}

// Night fades in the way dusk does: from the moment the sun touches the horizon to the end of nautical
// twilight, when it is 12 degrees below. Those two angles are the standard definitions, nothing is tuned by eye.
function nightPicture(t) {
  const s = sun(t), dec = s.lat * Math.PI / 180, sd = Math.sin(dec), cd = Math.cos(dec), r = Math.PI / 180;
  return picture(384, [0, 8, 24], (lon, lat) => {
    const alt = Math.asin(Math.sin(lat * r) * sd + Math.cos(lat * r) * cd * Math.cos((lon - s.lon) * r)) / r;
    const k = Math.min(1, Math.max(0, -alt / 12));
    return k * k * (3 - 2 * k);
  });
}
export const night = {
  id: 'night', title: 'Night', color: ['#1c1c1e', '#8e8e93'], feeds: {}, layers: ['ww-night'],
  addTo(map) {
    overlay(map, 'ww-night', nightPicture(now()), map.getStyle().layers.find(l => l.id.startsWith('ww-'))?.id);
    setInterval(() => overlay(map, 'ww-night', nightPicture(now())), 60000);
  },
  paint(map, dark) { map.setPaintProperty('ww-night', 'raster-opacity', dark ? 0.5 : 0.3); },
  onData() {}, render() {},
  count: () => 0, note: () => '', rows: () => [], locate: () => null, ring: () => 0, detail: () => null, local: true,
  about: () => 'The shaded side of the map is where the sun is below the horizon right now, fading in over twilight (sun 0 to 12 degrees below the horizon). Calculated from the date and time; not a feed.',
};

// ---- aurora: NOAA's forecast of where aurora is likely, plus the K index in the bottom strip ----
let sw = null, swInfo = null, auroraMap = null, auroraDark = false, auroraOn = true;
const G = kp => kp >= 9 ? 'G5, extreme storm' : kp >= 8 ? 'G4, severe storm' : kp >= 7 ? 'G3, strong storm' : kp >= 6 ? 'G2, moderate storm' : kp >= 5 ? 'G1, minor storm' : kp >= 4 ? 'active' : 'quiet';
export const aurora = {
  id: 'aurora', title: 'Aurora', color: ['#00a878', '#63e6be'], feeds: {space_weather: 300}, layers: ['ww-aurora'],
  addTo(map) { auroraMap = map; },
  paint(map, dark) { auroraDark = dark; if (sw) this.render(map); },
  onData(feed, d) { sw = d.payload; swInfo = d; },
  render(map) {
    // NOAA gives one number per degree of longitude and latitude. Neighbouring cells are averaged twice and the
    // picture is sampled smoothly between cells, so the glow has soft edges instead of grid lines.
    let g = new Float32Array(360 * 181);
    for (const [lon, lat, p] of sw.aurora) g[(lat + 90) * 360 + lon] = p;
    for (let pass = 0; pass < 2; pass++) {
      const o = new Float32Array(g.length);
      for (let y = 0; y < 181; y++) for (let x = 0; x < 360; x++) {
        let sum = 0, n = 0;
        for (let dy = -1; dy <= 1; dy++) { const yy = y + dy; if (yy < 0 || yy > 180) continue; for (let dx = -1; dx <= 1; dx++) { sum += g[yy * 360 + (x + dx + 360) % 360]; n++; } }
        o[y * 360 + x] = sum / n;
      }
      g = o;
    }
    const at = (lon, lat) => {
      const x = ((lon % 360) + 360) % 360, y = lat + 90, x0 = Math.floor(x), y0 = Math.min(179, Math.floor(y)), fx = x - x0, fy = y - y0, x1 = (x0 + 1) % 360;
      return (g[y0 * 360 + x0] * (1 - fx) + g[y0 * 360 + x1] * fx) * (1 - fy) + (g[(y0 + 1) * 360 + x0] * (1 - fx) + g[(y0 + 1) * 360 + x1] * fx) * fy;
    };
    const rgb = auroraDark ? [70, 235, 170] : [0, 168, 120];
    const first = map.getStyle().layers.find(l => l.id.startsWith('ww-') && !['ww-night', 'ww-rain', 'ww-aurora'].includes(l.id))?.id;
    overlay(map, 'ww-aurora', picture(768, rgb, (lon, lat) => Math.min(0.85, Math.max(0, (at(lon, lat) - 3) / 45))), first);
    map.setLayoutProperty('ww-aurora', 'visibility', auroraOn ? 'visible' : 'none');
    const el = $('#spaceweather');
    if (el) el.innerHTML = `<span class="quote" title="NOAA's planetary K index: how disturbed Earth's magnetic field is, from 0 to 9. From 5 up NOAA calls it a geomagnetic storm (G1 to G5), and aurora reaches lower latitudes."><b>Kp</b>${sw.kp.toFixed(1)} <span class="${sw.kp >= 5 ? 'down' : ''}">${G(sw.kp)}</span><i>${ago(sw.kp_time + 3 * 3600)}</i></span>`;
  },
  visible(on) { auroraOn = on; },
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
  about: () => sw ? `Green glow: where NOAA's model expects aurora, stronger where it is more likely, from the observation of ${utc(sw.aurora_observed)} (${ago(sw.aurora_observed)}). Being in the zone does not mean you will see it: it needs darkness and clear sky.` : '',
};
