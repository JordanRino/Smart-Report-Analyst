"""Chat handling for Chainlit."""

from __future__ import annotations

import asyncio
import logging
import uuid
from typing import Any, Dict, List

import chainlit as cl
from chainlit.data import get_data_layer

from smart_report_analyst.config.settings import Settings
from smart_report_analyst.service.bedrock.agent_manager import BedrockManager
from smart_report_analyst.service.strands.runner import async_stream_strands_turn
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
    thread_id = cl.user_session.get("thread_id")
    bedrock_session_id = cl.user_session.get("bedrock_session_id")
    data_layer = get_data_layer()

    if not thread_id:
        await cl.Message(content="No active session. Please select or create one.").send()
        return

    if not bedrock_session_id:
        bedrock_session_id = f"br-{uuid.uuid4().hex}"
        cl.user_session.set("bedrock_session_id", bedrock_session_id)

    history = cl.user_session.get("chat_history", [])

    history.append({
        "role": "user",
        "content": message.content
    })

    # Persist user message
    try:
        await data_layer.create_element({
            "thread_id": thread_id,
            "role": "user",
            "content": message.content,
            "metadata": None
        })

    except Exception:
        logger.exception("Failed to save user message")

    cl.user_session.set("chat_history", history)

    # response: Dict[str, Any] = {}

    full_response = ""
    tool_result = {}

    try:
        # with cl.Step(name="Bedrock Agent", type="llm", show_input=True) as step:
        #     step.input = message.content
        #     current_step = cl.context.current_step

        # response = await asyncio.to_thread(
        #     bedrock_manager.invoke_agent,
        #     prompt=message.content,
        #     agent_id=settings.SINGLE_COORDINATOR_BEDROCK_AGENT_ID,
        #     agent_alias_id=settings.SINGLE_COORDINATOR_BEDROCK_AGENT_ALIAS_ID,
        #     session_id=session_id,
        # )
        if settings.AGENT_BACKEND == "strands":
            async for event in async_stream_strands_turn(settings, history):
                if event["type"] == "chunk":
                    token = event["data"]
                    full_response += token
                elif event["type"] == "tool_result":
                    tool_result = event["data"]
        else:
            stream = bedrock_manager.invoke_agent_stream(
                prompt=message.content,
                agent_id=settings.SINGLE_COORDINATOR_BEDROCK_AGENT_ID,
                agent_alias_id=settings.SINGLE_COORDINATOR_BEDROCK_AGENT_ALIAS_ID,
                session_id=bedrock_session_id,
            )
            for event in stream:
                if event["type"] == "chunk":
                    token = event["data"]
                    full_response += token

                elif event["type"] == "tool_result":
                    tool_result = event["data"]

        history = cl.user_session.get("chat_history", [])

        history.append({
            "role": "assistant",
            "content": full_response
        })

        # Persist assistant message
        try:
            await data_layer.create_element({
                "thread_id": thread_id,
                "role": "assistant",
                "content": full_response,
                "metadata": tool_result or None
            })
        except Exception:
            logger.exception("Failed to save assistant message")

        cl.user_session.set("chat_history", history)
            
        # final_response = response.get("final_response", "Sorry, I could not generate a response.") 
        # tool_result = response.get("tool_result") or {}
        final_response = full_response

        cl.user_session.set("last_response", {
            "final_response": full_response,
            "tool_result": tool_result,
        })
        cl.user_session.set("last_tool_result", tool_result)

        elements = [] 
        if should_generate_report(tool_result): 
            # pdf_buffer = generate_pdf(tool_result, response.get("user_question", message.content)) 
            pdf_buffer = generate_pdf(tool_result, message.content)
            pdf_bytes = pdf_buffer.getvalue() 
            filename = build_report_filename( tool_result.get("refined_user_question", message.content) ) 
            report_file = cl.File( 
                name=filename, 
                content=pdf_bytes, 
            )
            elements.append(report_file)

        await cl.Message( 
            content=final_response, 
            # actions=_build_actions(response),
            actions=_build_actions({
                "final_response": full_response,
                "tool_result": tool_result,
            }),
            elements=elements, 
        ).send() 
        
    except Exception as exc: 
        logger.exception("Error while handling user message") 
        await cl.Message( 
            content=f"Sorry, something went wrong while processing your request.\n\n{exc}" 
        ).send()