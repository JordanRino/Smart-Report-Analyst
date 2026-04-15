import uuid
from typing import Any, cast

from copilotkit.integrations.fastapi import (
    add_fastapi_endpoint,
    handle_get_agent_state,
    handle_info,
)
from copilotkit.sdk import CopilotKitContext
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, Response, StreamingResponse
from smart_report_analyst.integrations.agui_stream import iter_connect_replay_frames
from smart_report_analyst.integrations.copilotkit import (
    CopilotKitRemoteEndpointAguiAgentsMap,
    patch_copilotkit_info_html_for_agent_map,
)
from smart_report_analyst.service.feedback import handle_positive_feedback
from smart_report_analyst.service.feedback.schemas import FeedbackPositiveBody
from smart_report_analyst.service.feedback.snapshot_index import pop_feedback_snapshot
from smart_report_analyst.service.reports.reports_models import ReportSaveRequest, RecordSaveRequest
from smart_report_analyst.service.reports.reports_store import ReportsStore
from smart_report_analyst.service.reports.report_pdf import (
    ReportPdfClientError,
    ReportPdfRequest,
    ReportPdfServerError,
    render_sql_report_pdf,
)
from smart_report_analyst.service.strands.agent import StrandsCopilotAgent
from smart_report_analyst.service.strands.agents.registry import is_main_specialist
from smart_report_analyst.service.strands.session.orchestrator_state import (
    get_main_agent_id,
    set_main_agent_id,
)
from smart_report_analyst.service.strands.session.reader import list_history_sessions

patch_copilotkit_info_html_for_agent_map()

router = APIRouter()


def get_reports_store() -> ReportsStore:
    return ReportsStore()


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
        StrandsCopilotAgent(
            name="sra_orchestrator_agent",
            description=(
                "Session orchestrator: routes to your selected main specialist (see properties.mainAgentId) "
                "plus a text-only report builder."
            ),
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
    - Explicit save: ``{ refined_user_question, executed_sql, to_store? }`` (e.g. report card Helpful).
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


@router.post("/records/saved", status_code=201, tags=["records"])
async def create_saved_record(
    body: RecordSaveRequest,
    store: ReportsStore = Depends(get_reports_store),
) -> JSONResponse:
    """Save raw SQL results as a CSV record. Returns existing record if already saved (idempotent)."""
    try:
        payload = store.save_record(
            results=body.results,
            executed_sql=body.executed_sql,
            refined_user_question=body.refined_user_question,
            row_count=body.row_count,
            thread_id=body.thread_id,
            agent_id=body.agent_id,
            title=body.title,
            source_message_id=body.source_message_id,
            main_agent_id=body.main_agent_id,
        )
    except ReportPdfClientError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    status = 200 if payload.get("already_exists") else 201
    return JSONResponse(status_code=status, content=payload)


@router.get("/records/saved/{record_id}/file", tags=["records"])
async def get_saved_record_file(
    record_id: str,
    store: ReportsStore = Depends(get_reports_store),
) -> Response:
    """Download CSV file for a saved record."""
    path = store.get_csv_path(record_id)
    if path is None:
        raise HTTPException(status_code=404, detail="CSV file not found")
    meta = store.get_metadata(record_id)
    title = (meta or {}).get("title", "records")
    safe = title.replace(" ", "_")[:48] or "records"
    return Response(
        content=path.read_bytes(),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{safe}.csv"'},
    )


@router.post("/reports/saved", status_code=201, tags=["reports"])
async def create_saved_report(
    body: ReportSaveRequest,
    store: ReportsStore = Depends(get_reports_store),
) -> JSONResponse:
    """Save a report PDF. Returns existing record if already saved (idempotent)."""
    try:
        payload = store.save_report(
            body=body,
            thread_id=body.thread_id,
            agent_id=body.agent_id,
            title=body.title,
            source_message_id=body.source_message_id,
            main_agent_id=body.main_agent_id,
        )
    except ReportPdfClientError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ReportPdfServerError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    status = 200 if payload.get("already_exists") else 201
    return JSONResponse(status_code=status, content=payload)




@router.get("/reports/saved", tags=["reports"])
async def list_saved_reports(
    limit: int = 50,
    offset: int = 0,
    thread_id: str | None = None,
    agent_id: str | None = None,
    kind: str | None = None,
    store: ReportsStore = Depends(get_reports_store),
) -> dict[str, Any]:
    items, total = store.list_reports(
        limit=limit,
        offset=offset,
        thread_id=thread_id,
        agent_id=agent_id,
        kind=kind,
    )
    return {"items": items, "total": total}


@router.get("/reports/saved/{report_id}", tags=["reports"])
async def get_saved_report_metadata(
    report_id: str,
    store: ReportsStore = Depends(get_reports_store),
) -> dict[str, Any]:
    try:
        meta = store.get_metadata(report_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if meta is None:
        raise HTTPException(status_code=404, detail="Not found")
    return meta


@router.get("/reports/saved/{report_id}/file", tags=["reports"])
async def get_saved_report_file(
    report_id: str,
    store: ReportsStore = Depends(get_reports_store),
) -> FileResponse:
    try:
        path = store.get_pdf_path(report_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if path is None:
        try:
            exists_meta = store.get_metadata(report_id) is not None
        except ValueError:
            exists_meta = False
        if not exists_meta:
            raise HTTPException(status_code=404, detail="Not found")
        raise HTTPException(status_code=404, detail="PDF missing on disk")
    return FileResponse(
        path=str(path),
        media_type="application/pdf",
        filename="report.pdf",
    )


@router.delete("/reports/saved/{report_id}", status_code=204, tags=["reports"])
async def delete_saved_report(
    report_id: str,
    store: ReportsStore = Depends(get_reports_store),
) -> Response:
    try:
        deleted = store.delete_report(report_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not deleted:
        raise HTTPException(status_code=404, detail="Not found")
    return Response(status_code=204)


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


@router.post("/session/{thread_id}/specialist")
async def set_session_specialist(thread_id: str, request: Request) -> JSONResponse:
    """Persist the orchestrator's active specialist for a thread.

    Body: ``{ "mainAgentId": "wlr_reporting_agent" }``
    Passing ``null`` or omitting the key clears the choice.
    """
    try:
        body = await request.json()
    except Exception:  # pylint: disable=broad-except
        raise HTTPException(status_code=400, detail="Request body must be valid JSON.")
    if not isinstance(body, dict):
        raise HTTPException(status_code=400, detail="Request body must be a JSON object.")

    raw_mid = body.get("mainAgentId")
    if raw_mid is not None and not isinstance(raw_mid, str):
        raise HTTPException(status_code=422, detail="mainAgentId must be a string or null.")

    mid: str | None = raw_mid.strip() if isinstance(raw_mid, str) and raw_mid.strip() else None
    if mid is not None and not is_main_specialist(mid):
        raise HTTPException(
            status_code=422,
            detail=f"Unknown specialist agent id: {mid!r}. "
            "Must be one of: wlr_reporting_agent, loan_report_analyst_agent.",
        )

    set_main_agent_id(thread_id.strip(), mid)
    return JSONResponse(content={"threadId": thread_id, "mainAgentId": mid})


@router.get("/session/{thread_id}/specialist")
async def get_session_specialist(thread_id: str) -> JSONResponse:
    """Return the currently persisted specialist for a thread.

    Response: ``{ "threadId": "...", "mainAgentId": "wlr_reporting_agent" | null }``
    """
    mid = get_main_agent_id(thread_id.strip())
    return JSONResponse(content={"threadId": thread_id, "mainAgentId": mid})


add_fastapi_endpoint(router, _copilot_sdk, prefix="/copilotkit")
