"use client";

import {
  AGENT_ORCHESTRATOR_ID,
  coerceAgentIdFromQuery,
  coerceMainSpecialistFromQuery,
  MAIN_SPECIALIST_OPTIONS,
} from "@/lib/agents";
import { useApp } from "@/providers/AppContext";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useRef } from "react";

function isMainSpecialistAgentId(id: string): boolean {
  return MAIN_SPECIALIST_OPTIONS.some((a) => a.id === id);
}

/**
 * Applies `/?thread=<uuid>` plus optional `agent` and `mainAgent`.
 * Chat is always session (orchestrator); legacy ``agent`` values map to ``mainAgent``.
 */
export function ThreadDeepLink() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const { setActiveThreadId, setPickedAgentId, setOrchestratorMainAgentId } = useApp();
  const lastHandled = useRef<string | null>(null);

  useEffect(() => {
    const thread = searchParams.get("thread")?.trim() ?? "";
    if (!thread) {
      lastHandled.current = null;
      return;
    }
    const agentRaw = searchParams.get("agent")?.trim() ?? "";
    const mainRaw = searchParams.get("mainAgent")?.trim() ?? "";
    const key = `${thread}\0${agentRaw}\0${mainRaw}`;
    if (lastHandled.current === key) {
      return;
    }
    lastHandled.current = key;

    setActiveThreadId(thread);

    if (!agentRaw && !mainRaw) {
      router.replace("/", { scroll: false });
      return;
    }

    setPickedAgentId(AGENT_ORCHESTRATOR_ID);

    const agentId = coerceAgentIdFromQuery(agentRaw);
    const mainId = coerceMainSpecialistFromQuery(mainRaw);

    if (agentId === AGENT_ORCHESTRATOR_ID) {
      setOrchestratorMainAgentId(mainId);
    } else if (agentId && isMainSpecialistAgentId(agentId)) {
      setOrchestratorMainAgentId(agentId);
    } else if (mainId) {
      setOrchestratorMainAgentId(mainId);
    } else {
      setOrchestratorMainAgentId(null);
    }

    router.replace("/", { scroll: false });
  }, [searchParams, router, setActiveThreadId, setPickedAgentId, setOrchestratorMainAgentId]);

  return null;
}
