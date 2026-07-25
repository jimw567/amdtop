"""Time-windowed sample history for sparkline trends (e.g. sclk/temp over 10 min)."""

from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass


@dataclass
class Series:
    """A fixed-width downsampled view of one metric over the window.

    ``points`` has ``len == width``; oldest bucket first, newest last. A bucket
    with no samples yet (the window not filled) is ``None`` and renders as a gap.
    ``cur/min/max`` are computed over the raw samples still inside the window.
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
    the x-axis is a stable window width regardless of the refresh rate.
    """

    def __init__(self, window_s: float) -> None:
        self._window_s = window_s
        self._samples: deque[tuple[float, float]] = deque()

    def record(self, value: float | None, *, now: float | None = None) -> None:
        t = time.monotonic() if now is None else now
        if value is not None:
            self._samples.append((t, float(value)))
        cutoff = t - self._window_s
        while self._samples and self._samples[0][0] < cutoff:
            self._samples.popleft()

    def series(self, width: int, *, now: float | None = None) -> Series:
        t = time.monotonic() if now is None else now
        if width <= 0 or not self._samples:
            return Series([None] * max(0, width), None, None, None)

        start = t - self._window_s
        span = self._window_s
        sums = [0.0] * width
        counts = [0] * width
        for st, sv in self._samples:
            idx = int((st - start) / span * width)
            idx = max(0, min(width - 1, idx))
            sums[idx] += sv
            counts[idx] += 1
        points = [sums[i] / counts[i] if counts[i] else None for i in range(width)]

        values = [sv for _, sv in self._samples]
        return Series(points, values[-1], min(values), max(values))
