"use client";
import React, { createContext, useCallback, useContext, useMemo, useState } from "react";
import { FRESH_CHAT_AGENT_ID, type AgentId } from "@/lib/agents";

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
  clearPickedAgent: () => void;
  /** Clear sidebar selection and start a new CopilotKit / Strands thread (new draft session id). */
  startNewConversation: () => void;
}

const AppContext = createContext<AppContextType | undefined>(undefined);

export function AppProvider({ children }: { children: React.ReactNode }) {
  const [activeThreadId, setActiveThreadId] = useState<string | null>(null);
  const [draftThreadId, setDraftThreadId] = useState<string>(newThreadId);
  const [pickedAgentId, setPickedAgentId] = useState<AgentId>(FRESH_CHAT_AGENT_ID);

  const startNewConversation = useCallback(() => {
    setActiveThreadId(null);
    setDraftThreadId(newThreadId());
    setPickedAgentId(FRESH_CHAT_AGENT_ID);
  }, []);

  const clearPickedAgent = useCallback(() => {
    setPickedAgentId("sra_router_agent");
  }, []);

  const effectiveThreadId = activeThreadId ?? draftThreadId;

  const value = useMemo(
    () => ({
      activeThreadId,
      setActiveThreadId,
      effectiveThreadId,
      pickedAgentId,
      setPickedAgentId,
      clearPickedAgent,
      startNewConversation,
    }),
    [
      activeThreadId,
      effectiveThreadId,
      pickedAgentId,
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
