"""Rich renderables for the header and the CPU / iGPU / NPU panels."""

from __future__ import annotations

import datetime as _dt

from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from .. import config
from ..telemetry.sample import (
    CpuSample,
    Frame,
    GpuProcess,
    IgpuSample,
    MemSample,
    NpuSample,
)
from . import gauges


def _fmt_uptime(s: float | None) -> str:
    if s is None:
        return "?"
    s = int(s)
    d, rem = divmod(s, 86400)
    h, rem = divmod(rem, 3600)
    m, _ = divmod(rem, 60)
    return (f"{d}d " if d else "") + f"{h:02d}:{m:02d}"


_FOCUS_LABELS = {"cpu": "CPU", "igpu": "iGPU", "npu": "NPU"}


def render_header(frame: Frame, interval: float, focus: str = "cpu") -> Panel:
    now = _dt.datetime.now().strftime("%H:%M:%S")
    left = Text()
    left.append(" amdtop ", style="bold reverse")
    left.append(f" {frame.host}", style="bold cyan")
    if frame.igpu.codename:
        left.append(f" ({frame.igpu.codename})", style="bold green")
    left.append(f"  up {_fmt_uptime(frame.uptime_s)}", style="dim")
    if frame.socket_power_w is not None:
        left.append(f"   socket {frame.socket_power_w:.1f} W", style="magenta")

    right = Text()
    right.append("focus ")
    for i, key in enumerate(("cpu", "igpu", "npu"), start=1):
        style = "bold reverse cyan" if key == focus else "dim"
        right.append(f" {i}:{_FOCUS_LABELS[key]} ", style=style)
    right.append(f"   {interval:.1f}s  q quit  +/- rate  {now}", style="dim")

    grid = Table.grid(expand=True)
    grid.add_column(justify="left")
    grid.add_column(justify="right")
    grid.add_row(left, right)
    return Panel(grid, box=config.PANEL_BOX, style="blue", padding=(0, 1))


def _core_grid(cpu: CpuSample, columns: int = 4) -> Table:
    n = cpu.n_threads
    rows = (n + columns - 1) // columns
    grid = Table.grid(expand=True, padding=(0, 1))
    for _ in range(columns):
        grid.add_column(justify="left")
    cells: list[Text] = []
    for i in range(n):
        pct = cpu.per_cpu_pct[i]
        cell = Text()
        cell.append(f"{i:2d}", style="dim")
        cell.append("[")
        cell.append_text(gauges.meter(pct, 6))
        cell.append("]")
        cell.append(f"{pct:3.0f}%", style=gauges.ramp_color(pct))
        cells.append(cell)
    for r in range(rows):
        row = [cells[r + c * rows] for c in range(columns) if r + c * rows < n]
        row += [Text("")] * (columns - len(row))
        grid.add_row(*row)
    return grid


def render_cpu(cpu: CpuSample) -> Panel:
    body = Table.grid(expand=True)
    body.add_column()

    summary = Text()
    summary.append_text(gauges.labeled_meter("all", cpu.total_pct, 24))
    body.add_row(summary)

    stats = Text()
    if cpu.avg_mhz is not None:
        stats.append(f"avg {cpu.avg_mhz} MHz   ", style="cyan")
    if cpu.temp_c is not None:
        stats.append(f"{cpu.temp_c:.0f}°C   ", style="yellow")
    if cpu.power_w is not None:
        stats.append(f"{cpu.power_w:.1f} W   ", style="magenta")
    if cpu.loadavg is not None:
        stats.append("load %.2f %.2f %.2f" % cpu.loadavg, style="dim")
    body.add_row(stats)
    body.add_row(Text())
    body.add_row(_core_grid(cpu))

    title = f"CPU · {cpu.model}"
    return Panel(body, box=config.PANEL_BOX, title=title, title_align="left", border_style="green")


def _mem_row(label: str, used: int | None, total: int | None, width: int = 20) -> Text:
    if used is None or total is None or total == 0:
        return gauges.labeled_meter(label, None, width)
    pct = 100.0 * used / total
    suffix = f"{gauges.fmt_bytes(used)}/{gauges.fmt_bytes(total)}"
    return gauges.labeled_meter(label, pct, width, suffix, label_w=4)


def render_mem(m: MemSample, width: int = 28) -> Panel:
    body = Table.grid(expand=True)
    body.add_column()
    body.add_row(_mem_row("ram", m.used, m.total, width=width))
    body.add_row(_mem_row("swap", m.swap_used, m.swap_total, width=width))

    stats = Text()
    if m.available is not None:
        stats.append(f"avail {gauges.fmt_bytes(m.available)}   ", style="green")
    if m.cached is not None:
        stats.append(f"cached {gauges.fmt_bytes(m.cached)}", style="dim")
    body.add_row(stats)

    return Panel(body, box=config.PANEL_BOX, title="Memory", title_align="left", border_style="yellow")


def _proc_rows(procs: list[GpuProcess], body: Table, width: int = 44) -> None:
    body.add_row(Text("─" * width, style="dim"))
    for p in procs:
        line = Text()
        line.append(f"{p.pid:>7} ")
        line.append(f"{(p.user or '?')[:8]:<8} ", style="cyan")
        line.append(f"{p.comm[:12]:<12} ", style="white")
        if p.gpu_pct is None:
            line.append(f"{'—':>4}", style="dim")
        else:
            line.append(f"{p.gpu_pct:3.0f}%", style=gauges.ramp_color(p.gpu_pct))
        line.append(f" {gauges.fmt_bytes(p.vram_bytes):>6}", style="magenta")
        body.add_row(line)


def _trend_rows(body: Table, g: IgpuSample) -> None:
    window_m = config.IGPU_HISTORY_WINDOW_S / 60.0
    win = f"{window_m:.0f}m" if window_m == int(window_m) else f"{window_m:.1f}m"
    specs = [
        ("sclk", g.sclk_history, "MHz", "cyan", "{:.0f}"),
        ("temp", g.temp_history, "°C", "yellow", "{:.0f}"),
        ("power", g.power_history, "W", "magenta", "{:.0f}"),
    ]
    # Each plot's vertical scale is the session extremes (sticky min..max learned
    # since process start), so bars fill the plot as the run's true range emerges.
    # Shared gutter width so every plot's bars start at the same column.
    gutter_w = max(
        (
            len(fmt.format(v))
            for _, series, _, _, fmt in specs
            if series is not None and series.min is not None
            for v in (series.min, series.max)
        ),
        default=1,
    )
    for label, series, unit, color, fmt in specs:
        if series is None:
            continue
        lo, hi = series.min, series.max
        head = Text()
        head.append(f"{label:<5}", style="bold")
        cur = "n/a" if series.cur is None else fmt.format(series.cur)
        head.append(f"{cur:>5} {unit}  ", style=color)
        if lo is not None and hi is not None:
            head.append(
                f"min {fmt.format(lo)}  max {fmt.format(hi)}",
                style="dim",
            )
        head.append(f"  · {win}", style="dim")
        body.add_row(head)
        lines = gauges.plot(
            series.points,
            config.IGPU_HISTORY_HEIGHT,
            lo=lo,
            hi=hi,
            color=color,
        )
        # y-axis gutter: max label on the top row, min on the bottom, blank between.
        for i, line in enumerate(lines):
            if i == 0 and hi is not None:
                tick = fmt.format(hi)
            elif i == len(lines) - 1 and lo is not None:
                tick = fmt.format(lo)
            else:
                tick = ""
            row = Text(f"{tick:>{gutter_w}} ", style="dim")
            row.append_text(line)
            body.add_row(row)


def render_igpu(g: IgpuSample, procs: list[GpuProcess] | None = None) -> Panel:
    body = Table.grid(expand=True)
    body.add_column()
    body.add_row(gauges.labeled_meter("gpu", g.busy_pct, 24))
    if g.mem_busy_pct is not None:
        body.add_row(gauges.labeled_meter("mem", g.mem_busy_pct, 24))

    clk = Text()
    if g.sclk_mhz is not None:
        mx = f"/{g.sclk_max_mhz}" if g.sclk_max_mhz else ""
        clk.append(f"sclk {g.sclk_mhz}{mx} MHz   ", style="cyan")
    if g.fclk_mhz is not None:
        clk.append(f"fclk {g.fclk_mhz}   ", style="cyan")
    if g.uclk_mhz is not None:
        clk.append(f"uclk {g.uclk_mhz}", style="cyan")
    body.add_row(clk)

    stats = Text()
    if g.temp_c is not None:
        stats.append(f"{g.temp_c:.0f}°C   ", style="yellow")
    if g.power_w is not None:
        stats.append(f"{g.power_w:.1f} W", style="magenta")
    body.add_row(stats)
    body.add_row(Text())
    _trend_rows(body, g)
    body.add_row(Text())
    body.add_row(_mem_row("vram", g.vram_used, g.vram_total))
    body.add_row(_mem_row("gtt", g.gtt_used, g.gtt_total))
    if procs:
        _proc_rows(procs, body)

    name = g.marketing or "iGPU"
    title = f"iGPU · {name}"
    if g.cu_count:
        title += f" · {g.cu_count} CU"
    if g.arch:
        title += f" · {g.arch}"
    if g.gfx:
        title += f" · {g.gfx}"
    peak_gbps = config.MEM_BW_PEAK_MBPS / 1000.0
    tilde = "~" if config.MEM_BW_PEAK_IS_ESTIMATE else ""
    mem = f"{config.MEM_TYPE} " if config.MEM_TYPE else ""
    title += f" · {mem}{tilde}{peak_gbps:.0f} GB/s"
    return Panel(body, box=config.PANEL_BOX, title=title, title_align="left", border_style="magenta")


def render_cpu_compact(cpu: CpuSample) -> Panel:
    body = Table.grid(expand=True)
    body.add_column()
    body.add_row(gauges.labeled_meter("all", cpu.total_pct, 10))
    stats = Text()
    if cpu.avg_mhz is not None:
        stats.append(f"{cpu.avg_mhz} MHz  ", style="cyan")
    if cpu.temp_c is not None:
        stats.append(f"{cpu.temp_c:.0f}°C  ", style="yellow")
    if cpu.power_w is not None:
        stats.append(f"{cpu.power_w:.1f} W", style="magenta")
    body.add_row(stats)
    return Panel(body, box=config.PANEL_BOX, title="CPU", title_align="left", border_style="green")


def render_igpu_compact(g: IgpuSample) -> Panel:
    body = Table.grid(expand=True)
    body.add_column()
    body.add_row(gauges.labeled_meter("busy", g.busy_pct, 10))
    body.add_row(_mem_row("vram", g.vram_used, g.vram_total, width=10))
    body.add_row(_mem_row("gtt", g.gtt_used, g.gtt_total, width=10))
    stats = Text()
    if g.sclk_mhz is not None:
        stats.append(f"{g.sclk_mhz} MHz  ", style="cyan")
    if g.temp_c is not None:
        stats.append(f"{g.temp_c:.0f}°C  ", style="yellow")
    if g.power_w is not None:
        stats.append(f"{g.power_w:.1f} W", style="magenta")
    body.add_row(stats)
    name = g.marketing or "iGPU"
    return Panel(body, box=config.PANEL_BOX, title=f"iGPU · {name}", title_align="left", border_style="magenta")


def render_npu_compact(n: NpuSample) -> Panel:
    body = Table.grid(expand=True)
    body.add_column()
    if not n.present:
        body.add_row(Text("not detected", style="dim"))
        return Panel(body, box=config.PANEL_BOX, title="NPU", title_align="left", border_style="cyan")
    body.add_row(gauges.labeled_meter("busy", n.activity_max, 10))
    stats = Text()
    if n.clk_mhz is not None:
        stats.append(f"{n.clk_mhz} MHz  ", style="cyan")
    if n.power_w is not None:
        stats.append(f"{n.power_w:.2f} W  ", style="magenta")
    if n.power_state:
        stats.append(n.power_state, style="green" if n.power_state == "D0" else "dim")
    body.add_row(stats)
    return Panel(body, box=config.PANEL_BOX, title="NPU · XDNA", title_align="left", border_style="cyan")


def render_npu(n: NpuSample) -> Panel:
    body = Table.grid(expand=True)
    body.add_column()

    if not n.present:
        body.add_row(Text("NPU not detected", style="dim"))
        return Panel(body, box=config.PANEL_BOX, title="NPU", title_align="left", border_style="cyan")

    head = gauges.labeled_meter("busy", n.activity_max, 24)
    body.add_row(head)
    body.add_row(Text())

    for i, a in enumerate(n.activity):
        body.add_row(gauges.labeled_meter(f"col{i}", float(a), 16, label_w=5))
    if not n.activity:
        body.add_row(Text("activity: n/a", style="dim"))

    body.add_row(Text())
    stats = Text()
    if n.clk_mhz is not None:
        stats.append(f"clk {n.clk_mhz} MHz   ", style="cyan")
    if n.power_w is not None:
        stats.append(f"{n.power_w:.2f} W   ", style="magenta")
    if n.power_state:
        stats.append(f"{n.power_state}", style="green" if n.power_state == "D0" else "dim")
    body.add_row(stats)
    ident = Text(f"{n.name or 'npu'}  fw {n.fw_version or '?'}", style="dim")
    body.add_row(ident)

    return Panel(body, box=config.PANEL_BOX, title="NPU · XDNA", title_align="left", border_style="cyan")
