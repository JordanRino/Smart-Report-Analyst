"""AG-UI SSE invariant: no ``REASONING_MESSAGE_CONTENT`` after ``REASONING_MESSAGE_END`` per message id."""

from __future__ import annotations

import json
from collections.abc import Iterable


def assert_no_reasoning_content_after_end_for_same_message(frames: Iterable[str]) -> None:
    """
    Parse ``data:{json}`` lines and enforce reasoning message lifecycle per ``messageId``.

    Raises:
        AssertionError: if any ``REASONING_MESSAGE_CONTENT`` appears after
        ``REASONING_MESSAGE_END`` for the same ``messageId``.
    """
    ended: set[str] = set()
    for fr in frames:
        for line in fr.splitlines():
            if not line.startswith("data:"):
                continue
            raw = line[5:].strip()
            if not raw:
                continue
            try:
                body = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if not isinstance(body, dict):
                continue
            et = body.get("type")
            mid = body.get("messageId")
            if not isinstance(mid, str) or not mid:
                continue
            if et == "REASONING_MESSAGE_END":
                ended.add(mid)
            elif et == "REASONING_MESSAGE_CONTENT":
                assert mid not in ended, (
                    f"REASONING_MESSAGE_CONTENT after REASONING_MESSAGE_END for messageId={mid!r}"
                )
