import sys

import yaml

from mediamtx_controller.cameras import load_cameras
from mediamtx_controller.generate import build_config


def main(config_path: str, out_path: str) -> None:
    cameras = load_cameras(config_path)
    config = build_config(cameras)
    with open(out_path, "w") as fh:
        fh.write(yaml.safe_dump(config, sort_keys=False))
    print(f"Wrote {out_path} ({len(config['paths'])} paths). Run: mediamtx {out_path}")


if __name__ == "__main__":
    config_path = sys.argv[1] if len(sys.argv) > 1 else "field.toml"
    out_path = sys.argv[2] if len(sys.argv) > 2 else "mediamtx.yml"
    main(config_path, out_path)
