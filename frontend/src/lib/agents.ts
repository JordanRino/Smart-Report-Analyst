/** CopilotKit agent names registered by the FastAPI runtime. */

export const AGENTS = [
  {
    id: "sra_router_agent",
    label: "Router",
    shortLabel: "Router",
    description: "Pick a specialist or get oriented",
  },
  {
    id: "wlr_reporting_agent",
    label: "WLR Reporting Agent",
    shortLabel: "WLR Reporting",
    description: "SBA loan analytics, SQL, and PDF reports",
  },
  {
    id: "loan_report_analyst_agent",
    label: "Loan Report Analyst (legacy)",
    shortLabel: "Loan Analyst",
    description: "Same as WLR — kept for backward compatibility",
  },
] as const;

export type AgentId = (typeof AGENTS)[number]["id"];

/** Default when opening an existing thread from history (most sessions are reporting). */
export const DEFAULT_AGENT_ID: AgentId = "wlr_reporting_agent";

/** Brand-new chat: show router / agent picker first. */
export const FRESH_CHAT_AGENT_ID: AgentId = "sra_router_agent";

export function getAgentLabel(id: string): string {
  const a = AGENTS.find((x) => x.id === id);
  return a?.label ?? id;
}
