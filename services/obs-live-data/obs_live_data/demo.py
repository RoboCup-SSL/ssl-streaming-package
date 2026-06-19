"""Manual smoke test: play a scripted match through a real OBS over obs-websocket.

No Game Controller needed — a FakeRefereeSource drives the same push path the live
app uses. Run: uv run python -m obs_live_data.demo field.toml
"""
import asyncio
import os
import sys

import simpleobsws
from configuration.appconfig import FieldConfig
from data_access.fake import FakeRefereeSource
from data_access.obs import ObsText
from data_structures.domain import MatchState, Team
from data_structures.enums import Command, Stage

from obs_live_data.app import effective_logos_dir, run_referee


def _state(stage: Stage, blue: int, yellow: int, command: Command) -> MatchState:
    return MatchState(stage, command, Team("ER-Force", blue, 0), Team("TIGERs", yellow, 0))


# (delay seconds before this state, state)
SCRIPT = [
    (0.0, _state(Stage.NORMAL_FIRST_HALF_PRE, 0, 0, Command.HALT)),
    (3.0, _state(Stage.NORMAL_FIRST_HALF, 0, 0, Command.NORMAL_START)),
    (3.0, _state(Stage.NORMAL_FIRST_HALF, 1, 0, Command.GOAL_BLUE)),
    (3.0, _state(Stage.NORMAL_FIRST_HALF, 1, 1, Command.GOAL_YELLOW)),
    (3.0, _state(Stage.NORMAL_HALF_TIME, 1, 1, Command.HALT)),
    (3.0, _state(Stage.NORMAL_SECOND_HALF, 2, 1, Command.GOAL_BLUE)),
    (3.0, _state(Stage.POST_GAME, 2, 1, Command.HALT)),
]


class _VerboseObs(ObsText):
    async def set_text(self, source_name: str, value: str) -> None:
        print(f"  OBS text  <- {source_name}: {value!r}")
        await super().set_text(source_name, value)

    async def set_image(self, source_name: str, path: str) -> None:
        print(f"  OBS image <- {source_name}: {path}")
        await super().set_image(source_name, path)


async def main(config_path: str) -> None:
    config = FieldConfig.load_from_file(config_path)
    print(f"Connecting to OBS at {config.obs.url} ...")
    ws = simpleobsws.WebSocketClient(url=config.obs.url, password=config.obs.password)
    await ws.connect()
    await ws.wait_until_identified()
    print("Connected. Playing scripted match (watch your OBS text sources):")
    obs = _VerboseObs(ws, text_field=config.obs.text_field)
    base_dir = os.path.dirname(os.path.abspath(config_path))
    logos_dir = effective_logos_dir(config.obs.logos_dir, config.obs.stage_dir, base_dir)
    try:
        await run_referee(
            FakeRefereeSource(SCRIPT), obs, config.obs.sources,
            config.obs.images, logos_dir,
        )
    finally:
        await ws.disconnect()
    print("Done.")


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1] if len(sys.argv) > 1 else "field.toml"))
