// The God's eye "Dense" layout (owner's pick, 2026-11-18; every screen drawn on the design canvas first).
// One column on the right (the open card on top, then the layer tiles and the list), a top bar (title, the view's name,
// search, feeds, map shape, 3D, Settings), a strip of views along the bottom and a sheet with every layer and its key.
// Apple Maps keeps its own layout: this module moves the same page elements into the God's eye places and back, so every
// listener and every layer keeps working in both themes.
import {esc} from './util.js';
import {eyeOn, glyphSvg} from './eyeicons.js';
import {renderLegend} from './legend.js';

const $ = s => document.querySelector(s);
let ctx = null;                 // {map, CHIPS, on, toggle(id), status(), dark()}
const home = new Map();         // element -> [parent, next sibling] in the Apple Maps layout

// ---- layers: icon and group for every chip ----
export const ICON = {hotspots: 'hotspot', news: 'news', spikes: 'breaking', unrest: 'clash', unrest1: 'protest', front: 'frontchange', navwarn: 'nw_weapons',
  airspace: 'as_avoid', quakes: 'quake_m', hazards: 'cyclone', outages: 'outage', hijacks: 'hijack', bases: 'airbase', nuclear: 'nuke', aircraft: 'narrow',
  military: 'mil_generic', orbits: 'awacs', tankers: 'tanker', vip: 'vip', doomsday: 'doomsday', satellites: 'sat_img', launches: 'launch', ships: 'cargo',
  warships: 'warship_s', sanctioned: 'sanctioned', cameras: 'camera', sdr: 'sdr', people: 'head', leaders: 'leader', fires: 'fire', gps: 'gps', gpslive: 'gps',
  cables: 'cable', rain: 'storm', lightning: 'lightning'};
const GROUPS = [['Conflict', ['hotspots', 'unrest', 'unrest1', 'front', 'spikes', 'news']], ['Air', ['aircraft', 'military', 'vip', 'doomsday', 'orbits', 'tankers', 'airspace']],
  ['Sea', ['ships', 'warships', 'sanctioned', 'navwarn']], ['Space', ['satellites', 'launches']], ['Networks', ['outages', 'hijacks', 'cables', 'gps', 'gpslive']],
  ['Earth', ['quakes', 'hazards', 'fires', 'rain', 'lightning']], ['Sites', ['bases', 'nuclear', 'cameras', 'sdr']], ['People', ['people', 'leaders']],
  ['Pictures and sky', ['photo', 'livephoto', 'sharp', 'night', 'aurora']]];
const icon = (l, px = 24) => ICON[l.id] ? glyphSvg(ICON[l.id], px, ctx.dark(), l.id === 'military' ? 'mil' : null)
  : `<span class="tile-swatch" style="--c:${l.color[+ctx.dark()]}"></span>`;

// source, state and age of a layer, from the feeds it reads
const AGO = s => s < 90 ? Math.max(1, Math.round(s)) + ' s' : s < 5400 ? Math.round(s / 60) + ' min' : s < 172800 ? (s / 3600).toFixed(s < 36000 ? 1 : 0) + ' h' : Math.round(s / 86400) + ' d';
function feedOf(l) {
  const st = ctx.status(); if (!st) return null;
  const names = Object.keys(l.feeds || {});
  const f = names.map(n => st.feeds.find(x => x.name === n)).filter(Boolean);
  if (!f.length) return l.local ? {source: 'computed here', state: 'ok', age: ''} : null;
  const worst = f.find(x => x.state === 'failing') || f.find(x => x.state === 'late') || f.find(x => x.state === 'waiting') || f[0];
  const t = worst.data_time || worst.fetched;
  const notSet = /not set up/.test(worst.error || '');
  return {source: worst.source.split(/[,(]/)[0].trim(), state: notSet ? 'off' : worst.state === 'failing' ? 'fail' : worst.state, age: notSet ? 'not set up' : t ? AGO(st.now - t) : 'waiting'};
}
const dot = s => `<span class="sdot s-${s || 'ok'}"></span>`;

// the tiles in the column: the layers that are on, each with its count, source and age; the rest are in the sheet
export function tiles(counts) {
  if (!ctx) return "";
  const on = ctx.CHIPS.filter(l => ctx.on[l.id]);
  return on.map(l => {
    const f = feedOf(l);
    return `<button class="chip tile${f && f.state !== 'ok' ? ' t-' + f.state : ''}" data-id="${l.id}" aria-pressed="true" title="${esc(l.about ? l.about() : l.title)}">${icon(l, 26)}
      <span class="t-main"><span class="t-name">${esc(l.title)}</span><span class="t-n">${esc(counts(l))}</span></span>
      <span class="t-src">${f ? dot(f.state) + `<span>${esc(f.source)}</span><span>${esc(f.age)}</span>` : ''}</span></button>`;
  }).join('') + `<button class="tile tile-all" data-all>All layers<span>${on.length} of ${ctx.CHIPS.length} on</span></button>`;
}

// The same tiles again with only counts, ages and states changed: patched in place, so the column is not rebuilt
// (and its icons not parsed again) on every feed answer. False when the set of tiles differs: then main.js redraws.
export function patchTiles(counts, box) {
  if (!ctx || !box) return false;
  const on = ctx.CHIPS.filter(l => ctx.on[l.id]), els = box.querySelectorAll('.tile[data-id]');
  if (els.length !== on.length || box.dataset.look !== lookKey()) return false;
  for (let i = 0; i < on.length; i++) if (els[i].dataset.id !== on[i].id) return false;
  on.forEach((l, i) => {
    const e = els[i], f = feedOf(l), cls = 'chip tile' + (f && f.state !== 'ok' ? ' t-' + f.state : '');
    if (e.className !== cls) e.className = cls;
    const n = e.querySelector('.t-n'), c = String(counts(l)); if (n && n.textContent !== c) n.textContent = c;
    const src = e.querySelectorAll('.t-src span');
    if (f && src.length === 3) {
      const d = 'sdot s-' + (f.state || 'ok'); if (src[0].className !== d) src[0].className = d;
      if (src[1].textContent !== f.source) src[1].textContent = f.source;
      if (src[2].textContent !== f.age) src[2].textContent = f.age;
    } else if (!!f !== (src.length === 3)) return false;
  });
  const all = box.querySelector('.tile-all span'), t = `${on.length} of ${ctx.CHIPS.length} on`; if (all && all.textContent !== t) all.textContent = t;
  return true;
}
export const lookKey = () => (ctx?.dark() ? 'd' : 'l') + document.documentElement.dataset.palette;

// ---- the sheet with every layer and the key ----
function sheet() {
  let el = $('#layers-sheet');
  if (!el) {
    el = document.createElement('div'); el.id = 'layers-sheet'; el.className = 'glass'; el.setAttribute('role', 'dialog'); el.setAttribute('aria-label', 'All layers'); el.hidden = true;
    document.body.appendChild(el);
    el.addEventListener('click', e => {
      if (e.target.closest('.ls-close')) { el.hidden = true; return; }
      const b = e.target.closest('[data-layer]'); if (b) { ctx.toggle(b.dataset.layer); drawSheet(); }
    });
  }
  return el;
}
function drawSheet() {
  const el = sheet(); if (el.hidden) return;
  const by = Object.fromEntries(ctx.CHIPS.map(l => [l.id, l]));
  const seen = new Set();
  const group = ([name, ids]) => {
    const ls = ids.map(i => by[i]).filter(Boolean); ls.forEach(l => seen.add(l.id));
    return ls.length ? `<h4>${name}</h4>` + ls.map(row).join('') : '';
  };
  const row = l => {
    const f = feedOf(l), on = !!ctx.on[l.id];
    return `<div class="ls-row${on ? ' on' : ''}">${icon(l, 22)}<span class="ls-name">${esc(l.title)}</span>
      <span class="ls-src">${f ? dot(f.state) + esc(f.source) + (f.age ? ' · ' + esc(f.age) : '') : ''}</span>
      <button class="sw" data-layer="${l.id}" role="switch" aria-checked="${on}" aria-label="${esc(l.title)}"></button></div>`;
  };
  const groups = GROUPS.map(group);
  const rest = ctx.CHIPS.filter(l => !seen.has(l.id));
  const half = Math.ceil(groups.length / 2);
  el.innerHTML = `<header class="ls-head"><h2>All layers</h2><span class="soft">${ctx.CHIPS.filter(l => ctx.on[l.id]).length} of ${ctx.CHIPS.length} on · source and state of each</span><button class="close ls-close" aria-label="Close"></button></header>
    <div class="ls-body"><div class="ls-col">${groups.slice(0, half).join('')}</div><div class="ls-col">${groups.slice(half).join('')}${rest.length ? '<h4>Other</h4>' + rest.map(row).join('') : ''}</div>
    <div class="ls-key"><h3>Key for what is on</h3><div class="ls-legend"></div></div></div>`;
  renderLegend(el.querySelector('.ls-legend'), ctx.CHIPS, ctx.on);
}
export function openSheet() { const el = sheet(); el.hidden = false; drawSheet(); }
export function closeSheet() { const el = $('#layers-sheet'); if (el && !el.hidden) { el.hidden = true; return true; } return false; }
export const refreshSheet = () => drawSheet();

// ---- views: camera positions of the one map (the two-globe and four-window views of the boards need several maps: not built) ----
const subsolarLon = () => { const d = new Date(); return -((d.getUTCHours() + d.getUTCMinutes() / 60) - 12) * 15; };
const VIEWS = [
  ['whole', 'Whole Earth', m => ({globe: true, center: [m.getCenter().lng, 20], zoom: 1.25, pitch: 0, bearing: 0})],
  ['theatre', 'Theatre', m => ({globe: true, center: m.getCenter(), zoom: Math.min(Math.max(3.4, m.getZoom()), 5), pitch: 55, bearing: m.getBearing() || 20})],
  ['dusk', 'Day and night', () => ({globe: true, center: [((subsolarLon() + 90 + 540) % 360) - 180, 12], zoom: 1.35, pitch: 0, bearing: 0, night: true})],
  ['front', 'Look down', m => ({center: m.getCenter(), zoom: Math.max(6, m.getZoom()), pitch: 0, bearing: 0})],
  ['polar', 'Over the pole', m => ({globe: true, center: [m.getCenter().lng, 78], zoom: 1.6, pitch: 0, bearing: 0})],
  ['low', 'Low orbit', m => ({globe: true, center: m.getCenter(), zoom: Math.max(4.6, Math.min(m.getZoom(), 6)), pitch: 72, bearing: m.getBearing()})],
  ['flat', 'Flat map', () => ({globe: false, center: [15, 25], zoom: 1.6, pitch: 0, bearing: 0})],
  ['chase', 'Chase', null],
];
let current = '';
function setView(k) {
  const v = VIEWS.find(x => x[0] === k); if (!v) return;
  if (!v[2]) {          // chase: follows the selected aircraft or ship through its card's own button
    const b = document.querySelector('#detail [data-chase]');
    if (b) b.click(); else flash('Select an aircraft or ship first; Chase follows it.');
    return;
  }
  const c = v[2](ctx.map);
  if (c.globe !== undefined) ctx.shape(c.globe);
  if (c.night) ctx.ensureOn('night');
  ctx.map.easeTo({center: c.center, zoom: c.zoom, pitch: c.pitch, bearing: c.bearing, duration: matchMedia('(prefers-reduced-motion: reduce)').matches ? 0 : 1400});
  current = k; strip();
}
function flash(t) { const b = $('#banner'); if (!b) return; b.textContent = t; b.hidden = false; clearTimeout(flash.t); flash.t = setTimeout(() => { b.hidden = true; }, 3500); }
function strip() {
  const el = $('#views'); if (!el) return;
  el.innerHTML = VIEWS.map(([k, n]) => `<button class="view" data-view="${k}" aria-pressed="${k === current}"><img src="${new URL(`../views/${k}.jpg`, import.meta.url)}" alt="" loading="lazy">${n}</button>`).join('')
    + '<span class="views-note">Camera positions of the live map. Imagery: NASA Blue Marble and Black Marble.</span>';
  const name = VIEWS.find(x => x[0] === current)?.[1] || '';
  const vn = $('#view-name'); if (vn) vn.textContent = name;
}

// ---- moving the page into the Dense places and back ----
function park(el, parent, before = null) {
  if (!el || !parent) return;
  if (!home.has(el)) home.set(el, [el.parentNode, el.nextSibling]);
  parent.insertBefore(el, before);
}
function unpark() {
  for (const [el, [p, next]] of home) p.insertBefore(el, next && next.parentNode === p ? next : null);
  home.clear();
}
export function apply() {
  const eye = eyeOn();
  document.body.classList.toggle('dense', eye);
  if (eye) {
    const tb = $('#topbar .tb-right');
    park($('#find'), $('#topbar .tb-search'));
    park($('#feeds'), tb);
    park($('.side-head .seg'), tb); park($('#three'), tb);
    let fold = $('#fold-btn');
    if (!fold) {
      fold = document.createElement('button'); fold.id = 'fold-btn'; fold.className = 'fold-btn'; fold.setAttribute('aria-label', 'Fold the column away'); fold.title = 'Fold the column away (more map)';
      fold.onclick = () => { $('#side-mini')?.click(); fold.setAttribute('aria-pressed', $('#sidebar').classList.contains('min')); };
      tb.appendChild(fold);
    }
    fold.setAttribute('aria-pressed', $('#sidebar').classList.contains('min'));
    park($('#settings-btn'), tb);
    const side = $('#sidebar');
    park($('#detail'), side, side.querySelector('.seg.wide'));
    strip();
  } else unpark();
  ctx?.repad();
}
export function init(c) {
  ctx = c;
  document.addEventListener('click', e => {
    const v = e.target.closest('[data-view]'); if (v) { setView(v.dataset.view); return; }
    if (e.target.closest('[data-all]')) openSheet();
  });
  ctx.map.on('dragstart', () => { if (current) { current = ''; strip(); } });
  apply();
}
