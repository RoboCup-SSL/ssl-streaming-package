import asyncio
from typing import Awaitable, Callable

import simpleobsws
from websockets.exceptions import ConnectionClosed

# Connection-level failures worth retrying (OBS not up yet). Auth/protocol errors are not
# OSErrors, so they propagate out and the caller reports them instead of looping forever.
_RETRYABLE = (ConnectionRefusedError, OSError, asyncio.TimeoutError)
# A call failing one of these means OBS went away mid-run (restarted): reconnect and retry.
_DROPPED = (ConnectionClosed,) + _RETRYABLE


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


class ReconnectingObsClient:
    """An obs-websocket client that survives OBS being restarted mid-run.

    Exposes the same call(request) interface as the raw client, so ObsText and
    run_referee are oblivious to drops. When a call hits a dropped connection it
    reconnects (with the same 'waiting for OBS' retry as the initial connect) and
    replays the last settings sent for every input, so a freshly-restarted OBS is
    brought straight back to the current scoreboard rather than waiting for the
    next change. Requests are assumed idempotent and keyed by inputName."""

    def __init__(
        self,
        client,
        on_waiting: Callable[[Exception], None],
        retry_seconds: float = 3.0,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ) -> None:
        self._client = client
        self._on_waiting = on_waiting
        self._retry_seconds = retry_seconds
        self._sleep = sleep
        self._last: dict[str, object] = {}

    async def connect(self) -> None:
        await self._establish()

    async def call(self, request):
        try:
            response = await self._client.call(request)
        except _DROPPED:
            await self._establish()
            for prior in self._last.values():
                await self._client.call(prior)
            response = await self._client.call(request)
        self._remember(request)
        return response

    async def _establish(self) -> None:
        # Announce the wait only once per reconnect episode, not on every retry.
        announced = False

        def once(exc: Exception) -> None:
            nonlocal announced
            if not announced:
                self._on_waiting(exc)
                announced = True

        await connect_obs(self._client, once, self._retry_seconds, self._sleep)

    def _remember(self, request) -> None:
        name = getattr(request, "requestData", {}).get("inputName")
        if name is not None:
            self._last[name] = request


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
