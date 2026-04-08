"""Rule-based topic classifier for user turns (pre-model gate)."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from smart_report_analyst.service.strands.guardrails.taxonomy import (
    DENY_PHRASES_ALWAYS,
    DENY_PHRASES_WITHOUT_DOMAIN,
    DENY_REGEX_RULES_ALWAYS,
    DENY_REGEX_RULES_WITHOUT_DOMAIN,
    DOMAIN_HINT_PATTERNS,
    DOMAIN_HINT_THRESHOLD_FOR_OFF_TOPIC_OVERRIDE,
    OFF_TOPIC_REFUSAL_MESSAGE,
    normalize_for_classification,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class TopicClassification:
    """Result of evaluating a single user message."""

    allowed: bool
    reason: str
    refusal_message: str
    detail: str | None = None


def _count_domain_hints(lower: str) -> int:
    """How many distinct domain-hint patterns match (used to reduce false blocks)."""
    return sum(1 for pat in DOMAIN_HINT_PATTERNS if pat.search(lower))


def classify_user_message(user_text: str) -> TopicClassification:
    """
    Return whether the message should proceed to the Strands agent.

    1. Normalize (Unicode NFKC, collapse whitespace).
    2. ``deny_always`` regex and phrases → block.
    3. ``only_without_domain`` regex/phrases → block only if domain-hint count is below
       ``DOMAIN_HINT_THRESHOLD_FOR_OFF_TOPIC_OVERRIDE``.
    4. Otherwise allow (strong domain context can coexist with a casual phrase).

    Empty input is allowed here; callers treat empty separately for streaming.
    """
    normalized = normalize_for_classification(user_text)
    if not normalized:
        return TopicClassification(
            allowed=True,
            reason="empty",
            refusal_message=OFF_TOPIC_REFUSAL_MESSAGE,
        )

    lower = normalized.lower()
    hints = _count_domain_hints(lower)

    def _block(rule_name: str, reason: str, detail: str | None = None) -> TopicClassification:
        logger.info(
            "guardrail_topic_block",
            extra={"rule": rule_name, "reason": reason, "domain_hints": hints, "detail": detail},
        )
        return TopicClassification(
            allowed=False,
            reason=reason,
            refusal_message=OFF_TOPIC_REFUSAL_MESSAGE,
            detail=detail,
        )

    for rule in DENY_REGEX_RULES_ALWAYS:
        if rule.pattern.search(lower):
            return _block(rule.name, "deny_regex", rule.name)

    for phrase in DENY_PHRASES_ALWAYS:
        if phrase in lower:
            return _block("deny_phrase", "deny_phrase", phrase)

    weak_domain = hints < DOMAIN_HINT_THRESHOLD_FOR_OFF_TOPIC_OVERRIDE

    if weak_domain:
        for rule in DENY_REGEX_RULES_WITHOUT_DOMAIN:
            if rule.pattern.search(lower):
                return _block(rule.name, "deny_regex", rule.name)

        for phrase in DENY_PHRASES_WITHOUT_DOMAIN:
            if phrase in lower:
                return _block("deny_phrase", "deny_phrase", phrase)

    if hints >= 1:
        return TopicClassification(
            allowed=True,
            reason="in_domain_hint",
            refusal_message=OFF_TOPIC_REFUSAL_MESSAGE,
            detail=str(hints),
        )

    return TopicClassification(
        allowed=True,
        reason="allowed_default",
        refusal_message=OFF_TOPIC_REFUSAL_MESSAGE,
    )
