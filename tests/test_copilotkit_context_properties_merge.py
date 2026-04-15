"""CopilotKit request context.properties must reach agent.execute(config=...)."""

from __future__ import annotations

from typing import Mapping, cast

from copilotkit.sdk import CopilotKitContext

from smart_report_analyst.integrations.copilotkit import _merge_config_with_context_properties


def test_merge_config_with_context_properties_fills_missing_config() -> None:
    ctx = cast_context({"mainAgentId": "wlr_reporting_agent"})
    merged = _merge_config_with_context_properties(None, ctx)
    assert merged is not None
    assert merged["properties"]["mainAgentId"] == "wlr_reporting_agent"
    assert merged["mainAgentId"] == "wlr_reporting_agent"


def test_merge_config_with_context_properties_shallow_overrides() -> None:
    ctx = cast_context({"mainAgentId": "loan_report_analyst_agent"})
    merged = _merge_config_with_context_properties({"properties": {"foo": 1}}, ctx)
    assert merged["properties"]["foo"] == 1
    assert merged["properties"]["mainAgentId"] == "loan_report_analyst_agent"


def test_merge_empty_context_returns_original() -> None:
    assert _merge_config_with_context_properties({"a": 1}, cast_context({})) == {"a": 1}
    assert _merge_config_with_context_properties(None, cast_context({})) is None


def cast_context(properties: dict) -> CopilotKitContext:
    return cast(
        CopilotKitContext,
        {
            "properties": properties,
            "frontend_url": None,
            "headers": cast(Mapping[str, str], {}),
        },
    )
