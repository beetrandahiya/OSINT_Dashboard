// Real 3D models for nearby aircraft (and anything else a provider hands in), drawn with three.js inside the map's own
// WebGL context so they share its depth buffer: terrain hides what is behind it, on the flat map and on the globe.
// Models: God's Eye View's procedural fleet set (MIT, see static/models/README.txt), one per type, drawn at the type's
// real length and at the aircraft's real altitude. The rules follow God's Eye View's: models only when zoomed in, for
// the nearest contacts first (on screen before off screen), up to CAP, new ones within ADD_KM of the view centre and
// kept to KEEP_KM so a model does not flicker at the edge; never smaller than MIN_PX on screen.
import * as THREE from '../vendor/three/three.module.js';
import {GLTFLoader} from '../vendor/three/GLTFLoader.js';
import {MeshoptDecoder} from '../vendor/three/meshopt_decoder.module.js';

const CAP = 150, ADD_KM = 150, KEEP_KM = 185, MIN_ZOOM = 6.5, MIN_PX = 24, TICK_MS = 80;
const base = new URL('../models/', import.meta.url);
let types = null, catalog = null, theMap = null, renderer = null, scene, camera, holder, dropHolder, dropLine, hemi, sun;
const providers = [];                 // functions returning [{id, layer, lon, lat, altM, heading, type, category, tint}]
const templates = new Map();          // model name -> {obj, mats} once loaded (or 'loading' / 'failed')
let eligible = new Set(), drawn = [], lastTick = 0, items = new Map();
export let lastM = null;   // the map's projection matrix of the last frame (also handy for checks in the console)
export const modelled = new Set();    // ids drawn as models right now (their flat icons are hidden)

const loader = new GLTFLoader();
loader.setMeshoptDecoder(MeshoptDecoder);
async function meta() {
  if (types) return;
  [types, catalog] = await Promise.all([fetch(new URL('types.json', base)).then(r => r.json()), fetch(new URL('catalog.json', base)).then(r => r.json())]);
}
meta().catch(() => {});

// which model draws a contact, and its real length: the ICAO type code it reports, else its ADS-B emitter category,
// else the generic aircraft (God's Eye View's types.json)
export function specFor(type, category, ship) {
  if (!types || !catalog) return null;
  if (ship) return null;
  const t = (type || '').toUpperCase();
  const hit = types.aircraft[t] || types.helicopters[t] || types.categories[(category || '').toUpperCase()] || types.default_aircraft;
  const [name, length] = hit, c = catalog[name];
  return c ? {name, length, built: c.length, file: c.file} : null;
}
function template(spec) {
  const t = templates.get(spec.name);
  if (t && t !== 'loading') return t === 'failed' ? null : t;
  if (!t) {
    templates.set(spec.name, 'loading');
    loader.load(new URL(spec.file, base).href, gltf => {
      const obj = gltf.scene, mats = [];
      obj.traverse(o => { if (o.isMesh) { const m = new THREE.MeshLambertMaterial({vertexColors: !!o.geometry.attributes.color, color: 0xffffff}); o.material = m; mats.push(m); } });
      templates.set(spec.name, {obj, mats});
      theMap?.triggerRepaint();
    }, undefined, () => templates.set(spec.name, 'failed'));
  }
  return null;
}

const km = (a, b, c, d) => { const r = Math.PI / 180, x = Math.sin((c - a) * r / 2) ** 2 + Math.cos(a * r) * Math.cos(c * r) * Math.sin((d - b) * r / 2) ** 2; return 12742 * Math.asin(Math.min(1, Math.sqrt(x))); };

// every TICK_MS: who may hold a model (God's Eye View's four passes: on-screen kept, on-screen new, off-screen kept, off-screen new)
function plan() {
  const map = theMap, z = map.getZoom();
  items = new Map();
  for (const p of providers) for (const it of p()) items.set(it.id, it);
  if (z < MIN_ZOOM || !types) { eligible = new Set(); return; }
  const c = map.getCenter(), b = map.getBounds(), cand = [];
  for (const it of items.values()) {
    const d = km(c.lat, c.lng, it.lat, it.lon);
    if (d <= KEEP_KM) cand.push([it.id, d, b.contains([it.lon, it.lat])]);
  }
  cand.sort((x, y) => x[1] - y[1]);
  const next = new Set(), passes = [(on, had) => on && had, (on, had, add) => on && add, (on, had) => !on && had, (on, had, add) => !on && add];
  for (const admit of passes) for (const [id, d, on] of cand) {
    if (next.size >= CAP) break;
    if (!next.has(id) && admit(on, eligible.has(id), d <= ADD_KM)) next.add(id);
  }
  eligible = next;
}

const tmpM = new THREE.Matrix4(), R = new THREE.Matrix4(), S = new THREE.Matrix4(), col = new THREE.Color();
function render(gl, args) {
  const map = theMap, M = args.defaultProjectionData?.mainMatrix;
  if (!M || !renderer) return;
  lastM = M;
  const t = performance.now();
  if (t - lastTick > TICK_MS) { lastTick = t; plan(); }
  modelled.clear(); drawn = [];
  if (!eligible.size) return;
  renderer.resetState();
  const z = map.getZoom(), tilted = map.getPitch() > 25, dark = matchMedia('(prefers-color-scheme: dark)').matches;
  for (const id of eligible) {
    const it = items.get(id); if (!it) continue;
    const spec = specFor(it.type, it.category); if (!spec) continue;
    const tpl = template(spec); if (!tpl) continue;
    const altM = Math.max(0, it.altM || 0);
    const model = map.transform.getMatrixForModel([it.lon, it.lat], altM);
    camera.projectionMatrix.fromArray(M).multiply(tmpM.fromArray(model));
    // never smaller than MIN_PX on screen, roughly: metres per pixel at this zoom and latitude
    const mpp = 40075016.686 * Math.cos(it.lat * Math.PI / 180) / (512 * 2 ** z);
    const s = Math.max(spec.length, MIN_PX * mpp) / spec.built;
    // MapLibre's local frame here is x east, y up, z south (measured: a step along y does not move on screen when
    // looking straight down). The glTF model is already y-up with its nose toward -x, so only the heading turns it:
    // about y, clockwise from north.
    R.makeRotationY(-((it.heading ?? 0) + 90) * Math.PI / 180);
    holder.matrix.copy(R).multiply(S.makeScale(s, s, s));   // three works out the children's matrices when it renders
    col.set(it.tint || '#ffffff');
    for (const m of tpl.mats) m.color.copy(col);
    holder.add(tpl.obj);
    dropHolder.visible = tilted && altM > 50;
    if (dropHolder.visible) { dropHolder.matrix.makeScale(1, altM, 1); dropLine.material.color.set(dark ? '#9aa4b8' : '#4b5563'); }
    renderer.render(scene, camera);
    holder.remove(tpl.obj);
    // where it is on screen, for clicks
    const v = new THREE.Vector4(0, 0, 0, 1).applyMatrix4(camera.projectionMatrix);
    if (v.w > 0) {
      const cv = map.getCanvas(), w = cv.clientWidth, h = cv.clientHeight;
      drawn.push({id, layer: it.layer, x: (v.x / v.w + 1) / 2 * w, y: (1 - v.y / v.w) / 2 * h, r: Math.max(14, s * spec.built / mpp / 2)});
    }
    modelled.add(id);
  }
  renderer.resetState();
  map.triggerRepaint();       // they move every frame (smooth playback between real reports)
}

export function attachModels(map) {
  theMap = map;
  map.addLayer({id: 'ww-models', type: 'custom', renderingMode: '3d',
    onAdd(m, gl) {
      renderer = new THREE.WebGLRenderer({canvas: m.getCanvas(), context: gl, antialias: true});
      renderer.autoClear = false;
      scene = new THREE.Scene();
      camera = new THREE.Camera();
      hemi = new THREE.HemisphereLight(0xffffff, 0x8a8f98, 1.7); hemi.position.set(0, 1, 0); scene.add(hemi);
      sun = new THREE.DirectionalLight(0xffffff, 1.4); sun.position.set(0.4, 1, 0.6); scene.add(sun);
      holder = new THREE.Group(); holder.matrixAutoUpdate = false; scene.add(holder);
      dropHolder = new THREE.Group(); dropHolder.matrixAutoUpdate = false; scene.add(dropHolder);
      dropLine = new THREE.Line(new THREE.BufferGeometry().setFromPoints([new THREE.Vector3(0, 0, 0), new THREE.Vector3(0, -1, 0)]),
        new THREE.LineBasicMaterial({color: 0x4b5563, transparent: true, opacity: 0.55}));
      dropLine.matrixAutoUpdate = false; dropHolder.add(dropLine);
    },
    render});
}
export const addModelProvider = fn => providers.push(fn);
// a click on a model: the nearest drawn model within its own size
export function hitModel(point) {
  let best = null, bd = Infinity;
  for (const d of drawn) { const e = Math.hypot(d.x - point.x, d.y - point.y); if (e <= d.r && e < bd) { bd = e; best = d; } }
  return best;
}
