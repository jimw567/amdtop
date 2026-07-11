"""Command-line entry point for amdtop."""

from __future__ import annotations

import argparse
import sys

from . import __version__, app, config


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="amdtop",
        description="btop-style CPU/iGPU/NPU monitor for AMD Strix Halo APUs.",
    )
    parser.add_argument(
        "-i", "--interval", type=float, default=config.DEFAULT_INTERVAL,
        metavar="SEC", help="refresh interval in seconds (default: %(default)s)",
    )
    parser.add_argument(
        "-1", "--once", action="store_true",
        help="print a single snapshot and exit",
    )
    parser.add_argument(
        "--no-strict", action="store_true",
        help="run with an estimated memory bandwidth peak instead of erroring "
             "when the real per-host value is unknown",
    )
    parser.add_argument("-V", "--version", action="version",
                        version=f"amdtop {__version__}")
    args = parser.parse_args(argv)

    if config.MEM_BW_PEAK_IS_ESTIMATE and not args.no_strict:
        print(
            "error: memory bandwidth peak is unknown for this host "
            "(no cached SMBIOS value).\n"
            "Prime it once (you'll be prompted for your sudo password), then "
            "re-run amdtop:\n"
            "    python -m amdtop.telemetry.memory\n"
            "Or run with --no-strict to use an estimated value.",
            file=sys.stderr,
        )
        return 1

    interval = max(config.MIN_INTERVAL, min(config.MAX_INTERVAL, args.interval))
    try:
        if args.once:
            app.run_once(interval)
        else:
            app.run(interval)
    except KeyboardInterrupt:
        pass
    return 0
