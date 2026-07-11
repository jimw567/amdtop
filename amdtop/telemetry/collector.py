"""Frame collector: reads gpu_metrics once, fans it out to the three sources."""

from __future__ import annotations

import socket

from . import gpu_metrics, sysfs
from .cpu import CpuSource
from .igpu import IgpuSource
from .memory import MemSource
from .npu import GpuMetricsNpuSource, NpuSource
from .sample import Frame


class Collector:
    def __init__(self, npu_source: NpuSource | None = None) -> None:
        self._cpu = CpuSource()
        self._mem = MemSource()
        self._igpu = IgpuSource()
        self._npu = npu_source or GpuMetricsNpuSource()
        self._host = socket.gethostname()

    def collect(self) -> Frame:
        gm = gpu_metrics.read()
        cpu = self._cpu.read(gm)
        mem = self._mem.read()
        igpu = self._igpu.read(gm)
        npu = self._npu.read(gm)
        socket_power = gm.socket_power if gm else None
        return Frame(
            host=self._host,
            uptime_s=_uptime(),
            cpu=cpu,
            mem=mem,
            igpu=igpu,
            npu=npu,
            socket_power_w=socket_power,
        )


def _uptime() -> float | None:
    txt = sysfs.read_text("/proc/uptime")
    if not txt:
        return None
    try:
        return float(txt.split()[0])
    except (ValueError, IndexError):
        return None
