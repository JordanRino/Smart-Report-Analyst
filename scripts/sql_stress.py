#!/usr/bin/env python3
"""Run concurrent SQL stress against ``AppDataLayer`` (production analytics path).

Requires MYSQL_HOST, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DB (and optional MYSQL_PORT)
via environment or ``.env`` — same as the main application.

Usage::

    uv run python scripts/sql_stress.py
    uv run python scripts/sql_stress.py --concurrency 50 --rounds 2

Exit code 0 only when every scheduled query succeeds (see report on stderr).
"""

from __future__ import annotations

import argparse
import asyncio
import sys


async def _async_main() -> int:
    from smart_report_analyst.service.persistence.mysql.sql_stress import (
        format_report,
        mysql_settings_configured,
        run_sql_concurrency_stress,
    )

    parser = argparse.ArgumentParser(description="Concurrent execute_generated_query stress test")
    parser.add_argument(
        "--concurrency",
        type=int,
        default=100,
        help="Overlapping queries per round (default: 100)",
    )
    parser.add_argument(
        "--rounds",
        type=int,
        default=1,
        help="Repeat the full concurrent batch (default: 1)",
    )
    parser.add_argument(
        "--no-warmup",
        action="store_true",
        help="Skip SELECT 1 warmup before the timed burst",
    )
    args = parser.parse_args()

    if not mysql_settings_configured():
        print(
            "Missing MySQL settings: set MYSQL_HOST, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DB.",
            file=sys.stderr,
        )
        return 2

    report = await run_sql_concurrency_stress(
        concurrency=args.concurrency,
        rounds=args.rounds,
        warmup=not args.no_warmup,
    )
    print(format_report(report), file=sys.stderr)
    return 0 if report.error_count == 0 else 1


def main() -> None:
    raise SystemExit(asyncio.run(_async_main()))


if __name__ == "__main__":
    main()
