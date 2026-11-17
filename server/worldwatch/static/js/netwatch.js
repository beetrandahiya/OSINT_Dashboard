// Internet routing incidents from Cloudflare Radar: BGP hijacks (a network announcing address blocks that belong to
// another) and route leaks, last 24 hours. Networks have no position: lines join the countries Cloudflare gives for
// the networks, drawn between country centres. See radar.py.
import {ago, esc, local, countryBtn} from './util.js';
import {flagImg} from './flags.js';

let d = {hijacks: [], leaks: []}, info = null, theMap = null, raf = 0, on = true, flows = [], stale = false;
// A dead feed is shown as dead (hard rule): the layer is "the last 24 hours", so events older than that are dropped by
// our own clock, not the snapshot's; and while the feed is failing or unread for two intervals nothing is called
// "still announced". Without a token Cloudflare's last snapshot would otherwise be drawn as current for ever.
const STALE_S = 2 * 900;
export const radarStale = x => !!x && (x.state === 'failing' || x.state === 'waiting' || !x.fetched || Date.now() / 1000 - x.fetched > STALE_S);

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
// The streaks are drawn on a canvas over the map, every frame, from positions interpolated along each arc: sending
// GeoJSON to the map 60 times a second made MapLibre re-tile it in a worker and the heads hopped vertex to vertex.
let cv = null;
const isGlobe = () => theMap?.getProjection?.()?.type === 'globe';
const dark = () => matchMedia('(prefers-color-scheme: dark)').matches;
const RAD = Math.PI / 180;
const unit = ([lon, lat]) => [Math.cos(lat * RAD) * Math.cos(lon * RAD), Math.cos(lat * RAD) * Math.sin(lon * RAD), Math.sin(lat * RAD)];
// the point a fraction f along a flow's arc, between its vertices
function along(pts, f) {
  const n = pts.length - 1, x = Math.max(0, Math.min(1, f)) * n, i = Math.min(n - 1, Math.floor(x)), u = x - i;
  return [pts[i][0] + (pts[i + 1][0] - pts[i][0]) * u, pts[i][1] + (pts[i + 1][1] - pts[i][1]) * u];
}
const rgba = (rgb, a) => `rgba(${rgb},${a.toFixed(3)})`;
const hexRgb = h => [1, 3, 5].map(i => parseInt(h.slice(i, i + 2), 16)).join(',');

function animate(t) {
  raf = 0;
  if (!theMap || !cv) return;
  const box = theMap.getContainer(), w = box.clientWidth, h = box.clientHeight, dpr = Math.min(devicePixelRatio || 1, 2);
  if (cv.width !== Math.round(w * dpr) || cv.height !== Math.round(h * dpr)) { cv.width = Math.round(w * dpr); cv.height = Math.round(h * dpr); }
  const x = cv.getContext('2d'); x.setTransform(dpr, 0, 0, dpr, 0, 0); x.clearRect(0, 0, w, h);
  if (!on || !flows.length || reduce.matches) return;
  const globe = isGlobe(), c = theMap.getCenter(), cu = unit([c.lng, c.lat]);
  const seen = pt => !globe || (() => { const u = unit(pt); return u[0] * cu[0] + u[1] * cu[1] + u[2] * cu[2] > 0.08; })();
  const dk = dark(), cols = {strong: hexRgb(dk ? '#ff6961' : '#e0001a'), weak: hexRgb(dk ? '#ff9f0a' : '#c93400'), leak: hexRgb(dk ? '#64d2ff' : '#0071a4')};
  x.lineCap = 'round'; x.lineJoin = 'round';
  x.globalCompositeOperation = dk ? 'lighter' : 'source-over';
  const TAIL = 0.22, STEPS = 22;
  for (const fl of flows) {
    const p = ((t / fl.period) + fl.phase) % 1, rgb = cols[fl.kind === 'leak' ? 'leak' : fl.strong ? 'strong' : 'weak'];
    const wide = fl.kind === 'leak' ? 1.4 : fl.strong ? 2.6 : 1.6, ease = q => q < 0.5 ? 2 * q * q : 1 - (-2 * q + 2) ** 2 / 2;
    if (p < 0.82) {
      const head = ease(p / 0.82), back = Math.max(0, head - TAIL);
      let prev = null;
      for (let k = 0; k <= STEPS; k++) {               // the tail: short pieces, fading in towards the head
        const f = back + (head - back) * k / STEPS, pt = along(fl.pts, f);
        if (!seen(pt)) { prev = null; continue; }
        const s = theMap.project(pt);
        if (prev) {
          const a = (k / STEPS) ** 1.6;
          x.strokeStyle = rgba(rgb, 0.22 * a); x.lineWidth = wide * 3.2; x.beginPath(); x.moveTo(prev.x, prev.y); x.lineTo(s.x, s.y); x.stroke();
          x.strokeStyle = rgba(rgb, 0.95 * a); x.lineWidth = wide * (0.5 + 0.5 * a); x.beginPath(); x.moveTo(prev.x, prev.y); x.lineTo(s.x, s.y); x.stroke();
        }
        prev = s;
      }
      const hp = along(fl.pts, head);
      if (seen(hp)) {                                   // a soft glowing head
        const s = theMap.project(hp), r = wide * 3.4, g = x.createRadialGradient(s.x, s.y, 0, s.x, s.y, r);
        g.addColorStop(0, dk ? 'rgba(255,255,255,0.95)' : rgba(rgb, 1)); g.addColorStop(0.35, rgba(rgb, 0.8)); g.addColorStop(1, rgba(rgb, 0));
        x.fillStyle = g; x.beginPath(); x.arc(s.x, s.y, r, 0, 2 * Math.PI); x.fill();
      }
    } else {                                            // arrival: a ring spreading out and fading
      const q = (p - 0.82) / 0.18, end = fl.pts[fl.pts.length - 1];
      if (seen(end)) {
        const s = theMap.project(end);
        x.strokeStyle = rgba(rgb, 0.85 * (1 - q) ** 1.5); x.lineWidth = 1.6; x.beginPath(); x.arc(s.x, s.y, 3 + 16 * ease(q), 0, 2 * Math.PI); x.stroke();
      }
    }
  }
  x.globalCompositeOperation = 'source-over';
  raf = requestAnimationFrame(animate);
}
const reduce = matchMedia('(prefers-reduced-motion: reduce)');
const LIST_MIN = 10;
const net = n => `${esc(n.org || 'unknown network')} <span class="soft">(AS${n.asn}${n.cc ? ', ' + esc(n.cc) : ''})</span>`;
const strong = h => (h.score ?? 0) >= LIST_MIN;

export default {
  id: 'hijacks', title: 'Internet hijacks', color: ['#d70015', '#ff6961'], feeds: {cf_radar: 600},
  layers: ['ww-bgp-leak', 'ww-bgp-line', 'ww-bgp-dot'],
  addTo(map) {
    map.addSource('ww-bgp', {type: 'geojson', data: {type: 'FeatureCollection', features: []}});
    map.addLayer({id: 'ww-bgp-leak', type: 'line', source: 'ww-bgp', filter: ['==', ['get', 'kind'], 'leak'],
      paint: {'line-width': 0.8, 'line-opacity': 0.2, 'line-dasharray': [2, 3]}});
    map.addLayer({id: 'ww-bgp-line', type: 'line', source: 'ww-bgp', filter: ['==', ['get', 'kind'], 'hijack'],
      paint: {'line-width': ['case', ['get', 'strong'], 1.2, 0.8], 'line-opacity': ['case', ['get', 'strong'], 0.35, 0.15]}});
    map.addLayer({id: 'ww-bgp-dot', type: 'circle', source: 'ww-bgp', filter: ['==', ['geometry-type'], 'Point'],
      paint: {'circle-radius': ['case', ['get', 'strong'], 6, 3.5], 'circle-stroke-width': 1.2, 'circle-opacity': ['case', ['get', 'strong'], 1, 0.6]}});
    cv = document.createElement('canvas');
    cv.style.cssText = 'position:absolute;inset:0;width:100%;height:100%;pointer-events:none;z-index:1';
    map.getContainer().appendChild(cv);
    theMap = map;
  },
  visible(v) { on = v; if (!raf) raf = requestAnimationFrame(animate); },
  paint(map, dark) {
    const c = this.color[+dark], soft = dark ? '#aeaeb2' : '#8e8e93';
    map.setPaintProperty('ww-bgp-line', 'line-color', ['case', ['get', 'strong'], c, soft]);
    map.setPaintProperty('ww-bgp-leak', 'line-color', dark ? '#64d2ff' : '#0071a4');
    map.setPaintProperty('ww-bgp-dot', 'circle-color', ['case', ['get', 'strong'], c, soft]);
    map.setPaintProperty('ww-bgp-dot', 'circle-stroke-color', dark ? '#1c1c1e' : '#ffffff');
  },
  onData(feed, x) {
    const p = x.payload || {}, cut = Date.now() / 1000 - 86400;
    info = x; stale = radarStale(x);
    d = {hijacks: (p.hijacks || []).filter(h => (h.start || 0) + (h.duration_s || 0) > cut), leaks: (p.leaks || []).filter(l => (l.last || l.start || 0) > cut)};
  },
  about: () => stale ? `Cloudflare Radar feed stopped: last read ${info?.fetched ? ago(info.fetched) : 'never'}${info?.error ? ' (' + (info.error.match(/not set up.*/)?.[0] || info.error) + ')' : ''}. Only events of the last 24 hours are drawn.` : 'BGP hijacks and route leaks of the last 24 hours, from Cloudflare Radar.',
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
        flows.push({pts: arc(h.hijacker.at, v.at), kind: 'hijack', strong: strong(h), period: 3200 + (k * 397) % 2200, phase: (k++ * 0.618) % 1});
    }
    for (const l of d.leaks) {
      const pts = l.countries.map(c => c.at).filter(Boolean);
      for (let i = 0; i + 1 < pts.length && flows.length < 120; i++) flows.push({pts: arc(pts[i], pts[i + 1]), kind: 'leak', strong: false, period: 4200 + (k * 271) % 2000, phase: (k++ * 0.618) % 1});
    }
    if (!raf && on) raf = requestAnimationFrame(animate);
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
    const src = `${stale ? `<p class="source prof-problems">The Cloudflare Radar feed has stopped (last read ${ago(info?.fetched)}): this event may have changed since.</p>` : ''}<p class="source">Source: Cloudflare Radar (CC BY-NC 4.0), read ${ago(info?.fetched)}. Detected from routing announcements Cloudflare's collectors saw; a "hijack" here means the announcement looks wrong, which also happens by mistake or when a customer's provider announces for it. Lines join the countries Cloudflare lists for the networks, drawn between country centres; networks have no single place. The moving streaks only show the direction of each event (from the announcing network's country to the victim's); they are not live traffic.</p>`;
    if (String(id).startsWith('leak:')) {
      const l = d.leaks.find(x => 'leak:' + x.id === id); if (!l) return null;
      return `<p class="eyebrow">Route leak</p><h2>${esc(l.leaker.org || 'AS' + l.leaker.asn)}</h2>
        <p class="where">passed on routes it should not have, ${l.finished ? 'finished' : stale ? 'not finished when last read' : 'still going'}</p>
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
        <dt>When</dt><dd>${local(h.start)}${h.duration_s ? `, lasted ${Math.round(h.duration_s / 60)} min` : ', a single announcement'}${h.ongoing && !stale ? ' <span class="soft">(still announced)</span>' : ''}</dd>
        <dt>Seen by</dt><dd>${h.seen_by_peers ?? '?'} of Cloudflare's peers</dd>
      </dl>
      <section class="pz"><h3>Why Cloudflare flags it (score ${h.score})</h3>${h.evidence.length ? `<ul class="dos-list">${h.evidence.map(e => `<li>${esc(e)}</li>`).join('')}</ul>` : '<p class="soft">No evidence tags.</p>'}
        <p class="soft">The score is the sum of these signs (8 for RPKI, 4 for the registries); we list 10 and above. A high score says the announcement is not authorised, not who meant what.</p></section>
      ${h.victim_countries[0] ? countryBtn({cc: h.victim_countries[0].cc}, 'Dossier of the victim\'s country') : ''}
      <a class="link" href="https://radar.cloudflare.com/routing" target="_blank" rel="noopener">Cloudflare Radar routing</a>${src}`;
  },
};
