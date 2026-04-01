"""MySQL Data Layer for App SQL execution and storage."""

from __future__ import annotations

import aiomysql
import json
import logging
from typing import Dict, Any

from smart_report_analyst.config.settings import get_settings

logger = logging.getLogger(__name__)


class AppDataLayer:
    def __init__(self):
        self.pool = None
        settings = get_settings()
        self.host = settings.MYSQL_HOST
        self.user = settings.MYSQL_USER
        self.password = settings.MYSQL_PASSWORD
        self.db = settings.MYSQL_DB
        self.port = settings.MYSQL_PORT

    async def init_pool(self):
        if not self.pool:
            self.pool = await aiomysql.create_pool(
                host=self.host,
                user=self.user,
                password=self.password,
                db=self.db,
                port=self.port,
                autocommit=True,
                cursorclass=aiomysql.cursors.DictCursor,
            )

    async def close(self):
        if self.pool:
            self.pool.close()
            await self.pool.wait_closed()

    async def execute_generated_query(self, query: str, user_refined_question: str, to_store: bool) -> Dict[str, Any]:
        """
        Execute SQL query on sba_loans table and optionally store in successful_queries.

        Args:
            query: The SQL query to execute.
            user_refined_question: Refined user question.
            to_store: Whether to store the query in successful_queries.

        Returns:
            Dict with results, similar to Lambda response.
        """
        await self.init_pool()
        try:
            async with self.pool.acquire() as conn:
                async with conn.cursor() as cur:
                    await cur.execute(query)
                    results = await cur.fetchall()

            row_count = len(results)

            return {
                "refined_user_question": user_refined_question,
                "executed_sql": query,
                "results": results,
                "row_count": row_count,
                "to_store": to_store,
            }

        except Exception as e:
            logger.exception("SQL execution failed")
            return {
                "error": True,
                "message": str(e),
                "refined_user_question": user_refined_question,
                "executed_sql": query,
                "results": [],
                "row_count": 0,
                "to_store": False,
            }

    async def store_successful_query(self, refined_user_question: str, executed_sql: str):
        """Store successful query in successful_queries table."""
        await self.init_pool()
        try:
            async with self.pool.acquire() as conn:
                async with conn.cursor() as cur:
                    await cur.execute(
                        """
                        INSERT INTO successful_queries (refined_user_question, executed_sql, created_at)
                        VALUES (%s, %s, NOW())
                        """,
                        (refined_user_question, executed_sql),
                    )
        except Exception as e:
            logger.exception("Failed to store successful query")

app_data_layer = AppDataLayer()