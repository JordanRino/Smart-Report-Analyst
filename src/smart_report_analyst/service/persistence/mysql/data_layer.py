import aiomysql
from typing import Optional, Dict, List
from chainlit.data import BaseDataLayer
from chainlit.types import User, Feedback, ElementDict, StepDict, ThreadDict, Pagination, ThreadFilter, PaginatedResponse

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
                autocommit=True
            )

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
                    (user.metadata["username"], user.metadata["password_hash"], user.metadata.get("role", "user"))
                )
                user_id = cur.lastrowid
                user.identifier = str(user_id)
                return user

    async def list_threads(self, pagination: Pagination, filters: ThreadFilter) -> PaginatedResponse[ThreadDict]:
        await self.init_pool()
        async with self.pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                sql = "SELECT * FROM chat_sessions WHERE user_id=%s ORDER BY updated_at DESC LIMIT %s OFFSET %s"
                await cur.execute(sql, (filters.user_id, pagination.limit, pagination.offset))
                rows = await cur.fetchall()
                threads = [
                    ThreadDict(
                        id=str(r["id"]),
                        user_id=str(r["user_id"]),
                        name=r.get("name"),
                        metadata=r.get("metadata")
                    )
                    for r in rows
                ]
                return PaginatedResponse(items=threads, total=len(threads))

    async def create_thread(self, user_id: str, name: Optional[str] = None, metadata: Optional[Dict] = None) -> ThreadDict:
        await self.init_pool()
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "INSERT INTO chat_sessions (user_id, name, metadata) VALUES (%s, %s, %s)",
                    (user_id, name, metadata)
                )
                thread_id = cur.lastrowid
                return ThreadDict(id=str(thread_id), user_id=user_id, name=name, metadata=metadata)

    async def create_element(self, element_dict: ElementDict):
        await self.init_pool()
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "INSERT INTO chat_messages (session_id, role, content, tool_result) VALUES (%s, %s, %s, %s)",
                    (
                        element_dict.thread_id,
                        element_dict.role,
                        element_dict.content,
                        element_dict.metadata or None,
                    )
                )
                return str(cur.lastrowid)