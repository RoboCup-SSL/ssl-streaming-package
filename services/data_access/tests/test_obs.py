import pytest

from data_access.obs import ObsText


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
