"use client";
import React, { createContext, useContext, useState } from "react";

interface AppContextType {
  activeThreadId: string | null;
  setActiveThreadId: (id: string | null) => void;
}

const AppContext = createContext<AppContextType | undefined>(undefined);

export function AppProvider({ children }: { children: React.ReactNode }) {
  const [activeThreadId, setActiveThreadId] = useState<string | null>(null);

  return (
    <AppContext.Provider value={{ activeThreadId, setActiveThreadId }}>
      {children}
    </AppContext.Provider>
  );
}

export const useApp = () => {
  const context = useContext(AppContext);
  if (!context) throw new Error("useApp must be used within AppProvider");
  return context;
};