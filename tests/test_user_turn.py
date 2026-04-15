"""UserTurnPayload parsing and Strands prompt mapping."""

from __future__ import annotations

import base64

from smart_report_analyst.service.strands.user_turn import (
    AttachmentRef,
    UserTurnPayload,
    parse_user_turn_from_messages,
    user_turn_to_strands_prompt,
)


def test_parse_text_only() -> None:
    p = parse_user_turn_from_messages(
        [{"role": "user", "content": "  hello  ", "id": "1", "createdAt": ""}]
    )
    assert p.text == "  hello  "
    assert p.attachments == []


def test_parse_text_blocks() -> None:
    p = parse_user_turn_from_messages(
        [
            {
                "role": "user",
                "content": [{"type": "text", "text": "a"}, {"text": "b"}],
                "id": "1",
                "createdAt": "",
            }
        ]
    )
    assert p.text == "ab"


def test_parse_pdf_attachment() -> None:
    b64 = base64.b64encode(b"%PDF-1.4 fake").decode("ascii")
    p = parse_user_turn_from_messages(
        [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Check this"},
                    {
                        "mimeType": "application/pdf",
                        "name": "report.pdf",
                        "content": b64,
                    },
                ],
                "id": "1",
                "createdAt": "",
            }
        ]
    )
    assert "Check this" in p.text
    assert len(p.attachments) == 1
    assert p.attachments[0].format == "pdf"
    assert p.attachments[0].bytes_content == b"%PDF-1.4 fake"


def test_user_turn_to_strands_string_without_files() -> None:
    out = user_turn_to_strands_prompt(UserTurnPayload(text="hi"))
    assert out == "hi"


def test_user_turn_to_strands_blocks_with_pdf() -> None:
    out = user_turn_to_strands_prompt(
        UserTurnPayload(
            text="Verify",
            attachments=[
                AttachmentRef(
                    neutral_name="doc_0.pdf",
                    format="pdf",
                    bytes_content=b"%PDF",
                    mime_type="application/pdf",
                )
            ],
        )
    )
    assert isinstance(out, list)
    assert out[0] == {"text": "Verify"}
    assert "document" in out[1]
    assert out[1]["document"]["format"] == "pdf"
    assert out[1]["document"]["source"]["bytes"] == b"%PDF"
