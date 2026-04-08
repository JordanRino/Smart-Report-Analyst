"""Structured allow/deny signals for pre-model topic filtering.

Bedrock Guardrails (configured in AWS via ``create_guardrail``) complement this layer by
evaluating prompts at inference time (denied topics, content filters, PII, etc.). This module
holds fast, deterministic rules so obvious off-topic turns never reach the model when
they match.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# User-visible copy when a deterministic rule blocks the turn (also align with Bedrock
# guardrail blockedInputMessaging in the AWS console if you use both).
OFF_TOPIC_REFUSAL_MESSAGE = (
    "I can only help with analytical questions about SBA loan data in this application "
    "(exploring the database, metrics, trends, and SQL-backed reports). "
    "Please ask a question about the loan data or how to analyze it."
)


@dataclass(frozen=True)
class DenyRegexRule:
    """A compiled pattern tagged for logging/tests."""

    name: str
    pattern: re.Pattern[str]


# Strong signals the user is asking about this product's domain; if present, we skip
# deny rules to avoid false blocks (e.g. "SBA" appearing in an otherwise odd phrasing).
IN_DOMAIN_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\bsba\b", re.I),
    re.compile(r"small\s+business\s+administration", re.I),
    re.compile(r"\b7\s*\(?a\)?\b", re.I),  # 7(a) program
    re.compile(r"\b504\s+loan\b", re.I),
    re.compile(r"\b504\s+program\b", re.I),
    re.compile(r"\bmis_status\b", re.I),
    re.compile(r"\bcharge[\s-]?off\b", re.I),
    re.compile(r"\bpif\b", re.I),
    re.compile(r"\bbank\b.*\bloan", re.I),
    re.compile(r"\bloan\b.*\b(default|count|volume|total|average|sum|trend)", re.I),
)


# Deterministic off-topic detectors (time, weather, general knowledge, politics, etc.).
DENY_REGEX_RULES: tuple[DenyRegexRule, ...] = (
    DenyRegexRule("time_now", re.compile(r"\bwhat\s+time\b", re.I)),
    DenyRegexRule("current_time", re.compile(r"\bcurrent\s+time\b", re.I)),
    DenyRegexRule("what_day", re.compile(r"\bwhat\s+day\b", re.I)),
    DenyRegexRule("todays_date", re.compile(r"\btoday'?s\s+date\b", re.I)),
    DenyRegexRule("weather", re.compile(r"\bweather\b", re.I)),
    DenyRegexRule("forecast", re.compile(r"\bforecast\b", re.I)),
    DenyRegexRule("stock_ticker", re.compile(r"\bstock\s+(price|market)\b", re.I)),
    DenyRegexRule("crypto_bitcoin", re.compile(r"\b(bitcoin|ethereum|crypto)\b", re.I)),
    DenyRegexRule("sports_scores", re.compile(r"\b(who\s+won|final\s+score|nba\s+game)\b", re.I)),
    DenyRegexRule("recipe_cooking", re.compile(r"\b(recipe|cook\s+\w+|how\s+to\s+make\s+\w+\s+soup)\b", re.I)),
    DenyRegexRule("joke", re.compile(r"\b(tell\s+me\s+a\s+joke|funny\s+joke)\b", re.I)),
    DenyRegexRule("tax_advice", re.compile(r"\b(tax\s+advice|file\s+my\s+taxes|irs\s+deduction)\b", re.I)),
    DenyRegexRule("legal_advice", re.compile(r"\b(legal\s+advice|should\s+i\s+sue|lawyer)\b", re.I)),
    DenyRegexRule("medical", re.compile(r"\b(diagnose|medical\s+advice|prescription\s+drug)\b", re.I)),
    DenyRegexRule("politics_election", re.compile(r"\b(election|vote\s+for|political\s+party|congressman|senator\s+\w+)\b", re.I)),
    DenyRegexRule("macro_econ", re.compile(r"\b(global\s+economics|macroeconomics|federal\s+reserve\s+policy|gdp\s+forecast)\b", re.I)),
    DenyRegexRule("investment_advice", re.compile(r"\b(which\s+stock\s+should\s+i\s+buy|investment\s+advice)\b", re.I)),
)


# Multi-word phrases (substring match on lowercased text).
DENY_PHRASES: frozenset[str] = frozenset(
    {
        "who is the president",
        "write me a poem",
        "homework help",
        "essay about",
        "translate this",
    }
)
