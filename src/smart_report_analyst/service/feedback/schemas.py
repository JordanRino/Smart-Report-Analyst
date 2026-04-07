"""Request bodies for feedback HTTP APIs (kept out of ``routes.py``)."""

from __future__ import annotations

from pydantic import BaseModel, model_validator


class FeedbackPositiveBody(BaseModel):
    """Built-in thumbs: ``message_id`` + ``thread_id``. Direct Helpful: question + SQL."""

    message_id: str | None = None
    thread_id: str | None = None
    refined_user_question: str | None = None
    executed_sql: str | None = None
    to_store: bool | None = None

    @model_validator(mode="after")
    def one_mode(self) -> FeedbackPositiveBody:
        by_msg = bool(self.message_id and self.thread_id)
        direct = bool(self.refined_user_question and self.executed_sql)
        if by_msg == direct:
            raise ValueError(
                "Provide exactly one of: (message_id + thread_id) OR (refined_user_question + executed_sql)"
            )
        return self
