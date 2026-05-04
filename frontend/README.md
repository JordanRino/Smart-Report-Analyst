# Smart Report Analyst (Frontend)

This is the Next.js UI for Smart Report Analyst.

For the full system overview and backend setup, start here:

- `../README.md`

## Requirements

- Node.js (recommended: recent LTS)
- Backend Copilot API running locally (default: `http://localhost:8000`)

## Configuration

Create a local env file:

- Copy `.env.example` → `.env.local` (or `.env`)

Key vars:

- `NEXT_PUBLIC_API_BASE_URL`: URL your **browser** uses to reach the backend (no trailing slash)
  - Local dev: `http://localhost:8000`
  - Remote dev (EC2/private IP): `http://<ip>:8000` (not `localhost`)
- `NEXT_ALLOWED_DEV_ORIGINS`: comma-separated hostnames only (no protocol/port) used when opening the UI by IP/DNS
- `NEXT_PUBLIC_COPILOT_PUBLIC_API_KEY`: optional Copilot Cloud public key (`ck_pub_...`)

## Run locally

From this directory (`frontend/`):

- `npm install`
- `npm run dev`

Then open:

- `http://localhost:3000`

## Common workflow (dev)

- Start backend API (repo root): `uv run smart-report-analyst --copilot`
- Start frontend (this folder): `npm run dev`
