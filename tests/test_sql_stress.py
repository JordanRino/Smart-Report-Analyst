"""Unit tests for SQL stress helpers (no DB). Integration test is opt-in."""

from __future__ import annotations

import asyncio
import os

import pytest

from smart_report_analyst.service.persistence.mysql import sql_stress


def test_percentile_edges() -> None:
    assert sql_stress._percentile([], 50) == 0.0
    assert sql_stress._percentile([10.0], 50) == 10.0
    xs = [1.0, 2.0, 3.0, 4.0, 100.0]
    assert sql_stress._percentile(sorted(xs), 50) == 3.0


def test_sba_loans_queries_non_empty_and_read_only_shape() -> None:
    assert len(sql_stress.SBA_LOANS_STRESS_QUERIES) >= 1
    for q in sql_stress.SBA_LOANS_STRESS_QUERIES:
        low = q.strip().lower()
        assert "sba_loans" in low
        assert low.startswith("select")


@pytest.mark.stress
def test_sql_stress_integration_live_mysql() -> None:
    """Runs only when RUN_SQL_STRESS=1 and MYSQL_* are configured."""
    if os.environ.get("RUN_SQL_STRESS") != "1":
        pytest.skip("Set RUN_SQL_STRESS=1 to run live MySQL stress test")
    if not sql_stress.mysql_settings_configured():
        pytest.skip("MYSQL_* not configured")

    async def _run() -> sql_stress.SqlStressReport:
        return await sql_stress.run_sql_concurrency_stress(
            concurrency=5,
            rounds=1,
            warmup=True,
        )

    report = asyncio.run(_run())
    assert report.scheduled == 5
    assert report.success_count == 5
    assert report.error_count == 0
