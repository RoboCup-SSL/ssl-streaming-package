# Live match data server

Serves per-field "now / next / countdown" JSON for the RoboCup 2026 SSL broadcast.
OBS pulls it with the **obs-urlsource** plugin and renders it as native text. You drive
it by editing one file — no clock guessing, no scene automation.

## Run (on ONE machine — the others reach it over the LAN)

```bash
pip install -r requirements.txt
python import_schedule.py                # (re)build data/schedule.json from data/schedule.md
PORT=8000 python app.py                  # binds 0.0.0.0:8000
```

Endpoints: `GET /field/A`, `/field/B0`, `/field/B1`, `/health`.

## Driving it during the stream

Edit `data/schedule.json` → `live.<field>.currentId` to the id of the match now on that
field; save. The server hot-reloads on save (no restart). Optional per-field overrides:
- `nextId` — force which match counts as "next".
- `nextStartsAt` — explicit ISO time for the countdown (e.g. `"2026-07-02T10:15"`) when a
  match is running late.

Divisions: Field A = Division A; Fields B0 + B1 = Division B. Group labels and playoff
codes repeat across divisions — that's expected; matches are keyed by field.

## Per-PC OBS setup checklist (for distributing the scene collection)

The Scene Collection export carries the urlsource URLs, text styling, and image/media
sources, but each target PC must have:

1. **obs-urlsource plugin installed** (https://github.com/royshil/obs-urlsource) — the
   collection references it; without it those text sources show as missing.
2. **Asset files at the SAME absolute path** on every PC (OBS stores absolute paths):
   keep `next-match.png`, `breathing-background.mp4`, `standby.mp4` in an identical folder
   (e.g. `C:\robocup\assets\`). Install the **brand font** on every PC or text falls back.
3. The urlsource URLs point at the **server's fixed LAN IP/hostname**, NOT `localhost`
   (e.g. `http://192.168.1.50:8000/field/A`) — so every PC pulls from the one shared file.

### Wiring one field's text in OBS

Add an **obs-urlsource** source → URL `http://<server>:8000/field/A` → refresh every
1–2 s → output type **Text**, extract a JSON pointer (e.g. `now.matchup`, `next.matchup`,
or `countdown`) → style with the brand font. Repeat per field / per string you want; place
over the `NextMatch` slot / lower-third. The plugin's output template can also combine
fields, e.g. `NEXT: {next.matchup} — {countdown}`.
