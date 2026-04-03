"use client";
import { useApp } from "@/context/AppContext";
import { useEffect, useState } from "react";
import { PlusIcon, FileTextIcon, Loader2 } from "lucide-react";
import { api, ChatSession } from "@/lib/api"; // Import the API layer

export function HistorySidebar() {
  const { activeThreadId, setActiveThreadId } = useApp();
  const [threads, setThreads] = useState<ChatSession[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchHistory = async () => {
      try {
        setLoading(true);
        setError(null);
        const data = await api.getHistory(); // Clean, centralized call
        setThreads(data);
      } catch (err) {
        setError("Failed to load history.");
      } finally {
        setLoading(false);
      }
    };
    fetchHistory();
  }, [activeThreadId]);

  return (
    <div className="w-72 bg-zinc-900 text-zinc-300 h-screen flex flex-col border-r border-zinc-800">
      <div className="p-4 border-b border-zinc-800">
        <button 
          onClick={() => setActiveThreadId(null)}
          className="flex items-center justify-center gap-2 w-full py-2 bg-zinc-100 text-zinc-900 rounded-lg font-medium hover:bg-white transition"
        >
          <PlusIcon size={16} /> New Analysis
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-1">
        <h3 className="text-xs font-semibold text-zinc-500 uppercase tracking-wider mb-4">Past Reports</h3>
        
        {loading ? (
          <div className="flex justify-center p-4"><Loader2 className="animate-spin text-zinc-500" /></div>
        ) : error ? (
          <p className="text-xs text-red-400 text-center py-4">{error}</p>
        ) : threads.length === 0 ? (
          <p className="text-xs text-zinc-600 text-center py-4 italic">No saved sessions found.</p>
        ) : (
          threads.map((t) => (
            <button
              key={t.id}
              onClick={() => setActiveThreadId(t.id)}
              className={`flex items-center gap-3 w-full p-3 rounded-lg text-sm transition-all ${
                activeThreadId === t.id 
                ? "bg-zinc-800 text-white shadow-inner ring-1 ring-zinc-700" 
                : "hover:bg-zinc-800/50 hover:text-zinc-100"
              }`}
            >
              <FileTextIcon size={16} className={activeThreadId === t.id ? "text-blue-400" : "text-zinc-500"} />
              <span className="truncate">{t.name}</span>
            </button>
          ))
        )}
      </div>
    </div>
  );
}