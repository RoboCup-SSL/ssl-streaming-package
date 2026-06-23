"""Replay a real SSL gamelog through OBS over obs-websocket — the real-data sibling
of demo.py (which plays a hand-scripted match).

Usage:
    uv run python -m obs_live_data.demo_gamelog <gamelog.log[.gz]> [field.toml] [speed]

`speed` is a playback multiplier (default 1.0 = real time; e.g. 5 plays 5x faster).
Name your OBS sources per obs-template/README.md to see the fields populate.
"""
import asyncio
import os
import sys

import simpleobsws
from configuration.appconfig import FieldConfig
from data_access.gamelog import GamelogRefereeSource
from data_access.obs import ObsText
from data_processing.decode import decode_referee

from obs_live_data.app import effective_logos_dir, run_referee
from obs_live_data.connect import connect_obs_or_exit


async def main(gamelog_path: str, config_path: str, speed: float) -> None:
    config = FieldConfig.load_from_file(config_path)
    ws = simpleobsws.WebSocketClient(url=config.obs.url, password=config.obs.password)
    client = await connect_obs_or_exit(ws, config.obs.url)
    print(f"Connected to OBS at {config.obs.url}. "
          f"Replaying {os.path.basename(gamelog_path)} at {speed}x (Ctrl-C to stop).")
    obs = ObsText(client, text_field=config.obs.text_field)
    base_dir = os.path.dirname(os.path.abspath(config_path))
    logos_dir = effective_logos_dir(config.obs.logos_dir, config.obs.stage_dir, base_dir)
    source = GamelogRefereeSource(gamelog_path, decode_referee, speed=speed)
    try:
        await run_referee(source, obs, logos_dir)
    finally:
        await ws.disconnect()
    print("Done.")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: python -m obs_live_data.demo_gamelog "
              "<gamelog.log[.gz]> [field.toml] [speed]")
        sys.exit(2)
    gamelog = sys.argv[1]
    config = sys.argv[2] if len(sys.argv) > 2 else "field.toml"
    playback_speed = float(sys.argv[3]) if len(sys.argv) > 3 else 1.0
    try:
        asyncio.run(main(gamelog, config, playback_speed))
    except KeyboardInterrupt:
        print("\nStopped.")
