"""`uv run python -m worldwatch serve` starts the collector and the web page."""
import sys

import uvicorn

from . import config


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "serve"
    if cmd != "serve":
        sys.exit("usage: python -m worldwatch serve")
    print(f"World Watch is starting. Open http://{config.HOST}:{config.PORT}/")
    uvicorn.run("worldwatch.web:app", host=config.HOST, port=config.PORT, log_level="warning")


if __name__ == "__main__":
    main()
