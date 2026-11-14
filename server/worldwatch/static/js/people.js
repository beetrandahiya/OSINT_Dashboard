// People layer: current heads of state and government at their countries. Click one for a full profile.
// Profiles come from public records (Wikidata, Wikipedia, GDELT, optional OpenSanctions) via our server.
import {ago, esc} from './util.js';
import {openProfile} from './profile.js';

let leaders = [], info = null;
export default {
  id: 'people', title: 'People', color: ['#ff9f0a', '#ffb340'], feeds: {}, layers: ['ww-people', 'ww-people-label'], defaultOff: true, local: true,
  addTo(map) {
    map.addSource('ww-people', {type: 'geojson', data: {type: 'FeatureCollection', features: []}});
    map.addLayer({id: 'ww-people', type: 'circle', source: 'ww-people',
      paint: {'circle-radius': 6, 'circle-opacity': 0.95, 'circle-stroke-width': 1.5}});
    map.addLayer({id: 'ww-people-label', type: 'symbol', source: 'ww-people', minzoom: 2.4,
      layout: {'text-field': ['get', 'name'], 'text-font': ['Noto Sans Bold'], 'text-size': 11, 'text-offset': [0, 1], 'text-anchor': 'top', 'text-optional': true},
      paint: {'text-halo-width': 1.3}});
    this.load(map);
  },
  async load(map) {
    try {
      const r = await fetch('/api/people/leaders', {cache: 'no-store'});
      const d = await r.json();
      if (!d.leaders) return;
      info = d; leaders = d.leaders;
      // several leaders share a country point (a monarch and a prime minister); nudge the second onto a ring
      const at = {};
      const feats = leaders.map(l => {
        const k = l.lon + ',' + l.lat, n = at[k] = (at[k] || 0);  at[k]++;
        const a = n * 2.4, r2 = n ? 0.8 + n * 0.15 : 0;
        return {type: 'Feature', geometry: {type: 'Point', coordinates: [l.lon + Math.cos(a) * r2, l.lat + Math.sin(a) * r2]},
          properties: {qid: l.qid, name: l.name, role: l.role}};
      });
      map.getSource('ww-people').setData({type: 'FeatureCollection', features: feats});
    } catch (e) { /* the chip simply shows nothing */ }
  },
  paint(map, dark) {
    map.setPaintProperty('ww-people', 'circle-color', this.color[+dark]);
    map.setPaintProperty('ww-people', 'circle-stroke-color', dark ? '#1c1c1e' : '#ffffff');
    map.setPaintProperty('ww-people-label', 'text-color', dark ? '#e5e5ea' : '#3a3a3c');
    map.setPaintProperty('ww-people-label', 'text-halo-color', dark ? '#1c1c1e' : '#ffffff');
  },
  onData() {}, render() {},
  count: () => leaders.length,
  rows: () => [],
  locate(id) { const l = leaders.find(x => 'person:' + x.qid === id); return l && [l.lon, l.lat]; },
  ring: () => 11,
  owns: id => String(id).startsWith('person:'),
  about: () => 'Current heads of state and government at their countries, from Wikidata. Click one for a full public-records profile.',
  pick(featureProps) { openProfile(featureProps.qid); return false; },   // handled by the profile overlay, not the normal card
  detail: () => null,
};
