"use client";

import { useCallback } from "react";
import { useApp } from "@/context/AppContext";
import { CopilotChat } from "@copilotkit/react-ui";
import { ActionRenderProps, useCopilotAction } from "@copilotkit/react-core";
import { SqlPdfReport } from "@/components/SqlPdfReport";
import { getApiPrefix } from "@/lib/env";

export function ChatInterface() {
  const { effectiveThreadId } = useApp();

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
        <SqlPdfReport
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
      <CopilotChat
        key={effectiveThreadId}
        instructions="Senior SBA Analyst. Always provide SQL results when asked. Be concise and professional."
        labels={{
          title: "SBA Loan Assistant",
          initial: "Hello! I can help you analyze SBA loan data. What would you like to see?",
        }}
        className="min-h-0 flex-1"
        observabilityHooks={{ onFeedbackGiven }}
      />
    </div>
  );
}
