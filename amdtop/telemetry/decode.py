"""Decode AMD iGPU PCI IDs into codename / architecture / gfx target.

Keyed by PCI device id (vendor 0x1002). Kept small and focused on the recent
APU integrated GPUs; unknown ids fall back to a generic label.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from . import sysfs


@dataclass
class GpuInfo:
    codename: str | None
    arch: str | None  # e.g. "RDNA 3.5"
    gfx: str | None  # e.g. "gfx1151"
    marketing: str | None  # e.g. "Radeon 8060S"


# device_id -> (codename, arch, gfx, marketing)
_APU_IDS: dict[int, tuple[str, str, str, str]] = {
    0x1586: ("Strix Halo", "RDNA 3.5", "gfx1151", "Radeon 8060S"),
    0x150E: ("Strix Point", "RDNA 3.5", "gfx1150", "Radeon 890M"),
    0x1114: ("Krackan Point", "RDNA 3.5", "gfx1152", "Radeon 860M"),
    0x15BF: ("Phoenix", "RDNA 3", "gfx1103", "Radeon 780M"),
    0x15C8: ("Phoenix 2", "RDNA 3", "gfx1103", "Radeon 740M"),
    0x1900: ("Strix Halo", "RDNA 3.5", "gfx1151", "Radeon 8060S"),
    0x1681: ("Rembrandt", "RDNA 2", "gfx1035", "Radeon 680M"),
}


# Theoretical peak unified-memory bandwidth (MB/s) per gfx target, from the
# LPDDR5X data rate and bus width: MT/s * bus_bits / 8.
# gfx1151 Strix Halo: LPDDR5X-8000 * 256-bit = 256000.
# gfx1150 Strix Point / gfx1152 Krackan: LPDDR5X-8000 * 128-bit = 128000.
_PEAK_MEM_BW_MBPS: dict[str, float] = {
    "gfx1151": 256000.0,
    "gfx1150": 128000.0,
    "gfx1152": 128000.0,
}
_DEFAULT_PEAK_MEM_BW_MBPS = 128000.0


def peak_mem_bw_mbps(gfx: str | None) -> float:
    """Theoretical peak unified-memory bandwidth for the given gfx target."""
    return _PEAK_MEM_BW_MBPS.get(gfx or "", _DEFAULT_PEAK_MEM_BW_MBPS)


def _marketing_from_cpuinfo() -> str | None:
    """Strix APUs advertise the Radeon SKU in the CPU model string."""
    try:
        with open("/proc/cpuinfo") as fh:
            for line in fh:
                if line.startswith("model name"):
                    m = re.search(r"(Radeon[\w\s+]*)", line.split(":", 1)[1])
                    return m.group(1).strip() if m else None
    except OSError:
        pass
    return None


def decode_igpu(device_path: str) -> GpuInfo:
    """Decode ``<drm>/device`` into a :class:`GpuInfo`."""
    dev_txt = sysfs.read_text(f"{device_path}/device")
    device_id = int(dev_txt, 16) if dev_txt else None

    codename = arch = gfx = table_marketing = None
    if device_id is not None and device_id in _APU_IDS:
        codename, arch, gfx, table_marketing = _APU_IDS[device_id]

    marketing = _marketing_from_cpuinfo() or table_marketing
    if marketing is None and device_id is not None:
        marketing = f"AMD GPU {device_id:#06x}"

    return GpuInfo(codename=codename, arch=arch, gfx=gfx, marketing=marketing)
