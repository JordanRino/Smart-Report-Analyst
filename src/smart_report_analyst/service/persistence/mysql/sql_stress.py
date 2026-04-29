"""Concurrent SQL stress harness for ``AppDataLayer.execute_generated_query``.

Uses the same MySQL pool and code path as production analytics SQL (no HTTP / Strands).
Queries target ``sba_loans`` — align columns with your warehouse schema if needed.
"""

from __future__ import annotations

import asyncio
import math
import time
from dataclasses import dataclass, field
from typing import Sequence

from smart_report_analyst.config.settings import get_settings
from smart_report_analyst.service.persistence.mysql.app_data_layer import app_data_layer

# Read-only patterns adapted from repo sample question SQL; table name is ``sba_loans``.
SBA_LOANS_STRESS_QUERIES: tuple[str, ...] = (
    "SELECT DISTINCT Bank FROM sba_loans",
    "SELECT * FROM sba_loans WHERE Bank = 'Wells Fargo' LIMIT 10",
    "SELECT COUNT(*) AS n FROM sba_loans",
    "SELECT Bank, COUNT(*) AS total_loans FROM sba_loans GROUP BY Bank ORDER BY total_loans DESC",
    "SELECT COUNT(*) AS n FROM sba_loans WHERE MIS_Status = 'CHGOFF'",
    "SELECT COUNT(*) AS n FROM sba_loans WHERE Bank = 'Bank of America' AND MIS_Status = 'P I F'",
    "SELECT Bank, SUM(DisbursementGross) AS total_disbursed FROM sba_loans GROUP BY Bank ORDER BY total_disbursed DESC",
    """SELECT Bank, COUNT(*) AS charged_off_loans FROM sba_loans WHERE MIS_Status = 'CHGOFF'
GROUP BY Bank ORDER BY charged_off_loans DESC""",
    """SELECT Bank, COUNT(*) AS total_loans, SUM(DisbursementGross) AS total_disbursed,
AVG(DisbursementGross) AS avg_loan_size FROM sba_loans GROUP BY Bank ORDER BY total_disbursed DESC""",
    """SELECT Bank,
SUM(CASE WHEN MIS_Status = 'CHGOFF' THEN 1 ELSE 0 END) AS charged_off,
COUNT(*) AS total_loans,
SUM(CASE WHEN MIS_Status = 'CHGOFF' THEN 1 ELSE 0 END) / COUNT(*) AS default_rate
FROM sba_loans GROUP BY Bank ORDER BY default_rate DESC""",
    """SELECT State, SUM(DisbursementGross) AS total_disbursement FROM sba_loans GROUP BY State
ORDER BY total_disbursement DESC LIMIT 1""",
)


def mysql_settings_configured() -> bool:
    """True when Pydantic settings have minimum fields for a live MySQL connection."""
    s = get_settings()
    return bool(s.MYSQL_HOST and s.MYSQL_USER and s.MYSQL_PASSWORD and s.MYSQL_DB)


def _percentile(sorted_vals: list[float], p: float) -> float:
    if not sorted_vals:
        return 0.0
    xs = sorted_vals
    k = (len(xs) - 1) * (p / 100.0)
    lo = int(math.floor(k))
    hi = int(math.ceil(k))
    if lo == hi:
        return xs[lo]
    return xs[lo] * (hi - k) + xs[hi] * (k - lo)


@dataclass
class SqlStressReport:
    concurrency: int
    """How many concurrent tasks were scheduled."""

    scheduled: int
    """Tasks actually started (``concurrency`` × ``rounds``)."""

    success_count: int
    error_count: int
    wall_time_seconds: float
    latency_ms: dict[str, float]
    """min, max, p50, p95, p99 — end-to-end per task (queue + execute + fetch)."""

    error_messages_sample: list[str] = field(default_factory=list)
    """First distinct error ``message`` strings from failed results (capped)."""


async def run_sql_concurrency_stress(
    *,
    concurrency: int = 100,
    queries: Sequence[str] | None = None,
    rounds: int = 1,
    close_pool_after: bool = True,
    warmup: bool = True,
) -> SqlStressReport:
    """Run ``execute_generated_query`` concurrently via ``asyncio.gather``.

    Each task picks ``queries[i % len(queries)]``. ``to_store`` is always ``False`` (read-only).

    Args:
        concurrency: Number of overlapping tasks per round.
        queries: SQL strings; defaults to ``SBA_LOANS_STRESS_QUERIES``.
        rounds: Repeat the full concurrent batch this many times (total tasks = concurrency × rounds).
        close_pool_after: If True, ``close()`` the shared ``app_data_layer`` pool when done
            so connection counts drop before other code runs in-process.
        warmup: If True, run one ``SELECT 1`` through the layer before the timed burst.
    """
    if concurrency < 1:
        raise ValueError("concurrency must be >= 1")
    if rounds < 1:
        raise ValueError("rounds must be >= 1")
    qlist = tuple(queries) if queries is not None else SBA_LOANS_STRESS_QUERIES
    if not qlist:
        raise ValueError("queries must be non-empty")

    scheduled = concurrency * rounds

    if warmup:
        ping = await app_data_layer.execute_generated_query(
            "SELECT 1 AS ok", "stress-warmup", False
        )
        if ping.get("error"):
            raise RuntimeError(
                f"Warmup failed: {ping.get('message', ping)} — check MYSQL_* settings and network."
            )

    async def one_task(task_index: int) -> tuple[bool, float, str | None]:
        sql = qlist[task_index % len(qlist)]
        label = f"stress-{task_index}"
        t0 = time.perf_counter()
        body = await app_data_layer.execute_generated_query(sql, label, False)
        dt_ms = (time.perf_counter() - t0) * 1000.0
        if body.get("error"):
            msg = str(body.get("message") or "unknown error")
            return False, dt_ms, msg
        return True, dt_ms, None

    t_wall0 = time.perf_counter()
    outcomes: list[tuple[bool, float, str | None]] = []
    for r in range(rounds):
        base = r * concurrency
        batch = await asyncio.gather(
            *[one_task(base + i) for i in range(concurrency)],
        )
        outcomes.extend(batch)
    wall = time.perf_counter() - t_wall0

    successes = sum(1 for ok, _, _ in outcomes if ok)
    errors = len(outcomes) - successes
    latencies_ms = [dt for _, dt, _ in outcomes]

    err_sample: list[str] = []
    seen_err: set[str] = set()
    for ok, _, em in outcomes:
        if ok or not em:
            continue
        if em not in seen_err and len(err_sample) < 8:
            seen_err.add(em)
            err_sample.append(em)

    lat_sorted = sorted(latencies_ms)
    report = SqlStressReport(
        concurrency=concurrency,
        scheduled=scheduled,
        success_count=successes,
        error_count=errors,
        wall_time_seconds=wall,
        latency_ms={
            "min": lat_sorted[0] if lat_sorted else 0.0,
            "max": lat_sorted[-1] if lat_sorted else 0.0,
            "p50": _percentile(lat_sorted, 50),
            "p95": _percentile(lat_sorted, 95),
            "p99": _percentile(lat_sorted, 99),
        },
        error_messages_sample=err_sample,
    )

    if close_pool_after:
        await app_data_layer.close()

    return report


def format_report(report: SqlStressReport) -> str:
    """Human-readable summary for logs or CLI."""
    lines = [
        f"SQL stress: scheduled={report.scheduled} (concurrency={report.concurrency})",
        f"  success={report.success_count}  errors={report.error_count}",
        f"  wall_time_s={report.wall_time_seconds:.3f}",
        "  latency_ms: "
        + " ".join(f"{k}={v:.2f}" for k, v in sorted(report.latency_ms.items())),
    ]
    if report.error_messages_sample:
        lines.append("  error_sample:")
        for e in report.error_messages_sample:
            lines.append(f"    - {e[:300]}")
    return "\n".join(lines)
