// "Which satellites actually photographed it": the button under a card's spy-pass button asks /api/imaged for the
// captures by Sentinel-1 (radar), Sentinel-2 and Landsat (optical) over that point in the last 30 days, lists them
// with the catalogue's own preview, and draws their outlines on the map while the card is open.
import {ago, esc, local} from './util.js';

let theMap = null, shown = [], watch = 0;
const SRC = 'ww-imaged';
const dark = () => matchMedia('(prefers-color-scheme: dark)').matches;

export function attachImaged(map) {
  theMap = map;
  const add = () => {
    if (map.getSource(SRC)) return;
    map.addSource(SRC, {type: 'geojson', data: {type: 'FeatureCollection', features: []}});
    map.addLayer({id: 'ww-imaged-fill', type: 'fill', source: SRC, paint: {'fill-color': ['case', ['==', ['get', 'kind'], 'radar'], '#bf5af2', '#0a84ff'],
      'fill-opacity': ['case', ['get', 'hot'], 0.22, 0]}});
    map.addLayer({id: 'ww-imaged-line', type: 'line', source: SRC, paint: {'line-color': ['case', ['==', ['get', 'kind'], 'radar'], '#bf5af2', '#0a84ff'],
      'line-width': ['case', ['get', 'hot'], 2.2, 0.8], 'line-opacity': ['case', ['get', 'hot'], 1, 0.35]}});
  };
  if (map.isStyleLoaded()) add(); else map.once('load', add);
}

function draw(hot = -1) {
  const src = theMap?.getSource(SRC); if (!src) return;
  src.setData({type: 'FeatureCollection', features: shown.filter(c => c.geometry).map((c, i) => ({type: 'Feature', geometry: c.geometry, properties: {kind: c.kind, hot: i === hot}}))});
}
// the outlines go away when the card that asked for them closes or shows something else
// (a closed card stays in the page, hidden, so a hidden box counts as gone too)
function keepWatching(lat, lon) {
  clearInterval(watch);
  watch = setInterval(() => {
    const b = document.getElementById('imaged');
    if (!b || !b.dataset.done || b.closest('[hidden]') || +b.dataset.lat !== lat || +b.dataset.lon !== lon) { shown = []; draw(); clearInterval(watch); }
  }, 1000);
}

const pic = u => '/api/imaged/pic?u=' + encodeURIComponent(u);
function row(c, i) {
  const what = c.kind === 'radar'
    ? `radar, ${esc(c.mode || '')} mode, ${esc(c.resolution)}, ${esc(c.direction)} pass${c.polarisation ? ', ' + esc(c.polarisation) : ''}`
    : `optical, ${esc(c.resolution)}${c.cloud != null ? `, ${Math.round(c.cloud)} % cloud` : ''}`;
  return `<li class="img-row" data-i="${i}">${c.preview ? `<a href="${esc(c.page)}" target="_blank" rel="noopener"><img src="${esc(pic(c.preview))}" alt="Preview of this capture" loading="lazy" onerror="this.remove()"></a>` : '<span class="img-none">no preview</span>'}
    <div><b>${esc(c.sat)}</b> <span class="soft">${local(c.time)} (${ago(c.time)})</span><br><span class="soft">${what}</span></div></li>`;
}

document.addEventListener('click', async e => {
  const b = e.target.closest('[data-imaged]'); if (!b) return;
  const lat = +b.closest('.imaged').dataset.lat, lon = +b.closest('.imaged').dataset.lon;
  b.disabled = true; b.textContent = 'Asking the satellite catalogues…';
  b.closest('.imaged').dataset.done = 'wait';   // a card redrawn while waiting keeps this box as it is (main.js keeps boxes marked done)
  // the card can be redrawn while the catalogues answer (any feed update does it): find the box that is there now
  const current = () => [...document.querySelectorAll('.imaged')].find(x => +x.dataset.lat === lat && +x.dataset.lon === lon && !x.closest('[hidden]'));
  let d;
  try { d = await fetch(`/api/imaged?lat=${lat}&lon=${lon}&days=30`).then(r => r.json()); }
  catch (err) { const x = current(); if (x) { x.dataset.done = ''; const bb = x.querySelector('[data-imaged]'); if (bb) { bb.disabled = false; bb.textContent = 'The catalogues did not answer. Try again'; } } return; }
  const box = current(); if (!box) return;
  shown = d.captures || [];
  const radar = shown.filter(c => c.kind === 'radar').length, clear = shown.filter(c => c.kind === 'optical' && c.cloud != null && c.cloud < 30);
  box.dataset.done = '1';
  box.innerHTML = `<h3>Photographed from orbit, last 30 days</h3>
    <p>${shown.length} captures: ${radar} radar (sees through cloud and at night), ${shown.length - radar} optical${clear.length ? `, ${clear.length} of them mostly clear (newest ${local(clear[0].time)})` : ', none of them mostly clear'}.</p>
    ${shown.length ? `<ul class="img-list">${shown.slice(0, 30).map(row).join('')}</ul>` : ''}
    ${d.failed?.length ? `<p class="source">Could not ask: ${d.failed.map(esc).join('; ')}.</p>` : ''}
    <p class="source">Real acquisitions from the public catalogues of Sentinel-1 (ESA, via the Alaska Satellite Facility), Sentinel-2 (ESA, Copernicus Data Space) and Landsat 8/9 (USGS). Previews are the catalogues' own small pictures; a click opens the scene in the catalogue, where the full picture is free. Outlines on the map: purple radar, blue optical; point at a row to light its outline. Commercial and military satellites publish no catalogue.</p>`;
  draw(); keepWatching(lat, lon);
});
document.addEventListener('mouseover', e => {
  const r = e.target.closest('.img-row'); if (!r || !shown.length) return;
  draw(+r.dataset.i);
});
document.addEventListener('mouseout', e => { if (e.target.closest('.img-list') && !e.relatedTarget?.closest?.('.img-list')) draw(); });
