"""Bedrock guardrail_config: create payload, get-or-create, model kwargs."""

from unittest.mock import MagicMock, patch

from smart_report_analyst.config.settings import Settings
from smart_report_analyst.service.bedrock.guardrail_config import (
    bedrock_model_guardrail_kwargs,
    build_sra_guardrail_create_request,
    create_sra_guardrail,
    get_or_create_sra_guardrail,
    reset_guardrail_cache_for_tests,
)


def test_build_sra_guardrail_create_request_shape():
    kw = build_sra_guardrail_create_request(name="test-gr")
    assert kw["name"] == "test-gr"
    assert "blockedInputMessaging" in kw
    assert "blockedOutputsMessaging" in kw
    assert "topicPolicyConfig" in kw
    assert "contentPolicyConfig" in kw
    assert "wordPolicyConfig" in kw
    assert "sensitiveInformationPolicyConfig" in kw

    topics = kw["topicPolicyConfig"]["topicsConfig"]
    assert len(topics) >= 1
    assert topics[0]["type"] == "DENY"

    filters = kw["contentPolicyConfig"]["filtersConfig"]
    types = {f["type"] for f in filters}
    assert "HATE" in types
    assert "MISCONDUCT" in types
    assert "PROMPT_ATTACK" in types

    pii = kw["sensitiveInformationPolicyConfig"]["piiEntitiesConfig"]
    pii_types = {e["type"] for e in pii}
    assert pii_types == {
        "ADDRESS",
        "AGE",
        "AWS_ACCESS_KEY",
        "AWS_SECRET_KEY",
        "CA_HEALTH_NUMBER",
        "CA_SOCIAL_INSURANCE_NUMBER",
        "CREDIT_DEBIT_CARD_CVV",
        "CREDIT_DEBIT_CARD_EXPIRY",
        "CREDIT_DEBIT_CARD_NUMBER",
        "DRIVER_ID",
        "EMAIL",
        "INTERNATIONAL_BANK_ACCOUNT_NUMBER",
        "IP_ADDRESS",
        "LICENSE_PLATE",
        "MAC_ADDRESS",
        "NAME",
        "PASSWORD",
        "PHONE",
        "PIN",
        "SWIFT_CODE",
        "UK_NATIONAL_HEALTH_SERVICE_NUMBER",
        "UK_NATIONAL_INSURANCE_NUMBER",
        "UK_UNIQUE_TAXPAYER_REFERENCE_NUMBER",
        "URL",
        "USERNAME",
        "US_BANK_ACCOUNT_NUMBER",
        "US_BANK_ROUTING_NUMBER",
        "US_INDIVIDUAL_TAX_IDENTIFICATION_NUMBER",
        "US_PASSPORT_NUMBER",
        "US_SOCIAL_SECURITY_NUMBER",
        "VEHICLE_IDENTIFICATION_NUMBER",
    }
    for e in pii:
        assert e["type"] in pii_types
        assert e["action"] == "ANONYMIZE"


def test_create_sra_guardrail_calls_client():
    client = MagicMock()
    client.create_guardrail.return_value = {"guardrailId": "g1", "version": "DRAFT"}
    out = create_sra_guardrail(client, name="custom")
    assert out["guardrailId"] == "g1"
    client.create_guardrail.assert_called_once()
    call_kw = client.create_guardrail.call_args.kwargs
    assert call_kw["name"] == "custom"


@patch("smart_report_analyst.service.bedrock.guardrail_config.get_settings")
def test_model_kwargs_empty_when_disabled(mock_get_settings: MagicMock) -> None:
    reset_guardrail_cache_for_tests()
    mock_get_settings.return_value = Settings.model_validate(
        {"BEDROCK_GUARDRAIL_ENABLED": False}
    )
    assert bedrock_model_guardrail_kwargs() == {}


@patch("smart_report_analyst.service.bedrock.guardrail_config.get_settings")
def test_get_or_create_reuses_from_list(mock_get_settings: MagicMock) -> None:
    reset_guardrail_cache_for_tests()
    client = MagicMock()
    client.list_guardrails.return_value = {
        "guardrails": [
            {
                "id": "existing-id",
                "name": "smart-report-analyst-sba-scope",
                "version": "DRAFT",
                "status": "READY",
            },
        ],
        "nextToken": None,
    }
    mock_get_settings.return_value = Settings.model_validate(
        {
            "BEDROCK_GUARDRAIL_ENABLED": True,
            "BEDROCK_GUARDRAIL_NAME": "smart-report-analyst-sba-scope",
        }
    )
    ident = get_or_create_sra_guardrail(client=client)
    assert ident.guardrail_id == "existing-id"
    assert ident.version == "DRAFT"
    client.create_guardrail.assert_not_called()

    kw = bedrock_model_guardrail_kwargs()
    assert kw["guardrail_id"] == "existing-id"
    client.create_guardrail.assert_not_called()

    reset_guardrail_cache_for_tests()


@patch("smart_report_analyst.service.bedrock.guardrail_config.get_settings")
def test_get_or_create_creates_when_missing(mock_get_settings: MagicMock) -> None:
    reset_guardrail_cache_for_tests()
    client = MagicMock()
    client.list_guardrails.return_value = {"guardrails": [], "nextToken": None}
    client.create_guardrail.return_value = {"guardrailId": "new-id", "version": "DRAFT"}

    mock_get_settings.return_value = Settings.model_validate(
        {
            "BEDROCK_GUARDRAIL_ENABLED": True,
            "BEDROCK_GUARDRAIL_NAME": "smart-report-analyst-sba-scope",
        }
    )
    ident = get_or_create_sra_guardrail(client=client)
    assert ident.guardrail_id == "new-id"
    client.create_guardrail.assert_called_once()

    reset_guardrail_cache_for_tests()
