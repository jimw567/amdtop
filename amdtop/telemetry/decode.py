"""Decode AMD iGPU PCI IDs into codename / architecture / gfx target.

Keyed by PCI device id (vendor 0x1002). Kept small and focused on the recent
APU integrated GPUs; unknown ids fall back to a generic label.
"""

from __future__ import annotations

import glob
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


_KFD_NODES = "/sys/class/kfd/kfd/topology/nodes"


def _gfx_target_version(gfx: str | None) -> int | None:
    """Encode a gfx target (e.g. ``gfx1150``) as KFD's numeric version (110500)."""
    if not gfx or not gfx.startswith("gfx"):
        return None
    digits = gfx[3:]
    if len(digits) < 3 or not digits.isdigit():
        return None
    return int(digits[:-2]) * 10000 + int(digits[-2]) * 100 + int(digits[-1])


def _read_props(path: str) -> dict[str, int]:
    txt = sysfs.read_text(path)
    props: dict[str, int] = {}
    if txt:
        for line in txt.splitlines():
            parts = line.split()
            if len(parts) == 2:
                try:
                    props[parts[0]] = int(parts[1])
                except ValueError:
                    pass
    return props


def cu_count(gfx: str | None = None) -> int | None:
    """Compute-unit count of the iGPU, from KFD topology.

    CU = simd_count / simd_per_cu. Prefers the node whose gfx_target_version
    matches ``gfx``; otherwise falls back to the first GPU node.
    """
    want = _gfx_target_version(gfx)
    fallback: int | None = None
    for node in sorted(glob.glob(f"{_KFD_NODES}/*/properties")):
        p = _read_props(node)
        simd, per_cu = p.get("simd_count", 0), p.get("simd_per_cu", 0)
        if simd <= 0 or per_cu <= 0:
            continue
        cu = simd // per_cu
        if want is not None and p.get("gfx_target_version") == want:
            return cu
        if fallback is None:
            fallback = cu
    return fallback


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
