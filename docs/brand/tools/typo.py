"""Outline text with HarfBuzz shaping (kerning) + fontTools pens; subset fonts to WOFF2."""
import io, base64, pathlib, functools
import uharfbuzz as hb
from fontTools.ttLib import TTFont
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.pens.boundsPen import BoundsPen
from fontTools import subset

FONTS = pathlib.Path(__file__).resolve().parent.parent / "fonts"

@functools.lru_cache(None)
def _load(key):
    path = FONTS / f"{key}.ttf"
    blob = hb.Blob.from_file_path(str(path))
    face = hb.Face(blob)
    font = hb.Font(face)
    tt = TTFont(str(path))
    return font, tt

def text_path(key, text, size, tracking=0.0):
    """Return (d, width, cap_height_px). Baseline at y=0, y grows downward (SVG)."""
    font, tt = _load(key)
    upem = tt["head"].unitsPerEm
    buf = hb.Buffer(); buf.add_str(text); buf.guess_segment_properties()
    hb.shape(font, buf, {"kern": True, "liga": True})
    gs = tt.getGlyphSet()
    order = tt.getGlyphOrder()
    scale = size / upem
    track = tracking * upem
    pen = SVGPathPen(gs)
    x = 0.0
    n = len(buf.glyph_infos)
    for i, (info, pos) in enumerate(zip(buf.glyph_infos, buf.glyph_positions)):
        name = order[info.codepoint]
        tp = TransformPen(pen, (scale, 0, 0, -scale, (x + pos.x_offset) * scale, -pos.y_offset * scale))
        gs[name].draw(tp)
        x += pos.x_advance + (track if i < n - 1 else 0)
    os2 = tt["OS/2"]
    cap = getattr(os2, "sCapHeight", 0) or int(upem * 0.7)
    # tight bounds
    bp = BoundsPen(gs)
    return pen.getCommands(), x * scale, cap * scale

def ink_bounds(key, text, size, tracking=0.0):
    font, tt = _load(key)
    upem = tt["head"].unitsPerEm
    buf = hb.Buffer(); buf.add_str(text); buf.guess_segment_properties()
    hb.shape(font, buf, {"kern": True})
    gs = tt.getGlyphSet(); order = tt.getGlyphOrder()
    scale = size / upem; track = tracking * upem
    bp = BoundsPen(gs)
    x = 0.0; n = len(buf.glyph_infos)
    for i, (info, pos) in enumerate(zip(buf.glyph_infos, buf.glyph_positions)):
        tp = TransformPen(bp, (scale, 0, 0, -scale, x * scale, 0))
        gs[order[info.codepoint]].draw(tp)
        x += pos.x_advance + (track if i < n - 1 else 0)
    return bp.bounds  # (xmin, ymin, xmax, ymax) in svg coords (y down)

TEXT_CHARS = "".join(chr(c) for c in range(32, 127)) + "·–—°’‘“”×→←↑↓…•é"

def woff2_b64(key):
    path = FONTS / f"{key}.ttf"
    opts = subset.Options(); opts.flavor = "woff2"; opts.layout_features = ["kern", "liga", "calt", "tnum", "case"]
    opts.name_IDs = ["*"]; opts.notdef_outline = True
    f = TTFont(str(path))
    s = subset.Subsetter(opts); s.populate(text=TEXT_CHARS); s.subset(f)
    out = io.BytesIO(); f.flavor = "woff2"; f.save(out)
    return base64.b64encode(out.getvalue()).decode()
