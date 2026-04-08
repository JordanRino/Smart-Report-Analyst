"""Map application settings to Strands ``BedrockModel`` guardrail kwargs.

Amazon Bedrock guardrails are created and versioned in AWS (``bedrock.create_guardrail`` and
related APIs). At runtime, ``InvokeModel`` / streaming calls can attach ``guardrailIdentifier``
and ``guardrailVersion`` so evaluation runs on the prompt (and optionally the completion).

See: https://docs.aws.amazon.com/boto3/latest/reference/services/bedrock/client/create_guardrail.html
"""

from __future__ import annotations

from typing import Any

from smart_report_analyst.config.settings import Settings


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
