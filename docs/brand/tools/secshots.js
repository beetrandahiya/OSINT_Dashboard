// node secshots.js <html> <outdir> <width> <height> [scheme] [selector-prefix]
const { chromium } = require('playwright');
(async () => {
  const [html, out, w, h, scheme = 'light', only = ''] = process.argv.slice(2);
  const b = await chromium.launch();
  const p = await b.newPage({ viewport: { width: +w, height: +h }, deviceScaleFactor: 1, colorScheme: scheme });
  const errs = [];
  p.on('pageerror', e => errs.push(String(e)));
  await p.goto('file://' + html);
  await p.evaluate(() => document.fonts.ready);
  await p.screenshot({ path: `${out}/top-${w}-${scheme}.png` });
  const ids = await p.$$eval('section.dir', s => s.map(x => x.id));
  for (const id of ids) {
    if (only && !id.startsWith('d' + only)) continue;
    const el = await p.$('[id="' + id + '"]');
    await el.screenshot({ path: `${out}/sec-${id.slice(1, 3)}-${w}-${scheme}.png` });
  }
  // overflow check per element: anything wider than viewport?
  const wide = await p.evaluate(() => {
    const vw = document.documentElement.clientWidth; const r = [];
    for (const el of document.querySelectorAll('body *')) { const b = el.getBoundingClientRect(); if (b.right > vw + 1 && b.width > 0) r.push(el.tagName + '.' + el.className + ' ' + Math.round(b.right)); }
    return r.slice(0, 10);
  });
  console.log(JSON.stringify({ errs, wide, sw: await p.evaluate(() => document.documentElement.scrollWidth) }));
  await b.close();
})();
