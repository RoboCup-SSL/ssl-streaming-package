import simpleobsws


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
