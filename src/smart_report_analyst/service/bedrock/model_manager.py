"""BedrockModel factory for Strands."""

from __future__ import annotations

from botocore.config import Config as BotocoreConfig

from strands.models import BedrockModel

from smart_report_analyst.config.settings import get_settings
from smart_report_analyst.service.bedrock.guardrail_config import (
    bedrock_model_guardrail_kwargs,
)


def build_bedrock_model() -> BedrockModel:
    settings = get_settings()
    model_id = settings.BEDROCK_MODEL_ID
    if not model_id:
        raise ValueError("BEDROCK_MODEL_ID must be set when AGENT_BACKEND=strands.")

    boto_config = BotocoreConfig(
        retries={"max_attempts": 3, "mode": "standard"},
        connect_timeout=10,
        read_timeout=120,
    )
    # Apply the guardrails once the we have access to perform: bedrock:ApplyGuardrail perms
    # guardrail_kwargs = bedrock_model_guardrail_kwargs()
    return BedrockModel(
        model_id=model_id,
        region_name=settings.AWS_REGION,
        boto_client_config=boto_config,
        # **guardrail_kwargs,
    )
