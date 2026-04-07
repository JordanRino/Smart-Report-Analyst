"""execute_sql tool: Lambda payload keys and Strands Lambda body passthrough."""

from __future__ import annotations

import io
import json
from unittest.mock import MagicMock, patch

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


@patch("smart_report_analyst.service.strands.tools.strands_tools.LambdaManager")
def test_execute_sql_lambda_payload_keys(mock_lm_class):
    mock_instance = MagicMock()
    mock_lm_class.return_value = mock_instance
    lambda_body = {
        "refined_user_question": "Count loans",
        "executed_sql": "SELECT COUNT(*) AS n FROM t",
        "results": [{"n": 3}],
        "row_count": 1,
        "to_store": True,
    }
    mock_instance.invoke_function.return_value = {
        "Payload": io.BytesIO(json.dumps(lambda_body).encode("utf-8")),
    }

    settings = _minimal_settings()
    state = StrandsTurnState()
    tools = build_strands_tools(settings, state)
    execute_sql = next(t for t in tools if getattr(t, "tool_name", None) == "execute_sql")

    result = execute_sql(
        query="SELECT COUNT(*) AS n FROM t",
        user_refined_question="Count loans",
        to_store=True,
    )

    mock_instance.invoke_function.assert_called_once()
    call = mock_instance.invoke_function.call_args
    assert call[0][0] == "store_sql_sra"
    payload = call[0][1]
    assert set(payload.keys()) == {"query", "user_refined_question", "to_store"}
    assert payload["query"] == "SELECT COUNT(*) AS n FROM t"
    assert payload["user_refined_question"] == "Count loans"
    assert payload["to_store"] is True

    assert result["refined_user_question"] == "Count loans"
    assert result["executed_sql"] == "SELECT COUNT(*) AS n FROM t"
    assert result["row_count"] == 1
    assert state.last_tool_result == result


@patch("smart_report_analyst.service.strands.tools.strands_tools.LambdaManager")
def test_execute_sql_uses_strands_lambda_name_when_set(mock_lm_class):
    mock_instance = MagicMock()
    mock_lm_class.return_value = mock_instance
    mock_instance.invoke_function.return_value = {
        "Payload": io.BytesIO(
            b'{"refined_user_question":"q","executed_sql":"SELECT 1","results":[],"row_count":0,"to_store":false}'
        ),
    }
    settings = _minimal_settings(STRANDS_SQL_LAMBDA_FUNCTION_NAME="strands_sql_fn")
    tools = build_strands_tools(settings, StrandsTurnState())
    execute_sql = next(t for t in tools if getattr(t, "tool_name", None) == "execute_sql")
    execute_sql(query="SELECT 1", user_refined_question="q", to_store=False)
    assert mock_instance.invoke_function.call_args[0][0] == "strands_sql_fn"


@patch("smart_report_analyst.service.strands.tools.strands_tools.LambdaManager")
def test_execute_sql_sets_turn_state_on_error(mock_lm_class):
    mock_instance = MagicMock()
    mock_lm_class.return_value = mock_instance
    mock_instance.invoke_function.side_effect = RuntimeError("lambda down")

    settings = _minimal_settings()
    state = StrandsTurnState()
    tools = build_strands_tools(settings, state)
    execute_sql = next(t for t in tools if getattr(t, "tool_name", None) == "execute_sql")

    result = execute_sql(
        query="SELECT 1",
        user_refined_question="Q",
        to_store=False,
    )

    assert result.get("error") is True
    assert state.last_tool_result.get("error") is True
