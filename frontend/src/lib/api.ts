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
}

export interface ReportsListResponse {
  items: ReportSummary[];
  total: number;
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

  async listReports(): Promise<ReportsListResponse> {
    const response = await fetch(`${API_BASE_URL}/reports/saved`);
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
};
