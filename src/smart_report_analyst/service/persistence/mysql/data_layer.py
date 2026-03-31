"""MySQL Data Layer for Chainlit persistence."""

from __future__ import annotations

import aiomysql
import json

from typing import Optional, Dict, Any
from chainlit.data import BaseDataLayer
from chainlit.user import PersistedUser, User
from chainlit.types import PaginatedResponse, PageInfo
from chainlit.element import ElementDict, Element

from typing import Any, Dict, Optional, List

from smart_report_analyst.service.persistence.mysql.utils import load_json, dump_json



class MySQLDataLayer(BaseDataLayer):
    def __init__(self, host, user, password, db, port=3306):
        self.pool = None
        self.host = host
        self.user = user
        self.password = password
        self.db = db
        self.port = port

    async def init_pool(self):
        if not self.pool:
            self.pool = await aiomysql.create_pool(
                host=self.host,
                user=self.user,
                password=self.password,
                db=self.db,
                port=self.port,
                autocommit=True,
            )

    async def close(self):
        if self.pool:
            self.pool.close()
            await self.pool.wait_closed()

    async def build_debug_url(self, thread_id: str) -> str:
        # Optional: implement a URL for debugging a thread
        return f"Debug URL for thread {thread_id}"

    # ----------------- User Methods -----------------
    async def get_user(self, identifier: str) -> Optional[Dict[str, Any]]:
        await self.init_pool()
        async with self.pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute(
                    """
                    SELECT id, identifier, metadata, created_at, updated_at
                    FROM users
                    WHERE identifier=%s OR id=%s
                    LIMIT 1
                    """,
                    (identifier, identifier),
                )
                row = await cur.fetchone()
                if row:
                    metadata = load_json(row.get("metadata")) or {}
                    return PersistedUser(
                        id=str(row["id"]),
                        identifier=row["identifier"],
                        metadata=metadata,
                        createdAt=row["created_at"].isoformat() if hasattr(row["created_at"], 'isoformat') else str(row["created_at"])
                    )
        return None

    async def create_user(self, user: Dict[str, Any]) -> Dict[str, Any]:
        await self.init_pool()

        identifier = user.get("identifier") or user.get("username") or user.get("id")
        if not identifier:
            raise ValueError("create_user requires 'identifier'")

        metadata = dump_json(user.get("metadata") or {})

        async with self.pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute(
                    """
                    INSERT INTO users (identifier, metadata)
                    VALUES (%s, %s)
                    ON DUPLICATE KEY UPDATE
                        metadata = VALUES(metadata),
                        updated_at = NOW()
                    """,
                    (identifier, metadata),
                )

                await cur.execute(
                    """
                    SELECT id, identifier, metadata, created_at, updated_at
                    FROM users
                    WHERE identifier=%s
                    LIMIT 1
                    """,
                    (identifier,),
                )
                row = await cur.fetchone()
                if not row:
                    raise RuntimeError("User insert succeeded but row could not be reloaded")

                return PersistedUser(
                    id=str(row["id"]),
                    identifier=row["identifier"],
                    metadata=load_json(row["metadata"]) or {},
                    createdAt=row["created_at"].isoformat() if hasattr(row["created_at"], 'isoformat') else str(row["created_at"])
                )

    # ----------------- Thread Methods -----------------
    async def list_threads(self, pagination, filters) -> Dict[str, Any]:
        await self.init_pool()

        user_id = filters.userId if hasattr(filters, "userId") else None
        limit = getattr(pagination, "first", 20) or 20
        offset = getattr(pagination, "cursor", 0) or 0

        async with self.pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                sql = """
                SELECT id, name, user_id, metadata, created_at, updated_at
                FROM chat_sessions
                WHERE user_id=%s
                ORDER BY updated_at DESC
                LIMIT %s OFFSET %s
                """
                await cur.execute(sql, (user_id, int(limit), int(offset)))
                rows = await cur.fetchall()
                # check if there's a next page
                has_next_page = len(rows) > limit

                threads = []
                for r in rows:
                    metadata = r.get("metadata")

                    if isinstance(metadata, str):
                        try:
                            metadata = json.loads(metadata)
                        except:
                            metadata = None

                    threads.append({
                        "id": str(r["id"]),
                        "name": r.get("name") or "Untitled Chat",
                        "userId": str(r["user_id"]),
                        "metadata": metadata,
                        "createdAt": r["created_at"].isoformat() if hasattr(r["created_at"], 'isoformat') else str(r["created_at"]),
                        "updatedAt": r["updated_at"].isoformat() if hasattr(r["updated_at"], 'isoformat') else str(r["updated_at"]),
                    })

                page_info = PageInfo(
                    hasNextPage=has_next_page,
                    startCursor=str(offset),
                    endCursor=str(offset + len(threads))
                )

                return PaginatedResponse(
                    data=threads,
                    pageInfo=page_info
                )

    async def create_thread(self, user_id: str, name: Optional[str] = None, metadata: Optional[Dict] = None) -> Dict[str, Any]:
        await self.init_pool()

        if metadata and isinstance(metadata, dict):
            metadata = json.dumps(metadata)
        elif not metadata:
            metadata = None

        async with self.pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute(
                    "INSERT INTO chat_sessions (user_id, name, metadata) VALUES (%s, %s, %s)",
                    (user_id, name, metadata),
                )
                thread_id = cur.lastrowid
                await cur.execute("SELECT created_at, updated_at FROM chat_sessions WHERE id=%s", (thread_id,))
                row = await cur.fetchone()
                return {
                    "id": str(thread_id),
                    "name": name,
                    "userIdentifier": str(user_id),
                    "metadata": metadata,
                    "createdAt": row["created_at"],
                    "updatedAt": row["updated_at"],
                }
    
    async def get_thread(self, thread_id: str) -> Optional[Dict[str, Any]]:
        await self.init_pool()
        async with self.pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute("SELECT * FROM chat_sessions WHERE id=%s", (thread_id,))
                row = await cur.fetchone()
                if not row:
                    return None

                metadata = row.get("metadata")
                if metadata and isinstance(metadata, str):
                    try:
                        metadata = json.loads(metadata)
                    except:
                        metadata = None

                return {
                    "id": str(row["id"]),
                    "name": row.get("name"),
                    "userId": str(row["user_id"]),
                    "metadata": metadata,
                    "createdAt": row["created_at"],
                    "updatedAt": row["updated_at"],
                }
            
    async def get_thread_author(self, thread_id: str) -> Optional[Dict[str, Any]]:
        await self.init_pool()
        async with self.pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute(
                    """
                    SELECT u.id, u.username, u.role, u.identifier, u.metadata
                    FROM users u
                    JOIN chat_sessions cs ON cs.user_id = u.id
                    WHERE cs.id = %s
                    """,
                    (thread_id,)
                )
                row = await cur.fetchone()
                if not row:
                    return None

                return PersistedUser(
                    id=str(row["id"]),
                    identifier=row["identifier"],
                    metadata=load_json(row.get("metadata")) or {},
                    createdAt=row["created_at"].isoformat() if hasattr(row["created_at"], 'isoformat') else str(row["created_at"])
                )

    async def update_thread(self, thread_id: str, name: Optional[str] = None, metadata: Optional[Dict] = None) -> None:
        await self.init_pool()

        metadata = thread.get("metadata")
        if metadata is not None:
            metadata = dump_json(metadata) 
        else:
            metadata = None

        async with self.pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute(
                    """
                    UPDATE chat_sessions
                    SET name=%s, metadata=%s, updated_at=NOW()
                    WHERE id=%s
                    """,
                    (name, metadata_json, thread_id),
                )
        updated = await self.get_thread(thread["id"])
        if not updated:
            return thread
        return updated

    async def delete_thread(self, thread_id: str) -> None:
        await self.init_pool()
        async with self.pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute("DELETE FROM chat_messages WHERE session_id=%s", (thread_id,))
                await cur.execute("DELETE FROM chat_sessions WHERE id=%s", (thread_id,))
    
    # ----------------- Messages -----------------
    async def get_messages(self, session_id: str) -> list[Dict[str, Any]]:
        """
        Fetch all messages for a thread, ordered by creation time.
        """
        await self.init_pool()
        async with self.pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute(
                    """
                    SELECT role, content, tool_result, created_at
                    FROM chat_messages
                    WHERE session_id=%s
                    ORDER BY created_at ASC
                    """,
                    (session_id,)
                )
                rows = await cur.fetchall()

                for r in rows:
                    if r.get("tool_result"):
                        try:
                            r["tool_result"] = json.loads(r["tool_result"])
                        except:
                            pass

                return rows

    # ----------------- Step Methods -----------------
    async def create_step(self, step_dict: Dict) -> None:
        await self.init_pool()

        # Map Chainlit StepDict to your chat_messages table
        thread_id = step_dict.get("threadId")
        # Determine role: if it's 'user_message', use 'user', otherwise 'assistant'
        role = "user" if step_dict.get("type") == "user_message" else "assistant"
        # Content can be in 'input' (for users) or 'output' (for assistant)
        content = step_dict.get("output") or step_dict.get("input") or ""
        
        # Metadata and Generation data
        metadata = step_dict.get("metadata", {})
        # If there's LLM generation data, we can bundle it into metadata
        if step_dict.get("generation"):
            metadata["generation"] = step_dict.get("generation")
        
        metadata_json = json.dumps(metadata) if metadata else None

        async with self.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    INSERT INTO chat_messages (id, session_id, role, content, tool_result)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (
                        step_dict.get("id"), # Use Chainlit's UUID to track the message
                        thread_id,
                        role,
                        content,
                        metadata_json
                    ),
                )
                # Optional: Update the session's 'updated_at' timestamp
                await cur.execute(
                    "UPDATE chat_sessions SET updated_at=NOW() WHERE id=%s",
                    (thread_id,)
                )

    async def update_step(self, step_dict: Dict) -> None:
        await self.init_pool()

        step_id = step_dict.get("id")
        content = step_dict.get("output") or step_dict.get("input") or ""
        metadata = json.dumps(step_dict.get("metadata", {}))

        async with self.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    UPDATE chat_messages 
                    SET content=%s, tool_result=%s, updated_at=NOW()
                    WHERE id=%s
                    """,
                    (content, metadata, step_id),
                )

    async def delete_step(self, *args, **kwargs):
        pass
    async def get_favorite_steps(self, *args, **kwargs):
        raise NotImplementedError

    # ----------------- Feedback Methods -----------------
    async def upsert_feedback(self, *args, **kwargs):
        raise NotImplementedError

    async def delete_feedback(self, *args, **kwargs):
        raise NotImplementedError

    # ----------------- Element Methods -----------------

    async def create_element(self, element: Element) -> None:
        await self.init_pool()

        # Chainlit's Element object provides .to_dict()
        element_dict = element.to_dict()
        
        # Extract values
        element_id = element_dict.get("id")
        thread_id = element_dict.get("threadId")
        for_id = element_dict.get("forId")  # This links it to the Message ID
        el_type = element_dict.get("type")
        name = element_dict.get("name")
        url = element_dict.get("url")
        chainlit_key = element_dict.get("chainlitKey")

        async with self.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    INSERT INTO chat_elements (id, session_id, for_id, type, name, url, chainlit_key)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE 
                        url = VALUES(url), 
                        chainlit_key = VALUES(chainlit_key)
                    """,
                    (
                        element_id,
                        thread_id,
                        for_id,
                        el_type,
                        name,
                        url,
                        chainlit_key
                    ),
                )
    # async def create_element(self, element ) -> str:
    #     await self.init_pool()

    #     if isinstance(element, Element):
    #         element_dict = element.to_dict()
    #     else:
    #         element_dict = element    

    #     thread_id = element_dict.get("threadId")
    #     role = element_dict.get("role", "assistant")
    #     content = element_dict.get("content")

    #     metadata = element_dict.get("metadata")
    #     metadata_json = dump_json(metadata) if metadata else None

    #     async with self.pool.acquire() as conn:
    #         async with conn.cursor(aiomysql.DictCursor) as cur:
    #             await cur.execute(
    #                 """
    #                 INSERT INTO chat_messages (session_id, role, content, tool_result)
    #                 VALUES (%s, %s, %s, %s)
    #                 """,
    #                 (
    #                     thread_id,
    #                     role,
    #                     content,
    #                     metadata_json,
    #                 ),
    #             )
    #             last_id = str(cur.lastrowid)

    #             # Update last activity
    #             await cur.execute(
    #                 "UPDATE chat_sessions SET updated_at=NOW() WHERE id=%s",
    #                 (thread_id,)
    #             )

    #             return last_id

    async def get_element(self, element_id: str):
        raise NotImplementedError

    async def delete_element(self, element_id: str):
        raise NotImplementedError