"""Non-fatal warnings for an un-edited or thin field.toml — the things a first-time
user forgets. Printed by run.sh; never blocks the run."""
import sys
import tomllib

# Values copied straight from field.toml.example — their presence means "not edited yet".
_EXAMPLE_CAMERA_VALUES = {"rtsp://10.0.0.5:554/stream"}


def config_warnings(path: str) -> list[str]:
    with open(path, "rb") as fh:
        data = tomllib.load(fh)

    warnings: list[str] = []
    obs = data.get("obs", {})
    if obs.get("password") == "change-me":
        warnings.append(
            "OBS password is still 'change-me' — set [obs].password "
            '(or "" if obs-websocket auth is off).'
        )

    cameras = data.get("cameras", {})
    placeholders = [n for n, v in cameras.items() if v in _EXAMPLE_CAMERA_VALUES]
    if placeholders:
        warnings.append(
            f"[cameras] still has example values for: {', '.join(placeholders)} "
            "— point them at real cameras or remove them."
        )
    if not cameras:
        warnings.append(
            "no [cameras] declared — MediaMTX will serve no video "
            "(text and logos still work)."
        )
    return warnings


def main(path: str) -> None:
    for warning in config_warnings(path):
        print(f"[warn] {warning}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "field.toml")
