"""Rule-based topic classifier for user turns (pre-model gate)."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from smart_report_analyst.service.strands.guardrails.taxonomy import (
    DENY_PHRASES,
    DENY_REGEX_RULES,
    IN_DOMAIN_PATTERNS,
    OFF_TOPIC_REFUSAL_MESSAGE,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class TopicClassification:
    """Result of evaluating a single user message."""

    allowed: bool
    reason: str
    refusal_message: str
    detail: str | None = None


def classify_user_message(user_text: str) -> TopicClassification:
    """
    Return whether the message should proceed to the Strands agent.

    Order:
    1. In-domain regex hints → allow (reduces false positives on loan analytics).
    2. Deny regex rules → block.
    3. Deny phrases → block.
    4. Otherwise allow.

    Empty strings are treated as allowed here; callers should handle empty input separately.
    """
    normalized = user_text.strip()
    if not normalized:
        return TopicClassification(
            allowed=True,
            reason="empty",
            refusal_message=OFF_TOPIC_REFUSAL_MESSAGE,
        )

    lower = normalized.lower()

    for pat in IN_DOMAIN_PATTERNS:
        if pat.search(lower):
            return TopicClassification(
                allowed=True,
                reason="in_domain_hint",
                refusal_message=OFF_TOPIC_REFUSAL_MESSAGE,
                detail=pat.pattern,
            )

    for rule in DENY_REGEX_RULES:
        if rule.pattern.search(lower):
            logger.info(
                "guardrail_topic_block",
                extra={"rule": rule.name, "pattern": rule.pattern.pattern},
            )
            return TopicClassification(
                allowed=False,
                reason="deny_regex",
                refusal_message=OFF_TOPIC_REFUSAL_MESSAGE,
                detail=rule.name,
            )

    for phrase in DENY_PHRASES:
        if phrase in lower:
            logger.info("guardrail_topic_block", extra={"rule": "deny_phrase", "phrase": phrase})
            return TopicClassification(
                allowed=False,
                reason="deny_phrase",
                refusal_message=OFF_TOPIC_REFUSAL_MESSAGE,
                detail=phrase,
            )

    return TopicClassification(
        allowed=True,
        reason="allowed_default",
        refusal_message=OFF_TOPIC_REFUSAL_MESSAGE,
    )
