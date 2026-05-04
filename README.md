# Smart Report Analyst

Smart Report Analyst is a small full-stack app for **asking questions about data and producing SQL-backed analysis** via an LLM agent.

- **Frontend**: Next.js (React + TypeScript) chat UI
- **Backend**: Python service that can run as:
  - an **interactive CLI**, or
  - a **CopilotKit-compatible API** (FastAPI) for the web UI

## Repository layout

- `frontend/`: Next.js UI
- `src/smart_report_analyst/`: Python package (CLI + API)
- `aws/`: **Optional tooling** (vendored AWS CLI v2 bundle; not required to run the app)
- `.env.example`: configuration template (copy to `.env` locally; do not commit)

## Quickstart (local)

### 1) Backend (Python)

Prereqs: Python (see `pyproject.toml`) and an environment manager (`uv` recommended).

- Create local env file:
  - Copy `.env.example` → `.env`
  - Fill in at least: `AGENT_BACKEND`, `AWS_REGION`, and any required Bedrock agent IDs / MySQL values
- Install deps and run:
  - `uv sync`

Run in **CLI mode**:

- `uv run smart-report-analyst`

Run in **Copilot API mode** (for the web UI):

- `uv run smart-report-analyst --copilot`
- Optional overrides:
  - `--host <addr>` (defaults to `COPILOT_HOST` or `0.0.0.0`)
  - `--port <port>` (defaults to `COPILOT_PORT` or `8000`)

The API mounts routes under:

- `http://<host>:<port>/api`

### 2) Frontend (Next.js)

Prereqs: Node.js.

From `frontend/`:

- `npm install`
- `npm run dev`

Then open:

- `http://localhost:3000`

## Configuration

All backend configuration is loaded from environment variables (see `.env.example`).

- **Do not commit** `.env` or any secrets.
- CORS for the Copilot API is controlled by `COPILOT_CORS_ORIGINS` (comma-separated origins, e.g. `http://localhost:3000`).

## Optional tooling: `aws/` bundle

This repo includes a vendored AWS CLI v2 bundle in `aws/`. This is **not used by the application at runtime**. It exists to make it easy to install AWS CLI v2 in environments where you want a pinned, offline-friendly installer.

If you use it, see:

- `aws/README.md`

## Notes for deployment (EC2 / SSM)

There is a reference checklist for running on Amazon Linux via SSM Session Manager:

- `project_setup_ec2_ssm.script`

