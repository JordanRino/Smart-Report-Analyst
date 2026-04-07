"use client";
import { useApp } from "@/context/AppContext";
import { HistorySidebar } from "@/components/HistorySidebar";
import { ChatInterface } from "@/components/ChatInterface";

export default function Home() {
  const { activeThreadId } = useApp();

  return (
    <div className="flex h-screen w-full bg-zinc-50 overflow-hidden">
      
      {/* LEFT: Navigation & History (Fixed Width) */}
      <HistorySidebar />

      {/* CENTER: The Chatbot App (Flexible Space) */}
      <main className="flex min-h-0 min-w-0 flex-1 flex-col bg-white">
        
        {/* Sub-Header */}
        <header className="flex h-16 shrink-0 items-center border-b px-8">
          <div className="flex items-center gap-3">
            <div className="w-2.5 h-2.5 bg-blue-600 rounded-full animate-pulse" />
            <h1 className="text-sm font-bold text-zinc-900 uppercase tracking-widest">
              {activeThreadId ? `Session: ${activeThreadId.slice(0,8)}` : "New Chat"}
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