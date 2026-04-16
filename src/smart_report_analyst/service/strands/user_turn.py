"""Copilot user turn → Strands prompt (text or Bedrock-shaped content blocks)."""

from __future__ import annotations

import base64
import re
from dataclasses import dataclass, field
from typing import Any, Literal

from strands.types.content import ContentBlock

# Bedrock Converse document formats supported by Strands DocumentContent.
DocumentFormat = Literal["pdf", "csv", "doc", "docx", "xls", "xlsx", "html", "txt", "md"]

_MIME_TO_FORMAT: dict[str, DocumentFormat] = {
    "application/pdf": "pdf",
    "text/plain": "txt",
    "text/markdown": "md",
    "text/html": "html",
    "text/csv": "csv",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
    "application/msword": "doc",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "xlsx",
    "application/vnd.ms-excel": "xls",
}

_SAFE_NAME = re.compile(r"[^a-zA-Z0-9._-]+")


def _neutral_attachment_name(original: str, index: int) -> str:
    base = (original or "attachment").strip() or "attachment"
    base = _SAFE_NAME.sub("_", base)[:120] or "attachment"
    if "." not in base:
        base = f"{base}_{index}.bin"
    return base


def _format_from_mime(mime: str) -> DocumentFormat | None:
    return _MIME_TO_FORMAT.get((mime or "").split(";")[0].strip().lower())


@dataclass
class AttachmentRef:
    """One uploaded file for a Bedrock ``document`` content block."""

    neutral_name: str
    format: DocumentFormat
    bytes_content: bytes | None = None
    mime_type: str | None = None


@dataclass
class UserTurnPayload:
    """Structured user message + optional documents."""

    text: str
    attachments: list[AttachmentRef] = field(default_factory=list)

    def classify_text(self) -> str:
        return self.text


def attachment_from_inline_dict(block: dict[str, Any], index: int) -> AttachmentRef | None:
    """Parse a single attachment-like dict from message content (best-effort)."""
    # CopilotKit 1.56+ / AG-UI: { type: "document", source: { type: "data", value: base64, mimeType }, metadata?: { filename } }
    source = block.get("source")
    mime = ""
    name = ""
    raw_b64: Any = None
    if isinstance(source, dict) and str(source.get("type") or "").lower() == "data":
        mime = str(source.get("mimeType") or source.get("mime_type") or "").strip()
        raw_b64 = source.get("value") or source.get("content") or source.get("data")
        meta = block.get("metadata")
        if isinstance(meta, dict):
            name = str(meta.get("filename") or meta.get("name") or "").strip()
    if not name:
        name = str(block.get("name") or block.get("filename") or "").strip()
    if not mime:
        mime = str(block.get("mimeType") or block.get("mediaType") or "").strip()
    if not raw_b64:
        raw_b64 = block.get("content") or block.get("data") or block.get("bytes")
    if not name:
        name = f"upload_{index}"

    blob: bytes | None = None
    if isinstance(raw_b64, str) and raw_b64:
        try:
            blob = base64.b64decode(raw_b64, validate=False)
        except Exception:
            blob = None
    elif isinstance(raw_b64, (bytes, bytearray)):
        blob = bytes(raw_b64)

    part_type = str(block.get("type") or "").lower()
    if part_type in ("image", "audio", "video"):
        return None

    fmt = _format_from_mime(mime) if mime else None
    if fmt is None and name:
        lower = name.lower()
        for ext, f in (
            (".pdf", "pdf"),
            (".txt", "txt"),
            (".md", "md"),
            (".html", "html"),
            (".csv", "csv"),
            (".docx", "docx"),
            (".doc", "doc"),
            (".xlsx", "xlsx"),
            (".xls", "xls"),
        ):
            if lower.endswith(ext):
                fmt = f
                break

    if fmt is None or not blob:
        return None

    return AttachmentRef(
        neutral_name=_neutral_attachment_name(name, index),
        format=fmt,
        bytes_content=blob,
        mime_type=mime or None,
    )


def parse_user_turn_from_messages(messages: list[dict[str, Any]]) -> UserTurnPayload:
    """Latest user message: text plus optional attachments from CopilotKit shapes."""
    for msg in reversed(messages):
        role = msg.get("role")
        r = getattr(role, "value", role)
        r = str(r or "")
        if r != "user":
            continue
        content = msg.get("content", "")
        if isinstance(content, str):
            return UserTurnPayload(text=content)

        if isinstance(content, list):
            text_parts: list[str] = []
            attachments: list[AttachmentRef] = []
            for i, block in enumerate(content):
                if isinstance(block, str):
                    text_parts.append(block)
                    continue
                if not isinstance(block, dict):
                    continue
                if "text" in block:
                    text_parts.append(str(block["text"]))
                    continue
                kind = str(block.get("type") or "").lower()
                if kind in ("image", "audio", "video"):
                    continue
                att = attachment_from_inline_dict(block, i)
                if att:
                    attachments.append(att)
            return UserTurnPayload(text="".join(text_parts).strip(), attachments=attachments)

        return UserTurnPayload(text=str(content))

    return UserTurnPayload(text="")


def user_turn_to_strands_prompt(payload: UserTurnPayload) -> str | list[ContentBlock]:
    """Map payload to ``Agent.stream_async`` input."""
    if not payload.attachments:
        return payload.text

    blocks: list[ContentBlock] = []
    if payload.text.strip():
        blocks.append({"text": payload.text})

    for att in payload.attachments:
        data = att.bytes_content
        if not data:
            continue
        doc = {
            "format": att.format,
            "name": att.neutral_name,
            "source": {"bytes": data},
        }
        blocks.append({"document": doc})

    if not blocks:
        return payload.text
    return blocks
