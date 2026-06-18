import json
import logging

log = logging.getLogger(__name__)


class ScheduleFile:
    """Reads the schedule JSON, returning the last good value if a read fails
    (e.g. a mid-edit save)."""

    def __init__(self, path: str) -> None:
        self._path = path
        self._last: dict | None = None

    def load(self) -> dict:
        try:
            with open(self._path, "rb") as fh:
                self._last = json.load(fh)
        except (OSError, json.JSONDecodeError):
            if self._last is None:
                raise
            log.warning("schedule unreadable; serving last good copy", exc_info=True)
        return self._last
