"""Service layer for smart_report_analyst."""

from __future__ import annotations

from typing import Any

from smart_report_analyst.service.bedrock.agent_manager import BedrockManager
from smart_report_analyst.service.lambda_function.manager import LambdaManager

__all__ = [
    "BedrockManager",
    "LambdaManager",
]

