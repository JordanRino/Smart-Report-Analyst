import logging
from botocore.exceptions import ClientError

from config.settings import Settings

logger = logging.getLogger(__name__)
settings = Settings()


class CoOrdinatorAgent:
    def __init__(self, agents_runtime_client):
        self.agents_runtime_client = agents_runtime_client

    def invoke_agent(self, prompt,session_id=None):
            """
            Sends a prompt for the agent to process and respond to.

            :param prompt: The prompt that you want Claude to complete.
            :param agent_id: The BEDROCK_AGENT_ID from settings.
            :param agent_alias_id: The BEDROCK_AGENT_ALIAS_ID from settings.
            :param session_id: The unique identifier of the session. Defaults to BEDROCK_SESSION_ID from settings.
            :return: Inference response from the model.
            """
            
            # Use settings values if not provided
            agent_id = settings.BEDROCK_AGENT_ID
            agent_alias_id = settings.BEDROCK_AGENT_ALIAS_ID
            session_id = session_id or settings.BEDROCK_SESSION_ID

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


