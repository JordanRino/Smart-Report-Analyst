"""Flatten Bedrock Knowledge Base retrieve results for LLM context."""

from __future__ import annotations

import base64
import logging
from typing import Any

import boto3
from botocore.exceptions import ClientError

from smart_report_analyst.config.settings import Settings

logger = logging.getLogger(__name__)


def _extract_chunk_text(chunk: dict[str, Any]) -> str:
    """Best-effort text extraction from a retrieval result content block."""
    content = chunk.get("content") or {}
    if isinstance(content, str):
        return content
    if not isinstance(content, dict):
        return str(content)

    text = content.get("text")
    if text:
        return str(text)

    row = content.get("row")
    if row is not None:
        return str(row)

    byte_content = content.get("byteContent")
    if byte_content:
        if isinstance(byte_content, bytes):
            try:
                return byte_content.decode("utf-8", errors="replace")
            except Exception:
                return str(byte_content)
        try:
            return base64.b64decode(byte_content).decode("utf-8", errors="replace")
        except Exception:
            return str(byte_content)

    return str(content)


class KnowledgeBaseRetriever:
    """Calls bedrock-agent-runtime `retrieve` and returns a capped plain-text context string."""

    def __init__(
        self,
        settings: Settings | None = None,
        *,
        bedrock_agent_runtime_client: Any | None = None,
    ):
        self._settings = settings or Settings()
        self._client = bedrock_agent_runtime_client or boto3.client(
            "bedrock-agent-runtime",
            region_name=self._settings.AWS_REGION,
        )

    def retrieve(self, query: str) -> str:
        kb_id = self._settings.BEDROCK_KNOWLEDGE_BASE_ID
        if not kb_id:
            return "KB retrieve skipped: BEDROCK_KNOWLEDGE_BASE_ID is not configured."

        q = (query or "").strip()
        if not q:
            return "KB retrieve skipped: empty query."

        try:
            response = self._client.retrieve(
                knowledgeBaseId=kb_id,
                retrievalQuery={"text": q},
                retrievalConfiguration={
                    "vectorSearchConfiguration": {
                        "numberOfResults": min(self._settings.RETRIEVAL_MAX_RESULTS, 100),
                    }
                },
            )
        except ClientError as e:
            logger.exception("Knowledge base retrieve failed")
            return f"KB retrieve failed: {e}"

        results = response.get("retrievalResults") or []
        parts: list[str] = []
        total = 0
        max_chars = self._settings.RETRIEVAL_MAX_CHARS

        for i, item in enumerate(results):
            text = _extract_chunk_text(item).strip()
            if not text:
                continue
            score = item.get("score")
            header = f"--- Chunk {i + 1}" + (f" (score={score})" if score is not None else "") + " ---"
            block = f"{header}\n{text}"
            if total + len(block) + 1 > max_chars:
                remaining = max_chars - total - 100
                if remaining > 200:
                    parts.append(block[:remaining] + "\n[truncated]")
                parts.append("\n[KB context truncated due to size limit]")
                break
            parts.append(block)
            total += len(block) + 1

        if not parts:
            return "No matching knowledge base passages were retrieved."

        return "\n\n".join(parts)
