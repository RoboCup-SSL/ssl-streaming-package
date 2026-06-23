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
from obs_live_data.connect import connect_obs_or_exit


# Team names match logo files in logos/ (lowercased, spaces -> hyphens).
MATCH_1 = ("ER-Force", "TIGERs Mannheim")
MATCH_2 = ("ZJUNlict", "RoboTeam Twente")


def _state(stage: Stage, blue: int, yellow: int, command: Command, teams) -> MatchState:
    blue_name, yellow_name = teams
    return MatchState(stage, command, Team(blue_name, blue, 0), Team(yellow_name, yellow, 0))


# (delay seconds before this state, state) — two matchups so names + logos swap halfway.
SCRIPT = [
    (0.0, _state(Stage.NORMAL_FIRST_HALF_PRE, 0, 0, Command.HALT, MATCH_1)),
    (3.0, _state(Stage.NORMAL_FIRST_HALF, 0, 0, Command.NORMAL_START, MATCH_1)),
    (3.0, _state(Stage.NORMAL_FIRST_HALF, 1, 0, Command.GOAL_BLUE, MATCH_1)),
    (3.0, _state(Stage.NORMAL_HALF_TIME, 1, 0, Command.HALT, MATCH_1)),
    # --- new match: different teams (watch names + logos swap) ---
    (3.0, _state(Stage.NORMAL_FIRST_HALF_PRE, 0, 0, Command.HALT, MATCH_2)),
    (3.0, _state(Stage.NORMAL_FIRST_HALF, 0, 0, Command.NORMAL_START, MATCH_2)),
    (3.0, _state(Stage.NORMAL_FIRST_HALF, 0, 1, Command.GOAL_YELLOW, MATCH_2)),
    (3.0, _state(Stage.POST_GAME, 0, 1, Command.HALT, MATCH_2)),
]


class _LoggingClient:
    """Wraps the simpleobsws client to print each request and response as JSON,
    so we can see exactly what goes on the wire and what OBS replies."""

    def __init__(self, inner) -> None:
        self._inner = inner

    async def connect(self):
        return await self._inner.connect()

    async def wait_until_identified(self):
        return await self._inner.wait_until_identified()

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


async def _preflight(client) -> None:
    """List OBS's actual inputs so you can confirm your sources are named to match
    the canonical field names (see obs-template/README.md)."""
    response = await client.call(simpleobsws.Request("GetInputList"))
    inputs = sorted(i["inputName"] for i in response.responseData.get("inputs", []))
    print(f"OBS inputs ({len(inputs)}): {inputs}")


async def main(config_path: str) -> None:
    config = FieldConfig.load_from_file(config_path)
    print(f"Connecting to OBS at {config.obs.url} ...")
    ws = simpleobsws.WebSocketClient(url=config.obs.url, password=config.obs.password)
    client = await connect_obs_or_exit(_LoggingClient(ws), config.obs.url)
    print("Connected.")
    await _preflight(client)
    print("Playing scripted match (watch your OBS text sources):")
    obs = ObsText(client, text_field=config.obs.text_field)
    base_dir = os.path.dirname(os.path.abspath(config_path))
    logos_dir = effective_logos_dir(config.obs.logos_dir, config.obs.stage_dir, base_dir)
    try:
        await run_referee(FakeRefereeSource(SCRIPT), obs, logos_dir)
    finally:
        await ws.disconnect()
    print("Done.")


if __name__ == "__main__":
    try:
        asyncio.run(main(sys.argv[1] if len(sys.argv) > 1 else "field.toml"))
    except KeyboardInterrupt:
        print("\nStopped.")
