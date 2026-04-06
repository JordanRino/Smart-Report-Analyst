"use client";

import { CopilotKit } from "@copilotkit/react-core";
import { getCopilotRuntimeUrl } from "@/lib/env";
import { useApp } from "@/context/AppContext";


const COPILOT_AGENT_NAME = "loan_report_analyst_agent";

export function CopilotRuntimeProvider({ children }: { children: React.ReactNode }) {
  const { effectiveThreadId } = useApp();

  return (
    <CopilotKit
      runtimeUrl={getCopilotRuntimeUrl()}
      threadId={effectiveThreadId}
      agent={COPILOT_AGENT_NAME}
    >
      {children}
    </CopilotKit>
  );
}
