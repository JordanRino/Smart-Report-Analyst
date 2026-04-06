from fastapi import APIRouter
from copilotkit.integrations.fastapi import add_fastapi_endpoint
from copilotkit import CopilotKitRemoteEndpoint

from smart_report_analyst.service.strands.agent import StrandsCopilotAgent
from smart_report_analyst.service.strands.session.reader import list_history_sessions

router = APIRouter()


@router.get("/history")
async def get_chat_history():
    """
    Lists Strands FileSessionManager sessions (``session_<id>/session.json``).
    Used by the Next.js HistorySidebar; ``id`` matches CopilotKit ``threadId`` / Strands ``session_id``.
    """
    return list_history_sessions()


add_fastapi_endpoint(
    router,
    CopilotKitRemoteEndpoint(
        agents=[
            StrandsCopilotAgent(
                name="loan_report_analyst_agent",
                description="Answers analytical questions about SBA loan data by generating SQL queries and generating reports of the records collected from the database.",
            ),
        ],
    ),
    prefix="/copilotkit",
)
