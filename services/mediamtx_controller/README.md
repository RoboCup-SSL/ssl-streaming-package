# mediamtx-controller

Generates a [MediaMTX](https://github.com/bluenviron/mediamtx) config from a field's
`[cameras]` block, so every field exposes the **same fixed set of named camera endpoints**
regardless of what physical cameras it has. The shared OBS scene collection references those
stable names, so all three fields' OBS instances are byte-identical (copy-paste).

## The camera-name contract

Fixed endpoints, identical on every field:

- `commentator` — the commentator webcam
- `field-1`, `field-2`, `field-3`, `field-4` — field cameras

A field declares only the ones it actually has; the rest are defined but black until fed. OBS
references them as `rtsp://localhost:8554/commentator`, `rtsp://localhost:8554/field-1`, ….

## Declare cameras (in `field.toml`)

```toml
[cameras]
commentator = "usb:/dev/video0"
field-1     = "rtsp://10.0.0.5:554/stream"
field-2     = "ts:udp://@:1234"
# field-3, field-4 omitted -> black
```

Source descriptors:
- `rtsp://…` (also rtsps/rtmp/srt/http/https) — MediaMTX pulls it directly.
- `usb:<device>` (e.g. `usb:/dev/video0`) — MediaMTX runs ffmpeg (v4l2) to publish it.
- `ts:<url>` (e.g. `ts:udp://@:1234`) — MediaMTX runs ffmpeg to publish an MPEG-TS stream.

For usb/ts, ffmpeg runs **under MediaMTX** (`runOnInit`), so MediaMTX owns the child process —
no separate process management.

## Generate and run

```bash
uv run python -m mediamtx_controller field.toml mediamtx.yml
mediamtx mediamtx.yml      # install MediaMTX separately (binary or Docker)
```

MediaMTX runs on the same field PC as OBS (the streaming PC), so the `rtsp://localhost:8554/…`
URLs resolve locally. Per-field difference is only the `[cameras]` block.
