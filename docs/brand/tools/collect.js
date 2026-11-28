// node collect.js <sheet.html> <out.png> <selector> <cols> <cellWidth> [scheme]
const { chromium } = require('playwright');
(async () => {
  const [html, out, sel, cols, cw, scheme = 'light'] = process.argv.slice(2);
  const b = await chromium.launch();
  const p = await b.newPage({ viewport: { width: cols * cw + 40, height: 800 }, colorScheme: scheme });
  await p.goto('file://' + html);
  await p.evaluate(() => document.fonts.ready);
  await p.evaluate(([sel, cols, cw]) => {
    const els = [...document.querySelectorAll(sel)].map(e => e.cloneNode(true));
    document.body.innerHTML = '';
    const g = document.createElement('div');
    g.style.cssText = `display:grid;grid-template-columns:repeat(${cols},${cw}px);gap:10px;padding:10px;background:#bbb`;
    els.forEach(e => { e.style.width = cw + 'px'; e.style.height = 'auto'; e.style.maxWidth = 'none'; g.appendChild(e); });
    document.body.appendChild(g);
  }, [sel, +cols, +cw]);
  await p.waitForTimeout(200);
  await p.screenshot({ path: out, fullPage: true });
  await b.close();
})();
