def logo_filename(team_name: str) -> str:
    """Team name -> logo file name, matching the ssl-status-board convention
    (lowercased, spaces -> hyphens)."""
    slug = team_name.lower().replace(" ", "-")
    return f"{slug}.png"
