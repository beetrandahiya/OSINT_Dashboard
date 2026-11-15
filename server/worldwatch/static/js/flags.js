// Flags for planes, ships and satellites, from the official allocation tables our server keeps (feed "flags"):
// aircraft by transponder address block (ICAO), ships by the country digits of their MMSI (ITU), satellites by
// CelesTrak's owner code or the UCS database's country. Shown as emoji, and drawn into small map icons on demand.
let T = null, loading = null;
const hexCache = new Map();
export function loadFlags() {
  if (!loading) loading = fetch('/api/data/flags').then(r => r.json()).then(d => { T = d.payload || null; document.dispatchEvent(new Event('ww-flags')); }).catch(() => { loading = null; });
  return loading;
}
export const ready = () => !!T;
export function emoji(cc) {
  if (!cc || cc.length !== 2) return '';
  return String.fromCodePoint(...[...cc.toUpperCase()].map(c => 0x1F1E6 + c.charCodeAt(0) - 65));
}
export function planeFlag(hex) {
  if (!T?.icao || !hex) return null;
  if (hexCache.has(hex)) return hexCache.get(hex);
  const n = parseInt(hex, 16); let lo = 0, hi = T.icao.length - 1, hit = null;
  while (lo <= hi) { const m = (lo + hi) >> 1, r = T.icao[m]; if (n < r[0]) hi = m - 1; else if (n > r[1]) lo = m + 1; else { hit = {cc: r[2], name: r[3]}; break; } }
  hexCache.set(hex, hit); return hit;
}
export function shipFlag(mmsi) {
  const s = String(mmsi || ''); if (!T?.mid || s.length !== 9) return null;
  const m = T.mid[s.slice(0, 3)]; return m ? {cc: m[0], name: m[1]} : null;
}
// Satellites: a list, since some are joint (the ISS has five partners).
export function satFlags(owner, ucsFlags) {
  const o = owner && T?.owners?.[owner];
  if (o && o[0].length) return {ccs: o[0], name: o[1]};
  if (ucsFlags?.length) return {ccs: ucsFlags, name: null};
  return o ? {ccs: [], name: o[1]} : null;
}
export const flagText = f => f ? (f.ccs ? f.ccs.map(emoji).join('') : emoji(f.cc)) : '';
// One place that turns a country code into a flag on a card, so emoji can be swapped for drawn flags later.
export function flagMark(cc, name) {
  if (!cc || !/^[A-Za-z]{2}$/.test(cc)) return '';
  const label = String(name || cc.toUpperCase()).replace(/[<>"&]/g, '');
  return `<span class="flag" role="img" aria-label="Flag of ${label}" title="${label}">${emoji(cc)}</span>`;
}
