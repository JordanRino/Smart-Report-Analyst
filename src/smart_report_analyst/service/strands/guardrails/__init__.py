"""Topic and safety guardrails for Strands turns (rules + optional Bedrock guardrails)."""

from smart_report_analyst.service.bedrock.guardrail_config import (
    bedrock_model_guardrail_kwargs,
)
from smart_report_analyst.service.strands.guardrails.classifier import (
    TopicClassification,
    classify_user_message,
)
from smart_report_analyst.service.strands.guardrails.taxonomy import (
    OFF_TOPIC_REFUSAL_MESSAGE,
)

__all__ = [
    "OFF_TOPIC_REFUSAL_MESSAGE",
    "TopicClassification",
    "bedrock_model_guardrail_kwargs",
    "classify_user_message",
]
