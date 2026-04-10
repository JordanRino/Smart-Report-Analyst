"""Strands helpers: chat history shape conversion and turn splitting."""

from __future__ import annotations

from typing import Any


def split_history_for_turn(history: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], str]:
    """
    Split so the last user message is the current turn prompt; remainder is prior context.

    If the last message is not from the user, treat the entire history as prior and return "".
    """
    if not history:
        return [], ""
    last = history[-1]
    if last.get("role") != "user":
        return history, ""
    prior = history[:-1]
    text = last.get("content", "")
    if not isinstance(text, str):
        text = str(text)
    return prior, text
