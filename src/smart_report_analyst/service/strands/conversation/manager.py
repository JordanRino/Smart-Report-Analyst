"""Strands SummarizingConversationManager for SQL / schema-aware context control."""

from __future__ import annotations

from strands.agent.conversation_manager import SummarizingConversationManager

from smart_report_analyst.config.settings import get_settings

SUMMARIZATION_SYSTEM_PROMPT = """
You are summarizing a technical data analysis session. Create a concise bullet-point summary that:
- Preserves specific table names, column names, and verified schema details.
- Captures key analytical findings (e.g., "Query confirmed 450 active loans in Florida").
- Notes successful SQL patterns or filters used to avoid redundant metadata lookups.
- Omits conversational filler; focus on technical state and data discovered.
Format as third-person technical bullet points.
"""


def build_strands_conversation_manager() -> SummarizingConversationManager:
    settings = get_settings()
    return SummarizingConversationManager(
        summary_ratio=settings.STRANDS_CONVERSATION_SUMMARY_RATIO,
        preserve_recent_messages=settings.STRANDS_CONVERSATION_PRESERVE_RECENT_MESSAGES,
        summarization_system_prompt=SUMMARIZATION_SYSTEM_PROMPT.strip(),
    )
