import pytest
import simpleobsws

from data_access.obs import ObsText, ReconnectingObsClient, connect_obs


async def _no_sleep(_):
    pass


def _set_text(name, value):
    return simpleobsws.Request(
        "SetInputSettings", {"inputName": name, "inputSettings": {"text": value}}
    )


class DropOnceClient:
    """Stub obs-websocket client. Records delivered inputNames and drops the
    connection on the given (0-based) inner-call indices."""

    def __init__(self, drop_on=()):
        self.delivered = []
        self.connects = 0
        self._n = 0
        self._drop_on = set(drop_on)

    async def connect(self):
        self.connects += 1

    async def wait_until_identified(self):
        pass

    async def call(self, request):
        i = self._n
        self._n += 1
        if i in self._drop_on:
            raise ConnectionResetError("OBS went away")
        self.delivered.append(request.requestData["inputName"])


class FlakyClient:
    def __init__(self, fails):
        self._fails = fails
        self.connects = 0
        self.identified = False

    async def connect(self):
        self.connects += 1
        if self.connects <= self._fails:
            raise ConnectionRefusedError("OBS not up yet")

    async def wait_until_identified(self):
        self.identified = True


@pytest.mark.asyncio
async def test_connect_obs_retries_until_reachable():
    client = FlakyClient(fails=2)
    waits = []

    async def no_sleep(_):
        pass

    await connect_obs(client, on_waiting=lambda e: waits.append(e), sleep=no_sleep)
    assert client.connects == 3
    assert client.identified
    assert len(waits) == 2  # two failed attempts before success


@pytest.mark.asyncio
async def test_connect_obs_propagates_non_connection_errors():
    class BadAuth:
        async def connect(self):
            pass

        async def wait_until_identified(self):
            raise RuntimeError("authentication failed")

    with pytest.raises(RuntimeError):
        await connect_obs(BadAuth(), on_waiting=lambda e: None)


class RecordingClient:
    def __init__(self):
        self.calls = []

    async def call(self, request):
        self.calls.append((request.requestType, request.requestData))


@pytest.mark.asyncio
async def test_set_text_issues_setinputsettings():
    client = RecordingClient()
    obs = ObsText(client, text_field="text")
    await obs.set_text("txt_blue", "ER-Force")
    assert client.calls == [
        ("SetInputSettings",
         {"inputName": "txt_blue", "inputSettings": {"text": "ER-Force"}}),
    ]


@pytest.mark.asyncio
async def test_set_image_issues_setinputsettings_with_file():
    client = RecordingClient()
    obs = ObsText(client)
    await obs.set_image("img_blue", "/logos/er-force.png")
    assert client.calls == [
        ("SetInputSettings",
         {"inputName": "img_blue", "inputSettings": {"file": "/logos/er-force.png"}}),
    ]


@pytest.mark.asyncio
async def test_reconnecting_client_retries_a_call_after_a_drop():
    inner = DropOnceClient(drop_on={0})
    client = ReconnectingObsClient(inner, on_waiting=lambda e: None, sleep=_no_sleep)
    await client.call(_set_text("txt", "x"))
    assert inner.connects == 1          # reconnected once
    assert inner.delivered == ["txt"]    # and the call still got through


@pytest.mark.asyncio
async def test_reconnecting_client_replays_prior_inputs_so_obs_is_current():
    # blue_name + blue_score land; then a score update drops the connection.
    # On reconnect the wrapper must re-push the inputs OBS forgot (blue_name),
    # not just the one call that failed.
    inner = DropOnceClient(drop_on={2})
    client = ReconnectingObsClient(inner, on_waiting=lambda e: None, sleep=_no_sleep)
    await client.call(_set_text("blue_name", "ER-Force"))
    await client.call(_set_text("blue_score", "0"))
    await client.call(_set_text("blue_score", "1"))
    assert inner.connects == 1
    assert inner.delivered == [
        "blue_name", "blue_score",            # before the restart
        "blue_name", "blue_score", "blue_score",  # replay of prior state, then the retry
    ]
