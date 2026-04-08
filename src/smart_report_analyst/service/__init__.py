"""Service layer for smart_report_analyst."""

from __future__ import annotations

from typing import Any

from smart_report_analyst.service.bedrock.agent_manager import BedrockManager
from smart_report_analyst.service.lambda_function.manager import LambdaManager

__all__ = [
    "BedrockManager",
    "LambdaManager",
    "run_app",
]


def __getattr__(name: str) -> Any:
    if name == "run_app":
        from smart_report_analyst.service.streamlit.manager import run_app as _run_app

        return _run_app
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
