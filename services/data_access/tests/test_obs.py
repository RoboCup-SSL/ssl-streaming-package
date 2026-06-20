import pytest

from data_access.obs import ObsText, connect_obs


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
