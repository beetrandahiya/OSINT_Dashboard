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
