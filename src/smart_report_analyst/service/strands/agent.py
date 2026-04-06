"""CopilotKit Agent adapter: maps Strands `run_stream` to CopilotKit runtime protocol (NDJSON)."""

from __future__ import annotations

import json
import logging
import uuid
from typing import Any, Optional

from copilotkit.action import ActionDict
from copilotkit.agent import Agent
from copilotkit.protocol import (
    action_execution_args,
    action_execution_end,
    action_execution_result,
    action_execution_start,
    agent_state_message,
    emit_runtime_event,
    emit_runtime_events,
    text_message_content,
    text_message_end,
    text_message_start,
)
from copilotkit.types import Message, MetaEvent

from smart_report_analyst.service.strands.runner import run_stream
from smart_report_analyst.service.strands.session.reader import get_copilot_state_for_thread

logger = logging.getLogger(__name__)

ACTION_EXECUTE_SQL = "execute_sql"


def _yield_execute_sql_action_events(final_tool_result: dict[str, Any]):
    """Emit CopilotKit ActionExecution NDJSON so useCopilotAction(execute_sql) can render SqlTable."""
    if not final_tool_result or final_tool_result.get("error"):
        return
    executed = final_tool_result.get("executed_sql")
    results = final_tool_result.get("results")
    if executed is None or results is None:
        return
    if not isinstance(results, list):
        results = list(results)

    exec_id = str(uuid.uuid4())
    args_obj = {"query": str(executed), "results": results}
    args_json = json.dumps(args_obj, default=str)

    yield emit_runtime_events(
        action_execution_start(
            action_execution_id=exec_id,
            action_name=ACTION_EXECUTE_SQL,
            parent_message_id=None,
        ),
        action_execution_args(action_execution_id=exec_id, args=args_json),
        action_execution_end(action_execution_id=exec_id),
        action_execution_result(
            action_name=ACTION_EXECUTE_SQL,
            action_execution_id=exec_id,
            result=args_json,
        ),
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
    Streams assistant text using `run_stream` and emits CopilotKit runtime events
    (TextMessageStart/Content/End + final AgentStateMessage with tool_result JSON).
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
        message_id = str(uuid.uuid4())

        yield emit_runtime_event(
            text_message_start(message_id=message_id, parent_message_id=None)
        )

        final_tool_result: dict[str, Any] = {}
        try:
            async for event in run_stream(user_message, thread_id):
                et = event.get("type")
                if et == "chunk":
                    data = event.get("data", "")
                    if isinstance(data, str) and data:
                        yield emit_runtime_event(
                            text_message_content(message_id=message_id, content=data)
                        )
                elif et == "tool_result":
                    raw = event.get("data")
                    final_tool_result = raw if isinstance(raw, dict) else {}
        except Exception:
            logger.exception("strands_copilotkit_agent_execute")
            raise

        yield emit_runtime_event(text_message_end(message_id=message_id))

        for line in _yield_execute_sql_action_events(final_tool_result):
            yield line

        yield emit_runtime_event(
            agent_state_message(
                thread_id=thread_id,
                agent_name=self.name,
                node_name="__end__",
                run_id=run_id,
                active=False,
                role="assistant",
                state=json.dumps({"tool_result": final_tool_result}),
                running=False,
            )
        )

    async def get_state(
        self,
        *,
        thread_id: str,
    ) -> dict[str, Any]:
        return get_copilot_state_for_thread(thread_id or "")
