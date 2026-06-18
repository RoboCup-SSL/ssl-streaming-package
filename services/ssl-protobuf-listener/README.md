# ssl-feed

Shared Python library for consuming **SSL protobuf feeds** — Game Controller, AutoRef, and
vision software. Parses the raw protobuf messages into clean Python objects (match phase,
team names, score, robot/ball positions, field geometry) for downstream programs to use.

It is a **library, not a runnable program** — imported by `obs-live-data` and `obs-controller`. This
keeps a single source of truth for protobuf parsing instead of duplicating it per service.

## Status

**Not built yet.** Scaffold only. This earns its keep once `obs-controller` (MVP2) exists and
`obs-live-data` starts pulling live scores from the Game Controller rather than a manual schedule
file. Until then, no code lives here — built when the second consumer appears.
