from amdtop.telemetry import cpu as cpu_mod


def _make_source(monkeypatch):
    # Avoid touching real sysfs during the delta-math test.
    monkeypatch.setattr(cpu_mod.CpuSource, "_per_core_mhz", lambda self: [])
    monkeypatch.setattr(cpu_mod.CpuSource, "_temp_c", lambda self: None)
    monkeypatch.setattr(cpu_mod, "_loadavg", lambda: None)
    monkeypatch.setattr(cpu_mod, "_read_proc_stat", lambda: {"cpu": (0, 0)})
    return cpu_mod.CpuSource()


def test_utilization_delta(monkeypatch):
    src = _make_source(monkeypatch)
    src._prev = {"cpu": (0, 0), "cpu0": (0, 0), "cpu1": (0, 0)}
    monkeypatch.setattr(
        cpu_mod,
        "_read_proc_stat",
        lambda: {"cpu": (50, 100), "cpu0": (100, 100), "cpu1": (0, 100)},
    )
    s = src.read(None)
    assert s.total_pct == 50.0
    assert s.per_cpu_pct == [100.0, 0.0]
    assert s.n_threads == 2


def test_zero_delta_is_zero(monkeypatch):
    src = _make_source(monkeypatch)
    src._prev = {"cpu": (10, 200), "cpu0": (10, 200)}
    monkeypatch.setattr(
        cpu_mod, "_read_proc_stat", lambda: {"cpu": (10, 200), "cpu0": (10, 200)}
    )
    s = src.read(None)
    assert s.total_pct == 0.0
    assert s.per_cpu_pct == [0.0]


def test_pct_clamped(monkeypatch):
    src = _make_source(monkeypatch)
    src._prev = {"cpu": (0, 0), "cpu0": (0, 0)}
    # busy grows more than total (shouldn't happen, but must clamp to 100).
    monkeypatch.setattr(
        cpu_mod, "_read_proc_stat", lambda: {"cpu": (500, 100), "cpu0": (500, 100)}
    )
    s = src.read(None)
    assert s.total_pct == 100.0
