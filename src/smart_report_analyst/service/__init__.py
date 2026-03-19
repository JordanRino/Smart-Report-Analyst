"""Service layer for smart_report_analyst."""

from .bedrock.manager import BedrockManager

__all__ = [
    "BedrockManager",
]
