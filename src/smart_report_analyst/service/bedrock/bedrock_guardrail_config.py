"""Bedrock Guardrails: create via boto3 and attach to Strands ``BedrockModel``.

- **Provisioning**: ``bedrock.Client.create_guardrail`` (control plane) defines policies.
- **Runtime**: ``bedrock-runtime`` InvokeModel uses ``guardrailIdentifier`` / version from settings.

See: https://docs.aws.amazon.com/boto3/latest/reference/services/bedrock/client/create_guardrail.html
"""

from __future__ import annotations

from typing import Any

import boto3
from botocore.client import BaseClient

from smart_report_analyst.config.settings import Settings, get_settings

# Align with ``strands.guardrails.taxonomy.OFF_TOPIC_REFUSAL_MESSAGE`` (Bedrock blocked prompt text).
_DEFAULT_BLOCKED_INPUT = (
    "I can only help with analytical questions about SBA loan data in this application "
    "(exploring the database, metrics, trends, and SQL-backed reports). "
    "Please ask a question about the loan data or how to analyze it."
)
_DEFAULT_BLOCKED_OUTPUT = (
    "The assistant cannot provide that response in this application. "
    "Ask about SBA loan data analysis instead."
)


def bedrock_control_plane_client(*, region_name: str) -> BaseClient:
    """Bedrock management API (create/list/update guardrails), not InvokeModel."""
    return boto3.client("bedrock", region_name=region_name)


def bedrock_model_guardrail_kwargs(settings: Settings) -> dict[str, Any]:
    """
    Build kwargs for ``BedrockModel(..., **kwargs)`` when guardrail env vars are set.

    If ``BEDROCK_GUARDRAIL_ID`` is unset, returns an empty dict (no Bedrock guardrail).
    """
    gid = (settings.BEDROCK_GUARDRAIL_ID or "").strip()
    if not gid:
        return {}

    version = (settings.BEDROCK_GUARDRAIL_VERSION or "").strip() or "DRAFT"
    out: dict[str, Any] = {
        "guardrail_id": gid,
        "guardrail_version": version,
    }

    trace = (settings.BEDROCK_GUARDRAIL_TRACE or "").strip().lower()
    if trace in ("enabled", "disabled", "enabled_full"):
        out["guardrail_trace"] = trace  # type: ignore[assignment]

    if settings.BEDROCK_GUARDRAIL_REDACT_INPUT is not None:
        out["guardrail_redact_input"] = settings.BEDROCK_GUARDRAIL_REDACT_INPUT
    msg = (settings.BEDROCK_GUARDRAIL_REDACT_INPUT_MESSAGE or "").strip()
    if msg:
        out["guardrail_redact_input_message"] = msg

    if settings.BEDROCK_GUARDRAIL_REDACT_OUTPUT is not None:
        out["guardrail_redact_output"] = settings.BEDROCK_GUARDRAIL_REDACT_OUTPUT
    omsg = (settings.BEDROCK_GUARDRAIL_REDACT_OUTPUT_MESSAGE or "").strip()
    if omsg:
        out["guardrail_redact_output_message"] = omsg

    return out


def _content_filter(
    harm_type: str,
    *,
    input_strength: str = "MEDIUM",
    output_strength: str = "MEDIUM",
) -> dict[str, Any]:
    return {
        "type": harm_type,
        "inputStrength": input_strength,
        "outputStrength": output_strength,
        "inputAction": "BLOCK",
        "outputAction": "BLOCK",
        "inputEnabled": True,
        "outputEnabled": True,
    }


def build_sra_guardrail_create_kwargs(
    *,
    name: str = "smart-report-analyst-sba-scope",
    description: str = (
        "Restricts Smart Report Analyst to SBA loan data analytics; blocks general "
        "knowledge, time/weather, politics, macro/tax/legal/medical advice, and similar off-topic prompts."
    ),
    blocked_input_messaging: str | None = None,
    blocked_outputs_messaging: str | None = None,
    topic_tier: str = "CLASSIC",
    content_tier: str = "CLASSIC",
) -> dict[str, Any]:
    """
    Default ``**kwargs`` for ``bedrock.create_guardrail`` aligned with SRA product scope.

    Override any top-level key by passing through ``create_sra_guardrail(..., **overrides)``
    or by editing the returned dict before calling the client.
    """
    blocked_in = (blocked_input_messaging or _DEFAULT_BLOCKED_INPUT).strip()
    blocked_out = (blocked_outputs_messaging or _DEFAULT_BLOCKED_OUTPUT).strip()

    return {
        "name": name,
        "description": description,
        "blockedInputMessaging": blocked_in,
        "blockedOutputsMessaging": blocked_out,
        "topicPolicyConfig": {
            "topicsConfig": [
                {
                    "name": "OffTopicNonLoanAnalytics",
                    "definition": (
                        "Requests that are not about analyzing, filtering, aggregating, or reporting on "
                        "SBA or small-business loan records in this application's database. Includes: current "
                        "time or date, weather, sports, recipes, jokes, creative writing, homework, translation "
                        "unrelated to loan data, personal tax/legal/medical/investment advice, electoral or "
                        "partisan politics, global macroeconomics or central-bank policy unrelated to the loan "
                        "dataset, cryptocurrency trading, or other general chit-chat."
                    ),
                    "examples": [
                        "What time is it in Tokyo?",
                        "What's the weather this weekend?",
                        "Who should I vote for?",
                        "Give me tax advice for my LLC.",
                        "Should I buy Bitcoin?",
                        "Explain global inflation trends.",
                        "Write me a poem.",
                    ],
                    "type": "DENY",
                    "inputAction": "BLOCK",
                    "outputAction": "BLOCK",
                    "inputEnabled": True,
                    "outputEnabled": True,
                },
            ],
            "tierConfig": {"tierName": topic_tier},
        },
        "contentPolicyConfig": {
            "filtersConfig": [
                _content_filter("HATE"),
                _content_filter("VIOLENCE"),
                _content_filter("SEXUAL"),
                _content_filter("INSULTS"),
            ],
            "tierConfig": {"tierName": content_tier},
        },
    }


def create_sra_guardrail(
    client: BaseClient,
    **kwargs: Any,
) -> dict[str, Any]:
    """
    Call ``client.create_guardrail`` with SRA defaults, merged with ``kwargs`` (top-level only).

    Use a client from ``bedrock_control_plane_client(region_name=settings.AWS_REGION)``.
    Requires IAM permissions such as ``bedrock:CreateGuardrail`` on the account.

    Returns the API response (``guardrailId``, ``guardrailArn``, ``version``, ``createdAt``).
    """
    request = build_sra_guardrail_create_kwargs()
    request.update(kwargs)
    return client.create_guardrail(**request)


def create_sra_guardrail_from_settings(
    settings: Settings | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """Convenience: build control client from settings and create the default guardrail."""
    s = settings or get_settings()
    client = bedrock_control_plane_client(region_name=s.AWS_REGION)
    return create_sra_guardrail(client, **kwargs)
