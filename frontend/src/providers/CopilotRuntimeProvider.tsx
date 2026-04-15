"use client";

import { CopilotKit } from "@copilotkit/react-core";
import { getCopilotPublicApiKey, getCopilotRuntimeUrl } from "@/lib/env";
import { useApp } from "@/providers/AppContext";
export function CopilotRuntimeProvider({ children }: { children: React.ReactNode }) {
  const { effectiveThreadId, pickedAgentId, orchestratorMainAgentId } = useApp();
  const publicApiKey = getCopilotPublicApiKey();

  const properties: Record<string, string> | undefined =
    pickedAgentId === "sra_orchestrator_agent" && orchestratorMainAgentId
      ? { mainAgentId: orchestratorMainAgentId }
      : undefined;

  return (
    <CopilotKit
      key={`${effectiveThreadId}:${pickedAgentId}:${orchestratorMainAgentId ?? ""}`}
      runtimeUrl={getCopilotRuntimeUrl()}
      publicApiKey={publicApiKey}
      threadId={effectiveThreadId}
      agent={pickedAgentId}
      properties={properties}
      useSingleEndpoint={false}
    >
      {children}
    </CopilotKit>
  );
}
