"""Integrated GPU (Radeon 8060S) telemetry from amdgpu sysfs + gpu_metrics."""

from __future__ import annotations

from .. import config
from . import sysfs
from .decode import cu_count, decode_igpu
from .gpu_metrics import GpuMetrics
from .history import MetricHistory
from .sample import IgpuSample


class IgpuSource:
    def __init__(self) -> None:
        # GPU identity is fixed for the life of the process; decode it once.
        self._info = decode_igpu(config.DRM_DEVICE)
        self._cu_count = cu_count(self._info.gfx)
        self._sclk_hist = MetricHistory(config.IGPU_HISTORY_WINDOW_S)
        self._temp_hist = MetricHistory(config.IGPU_HISTORY_WINDOW_S)
        self._power_hist = MetricHistory(config.IGPU_HISTORY_WINDOW_S)

    def read(self, gm: GpuMetrics | None) -> IgpuSample:
        busy: float | None = None
        sclk = sclk_max = fclk = uclk = None
        temp = power = None
        dram_r = dram_w = None
        if gm is not None:
            busy = gm.gfx_activity
            sclk, sclk_max = gm.gfxclk, gm.gfx_maxfreq
            fclk, uclk = gm.fclk, gm.uclk
            temp, power = gm.temp_gfx, gm.gfx_power
            dram_r, dram_w = gm.dram_reads, gm.dram_writes

        if busy is None:
            busy = sysfs.read_int(config.GPU_BUSY)

        self._sclk_hist.record(sclk)
        self._temp_hist.record(temp)
        self._power_hist.record(power)
        width = config.IGPU_HISTORY_WIDTH

        return IgpuSample(
            marketing=self._info.marketing,
            codename=self._info.codename,
            arch=self._info.arch,
            gfx=self._info.gfx,
            cu_count=self._cu_count,
            busy_pct=busy,
            mem_busy_pct=sysfs.read_int(config.MEM_BUSY),
            vram_used=sysfs.read_int(config.VRAM_USED),
            vram_total=sysfs.read_int(config.VRAM_TOTAL),
            gtt_used=sysfs.read_int(config.GTT_USED),
            gtt_total=sysfs.read_int(config.GTT_TOTAL),
            sclk_mhz=sclk,
            sclk_max_mhz=sclk_max,
            fclk_mhz=fclk,
            uclk_mhz=uclk,
            temp_c=temp,
            power_w=power,
            dram_read_mbps=dram_r,
            dram_write_mbps=dram_w,
            sclk_history=self._sclk_hist.series(width),
            temp_history=self._temp_hist.series(width),
            power_history=self._power_hist.series(width),
        )
