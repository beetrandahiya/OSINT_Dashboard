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
};

export function createMap(container, leftPadding) {
  const map = new maplibregl.Map({
    container, style: BASE_STYLE, center: [11.575, 28], zoom: 1.7, minZoom: 0.8, maxZoom: 16,
    attributionControl: false, dragRotate: false, pitchWithRotate: false, renderWorldCopies: true,
  });
  map.addControl(new maplibregl.AttributionControl({compact: true}), 'bottom-left');
  map.touchZoomRotate.disableRotation();
  map.setPadding({left: leftPadding, top: 0, right: 0, bottom: 0});
  return map;
}

export function paintBase(map, dark) {
  const c = PALETTE[dark ? 'dark' : 'light'];
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
      set(id, 'text-color', water ? c.waterLabel : big ? c.label : c.labelSoft);
      set(id, 'text-halo-color', water ? c.water : c.halo);
      set(id, 'text-halo-width', 1.2);
    } else if (l.type === 'raster') set(id, 'raster-opacity', 0);   // shaded relief does not suit this look
  }
}

export function setGlobe(map, on) {
  map.setProjection({type: on ? 'globe' : 'mercator'});
  if (on && map.getZoom() < 1.9) map.easeTo({zoom: 1.9, duration: 250});
}

// Colour of the space around the globe.
export function paintSky(map, dark) {
  try { map.setSky({'atmosphere-blend': 0}); } catch (e) { /* older engines */ }
  map.getContainer().style.background = dark ? '#0e0f11' : '#e9edf2';
}
