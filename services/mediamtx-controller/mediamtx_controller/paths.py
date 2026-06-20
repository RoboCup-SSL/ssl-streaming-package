"""Map a camera source descriptor to a MediaMTX path config.

Descriptors:
- "rtsp://..." (also rtsps/rtmp/srt/http/https) -> MediaMTX pulls it directly.
- "usb:<device>"  -> MediaMTX runs ffmpeg (v4l2) to publish the device into the path.
- "ts:<url>"      -> MediaMTX runs ffmpeg to publish an MPEG-TS stream into the path.

For usb/ts, ffmpeg runs under MediaMTX (runOnInit) so MediaMTX owns the child process.
"""

_PULL_SCHEMES = ("rtsp://", "rtsps://", "rtmp://", "rtmps://", "srt://", "http://", "https://")


# Keep the console readable: no banner, no rewriting "frame= fps=" progress line,
# no stdin handling, and only fatal errors. At "fatal" the SIGINT-teardown
# broken-pipe/muxing spew is suppressed, but a camera that can't be opened still
# reports. Bump a child to "-loglevel warning" temporarily to debug one camera.
_QUIET = "-hide_banner -loglevel fatal -nostdin -nostats"


def _ffmpeg(input_args: str, name: str, rtsp_port: int) -> dict:
    target = f"rtsp://localhost:{rtsp_port}/{name}"
    cmd = (
        f"ffmpeg {_QUIET} {input_args} "
        f"-c:v libx264 -preset ultrafast -tune zerolatency "
        f"-f rtsp {target}"
    )
    return {"runOnInit": cmd, "runOnInitRestart": True}


def path_config(name: str, descriptor: str, rtsp_port: int = 8554) -> dict:
    if descriptor.startswith(_PULL_SCHEMES):
        return {"source": descriptor}
    if descriptor.startswith("usb:"):
        device = descriptor[len("usb:"):]
        return _ffmpeg(f"-f v4l2 -i {device}", name, rtsp_port)
    if descriptor.startswith("ts:"):
        url = descriptor[len("ts:"):]
        return _ffmpeg(f"-i {url}", name, rtsp_port)
    raise ValueError(f"unknown camera source descriptor: {descriptor!r}")
