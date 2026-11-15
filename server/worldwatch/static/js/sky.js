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

// ---- photo: yesterday's view of the Earth from space, as an optional base picture ----
// NASA's VIIRS instrument on the NOAA-20 satellite photographs the whole planet once a day. Yesterday is
// the newest complete day. The strips where two passes meet, and the clouds, are part of the real picture.
const photoDay = () => new Date((now() - 86400) * 1000).toISOString().slice(0, 10);
let photoHook = () => {};
export const onPhoto = fn => { photoHook = fn; };
export const photo = {
  id: 'photo', title: 'Photo', color: ['#3a6b4a', '#6fae84'], feeds: {}, layers: ['ww-photo'], local: true, defaultOff: true,
  addTo(map) {
    map.addSource('ww-photo', {type: 'raster', tileSize: 256, maxzoom: 9, attribution: 'Imagery: NASA GIBS, VIIRS NOAA-20',
      tiles: [`https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/VIIRS_NOAA20_CorrectedReflectance_TrueColor/default/${photoDay()}/GoogleMapsCompatible_Level9/{z}/{y}/{x}.jpg`]});
    const labels = map.getStyle().layers.find(l => l.type === 'symbol')?.id;     // under the place names, over everything else of the base map
    map.addLayer({id: 'ww-photo', type: 'raster', source: 'ww-photo', paint: {'raster-fade-duration': 150}}, labels);
  },
  paint() {}, onData() {}, render() {},
  visible(on) { photoHook(on); },
  count: () => 0, note: () => photoDay().slice(8) + '.' + photoDay().slice(5, 7) + '.', rows: () => [], locate: () => null, ring: () => 0, detail: () => null,
  about: () => `The Earth as NASA's NOAA-20 satellite photographed it on ${photoDay()} (yesterday, the newest complete day). Clouds and the seams between passes are real. Sharp down to about regional zoom.`,
};

// ---- lightning: EUMETSAT's MTG Lightning Imager, flashes seen from geostationary orbit over Europe, Africa and the
// Atlantic. The picture is EUMETSAT's own (transparent where there was none), the newest they serve. ----
const EUM = 'https://view.eumetsat.int/geoserver/wms?service=WMS&version=1.3.0&request=GetMap&styles=&crs=EPSG:3857&format=image/png&transparent=true';
let lightMap = null, lightAt = 0, lightOn = true;
export const lightning = {
  id: 'lightning', title: 'Lightning', color: ['#ff9f0a', '#ffb340'], feeds: {}, layers: ['ww-lightning'], local: true,
  addTo(map) {
    lightMap = map;
    const add = () => {
      if (map.getLayer('ww-lightning')) map.removeLayer('ww-lightning');
      if (map.getSource('ww-lightning')) map.removeSource('ww-lightning');
      lightAt = now();
      map.addSource('ww-lightning', {type: 'raster', tileSize: 256, maxzoom: 8, attribution: 'Lightning: EUMETSAT MTG-LI',
        tiles: [`${EUM}&layers=mtg_fd:li_afa&width=256&height=256&bbox={bbox-epsg-3857}&_=${Math.floor(lightAt / 300)}`]});
      const first = map.getStyle().layers.find(l => l.id.startsWith('ww-') && !['ww-night', 'ww-photo', 'ww-sharp', 'ww-clouds'].includes(l.id))?.id;
      map.addLayer({id: 'ww-lightning', type: 'raster', source: 'ww-lightning', paint: {'raster-opacity': 0.95, 'raster-fade-duration': 0}, layout: {visibility: lightOn ? 'visible' : 'none'}}, first);
    };
    add(); setInterval(add, 300000);          // a fresh picture every five minutes
  },
  paint() {}, onData() {}, render() {},
  visible(on) { lightOn = on; },
  count: () => 0, note: () => lightAt ? local(lightAt) : '', rows: () => [], locate: () => null, ring: () => 0, detail: () => null,
  about: () => `Lightning seen by EUMETSAT's MTG weather satellite (Lightning Imager, accumulated flash area), the newest picture they serve, asked for at ${local(lightAt)}. Covers Europe, Africa, the Middle East, the Atlantic and eastern South America; elsewhere it is empty, not calm.`,
};

// ---- clouds: EUMETSAT's cloud mask from the Meteosat satellites (Europe, Africa, the Atlantic, and from the
// Indian Ocean satellite also India and the Middle East). Only the cloudy pixels are kept, drawn as soft white. ----
let cloudsOn = false, cloudAt = 0, cloudBusy = false;
async function cloudPicture(map) {
  if (cloudBusy || !cloudsOn) return; cloudBusy = true;
  try {
    const b = map.getBounds(), W = 700, H = 450;
    const x0 = Math.max(-180, b.getWest()), x1 = Math.min(180, b.getEast()), y0 = Math.max(-80, b.getSouth()), y1 = Math.min(80, b.getNorth());
    const m = ll => [ll[0] * 20037508.34 / 180, Math.log(Math.tan((90 + ll[1]) * Math.PI / 360)) * 20037508.34 / Math.PI];
    const [a, c] = [m([x0, y0]), m([x1, y1])], bbox = `${a[0]},${a[1]},${c[0]},${c[1]}`;
    const load = layer => new Promise(ok => { const im = new Image(); im.crossOrigin = 'anonymous'; im.onload = () => ok(im); im.onerror = () => ok(null);
      im.src = `${EUM}&layers=${layer}&width=${W}&height=${H}&bbox=${bbox}`; });
    const imgs = (await Promise.all([load('msg_iodc:clm'), load('msg_fes:clm')])).filter(Boolean);   // the 0-degree satellite drawn last wins where both see
    const cv = document.createElement('canvas'); cv.width = W; cv.height = H;
    const x = cv.getContext('2d'), out = x.createImageData(W, H);
    for (const im of imgs) {
      const t = document.createElement('canvas'); t.width = W; t.height = H; const tx = t.getContext('2d'); tx.drawImage(im, 0, 0, W, H);
      const px = tx.getImageData(0, 0, W, H).data;
      for (let i = 0; i < px.length; i += 4) {
        if (px[i + 3] < 128) continue;                                 // outside this satellite's view
        const cloud = px[i] > 200 && px[i + 1] > 200 && px[i + 2] > 200; // the mask paints clouds white, clear land green, clear sea blue
        out.data[i] = out.data[i + 1] = out.data[i + 2] = 255; out.data[i + 3] = cloud ? 150 : 0;
      }
    }
    x.putImageData(out, 0, 0);
    const coords = [[x0, y1], [x1, y1], [x1, y0], [x0, y0]];
    const src = map.getSource('ww-clouds');
    if (src) src.updateImage({url: cv.toDataURL(), coordinates: coords});
    else {
      map.addSource('ww-clouds', {type: 'image', url: cv.toDataURL(), coordinates: coords});
      const first = map.getStyle().layers.find(l => l.id.startsWith('ww-') && !['ww-night', 'ww-photo', 'ww-sharp'].includes(l.id))?.id;
      map.addLayer({id: 'ww-clouds', type: 'raster', source: 'ww-clouds', paint: {'raster-opacity': 0.85, 'raster-fade-duration': 0}}, first);
    }
    cloudAt = now();
  } finally { cloudBusy = false; }
}
export const clouds = {
  id: 'clouds', title: 'Clouds', color: ['#8e8e93', '#aeaeb2'], feeds: {}, layers: ['ww-clouds'], local: true, defaultOff: true,
  addTo(map) {
    let t = null;
    map.on('moveend', () => { clearTimeout(t); t = setTimeout(() => cloudPicture(map), 500); });
    setInterval(() => cloudPicture(map), 600000);
    cloudPicture(map);
  },
  paint() {}, onData() {}, render() {},
  visible(on) { cloudsOn = on; if (on && lightMap) cloudPicture(lightMap); },
  count: () => 0, note: () => cloudAt ? local(cloudAt) : '', rows: () => [], locate: () => null, ring: () => 0, detail: () => null,
  about: () => `Clouds from EUMETSAT's Meteosat cloud mask (the 0° and Indian Ocean satellites), the newest picture they serve, refreshed every 10 minutes and when the map moves. Covers Europe, Africa, the Middle East and India; the Americas and East Asia are not covered.`,
};

// ---- sharp photo: Esri World Imagery, up to 0.3-0.5 m per pixel in cities. Sharp but not current: each area is a
// different date. The date of the picture under the map's centre is looked up and shown. ----
let sharpOn = false, sharpDate = null, sharpMap = null;
async function sharpWhen() {
  if (!sharpOn || !sharpMap) return;
  const c = sharpMap.getCenter();
  try { sharpDate = await fetch(`/api/imagery/date?lat=${c.lat.toFixed(3)}&lon=${c.lng.toFixed(3)}&z=${Math.round(sharpMap.getZoom())}`).then(r => r.json()); } catch (e) { sharpDate = null; }
  document.dispatchEvent(new Event('ww-chips'));
}
export const sharp = {
  id: 'sharp', title: 'Sharp photo', color: ['#5e5ce6', '#7d7aff'], feeds: {}, layers: ['ww-sharp'], local: true, defaultOff: true,
  addTo(map) {
    sharpMap = map;
    map.addSource('ww-sharp', {type: 'raster', tileSize: 256, maxzoom: 19, attribution: 'Imagery: Esri, Vantor, Earthstar Geographics',
      tiles: ['https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}']});
    const labels = map.getStyle().layers.find(l => l.type === 'symbol')?.id;
    map.addLayer({id: 'ww-sharp', type: 'raster', source: 'ww-sharp', paint: {'raster-fade-duration': 150}}, labels);
    let t = null; map.on('moveend', () => { clearTimeout(t); t = setTimeout(sharpWhen, 700); });
  },
  paint() {}, onData() {}, render() {},
  visible(on) { sharpOn = on; photoHook(on); if (on) sharpWhen(); },
  count: () => 0, note: () => sharpDate?.date ? sharpDate.date.slice(0, 7) : '', rows: () => [], locate: () => null, ring: () => 0, detail: () => null,
  about: () => sharpDate?.date ? `Under the map's centre: a picture taken ${sharpDate.date}${sharpDate.res ? ', ' + sharpDate.res + ' m per pixel' : ''}${sharpDate.sensor ? ', ' + sharpDate.sensor : ''} (${sharpDate.source || 'Esri World Imagery'}). Sharp, but not current: each area has its own date, often months or years old.`
    : 'Esri World Imagery: sharp aerial and satellite pictures, each area from its own date (months or years old). Zoom in for the date of the picture under the map\'s centre.',
};
