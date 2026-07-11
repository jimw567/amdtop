"""System RAM / swap telemetry from /proc/meminfo."""

from __future__ import annotations

from .sample import MemSample

_MEMINFO = "/proc/meminfo"


def _read_meminfo() -> dict[str, int]:
    """Return /proc/meminfo as {key: bytes}."""
    out: dict[str, int] = {}
    try:
        with open(_MEMINFO) as fh:
            for line in fh:
                key, _, rest = line.partition(":")
                parts = rest.split()
                if parts:
                    # values are in kB
                    out[key] = int(parts[0]) * 1024
    except OSError:
        pass
    return out


class MemSource:
    def read(self) -> MemSample:
        m = _read_meminfo()
        total = m.get("MemTotal")
        available = m.get("MemAvailable")
        cached = m.get("Cached")
        swap_total = m.get("SwapTotal")
        swap_free = m.get("SwapFree")

        used = None if total is None or available is None else total - available
        swap_used = (
            None
            if swap_total is None or swap_free is None
            else swap_total - swap_free
        )
        return MemSample(
            total=total,
            used=used,
            available=available,
            cached=cached,
            swap_total=swap_total,
            swap_used=swap_used,
        )
