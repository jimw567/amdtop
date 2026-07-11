"""System RAM / swap telemetry from /proc/meminfo."""

from __future__ import annotations

import os
import pwd
import socket
import subprocess

from .sample import MemSample

_MEMINFO = "/proc/meminfo"


def _cache_home() -> str:
    """Real user's home, even under sudo (so a root-primed cache is found later)."""
    sudo_user = os.environ.get("SUDO_USER")
    if sudo_user:
        try:
            return pwd.getpwnam(sudo_user).pw_dir
        except KeyError:
            pass
    return os.path.expanduser("~")


# Peak memory bandwidth can't be derived from the GPU alone: the same APU ships
# with soldered LPDDR5X (wide bus) or socketed DDR5 (narrower, slower), so it
# must be read from the actual DIMMs via SMBIOS. dmidecode needs root, so a
# successful detection is cached for later no-root runs. The home dir is often
# NFS-shared across hosts, so the cache is keyed by hostname to avoid collisions.
_MEM_BW_CACHE = os.path.join(
    _cache_home(), ".cache", "amdtop", f"mem_bw_mbps.{socket.gethostname()}"
)


def _first_int(val: str | None) -> int | None:
    if not val:
        return None
    try:
        return int(val.split()[0])
    except (ValueError, IndexError):
        return None


def _parse_dmidecode_mem_bw(text: str) -> float | None:
    """Sum data-width x configured-speed / 8 over populated modules -> MB/s."""
    total = 0.0
    cur: dict[str, str] = {}

    def flush() -> None:
        nonlocal total
        if _first_int(cur.get("Size")):  # populated (not "No Module Installed")
            width = _first_int(cur.get("Data Width") or cur.get("Total Width"))
            mts = _first_int(cur.get("Configured Memory Speed") or cur.get("Speed"))
            if width and mts:
                total += width * mts / 8.0

    for line in text.splitlines():
        s = line.strip()
        if s == "Memory Device":
            flush()
            cur = {}
            continue
        key, sep, val = s.partition(":")
        if sep:
            cur[key.strip()] = val.strip()
    flush()
    return total or None


def detect_mem_bw_mbps(allow_sudo: bool = False) -> float | None:
    """Read peak memory bandwidth from SMBIOS via dmidecode.

    Runs dmidecode directly when already root. Otherwise, if ``allow_sudo`` is
    set, escalates only dmidecode via ``sudo`` (may prompt for a password) so the
    calling user still owns any cache it writes -- important on root_squash NFS
    homes where a root process cannot write the user's cache. Returns None when
    the data can't be read.
    """
    if os.geteuid() == 0:
        cmd = ["dmidecode", "-t", "17"]
        timeout: float | None = 5
    elif allow_sudo:
        cmd = ["sudo", "dmidecode", "-t", "17"]
        timeout = 120  # allow time for an interactive password prompt
    else:
        return None
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.SubprocessError):
        return None
    if out.returncode != 0:
        return None
    return _parse_dmidecode_mem_bw(out.stdout)


def _read_cache() -> float | None:
    try:
        with open(_MEM_BW_CACHE) as fh:
            v = float(fh.read().strip())
        return v if v > 0 else None
    except (OSError, ValueError):
        return None


def _write_cache(v: float) -> bool:
    try:
        os.makedirs(os.path.dirname(_MEM_BW_CACHE), exist_ok=True)
        with open(_MEM_BW_CACHE, "w") as fh:
            fh.write(str(v))
        return True
    except OSError:
        return False


def cached_or_detected_mem_bw_mbps() -> float | None:
    """Real DIMM-derived peak from cache, or SMBIOS if already root; else None.

    Never prompts for a password here (no sudo) -- that would hang the TUI on
    startup. Priming via sudo is an explicit step (see the module ``__main__``).
    """
    cached = _read_cache()
    if cached is not None:
        return cached
    detected = detect_mem_bw_mbps()
    if detected is not None and _write_cache(detected):
        return detected
    return None


def mem_bw_mbps(fallback: float) -> float:
    """Real DIMM-derived peak if known, else the given fallback."""
    real = cached_or_detected_mem_bw_mbps()
    return real if real is not None else fallback


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


if __name__ == "__main__":
    # Prime the per-host bandwidth cache. Run this as yourself (NOT under sudo) --
    # it escalates only dmidecode via sudo (you may be prompted for a password),
    # and writes the cache as you, so it works on root_squash NFS homes.
    import sys

    bw = detect_mem_bw_mbps(allow_sudo=True)
    if bw is None:
        print("could not read SMBIOS memory info via dmidecode.", file=sys.stderr)
        sys.exit(1)
    if not _write_cache(bw):
        print(f"could not write cache to {_MEM_BW_CACHE}", file=sys.stderr)
        sys.exit(1)
    print(
        f"memory bandwidth peak: {bw / 1000:.1f} GB/s ({bw:.0f} MB/s)\n"
        f"cached at {_MEM_BW_CACHE}"
    )
