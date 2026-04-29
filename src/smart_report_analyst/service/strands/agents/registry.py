"""Registered main specialists (KB + SQL tooling) for orchestrator routing."""

from __future__ import annotations

from dataclasses import dataclass

# CopilotKit agent ids that are full data specialists (not router / orchestrator / builder).
MAIN_SPECIALIST_AGENT_IDS: frozenset[str] = frozenset(
    {
        "wlr_reporting_agent",
    }
)

AGENT_ORCHESTRATOR = "sra_orchestrator_agent"


@dataclass(frozen=True)
class MainSpecialistEntry:
    """Per-specialist metadata (prompt wiring only; KB/SQL come from global Settings today)."""

    agent_id: str
    display_name: str


_REGISTRY: dict[str, MainSpecialistEntry] = {
    "wlr_reporting_agent": MainSpecialistEntry(
        agent_id="wlr_reporting_agent",
        display_name="WLR Reporting Agent",
    ),
}


def is_main_specialist(agent_id: str) -> bool:
    return agent_id.strip() in MAIN_SPECIALIST_AGENT_IDS


def resolve_main_specialist(agent_id: str) -> MainSpecialistEntry:
    key = (agent_id or "").strip()
    if key not in _REGISTRY:
        raise KeyError(f"Unknown main specialist agent_id: {agent_id!r}")
    return _REGISTRY[key]
