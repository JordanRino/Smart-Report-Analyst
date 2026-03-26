"""MySQL Data Layer for Chainlit persistence."""

import aiomysql
import json

from __future__ import annotations
from typing import Optional, Dict, Any
from chainlit.data import BaseDataLayer
from typing import Any, Dict, Optional, List


# Minimal replacements for Chainlit types
class ThreadDict:
    def __init__(self, id: str, user_id: str, name: Optional[str] = None, metadata: Optional[Dict] = None):
        self.id = id
        self.user_id = user_id
        self.name = name
        self.metadata = metadata

class ElementDict:
    def __init__(self, thread_id: str, role: str, content: str, metadata: Optional[Dict] = None):
        self.thread_id = thread_id
        self.role = role
        self.content = content
        self.metadata = metadata

class Pagination:
    def __init__(self, limit: int = 10, offset: int = 0):
        self.limit = limit
        self.offset = offset

class ThreadFilter:
    def __init__(self, user_id: str):
        self.user_id = user_id

class PaginatedResponse:
    def __init__(self, items: List[Any], total: int):
        self.items = items
        self.total = total

# If you need User, use cl.user_session instead of importing User from Chainlit
class User:
    def __init__(self, identifier: str, metadata: Dict[str, Any]):
        self.identifier = identifier
        self.metadata = metadata


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
    async def get_user(self, identifier: str) -> Optional[User]:
        await self.init_pool()
        async with self.pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute("SELECT * FROM users WHERE id=%s", (identifier,))
                row = await cur.fetchone()
                if row:
                    return User(identifier=str(row["id"]), metadata={"username": row["username"], "role": row["role"]})
        return None

    async def create_user(self, user: User) -> User:
        await self.init_pool()
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "INSERT INTO users (username, password_hash, role) VALUES (%s, %s, %s)",
                    (
                        user.metadata["username"],
                        user.metadata.get("password_hash", ""),
                        user.metadata.get("role", "user"),
                    ),
                )
                user.identifier = str(cur.lastrowid)
                return user

    # ----------------- Thread Methods -----------------
    async def list_threads(self, pagination: Pagination, filters: ThreadFilter) -> PaginatedResponse[ThreadDict]:
        await self.init_pool()
        async with self.pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                sql = "SELECT * FROM chat_sessions WHERE user_id=%s ORDER BY updated_at DESC LIMIT %s OFFSET %s"
                await cur.execute(sql, (filters.user_id, pagination.limit, pagination.offset))
                rows = await cur.fetchall()
                threads = [
                    ThreadDict(id=str(r["id"]), user_id=str(r["user_id"]), name=r.get("name"), metadata=r.get("metadata"))
                    for r in rows
                ]
                return PaginatedResponse(items=threads, total=len(threads))

    async def create_thread(self, user_id: str, name: Optional[str] = None, metadata: Optional[Dict] = None) -> ThreadDict:
        await self.init_pool()
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "INSERT INTO chat_sessions (user_id, name, metadata) VALUES (%s, %s, %s)",
                    (user_id, name, metadata),
                )
                thread_id = cur.lastrowid
                return ThreadDict(id=str(thread_id), user_id=user_id, name=name, metadata=metadata)

    async def get_thread(self, thread_id: str) -> ThreadDict:
        raise NotImplementedError

    async def get_thread_author(self, thread_id: str) -> Optional[User]:
        raise NotImplementedError

    async def update_thread(self, thread: ThreadDict) -> ThreadDict:
        raise NotImplementedError

    async def delete_thread(self, thread_id: str) -> None:
        raise NotImplementedError

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
    async def create_element(self, element_dict: ElementDict):
        await self.init_pool()
        if isinstance(element_dict.metadata, dict):
            element_dict.metadata = json.dumps(element_dict.metadata)
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "INSERT INTO chat_messages (session_id, role, content, tool_result) VALUES (%s, %s, %s, %s)",
                    (
                        element_dict.thread_id,
                        element_dict.role,
                        element_dict.content,
                        element_dict.metadata or None,
                    ),
                )
                return str(cur.lastrowid)

    async def get_element(self, element_id: str):
        raise NotImplementedError

    async def delete_element(self, element_id: str):
        raise NotImplementedError