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
    return {"paths": paths}
