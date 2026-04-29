#!/usr/bin/env python3
"""Run concurrent SQL stress against ``AppDataLayer`` (production analytics path).

Requires MYSQL_HOST, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DB (and optional MYSQL_PORT)
via environment or ``.env`` — same as the main application.

Usage (many EC2 images have ``python3`` but not ``python`` on PATH)::

    uv sync
    uv run python scripts/sql_stress.py --concurrency 100 --rounds 1

Do **not** use the OS ``python3`` if it is older than 3.13 — this package targets
Python **>= 3.13** (see ``pyproject.toml``). ``uv run`` uses the project's venv.

Exit code 0 only when every scheduled query succeeds (see report on stderr).
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

# Allow `python scripts/sql_stress.py` from repo root without a prior `pip install -e .`
_REPO_ROOT = Path(__file__).resolve().parent.parent
_SRC = _REPO_ROOT / "src"
if _SRC.is_dir():
    sys.path.insert(0, str(_SRC))

_MIN_PY = (3, 13)


def _ensure_python_and_package() -> None:
    if sys.version_info < _MIN_PY:
        print(
            f"Need Python {_MIN_PY[0]}.{_MIN_PY[1]}+ (this interpreter is "
            f"{sys.version_info.major}.{sys.version_info.minor}).\n"
            "From the repo root:\n"
            "  uv sync\n"
            "  uv run python scripts/sql_stress.py [args]\n",
            file=sys.stderr,
        )
        raise SystemExit(2)
    try:
        import smart_report_analyst  # noqa: F401
    except ImportError as e:
        print(
            "Cannot import smart_report_analyst. From the repo root run:\n"
            "  uv sync\n"
            "  uv run python scripts/sql_stress.py [args]\n"
            f"Original error: {e}",
            file=sys.stderr,
        )
        raise SystemExit(2) from e


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
    _ensure_python_and_package()
    raise SystemExit(asyncio.run(_async_main()))


if __name__ == "__main__":
    main()
