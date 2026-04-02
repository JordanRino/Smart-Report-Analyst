"""Strands tools: KB retrieve and SQL Lambda execution."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any

from strands import tool

from smart_report_analyst.config.settings import get_settings
from smart_report_analyst.service.bedrock.kb_manager import KnowledgeBaseRetriever
from smart_report_analyst.service.persistence.mysql.app_data_layer import app_data_layer

logger = logging.getLogger(__name__)



@dataclass
class StrandsTurnState:
    """Per-turn mutable state (last execute_sql result for UI)."""

    last_tool_result: dict = field(default_factory=dict)


def build_strands_tools(turn_state: StrandsTurnState) -> list:
    """Build tool callables bound to settings and turn-scoped result capture."""
    
    settings = get_settings()
    kb = KnowledgeBaseRetriever(settings)

    @tool
    def retrieve_kb_context(query: str) -> str:
        """
        Search the Smart Report Analyst knowledge base for database metadata (tables, columns)
        and historical SQL examples. Call this before writing SQL when schema or similar queries matter.

        Args:
            query: Natural language search string (e.g. user question or table/column hints).

        Returns:
            Concatenated retrieval passages for the model to use.
        """
        return kb.retrieve(query)

    @tool
    async def execute_sql(query: str, user_refined_question: str, to_store: bool) -> dict:
        """
        Execute a SQL query against the SBA loan database directly via MySQL.

        Args:
            query: The SQL statement to run.
            user_refined_question: Clear, concise version of the user's analytical question.
            to_store: True if this question/SQL pair should be stored for future retrieval; false if duplicate.

        Returns:
            JSON object with executed_sql, results, row_count, refined_user_question, to_store.
        """
        try:
            body = await app_data_layer.execute_generated_query(query, user_refined_question, to_store)
            turn_state.last_tool_result = body
            return body
        except Exception as e:
            logger.exception("execute_sql failed")
            err = {
                "error": True,
                "message": str(e),
                "refined_user_question": user_refined_question,
                "executed_sql": query,
                "results": [],
                "row_count": 0,
                "to_store": False,
            }
            turn_state.last_tool_result = err
            return err

    return [retrieve_kb_context, execute_sql]
