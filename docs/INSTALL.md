# Install & run (deployer guide)

How to get the whole package running on a streaming PC. Audience: whoever sets up a field
(Linux/programmer-literate). Target: Ubuntu 24+. Windows is a nice-to-have, not required.

> **Status: stub.** Filled in as each component lands. Installs are run manually by the
> operator/deployer.

## Components

| Component | What it is | Runtime |
|---|---|---|
| [`graphics/`](../graphics/) | Renders the broadcast graphics (stingers, overlays, standby) | Node + Remotion |
| [`obs-template/`](../obs-template/) | OBS scene collection to import | OBS |
| [`services/obs-live-data/`](../services/obs-live-data/) | Serves live match text to OBS (2.2) | Python (Flask) |
| [`services/obs-controller/`](../services/obs-controller/) | (MVP2) automates OBS | Python |
| [`services/ssl-protobuf-listener/`](../services/ssl-protobuf-listener/) | (MVP2) shared SSL protobuf library | Python lib |

## Rough order (to be detailed)

1. Install OBS + Node + Python.
2. Render / fetch the graphics from `graphics/`.
3. Import the `obs-template/` scene collection into OBS; point it at the rendered graphics.
4. Configure and run `services/obs-live-data/` (`cp field.toml.example field.toml`, edit, then
   `uv run python -m obs_live_data field.toml`); it pushes live text to OBS over obs-websocket.
5. (MVP2) Run `services/obs-controller/` for unattended operation.

For *operating* a match once installed, see the [operator handbook](handbook/).
