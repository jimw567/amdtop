"""Small sysfs read helpers shared by the telemetry sources."""

from __future__ import annotations

import glob


def read_text(path: str) -> str | None:
    try:
        with open(path) as fh:
            return fh.read().strip()
    except OSError:
        return None


def read_int(path: str) -> int | None:
    txt = read_text(path)
    if txt is None:
        return None
    try:
        return int(txt)
    except ValueError:
        return None


def find_hwmon(name: str) -> str | None:
    """Return the /sys/class/hwmon/hwmonN dir whose ``name`` matches, or None."""
    for d in sorted(glob.glob("/sys/class/hwmon/hwmon*")):
        if read_text(f"{d}/name") == name:
            return d
    return None
