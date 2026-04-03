"use client";
import { useApp } from "@/context/AppContext";
import { CopilotChat } from "@copilotkit/react-ui";
import { ActionRenderProps, useCopilotAction } from "@copilotkit/react-core";
import { SqlTable } from "@/components/SqlTable";

export function ChatInterface() {
  const { activeThreadId } = useApp();

  useCopilotAction({
    name: "execute_sql",
    description: "Executes SQL query on the SBA database",
    parameters: [
      { name: "query", type: "string", description: "The SQL query being executed" },
      { name: "results", type: "object", description: "The JSON results from the database" },
    ],
    render: ({ status, args }: ActionRenderProps<
        [
        { name: "query"; type: "string"; description: string },
        { name: "results"; type: "object"; description: string }
        ]
    >): React.ReactElement => {
            const results = Array.isArray(args.results) ? (args.results as any[]) : [];
            if (status === "inProgress") {
                return <div className="p-4 ...">Running SQL...</div>;
            }
            if (status === "complete") {
                return <SqlTable data={results} query={args.query} />;
            }
            return <></>;
        },
  });

  return (
    // The h-full ensures it fills the container in page.tsx
    <div className="h-full w-full flex flex-col">
      <CopilotChat
        key={activeThreadId || "new-chat"}
        instructions="Senior SBA Analyst. Always provide SQL results when asked. Be concise and professional."
        labels={{
          title: "SBA Loan Assistant",
          initial: "Hello! I can help you analyze SBA loan data. What would you like to see?",
        }}
        // In "Chatbot-first" mode, we usually disable the pop-out behavior
        className="flex-1" 
      />
    </div>
  );
}