const { chromium } = require('playwright');
(async () => {
  const b = await chromium.launch(); const p = await b.newPage({ viewport: { width: 1920, height: 1100 } });
  await p.goto('file://' + process.cwd() + '/out/wrapped.html'); await p.waitForTimeout(2500);
  await p.addStyleTag({ content: '.wrap{max-width:none!important;padding:0!important}' }); await p.evaluate(() => dispatchEvent(new Event('resize'))); await p.waitForTimeout(500);
  for (const id of ['map','map-folded','connections','connections-map','investigate','sources']) {
    const el = await p.$(`#${id} .fit`); await el.screenshot({ path: `out/b-${id}.png` });
  }
  await b.close();
})();
