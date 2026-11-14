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

Project history, decisions and open issues are in `CLAUDE.md`.
