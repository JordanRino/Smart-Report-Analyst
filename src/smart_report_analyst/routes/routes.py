from typing import cast

from copilotkit.integrations.fastapi import add_fastapi_endpoint, handle_info
from copilotkit.sdk import CopilotKitContext
from fastapi import APIRouter, Request
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


add_fastapi_endpoint(router, _copilot_sdk, prefix="/copilotkit")
