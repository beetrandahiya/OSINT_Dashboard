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
