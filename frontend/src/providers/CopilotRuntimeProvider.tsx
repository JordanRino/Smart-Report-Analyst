"use client";

import { CopilotKit } from "@copilotkit/react-core";
import { getCopilotPublicApiKey, getCopilotRuntimeUrl } from "@/lib/env";
import { useApp } from "@/context/AppContext";

export function CopilotRuntimeProvider({ children }: { children: React.ReactNode }) {
  const { effectiveThreadId, pickedAgentId } = useApp();
  const publicApiKey = getCopilotPublicApiKey();

  return (
    <CopilotKit
      key={`${effectiveThreadId}:${pickedAgentId}`}
      runtimeUrl={getCopilotRuntimeUrl()}
      publicApiKey={publicApiKey}
      threadId={effectiveThreadId}
      agent={pickedAgentId}
      useSingleEndpoint={false}
    >
      {children}
    </CopilotKit>
  );
}
