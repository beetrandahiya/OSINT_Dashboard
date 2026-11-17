// Hotspots: places where at least three different kinds of security signal coincide within a day (hotspots.py).
// A pulsing ring on the map; the card lists every signal behind it, each with its source and a way to show it.
import {ago, esc, local, countryBtn, spyPass} from './util.js';

let d = {hotspots: [], families: {}}, theMap = null, on = true, at = 0, pulses = [];
const place = h => {
  const s = h.signals.find(x => x.fam === 'unrest' || x.fam === 'spike') || h.signals[0];
  const m = s?.title.match(/ in ([^,:]+)/);
  return m ? m[1] : `${h.lat.toFixed(1)}°, ${h.lon.toFixed(1)}°`;
};
// The pulse is a small page element per hotspot with a CSS animation (.hot-pulse in app.css), placed by a map marker:
// the browser animates it on its own, so the map is not redrawn 60 times a second for it (setting a paint property
// every frame did that, forever, while the layer was on). Off under Reduce Motion (CSS) and while the layer is off.
function pulse() {
  for (const m of pulses) m.remove();
  pulses = [];
  if (!theMap || !on) return;
  for (const h of d.hotspots) {
    const el = document.createElement('div');
    el.className = 'hot-pulse';
    pulses.push(new maplibregl.Marker({element: el, anchor: 'center', opacityWhenCovered: '0'}).setLngLat([h.lon, h.lat]).addTo(theMap));
  }
}
async function load() {
  try { d = await fetch('/api/hotspots').then(r => r.json()); at = Date.now() / 1000; } catch (e) { return; }
  hotspots.render(theMap);
  document.dispatchEvent(new Event('ww-chips'));
}

// ids come from the server (the oldest signal), so a 5-minute reload that reorders the list never swaps an open card
const hid = (h, i) => h.id || 'hot:' + i, get = id => d.hotspots.find((h, i) => hid(h, i) === id);

const hotspots = {
  id: 'hotspots', title: 'Hotspots', color: ['#ff2d55', '#ff375f'], feeds: {}, local: true,
  about: () => 'Places where three or more different kinds of security signal coincide within a day. Each signal is listed; no score.',
  addTo(map) {
    theMap = map;
    map.addSource('ww-hot', {type: 'geojson', data: {type: 'FeatureCollection', features: []}});
    map.addLayer({id: 'ww-hot-area', type: 'circle', source: 'ww-hot',
      paint: {'circle-radius': ['interpolate', ['exponential', 2], ['zoom'], 0, ['*', ['get', 'r0'], 1], 20, ['*', ['get', 'r0'], 1048576]], 'circle-opacity': 0.08, 'circle-stroke-width': 1, 'circle-stroke-opacity': 0.5}});
    map.addLayer({id: 'ww-hot', type: 'circle', source: 'ww-hot', paint: {'circle-radius': 11, 'circle-stroke-width': 2}});
    map.addLayer({id: 'ww-hot-label', type: 'symbol', source: 'ww-hot',
      layout: {'text-field': ['to-string', ['get', 'kinds']], 'text-font': ['Noto Sans Bold'], 'text-size': 12, 'text-allow-overlap': true, 'text-ignore-placement': true}, paint: {'text-color': '#ffffff'}});
    load(); setInterval(load, 5 * 60 * 1000);
  },
  layers: ['ww-hot-area', 'ww-hot', 'ww-hot-label'],
  visible(v) { on = v; pulse(); },
  paint(map, dark) {
    const c = this.color[+dark];
    for (const [id, p] of [['ww-hot', 'circle-color'], ['ww-hot-area', 'circle-color'], ['ww-hot-area', 'circle-stroke-color']]) map.setPaintProperty(id, p, c);
    map.getContainer().style.setProperty('--hot', c);
    map.setPaintProperty('ww-hot', 'circle-stroke-color', dark ? '#1c1c1e' : '#ffffff');
  },
  onData() {},
  render(map = theMap) {
    if (!map?.getSource('ww-hot')) return;
    // r0: the 250 km radius in pixels at zoom 0 (512 px world), so the area ring is true to scale at any zoom
    map.getSource('ww-hot').setData({type: 'FeatureCollection', features: d.hotspots.map((h, i) => ({type: 'Feature', geometry: {type: 'Point', coordinates: [h.lon, h.lat]},
      properties: {id: hid(h, i), kinds: h.kinds, r0: d.radius_km / (40075 * Math.cos(h.lat * Math.PI / 180)) * 512}}))});
    pulse();
  },
  count: () => d.hotspots.length,
  rows: () => d.hotspots.map((h, i) => ({id: hid(h, i), time: h.last, badge: String(h.kinds), strong: true,
    title: `Hotspot: ${place(h)} · ${h.families.map(f => (d.families[f] || f).split(' (')[0].toLowerCase()).join(', ')}`,
    meta: `${h.signals.length} signals within ${d.radius_km} km · ${ago(h.last)}`})),
  owns: id => String(id).startsWith('hot:'),
  locate(id) { const h = get(id); return h && [h.lon, h.lat]; },
  ring: () => 16,
  detail(id) {
    const h = get(id); if (!h) return null;
    const by = {};
    for (const s of h.signals) (by[s.fam] ||= []).push(s);
    return `<p class="eyebrow">Hotspot · ${h.kinds} kinds of signal</p><h2>${esc(place(h))}</h2>
      <p class="where">Within ${d.radius_km} km, last ${d.window_h} hours · newest ${ago(h.last)}</p>
      ${Object.entries(by).map(([fam, list]) => `<section class="pz"><h3>${esc(d.families[fam] || fam)}${h.context.includes(fam) ? ' <span class="soft">(context, not counted)</span>' : ''}</h3>
        <ul class="pz-list">${list.slice(0, 8).map(s => `<li><a href="#" data-hotpick="${esc(JSON.stringify({layer: s.layer, id: s.id, lon: s.lon, lat: s.lat}))}">${esc(s.title)}</a>${s.time ? ` <span class="soft">· ${ago(s.time)}</span>` : ''}</li>`).join('')}${list.length > 8 ? `<li class="soft">and ${list.length - 8} more</li>` : ''}</ul></section>`).join('')}
      ${h.country ? countryBtn({cc: h.country}) : ''}
      ${spyPass(h.lat, h.lon)}
      <p class="source">Worked out by World Watch from the layers' own sources: a hotspot is three or more different kinds of security signal within ${d.radius_km} km in a day, at least two tied to a place; earthquakes and disasters are shown as context only, and a country-wide outage counts only inside that country. Being near each other does not prove the signals are connected: open each one. Checked ${ago(at)}.</p>`;
  },
};
document.addEventListener('click', e => {
  const a = e.target.closest('[data-hotpick]'); if (!a) return;
  e.preventDefault();
  window.dispatchEvent(new CustomEvent('ww-try-pick', {detail: JSON.parse(a.dataset.hotpick)}));
});
export default hotspots;
