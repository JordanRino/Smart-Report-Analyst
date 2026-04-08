"""Strands agent orchestration (optional backend)."""

from __future__ import annotations

from typing import Any

__all__ = [
    "StrandsTurnState",
    "build_strands_tools",
    "create_strands_agent",
]


def __getattr__(name: str) -> Any:
    if name == "create_strands_agent":
        from smart_report_analyst.service.strands.agents import create_strands_agent as _fn

        return _fn
    if name == "StrandsTurnState":
        from smart_report_analyst.service.strands.tools import StrandsTurnState as _cls

        return _cls
    if name == "build_strands_tools":
        from smart_report_analyst.service.strands.tools import build_strands_tools as _fn

        return _fn
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
