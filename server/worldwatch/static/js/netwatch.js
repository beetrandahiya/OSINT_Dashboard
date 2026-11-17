// Internet routing incidents from Cloudflare Radar: BGP hijacks (a network announcing address blocks that belong to
// another) and route leaks, last 24 hours. Networks have no position: lines join the countries Cloudflare gives for
// the networks, drawn between country centres. See radar.py.
import {ago, esc, local, countryBtn} from './util.js';
import {flagImg} from './flags.js';
import {moving, fpsCap} from './prefs.js';

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
// Per frame this was ~5,000 separate strokes, each with a freshly formatted colour string, plus ~2,800 map.project calls
// and a radial gradient per head: about a fifth of the page's main thread with only this layer on. Now: at most
// prefs.fps frames a second (30); each flow's arc vertices are projected once per view and reused until the map moves
// (lazily, only the ~12 a tail covers); the tail pieces of every flow that share a colour and a fade step are drawn
// as one path (3 colours x 22 steps x 2 passes = at most 132 strokes); colour strings are made once per theme; heads
// are a pre-drawn glow sprite. Same look.
const TAIL = 0.22, STEPS = 22;
const easeIO = q => q < 0.5 ? 2 * q * q : 1 - (-2 * q + 2) ** 2 / 2;
const hexRgb = h => [1, 3, 5].map(i => parseInt(h.slice(i, i + 2), 16)).join(',');
const KINDS = ['strong', 'weak', 'leak'], WIDE = {strong: 2.6, weak: 1.6, leak: 1.4};
const kindOf = fl => fl.kind === 'leak' ? 'leak' : fl.strong ? 'strong' : 'weak';
let style = null;                 // per theme: colour strings for every fade step, glow sprites
function styles(dk, dpr) {
  const key = dk + '|' + dpr;
  if (style?.key === key) return style;
  const rgbOf = {strong: hexRgb(dk ? '#ff6961' : '#e0001a'), weak: hexRgb(dk ? '#ff9f0a' : '#c93400'), leak: hexRgb(dk ? '#64d2ff' : '#0071a4')};
  const rgba = (rgb, a) => `rgba(${rgb},${a.toFixed(3)})`;
  const st = {key, rgbOf, glow: {}, core: {}, sprite: {}, ring: {}};
  for (const k of KINDS) {
    st.glow[k] = []; st.core[k] = [];
    for (let i = 0; i <= STEPS; i++) { const a = (i / STEPS) ** 1.6; st.glow[k][i] = rgba(rgbOf[k], 0.22 * a); st.core[k][i] = rgba(rgbOf[k], 0.95 * a); }
    st.ring[k] = Array.from({length: 33}, (_, i) => rgba(rgbOf[k], 0.85 * (1 - i / 32) ** 1.5));
    // the soft glowing head, drawn once at device resolution
    const r = WIDE[k] * 3.4, n = Math.ceil(r * 2 * dpr) + 2, c = document.createElement('canvas'); c.width = c.height = n;
    const g = c.getContext('2d'), m = n / 2, gr = g.createRadialGradient(m, m, 0, m, m, r * dpr);
    gr.addColorStop(0, dk ? 'rgba(255,255,255,0.95)' : rgba(rgbOf[k], 1)); gr.addColorStop(0.35, rgba(rgbOf[k], 0.8)); gr.addColorStop(1, rgba(rgbOf[k], 0));
    g.fillStyle = gr; g.beginPath(); g.arc(m, m, r * dpr, 0, 2 * Math.PI); g.fill();
    st.sprite[k] = {c, size: n / dpr};
  }
  return (style = st);
}
let viewKey = '', viewVer = 0, lastDraw = -1e9, cu = [0, 0, 1], globeView = false;
// a vertex of a flow on screen (null when behind the globe), worked out once per view
function vtx(fl, i) {
  if (fl.ver !== viewVer) { fl.ver = viewVer; fl.sc.fill(undefined); }
  let s = fl.sc[i];
  if (s === undefined) {
    const pt = fl.pts[i];
    let ok = true;
    if (globeView) { const u = unit(pt); ok = u[0] * cu[0] + u[1] * cu[1] + u[2] * cu[2] > 0.08; }
    s = fl.sc[i] = ok ? theMap.project(pt) : null;
  }
  return s;
}
// the screen point a fraction f along a flow's arc, written into out[j]; false when that piece is behind the globe
function alongS(fl, f, out, j) {
  const n = fl.pts.length - 1, x = Math.max(0, Math.min(1, f)) * n, i = Math.min(n - 1, Math.floor(x)), u = x - i;
  const a = vtx(fl, i), b = vtx(fl, i + 1);
  if (!a || !b) return false;
  out[j] = a.x + (b.x - a.x) * u; out[j + 1] = a.y + (b.y - a.y) * u;
  return true;
}

function animate(t) {
  raf = 0;
  if (!theMap || !cv) return;
  const go = on && flows.length && moving();
  if (go && t - lastDraw < 1000 / fpsCap() - 2) { raf = requestAnimationFrame(animate); return; }   // frame cap
  lastDraw = t;
  const box = theMap.getContainer(), w = box.clientWidth, h = box.clientHeight, dpr = Math.min(devicePixelRatio || 1, 2);
  if (cv.width !== Math.round(w * dpr) || cv.height !== Math.round(h * dpr)) { cv.width = Math.round(w * dpr); cv.height = Math.round(h * dpr); }
  const x = cv.getContext('2d'); x.setTransform(dpr, 0, 0, dpr, 0, 0); x.clearRect(0, 0, w, h);
  if (!go) return;                                    // off, nothing to show, Reduce Motion, animations off or low power
  const c = theMap.getCenter(), key = [c.lng, c.lat, theMap.getZoom(), theMap.getBearing(), theMap.getPitch(), w, h, isGlobe()].join();
  if (key !== viewKey) { viewKey = key; viewVer++; globeView = isGlobe(); cu = unit([c.lng, c.lat]); }
  const dk = dark(), st = styles(dk, dpr);
  x.lineCap = 'round'; x.lineJoin = 'round';
  x.globalCompositeOperation = dk ? 'lighter' : 'source-over';
  // where every flow is this frame: its tail points (or its arrival ring)
  const by = {strong: [], weak: [], leak: []}, rings = [];
  for (const fl of flows) {
    const p = ((t / fl.period) + fl.phase) % 1, k = kindOf(fl);
    if (p < 0.82) {
      const head = easeIO(p / 0.82), back = Math.max(0, head - TAIL);
      for (let i = 0; i <= STEPS; i++) fl.ok[i] = alongS(fl, back + (head - back) * i / STEPS, fl.tail, 2 * i) ? 1 : 0;
      fl.headOk = alongS(fl, head, fl.hd, 0);
      by[k].push(fl);
    } else {
      const end = vtx(fl, fl.pts.length - 1);
      if (end) rings.push([k, end, (p - 0.82) / 0.18]);
    }
  }
  for (const k of KINDS) {
    const list = by[k], wide = WIDE[k];
    if (!list.length) continue;
    for (let i = 1; i <= STEPS; i++) {                 // the tail: short pieces, fading in towards the head
      const a = (i / STEPS) ** 1.6;
      x.beginPath();
      for (const fl of list) if (fl.ok[i] && fl.ok[i - 1]) { x.moveTo(fl.tail[2 * i - 2], fl.tail[2 * i - 1]); x.lineTo(fl.tail[2 * i], fl.tail[2 * i + 1]); }
      x.strokeStyle = st.glow[k][i]; x.lineWidth = wide * 3.2; x.stroke();
      x.strokeStyle = st.core[k][i]; x.lineWidth = wide * (0.5 + 0.5 * a); x.stroke();
    }
    const sp = st.sprite[k];                            // a soft glowing head
    for (const fl of list) if (fl.headOk) x.drawImage(sp.c, fl.hd[0] - sp.size / 2, fl.hd[1] - sp.size / 2, sp.size, sp.size);
  }
  x.lineWidth = 1.6;
  for (const [k, s, q] of rings) {                      // arrival: a ring spreading out and fading
    x.strokeStyle = st.ring[k][Math.min(32, Math.round(q * 32))]; x.beginPath(); x.arc(s.x, s.y, 3 + 16 * easeIO(q), 0, 2 * Math.PI); x.stroke();
  }
  x.globalCompositeOperation = 'source-over';
  raf = requestAnimationFrame(animate);
}
const LIST_MIN = 10;
const flow = (pts, kind, strong, period, phase) => ({pts, kind, strong, period, phase, ver: -1, sc: new Array(pts.length), tail: new Float64Array(2 * (STEPS + 1)), ok: new Uint8Array(STEPS + 1), hd: new Float64Array(2), headOk: false});
// animations switched back on (prefs, Reduce Motion): start the loop again
document.addEventListener('ww-motion', () => { if (!raf && on && theMap) raf = requestAnimationFrame(animate); });
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
      paint: {'line-width': ['case', ['==', ['get', 'strong'], true], 1.2, 0.8], 'line-opacity': ['case', ['==', ['get', 'strong'], true], 0.35, 0.15]}});
    map.addLayer({id: 'ww-bgp-dot', type: 'circle', source: 'ww-bgp', filter: ['==', ['geometry-type'], 'Point'],
      paint: {'circle-radius': ['case', ['==', ['get', 'strong'], true], 6, 3.5], 'circle-stroke-width': 1.2, 'circle-opacity': ['case', ['==', ['get', 'strong'], true], 1, 0.6]}});
    cv = document.createElement('canvas');
    cv.style.cssText = 'position:absolute;inset:0;width:100%;height:100%;pointer-events:none;z-index:1';
    map.getContainer().appendChild(cv);
    theMap = map;
  },
  visible(v) { on = v; if (!raf) raf = requestAnimationFrame(animate); },
  paint(map, dark) {
    const c = this.color[+dark], soft = dark ? '#aeaeb2' : '#8e8e93';
    map.setPaintProperty('ww-bgp-line', 'line-color', ['case', ['==', ['get', 'strong'], true], c, soft]);
    map.setPaintProperty('ww-bgp-leak', 'line-color', dark ? '#64d2ff' : '#0071a4');
    map.setPaintProperty('ww-bgp-dot', 'circle-color', ['case', ['==', ['get', 'strong'], true], c, soft]);
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
        flows.push(flow(arc(h.hijacker.at, v.at), 'hijack', strong(h), 3200 + (k * 397) % 2200, (k++ * 0.618) % 1));
    }
    for (const l of d.leaks) {
      const pts = l.countries.map(c => c.at).filter(Boolean);
      for (let i = 0; i + 1 < pts.length && flows.length < 120; i++) flows.push(flow(arc(pts[i], pts[i + 1]), 'leak', false, 4200 + (k * 271) % 2000, (k++ * 0.618) % 1));
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
