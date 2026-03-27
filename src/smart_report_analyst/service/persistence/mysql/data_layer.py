"""MySQL Data Layer for Chainlit persistence."""

from __future__ import annotations

import aiomysql
import json

from typing import Optional, Dict, Any
from chainlit.data import BaseDataLayer
from typing import Any, Dict, Optional, List


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
                await cur.execute("SELECT * FROM users WHERE id=%s", (identifier,))
                row = await cur.fetchone()
                if row:
                    return {
                        "id": str(row["id"]),
                        "username": row["username"],
                        "role": row["role"]
                    }   
        return None

    async def create_user(self, user: Dict[str, Any]) -> Dict[str, Any]:
        await self.init_pool()
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "INSERT INTO users (username, password_hash, role) VALUES (%s, %s, %s)",
                    (
                        user["username"],
                        user.get("password_hash", ""),
                        user.get("role", "user"),
                    ),
                )
                user_id = str(cur.lastrowid)
                return {
                    "id": user_id,
                    "username": user["username"],
                    "role": user.get("role", "user"),
                }

    # ----------------- Thread Methods -----------------
    async def list_threads(self, pagination: Dict, filters: Dict) -> Dict[str, Any]:
        await self.init_pool()
        async with self.pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                sql = """
                SELECT * FROM chat_sessions
                WHERE user_id=%s
                ORDER BY updated_at DESC
                LIMIT %s OFFSET %s
                """
                await cur.execute(sql, (filters["user_id"], pagination["limit"], pagination["offset"]))
                rows = await cur.fetchall()

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
                        "name": r.get("name"),
                        "userId": str(r["user_id"]),
                        "metadata": metadata,
                        "createdAt": r["created_at"],
                        "updatedAt": r["updated_at"],
                    })

                return {"items": threads, "total": len(threads)}

    async def create_thread(self, user_id: str, name: Optional[str] = None, metadata: Optional[Dict] = None) -> Dict[str, Any]:
        await self.init_pool()

        if metadata and isinstance(metadata, dict):
            metadata = json.dumps(metadata)

        async with self.pool.acquire() as conn:
            async with conn.cursor() as cur:
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
                    "userId": str(user_id),
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
                if isinstance(metadata, str):
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
                    SELECT u.id, u.username, u.role
                    FROM users u
                    JOIN chat_sessions cs ON cs.user_id = u.id
                    WHERE cs.id = %s
                    """,
                    (thread_id,)
                )
                row = await cur.fetchone()
                if not row:
                    return None

                return {
                    "id": str(row["id"]),
                    "metadata": {
                        "username": row["username"],
                        "role": row["role"]
                    }
                }

    async def update_thread(self, thread: Dict[str, Any]) -> Dict[str, Any]:
        await self.init_pool()

        metadata = thread["metadata"]
        if isinstance(metadata, dict):
            metadata = json.dumps(metadata)

        async with self.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    UPDATE chat_sessions
                    SET name=%s, metadata=%s, updated_at=NOW()
                    WHERE id=%s
                    """,
                    (thread["name"], metadata, thread["id"]),
                )
        return thread

    async def delete_thread(self, thread_id: str) -> None:
        await self.init_pool()
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cur:
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
    async def create_step(self, *args, **kwargs):
        raise NotImplementedError

    async def update_step(self, *args, **kwargs):
        raise NotImplementedError

    async def delete_step(self, *args, **kwargs):
        raise NotImplementedError

    async def get_favorite_steps(self, *args, **kwargs):
        raise NotImplementedError

    # ----------------- Feedback Methods -----------------
    async def upsert_feedback(self, *args, **kwargs):
        raise NotImplementedError

    async def delete_feedback(self, *args, **kwargs):
        raise NotImplementedError

    # ----------------- Element Methods -----------------
    async def create_element(self, element_dict: Dict[str, Any]) -> str:
        await self.init_pool()

        metadata = element_dict.get("metadata")
        if isinstance(metadata, dict):
            element_dict["metadata"] = json.dumps(metadata)

        async with self.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    INSERT INTO chat_messages (session_id, role, content, tool_result)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (
                        element_dict["thread_id"],
                        element_dict["role"],
                        element_dict["content"],
                        element_dict.get("metadata") or None,
                    ),
                )

                # Update last activity
                await cur.execute(
                    "UPDATE chat_sessions SET updated_at=NOW() WHERE id=%s",
                    (element_dict["thread_id"],)
                )

                return str(cur.lastrowid)

    async def get_element(self, element_id: str):
        raise NotImplementedError

    async def delete_element(self, element_id: str):
        raise NotImplementedError