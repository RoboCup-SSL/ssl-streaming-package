from data_access.staging import stage_logos


def test_stage_logos_copies_into_dst_and_returns_it(tmp_path):
    src = tmp_path / "bundle"
    src.mkdir()
    (src / "er-force.png").write_bytes(b"x")
    dst = tmp_path / "staged" / "ssl-logos"

    result = stage_logos(str(src), str(dst))

    assert result == str(dst)
    assert (dst / "er-force.png").read_bytes() == b"x"
