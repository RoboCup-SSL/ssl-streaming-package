"""Manual smoke test: play a scripted match through a real OBS over obs-websocket.

No Game Controller needed — a FakeRefereeSource drives the same push path the live
app uses. Run: uv run python -m obs_live_data.demo field.toml
"""
import asyncio
import json
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


class _LoggingClient:
    """Wraps the simpleobsws client to print each request and response as JSON,
    so we can see exactly what goes on the wire and what OBS replies."""

    def __init__(self, inner) -> None:
        self._inner = inner

    async def call(self, request):
        print("  -> " + json.dumps(
            {"requestType": request.requestType, "requestData": request.requestData}))
        response = await self._inner.call(request)
        print("  <- " + json.dumps(
            {
                "ok": response.ok(),
                "requestStatus": getattr(response, "requestStatus", None),
                "responseData": getattr(response, "responseData", None),
            },
            default=str,
        ))
        return response


async def _preflight(ws, config) -> None:
    """List OBS's actual inputs and flag any configured source/image names that
    don't exist — the usual reason updates silently do nothing."""
    response = await ws.call(simpleobsws.Request("GetInputList"))
    inputs = {i["inputName"] for i in response.responseData.get("inputs", [])}
    print(f"OBS inputs ({len(inputs)}): {sorted(inputs)}")
    configured = set(config.obs.sources.values()) | set(config.obs.images.values())
    missing = sorted(configured - inputs)
    if missing:
        print(f"!! configured but NOT in OBS (will silently no-op): {missing}")
    else:
        print("All configured source names exist in OBS.")


async def main(config_path: str) -> None:
    config = FieldConfig.load_from_file(config_path)
    print(f"Connecting to OBS at {config.obs.url} ...")
    ws = simpleobsws.WebSocketClient(url=config.obs.url, password=config.obs.password)
    await ws.connect()
    await ws.wait_until_identified()
    print("Connected.")
    await _preflight(ws, config)
    print("Playing scripted match (watch your OBS text sources):")
    obs = ObsText(_LoggingClient(ws), text_field=config.obs.text_field)
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
