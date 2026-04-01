import boto3
import logging
import json
from botocore.exceptions import ClientError, EventStreamError
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
                                    print (f"\n Tool result: {json.dumps(tool_result, indent=2)}")
                                    logger.info(f"Tool result: {json.dumps(tool_result)}")
                                except json.JSONDecodeError:
                                    tool_result = raw_text

            except ClientError as e:
                logger.error(f"Couldn't invoke agent. {e}")
                raise
            formatted_response = {
                "final_response": completion,
                "user_question": prompt,
                "tool_result": tool_result,
            }
            return formatted_response
    
    def invoke_agent_stream(self, prompt, agent_id, agent_alias_id, session_id):
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
                                except:
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
    # def invoke_orchestration(self, prompt, session_id):
    #     """
    #     Sends a prompt for the orchestration to process and respond to.

    #     :param prompt: The prompt that you want the orchestration to complete.
    #     :param session_id: The unique identifier of the session. Defaults to BEDROCK_SESSION_ID from settings.
    #     :return: Inference response from the multi-agent orchestration.
    #     """

    #     # First we pass the prompt to the CoOrdinatorAgent which will refine the prompt, if its a user question.

    #     try:
    #         # refined_user_question = self.invoke_agent(
    #         #     prompt=prompt,
    #         #     agent_id=settings.COORDINATOR_BEDROCK_AGENT_ID,
    #         #     agent_alias_id=settings.COORDINATOR_BEDROCK_AGENT_ALIAS_ID,
    #         #     session_id=session_id,
    #         # )
    #         # print("\n Prompt sent to CoOrdinatorAgent:", prompt)
    #         # print("\n Refined user question:", refined_user_question)
    #         # logger.info(f"Refined user question: {refined_user_question}")

    #         # Then we pass user question to the SQL Generator agent which will generate the SQL query.
    #         sql_generator_raw_response = self.invoke_agent(
    #             prompt=prompt,
    #             agent_id=settings.SQL_GENERATOR_BEDROCK_AGENT_ID,
    #             agent_alias_id=settings.SQL_GENERATOR_BEDROCK_AGENT_ALIAS_ID,
    #             session_id=session_id,
    #         )
    #         try:
    #             sql_generator_response = json.loads(sql_generator_raw_response)
    #         except json.JSONDecodeError:
    #             logger.error(f"SQL Generator returned invalid JSON: {sql_generator_raw_response}")
    #             raise ValueError("SQL Generator agent output was not valid JSON")
            
    #         sql_query = sql_generator_response.get("sql_query")
    #         store_sql = sql_generator_response.get("store_sql")
    #         if isinstance(store_sql, str):
    #             store_sql = store_sql.lower() == "true"
    #         print("\n Generated SQL query:", sql_query)  
    #         print("\n Store SQL:", store_sql)
    #         logger.info(f"\nGenerated SQL query: {sql_query}")
    #         logger.info(f"\nStore SQL: {store_sql}")

    #         # Then we pass the SQL query to the SQL Executor agent which will execute the query and return the results.
    #         sql_executor_raw_response = self.invoke_agent(
    #             prompt=json.dumps(sql_generator_response),
    #             agent_id=settings.SQL_EXECUTOR_BEDROCK_AGENT_ID,
    #             agent_alias_id=settings.SQL_EXECUTOR_BEDROCK_AGENT_ALIAS_ID,
    #             session_id=session_id,
    #         )
    #         try:
    #             sql_executor_response = json.loads(sql_executor_raw_response)
    #         except json.JSONDecodeError:
    #             logger.error(f"SQL Executor returned invalid JSON: {sql_executor_raw_response}")
    #             raise ValueError("SQL Executor agent output was not valid JSON")
            
    #         executed_sql = sql_executor_response.get("executed_sql_query")
    #         results = sql_executor_response.get("results")

    #         print("\n SQL Executor Response:", json.dumps(sql_executor_response, indent=2))
    #         logger.info(f"Executed SQL: {executed_sql}")
    #         logger.info(f"Execution results: {results}")
    #         formatted_prompt = f"User question: {prompt}\n\nExecuted SQL: {executed_sql}\n\nResults: {results}"
            
    #         # Then we pass the SQL execution response back to the CoOrdinatorAgent which will generate the final answer for the user.
    #         final_response = self.invoke_agent(
    #             prompt=formatted_prompt,
    #             agent_id=settings.COORDINATOR_BEDROCK_AGENT_ID,
    #             agent_alias_id=settings.COORDINATOR_BEDROCK_AGENT_ALIAS_ID,
    #             session_id=session_id,
    #         )
    #         logger.info(f"Final response: {final_response}")
    #         formatted_final_response = {
    #             "final_response": final_response,
    #             "sql_query": sql_query,
    #             "refined_user_question": prompt,
    #             "store_sql": store_sql,
    #         }
    #         return formatted_final_response

    #     except ClientError as e:
    #         logger.error(f"Couldn't invoke orchestration. {e}")
    #         raise
