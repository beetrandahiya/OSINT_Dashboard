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
//
// three.js (~1.5 MB of script) and the models (~0.5 MB) are fetched only when first needed: the first time the map is
// zoomed in to MODEL_ZOOM - 1. Until they are ready every aircraft stays a flat icon (isOn() is false and the icon
// layers keep their full zoom range; aircraft.js narrows them in onReady). Loading them at start delayed the map.
import {maxModels} from './prefs.js';
let THREE = null, loader = null, booting = null, glOf = null;

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
// three.js first, then all aircraft and helicopter models (about 0.9 MB), the generic one first, so a model is there
// the moment an aircraft needs it
function boot() {
  return booting ||= (async () => {
    const [three, {GLTFLoader}, {MeshoptDecoder}] = await Promise.all([import('../vendor/three/three.module.js'), import('../vendor/three/GLTFLoader.js'), import('../vendor/three/meshopt_decoder.module.js')]);
    THREE = three;
    Mm = new THREE.Matrix4(); C = new THREE.Matrix4(); Ci = new THREE.Matrix4(); Mi = new THREE.Matrix4(); Rel = new THREE.Matrix4();
    R = new THREE.Matrix4(); S = new THREE.Matrix4(); T = new THREE.Matrix4(); SelRel = new THREE.Matrix4(); v4 = new THREE.Vector4();
    loader = new GLTFLoader();
    loader.setMeshoptDecoder(MeshoptDecoder);
    theMap?.triggerRepaint();            // the renderer is made in the next frame (render), inside the map's own drawing
    [types, catalog] = await Promise.all([fetch(new URL('types.json', base)).then(r => r.json()), fetch(new URL('catalog.json', base)).then(r => r.json())]);
    const g = types.default_aircraft[0];
    load(g, catalog[g].file);
    for (const [name, c] of Object.entries(catalog)) if (c.category === 'aircraft' || c.category === 'helicopters') load(name, c.file);
  })().catch(e => { booting = null; console.error('3D models could not be loaded', e); theMap?.once('zoomend', () => theMap.getZoom() >= MODEL_ZOOM - 1 && boot()); });   // try again on a later zoom
}
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
// Nothing is allocated per aircraft per frame: item objects come from the providers' pools, instance matrices and
// screen records are reused, colours are parsed once per tint, label widths measured once per text. A frame is asked
// for again only while something on screen is moving (or an aircraft waiting at its first report is about to start);
// providers call triggerRepaint when new reports arrive, the map repaints on its own when the camera moves.
let Mm, C, Ci, Mi, Rel, R, S, T, SelRel, v4;        // made in boot(), once three.js is here
const mpp = (lat, z) => 40075016.686 * Math.cos(lat * Math.PI / 180) / (512 * 2 ** z);
// a longitude moved by whole turns to the side of the view centre: the custom layer has no world copies, so a model
// just across the date line from the centre would otherwise be placed a whole world away (and not drawn)
let ctrLng = 0;
const near = l => l + 360 * Math.round((ctrLng - l) / 360);
const LL = [0, 0];
function modelMatrix(lon, lat, alt) { LL[0] = near(lon); LL[1] = lat; return Mi.fromArray(theMap.transform.getMatrixForModel(LL, alt)); }
function rel(lon, lat, alt) {   // a point in the centre frame (metres, x east, y up, z south at the centre)
  modelMatrix(lon, lat, alt);
  v4.set(Mi.elements[12], Mi.elements[13], Mi.elements[14], Mi.elements[15]).applyMatrix4(Ci);
  return [v4.x / v4.w, v4.y / v4.w, v4.z / v4.w];
}
const colours = new Map(), colourOf = c => colours.get(c) || (colours.set(c, new THREE.Color(c)), colours.get(c));
const widths = new Map();
const items = [], groups = new Map();       // template -> {n, mats: [Matrix4], cols: [Color]}
const screen = new Map();                   // id -> {x, y, hd, lx, ly, label, gen}: last frame's screen point, last laid-out label
let gen = 0, wakeTimer = 0, laidSel = null, laidW = 0, laidH = 0, laidDark = null, laidN = -1, lastCount = -1;
const pick = [];                            // reused records of what was drawn where (for clicks, labels and the ring)
let nDrawn = 0;
const still = (a, b, eps) => a !== a ? b !== b : Math.abs(a - b) <= eps;   // NaN (not on screen) counts as unchanged when it was NaN before

function render(gl, args) {
  const map = theMap, M = args.defaultProjectionData?.mainMatrix;
  if (!renderer && THREE && glOf) initGL(...glOf);   // made here, where the map expects its GL state to be changed
  if (!M || !renderer) return;
  const t0 = performance.now();
  lastM = M;
  modelled.clear(); drawn.length = 0; nDrawn = 0;
  let k = 0;
  const on = isOn();
  if (!on) { if (wasOn) { clearOverlay(); wasOn = false; laidN = -1; Object.assign(stats, {items: 0, models: 0, onScreen: 0, trail: 0, route: 0, sel: null}); } return; }
  wasOn = true;
  const z = map.getZoom(), cv = map.getCanvas(), w = cv.clientWidth, h = cv.clientHeight, dark = matchMedia('(prefers-color-scheme: dark)').matches;
  const ctr = map.getCenter();
  ctrLng = ctr.lng;
  Mm.fromArray(M);
  C.fromArray(map.transform.getMatrixForModel([ctr.lng, ctr.lat], 0));
  Ci.copy(C).invert();
  camera.projectionMatrix.copy(Mm).multiply(C);
  camera.projectionMatrixInverse.copy(camera.projectionMatrix).invert();

  // everyone on screen (a margin around it, so models do not pop in at the edge)
  const b = map.getBounds(), padX = (b.getEast() - b.getWest()) * 0.15, padY = (b.getNorth() - b.getSouth()) * 0.15;
  const W = b.getWest() - padX, E = b.getEast() + padX, Sx = b.getSouth() - padY, N = b.getNorth() + padY;
  const inView = (lon, lat) => lat >= Sx && lat <= N && (E - W >= 360 || ((lon - W) % 360 + 360) % 360 <= E - W);
  items.length = 0;
  for (const p of providers) p(inView, items);
  const cap = Math.min(CAP, maxModels());   // prefs.js (default: no lower limit than CAP)
  if (items.length > cap) { const d = it => Math.hypot(near(it.lon) - ctr.lng, it.lat - ctr.lat); items.sort((a, c) => d(a) - d(c)); items.length = cap; }

  // group by model, fill the instance buffers
  for (const g of groups.values()) g.n = 0;
  gen++;
  let sel = null, moving = false, waiting = false, relayout = false;
  if (items.length !== lastCount) { moving = true; relayout = true; lastCount = items.length; }
  for (const it of items) {
    const spec = specFor(it.type, it.category); if (!spec) continue;
    const tpl = template(spec); if (!tpl) continue;
    const built = tpl === templates.get(spec.name) ? spec.built : catalog[types.default_aircraft[0]].length;
    const altM = Math.max(0, it.altM || 0);
    modelMatrix(it.lon, it.lat, altM);
    Rel.multiplyMatrices(Ci, Mi);
    const px = mpp(it.lat, z), s = Math.max(spec.length, (it.sel ? SEL_PX : MIN_PX) * px) / built;
    // MapLibre's local frame is x east, y up, z south (measured); the glTF is y-up with its nose toward -x, so the
    // heading turns it about y, clockwise from north
    R.makeRotationY(-((it.heading ?? 0) + 90) * Math.PI / 180);
    let g = groups.get(tpl);
    if (!g) groups.set(tpl, g = {n: 0, mats: [], cols: []});
    const m = g.mats[g.n] || (g.mats[g.n] = new THREE.Matrix4());
    m.multiplyMatrices(Rel, R).multiply(S.makeScale(s, s, s));
    g.cols[g.n] = colourOf(it.tint || '#ffffff');
    g.n++;
    if (it.wait) waiting = true;
    v4.set(Mi.elements[12], Mi.elements[13], Mi.elements[14], Mi.elements[15]).applyMatrix4(Mm);
    let x = NaN, y = NaN, above = false;
    if (v4.w > 0) { x = (v4.x / v4.w + 1) / 2 * w; y = (1 - v4.y / v4.w) / 2 * h; }
    else if (it.sel) {   // zoomed in so far that the camera is lower than the aircraft: ring its point on the ground instead
      modelMatrix(it.lon, it.lat, 0);
      v4.set(Mi.elements[12], Mi.elements[13], Mi.elements[14], Mi.elements[15]).applyMatrix4(Mm);
      if (v4.w > 0) { x = (v4.x / v4.w + 1) / 2 * w; y = (1 - v4.y / v4.w) / 2 * h; above = true; }
    }
    let e = screen.get(it.id);
    if (!e) { screen.set(it.id, e = {x: NaN, y: NaN, hd: null, lx: NaN, ly: NaN, label: null, gen}); moving = true; relayout = true; }
    if (!still(x, e.x, 0.05) || !still(y, e.y, 0.05) || Math.abs((it.heading ?? 0) - (e.hd ?? 0)) > 0.05) moving = true;
    if (!still(x, e.lx, 0.99) || !still(y, e.ly, 0.99) || e.label !== it.label) relayout = true;
    e.x = x; e.y = y; e.hd = it.heading; e.gen = gen;
    if (x === x) {   // not NaN
      const d = pick[k] || (pick[k] = {});
      k++;
      d.id = it.id; d.layer = it.layer; d.x = x; d.y = y; d.r = Math.max(12, s * built / px / 2 + 4); d.label = it.label; d.sel = it.sel; d.above = above; d.altM = altM; d.e = e;
      if (d.x > -50 && d.y > -50 && d.x < w + 50 && d.y < h + 50) { drawn.push(d); nDrawn++; }
      if (it.sel) { sel = {d, altM, lon: it.lon, lat: it.lat}; SelRel.copy(Rel); if (above) d.r = 18; }
    }
    modelled.add(it.id);
  }
  if (screen.size > items.length * 2 + 64) for (const [k, e] of screen) if (e.gen !== gen) screen.delete(k);
  for (const [name, tpl] of templates) {
    if (typeof tpl !== 'object') continue;
    const g = groups.get(tpl), n = g ? g.n : 0;
    for (const part of tpl.parts) {
      if (n > part.cap) {
        if (part.inst) { scene.remove(part.inst); part.inst.dispose(); }
        part.cap = Math.max(16, 2 ** Math.ceil(Math.log2(n)));
        part.inst = new THREE.InstancedMesh(part.geo, part.mat, part.cap);
        part.inst.frustumCulled = false; part.inst.matrixAutoUpdate = false;
        part.inst.setColorAt(0, colourOf('#ffffff'));
        scene.add(part.inst);
      }
      if (!part.inst) continue;
      if (!n && !part.inst.count) continue;
      for (let k = 0; k < n; k++) { part.inst.setMatrixAt(k, T.multiplyMatrices(g.mats[k], part.local)); part.inst.setColorAt(k, g.cols[k]); }
      part.inst.count = n;
      part.inst.instanceMatrix.needsUpdate = true;
      if (part.inst.instanceColor) part.inst.instanceColor.needsUpdate = true;
    }
  }

  // the selected aircraft: a line down to the ground when the map is tilted, its flown path and its route, in the air
  dropLine.visible = !!sel && !sel.d.above && map.getPitch() > 20 && sel.altM > 30;
  if (dropLine.visible) {
    const ground = Math.min(sel.altM, (map.getTerrain?.() && map.queryTerrainElevation?.([sel.lon, sel.lat])) || 0);   // to the terrain in 3D, else sea level
    const a = dropLine.geometry.attributes.position.array;
    v4.set(0, 0, 0, 1).applyMatrix4(SelRel); a[0] = v4.x; a[1] = v4.y; a[2] = v4.z;
    v4.set(0, -(sel.altM - ground), 0, 1).applyMatrix4(SelRel); a[3] = v4.x; a[4] = v4.y; a[5] = v4.z;
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
  const selKey = sel ? sel.d.id + (sel.d.above ? '^' : '') : null;
  if (relayout || selKey !== laidSel || w !== laidW || h !== laidH || dark !== laidDark || nDrawn !== laidN) {   // labels and ring: only when something moved a pixel
    drawOverlay(w, h, dark, sel, z);
    laidSel = selKey; laidW = w; laidH = h; laidDark = dark; laidN = nDrawn;
    for (const d of drawn) { d.e.lx = d.x; d.e.ly = d.y; d.e.label = d.label; }
    stats.overlays = (stats.overlays || 0) + 1;
  }
  Object.assign(stats, {items: items.length, models: modelled.size, onScreen: nDrawn, trail: trail.visible ? trail.n : 0, route: route.visible ? route.n : 0,
    sel: sel ? [Math.round(sel.d.x), Math.round(sel.d.y)] : null, above: !!sel?.d.above, w, h, frame: (stats.frame || 0) + 1, ms: +(performance.now() - t0).toFixed(2), moving});
  if (moving) map.triggerRepaint();       // they move (smooth playback between real reports): draw the next frame too
  else if (waiting && !wakeTimer) wakeTimer = setTimeout(() => { wakeTimer = 0; map.triggerRepaint(); }, 500);   // one just came into view and starts moving soon
}

// ---- labels and the selection ring, on a 2D canvas over the map ----
function clearOverlay() { if (octx) octx.clearRect(0, 0, overlay.width, overlay.height); }
const order = [];
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
  order.length = 0;
  for (const d of drawn) if (d.label && !d.above && d.x > 0 && d.y > 0 && d.x < w && d.y < h) { d.c = (d.x - cx) ** 2 + (d.y - cy) ** 2; order.push(d); }
  order.sort((a, b) => (b.sel - a.sel) || (a.c - b.c));
  const n = Math.min(250, order.length);
  for (let i = 0; i < n; i++) {
    const d = order[i];
    let tw = widths.get(d.label); if (tw == null) { tw = x.measureText(d.label).width; if (widths.size > 5000) widths.clear(); widths.set(d.label, tw); }
    const bx = [d.x - tw / 2 - 2, d.y + d.r - 2, d.x + tw / 2 + 2, d.y + d.r + 12];
    if (!d.sel && boxes.some(o => bx[0] < o[2] && bx[2] > o[0] && bx[1] < o[3] && bx[3] > o[1])) continue;
    boxes.push(bx);
    x.strokeText(d.label, d.x, d.y + d.r); x.fillText(d.label, d.x, d.y + d.r);
  }
  if (sel) {   // the same black / white ring as every other selected item, around the aircraft where it is drawn
    x.lineWidth = 2.5; x.strokeStyle = dark ? '#ffffff' : '#000000';
    if (sel.d.above) x.setLineDash([5, 4]);
    x.beginPath(); x.arc(sel.d.x, sel.d.y, Math.max(16, sel.d.r + 2), 0, Math.PI * 2); x.stroke();
    x.setLineDash([]);
    if (sel.d.above) {   // the camera is below the aircraft (zoomed in very far): say so instead of losing it
      const t = `${sel.d.label ? sel.d.label + ' is ' : ''}above the camera, ${Math.round(sel.altM).toLocaleString('en-GB')} m up: zoom out to see it`;
      x.lineWidth = 3; x.strokeStyle = dark ? '#1c1c1e' : '#ffffff'; x.fillStyle = dark ? '#e5e5ea' : '#3a3a3c';
      x.textBaseline = 'bottom'; x.strokeText(t, sel.d.x, sel.d.y - 22); x.fillText(t, sel.d.x, sel.d.y - 22);
    }
  }
}

export function attachModels(map) {
  theMap = map;
  overlay = document.createElement('canvas');
  overlay.className = 'ww-models-overlay';
  overlay.style.cssText = 'position:absolute;left:0;top:0;pointer-events:none;';
  map.getCanvasContainer().appendChild(overlay);
  octx = overlay.getContext('2d');
  const need = () => { if (map.getZoom() >= MODEL_ZOOM - 1) { boot(); map.off('zoom', need); } };
  map.on('zoom', need); need();
  map.addLayer({id: 'ww-models', type: 'custom', renderingMode: '3d',
    onAdd(m, gl) { glOf = [m, gl]; },
    render});
}
function initGL(m, gl) {
      if (renderer) return;
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
}
// a click on a model: the nearest drawn model within its own size
export function hitModel(point) {
  if (!isOn()) return null;
  let best = null, bd = Infinity;
  for (const d of drawn) { const e = Math.hypot(d.x - point.x, d.y - point.y); if (e <= d.r && e < bd) { bd = e; best = d; } }
  return best;
}
