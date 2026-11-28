"""Download static TTFs from the Google Fonts CSS API (all families are SIL OFL)."""
import re, sys, pathlib, urllib.request, json
OUT = pathlib.Path(sys.argv[1])
OUT.mkdir(parents=True, exist_ok=True)
FAMILIES = {
  # key: css2 family query
  "archivo-x600": "Archivo:wdth,wght@125,600",
  "spacegrotesk-600": "Space+Grotesk:wght@600",
  "barlowsc-600": "Barlow+Semi+Condensed:wght@600",
  "sora-600": "Sora:wght@600",
  "publicsans-700": "Public+Sans:wght@700",
  "plexmono-400": "IBM+Plex+Mono:wght@400",
  "plexmono-500": "IBM+Plex+Mono:wght@500",
  "plexmono-600": "IBM+Plex+Mono:wght@600",
  "michroma-400": "Michroma",
  "sairasc-600": "Saira+Semi+Condensed:wght@600",
  "librefranklin-700": "Libre+Franklin:wght@700",
  "fraunces-600": "Fraunces:opsz,wght@72,600",
  "bigshoulders-800": "Big+Shoulders+Display:wght@800",
  "inter-400": "Inter:wght@400",
  "inter-500": "Inter:wght@500",
  "inter-600": "Inter:wght@600",
}
meta = {}
for key, q in FAMILIES.items():
    url = f"https://fonts.googleapis.com/css2?family={q}&display=swap"
    css = urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"}), timeout=30).read().decode()
    m = re.search(r"font-family: '([^']+)'.*?url\((https://fonts.gstatic.com/[^)]+\.ttf)\)", css, re.S)
    fam, src = m.group(1), m.group(2)
    data = urllib.request.urlopen(src, timeout=60).read()
    (OUT / f"{key}.ttf").write_bytes(data)
    meta[key] = {"family": fam, "query": q, "src": src, "bytes": len(data)}
    print(key, fam, len(data))
(OUT / "fonts.json").write_text(json.dumps(meta, indent=1))
