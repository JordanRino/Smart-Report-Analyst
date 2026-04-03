"use client";
import { useApp } from "@/context/AppContext";
import { HistorySidebar } from "@/components/HistorySidebar";
import { ChatInterface } from "@/components/ChatInterface";

export default function Home() {
  const { activeThreadId, setActiveThreadId } = useApp();

  return (
    <div className="flex h-screen w-full bg-zinc-50 overflow-hidden">
      
      {/* LEFT: Navigation & History (Fixed Width) */}
      <HistorySidebar />

      {/* CENTER: The Chatbot App (Flexible Space) */}
      <main className="flex-1 flex flex-col min-w-0 bg-white">
        
        {/* Sub-Header */}
        <header className="flex h-16 items-center justify-between border-b px-8 flex-shrink-0">
          <div className="flex items-center gap-3">
            <div className="w-2.5 h-2.5 bg-blue-600 rounded-full animate-pulse" />
            <h1 className="text-sm font-bold text-zinc-900 uppercase tracking-widest">
              {activeThreadId ? `Session: ${activeThreadId.slice(0,8)}` : "New Analysis"}
            </h1>
          </div>
          
          <button 
            onClick={() => setActiveThreadId(null)}
            className="rounded-lg bg-zinc-100 px-4 py-2 text-xs font-bold text-zinc-900 transition-all hover:bg-zinc-200 active:scale-95"
          >
            + RESET SESSION
          </button>
        </header>

        <div className="flex-1 relative overflow-hidden">
          <ChatInterface />
        </div>

      </main>
    </div>
  );
}