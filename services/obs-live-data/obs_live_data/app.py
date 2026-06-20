import os

from data_access.staging import stage_logos
from data_processing.format import format_updates
from data_processing.logo import logo_filename


def bundled_logos_dir() -> str:
    """Absolute path to the team logos shipped inside this package."""
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "logos"))


def effective_logos_dir(logos_dir: str, stage_dir: str, base_dir: str) -> str:
    """The logo dir to send paths from. An empty logos_dir uses the bundled package
    logos; a relative one resolves against base_dir (the config file's directory),
    not the current working directory; an absolute one is used as-is. When stage_dir
    is set, the logos are copied there first so paths line up with a mirror on a
    remote OBS machine."""
    if not logos_dir:
        resolved = bundled_logos_dir()
    elif os.path.isabs(logos_dir):
        resolved = logos_dir
    else:
        resolved = os.path.join(base_dir, logos_dir)
    return stage_logos(resolved, stage_dir) if stage_dir else resolved


def _logo_path(team_name: str, logos_dir: str) -> str:
    """Absolute path to a team's logo, falling back to no-logo.png when absent.
    Absolute so OBS resolves it regardless of its own working directory."""
    candidate = os.path.join(logos_dir, logo_filename(team_name))
    if not os.path.exists(candidate):
        candidate = os.path.join(logos_dir, "no-logo.png")
    return os.path.abspath(candidate)


def resolve_images(state, image_sources: dict[str, str], logos_dir: str) -> dict[str, str]:
    """OBS image-source name -> absolute logo path, for the mapped team logos."""
    teams = {"blue_logo": state.blue.name, "yellow_logo": state.yellow.name}
    return {
        image_sources[key]: _logo_path(team_name, logos_dir)
        for key, team_name in teams.items()
        if key in image_sources
    }


async def run_referee(
    source,
    obs,
    text_sources: dict[str, str],
    image_sources: dict[str, str] | None = None,
    logos_dir: str = "logos",
) -> None:
    """Push live referee-derived text and team logos to OBS, sending only values
    that changed since the last push (last-write-wins per source)."""
    image_sources = image_sources or {}
    last: dict[str, str] = {}
    async for state in source:
        for name, value in format_updates(state, None, text_sources).items():
            if last.get(name) != value:
                await obs.set_text(name, value)
                last[name] = value
        for name, path in resolve_images(state, image_sources, logos_dir).items():
            if last.get(name) != path:
                await obs.set_image(name, path)
                last[name] = path
