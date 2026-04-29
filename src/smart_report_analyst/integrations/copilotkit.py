"""CopilotKit Python SDK ↔ @copilotkitnext/core compatibility.

The SDK's ``info()`` returns ``agents`` as a list of ``{name, description}`` dicts.
``@copilotkitnext/core`` treats ``agents`` as a record and does
``Object.entries(agents)``, which for an array yields keys ``"0"``, ``"1"``, …
so the UI looks up a named agent (e.g. ``wlr_reporting_agent``) but the runtime only registers ``"0"``.
"""

from __future__ import annotations

from typing import Any, List, Mapping, MutableMapping, Optional, cast

from copilotkit import CopilotKitRemoteEndpoint
from copilotkit.action import ActionDict
from copilotkit.sdk import CopilotKitContext
from copilotkit.types import Message, MetaEvent


def _merge_config_with_context_properties(
    config: Optional[dict],
    context: CopilotKitContext,
) -> Optional[dict]:
    """
    ``copilotkit.integrations.fastapi`` builds ``context['properties']`` from the JSON body
    but calls ``agent.execute(..., config=config)`` with ``config=None`` on the
    ``POST .../agent/{name}`` path, so ``<CopilotKit properties={...} />`` never reached
    our adapter. Merge request properties (and ``mainAgentId``) into ``config``.
    """
    ctx_props = context.get("properties")
    if not isinstance(ctx_props, dict) or not ctx_props:
        return config
    out = dict(config) if isinstance(config, dict) else {}
    existing = out.get("properties")
    if isinstance(existing, dict):
        out["properties"] = {**existing, **ctx_props}
    else:
        out["properties"] = dict(ctx_props)
    mid = ctx_props.get("mainAgentId") or ctx_props.get("main_agent_id")
    if isinstance(mid, str) and mid.strip():
        out.setdefault("mainAgentId", mid.strip())
    return out


def _agents_list_to_map(
    agents: List[Mapping[str, Any]],
) -> dict[str, dict[str, str]]:
    out: dict[str, dict[str, str]] = {}
    for item in agents:
        name = item.get("name")
        if not name:
            continue
        desc = item.get("description")
        out[str(name)] = {"description": desc if isinstance(desc, str) else (desc or "")}
    return out


class CopilotKitRemoteEndpointAguiAgentsMap(CopilotKitRemoteEndpoint):
    """Same as ``CopilotKitRemoteEndpoint`` but ``/info`` exposes ``agents`` as a name-keyed map."""

    def execute_agent(  # pylint: disable=too-many-arguments
        self,
        *,
        context: CopilotKitContext,
        name: str,
        thread_id: str,
        state: dict,
        config: Optional[dict] = None,
        messages: List[Message],
        actions: List[ActionDict],
        node_name: str,
        meta_events: Optional[List[MetaEvent]] = None,
    ) -> Any:
        merged = _merge_config_with_context_properties(config, context)
        return super().execute_agent(
            context=context,
            name=name,
            thread_id=thread_id,
            state=state,
            config=merged,
            messages=messages,
            actions=actions,
            node_name=node_name,
            meta_events=meta_events,
        )

    def info(self, *, context: CopilotKitContext) -> Any:
        payload = cast(MutableMapping[str, Any], super().info(context=context))
        agents = payload.get("agents")
        if isinstance(agents, list):
            payload["agents"] = _agents_list_to_map(agents)
        return dict(payload)


def patch_copilotkit_info_html_for_agent_map() -> None:
    """Make ``generate_info_html`` accept ``agents`` as a name-keyed map (our ``info()`` shape)."""
    import copilotkit.html as ck_html

    if getattr(ck_html.generate_info_html, "_smart_report_analyst_agui_patch", False):
        return

    _orig = ck_html.generate_info_html

    def generate_info_html(info: object) -> str:
        if not isinstance(info, dict):
            return _orig(info)
        agents = info.get("agents")
        if isinstance(agents, dict):
            info = {
                **info,
                "agents": [
                    {
                        "name": name,
                        "description": (meta or {}).get("description", "")
                        if isinstance(meta, dict)
                        else "",
                    }
                    for name, meta in agents.items()
                ],
            }
        return _orig(info)

    setattr(generate_info_html, "_smart_report_analyst_agui_patch", True)
    ck_html.generate_info_html = generate_info_html


__all__ = [
    "CopilotKitRemoteEndpointAguiAgentsMap",
    "patch_copilotkit_info_html_for_agent_map",
    "_merge_config_with_context_properties",
]
