import boto3
import logging
import json
from botocore.exceptions import ClientError, EventStreamError
from smart_report_analyst.config.settings import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)


class BedrockManager:
    def __init__(self):
        self.agents_runtime_client = boto3.client(
            "bedrock-agent-runtime", region_name=settings.AWS_REGION
        )

    def get_bedrock_agent_runtime_client(self):
        """Return the initialized Bedrock Agent Runtime client."""
        return self.agents_runtime_client

    def invoke_agent(self, prompt, agent_id, agent_alias_id, session_id):
        """
        Invoke a managed Bedrock Agent (InvokeAgent) and return its final text.

        This consumes the event stream and concatenates any `chunk` bytes into a single
        `final_response`. If the agent triggers an action group invocation and returns
        a JSON payload as text, `tool_result` is parsed and returned as an object.

        Args:
            prompt: Natural language user prompt.
            agent_id: Bedrock Agent ID.
            agent_alias_id: Bedrock Agent alias ID.
            session_id: Conversation/session identifier.

        Returns:
            Dict with keys: `final_response`, `user_question`, `tool_result`.

        Raises:
            botocore.exceptions.ClientError: If Bedrock invocation fails.
        """
        try:
            # Execution time depends on model + agent complexity and can exceed 60s.
            response = self.agents_runtime_client.invoke_agent(
                agentId=agent_id,
                agentAliasId=agent_alias_id,
                sessionId=session_id,
                inputText=prompt,
                enableTrace=True,
            )

            completion = ""
            tool_result = None

            for event in response.get("completion"):
                if "chunk" in event:
                    chunk = event["chunk"]
                    completion = completion + chunk["bytes"].decode()
                if "trace" in event:
                    trace = event["trace"].get("trace", {})
                    orchestration = trace.get("orchestrationTrace", {})
                    observation = orchestration.get("observation", {})

                    if "actionGroupInvocationOutput" in observation:
                        action_output = observation.get("actionGroupInvocationOutput")
                        if action_output and action_output.get("text"):
                            raw_text = action_output["text"]
                            try:
                                tool_result = json.loads(raw_text)
                                logger.info("Tool result: %s", json.dumps(tool_result))
                            except json.JSONDecodeError:
                                tool_result = raw_text

        except ClientError as e:
            logger.error("Couldn't invoke agent. %s", e)
            raise
        formatted_response = {
            "final_response": completion,
            "user_question": prompt,
            "tool_result": tool_result,
        }
        return formatted_response

    def invoke_agent_stream(self, prompt, agent_id, agent_alias_id, session_id):
        """
        Invoke a managed Bedrock Agent and yield a simplified event stream.

        Yields dicts of shape:
        - `{ "type": "chunk", "data": "<text>" }`
        - `{ "type": "tool_result", "data": <object|string> }`
        - `{ "type": "error", "data": "<message>" }`
        """
        try:
            response = self.agents_runtime_client.invoke_agent(
                agentId=agent_id,
                agentAliasId=agent_alias_id,
                sessionId=session_id,
                inputText=prompt,
                enableTrace=True,
                streamingConfigurations={"streamFinalResponse": True},
            )
            
            try:
                for event in response.get("completion"):
                    if "chunk" in event:
                        yield {
                            "type": "chunk",
                            "data": event["chunk"]["bytes"].decode(),
                        }

                    if "trace" in event:
                        trace = event["trace"].get("trace", {})
                        orchestration = trace.get("orchestrationTrace", {})
                        observation = orchestration.get("observation", {})

                        if "actionGroupInvocationOutput" in observation:
                            action_output = observation.get("actionGroupInvocationOutput")

                            if action_output and action_output.get("text"):
                                try:
                                    tool_result = json.loads(action_output["text"])
                                except (json.JSONDecodeError, TypeError, ValueError):
                                    tool_result = action_output["text"]

                                yield {
                                    "type": "tool_result",
                                    "data": tool_result,
                                }

            except EventStreamError as e:
                logger.error(f"Stream error: {e}")

                yield {
                    "type": "error",
                    "data": str(e),
                }

        except ClientError as e:
            logger.error(f"Couldn't invoke agent. {e}")
            raise
