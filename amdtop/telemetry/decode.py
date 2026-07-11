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


# device_id -> (codename, arch, gfx)
_APU_IDS: dict[int, tuple[str, str, str]] = {
    0x1586: ("Strix Halo", "RDNA 3.5", "gfx1151"),
    0x150E: ("Strix Point", "RDNA 3.5", "gfx1150"),
    0x1114: ("Krackan Point", "RDNA 3.5", "gfx1152"),
    0x15BF: ("Phoenix", "RDNA 3", "gfx1103"),
    0x15C8: ("Phoenix 2", "RDNA 3", "gfx1103"),
    0x1900: ("Strix Halo", "RDNA 3.5", "gfx1151"),
    0x1681: ("Rembrandt", "RDNA 2", "gfx1035"),
}


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

    codename = arch = gfx = None
    if device_id is not None and device_id in _APU_IDS:
        codename, arch, gfx = _APU_IDS[device_id]

    marketing = _marketing_from_cpuinfo()
    if marketing is None and device_id is not None:
        marketing = f"AMD GPU {device_id:#06x}"

    return GpuInfo(codename=codename, arch=arch, gfx=gfx, marketing=marketing)
