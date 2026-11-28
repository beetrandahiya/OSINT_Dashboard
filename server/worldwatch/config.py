"""Settings. Everything can be overridden with environment variables; nothing here is secret."""
import os
from pathlib import Path

DATA = Path(os.environ.get("WW_DATA", Path(__file__).resolve().parents[2] / "data"))
DB_PATH = DATA / "worldwatch.db"
HOST = os.environ.get("WW_HOST", "127.0.0.1")
PORT = int(os.environ.get("WW_PORT", "8710"))

# Home point for the "around me" feeds (Munich city centre).
HOME_LAT = float(os.environ.get("WW_LAT", "48.137"))
HOME_LON = float(os.environ.get("WW_LON", "11.575"))
HOME_RADIUS_NM = int(os.environ.get("WW_RADIUS_NM", "100"))

# Sent with every request so feed operators can see who is calling.
USER_AGENT = os.environ.get("WW_USER_AGENT", "WorldWatch/0.1 (personal non-commercial dashboard)")


def contact() -> str | None:
    """An email or web address of whoever runs this copy. planespotters.net requires one in the request header
    before it serves aircraft photos; it is sent to them and to nobody else. Kept out of the code: put it in
    data/contact.txt (one line) or in the WW_CONTACT environment variable. Without it, photos are simply off."""
    if os.environ.get("WW_CONTACT"):
        return os.environ["WW_CONTACT"].strip()
    f = DATA / "contact.txt"
    return f.read_text().strip() or None if f.exists() else None


def opensanctions_key() -> str | None:
    """A free OpenSanctions API key, if the user registered for one, for the sanctions / politically-exposed
    check in profiles. Put it in data/opensanctions-key.txt or WW_OPENSANCTIONS_KEY. Without it that one
    section is skipped and says so. Never in git."""
    import os
    if os.environ.get("WW_OPENSANCTIONS_KEY"):
        return os.environ["WW_OPENSANCTIONS_KEY"].strip()
    f = DATA / "opensanctions-key.txt"
    return f.read_text().strip() or None if f.exists() else None


def cloudflare_token() -> str | None:
    """A free Cloudflare API token with Account > Radar > Read, for internet hijacks, route leaks and outage notes.
    data/cloudflare-token.txt or WW_CLOUDFLARE_TOKEN. Never in git."""
    import os
    if os.environ.get("WW_CLOUDFLARE_TOKEN"):
        return os.environ["WW_CLOUDFLARE_TOKEN"].strip()
    for f in (DATA / "cloudflare-token.txt", Path(__file__).resolve().parents[2] / "keys" / "cloudflare-token.txt"):
        if f.exists() and f.read_text().strip():
            return f.read_text().strip()   # data/ first; keys/ is committed to the repo at the owner's request (2026-11-15)
    return None


def windy_key() -> str | None:
    """A free Windy Webcams API key (api.windy.com/keys), for public webcams worldwide. data/windy-key.txt or
    WW_WINDY_KEY. Never in git."""
    import os
    if os.environ.get("WW_WINDY_KEY"):
        return os.environ["WW_WINDY_KEY"].strip()
    f = DATA / "windy-key.txt"
    return (f.read_text().strip() or None) if f.exists() else None


def brave_key() -> str | None:
    """A Brave Search API key (free monthly credit), for ship photos when Wikimedia has none. data/brave-key.txt or
    WW_BRAVE_KEY. Never in git."""
    import os
    if os.environ.get("WW_BRAVE_KEY"):
        return os.environ["WW_BRAVE_KEY"].strip()
    f = DATA / "brave-key.txt"
    return (f.read_text().strip() or None) if f.exists() else None


def github_token() -> str | None:
    """A GitHub token (no scopes needed) for the lookup page's GitHub checks: 5,000 requests an hour instead of 60.
    data/github-token.txt or WW_GITHUB_TOKEN. Never in git."""
    if os.environ.get("WW_GITHUB_TOKEN"):
        return os.environ["WW_GITHUB_TOKEN"].strip()
    f = DATA / "github-token.txt"
    return (f.read_text().strip() or None) if f.exists() else None
