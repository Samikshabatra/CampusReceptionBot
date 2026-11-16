"""Terminal chat with the assistant (typed input)."""

import argparse
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from reception.app_factory import build_assistant
from reception.nlu.context import SessionContext


def main() -> None:
    """Run an interactive text session. Type 'quit' to exit, 'new' for a new visitor."""
    ap = argparse.ArgumentParser(description=main.__doc__)
    ap.add_argument("--config", type=Path, default=Path("configs/app.yaml"))
    ap.add_argument("--offline", action="store_true", help="no LLM")
    args = ap.parse_args()
    print("Loading knowledge base and models...")
    assistant = build_assistant(args.config, offline=args.offline)
    tz = ZoneInfo(assistant.cfg.timezone)
    ctx = SessionContext()
    print("Ready. Type a question ('new' = new visitor, 'quit' = exit).")
    while True:
        try:
            text = input("\nvisitor> ")
        except (EOFError, KeyboardInterrupt):
            break
        if text.strip().lower() in ("quit", "exit"):
            break
        if text.strip().lower() == "new":
            ctx = SessionContext()
            print("(new session)")
            continue
        r = assistant.handle(text, ctx, datetime.now(tz))
        print(f"kiosk> {r.speech}")
        print(f"  [{r.intent} {r.confidence:.2f}] card={r.card.kind}", end="")
        if r.handover_reason:
            print(f" handover={r.handover_reason}", end="")
        print()
        if r.card.kind == "map":
            for step in r.card.data.get("steps", []):
                print(f"   - {step}")
        if r.card.kind == "clarify":
            print("   options:", ", ".join(r.card.data.get("options", [])))
        for link in r.links:
            print(f"   link: {link.label} -> {link.url}")
        if r.sources:
            print("   sources:", ", ".join(r.sources))
        if ctx.ended:
            print("(session ended)")
            ctx = SessionContext()


if __name__ == "__main__":
    main()
