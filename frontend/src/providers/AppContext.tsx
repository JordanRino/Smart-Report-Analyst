"use client";
import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { AGENT_ORCHESTRATOR_ID, type AgentId } from "@/lib/agents";
import { api } from "@/lib/api";

function newThreadId(): string {
  if (typeof crypto !== "undefined" && crypto.randomUUID) {
    return crypto.randomUUID();
  }
  return `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 12)}`;
}

interface AppContextType {
  /** Sidebar selection: null = "new chat" mode using draft thread id */
  activeThreadId: string | null;
  setActiveThreadId: (id: string | null) => void;
  /** CopilotKit / Strands session id: history row id or fresh draft */
  effectiveThreadId: string;
  /** Sticky CopilotKit agent (isolated Strands state per agent + thread). */
  pickedAgentId: AgentId;
  setPickedAgentId: (id: AgentId) => void;
  /**
   * When ``pickedAgentId`` is the orchestrator: Copilot ``properties.mainAgentId``.
   * ``null`` until the user picks a data specialist (required before tools run).
   */
  orchestratorMainAgentId: AgentId | null;
  setOrchestratorMainAgentId: (id: AgentId | null) => void;
  /** Return to session orchestrator and clear the data specialist choice. */
  clearPickedAgent: () => void;
  /** Clear sidebar selection and start a new CopilotKit / Strands thread (new draft session id). */
  startNewConversation: () => void;
}

const AppContext = createContext<AppContextType | undefined>(undefined);

export function AppProvider({ children }: { children: React.ReactNode }) {
  const [activeThreadId, setActiveThreadId] = useState<string | null>(null);
  const [draftThreadId, setDraftThreadId] = useState<string>(newThreadId);
  const [pickedAgentId, setPickedAgentId] = useState<AgentId>(AGENT_ORCHESTRATOR_ID);
  const [orchestratorMainAgentId, setOrchestratorMainAgentId] = useState<AgentId | null>(null);

  // When loading a past thread from history, hydrate orchestratorMainAgentId from the
  // backend persisted state so the specialist picker reflects the saved choice.
  useEffect(() => {
    if (!activeThreadId) return;
    let cancelled = false;
    api
      .getSpecialist(activeThreadId)
      .then(({ mainAgentId }) => {
        if (cancelled) return;
        const id = mainAgentId as AgentId | null;
        // Hydrate only if the backend has a stored choice; otherwise keep whatever
        // HistorySidebar set as a reasonable default for existing sessions.
        if (id) {
          setOrchestratorMainAgentId(id);
        }
      })
      .catch(() => {
        // Non-fatal: HistorySidebar already set a safe fallback specialist.
      });
    return () => {
      cancelled = true;
    };
  }, [activeThreadId]);

  const startNewConversation = useCallback(() => {
    setActiveThreadId(null);
    setDraftThreadId(newThreadId());
    setPickedAgentId(AGENT_ORCHESTRATOR_ID);
    setOrchestratorMainAgentId(null);
  }, []);

  const clearPickedAgent = useCallback(() => {
    setPickedAgentId(AGENT_ORCHESTRATOR_ID);
    setOrchestratorMainAgentId(null);
  }, []);

  const effectiveThreadId = activeThreadId ?? draftThreadId;

  const value = useMemo(
    () => ({
      activeThreadId,
      setActiveThreadId,
      effectiveThreadId,
      pickedAgentId,
      setPickedAgentId,
      orchestratorMainAgentId,
      setOrchestratorMainAgentId,
      clearPickedAgent,
      startNewConversation,
    }),
    [
      activeThreadId,
      effectiveThreadId,
      pickedAgentId,
      orchestratorMainAgentId,
      clearPickedAgent,
      startNewConversation,
    ],
  );

  return <AppContext.Provider value={value}>{children}</AppContext.Provider>;
}

export const useApp = () => {
  const context = useContext(AppContext);
  if (!context) throw new Error("useApp must be used within AppProvider");
  return context;
};
