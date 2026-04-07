import uuid
from typing import cast

from copilotkit.integrations.fastapi import (
    add_fastapi_endpoint,
    handle_get_agent_state,
    handle_info,
)
from copilotkit.sdk import CopilotKitContext
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse

from smart_report_analyst.integrations.agui_stream import (
    agui_run_finished,
    agui_run_started,
)
from smart_report_analyst.integrations.copilotkit import (
    CopilotKitRemoteEndpointAguiAgentsMap,
    patch_copilotkit_info_html_for_agent_map,
)
from smart_report_analyst.service.strands.agent import StrandsCopilotAgent
from smart_report_analyst.service.strands.session.reader import list_history_sessions

patch_copilotkit_info_html_for_agent_map()

router = APIRouter()

_copilot_sdk = CopilotKitRemoteEndpointAguiAgentsMap(
    agents=[
        StrandsCopilotAgent(
            name="loan_report_analyst_agent",
            description="Answers analytical questions about SBA loan data by generating SQL queries and generating reports of the records collected from the database.",
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
        yield agui_run_started(thread_id=thread_id, run_id=run_id)
        yield agui_run_finished(thread_id=thread_id, run_id=run_id)

    return StreamingResponse(agui_connect_chunks(), media_type="application/json")


@router.post("/copilotkit/agent/{agent_name}/stop/{thread_id_param}")
async def copilotkit_agent_stop(agent_name: str, thread_id_param: str):
    """Prevent ``agent/name/stop/...`` from being handled as ``execute_agent``."""
    _ = agent_name, thread_id_param
    return JSONResponse(content={"ok": True})


add_fastapi_endpoint(router, _copilot_sdk, prefix="/copilotkit")
