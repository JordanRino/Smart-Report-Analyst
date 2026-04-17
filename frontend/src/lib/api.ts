import { getApiPrefix } from "@/lib/env";

// Define your types for strict TypeScript checking
export interface ChatSession {
  id: string;
  name: string;
}

const API_BASE_URL = getApiPrefix();

/** One row from GET /api/reports/saved (metadata only, no result rows). */
export interface ReportSummary {
  id: string;
  created_at: number;
  updated_at: number;
  thread_id: string;
  agent_id: string;
  title: string;
  executed_sql: string;
  row_count: number | null;
  results_row_count: number;
  payload_sha256: string;
  pdf_sha256: string;
  pdf_size_bytes: number;
  source_message_id: string | null;
  /** Orchestrator mode: persisted ``properties.mainAgentId`` when saved. */
  main_agent_id?: string | null;
  /** "record" (CSV) or "report" (narrative PDF). */
  kind?: "record" | "report";
}

export interface ReportsListResponse {
  items: ReportSummary[];
  total: number;
}

export interface SpecialistState {
  threadId: string;
  /** null when no specialist has been persisted yet for this thread. */
  mainAgentId: string | null;
}

export const api = {
  /**
   * Fetches the list of saved sessions from the backend.
   */
  async getHistory(): Promise<ChatSession[]> {
    try {
      const response = await fetch(`${API_BASE_URL}/history`);
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      return await response.json();
    } catch (error) {
      console.error("API Error - getHistory:", error);
      throw error; // Let the component handle the error state
    }
  },

  async listReports(kind?: "record" | "report"): Promise<ReportsListResponse> {
    const url = kind
      ? `${API_BASE_URL}/reports/saved?kind=${encodeURIComponent(kind)}`
      : `${API_BASE_URL}/reports/saved`;
    const response = await fetch(url);
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    return (await response.json()) as ReportsListResponse;
  },

  async deleteReport(id: string): Promise<void> {
    const response = await fetch(`${API_BASE_URL}/reports/saved/${encodeURIComponent(id)}`, {
      method: "DELETE",
    });
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
  },

  /**
   * Persist the active specialist agent for a thread.
   * Pass null to clear the selection (reverts to "no specialist" state).
   */
  async setSpecialist(threadId: string, mainAgentId: string | null): Promise<SpecialistState> {
    const response = await fetch(`${API_BASE_URL}/session/${encodeURIComponent(threadId)}/specialist`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ mainAgentId }),
    });
    if (!response.ok) {
      throw new Error(`setSpecialist HTTP error: ${response.status}`);
    }
    return (await response.json()) as SpecialistState;
  },

  /**
   * Fetch the persisted specialist agent for a thread.
   * Returns { mainAgentId: null } when no specialist has been set yet.
   */
  async getSpecialist(threadId: string): Promise<SpecialistState> {
    const response = await fetch(`${API_BASE_URL}/session/${encodeURIComponent(threadId)}/specialist`);
    if (!response.ok) {
      throw new Error(`getSpecialist HTTP error: ${response.status}`);
    }
    return (await response.json()) as SpecialistState;
  },

  /** Remove Strands session dirs and orchestrator state for a logical thread id. */
  async deleteSession(threadId: string): Promise<void> {
    const response = await fetch(`${API_BASE_URL}/session/${encodeURIComponent(threadId)}`, {
      method: "DELETE",
    });
    if (!response.ok) {
      throw new Error(`deleteSession HTTP error: ${response.status}`);
    }
  },
};
