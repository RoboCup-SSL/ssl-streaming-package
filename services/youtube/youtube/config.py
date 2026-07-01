"""Per-event YouTube config, loaded from youtube.toml (see youtube.toml.example).

Mirrors configuration.FieldConfig: a frozen dataclass built from a TOML file, with
relative paths resolved next to the file. This is the single source of truth for
titles, description, tags, playlist, streams and credential locations — no settings
are hardcoded in the CLIs.
"""

import tomllib
from dataclasses import dataclass
from datetime import timedelta, timezone
from pathlib import Path

# repo root = …/services/youtube/youtube/config.py → parents[3]
REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_CONFIG = REPO_ROOT / "youtube.toml"


@dataclass(frozen=True)
class YoutubeConfig:
    tz: timezone
    title: str                 # template: {division}{field}{teamA}{teamB}{phase}{day}{time}
    description_header: str     # template: same placeholders
    description_body: str       # shared, static boilerplate
    tags: list[str]
    category_id: str
    playlist: str               # title or PL… id; "" disables
    privacy: str
    auto_start: bool            # OBS Start Streaming -> broadcast goes live
    auto_stop: bool             # OBS Stop -> broadcast ends (off = blip-safe; end deliberately)
    schedule_path: Path
    thumbnails_dir: Path
    client_secret: Path
    token: Path

    @classmethod
    def load_from_file(cls, path: Path) -> "YoutubeConfig":
        path = Path(path)
        with open(path, "rb") as fh:
            data = tomllib.load(fh)
        base = path.parent

        def rp(p: str) -> Path:
            p = Path(p)
            return p if p.is_absolute() else (base / p)

        bc = data["broadcast"]
        desc = bc["description"]
        paths = data["paths"]
        auth = data.get("auth", {})
        return cls(
            tz=timezone(timedelta(hours=data["event"].get("tz_offset_hours", 0))),
            title=bc["title"],
            description_header=desc["header"],
            description_body=desc.get("body", ""),
            tags=list(bc.get("tags", [])),
            category_id=str(bc.get("category_id", "28")),
            playlist=bc.get("playlist", ""),
            privacy=bc.get("privacy", "public"),
            auto_start=bc.get("auto_start", True),
            auto_stop=bc.get("auto_stop", False),
            schedule_path=rp(paths["schedule"]),
            thumbnails_dir=rp(paths["thumbnails"]),
            client_secret=rp(auth.get("client_secret", "services/youtube/client_secret.json")),
            token=rp(auth.get("token", "services/youtube/youtube_token.json")),
        )


def load(path: Path | None = None) -> YoutubeConfig:
    """Load the config at `path` (default: repo-root youtube.toml).

    Raises FileNotFoundError with a copy-the-example hint if it's missing."""
    path = Path(path) if path else DEFAULT_CONFIG
    if not path.exists():
        raise FileNotFoundError(
            f"{path} not found — copy the template:\n"
            f"    cp {path.name}.example {path.name}\n"
            f"(in {path.parent}), then edit it."
        )
    return YoutubeConfig.load_from_file(path)
