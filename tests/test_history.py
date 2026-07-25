from amdtop.telemetry.history import MetricHistory
from amdtop.ui import gauges


def test_empty_series_is_all_gaps():
    h = MetricHistory(window_s=600.0)
    s = h.series(10, now=0.0)
    assert s.points == [None] * 10
    assert s.cur is s.min is s.max is None


def test_min_max_cur_over_window():
    h = MetricHistory(window_s=600.0)
    for t, v in enumerate([800, 1600, 2900, 1200]):
        h.record(v, now=float(t))
    s = h.series(4, now=3.0)
    assert s.cur == 1200
    assert s.min == 800
    assert s.max == 2900


def test_old_samples_fall_out_of_window():
    h = MetricHistory(window_s=10.0)
    h.record(100, now=0.0)
    h.record(200, now=5.0)
    h.record(300, now=100.0)  # evicts the two older samples from the plot
    s = h.series(4, now=100.0)
    assert s.cur == 300
    # only the newest sample is still plotted...
    assert [p for p in s.points if p is not None] == [300]


def test_min_max_are_sticky_across_window():
    h = MetricHistory(window_s=10.0)
    h.record(100, now=0.0)  # slides out of the window later
    h.record(2900, now=5.0)  # slides out too
    h.record(300, now=100.0)  # only this remains in-window
    s = h.series(4, now=100.0)
    assert s.cur == 300
    # min/max persist even though those samples left the window
    assert s.min == 100 and s.max == 2900


def test_min_max_survive_empty_window():
    h = MetricHistory(window_s=10.0)
    h.record(800, now=0.0)
    h.record(2900, now=1.0)
    h.record(None, now=1000.0)  # a later frame evicts every aged-out sample
    s = h.series(4, now=1000.0)
    assert s.points == [None] * 4
    assert s.cur is None
    assert s.min == 800 and s.max == 2900


def test_none_values_not_recorded():
    h = MetricHistory(window_s=600.0)
    h.record(None, now=0.0)
    h.record(500, now=1.0)
    h.record(None, now=2.0)
    s = h.series(4, now=2.0)
    assert s.cur == 500 and s.min == 500 and s.max == 500


def test_buckets_average_samples_in_slot():
    h = MetricHistory(window_s=4.0)
    # window [0,4] into 4 buckets of width 1s; two samples land in bucket 0.
    h.record(100, now=0.0)
    h.record(200, now=0.5)
    s = h.series(4, now=4.0)
    assert s.points[0] == 150.0


def test_sparkline_flat_series_on_baseline():
    txt = gauges.sparkline([5.0, 5.0, 5.0])
    assert txt.plain == "▁▁▁"


def test_sparkline_gap_for_none():
    txt = gauges.sparkline([1.0, None, 2.0])
    assert txt.plain[1] == " "
    assert len(txt.plain) == 3


def test_sparkline_all_none_is_dashes():
    txt = gauges.sparkline([None, None])
    assert txt.plain == "──"


def test_sparkline_ramp_spans_low_to_high():
    txt = gauges.sparkline([0.0, 100.0])
    assert txt.plain == "▁█"


def test_plot_height_and_width():
    rows = gauges.plot([0.0, 50.0, 100.0], 4)
    assert len(rows) == 4
    assert all(len(r.plain) == 3 for r in rows)


def test_plot_full_column_is_all_blocks():
    rows = gauges.plot([0.0, 100.0], 4)  # col1 min -> low, col2 max -> full
    top_to_bottom = [r.plain[1] for r in rows]
    assert top_to_bottom == ["█", "█", "█", "█"]


def test_plot_min_column_only_bottom_row():
    rows = gauges.plot([0.0, 100.0], 4)
    col0 = [r.plain[0] for r in rows]
    assert col0[0] == " " and col0[1] == " " and col0[2] == " "
    assert col0[3] != " "  # smallest bar still shows one glyph at the base


def test_plot_all_none_dashes_top_blank_below():
    rows = gauges.plot([None, None], 3)
    assert rows[0].plain == "──"
    assert rows[1].plain == "  " and rows[2].plain == "  "


def test_plot_none_slot_is_gap_every_row():
    rows = gauges.plot([100.0, None, 100.0], 2)
    assert all(r.plain[1] == " " for r in rows)
