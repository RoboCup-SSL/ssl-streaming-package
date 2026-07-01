"""Show each match's RTMP ingestion stream key.

    python -m youtube.keys            # table: key + match title
    python -m youtube.keys --json     # raw rows for scripting

youtube.schedule titles each match's stream "SSL <match-id>", so this maps every
stream back to its match (via schedule.json) and prints the key OBS needs. The keys
are the same ones in stream_keys.json — this is just a live read from YouTube.

Keys are secrets: don't paste the output anywhere public.
"""

import argparse
import json
from pathlib import Path

from . import config
from .client import YouTubeClient
from .schedule import build_plan


def main() -> None:
    ap = argparse.ArgumentParser(description="Show per-match RTMP stream keys.")
    ap.add_argument("--config", type=Path, default=None,
                    help="Path to youtube.toml (default: repo-root youtube.toml).")
    ap.add_argument("--json", action="store_true", help="Print raw JSON instead of a table.")
    args = ap.parse_args()

    cfg = config.load(args.config)
    titles = {m["id"]: m["title"] for m in build_plan(cfg)}  # match_id -> friendly title
    yt = YouTubeClient.authenticate(cfg.client_secret, cfg.token)

    rows = []
    for s in yt.list_streams():
        mid = s["title"][4:] if s["title"].startswith("SSL ") else None
        rows.append({
            "match_id": mid,
            "match_title": titles.get(mid, ""),
            "stream_title": s["title"],
            "key": s["key"],
            "stream_id": s["id"],
        })
    # SSL-<match-id> streams first, ordered by id; anything else after
    rows.sort(key=lambda r: (r["match_id"] is None, r["match_id"] or r["stream_title"]))

    if args.json:
        print(json.dumps(rows, indent=2))
        return

    print(f"{len(rows)} stream(s):\n")
    for r in rows:
        label = r["match_title"] or r["stream_title"]
        print(f"  {r['key']:<26} {label}")


if __name__ == "__main__":
    main()
