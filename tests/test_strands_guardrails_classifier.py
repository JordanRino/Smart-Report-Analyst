"""Tests for deterministic topic guardrails (pre-model)."""

from smart_report_analyst.service.strands.guardrails.classifier import classify_user_message


def test_allows_loan_question():
    c = classify_user_message("How many SBA loans were charged off by bank in 2020?")
    assert c.allowed
    assert c.reason == "in_domain_hint"


def test_blocks_weather():
    c = classify_user_message("What's the weather in Seattle today?")
    assert not c.allowed
    assert c.reason == "deny_regex"
    assert "SBA loan data" in c.refusal_message


def test_blocks_time():
    c = classify_user_message("What time is it in New York?")
    assert not c.allowed


def test_blocks_phrase():
    c = classify_user_message("Can you write me a poem about loans?")
    assert not c.allowed
    assert c.reason == "deny_phrase"
