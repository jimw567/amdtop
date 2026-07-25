"""Time-windowed sample history for sparkline trends (e.g. sclk/temp over 10 min)."""

from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass


@dataclass
class Series:
    """A fixed-width downsampled view of one metric over the window.

    ``points`` has ``len == width``; oldest bucket first, newest last. Each
    bucket holds the *peak* value of the samples in its time slot; a bucket with
    no samples yet (the window not filled) is ``None`` and renders as a gap.
    ``cur`` is the newest windowed sample; ``min``/``max`` are *sticky* extremes
    over every value seen since process start, so the plot's vertical scale is
    fixed and doesn't rescale as samples slide out of the window.
    """

    points: list[float | None]
    cur: float | None
    min: float | None
    max: float | None


class MetricHistory:
    """Keeps ``(t, value)`` samples within a sliding time window.

    One instance per metric. ``record`` is called once per collected frame; old
    samples fall out of the window on each call. ``series`` buckets the retained
    samples into ``width`` equal time slots spanning ``[now - window, now]`` so
    the x-axis is a stable window width regardless of the refresh rate. The
    reported min/max are sticky across the whole run, not just the window.
    """

    def __init__(self, window_s: float) -> None:
        self._window_s = window_s
        self._samples: deque[tuple[float, float]] = deque()
        self._min: float | None = None
        self._max: float | None = None

    def record(self, value: float | None, *, now: float | None = None) -> None:
        t = time.monotonic() if now is None else now
        if value is not None:
            v = float(value)
            self._samples.append((t, v))
            self._min = v if self._min is None else min(self._min, v)
            self._max = v if self._max is None else max(self._max, v)
        cutoff = t - self._window_s
        while self._samples and self._samples[0][0] < cutoff:
            self._samples.popleft()

    def series(self, width: int, *, now: float | None = None) -> Series:
        t = time.monotonic() if now is None else now
        if width <= 0 or not self._samples:
            return Series([None] * max(0, width), None, self._min, self._max)

        start = t - self._window_s
        span = self._window_s
        points: list[float | None] = [None] * width
        for st, sv in self._samples:
            idx = int((st - start) / span * width)
            idx = max(0, min(width - 1, idx))
            # Peak within the time slot, so a brief boost isn't averaged away.
            prev = points[idx]
            points[idx] = sv if prev is None else max(prev, sv)

        cur = self._samples[-1][1]
        return Series(points, cur, self._min, self._max)
