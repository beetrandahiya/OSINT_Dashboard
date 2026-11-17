// Tunables in one place, so a settings sheet can drive them later (none is shown in the page yet). Stored per computer
// in localStorage 'ww-prefs' as JSON; anything missing or unreadable falls back to the defaults below.
//
//   lowPower    one switch for a quiet machine: no continuous animation (hijack streaks, hotspot pulse), every
//               background update at least twice as slow, the status poll every 30 s, the list capped at 100 rows.
//               Ages stay true: a slower refresh only means the "x min ago" grows.
//   animations  false: the same animations off without the slower updates.
//   fps         frame cap for the canvas animations (hijack streaks). The map itself is not capped.
//   maxModels   most 3D aircraft models drawn at once, nearest the middle of the map first (Infinity: every one on screen).
//   listRows    rows the list draws before a "Show all" row.
//   rate        multiplier on every background update interval (1 = as fast as the data changes; 2 = half as often).
const DEFAULTS = {lowPower: false, animations: true, fps: 30, maxModels: Infinity, listRows: 150, rate: 1};

function read() {
  try {
    const o = JSON.parse(localStorage.getItem('ww-prefs') || '{}');
    const out = {};
    for (const [k, v] of Object.entries(DEFAULTS)) if (o && typeof o[k] === typeof v && (typeof v !== 'number' || o[k] > 0)) out[k] = o[k];
    if (o && o.maxModels === null) out.maxModels = Infinity;      // JSON has no Infinity
    return out;
  } catch (e) { return {}; }    // private window, or not JSON
}

export const prefs = {...DEFAULTS, ...read()};
const reduce = matchMedia('(prefers-reduced-motion: reduce)');

// continuous animation allowed? (system Reduce Motion, the animations switch, low power)
export const moving = () => prefs.animations && !prefs.lowPower && !reduce.matches;
// the factor on update intervals
export const rate = () => Math.max(0.25, prefs.rate) * (prefs.lowPower ? 2 : 1);
export const listRows = () => prefs.lowPower ? Math.min(100, prefs.listRows) : prefs.listRows;
export const fpsCap = () => Math.max(1, prefs.fps);
export const maxModels = () => prefs.lowPower ? Math.min(100, prefs.maxModels) : prefs.maxModels;
export const statusEvery = () => (prefs.lowPower ? 30 : 5) * 1000;

// change and remember; 'ww-prefs' tells the loops to look again
export function setPrefs(p) {
  Object.assign(prefs, p);
  try { localStorage.setItem('ww-prefs', JSON.stringify({...prefs, maxModels: prefs.maxModels === Infinity ? null : prefs.maxModels})); } catch (e) { /* private window */ }
  document.dispatchEvent(new Event('ww-prefs'));
}
const changed = () => { document.documentElement.classList.toggle('ww-still', !moving()); document.dispatchEvent(new Event('ww-motion')); };
reduce.addEventListener('change', changed);
document.addEventListener('ww-prefs', changed);
changed();

// One clock for the small background polls (hotspots, orbits, sanctioned, breaking news, leaders, markets...): nothing
// runs while the tab is hidden (Safari slows hidden timers but does not stop them), jobs that came due meanwhile run
// once when it shows again, and intervals follow `rate()`.
const jobs = [];
export function every(secs, fn, {scaled = true, now = false} = {}) {
  const job = {secs, fn, scaled, last: now ? 0 : performance.now()};
  jobs.push(job);
  if (now && !document.hidden) { job.last = performance.now(); fn(); }
  return () => { const i = jobs.indexOf(job); if (i >= 0) jobs.splice(i, 1); };
}
function run() {
  if (document.hidden) return;
  const t = performance.now();
  for (const j of [...jobs]) if (t - j.last >= j.secs * 1000 * (j.scaled ? rate() : 1)) { j.last = t; try { j.fn(); } catch (e) { console.error(e); } }
}
setInterval(run, 1000);
document.addEventListener('visibilitychange', run);
