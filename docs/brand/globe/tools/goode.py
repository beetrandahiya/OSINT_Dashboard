"""Goode homolosine, interrupted as Goode drew it in 1923 (land kept whole).
North: lobes -180..-40 (central meridian -100) and -40..180 (30).
South: lobes -180..-100 (-160), -100..-20 (-60), -20..80 (20), 80..180 (140).
Units: radians of a unit sphere (x roughly -pi..pi, y up)."""
import math

PHI_JOIN = 0.71098  # 40 deg 44' 11.8", where sinusoidal and Mollweide meet
Y_OFF = 0.0528035274542

NORTH = [(-180, -40, -100), (-40, 180, 30)]
SOUTH = [(-180, -100, -160), (-100, -20, -60), (-20, 80, 20), (80, 180, 140)]


def _moll_theta(phi):
    t = phi
    for _ in range(60):
        f = 2 * t + math.sin(2 * t) - math.pi * math.sin(phi)
        d = 2 + 2 * math.cos(2 * t)
        if abs(d) < 1e-12:
            break
        t -= f / d
    return t


def project(lat, lon, lc):
    """Project (lat, lon) degrees within a lobe of central meridian lc. Returns (x, y), y up."""
    phi, dl = math.radians(lat), math.radians(lon - lc)
    if abs(phi) <= PHI_JOIN:
        return math.radians(lc) + dl * math.cos(phi), phi
    t = _moll_theta(phi)
    x = (2 * math.sqrt(2) / math.pi) * dl * math.cos(t)
    y = math.sqrt(2) * math.sin(t) - math.copysign(Y_OFF, phi)
    return math.radians(lc) + x, y


def lobe(a, b, lc, north, n=90):
    """Outline of one lobe: from the equator up/down its west edge to the pole and back along its east edge."""
    sgn = 1 if north else -1
    west = [project(sgn * 90 * i / n, a, lc) for i in range(n + 1)]
    east = [project(sgn * 90 * (n - i) / n, b, lc) for i in range(n + 1)]
    return west + east


def outline():
    """The whole interrupted outline as one closed ring (clockwise from the west end of the equator)."""
    ring = []
    for a, b, lc in NORTH:                       # north, west to east, above the equator
        ring += lobe(a, b, lc, True)
    for a, b, lc in reversed(SOUTH):             # south, east to west, below the equator
        pts = lobe(b, a, lc, False)
        ring += pts
    return ring


def southern():
    ring = []
    for a, b, lc in SOUTH:
        ring += lobe(a, b, lc, False)
    return ring
