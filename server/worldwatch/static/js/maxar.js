// Disaster imagery from Maxar's Open Data programme: sharp pictures (about 0.3-0.8 m) released free for major
// disasters. Events are drawn as outlined areas; open one, pick a satellite pass, and its pictures load as you zoom
// in, piece by piece, straight out of Maxar's files through our server (/api/maxar/tile).
import {ago, esc} from './util.js';

const SRC = 'ww-maxar';
let events = [], ems = [], emsInfo = null, info = null, theMap = null, active = null, items = [], metas = new Map(), shownPieces = new Map(), busy = false, again = false, msg = '';

const bboxPoly = b => [[[b[0], b[1]], [b[2], b[1]], [b[2], b[3]], [b[0], b[3]], [b[0], b[1]]]];
const lerp = (a, b, t) => [a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t];
// a point inside the picture at fractions (u across, v down), from its four corners (NW, NE, SE, SW)
const at = (c, u, v) => lerp(lerp(c[0], c[1], u), lerp(c[3], c[2], u), v);

async function meta(u) {
  if (!metas.has(u)) metas.set(u, fetch('/api/maxar/meta?u=' + encodeURIComponent(u)).then(r => r.ok ? r.json() : null).catch(() => null));
  return metas.get(u);
}

async function refresh() {
  const map = theMap; if (!map || !active) return;
  if (busy) { again = true; return; }                 // a move while pieces load: run once more afterwards, so the last view wins
  busy = true;
  try {
    const want = new Map();
    if (map.getZoom() >= 9) {
      const b = map.getBounds(), view = [b.getWest(), b.getSouth(), b.getEast(), b.getNorth()];
      const visible = items.filter(i => i.bbox[0] < view[2] && i.bbox[2] > view[0] && i.bbox[1] < view[3] && i.bbox[3] > view[1]).slice(0, 12);
      for (const it of visible) {
        const m = await meta(it.visual); if (!m) continue;
        const px = Math.abs(map.project(m.corners[1]).x - map.project(m.corners[0]).x);     // how wide the picture is on screen
        let L = m.levels.length - 1;
        while (L > 0 && m.levels[L].w < px * 1.2) L--;                                       // the smallest level that is still sharp enough
        const lv = m.levels[L], across = Math.ceil(lv.w / lv.tw), down = Math.ceil(lv.h / lv.th);
        for (let y = 0; y < down; y++) for (let x = 0; x < across; x++) {
          const u0 = x * lv.tw / lv.w, u1 = (x + 1) * lv.tw / lv.w, v0 = y * lv.th / lv.h, v1 = (y + 1) * lv.th / lv.h;
          const q = [at(m.corners, u0, v0), at(m.corners, u1, v0), at(m.corners, u1, v1), at(m.corners, u0, v1)];
          const lo = Math.min(...q.map(p => p[0])), hi = Math.max(...q.map(p => p[0])), la = Math.min(...q.map(p => p[1])), ha = Math.max(...q.map(p => p[1]));
          if (hi < view[0] || lo > view[2] || ha < view[1] || la > view[3]) continue;
          if (want.size >= 60) break;
          want.set(`${it.id}|${L}|${x}|${y}`, {url: `/api/maxar/tile?u=${encodeURIComponent(it.visual)}&l=${L}&x=${x}&y=${y}`, q});
        }
      }
    }
    for (const [k, id] of shownPieces) if (!want.has(k)) { if (map.getLayer(id)) map.removeLayer(id); if (map.getSource(id)) map.removeSource(id); shownPieces.delete(k); }
    const before = map.getStyle().layers.find(l => l.id.startsWith('ww-') && !l.id.startsWith('ww-mx-') && !['ww-night', 'ww-photo', 'ww-sharp'].includes(l.id))?.id;
    let n = 0;
    for (const [k, p] of want) {
      if (shownPieces.has(k)) continue;
      const id = 'ww-mx-' + (n++) + '-' + Date.now();
      map.addSource(id, {type: 'image', url: p.url, coordinates: p.q});
      map.addLayer({id, type: 'raster', source: id, paint: {'raster-fade-duration': 0}}, before);
      shownPieces.set(k, id);
    }
    msg = map.getZoom() < 9 ? 'Zoom in on the outlined area to load the pictures.' : want.size ? '' : 'No pictures of this pass in view; pan to the outlined squares.';
  } finally { busy = false; if (again) { again = false; setTimeout(refresh, 50); } }
}

function drawOutlines() {
  const map = theMap; if (!map?.getSource(SRC)) return;
  // Copernicus activations (current) first; Maxar's archive only when no Copernicus area covers it
  const feats = [];
  for (const a of ems) for (const r of a.rings) feats.push({type: 'Feature', geometry: {type: 'Polygon', coordinates: [r]}, properties: {id: 'ems:' + a.code, name: a.name, kind: 'event', current: true}});
  for (const a of ems) if (a.lon != null) feats.push({type: 'Feature', geometry: {type: 'Point', coordinates: [a.lon, a.lat]}, properties: {id: 'ems:' + a.code, name: a.name, kind: 'pin'}});
  for (const e of events.filter(e => e.bbox?.[0] != null)) feats.push({type: 'Feature', geometry: {type: 'Polygon', coordinates: bboxPoly(e.bbox)}, properties: {id: 'mx:' + e.id, name: e.title + ' (archive)', kind: 'event', current: false}});
  for (const it of items) feats.push({type: 'Feature', geometry: {type: 'Polygon', coordinates: bboxPoly(it.bbox)}, properties: {kind: 'item'}});
  map.getSource(SRC).setData({type: 'FeatureCollection', features: feats});
}

export async function openAcquisition(eventId, acq) {
  active = {event: eventId, acq: acq.href, when: acq.when};
  for (const [, id] of shownPieces) { if (theMap.getLayer(id)) theMap.removeLayer(id); if (theMap.getSource(id)) theMap.removeSource(id); }
  shownPieces.clear(); items = []; msg = 'Loading the list of pictures…'; document.dispatchEvent(new Event('ww-detail'));
  try {
    const r = await fetch(`/api/maxar/items?event=${encodeURIComponent(eventId)}&acq=${encodeURIComponent(acq.href)}`).then(x => x.json());
    items = r.items || []; msg = r.error || '';
  } catch (e) { msg = 'Maxar\'s catalogue could not be read.'; }
  drawOutlines();
  if (acq.bbox) theMap.fitBounds([[acq.bbox[0], acq.bbox[1]], [acq.bbox[2], acq.bbox[3]]], {padding: 60, maxZoom: 14});
  document.dispatchEvent(new Event('ww-detail'));
}
const acqCache = new Map();
document.addEventListener('click', async e => {
  const b = e.target.closest('[data-mxacq]'); if (!b) return;
  const list = acqCache.get(b.dataset.event) || [], a = list.find(x => x.href === b.dataset.mxacq);
  if (a) openAcquisition(b.dataset.event, a);
});

export default {
  id: 'maxar', title: 'Disaster imagery', color: ['#bf5af2', '#da8fff'], feeds: {maxar_events: 21600, ems: 1800}, layers: ['ww-maxar-fill', 'ww-maxar-line', 'ww-maxar-pin', 'ww-maxar-label'], defaultOff: true,
  about: () => 'Satellite pictures of disasters: current ones from Copernicus EMS (pins with filled areas), and Maxar\'s free archive (faint outlines, up to Dec 2025). Click one, press "Show the picture", then zoom in.',
  addTo(map) {
    theMap = map;
    map.addSource(SRC, {type: 'geojson', data: {type: 'FeatureCollection', features: []}});
    map.addLayer({id: 'ww-maxar-fill', type: 'fill', source: SRC, filter: ['==', ['get', 'kind'], 'event'], paint: {'fill-opacity': ['case', ['==', ['get', 'current'], true], 0.12, 0.04]}});
    map.addLayer({id: 'ww-maxar-pin', type: 'circle', source: SRC, filter: ['==', ['get', 'kind'], 'pin'], paint: {'circle-radius': 6, 'circle-stroke-width': 1.5, 'circle-stroke-color': '#ffffff'}});
    map.addLayer({id: 'ww-maxar-line', type: 'line', source: SRC, paint: {'line-width': ['case', ['==', ['get', 'kind'], 'item'], 0.8, 1.6], 'line-opacity': 0.8}});
    map.addLayer({id: 'ww-maxar-label', type: 'symbol', source: SRC, filter: ['==', ['get', 'kind'], 'event'],
      layout: {'text-field': ['get', 'name'], 'text-font': ['Noto Sans Bold'], 'text-size': 11, 'text-optional': true}, paint: {'text-halo-width': 1.3}});
    let t = null; map.on('moveend', () => { clearTimeout(t); t = setTimeout(refresh, 300); });
  },
  paint(map, dark) {
    const c = this.color[+dark];
    map.setPaintProperty('ww-maxar-fill', 'fill-color', c); map.setPaintProperty('ww-maxar-line', 'line-color', c); map.setPaintProperty('ww-maxar-pin', 'circle-color', c);
    map.setPaintProperty('ww-maxar-label', 'text-color', dark ? '#e5e5ea' : '#3a3a3c'); map.setPaintProperty('ww-maxar-label', 'text-halo-color', dark ? '#1c1c1e' : '#ffffff');
  },
  onData(feed, d) { if (feed === 'ems') { emsInfo = d; ems = d.payload.activations || []; } else { info = d; events = d.payload.events || []; } },
  render() { drawOutlines(); },
  visible(on) {
    if (on || !theMap) return;
    for (const [, id] of shownPieces) { if (theMap.getLayer(id)) theMap.removeLayer(id); if (theMap.getSource(id)) theMap.removeSource(id); }
    shownPieces.clear(); active = null; items = []; drawOutlines();
  },
  count: () => ems.length + events.length,
  locate(id) {
    if (id.startsWith('ems:')) { const a = ems.find(x => 'ems:' + x.code === id); return a && a.lon != null ? [a.lon, a.lat] : null; }
    const e = events.find(x => 'mx:' + x.id === id); return e && [(e.bbox[0] + e.bbox[2]) / 2, (e.bbox[1] + e.bbox[3]) / 2];
  },
  ring: () => 18,
  owns: id => String(id).startsWith('mx:') || String(id).startsWith('ems:'),
  rows: () => ems.filter(a => Date.parse(a.eventTime + 'Z') > Date.now() - 14 * 86400000).map(a => ({id: 'ems:' + a.code, time: Date.parse((a.activationTime || a.eventTime) + 'Z') / 1000, badge: '◩',
    title: `Disaster pictures: ${a.name}`, meta: `Copernicus ${a.code} · ${a.category}`})),
  detail(id) {
    if (id.startsWith('ems:')) return emsDetail(ems.find(x => 'ems:' + x.code === id));
    const e = events.find(x => 'mx:' + x.id === id);
    if (!e) return null;
    const acqs = acqCache.get(e.id);
    return `<p class="eyebrow">Disaster imagery · Maxar Open Data archive</p><h2>${esc(e.title)}</h2>
      <p class="where">Pictures taken ${esc((e.start || '').slice(0, 10))} to ${esc((e.end || '').slice(0, 10))} · ${e.acquisitions} satellite passes</p>
      <div id="mxacq" data-event="${esc(e.id)}">${acqs ? acqList(e.id, acqs) : '<p class="pic-wait">Loading the satellite passes…</p>'}</div>
      ${active?.event === e.id ? `<p class="source">${msg ? esc(msg) : `Showing the pass of ${esc(active.when)} UTC. Zoom in for more detail; pieces load as you go.`}</p>` : ''}
      <p class="source">Source: Maxar (now Vantor) Open Data, CC BY-NC 4.0, free for non-commercial use. Released only for major disasters, often days after the event; Maxar has published nothing newer than ${esc((events[0]?.end || '').slice(0, 10))}. Pictures are placed by their four corners, which is exact to a few metres over one picture. Event list fetched ${ago(info?.fetched)}.</p>`;
  },
  async fill(id) {
    const box = document.getElementById('mxacq'); if (!box || box.dataset.done || acqCache.has(box.dataset.event)) return;
    box.dataset.done = '1';
    try {
      const r = await fetch('/api/maxar/acquisitions?event=' + encodeURIComponent(box.dataset.event)).then(x => x.json());
      acqCache.set(box.dataset.event, r.acquisitions || []);
      const now2 = document.getElementById('mxacq'); if (now2) now2.innerHTML = r.error ? `<p class="pic-wait">${esc(r.error)}</p>` : acqList(box.dataset.event, r.acquisitions || []);
    } catch (e) { box.dataset.done = ''; }
  },
};
function acqList(eventId, acqs) {
  return `<ul class="pz-list">${acqs.map(a => `<li><button class="btn" data-event="${esc(eventId)}" data-mxacq="${esc(a.href)}">${esc(a.when)} UTC</button> <span class="soft">${a.items} pictures${active?.acq === a.href ? ' · showing' : ''}</span></li>`).join('')}</ul>`;
}

// ---- Copernicus EMS: current disasters, pictures used for the maps (often 0.3-1.5 m), and what they counted ----
let emsShown = null;
function emsDetail(a) {
  if (!a) return null;
  const when = t => t ? t.slice(0, 16).replace('T', ' ') + ' UTC' : '';
  const blocks = a.aois.map(ao => {
    const pics = ao.products.flatMap(p => p.cogs.map(u => ({u, p, img: p.images.find(i => u.includes((i.file || '').replace('.tif', ''))) || p.images[0]})));
    const built = Object.assign({}, ...ao.products.map(p => p.built));
    return `<section class="pz"><h3>${esc(ao.name || 'Area ' + ao.number)}</h3>
      ${Object.keys(built).length ? `<dl>${Object.entries(built).map(([k, v]) => `<dt>${esc(k)}</dt><dd>${v.affected ?? '?'} affected of ${v.total ?? '?'}${v.unit ? ' ' + esc(v.unit) : ''}</dd>`).join('')}</dl>` : ''}
      ${pics.length ? `<ul class="pz-list">${pics.map(x => `<li><button class="btn" data-emscog="${esc(x.u)}" data-code="${esc(a.code)}">Show the picture</button> <span class="soft">${esc(x.img?.sensor || '')} · ${esc(when(x.img?.time))}${x.img?.res ? ' · ' + esc(x.img.res) : ''}${emsShown === x.u ? ' · showing' : ''}</span></li>`).join('')}</ul>` : '<p class="soft">No picture published for this area.</p>'}
    </section>`;
  }).join('');
  return `<p class="eyebrow">Disaster pictures · Copernicus EMS ${esc(a.code)}</p><h2>${esc(a.name)}</h2>
    <p class="where">${esc(a.category || '')} · event ${esc(when(a.eventTime))} · ${esc((a.countries || []).map(c => typeof c === 'string' ? c : c.name || c.short_name || '').filter(Boolean).join(', '))}${a.closed ? ' · closed' : ' · ongoing'}</p>
    ${blocks}
    ${active?.cog ? `<p class="source">${msg ? esc(msg) : 'Zoom in for more detail; pieces load as you go.'}</p>` : ''}
    ${a.report ? `<a class="link" href="${esc(a.report)}" target="_blank" rel="noopener">Copernicus activation page</a>` : ''}
    <p class="source">Source: Copernicus Emergency Management Service (rapid mapping), fetched ${ago(emsInfo?.fetched)}. Pictures are the ones Copernicus used for its maps (sensor and time as listed; "VHR" is very high resolution, about 0.3-1 m). Counts of affected buildings are Copernicus's own analysis of those pictures. Copernicus is activated mainly for Europe and on request elsewhere, so many disasters have no entry.</p>`;
}
document.addEventListener('click', async e => {
  const b = e.target.closest('[data-emscog]'); if (!b) return;
  const u = b.dataset.emscog;
  emsShown = u; active = {cog: u}; msg = 'Reading the picture…';
  for (const [, id] of shownPieces) { if (theMap.getLayer(id)) theMap.removeLayer(id); if (theMap.getSource(id)) theMap.removeSource(id); }
  shownPieces.clear();
  const m = await meta(u);
  if (!m) { msg = 'The picture could not be read.'; document.dispatchEvent(new Event('ww-detail')); return; }
  const xs = m.corners.map(c => c[0]), ys = m.corners.map(c => c[1]);
  items = [{id: u.split('/').pop(), visual: u, bbox: [Math.min(...xs), Math.min(...ys), Math.max(...xs), Math.max(...ys)]}];
  msg = ''; drawOutlines();
  theMap.fitBounds([[items[0].bbox[0], items[0].bbox[1]], [items[0].bbox[2], items[0].bbox[3]]], {padding: 40, maxZoom: 15});
  document.dispatchEvent(new Event('ww-detail'));
});
