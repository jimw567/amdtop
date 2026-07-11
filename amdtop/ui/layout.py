"""Compose the header + CPU / iGPU / NPU panels into one screen renderable."""

from __future__ import annotations

from rich.console import Group
from rich.layout import Layout

from ..telemetry.sample import Frame
from . import panels


def render(frame: Frame, interval: float) -> Layout:
    root = Layout()
    root.split_column(
        Layout(panels.render_header(frame, interval), name="header", size=3),
        Layout(name="body"),
    )
    root["body"].split_row(
        Layout(name="left", ratio=2),
        Layout(name="side", ratio=1),
    )
    root["body"]["left"].split_column(
        Layout(panels.render_cpu(frame.cpu), name="cpu"),
        Layout(panels.render_mem(frame.mem), name="mem", size=5),
    )
    root["body"]["side"].split_column(
        Layout(panels.render_igpu(frame.igpu), name="igpu"),
        Layout(panels.render_npu(frame.npu), name="npu"),
    )
    return root


def render_static(frame: Frame, interval: float) -> Group:
    """Flat top-to-bottom rendering for --once / non-fullscreen output."""
    return Group(
        panels.render_header(frame, interval),
        panels.render_cpu(frame.cpu),
        panels.render_mem(frame.mem),
        panels.render_igpu(frame.igpu),
        panels.render_npu(frame.npu),
    )
