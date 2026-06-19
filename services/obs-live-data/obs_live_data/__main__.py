import asyncio
import os
import sys

import simpleobsws
from configuration.appconfig import FieldConfig
from data_access.config import GameControllerConfig
from data_access.gc import MulticastRefereeSource
from data_access.obs import ObsText
from data_processing.decode import decode_referee

from obs_live_data.app import effective_logos_dir, run_referee


def build_source(gc: GameControllerConfig) -> MulticastRefereeSource:
    return MulticastRefereeSource(gc, decode_referee)


async def main(config_path: str) -> None:
    config = FieldConfig.load_from_file(config_path)
    base_dir = os.path.dirname(os.path.abspath(config_path))
    ws = simpleobsws.WebSocketClient(url=config.obs.url, password=config.obs.password)
    await ws.connect()
    await ws.wait_until_identified()
    obs = ObsText(ws, text_field=config.obs.text_field)
    source = build_source(config.game_controller)
    await source.start()
    logos_dir = effective_logos_dir(config.obs.logos_dir, config.obs.stage_dir, base_dir)
    try:
        await run_referee(
            source, obs, config.obs.sources, config.obs.images, logos_dir
        )
    finally:
        await ws.disconnect()


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1] if len(sys.argv) > 1 else "field.toml"))
