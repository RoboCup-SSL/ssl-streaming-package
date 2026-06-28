# youtube

A thin **YouTube Data API v3** client for the SSL stream — auth, live broadcasts,
reusable ingestion streams, and thumbnails. **OBS-agnostic and schedule-format-agnostic**:
it only knows YouTube. Two consumers:

- **`youtube.schedule`** (this package's CLI) — pre-tournament batch-scheduling of every
  match from `obs_live_data/data/schedule.json`.
- **`obs-controller`** (runtime, MVP2 feature 2.1) — imports `YouTubeClient` to pull a
  field's stream key and feed OBS. *(not built yet)*

Keeping the API in one place means a single home for the OAuth/quota logic.

## Batch-schedule the tournament

```bash
# preview — no auth, no network
python -m youtube.schedule --dry-run

# create the broadcasts (opens a browser once, caches youtube_token.json)
python -m youtube.schedule            # --privacy public by default
```

What it does:
- Skips placeholder bracket slots (same rule as `generate_thumbnails.py`); ~30 real matches.
- Creates **one reusable RTMP stream per field** (A, B0, B1) and binds each broadcast to its
  field's stream — ~150 quota units/match, under the 10k/day cap.
- Sets each match's custom thumbnail from `obs_live_data/youtube_thumbnails/png/`.
- **Idempotent** — skips any slot whose `scheduledStartTime` already exists, so
  hand-scheduled matches are left alone and re-runs don't duplicate.

## Auth

Needs an OAuth 2.0 **Desktop app** client from the Google Cloud project that owns the
channel, with **YouTube Data API v3** enabled. Download it as `client_secret.json` in this
directory (override with `--client-secret`). First run opens a browser for consent and caches
a refresh token in `youtube_token.json`.

> `client_secret.json` and `youtube_token.json` are credentials — keep them out of git.

After scheduling, each field's RTMP key (`YouTubeClient.stream_key(<id>)` or YouTube Studio)
goes into that field's `obs-template` `service.json`.
