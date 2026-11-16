"""Start the kiosk server. Usage: uv run python scripts/run_kiosk.py [--offline] [--port 8765]"""

import argparse
import os

import uvicorn


def main() -> None:
    """CLI entry point."""
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--offline", action="store_true", help="no LLM")
    args = ap.parse_args()
    if args.offline:
        os.environ["RECEPTION_OFFLINE"] = "1"
    uvicorn.run("reception.server.main:app", host=args.host, port=args.port, log_level="info")


if __name__ == "__main__":
    main()
