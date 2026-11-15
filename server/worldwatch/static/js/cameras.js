// Public road and traffic cameras that their operators publish openly (TfL, NYC DOT, Caltrans, Singapore LTA, Hong
// Kong Transport Department, Fintraffic). Pictures are fetched through our server when a card opens and refreshed
// while it stays open. No private or unsecured cameras, ever.
import {ago, esc} from './util.js';

let cams = [], byId = new Map(), info = null, timer = null, windy = [], windyNote = null;
const SRC = {tfl: ['London', 'Transport for London JamCams', 'Powered by TfL Open Data'],
  nyc: ['New York', 'NYC DOT traffic cameras', 'NYC DOT'],
  caltrans: ['California', 'Caltrans CCTV', 'Caltrans'],
  sg: ['Singapore', 'Land Transport Authority traffic images', 'Singapore Open Data Licence'],
  hk: ['Hong Kong', 'Transport Department traffic snapshots', 'DATA.GOV.HK'],
  fi: ['Finland', 'Fintraffic road weather cameras (Digitraffic)', 'CC BY 4.0']};
// how often each operator publishes a new still (their pages / our measurement), so the card does not ask more often
const EVERY = {nyc: 3, hk: 60, sg: 20, fi: 60, tfl: 60, caltrans: 30};
const STILL = {nyc: 'NYC DOT cameras publish a new still picture every second or two; there is no video.', hk: 'The Transport Department publishes a new still every two minutes.',
  sg: 'The LTA publishes a new still every 20 seconds or so.', fi: 'Fintraffic weather cameras take a picture about every 10 minutes.'};
const imgUrl = (c, u) => c.src === 'sg' ? '/api/cam/image?sg=' + encodeURIComponent(c.id.slice(3)) : '/api/cam/image?u=' + encodeURIComponent(u);

export default {
  id: 'cameras', title: 'Cameras', color: ['#0071a4', '#64d2ff'], feeds: {cameras: 21600}, defaultOff: true,
  layers: ['ww-cams', 'ww-cams-windy'],
  about: () => 'Public cameras: road and traffic cameras of London, New York, California, Singapore, Hong Kong and Finland, and, with a free key, Windy\'s public webcams worldwide (from zoom 5).',
  addTo(map) {
    map.addSource('ww-cams', {type: 'geojson', data: {type: 'FeatureCollection', features: []}});
    map.addLayer({id: 'ww-cams', type: 'circle', source: 'ww-cams',
      paint: {'circle-radius': ['interpolate', ['linear'], ['zoom'], 3, 2, 10, 5.5, 14, 8], 'circle-stroke-width': ['interpolate', ['linear'], ['zoom'], 5, 0, 9, 1.2]}});
    // Windy's public webcams worldwide (free key): asked for the box on screen from zoom 5, up to 50 at a time
    map.addSource('ww-cams-windy', {type: 'geojson', data: {type: 'FeatureCollection', features: []}});
    map.addLayer({id: 'ww-cams-windy', type: 'circle', source: 'ww-cams-windy', minzoom: 5,
      paint: {'circle-radius': ['interpolate', ['linear'], ['zoom'], 5, 3.5, 10, 6, 14, 8], 'circle-stroke-width': 1.2}});
    let busy = false, again = false;
    const pull = async () => {
      if (map.getZoom() < 5 || map.getLayoutProperty('ww-cams', 'visibility') === 'none') return;
      if (busy) { again = true; return; }
      busy = true;
      const b = map.getBounds();
      try {
        const r = await fetch(`/api/cam/windy?n=${b.getNorth()}&e=${b.getEast()}&s=${b.getSouth()}&w=${b.getWest()}`).then(x => x.json());
        windyNote = r.error || (r.total > (r.cams || []).length ? `${r.total} Windy cameras in this area; the ${(r.cams || []).length} most popular are shown (the free key gives 50 at a time). Zoom in for others.` : null);
        if (r.cams?.length || !r.error) {
          windy = r.cams || [];
          for (const c of windy) byId.set(c.id, c);
          map.getSource('ww-cams-windy').setData({type: 'FeatureCollection', features: windy.map(c => ({type: 'Feature', geometry: {type: 'Point', coordinates: [c.lon, c.lat]}, properties: {id: c.id}}))});
        }
      } catch (e) { /* next move asks again */ }
      busy = false;
      if (again) { again = false; pull(); }
    };
    map.on('moveend', pull);
    this.pull = pull;
  },
  visible(on) { if (on) this.pull?.(); },
  paint(map, dark) {
    map.setPaintProperty('ww-cams', 'circle-color', this.color[+dark]);
    map.setPaintProperty('ww-cams', 'circle-stroke-color', dark ? '#1c1c1e' : '#ffffff');
    map.setPaintProperty('ww-cams-windy', 'circle-color', dark ? '#5ac8fa' : '#0a84ff');
    map.setPaintProperty('ww-cams-windy', 'circle-stroke-color', dark ? '#1c1c1e' : '#ffffff');
  },
  onData(feed, d) { info = d; cams = d.payload.cameras || []; byId = new Map([...cams, ...windy].map(c => [c.id, c])); },
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
    if (c.src === 'windy') {
      return `<p class="eyebrow">Public webcam · Windy</p><h2>${esc(c.name || 'Webcam')}</h2><p class="where">${esc(c.area || '')}</p>
        ${c.player ? `<iframe class="windy-player" src="${esc(c.player)}" title="Windy webcam player" loading="lazy" allow="autoplay; fullscreen"></iframe>` : ''}
        <div id="windycam" data-wid="${esc(c.id.slice(6))}" ${c.player ? 'hidden' : ''}>${c.preview ? `<a href="${esc(c.page || 'https://www.windy.com/webcams')}" target="_blank" rel="noopener"><img class="windy-pic" src="${esc(c.preview)}" alt="Webcam picture"></a>` : '<p class="pic-wait">Loading the picture…</p>'}</div>
        <p class="soft">${c.updated ? 'Picture updated ' + ago(Date.parse(c.updated) / 1000) + '. ' : ''}${c.status && c.status !== 'active' ? 'Windy lists this camera as ' + esc(c.status) + '. ' : ''}The free Windy key gives small pictures only.</p>
        <p class="links">${c.page ? `<a class="link" href="${esc(c.page)}" target="_blank" rel="noopener">This webcam on Windy</a>` : ''}${c.player ? ` <a class="link" href="${esc(c.player)}" target="_blank" rel="noopener">Today's time-lapse</a>` : ''}</p>
        ${windyNote ? `<p class="source">${esc(windyNote)}</p>` : ''}
        <p class="source">Webcams provided by <a class="link" href="https://windy.com" target="_blank" rel="noopener">Windy.com</a> — <a class="link" href="https://www.windy.com/webcams/add" target="_blank" rel="noopener">add a webcam</a>. Public webcams their owners chose to share on Windy.</p>`;
    }
    const s = SRC[c.src] || [c.src, c.src, ''];
    const pics = c.img.map((u, i) => `<div class="photo cam-pic"><img data-cam="${esc(imgUrl(c, u))}" src="${esc(imgUrl(c, u))}&t=${Date.now()}" alt="Camera picture${c.img.length > 1 ? ' ' + (i + 1) : ''}" onerror="this.closest('.cam-pic').innerHTML='<p class=pic-wait>The camera did not send a picture just now.</p>'"></div>`).join('');
    // Moving pictures play right here: TfL's clip and Caltrans' live stream start by themselves (muted, as browsers
    // require for autoplay); the still is shown underneath until they load
    const video = c.video ? (c.src === 'caltrans'
      ? `<video class="cam-video" src="${esc(c.video)}" poster="${esc(imgUrl(c, c.img[0]))}" autoplay muted playsinline controls></video><p class="source">Live stream from Caltrans' own server (HLS: plays in Safari; other browsers may show only the still).</p>`
      : `<video class="cam-video" src="${esc(c.video)}" poster="${esc(imgUrl(c, c.img[0]))}" autoplay muted playsinline loop controls></video><p class="source">A short clip TfL replaces every few minutes, played from TfL's own server.</p>`) : '';
    return `<p class="eyebrow">Public camera · ${esc(s[0])}</p><h2>${esc(c.name || 'Camera')}</h2>
      <p class="where">${[c.area, c.view && 'facing ' + c.view].filter(Boolean).map(esc).join(' · ')}</p>
      ${video || `<div id="camwrap" data-every="${EVERY[c.src] || 30}">${pics}</div>
      <p class="soft" id="camstamp">${esc(STILL[c.src] || 'This camera publishes still pictures.')} Refreshed here every ${EVERY[c.src] || 30} seconds while this card is open.</p>`}
      <p class="source">Source: ${esc(s[1])} (${esc(s[2])}); camera list read ${ago(info?.fetched)}. Fetched through this server. Only cameras their operators publish for everyone are shown.</p>`;
  },
  async fill(id) {
    clearInterval(timer);
    const wc = document.getElementById('windycam');
    if (wc && !wc.dataset.done) {        // Windy's picture links expire after ~10 minutes: ask for a fresh one
      wc.dataset.done = '1';
      try {
        const c = await fetch('/api/cam/windy/' + wc.dataset.wid).then(r => r.json());
        if (document.getElementById('windycam') === wc && c.preview) wc.innerHTML = `<a href="${esc(c.page || 'https://www.windy.com/webcams')}" target="_blank" rel="noopener"><img class="windy-pic" src="${esc(c.preview)}" alt="Webcam picture"></a>`;
      } catch (e) { /* the list's picture stays */ }
      return;
    }
    const wrap = document.getElementById('camwrap'); if (!wrap) return;
    const every = +wrap.dataset.every || 30;
    timer = setInterval(() => {
      const imgs = document.querySelectorAll('#camwrap img[data-cam]');
      if (!imgs.length) { clearInterval(timer); return; }
      // load the next picture off-screen and swap it in when complete, so the picture never flashes blank
      imgs.forEach(im => { const n = new Image(); n.onload = () => { im.src = n.src; }; n.src = im.dataset.cam + '&t=' + Date.now(); });
    }, every * 1000);
  },
};
