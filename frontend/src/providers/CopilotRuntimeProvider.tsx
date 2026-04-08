"use client";

import { CopilotKit } from "@copilotkit/react-core";
import { getCopilotPublicApiKey, getCopilotRuntimeUrl } from "@/lib/env";
import { useApp } from "@/context/AppContext";


const COPILOT_AGENT_NAME = "loan_report_analyst_agent";

export function CopilotRuntimeProvider({ children }: { children: React.ReactNode }) {
  const { effectiveThreadId } = useApp();
  const publicApiKey = getCopilotPublicApiKey();

  return (
    <CopilotKit
      runtimeUrl={getCopilotRuntimeUrl()}
      publicApiKey={publicApiKey}
      threadId={effectiveThreadId}
      agent={COPILOT_AGENT_NAME}
      useSingleEndpoint={false}
      properties={{
        threadId: effectiveThreadId 
      }}
    >
      {children}
    </CopilotKit>
  );
}
