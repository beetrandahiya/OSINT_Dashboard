// Flags for planes, ships and satellites, from the official allocation tables our server keeps (feed "flags"):
// aircraft by transponder address block (ICAO), ships by the country digits of their MMSI (ITU), satellites by
// CelesTrak's owner code or the UCS database's country. Shown as emoji, and drawn into small map icons on demand.
let T = null, loading = null;
const hexCache = new Map();
export function loadFlags() {
  if (!loading) loading = fetch('/api/data/flags').then(r => r.json()).then(d => {
    T = d.payload || null;
    if (T) document.dispatchEvent(new Event('ww-flags'));
    else { loading = null; setTimeout(loadFlags, 10000); }           // the server has not fetched the tables yet: ask again soon
  }).catch(() => { loading = null; setTimeout(loadFlags, 10000); });
  return loading;
}
export const ready = () => !!T;
// Plain, flat flags (flag-icons, MIT, vendored in static/flags) instead of the system's wavy emoji.
const FLAG_DIR = new URL('../flags/', import.meta.url).href;
export function flagImg(cc, title = '') {
  if (!cc || cc.length !== 2) return '';
  return `<img class="flagimg" src="${FLAG_DIR}${cc.toLowerCase()}.svg" alt="${cc}" title="${title.replace(/"/g, '&quot;')}" onerror="this.remove()">`;
}
export const flagsHtml = f => f ? (f.ccs ? f.ccs.map(c => flagImg(c, f.name || c)).join('') : flagImg(f.cc, f.name)) : '';
export function emoji(cc) {
  if (!cc || cc.length !== 2) return '';
  return String.fromCodePoint(...[...cc.toUpperCase()].map(c => 0x1F1E6 + c.charCodeAt(0) - 65));
}
export function planeFlag(hex) {
  if (!T?.icao || !hex) return null;
  if (hexCache.has(hex)) return hexCache.get(hex);
  // Blocks nest (the UK's contains Bermuda's, Gibraltar's...), so a binary search could miss the parent block and leave
  // e.g. RAF aircraft without a flag. 205 blocks: scan them all and take the smallest that holds the address.
  const clean = String(hex).replace(/[^0-9a-f]/gi, ''); if (clean.length !== 6) { hexCache.set(hex, null); return null; }
  const n = parseInt(clean, 16); let hit = null, size = Infinity;
  for (const r of T.icao) if (n >= r[0] && n <= r[1] && r[1] - r[0] < size) { size = r[1] - r[0]; hit = {cc: r[2], name: r[3]}; }
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
  return flagImg(cc, label);                      // plain SVG flag (flag-icons), not the wavy emoji
}
