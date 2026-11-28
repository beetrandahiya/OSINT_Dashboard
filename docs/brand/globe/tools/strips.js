// Render each mark at 16/24/32/48 px on a dark taskbar, a light taskbar and a Dock-like shelf, 1 device pixel per px.
// Usage: node strips.js marks.json outdir
const { chromium } = require('playwright');
const fs = require('fs'), path = require('path');
const [,, src, out] = process.argv;
const marks = JSON.parse(fs.readFileSync(src, 'utf8'));
const BGS = { dark: 'background:#202020', light: 'background:#f3f3f3',
  dock: 'background:linear-gradient(160deg,#3a4a63,#1f2a3b 55%,#2d2438)' };
(async () => {
  const b = await chromium.launch();
  const p = await b.newPage({ deviceScaleFactor: 1, viewport: { width: 600, height: 200 } });
  for (const [key, m] of Object.entries(marks)) {
    for (const [bg, css] of Object.entries(BGS)) {
      const img = s => `<img src="data:image/svg+xml;base64,${Buffer.from(s <= 24 ? m.small : m.full).toString('base64')}" width="${s}" height="${s}">`;
      await p.setContent(`<body style="margin:0"><div id=s style="${css};display:inline-flex;gap:14px;align-items:center;padding:12px 16px;height:48px">${[16,24,32,48].map(img).join('')}</div></body>`);
      await p.waitForLoadState('load');
      await (await p.$('#s')).screenshot({ path: path.join(out, `${key}-${bg}.png`) });
    }
  }
  await b.close();
})();
