// Listening stations: public KiwiSDR shortwave receivers (0-30 MHz) that their owners list for anyone to tune.
// The card opens the receiver's own web page in a new tab, optionally tuned to a well-known public broadcast.
import {eyeImages, eyeSwap, addEye} from './eyeicons.js';
import {ago, esc} from './util.js';

let rx = [], byId = new Map(), info = null;
// Public broadcasts documented on Wikipedia and in amateur logs. Whether anything is on air when you tune is up to them.
const TUNE = [
  ['4625usb', '4625 kHz', 'UVB-76, "The Buzzer"', 'Russian military channel: a buzz, with rare voice messages'],
  ['8992usb', '8992 kHz', 'HFGCS', 'US Air Force High Frequency Global Communications System (also 11175 kHz)'],
  ['11175usb', '11175 kHz', 'HFGCS', 'US Air Force, the busiest HFGCS frequency'],
  ['5505usb', '5505 kHz', 'Shannon VOLMET', 'Irish weather broadcasts for aircraft over the Atlantic'],
  ['10000am', '10000 kHz', 'WWV / time signals', 'Standard time and frequency stations'],
];
const tuned = (u, f) => u.replace(/\/+$/, '') + '/?f=' + f;

export default {
  id: 'sdr', title: 'Listening stations', color: ['#008a7a', '#40d9c4'], feeds: {sdr: 3600}, layers: ['ww-sdr', 'ww-sdr-eye'], defaultOff: true,
  about: () => 'Public shortwave radio receivers (KiwiSDR) that anyone can tune in their browser.',
  addTo(map) {
    map.addSource('ww-sdr', {type: 'geojson', data: {type: 'FeatureCollection', features: []}});
    map.addLayer({id: 'ww-sdr', type: 'circle', source: 'ww-sdr',
      paint: {'circle-radius': ['interpolate', ['linear'], ['zoom'], 1, 2.5, 6, 5, 10, 7], 'circle-stroke-width': 1,
        'circle-opacity': ['case', ['==', ['get', 'full'], true], 0.35, 0.95]}});
  },
  paint(map, dark) {
    if (!map.getLayer('ww-sdr-eye')) addEye(map, 'ww-sdr-eye', 'ww-sdr', 'eye-sdr', ['interpolate', ['linear'], ['zoom'], 2, 0.24, 8, 0.5], {opacity: ['case', ['==', ['get', 'full'], true], 0.4, 1]});
    eyeImages(map, dark); eyeSwap(map, ['ww-sdr-eye'], ['ww-sdr']);
    map.setPaintProperty('ww-sdr', 'circle-color', this.color[+dark]);
    map.setPaintProperty('ww-sdr', 'circle-stroke-color', dark ? '#1c1c1e' : '#ffffff');
  },
  onData(feed, d) { info = d; rx = d.payload.receivers || []; byId = new Map(rx.map(r => ['sdr:' + r.id, r])); },
  render(map) {
    map.getSource('ww-sdr').setData({type: 'FeatureCollection', features: rx.map(r => ({type: 'Feature', geometry: {type: 'Point', coordinates: [r.lon, r.lat]},
      properties: {id: 'sdr:' + r.id, full: !!(r.max && r.users >= r.max)}}))});
  },
  count: () => rx.length,
  rows: () => [],
  owns: id => byId.has(id),
  locate(id) { const r = byId.get(id); return r && [r.lon, r.lat]; },
  ring: () => 9,
  detail(id) {
    const r = byId.get(id); if (!r) return null;
    const full = r.max && r.users >= r.max, mhz = v => v == null ? '?' : (v / 1e6).toLocaleString('en-GB', {maximumFractionDigits: 1});
    return `<p class="eyebrow">Listening station · KiwiSDR</p><h2>${esc(r.name)}</h2><p class="where">${esc(r.loc || '')}</p>
      <dl><dt>Listeners now</dt><dd>${r.users} of ${r.max || '?'}${full ? ' <span class="soft">(full: try again later or pick another)</span>' : ''}</dd>
        <dt>Covers</dt><dd>${mhz(r.band[0])} to ${mhz(r.band[1])} MHz (shortwave)</dd>
        ${r.antenna ? `<dt>Antenna</dt><dd>${esc(r.antenna)}</dd>` : ''}
        ${r.snr ? `<dt>Signal to noise</dt><dd>${esc(r.snr)} dB <span class="soft">(as the receiver reports it; higher is cleaner)</span></dd>` : ''}
        ${r.asl ? `<dt>Height</dt><dd>${esc(String(r.asl))} m above sea level</dd>` : ''}</dl>
      <p class="links"><a class="link" href="${esc(r.url)}" target="_blank" rel="noopener">Open the receiver and listen</a></p>
      <section class="pz"><h3>Tune it straight to</h3><ul class="pz-list">${TUNE.map(([f, k, n, what]) =>
        `<li><a href="${esc(tuned(r.url, f))}" target="_blank" rel="noopener">${esc(n)}</a> <span class="soft">· ${k} · ${esc(what)}</span></li>`).join('')}</ul>
      <p class="source">Well-known public broadcasts (frequencies from Wikipedia and amateur logs). Whether anything is on air, and whether this receiver hears it from here, varies with time of day and propagation.</p></section>
      <p class="source">Source: the public receiver list of kiwisdr.com (via rx.linkfanel.net), list made ${ago(info?.data_time)}. Each receiver is run by a private owner who chose to share it; it opens in their own page, in a new tab. Only receivers marked online with a position are shown.</p>`;
  },
};
