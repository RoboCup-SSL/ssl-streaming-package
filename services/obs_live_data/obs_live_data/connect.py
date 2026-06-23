"""Connecting to OBS with operator-friendly messaging, shared by the live app and
the demo so the 'waiting for OBS' and failure messages live in one place."""
import sys

from data_access.obs import ReconnectingObsClient


def waiting_message(url: str) -> str:
    return (f"Waiting for OBS at {url} — start OBS with obs-websocket enabled, "
            f"and check [obs].url / [obs].password. (Ctrl-C to quit)")


async def connect_obs_or_exit(client, url: str, exit=sys.exit) -> ReconnectingObsClient:
    """Wrap a raw obs-websocket client in a self-healing client and connect, waiting
    while OBS is simply not up yet. On a non-retryable failure (bad auth/url) report
    it and exit. Returns the resilient client for the rest of the app to use."""
    resilient = ReconnectingObsClient(client, on_waiting=lambda _exc: print(waiting_message(url)))
    try:
        await resilient.connect()
    except Exception as exc:
        print(f"Could not connect to OBS at {url}: {exc}")
        print("Check [obs].url and [obs].password, and that obs-websocket is enabled in OBS.")
        exit(1)
    return resilient
