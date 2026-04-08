"""Mapping settings → Strands BedrockModel guardrail kwargs."""

from smart_report_analyst.config.settings import Settings
from smart_report_analyst.service.strands.guardrails.bedrock_guardrail_config import (
    bedrock_model_guardrail_kwargs,
)


def test_empty_kwargs_without_guardrail_id():
    s = Settings.model_validate(
        {
            "BEDROCK_GUARDRAIL_ID": None,
            "BEDROCK_GUARDRAIL_VERSION": None,
        }
    )
    assert bedrock_model_guardrail_kwargs(s) == {}


def test_kwargs_with_id_and_defaults():
    s = Settings.model_validate(
        {
            "BEDROCK_GUARDRAIL_ID": "abc123",
            "BEDROCK_GUARDRAIL_VERSION": None,
        }
    )
    kw = bedrock_model_guardrail_kwargs(s)
    assert kw["guardrail_id"] == "abc123"
    assert kw["guardrail_version"] == "DRAFT"


def test_kwargs_passes_trace_and_redact():
    s = Settings.model_validate(
        {
            "BEDROCK_GUARDRAIL_ID": "gr1",
            "BEDROCK_GUARDRAIL_VERSION": "5",
            "BEDROCK_GUARDRAIL_TRACE": "enabled_full",
            "BEDROCK_GUARDRAIL_REDACT_INPUT": True,
            "BEDROCK_GUARDRAIL_REDACT_INPUT_MESSAGE": "blocked",
            "BEDROCK_GUARDRAIL_REDACT_OUTPUT": False,
            "BEDROCK_GUARDRAIL_REDACT_OUTPUT_MESSAGE": "",
        }
    )
    kw = bedrock_model_guardrail_kwargs(s)
    assert kw["guardrail_trace"] == "enabled_full"
    assert kw["guardrail_redact_input"] is True
    assert kw["guardrail_redact_input_message"] == "blocked"
    assert kw["guardrail_redact_output"] is False
    assert "guardrail_redact_output_message" not in kw
