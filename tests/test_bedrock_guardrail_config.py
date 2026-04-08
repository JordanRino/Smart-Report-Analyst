"""Mapping settings → Strands BedrockModel guardrail kwargs and create_guardrail builders."""

from unittest.mock import MagicMock

from smart_report_analyst.config.settings import Settings
from smart_report_analyst.service.bedrock.bedrock_guardrail_config import (
    bedrock_model_guardrail_kwargs,
    build_sra_guardrail_create_kwargs,
    create_sra_guardrail,
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


def test_build_sra_guardrail_create_kwargs_shape():
    kw = build_sra_guardrail_create_kwargs(name="test-gr")
    assert kw["name"] == "test-gr"
    assert "blockedInputMessaging" in kw
    assert "blockedOutputsMessaging" in kw
    assert "topicPolicyConfig" in kw
    assert "contentPolicyConfig" in kw
    topics = kw["topicPolicyConfig"]["topicsConfig"]
    assert len(topics) >= 1
    assert topics[0]["type"] == "DENY"
    filters = kw["contentPolicyConfig"]["filtersConfig"]
    types = {f["type"] for f in filters}
    assert "HATE" in types
    assert "VIOLENCE" in types


def test_create_sra_guardrail_calls_client():
    client = MagicMock()
    client.create_guardrail.return_value = {"guardrailId": "g1", "version": "DRAFT"}
    out = create_sra_guardrail(client, name="custom")
    assert out["guardrailId"] == "g1"
    client.create_guardrail.assert_called_once()
    call_kw = client.create_guardrail.call_args.kwargs
    assert call_kw["name"] == "custom"
    assert "topicPolicyConfig" in call_kw
