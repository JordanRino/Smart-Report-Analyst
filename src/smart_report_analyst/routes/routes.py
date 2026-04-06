from fastapi import APIRouter
from copilotkit.integrations.fastapi import add_fastapi_endpoint
from copilotkit import CopilotKitRemoteEndpoint

from smart_report_analyst.service.strands.agent import StrandsCopilotAgent
from smart_report_analyst.service.strands.session.manager import _resolved_storage_dir

router = APIRouter()


@router.get("/history")
async def get_chat_history():
    """
    Scans the Strands storage directory and returns a list of sessions.
    This populates your Next.js HistorySidebar.
    """
    storage_dir = _resolved_storage_dir()
    history = []

    if storage_dir.exists():
        # Strands FileSessionManager saves files as {session_id}.json
        for file in storage_dir.glob("*.json"):
            history.append(
                {
                    "id": file.stem,
                    "name": f"Analysis {file.stem[:8]}...",
                }
            )

    # Sort by most recent (using file metadata or ID)
    return sorted(history, key=lambda x: x["id"], reverse=True)


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
