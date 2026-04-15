"use client";

import { useApp } from "@/providers/AppContext";
import { HistorySidebar } from "@/modules/chat/HistorySidebar";
import { ChatInterface } from "@/modules/chat/ChatInterface";

/** Home route: sidebar + main chat shell. */
export default function ChatScreen() {
  const { activeThreadId } = useApp();

  return (
    <div className="flex h-screen w-full overflow-hidden bg-zinc-50">
      <HistorySidebar />

      <main className="flex min-h-0 min-w-0 flex-1 flex-col bg-white">
        <header className="flex h-16 shrink-0 items-center border-b px-8">
          <div className="flex items-center gap-3">
            <div className="h-2.5 w-2.5 animate-pulse rounded-full bg-blue-600" />
            <h1 className="text-sm font-bold uppercase tracking-widest text-zinc-900">
              {activeThreadId ? `Session: ${activeThreadId.slice(0, 8)}` : "New Chat"}
            </h1>
          </div>
        </header>

        <div className="relative min-h-0 flex-1 overflow-hidden">
          <ChatInterface />
        </div>
      </main>
    </div>
  );
}
