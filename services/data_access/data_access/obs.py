import asyncio
from typing import Awaitable, Callable

import simpleobsws

# Connection-level failures worth retrying (OBS not up yet). Auth/protocol errors are not
# OSErrors, so they propagate out and the caller reports them instead of looping forever.
_RETRYABLE = (ConnectionRefusedError, OSError, asyncio.TimeoutError)


async def connect_obs(
    client,
    on_waiting: Callable[[Exception], None],
    retry_seconds: float = 3.0,
    sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
) -> None:
    """Connect + identify, retrying while OBS is simply not reachable yet. Calls
    on_waiting(exc) before each retry so the caller can tell the operator what's up."""
    while True:
        try:
            await client.connect()
            await client.wait_until_identified()
            return
        except _RETRYABLE as exc:
            on_waiting(exc)
            await sleep(retry_seconds)


class ObsText:
    """Sets text on named OBS sources over obs-websocket. The simpleobsws client
    is injected so it can be stubbed in tests."""

    def __init__(self, client, text_field: str = "text") -> None:
        self._client = client
        self._text_field = text_field

    async def set_text(self, source_name: str, value: str) -> None:
        request = simpleobsws.Request(
            "SetInputSettings",
            {"inputName": source_name, "inputSettings": {self._text_field: value}},
        )
        await self._client.call(request)

    async def set_image(self, source_name: str, path: str) -> None:
        request = simpleobsws.Request(
            "SetInputSettings",
            {"inputName": source_name, "inputSettings": {"file": path}},
        )
        await self._client.call(request)
