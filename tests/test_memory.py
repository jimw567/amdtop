from amdtop.telemetry import memory

# Real `dmidecode -t 17` output from a socketed DDR5-5600 Strix Point box.
_DDR5_5600_DUAL = """
Memory Device
        Total Width: 64 bits
        Data Width: 64 bits
        Size: 64 GB
        Locator: DIMM 0
        Bank Locator: P0 CHANNEL A
        Type: DDR5
        Speed: 5600 MT/s
        Rank: 2
        Configured Memory Speed: 5600 MT/s
Memory Device
        Total Width: 64 bits
        Data Width: 64 bits
        Size: 64 GB
        Locator: DIMM 0
        Bank Locator: P0 CHANNEL B
        Type: DDR5
        Speed: 5600 MT/s
        Rank: 2
        Configured Memory Speed: 5600 MT/s
"""


def test_parse_ddr5_5600_dual_channel():
    # 2 x 64-bit x 5600 MT/s / 8 = 89600 MB/s.
    assert memory._parse_dmidecode_mem_bw(_DDR5_5600_DUAL) == 89600.0


def test_parse_skips_empty_slots():
    text = """
Memory Device
        Data Width: 64 bits
        Size: No Module Installed
        Speed: Unknown
Memory Device
        Data Width: 64 bits
        Size: 32 GB
        Speed: 8000 MT/s
        Configured Memory Speed: 8000 MT/s
"""
    # Only the populated 64-bit @ 8000 module counts: 64 * 8000 / 8 = 64000.
    assert memory._parse_dmidecode_mem_bw(text) == 64000.0


def test_parse_prefers_configured_speed():
    text = """
Memory Device
        Data Width: 64 bits
        Size: 16 GB
        Speed: 6000 MT/s
        Configured Memory Speed: 4800 MT/s
"""
    # Configured (4800) wins over rated Speed (6000): 64 * 4800 / 8 = 38400.
    assert memory._parse_dmidecode_mem_bw(text) == 38400.0


def test_parse_empty_returns_none():
    assert memory._parse_dmidecode_mem_bw("") is None


def test_parse_type_ddr5():
    assert memory._parse_dmidecode_mem_type(_DDR5_5600_DUAL) == "DDR5"


def test_parse_type_skips_unpopulated_and_unknown():
    text = """
Memory Device
        Size: No Module Installed
        Type: Unknown
Memory Device
        Size: 16 GB
        Type: LPDDR5
"""
    assert memory._parse_dmidecode_mem_type(text) == "LPDDR5"


def test_parse_type_empty_returns_none():
    assert memory._parse_dmidecode_mem_type("") is None


def test_parse_type_ignores_unknown_type_on_populated():
    text = """
Memory Device
        Size: 16 GB
        Type: Unknown
"""
    assert memory._parse_dmidecode_mem_type(text) is None


def test_mem_type_prefers_cache(monkeypatch):
    monkeypatch.setattr(memory, "_read_type_cache", lambda: "LPDDR5X")
    assert memory.cached_or_detected_mem_type() == "LPDDR5X"


def test_mem_bw_falls_back_when_undetectable(monkeypatch):
    monkeypatch.setattr(memory, "_read_cache", lambda: None)
    monkeypatch.setattr(memory, "detect_mem_bw_mbps", lambda: None)
    assert memory.mem_bw_mbps(fallback=128000.0) == 128000.0


def test_mem_bw_prefers_cache(monkeypatch):
    monkeypatch.setattr(memory, "_read_cache", lambda: 89600.0)
    assert memory.mem_bw_mbps(fallback=128000.0) == 89600.0
