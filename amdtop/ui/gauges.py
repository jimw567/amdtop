"""Reusable bar-meter renderables with a green->yellow->red utilization ramp."""

from __future__ import annotations

from rich.text import Text

from .. import config

_BLOCKS = " ▏▎▍▌▋▊▉█"  # 1/8-step partial blocks for smooth fills
_SPARK = "▁▂▃▄▅▆▇█"  # 8 vertical levels for trend sparklines


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


def sparkline(
    points: list[float | None],
    *,
    lo: float | None = None,
    hi: float | None = None,
    color: str = "cyan",
) -> Text:
    """A single-row trend from ``points``; ``None`` slots render as a dim gap.

    ``lo``/``hi`` fix the value range so successive frames stay comparable; when
    omitted they default to the min/max of the present points. A flat series
    (or one point) sits on the baseline glyph.
    """
    vals = [p for p in points if p is not None]
    if not vals:
        return Text("─" * len(points), style="dim")
    lo = min(vals) if lo is None else lo
    hi = max(vals) if hi is None else hi
    span = hi - lo
    txt = Text()
    for p in points:
        if p is None:
            txt.append(" ", style="dim")
            continue
        frac = 0.0 if span <= 0 else (p - lo) / span
        level = max(0, min(len(_SPARK) - 1, int(frac * (len(_SPARK) - 1) + 0.5)))
        txt.append(_SPARK[level], style=color)
    return txt


def plot(
    points: list[float | None],
    height: int,
    *,
    lo: float | None = None,
    hi: float | None = None,
    color: str = "cyan",
) -> list[Text]:
    """A ``height``-row vertical bar chart of ``points``, top row first.

    Each column is a bar whose height encodes its value against ``[lo, hi]``,
    drawn with 1/8-block partials for smooth tops. ``None`` slots are dim gaps.
    With ``height == 1`` this is a single-row sparkline.
    """
    height = max(1, height)
    if not any(p is not None for p in points):
        return [Text("─" * len(points), style="dim")] + [
            Text(" " * len(points)) for _ in range(height - 1)
        ]
    vals = [p for p in points if p is not None]
    lo = min(vals) if lo is None else lo
    hi = max(vals) if hi is None else hi
    span = hi - lo
    steps = height * 8  # total eighth-block units in a full-height column
    rows = [Text() for _ in range(height)]
    for p in points:
        if p is None:
            for row in rows:
                row.append(" ", style="dim")
            continue
        frac = 0.0 if span <= 0 else (p - lo) / span
        units = max(1, min(steps, int(round(frac * steps))))
        for r in range(height):
            # rows[0] is the top; fill from the bottom row up.
            cell_from_bottom = height - 1 - r
            base = cell_from_bottom * 8
            if units >= base + 8:
                rows[r].append("█", style=color)
            elif units <= base:
                rows[r].append(" ")
            else:
                rows[r].append(_SPARK[units - base - 1], style=color)
    return rows


def fmt_bytes(n: int | None) -> str:
    if n is None:
        return "n/a"
    for unit in ("B", "K", "M", "G", "T"):
        if abs(n) < 1024:
            return f"{n:.0f}{unit}"
        n /= 1024
    return f"{n:.0f}P"
