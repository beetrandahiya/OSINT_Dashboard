import math, sys
import marks as M
from variants import page
def wrap(inner): return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">{inner}</svg>'
def rot(P, deg, c=(32,32)):
    t=math.radians(deg); out=[]
    for x,y in P:
        dx,dy=x-c[0],y-c[1]
        out.append((c[0]+dx*math.cos(t)-dy*math.sin(t), c[1]+dx*math.sin(t)+dy*math.cos(t)))
    return out
rows=[]
# cocked hat rotations
for deg in (0, 25, 40, 180, 205):
    def mk(v, deg=deg):
        g=M.COCKED[v]; P=rot(g["P"],deg,(32,32.5)); w=g["w"]
        uid=f"r{deg}{v}"
        lines="".join(M._bearing(P[i],P[(i+1)%3],w,M.BP["lg5"]) for i in range(3))
        return wrap(M.clip(uid)+M.tile(M.BP["black"])+f'<g clip-path="url(#c{uid})">{lines}<polygon points="{M.pts(P)}" fill="{M.BP["blue4"]}"/></g>')
    rows.append((f"cocked rot {deg}", mk("small"), mk("full")))
# terminator band (2:1 map window)
def term_band(v):
    uid="tb"+v
    x0,x1,y0,y1 = (5,59,18.5,45.5) if v=="full" else (3,61,17,47)
    day=M.terminator_path(x0,x1,y0,y1,x0+(x1-x0)*0.62,360,0)
    tw=M.terminator_path(x0,x1,y0,y1,x0+(x1-x0)*0.62,360,-12 if v=="full" else -18)
    r=3 if v=="full" else 4
    return wrap(M.tile(M.ESA["deep"])+f'<clipPath id="m{uid}"><rect x="{x0}" y="{y0}" width="{x1-x0}" height="{y1-y0}" rx="{r}"/></clipPath>'
                f'<g clip-path="url(#m{uid})"><rect x="0" y="0" width="64" height="64" fill="{M.ESA["deep2"]}"/><path d="{tw}" fill="{M.ESA["blue"]}"/><path d="{day}" fill="{M.ESA["paper"]}"/></g>'
                f'<rect x="{x0}" y="{y0}" width="{x1-x0}" height="{y1-y0}" rx="{r}" fill="none" stroke="{M.ESA["grey"]}" stroke-width="{1.2 if v=="full" else 2}"/>')
rows.append(("term band", term_band("small"), term_band("full")))
# terminator 1.5 periods full tile
def term15(v, sub):
    uid=f"t15{v}{sub}"
    ytop,ybot=(-2,66)
    day=M.terminator_path(0,64,ytop,ybot,sub,540,0)
    tw=M.terminator_path(0,64,ytop,ybot,sub,540,-12 if v=="full" else -18)
    return wrap(M.clip(uid)+M.tile(M.ESA["deep"])+f'<g clip-path="url(#c{uid})"><path d="{tw}" fill="{M.ESA["blue"]}"/><path d="{day}" fill="{M.ESA["paper"]}"/></g>')
rows.append(("term 540 trough mid", term15("small",10.67), term15("full",10.67)))
rows.append(("term 540 peak mid", term15("small",32), term15("full",32)))
# quadkey stronger contrast
def quad2(v, plate, steps, grid=None):
    digits="12023" if v=="full" else "120"
    cells=M.quad_cells(digits); uid="q"+v+plate[1:]
    st=steps if v=="full" else [steps[0],steps[2],steps[3]]
    out=M.clip(uid)+M.tile(plate)+f'<g clip-path="url(#c{uid})">'
    for (x,y,s),col in zip(cells,st): out+=f'<rect x="{x}" y="{y}" width="{s}" height="{s}" fill="{col}"/>'
    if grid and v=="full": out+=f'<path d="M32 0V64M0 32H64" stroke="{grid}" stroke-width="1"/>'
    return wrap(out+"</g>")
B=M.BRG
rows.append(("quad petrol t60", quad2("small",B["petrol"],[B["t60"],B["t40"],B["t20"],B["white"],B["petrol"]]), quad2("full",B["petrol"],[B["t60"],B["t40"],B["t20"],B["white"],B["petrol"]],B["t80"])))
rows.append(("quad black", quad2("small","#000000",[B["petrol"],B["t60"],B["t20"],B["white"],B["petrol"]]), quad2("full","#000000",[B["petrol"],B["t60"],B["t20"],B["white"],B["petrol"]],"#1a1a1a")))
open(sys.argv[1],"w").write(page(rows))
