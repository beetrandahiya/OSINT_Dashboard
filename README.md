# World Watch

A personal live view of the world from free public feeds. Real data only: every feed shows its
source, when it was fetched, and the source's own timestamp.

Right now this is the first step: the feed collector and a live status page. The map comes next.

## Run it

You need [uv](https://docs.astral.sh/uv/) (`brew install uv`). Nothing else, no API keys.

```bash
cd server
uv run python -m worldwatch serve
```

Then open http://127.0.0.1:8710/

The first start downloads Python packages (three small ones) and takes a few seconds longer.
Stop it with Ctrl-C. Collected data is kept in `data/` and survives restarts.

To reach it from another device (for example over Tailscale), start it with `WW_HOST=0.0.0.0`.

## What it fetches

| Feed | Source | How often |
|---|---|---|
| Aircraft near Munich | adsb.fi | 10 s |
| Military aircraft | adsb.lol | 5 min |
| Aircraft worldwide | OpenSky Network | 15 min |
| Satellites and ISS | CelesTrak | 2 h |
| Rocket launches | Launch Library 2 | 15 min |
| News places | GDELT | checks every 2 min, new file every 15 min |
| Earthquakes | USGS | 60 s |
| Internet outages | IODA (Georgia Tech) | 5 min |
| Markets | Yahoo Finance (unofficial, delayed) | 5 min |
| Bitcoin | CoinGecko | 2 min |
| Exchange rates | ECB via Frankfurter | 60 min |

The intervals follow each source's published limits. Please don't shorten them.

Project history, decisions and open issues are in `CLAUDE.md`.
