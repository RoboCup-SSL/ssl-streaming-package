"""Log in to YouTube and confirm which channel the credentials authorize.

    python -m youtube.auth

Runs the OAuth flow if needed (opens a browser, caches the token), then prints the
authenticated channel. Credentials come from youtube.toml ([auth] section). Run this
once before scheduling so you know the token is valid and points at the right account.
"""

import argparse
from pathlib import Path

from . import config
from .client import YouTubeClient


def main() -> None:
    ap = argparse.ArgumentParser(description="Authorize YouTube and show the channel.")
    ap.add_argument("--config", type=Path, default=None,
                    help="Path to youtube.toml (default: repo-root youtube.toml).")
    args = ap.parse_args()

    cfg = config.load(args.config)
    yt = YouTubeClient.authenticate(cfg.client_secret, cfg.token)
    ch = yt.channel()
    print(f"Authorized as channel: {ch['title']}  ({ch['id']})")
    print(f"Token cached at: {cfg.token}")


if __name__ == "__main__":
    main()
