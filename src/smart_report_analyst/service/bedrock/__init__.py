"""AWS Bedrock service wrapper."""

from smart_report_analyst.service.bedrock.agent_manager import BedrockManager
from smart_report_analyst.service.bedrock.guardrail_config import (
    GuardrailIdentity,
    bedrock_model_guardrail_kwargs,
    build_sra_guardrail_create_kwargs,
    create_sra_guardrail,
    get_or_create_sra_guardrail,
)

__all__ = [
    "BedrockManager",
    "GuardrailIdentity",
    "bedrock_model_guardrail_kwargs",
    "build_sra_guardrail_create_kwargs",
    "create_sra_guardrail",
    "get_or_create_sra_guardrail",
]
