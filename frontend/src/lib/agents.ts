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
  {
    id: "sra_orchestrator_agent",
    label: "Report session (orchestrator)",
    shortLabel: "Orchestrator",
    description: "Coordinates the report builder with your chosen WLR specialist (pick main specialist below)",
  },
] as const;

export type AgentId = (typeof AGENTS)[number]["id"];

/** CopilotKit id for session orchestrator (not listed in the compact mode bar). */
export const AGENT_ORCHESTRATOR_ID: AgentId = "sra_orchestrator_agent";

/** Subset for orchestrator ``properties.mainAgentId`` (data specialists only). */
export const MAIN_SPECIALIST_OPTIONS = AGENTS.filter(
  (a) => a.id === "wlr_reporting_agent" || a.id === "loan_report_analyst_agent",
);

/** Default when opening an existing thread from history (most sessions are reporting). */
export const DEFAULT_AGENT_ID: AgentId = "wlr_reporting_agent";

/**
 * @deprecated Use ``AGENT_ORCHESTRATOR_ID`` / default session state. Router remains on the API only.
 */
export const FRESH_CHAT_AGENT_ID: AgentId = "sra_router_agent";

export function getAgentLabel(id: string): string {
  const a = AGENTS.find((x) => x.id === id);
  return a?.label ?? id;
}

/** Valid Copilot agent id from a query string, or null if unknown / empty. */
export function coerceAgentIdFromQuery(raw: string | null): AgentId | null {
  const t = raw?.trim() ?? "";
  if (!t) return null;
  const hit = AGENTS.find((a) => a.id === t);
  return hit ? hit.id : null;
}

/** Valid orchestrator ``mainAgentId`` from a query string, or null if unknown / empty. */
export function coerceMainSpecialistFromQuery(raw: string | null): AgentId | null {
  const t = raw?.trim() ?? "";
  if (!t) return null;
  const hit = MAIN_SPECIALIST_OPTIONS.find((a) => a.id === t);
  return hit ? hit.id : null;
}
