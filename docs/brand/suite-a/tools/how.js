const { chromium } = require('playwright');
(async () => {
  const b = await chromium.launch();
  for (const [w, s] of [[1440, 'dark'], [400, 'light']]) {
    const p = await b.newPage({ viewport: { width: w, height: 900 }, colorScheme: s });
    await p.goto('file://' + process.cwd() + '/out/wrapped.html'); await p.waitForTimeout(2500);
    const el = await p.$('#how'); await el.screenshot({ path: `out/how-${w}.png` });
    await p.close();
  }
  await b.close();
})();
