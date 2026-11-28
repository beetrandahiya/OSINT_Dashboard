// node shot.js <html> <png> [width] [height] [fullPage 0/1] [dsf]
const { chromium } = require('playwright');
(async () => {
  const [html, png, w = '1600', h = '900', full = '1', dsf = '1'] = process.argv.slice(2);
  const b = await chromium.launch();
  const p = await b.newPage({ viewport: { width: +w, height: +h }, deviceScaleFactor: +dsf });
  const errs = [];
  p.on('pageerror', e => errs.push(String(e)));
  p.on('console', m => { if (m.type() === 'error') errs.push(m.text()); });
  await p.goto('file://' + html);
  await p.waitForLoadState('networkidle').catch(() => {});
  await p.evaluate(() => document.fonts && document.fonts.ready);
  await p.waitForFunction(() => !window.done || window.done(), null, { timeout: 15000 }).catch(() => {});
  await p.waitForTimeout(300);
  const over = await p.evaluate(() => ({ sw: document.documentElement.scrollWidth, cw: document.documentElement.clientWidth, sh: document.documentElement.scrollHeight }));
  await p.screenshot({ path: png, fullPage: full === '1' });
  console.log(JSON.stringify({ over, errs: errs.slice(0, 5) }));
  await b.close();
})();
