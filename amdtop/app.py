"""Live loop: collect a frame, render it, handle keys, repeat."""

from __future__ import annotations

import select
import sys
import termios
import time
import tty
from contextlib import contextmanager

from rich.console import Console
from rich.live import Live

from . import config
from .telemetry.collector import Collector
from .ui import layout


@contextmanager
def _raw_stdin():
    """Put stdin in cbreak mode for single-key reads; no-op if not a TTY."""
    if not sys.stdin.isatty():
        yield None
        return
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setcbreak(fd)
        yield fd
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)


def _wait_key(timeout: float) -> str | None:
    """Block up to ``timeout`` s for one keypress; return it or None."""
    if not sys.stdin.isatty():
        time.sleep(timeout)
        return None
    r, _, _ = select.select([sys.stdin], [], [], timeout)
    if r:
        return sys.stdin.read(1)
    return None


def _adjust(interval: float, faster: bool) -> float:
    interval = interval / 1.5 if faster else interval * 1.5
    return max(config.MIN_INTERVAL, min(config.MAX_INTERVAL, interval))


def run_once(interval: float, prime: float = 0.3) -> None:
    """Print a single snapshot (primes CPU deltas with a short sleep first)."""
    collector = Collector()
    collector.collect()
    time.sleep(prime)
    frame = collector.collect()
    Console().print(layout.render_static(frame, interval))


def run(interval: float = config.DEFAULT_INTERVAL) -> None:
    collector = Collector()
    collector.collect()  # prime CPU deltas
    console = Console()
    with _raw_stdin(), Live(
        console=console, screen=True, auto_refresh=False, transient=True
    ) as live:
        while True:
            frame = collector.collect()
            live.update(layout.render(frame, interval), refresh=True)
            key = _wait_key(interval)
            if key in ("q", "Q", "\x03"):  # q or Ctrl-C
                break
            if key in ("+", "="):
                interval = _adjust(interval, faster=True)
            elif key == "-":
                interval = _adjust(interval, faster=False)
