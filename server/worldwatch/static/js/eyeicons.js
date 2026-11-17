// The God's eye icon set on the map: the 147 symbols of glyphs.js drawn into map images, in the solid treatment the
// owner approved ("today is alright": filled shapes with a dark edge in dark mode, a white edge in light mode; every
// piece's edge is drawn before any fill, so overlapping pieces join into one silhouette with no lines inside).
// Images are named 'eye-<id>' (own colour), 'eye-<id>-mil' (aircraft drawn in the military colour) and '-s' variants
// (aircraft at small sizes fall back to their simple class shape, as on the design boards).
import G from './glyphs.js';
import {look} from './look.js';

export const eyeOn = () => look.theme === 'eye';

// broadcast ICAO type code -> aircraft symbol (only real codes: the descriptive "codes" text of vip / mil_generic /
// ground is not a code list)
const CODE = new Map();
for (const [id, s] of Object.entries(G.lib)) {
  if (s.grp !== 'Aircraft' || !s.c || ['vip', 'mil_generic', 'ground', 'doomsday'].includes(id)) continue;
  for (const t of s.c.split(/\s+/)) if (/^[A-Z0-9-]{2,}$/.test(t)) CODE.set(t, id);
}
// the category the aircraft broadcasts, when its type code is not in the table
const BY_CAT = {A1: 'light', A2: 'bizjet', A3: 'narrow', A4: 'narrow', A5: 'wide', A6: 'fighter', A7: 'heli_med', B1: 'glider', B2: 'balloon', B4: 'light', B6: 'male', C1: 'ground', C2: 'ground', C3: 'ground'};
export function aircraftSymbol(a, mil) {
  return CODE.get(String(a.type || '').toUpperCase()) || BY_CAT[a.category] || (mil ? 'mil_generic' : 'narrow');
}
export const turns = id => !!G.lib[id]?.r;     // symbols with a nose turn to the heading

function paint(pieces, col, ink, acc, px) {
  const c = document.createElement('canvas'); c.width = c.height = px;
  const x = c.getContext('2d'); x.scale(px / 64, px / 64); x.lineJoin = 'round';
  const ps = pieces.map(([d, m]) => [new Path2D(d), m]);
  x.strokeStyle = ink;
  for (const [p, m] of ps) {
    if (m === 'f' || m === 'x') { x.lineWidth = 6; x.lineCap = 'butt'; x.stroke(p); }
    if (m === 's' || m === 'd') { x.lineWidth = 11; x.lineCap = 'round'; x.stroke(p); }
  }
  for (const [p, m] of ps) {
    if (m === 'f') { x.fillStyle = col; x.fill(p); }
    else if (m === 'k') { x.fillStyle = ink; x.fill(p); }
    else if (m === 's') { x.strokeStyle = col; x.lineWidth = 6; x.lineCap = 'round'; x.setLineDash([]); x.stroke(p); }
    else if (m === 'd') { x.strokeStyle = col; x.lineWidth = 5; x.lineCap = 'butt'; x.setLineDash([7, 6]); x.stroke(p); x.setLineDash([]); }
    else if (m === 'a') { x.globalAlpha = 0.35; x.fillStyle = col; x.fill(p); x.globalAlpha = 1; x.strokeStyle = col; x.lineWidth = 3; x.stroke(p); }
    else if (m === 'x') { x.fillStyle = acc; x.fill(p); }
  }
  return x.getImageData(0, 0, px, px);
}

// colour of a palette key in the current palette and mode (for halos, rings and labels of the new set)
export const eyeColour = (key, dark) => G.pal[look.palette][dark ? 'dark' : 'light'][key];

let done = '';
export function eyeImages(map, dark) {
  const key = look.palette + (dark ? 'd' : 'l');
  if (done === key && map.hasImage('eye-narrow')) return;
  done = key;
  const mode = dark ? 'dark' : 'light', P = G.pal[look.palette][mode], ink = G.ink[mode];
  const put = (name, img) => { if (map.hasImage(name)) map.updateImage(name, img); else map.addImage(name, img, {pixelRatio: 2}); };
  for (const [id, s] of Object.entries(G.lib)) {
    const acc = P[G.acc[id] || 'warn'];
    put('eye-' + id, paint(s.g, P[s.k], ink, acc, 64));
    if (s.grp === 'Aircraft') {
      put('eye-' + id + '-mil', paint(s.g, P.mil, ink, acc, 64));
      const sm = G.small[s.sm] || s.g;
      put('eye-' + id + '-s', paint(sm, P[s.k], ink, acc, 64));
      put('eye-' + id + '-s-mil', paint(sm, P.mil, ink, acc, 64));
    }
  }
}
