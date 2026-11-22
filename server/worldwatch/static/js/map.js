import {look, mapPixelRatio} from './look.js';
// The map: one MapLibre instance that is both the flat map and the globe.
// Base map data: OpenStreetMap via OpenFreeMap's free tiles. We recolour their "positron" style
// for light and dark instead of loading two styles, so our own layers survive a theme change.

const BASE_STYLE = 'https://tiles.openfreemap.org/styles/positron';

const PALETTE = {
  light: {land: '#f6f4ee', water: '#a9d3f5', park: '#d3ecc8', wood: '#d9eccf', ice: '#ffffff', urban: '#efece4', building: '#e6e2d8',
          road: '#ffffff', casing: '#dedad0', rail: '#cfcbc2', border: '#b9b4ab', aero: '#e7e4ec',
          label: '#4a4a4f', labelSoft: '#7b7b80', waterLabel: '#4f83b8', halo: '#f6f4ee'},
  dark:  {land: '#25262a', water: '#152334', park: '#1f3327', wood: '#213226', ice: '#3a3c42', urban: '#2a2b30', building: '#303137',
          road: '#3b3d44', casing: '#1d1e21', rail: '#3a3b40', border: '#5a5c63', aero: '#2f2f38',
          label: '#c9c9ce', labelSoft: '#8e8e93', waterLabel: '#6d94bf', halo: '#1c1c1e'},
  // God's eye: cold steel greys (no orange or warm tones anywhere in this theme)
  eyeLight: {land: '#e6ebef', water: '#c3d2dd', park: '#dde5e6', wood: '#d9e2e3', ice: '#f4f7f9', urban: '#dfe5ea', building: '#d3dbe1',
          road: '#f4f7f9', casing: '#cdd6dd', rail: '#c2ccd4', border: '#8a9cab', aero: '#d8dfe5',
          label: '#2c3a45', labelSoft: '#5d6d79', waterLabel: '#4d7189', halo: '#e6ebef'},
  eyeDark: {land: '#121a21', water: '#070c11', park: '#131d1f', wood: '#131c1e', ice: '#26313a', urban: '#162029', building: '#1b2630',
          road: '#1f2b35', casing: '#0d1419', rail: '#202c36', border: '#4f6879', aero: '#18222b',
          label: '#b7c8d3', labelSoft: '#7f95a3', waterLabel: '#5f8aa6', halo: '#070c11'},
  // the Outline ground: coasts and borders only
  outline: {land: '#0a1016', water: '#03060a', park: '#0a1016', wood: '#0a1016', ice: '#0d151c', urban: '#0a1016', building: '#0a1016',
          road: '#0a1016', casing: '#0a1016', rail: '#0a1016', border: '#4c7a94', aero: '#0a1016',
          label: '#a9c0cd', labelSoft: '#6f8795', waterLabel: '#4d7189', halo: '#03060a'},
};
// which of the palettes above the vector map uses: 'apple', 'eye' or 'outline' (set by setBase from the look)
let baseMode = 'apple';

export function createMap(container, leftPadding) {
  // MapLibre gives itself few background workers by default (one on a 4-core machine); our many data layers kept a
  // single worker so busy that 3D terrain tiles were never decoded. Use more, leaving a core for the page itself.
  try { maplibregl.setWorkerCount(Math.max(2, Math.min(4, (navigator.hardwareConcurrency || 4) - 1))); } catch (e) { /* engine without it */ }
  const map = new maplibregl.Map({
    container, style: BASE_STYLE, center: [11.575, 28], zoom: 1.7, minZoom: 0.3, maxZoom: 16,
    attributionControl: false, dragRotate: true, pitchWithRotate: true, renderWorldCopies: true,
    fadeDuration: 0,   // no label fade-in: each fade kept the map redrawing for a while after every data update
    pixelRatio: mapPixelRatio(),   // Settings > Map sharpness (look.js)
  });
  document.addEventListener('ww-look', () => { const r = mapPixelRatio(); if (map.getPixelRatio() !== r) map.setPixelRatio(r); });
  dynamicResolution(map);
  map.addControl(new maplibregl.AttributionControl({compact: true}), 'bottom-left');
  // the elevation source exists from the start (terrain is switched on only in 3D): added later, after our many
  // layers, its tiles were requested but never finished loading
  map.once('style.load', () => { globeLod(map); if (!map.getSource('ww-dem')) map.addSource('ww-dem', {type: 'raster-dem', tiles: [DEM], tileSize: 512, encoding: 'terrarium', maxzoom: 12,
    attribution: 'Elevation: © Mapterhorn (CC BY 4.0)'}); });
  // turning and tilting everywhere: right-drag or Ctrl-drag, two-finger twist, or the compass (click: north up again;
  // drag it: turn and tilt)
  map.addControl(new maplibregl.NavigationControl({visualizePitch: true, showZoom: true}), 'bottom-right');
  map.setPadding({left: leftPadding, top: 0, right: 0, bottom: 0});
  return map;
}

let photoLayer = false, groundPhoto = false;   // a photo layer is on / the ground itself is a picture: place names turn white
export function setPhoto(on) { photoLayer = on; }

// ---- where our own pictures sit in the layer stack ----
// Fixed slots, bottom first, all under the base map's place names: the photos (daily, sharp, live: a live photo the
// owner switches on is not hidden by the sharp photo 3D turns on by itself), then the sky and
// weather pictures (night, aurora, rain, lightning), then GPS hexagons, then other area layers (cables, fires). Each
// slot is an invisible marker layer and a layer is always inserted just below its slot's marker, so the order no longer
// depends on which chip was switched on first or when a picture was replaced (before, the photos landed on top of
// night, rain and GPS, and 3D switches the sharp photo on by itself). Markers of ours are added above the place names.
const SLOTS = ['ground', 'photo', 'sharp', 'live', 'night', 'aurora', 'rain', 'lightning', 'gps', 'area'];
export function slot(map, name) {
  if (!map.getLayer('ww-z-area')) {
    const labels = map.getStyle().layers.find(l => l.type === 'symbol' && !l.id.startsWith('ww-'))?.id;
    for (const s of SLOTS) if (!map.getLayer('ww-z-' + s)) map.addLayer({id: 'ww-z-' + s, type: 'background', layout: {visibility: 'none'}, paint: {'background-opacity': 0}}, labels);
  }
  return 'ww-z-' + name;
}

export function paintBase(map, dark) {
  const c = baseMode === 'outline' ? PALETTE.outline : baseMode === 'eye' ? PALETTE[dark ? 'eyeDark' : 'eyeLight'] : PALETTE[dark ? 'dark' : 'light'];
  const onPhoto = PALETTE.dark, photoOn = photoLayer || groundPhoto;   // over the satellite photo, place names use the dark-map colours so they stay readable
  const set = (id, prop, v) => { try { map.setPaintProperty(id, prop, v); } catch (e) { /* layer lacks that property */ } };
  for (const l of map.getStyle().layers) {
    const id = l.id;
    if (id.startsWith('ww-')) continue;                       // our own layers are styled where they are added
    if (l.type === 'background') set(id, 'background-color', c.land);
    else if (l.type === 'fill') {
      const v = /water/.test(id) ? c.water : /park/.test(id) ? c.park : /wood/.test(id) ? c.wood : /ice|glacier/.test(id) ? c.ice
        : /residential/.test(id) ? c.urban : /building/.test(id) ? c.building : /aeroway/.test(id) ? c.aero : /pier/.test(id) ? c.land : null;
      if (v) { set(id, 'fill-color', v); if (/building/.test(id)) set(id, 'fill-outline-color', v); }
    } else if (l.type === 'line') {
      const v = /waterway/.test(id) ? c.water : /boundary/.test(id) ? c.border : /rail/.test(id) ? c.rail : /aeroway/.test(id) ? c.aero
        : /casing/.test(id) ? c.casing : c.road;
      set(id, 'line-color', v);
    } else if (l.type === 'symbol') {
      const water = /water/.test(id), big = /country|state|city/.test(id);
      const k = photoOn ? onPhoto : c;
      set(id, 'text-color', photoOn ? '#ffffff' : water ? k.waterLabel : big ? k.label : k.labelSoft);
      set(id, 'text-halo-color', photoOn ? 'rgba(0,0,0,0.75)' : water ? k.water : k.halo);
      set(id, 'text-halo-width', 1.2);
    } else if (l.type === 'raster') set(id, 'raster-opacity', 0);   // shaded relief does not suit this look
  }
}

// ---- the ground: what lies under everything (Settings > Ground) ----
// Pictures are raster layers in the lowest slot, above the vector map's areas and roads and below its place names.
// All keyless. NASA GIBS (public domain): Blue Marble Next Generation (cloud-free 2004 composite, to zoom 8), Black
// Marble (2016 night composite, to zoom 8), ASTER GDEM shaded relief (to zoom 12). Closer than zoom 8.5 the photo
// grounds switch to Esri World Imagery (each area from its own date), the same pictures as the Sharp photo layer.
const GIBS = 'https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/';
const ESRI = 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}';
const PHOTO = [
  {tiles: GIBS + 'BlueMarble_NextGeneration/default/GoogleMapsCompatible_Level8/{z}/{y}/{x}.jpeg', maxzoom: 8, until: 8.5, attribution: 'Ground: NASA Blue Marble (cloud-free composite)'},
  {tiles: ESRI, maxzoom: 19, from: 8.5, attribution: 'Ground: Esri, Vantor, Earthstar Geographics'}];
const GROUNDS = {
  map: [], outline: [], photo: PHOTO, mono: PHOTO,
  lights: [{tiles: GIBS + 'VIIRS_Black_Marble/default/2016-01-01/GoogleMapsCompatible_Level8/{z}/{y}/{x}.png', maxzoom: 8, attribution: 'Ground: NASA Black Marble (2016 night composite)'}],
  relief: [{tiles: GIBS + 'ASTER_GDEM_Greyscale_Shaded_Relief/default/GoogleMapsCompatible_Level12/{z}/{y}/{x}.jpg', maxzoom: 12, attribution: 'Ground: NASA/METI ASTER GDEM shaded relief'}],
};
let groundNow = null;
// look: {theme, ground}. Returns true when the place names need repainting (photo under them or not).
export function setGround(map, g, theme, dark) {
  baseMode = g === 'outline' ? 'outline' : theme === 'eye' ? 'eye' : 'apple';
  const key = g + '|' + theme + '|' + (dark ? 1 : 0);
  if (key === groundNow) return;
  groundNow = key;
  for (let i = 0; i < 3; i++) {
    if (map.getLayer('ww-ground-' + i)) map.removeLayer('ww-ground-' + i);
    if (map.getSource('ww-ground-' + i)) map.removeSource('ww-ground-' + i);
  }
  if (map.getLayer('ww-ground-tint')) map.removeLayer('ww-ground-tint');
  const parts = GROUNDS[g] || [];
  groundPhoto = parts.length > 0;
  if (map.getLayer('ww-relief')) map.setLayoutProperty('ww-relief', 'visibility', groundPhoto ? 'none' : 'visible');
  const eye = theme === 'eye';
  parts.forEach((p, i) => {
    map.addSource('ww-ground-' + i, {type: 'raster', tiles: [p.tiles], tileSize: 256, maxzoom: p.maxzoom, attribution: p.attribution});
    const paint = {'raster-fade-duration': 0};   // no fade: each fading tile kept the whole map redrawing
    if (g === 'mono') paint['raster-saturation'] = -1;
    // God's eye grades pictures cold and dark so the symbols read on top (the mock-ups' "graded photo")
    // God's eye shows the picture as the first God's eye boards did: true colour, a little darker in dark mode
    if (eye && g === 'photo') Object.assign(paint, {'raster-saturation': -0.1, 'raster-brightness-max': dark ? 0.8 : 1});
    if (eye && g === 'mono') Object.assign(paint, {'raster-brightness-max': dark ? 0.75 : 1, 'raster-contrast': 0.1});
    if (eye && g === 'relief') Object.assign(paint, {'raster-brightness-max': dark ? 0.55 : 1, 'raster-contrast': 0.1});
    if (g === 'lights') Object.assign(paint, {'raster-saturation': eye ? -0.8 : -0.3, 'raster-hue-rotate': eye ? 180 : 0});
    const layer = {id: 'ww-ground-' + i, type: 'raster', source: 'ww-ground-' + i, paint};
    if (p.until) layer.maxzoom = p.until;
    if (p.from) layer.minzoom = p.from;
    map.addLayer(layer, slot(map, 'ground'));
  });
  // the cold cast of the graded photo: a thin blue-grey wash over the picture, under everything of ours
  if (false) map.addLayer({id: 'ww-ground-tint', type: 'background',
    paint: {'background-color': dark ? '#0c2a40' : '#9fc3db', 'background-opacity': dark ? 0.28 : 0.16}}, slot(map, 'ground'));
  return true;
}
export const groundIsPicture = () => groundPhoto;

// On the globe you can zoom out until the geostationary ring (6.6 Earth radii) fits; the flat map stops earlier,
// where the world would otherwise repeat in tiny copies.
// ---- dynamic resolution (as games do): while the map is being moved by hand and frames are slow, draw it with fewer
// pixels; sharp again a moment after it stops. Only in Map sharpness "Balanced" (look.js), only when the last frames
// really took longer than SLOW ms (a fast machine never drops), never while nothing moves, and never for the chase
// camera (it moves the map every frame by itself). Blur in motion is not seen; a stutter is.
const SLOW = 22;
// MapLibre's setPixelRatio() runs resize(), which calls stop() when it thinks the map is not moving: mid-drag that
// ended the drag (measured: a 300 px drag turned the globe 4 degrees instead of 57). The inner step only resizes the
// canvas and drawing buffers (vendored MapLibre 5.24.1; the public call stays as the fallback).
function setRatio(map, r) {
  if (typeof map._resizeInternal !== 'function') return map.setPixelRatio(r);
  map._overridePixelRatio = r; map._resizeInternal(); map.triggerRepaint();
}
function dynamicResolution(map) {
  let gaps = [], last = 0, low = false, back = 0, moving = false;
  const lowRatio = () => Math.max(0.75, mapPixelRatio() * 0.67);   // Retina, Balanced: 1.5 -> 1.0; ordinary screen: 1 -> 0.75
  map.on('movestart', e => { if (!e.originalEvent) return; moving = true; gaps = []; last = 0; clearTimeout(back); });
  map.on('render', () => {
    if (!moving) return;
    const t = performance.now();
    if (last) { gaps.push(t - last); if (gaps.length > 8) gaps.shift(); }
    last = t;
    if (!low && gaps.length >= 6 && look.sharp !== 'full') {
      const sorted = [...gaps].sort((a, b) => a - b);
      if (sorted[3] > SLOW && lowRatio() < map.getPixelRatio()) { low = true; setRatio(map, lowRatio()); }
    }
  });
  map.on('moveend', () => {
    moving = false; last = 0;
    if (low) { clearTimeout(back); back = setTimeout(() => { if (moving) return; low = false; setRatio(map, mapPixelRatio()); }, 250); }
  });
}

// ---- globe level of detail (the trick games use: only as much geometry as the eye can see) ----
// To bend flat tiles round the Earth, MapLibre cuts every line, area, circle and picture tile into small pieces. Its
// defaults are finer than a screen shows: lines in 512 pieces round the world at zoom 0, picture tiles never under
// 32 x 32 cells, each circle 3 x 3. Measured on our default layers: 8.9 million vertex indices a frame on the globe
// against 0.6 million on the flat map. A straight piece covering angle a sags R(1 - cos(a/2)) below the curve; worked
// out per zoom (1-10) the largest sag with these numbers is 0.39 px for lines and pictures (MapLibre's own lines reach
// the same at zoom 8) and 0.78 px for area edges at zoom 3. (base, minimum) = pieces per tile side at zoom 0, halved per
// zoom level, never under the minimum. Set once, before any tile is built.
// The largest part was not the layers at all: on the globe every tile of every source first draws a curved clipping
// mask (stencil) mesh, 6 of the 7 million indices a frame. Mask (64, 8): largest gap at a tile seam 0.78 px at zoom 3
// and under 0.4 px from zoom 4 in; MapLibre's (128, 1) reaches 1.57 px at zoom 6 and 3 px at 7, so closer in this is
// also more exact. Measured on our default layers: 8.9 -> 2.7 million indices a frame.
const GLOBE_LOD = {fill: [64, 8], line: [128, 8], tile: [64, 16], stencil: [64, 8], circle: 1};
let lodDone = false;
export function globeLod(map) {
  if (lodDone) return;
  const g = map.style?.projection?._verticalPerspectiveProjection?.subdivisionGranularity;
  if (!g || !g.fill?.constructor) return;            // another engine version: keep its defaults
  const lod = {...GLOBE_LOD, ...(window.WW_LOD || {})};  // WW_LOD: for measuring other levels from the console
  const Gran = g.fill.constructor;
  for (const k of ['fill', 'line', 'tile', 'stencil']) g[k] = new Gran(lod[k][0], lod[k][1]);
  g.circle = lod.circle;
  lodDone = true;
}

export function setGlobe(map, on) {
  globeLod(map);
  map.setMinZoom(on ? -2 : 0.3);
  map.setProjection({type: on ? 'globe' : 'mercator'});
  globeLod(map);          // the projection object exists only once a projection has been set
  if (on && map.getZoom() < 1.9) map.easeTo({zoom: 1.9, duration: 250});
}

// Colour of the space around the globe.
export function paintSky(map, dark) {
  const eye = baseMode !== 'apple';
  // God's eye: the thin blue rim of atmosphere around the globe when zoomed out (MapLibre's own atmosphere), as in the mock-ups
  try {
    map.setSky(eye ? {'sky-color': dark ? '#000814' : '#cfe0ec', 'horizon-color': dark ? '#1b4a6b' : '#9fc3db', 'fog-color': dark ? '#000814' : '#cfe0ec',
      'sky-horizon-blend': 0.5, 'horizon-fog-blend': 0, 'fog-ground-blend': 1, 'atmosphere-blend': ['interpolate', ['linear'], ['zoom'], 0, 0.45, 5, 0.45, 7, 0]}
      : {'atmosphere-blend': 0});
  } catch (e) { /* older engines */ }
  map.getContainer().style.background = eye ? (dark ? '#010306' : '#dfe6ec') : dark ? '#0e0f11' : '#e9edf2';
}

// ---- 3D: real terrain relief and building heights when zoomed in; tilting and turning allowed while it is on ----
// Elevation: Mapterhorn (terrarium encoding, 512 px webp, keyless, CC BY 4.0; sharper than AWS Terrain Tiles, the
// source God's Eye View falls back to as well). Heights are drawn true (exaggeration 1) so aircraft models at their
// real altitude never sink into exaggerated mountains.
// Buildings: the heights OpenStreetMap mappers entered (OpenFreeMap's "building" layer, render_height).
const DEM = 'https://tiles.mapterhorn.com/{z}/{x}/{y}.webp';
let threeOn = false;
export const is3D = () => threeOn;
export function set3D(map, on, dark) {
  threeOn = on;
  if (on) {
    if (!map.getSource('ww-dem')) map.addSource('ww-dem', {type: 'raster-dem', tiles: [DEM], tileSize: 512, encoding: 'terrarium', maxzoom: 12,
      attribution: 'Elevation: © Mapterhorn (CC BY 4.0)'});
    const firstOwn = map.getStyle().layers.find(l => l.id.startsWith('ww-'))?.id;
    // shading is drawn only over the drawn map: under a picture ground it cannot be seen and only costs
    if (!map.getLayer('ww-relief')) map.addLayer({id: 'ww-relief', type: 'hillshade', source: 'ww-dem', layout: {visibility: groundPhoto ? 'none' : 'visible'}, paint: {'hillshade-exaggeration': 0.35}}, firstOwn);
    if (!map.getLayer('ww-buildings')) {
      const src = Object.entries(map.getStyle().sources).find(([, s]) => s.type === 'vector')?.[0];
      if (src) map.addLayer({id: 'ww-buildings', type: 'fill-extrusion', source: src, 'source-layer': 'building', minzoom: 13,
        paint: {'fill-extrusion-height': ['coalesce', ['get', 'render_height'], 8], 'fill-extrusion-base': ['coalesce', ['get', 'render_min_height'], 0],
          'fill-extrusion-opacity': ['interpolate', ['linear'], ['zoom'], 13, 0, 14, 0.85]}}, firstOwn);
    }
    paint3D(map, dark);
    try { map.setTerrain({source: 'ww-dem', exaggeration: 1}); } catch (e) { /* terrain not available in this projection */ }
    sky3D(map, dark);
    map.setMaxPitch(75);
    if (map.getPitch() < 20) map.easeTo({pitch: map.getZoom() >= 8 ? 60 : 45, duration: 700});
  } else {
    try { map.setTerrain(null); } catch (e) { /* ignore */ }
    for (const id of ['ww-relief', 'ww-buildings']) if (map.getLayer(id)) map.removeLayer(id);
    try { map.setSky({'atmosphere-blend': 0}); } catch (e) { /* older engines */ }
    map.easeTo({pitch: 0, bearing: 0, duration: 600});
  }
}
// a sky and haze towards the horizon, so a tilted view has depth (MapLibre's sky; colours for light and dark)
function sky3D(map, dark) {
  try {
    // no fog over the ground (the owner found the white wash at the top of a tilted view ugly): only a sky above the horizon
    map.setSky(dark ? {'sky-color': '#0b1427', 'horizon-color': '#22324d', 'fog-color': '#0b1427', 'sky-horizon-blend': 0.5, 'horizon-fog-blend': 0, 'fog-ground-blend': 1, 'atmosphere-blend': 0}
      : {'sky-color': '#7fb2e5', 'horizon-color': '#a9cbec', 'fog-color': '#7fb2e5', 'sky-horizon-blend': 0.5, 'horizon-fog-blend': 0, 'fog-ground-blend': 1, 'atmosphere-blend': 0});
  } catch (e) { /* older engines */ }
}
export function paint3D(map, dark) {
  if (threeOn) sky3D(map, dark);
  if (map.getLayer('ww-buildings')) map.setPaintProperty('ww-buildings', 'fill-extrusion-color', dark ? '#3a3b42' : '#e2ddd2');
  if (map.getLayer('ww-relief')) {
    map.setPaintProperty('ww-relief', 'hillshade-shadow-color', dark ? '#000000' : '#6b6456');
    map.setPaintProperty('ww-relief', 'hillshade-highlight-color', dark ? '#4a4c55' : '#ffffff');
    map.setPaintProperty('ww-relief', 'hillshade-accent-color', dark ? '#111214' : '#8a8274');
  }
}
