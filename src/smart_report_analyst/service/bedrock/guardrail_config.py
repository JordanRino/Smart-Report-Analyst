"""Bedrock Guardrails: provision with boto3 and resolve id/version for ``BedrockModel``.

Uses ``list_guardrails`` + ``create_guardrail`` (control plane). Inference attaches the
resolved guardrail via Strands ``BedrockModel`` kwargs.

PII ``type`` values must match Bedrock's allowed enum exactly.
See: https://docs.aws.amazon.com/boto3/latest/reference/services/bedrock/client/create_guardrail.html
"""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass
from typing import Any

import boto3
from botocore.client import BaseClient

from smart_report_analyst.config.settings import get_settings

logger = logging.getLogger(__name__)

DEFAULT_SRA_GUARDRAIL_NAME = "smart-report-analyst-sba-scope"

_DEFAULT_BLOCKED_INPUT = (
    "I can only help with analytical questions about SBA loan data in this application "
    "(exploring the database, metrics, trends, and SQL-backed reports). "
    "Please ask a question about the loan data or how to analyze it."
)
_DEFAULT_BLOCKED_OUTPUT = (
    "The assistant cannot provide that response in this application. "
    "Ask about SBA loan data analysis instead."
)

# Bedrock API enum for ``piiEntitiesConfig[].type`` (must match exactly).
_PII_TYPES_FOR_SRA: tuple[str, ...] = (
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
)

_guardrail_resolve_lock = threading.Lock()
_resolved_guardrail: dict[str, Any] | None = None


@dataclass(frozen=True)
class GuardrailIdentity:
    """Identifiers returned from list/create for use with InvokeModel."""

    guardrail_id: str
    version: str


def bedrock_control_plane_client(*, region_name: str) -> BaseClient:
    return boto3.client("bedrock", region_name=region_name)


def _pii_entity(pii_type: str) -> dict[str, Any]:
    return {
        "type": pii_type,
        "action": "ANONYMIZE",
        "inputAction": "ANONYMIZE",
        "outputAction": "ANONYMIZE",
        "inputEnabled": True,
        "outputEnabled": True,
    }


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


def build_sra_guardrail_create_request(
    *,
    name: str,
    description: str = (
        "Smart Report Analyst: SBA loan analytics scope; denied off-topic prompts; "
        "content and PII safeguards."
    ),
    blocked_input_messaging: str | None = None,
    blocked_outputs_messaging: str | None = None,
    topic_tier: str = "CLASSIC",
    content_tier: str = "CLASSIC",
) -> dict[str, Any]:
    """Full ``create_guardrail`` request body for the SRA default guardrail."""
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
                    "name": "ChitChatAndGeneral",
                    "definition": "Time, date, weather, sports, jokes, creative writing, homework, or general conversation unrelated to SBA loan data.",
                    "examples": [
                        "What time is it in Tokyo?",
                        "What's the weather today?",
                        "Who won the game?",
                        "Tell me a joke.",
                        "Help me with my homework."
                    ],
                    "type": "DENY",
                    "inputAction": "BLOCK",
                    "outputAction": "BLOCK",
                    "inputEnabled": True,
                    "outputEnabled": True,
                },
                {
                    "name": "ProfessionalAdvice",
                    "definition": "Personal tax, legal, medical, or investment advice. Includes cryptocurrency trading, electoral, or partisan politics.",
                    "examples": [
                        "Give me tax advice for my LLC.",
                        "Should I buy Bitcoin?",
                        "Who should I vote for?",
                        "Legal help for my business.",
                        "Medical symptoms check."
                    ],
                    "type": "DENY",
                    "inputAction": "BLOCK",
                    "outputAction": "BLOCK",
                    "inputEnabled": True,
                    "outputEnabled": True,
                },
                {
                    "name": "EconomicsAndMisc",
                    "definition": "Global macroeconomics, central-bank policy, recipes, or non-loan translation services.",
                    "examples": [
                        "Explain global inflation trends.",
                        "Give me a brownie recipe.",
                        "Translate this to Spanish.",
                        "What is the Fed doing with rates?",
                        "How do I cook pasta?"
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
                _content_filter("MISCONDUCT"),
                # Manually define prompt attack to avoid the strength error
                {
                    "type": "PROMPT_ATTACK",
                    "inputStrength": "MEDIUM",
                    "outputStrength": "NONE", # This MUST be NONE
                    "inputAction": "BLOCK",
                    "outputAction": "NONE",  # Recommended as output check isn't applicable
                    "inputEnabled": True,
                    "outputEnabled": False, # Recommended
                },
            ],
            "tierConfig": {"tierName": content_tier},
        },
        "wordPolicyConfig": {
            "managedWordListsConfig": [
                {
                    "type": "PROFANITY",
                    "inputAction": "BLOCK",
                    "outputAction": "BLOCK",
                    "inputEnabled": True,
                    "outputEnabled": True,
                },
            ],
        },
        "sensitiveInformationPolicyConfig": {
            "piiEntitiesConfig": [_pii_entity(t) for t in _PII_TYPES_FOR_SRA],
        },
    }


def _list_all_guardrails(client: BaseClient) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    token: str | None = None
    while True:
        req: dict[str, Any] = {"maxResults": 50}
        if token:
            req["nextToken"] = token
        resp = client.list_guardrails(**req)
        out.extend(resp.get("guardrails") or [])
        token = resp.get("nextToken")
        if not token:
            break
    return out


def find_existing_sra_guardrail(
    client: BaseClient,
    *,
    name: str,
) -> dict[str, Any] | None:
    """Return one list_guardrails entry for ``name``, preferring ``READY`` status."""
    matches = [g for g in _list_all_guardrails(client) if g.get("name") == name]
    if not matches:
        return None
    for g in matches:
        if g.get("status") == "READY":
            return g
    return matches[0]


def create_sra_guardrail(
    client: BaseClient,
    *,
    name: str,
    **overrides: Any,
) -> dict[str, Any]:
    body = build_sra_guardrail_create_request(name=name)
    body.update(overrides)
    return client.create_guardrail(**body)


def get_or_create_sra_guardrail(
    *,
    client: BaseClient | None = None,
) -> GuardrailIdentity:
    """
    Resolve guardrail id + version: find by configured name, else ``create_guardrail``.

    Cached per process after first successful resolution.
    """
    global _resolved_guardrail  # noqa: PLW0603 — intentional module singleton

    settings = get_settings()
    if _resolved_guardrail is not None:
        return GuardrailIdentity(
            guardrail_id=_resolved_guardrail["guardrail_id"],
            version=_resolved_guardrail["version"],
        )

    with _guardrail_resolve_lock:
        if _resolved_guardrail is not None:
            return GuardrailIdentity(
                guardrail_id=_resolved_guardrail["guardrail_id"],
                version=_resolved_guardrail["version"],
            )

        c = client or bedrock_control_plane_client(region_name=settings.AWS_REGION)
        name = (settings.BEDROCK_GUARDRAIL_NAME or DEFAULT_SRA_GUARDRAIL_NAME).strip()

        existing = find_existing_sra_guardrail(c, name=name)
        if existing:
            gid = existing.get("id") or ""
            ver = (existing.get("version") or "DRAFT").strip() or "DRAFT"
            if not gid:
                raise RuntimeError("list_guardrails entry missing id")
            logger.info(
                "bedrock_guardrail_reuse",
                extra={"guardrail_id": gid, "version": ver, "name": name},
            )
            _resolved_guardrail = {"guardrail_id": gid, "version": ver}
            return GuardrailIdentity(guardrail_id=gid, version=ver)

        resp = create_sra_guardrail(c, name=name)
        gid = resp.get("guardrailId") or ""
        ver = (resp.get("version") or "DRAFT").strip() or "DRAFT"
        if not gid:
            raise RuntimeError("create_guardrail response missing guardrailId")
        logger.info(
            "bedrock_guardrail_created",
            extra={"guardrail_id": gid, "version": ver, "name": name},
        )
        _resolved_guardrail = {"guardrail_id": gid, "version": ver}
        return GuardrailIdentity(guardrail_id=gid, version=ver)


def bedrock_model_guardrail_kwargs() -> dict[str, Any]:
    """
    Kwargs for Strands ``BedrockModel`` after resolving guardrail via get-or-create.

    Empty dict when ``BEDROCK_GUARDRAIL_ENABLED`` is false.
    """
    settings = get_settings()
    if not settings.BEDROCK_GUARDRAIL_ENABLED:
        return {}

    sra_guardrail = get_or_create_sra_guardrail()
    out: dict[str, Any] = {
        "guardrail_id": sra_guardrail.guardrail_id,
        "guardrail_version": sra_guardrail.version,
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


def reset_guardrail_cache_for_tests() -> None:
    """Clear process cache (tests only)."""
    global _resolved_guardrail  # noqa: PLW0603
    _resolved_guardrail = None


build_sra_guardrail_create_kwargs = build_sra_guardrail_create_request

