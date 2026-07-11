from amdtop.telemetry import decode


def test_strix_halo_mapping():
    codename, arch, gfx = decode._APU_IDS[0x1586]
    assert codename == "Strix Halo"
    assert arch == "RDNA 3.5"
    assert gfx == "gfx1151"


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


def test_marketing_regex(monkeypatch):
    sample = "model name\t: AMD RYZEN AI MAX+ 395 w/ Radeon 8060S\n"

    class FakeFile:
        def __enter__(self):
            return [sample]

        def __exit__(self, *a):
            return False

    monkeypatch.setattr("builtins.open", lambda *a, **k: FakeFile())
    assert decode._marketing_from_cpuinfo() == "Radeon 8060S"
