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
| [`services/obs_live_data/`](../services/obs_live_data/) | Pushes live match text + logos to OBS (2.2) | Python |
| [`services/mediamtx_controller/`](../services/mediamtx_controller/) | Generates the MediaMTX config from `[cameras]` | Python |
| [`services/obs-controller/`](../services/obs-controller/) | (MVP2) automates OBS | Python |
| [`services/ssl-protobuf-listener/`](../services/ssl-protobuf-listener/) | (MVP2) shared SSL protobuf library | Python lib |

## The happy path

```bash
./setup.sh                            # uv + Python deps + MediaMTX binary; reports missing prereqs
cp field.toml.example field.toml      # edit per field (root of the repo)
./run.sh                              # validate config, start MediaMTX + obs-live-data
```

`./run.sh` generates `mediamtx.yml` from `field.toml`'s `[cameras]`, starts MediaMTX (which
ingests the cameras) and `obs-live-data` (which pushes score/stage/team text + logos to OBS),
and tears both down on `Ctrl-C`. Replicate to another field by copying the repo and editing
only `[cameras]`.

Still manual (by design): install OBS 28+ (with obs-websocket), **import the
`obs-template/` scene collection** and launch OBS, and render/fetch the `graphics/` overlays.

For *operating* a match once installed, see the [operator handbook](handbook/).
