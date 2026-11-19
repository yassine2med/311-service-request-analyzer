"""Time-to-close statistics for 311 style service requests."""
from __future__ import annotations

import csv
import math
import statistics
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

REQUIRED = ("request_id", "category", "opened", "closed")


@dataclass(frozen=True)
class Request:
    request_id: str
    category: str
    opened: datetime
    closed: datetime | None

    @property
    def hours_to_close(self) -> float | None:
        """Hours between open and close, or None while still open."""
        if self.closed is None:
            return None
        return (self.closed - self.opened).total_seconds() / 3600


@dataclass(frozen=True)
class CategoryStats:
    category: str
    total: int
    closed: int
    open: int
    median_hours: float | None
    p90_hours: float | None
    oldest_open_days: float | None


def load(path: str | Path) -> list[Request]:
    """Read requests from CSV. A blank closed value means the request is open."""
    with open(path, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        missing = [c for c in REQUIRED if c not in (reader.fieldnames or [])]
        if missing:
            raise ValueError(f"missing columns: {', '.join(missing)}")
        rows = []
        for line, row in enumerate(reader, start=2):
            try:
                opened = datetime.fromisoformat(row["opened"])
                closed = datetime.fromisoformat(row["closed"]) if row["closed"].strip() else None
            except ValueError as exc:
                raise ValueError(f"line {line}: {exc}") from exc
            if closed is not None and closed < opened:
                raise ValueError(f"line {line}: closed before opened")
            rows.append(Request(row["request_id"].strip(), row["category"].strip(), opened, closed))
    return rows


def percentile(values: list[float], pct: float) -> float:
    """Nearest-rank percentile. Raises ValueError on an empty list."""
    if not values:
        raise ValueError("no values")
    ordered = sorted(values)
    rank = max(1, math.ceil(pct / 100 * len(ordered)))
    return ordered[rank - 1]


def analyze(rows: list[Request], now: datetime) -> list[CategoryStats]:
    """Per-category stats, slowest median first. Categories with no closed request sort last."""
    groups: dict[str, list[Request]] = {}
    for r in rows:
        groups.setdefault(r.category, []).append(r)
    out = []
    for cat, items in groups.items():
        hours = [h for r in items if (h := r.hours_to_close) is not None]
        open_items = [r for r in items if r.closed is None]
        oldest = max(((now - r.opened).total_seconds() / 86400 for r in open_items), default=None)
        out.append(CategoryStats(cat, len(items), len(hours), len(open_items),
                                 statistics.median(hours) if hours else None,
                                 percentile(hours, 90) if hours else None, oldest))
    return sorted(out, key=lambda s: (s.median_hours is None, -(s.median_hours or 0), s.category))


def format_table(stats: list[CategoryStats]) -> str:
    """Plain text table."""
    def num(v: float | None) -> str:
        return "-" if v is None else f"{v:.1f}"
    head = f"{'Category':<22}{'Total':>6}{'Open':>6}{'Median h':>10}{'P90 h':>9}{'Oldest open d':>15}"
    lines = [head, "-" * len(head)]
    for s in stats:
        lines.append(f"{s.category:<22}{s.total:>6}{s.open:>6}{num(s.median_hours):>10}{num(s.p90_hours):>9}{num(s.oldest_open_days):>15}")
    return "\n".join(lines)
