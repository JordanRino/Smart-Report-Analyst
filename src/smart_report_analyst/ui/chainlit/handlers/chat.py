"""Chat handling for Chainlit."""

from __future__ import annotations

import asyncio
import logging
import uuid
from typing import Any, Dict, List

import chainlit as cl

from smart_report_analyst.config.settings import Settings
from smart_report_analyst.service.bedrock.manager import BedrockManager
from smart_report_analyst.service.report_generation import generate_pdf
from smart_report_analyst.ui.chainlit.utils.formatting import (
    build_report_filename,
    should_generate_report,
)

logger = logging.getLogger(__name__)
settings = Settings()
bedrock_manager = BedrockManager()


def _build_feedback_payload(response: Dict[str, Any]) -> Dict[str, Any]:
    """Build a compact payload for feedback storage."""
    tool_result = response.get("tool_result", {})
    return {
        "refined_user_question": tool_result.get(
            "refined_user_question",
            response.get("user_question", ""),
        ),
        "executed_sql": tool_result.get("executed_sql", ""),
        "to_store": tool_result.get("to_store", False),
        "row_count": tool_result.get("row_count", 0),
    }


def _build_actions(response: Dict[str, Any]) -> List[cl.Action]:
    """Create feedback actions for the assistant message."""
    payload = _build_feedback_payload(response)

    return [
        cl.Action(
            name="report_helpful",
            icon="thumbs-up",
            label="Helpful",
            payload={**payload, "rating": 1},
        )
    ]


@cl.on_message
async def on_message(message: cl.Message):
    session_id = cl.user_session.get("session_id") or str(uuid.uuid4())
    cl.user_session.set("session_id", session_id)

    response: Dict[str, Any] = {}

    try:
        with cl.Step(name="Bedrock Agent", type="llm", show_input=True) as step:
            step.input = message.content

            response = await asyncio.to_thread(
                bedrock_manager.invoke_agent,
                prompt=message.content,
                agent_id=settings.SINGLE_COORDINATOR_BEDROCK_AGENT_ID,
                agent_alias_id=settings.SINGLE_COORDINATOR_BEDROCK_AGENT_ALIAS_ID,
                session_id=session_id,
            )
            step.output = response.get("final_response", "") 
            
        final_response = response.get("final_response", "Sorry, I could not generate a response.") 
        tool_result = response.get("tool_result") or {}

        cl.user_session.set("last_response", response) 
        cl.user_session.set("last_tool_result", tool_result)

        elements = [] 
        if should_generate_report(tool_result): 
            pdf_buffer = generate_pdf(tool_result, response.get("user_question", message.content)) 
            pdf_bytes = pdf_buffer.getvalue() 
            filename = build_report_filename( tool_result.get("refined_user_question", message.content) ) 
            elements.append( 
                cl.File( 
                    name=filename, 
                    content=pdf_bytes, 
                ) 
            ) 

        await cl.Message( 
            content=final_response, 
            actions=_build_actions(response), 
            elements=elements, 
        ).send() 
        
    except Exception as exc: 
        logger.exception("Error while handling user message") 
        await cl.Message( 
            content=f"Sorry, something went wrong while processing your request.\n\n{exc}" ).send()