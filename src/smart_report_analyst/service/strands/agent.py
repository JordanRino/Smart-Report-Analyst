"""CopilotKit Agent adapter: maps Strands ``run_stream`` to AG-UI + SSE (CopilotKit HTTP)."""

from __future__ import annotations

import json
import logging
import uuid
from typing import Any, Iterator, Optional

from copilotkit.action import ActionDict
from copilotkit.agent import Agent
from copilotkit.types import Message, MetaEvent

from smart_report_analyst.integrations.agui_stream import (
    agui_run_finished,
    agui_run_started,
    agui_state_snapshot,
    agui_text_message_content,
    agui_text_message_end,
    agui_text_message_start,
    agui_tool_call_args,
    agui_tool_call_end,
    agui_tool_call_result,
    agui_tool_call_start,
)
from smart_report_analyst.service.strands.runner import run_stream
from smart_report_analyst.service.strands.session.reader import get_copilot_state_for_thread

logger = logging.getLogger(__name__)

ACTION_EXECUTE_SQL = "execute_sql"


def _yield_execute_sql_tool_events(
    *,
    final_tool_result: dict[str, Any],
    parent_message_id: str,
) -> Iterator[str]:
    """AG-UI tool-call SSE frames so ``useCopilotAction(execute_sql)`` receives ActionExecution (via client bridge)."""
    if not final_tool_result or final_tool_result.get("error"):
        return
    executed = final_tool_result.get("executed_sql")
    results = final_tool_result.get("results")
    if executed is None or results is None:
        return
    if not isinstance(results, list):
        results = list(results)

    tool_call_id = str(uuid.uuid4())
    result_message_id = str(uuid.uuid4())
    args_obj = {
        "query": str(executed),
        "results": results,
        "refined_user_question": final_tool_result.get("refined_user_question"),
        "row_count": final_tool_result.get("row_count"),
    }
    args_json = json.dumps(args_obj, default=str)

    yield agui_tool_call_start(
        tool_call_id=tool_call_id,
        tool_call_name=ACTION_EXECUTE_SQL,
        parent_message_id=parent_message_id,
    )
    yield agui_tool_call_args(tool_call_id=tool_call_id, delta=args_json)
    yield agui_tool_call_end(tool_call_id=tool_call_id)
    yield agui_tool_call_result(
        message_id=result_message_id,
        tool_call_id=tool_call_id,
        content=args_json,
    )


def _message_role_str(msg: Message) -> str:
    r = msg.get("role")
    if r is None:
        return ""
    return r.value if hasattr(r, "value") else str(r)


def _last_user_text(messages: list[Message]) -> str:
    """Latest user text from CopilotKit message list (JSON uses string roles)."""
    for msg in reversed(messages):
        if _message_role_str(msg) != "user":
            continue
        content = msg.get("content", "")
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts: list[str] = []
            for block in content:
                if isinstance(block, dict) and "text" in block:
                    parts.append(str(block["text"]))
                elif isinstance(block, str):
                    parts.append(block)
            return "".join(parts)
        return str(content)
    return ""


class StrandsCopilotAgent(Agent):
    """
    Streams assistant text using ``run_stream`` and emits AG-UI events over SSE
    (``data:`` lines + ``\\n\\n``), ending with ``STATE_SNAPSHOT`` and ``RUN_FINISHED``.
    """

    def __init__(
        self,
        *,
        name: str = "loan_analyst_agent",
        description: str | None = None,
    ) -> None:
        super().__init__(
            name=name,
            description=description or "SBA loan analysis (Strands + Bedrock)",
        )

    async def execute(  # pylint: disable=too-many-arguments
        self,
        *,
        state: dict,
        config: Optional[dict] = None,
        messages: list[Message],
        thread_id: str,
        actions: Optional[list[ActionDict]] = None,
        meta_events: Optional[list[MetaEvent]] = None,
        **kwargs: Any,
    ):
        _ = state, config, actions, meta_events, kwargs

        user_message = _last_user_text(messages)
        run_id = str(uuid.uuid4())

        if not user_message.strip():
            yield agui_run_started(thread_id=thread_id, run_id=run_id)
            yield agui_state_snapshot(snapshot={"tool_result": {}})
            yield agui_run_finished(thread_id=thread_id, run_id=run_id)
            return

        message_id = str(uuid.uuid4())

        yield agui_run_started(thread_id=thread_id, run_id=run_id)
        yield agui_text_message_start(message_id=message_id, role="assistant")

        final_tool_result: dict[str, Any] = {}
        try:
            async for event in run_stream(user_message, thread_id):
                et = event.get("type")
                if et == "chunk":
                    data = event.get("data", "")
                    if isinstance(data, str) and data:
                        frame = agui_text_message_content(
                            message_id=message_id, delta=data
                        )
                        if frame:
                            yield frame
                elif et == "tool_result":
                    raw = event.get("data")
                    final_tool_result = raw if isinstance(raw, dict) else {}
        except Exception:
            logger.exception("strands_copilotkit_agent_execute")
            raise

        yield agui_text_message_end(message_id=message_id)

        for frame in _yield_execute_sql_tool_events(
            final_tool_result=final_tool_result,
            parent_message_id=message_id,
        ):
            yield frame

        yield agui_state_snapshot(
            snapshot={"tool_result": final_tool_result},
        )
        yield agui_run_finished(thread_id=thread_id, run_id=run_id)

    async def get_state(
        self,
        *,
        thread_id: str,
    ) -> dict[str, Any]:
        return get_copilot_state_for_thread(thread_id or "")
