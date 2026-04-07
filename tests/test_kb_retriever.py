"""Unit tests for KnowledgeBaseRetriever (mocked bedrock-agent-runtime)."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from smart_report_analyst.config.settings import Settings
from smart_report_analyst.service.bedrock.kb_manager import KnowledgeBaseRetriever, _extract_chunk_text


@pytest.mark.parametrize(
    "chunk,expected_substr",
    [
        ({"content": {"text": "hello schema"}}, "hello schema"),
        ({"content": "plain"}, "plain"),
        ({"content": {"row": {"col": 1}}}, "col"),
    ],
)
def test_extract_chunk_text(chunk, expected_substr):
    assert expected_substr in _extract_chunk_text(chunk)


def test_retrieve_flattens_fixture_results():
    mock_client = MagicMock()
    mock_client.retrieve.return_value = {
        "retrievalResults": [
            {"content": {"text": "Table sba_loans has column Bank"}, "score": 0.9},
            {"content": {"text": "Historical SQL: SELECT COUNT(*) FROM sba_loans"}, "score": 0.8},
        ]
    }
    settings = Settings.model_construct(
        AWS_REGION="us-east-1",
        BEDROCK_KNOWLEDGE_BASE_ID="kb-12345",
        RETRIEVAL_MAX_RESULTS=10,
        RETRIEVAL_MAX_CHARS=48_000,
    )
    r = KnowledgeBaseRetriever(settings, bedrock_agent_runtime_client=mock_client)
    out = r.retrieve("loans by bank")

    mock_client.retrieve.assert_called_once()
    call_kw = mock_client.retrieve.call_args.kwargs
    assert call_kw["knowledgeBaseId"] == "kb-12345"
    assert call_kw["retrievalQuery"] == {"text": "loans by bank"}

    assert "sba_loans" in out
    assert "Chunk 1" in out
    assert "SELECT COUNT" in out


def test_retrieve_skips_when_kb_unconfigured():
    settings = Settings.model_construct(
        AWS_REGION="us-east-1",
        BEDROCK_KNOWLEDGE_BASE_ID=None,
    )
    mock_client = MagicMock()
    r = KnowledgeBaseRetriever(settings, bedrock_agent_runtime_client=mock_client)
    out = r.retrieve("anything")
    assert "skipped" in out.lower()
    mock_client.retrieve.assert_not_called()


def test_retrieve_handles_client_error():
    from botocore.exceptions import ClientError

    mock_client = MagicMock()
    mock_client.retrieve.side_effect = ClientError(
        {"Error": {"Code": "AccessDeniedException", "Message": "denied"}},
        "Retrieve",
    )
    settings = Settings.model_construct(
        AWS_REGION="us-east-1",
        BEDROCK_KNOWLEDGE_BASE_ID="kb-x",
        RETRIEVAL_MAX_RESULTS=5,
        RETRIEVAL_MAX_CHARS=1000,
    )
    r = KnowledgeBaseRetriever(settings, bedrock_agent_runtime_client=mock_client)
    out = r.retrieve("q")
    assert "KB retrieve failed" in out
