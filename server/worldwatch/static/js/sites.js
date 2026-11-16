// Military bases and nuclear sites from open data (Wikidata, OpenStreetMap, US DoD MIRTA, Global Energy Monitor).
// Static places, refreshed weekly on the server (sites.py). Each card names its source and links to it.
import {ago, esc, spyPass} from './util.js';
import {flagImg} from './flags.js';

let d = null, info = null, areas = [];
const MIL = {air: ['A', 'Air base'], naval: ['N', 'Naval base'], base: ['B', 'Military base'], radar: ['R', 'Military radar'],
  sigint: ['S', 'Listening (signals intelligence) station'], missile: ['M', 'Missile base or launch facility'], space: ['L', 'Launch site'],
  ammo: ['D', 'Ammunition depot'], training: ['T', 'Training area']};
const NUC = {research: 'Research reactor', fuel: 'Fuel-cycle facility (enrichment, reprocessing, conversion, fuel)', mine: 'Uranium mine',
  waste: 'Radioactive waste site', test: 'Nuclear test site', weapons: 'Nuclear weapons facility', facility: 'Nuclear facility'};
const STATUS = {operating: 'operating', construction: 'under construction', 'pre-construction': 'planned (pre-construction)', announced: 'announced',
  mothballed: 'mothballed', retired: 'shut down'};
const SRC = {wikidata: q => `<a class="link" href="https://www.wikidata.org/wiki/${esc(q)}" target="_blank" rel="noopener">Wikidata ${esc(q)}</a>`,
  osm: o => `<a class="link" href="https://www.openstreetmap.org/${esc(o)}" target="_blank" rel="noopener">OpenStreetMap ${esc(o)}</a>`,
  mirta: () => 'US Department of Defense, MIRTA list'};
const look = (lon, lat) => `<button class="btn" data-sharpat="${lon},${lat}">Look at it in the sharp photo</button>`;
const footer = () => `<p class="source">Military sites: Wikidata (CC0), OpenStreetMap (© OpenStreetMap contributors, ODbL; via QLever, about two months behind) and the US Department of Defense's MIRTA list (US and Guam only). Nuclear: Global Energy Monitor's Global Nuclear Power Tracker (CC BY 4.0) and Wikidata. Read ${ago(info?.fetched)}, refreshed weekly. A point can be the town a base is named after rather than its runway. There is no open list of nuclear-weapons storage or production sites, so only those Wikidata or OpenStreetMap name are here.</p>`;

let theMap = null;
function onSites(x) { d = x.payload; info = x; if (theMap) nuclear.render(theMap); }   // one download feeds both layers

export const bases = {
  id: 'bases', title: 'Military bases', color: ['#6e4f2d', '#c8a37a'], feeds: {sites: 21600}, defaultOff: true,
  layers: ['ww-milarea', 'ww-bases', 'ww-bases-k', 'ww-bases-name'],
  visible(on) { if (on) this.pull?.(); },
  about: () => 'Military bases, radar and listening stations, missile and launch sites, from Wikidata, OpenStreetMap and the US DoD.',
  addTo(map) {
    map.addSource('ww-bases', {type: 'geojson', data: {type: 'FeatureCollection', features: []}});
    map.addLayer({id: 'ww-bases', type: 'circle', source: 'ww-bases',
      paint: {'circle-radius': ['interpolate', ['linear'], ['zoom'], 2, ['match', ['get', 'kind'], ['missile', 'sigint'], 3, 1.8], 6, 6, 10, 9], 'circle-stroke-width': ['interpolate', ['linear'], ['zoom'], 3, 0, 6, 1]}});
    map.addLayer({id: 'ww-bases-k', type: 'symbol', source: 'ww-bases', minzoom: 6,
      layout: {'text-field': ['get', 'k'], 'text-font': ['Noto Sans Bold'], 'text-size': 9, 'text-allow-overlap': true, 'text-ignore-placement': true}, paint: {'text-color': '#ffffff'}});
    // OpenStreetMap's military areas (landuse=military): 96,000 worldwide, so only the ones on screen, from zoom 7
    map.addSource('ww-milarea', {type: 'geojson', data: {type: 'FeatureCollection', features: []}});
    map.addLayer({id: 'ww-milarea', type: 'circle', source: 'ww-milarea', minzoom: 7,
      paint: {'circle-radius': ['interpolate', ['linear'], ['zoom'], 7, 3.5, 12, 8], 'circle-opacity': 0.75, 'circle-stroke-width': 1.5, 'circle-stroke-opacity': 1}});
    let busy = false, again = false;
    const pull = async () => {
      if (map.getZoom() < 7 || map.getLayoutProperty('ww-bases', 'visibility') === 'none') return;
      if (busy) { again = true; return; }
      busy = true;
      const b = map.getBounds();
      try {
        const r = await fetch(`/api/sites/areas?w=${b.getWest()}&s=${b.getSouth()}&e=${b.getEast()}&n=${b.getNorth()}`).then(x => x.json());
        areas = r.areas || [];
        map.getSource('ww-milarea').setData({type: 'FeatureCollection', features: areas.map((a, i) => ({type: 'Feature', geometry: {type: 'Point', coordinates: [a[0], a[1]]}, properties: {id: 'marea:' + i}}))});
      } catch (e) { /* the next move asks again */ }
      busy = false;
      if (again) { again = false; pull(); }
    };
    let wait = null; map.on('moveend', () => { clearTimeout(wait); wait = setTimeout(pull, 400); });   // the chase camera moves the map every frame
    this.pull = pull;
    map.addLayer({id: 'ww-bases-name', type: 'symbol', source: 'ww-bases', minzoom: 7.5, filter: ['has', 'name'],
      layout: {'text-field': ['get', 'name'], 'text-font': ['Noto Sans Regular'], 'text-size': 11, 'text-offset': [0, 1.2], 'text-anchor': 'top', 'text-optional': true},
      paint: {'text-halo-width': 1.2}});
  },
  paint(map, dark) {
    map.setPaintProperty('ww-bases', 'circle-color', ['match', ['get', 'kind'], ['missile', 'sigint'], dark ? '#ff6961' : '#c4161c', 'radar', dark ? '#ffb340' : '#b25000', this.color[+dark]]);
    map.setPaintProperty('ww-bases', 'circle-stroke-color', dark ? '#1c1c1e' : '#ffffff');
    map.setPaintProperty('ww-milarea', 'circle-color', this.color[+dark]);
    map.setPaintProperty('ww-milarea', 'circle-stroke-color', dark ? '#1c1c1e' : '#ffffff');   // a white edge stays visible on brown ground
    map.setPaintProperty('ww-bases-name', 'text-color', dark ? '#e5e5ea' : '#3a3a3c');
    map.setPaintProperty('ww-bases-name', 'text-halo-color', dark ? '#1c1c1e' : '#ffffff');
  },
  onData(feed, x) { onSites(x); },
  render(map) {
    if (!d) return;
    map.getSource('ww-bases').setData({type: 'FeatureCollection', features: d.military.map((s, i) => ({type: 'Feature', geometry: {type: 'Point', coordinates: [s[0], s[1]]},
      properties: {id: 'base:' + i, kind: s[2], k: MIL[s[2]]?.[0] || 'B', ...(s[3] ? {name: s[3]} : {})}}))});
  },
  count: () => d ? d.military.length : 0,
  rows: () => [],
  owns: id => /^(base|marea):/.test(String(id)),
  locate(id) {
    if (String(id).startsWith('marea:')) { const a = areas[+id.slice(6)]; return a && [a[0], a[1]]; }
    const s = d?.military[+id.slice(5)]; return s && [s[0], s[1]];
  },
  ring: () => 10,
  detail(id) {
    if (String(id).startsWith('marea:')) {
      const a = areas[+id.slice(6)]; if (!a) return null;
      return `<p class="eyebrow">Military area</p><h2>${esc(a[2] || 'Unnamed military area')}</h2>
        <dl><dt>Where</dt><dd>${Math.abs(a[1]).toFixed(4)}° ${a[1] >= 0 ? 'N' : 'S'}, ${Math.abs(a[0]).toFixed(4)}° ${a[0] >= 0 ? 'E' : 'W'} <span class="soft">(centre of the mapped area)</span></dd>
          <dt>Source</dt><dd>${SRC.osm(a[3])}</dd></dl>
        <p class="soft">Land OpenStreetMap's mappers marked as military use (landuse=military): barracks, cantonments, depots, ranges. Many have no name on the map.</p>
        ${look(a[0], a[1])} ${spyPass(a[1], a[0])}${footer()}`;
    }
    const s = d?.military[+id.slice(5)]; if (!s) return null;
    const [lon, lat, kind, name, src, ref, cc, op, osm] = s;
    return `<p class="eyebrow">${esc(MIL[kind]?.[1] || 'Military site')}</p>
      <h2>${esc(name || 'Unnamed ' + (MIL[kind]?.[1] || 'military site').toLowerCase())}${cc ? ' ' + flagImg(cc) : ''}</h2>
      <dl>
        ${op ? `<dt>Operated by</dt><dd>${esc(op)}</dd>` : ''}
        ${cc ? `<dt>Country</dt><dd>${esc(cc)}</dd>` : ''}
        <dt>Where</dt><dd>${Math.abs(lat).toFixed(4)}° ${lat >= 0 ? 'N' : 'S'}, ${Math.abs(lon).toFixed(4)}° ${lon >= 0 ? 'E' : 'W'}</dd>
        <dt>Source</dt><dd>${SRC[src](ref)}${osm ? ' · ' + SRC.osm(osm) : ''}</dd>
      </dl>
      ${look(lon, lat)} ${spyPass(lat, lon)}
      ${footer()}`;
  },
};

export const nuclear = {
  id: 'nuclear', title: 'Nuclear sites', color: ['#b8860b', '#ffd60a'], feeds: {}, local: true,
  layers: ['ww-nuc-test', 'ww-nuc-boom', 'ww-nuc', 'ww-nuc-k', 'ww-nuc-name'],
  about: () => 'Nuclear power plants, research reactors, fuel-cycle and waste sites, and the nuclear test sites with their explosion points.',
  addTo(map) {
    map.addSource('ww-nuc', {type: 'geojson', data: {type: 'FeatureCollection', features: []}});
    map.addLayer({id: 'ww-nuc-test', type: 'circle', source: 'ww-nuc', filter: ['==', ['get', 'kind'], 'testsite'],
      paint: {'circle-radius': ['interpolate', ['linear'], ['zoom'], 2, 7, 8, 26], 'circle-opacity': 0.12, 'circle-stroke-width': 1.5}});
    map.addLayer({id: 'ww-nuc-boom', type: 'circle', source: 'ww-nuc', minzoom: 5, filter: ['==', ['get', 'kind'], 'explosion'],
      paint: {'circle-radius': ['interpolate', ['linear'], ['zoom'], 5, 1.2, 10, 3.5], 'circle-opacity': 0.75}});
    map.addLayer({id: 'ww-nuc', type: 'circle', source: 'ww-nuc', filter: ['!', ['in', ['get', 'kind'], ['literal', ['testsite', 'explosion']]]],
      paint: {'circle-radius': ['interpolate', ['linear'], ['zoom'], 2, ['match', ['get', 'kind'], 'plant', 3.2, 2.4], 7, 8], 'circle-stroke-width': 1,
        'circle-opacity': ['match', ['get', 'status'], 'operating', 1, 'construction', 0.9, 0.5]}});
    map.addLayer({id: 'ww-nuc-k', type: 'symbol', source: 'ww-nuc', minzoom: 5, filter: ['!', ['in', ['get', 'kind'], ['literal', ['testsite', 'explosion']]]],
      layout: {'text-field': '☢', 'text-font': ['Noto Sans Bold'], 'text-size': 10, 'text-allow-overlap': true, 'text-ignore-placement': true}, paint: {'text-color': '#1c1c1e'}});
    map.addLayer({id: 'ww-nuc-name', type: 'symbol', source: 'ww-nuc', filter: ['any', ['==', ['get', 'kind'], 'testsite'], ['>=', ['zoom'], 7]],
      layout: {'text-field': ['get', 'name'], 'text-font': ['Noto Sans Bold'], 'text-size': 11, 'text-offset': [0, 1.4], 'text-anchor': 'top', 'text-optional': true},
      paint: {'text-halo-width': 1.3}});
    theMap = map; this.render(map);
  },
  paint(map, dark) {
    const c = this.color[+dark];
    map.setPaintProperty('ww-nuc', 'circle-color', ['match', ['get', 'kind'], 'plant', c, dark ? '#ff9f0a' : '#c93400']);
    map.setPaintProperty('ww-nuc', 'circle-stroke-color', dark ? '#1c1c1e' : '#ffffff');
    map.setPaintProperty('ww-nuc-test', 'circle-color', dark ? '#ff6961' : '#d70015');
    map.setPaintProperty('ww-nuc-test', 'circle-stroke-color', dark ? '#ff6961' : '#d70015');
    map.setPaintProperty('ww-nuc-boom', 'circle-color', dark ? '#ff6961' : '#d70015');
    map.setPaintProperty('ww-nuc-name', 'text-color', dark ? '#e5e5ea' : '#3a3a3c');
    map.setPaintProperty('ww-nuc-name', 'text-halo-color', dark ? '#1c1c1e' : '#ffffff');
  },
  onData(feed, x) { onSites(x); },
  render(map) {
    if (!d) return;
    const f = [];
    d.plants.forEach((p, i) => f.push({type: 'Feature', geometry: {type: 'Point', coordinates: [p.lon, p.lat]}, properties: {id: 'nuc:p' + i, kind: 'plant', status: p.status, name: p.name}}));
    d.facilities.forEach((p, i) => f.push({type: 'Feature', geometry: {type: 'Point', coordinates: [p.lon, p.lat]}, properties: {id: 'nuc:f' + i, kind: p.kind, status: 'operating', name: p.name}}));
    d.tests.forEach((t, i) => f.push({type: 'Feature', geometry: {type: 'Point', coordinates: [t.lon, t.lat]}, properties: {id: 'nuc:t' + i, kind: 'testsite', name: t.name}}));
    d.explosions.forEach((e, i) => f.push({type: 'Feature', geometry: {type: 'Point', coordinates: [e[0], e[1]]}, properties: {id: 'nuc:e' + i, kind: 'explosion'}}));
    map.getSource('ww-nuc').setData({type: 'FeatureCollection', features: f});
  },
  count: () => d ? d.plants.length + d.facilities.length + d.tests.length : 0,
  rows: () => [],
  owns: id => String(id).startsWith('nuc:'),
  locate(id) {
    if (!d) return null;
    const k = id[4], n = +id.slice(5), x = {p: d.plants, f: d.facilities, t: d.tests, e: d.explosions}[k]?.[n];
    return x && (Array.isArray(x) ? [x[0], x[1]] : [x.lon, x.lat]);
  },
  ring: id => id[4] === 't' ? 22 : 10,
  detail(id) {
    if (!d) return null;
    const k = id[4], n = +id.slice(5);
    if (k === 'p') {
      const p = d.plants[n]; if (!p) return null;
      const units = Object.entries(p.units).map(([s, c]) => `${c} ${STATUS[s] || s}${p.mw[s] ? ` <span class="soft">(${Math.round(p.mw[s]).toLocaleString('en-GB')} MW)</span>` : ''}`).join(', ');
      return `<p class="eyebrow">Nuclear power plant · ${esc(STATUS[p.status] || p.status)}</p><h2>${esc(p.name)}</h2><p class="where">${esc(p.country || '')}</p>
        <dl><dt>Reactors</dt><dd>${units}</dd>
          ${p.types.length ? `<dt>Type</dt><dd>${p.types.map(esc).join(', ')}</dd>` : ''}
          ${p.operator ? `<dt>Operator</dt><dd>${esc(p.operator)}</dd>` : ''}${p.owner ? `<dt>Owner</dt><dd>${esc(p.owner)}</dd>` : ''}
          <dt>Location</dt><dd>${p.exact ? 'exact' : 'approximate (as Global Energy Monitor marks it)'}</dd></dl>
        ${(p.reactors || []).length ? `<section class="pz"><h3>Reactors</h3><table class="units"><tr><th>Unit</th><th>Status</th><th>MW</th><th>Construction</th><th>Grid</th><th>Commercial</th><th>Retired</th></tr>
          ${p.reactors.map(r => `<tr><td>${esc(r.unit || '–')}${r.datacenter_ppa === 'Y' ? ' <span class="pill" title="Has a power purchase agreement with a data centre">data centre</span>' : ''}</td><td>${esc(STATUS[r.status] || r.status)}</td><td>${r.mw ? Math.round(r.mw).toLocaleString('en-GB') : '–'}</td>
            <td>${esc((r.construction || '–').slice(0, 7))}</td><td>${esc((r.grid || '–').slice(0, 7))}</td><td>${esc((r.commercial || '–').slice(0, 7))}</td>
            <td>${esc((r.retired || r.retired_year || (r.planned_retirement ? 'planned ' + r.planned_retirement : '') || (r.cancelled_year ? 'cancelled ' + r.cancelled_year : '') || '–').slice(0, 16))}</td></tr>`).join('')}</table>
          <p class="source">Dates per reactor from Global Energy Monitor's spreadsheet (${esc(d.dates_from || '')}); a dash means none recorded.</p></section>` : ''}
        ${look(p.lon, p.lat)} ${spyPass(p.lat, p.lon)}
        ${p.url ? `<a class="link" href="${esc(p.url)}" target="_blank" rel="noopener">Global Energy Monitor wiki</a>` : ''}${footer()}`;
    }
    if (k === 'f') {
      const p = d.facilities[n]; if (!p) return null;
      return `<p class="eyebrow">${esc(NUC[p.kind] || 'Nuclear facility')}</p><h2>${esc(p.name)}${p.country ? ' ' + flagImg(p.country) : ''}</h2>
        <dl><dt>Recorded as</dt><dd>${esc(p.types)}</dd>${p.operator ? `<dt>Operator</dt><dd>${esc(p.operator)}</dd>` : ''}
          <dt>Source</dt><dd>${SRC.wikidata(p.qid)}</dd></dl>${look(p.lon, p.lat)} ${spyPass(p.lat, p.lon)}${footer()}`;
    }
    if (k === 't' || k === 'e') {
      const t = k === 't' ? d.tests[n] : d.tests.find(x => x.qid === d.explosions[n]?.[4]);
      const e = k === 'e' ? d.explosions[n] : null;
      if (!t) return null;
      return `<p class="eyebrow">${e ? 'Nuclear explosion point' : 'Nuclear test site'}</p><h2>${esc(e?.[2] || t.name)}</h2>
        <p class="where">${e ? esc(t.name) + ' · ' : ''}tested by ${esc(t.by)}</p>
        <dl>${!e ? `<dt>Explosion points mapped</dt><dd>${t.explosions} <span class="soft">(OpenStreetMap; zoom in to see them)</span></dd>` : `<dt>Source</dt><dd>${SRC.osm(e[3])}</dd>`}
          <dt>Site</dt><dd>${SRC.wikidata(t.qid)}${t.from_osm ? ' <span class="soft">(Wikidata has no point for it: placed at the centre of OpenStreetMap\'s explosion points)</span>' : ''}</dd></dl>
        <p class="soft">Earthquakes near a test site are flagged on the earthquake layer; a quake there is not a test, and seismologists tell them apart by depth and wave shape.</p>
        ${look(e ? e[0] : t.lon, e ? e[1] : t.lat)} ${spyPass(e ? e[1] : t.lat, e ? e[0] : t.lon)}${footer()}`;
    }
    return null;
  },
};

// for the earthquake layer: the nearest test site within a distance
export function nearTestSite(lon, lat, maxKm = 50) {
  if (!d) return null;
  let best = null;
  for (const t of d.tests) {
    const p1 = lat * Math.PI / 180, p2 = t.lat * Math.PI / 180;
    const a = Math.sin((p2 - p1) / 2) ** 2 + Math.cos(p1) * Math.cos(p2) * Math.sin((t.lon - lon) * Math.PI / 360) ** 2;
    const k = 12742 * Math.asin(Math.min(1, Math.sqrt(a)));
    if (k <= maxKm && (!best || k < best.km)) best = {...t, km: Math.round(k)};
  }
  return best;
}
