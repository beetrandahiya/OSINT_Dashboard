const { chromium } = require('playwright');
const fs = require('fs');
(async () => {
  const body = fs.readFileSync('out/suite.html', 'utf8');
  fs.writeFileSync('out/wrapped.html', `<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"><style>:root{color-scheme:light}body{margin:0;font:14px system-ui}img{max-width:100%}[hidden]{display:none!important}</style></head><body>${body}</body></html>`);
  const b = await chromium.launch();
  for (const [w, scheme] of [[1440, 'light'], [1440, 'dark'], [400, 'light']]) {
    const p = await b.newPage({ viewport: { width: w, height: 1000 }, colorScheme: scheme });
    const errs = []; p.on('pageerror', e => errs.push(e.message)); p.on('console', m => m.type() === 'error' && errs.push(m.text()));
    p.on('requestfailed', r => errs.push('FAIL ' + r.url().slice(0, 80)));
    await p.goto('file://' + process.cwd() + '/out/wrapped.html'); await p.waitForTimeout(3500);
    const info = await p.evaluate(() => ({ sw: document.documentElement.scrollWidth, iw: innerWidth, h: document.documentElement.scrollHeight,
      fonts: [...document.fonts].filter(f => f.status === 'loaded').map(f => f.family).filter((v, i, a) => a.indexOf(v) === i),
      wide: [...document.querySelectorAll('body *')].filter(e => { const r = e.getBoundingClientRect(); return r.right > innerWidth + 1 && !e.closest('.scroll') && !e.closest('.fit'); }).slice(0, 5).map(e => e.className || e.tagName) }));
    console.log(w, scheme, JSON.stringify(info), errs.slice(0, 4));
    const tag = `${w}-${scheme}`;
    await p.screenshot({ path: `out/p-${tag}.png`, fullPage: true });
    await p.close();
  }
  await b.close();
})();
