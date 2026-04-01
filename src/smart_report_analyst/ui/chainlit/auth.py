from typing import Optional
import bcrypt
import aiomysql
import chainlit as cl

from smart_report_analyst.config.settings import get_settings
from smart_report_analyst.service.persistence.mysql.chainlit_data_layer import data_layer

settings = get_settings()


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
                print("\nAuthentication successful")
                return cl.User(
                    identifier=str(row["id"]),
                    metadata={
                        "username": row["username"],
                        "role": row["role"],
                    },
                )
            else:
                print("\nInvalid credentials")

    return None