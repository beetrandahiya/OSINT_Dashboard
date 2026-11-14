// Earthquakes, exactly as the USGS feed lists them. Circle size follows magnitude; nothing else is implied.
import {ago, esc, local, utc} from './util.js';

const SRC = 'ww-quakes';
const LIST_MIN_MAG = 2.5;   // the list shows these; the map shows every quake in the feed

export const feed = 'quakes';

export function addTo(map, onPick) {
  map.addSource(SRC, {type: 'geojson', data: {type: 'FeatureCollection', features: []}, promoteId: 'id'});
  const size = ['interpolate', ['linear'], ['coalesce', ['get', 'mag'], 0], 0, 2.5, 3, 4, 4.5, 9, 6, 13, 7, 18, 8, 25];
  map.addLayer({id: 'ww-quakes-ring', type: 'circle', source: SRC,
    paint: {'circle-radius': ['+', size, 5], 'circle-color': 'transparent', 'circle-stroke-width': 2,
            'circle-stroke-opacity': ['case', ['boolean', ['feature-state', 'picked'], false], 1, 0]}});
  map.addLayer({id: 'ww-quakes', type: 'circle', source: SRC,
    paint: {'circle-radius': size, 'circle-opacity': 0.88, 'circle-stroke-width': 1.2}});
  // Apple's map guidance allows a short label inside a marker; the stronger quakes carry their magnitude.
  map.addLayer({id: 'ww-quakes-label', type: 'symbol', source: SRC, filter: ['>=', ['coalesce', ['get', 'mag'], 0], 4.5],
    layout: {'text-field': ['number-format', ['get', 'mag'], {'min-fraction-digits': 1, 'max-fraction-digits': 1}],
             'text-font': ['Noto Sans Bold'], 'text-size': ['interpolate', ['linear'], ['get', 'mag'], 4.5, 9, 7, 12],
             'text-allow-overlap': true, 'text-ignore-placement': true},
    paint: {'text-color': '#ffffff'}});
  map.on('click', 'ww-quakes', e => onPick(e.features[0].properties.id));
  map.on('mouseenter', 'ww-quakes', () => { map.getCanvas().style.cursor = 'pointer'; });
  map.on('mouseleave', 'ww-quakes', () => { map.getCanvas().style.cursor = ''; });
}

export function paint(map, dark) {
  const c = dark ? '#ff9f0a' : '#ff9500', edge = dark ? '#1c1c1e' : '#ffffff';
  map.setPaintProperty('ww-quakes', 'circle-color', c);
  map.setPaintProperty('ww-quakes', 'circle-stroke-color', edge);
  map.setPaintProperty('ww-quakes-ring', 'circle-stroke-color', c);
}

export function setData(map, quakes) {
  map.getSource(SRC).setData({type: 'FeatureCollection', features: quakes.map(q => (
    {type: 'Feature', id: q.id, geometry: {type: 'Point', coordinates: [q.lon, q.lat]}, properties: {id: q.id, mag: q.mag}}))});
}

let picked = null;
export function mark(map, id) {
  if (picked) map.setFeatureState({source: SRC, id: picked}, {picked: false});
  picked = id;
  if (id) map.setFeatureState({source: SRC, id}, {picked: true});
}

const mag = q => q.mag == null ? '?' : q.mag.toFixed(1);

export function rows(quakes) {
  return quakes.filter(q => (q.mag ?? 0) >= LIST_MIN_MAG).sort((a, b) => b.time - a.time).map(q => ({
    id: q.id, time: q.time,
    badge: mag(q), strong: (q.mag ?? 0) >= 5,
    title: q.place || 'Unnamed location',
    meta: `${local(q.time)} · ${ago(q.time)} · ${Math.round(q.depth_km)} km deep`,
  }));
}
export const listNote = n => `${n} of magnitude ${LIST_MIN_MAG}+ in 24 hours`;

export function detail(q, f) {
  return `<p class="eyebrow">Earthquake</p>
    <h2>Magnitude ${mag(q)}</h2>
    <p class="where">${esc(q.place || 'Unnamed location')}</p>
    <dl>
      <dt>Time</dt><dd>${local(q.time)} <span class="soft">(${utc(q.time)}, ${ago(q.time)})</span></dd>
      <dt>Depth</dt><dd>${q.depth_km.toFixed(1)} km</dd>
      <dt>Position</dt><dd>${Math.abs(q.lat).toFixed(3)}° ${q.lat >= 0 ? 'N' : 'S'}, ${Math.abs(q.lon).toFixed(3)}° ${q.lon >= 0 ? 'E' : 'W'}</dd>
      <dt>Last revised</dt><dd>${local(q.updated)} <span class="soft">(${ago(q.updated)})</span></dd>
    </dl>
    <a class="link" href="${esc(q.url)}" target="_blank" rel="noopener">Open the USGS event page</a>
    <p class="source">Source: USGS. Their feed was generated at ${utc(f.data_time)}; we fetched it ${ago(f.fetched)}.</p>`;
}
