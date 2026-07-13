from amdtop.telemetry import decode


def test_strix_halo_mapping():
    codename, arch, gfx, marketing = decode._APU_IDS[0x1586]
    assert codename == "Strix Halo"
    assert arch == "RDNA 3.5"
    assert gfx == "gfx1151"
    assert marketing == "Radeon 8060S"


def test_strix_point_890m_mapping():
    codename, arch, gfx, marketing = decode._APU_IDS[0x150E]
    assert codename == "Strix Point"
    assert arch == "RDNA 3.5"
    assert gfx == "gfx1150"
    assert marketing == "Radeon 890M"


def test_marketing_falls_back_to_table(tmp_path, monkeypatch):
    (tmp_path / "device").write_text("0x150E\n")
    monkeypatch.setattr(decode, "_marketing_from_cpuinfo", lambda: None)
    info = decode.decode_igpu(str(tmp_path))
    assert info.codename == "Strix Point"
    assert info.marketing == "Radeon 890M"


def test_decode_known_device(tmp_path, monkeypatch):
    (tmp_path / "device").write_text("0x1586\n")
    monkeypatch.setattr(decode, "_marketing_from_cpuinfo", lambda: "Radeon 8060S")
    info = decode.decode_igpu(str(tmp_path))
    assert info.codename == "Strix Halo"
    assert info.arch == "RDNA 3.5"
    assert info.gfx == "gfx1151"
    assert info.marketing == "Radeon 8060S"


def test_decode_unknown_device(tmp_path, monkeypatch):
    (tmp_path / "device").write_text("0xdead\n")
    monkeypatch.setattr(decode, "_marketing_from_cpuinfo", lambda: None)
    info = decode.decode_igpu(str(tmp_path))
    assert info.codename is None
    assert info.arch is None
    assert info.marketing == "AMD GPU 0xdead"


def test_gfx_target_version():
    assert decode._gfx_target_version("gfx1150") == 110500
    assert decode._gfx_target_version("gfx1151") == 110501
    assert decode._gfx_target_version("gfx1103") == 110003
    assert decode._gfx_target_version(None) is None
    assert decode._gfx_target_version("radeon") is None


def _write_node(root, idx, **props):
    node = root / str(idx)
    node.mkdir()
    node.joinpath("properties").write_text(
        "".join(f"{k} {v}\n" for k, v in props.items())
    )


def test_cu_count_matches_gfx_target(tmp_path, monkeypatch):
    nodes = tmp_path / "nodes"
    nodes.mkdir()
    _write_node(nodes, 0, simd_count=0, simd_per_cu=0, gfx_target_version=0)  # CPU
    _write_node(nodes, 1, simd_count=32, simd_per_cu=2, gfx_target_version=110500)
    monkeypatch.setattr(decode, "_KFD_NODES", str(nodes))
    assert decode.cu_count("gfx1150") == 16


def test_cu_count_falls_back_to_first_gpu_node(tmp_path, monkeypatch):
    nodes = tmp_path / "nodes"
    nodes.mkdir()
    _write_node(nodes, 0, simd_count=0, simd_per_cu=0)
    _write_node(nodes, 1, simd_count=80, simd_per_cu=2, gfx_target_version=110501)
    monkeypatch.setattr(decode, "_KFD_NODES", str(nodes))
    assert decode.cu_count("gfx9999") == 40  # no match -> first GPU node


def test_cu_count_none_when_no_gpu(tmp_path, monkeypatch):
    nodes = tmp_path / "nodes"
    nodes.mkdir()
    _write_node(nodes, 0, simd_count=0, simd_per_cu=0)
    monkeypatch.setattr(decode, "_KFD_NODES", str(nodes))
    assert decode.cu_count("gfx1150") is None


def test_marketing_regex(monkeypatch):
    sample = "model name\t: AMD RYZEN AI MAX+ 395 w/ Radeon 8060S\n"

    class FakeFile:
        def __enter__(self):
            return [sample]

        def __exit__(self, *a):
            return False

    monkeypatch.setattr("builtins.open", lambda *a, **k: FakeFile())
    assert decode._marketing_from_cpuinfo() == "Radeon 8060S"
