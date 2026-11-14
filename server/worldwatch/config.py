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
