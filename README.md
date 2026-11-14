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

The first start downloads Python packages (three small ones) and takes a few seconds longer.
Stop it with Ctrl-C. Collected data is kept in `data/` and survives restarts.

### Free keys (optional, each switches on one extra)

Each key goes in its own one-line file in `data/` (created on first start; git ignores it). Nothing else
needs a key.

| File | Register at | Switches on |
|---|---|---|
| `data/aisstream-key.txt` | aisstream.io (sign in with GitHub, "API Keys") | ships worldwide, not only the northern Baltic |
| `data/opensanctions-key.txt` | opensanctions.org/api (free for non-commercial use) | sanctions and politically-exposed-person lists in people profiles |

```bash
echo "YOUR-KEY" > data/aisstream-key.txt
```

Restart the server after adding a key.

### Aircraft photos (optional)

Photos in the aircraft card come from planespotters.net, which asks every client to send a contact
email or web address. Put yours in a one-line file; it stays on your machine and out of git:

```bash
mkdir -p data && echo "you@example.com" > data/contact.txt
```

Without that file the app works the same, just without photos.

To reach it from another device (for example over Tailscale), start it with `WW_HOST=0.0.0.0`.

## What it fetches

| Feed | Source | How often |
|---|---|---|
| Aircraft where you are looking | adsb.fi | about every 10 s, only while zoomed in |
| Aircraft near Munich | adsb.fi | 20 s |
| Military aircraft | adsb.lol | 5 min |
| Aircraft worldwide, and flown paths on request | OpenSky Network | 20 min |
| Satellites and ISS | CelesTrak | 2 h |
| Rocket launches | Launch Library 2 | 15 min |
| News places | GDELT | checks every 2 min, new file every 15 min |
| News in German and Hindi | GDELT | checks every 5 min, about an hour behind |
| Earthquakes | USGS | 60 s |
| Internet outages | IODA (Georgia Tech) | 5 min |
| Disaster alerts | GDACS (UN and EU) | 10 min |
| Natural events | NASA EONET | 30 min |
| Rain radar | RainViewer | 5 min (new picture every 10) |
| Space weather and aurora | NOAA SWPC | 10 min |
| Undersea cables | TeleGeography (CC BY-NC-SA, private use only) | weekly |
| GPS interference | GPSJAM (their analysis, one map per day) | 6 h |
| Fire detections | NASA FIRMS (MODIS, last 24 hours) | 30 min |
| Ships, northern Baltic only | Digitraffic, Finland (open data) | 60 s |
| Satellite photo of yesterday | NASA GIBS (map tiles, loaded by the browser) | daily |
| Munich weather and warnings | German Weather Service via Bright Sky | 10 min |
| Munich transport disruptions | MVG (unofficial feed) | 5 min |
| Markets | Yahoo Finance (unofficial, delayed) | 5 min |
| Bitcoin | CoinGecko | 2 min |
| Exchange rates | ECB via Frankfurter | 60 min |

The intervals follow each source's published limits. Please don't shorten them.

## People (public figures)

A **People** chip on the map shows current heads of state and government at their countries; click one,
or use "Find a person" in the sidebar, for a profile built from public records (Wikidata, Wikipedia,
GDELT news, and OpenSanctions if a key is set). It covers public roles and anyone with a Wikidata entry;
it shows who a person is and what the record holds, never where they are now.

For the sanctions / politically-exposed-person section, register a free OpenSanctions API key and put it in
`data/opensanctions-key.txt` (or `WW_OPENSANCTIONS_KEY`). Without it that one section is skipped.

## Lookup

`/lookup` shows what public sources reveal about your own usernames and email addresses, as a graph.
Besides its own checks it runs the standard open-source tools unchanged, as separate programs
through `uvx`: Maigret, Sherlock, Holehe and theHarvester. They are downloaded on first use
(Maigret is about 190 MB) into uv's tool cache, not into World Watch.
It runs only when you press Scan, shows first what will be sent where, and keeps results in
`data/lookup.db` on this computer. It answers only on the computer World Watch runs on
(set `WW_LOOKUP_REMOTE=1` to allow other devices).

Project history, decisions and open issues are in `CLAUDE.md`.
