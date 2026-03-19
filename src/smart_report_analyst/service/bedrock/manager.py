import boto3
import logging
from botocore.exceptions import ClientError
from smart_report_analyst.config.settings import Settings

settings = Settings()
logger = logging.getLogger(__name__)

class BedrockManager:

    def __init__(self):
        self.agents_runtime_client = boto3.client(
            "bedrock-agent-runtime", region_name=settings.AWS_REGION
        )

    def get_bedrock_agent_runtime_client(self):
        return self.agents_runtime_client
    
    def invoke_agent(self, prompt, agent_id, agent_alias_id, session_id):
            """
            Sends a prompt for the agent to process and respond to.

            :param prompt: The prompt that you want Claude to complete.
            :param agent_id: The BEDROCK_AGENT_ID from settings.
            :param agent_alias_id: The BEDROCK_AGENT_ALIAS_ID from settings.
            :param session_id: The unique identifier of the session. Defaults to BEDROCK_SESSION_ID from settings.
            :return: Inference response from the model.
            """

            try:
                # Note: The execution time depends on the foundation model, complexity of the agent,
                # and the length of the prompt. In some cases, it can take up to a minute or more to
                # generate a response.
                response = self.agents_runtime_client.invoke_agent(
                    agentId=agent_id,
                    agentAliasId=agent_alias_id,
                    sessionId=session_id,
                    inputText=prompt,
                )

                completion = ""

                for event in response.get("completion"):
                    chunk = event["chunk"]
                    completion = completion + chunk["bytes"].decode()

            except ClientError as e:
                logger.error(f"Couldn't invoke agent. {e}")
                raise

            return completion
    
    def invoke_orchestration(self, prompt, session_id):
        """
        Sends a prompt for the orchestration to process and respond to.

        :param prompt: The prompt that you want the orchestration to complete.
        :param session_id: The unique identifier of the session. Defaults to BEDROCK_SESSION_ID from settings.
        :return: Inference response from the multi-agent orchestration.
        """

        # First we pass the prompt to the CoOrdinatorAgent which will refine the prompt, if its a user question.

        try:
            refined_user_question = self.invoke_agent(
                prompt=prompt,
                agent_id=settings.COORDINATOR_BEDROCK_AGENT_ID,
                agent_alias_id=settings.COORDINATOR_BEDROCK_AGENT_ALIAS_ID,
                session_id=session_id,
            )
            logger.info(f"Refined user question: {refined_user_question}")

            # Then we pass the refined  user question to the SQL Generator agent which will generate the SQL query.
            sql_query = self.invoke_agent(
                prompt=refined_user_question,
                agent_id=settings.SQL_GENERATOR_BEDROCK_AGENT_ID,
                agent_alias_id=settings.SQL_GENERATOR_BEDROCK_AGENT_ALIAS_ID,
                session_id=session_id,
            )
            logger.info(f"Generated SQL query: {sql_query}")

            # Then we pass the SQL query to the SQL Executor agent which will execute the query and return the results.
            sql_execution_response = self.invoke_agent(
                prompt=sql_query,
                agent_id=settings.SQL_EXECUTOR_BEDROCK_AGENT_ID,
                agent_alias_id=settings.SQL_EXECUTOR_BEDROCK_AGENT_ALIAS_ID,
                session_id=session_id,
            )
            logger.info(f"SQL execution response: {sql_execution_response}")

            # Then we pass the SQL execution response back to the CoOrdinatorAgent which will generate the final answer for the user.
            final_response = self.invoke_agent(
                prompt=sql_execution_response,
                agent_id=settings.COORDINATOR_BEDROCK_AGENT_ID,
                agent_alias_id=settings.COORDINATOR_BEDROCK_AGENT_ALIAS_ID,
                session_id=session_id,
            )
            logger.info(f"Final response: {final_response}")
            return final_response

        except ClientError as e:
            logger.error(f"Couldn't invoke orchestration. {e}")
            raise