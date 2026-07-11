"""Reusable bar-meter renderables with a green->yellow->red utilization ramp."""

from __future__ import annotations

from rich.text import Text

from .. import config

_BLOCKS = " ▏▎▍▌▋▊▉█"  # 1/8-step partial blocks for smooth fills


def ramp_color(pct: float) -> str:
    if pct < config.RAMP_GREEN_MAX:
        return "green"
    if pct < config.RAMP_YELLOW_MAX:
        return "yellow"
    return "red"


def meter(pct: float | None, width: int, *, color: str | None = None) -> Text:
    """A ``width``-cell bar filled to ``pct`` (0-100), colored by the ramp."""
    if pct is None:
        return Text("─" * width, style="dim")
    pct = max(0.0, min(100.0, pct))
    style = color or ramp_color(pct)
    filled = pct / 100.0 * width
    full = int(filled)
    rem = filled - full
    bar = "█" * full
    if full < width:
        bar += _BLOCKS[int(rem * 8)]
        bar += " " * (width - full - 1)
    txt = Text()
    txt.append(bar[:width], style=style)
    return txt


def labeled_meter(
    label: str, pct: float | None, width: int, suffix: str = "", *, label_w: int = 4
) -> Text:
    """``label [====   ] 42% suffix`` on one line."""
    txt = Text()
    txt.append(f"{label:<{label_w}}", style="bold")
    txt.append("[")
    txt.append_text(meter(pct, width))
    txt.append("]")
    val = "  n/a" if pct is None else f"{pct:4.0f}%"
    txt.append(f" {val}", style="" if pct is None else ramp_color(pct))
    if suffix:
        txt.append(f" {suffix}", style="dim")
    return txt


def fmt_bytes(n: int | None) -> str:
    if n is None:
        return "n/a"
    for unit in ("B", "K", "M", "G", "T"):
        if abs(n) < 1024:
            return f"{n:.0f}{unit}"
        n /= 1024
    return f"{n:.0f}P"
