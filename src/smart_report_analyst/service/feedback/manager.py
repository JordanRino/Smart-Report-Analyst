"""Handles feedback logic and integration with backend services."""

from email.mime import message
import logging

from smart_report_analyst.service.streamlit.state import UIState
from smart_report_analyst.service.lambda_function.manager import LambdaManager
from smart_report_analyst.config.settings import Settings

logger = logging.getLogger(__name__)
settings = Settings()


def handle_positive_feedback(message_id: str):
    """
    Handles thumbs-up feedback for a message.

    Flow:
    - Update feedback state
    - Extract metadata (SQL + refined question)
    - Invoke Lambda to store data
    """

    # Firs we gotta Update feedback in state
    UIState.set_feedback(message_id, "like")

    message = UIState.get_message_by_id(message_id)

    if not message:
        logger.warning(f"Message not found for ID: {message_id}")
        return {"status": "error", "message": "Message not found"}


    metadata = message.get("metadata", {})
    user_question = metadata.get("user_question")
    agent_response = message.get("content")

    if not user_question or not agent_response:
        logger.warning("Missing user question or agent response in metadata")
        return {"status": "error", "message": "Missing metadata"}
    
    # After we get the metadata we Invoke Lambda
    try:
        lambda_manager = LambdaManager()

        payload = {
            "parameters": [
                {"name": "query", "value": user_question},
                {"name": "refined_user_question", "value": agent_response},
            ]
        }

        print("\n INVOKING LAMBDA WITH:", payload)

        lambda_manager.invoke_function(
            function_name=settings.STORE_SQL_LAMBDA_FUNCTION_NAME,
            function_params=payload,
        )

        logger.info(f"Stored successful query for message {message_id}")

        return {"status": "success"}

    except Exception as e:
        logger.error(f"Lambda invocation failed: {e}")
        return {"status": "error", "message": str(e)}