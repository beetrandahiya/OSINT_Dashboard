import math, sys
import marks as M
import typo
from variants import page
def wrap(inner): return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">{inner}</svg>'
rows=[]
U=M.UN
# great circle asymmetric
def gc(v, a, b, c1, c2, sw, rn, rd, chord=True):
    fg=U["white"]; pl=U["blue"]
    out=M.tile(pl)+f'<path d="M{a[0]} {a[1]} C{c1[0]} {c1[1]} {c2[0]} {c2[1]} {b[0]} {b[1]}" fill="none" stroke="{fg}" stroke-width="{sw}" stroke-linecap="round"/>'
    if chord:
        dx,dy=b[0]-a[0],b[1]-a[1]; n=math.hypot(dx,dy); ux,uy=dx/n,dy/n
        s=(a[0]+ux*(rn+5),a[1]+uy*(rn+5)); e=(b[0]-ux*(rd+4),b[1]-uy*(rd+4))
        if v=="full": out+=f'<line x1="{s[0]:.1f}" y1="{s[1]:.1f}" x2="{e[0]:.1f}" y2="{e[1]:.1f}" stroke="{fg}" stroke-width="2.6" stroke-dasharray="3.4 3"/>'
        else: out+=f'<line x1="{s[0]:.1f}" y1="{s[1]:.1f}" x2="{e[0]:.1f}" y2="{e[1]:.1f}" stroke="{fg}" stroke-width="3.6" stroke-dasharray="5 4"/>'
    out+=f'<circle cx="{a[0]}" cy="{a[1]}" r="{rn}" fill="{pl}" stroke="{fg}" stroke-width="{sw*0.7:.1f}"/><circle cx="{b[0]}" cy="{b[1]}" r="{rd}" fill="{fg}"/>'
    return wrap(out)
rows.append(("gc asym A", gc("small",(11,50),(52,40),(12,10),(40,6),8,5.5,8), gc("full",(12,49),(51,39),(13,14),(38,9),5,4,5.6)))
rows.append(("gc asym B", gc("small",(10,49),(54,33),(18,9),(44,8),8,5.5,8), gc("full",(11,48),(53,34),(18,12),(42,10),5,4,5.6)))
rows.append(("gc no chord", gc("small",(10,49),(54,33),(18,9),(44,8),8,5.5,8,False), gc("full",(11,48),(53,34),(18,12),(42,10),5,4,5.6)))
# plot: curved trail + diamond head
N=M.NGA
def plot(v, dots, r, head, hs, ang):
    out=M.tile(N["navy2"])
    for x,y in dots: out+=f'<circle cx="{x}" cy="{y}" r="{r}" fill="{N["mist"]}"/>'
    hx,hy=head; t=math.radians(ang)
    ux,uy=math.cos(t),math.sin(t); px,py=-uy,ux
    d=[(hx+ux*hs*1.25,hy+uy*hs*1.25),(hx+px*hs*.8,hy+py*hs*.8),(hx-ux*hs*.9,hy-uy*hs*.9),(hx-px*hs*.8,hy-py*hs*.8)]
    out+=f'<polygon points="{M.pts(d)}" fill="{N["teal"]}"/>'
    return wrap(out)
rows.append(("plot curve", plot("small",[(12,50),(18,36)],5,(37,26),11,-20), plot("full",[(12,51),(14,42),(19,34),(26,28.5)],3,(40,25),8.5,-12)))
rows.append(("plot square tgt", wrap(M.tile(N["navy2"])+''.join(f'<circle cx="{x}" cy="{y}" r="5" fill="{N["mist"]}"/>' for x,y in [(11,51),(20,40)])+f'<rect x="31" y="20" width="18" height="18" fill="none" stroke="{N["teal"]}" stroke-width="6"/>'),
             wrap(M.tile(N["navy2"])+''.join(f'<circle cx="{x}" cy="{y}" r="3" fill="{N["mist"]}"/>' for x,y in [(10,52),(16,46),(22,40)])+f'<rect x="31" y="22" width="15" height="15" fill="none" stroke="{N["teal"]}" stroke-width="4"/><line x1="46" y1="22" x2="54" y2="14" stroke="{N["teal"]}" stroke-width="3" stroke-linecap="round"/>')))
# GMT rework: ring with ticked night half
A=M.NASA
def gmt(v):
    cx=cy=32
    if v=="full": r,w,nt,hl,tip=20,7,12,12,6.5
    else: r,w,nt,hl,tip=21.5,10,6,9,9
    out=M.tile(A["blue"])
    out+=f'<path d="{M._arc(cx,cy,r,90,270)}" fill="none" stroke="{A["white"]}" stroke-width="{w}"/>'
    # night half as ticks: nt segments between 270..450
    seg=180/nt
    for i in range(nt):
        a0=270+i*seg+seg*0.22; a1=270+(i+1)*seg-seg*0.22
        out+=f'<path d="{M._arc(cx,cy,r,a0,a1)}" fill="none" stroke="{A["white"]}" stroke-width="{w}"/>'
    ang=math.radians(-58); ux,uy=math.sin(ang),-math.cos(ang)
    hx,hy=cx+ux*hl,cy+uy*hl; px,py=-uy,ux
    t1=(hx+ux*tip*1.3,hy+uy*tip*1.3); t2=(hx+px*tip*.75,hy+py*tip*.75); t3=(hx-px*tip*.75,hy-py*tip*.75)
    hw=3 if v=="full" else 4.5
    out+=f'<line x1="{cx}" y1="{cy}" x2="{hx:.1f}" y2="{hy:.1f}" stroke="{A["white"]}" stroke-width="{hw}" stroke-linecap="round"/><polygon points="{M.pts([t1,t2,t3])}" fill="{A["red"]}"/><circle cx="{cx}" cy="{cy}" r="{hw*1.1:.1f}" fill="{A["white"]}"/>'
    return wrap(out)
rows.append(("gmt ticks", gmt("small"), gmt("full")))
# GMT alt: ring split two tones: solid white day half, red-free; night half = plate with white outline
def gmt2(v):
    cx=cy=32
    r,w=(20,8) if v=="full" else (21,11)
    out=M.tile(A["blue"])
    out+=f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{A["white"]}" stroke-width="{w}" opacity=".38"/>'
    out+=f'<path d="{M._arc(cx,cy,r,90,270)}" fill="none" stroke="{A["white"]}" stroke-width="{w}"/>'
    # hand: red triangle pointer from centre to night half
    ang=math.radians(-55); ux,uy=math.sin(ang),-math.cos(ang); px,py=-uy,ux
    L=r-w/2-2.5; bw=(4 if v=="full" else 6)
    tri=[(cx+ux*L,cy+uy*L),(cx+px*bw,cy+py*bw),(cx-px*bw,cy-py*bw)]
    out+=f'<polygon points="{M.pts(tri)}" fill="{A["red"]}"/><circle cx="{cx}" cy="{cy}" r="{bw}" fill="{A["red"]}"/>'
    return wrap(out)
rows.append(("gmt two-tone", gmt2("small"), gmt2("full")))
# contact rework: NATO navy sky, light-blue sea arc, white mast
T=M.NATO
def contact(v, sea=T["light"]):
    R_,top,mx,mw,mt=(92,42,41,4.2,24) if v=="full" else (80,40,40,7,15)
    cy=top+R_; uid="ct"+v+sea[1:]
    foot=cy-math.sqrt(R_**2-(mx-32)**2)
    return wrap(M.clip(uid)+M.tile(T["blue"])+f'<g clip-path="url(#c{uid})"><circle cx="32" cy="{cy}" r="{R_}" fill="{sea}"/><rect x="{mx-mw/2}" y="{mt}" width="{mw}" height="{foot-mt+1}" fill="{T["white"]}"/></g>')
rows.append(("contact nato", contact("small"), contact("full")))
# footnote: serif W + red superscript 1
C=M.CAN
def footnote(v, key="fraunces-600"):
    if v=="full": size,x,y,fs,fx,fy=44,7,48,22,46,30
    else: size,x,y,fs,fx,fy=50,3,51,26,46,30
    d,w,cap=typo.text_path(key,"W",size)
    d1,w1,_=typo.text_path(key,"1",fs)
    return wrap(M.tile(C["slate"])+f'<path transform="translate({x} {y})" d="{d}" fill="{C["white"]}"/><path transform="translate({fx} {fy})" d="{d1}" fill="{C["red"]}"/>')
rows.append(("footnote fraunces", footnote("small"), footnote("full")))
def footnote2(v):
    # W + red square footnote marker
    key="librefranklin-700"
    size,x,y=(46,4,49) if v=="full" else (54,1,52)
    d,w,cap=typo.text_path(key,"W",size)
    sq=(48,14,8) if v=="full" else (50,10,11)
    return wrap(M.tile(C["slate"])+f'<path transform="translate({x} {y})" d="{d}" fill="{C["white"]}"/><rect x="{sq[0]}" y="{sq[1]}" width="{sq[2]}" height="{sq[2]}" fill="{C["red"]}"/>')
rows.append(("footnote franklin sq", footnote2("small"), footnote2("full")))
# date line: EU blue / yellow split by simplified real IDL
E=M.EU
def idl(v):
    # lon offsets from 180 (east +) by latitude, simplified from the real line
    path=[(90,0),(75,0),(68,11),(65.5,11),(53,-10),(47.5,0),(5,0),(5,30),(-10,30),(-12,10),(-45,7.5),(-51,0),(-90,0)]
    k=0.55 if v=="full" else 0.6
    pts_=[(32+lo*k, 32-la/90*34) for la,lo in path]
    d="M"+" L".join(f"{x:.1f} {y:.1f}" for x,y in pts_)+" L80 -10 L80 80 Z"
    d2="M"+" L".join(f"{x:.1f} {y:.1f}" for x,y in pts_)+" L-20 80 L-20 -10 Z"
    uid="idl"+v
    return wrap(M.clip(uid)+M.tile(E["blue"])+f'<g clip-path="url(#c{uid})"><path d="{d}" fill="{E["yellow"]}"/></g>')
rows.append(("date line", idl("small"), idl("full")))
open(sys.argv[1],"w").write(page(rows))
