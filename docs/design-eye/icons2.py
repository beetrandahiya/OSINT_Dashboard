"""Deeper God's eye symbol set: precise silhouettes generated from parameters (top view, nose up, 64 grid).
Families: solid and line (renderers from icons.py). Elements: (d, mode) with f fill, k knockout, s stroke, d dashed, a area, x accent."""
import math
import icons as I
from icons import circ, star, trefoil
def R(x, y, w, h): return f'M{x:.1f} {y:.1f}h{w:.1f}v{h:.1f}h{-w:.1f}Z'
def poly(pts): return 'M' + ' L'.join(f'{x:.1f} {y:.1f}' for x, y in pts) + 'Z'
def mirror(pts): return [(64 - x, y) for x, y in pts]
# ---------- aircraft ----------
def plane(L=54, fw=5.5, wy=26, span=54, sweep=10, cr=11, ct=3.5, tsp=20, tsw=5, tcr=6, tct=2.5, eng=(), rear=None, props=False, dome=None, boom=False, vtail=False, cheeks=False, nose=None):
    y0, y1 = 32 - L/2, 32 + L/2; h = fw/2
    nl = nose if nose is not None else fw*1.6
    fus = (f'M32 {y0:.1f}C{32+h:.1f} {y0:.1f} {32+h:.1f} {y0+nl*0.5:.1f} {32+h:.1f} {y0+nl:.1f}L{32+h:.1f} {y1-fw*1.4:.1f}L{32+h*0.35:.1f} {y1:.1f}'
           f'L{32-h*0.35:.1f} {y1:.1f}L{32-h:.1f} {y1-fw*1.4:.1f}L{32-h:.1f} {y0+nl:.1f}C{32-h:.1f} {y0+nl*0.5:.1f} {32-h:.1f} {y0:.1f} 32 {y0:.1f}Z')
    g = [(fus, 'f')]
    wing = [(32 + h - 0.6, wy), (32 + span/2, wy + sweep), (32 + span/2, wy + sweep + ct), (32 + h - 0.6, wy + cr)]
    g += [(poly(wing), 'f'), (poly(mirror(wing)), 'f')]
    ty = y1 - fw*1.4 - tcr*0.9
    if vtail:
        t = [(32 + h*0.6, ty), (32 + tsp/2, ty + tsw - 3), (32 + tsp/2, ty + tsw - 3 + tct), (32 + h*0.6, ty + tcr)]
    else:
        t = [(32 + h - 0.6, ty), (32 + tsp/2, ty + tsw), (32 + tsp/2, ty + tsw + tct), (32 + h - 0.6, ty + tcr)]
    g += [(poly(t), 'f'), (poly(mirror(t)), 'f')]
    for f, ln, wd, ah in eng:   # fraction of half-span, pod length, width, how far ahead of the leading edge
        dx = h + f*(span/2 - h); ly = wy + sweep*(dx - h)/(span/2 - h)
        for sx in (1, -1):
            x = 32 + sx*dx
            g.append((R(x - wd/2, ly - ah, wd, ln), 'f'))
            if props: g.append((R(x - 5.5, ly - ah - 1.6, 11, 1.6), 'f'))
    if rear:
        yy, ln, wd = rear
        for sx in (1, -1): g.append((R(32 + sx*(h + wd/2 + 0.4) - wd/2, yy, wd, ln), 'f'))
    if props and not eng: g.append((R(26.5, y0 - 1.2, 11, 1.6), 'f'))
    if dome: g.append((circ(32, dome[0], dome[1]), 'f')); g.append((circ(32, dome[0], dome[1]*0.45), 'k'))
    if boom: g.append((poly([(31.2, y1 - 1), (32.8, y1 - 1), (33.6, y1 + 6), (30.4, y1 + 6)]), 'f'))
    if cheeks: g += [(R(32 + h - 0.2, y0 + nl, 1.8, 7), 'f'), (R(32 - h - 1.6, y0 + nl, 1.8, 7), 'f')]
    return g
def heli(rot='x', tandem=False, stub=False, body=(9, 20), boom=22):
    bw, bl = body; g = []
    if tandem:
        g.append((f'M{32-bw/2} 12a{bw/2} {bw/2} 0 0 1 {bw} 0V52a{bw/2} {bw/2} 0 0 1 {-bw} 0Z', 'f'))
        for cy in (13, 51):
            g += [(f'M{32-15} {cy-6}L{32+15} {cy+6}', 's'), (f'M{32-15} {cy+6}L{32+15} {cy-6}', 's'), (circ(32, cy, 3.5), 'f')]
        return g
    by = 14
    g.append((f'M32 {by}c{bw/2} 0 {bw/2} 3 {bw/2} 7v{bl-12}c0 3-{bw/4} 5-{bw/2} 5s-{bw/2}-2-{bw/2}-5v-{bl-12}c0-4 0-7 {bw/2}-7Z', 'f'))
    g.append((R(31, by + bl - 2, 2, boom), 'f')); g.append((R(27, by + bl + boom - 4, 10, 2.4), 'f'))
    if stub: g.append((R(32 - bw/2 - 6, by + 9, bw + 12, 3), 'f'))
    if rot == 'x':
        g += [('M12 4L52 44', 's'), ('M52 4L12 44', 's')]
    elif rot == '2':
        g += [('M8 22L56 22', 's')]
    else:
        g += [('M10 13L54 31', 's'), ('M10 31L54 13', 's'), ('M32 2V42', 's')]
    return g
STEALTH = [(poly([(32, 4), (44, 30), (60, 46), (60, 50), (44, 48), (40, 58), (32, 54), (24, 58), (20, 48), (4, 50), (4, 46), (20, 30)]), 'f')]
FLYWING = [(poly([(32, 14), (62, 40), (58, 44), (50, 40), (44, 46), (38, 42), (32, 48), (26, 42), (20, 46), (14, 40), (6, 44), (2, 40)]), 'f')]
BALLOON = [('M32 5a20 20 0 0 1 20 20c0 9.5-7.5 15.5-12.5 21h-15C19.5 40.5 12 34.5 12 25A20 20 0 0 1 32 5zM27 49h10v9H27z', 'f')]
AIRSHIP = [('M32 4c7 0 10 12 10 26s-3 26-10 26-10-12-10-26 3-26 10-26z', 'f'), (poly([(25, 50), (18, 60), (24, 60), (30, 54)]), 'f'), (poly(mirror([(25, 50), (18, 60), (24, 60), (30, 54)])), 'f')]
GROUND = [('M22 20h20a3 3 0 0 1 3 3v18a3 3 0 0 1-3 3H22a3 3 0 0 1-3-3V23a3 3 0 0 1 3-3z', 'f')]
AIR = [  # id, name, glyph, ICAO type codes (broadcast) that map to it, colour key, small-size fallback
 ('narrow', 'Airliner, narrow body', plane(eng=[(0.36, 7, 3.4, 3)]), 'A319 A320 A321 A20N A21N B737 B738 B739 B38M B39M B752 C919 A318', 'civil', 'jet'),
 ('wide', 'Airliner, wide body', plane(L=58, fw=7, span=60, cr=13, eng=[(0.33, 9, 4.6, 4)]), 'A332 A333 A339 A359 A35K B762 B763 B772 B77W B788 B789 B78X', 'civil', 'heavy'),
 ('quad', 'Airliner, four engines', plane(L=60, fw=7.5, span=62, cr=14, eng=[(0.3, 8, 3.8, 3), (0.62, 7, 3.4, 2.5)]), 'B744 B748 A388 A346 A343 IL96', 'civil', 'heavy'),
 ('regional', 'Regional jet', plane(L=48, fw=4.6, span=44, sweep=7, cr=9, eng=[(0.36, 6, 3, 2)]), 'E170 E175 E190 E195 E290 E295 BCS1 BCS3 CRJ7 CRJ9 CRJX', 'civil', 'jet'),
 ('turboprop', 'Turboprop airliner', plane(L=50, fw=5, span=54, sweep=0, cr=7, ct=4.5, eng=[(0.33, 7, 3, 3)], props=True, tsw=0), 'AT72 AT76 AT75 DH8D DH8C DH8B SF34 D328', 'civil', 'prop'),
 ('bizjet', 'Business jet', plane(L=46, fw=4.4, span=38, sweep=8, cr=8, ct=3, rear=(40, 7, 3.2), tsp=16), 'GLF4 GLF5 GLF6 GLEX GL5T GL7T CL60 CL35 C680 C68A C750 FA7X FA8X LJ45 E55P C560 PC24 H25B', 'civil', 'jet'),
 ('light', 'Light aircraft', plane(L=40, fw=4.4, span=46, sweep=0, cr=6, ct=5, tsw=0, props=True), 'C172 C182 P28A SR22 DA40 DA42 C152 PA46 TBM7 TBM9 PC12 C208', 'civil', 'prop'),
 ('glider', 'Glider', plane(L=42, fw=3.4, span=62, sweep=0, cr=4.2, ct=2.4, tsw=0, tsp=14, tcr=4), 'GLID', 'civil', 'glider'),
 ('heli_light', 'Helicopter, light', heli('3', body=(8, 16), boom=20), 'A119 EC30 EC35 R44 R22 B06 B407 AS50 EC20 A109', 'civil', 'heli'),
 ('heli_med', 'Helicopter, medium / utility', heli('x', body=(10, 20), boom=22), 'H60 S70 NH90 AS32 EC75 EC45 EC25 A139 A169 B412 MI8 S92', 'mil', 'heli'),
 ('heli_tandem', 'Helicopter, tandem rotor', heli(tandem=True), 'H47 CH47', 'mil', 'heli'),
 ('heli_attack', 'Attack helicopter', heli('x', stub=True, body=(7, 20), boom=22), 'H64 AH64 TIGR MI24 MI28 KA52 AH1', 'mil', 'heli'),
 ('trainer_prop', 'Trainer, propeller', plane(L=42, fw=4.8, span=40, sweep=2, cr=7, ct=4, tsw=1, props=True), 'PC21 PC9 PC7 T6 G120 EMB3 T27', 'mil', 'prop'),
 ('twin_tp', 'Twin turboprop, light', plane(L=44, fw=4.6, span=48, sweep=0, cr=6.5, ct=4, tsw=0, eng=[(0.28, 6, 3, 3)], props=True), 'BE20 B350 BE9L C295 CN35 DHC6 P180 L410 BE30', 'mil', 'prop'),
 ('tactical', 'Tactical airlifter', plane(L=52, fw=7, span=60, sweep=0, cr=8, ct=5, tsw=0, eng=[(0.3, 7, 3, 3), (0.6, 7, 3, 3)], props=True, tsp=24), 'C130 C30J A400 AN12 Y8 Y9 KC39', 'mil', 'heavy'),
 ('strategic', 'Strategic airlifter', plane(L=58, fw=8, span=60, sweep=9, cr=12, ct=4, eng=[(0.32, 8, 3.6, 3), (0.6, 7, 3.4, 2.5)], tsp=26), 'C17 C5M IL76 A124 Y20 AN22', 'mil', 'heavy'),
 ('tanker', 'Tanker', plane(L=56, fw=6, span=56, cr=11, eng=[(0.3, 7, 3.4, 3), (0.6, 6, 3, 2.5)], boom=True), 'K35R KC46 KC10 IL78 MRTT A310 KC2', 'tanker', 'heavy'),
 ('awacs', 'Airborne early warning (radar dome)', plane(L=56, fw=6, span=56, cr=11, eng=[(0.3, 7, 3.4, 3), (0.6, 6, 3, 2.5)], dome=(38, 9)), 'E3TF E3CF E767 A50 KJ2K E2 E737 GLEX-AEW', 'isr', 'heavy'),
 ('mpa', 'Patrol / surveillance jet', plane(L=54, fw=5.5, span=50, cr=10, eng=[(0.36, 7, 3.4, 3)], cheeks=True), 'P8 R135 E6 E8 IL20 IL38 P1 RC12 MC12 Q4MA', 'isr', 'jet'),
 ('fighter', 'Fighter', [(I.SH['fighter'], 'f')], 'F16 F15 F18 FA18 F18S EUFI RFAL GRIF SU27 SU30 SU35 MG29 J10 J11 F5 M2K TOR', 'mil', 'fighter'),
 ('stealth', 'Stealth fighter', STEALTH, 'F35 F22 J20 SU57', 'mil', 'fighter'),
 ('trainer_jet', 'Trainer jet', plane(L=42, fw=4.4, span=34, sweep=6, cr=8, ct=3, tsp=16), 'T38 HAWK M346 L39 T7 K8 L159 ALJ', 'mil', 'jet'),
 ('bomber', 'Bomber', plane(L=60, fw=5.6, span=62, sweep=16, cr=11, ct=3, eng=[(0.3, 7, 4.4, 3), (0.55, 7, 4.4, 2.5), (0.78, 7, 4.4, 2)]), 'B52 TU95 H6 TU16', 'mil', 'heavy'),
 ('flywing', 'Flying-wing bomber', FLYWING, 'B2 B21', 'mil', 'heavy'),
 ('hale', 'Drone, high altitude (Global Hawk class)', plane(L=40, fw=4.6, span=62, sweep=0, cr=4, ct=2.2, vtail=True, tsp=16, tcr=4), 'GLHK Q4 RQ4 MQ4 TRIT', 'isr', 'drone'),
 ('male', 'Drone, medium altitude (Reaper class)', plane(L=34, fw=4.2, span=56, sweep=0, cr=4, ct=2.4, vtail=True, tsp=14, tcr=4, props=False), 'Q9 MQ9 Q1 TB2 TB3 HRON WL2 CH4', 'isr', 'drone'),
 ('mil_generic', 'Military aircraft, type not mapped', I.S['military']['g'], 'any other military type code', 'mil', 'jet'),
 ('vip', 'Government / VIP aircraft', plane(L=54, fw=5.5, span=50, cr=10, eng=[(0.36, 7, 3.4, 3)]) + [(star(5, 7, 3, 32, 40), 'k')], 'from plane-alert-db, any type', 'vip', 'jet'),
 ('doomsday', 'Airborne command post', plane(L=60, fw=7.5, span=62, cr=14, eng=[(0.3, 8, 3.8, 3), (0.62, 7, 3.4, 2.5)]) + [(circ(32, 26, 4), 'k')], 'E4B E6B IL80 IL86VKP TU214SR', 'doom', 'heavy'),
 ('balloon', 'Balloon', BALLOON, 'BALL', 'civil', 'balloon'),
 ('airship', 'Airship', AIRSHIP, 'SHIP', 'civil', 'balloon'),
 ('ground', 'On the ground (vehicle or parked)', GROUND, 'category C1 C2', 'civil', 'ground'),
]
# ---------- ships (AIS ship-type codes) ----------
def hull(L=56, B=18, bow=16, stern='sq', cx=32):
    y0, y1 = 32 - L/2, 32 + L/2; h = B/2
    st = f'L{cx+h:.1f} {y1:.1f}L{cx-h:.1f} {y1:.1f}' if stern == 'sq' else f'L{cx+h:.1f} {y1-h:.1f}A{h:.1f} {h:.1f} 0 0 1 {cx-h:.1f} {y1-h:.1f}'
    return f'M{cx} {y0:.1f}C{cx+h*0.9:.1f} {y0+bow*0.4:.1f} {cx+h:.1f} {y0+bow*0.7:.1f} {cx+h:.1f} {y0+bow:.1f}{st}L{cx-h:.1f} {y0+bow:.1f}C{cx-h:.1f} {y0+bow*0.7:.1f} {cx-h*0.9:.1f} {y0+bow*0.4:.1f} {cx} {y0:.1f}Z'
SHIPS = [
 ('cargo', 'Cargo ship', [(hull(), 'f'), (R(27, 22, 10, 6), 'k'), (R(27, 31, 10, 6), 'k'), (R(27, 40, 10, 6), 'k'), (R(25, 52, 14, 4), 'k')], 'AIS 70-79', 'ship'),
 ('container', 'Container ship', [(hull(L=58, B=19), 'f'), (R(25.5, 20, 13, 26), 'k'), (R(27, 21.5, 10, 3), 'f'), (R(27, 27, 10, 3), 'f'), (R(27, 32.5, 10, 3), 'f'), (R(27, 38, 10, 3), 'f'), (R(25, 52, 14, 4), 'k')], 'AIS 70-79', 'ship'),
 ('tanker_s', 'Tanker', [(hull(L=58, B=19, bow=13, stern='rd'), 'f'), (R(30.5, 15, 3, 32), 'k'), (R(25, 50, 14, 4), 'k')], 'AIS 80-89', 'ship'),
 ('passenger', 'Passenger ship / ferry', [(hull(L=56, B=19, stern='rd'), 'f'), (R(26, 18, 12, 30), 'k'), (R(29, 21, 6, 24), 'f')], 'AIS 60-69', 'ship'),
 ('fishing', 'Fishing vessel', [(hull(L=42, B=17, bow=12), 'f'), (R(27, 32, 10, 8), 'k'), ('M32 26L32 6', 's'), ('M32 10L44 4', 's')], 'AIS 30', 'ship'),
 ('tug', 'Tug / towing', [(hull(L=36, B=21, bow=10, stern='rd'), 'f'), (circ(32, 34, 4.5), 'k'), ('M32 50V62', 'd')], 'AIS 31, 32, 52', 'ship'),
 ('sailing', 'Sailing boat', [(hull(L=40, B=13, bow=14, stern='rd'), 'f'), ('M32 12L32 50', 's'), (poly([(34, 14), (50, 44), (34, 44)]), 'f')], 'AIS 36', 'ship'),
 ('pleasure', 'Pleasure craft', [(hull(L=34, B=16, bow=12, stern='sq'), 'f'), (R(27, 38, 10, 7), 'k')], 'AIS 37', 'ship'),
 ('hsc', 'High-speed craft (catamaran)', [(hull(L=50, B=7, bow=12, cx=23), 'f'), (hull(L=50, B=7, bow=12, cx=41), 'f'), (R(22, 26, 20, 14), 'f')], 'AIS 40-49', 'ship'),
 ('sar', 'Pilot / search and rescue', [(hull(L=38, B=17, bow=12, stern='rd'), 'f'), (R(30, 26, 4, 16), 'k'), (R(24, 32, 16, 4), 'k')], 'AIS 50, 51', 'ship'),
 ('warship_s', 'Warship (on AIS)', [(hull(L=60, B=15, bow=20), 'f'), (R(28, 30, 8, 14), 'k'), (circ(32, 20, 3), 'k')], 'AIS 35', 'ship'),
 ('carrier', 'Aircraft carrier', [(poly([(22, 3), (40, 3), (43, 12), (43, 61), (19, 61), (19, 12)]), 'f'), (R(43, 26, 6, 13), 'f'), (poly([(23, 9), (27, 9), (36, 54), (32, 54)]), 'k')], 'USNI tracker (CVN)', 'ship'),
 ('amphib', 'Amphibious assault ship', [(poly([(23, 3), (41, 3), (42, 10), (42, 61), (22, 61), (22, 10)]), 'f'), (R(42, 27, 5.5, 11), 'f'), (R(26, 53, 12, 5), 'k'), (R(30.5, 11, 3, 36), 'k')], 'USNI tracker (LHA, LHD)', 'ship'),
 ('sanctioned', 'Sanctioned / shadow-fleet ship', [(hull(L=58, B=19, bow=13, stern='rd'), 'f'), (R(30.5, 15, 3, 32), 'k'), (circ(49, 12, 10), 'x')], 'OpenSanctions match', 'ship'),
]
# ---------- satellites (UCS purpose) ----------
def sat(extra, panels=True):
    g = [(R(26, 26, 12, 12), 'f')]
    if panels: g += [(R(3, 28.5, 19, 7), 'f'), (R(42, 28.5, 19, 7), 'f'), (R(22, 31, 4, 2), 'f'), (R(38, 31, 4, 2), 'f')]
    return g + extra
SATS = [
 ('sat_img', 'Imaging (camera)', sat([(circ(32, 32, 3.6), 'k')]), 'UCS: Earth observation, optical', 'leo'),
 ('sat_sar', 'Radar imaging', sat([(R(22, 40, 20, 8), 'f')]), 'UCS: radar', 'leo'),
 ('sat_sig', 'Signals intelligence', sat([(circ(32, 16, 9), 's'), ('M32 25V20', 's')]), 'UCS: signals / ELINT', 'spy'),
 ('sat_warn', 'Missile early warning', sat([(R(29, 12, 6, 14), 'f'), (circ(32, 12, 3), 'k')]), 'UCS: early warning', 'spy'),
 ('sat_wx', 'Weather', sat([('M24 44a8 8 0 0 1 16 0', 's'), ('M20 50a12 12 0 0 1 24 0', 's')]), 'UCS: meteorology', 'geo'),
 ('sat_nav', 'Navigation (GPS, Galileo...)', sat([(poly([(32, 40), (37, 50), (27, 50)]), 'f')]), 'UCS: navigation', 'meo'),
 ('sat_com', 'Communications', sat([('M22 18a10 10 0 0 0 20 0Z', 'f'), ('M32 18V26', 's')]), 'UCS: communications', 'geo'),
 ('sat_sci', 'Science', sat([(R(29.5, 10, 5, 16), 'f')], panels=True), 'UCS: space science', 'heo'),
 ('sat_tech', 'Technology test', [(R(20, 20, 24, 24), 'f'), (R(28, 28, 8, 8), 'k'), ('M32 20V8', 's')], 'UCS: technology development', 'leo'),
 ('sat_spy', 'Military imaging / signals (flag)', [(poly([(32, 6), (54, 32), (32, 58), (10, 32)]), 'f'), (circ(32, 32, 7), 'k')], 'UCS military users + McCants list', 'spy'),
 ('iss', 'Space station', I.S['iss']['g'], 'CelesTrak stations', 'leo'),
 ('starlink', 'Constellation satellite (Starlink, OneWeb...)', [(R(22, 24, 20, 16), 'f'), (R(4, 28, 18, 8), 'f'), (R(24, 27, 16, 2), 'k')], 'name family', 'leo'),
 ('debris', 'Rocket body / debris', [(R(25, 10, 14, 34), 'f'), (poly([(25, 44), (39, 44), (44, 56), (20, 56)]), 'f')], 'catalogue object type', 'net'),
 ('launch', 'Launch pad, launch coming up', I.S['launch']['g'], 'Launch Library 2', 'launch'),
]
# ---------- conflict (GDELT CAMEO codes) ----------
BURST = star(8, 29, 14)
def badge_in(inner):   # pictogram knocked out of the burst centre
    return [(BURST, 'f'), (circ(32, 32, 10.5), 'k')] + inner
def tiny(d, mode='f'): return (d, mode)
CONF = [
 ('clash', 'Armed clash (190 conventional force)', [(BURST, 'f')], 'CAMEO 190', 'clash'),
 ('smallarms', 'Small arms (193)', badge_in([(R(25, 31, 14, 2.4), 'f'), (R(36, 29, 3, 7), 'f')]), 'CAMEO 193', 'clash'),
 ('artillery', 'Artillery and tanks (194)', badge_in([(poly([(32, 23), (35, 28), (35, 40), (29, 40), (29, 28)]), 'f')]), 'CAMEO 194', 'clash'),
 ('aerial', 'Aerial weapons: air strike, drone (195)', badge_in([(poly([(32, 23), (33.4, 29), (40, 32), (40, 34), (33.4, 33), (33, 38), (35, 40), (29, 40), (31, 38), (30.6, 33), (24, 34), (24, 32), (30.6, 29)]), 'f')]), 'CAMEO 195', 'clash'),
 ('blockade', 'Blockade (191)', badge_in([(R(24, 30, 16, 4), 'f'), (R(25, 34, 2, 5), 'f'), (R(37, 34, 2, 5), 'f')]), 'CAMEO 191', 'clash'),
 ('occupy', 'Occupation of territory (192)', badge_in([(R(27, 23, 2, 17), 'f'), (poly([(29, 23), (39, 26), (29, 30)]), 'f')]), 'CAMEO 192', 'clash'),
 ('ceasefire', 'Ceasefire violation (196)', badge_in([('M24 32h6M34 32h6', 's')]), 'CAMEO 196', 'clash'),
 ('attack', 'Attack, assault (18x)', I.S['attack']['g'], 'CAMEO 180, 182', 'clash'),
 ('bombing', 'Bombing (183)', [(star(12, 30, 18), 'f'), (circ(32, 32, 9), 'k'), (circ(32, 32, 4), 'f')], 'CAMEO 183', 'clash'),
 ('abduct', 'Abduction, hostage taking (181)', [('M32 6L59 55H5Z', 'f'), (circ(32, 30, 5), 'k'), ('M24 50c0-8 4-12 8-12s8 4 8 12Z', 'k')], 'CAMEO 181', 'clash'),
 ('assassin', 'Assassination, attempt (185, 186)', [('M32 6L59 55H5Z', 'f'), (circ(32, 38, 9), 'k'), (circ(32, 38, 3), 'f')], 'CAMEO 185, 186', 'clash'),
 ('mass', 'Mass violence (20x)', I.S['mass']['g'], 'CAMEO 200-204', 'clash'),
 ('protest', 'Protest, demonstration (140, 141)', [(circ(32, 32, 24), 's')], 'CAMEO 140, 141', 'protest'),
 ('strike', 'Strike, boycott, hunger strike (142, 143)', [(circ(32, 32, 24), 's'), (R(25, 23, 5, 18), 'f'), (R(34, 23, 5, 18), 'f')], 'CAMEO 142, 143', 'protest'),
 ('obstruct', 'Obstruction, road blockade (144)', [(circ(32, 32, 24), 's'), (R(20, 29, 24, 6), 'f')], 'CAMEO 144', 'protest'),
 ('riot', 'Riot, violent protest (145)', [(circ(32, 32, 24), 's'), (star(6, 13, 6), 'f')], 'CAMEO 145', 'clash'),
 ('occupied', 'Occupied area (DeepState)', I.S['occupied']['g'], 'DeepState', 'clash'),
 ('contested', 'Status unclear (DeepState)', [('M6 10H58V54H6Z', 'd'), ('M6 30L26 10M6 50L46 10M22 54L58 18M42 54L58 38', 'd')], 'DeepState', 'net'),
 ('frontchange', 'Front-line change', I.S['frontchange']['g'], 'DeepState', 'front'),
 ('unit', 'Unit position (DeepState)', I.S['unit']['g'], 'DeepState', 'clash'),
 ('direction', 'Direction of attack (DeepState)', I.S['direction']['g'], 'DeepState', 'clash'),
 ('hotspot', 'Hotspot (3+ kinds of signal)', I.S['hotspot']['g'], 'our rule', 'hot'),
 ('news', 'Place in the news', I.S['news']['g'], 'GDELT', 'news'),
 ('breaking', 'Breaking: sudden jump', I.S['breaking']['g'], 'GDELT', 'news'),
 ('leader', 'Leader placed by the news', I.S['leader']['g'], 'GDELT + Wikidata', 'leader'),
 ('head', 'Head of state, at the country', I.S['head']['g'], 'Wikidata', 'leader'),
]
# ---------- Earth ----------
def quake(r_): return [(circ(32, 32, 5), 'f'), (circ(32, 32, r_*0.55), 's'), (circ(32, 32, r_), 'd')]
EARTH = [
 ('quake_s', 'Earthquake M4.5-5.4', quake(18), 'USGS', 'quake'),
 ('quake_m', 'Earthquake M5.5-6.4', quake(23), 'USGS', 'quake'),
 ('quake_l', 'Earthquake M6.5+', quake(28) + [(circ(32, 32, 10), 's')], 'USGS', 'quake'),
 ('quake_test', 'Quake near a nuclear test site', I.S['quake_test']['g'], 'USGS + our site list', 'quake'),
 ('explosion', 'Explosion / quarry blast (USGS type)', [(star(10, 24, 12), 's'), (circ(32, 32, 5), 'f')], 'USGS event type', 'quake'),
 ('cyclone', 'Tropical cyclone', I.S['cyclone']['g'], 'GDACS', 'disaster'),
 ('storm', 'Severe storm', [('M12 30a12 12 0 0 1 22-6a9 9 0 0 1 18 6Z', 'f'), ('M30 34L24 46h7l-4 12', 's')], 'NASA EONET', 'disaster'),
 ('flood', 'Flood', I.S['flood']['g'], 'GDACS', 'disaster'),
 ('volcano', 'Volcano', I.S['volcano']['g'], 'GDACS, EONET', 'disaster'),
 ('drought', 'Drought', [(circ(32, 22, 9), 'f'), ('M8 46L20 40 28 48 38 38 48 46 58 40', 's'), ('M32 6V2M46 10l3-3M18 10l-3-3', 's')], 'GDACS', 'disaster'),
 ('wildfire', 'Wildfire alert', I.S['wildfire']['g'], 'GDACS, EONET', 'disaster'),
 ('landslide', 'Landslide', [(poly([(6, 56), (30, 14), (58, 56)]), 'a'), (circ(40, 46, 5), 'f'), (circ(50, 52, 3.5), 'f')], 'NASA EONET', 'disaster'),
 ('ice', 'Sea and lake ice', [('M32 6V58M9 19L55 45M55 19L9 45', 's'), (circ(32, 32, 6), 'k')], 'NASA EONET', 'disaster'),
 ('dust', 'Dust and haze', [('M8 22h36M14 32h42M8 42h30', 's'), (circ(50, 22, 3), 'f'), (circ(46, 42, 3), 'f')], 'NASA EONET', 'disaster'),
 ('fire', 'Hot spot (NASA MODIS)', I.S['fire']['g'], 'NASA FIRMS', 'fire'),
 ('lightning', 'Lightning', I.S['lightning']['g'], 'EUMETSAT', 'bolt'),
]
# ---------- networks, warnings ----------
def outage(code):   # signal bars + a cause pictogram in the corner
    return [(R(8, 44, 7, 12), 'f'), (R(19, 36, 7, 20), 'f'), (R(30, 28, 7, 28), 'a'), (R(41, 20, 7, 36), 'a'), ('M6 6L50 54', 's')] + code
NET = [
 ('outage', 'Internet outage (IODA)', I.S['outage']['g'], 'IODA', 'net'),
 ('out_power', 'Outage: power cut', outage([(poly([(54, 4), (46, 18), (52, 18), (48, 28), (60, 12), (54, 12)]), 'x')]), 'Cloudflare cause', 'net'),
 ('out_cable', 'Outage: cable cut', outage([('M44 14c4-6 10 2 16-4', 'x'), ('M50 6l6 12', 'x')]), 'Cloudflare cause', 'net'),
 ('out_gov', 'Outage: government ordered', outage([(R(46, 8, 14, 3), 'x'), (R(47, 12, 3, 10), 'x'), (R(56, 12, 3, 10), 'x')]), 'Cloudflare cause', 'net'),
 ('out_mil', 'Outage: military action', outage([(star(6, 9, 4, 53, 13), 'x')]), 'Cloudflare cause', 'net'),
 ('out_cyber', 'Outage: cyberattack', outage([(R(46, 6, 14, 14), 'x')]), 'Cloudflare cause', 'net'),
 ('out_nat', 'Outage: natural disaster, weather', outage([(circ(53, 13, 7), 'x')]), 'Cloudflare cause', 'net'),
 ('cfnote', 'Cloudflare outage note', I.S['cfnote']['g'], 'Cloudflare Radar', 'ice'),
 ('hijack', 'Possible route hijack', I.S['hijack']['g'], 'Cloudflare Radar', 'hijack'),
 ('leak', 'Route leak', I.S['leak']['g'], 'Cloudflare Radar', 'leak'),
 ('cable', 'Undersea cable', I.S['cable']['g'], 'TeleGeography', 'cable'),
 ('cable_fault', 'Cable named in fault news', I.S['cable_fault']['g'], 'SubTel Forum, news', 'clash'),
 ('cable_fixed', 'Cable reported repaired', I.S['cable_fixed']['g'], 'SubTel Forum, news', 'ok'),
 ('nw_rocket', 'Navy warning: rocket, space debris', [('M32 4L60 54H4Z', 's'), ('M32 20c3 4 4 9 4 15v6h-8v-6c0-6 1-11 4-15Z', 'f')], 'NGA, UKHO', 'warn'),
 ('nw_missile', 'Navy warning: missile firing', [('M32 4L60 54H4Z', 's'), ('M24 44L40 24', 's'), (poly([(40, 24), (34, 26), (38, 30)]), 'f')], 'NGA, UKHO', 'warn'),
 ('nw_weapons', 'Navy warning: weapons, explosives', [('M32 4L60 54H4Z', 's'), (star(8, 10, 5, 32, 38), 'f')], 'NGA, UKHO', 'warn'),
 ('nw_exercise', 'Navy warning: military exercise', [('M32 4L60 54H4Z', 's'), ('M22 44l10-14 10 14', 's')], 'NGA, UKHO', 'warn'),
 ('nw_security', 'Navy warning: security threat', [('M32 4L60 54H4Z', 's'), (R(30, 24, 4, 14), 'f'), (R(30, 41, 4, 4), 'f')], 'NGA, UKHO', 'warn'),
 ('nw_gnss', 'Navy warning: GPS interference', [('M32 4L60 54H4Z', 's'), (circ(32, 38, 4), 'f'), ('M22 36a10 10 0 0 1 20 0', 's')], 'NGA, UKHO', 'warn'),
 ('as_avoid', 'Airspace: do not operate', [('M18 6H46L60 32 46 58H18L4 32Z', 's'), ('M18 18L46 46M46 18L18 46', 's')], 'EASA, FAA', 'clash'),
 ('as_notice', 'Airspace: caution notice', [('M18 6H46L60 32 46 58H18L4 32Z', 'd'), (R(30, 18, 4, 18), 'f'), (R(30, 40, 4, 4), 'f')], 'EASA, FAA', 'warn'),
 ('tfr', 'US flight restriction (TFR)', I.S['tfr']['g'], 'FAA', 'warn'),
 ('tfr_space', 'TFR: space operations', [(circ(32, 32, 26), 'd'), ('M32 14c4 6 6 12 6 20v8H26v-8c0-8 2-14 6-20Z', 'f')], 'FAA', 'warn'),
 ('gps', 'GPS interference area', [('M32 6L54 19V45L32 58 10 45V19Z', 'a'), (circ(32, 34, 4), 'f'), ('M22 30a10 10 0 0 1 20 0', 's')], 'GPSJAM, own count', 'warn'),
]
# ---------- sites ----------
SQ = 'M8 8H56V56H8Z'
SITES = [
 ('airbase', 'Air base', [(SQ, 'f'), (poly([(32, 15), (34, 27), (46, 33), (46, 36), (34, 34), (33.5, 42), (37, 45), (37, 47), (32, 46), (27, 47), (27, 45), (30.5, 42), (30, 34), (18, 36), (18, 33), (30, 27)]), 'k')], 'Wikidata, OSM, MIRTA', 'site'),
 ('navalbase', 'Naval base', [(SQ, 'f'), ('M32 16V46M24 22h16M18 36c2 8 8 12 14 12s12-4 14-12', 'k')], 'Wikidata, OSM', 'site'),
 ('armybase', 'Army base, barracks', [(SQ, 'f'), (star(5, 15, 6), 'k')], 'Wikidata, OSM', 'site'),
 ('missile_site', 'Missile site', [(SQ, 'f'), ('M32 14c3 4 4 10 4 16v14h-8V30c0-6 1-12 4-16Z', 'k')], 'Wikidata, OSM', 'clash'),
 ('sigint_site', 'Signals intelligence site', [(SQ, 'f'), (circ(32, 26, 9), 'k'), (R(30.5, 34, 3, 12), 'k')], 'Wikidata', 'clash'),
 ('radar', 'Military radar', I.S['radar']['g'], 'Wikidata, OSM', 'ice'),
 ('launchsite', 'Launch site, spaceport', [(SQ, 'f'), (poly([(32, 14), (36, 22), (36, 40), (40, 46), (24, 46), (28, 40), (28, 22)]), 'k')], 'Wikidata, OSM', 'launch'),
 ('ammo', 'Ammunition depot', [(SQ, 'f'), (circ(32, 34, 9), 'k'), (R(30.5, 16, 3, 9), 'k')], 'OSM (named only)', 'site'),
 ('range', 'Firing range, training area', [('M6 10H58V54H6Z', 'a'), (circ(32, 32, 10), 's'), (circ(32, 32, 3), 'f')], 'OSM', 'site'),
 ('milarea', 'Military area (OSM, unnamed)', I.S['milarea']['g'], 'OSM', 'site'),
 ('nuke', 'Nuclear power plant, operating', I.S['nuke']['g'], 'GEM', 'nuke'),
 ('nuke_build', 'Nuclear plant, under construction', [('M18 58c4-12 4-30 0-46h28c-4 16-4 34 0 46Z', 'd')], 'GEM', 'nuke'),
 ('nuke_off', 'Nuclear plant, shut down', [('M18 58c4-12 4-30 0-46h28c-4 16-4 34 0 46Z', 'a')], 'GEM', 'net'),
 ('reactor', 'Research reactor', [(circ(32, 32, 26), 's'), (trefoil(32, 32, 5, 19), 'f')], 'Wikidata', 'nuke'),
 ('fuelcycle', 'Enrichment / fuel-cycle site', [(SQ, 'f'), (trefoil(32, 32, 5, 19), 'k')], 'Wikidata', 'nuke'),
 ('waste', 'Nuclear waste site', [(poly([(32, 6), (58, 52), (6, 52)]), 'f'), (trefoil(32, 36, 4, 13), 'k')], 'Wikidata', 'nuke'),
 ('uranium', 'Uranium mine', [(poly([(6, 54), (24, 22), (32, 34), (42, 18), (58, 54)]), 'f'), (trefoil(36, 44, 3, 9), 'k')], 'Wikidata', 'nuke'),
 ('testsite', 'Nuclear test site', I.S['testsite']['g'], 'our list of 28', 'clash'),
 ('camera', 'Public traffic / weather camera', I.S['camera']['g'], 'TfL, NYC, Caltrans, ...', 'cam'),
 ('camlive', 'Webcam with live stream', I.S['camlive']['g'], 'Windy', 'cam'),
 ('sdr', 'Shortwave receiver', I.S['sdr']['g'], 'KiwiSDR', 'sdr'),
]
GROUPS = [('Aircraft', AIR), ('Ships', SHIPS), ('Space', SATS), ('Conflict and news', CONF), ('Earth', EARTH), ('Networks and warnings', NET), ('Sites', SITES)]
LIB = {}
for gname, rows in GROUPS:
    for r_ in rows:
        if gname == 'Aircraft': i, n, g, codes, col, small = r_
        else: i, n, g, codes, col = r_; small = None
        LIB[i] = dict(name=n, g=g, codes=codes, colkey=col, small=small, group=gname, rot=gname in ('Aircraft', 'Ships') and i not in ('balloon', 'ground', 'airship'))
# palettes: dark (God's eye A), fewer colours (B), muted domain hues (C); each with a light-mode twin
PAL = {
 'A': dict(dark=I.P, light=dict(civil='#2a3440', mil='#0b1118', vip='#a37b00', doom='#d6203f', tanker='#138a5e', isr='#c2334f', ship='#0089a8', leo='#138a5e', meo='#a37b00', geo='#0071c2', heo='#c23d8c',
           spy='#d6203f', launch='#6a4bd6', clash='#d6203f', protest='#d6203f', front='#1c2430', warn='#a37b00', quake='#1c2430', disaster='#a43fb8', fire='#b88a00', bolt='#1c2430', net='#5c6670', hijack='#d6203f',
           leak='#0071c2', cable='#6b7782', ok='#138a5e', site='#5c6670', nuke='#6b8a00', cam='#0071c2', sdr='#6a5fa8', leader='#1c2430', news='#3a4652', hot='#d6203f', ice='#0071c2')),
}
B_D = {k: '#e6eaed' for k in I.P}; B_D.update(clash='#ff3b5c', hijack='#ff3b5c', doom='#ff3b5c', spy='#ff3b5c', hot='#ff3b5c', isr='#ff8fa3', protest='#ffc2cd', warn='#ffe066', fire='#ffe066', ice='#8fdcff', leak='#8fdcff', ok='#c9d1d6', net='#9aa7b2', cable='#9aa7b2', site='#c9d1d6', mil='#ffffff')
B_L = {k: '#1c2430' for k in I.P}; B_L.update(clash='#d6203f', hijack='#d6203f', doom='#d6203f', spy='#d6203f', hot='#d6203f', isr='#c2334f', protest='#d6203f', warn='#a37b00', fire='#a37b00', ice='#0071c2', leak='#0071c2', net='#5c6670', cable='#6b7782', site='#5c6670', ok='#5c6670')
PAL['B'] = dict(dark=B_D, light=B_L)
C_D = dict(I.P); C_D.update(civil='#cfd8e3', mil='#f0f3f6', ship='#7fd0e0', leo='#9ad9b8', meo='#e6d68a', geo='#9cc7e8', heo='#e3a8cf', launch='#b8aee6', clash='#f06a7e', protest='#f3b8c3', disaster='#d9a6e6', warn='#e8d27a', tanker='#9ad9b8', vip='#e6d07a', isr='#f0a0b0', nuke='#c9de84', cam='#9cc7e8', sdr='#c3bde0', fire='#efe0a0', hot='#f06a7e', hijack='#f06a7e', doom='#f06a7e', spy='#f06a7e', ice='#9cd8f5', ok='#9ad9b8')
C_L = dict(PAL['A']['light']); C_L.update(clash='#b8394b', ship='#2a7f91', launch='#5b4fa3', disaster='#8a4d99', warn='#8f7420', tanker='#2f7f5c', leo='#2f7f5c', geo='#2f6f9e', heo='#9e4a7f', nuke='#5f7a1f', vip='#8f7420', isr='#a8455a')
PAL['C'] = dict(dark=C_D, light=C_L)
PALN = dict(A='A  Current: colour per domain', B='B  Fewer colours: white, rose, yellow', C='C  Muted: same hues, softer')
def colour(i, pal='A', mode='dark'):
    return PAL[pal][mode][LIB[i]['colkey']]
SMALLMAP = {'jet': 'airliner', 'heavy': 'heavy', 'prop': 'prop', 'heli': 'heli', 'fighter': 'fighter', 'glider': 'glider', 'balloon': 'balloon', 'drone': 'drone', 'ground': 'ground'}
def glyph(i, px):
    """at 16 px and below an aircraft falls back to its simple class shape; other symbols keep their own"""
    s = LIB[i]
    if px <= 16 and s['small']: return I.S[SMALLMAP[s['small']]]['g']
    return s['g']
def draw(i, fam, x, y, px, rot=0, pal='A', mode='dark', state=None, colkey=None):
    s = LIB[i]; col = PAL[pal][mode][colkey] if colkey else colour(i, pal, mode); ink = I.INK if mode == 'dark' else '#ffffff'
    if state == 'stale': col = '#8a949c'
    acc = None
    if any(m == 'x' for _, m in s['g']):
        acc = {'sanctioned': 'clash', 'breaking': 'clash', 'quake_test': 'nuke', 'head': 'vip', 'camlive': 'ok'}.get(i)
        acc = PAL[pal][mode][acc] if acc else PAL[pal][mode]['warn']
    sym = dict(g=glyph(i, px), acc=acc, pt=('dot', ''), rot=s['rot'], col=col)
    body = I.els(sym, fam, col, ink)
    if fam == 'line' and mode == 'light': body = body.replace(' filter="url(#glow)"', '').replace('fill-opacity="0.14"', 'fill-opacity="0.22"')
    k = px/64; r_ = rot if s['rot'] else 0
    op = ' opacity="0.5"' if state == 'faint' else ''
    g = f'<g transform="translate({x - px/2:.1f} {y - px/2:.1f}) scale({k:.4f})"{op}>' + (f'<g transform="rotate({r_:.0f} 32 32)">{body}</g>' if r_ else body) + '</g>'
    sel = PAL[pal][mode]['ice']
    if state == 'sel':
        R_ = px*0.72
        g += (f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{R_:.1f}" fill="none" stroke="{sel}" stroke-width="2"></circle>'
              f'<path d="M{x-R_-7:.1f} {y:.1f}h6M{x+R_+1:.1f} {y:.1f}h6M{x:.1f} {y-R_-7:.1f}v6M{x:.1f} {y+R_+1:.1f}v6" stroke="{sel}" stroke-width="2"></path>')
    if state == 'hover': g += f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{px*0.62:.1f}" fill="none" stroke="{"#ffffff" if mode == "dark" else "#1c2430"}" stroke-opacity="0.7" stroke-width="1.4"></circle>'
    return g
DEFS2 = I.DEFS.replace('</defs>', '<filter id="glowl" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="1.4" result="b"></feGaussianBlur><feMerge><feMergeNode in="b"></feMergeNode><feMergeNode in="SourceGraphic"></feMergeNode></feMerge></filter></defs>')
def typecode_class(t, mil=False):
    t = (t or '').upper()
    for i, s in LIB.items():
        if s['group'] == 'Aircraft' and t and t in s['codes'].split(): return i
    return None
