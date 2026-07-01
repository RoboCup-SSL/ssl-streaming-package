# youtube

A thin **YouTube Data API v3** client for the SSL stream — auth, live broadcasts,
reusable ingestion streams, and thumbnails. **OBS-agnostic and schedule-format-agnostic**:
it only knows YouTube. Two consumers:

- **`youtube.schedule`** (this package's CLI) — pre-tournament batch-scheduling of every
  match from `obs_live_data/data/schedule.json`.
- **`obs-controller`** (runtime, MVP2 feature 2.1) — imports `YouTubeClient` to pull a
  field's stream key and feed OBS. *(not built yet)*

Keeping the API in one place means a single home for the OAuth/quota logic.

## Config — one file per event

Everything event-specific lives in **`youtube.toml`** at the repo root (like `field.toml`):
title/description templates, tags, category, playlist, privacy, `auto_start`/`auto_stop`, and
the paths to `schedule.json`, the thumbnails, and the OAuth files. Copy the template and edit:

```bash
cp youtube.toml.example youtube.toml     # in the repo root
```

Description/title templates take per-match placeholders: `{division} {field} {teamA} {teamB}
{phase} {day} {time}`. Nothing is hardcoded in the code — change the event by editing the TOML.

## Commands

```bash
# preview the plan — no auth, no network
python -m youtube.schedule --dry-run

# create the broadcasts (per-match [y/n] prompt; -y to skip prompts)
python -m youtube.schedule

# list what's already scheduled (read-only) — confirm the above, or hand-scheduled ones
python -m youtube.list                # table sorted by start; --json for raw items

# show each match's RTMP stream key (for loading into OBS)
python -m youtube.keys                # key + match title; --json for raw rows

# log in / confirm you're on the right channel (no scheduling)
python -m youtube.auth                # prints the authenticated channel name
```

All three accept `--config <path>` (default: repo-root `youtube.toml`).

What `schedule` does:
- Skips placeholder bracket slots (same rule as `generate_thumbnails.py`); ~30 real matches.
- Creates a **dedicated RTMP stream (key) per match** and binds each broadcast to its own —
  so one key maps to exactly one match, no ambiguity about which goes live.
- Sets title, description, tags, category, custom thumbnail, and adds each video to the playlist.
- Writes a `match_id → key` map to **`stream_keys.json`** (gitignored — keys are secrets) for
  the future script that injects each match's key into OBS.
- **Idempotent** — skips a match if a broadcast with the same start time *and* both team names
  already exists, so hand-scheduled matches are left alone and re-runs don't duplicate.

### Going live (operator model)

`auto_start = true`, `auto_stop = false`: an operator hits **Start Streaming** in OBS (with that
match's key loaded) and the broadcast goes live; a network blip can't end it. Matches are ended
**deliberately** — eventually via OBS Stop (the planned controller turns a *deliberate* stop into
a YouTube "complete"), or right now via YouTube Studio's **End stream**. One key carries exactly
one match, so there's never a question of which broadcast a key feeds.

## Auth (one-time setup)

Write operations need **OAuth 2.0** (an API key is not enough). Set it up once in the Google
Cloud project that owns the channel:

1. **Google Cloud Console → APIs & Services → Library** → enable **YouTube Data API v3**.
2. **OAuth consent screen** → User type **External**, fill the app name/contact, and add your
   Google account under **Test users** (so you can use it while the app is unpublished).
3. **Credentials → Create credentials → OAuth client ID → Application type: Desktop app**.
4. **Download JSON** and save it at the path `youtube.toml`'s `[auth] client_secret` points to
   (default `services/youtube/client_secret.json`).

Then `python -m youtube.auth` opens a browser for consent, caches a refresh token (default
`services/youtube/youtube_token.json`), and prints the channel it authorized — check it's the
right one before scheduling. `schedule`/`list` reuse that cached token (re-running `auth` is
just a verify).

> `client_secret.json` and `youtube_token.json` are credentials — already gitignored; never commit them.

After scheduling, the per-match RTMP keys are in `stream_keys.json` (and YouTube Studio). The
right match's key gets loaded into OBS at match time — for now by hand into `service.json`,
later by a small obs-websocket script driven by the schedule.
