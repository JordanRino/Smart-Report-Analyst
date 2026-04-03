// Define your types for strict TypeScript checking
export interface ChatSession {
  id: string;
  name: string;
}

// Fallback to localhost if the environment variable isn't set
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";

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
  
};