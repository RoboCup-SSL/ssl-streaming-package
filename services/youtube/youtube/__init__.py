"""YouTube Data API client for the SSL stream.

A thin, OBS-agnostic wrapper around YouTube live broadcasts/streams. Two consumers:
- `youtube.schedule` (CLI): pre-tournament batch-scheduling of every match.
- obs-controller (runtime, MVP2 2.1): pulls a field's stream key to feed OBS.

Keep this package free of OBS and schedule-format knowledge — it only knows YouTube.
"""

from .client import YouTubeClient

__all__ = ["YouTubeClient"]
