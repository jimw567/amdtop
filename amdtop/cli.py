"""Command-line entry point for amdtop."""

from __future__ import annotations

import argparse

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
    parser.add_argument("-V", "--version", action="version",
                        version=f"amdtop {__version__}")
    args = parser.parse_args(argv)

    interval = max(config.MIN_INTERVAL, min(config.MAX_INTERVAL, args.interval))
    try:
        if args.once:
            app.run_once(interval)
        else:
            app.run(interval)
    except KeyboardInterrupt:
        pass
    return 0
