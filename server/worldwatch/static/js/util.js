// Small helpers: fetching from our own server, and telling time honestly.

let skew = 0;   // server clock minus this browser's clock, so ages are right even if this device's clock is off

export async function api(path) {
  const t0 = Date.now();
  const r = await fetch(path, {cache: 'no-store'});
  if (!r.ok) throw new Error(path + ' answered ' + r.status);
  const d = await r.json();
  if (typeof d.now === 'number') skew = d.now - (t0 + Date.now()) / 2000;
  return d;
}

export const now = () => Date.now() / 1000 + skew;

export function ago(t, n = now()) {
  const s = n - t, a = Math.abs(s);
  const v = a < 90 ? Math.max(0, Math.round(a)) + ' s' : a < 5400 ? Math.round(a / 60) + ' min'
    : a < 172800 ? (a / 3600).toFixed(a < 36000 ? 1 : 0) + ' h' : Math.round(a / 86400) + ' d';
  return s < 0 ? 'in ' + v : v + ' ago';
}

const pad = n => String(n).padStart(2, '0');
// Local time of whoever is looking, with the date only when it is not today.
export function local(t) {
  const d = new Date(t * 1000), today = new Date(now() * 1000);
  const hm = pad(d.getHours()) + ':' + pad(d.getMinutes());
  return d.toDateString() === today.toDateString() ? hm : d.toLocaleDateString('en-GB', {day: 'numeric', month: 'short'}) + ', ' + hm;
}
export const utc = t => new Date(t * 1000).toISOString().slice(11, 16) + ' UTC';

export const esc = s => String(s ?? '').replace(/[&<>"]/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;'}[c]));
export const $ = s => document.querySelector(s);

// NASA's daily true-colour picture of the area around a point (NOAA-20 VIIRS via GIBS, about 375 m per pixel,
// one picture a day around early afternoon local time). Used in news, unrest and disaster cards. Not a live camera.
const GIBS = 'https://gibs.earthdata.nasa.gov/wms/epsg4326/best/wms.cgi?SERVICE=WMS&REQUEST=GetMap&VERSION=1.3.0&STYLES=&CRS=EPSG:4326&FORMAT=image/jpeg&LAYERS=VIIRS_NOAA20_CorrectedReflectance_TrueColor&WIDTH=640&HEIGHT=400';
const dayStr = back => new Date(Date.now() - back * 86400000).toISOString().slice(0, 10);
export function skyUrl(lat, lon, back) {
  const h = 0.75, w = h * 1.6 / Math.max(0.3, Math.cos(lat * Math.PI / 180));   // ~165 km tall, same width on the ground
  return `${GIBS}&TIME=${dayStr(back)}&BBOX=${(lat - h).toFixed(3)},${(lon - w).toFixed(3)},${(lat + h).toFixed(3)},${(lon + w).toFixed(3)}`;
}
export function skyShot(lat, lon) {
  return `<figure class="sky" data-lat="${lat}" data-lon="${lon}"><div class="sky-img"><img src="${skyUrl(lat, lon, 1)}" alt="Satellite picture of the area" loading="lazy"><span class="sky-pin"></span></div>
    <figcaption><span>From space, about 165 km across</span><span class="sky-days">${[2, 1, 0].map(b => `<button data-sky="${b}" aria-pressed="${b === 1}">${b === 0 ? 'Today' : b === 1 ? 'Yesterday' : dayStr(b).slice(5)}</button>`).join('')}</span></figcaption>
    <p class="source">NASA GIBS, NOAA-20 VIIRS true colour of ${'<span class="sky-date">' + dayStr(1) + '</span>'} (UTC day), about 375 m per pixel, taken once a day around early afternoon local time. Clouds are real; "Today" is blank where the satellite has not passed yet.</p></figure>`;
}
document.addEventListener('click', e => {
  const b = e.target.closest('[data-sky]'); if (!b) return;
  const f = b.closest('.sky'), back = +b.dataset.sky;
  f.querySelector('img').src = skyUrl(+f.dataset.lat, +f.dataset.lon, back);
  f.querySelector('.sky-date').textContent = dayStr(back);
  f.querySelectorAll('[data-sky]').forEach(x => x.setAttribute('aria-pressed', x === b));
});
