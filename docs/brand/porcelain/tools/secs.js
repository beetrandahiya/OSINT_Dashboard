const { chromium } = require('playwright');
(async () => {
  const b = await chromium.launch(); const scheme = process.argv[2] || 'light';
  const p = await b.newPage({ viewport: { width: 1440, height: 1000 }, colorScheme: scheme });
  await p.goto('file://' + process.cwd() + '/out/wrapped.html'); await p.waitForTimeout(3000);
  for (const id of (process.argv[3] || '.hero,#icon,#sizes,#name,#colour,#type,#devices,#components,#app,#documents,#splash').split(',')) {
    const el = await p.$(id); if (el) await el.screenshot({ path: `out/sec-${scheme}-${id.replace(/[#.]/g, '')}.png` });
  }
  await b.close();
})();
