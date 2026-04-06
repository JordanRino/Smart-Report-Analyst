"use client";
import React, { createContext, useCallback, useContext, useMemo, useState } from "react";

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
  /** Clear sidebar selection and start a new CopilotKit / Strands thread (new draft session id). */
  startNewConversation: () => void;
}

const AppContext = createContext<AppContextType | undefined>(undefined);

export function AppProvider({ children }: { children: React.ReactNode }) {
  const [activeThreadId, setActiveThreadId] = useState<string | null>(null);
  const [draftThreadId, setDraftThreadId] = useState<string>(newThreadId);

  const startNewConversation = useCallback(() => {
    setActiveThreadId(null);
    setDraftThreadId(newThreadId());
  }, []);

  const effectiveThreadId = activeThreadId ?? draftThreadId;

  const value = useMemo(
    () => ({
      activeThreadId,
      setActiveThreadId,
      effectiveThreadId,
      startNewConversation,
    }),
    [activeThreadId, effectiveThreadId, startNewConversation],
  );

  return <AppContext.Provider value={value}>{children}</AppContext.Provider>;
}

export const useApp = () => {
  const context = useContext(AppContext);
  if (!context) throw new Error("useApp must be used within AppProvider");
  return context;
};
