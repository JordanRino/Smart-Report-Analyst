"""AWS Bedrock AgentCore Memory session management."""

from __future__ import annotations

from bedrock_agentcore.memory.integrations.strands.config import (
    AgentCoreMemoryConfig, 
    RetrievalConfig
)
from bedrock_agentcore.memory.integrations.strands.session_manager import (
    AgentCoreMemorySessionManager
)
from smart_report_analyst.config.settings import Settings

def build_agentcore_memory_manager(
    settings: Settings, 
    session_id: str, 
    actor_id: str
) -> AgentCoreMemorySessionManager:
    """
    Initialize the Bedrock AgentCore Session Manager with LTM strategies.
    
    Args:
        settings: Application settings containing Memory IDs and AWS Region.
        session_id: The unique thread/chat ID (e.g., from Chainlit).
        actor_id: The unique user ID.
    """
    
    # Configure retrieval for Long-Term Memory (LTM) strategies
    # These namespaces must match your Bedrock Memory Resource configuration
    retrieval_config = {
        "/preferences/{actorId}": RetrievalConfig(
            top_k=5,
            relevance_score=0.7
        ),
        "/facts/{actorId}": RetrievalConfig(
            top_k=10,
            relevance_score=0.5
        ),
        "/summaries/{actorId}/{sessionId}": RetrievalConfig(
            top_k=5,
            relevance_score=0.6
        )
    }

    config = AgentCoreMemoryConfig(
        memory_id=settings.AGENTCORE_MEMORY_ID,
        session_id=session_id,
        actor_id=actor_id,
        retrieval_config=retrieval_config,
        batch_size=1  # Immediate flush for real-time responsiveness
    )

    return AgentCoreMemorySessionManager(
        agentcore_memory_config=config,
        region_name=settings.AWS_REGION
    )