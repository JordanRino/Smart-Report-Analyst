"""execute_sql / retrieve_kb Strands tools (MySQL via app_data_layer)."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from smart_report_analyst.config.settings import Settings
from smart_report_analyst.service.strands.tools import StrandsTurnState, build_strands_tools


def _minimal_settings(**kwargs) -> Settings:
    base = dict(
        AWS_REGION="us-east-1",
        environment="development",
        AGENT_BACKEND="strands",
        BEDROCK_KNOWLEDGE_BASE_ID="kb",
        BEDROCK_MODEL_ID="us.anthropic.fake-v1:0",
        STORE_SQL_LAMBDA_FUNCTION_NAME="store_sql_sra",
        STRANDS_SQL_LAMBDA_FUNCTION_NAME=None,
        RETRIEVAL_MAX_RESULTS=5,
        RETRIEVAL_MAX_CHARS=1000,
    )
    base.update(kwargs)
    return Settings.model_construct(**base)


@patch("smart_report_analyst.service.strands.tools.tools.KnowledgeBaseRetriever")
@patch("smart_report_analyst.service.strands.tools.tools.get_settings")
@patch("smart_report_analyst.service.strands.tools.tools.app_data_layer")
def test_execute_sql_passthrough_body(mock_adl, mock_get_settings, _mock_kb) -> None:
    mock_get_settings.return_value = _minimal_settings()
    body = {
        "refined_user_question": "Count loans",
        "executed_sql": "SELECT COUNT(*) AS n FROM t",
        "results": [{"n": 3}],
        "row_count": 1,
        "to_store": True,
    }
    mock_adl.execute_generated_query = AsyncMock(return_value=body)

    state = StrandsTurnState()
    tools = build_strands_tools(state)
    execute_sql = next(t for t in tools if getattr(t, "tool_name", None) == "execute_sql")

    async def _run() -> None:
        result = await execute_sql(
            query="SELECT COUNT(*) AS n FROM t",
            user_refined_question="Count loans",
            to_store=True,
        )
        mock_adl.execute_generated_query.assert_awaited_once_with(
            "SELECT COUNT(*) AS n FROM t",
            "Count loans",
            True,
        )
        assert result == body
        assert state.last_tool_result == body

    asyncio.run(_run())


@patch("smart_report_analyst.service.strands.tools.tools.KnowledgeBaseRetriever")
@patch("smart_report_analyst.service.strands.tools.tools.get_settings")
@patch("smart_report_analyst.service.strands.tools.tools.app_data_layer")
def test_execute_sql_sets_turn_state_on_error(
    mock_adl, mock_get_settings, _mock_kb
) -> None:
    mock_get_settings.return_value = _minimal_settings()
    mock_adl.execute_generated_query = AsyncMock(side_effect=RuntimeError("db down"))

    state = StrandsTurnState()
    tools = build_strands_tools(state)
    execute_sql = next(t for t in tools if getattr(t, "tool_name", None) == "execute_sql")

    async def _run() -> None:
        result = await execute_sql(
            query="SELECT 1",
            user_refined_question="Q",
            to_store=False,
        )
        assert result.get("error") is True
        assert state.last_tool_result.get("error") is True

    asyncio.run(_run())


@patch("smart_report_analyst.service.strands.tools.tools.KnowledgeBaseRetriever")
@patch("smart_report_analyst.service.strands.tools.tools.get_settings")
def test_retrieve_kb_context_delegates(mock_get_settings, mock_kb_class) -> None:
    mock_get_settings.return_value = _minimal_settings()
    mock_kb = MagicMock()
    mock_kb.retrieve.return_value = "ctx text"
    mock_kb_class.return_value = mock_kb

    tools = build_strands_tools(StrandsTurnState())
    retrieve = next(t for t in tools if getattr(t, "tool_name", None) == "retrieve_kb_context")

    async def _run() -> None:
        out = await retrieve(query="tables")
        assert out == "ctx text"
        mock_kb.retrieve.assert_called_once_with("tables")

    asyncio.run(_run())
