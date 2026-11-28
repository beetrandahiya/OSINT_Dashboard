"""The six globe directions: idea, story, facts, palette with sources, UI tokens, wordmark, verdict."""

SRC = {
    "nato": ("NATO Visual Identity Guidelines (2016), colour table",
             "https://www.act.nato.int/wp-content/uploads/2023/06/NATO-VIGs-2016-en.pdf",
             "Read from the PDF in round one: dark blue PMS 280 = #004990, light blue PMS 2718 = #118ACB, black, white."),
    "bp": ("Palantir Blueprint colours (packages/colors/src/colors.ts)",
           "https://github.com/palantir/blueprint/blob/develop/packages/colors/src/colors.ts",
           "Palantir's own open-source UI system; read from the file on GitHub in round one."),
    "nga": ("NGA website stylesheet (nga.mil)", "https://www.nga.mil/assets/css/main.css",
            "Most-used colours of the agency's live site (built on the U.S. Web Design System, whose typeface is Public Sans). "
            "A website, not a published brand guide."),
    "brg": ("Bundesregierung styleguide: Petrol",
            "https://styleguide.bundesregierung.gov.de/sg-de/basiselemente/farben/petrol-2051434",
            "Petrol #007194 (Pantone 315) with its 80/60/40/20 % tints; black is the styleguide's text colour."),
    "eum": ("EUMETSAT website stylesheet (eumetsat.int)", "https://www.eumetsat.int/",
            "Named colours in the site's CSS, read 28 Nov 2026: --eumetsat-blue #00205B (also #1E3650, #6D96B2), "
            "--primary #0079C0, --secondary #A8CF45. A website, not a published brand guide."),
    "dlr": ("DLR website stylesheet (dlr.de)", "https://www.dlr.de/de",
            "Most-used colours of the German Aerospace Center's site, read 28 Nov 2026: #007EB1, #252525, #C7D5D8, "
            "#EDF1F2, #55B8DA, #517776, #E40166. A website, not a published brand guide."),
}


def C(name, hexv, role, share, src, mix=False):
    return dict(name=name, hex=hexv, role=role, share=share, src=src, mix=mix)


DIRS = [
    dict(
        key="oko", name="Oko", rank=1, src="nato", agency="NATO",
        idea="The orbit of the Soviet early-warning satellites called Oko, “eye”, drawn to scale with the Earth: "
             "it looks like an eye because it was one.",
        story=["Oko is Russian for eye. From 1972 the Soviet Union watched for missile launches with infrared satellites on "
               "Molniya orbits: long ellipses that swing a satellite low past the Earth and then hold it high over the "
               "northern hemisphere for most of its twelve hours.",
               "Drawn to scale, with the Earth where physics puts it (at one focus), the orbit becomes an eye and the planet "
               "its iris, almost touching the line at the near end. In large sizes the line can give way to the satellite's "
               "position every 30 minutes: the dots bunch at the far end, where it slows down and watches."],
        facts=[("Orbit", "Molniya, flown by Oko (US-K)"), ("Lowest / highest", "600 km / 39,700 km up"),
               ("Eccentricity", "0.737"), ("One orbit", "11.94 h"), ("Time in the far half", "73.5 %"),
               ("Scale", "Earth and orbit at one scale"), ("First / last US-K", "Kosmos 520, 1972 / Kosmos 2469, 2010")],
        palette=[C("Dark blue (PMS 280)", "#004990", "plate, panels", 45, "nato"), C("Black", "#000000", "dark UI", 25, "nato"),
                 C("White", "#FFFFFF", "Earth, orbit, light UI", 20, "nato"), C("Light blue (PMS 2718)", "#118ACB", "time dots, links", 10, "nato")],
        dark=dict(bg="#000000", panel="#0B1A2A", line="#1F3550", ink="#FFFFFF", sub="#9DB3C8", acc="#118ACB"),
        light=dict(bg="#FFFFFF", panel="#EEF3F8", line="#C9D6E3", ink="#000000", sub="#004990", acc="#004990"),
        mixes="#0B1A2A, #1F3550, #9DB3C8, #EEF3F8 and #C9D6E3 are mixes of the NATO colours for UI, not published values.",
        wm=dict(font="chakrapetch-600", text="WORLD WATCH", track=0.10, family="Chakra Petch SemiBold, capitals"),
        devices=[("Loading dots", "24 dots, one per 30 minutes of the orbit. They bunch where the satellite is slow; the bright one "
                  "moves at the real relative pace (one orbit compressed to 6 seconds)."),
                 ("Altitude ruler", "To scale from the ground to 40,000 km: the classes the app colours on the globe, with this "
                  "orbit's highest point for reference. Used as the space view's key.")],
        good="The strongest story of the set, and every part of it is true: the shape, the scale and the name. Nothing like the "
             "usual globe icons; there is an eye in it without anyone drawing an eye. Clean at 16 px.",
        weak="At small size it sits close to the generic “orbit” icon (an oval around a planet); the meaning needs the "
             "story once. It quotes a Soviet military programme: flavour for a private tool, but say so if that bothers you. "
             "The Earth is a plain disc, as there is no room for coastlines at this scale.",
        small="Small variant: a 4-unit line instead of 2 and a slightly wider span. The Earth keeps its true size against the orbit.",
    ),
    dict(
        key="unrolled", name="Unrolled", rank=2, src="nga", agency="NGA (National Geospatial-Intelligence Agency)",
        idea="At Greenwich the globe unrolls into the square tiles the map engine really loads; the one lit tile holds Munich.",
        story=["World Watch is one world drawn two ways, and the switch between globe and flat map was the first decision in "
               "the project. The mark shows both at once.",
               "West of Greenwich the Earth is a globe with curved meridians. East of it the same world becomes what the "
               "map engine actually downloads: square Web Mercator tiles, four by four at zoom 2. The teal tile is the one "
               "that contains Munich."],
        facts=[("Seam", "Greenwich, 0°"), ("Left", "globe, 90° W to 0°"), ("Right", "web map, 0° to 180° E"),
               ("Munich's tile, zoom 2", "x 2, y 1 (0–66.5° N, 0–90° E)"), ("Same, zoom 14", "x 8718, y 5685"),
               ("Square world", "±85.05° latitude")],
        palette=[C("Navy", "#0D2F4B", "plate, panels", 45, "nga"), C("Mist", "#F0F0F0", "globe, tiles, light UI", 30, "nga"),
                 C("Blue", "#154E7D", "links, selected", 10, "nga"), C("Ink", "#1B1B1B", "dark UI, text", 8, "nga"),
                 C("Teal", "#2FA3AA", "Munich's tile, accent", 5, "nga"), C("Grey", "#DFE1E2", "lines (light)", 2, "nga")],
        dark=dict(bg="#1B1B1B", panel="#0D2F4B", line="#2C4B66", ink="#F0F0F0", sub="#A9B9C8", acc="#2FA3AA"),
        light=dict(bg="#F0F0F0", panel="#FFFFFF", line="#DFE1E2", ink="#1B1B1B", sub="#154E7D", acc="#154E7D"),
        mixes="#2C4B66 and #A9B9C8 are mixes for UI, not NGA values.",
        wm=dict(font="publicsans-700", text="World Watch", track=-0.005, family="Public Sans Bold (the U.S. Web Design System's typeface, which NGA's site uses)"),
        devices=[("Map / Globe switch", "The app's oldest control, built from the mark: the half globe for the globe, the tiles for "
                  "the flat map."),
                 ("Tile address", "Munich's real tile numbers at four zoom levels, as a stamp on cards and covers.")],
        good="The most distinctive silhouette (half disc, half grid) and the most honest about how the app works. It doubles as "
             "the Map / Globe switch, and the mapping agency's colours fit it.",
        weak="The busiest of the six: at 16 px the tiles merge into a grid texture. It is a technical idea; someone who has never "
             "thought about web maps sees “globe and grid”. Close in spirit to Quadkey from round one.",
        small="Small variant: one meridian instead of two, wider gaps between tiles.",
    ),
    dict(
        key="footprint", name="Footprint", rank=3, src="bp", agency="Palantir (Blueprint)",
        idea="Everything a satellite can see from above Munich, drawn on the globe: the Earth becomes an eyeball and the "
             "footprint its iris.",
        story=["A satellite sees everything inside a circle on the globe, and the size of that circle depends only on its "
               "height. For Sentinel-2, whose pictures the app lists under “photographed from orbit”, the circle reaches "
               "27.1 degrees from the point below it: 6,030 km across.",
               "Centred on Munich and seen from off to one side, the circle becomes an ellipse and the globe an eye looking at "
               "home. The app already draws this shape as the satellite spotlight."],
        facts=[("Satellite", "Sentinel-2, 786 km up"), ("Horizon", "27.1° from the point below"),
               ("Across the ground", "6,030 km"), ("Share of the Earth", "5.5 %"),
               ("Centre", "Munich, 48.14° N 11.58° E"), ("Seen from above", "20° N 10° W")],
        palette=[C("Black", "#111418", "plate, dark UI", 50, "bp"), C("Light Gray 5", "#F6F7F9", "globe, light UI", 25, "bp"),
                 C("Dark Gray 1", "#1C2127", "panels", 12, "bp"), C("Blue 3", "#2D72D2", "footprint (light)", 6, "bp"),
                 C("Blue 4", "#4C90F0", "footprint (dark)", 4, "bp"), C("Gray 1", "#5F6B7C", "secondary text", 3, "bp")],
        dark=dict(bg="#111418", panel="#1C2127", line="#2F343C", ink="#F6F7F9", sub="#ABB3BF", acc="#4C90F0"),
        light=dict(bg="#F6F7F9", panel="#FFFFFF", line="#D3D8DE", ink="#111418", sub="#5F6B7C", acc="#2D72D2"),
        mixes="All values are Blueprint's own.",
        wm=dict(font="geist-600", text="World Watch", track=-0.012, family="Geist SemiBold"),
        devices=[("Coverage chips", "What a satellite can see, with real numbers, on satellite cards and in the space view's list."),
                 ("Horizon scale", "Four real satellites' footprints around Munich: the higher the orbit, the more of the Earth it sees.")],
        good="The clearest double reading, globe and eye at once, and readable at 16 px. Palantir's own colours suit a mark "
             "about seeing far.",
        weak="It reads as an eye first, and the round iris with a black pupil comes close to a cartoon eye. “Eye and globe” "
             "logos exist, though usually with the globe inside an eye; here it is the other way round. The viewing direction "
             "is a choice, picked so the footprint sits up and to the right.",
        small="Small variant: the globe fills more of the tile and the pupil is larger; the footprint keeps its true size.",
    ),
    dict(
        key="above", name="Above home", rank=0, src="brg", agency="Bundesregierung (German Federal Government)",
        idea="The Earth seen from straight above Munich, which shows almost as much land as any single view of the Earth can.",
        story=["Look down on the Earth from far above Munich and almost half of what you see is land: 45.5 percent, with four "
               "fifths of all the world's land in one view. No view does much better. The best, centred over western France, "
               "reaches 46.7 percent; geographers call it the land hemisphere, and home is about 10 degrees from its centre.",
               "The mark is that view, with the real coastlines and a point on Munich."],
        facts=[("Centre", "Munich, 48.14° N 11.58° E"), ("Land in view", "45.5 % of the hemisphere"),
               ("All land in view", "79.1 %"), ("Best possible view", "46.7 %, over western France"),
               ("Whole Earth", "28.7 % land (same data)"), ("Computed from", "Natural Earth outlines, 400,000 points")],
        palette=[C("Petrol (Pantone 315)", "#007194", "plate, land", 45, "brg"), C("White", "#FFFFFF", "globe, light UI", 25, "brg"),
                 C("Black (text)", "#000000", "text, home point, dark UI", 15, "brg"), C("Petrol 20 %", "#CCE3EA", "globe on dark, panels", 10, "brg"),
                 C("Petrol 60 %", "#66AABF", "accent on dark", 5, "brg")],
        dark=dict(bg="#000000", panel="#00303F", line="#007194", ink="#FFFFFF", sub="#99C6D4", acc="#66AABF"),
        light=dict(bg="#FFFFFF", panel="#CCE3EA", line="#99C6D4", ink="#000000", sub="#007194", acc="#007194"),
        mixes="#00303F (petrol and black) is a mix for dark panels, not a published colour.",
        wm=dict(font="manrope-700", text="World Watch", track=-0.01, family="Manrope Bold"),
        devices=[("Land share", "The computed numbers as a bar, to scale. Facts as decoration, where decoration is needed."),
                 ("Points of light", "The same view as dots of land on a regular grid: a quiet background for the splash and empty states.")],
        good="The most recognisable as the Earth and the most personal: real coastlines, centred on home, with a computed fact "
             "behind it. Anyone gets it at first sight.",
        weak="It looks like a globe with continents, as many logos do; what is special is the story, not the shape. The "
             "coastlines turn into blobs at 16 px. German government petrol makes it feel official.",
        small="Small variant: coastlines simplified to about 1 unit, the home point larger.",
    ),
    dict(
        key="octant", name="Octant", rank=0, src="eum", agency="EUMETSAT",
        idea="A triangle with three right angles: impossible on paper, ordinary on a globe, and Munich is inside it.",
        story=["Draw a line from the North Pole down the Greenwich meridian to the equator, a quarter of the way round the "
               "equator, and back up to the pole. Every corner is a right angle, the angles add up to 270 degrees, and the "
               "triangle covers exactly one eighth of the Earth.",
               "Munich lies inside it. A flat map cannot draw this shape truthfully, which is why World Watch has a globe."],
        facts=[("Corners", "North Pole, 0° N 0° E, 0° N 90° E"), ("Angles", "90° + 90° + 90° = 270°"),
               ("Area", "1/8 of the Earth, 63.8 million km²"), ("Munich", "inside, 48.14° N 11.58° E"),
               ("Seen from above", "35.26° N 45° E, its centre")],
        palette=[C("EUMETSAT blue", "#00205B", "plate, dark UI", 50, "eum"), C("White", "#FFFFFF", "globe, light UI", 25, "eum"),
                 C("Primary blue", "#0079C0", "the triangle, links", 10, "eum"), C("Grey blue", "#6D96B2", "secondary", 8, "eum"),
                 C("Dark blue", "#1E3650", "panels", 5, "eum"), C("Secondary green", "#A8CF45", "status: ok", 2, "eum")],
        dark=dict(bg="#00205B", panel="#1E3650", line="#2F4A70", ink="#FFFFFF", sub="#B9CCDA", acc="#6D96B2"),
        light=dict(bg="#FFFFFF", panel="#F1F5F8", line="#D5DEE6", ink="#00205B", sub="#1E3650", acc="#0079C0"),
        mixes="#2F4A70, #B9CCDA, #F1F5F8 and #D5DEE6 are mixes for UI, not EUMETSAT values.",
        wm=dict(font="redhatdisplay-600", text="World Watch", track=-0.01, family="Red Hat Display SemiBold"),
        devices=[("Curvature hint", "Shown where the app measures across the globe: the triangle with its three right angles."),
                 ("Progress in eighths", "Eight octants for long jobs such as a lookup scan (the state shown is an example).")],
        good="Bold and simple: reads at 16 px and still holds as a 1,024 px icon. A geometric fact anyone can check.",
        weak="The shape can read as a sail, a fin or a guitar pick before it reads as geometry. The fact belongs to the world, "
             "not to World Watch. EUMETSAT's colours come from its website's code, not a brand guide.",
        small="Small variant: the globe fills more of the tile.",
    ),
    dict(
        key="lune", name="Lune", rank=0, src="dlr", agency="DLR (German Aerospace Center)",
        idea="Home's hour on the globe: the 15-degree slice of Central European Time, a shape with only two sides.",
        story=["The Earth turns 15 degrees an hour, and time zones were laid out as 15-degree slices from pole to pole. "
               "Germany's hour, UTC+1, is nominally the slice from 7.5 to 22.5 degrees east, and Munich is inside it.",
               "On a sphere such a slice is a lune, a figure with two sides that cannot exist on a flat page. Face on, it is a "
               "slit across the globe: an hour, a watch, an eye half closed."],
        facts=[("Slice", "7.5° E to 22.5° E (UTC+1, nominal)"), ("Width", "15°, one hour of the Earth's turn"),
               ("Area", "1/24 of the Earth, 21.3 million km²"), ("Munich", "inside, 11.58° E"),
               ("Seen from above", "0° N 15° E")],
        palette=[C("DLR blue", "#007EB1", "globe, links", 35, "dlr"), C("Near black", "#252525", "plate, dark UI", 30, "dlr"),
                 C("Pale", "#EDF1F2", "the lune, light UI", 20, "dlr"), C("Grey blue", "#C7D5D8", "lines", 8, "dlr"),
                 C("Light blue", "#55B8DA", "accent on dark", 5, "dlr"), C("Magenta", "#E40166", "the current hour only", 2, "dlr")],
        dark=dict(bg="#252525", panel="#2F3336", line="#3E474C", ink="#EDF1F2", sub="#C7D5D8", acc="#55B8DA"),
        light=dict(bg="#EDF1F2", panel="#FFFFFF", line="#C7D5D8", ink="#252525", sub="#517776", acc="#007EB1"),
        mixes="#2F3336 and #3E474C are mixes for dark panels; #517776 is from DLR's stylesheet.",
        wm=dict(font="plexsanscond-600", text="WORLD WATCH", track=0.06, family="IBM Plex Sans Condensed SemiBold, capitals"),
        devices=[("World clock strip", "24 lunes, one per hour. Home's is lit; the magenta tick is where the sun stood overhead when this page was built."),
                 ("Hour stamp", "Next to times in cards, so every time says which hour it is in.")],
        good="Very simple, and it ties “watch” to time. DLR, whose space operations centre is at Oberpfaffenhofen near "
             "Munich, is a local and fitting palette.",
        weak="The weakest at small size: a disc with a vertical slit reads as a coin on edge, a reptile's eye or a power symbol. "
             "Real time zones zigzag; the lune is the nominal one.",
        small="Small variant: the globe fills more of the tile; the lune keeps its true width.",
    ),
]
