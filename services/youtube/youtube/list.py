"""List the livestreams already scheduled on the channel.

    python -m youtube.list                 # table, sorted by start time
    python -m youtube.list --json          # raw items for scripting

Read-only: authenticates (credentials from youtube.toml), fetches every broadcast,
prints them. Handy to confirm what `youtube.schedule` created (or what was scheduled
by hand).
"""

import argparse
import json
from datetime import datetime
from pathlib import Path

from . import config
from .client import YouTubeClient


def _fmt_start(rfc3339: str | None, tz) -> str:
    if not rfc3339:
        return "(no start time)"
    dt = datetime.fromisoformat(rfc3339.replace("Z", "+00:00")).astimezone(tz)
    return dt.strftime("%a %m-%d %H:%M %Z")


def main() -> None:
    ap = argparse.ArgumentParser(description="List scheduled YouTube broadcasts.")
    ap.add_argument("--config", type=Path, default=None,
                    help="Path to youtube.toml (default: repo-root youtube.toml).")
    ap.add_argument("--json", action="store_true", help="Print raw JSON instead of a table.")
    args = ap.parse_args()

    cfg = config.load(args.config)
    yt = YouTubeClient.authenticate(cfg.client_secret, cfg.token)
    broadcasts = yt.list_broadcasts()
    broadcasts.sort(key=lambda b: b["start"] or "")

    if args.json:
        print(json.dumps(broadcasts, indent=2))
        return

    print(f"{len(broadcasts)} broadcast(s) on the channel:\n")
    for b in broadcasts:
        print(f"  {_fmt_start(b['start'], cfg.tz)}  {b['status']:<9} {b['privacy']:<8} "
              f"{b['title']}  ({b['id']})")


if __name__ == "__main__":
    main()
