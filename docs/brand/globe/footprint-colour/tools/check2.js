const { chromium } = require('playwright');
const fs = require('fs');
(async () => {
  const body = fs.readFileSync('out/page.html', 'utf8');
  fs.writeFileSync('out/wrapped.html', `<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head><body>${body}</body></html>`);
  const b = await chromium.launch();
  for (const [w, scheme] of [[1440, 'dark'], [1440, 'light'], [400, 'light']]) {
    const p = await b.newPage({ viewport: { width: w, height: 1000 }, colorScheme: scheme });
    const errs = []; p.on('pageerror', e => errs.push(e.message)); p.on('console', m => m.type() === 'error' && errs.push(m.text()));
    await p.goto('file://' + process.cwd() + '/out/wrapped.html'); await p.waitForTimeout(2000);
    console.log(w, scheme, await p.evaluate(() => [document.documentElement.scrollWidth, innerWidth]), errs.slice(0, 3));
    if (w === 1440 && scheme === 'dark') { await p.screenshot({ path: 'out/top.png' }); await (await p.$('#two')).screenshot({ path: 'out/two.png' }); }
    if (w === 400) await p.screenshot({ path: 'out/phone.png' });
    await p.close();
  }
  await b.close();
})();
