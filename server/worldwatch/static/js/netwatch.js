// Internet routing incidents from Cloudflare Radar: BGP hijacks (a network announcing address blocks that belong to
// another) and route leaks, last 24 hours. Networks have no position: lines join the countries Cloudflare gives for
// the networks, drawn between country centres. See radar.py.
import {ago, esc, local, countryBtn} from './util.js';
import {flagImg} from './flags.js';

let d = {hijacks: [], leaks: []}, info = null, theMap = null, raf = 0, on = true, flows = [];

// Points along the great circle between two [lon, lat] points, longitudes kept continuous across the antimeridian
function arc(a, b, n = 48) {
  const R = Math.PI / 180, [l1, p1, l2, p2] = [a[0] * R, a[1] * R, b[0] * R, b[1] * R];
  const dd = 2 * Math.asin(Math.sqrt(Math.sin((p2 - p1) / 2) ** 2 + Math.cos(p1) * Math.cos(p2) * Math.sin((l2 - l1) / 2) ** 2));
  if (dd < 1e-6) return [a, b];
  const out = [];
  for (let i = 0; i <= n; i++) {
    const f = i / n, A = Math.sin((1 - f) * dd) / Math.sin(dd), B = Math.sin(f * dd) / Math.sin(dd);
    const x = A * Math.cos(p1) * Math.cos(l1) + B * Math.cos(p2) * Math.cos(l2), y = A * Math.cos(p1) * Math.sin(l1) + B * Math.cos(p2) * Math.sin(l2), z = A * Math.sin(p1) + B * Math.sin(p2);
    let lon = Math.atan2(y, x) / R; const lat = Math.atan2(z, Math.hypot(x, y)) / R;
    if (out.length) { const prev = out[out.length - 1][0]; while (lon - prev > 180) lon -= 360; while (lon - prev < -180) lon += 360; }
    out.push([lon, lat]);
  }
  return out;
}
const slice = (pts, a, b) => { const n = pts.length - 1, i0 = Math.max(0, Math.floor(a * n)), i1 = Math.min(n, Math.ceil(b * n)); return pts.slice(i0, i1 + 1); };

// The streaks: one per event, travelling source -> target and pulsing on arrival, each on its own phase
function animate(t) {
  raf = 0;
  if (!theMap || !on || !flows.length) return;
  const tails = [], heads = [];
  for (const fl of flows) {
    const p = ((t / fl.period) + fl.phase) % 1;                // 0..1 along the arc, then a short rest at the target
    const head = Math.min(1, p / 0.8);
    if (p < 0.8) {
      const seg = slice(fl.pts, Math.max(0, head - 0.25), head);
      if (seg.length > 1) tails.push({type: 'Feature', geometry: {type: 'LineString', coordinates: seg}, properties: {kind: fl.kind, strong: fl.strong}});
      heads.push({type: 'Feature', geometry: {type: 'Point', coordinates: seg[seg.length - 1]}, properties: {kind: fl.kind, strong: fl.strong, pulse: 0}});
    } else {
      heads.push({type: 'Feature', geometry: {type: 'Point', coordinates: fl.pts[fl.pts.length - 1]}, properties: {kind: fl.kind, strong: fl.strong, pulse: (p - 0.8) / 0.2}});
    }
  }
  theMap.getSource('ww-bgp-tail')?.setData({type: 'FeatureCollection', features: tails});
  theMap.getSource('ww-bgp-head')?.setData({type: 'FeatureCollection', features: heads});
  raf = requestAnimationFrame(animate);
}
const reduce = matchMedia('(prefers-reduced-motion: reduce)');
const LIST_MIN = 10;
const net = n => `${esc(n.org || 'unknown network')} <span class="soft">(AS${n.asn}${n.cc ? ', ' + esc(n.cc) : ''})</span>`;
const strong = h => (h.score ?? 0) >= LIST_MIN;

export default {
  id: 'hijacks', title: 'Internet hijacks', color: ['#d70015', '#ff6961'], feeds: {cf_radar: 600},
  layers: ['ww-bgp-leak', 'ww-bgp-line', 'ww-bgp-dot'],
  about: () => 'BGP hijacks and route leaks of the last 24 hours, from Cloudflare Radar.',
  addTo(map) {
    map.addSource('ww-bgp', {type: 'geojson', data: {type: 'FeatureCollection', features: []}});
    map.addLayer({id: 'ww-bgp-leak', type: 'line', source: 'ww-bgp', filter: ['==', ['get', 'kind'], 'leak'],
      paint: {'line-width': 0.8, 'line-opacity': 0.2, 'line-dasharray': [2, 3]}});
    map.addLayer({id: 'ww-bgp-line', type: 'line', source: 'ww-bgp', filter: ['==', ['get', 'kind'], 'hijack'],
      paint: {'line-width': ['case', ['get', 'strong'], 1.2, 0.8], 'line-opacity': ['case', ['get', 'strong'], 0.35, 0.15]}});
    map.addLayer({id: 'ww-bgp-dot', type: 'circle', source: 'ww-bgp', filter: ['==', ['geometry-type'], 'Point'],
      paint: {'circle-radius': ['case', ['get', 'strong'], 6, 3.5], 'circle-stroke-width': 1.2, 'circle-opacity': ['case', ['get', 'strong'], 1, 0.6]}});
    // the moving streaks (comet tails fade along each segment: line-progress needs lineMetrics) and their heads
    map.addSource('ww-bgp-tail', {type: 'geojson', lineMetrics: true, data: {type: 'FeatureCollection', features: []}});
    map.addSource('ww-bgp-head', {type: 'geojson', data: {type: 'FeatureCollection', features: []}});
    map.addLayer({id: 'ww-bgp-tail', type: 'line', source: 'ww-bgp-tail', layout: {'line-cap': 'round'},
      paint: {'line-width': ['case', ['get', 'strong'], 3, 1.6]}});
    map.addLayer({id: 'ww-bgp-head', type: 'circle', source: 'ww-bgp-head',
      paint: {'circle-radius': ['+', ['case', ['get', 'strong'], 3.5, 2], ['*', ['get', 'pulse'], 14]], 'circle-blur': 0.6,
        'circle-opacity': ['-', 1, ['get', 'pulse']], 'circle-stroke-width': 0}});
    theMap = map;
  },
  visible(v) { on = v; for (const id of ['ww-bgp-tail', 'ww-bgp-head']) theMap?.getLayer(id) && theMap.setLayoutProperty(id, 'visibility', v ? 'visible' : 'none'); if (v && !raf && !reduce.matches) raf = requestAnimationFrame(animate); },
  paint(map, dark) {
    const c = this.color[+dark], soft = dark ? '#aeaeb2' : '#8e8e93';
    map.setPaintProperty('ww-bgp-line', 'line-color', ['case', ['get', 'strong'], c, soft]);
    map.setPaintProperty('ww-bgp-leak', 'line-color', dark ? '#64d2ff' : '#0071a4');
    map.setPaintProperty('ww-bgp-dot', 'circle-color', ['case', ['get', 'strong'], c, soft]);
    map.setPaintProperty('ww-bgp-dot', 'circle-stroke-color', dark ? '#1c1c1e' : '#ffffff');
    const leak = dark ? '#64d2ff' : '#0071a4', weak = dark ? '#ff9f0a' : '#c93400';
    const col = ['case', ['==', ['get', 'kind'], 'leak'], leak, ['get', 'strong'], c, weak];
    map.setPaintProperty('ww-bgp-head', 'circle-color', col);
    // each tail fades from transparent at its back to full colour at the head (line-progress runs 0..1 along a segment)
    const grad = rgb => ['interpolate', ['linear'], ['line-progress'], 0, `rgba(${rgb},0)`, 1, `rgba(${rgb},0.95)`];
    const hex2 = h => [1, 3, 5].map(i => parseInt(h.slice(i, i + 2), 16)).join(',');
    map.setPaintProperty('ww-bgp-tail', 'line-gradient', grad(hex2(c)));     // gradients cannot depend on data: one colour, hijack red
  },
  onData(feed, x) { d = x.payload; info = x; },
  render(map = theMap) {
    if (!map) return;
    const f = [];
    for (const h of d.hijacks) {
      const a = h.hijacker.at; if (!a) continue;
      const props = {id: 'bgp:' + h.id, kind: 'hijack', strong: strong(h)};
      for (const v of h.victim_countries) if (v.at && v.cc !== h.hijacker.cc) f.push({type: 'Feature', geometry: {type: 'LineString', coordinates: arc(a, v.at)}, properties: props});
      f.push({type: 'Feature', geometry: {type: 'Point', coordinates: a}, properties: props});
    }
    for (const l of d.leaks) {
      const pts = l.countries.map(c => c.at).filter(Boolean);
      for (let i = 0; i + 1 < pts.length; i++) f.push({type: 'Feature', geometry: {type: 'LineString', coordinates: arc(pts[i], pts[i + 1])}, properties: {id: 'leak:' + l.id, kind: 'leak'}});
    }
    map.getSource('ww-bgp').setData({type: 'FeatureCollection', features: f});
    // one streak per event with distinct ends: strong hijacks, then weak ones, then leaks (at most 120 moving at once)
    flows = [];
    let k = 0;
    for (const h of [...d.hijacks].sort((a, b) => strong(b) - strong(a))) {
      for (const v of h.victim_countries) if (h.hijacker.at && v.at && v.cc !== h.hijacker.cc && flows.length < 120)
        flows.push({pts: arc(h.hijacker.at, v.at), kind: 'hijack', strong: strong(h), period: 2600 + (k * 397) % 1900, phase: (k++ * 0.618) % 1});
    }
    for (const l of d.leaks) {
      const pts = l.countries.map(c => c.at).filter(Boolean);
      for (let i = 0; i + 1 < pts.length && flows.length < 120; i++) flows.push({pts: arc(pts[i], pts[i + 1]), kind: 'leak', strong: false, period: 3400 + (k * 271) % 1700, phase: (k++ * 0.618) % 1});
    }
    if (!raf && on && !reduce.matches) raf = requestAnimationFrame(animate);
  },
  count: () => d.hijacks.filter(strong).length,
  rows: () => d.hijacks.filter(strong).map(h => ({id: 'bgp:' + h.id, time: h.start, badge: '⇄', strong: (h.score ?? 0) >= 12,
    title: `${h.hijacker.org || 'AS' + h.hijacker.asn} announced ${h.prefix_count} address ${h.prefix_count === 1 ? 'block' : 'blocks'} of ${h.victims.map(v => v.org || 'AS' + v.asn).join(', ')}`,
    meta: `Possible hijack · ${h.hijacker.cc || '?'} → ${h.victim_countries.map(v => v.cc).join(', ') || '?'} · score ${h.score} · ${ago(h.start)}`})),
  owns: id => /^(bgp|leak):/.test(String(id)),
  locate(id) {
    if (String(id).startsWith('leak:')) return d.leaks.find(x => 'leak:' + x.id === id)?.countries.find(c => c.at)?.at || null;
    return d.hijacks.find(x => 'bgp:' + x.id === id)?.hijacker.at || null;
  },
  ring: () => 12,
  detail(id) {
    const src = `<p class="source">Source: Cloudflare Radar (CC BY-NC 4.0), read ${ago(info?.fetched)}. Detected from routing announcements Cloudflare's collectors saw; a "hijack" here means the announcement looks wrong, which also happens by mistake or when a customer's provider announces for it. Lines join the countries Cloudflare lists for the networks, drawn between country centres; networks have no single place. The moving streaks only show the direction of each event (from the announcing network's country to the victim's); they are not live traffic.</p>`;
    if (String(id).startsWith('leak:')) {
      const l = d.leaks.find(x => 'leak:' + x.id === id); if (!l) return null;
      return `<p class="eyebrow">Route leak</p><h2>${esc(l.leaker.org || 'AS' + l.leaker.asn)}</h2>
        <p class="where">passed on routes it should not have, ${l.finished ? 'finished' : 'still going'}</p>
        <dl><dt>Path</dt><dd>${l.path.map(net).join(' → ')}</dd><dt>Countries</dt><dd>${l.countries.map(c => flagImg(c.cc) + ' ' + esc(c.cc)).join(' · ')}</dd>
          <dt>Address blocks</dt><dd>${l.prefixes}</dd><dt>Seen</dt><dd>${local(l.start)}${l.last && l.last !== l.start ? ' to ' + local(l.last) : ''}</dd></dl>
        <p class="soft">A leak sends other networks' traffic the wrong way, usually by mistake. Over 400 happen on a normal day; only the 40 involving the most address blocks across a border are drawn.</p>${src}`;
    }
    const h = d.hijacks.find(x => 'bgp:' + x.id === id); if (!h) return null;
    return `<p class="eyebrow">Possible BGP hijack · score ${h.score}</p>
      <h2>${esc(h.hijacker.org || 'AS' + h.hijacker.asn)} ${h.hijacker.cc ? flagImg(h.hijacker.cc) : ''}</h2>
      <p class="where">announced address blocks that belong to ${h.victims.map(v => esc(v.org || 'AS' + v.asn)).join(', ')}</p>
      <dl>
        <dt>Announced by</dt><dd>${net(h.hijacker)}</dd>
        <dt>Belongs to</dt><dd>${h.victims.map(net).join('<br>')}</dd>
        <dt>Address blocks</dt><dd>${h.prefixes.map(esc).join(', ')}${h.prefix_count > h.prefixes.length ? ` and ${h.prefix_count - h.prefixes.length} more` : ''}</dd>
        <dt>When</dt><dd>${local(h.start)}${h.duration_s ? `, lasted ${Math.round(h.duration_s / 60)} min` : ', a single announcement'}${h.ongoing ? ' <span class="soft">(still announced)</span>' : ''}</dd>
        <dt>Seen by</dt><dd>${h.seen_by_peers ?? '?'} of Cloudflare's peers</dd>
      </dl>
      <section class="pz"><h3>Why Cloudflare flags it (score ${h.score})</h3>${h.evidence.length ? `<ul class="dos-list">${h.evidence.map(e => `<li>${esc(e)}</li>`).join('')}</ul>` : '<p class="soft">No evidence tags.</p>'}
        <p class="soft">The score is the sum of these signs (8 for RPKI, 4 for the registries); we list 10 and above. A high score says the announcement is not authorised, not who meant what.</p></section>
      ${h.victim_countries[0] ? countryBtn({cc: h.victim_countries[0].cc}, 'Dossier of the victim\'s country') : ''}
      <a class="link" href="https://radar.cloudflare.com/routing" target="_blank" rel="noopener">Cloudflare Radar routing</a>${src}`;
  },
};
