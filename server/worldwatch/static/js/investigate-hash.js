// Picture fingerprints for a case: a 64-bit difference hash (dHash) of each picture, computed here in the browser.
// The picture is shrunk to 9 x 8 grey blocks and each bit says whether a block is brighter than its right-hand
// neighbour, so a resized or recompressed copy of the same file gets (nearly) the same 64 bits. The server compares
// them by Hamming distance (6 bits or fewer = "same picture").
// This is picture-copy matching, NOT face recognition: it says nothing about who is in a picture, and two different
// photos of the same person do not match. No picture goes to any face-search service.

export async function dhash(blob) {
  const bmp = await createImageBitmap(blob);
  const c = document.createElement('canvas');
  c.width = 72; c.height = 64;                      // 9 x 8 blocks of 8 x 8 pixels, averaged below
  const x = c.getContext('2d', {willReadFrequently: true});
  x.fillStyle = '#fff'; x.fillRect(0, 0, 72, 64);   // transparent parts count as white, the same for every copy
  x.imageSmoothingEnabled = true; x.imageSmoothingQuality = 'high';
  x.drawImage(bmp, 0, 0, 72, 64);
  if (bmp.close) bmp.close();
  const d = x.getImageData(0, 0, 72, 64).data, g = new Float64Array(72);
  for (let y = 0; y < 64; y++) for (let xx = 0; xx < 72; xx++) {
    const i = (y * 72 + xx) * 4;
    g[(y >> 3) * 9 + (xx >> 3)] += 0.299 * d[i] + 0.587 * d[i + 1] + 0.114 * d[i + 2];
  }
  let hex = '';
  for (let r = 0; r < 8; r++) {
    let nib = 0;
    for (let col = 0; col < 8; col++) {
      nib = (nib << 1) | (g[r * 9 + col] > g[r * 9 + col + 1] ? 1 : 0);
      if (col % 4 === 3) { hex += nib.toString(16); nib = 0; }
    }
  }
  return hex;
}

// Every picture of the case that has no fingerprint yet: found profile pictures (through the server's picture proxy,
// which fetches only addresses the case's findings name) and uploaded seed pictures. Four at a time, sent in batches.
// A picture that cannot be read is stored with an empty hash, so it is not asked for again on every visit.
let running = false;
export async function fingerprintAll(S, post) {
  if (running || !S?.subject) return 0;
  const sid = S.subject.id, have = S.fingerprints || {}, todo = [];
  const pics = new Set();
  for (const f of S.findings || []) for (const u of [f.detail?.image, f.detail?.photo, f.page?.image]) if (typeof u === 'string' && /^https?:\/\//.test(u)) pics.add(u);
  for (const u of pics) if (!(u in have)) todo.push({url: u, src: `/api/lookup/img?s=${sid}&u=${encodeURIComponent(u)}`});
  for (const i of S.identifiers || []) if (i.kind === 'picture' && !(('picture:' + i.value) in have))
    todo.push({url: 'picture:' + i.value, src: `/api/lookup/picture/${encodeURIComponent(i.value)}?s=${sid}`});
  if (!todo.length) return 0;
  running = true;
  const out = [];
  let k = 0;
  async function worker() {
    while (k < todo.length) {
      const t = todo[k++];
      try {
        const r = await fetch(t.src, {cache: 'default'});
        if (!r.ok) throw new Error(r.status);
        out.push({url: t.url, hash: await dhash(await r.blob()), location_meta: r.headers.get('X-Location-Meta') === '1'});
      } catch (e) { out.push({url: t.url, hash: ''}); }
      if (out.length >= 20) await post(sid, out.splice(0));
    }
  }
  try {
    await Promise.all([worker(), worker(), worker(), worker()]);
    if (out.length) await post(sid, out.splice(0));
  } finally { running = false; }
  return todo.length;
}
