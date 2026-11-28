// node crop.js <png> <out> <y0> <y1>  : crop a vertical slice using a canvas page
const { chromium } = require('playwright'); const fs = require('fs');
(async () => {
  const [src, out, y0, y1] = process.argv.slice(2);
  const b = await chromium.launch(); const p = await b.newPage({ viewport: { width: 1700, height: 1000 } });
  const data = 'data:image/png;base64,' + fs.readFileSync(src).toString('base64');
  await p.setContent(`<canvas id=c></canvas><script>const i=new Image();i.onload=()=>{const c=document.getElementById('c');c.width=i.width;c.height=${y1}-${y0};c.getContext('2d').drawImage(i,0,-${y0});window.ok=1};i.src='${data}'</script>`);
  await p.waitForFunction(() => window.ok);
  const url = await p.evaluate(() => document.getElementById('c').toDataURL('image/png'));
  fs.writeFileSync(out, Buffer.from(url.split(',')[1], 'base64')); await b.close();
})();
