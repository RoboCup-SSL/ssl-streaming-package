"""Batch-schedule the tournament's YouTube livestreams from schedule.json.

    python -m youtube.schedule --dry-run      # print the plan, no API calls
    python -m youtube.schedule                # create the broadcasts

All event settings (title/description templates, tags, playlist, streams, paths,
credentials) come from youtube.toml — see youtube.toml.example. Nothing here is
hardcoded per event.

For every *real* match (placeholder bracket slots like "W1.A vs L1.B" are skipped,
same rule as obs_live_data/youtube_thumbnails/generate_thumbnails.py) it creates a
scheduled liveBroadcast with the matching custom thumbnail.

One key per match: each broadcast gets its own dedicated RTMP stream (key), so the
key↔match mapping is unambiguous — OBS pushes a match's key and that match goes live
(enableAutoStart). The match_id -> key map is written to stream_keys.json for the
(future) script that injects the right key into OBS per match. With auto_stop off, a
dropped feed never ends a match; end it deliberately (OBS Stop via the controller, or
Studio).

Idempotent: existing broadcasts are fetched first and a match is skipped if one with
the same start time AND both team names already exists — so hand-scheduled matches
are left alone and re-runs don't duplicate.
"""

import argparse
import json
import re
from datetime import datetime
from pathlib import Path

from . import config
from .client import YouTubeClient, _to_utc_z

# match_id -> key map for the OBS key-injection script; next to the package (gitignored).
KEY_MAP_PATH = config.REPO_ROOT / "services" / "youtube" / "stream_keys.json"


# --- schedule -> presentation helpers -------------------------------------
# skip_match / day_label mirror generate_thumbnails.py so titles and thumbnail
# filenames line up exactly. Kept as a copy (that module runs work at import time);
# keep the two in sync if its rules change.
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


def build_plan(cfg: config.YoutubeConfig) -> list[dict]:
    """Real matches to schedule, sorted by start, with derived title/desc/thumbnail."""
    schedule = json.loads(cfg.schedule_path.read_text())["schedule"]
    first_day = schedule[0]["day"]
    plan = []
    for match in schedule:
        if skip_match(match["teamA"], match["teamB"]):
            continue
        phase = day_label(match["label"], first_day, match["day"])
        start = datetime.strptime(
            f"{match['day']} {match['time']}", "%Y-%m-%d %H:%M"
        ).replace(tzinfo=cfg.tz)
        fields = {
            "division": match["division"], "field": match["field"],
            "teamA": match["teamA"], "teamB": match["teamB"],
            "phase": phase, "day": match["day"], "time": match["time"],
        }
        description = cfg.description_header.format(**fields)
        if cfg.description_body.strip():
            description += f"\n\n{cfg.description_body.strip()}"
        plan.append(
            {
                "id": match["id"],
                "field": match["field"],
                "teamA": match["teamA"],
                "teamB": match["teamB"],
                "start": start,
                "title": cfg.title.format(**fields),
                "description": description,
                # generate_thumbnails.py names files: f"{day}_{teamA}_vs_{teamB}.png"
                "thumbnail": cfg.thumbnails_dir / f"{phase}_{match['teamA']}_vs_{match['teamB']}.png",
            }
        )
    plan.sort(key=lambda m: m["start"])
    return plan


def _confirm(prompt: str) -> bool:
    while True:
        ans = input(prompt).strip().lower()
        if ans in ("y", "yes"):
            return True
        if ans in ("n", "no"):
            return False
        print("    please answer y or n")


def _already_scheduled(match: dict, existing: list[dict]) -> dict | None:
    """An existing broadcast for this match, or None.

    Matched by same start time AND both team names appearing in the title
    (case-insensitive). Start time alone is NOT unique — fields run matches in
    parallel — so we also require the teams, which also tolerates hand-typed title
    variants (e.g. 'luhbots' vs 'LUHBots')."""
    start_iso = _to_utc_z(match["start"])
    a, b = match["teamA"].lower(), match["teamB"].lower()
    for bc in existing:
        title = bc["title"].lower()
        if bc["start"] == start_iso and a in title and b in title:
            return bc
    return None


def main() -> None:
    ap = argparse.ArgumentParser(description="Batch-schedule RoboCup YouTube livestreams.")
    ap.add_argument("--config", type=Path, default=None,
                    help="Path to youtube.toml (default: repo-root youtube.toml).")
    ap.add_argument("--dry-run", action="store_true", help="Print the plan; make no API calls.")
    ap.add_argument("-y", "--yes", action="store_true",
                    help="Skip the per-match [y/n] prompt and schedule all of them.")
    args = ap.parse_args()

    cfg = config.load(args.config)
    plan = build_plan(cfg)
    print(f"{len(plan)} real matches in schedule (placeholder slots skipped).\n")

    missing = [m for m in plan if not m["thumbnail"].exists()]
    if missing:
        print(f"[warn] {len(missing)} matches have no thumbnail yet "
              f"(run generate_thumbnails.py): they'll be scheduled without one.\n")

    if args.dry_run:
        print("Streams: a dedicated RTMP key per match (1 key ↔ 1 match).")
        print(f"auto_start={cfg.auto_start}  auto_stop={cfg.auto_stop}  "
              f"(OBS Start = go live; ending is deliberate when auto_stop is off)")
        print("Tags on every video: " + ", ".join(cfg.tags))
        if cfg.playlist:
            print(f"Playlist: each video added to '{cfg.playlist}'")
        for m in plan:
            thumb = "✓" if m["thumbnail"].exists() else "—"
            print(f"  [{m['field']}] {m['start'].strftime('%a %m-%d %H:%M')}  "
                  f"thumb:{thumb}  {m['title']}")
        print(f"\nDry run — nothing scheduled. Privacy would be: {cfg.privacy}")
        return

    yt = YouTubeClient.authenticate(cfg.client_secret, cfg.token)

    playlist_id = None
    if cfg.playlist:
        # Accept a raw PL… id directly; otherwise look it up by title.
        playlist_id = cfg.playlist if cfg.playlist.startswith("PL") \
            else yt.find_playlist_id(cfg.playlist)
        if playlist_id:
            print(f"Playlist: adding each video to '{cfg.playlist}' ({playlist_id})")
        else:
            print(f"[warn] playlist '{cfg.playlist}' not found — videos won't be "
                  f"added to a playlist. Create it first or set playlist = \"\".")

    print("Fetching existing broadcasts and streams…")
    existing_broadcasts = yt.list_broadcasts()
    # reuse a match's stream by its stable title across re-runs (avoids duplicates)
    streams_by_title = {s["title"]: s for s in yt.list_streams()}

    key_map = {}  # match_id -> {title, field, start, broadcast_id, stream_id, key}
    created = already = declined = 0
    for m in plan:
        dup = _already_scheduled(m, existing_broadcasts)
        if dup:
            print(f"\n  skip (already scheduled as '{dup['title']}'): {m['title']}")
            already += 1
            continue

        thumb = m["thumbnail"]
        thumb_str = thumb.name if thumb.exists() else f"MISSING ({thumb.name})"
        print()
        print(f"  Title: {m['title']}")
        print(f"  When:  {m['start'].strftime('%a %Y-%m-%d %H:%M %Z')}   [Field {m['field']}]")
        print(f"  Thumb: {thumb_str}")
        if not args.yes and not _confirm("  Schedule this one? [y/n] "):
            print("  → skipped by you")
            declined += 1
            continue

        # dedicated stream for this match (stable title so re-runs reuse, not duplicate)
        stream_title = f"SSL {m['id']}"
        stream = streams_by_title.get(stream_title) or yt.create_stream(stream_title)
        streams_by_title[stream_title] = stream

        bid = yt.create_broadcast(
            title=m["title"], description=m["description"],
            start=m["start"], privacy=cfg.privacy,
            auto_start=cfg.auto_start, auto_stop=cfg.auto_stop,
        )
        yt.bind(bid, stream["id"])
        yt.set_video_metadata(bid, title=m["title"], description=m["description"],
                              tags=cfg.tags, category_id=cfg.category_id)
        if m["thumbnail"].exists():
            yt.set_thumbnail(bid, m["thumbnail"])
        if playlist_id:
            yt.add_to_playlist(playlist_id, bid)
        key_map[m["id"]] = {
            "title": m["title"], "field": m["field"], "start": _to_utc_z(m["start"]),
            "broadcast_id": bid, "stream_id": stream["id"], "key": stream["key"],
        }
        # track it so a duplicate match within this same run is also caught
        existing_broadcasts.append(
            {"id": bid, "title": m["title"], "start": _to_utc_z(m["start"])}
        )
        created += 1
        print(f"  → created ({bid})")

    if key_map:
        KEY_MAP_PATH.write_text(json.dumps(key_map, indent=2))
        print(f"\nWrote {len(key_map)} match→key mappings to {KEY_MAP_PATH}")
    print(f"\nDone. {created} created, {already} already scheduled, {declined} declined.")
    if already:
        print("Note: already-scheduled matches are NOT in stream_keys.json (their keys "
              "weren't created here). Delete + reschedule them to capture their keys.")


if __name__ == "__main__":
    main()
