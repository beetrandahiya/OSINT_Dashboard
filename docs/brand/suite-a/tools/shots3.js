const { chromium } = require('playwright');
(async () => {
  const b = await chromium.launch(); const p = await b.newPage({ viewport: { width: 1920, height: 1100 } });
  await p.goto('file://' + process.cwd() + '/out/wrapped.html'); await p.waitForTimeout(2500);
  await p.addStyleTag({ content: '.wrap{max-width:none!important;padding:0!important}' }); await p.evaluate(() => dispatchEvent(new Event('resize'))); await p.waitForTimeout(500);
  for (const id of ['connections-air', 'connections-sea']) {
    const el = await p.$(`#${id} .fit`); await el.screenshot({ path: `out/b-${id}.png` });
    await p.click(`#${id} .tog button[data-t="l"]`); await p.waitForTimeout(200);
    await el.screenshot({ path: `out/b-${id}-l.png` });
  }
  const over = await p.evaluate(() => [...document.querySelectorAll('#connections-air .pnl, #connections-sea .pnl')].map(e => [e.closest('section.pg').id, e.querySelector('b')?.textContent, e.scrollHeight - e.clientHeight]));
  console.log(JSON.stringify(over));
  await b.close();
})();
