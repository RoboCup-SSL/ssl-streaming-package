# live/schedule_logic.py
from datetime import datetime


def _match_dt(m):
    """Absolute datetime of a match from its day + time (venue-local)."""
    return datetime.strptime(f'{m["day"]} {m["time"]}', "%Y-%m-%d %H:%M")


def _view(m):
    """Public match view with a ready-to-render matchup string."""
    return {
        "label": m["label"],
        "teamA": m["teamA"],
        "teamB": m["teamB"],
        "time": m["time"],
        "matchup": f'{m["teamA"]} vs {m["teamB"]}',
    }


def format_countdown(seconds):
    """None -> None. Else clamp >=0 and format M:SS (<1h) or H:MM:SS (>=1h)."""
    if seconds is None:
        return None
    seconds = max(0, int(seconds))
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    if h > 0:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"


def resolve(data, field, now_dt):
    """Given loaded schedule data, a field, and 'now', return the field's
    now/next/countdown payload. Raises ValueError on unknown field or bad currentId."""
    field_matches = sorted(
        (m for m in data["schedule"] if m["field"] == field),
        key=_match_dt,
    )
    if not field_matches:
        raise ValueError(f"unknown field: {field!r}")

    live = data.get("live", {}).get(field, {})
    current_id = live.get("currentId")
    if current_id is None:
        raise ValueError(f"no currentId configured for field {field!r}")
    now_match = next((m for m in field_matches if m["id"] == current_id), None)
    if now_match is None:
        raise ValueError(f"currentId {current_id!r} not found for field {field!r}")

    next_id = live.get("nextId")
    if next_id is not None:
        next_match = next((m for m in field_matches if m["id"] == next_id), None)
    else:
        idx = field_matches.index(now_match)
        next_match = field_matches[idx + 1] if idx + 1 < len(field_matches) else None

    seconds = None
    if next_match is not None:
        target_str = live.get("nextStartsAt")
        target = datetime.fromisoformat(target_str) if target_str else _match_dt(next_match)
        seconds = max(0, int((target - now_dt).total_seconds()))

    return {
        "field": field,
        "division": now_match["division"],
        "now": _view(now_match),
        "next": _view(next_match) if next_match else None,
        "secondsUntilNext": seconds,
        "countdown": format_countdown(seconds),
    }
