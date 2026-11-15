// Public road and traffic cameras that their operators publish openly (TfL, NYC DOT, Caltrans, Singapore LTA, Hong
// Kong Transport Department, Fintraffic). Pictures are fetched through our server when a card opens and refreshed
// while it stays open. No private or unsecured cameras, ever.
import {ago, esc} from './util.js';

let cams = [], byId = new Map(), info = null, timer = null;
const SRC = {tfl: ['London', 'Transport for London JamCams', 'Powered by TfL Open Data'],
  nyc: ['New York', 'NYC DOT traffic cameras', 'NYC DOT'],
  caltrans: ['California', 'Caltrans CCTV', 'Caltrans'],
  sg: ['Singapore', 'Land Transport Authority traffic images', 'Singapore Open Data Licence'],
  hk: ['Hong Kong', 'Transport Department traffic snapshots', 'DATA.GOV.HK'],
  fi: ['Finland', 'Fintraffic road weather cameras (Digitraffic)', 'CC BY 4.0']};
const imgUrl = (c, u) => c.src === 'sg' ? '/api/cam/image?sg=' + encodeURIComponent(c.id.slice(3)) : '/api/cam/image?u=' + encodeURIComponent(u);

export default {
  id: 'cameras', title: 'Cameras', color: ['#0071a4', '#64d2ff'], feeds: {cameras: 21600}, defaultOff: true,
  layers: ['ww-cams'],
  about: () => 'Public road and traffic cameras published by London, New York, California, Singapore, Hong Kong and Finland.',
  addTo(map) {
    map.addSource('ww-cams', {type: 'geojson', data: {type: 'FeatureCollection', features: []}});
    map.addLayer({id: 'ww-cams', type: 'circle', source: 'ww-cams',
      paint: {'circle-radius': ['interpolate', ['linear'], ['zoom'], 3, 2, 10, 5.5, 14, 8], 'circle-stroke-width': ['interpolate', ['linear'], ['zoom'], 5, 0, 9, 1.2]}});
  },
  paint(map, dark) {
    map.setPaintProperty('ww-cams', 'circle-color', this.color[+dark]);
    map.setPaintProperty('ww-cams', 'circle-stroke-color', dark ? '#1c1c1e' : '#ffffff');
  },
  onData(feed, d) { info = d; cams = d.payload.cameras || []; byId = new Map(cams.map(c => [c.id, c])); },
  render(map) {
    map.getSource('ww-cams').setData({type: 'FeatureCollection', features: cams.map(c => ({type: 'Feature', geometry: {type: 'Point', coordinates: [c.lon, c.lat]}, properties: {id: c.id}}))});
  },
  count: () => cams.length,
  rows: () => [],
  owns: id => byId.has(id),
  locate(id) { const c = byId.get(id); return c && [c.lon, c.lat]; },
  ring: () => 10,
  detail(id) {
    const c = byId.get(id); if (!c) return null;
    const s = SRC[c.src] || [c.src, c.src, ''];
    const pics = c.img.map((u, i) => `<div class="photo cam-pic"><img data-cam="${esc(imgUrl(c, u))}" src="${esc(imgUrl(c, u))}&t=${Date.now()}" alt="Camera picture${c.img.length > 1 ? ' ' + (i + 1) : ''}" onerror="this.closest('.cam-pic').innerHTML='<p class=pic-wait>The camera did not send a picture just now.</p>'"></div>`).join('');
    const video = c.video ? (c.src === 'caltrans'
      ? `<video class="cam-video" src="${esc(c.video)}" controls muted playsinline preload="none"></video><p class="source">Live stream from Caltrans' own server (HLS: plays in Safari; other browsers may not play it).</p>`
      : `<video class="cam-video" src="${esc(c.video)}" controls muted playsinline loop preload="none"></video><p class="source">A short clip TfL refreshes every few minutes, played from TfL's own server.</p>`) : '';
    return `<p class="eyebrow">Public camera · ${esc(s[0])}</p><h2>${esc(c.name || 'Camera')}</h2>
      <p class="where">${[c.area, c.view && 'facing ' + c.view].filter(Boolean).map(esc).join(' · ')}</p>
      <div id="camwrap">${pics}</div>
      <p class="soft" id="camstamp">Picture as the camera sent it when this card opened; refreshed every 30 seconds while open.</p>
      ${video}
      <p class="source">Source: ${esc(s[1])} (${esc(s[2])}); camera list read ${ago(info?.fetched)}. Fetched through this server. Only cameras their operators publish for everyone are shown.</p>`;
  },
  fill(id) {
    clearInterval(timer);
    timer = setInterval(() => {
      const imgs = document.querySelectorAll('#camwrap img[data-cam]');
      if (!imgs.length) { clearInterval(timer); return; }
      imgs.forEach(im => { im.src = im.dataset.cam + '&t=' + Date.now(); });
      const st = document.getElementById('camstamp'); if (st) st.textContent = 'Refreshed ' + new Date().toLocaleTimeString('en-GB') + '; again in 30 seconds.';
    }, 30000);
  },
};
