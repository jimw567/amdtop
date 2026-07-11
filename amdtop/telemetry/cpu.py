"""CPU telemetry: per-thread utilization, per-core clocks, temp, package power."""

from __future__ import annotations

import glob

from .. import config
from . import sysfs
from .gpu_metrics import GpuMetrics
from .sample import CpuSample


def _read_proc_stat() -> dict[str, tuple[int, int]]:
    """Return {cpu_key: (busy_jiffies, total_jiffies)} for 'cpu' and each 'cpuN'."""
    out: dict[str, tuple[int, int]] = {}
    with open(config.PROC_STAT) as fh:
        for line in fh:
            if not line.startswith("cpu"):
                break
            parts = line.split()
            key = parts[0]
            vals = [int(x) for x in parts[1:]]
            idle = vals[3] + (vals[4] if len(vals) > 4 else 0)  # idle + iowait
            total = sum(vals)
            out[key] = (total - idle, total)
    return out


def _cpu_model() -> str:
    try:
        with open("/proc/cpuinfo") as fh:
            for line in fh:
                if line.startswith("model name"):
                    return line.split(":", 1)[1].strip()
    except OSError:
        pass
    return "CPU"


def _loadavg() -> tuple[float, float, float] | None:
    txt = sysfs.read_text("/proc/loadavg")
    if not txt:
        return None
    p = txt.split()
    return (float(p[0]), float(p[1]), float(p[2]))


class CpuSource:
    """Stateful CPU collector (holds previous /proc/stat snapshot for deltas)."""

    def __init__(self) -> None:
        self._prev = _read_proc_stat()
        self._model = _cpu_model()
        self._hwmon = sysfs.find_hwmon("k10temp")

    def _temp_c(self) -> float | None:
        if not self._hwmon:
            return None
        raw = sysfs.read_int(f"{self._hwmon}/temp1_input")  # Tctl, milli-degC
        return None if raw is None else round(raw / 1000.0, 1)

    def _per_core_mhz(self) -> list[int]:
        def cpu_index(p: str) -> int:
            return int(p.split("/cpufreq")[0].rsplit("/cpu", 1)[1])

        mhz: list[int] = []
        for path in sorted(glob.glob(config.CPUFREQ_GLOB), key=cpu_index):
            khz = sysfs.read_int(path)
            if khz is not None:
                mhz.append(round(khz / 1000))
        return mhz

    def read(self, gm: GpuMetrics | None) -> CpuSample:
        cur = _read_proc_stat()

        def pct(key: str) -> float:
            pb, pt = self._prev.get(key, (0, 0))
            cb, ct = cur[key]
            dt = ct - pt
            if dt <= 0:
                return 0.0
            return max(0.0, min(100.0, 100.0 * (cb - pb) / dt))

        per_cpu = [pct(k) for k in cur if k != "cpu"]
        total = pct("cpu")
        self._prev = cur

        mhz = self._per_core_mhz()
        avg_mhz = round(sum(mhz) / len(mhz)) if mhz else None

        power = None
        if gm is not None:
            power = gm.apu_power if gm.apu_power else gm.socket_power

        return CpuSample(
            total_pct=total,
            per_cpu_pct=per_cpu,
            per_core_mhz=mhz,
            avg_mhz=avg_mhz,
            temp_c=self._temp_c(),
            power_w=power,
            loadavg=_loadavg(),
            model=self._model,
            n_threads=len(per_cpu),
        )
