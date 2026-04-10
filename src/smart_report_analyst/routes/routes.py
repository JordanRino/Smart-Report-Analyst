import uuid
from typing import Any, cast

from copilotkit.integrations.fastapi import (
    add_fastapi_endpoint,
    handle_get_agent_state,
    handle_info,
)
from copilotkit.sdk import CopilotKitContext
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse, Response, StreamingResponse
from smart_report_analyst.integrations.agui_stream import iter_connect_replay_frames
from smart_report_analyst.integrations.copilotkit import (
    CopilotKitRemoteEndpointAguiAgentsMap,
    patch_copilotkit_info_html_for_agent_map,
)
from smart_report_analyst.service.feedback import handle_positive_feedback
from smart_report_analyst.service.feedback.schemas import FeedbackPositiveBody
from smart_report_analyst.service.feedback.snapshot_index import pop_feedback_snapshot
from smart_report_analyst.service.report_generation.report_pdf import (
    ReportPdfClientError,
    ReportPdfRequest,
    ReportPdfServerError,
    render_sql_report_pdf,
)
from smart_report_analyst.service.strands.agent import StrandsCopilotAgent
from smart_report_analyst.service.strands.session.reader import list_history_sessions

patch_copilotkit_info_html_for_agent_map()

router = APIRouter()


_copilot_sdk = CopilotKitRemoteEndpointAguiAgentsMap(
    agents=[
        StrandsCopilotAgent(
            name="sra_router_agent",
            description="Front-door assistant: helps you pick a specialist or explains available reporting agents.",
        ),
        StrandsCopilotAgent(
            name="wlr_reporting_agent",
            description="WLR reporting specialist: SBA loan analytics via knowledge base and SQL execution.",
        ),
        StrandsCopilotAgent(
            name="loan_report_analyst_agent",
            description="(Legacy) Same capability as WLR Reporting Agent — SBA loan SQL and reports.",
        ),
    ],
)


@router.get("/copilotkit/info")
async def copilotkit_runtime_info(request: Request):
    """
    REST transport (``useSingleEndpoint={false}``) fetches runtime metadata with
    ``GET .../copilotkit/info``. The catch-all CopilotKit route would otherwise
    hit ``handler_v1``, which rejects requests with no JSON body.
    """
    context = cast(
        CopilotKitContext,
        {
            "properties": {},
            "frontend_url": None,
            "headers": request.headers,
        },
    )
    return await handle_info(sdk=_copilot_sdk, context=context, as_html=False)


@router.post("/feedback/positive", tags=["feedback"])
async def feedback_positive(body: FeedbackPositiveBody) -> dict[str, Any]:
    """
    Persist helpful feedback.

    - CopilotKit thumbs-up: body ``{ message_id, thread_id }`` (snapshot from last ``execute_sql`` emit).
    - Explicit save: ``{ refined_user_question, executed_sql, to_store? }`` (e.g. SqlPdfReport Helpful).
    """
    if body.message_id and body.thread_id:
        snap = pop_feedback_snapshot(body.thread_id.strip(), body.message_id.strip())
        if not snap:
            raise HTTPException(
                status_code=404,
                detail="No snapshot for this message (unknown id, wrong thread, or expired).",
            )
        payload = snap
    else:
        payload = {
            "refined_user_question": (body.refined_user_question or "").strip(),
            "executed_sql": (body.executed_sql or "").strip(),
            "to_store": True if body.to_store is None else body.to_store,
        }
    return await handle_positive_feedback(payload)


@router.post("/reports/pdf", tags=["reports"])
async def create_report_pdf(body: ReportPdfRequest):
    try:
        pdf_bytes, content_disposition = render_sql_report_pdf(body)
    except ReportPdfClientError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ReportPdfServerError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": content_disposition},
    )


@router.get("/history")
async def get_chat_history():
    """
    Lists Strands FileSessionManager sessions (``session_<id>/session.json``).
    Used by the Next.js HistorySidebar; ``id`` matches CopilotKit ``threadId`` / Strands ``session_id``.
    """
    return list_history_sessions()


def _copilot_context_from_request(request: Request, body: dict) -> CopilotKitContext:
    return cast(
        CopilotKitContext,
        {
            "properties": body.get("properties", {}),
            "frontend_url": body.get("frontendUrl"),
            "headers": request.headers,
        },
    )


@router.post("/copilotkit/agent/{agent_name}/state")
async def copilotkit_agent_state(agent_name: str, request: Request):
    """
    Must register before CopilotKit's catch-all: otherwise ``agent/name`` regex matches
    ``agent/name/state`` and incorrectly runs ``execute_agent``.
    """
    try:
        body = await request.json()
    except Exception:  # pylint: disable=broad-except
        body = {}
    thread_id = body.get("threadId")
    if thread_id is None:
        raise HTTPException(status_code=400, detail="threadId is required")
    context = _copilot_context_from_request(request, body if isinstance(body, dict) else {})
    return await handle_get_agent_state(
        sdk=_copilot_sdk,
        context=context,
        thread_id=thread_id,
        name=agent_name,
    )


@router.post("/copilotkit/agent/{agent_name}/connect")
async def copilotkit_agent_connect(agent_name: str, request: Request):
    """
    AG-UI ``connectAgent`` handshake without invoking Strands. The generic CopilotKit
    handler would treat this path as ``execute`` and stream "no user message".
    """
    _ = agent_name
    try:
        body = await request.json()
    except Exception:  # pylint: disable=broad-except
        body = {}
    if not isinstance(body, dict):
        body = {}
    thread_id = body.get("threadId") or str(uuid.uuid4())
    run_id = body.get("runId") or str(uuid.uuid4())

    async def agui_connect_chunks():
        for frame in iter_connect_replay_frames(
            thread_id=thread_id, run_id=run_id, agent_name=agent_name
        ):
            yield frame

    return StreamingResponse(agui_connect_chunks(), media_type="text/event-stream")


@router.post("/copilotkit/agent/{agent_name}/stop/{thread_id_param}")
async def copilotkit_agent_stop(agent_name: str, thread_id_param: str):
    """Prevent ``agent/name/stop/...`` from being handled as ``execute_agent``."""
    _ = agent_name, thread_id_param
    return JSONResponse(content={"ok": True})


add_fastapi_endpoint(router, _copilot_sdk, prefix="/copilotkit")
