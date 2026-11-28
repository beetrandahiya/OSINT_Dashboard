"""The ten World Watch identity directions: concept, palette (with sources), type, devices, notes."""
import math
import marks as M

SRC = {
    "bp": ("Palantir Blueprint colours (packages/colors/src/colors.ts)",
           "https://github.com/palantir/blueprint/blob/develop/packages/colors/src/colors.ts",
           "Read from the file on GitHub, 28 Nov 2026. Blueprint is Palantir's own open-source UI system (Apache-2.0)."),
    "esa": ("ESA: Deep Space logo colour (brand.esa.int) and esa.int stylesheet",
            "https://www.esa.int/assets/css/styles.css",
            "#003247 is ESA's 'Deep Space' logo colour per brand.esa.int (page refused this sandbox; value from a search "
            "excerpt of that page) and is the most used colour in esa.int's own stylesheet (202 uses). "
            "The other values were read from that stylesheet."),
    "esa2": ("ESA brand centre (logo colour codes)", "https://brand.esa.int/", ""),
    "brg": ("Bundesregierung styleguide: Petrol", "https://styleguide.bundesregierung.gov.de/sg-de/basiselemente/farben/petrol-2051434",
            "Read 28 Nov 2026: Petrol #007194, Pantone 315, tints 80/60/40/20 %. Black is the styleguide's text colour."),
    "un": ("UN brand identity quick guide (2020)", "https://www.un.org/styleguide/pdf/UN_brand_identity_quick_guide_2020.pdf",
           "UN Blue: Pantone 2925, RGB 0/158/219, #009edb. The PDF answered 403 to this sandbox; the value was quoted "
           "from it by a web search result and matches brandcolorcode.com, which cites the same PDF."),
    "nga": ("NGA website stylesheet (nga.mil, built on the U.S. Web Design System)", "https://www.nga.mil/assets/css/main.css",
            "Read 28 Nov 2026; most-used colours. This is the agency's live website, not a published brand guide."),
    "and": ("Anduril website colour tokens", "https://www.anduril.com/",
            "Named colours in the site's CMS data (Black #010101, Mid Gray #8E9291, Green #505544) and its page-loading "
            "bar (#DFF140), read 28 Nov 2026. Not a published brand guide."),
    "nasa": ("NASA brand guidelines: Insignia colours", "https://www.nasa.gov/nasa-brand-center/brand-guidelines/",
             "Read from NASA's colour chart image on that page: NASA Blue #0032A0 (PMS 286), NASA Red #E4002B (PMS 185)."),
    "nato": ("NATO Visual Identity Guidelines (2016), colour table", "https://www.act.nato.int/wp-content/uploads/2023/06/NATO-VIGs-2016-en.pdf",
             "Read from the PDF: dark blue PMS 280 = HTML 004990, light blue PMS 2718 = HTML 118ACB, black."),
    "gov": ("GOV.UK Design System: colour", "https://design-system.service.gov.uk/styles/colour/",
            "Read 28 Nov 2026 (current palette). Used by UK government services, Companies House included."),
    "can": ("Canada.ca design system: colours", "https://design.canada.ca/styles/colours.html",
            "Read 28 Nov 2026: text #333, links #284162, main accent #26374A, error/required #d3080c, background white."),
}


def C(name, hexv, role, share, src):
    return dict(name=name, hex=hexv, role=role, share=share, src=src)


# Munich, 28 Nov 2026 (computed with the standard NOAA solar equations, see notes.md)
MUC_SUNRISE_UTC = 6 + 39 / 60
MUC_SUNSET_UTC = 15 + 25 / 60
SUBSOLAR_LON_1200Z = -3.0   # degrees, 28 Nov 2026 12:00 UTC (equation of time about +12 min)

DIRECTIONS = [
    dict(
        key="01-cocked-hat", name="Cocked Hat", src="bp", agency="Palantir (Blueprint)",
        line="Three bearings never meet in a single point; the small triangle between them is where the truth lies, "
             "and its size says how sure you can be.",
        story="Navigators call it the cocked hat: take three bearings and they form a small triangle instead of a "
              "point. World Watch works the same way: it shows where independent sources agree and is honest about "
              "the spread. The mark is that triangle, the lines running off the edge because bearings are endless.",
        wm=dict(font="archivo-x600", text="WORLD WATCH", track=0.14, family="Archivo Expanded", weight="SemiBold 600"),
        palette=[C("Black", "#111418", "plate, dark UI", 55, "bp"), C("Dark Gray 1", "#1C2127", "panels", 20, "bp"),
                 C("Light Gray 5", "#F6F7F9", "bearing lines, light UI", 18, "bp"), C("Gray 1", "#5F6B7C", "secondary text (light)", 2, "bp"),
                 C("Blue 4", "#4C90F0", "the triangle (dark)", 3, "bp"), C("Blue 3", "#2D72D2", "the triangle (light)", 2, "bp")],
        dark=dict(bg="#111418", panel="#1C2127", line="#2F343C", ink="#F6F7F9", sub="#ABB3BF", acc="#4C90F0"),
        light=dict(bg="#F6F7F9", panel="#FFFFFF", line="#D3D8DE", ink="#111418", sub="#5F6B7C", acc="#2D72D2"),
        devices=["Bearing rules: the three bearing angles crossing a panel corner, the triangle in the accent colour.",
                 "Fix badge: one source is a single line, two agreeing sources cross, three make a triangle whose size is the real spread."],
        good="The strongest idea in the set: it states the project's hard rule (sources, honesty about uncertainty) as geometry. "
             "Stark, monochrome plus one accent, closest to the Palantir/Anduril temperament without borrowing a shape.",
        weak="At 16 px it reads as an asterisk with a blue dot; the meaning needs the story once. The 'cocked hat' term is "
             "niche (navigation). Rotated 25 degrees so it does not read as the App Store's three-stroke 'A'.",
        small="Small variant: thicker lines (6.2 units) and a triangle about 1.6 times larger.",
    ),
    dict(
        key="02-terminator", name="Terminator", src="esa", agency="ESA (European Space Agency)",
        line="The shape night makes on the flat map of the world, computed for one real moment; the brand's main line is "
             "a fact, not a decoration.",
        story="On a flat world map the line between day and night is not straight: it bends into this flattened wave, "
              "and its shape changes with the season. The mark is the map window with night, twilight (sun 0 to 12 degrees "
              "below the horizon, as the app draws it) and day, computed for 28 Nov 2026 at 08:56 UTC.",
        wm=dict(font="spacegrotesk-600", text="World Watch", track=-0.01, family="Space Grotesk", weight="SemiBold 600"),
        palette=[C("Space (esa.int)", "#00121A", "plate, dark UI", 45, "esa"), C("Deep Space", "#003247", "night, panels", 25, "esa"),
                 C("ESA blue (esa.int)", "#009BDB", "twilight, accent", 8, "esa"), C("Paper (esa.int)", "#E8E8E4", "day, light UI", 18, "esa"),
                 C("Slate grey (esa.int)", "#9FB0BB", "secondary text", 4, "esa")],
        dark=dict(bg="#00121A", panel="#003247", line="#335E6F", ink="#E8E8E4", sub="#9FB0BB", acc="#009BDB"),
        light=dict(bg="#E8E8E4", panel="#FFFFFF", line="#9FB0BB", ink="#00121A", sub="#335E6F", acc="#003247"),
        devices=["Live terminator rule: the same computed curve as a thin band under the top bar and on the splash, always for the current time.",
                 "Twilight scale: night, twilight and day as a three-step bar for progress and legends."],
        good="The only direction whose central line can be real data every time it is drawn (the app already computes night). "
             "Calm, scientific, very 'world'.",
        weak="At 16 px it is a light hump in a dark tile and can read as a bell curve. The mark itself is frozen at one moment "
             "(stated); only the device in the app is live. ESA's Deep Space value comes from a search excerpt of brand.esa.int "
             "plus esa.int's stylesheet, not a PDF I could open.",
        small="Small variant: the map window fills more of the tile and the twilight band uses -18 degrees so it stays visible.",
    ),
    dict(
        key="03-quadkey", name="Quadkey 1-2-0-2-3", src="brg", agency="Bundesregierung (German Federal Government)",
        line="The address of Munich on the web map: split the world in four, take one, repeat; the mark is the zoom from "
             "the whole world to the place where the watching starts.",
        story="Web maps cut the world into square tiles; each zoom level splits a tile in four, and a place's tile address "
              "is a string of digits called a quadkey. Munich's begins 1-2-0-2-3. Each lighter square is one zoom level, "
              "converging on the city. It also stands for the Connections page: open one layer, find the next inside it.",
        wm=dict(font="barlowsc-600", text="WORLD WATCH", track=0.12, family="Barlow Semi Condensed", weight="SemiBold 600"),
        palette=[C("Petrol", "#007194", "plate, primary", 50, "brg"), C("Petrol 60 %", "#66AABF", "zoom level 1", 8, "brg"),
                 C("Petrol 40 %", "#99C6D4", "zoom level 2", 6, "brg"), C("Petrol 20 %", "#CCE3EA", "zoom level 3, light panels", 10, "brg"),
                 C("Petrol 80 %", "#338DA9", "grid lines", 3, "brg"), C("Black (text)", "#000000", "text, dark UI", 18, "brg"),
                 C("White", "#FFFFFF", "the target tile", 5, "brg")],
        dark=dict(bg="#000000", panel="#00303F", line="#007194", ink="#FFFFFF", sub="#99C6D4", acc="#66AABF"),
        light=dict(bg="#FFFFFF", panel="#CCE3EA", line="#99C6D4", ink="#000000", sub="#007194", acc="#007194"),
        devices=["Tile grid: the recursive four-way split as a hairline background that converges on the selected item.",
                 "Quadkey stamp: 'QK 120230 · 48.14 N 11.58 E' in mono, a real location reference on cards and covers."],
        good="Personal (it is literally Munich's tile address), true to how the map engine works, and the tints make a "
             "ready-made zoom/progress scale. Very German-federal in tone: orderly, quiet.",
        weak="Quiet at small size: a petrol tile with a lighter corner and one bright pixel. The meaning is invisible "
             "without the story. Dark panel #00303F is a mix of Petrol and black, not a published colour.",
        small="Small variant: three zoom levels instead of five, so the white target tile stays 2 px at 16 px.",
    ),
    dict(
        key="04-great-circle", name="Great Circle", src="un", agency="United Nations",
        line="The straight line on the flat map is not the shortest way; the curve is. The mark keeps both, because "
             "World Watch shows things as they are, not as they look.",
        story="Every flight, cable and connection between two places on Earth follows a great circle, which bows towards "
              "the pole on a flat map. The dashed chord is the obvious line, the solid arc is the true one. Origin hollow, "
              "destination solid: a connection with a direction, the core of the Connections page.",
        wm=dict(font="sora-600", text="World Watch", track=-0.01, family="Sora", weight="SemiBold 600"),
        palette=[C("UN Blue", "#009EDB", "plate, accent", 40, "un"), C("White", "#FFFFFF", "arc, light UI", 40, "un"),
                 C("Black", "#000000", "text, dark UI", 20, "un")],
        dark=dict(bg="#000000", panel="#0B1E26", line="#1D3C49", ink="#FFFFFF", sub="#A9C9D6", acc="#009EDB"),
        light=dict(bg="#FFFFFF", panel="#EEF7FB", line="#CFE7F2", ink="#000000", sub="#3D5560", acc="#0083B6"),
        devices=["Connection arcs: nodes joined by arcs that bow like great circles, the dashed chord shown faintly beneath.",
                 "Arc rule: the solid arc over the dashed chord as a divider and as a loading line that draws itself."],
        good="Friendly, clear, instantly about connections and travel; reads well at every size. A natural fit for the "
             "Connections page and the aircraft layer.",
        weak="The most 'app-like' of the ten (bright blue tile, route icon); less of the stark defence temperament. "
             "Route-with-endpoints icons exist (travel apps). Panels and secondary text in the app tables are tints of UN Blue "
             "mixed with black or white, not published colours. UN Blue was verified via a search quote of the UN PDF.",
        small="Small variant: no dashed chord (it turns to noise), heavier arc and nodes.",
    ),
    dict(
        key="05-plot", name="Plot", src="nga", agency="NGA (National Geospatial-Intelligence Agency)",
        line="On a radar scope the dots behind a target are where it really was; World Watch only ever draws positions "
             "someone actually reported.",
        story="Air traffic scopes leave a trail of history dots behind each target. They are not a line: the gaps are "
              "honest. The mark is a turning track: past reports in white, the newest one as the teal diamond pointing "
              "where it is heading. The project's rule 'never move anything ahead of its last report' made visible.",
        wm=dict(font="publicsans-700", text="WORLD WATCH", track=0.1, family="Public Sans", weight="Bold 700"),
        palette=[C("Navy (nga.mil)", "#0D2F4B", "plate, dark panels", 40, "nga"), C("Ink (nga.mil)", "#1B1B1B", "dark UI, text", 25, "nga"),
                 C("Mist (nga.mil)", "#F0F0F0", "history dots, light UI", 20, "nga"), C("Teal (nga.mil)", "#2FA3AA", "the newest report", 5, "nga"),
                 C("Blue (nga.mil)", "#154E7D", "lines, links", 7, "nga"), C("Grey (nga.mil)", "#DFE1E2", "light borders", 3, "nga")],
        dark=dict(bg="#1B1B1B", panel="#0D2F4B", line="#154E7D", ink="#F0F0F0", sub="#DFE1E2", acc="#2FA3AA"),
        light=dict(bg="#F0F0F0", panel="#FFFFFF", line="#DFE1E2", ink="#1B1B1B", sub="#154E7D", acc="#154E7D"),
        devices=["History-dot progress: loading as dots that appear one per feed that has answered; no bar that pretends to know the end.",
                 "Leader line and data block: the air-traffic label style for captions (callsign, type, level, speed)."],
        good="Instantly 'tracking': aircraft, ships, satellites. Public Sans is the U.S. government's open typeface, which "
             "suits NGA's palette. Honest-motion rule built in.",
        weak="Dots on a diagonal can read as a generic 'trend' or 'comet'. NGA colours come from its website stylesheet, "
             "not a brand guide.",
        small="Small variant: two history dots instead of four, larger diamond.",
    ),
    dict(
        key="06-w-trace", name="W Trace", src="and", agency="Anduril",
        line="The initial of World Watch drawn as a signal burst on a quiet baseline: the world's signals and the "
             "name are the same line.",
        story="Quakes, transponder pings and news spikes all arrive as a trace that is mostly flat with sudden bursts. "
              "Here the burst is the letter W. In the app the same trace is drawn from real counts (for example news "
              "per 15 minutes), so the brand's line is data whenever it appears.",
        wm=dict(font="plexmono-600", text="WORLD WATCH", track=0.06, family="IBM Plex Mono", weight="SemiBold 600"),
        palette=[C("Black", "#010101", "plate, dark UI", 70, "and"), C("Mid Gray", "#8E9291", "baseline, secondary", 12, "and"),
                 C("Signal lime (loading bar)", "#DFF140", "the burst, live state", 6, "and"), C("Green (olive)", "#505544", "lines, light accent", 7, "and"),
                 C("White", "#FFFFFF", "text", 5, "and")],
        dark=dict(bg="#010101", panel="#0B0C0B", line="#26281F", ink="#FFFFFF", sub="#8E9291", acc="#DFF140"),
        light=dict(bg="#FFFFFF", panel="#F4F4F2", line="#D9DAD6", ink="#010101", sub="#505544", acc="#505544"),
        devices=["Activity trace: a baseline that bursts where counts jump; lime only where something is happening.",
                 "Scope grid: a fine 10-division graticule as the background of panels and the splash."],
        good="The most legible mark at 16 px in the set, and the most 'defence tech' (oscilloscope lime on black). "
             "Monogram, so it also works as a letter W in tight spaces.",
        weak="Close to the generic 'audio waveform / heartbeat' icon family; the W must stay crisp or it becomes noise. "
             "Lime is unreadable as text on white, so light mode uses olive. Anduril colours come from its website data, "
             "not a published guide, and the lime is the colour of its page-loading bar.",
        small="Small variant: heavier stroke (7 units) and a wider W.",
    ),
    dict(
        key="07-gmt", name="GMT Bezel", src="nasa", agency="NASA",
        line="A GMT watch tells the time in two places at once; World Watch tells you what is happening everywhere at once.",
        story="A watch made for pilots and navigators carries a 24-hour bezel, day on one half and night on the other, "
              "and one extra hand for another part of the world. Here the solid half is day, the faint half night, and "
              "the red pointer reaches into the night side: the half of the world that is asleep is still being watched.",
        wm=dict(font="michroma-400", text="WORLD WATCH", track=0.16, family="Michroma", weight="Regular 400"),
        palette=[C("NASA Blue", "#0032A0", "plate, primary", 55, "nasa"), C("White", "#FFFFFF", "bezel, light UI", 30, "nasa"),
                 C("NASA Red", "#E4002B", "the pointer, 'now'", 5, "nasa"), C("Black", "#000000", "dark UI", 10, "nasa")],
        dark=dict(bg="#000000", panel="#00164A", line="#0032A0", ink="#FFFFFF", sub="#B7C2E0", acc="#E4002B"),
        light=dict(bg="#FFFFFF", panel="#EEF1F9", line="#C9D2EA", ink="#000000", sub="#0032A0", acc="#E4002B"),
        devices=["Daylight bezel: a 24-hour UTC ring with the real day arc of a place (Munich, 28 Nov 2026: 06:39 to 15:25 UTC, computed).",
                 "Dual time stamp: every time in UTC first, local second ('12:00Z · 13:00 Munich')."],
        good="The best pun on the name; red-white-blue gives instant authority (and NASA's own colours). The bezel is a "
             "ready-made loading ring with real content.",
        weak="At 16 px it reads as a ring with a red dot (a gauge, compass or record button). Watch faces are a crowded "
             "icon genre. Red and blue together can recall the 'Pepsi' bezel of a famous GMT watch; I kept the bezel blue and "
             "white so it is not that.",
        small="Small variant: thicker ring (11 units) and a wider pointer.",
    ),
    dict(
        key="08-contact", name="Contact", src="nato", agency="NATO",
        line="Hull down: beyond the curve of the Earth the first thing you see of a ship is its mast, the moment "
             "a lookout exists for.",
        story="Because the Earth is round, a ship coming over the horizon shows its mast before its hull. A lookout's "
              "job is to catch that first sign. The mark is the curved sea, the sky and one mast: restrained, nautical, "
              "the alliance's two blues.",
        wm=dict(font="bigshoulders-800", text="WORLD WATCH", track=0.08, family="Big Shoulders Display", weight="ExtraBold 800"),
        palette=[C("NATO dark blue (PMS 280)", "#004990", "plate (sky), primary", 55, "nato"), C("NATO light blue (PMS 2718)", "#118ACB", "sea, accent", 20, "nato"),
                 C("White", "#FFFFFF", "mast, light UI", 15, "nato"), C("Black", "#000000", "dark UI, text", 10, "nato")],
        dark=dict(bg="#000000", panel="#00213F", line="#004990", ink="#FFFFFF", sub="#9EC6E6", acc="#118ACB"),
        light=dict(bg="#FFFFFF", panel="#EDF4FA", line="#C6DCEE", ink="#000000", sub="#004990", acc="#004990"),
        devices=["Horizon rule: a gently curved line used as a divider, with short ticks rising above it where items are.",
                 "Hull-down loader: a mast rising over the horizon in steps."],
        good="The calmest, most poetic idea; very ownable story; NATO's blues read as alliance/maritime without any symbol.",
        weak="Weakest at 16-24 px: a blue tile with a light bottom and a thin tick; recognisable only once known. "
             "Big Shoulders is a Chicago-born display face, not a NATO typeface.",
        small="Small variant: taller and wider mast (7 units), higher horizon.",
    ),
    dict(
        key="09-shells", name="Shells", src="gov", agency="GOV.UK (UK Government, incl. Companies House)",
        line="Open each shell until you reach the solid one: the person who really owns it.",
        story="Ownership chains hide behind holding companies inside holding companies. Registers such as the UK's "
              "'people with significant control' exist to reach the end of the chain. The mark is two shells and a solid "
              "core pushed into the corner, the way the Connections page drills to a beneficial owner.",
        wm=dict(font="librefranklin-700", text="World Watch", track=-0.005, family="Libre Franklin", weight="Bold 700"),
        palette=[C("Blue", "#1D70B8", "plate, primary, links", 45, "gov"), C("White", "#FFFFFF", "shells, light UI", 25, "gov"),
                 C("Black", "#0B0C0C", "text, dark UI", 22, "gov"), C("Dark blue (shade 50)", "#0F385C", "dark panels", 6, "gov"),
                 C("Red", "#CA3535", "warnings only (sanctions)", 2, "gov")],
        dark=dict(bg="#0B0C0C", panel="#0F385C", line="#1D70B8", ink="#FFFFFF", sub="#B9CCE0", acc="#1D70B8"),
        light=dict(bg="#FFFFFF", panel="#F2F6FA", line="#CBD9E8", ink="#0B0C0C", sub="#0F385C", acc="#1D70B8"),
        devices=["Shell frames: panels nested as frame within frame, the solid block marking the end of a chain.",
                 "Ownership chain: boxes joined by arrows labelled with the share held, read left to right to the owner."],
        good="Perfectly legible at every size; speaks directly to the Connections page; the GOV.UK palette is the house colour "
             "of the very registers the feature reads.",
        weak="Nested squares are a common shape (frames, 'fit to screen' icons); the corner placement of the core is the only "
             "distinctive move. Feels civic rather than intelligence.",
        small="Small variant: one shell and a larger core.",
    ),
    dict(
        key="10-footnote", name="Footnote", src="can", agency="Government of Canada (Canada.ca)",
        line="W for World Watch with its reference mark: nothing on the screen appears without a source.",
        story="Every claim in a serious report carries a small number that leads to its source. The mark is the initial "
              "with that number in red. It is the editorial direction: the Investigate page as a well-sourced document, "
              "and the brand's promise that summaries are traceable.",
        wm=dict(font="fraunces-600", text="World Watch", track=-0.005, family="Fraunces", weight="SemiBold 600"),
        palette=[C("Accent (slate)", "#26374A", "plate, headings", 40, "can"), C("White", "#FFFFFF", "W, background", 35, "can"),
                 C("Text grey", "#333333", "body text", 15, "can"), C("Link blue", "#284162", "links, rules", 6, "can"),
                 C("Required red", "#D3080C", "the reference mark only", 4, "can")],
        dark=dict(bg="#1B2836", panel="#26374A", line="#3A4D63", ink="#FFFFFF", sub="#C3CDD8", acc="#D3080C"),
        light=dict(bg="#FFFFFF", panel="#F5F6F7", line="#D7DCE1", ink="#333333", sub="#284162", acc="#D3080C"),
        devices=["Reference marks: red superscript numbers after every claim, the sources listed beneath with their date.",
                 "Source rule: a thin rule with a red tick that opens every source line."],
        good="Typographic and editorial; the only serif direction; ties directly to the 'traceable to source data' rule and "
             "to printed case files.",
        weak="A white W on a dark tile sits close to Microsoft Word's icon on a Windows taskbar, the exact place it will live; "
             "the serif and the red numeral help but do not remove the risk. At 16 px the numeral is a red smudge. Dark "
             "background #1B2836 is a darker mix of the Canada.ca accent, not a published colour.",
        small="Small variant: larger W (the numeral keeps its size).",
    ),
]

BY_KEY = {d["key"]: d for d in DIRECTIONS}
TOP3 = ["01-cocked-hat", "06-w-trace", "02-terminator"]
