# World Watch

A personal live view of the world from free public feeds. Real data only: every feed shows its
source, when it was fetched, and the source's own timestamp.

The app is the map at `/`; a full report on every feed is at `/feeds`.

## Run it

You need [uv](https://docs.astral.sh/uv/) (`brew install uv`). Nothing else, no API keys.

```bash
cd server
uv run python -m worldwatch serve
```

Then open http://127.0.0.1:8710/

The first start downloads the Python packages and takes a few seconds longer.
Stop it with Ctrl-C. Collected data is kept in `data/` and survives restarts.

### Free keys and settings (optional, each switches on one extra)

Each goes in its own one-line file in the `data` folder, which sits in the project's top folder
(next to `README.md`, not inside `server`). It is created on first start; git ignores it. Never put a
key in git: a key pushed to GitHub gets reported and revoked within minutes. Each can also be given as
the environment variable shown. Restart the server after adding one. Without them everything else works;
the feed report shows the missing ones as "not set up".

| File (or variable) | Register at | Switches on |
|---|---|---|
| `data/aisstream-key.txt` (`WW_AISSTREAM_KEY`) | aisstream.io (sign in with GitHub, "API Keys"), free | ships and warships worldwide, not only the northern Baltic |
| `data/opensanctions-key.txt` (`WW_OPENSANCTIONS_KEY`) | opensanctions.org/api, free for non-commercial use | sanctions and politically-exposed-person lists in people dossiers |
| `data/cloudflare-token.txt` (`WW_CLOUDFLARE_TOKEN`) | dash.cloudflare.com: My Profile > API Tokens > custom token with Account > Radar > Read, free | internet hijacks and route leaks, Cloudflare's outage notes, cable cuts |
| `data/windy-key.txt` (`WW_WINDY_KEY`) | api.windy.com/keys (Webcams API, free tier) | public webcams worldwide in the Cameras layer |
| `data/brave-key.txt` (`WW_BRAVE_KEY`) | api-dashboard.search.brave.com (free monthly credit, needs a payment card) | ship photos from VesselFinder when Wikimedia has none |
| `data/contact.txt` (`WW_CONTACT`) | not a key: your email or web address | aircraft photos (planespotters.net asks every client for a contact) and polite requests to Wikimedia |

From the `server` folder (where you start the app):

```bash
echo "YOUR-KEY" > ../data/aisstream-key.txt
```

Other settings (environment variables, see `server/worldwatch/config.py`): `WW_HOST=0.0.0.0` to reach the
map from another device (for example over Tailscale), `WW_PORT`, `WW_DATA` (data folder), `WW_LAT` / `WW_LON`
(home point, Munich by default).

## What it fetches

44 feeds, each with its own page row at `/feeds`. The intervals follow each source's published limits;
please don't shorten them.

| Feed | Source | How often |
|---|---|---|
| Aircraft where you are looking | adsb.fi | 10 s, only while zoomed in |
| Aircraft near Munich | adsb.fi | 20 s |
| Military aircraft | adsb.fi (adsb.lol as fallback) | 30 s |
| Aircraft worldwide, and flown paths on request | OpenSky Network | 20 min |
| Government, VIP and "doomsday" aircraft list | plane-alert-db (ODbL) | weekly |
| GPS interference, last hour (derived) | adsb.fi, worked out by World Watch | 10 min |
| GPS interference, one map per day | GPSJAM (their analysis) | 6 h |
| Satellites and ISS | CelesTrak | 2 h |
| Spy satellites | CelesTrak, amateur observers | 12 h |
| What satellites do | UCS Satellite Database | weekly |
| Rocket launches | Launch Library 2 | 15 min |
| News places, and news in other languages | GDELT | 2 min / 5 min |
| Protests and clashes | GDELT events (machine-coded) | 2 min |
| Cable faults in the news | SubTel Forum, GDELT | 3 h |
| Navy warnings at sea | NGA and UKHO | 30 min |
| Airspace warnings and closures | EASA, FAA | 60 min |
| Front line, Ukraine | DeepState | 2 h |
| Military bases and nuclear sites | Wikidata, OpenStreetMap, US DoD, Global Energy Monitor | weekly |
| US carriers | USNI News Fleet Tracker | 6 h |
| Sanctioned ships and aircraft | OpenSanctions (bulk data, no key) | weekly |
| International Criminal Court cases | icc-cpi.int | daily |
| Travel advice per country | US State Department, German Foreign Office | 6 h |
| Earthquakes | USGS | 60 s |
| Disaster alerts / natural events | GDACS (UN and EU) / NASA EONET | 10 min / 30 min |
| Disaster maps and pictures | Copernicus EMS, Maxar Open Data | hourly / daily |
| Fire detections | NASA FIRMS (MODIS, last 24 hours) | 30 min |
| Rain radar | RainViewer | 5 min |
| Space weather and aurora | NOAA SWPC | 10 min |
| Undersea cables | TeleGeography (CC BY-NC-SA, private use only) | weekly |
| Internet outages | IODA (Georgia Tech) | 5 min |
| Internet hijacks, leaks, outage notes | Cloudflare Radar (key) | 15 min |
| Ships, northern Baltic / worldwide | Digitraffic, Finland / aisstream.io (key) | 60 s / live stream |
| Public cameras | TfL, NYC DOT, Caltrans, LTA Singapore, HK Transport Dept, Fintraffic; Windy (key) | daily list; Windy on request |
| Listening stations | KiwiSDR public list | hourly |
| Country tables for flags | ICAO (via tar1090), ITU (via Wikidata), CelesTrak | weekly |
| Munich weather and warnings | German Weather Service via Bright Sky | 10 min |
| Munich transport disruptions | MVG (unofficial feed) | 5 min |
| Markets / Bitcoin / exchange rates | Yahoo Finance (unofficial, delayed) / CoinGecko / ECB via Frankfurter | 5 min / 2 min / 60 min |

The browser also loads map pictures directly: OpenFreeMap (base map), NASA GIBS (daily and live satellite photos),
EUMETSAT (lightning, live photo), Esri World Imagery (sharp photo), terrain heights for 3D.

## People (public figures)

A **People** chip on the map shows current heads of state and government at their countries; click one,
or use "Find a person or country" in the sidebar, for a profile built from public records (Wikidata, Wikipedia,
GDELT news, and OpenSanctions if a key is set). It covers public roles and anyone with a Wikidata entry;
it shows who a person is and what the record holds, never where they are now.

The sanctions / politically-exposed-person section needs the OpenSanctions key (see above); without it that one
section is skipped and says so.

## Lookup

`/lookup` shows what public sources reveal about your own usernames and email addresses, as a graph.
Besides its own checks it runs the standard open-source tools unchanged, as separate programs
through `uvx`: Maigret, Sherlock, Holehe and theHarvester. They are downloaded on first use
(Maigret is about 190 MB) into uv's tool cache, not into World Watch.
It runs only when you press Scan, shows first what will be sent where, and keeps results in
`data/lookup.db` on this computer. Its API answers only on the computer World Watch runs on, and only to its
own page: other websites open in your browser cannot read it or start anything. To use it from another device
(for example over Tailscale) start with `WW_LOOKUP_REMOTE=1`; it then accepts IP addresses, one-word machine
names and `*.ts.net` names, plus any names listed in `WW_ALLOWED_HOSTS` (comma-separated).

Project history, decisions and open issues are in `CLAUDE.md`.
