"""AWS Bedrock service wrapper."""

from smart_report_analyst.service.bedrock.agent_manager import BedrockManager
from smart_report_analyst.service.bedrock.guardrail_config import (
    bedrock_model_guardrail_kwargs,
    build_sra_guardrail_create_kwargs,
    create_sra_guardrail,
    create_sra_guardrail_from_settings,
)

__all__ = [
    "BedrockManager",
    "bedrock_model_guardrail_kwargs",
    "build_sra_guardrail_create_kwargs",
    "create_sra_guardrail",
    "create_sra_guardrail_from_settings",
]
