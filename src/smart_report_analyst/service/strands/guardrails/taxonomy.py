"""Structured allow/deny signals for pre-model topic filtering.

Bedrock Guardrails complement this layer. These rules are fast and deterministic; they
should avoid both obvious off-topic traffic and false blocks when the user mixes a stray
phrase with a real loan-analytics question.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

# User-visible copy when a deterministic rule blocks the turn.
OFF_TOPIC_REFUSAL_MESSAGE = (
    "I can only help with analytical questions about SBA loan data in this application "
    "(exploring the database, metrics, trends, and SQL-backed reports). "
    "Please ask a question about the loan data or how to analyze it."
)

# Minimum number of distinct domain-hint pattern hits required to ignore
# ``only_without_domain`` deny rules (time, weather, etc.).
DOMAIN_HINT_THRESHOLD_FOR_OFF_TOPIC_OVERRIDE = 2


@dataclass(frozen=True)
class DenyRegexRule:
    """Compiled pattern with policy for when it applies."""

    name: str
    pattern: re.Pattern[str]
    # If True: block only when domain-hint score is below DOMAIN_HINT_THRESHOLD.
    only_without_domain: bool = False


# Spaces often inserted inside tokens to evade substring/regex checks (NFKC maps
# NBSP to ASCII space, which still breaks ``weather`` → ``we ather``).
_EVASION_SPACE_CHARS = frozenset(
    "\u00a0\u1680\u2000\u2001\u2002\u2003\u2004\u2005\u2006\u2007\u2008\u2009\u200a\u200b\u200c\u200d\u202f\u205f\u3000\ufeff"
)


def normalize_for_classification(text: str) -> str:
    """
    Normalize user text before regex/phrase checks.

    Strip evasion characters **before** NFKC (NFKC maps NBSP to ASCII space, which would
    still split tokens). Then NFKC, drop remaining format chars, collapse whitespace.
    """
    if not isinstance(text, str):
        text = str(text)
    s = "".join(ch for ch in text if ch not in _EVASION_SPACE_CHARS)
    s = unicodedata.normalize("NFKC", s)
    s = "".join(ch for ch in s if unicodedata.category(ch) != "Cf")
    s = re.sub(r"\s+", " ", s)
    return s.strip()


# Signals the message is plausibly about this product's data domain. Count distinct hits
# for ``only_without_domain`` overrides (see classifier).
DOMAIN_HINT_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\bsba\b", re.I),
    re.compile(r"small\s+business\s+administration", re.I),
    re.compile(r"\b7\s*\(?a\)?\b", re.I),
    re.compile(r"\b504\s+(loan|program|loans)\b", re.I),
    re.compile(r"\bsba_loans", re.I),
    re.compile(r"\bmis_status\b", re.I),
    re.compile(r"\bcharge[\s-]?off\b", re.I),
    re.compile(r"\bpif\b", re.I),
    re.compile(r"\b(gross|approval|disbursement|origination)\b", re.I),
    re.compile(r"\b(naics|franchise|borrower)\b", re.I),
    re.compile(r"\b(bank|lender)\b.*\bloan", re.I),
    re.compile(r"\bloan(s)?\b.*\b(count|total|volume|sum|average|avg|rate|trend|breakdown|default)\b", re.I),
    re.compile(
        r"\b(how\s+many|number\s+of|count\s+of|top\s+\d+|group\s+by|break\s+down|breakdown)\b",
        re.I,
    ),
)


# Always block when matched (personal advice, politics, obvious non-analytics).
DENY_REGEX_RULES_ALWAYS: tuple[DenyRegexRule, ...] = (
    DenyRegexRule("ignore_instructions", re.compile(r"\b(ignore|disregard)\b.{0,40}\b(instructions|rules)\b", re.I)),
    DenyRegexRule("jailbreak_dan", re.compile(r"\b(dan\s+mode|developer\s+mode)\b", re.I)),
    DenyRegexRule("stock_ticker", re.compile(r"\bstock\s+(price|market|pick)\b", re.I)),
    DenyRegexRule("crypto_trading", re.compile(r"\b(bitcoin|ethereum|crypto(currency)?)\b.{0,30}\b(buy|sell|trade)\b", re.I)),
    DenyRegexRule("sports_scores", re.compile(r"\b(who\s+won|final\s+score|nba\s+game|super\s+bowl)\b", re.I)),
    DenyRegexRule("recipe_cooking", re.compile(r"\b(recipe|how\s+to\s+cook)\b", re.I)),
    DenyRegexRule("joke", re.compile(r"\b(tell\s+me\s+a\s+joke|funny\s+joke)\b", re.I)),
    DenyRegexRule("horoscope", re.compile(r"\b(horoscope|zodiac|astrology)\b", re.I)),
    DenyRegexRule("tax_advice", re.compile(r"\b(tax\s+advice|file\s+my\s+taxes|irs\s+deduction)\b", re.I)),
    DenyRegexRule("legal_advice", re.compile(r"\b(legal\s+advice|should\s+i\s+sue|hire\s+a\s+lawyer)\b", re.I)),
    DenyRegexRule("medical", re.compile(r"\b(diagnose\s+me|medical\s+advice|prescription\s+drug)\b", re.I)),
    DenyRegexRule(
        "politics_election",
        re.compile(
            r"\b(vote\s+for|political\s+party|who\s+(should|will)\s+i\s+vote)\b|"
            r"\b(election\s+fraud|impeach(ment)?)\b",
            re.I,
        ),
    ),
    DenyRegexRule(
        "macro_econ",
        re.compile(
            r"\b(global\s+economics|macroeconomics|federal\s+reserve\s+policy|gdp\s+forecast)\b",
            re.I,
        ),
    ),
    DenyRegexRule(
        "investment_advice",
        re.compile(r"\b(which\s+stock\s+should\s+i\s+buy|investment\s+advice|financial\s+advisor)\b", re.I),
    ),
    DenyRegexRule("cheating", re.compile(r"\b(cheat\s+on|plagiar|write\s+my\s+essay\s+for\s+me)\b", re.I)),
)


# Block only when the message lacks enough domain hints (pure chit-chat / general knowledge).
DENY_REGEX_RULES_WITHOUT_DOMAIN: tuple[DenyRegexRule, ...] = (
    DenyRegexRule("time_now", re.compile(r"\bwhat\s+time\b", re.I), only_without_domain=True),
    DenyRegexRule("what_time_is_it", re.compile(r"\bwhat'?s?\s+the\s+time\b", re.I), only_without_domain=True),
    DenyRegexRule("current_time", re.compile(r"\bcurrent\s+time\b", re.I), only_without_domain=True),
    DenyRegexRule("what_day", re.compile(r"\bwhat\s+day\b", re.I), only_without_domain=True),
    DenyRegexRule("todays_date", re.compile(r"\btoday'?s\s+date\b", re.I), only_without_domain=True),
    DenyRegexRule("weather", re.compile(r"\bweather\b", re.I), only_without_domain=True),
    DenyRegexRule("forecast", re.compile(r"\bforecast\b", re.I), only_without_domain=True),
)


DENY_REGEX_RULES: tuple[DenyRegexRule, ...] = DENY_REGEX_RULES_ALWAYS + DENY_REGEX_RULES_WITHOUT_DOMAIN


# Phrases: substring match on lowercased normalized text.
DENY_PHRASES_ALWAYS: frozenset[str] = frozenset(
    {
        "who is the president",
        "who was the president",
        "write me a poem",
        "write a poem",
        "homework help",
        "do my homework",
        "essay about",
        "translate this paragraph",
        "translate this text",
    }
)

DENY_PHRASES_WITHOUT_DOMAIN: frozenset[str] = frozenset(
    {
        "what is the capital",
        "capital of ",
        "tell me a story",
    }
)

DENY_PHRASES: frozenset[str] = DENY_PHRASES_ALWAYS | DENY_PHRASES_WITHOUT_DOMAIN
