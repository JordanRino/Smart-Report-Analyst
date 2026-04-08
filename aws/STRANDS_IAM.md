# IAM notes: Strands + Bedrock Knowledge Base path

When `AGENT_BACKEND=strands`, the application principal (user, role, or task role) needs permissions **in addition** to any existing `bedrock:InvokeAgent` policies used by the default Bedrock Agent path.

## Bedrock Runtime (Strands `BedrockModel`)

- `bedrock:InvokeModel`
- `bedrock:InvokeModelWithResponseStream`

Scope `Resource` to your model or inference profile ARNs in production.

### Bedrock Guardrails (optional)

When `BEDROCK_GUARDRAIL_ID` is set, inference attaches that guardrail. The runtime role typically also needs:

- `bedrock:ApplyGuardrail` on the guardrail resource ARN (see [Guardrails permissions](https://docs.aws.amazon.com/bedrock/latest/userguide/guardrails-permissions.html)).

Creating or editing guardrails in AWS uses APIs such as `bedrock:CreateGuardrail` (see [Boto3 `create_guardrail`](https://docs.aws.amazon.com/boto3/latest/reference/services/bedrock/client/create_guardrail.html)); those are operator/console permissions, not required on the app role unless your deployment creates guardrails from code.

## Knowledge Base retrieve

Retriever logic lives in `smart_report_analyst.service.bedrock.kb_manager`. The app calls `bedrock-agent-runtime:Retrieve` with `BEDROCK_KNOWLEDGE_BASE_ID`.

- Grant `bedrock:Retrieve` (confirm exact action name in the current [Bedrock IAM reference](https://docs.aws.amazon.com/service-authorization/latest/reference/list_amazonbedrock.html) for your API variant) on the knowledge base ARN.

## Lambda (unchanged)

- `lambda:InvokeFunction` on `STORE_SQL_LAMBDA_FUNCTION_NAME`.
- When `STRANDS_SQL_LAMBDA_FUNCTION_NAME` is set, Strands `execute_sql` invokes that function instead; grant `lambda:InvokeFunction` on that ARN or name as well.

## Migration

Keep `bedrock:InvokeAgent` while `AGENT_BACKEND=bedrock_agent` remains the default or in use; add Strands/KB permissions alongside, then narrow policies after cutover.

## Operations / logging

Strands turns log at INFO on `smart_report_analyst.service.strands.runner` with messages `strands_stream_turn` and `strands_complete_turn` and `extra` fields `prior_turns` and `user_chars`. Point your log aggregator at those keys if you need turn-level metrics without enabling debug for the whole app.
