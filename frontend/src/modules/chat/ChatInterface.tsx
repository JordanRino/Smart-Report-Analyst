"use client";

import { useCallback, useMemo } from "react";
import { useApp } from "@/providers/AppContext";
import {
  AssistantMessage,
  CopilotChat,
  ImageRenderer,
  UserMessage,
  type RenderMessageProps,
} from "@copilotkit/react-ui";
import { ActionRenderProps, useCopilotAction } from "@copilotkit/react-core";
import type { ReasoningMessage } from "@copilotkit/shared";
import { SqlResultPdfReport } from "@/modules/reports/SqlResultPdfReport";
import { ReportBuilderCard } from "@/modules/reports/ReportBuilderCard";
import { ReasoningTraceMessage } from "@/components/agent-trace/ReasoningTraceMessage";
import { AgentPicker } from "./AgentPicker";
import { CopilotPrefillInput } from "./CopilotPrefillInput";
import { getApiPrefix } from "@/lib/env";
import {
  CHAT_ATTACHMENTS_ACCEPT,
  CHAT_ATTACHMENTS_MAX_BYTES,
} from "@/lib/chatAttachments";

/**
 * Match ``@copilotkit/react-ui`` default ``RenderMessage`` routing so user/assistant
 * still render when we only customize AG-UI reasoning (server tool trace).
 */
function AgentRenderMessage(props: RenderMessageProps) {
  const {
    message,
    messages,
    inProgress,
    index,
    isCurrentMessage,
    AssistantMessage: AssistantMessageOverride,
    UserMessage: UserMessageOverride,
    ImageRenderer: ImageRendererOverride,
    onRegenerate,
    onCopy,
    onThumbsUp,
    onThumbsDown,
    messageFeedback,
    markdownTagRenderers,
  } = props;

  const User = UserMessageOverride ?? UserMessage;
  const Assistant = AssistantMessageOverride ?? AssistantMessage;
  const Img = ImageRendererOverride ?? ImageRenderer;

  if (message.role === "reasoning") {
    return (
      <ReasoningTraceMessage
        message={message as ReasoningMessage}
        inProgress={Boolean(inProgress && isCurrentMessage)}
      />
    );
  }

  switch (message.role) {
    case "user":
      return (
        <User
          key={index}
          rawData={message}
          data-message-role="user"
          message={message}
          ImageRenderer={Img}
        />
      );
    case "assistant":
      return (
        <Assistant
          key={index}
          data-message-role="assistant"
          subComponent={message.generativeUI?.()}
          rawData={message}
          message={message}
          messages={messages}
          isLoading={inProgress && isCurrentMessage && !message.content}
          isGenerating={inProgress && isCurrentMessage && !!message.content}
          isCurrentMessage={isCurrentMessage}
          onRegenerate={() => onRegenerate?.(message.id)}
          onCopy={onCopy}
          onThumbsUp={onThumbsUp}
          onThumbsDown={onThumbsDown}
          feedback={messageFeedback?.[message.id] || null}
          markdownTagRenderers={markdownTagRenderers}
          ImageRenderer={Img}
        />
      );
    default:
      return null;
  }
}

export function ChatInterface() {
  const { effectiveThreadId, pickedAgentId, orchestratorMainAgentId } = useApp();

  /** CopilotKit message thumbs-up → server snapshot (agent.py) → MySQL successful_queries. */
  const onFeedbackGiven = useCallback(
    (messageId: string, type: "thumbsUp" | "thumbsDown") => {
      if (type !== "thumbsUp" || !effectiveThreadId) return;
      void fetch(`${getApiPrefix()}/feedback/positive`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message_id: messageId,
          thread_id: effectiveThreadId,
        }),
      }).catch(() => {
        /* ignore network errors for observability hook */
      });
    },
    [effectiveThreadId],
  );

  const observabilityHooks = useMemo(
    () => ({ onFeedbackGiven }),
    [onFeedbackGiven],
  );

  const copilotLabels = useMemo(() => {
    const initial = orchestratorMainAgentId
      ? "I'm the WLR Reporting Agent—how can I assist you today?"
      : "Please choose your team's specialist in the bar above";

    return {
      title: "Smart Report Analyst",
      initial,
    };
  }, [orchestratorMainAgentId]);

  useCopilotAction({
    name: "deliver_report",
    available: "frontend",
    description: "Displays a narrative PDF report generated and auto-saved by the report_builder agent.",
    parameters: [
      { name: "report_id", type: "string", description: "Permanent report ID in the saved store" },
      { name: "title", type: "string", description: "Report title" },
    ],
    render: ({
      status,
      args,
    }: ActionRenderProps<
      [
        { name: "report_id"; type: "string"; description: string },
        { name: "title"; type: "string"; description: string },
      ]
    >): React.ReactElement => (
      <ReportBuilderCard
        status={status}
        report_id={typeof args.report_id === "string" ? args.report_id : ""}
        title={typeof args.title === "string" ? args.title : ""}
      />
    ),
  });

  useCopilotAction({
    name: "execute_sql",
    available: "frontend",
    description: "Executes SQL query on the SBA database",
    parameters: [
      { name: "query", type: "string", description: "The SQL query being executed" },
      { name: "results", type: "object", description: "The JSON results from the database" },
      {
        name: "refined_user_question",
        type: "string",
        description: "Short title for the analytical question",
      },
      {
        name: "row_count",
        type: "number",
        description: "Number of rows returned",
      },
      {
        name: "to_store",
        type: "boolean",
        description: "Whether this question/SQL pair is eligible for examples storage",
      },
    ],
    render: ({
      status,
      args,
    }: ActionRenderProps<
      [
        { name: "query"; type: "string"; description: string },
        { name: "results"; type: "object"; description: string },
        { name: "refined_user_question"; type: "string"; description: string },
        { name: "row_count"; type: "number"; description: string },
        { name: "to_store"; type: "boolean"; description: string },
      ]
    >): React.ReactElement => {
      const results = Array.isArray(args.results) ? (args.results as unknown[]) : [];
      const rq =
        typeof args.refined_user_question === "string"
          ? args.refined_user_question
          : undefined;
      const rc =
        typeof args.row_count === "number" && !Number.isNaN(args.row_count)
          ? args.row_count
          : undefined;
      return (
        <SqlResultPdfReport
          status={status}
          query={typeof args.query === "string" ? args.query : ""}
          results={results}
          refinedUserQuestion={rq}
          rowCount={rc}
        />
      );
    },
  });

  return (
    <div className="flex h-full min-h-0 w-full flex-col">
      <AgentPicker />
      <CopilotChat
        key={`${effectiveThreadId}:${pickedAgentId}`}
        instructions="Senior SBA Analyst. Always provide SQL results when asked. Be concise and professional."
        labels={copilotLabels}
        className="min-h-0 flex-1"
        observabilityHooks={observabilityHooks}
        RenderMessage={AgentRenderMessage}
        Input={CopilotPrefillInput}
        attachments={{
          enabled: true,
          accept: CHAT_ATTACHMENTS_ACCEPT,
          maxSize: CHAT_ATTACHMENTS_MAX_BYTES,
        }}
      />
    </div>
  );
}
