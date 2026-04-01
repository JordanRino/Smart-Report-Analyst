import logging
import asyncio

from smart_report_analyst.service.lambda_function.manager import LambdaManager
from smart_report_analyst.config.settings import get_settings
from smart_report_analyst.service.persistence.mysql.app_data_layer import app_data_layer

logger = logging.getLogger(__name__)
settings = get_settings()


def handle_positive_feedback(payload: dict):
    """
    Handles thumbs-up feedback.

    Expected payload:
    {
        "refined_user_question": str,
        "executed_sql": str,
        "to_store": bool
    }
    """

    refined_user_question = payload.get("refined_user_question")
    executed_sql = payload.get("executed_sql")
    to_store = payload.get("to_store")

    if not refined_user_question or not executed_sql:
        logger.warning("Missing refined_user_question or executed_sql")
        return {"status": "error", "message": "Missing required fields"}

    if not to_store:
        logger.info("Skipping storage (duplicate or reused query)")
        return {
            "status": "success",
            "message": "Skipped storing duplicate query",
        }

    try:
        # lambda_manager = LambdaManager()

        # lambda_payload = {
        #     "parameters": [
        #         {"name": "refined_user_question", "value": refined_user_question},
        #         {"name": "query", "value": executed_sql},
        #     ]
        # }

        # print("\n INVOKING LAMBDA WITH:", lambda_payload)

        # lambda_manager.invoke_function(
        #     function_name=settings.STORE_SQL_LAMBDA_FUNCTION_NAME,
        #     function_params=lambda_payload,
        # )

        asyncio.run(app_data_layer.store_successful_query(refined_user_question, executed_sql))

        return {"status": "success"}

    except Exception as e:
        logger.error(f"Failed to store successful query: {e}")
        return {"status": "error", "message": str(e)}