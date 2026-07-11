"""Integrated GPU (Radeon 8060S) telemetry from amdgpu sysfs + gpu_metrics."""

from __future__ import annotations

from .. import config
from . import sysfs
from .decode import decode_igpu
from .gpu_metrics import GpuMetrics
from .sample import IgpuSample


class IgpuSource:
    def __init__(self) -> None:
        # GPU identity is fixed for the life of the process; decode it once.
        self._info = decode_igpu(config.DRM_DEVICE)

    def read(self, gm: GpuMetrics | None) -> IgpuSample:
        busy: float | None = None
        sclk = sclk_max = fclk = uclk = None
        temp = power = None
        if gm is not None:
            busy = gm.gfx_activity
            sclk, sclk_max = gm.gfxclk, gm.gfx_maxfreq
            fclk, uclk = gm.fclk, gm.uclk
            temp, power = gm.temp_gfx, gm.gfx_power

        if busy is None:
            busy = sysfs.read_int(config.GPU_BUSY)

        return IgpuSample(
            marketing=self._info.marketing,
            codename=self._info.codename,
            arch=self._info.arch,
            gfx=self._info.gfx,
            busy_pct=busy,
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
        )
