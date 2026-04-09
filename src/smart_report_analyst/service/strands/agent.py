"""CopilotKit Agent adapter: maps Strands ``run_stream`` to AG-UI + SSE (CopilotKit HTTP)."""

from __future__ import annotations

import json
import logging
import time
import uuid
from typing import Any, Iterator, Optional

from copilotkit.action import ActionDict
from copilotkit.agent import Agent
from copilotkit.types import Message, MetaEvent

from smart_report_analyst.integrations.agui_stream import (
    agui_reasoning_end,
    agui_reasoning_message_content,
    agui_reasoning_message_end,
    agui_reasoning_message_start,
    agui_reasoning_start,
    agui_run_finished,
    agui_run_started,
    agui_state_snapshot,
    agui_step_finished,
    agui_step_started,
    agui_text_message_content,
    agui_text_message_end,
    agui_text_message_start,
    agui_tool_call_args,
    agui_tool_call_end,
    agui_tool_call_result,
    agui_tool_call_start,
)
from smart_report_analyst.service.agent_trace.agui_mapper import (
    DEFAULT_TOOL_TRACE_ACTIVITY_TYPE,
    ToolTraceActivityState,
    TraceEventChannel,
    trace_event_to_activity_snapshot_frame,
    trace_events_to_sse_frames,
)
from smart_report_analyst.service.agent_trace.events import TraceEvent
from smart_report_analyst.service.feedback.snapshot_index import (
    register_feedback_snapshot,
)
from smart_report_analyst.service.strands.runner import run_stream
from smart_report_analyst.service.strands.session.reader import (
    get_copilot_state_for_thread,
)

logger = logging.getLogger(__name__)

ACTION_EXECUTE_SQL = "execute_sql"


def _ts_ms() -> int:
    return int(time.time() * 1000)


def _yield_execute_sql_tool_events(
    *,
    thread_id: str,
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
        "to_store": final_tool_result.get("to_store"),
    }
    args_json = json.dumps(args_obj, default=str)

    # Thumbs-up resolves SQL via (thread_id, message_id); register both assistant and tool-result ids.
    _fb_snap = {
        "refined_user_question": str(
            final_tool_result.get("refined_user_question") or ""
        ),
        "executed_sql": str(executed),
        "to_store": bool(final_tool_result.get("to_store")),
    }
    register_feedback_snapshot(thread_id, parent_message_id, _fb_snap)
    register_feedback_snapshot(thread_id, result_message_id, _fb_snap)

    t = _ts_ms()
    yield agui_tool_call_start(
        tool_call_id=tool_call_id,
        tool_call_name=ACTION_EXECUTE_SQL,
        parent_message_id=parent_message_id,
        timestamp=t,
    )
    yield agui_tool_call_args(tool_call_id=tool_call_id, delta=args_json, timestamp=t)
    yield agui_tool_call_end(tool_call_id=tool_call_id, timestamp=t)
    yield agui_tool_call_result(
        message_id=result_message_id,
        tool_call_id=tool_call_id,
        content=args_json,
        timestamp=t,
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

    def _emit_pre_answer_trace_frames(
        self, raw: Any, *, reasoning_message_id: str
    ) -> Iterator[str]:
        """Map tool trace to REASONING_* / STEP_* only before assistant text starts."""
        if isinstance(raw, TraceEvent):
            yield from trace_events_to_sse_frames(
                raw,
                reasoning_message_id=reasoning_message_id,
                channel=TraceEventChannel.PRE_ANSWER,
            )

    def _emit_post_answer_tool_activity(
        self,
        raw: Any,
        *,
        activity_message_id: str,
        tool_trace_state: ToolTraceActivityState,
    ) -> Iterator[str]:
        """
        After assistant streaming starts, tool trace must not touch REASONING_*.
        Emit ACTIVITY_SNAPSHOT (replace) for CopilotKit activity UI.
        """
        if not isinstance(raw, TraceEvent):
            return
        yield from trace_event_to_activity_snapshot_frame(
            raw,
            state=tool_trace_state,
            message_id=activity_message_id,
            activity_type=DEFAULT_TOOL_TRACE_ACTIVITY_TYPE,
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
            t = _ts_ms()
            yield agui_run_started(thread_id=thread_id, run_id=run_id, timestamp=t)
            yield agui_state_snapshot(snapshot={"tool_result": {}}, timestamp=t)
            yield agui_run_finished(thread_id=thread_id, run_id=run_id, timestamp=t)
            return

        message_id = str(uuid.uuid4())
        reasoning_message_id = str(uuid.uuid4())
        tool_trace_activity_message_id = str(uuid.uuid4())
        tool_trace_activity_state = ToolTraceActivityState()
        t0 = _ts_ms()
        yield agui_run_started(thread_id=thread_id, run_id=run_id, timestamp=t0)
        yield agui_reasoning_start(
            message_id=reasoning_message_id, timestamp=t0
        )
        yield agui_reasoning_message_start(
            message_id=reasoning_message_id, timestamp=t0
        )
        yield agui_reasoning_message_content(
            message_id=reasoning_message_id,
            delta="Working on your request…\n",
            timestamp=t0,
        )
        yield agui_step_started(step_name="strands_turn", timestamp=t0)

        final_tool_result: dict[str, Any] = {}
        first_text_chunk = False
        try:
            async for event in run_stream(
                user_message,
                thread_id,
                run_id=run_id,
                agent_name=self.name,
            ):
                et = event.get("type")
                if et == "trace":
                    raw = event.get("data")
                    if first_text_chunk:
                        for frame in self._emit_post_answer_tool_activity(
                            raw,
                            activity_message_id=tool_trace_activity_message_id,
                            tool_trace_state=tool_trace_activity_state,
                        ):
                            if frame:
                                yield frame
                    else:
                        for frame in self._emit_pre_answer_trace_frames(
                            raw, reasoning_message_id=reasoning_message_id
                        ):
                            if frame:
                                yield frame
                    continue
                if et == "chunk":
                    data = event.get("data", "")
                    if isinstance(data, str) and data:
                        if not first_text_chunk:
                            first_text_chunk = True
                            t1 = _ts_ms()
                            yield agui_step_finished(
                                step_name="strands_turn", timestamp=t1
                            )
                            yield agui_reasoning_message_end(
                                message_id=reasoning_message_id, timestamp=t1
                            )
                            yield agui_reasoning_end(
                                message_id=reasoning_message_id, timestamp=t1
                            )
                            yield agui_text_message_start(
                                message_id=message_id,
                                role="assistant",
                                timestamp=t1,
                            )
                        frame = agui_text_message_content(
                            message_id=message_id,
                            delta=data,
                            timestamp=_ts_ms(),
                        )
                        if frame:
                            yield frame
                elif et == "tool_result":
                    raw = event.get("data")
                    final_tool_result = raw if isinstance(raw, dict) else {}
        except Exception:
            logger.exception("strands_copilotkit_agent_execute")
            raise

        if not first_text_chunk:
            t2 = _ts_ms()
            yield agui_step_finished(step_name="strands_turn", timestamp=t2)
            yield agui_reasoning_message_end(
                message_id=reasoning_message_id, timestamp=t2
            )
            yield agui_reasoning_end(message_id=reasoning_message_id, timestamp=t2)
            yield agui_text_message_start(
                message_id=message_id, role="assistant", timestamp=t2
            )

        yield agui_text_message_end(message_id=message_id, timestamp=_ts_ms())

        for frame in _yield_execute_sql_tool_events(
            thread_id=thread_id,
            final_tool_result=final_tool_result,
            parent_message_id=message_id,
        ):
            yield frame

        t3 = _ts_ms()
        yield agui_state_snapshot(
            snapshot={"tool_result": final_tool_result},
            timestamp=t3,
        )
        yield agui_run_finished(thread_id=thread_id, run_id=run_id, timestamp=t3)

    async def get_state(
        self,
        *,
        thread_id: str,
    ) -> dict[str, Any]:
        return get_copilot_state_for_thread(thread_id or "")
