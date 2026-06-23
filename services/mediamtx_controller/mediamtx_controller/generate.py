from mediamtx_controller.paths import path_config

CAMERA_NAMES = ["commentator", "field-1", "field-2", "field-3", "field-4"]


def build_config(cameras: dict[str, str], rtsp_port: int = 8554) -> dict:
    """Build a MediaMTX config with the fixed set of named paths. Declared cameras
    get their source; the rest are blank publisher paths (black until something
    feeds them). An unknown camera name is a config error."""
    unknown = set(cameras) - set(CAMERA_NAMES)
    if unknown:
        raise ValueError(f"unknown camera names: {sorted(unknown)}; allowed: {CAMERA_NAMES}")
    paths = {
        name: path_config(name, cameras[name], rtsp_port) if name in cameras else {}
        for name in CAMERA_NAMES
    }
    # "warn" drops MediaMTX's per-listener/per-session INFO chatter off the console
    # while keeping genuine warnings/errors (and a failed start) visible.
    # RTSP is how OBS pulls and ffmpeg publishes. WebRTC stays on for a zero-setup
    # browser preview (http://<host>:8889/<camera>) to check a camera is live. The
    # rest are off: fewer open ports, and no MoQ self-signed cert written to cwd.
    return {
        "logLevel": "warn",
        "webrtc": True,
        "rtmp": False,
        "hls": False,
        "srt": False,
        "moq": False,
        "paths": paths,
    }
