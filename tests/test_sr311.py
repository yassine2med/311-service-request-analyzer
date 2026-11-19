from datetime import datetime

import pytest

from sr311.__main__ import main
from sr311.core import Request, analyze, format_table, load, percentile

NOW = datetime(2026, 3, 1, 0, 0)


def req(i, cat, opened, closed=None):
    return Request(i, cat, datetime.fromisoformat(opened), datetime.fromisoformat(closed) if closed else None)


def test_hours_to_close():
    assert req("1", "A", "2026-01-01T00:00", "2026-01-01T06:30").hours_to_close == 6.5


def test_hours_to_close_open_is_none():
    assert req("1", "A", "2026-01-01T00:00").hours_to_close is None


def test_percentile_nearest_rank():
    assert percentile([1, 2, 3, 4, 5, 6, 7, 8, 9, 10], 90) == 9


def test_percentile_single_value():
    assert percentile([4.0], 90) == 4.0


def test_percentile_empty():
    with pytest.raises(ValueError):
        percentile([], 50)


def test_analyze_median_and_counts():
    rows = [req("1", "A", "2026-01-01T00:00", "2026-01-01T02:00"),
            req("2", "A", "2026-01-01T00:00", "2026-01-01T10:00"),
            req("3", "A", "2026-02-01T00:00")]
    (s,) = analyze(rows, NOW)
    assert (s.total, s.closed, s.open, s.median_hours) == (3, 2, 1, 6.0)
    assert s.oldest_open_days == 28.0


def test_analyze_sorts_slowest_first():
    rows = [req("1", "Fast", "2026-01-01T00:00", "2026-01-01T01:00"),
            req("2", "Slow", "2026-01-01T00:00", "2026-01-05T00:00")]
    assert [s.category for s in analyze(rows, NOW)] == ["Slow", "Fast"]


def test_analyze_all_open_category_sorts_last():
    rows = [req("1", "Done", "2026-01-01T00:00", "2026-01-01T01:00"), req("2", "Pending", "2026-01-01T00:00")]
    stats = analyze(rows, NOW)
    assert stats[-1].category == "Pending" and stats[-1].median_hours is None


def test_format_table_dash_for_missing():
    text = format_table(analyze([req("1", "Pending", "2026-01-01T00:00")], NOW))
    assert "-" in text.splitlines()[-1]


def test_load_sample():
    assert len(load("data/requests.csv")) == 72


def test_load_closed_before_opened(tmp_path):
    f = tmp_path / "a.csv"
    f.write_text("request_id,category,opened,closed\n1,A,2026-01-02T00:00,2026-01-01T00:00\n")
    with pytest.raises(ValueError, match="closed before opened"):
        load(f)


def test_load_missing_column(tmp_path):
    f = tmp_path / "a.csv"
    f.write_text("request_id,category\n1,A\n")
    with pytest.raises(ValueError, match="missing columns"):
        load(f)


def test_cli_ok(capsys):
    assert main(["data/requests.csv", "--now", "2026-04-01T00:00"]) == 0
    assert "Category" in capsys.readouterr().out


def test_cli_bad_now():
    assert main(["data/requests.csv", "--now", "yesterday"]) == 2
