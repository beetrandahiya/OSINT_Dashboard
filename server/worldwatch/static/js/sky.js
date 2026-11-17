// Three layers that colour the map rather than add markers: rain radar, night, and the aurora zone.
import {every} from './prefs.js';
import {$, ago, esc, local, now, utc} from './util.js';
import {slot} from './map.js';

// A tiled picture that is replaced from time to time (a new radar frame, a new satellite time): the source keeps its
// id and only its tile address changes, so the old tiles stay on screen until the new ones arrive (removing and
// re-adding the layer left the area blank for seconds) and the layer keeps its place in the stack.
function tiles(map, id, url, source, layer, before) {
  const src = map.getSource(id);
  if (src) { if (src.tiles?.[0] !== url) src.setTiles([url]); return; }
  map.addSource(id, {type: 'raster', tiles: [url], ...source});
  map.addLayer({id, type: 'raster', source: id, ...layer}, before);
}

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
    tiles(map, 'ww-rain', url, {tileSize: 256, maxzoom: 7, attribution: 'Rain radar: RainViewer'},
      {paint: {'raster-opacity': 0.65, 'raster-fade-duration': 0}, layout: {visibility: radarOn ? 'visible' : 'none'}}, slot(map, 'rain'));
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
// The picture is only drawn while the layer is on (it was rebuilt every minute whether shown or not).
const BLANK = 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==';
let nightMap = null, nightOn = false, nightAt = 0;
const nightNow = () => { if (!nightMap) return; nightAt = now(); overlay(nightMap, 'ww-night', nightPicture(nightAt)); };
export const night = {
  id: 'night', title: 'Night', color: ['#1c1c1e', '#8e8e93'], feeds: {}, layers: ['ww-night'],
  addTo(map) {
    nightMap = map;
    overlay(map, 'ww-night', BLANK, slot(map, 'night'));
    every(60, () => { if (nightOn) nightNow(); }, {scaled: false});
  },
  visible(on) { nightOn = on; if (on && now() - nightAt > 50) nightNow(); },
  paint(map, dark) { map.setPaintProperty('ww-night', 'raster-opacity', dark ? 0.5 : 0.3); },
  onData() {}, render() {},
  count: () => 0, note: () => '', rows: () => [], locate: () => null, ring: () => 0, detail: () => null, local: true,
  about: () => 'The shaded side of the map is where the sun is below the horizon right now, fading in over twilight (sun 0 to 12 degrees below the horizon). Calculated from the date and time; not a feed.',
};

// ---- aurora: NOAA's forecast of where aurora is likely, plus the K index in the bottom strip ----
let sw = null, swInfo = null, auroraMap = null, auroraDark = false, auroraOn = true, auroraBuilt = '';
const G = kp => kp >= 9 ? 'G5, extreme storm' : kp >= 8 ? 'G4, severe storm' : kp >= 7 ? 'G3, strong storm' : kp >= 6 ? 'G2, moderate storm' : kp >= 5 ? 'G1, minor storm' : kp >= 4 ? 'active' : 'quiet';
export const aurora = {
  id: 'aurora', title: 'Aurora', color: ['#00a878', '#63e6be'], feeds: {space_weather: 300}, layers: ['ww-aurora'],
  addTo(map) { auroraMap = map; },
  paint(map, dark) { auroraDark = dark; this.render(map); },
  onData(feed, d) { sw = d.payload; swInfo = d; },
  render(map) {
    if (!sw) return;
    const el = $('#spaceweather');
    if (el) el.innerHTML = `<span class="quote" title="NOAA's planetary K index: how disturbed Earth's magnetic field is, from 0 to 9. From 5 up NOAA calls it a geomagnetic storm (G1 to G5), and aurora reaches lower latitudes."><b>Kp</b>${sw.kp.toFixed(1)} <span class="${sw.kp >= 5 ? 'down' : ''}">${G(sw.kp)}</span><i>${ago(sw.kp_time + 3 * 3600)}</i></span>`;
    // the picture costs most of a second: built only while the layer is on, and only for a new observation or theme
    const key = sw.aurora_observed + '|' + auroraDark;
    if (!auroraOn || key === auroraBuilt) return;
    auroraBuilt = key;
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
    overlay(map, 'ww-aurora', picture(768, rgb, (lon, lat) => Math.min(0.85, Math.max(0, (at(lon, lat) - 3) / 45))), slot(map, 'aurora'));
    map.setLayoutProperty('ww-aurora', 'visibility', auroraOn ? 'visible' : 'none');
  },
  visible(on) { auroraOn = on; if (on && auroraMap) this.render(auroraMap); },
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
// Place names turn white over a photo. Three layers are photos; the names follow whether ANY of them is on (each used
// to report only its own state, so switching one off darkened the names over another that was still showing).
let photoHook = () => {}, photoOn = false;
export const onPhoto = fn => { photoHook = fn; };
const photoState = () => photoHook(photoOn || liveOn || sharpOn);
export const photo = {
  id: 'photo', title: 'Photo', color: ['#3a6b4a', '#6fae84'], feeds: {}, layers: ['ww-photo'], local: true, defaultOff: true,
  addTo(map) {
    map.addSource('ww-photo', {type: 'raster', tileSize: 256, maxzoom: 9, attribution: 'Imagery: NASA GIBS, VIIRS NOAA-20',
      tiles: [`https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/VIIRS_NOAA20_CorrectedReflectance_TrueColor/default/${photoDay()}/GoogleMapsCompatible_Level9/{z}/{y}/{x}.jpg`]});
    map.addLayer({id: 'ww-photo', type: 'raster', source: 'ww-photo', paint: {'raster-fade-duration': 150}}, slot(map, 'photo'));   // over the base map, under everything of ours
  },
  paint() {}, onData() {}, render() {},
  visible(on) { photoOn = on; photoState(); },
  count: () => 0, note: () => photoDay().slice(8) + '.' + photoDay().slice(5, 7) + '.', rows: () => [], locate: () => null, ring: () => 0, detail: () => null,
  about: () => `The Earth as NASA's NOAA-20 satellite photographed it on ${photoDay()} (yesterday, the newest complete day). Clouds and the seams between passes are real. Sharp down to about regional zoom.`,
};

// ---- lightning: EUMETSAT's MTG Lightning Imager, flashes seen from geostationary orbit over Europe, Africa and the
// Atlantic. The picture is EUMETSAT's own (transparent where there was none), the newest they serve. ----
const EUM = 'https://view.eumetsat.int/geoserver/wms?service=WMS&version=1.3.0&request=GetMap&styles=&crs=EPSG:3857&format=image/png&transparent=true';
let lightMap = null, lightAt = 0, lightOn = true, lightTime = null, lightFail = false, lightAsk = null;
export const lightning = {
  id: 'lightning', title: 'Lightning', color: ['#ff9f0a', '#ffb340'], feeds: {}, layers: ['ww-lightning'], local: true,
  addTo(map) {
    lightMap = map;
    const add = async () => {
      let t = null;
      try { t = (await fetch('/api/eumetsat/time?layer=mtg_fd:li_afa').then(r => r.json())).time; } catch (e) { /* keep the last picture */ }
      // no time from EUMETSAT: keep the last picture, but say so instead of looking like a quiet sky
      const fail = !t && (!lightAt || now() - lightAt > 1800);
      if (fail !== lightFail) { lightFail = fail; document.dispatchEvent(new Event('ww-chips')); }
      if (!t || t === lightTime) return;
      lightTime = t; lightAt = Date.parse(t) / 1000;
      // every tile asks for the same image time, so the picture holds still while zooming
      tiles(map, 'ww-lightning', `${EUM}&layers=mtg_fd:li_afa&width=256&height=256&bbox={bbox-epsg-3857}&TIME=${encodeURIComponent(t)}`,
        {tileSize: 256, maxzoom: 8, attribution: 'Lightning: EUMETSAT MTG-LI'},
        {paint: {'raster-opacity': 0.95, 'raster-fade-duration': 0}, layout: {visibility: lightOn ? 'visible' : 'none'}}, slot(map, 'lightning'));
      document.dispatchEvent(new Event('ww-chips'));
    };
    // EUMETSAT adds a new picture every five minutes (prefs.js: not while hidden); while the layer is off only every
    // 15 minutes, for the chip's time, like the feeds of other layers that are off
    let asked = 0;
    lightAsk = () => { asked = performance.now(); add(); };
    lightAsk(); every(60, () => { if (lightOn || performance.now() - asked > 900000) lightAsk(); }, {scaled: false});
  },
  paint() {}, onData() {}, render() {},
  visible(on) { const was = lightOn; lightOn = on; if (on && !was) lightAsk?.(); },
  count: () => 0, note: () => lightFail ? 'no answer' : lightAt ? local(lightAt) : '', rows: () => [], locate: () => null, ring: () => 0, detail: () => null,
  about: () => (lightFail ? `EUMETSAT did not say which lightning picture is newest${lightAt ? '; the one shown is from ' + utc(lightAt) + ' (' + ago(lightAt) + ')' : ', so nothing is shown'}. ` : '') + `Lightning seen by EUMETSAT's MTG weather satellite (Lightning Imager, accumulated flash area) in the picture of ${lightAt ? utc(lightAt) + ' (' + ago(lightAt) + ')' : 'the newest time'}. Covers Europe, Africa, the Middle East, the Atlantic and eastern South America; elsewhere it is empty, not calm.`,
};

// ---- live photo: the newest whole-disk pictures from weather satellites in geostationary orbit, every 10-15
// minutes, about 1-3 km per pixel: Europe/Africa/Middle East from MTG (true colour by day, a night version after dark),
// India and the Indian Ocean from Meteosat's Indian Ocean satellite, the Americas from GOES-East and GOES-West (via
// NASA GIBS). East Asia and the western Pacific (Himawari) have no colour picture in these services. ----
let liveOn = false, liveAt = null, liveMap = null;
const LIVE = [
  ['ww-live-goesw', 'https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/GOES-West_ABI_GeoColor/default/default/GoogleMapsCompatible_Level7/{z}/{y}/{x}.png', 7, 'GOES-West (NOAA, via NASA GIBS)'],
  ['ww-live-goese', 'https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/GOES-East_ABI_GeoColor/default/default/GoogleMapsCompatible_Level7/{z}/{y}/{x}.png', 7, 'GOES-East (NOAA, via NASA GIBS)'],
  ['ww-live-iodc', 'msg_iodc:rgb_naturalenhncd', 7, 'Meteosat Indian Ocean (EUMETSAT)'],
  ['ww-live-mtg', 'mtg_fd:rgb_geocolour', 8, 'MTG (EUMETSAT)'],
];
async function liveAdd(map) {
  let t = null;
  try { t = (await fetch('/api/eumetsat/time?layer=mtg_fd:rgb_geocolour').then(r => r.json())).time; } catch (e) { /* keep */ }
  if (t && t === liveAt) return;
  liveAt = t;
  for (const [id, src, maxzoom, credit] of LIVE) {
    const url = src.startsWith('http') ? src : `${EUM}&layers=${src}&width=256&height=256&bbox={bbox-epsg-3857}${t ? '&TIME=' + encodeURIComponent(t) : ''}`;
    // GIBS's GOES addresses never change: those sources are left alone; EUMETSAT's carry the new time
    tiles(map, id, url, {tileSize: 256, maxzoom, attribution: 'Live photo: ' + credit},
      {paint: {'raster-fade-duration': 0}, layout: {visibility: liveOn ? 'visible' : 'none'}}, slot(map, 'live'));
  }
  document.dispatchEvent(new Event('ww-chips'));
}
export const livephoto = {
  id: 'livephoto', title: 'Live photo', color: ['#3a6b4a', '#6fae84'], feeds: {}, layers: LIVE.map(l => l[0]), local: true, defaultOff: true,
  addTo(map) { liveMap = map; liveAdd(map); every(120, () => liveOn && liveAdd(map), {scaled: false}); },
  paint() {}, onData() {}, render() {},
  visible(on) { liveOn = on; photoState(); if (on && liveMap) liveAdd(liveMap); },
  count: () => 0, note: () => liveAt ? local(Date.parse(liveAt) / 1000) : '', rows: () => [], locate: () => null, ring: () => 0, detail: () => null,
  about: () => `The newest pictures from weather satellites that stay over one spot (every 10-15 minutes, 1-3 km per pixel): Europe, Africa and the Middle East from MTG${liveAt ? ' (' + utc(Date.parse(liveAt) / 1000) + ')' : ''}, India from Meteosat's Indian Ocean satellite, the Americas from GOES-East and GOES-West. Coarser than the daily Photo but current. East Asia is not covered.`,
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
    map.addLayer({id: 'ww-sharp', type: 'raster', source: 'ww-sharp', paint: {'raster-fade-duration': 150}}, slot(map, 'sharp'));
    let t = null; map.on('moveend', () => { clearTimeout(t); t = setTimeout(sharpWhen, 700); });
  },
  paint() {}, onData() {}, render() {},
  visible(on) { sharpOn = on; photoState(); if (on) sharpWhen(); },
  count: () => 0, note: () => sharpDate?.date ? sharpDate.date.slice(0, 7) : '', rows: () => [], locate: () => null, ring: () => 0, detail: () => null,
  about: () => sharpDate?.date ? `Under the map's centre: a picture taken ${sharpDate.date}${sharpDate.res ? ', ' + sharpDate.res + ' m per pixel' : ''}${sharpDate.sensor ? ', ' + sharpDate.sensor : ''} (${sharpDate.source || 'Esri World Imagery'}). Sharp, but not current: each area has its own date, often months or years old.`
    : 'Esri World Imagery: sharp aerial and satellite pictures, each area from its own date (months or years old). Zoom in for the date of the picture under the map\'s centre.',
};
