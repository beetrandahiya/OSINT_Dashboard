// Render every mark at taskbar/dock sizes on three backgrounds, 1x device pixels.
// Usage: node render.js <logoDir> [keyFilter]
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const dir = process.argv[2];
const only = process.argv[3] || '';
const SIZES = [16, 24, 32, 48, 256];
const BGS = {
  dark: 'background:#202020',
  light: 'background:#f3f3f3',
  // macOS Dock: translucent shelf over a wallpaper
  dock: 'background:linear-gradient(160deg,#3a4a63,#1f2a3b 55%,#2d2438)',
};

function stripHTML(svg, size, bg) {
  const pad = size >= 256 ? 28 : 12;
  const h = size + pad * 2;
  const w = size >= 256 ? h : size + 40;
  const shelf = bg === 'dock'
    ? `<div style="position:absolute;left:4px;right:4px;top:${pad - 6}px;bottom:${pad - 6}px;border-radius:${Math.max(8, size * .32)}px;background:rgba(255,255,255,.16);box-shadow:inset 0 0 0 .5px rgba(255,255,255,.28)"></div>`
    : '';
  const src = 'data:image/svg+xml;base64,' + Buffer.from(svg).toString('base64');
  return `<div class="strip" style="position:relative;width:${w}px;height:${h}px;${BGS[bg]}">${shelf}
    <img src="${src}" width="${size}" height="${size}" style="position:absolute;left:${(w - size) / 2}px;top:${pad}px"></div>`;
}

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ deviceScaleFactor: 1, viewport: { width: 400, height: 400 } });
  const keys = fs.readdirSync(path.join(dir, 'marks')).filter(f => f.endsWith('.svg') && !f.includes('-small') && f.startsWith(only)).map(f => f.replace('.svg', ''));
  for (const key of keys) {
    const full = fs.readFileSync(path.join(dir, 'marks', key + '.svg'), 'utf8');
    const smallPath = path.join(dir, 'marks', key + '-small.svg');
    const small = fs.existsSync(smallPath) ? fs.readFileSync(smallPath, 'utf8') : full;
    for (const size of SIZES) {
      const svg = size <= 24 ? small : full;
      for (const bg of Object.keys(BGS)) {
        await page.setContent(`<html><body style="margin:0">${stripHTML(svg, size, bg)}</body></html>`);
        await page.waitForLoadState('load');
        const el = await page.$('.strip');
        await el.screenshot({ path: path.join(dir, 'renders', `${key}-${size}-${bg}.png`) });
      }
    }
    console.log('rendered', key);
  }
  // review sheet: 4x nearest-neighbour zoom of 16-48, plus the 256
  const rows = keys.map(key => {
    const cells = Object.keys(BGS).map(bg => [16, 24, 32, 48].map(s => {
      const f = 'data:image/png;base64,' + fs.readFileSync(path.join(dir, 'renders', `${key}-${s}-${bg}.png`)).toString('base64');
      const w = s + 40, h = s + 24;
      return `<img src="${f}" style="width:${w * 4}px;height:${h * 4}px;image-rendering:pixelated;margin:2px">`;
    }).join('')).join('<br>');
    const big = 'data:image/png;base64,' + fs.readFileSync(path.join(dir, 'renders', `${key}-256-dark.png`)).toString('base64');
    return `<div style="display:flex;gap:12px;align-items:flex-start;margin:8px 0;font:14px sans-serif;color:#ccc">
      <div style="width:120px">${key}</div><div>${cells}</div><img src="${big}" style="width:250px"></div>`;
  }).join('');
  fs.mkdirSync(path.join(dir, 'review'), { recursive: true });
  const rp = await browser.newPage({ deviceScaleFactor: 1, viewport: { width: 1900, height: 900 } });
  for (const key of keys) {
    const html = rows.split('<div style="display:flex').filter(r => r.includes(`>${key}<`)).map(r => '<div style="display:flex' + r).join('');
    await rp.setContent(`<html><body style="margin:8px;background:#555">${html}</body></html>`);
    await rp.waitForLoadState('load');
    await rp.screenshot({ path: path.join(dir, 'review', key + '.png'), fullPage: true });
  }
  await browser.close();
})();
