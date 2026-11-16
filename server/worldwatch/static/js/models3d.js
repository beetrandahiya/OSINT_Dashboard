// Real 3D models for aircraft, drawn with three.js inside the map's own WebGL context so they share its depth buffer
// (terrain hides what is behind it, on the flat map and on the globe).
// Models: God's Eye View's procedural fleet set (MIT, see static/models/README.txt), one per type, at the type's real
// length (never smaller than MIN_PX on screen) and at the aircraft's real altitude.
//
// One rule, so it never looks arbitrary: zoomed out (below MODEL_ZOOM) every aircraft is a flat icon on the map;
// zoomed in, every aircraft on screen is a model in the air, and everything that belongs to it (selection ring,
// the path it has flown, the line to its destination, its label) is drawn up there with it.
//
// Drawing: one InstancedMesh per model part, so a thousand aircraft cost a handful of draw calls. Every matrix is
// worked out relative to the view centre in double precision, so nothing shakes when zoomed far in.
import * as THREE from '../vendor/three/three.module.js';
import {GLTFLoader} from '../vendor/three/GLTFLoader.js';
import {MeshoptDecoder} from '../vendor/three/meshopt_decoder.module.js';

export const MODEL_ZOOM = 7;
const MIN_PX = 24, SEL_PX = 46, CAP = 3000;
const base = new URL('../models/', import.meta.url);
let types = null, catalog = null, theMap = null, renderer = null, scene, camera, dropLine, overlay = null, octx = null;
const providers = [], pathProviders = [], readyFns = [];
const templates = new Map();          // model name -> {parts: [{geo, mat, local, inst, cap}]} once loaded (or 'loading' / 'failed')
let drawn = [], ready = false, wasOn = false;
export let lastM = null;              // the map's projection matrix of the last frame (handy for checks in the console)
export const modelled = new Set();    // ids drawn as models in the last frame
export const stats = {};              // what the last frame drew (for checks in the console and in tests)
export const isOn = () => ready && theMap && theMap.getZoom() >= MODEL_ZOOM;
export const onReady = fn => ready ? fn() : readyFns.push(fn);
export const addModelProvider = fn => providers.push(fn);
export const addPathProvider = fn => pathProviders.push(fn);

const loader = new GLTFLoader();
loader.setMeshoptDecoder(MeshoptDecoder);

// which model draws an aircraft, and its real length: the ICAO type code it reports, else its ADS-B emitter category,
// else the generic aircraft (God's Eye View's types.json)
export function specFor(type, category) {
  if (!types || !catalog) return null;
  const t = (type || '').toUpperCase();
  const hit = types.aircraft[t] || types.helicopters[t] || types.categories[(category || '').toUpperCase()] || types.default_aircraft;
  const [name, length] = hit, c = catalog[name];
  return c ? {name, length, built: c.length, file: c.file} : null;
}
function load(name, file) {
  if (templates.has(name)) return;
  templates.set(name, 'loading');
  loader.load(new URL(file, base).href, gltf => {
    const obj = gltf.scene, parts = [];
    obj.updateMatrixWorld(true);
    obj.traverse(o => {
      if (!o.isMesh) return;
      const mat = new THREE.MeshLambertMaterial({vertexColors: !!o.geometry.attributes.color, color: 0xffffff});
      // the models' darkest parts (rotors, windows, military paint) are lifted to 40 % of the aircraft's colour, so no
      // model turns into a black speck on a dark map or edge-on
      mat.onBeforeCompile = sh => { sh.vertexShader = sh.vertexShader.replace('#include <color_vertex>', '#include <color_vertex>\n#ifdef USE_INSTANCING_COLOR\nvColor.rgb = max(vColor.rgb, instanceColor.rgb * 0.4);\n#endif'); };
      parts.push({geo: o.geometry, mat, local: o.matrixWorld.clone(), inst: null, cap: 0});
    });
    templates.set(name, {parts});
    if (name === types.default_aircraft[0] && !ready) { ready = true; readyFns.splice(0).forEach(f => f()); }
    theMap?.triggerRepaint();
  }, undefined, () => templates.set(name, 'failed'));
}
// all aircraft and helicopter models (about 0.9 MB) are fetched once at start, the generic one first, so a model is
// there the moment an aircraft needs it
(async () => {
  [types, catalog] = await Promise.all([fetch(new URL('types.json', base)).then(r => r.json()), fetch(new URL('catalog.json', base)).then(r => r.json())]);
  const g = types.default_aircraft[0];
  load(g, catalog[g].file);
  for (const [name, c] of Object.entries(catalog)) if (c.category === 'aircraft' || c.category === 'helicopters') load(name, c.file);
})().catch(() => {});
function template(spec) {
  const t = templates.get(spec.name);
  if (t && typeof t === 'object') return t;
  const g = templates.get(types.default_aircraft[0]);   // still loading: the generic aircraft stands in
  return g && typeof g === 'object' ? g : null;
}

// ---- a line of constant screen width in 3D (WebGL lines are always 1 px) ----
const ribbonMat = (dash) => new THREE.ShaderMaterial({
  transparent: true, depthWrite: false,
  uniforms: {res: {value: new THREE.Vector2(1, 1)}, width: {value: 3}, color: {value: new THREE.Color('#5856d6')}, opacity: {value: 1}, dash: {value: dash ? 1 : 0}},
  vertexShader: `
    attribute vec3 prev; attribute vec3 next; attribute float side; attribute float along; attribute float fade;
    uniform vec2 res; uniform float width; varying float vAlong; varying float vFade;
    void main() {
      mat4 pm = projectionMatrix * modelViewMatrix;
      vec4 c = pm * vec4(position, 1.0), p = pm * vec4(prev, 1.0), n = pm * vec4(next, 1.0);
      vec2 sp = p.xy / p.w * res, sn = n.xy / n.w * res;
      vec2 d = sn - sp; d = length(d) < 1e-4 ? vec2(1.0, 0.0) : normalize(d);
      c.xy += vec2(-d.y, d.x) * side * width / res * c.w;
      gl_Position = c; vAlong = along; vFade = fade;
    }`,
  fragmentShader: `
    uniform vec3 color; uniform float opacity; uniform float dash; varying float vAlong; varying float vFade;
    void main() {
      if (dash > 0.5 && mod(vAlong, 2.0) > 1.0) discard;
      gl_FragColor = vec4(color, opacity * vFade);
    }`,
});
function ribbon(dash) {
  const mesh = new THREE.Mesh(new THREE.BufferGeometry(), ribbonMat(dash));
  mesh.frustumCulled = false; mesh.matrixAutoUpdate = false; mesh.renderOrder = 2; mesh.n = 0;
  return mesh;
}
// pts: [[x, y, z] in the centre frame]; along: dash phase per point; fade: opacity per point
function setRibbon(mesh, pts, along, fade) {
  const n = pts.length;
  mesh.visible = n > 1;
  if (n < 2) return;
  const g = mesh.geometry;
  if (mesh.n !== n) {
    mesh.n = n;
    for (const [k, s] of [['position', 3], ['prev', 3], ['next', 3], ['side', 1], ['along', 1], ['fade', 1]]) g.setAttribute(k, new THREE.BufferAttribute(new Float32Array(n * 2 * s), s));
    const idx = [];
    for (let i = 0; i < n - 1; i++) { const a = i * 2; idx.push(a, a + 1, a + 2, a + 1, a + 3, a + 2); }
    g.setIndex(idx);
    const side = g.attributes.side.array; for (let i = 0; i < n; i++) { side[i * 2] = 1; side[i * 2 + 1] = -1; }
    g.attributes.side.needsUpdate = true;
  }
  const P = g.attributes.position.array, Pr = g.attributes.prev.array, Nx = g.attributes.next.array, A = g.attributes.along.array, F = g.attributes.fade.array;
  for (let i = 0; i < n; i++) {
    const c = pts[i], p = pts[Math.max(0, i - 1)], q = pts[Math.min(n - 1, i + 1)];
    for (let s = 0; s < 2; s++) {
      const v = (i * 2 + s) * 3;
      P[v] = c[0]; P[v + 1] = c[1]; P[v + 2] = c[2];
      Pr[v] = p[0]; Pr[v + 1] = p[1]; Pr[v + 2] = p[2];
      Nx[v] = q[0]; Nx[v + 1] = q[1]; Nx[v + 2] = q[2];
      A[i * 2 + s] = along[i]; F[i * 2 + s] = fade[i];
    }
  }
  for (const k of ['position', 'prev', 'next', 'along', 'fade']) g.attributes[k].needsUpdate = true;
}
let trail, route;

// ---- per frame ----
const Mm = new THREE.Matrix4(), C = new THREE.Matrix4(), Ci = new THREE.Matrix4(), Mi = new THREE.Matrix4(), Rel = new THREE.Matrix4(),
  R = new THREE.Matrix4(), S = new THREE.Matrix4(), T = new THREE.Matrix4(), v4 = new THREE.Vector4(), col = new THREE.Color();
const mpp = (lat, z) => 40075016.686 * Math.cos(lat * Math.PI / 180) / (512 * 2 ** z);
function rel(lon, lat, alt) {   // a point in the centre frame (metres, x east, y up, z south at the centre)
  Mi.fromArray(theMap.transform.getMatrixForModel([lon, lat], alt));
  v4.set(Mi.elements[12], Mi.elements[13], Mi.elements[14], Mi.elements[15]).applyMatrix4(Ci);
  return [v4.x / v4.w, v4.y / v4.w, v4.z / v4.w];
}

function render(gl, args) {
  const map = theMap, M = args.defaultProjectionData?.mainMatrix;
  if (!M || !renderer) return;
  lastM = M;
  modelled.clear(); drawn = [];
  const on = isOn();
  if (!on) { if (wasOn) { clearOverlay(); wasOn = false; Object.assign(stats, {items: 0, models: 0, onScreen: 0, trail: 0, route: 0, sel: null}); } return; }
  wasOn = true;
  const z = map.getZoom(), cv = map.getCanvas(), w = cv.clientWidth, h = cv.clientHeight, dark = matchMedia('(prefers-color-scheme: dark)').matches;
  const ctr = map.getCenter();
  Mm.fromArray(M);
  C.fromArray(map.transform.getMatrixForModel([ctr.lng, ctr.lat], 0));
  Ci.copy(C).invert();
  camera.projectionMatrix.copy(Mm).multiply(C);
  camera.projectionMatrixInverse.copy(camera.projectionMatrix).invert();

  // everyone on screen (a margin around it, so models do not pop in at the edge)
  const b = map.getBounds(), padX = (b.getEast() - b.getWest()) * 0.15, padY = (b.getNorth() - b.getSouth()) * 0.15;
  const W = b.getWest() - padX, E = b.getEast() + padX, Sx = b.getSouth() - padY, N = b.getNorth() + padY;
  const inView = (lon, lat) => lat >= Sx && lat <= N && (E - W >= 360 || ((lon - W) % 360 + 360) % 360 <= E - W);
  let items = [];
  for (const p of providers) for (const it of p(inView)) items.push(it);
  if (items.length > CAP) { items.sort((a, c) => Math.hypot(a.lon - ctr.lng, a.lat - ctr.lat) - Math.hypot(c.lon - ctr.lng, c.lat - ctr.lat)); items = items.slice(0, CAP); }

  // group by model, fill the instance buffers
  const groups = new Map();
  let sel = null;
  for (const it of items) {
    const spec = specFor(it.type, it.category); if (!spec) continue;
    const tpl = template(spec); if (!tpl) continue;
    const built = tpl === templates.get(spec.name) ? spec.built : catalog[types.default_aircraft[0]].length;
    const altM = Math.max(0, it.altM || 0);
    Mi.fromArray(map.transform.getMatrixForModel([it.lon, it.lat], altM));
    Rel.copy(Ci).multiply(Mi);
    const px = mpp(it.lat, z), s = Math.max(spec.length, (it.sel ? SEL_PX : MIN_PX) * px) / built;
    // MapLibre's local frame is x east, y up, z south (measured); the glTF is y-up with its nose toward -x, so the
    // heading turns it about y, clockwise from north
    R.makeRotationY(-((it.heading ?? 0) + 90) * Math.PI / 180);
    const inst = new THREE.Matrix4().copy(Rel).multiply(R).multiply(S.makeScale(s, s, s));
    if (!groups.has(tpl)) groups.set(tpl, []);
    groups.get(tpl).push([inst, it.tint || '#ffffff']);
    v4.set(Mi.elements[12], Mi.elements[13], Mi.elements[14], Mi.elements[15]).applyMatrix4(Mm);
    if (v4.w > 0) {
      const d = {id: it.id, layer: it.layer, x: (v4.x / v4.w + 1) / 2 * w, y: (1 - v4.y / v4.w) / 2 * h, r: Math.max(12, s * built / px / 2 + 4), label: it.label, sel: it.sel, dist: 0};
      if (d.x > -50 && d.y > -50 && d.x < w + 50 && d.y < h + 50) drawn.push(d);
      if (it.sel) sel = {d, rel: Rel.clone(), altM};
    }
    modelled.add(it.id);
  }
  for (const [name, tpl] of templates) {
    if (typeof tpl !== 'object') continue;
    const list = groups.get(tpl) || [];
    for (const part of tpl.parts) {
      if (list.length > part.cap) {
        if (part.inst) { scene.remove(part.inst); part.inst.dispose(); }
        part.cap = Math.max(16, 2 ** Math.ceil(Math.log2(list.length)));
        part.inst = new THREE.InstancedMesh(part.geo, part.mat, part.cap);
        part.inst.frustumCulled = false; part.inst.matrixAutoUpdate = false;
        part.inst.setColorAt(0, col.set('#ffffff'));
        scene.add(part.inst);
      }
      if (!part.inst) continue;
      list.forEach(([inst, tint], k) => { part.inst.setMatrixAt(k, T.copy(inst).multiply(part.local)); part.inst.setColorAt(k, col.set(tint)); });
      part.inst.count = list.length;
      part.inst.instanceMatrix.needsUpdate = true;
      if (part.inst.instanceColor) part.inst.instanceColor.needsUpdate = true;
    }
  }

  // the selected aircraft: a line down to the ground when the map is tilted, its flown path and its route, in the air
  dropLine.visible = !!sel && map.getPitch() > 20 && sel.altM > 30;
  if (dropLine.visible) {
    const a = dropLine.geometry.attributes.position.array;
    v4.set(0, 0, 0, 1).applyMatrix4(sel.rel); a[0] = v4.x; a[1] = v4.y; a[2] = v4.z;
    v4.set(0, -sel.altM, 0, 1).applyMatrix4(sel.rel); a[3] = v4.x; a[4] = v4.y; a[5] = v4.z;
    dropLine.geometry.attributes.position.needsUpdate = true;
    dropLine.material.color.set(dark ? '#c7cbd6' : '#3a3a3c');
  }
  const path = sel && pathProviders.map(f => f()).find(Boolean);
  for (const [mesh, line, isRoute] of [[trail, path?.trail, false], [route, path?.route, true]]) {
    if (!line || line.length < 2) { mesh.visible = false; continue; }
    const pts = line.map(p => rel(p[0], p[1], Math.max(0, p[2] || 0)));
    const along = [0], fade = [];
    const dashM = 9 * mpp(ctr.lat, z);
    for (let i = 1; i < pts.length; i++) { const p = pts[i], q = pts[i - 1]; along.push(along[i - 1] + Math.hypot(p[0] - q[0], p[1] - q[1], p[2] - q[2]) / dashM); }
    for (let i = 0; i < pts.length; i++) fade.push(isRoute ? 0.9 : 0.25 + 0.75 * (pts.length < 2 ? 1 : i / (pts.length - 1)));   // the trail fades out towards its start
    setRibbon(mesh, pts, along, fade);
    mesh.material.uniforms.res.value.set(w, h);
    mesh.material.uniforms.width.value = isRoute ? 2 : 3;
    mesh.material.uniforms.color.value.set(path.color || '#5856d6');
  }
  if (!sel) { trail.visible = false; route.visible = false; }

  renderer.resetState();
  renderer.render(scene, camera);
  renderer.resetState();
  Object.assign(stats, {items: items.length, models: modelled.size, onScreen: drawn.length, trail: trail.visible ? trail.n : 0, route: route.visible ? route.n : 0,
    sel: sel ? [Math.round(sel.d.x), Math.round(sel.d.y)] : null, w, h, frame: (stats.frame || 0) + 1});
  drawOverlay(w, h, dark, sel, z);
  map.triggerRepaint();       // they move every frame (smooth playback between real reports)
}

// ---- labels and the selection ring, on a 2D canvas over the map ----
function clearOverlay() { if (octx) octx.clearRect(0, 0, overlay.width, overlay.height); }
function drawOverlay(w, h, dark, sel, z) {
  const dpr = devicePixelRatio || 1;
  if (overlay.width !== Math.round(w * dpr) || overlay.height !== Math.round(h * dpr)) { overlay.width = Math.round(w * dpr); overlay.height = Math.round(h * dpr); overlay.style.width = w + 'px'; overlay.style.height = h + 'px'; }
  const x = octx;
  x.setTransform(dpr, 0, 0, dpr, 0, 0);
  x.clearRect(0, 0, w, h);
  // callsigns, nearest to the middle first, none overlapping (like the map's own labels)
  x.font = '600 10.5px -apple-system, BlinkMacSystemFont, "Helvetica Neue", sans-serif';
  x.textAlign = 'center'; x.textBaseline = 'top'; x.lineJoin = 'round'; x.lineWidth = 3;
  x.strokeStyle = dark ? '#1c1c1e' : '#ffffff'; x.fillStyle = dark ? '#e5e5ea' : '#3a3a3c';
  const boxes = [], cx = w / 2, cy = h / 2;
  const list = drawn.filter(d => d.label && d.x > 0 && d.y > 0 && d.x < w && d.y < h).sort((a, b) => (b.sel - a.sel) || (Math.hypot(a.x - cx, a.y - cy) - Math.hypot(b.x - cx, b.y - cy)));
  for (const d of list.slice(0, 250)) {
    const tw = x.measureText(d.label).width, bx = [d.x - tw / 2 - 2, d.y + d.r - 2, d.x + tw / 2 + 2, d.y + d.r + 12];
    if (!d.sel && boxes.some(o => bx[0] < o[2] && bx[2] > o[0] && bx[1] < o[3] && bx[3] > o[1])) continue;
    boxes.push(bx);
    x.strokeText(d.label, d.x, d.y + d.r); x.fillText(d.label, d.x, d.y + d.r);
  }
  if (sel) {   // the same black / white ring as every other selected item, around the aircraft where it is drawn
    x.lineWidth = 2.5; x.strokeStyle = dark ? '#ffffff' : '#000000';
    x.beginPath(); x.arc(sel.d.x, sel.d.y, Math.max(16, sel.d.r + 2), 0, Math.PI * 2); x.stroke();
  }
}

export function attachModels(map) {
  theMap = map;
  overlay = document.createElement('canvas');
  overlay.className = 'ww-models-overlay';
  overlay.style.cssText = 'position:absolute;left:0;top:0;pointer-events:none;';
  map.getCanvasContainer().appendChild(overlay);
  octx = overlay.getContext('2d');
  map.addLayer({id: 'ww-models', type: 'custom', renderingMode: '3d',
    onAdd(m, gl) {
      renderer = new THREE.WebGLRenderer({canvas: m.getCanvas(), context: gl, antialias: true});
      renderer.autoClear = false;
      scene = new THREE.Scene();
      camera = new THREE.Camera();
      const hemi = new THREE.HemisphereLight(0xffffff, 0x8a8f98, 1.7); hemi.position.set(0, 1, 0); scene.add(hemi);
      const sun = new THREE.DirectionalLight(0xffffff, 1.4); sun.position.set(0.4, 1, 0.6); scene.add(sun);
      dropLine = new THREE.Line(new THREE.BufferGeometry().setAttribute('position', new THREE.BufferAttribute(new Float32Array(6), 3)),
        new THREE.LineBasicMaterial({color: 0x4b5563, transparent: true, opacity: 0.6}));
      dropLine.frustumCulled = false; dropLine.matrixAutoUpdate = false; scene.add(dropLine);
      trail = ribbon(false); route = ribbon(true); scene.add(trail); scene.add(route);
    },
    render});
}
// a click on a model: the nearest drawn model within its own size
export function hitModel(point) {
  if (!isOn()) return null;
  let best = null, bd = Infinity;
  for (const d of drawn) { const e = Math.hypot(d.x - point.x, d.y - point.y); if (e <= d.r && e < bd) { bd = e; best = d; } }
  return best;
}
