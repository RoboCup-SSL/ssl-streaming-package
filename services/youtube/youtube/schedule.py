"""Batch-schedule the tournament's YouTube livestreams from schedule.json.

    python -m youtube.schedule --dry-run      # print the plan, no API calls
    python -m youtube.schedule                # create the broadcasts

For every *real* match (placeholder bracket slots like "W1.A vs L1.B" are skipped,
same rule as obs_live_data/youtube_thumbnails/generate_thumbnails.py) it creates a
scheduled liveBroadcast with the matching custom thumbnail.

Field economy: the 3 fields (A, B0, B1) never overlap on their own field, so we
create ONE reusable ingestion stream per field and bind every broadcast to its
field's stream. ~150 quota units/match, well under the 10k/day cap, and each field
gets a stable RTMP key for its obs-template service.json.

Idempotent: existing broadcasts are fetched first and any match whose start time is
already taken is skipped — so hand-scheduled matches are left alone and re-runs
don't duplicate.
"""

import argparse
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .client import SCOPES, YouTubeClient, _to_utc_z  # noqa: F401  (SCOPES re-exported for callers)

HERE = Path(__file__).resolve().parent
_OBS_LIVE_DATA = HERE / ".." / ".." / "obs_live_data"

# RoboCup 2026 is in Incheon, KR. schedule.json times are local (KST = UTC+9).
KST = timezone(timedelta(hours=9))

# Reusable ingestion stream per field; matches on one field never overlap.
FIELDS = ["A", "B0", "B1"]


# --- schedule -> presentation helpers -------------------------------------
# These mirror generate_thumbnails.py so titles/thumbnail filenames line up
# exactly. Kept as a copy (not an import) because that module runs work at
# import time; keep the two in sync if its rules change.
def skip_match(team_a: str, team_b: str) -> bool:
    """True for bracket-placeholder slots that have no known teams yet."""
    return bool(
        "." in team_a
        or re.match(r"(L|W)(L|U)(\d|F)", team_a)
        or re.match(r"G\d\.\D", team_a)
    )


def day_label(label: str, first_day: str, day: str) -> str:
    """e.g. 'Day 1 - Group Phase' — same string generate_thumbnails.py uses."""
    n_days = (
        datetime.strptime(day, "%Y-%m-%d") - datetime.strptime(first_day, "%Y-%m-%d")
    ).days + 1
    if re.match(r"G\d", label):
        return f"Day {n_days} - Group Phase"
    return f"Day {n_days} - {label}"


def _start_datetime(match: dict) -> datetime:
    return datetime.strptime(
        f"{match['day']} {match['time']}", "%Y-%m-%d %H:%M"
    ).replace(tzinfo=KST)


def build_plan(schedule_path: Path, thumbs_dir: Path) -> list[dict]:
    """Real matches to schedule, sorted by start, with derived title/desc/thumbnail."""
    schedule = json.loads(schedule_path.read_text())["schedule"]
    first_day = schedule[0]["day"]
    plan = []
    for match in schedule:
        if skip_match(match["teamA"], match["teamB"]):
            continue
        phase = day_label(match["label"], first_day, match["day"])
        start = _start_datetime(match)
        plan.append(
            {
                "id": match["id"],
                "field": match["field"],
                "start": start,
                "title": (
                    f"RoboCup 2026 SSL — Division {match['division']}: "
                    f"{match['teamA']} vs {match['teamB']} ({phase})"
                ),
                "description": (
                    f"RoboCup 2026 Small Size League\n"
                    f"{phase} — Field {match['field']} (Division {match['division']})\n"
                    f"{match['teamA']} vs {match['teamB']}\n"
                    f"Scheduled start: {start.strftime('%Y-%m-%d %H:%M')} KST"
                ),
                # generate_thumbnails.py names files: f"{day}_{teamA}_vs_{teamB}.png"
                "thumbnail": thumbs_dir / f"{phase}_{match['teamA']}_vs_{match['teamB']}.png",
            }
        )
    plan.sort(key=lambda m: m["start"])
    return plan


def _field_stream_title(field: str) -> str:
    return f"SSL Field {field}"


def main() -> None:
    ap = argparse.ArgumentParser(description="Batch-schedule RoboCup YouTube livestreams.")
    ap.add_argument("--schedule", type=Path,
                    default=_OBS_LIVE_DATA / "data" / "schedule.json")
    ap.add_argument("--thumbnails", type=Path,
                    default=_OBS_LIVE_DATA / "youtube_thumbnails" / "png")
    ap.add_argument("--client-secret", type=Path, default=HERE / "client_secret.json")
    ap.add_argument("--token", type=Path, default=HERE / "youtube_token.json")
    ap.add_argument("--privacy", choices=["public", "unlisted", "private"], default="public")
    ap.add_argument("--dry-run", action="store_true", help="Print the plan; make no API calls.")
    args = ap.parse_args()

    plan = build_plan(args.schedule.resolve(), args.thumbnails.resolve())
    print(f"{len(plan)} real matches in schedule (placeholder slots skipped).\n")

    missing = [m for m in plan if not m["thumbnail"].exists()]
    if missing:
        print(f"[warn] {len(missing)} matches have no thumbnail yet "
              f"(run generate_thumbnails.py): they'll be scheduled without one.\n")

    if args.dry_run:
        print("Streams (one reusable RTMP key per field): " + ", ".join(FIELDS))
        for m in plan:
            thumb = "✓" if m["thumbnail"].exists() else "—"
            print(f"  [{m['field']}] {m['start'].strftime('%a %m-%d %H:%M')} KST  "
                  f"thumb:{thumb}  {m['title']}")
        print(f"\nDry run — nothing scheduled. Privacy would be: {args.privacy}")
        return

    yt = YouTubeClient.authenticate(args.client_secret.resolve(), args.token.resolve())

    print("Resolving field streams…")
    titles = {f: _field_stream_title(f) for f in FIELDS}
    existing = yt.reusable_streams_by_title(list(titles.values()))
    stream_ids = {}
    for f in FIELDS:
        if titles[f] in existing:
            stream_ids[f] = existing[titles[f]]
            print(f"  stream reuse: Field {f} -> {stream_ids[f]}")
        else:
            stream_ids[f] = yt.create_reusable_stream(titles[f])
            print(f"  stream create: Field {f} -> {stream_ids[f]}")

    print("\nFetching existing broadcasts (so already-scheduled slots are skipped)…")
    taken = yt.scheduled_start_times()

    created = skipped = 0
    for m in plan:
        start_iso = _to_utc_z(m["start"])
        if start_iso in taken:
            print(f"  skip (slot already scheduled): {m['title']}")
            skipped += 1
            continue
        bid = yt.create_broadcast(
            title=m["title"], description=m["description"],
            start=m["start"], privacy=args.privacy,
        )
        yt.bind(bid, stream_ids[m["field"]])
        if m["thumbnail"].exists():
            yt.set_thumbnail(bid, m["thumbnail"])
        taken.add(start_iso)  # guard against duplicate slots within this run too
        created += 1
        print(f"  created [{m['field']}]: {m['title']}  ({bid})")

    print(f"\nDone. {created} created, {skipped} skipped (already scheduled).")
    print("RTMP keys per field: yt.stream_key(<id>) or YouTube Studio — "
          "drop each into that field's obs-template service.json.")


if __name__ == "__main__":
    main()
