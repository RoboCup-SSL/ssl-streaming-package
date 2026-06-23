import pytest

from data_access.obs import ReconnectingObsClient
from obs_live_data.connect import connect_obs_or_exit, waiting_message


class OkClient:
    async def connect(self):
        pass

    async def wait_until_identified(self):
        pass


class BadAuthClient:
    async def connect(self):
        pass

    async def wait_until_identified(self):
        raise RuntimeError("authentication failed")


async def test_returns_a_resilient_client_on_success():
    client = await connect_obs_or_exit(OkClient(), "ws://host:4455")
    assert isinstance(client, ReconnectingObsClient)


async def test_reports_and_exits_on_a_non_retryable_failure(capsys):
    codes = []

    def fake_exit(code):
        codes.append(code)
        raise SystemExit(code)

    with pytest.raises(SystemExit):
        await connect_obs_or_exit(BadAuthClient(), "ws://host:4455", exit=fake_exit)

    assert codes == [1]
    assert "Could not connect to OBS at ws://host:4455" in capsys.readouterr().out


def test_waiting_message_names_the_url():
    assert "ws://host:4455" in waiting_message("ws://host:4455")
