# ui/chainlit/handlers/feedback.py
"""Feedback buttons and callbacks for assistant messages."""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict

import chainlit as cl

from smart_report_analyst.service.feedback import handle_positive_feedback

logger = logging.getLogger(__name__)


@cl.action_callback("report_helpful")
async def on_report_helpful(action: cl.Action):
    """Persist helpful feedback for a response."""
    payload: Dict[str, Any] = action.payload or {}

    try:
        result = await handle_positive_feedback(payload)

        if isinstance(result, dict) and result.get("status") == "success":
            await cl.Message(content="👍 Thanks for your feedback!").send()
        else:
            await cl.Message(
                content="👍 Feedback received."
            ).send()

    except Exception as exc:
        logger.exception("Failed to save feedback")
        await cl.Message(
            content=f"Feedback could not be saved: {exc}"
        ).send()

