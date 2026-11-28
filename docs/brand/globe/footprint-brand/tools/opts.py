"""Footprint palettes taken straight from real apps' and agencies' published colours."""
def lum(h):
    h = h.lstrip("#"); c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    c = [x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c]
    return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]
def cr(a, b):
    la, lb = sorted((lum(a), lum(b)), reverse=True); return (la + 0.05) / (lb + 0.05)

OPTS = [
 dict(key="apple-blue", name="Apple Blue and Cyan", brand="Apple Human Interface Guidelines, system colours",
      mark=dict(plate="#0088FF", plate2="#00C0E8", globe="#FFFFFF", fp="#6155F5", pupil="#000000")),
 dict(key="apple-green", name="Apple Green", brand="Apple Human Interface Guidelines, system colours",
      mark=dict(plate="#34C759", globe="#FFFFFF", fp="#0088FF", pupil="#000000")),
 dict(key="telegram", name="Telegram", brand="Telegram's logo file (telegram.org/img/t_logo.svg)",
      mark=dict(plate="#2AABEE", plate2="#229ED9", globe="#FFFFFF", fp="#229ED9", pupil="#FFFFFF")),
 dict(key="signal", name="Signal", brand="Signal Desktop source, stylesheets/_variables.scss",
      mark=dict(plate="#3B45FD", globe="#FFFFFF", fp="#2C6BED", pupil="#000000")),
 dict(key="nasa", name="NASA", brand="NASA brand guidelines, insignia colours",
      mark=dict(plate="#0032A0", globe="#FFFFFF", fp="#E4002B", pupil="#0032A0")),
 dict(key="google", name="Google", brand="Google's logo file (gstatic.com)",
      mark=dict(plate="#4285F4", globe="#FFFFFF", fp="#34A853", pupil="#000000")),
 dict(key="nasa-b", name="NASA (white pupil)", brand="NASA brand guidelines, insignia colours",
      mark=dict(plate="#0032A0", globe="#FFFFFF", fp="#E4002B", pupil="#FFFFFF")),
 dict(key="anduril", name="Anduril", brand="anduril.com site colours",
      mark=dict(plate="#DFF140", globe="#010101", fp="#FFFFFF", pupil="#010101")),
 dict(key="discord", name="Discord", brand="discord.com/branding",
      mark=dict(plate="#5865F2", globe="#FFFFFF", fp="#23272A", pupil="#5865F2")),
 dict(key="nato", name="NATO", brand="NATO Visual Identity Guidelines 2016",
      mark=dict(plate="#004990", globe="#FFFFFF", fp="#118ACB", pupil="#000000")),
 dict(key="nasa-meatball", name="NASA, meatball order", brand="NASA brand guidelines, insignia colours",
      mark=dict(plate="#FFFFFF", globe="#0032A0", fp="#FFFFFF", pupil="#E4002B")),
 dict(key="signal-lit", name="Signal, lit footprint", brand="Signal Desktop source, stylesheets/_variables.scss",
      mark=dict(plate="#3B45FD", globe="#1851B4", fp="#FFFFFF", pupil="#3B45FD")),
 dict(key="apple-lit", name="Apple Indigo and Blue, lit footprint", brand="Apple Human Interface Guidelines, system colours",
      mark=dict(plate="#6155F5", globe="#0088FF", fp="#FFFFFF", pupil="#6155F5")),
 dict(key="nato-lit", name="NATO, lit footprint", brand="NATO Visual Identity Guidelines 2016",
      mark=dict(plate="#118ACB", globe="#004990", fp="#FFFFFF", pupil="#118ACB")),
 dict(key="telegram-lit", name="Telegram, lit footprint", brand="Telegram's logo file",
      mark=dict(plate="#FFFFFF", globe="#2AABEE", plate2=None, fp="#FFFFFF", pupil="#229ED9")),
]
if __name__ == "__main__":
    for o in OPTS:
        m = o["mark"]
        print(f'{o["key"]:12} plate/globe {cr(m["plate"], m["globe"]):4.1f}  globe/fp {cr(m["globe"], m["fp"]):4.1f}  fp/pupil {cr(m["fp"], m["pupil"]):4.1f}  plate/darkbar {cr(m["plate"], "#202020"):4.1f}  plate/lightbar {cr(m["plate"], "#F3F3F3"):4.1f}')
