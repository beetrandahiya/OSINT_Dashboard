// The look: theme, icon palette, ground under the map, panel motion. One place, stored per computer in localStorage
// 'ww-look', driven by the Settings sheet. Light and dark always follow the system (owner's choice, 2026-11-17).
//
//   theme    'apple'  Apple Maps (the original look)
//            'eye'    God's eye (thin framed panels, condensed capitals, cold graded ground)
//   palette  'A' colour per domain, 'C' the same colours muted (God's eye icons; B was dropped by the owner)
//   ground   'auto'   the theme's own: the map for Apple Maps, the graded photo for God's eye
//            'map' | 'photo' | 'mono' | 'lights' | 'relief' | 'outline'   (see GROUNDS in map.js)
//   motion   'off' | 'subtle' | 'full'   only panel text ever moves; map markers and their labels never do
const DEFAULTS = {theme: 'eye', palette: 'C', ground: 'auto', motion: 'subtle'};   // God's eye is the app's look; Apple Maps stays a choice in Settings
const ALLOWED = {theme: ['apple', 'eye'], palette: ['A', 'C'], ground: ['auto', 'map', 'photo', 'mono', 'lights', 'relief', 'outline'],
  motion: ['off', 'subtle', 'full']};

function read() {
  try {
    const o = JSON.parse(localStorage.getItem('ww-look') || '{}'), out = {};
    for (const k of Object.keys(DEFAULTS)) if (ALLOWED[k].includes(o?.[k])) out[k] = o[k];
    return out;
  } catch (e) { return {}; }
}
export const look = {...DEFAULTS, ...read()};

// the ground actually drawn
export const ground = () => look.ground !== 'auto' ? look.ground : look.theme === 'eye' ? 'photo' : 'map';

// God's eye type: Space Grotesk for headings and numbers, Inter for text (both free, Google Fonts, SIL OFL); loaded only
// while the theme is on (owner, 2026-11-18: "we had good fonts there")
function fonts() {
  if (look.theme !== 'eye') return;
  const href = 'https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=Inter:wght@400;500;600&display=swap';
  let link = document.getElementById('ww-fonts');
  if (!link) { link = document.createElement('link'); link.id = 'ww-fonts'; link.rel = 'stylesheet'; document.head.appendChild(link); }
  if (link.href !== href) link.href = href;
}

function apply() {
  const d = document.documentElement.dataset;
  d.theme = look.theme; d.palette = look.palette; d.motion = look.motion; d.ground = ground();
  fonts();
}
apply();

export function setLook(p) {
  for (const [k, v] of Object.entries(p)) if (ALLOWED[k]?.includes(v)) look[k] = v;
  try { localStorage.setItem('ww-look', JSON.stringify(look)); } catch (e) { /* private window */ }
  apply();
  document.dispatchEvent(new Event('ww-look'));
}

// the Settings sheet: built from the same lists, so a choice that exists here exists in the code
const GROUND_TEXT = {
  auto: ['Theme default', 'The map for Apple Maps, the graded photo for God\'s eye'],
  map: ['Map', 'OpenStreetMap drawing, recoloured for the theme'],
  photo: ['Photo', 'NASA Blue Marble (cloud-free composite) when zoomed out, Esri World Imagery closer in (each area from its own date)'],
  mono: ['Mono', 'The same photo without colour'],
  lights: ['Night lights', 'NASA Black Marble city lights, a composite of 2016, not tonight'],
  relief: ['Relief', 'NASA/METI ASTER shaded relief, grey'],
  outline: ['Outline', 'Coasts and borders only, on dark'],
};
const esc = s => String(s).replace(/[&<>"]/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;'}[c]));
function seg(key, opts) {
  return `<div class="seg wide set-seg" role="group" aria-label="${key}">${opts.map(([v, t]) =>
    `<button data-k="${key}" data-v="${v}" aria-pressed="${look[key] === v}">${esc(t)}</button>`).join('')}</div>`;
}
function body() {
  return `<header class="set-head"><h2>Settings</h2><button class="close" id="set-close" aria-label="Close"></button></header>
  <section><h3>Theme</h3>${seg('theme', [['apple', 'Apple Maps'], ['eye', 'God\'s eye']])}
    <p class="soft">Light and dark follow your Mac's setting in both themes.</p></section>
  <section><h3>Ground</h3><ul class="set-list">${Object.entries(GROUND_TEXT).map(([v, [t, s]]) =>
    `<li><button data-k="ground" data-v="${v}" aria-pressed="${look.ground === v}"><b>${esc(t)}</b><span>${esc(s)}</span></button></li>`).join('')}</ul></section>
  <section${look.theme === 'eye' ? '' : ' class="dim"'}><h3>God's eye</h3>
    <h4>Icon colours</h4>${seg('palette', [['A', 'A: colour per domain'], ['C', 'C: muted']])}
    <p class="soft">Colours of the God's eye symbols. Military aircraft keep their own ice tint in both.</p>
    <h4>Panel motion</h4>${seg('motion', [['off', 'Off'], ['subtle', 'Subtle'], ['full', 'Full']])}
    <p class="soft">Only panel text moves. Map symbols and their labels never move. Off as well when macOS Reduce Motion is on.</p>
</section>`;
}
export function openSettings() {
  let el = document.getElementById('settings');
  if (!el) {
    el = document.createElement('div'); el.id = 'settings'; el.className = 'glass settings'; el.setAttribute('role', 'dialog'); el.setAttribute('aria-label', 'Settings');
    document.body.appendChild(el);
    el.addEventListener('click', e => {
      const b = e.target.closest('button[data-k]');
      if (b) { setLook({[b.dataset.k]: b.dataset.v}); el.innerHTML = body(); return; }
      if (e.target.closest('#set-close')) closeSettings();
    });
  }
  el.innerHTML = body(); el.hidden = false;
}
export function closeSettings() { const el = document.getElementById('settings'); if (el && !el.hidden) { el.hidden = true; return true; } return false; }
export const settingsOpen = () => !document.getElementById('settings')?.hidden && !!document.getElementById('settings');
