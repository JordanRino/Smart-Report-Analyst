from typing import Optional
import bcrypt
import aiomysql
import chainlit as cl

from smart_report_analyst.config.settings import Settings
from smart_report_analyst.service.persistence.mysql.data_layer import MySQLDataLayer

settings = Settings()

data_layer = MySQLDataLayer(
    host=settings.MYSQL_HOST,
    user=settings.MYSQL_USER,
    password=settings.MYSQL_PASSWORD,
    db=settings.MYSQL_DB,
    port=settings.MYSQL_PORT,
)


@cl.password_auth_callback
async def auth_callback(username: str, password: str) -> Optional[cl.User]:
    """Authenticate the user and store them in user_session for chat initialization."""
    await data_layer.init_pool()

    async with data_layer.pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute(
                "SELECT * FROM users WHERE username=%s", (username,)
            )
            row = await cur.fetchone()

            if not row:
                return None

            # Verify password
            if bcrypt.checkpw(password.encode(), row["password_hash"].encode()):
                user = cl.User(
                    identifier=str(row["id"]),
                    metadata={
                        "username": row["username"],
                        "role": row["role"],
                    },
                )
                cl.user_session.set("user", user)
                return user

    return None