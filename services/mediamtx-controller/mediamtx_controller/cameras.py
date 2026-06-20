import tomllib


def load_cameras(config_path: str) -> dict[str, str]:
    """Read the [cameras] table (name -> source descriptor) from a field.toml."""
    with open(config_path, "rb") as fh:
        data = tomllib.load(fh)
    return data.get("cameras", {})
