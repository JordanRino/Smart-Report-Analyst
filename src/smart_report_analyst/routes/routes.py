import os
from fastapi import APIRouter, Header, HTTPException
from copilotkit.integrations.fastapi import add_fastapi_endpoint
from copilotkit import CopilotKitRemoteEndpoint

# Import your existing Strands session logic
from smart_report_analyst.service.strands.session.manager import (
    build_strands_session_manager, 
    _resolved_storage_dir
)
# Assuming you have a runner function that takes a session_manager
from smart_report_analyst.service.strands.runner import run_strands_agent

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
            history.append({
                "id": file.stem,
                "name": f"Analysis {file.stem[:8]}..."
            })
    
    # Sort by most recent (using file metadata or ID)
    return sorted(history, key=lambda x: x['id'], reverse=True)

async def copilotkit_handler(context: dict):
    """
    The 'Glue' between CopilotKit and Strands.
    """

    thread_id = context.get("threadId", "default-session")
    
    # This automatically loads the .json file if it exists
    session_manager = build_strands_session_manager(thread_id)
    
    # We pass the session_manager so Strands handles the persistence automatically
    messages = context.get("messages", [])
    response = await run_strands_agent(messages, session_manager)
    
    return response

# This attaches the CopilotKit logic to your FastAPI router
add_fastapi_endpoint(
    router,
    CopilotKitRemoteEndpoint(
        name="loan_analyst_agent",
        handler=copilotkit_handler,
    ),
    path="/copilotkit",
)