"""Flatten Bedrock Knowledge Base retrieve results for LLM context."""

from __future__ import annotations

import base64
import logging
import re
from dataclasses import dataclass
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


# --- Trace UI preview (matches ``retrieve`` chunk headers below) ----------------

DEFAULT_MAX_CHUNKS_IN_TRACE = 2
DEFAULT_MAX_CHARS_PER_CHUNK = 1_800


@dataclass(frozen=True, slots=True)
class KbChunk:
    """One ``--- Chunk N (score=x) ---`` section from flattened retrieve output."""

    index: int
    score: str | None
    body: str


_CHUNK_HEADER = re.compile(
    r"---\s*Chunk\s+(\d+)\s*(?:\(score=([\d.]+)\)\s*)?---\s*",
    re.IGNORECASE,
)


def parse_kb_retrieval_chunks(raw: str) -> list[KbChunk]:
    """
    Split flattened KB retrieve text into chunk records.

    If the string does not match chunk markers, returns a single synthetic chunk
    with index 0 so callers can still truncate the body.
    """
    text = raw or ""
    matches = list(_CHUNK_HEADER.finditer(text))
    if not matches:
        stripped = text.strip()
        if not stripped:
            return []
        return [KbChunk(index=0, score=None, body=stripped)]

    out: list[KbChunk] = []
    for i, m in enumerate(matches):
        idx = int(m.group(1))
        score = m.group(2)
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[start:end].strip()
        out.append(KbChunk(index=idx, score=score, body=body))
    return out


def format_kb_trace_preview(
    raw: str,
    *,
    max_chunks: int = DEFAULT_MAX_CHUNKS_IN_TRACE,
    max_chars_per_chunk: int = DEFAULT_MAX_CHARS_PER_CHUNK,
) -> str | None:
    """
    Build a short multi-line preview for the trace panel.

    Returns ``None`` if there is nothing to show.
    """
    chunks = parse_kb_retrieval_chunks(raw)
    if not chunks:
        return None

    lines: list[str] = []
    shown = chunks[:max(1, max_chunks)]
    rest_count = max(0, len(chunks) - len(shown))

    for ch in shown:
        header = f"--- Chunk {ch.index}"
        if ch.score is not None:
            header += f" (score={ch.score})"
        header += " ---"
        lines.append(header)
        body = ch.body.strip()
        if len(body) > max_chars_per_chunk:
            body = body[: max_chars_per_chunk - 3].rstrip() + "..."
        lines.append(body)
        lines.append("")

    if rest_count:
        lines.append(f"… {rest_count} more chunk(s) not shown (truncated).")

    result = "\n".join(lines).strip()
    return result or None


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
