# obs-live-data

The per-field app that pushes live match text into OBS — team names, score, and match stage
from the Game Controller, plus next-up / countdown from the schedule — with no manual typing.

**One instance per field.** It is event-driven: it listens to the GC `Referee` multicast feed
and pushes updates to OBS over **obs-websocket** (`simpleobsws`) the moment they change. No HTTP
server, no `obs-urlsource` plugin, no polling.

## Run

```bash
cp field.toml.example field.toml          # then edit: OBS url/password, source names, GC address
uv run python import_schedule.py          # (re)build data/schedule.json from data/schedule.md
uv run python -m obs_live_data field.toml
```

`field.toml` is the single per-field config (see `field.toml.example`): `[field].name`,
`[game_controller]` multicast address/port, `[obs]` url/password + the `[obs.sources]`
name-map (which OBS text source shows each value), and `[schedule].path`.

## OBS setup per field

In OBS (28+, obs-websocket enabled): create one **Text** source per value you want shown
(score, stage, team names, next-up, countdown) and put each source's name in `[obs.sources]`.
The app sets each source's text as updates arrive. On Linux the FreeType2 text source's
setting key is `text` (the default `text_field`).

For team logos, create an **Image** source per team and map them in `[obs.images]`
(`blue_logo`, `yellow_logo`). On each update the app sets that source's `file` to the logo
matching the team name. **The path resolves on the OBS machine** — so when OBS and this app
run on separate boxes, the logo folder must exist at the same path on the OBS box; co-located
is the simple case.

### Remote-OBS testing (`stage_dir`)

When OBS runs on a different machine, set `stage_dir` (e.g. `/tmp/ssl-logos`) in `[obs]`. On
startup the app copies the bundled logos there and sends paths from it. Mirror the same folder
on the OBS machine (copy `logos/` into `/tmp/ssl-logos` there) so the absolute paths line up.
Leave `stage_dir` empty for co-located deploys.

### Team logos

Bundled in [`logos/`](logos/) (see [`logos/SOURCE.md`](logos/SOURCE.md)) — sourced from the
[ssl-status-board](https://github.com/RoboCup-SSL/ssl-status-board) project. A team's logo is
its GC name lowercased with spaces→hyphens (`tigers-mannheim.png`); unknown teams fall back to
`no-logo.png`.

## Driving the schedule during the stream

Edit `data/schedule.json` → `live.<field>.currentId` to the id of the match now on that field;
save. The reader serves the last good copy if it catches a mid-edit save. Optional per-field
overrides: `nextId` (force which match is "next") and `nextStartsAt` (explicit ISO countdown
target when running late).

## Tests

```bash
uv run pytest        # from the services/ workspace root
```

No real OBS or network is needed: a `FakeRefereeSource` drives the loop and a recording stub
stands in for OBS.
