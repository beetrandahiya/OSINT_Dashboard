"""Render candidate SVGs side by side at true 16/24/48 px (zoomed 4x, nearest neighbour) + 160 px."""
import base64, json
def page(rows):
    data = []
    for label, sm, fu in rows:
        data.append([label, "data:image/svg+xml;base64," + base64.b64encode(sm.encode()).decode(),
                     "data:image/svg+xml;base64," + base64.b64encode(fu.encode()).decode()])
    return """<html><body style="margin:6px;background:#666;font:12px sans-serif;color:#eee"><div id=r></div><script>
const D=%s;
const r=document.getElementById('r');
let pending=0;
for(const [label,sm,fu] of D){
  const row=document.createElement('div');row.style.cssText='display:flex;align-items:center;gap:6px;margin:4px 0';
  const l=document.createElement('div');l.style.width='110px';l.textContent=label;row.appendChild(l);
  for(const bg of ['#202020','#f3f3f3']) for(const s of [16,24,48]){
    const c=document.createElement('canvas');c.width=s+8;c.height=s+8;
    c.style.cssText=`width:${(s+8)*4}px;height:${(s+8)*4}px;image-rendering:pixelated`;
    const ctx=c.getContext('2d');ctx.fillStyle=bg;ctx.fillRect(0,0,s+8,s+8);
    const im=new Image();pending++;im.onload=()=>{ctx.drawImage(im,4,4,s,s);pending--;};im.src=s<=24?sm:fu;
    row.appendChild(c);
  }
  const big=new Image();big.src=fu;big.width=160;big.height=160;row.appendChild(big);
  r.appendChild(row);
}
window.done=()=>pending===0;
</script></body></html>""" % json.dumps(data)
