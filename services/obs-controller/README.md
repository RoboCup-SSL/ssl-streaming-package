# controller

Python program that **drives OBS over the websocket interface** for the unattended-fallback
mode (MVP2). Runs alongside OBS on the streaming PC, listens to SSL protobuf (via
[`ssl-protobuf-listener`](../ssl-protobuf-listener/)), reads a schedule file, and automates the stream when no operator
is available.

Planned scope (README features):
- **2.1** auto start/stop the livestream per match (per-match YouTube key, schedule + Game
  Controller driven) — *first in line*
- **2.3** auto scene switching (live / halftime / post-match)
- **2.4** (later) digital ball-zoom

## Status

**Not built yet.** Scaffold only — MVP2. MVP1 keeps the operator fully manual (assisted by the
polished OBS template and the `obs-live-data` text feed).
