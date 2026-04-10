"""Composite session ids for per-agent Strands isolation."""

from __future__ import annotations

from smart_report_analyst.service.strands.session.scoped import composite_session_id


def test_composite_session_id_joins_thread_and_agent() -> None:
    assert composite_session_id("tid-1", "wlr_reporting_agent") == "tid-1__wlr_reporting_agent"


def test_composite_session_id_sanitizes_agent_name() -> None:
    assert composite_session_id("abc", "weird name!") == "abc__weird_name_"
