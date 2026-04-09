# Architecture: Strands + CopilotKit + AG-UI

**Audience:** Engineering and product leadership  
**Scope:** How the SBA analyst chat connects the Next.js UI, CopilotKit runtime, and Strands agent over the AG-UI streaming protocol.

---

## Purpose

End users chat in a **CopilotKit**-powered UI. Each turn is executed by a **Strands** agent (AWS Bedrock) that can query SBA loan data. Assistant output and tool results reach the browser as **AG-UI** events over **Server-Sent Events (SSE)** so the UI can stream text, render the SQL action, and drive follow-on features (PDF, feedback).

---

## High-level architecture

```mermaid
flowchart TB
  subgraph client [Browser - Next.js]
    UI[CopilotChat and app chrome]
    CK[CopilotKit React SDK]
    UI --> CK
  end

  subgraph api [Backend - FastAPI]
    RT[CopilotKit runtime routes]
    AG[StrandsCopilotAgent]
    REST[REST APIs - PDF history feedback]
    RT --> AG
  end

  subgraph proto [Wire format]
    SSE[AG-UI events over SSE]
  end

  subgraph strands [Strands agent]
    RUN[run_stream merged stream + trace queue]
    TOOLS[Tools - KB retrieve SQL execute]
    SESS[File session storage]
    RUN --> TOOLS
    RUN --> SESS
  end

  subgraph data [Data]
    MYSQL[(MySQL - SBA and app tables)]
    BEDROCK[Amazon Bedrock]
  end

  CK <-->|HTTP SSE JSON| RT
  AG --> SSE
  SSE --> CK
  AG --> RUN
  TOOLS --> MYSQL
  RUN --> BEDROCK
  CK --> REST
```

---

## Layer summary

| Layer | Role |
|--------|------|
| **CopilotKit (client)** | Chat UI, thread id, agent name, optional public key for observability; calls the runtime URL. |
| **CopilotKit (FastAPI)** | Registers the remote agent; handles agent execute, info, and related HTTP endpoints. |
| **StrandsCopilotAgent** | Maps one user turn into AG-UI frames: run lifecycle, **reasoning / trace** (`REASONING_*`, `STEP_*`, `CUSTOM`), streaming assistant text, synthetic `execute_sql` tool frames for the frontend, final state snapshot. |
| **agent_trace** | Canonical `TraceEvent` model and mapper to AG-UI; backend-agnostic so other agents could reuse the same codec. |
| **AG-UI helpers** | Build SSE `data: {...}` lines (`RUN_*`, `TEXT_MESSAGE_*`, `TOOL_CALL_*`, `REASONING_*`, `STEP_*`, `CUSTOM`, optional `timestamp`, etc.) compatible with CopilotKit’s AG-UI client. |
| **Strands** | Orchestrates the model, tools, and session persistence on disk (per thread). |
| **REST beside Copilot** | PDF generation, chat history listing, positive feedback—same origin/CORS as the app, not part of the AG-UI stream. |

---

## Repository layout (Strands / Copilot path)

High-signal folders only. The package also contains **Chainlit** and **Streamlit** UIs under `ui/` and `service/streamlit/`; they are separate entry points from the Next.js + CopilotKit app.

### Backend — `src/smart_report_analyst/`

```text
src/smart_report_analyst/
├── app.py                      # FastAPI application
├── config/                     # Settings and environment
├── routes/
│   └── routes.py               # CopilotKit runtime mount, REST: PDF, history, feedback
├── integrations/
│   ├── agui_stream.py          # AG-UI SSE event builders (incl. reasoning / steps / custom)
│   └── copilotkit.py           # CopilotKit remote endpoint + info HTML patch
└── service/
    ├── agent_trace/            # TraceEvent + mapper → AG-UI (agent-agnostic)
    ├── strands/
    │   ├── agent.py            # StrandsCopilotAgent → AG-UI stream
    │   ├── runner.py           # Async turn: merged Strands stream + trace queue → chunks + trace + tool_result
    │   ├── tools/              # execute_sql, KB retrieve (Bedrock KB); tools enqueue TraceEvent while running
    │   ├── agents/             # Strands agent / orchestrator definitions
    │   ├── session/            # File-backed sessions (thread ↔ storage)
    │   └── conversation/       # Conversation manager wiring
    ├── bedrock/                # Model + knowledge base clients
    ├── persistence/mysql/      # App SQL execution, Chainlit store, etc.
    ├── report_generation/      # PDF build + HTTP request models
    └── feedback/               # Positive feedback + snapshot index for thumbs-up
```

### Frontend — `frontend/src/`

```text
frontend/src/
├── app/                        # Next.js App Router (layout, home page)
├── components/
│   ├── ChatInterface.tsx       # CopilotChat, RenderMessage → ReasoningTraceMessage, execute_sql action
│   ├── agent-trace/            # Collapsible reasoning / trace UI (ReasoningTraceMessage)
│   ├── SqlPdfReport.tsx        # PDF fetch + preview overlay
│   └── HistorySidebar.tsx      # Session list from /api/history
├── providers/
│   └── CopilotRuntimeProvider.tsx   # CopilotKit provider + thread + public API key
├── context/
│   └── AppContext.tsx          # Active thread id for Copilot + sidebar
└── lib/
    ├── env.ts                  # API base URL, Copilot runtime URL, public key
    └── api.ts                  # Shared fetch helpers (if used)
```

---

## Live agent trace (reasoning + steps)

During a turn, the server can surface **live** work while Strands is blocked in tools:

1. **`StrandsTurnState`** holds an `asyncio.Queue` and trace metadata (`run_id`, `thread_id`, `agent_name`) for the turn.
2. **`retrieve_kb_context`** and **`execute_sql`** enqueue **`TraceEvent`** instances (`STEP_*`, human-readable **`REASONING_LINE`**, optional **`CUSTOM`** timings). Sync tools use `asyncio.run_coroutine_threadsafe` to the main loop; async tools `await` the queue.
3. **`run_stream`** merges the Strands `stream_async` iterator with the queue so trace events yield **`{"type":"trace","data": TraceEvent}`** interleaved with **`chunk`** events.
4. **`StrandsCopilotAgent`** opens **`REASONING_*`** before the first assistant token, forwards trace rows through **`trace_events_to_sse_frames`**, then closes reasoning and starts **`TEXT_MESSAGE_*`** on the first text chunk.
5. **Frontend** — `CopilotChat` **`RenderMessage`** renders `role === "reasoning"` via **`ReasoningTraceMessage`** (collapsible trace body). The default CopilotKit renderer still applies to other message types when our renderer returns `null`.

**Note:** The synthetic **`execute_sql`** AG-UI tool sequence remains the bridge for **`useCopilotAction`** (PDF widget). Trace lines describe **server-side** KB/SQL work; labels in the UI distinguish that from the report card.

---

## Design choices (short)

1. **AG-UI over raw Copilot NDJSON** — The stream matches `@ag-ui/core` event shapes so the React client can parse and verify the run incrementally.  
2. **Synthetic frontend `execute_sql`** — The model runs SQL on the server; the adapter re-emits a frontend `execute_sql` action with query + results so CopilotKit can render the report strip and call PDF/feedback APIs without exposing raw Strands internals to the UI.  
3. **Thread = Strands session** — CopilotKit `threadId` aligns with on-disk session folders for history and continuity.  
4. **CopilotKit compatibility patch** — Runtime `info` exposes agents as a name-keyed map so the UI resolves `loan_report_analyst_agent` correctly.

---

## Related code (for implementers)

- Agent adapter: `src/smart_report_analyst/service/strands/agent.py`  
- AG-UI framing: `src/smart_report_analyst/integrations/agui_stream.py`  
- Runtime registration: `src/smart_report_analyst/routes/routes.py` (CopilotKit + REST)  
- CopilotKit bridge: `src/smart_report_analyst/integrations/copilotkit.py`  
- Frontend shell: `frontend/src/providers/CopilotRuntimeProvider.tsx`, `frontend/src/components/ChatInterface.tsx`
