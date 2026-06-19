import shutil


def stage_logos(src_dir: str, dst_dir: str) -> str:
    """Copy the logo set into a fixed location so its absolute paths line up with
    a copy placed at the same path on a remote OBS machine. Returns dst_dir."""
    shutil.copytree(src_dir, dst_dir, dirs_exist_ok=True)
    return dst_dir
