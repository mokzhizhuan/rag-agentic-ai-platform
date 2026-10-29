# Phase 8.4 — Diagnostics (frontend-only)

Adds a Diagnostics tab to the existing RAG Knowledge AI application. Uses only existing React state and authenticated APIs: jobs, artifacts, documents, selected provider and chat mode. No backend changes, migrations, new packages or video API credits.

## Install

Extract `phase8_4_diagnostics` at the root of `rag-fullstack-phase1` (alongside `frontend` and `docker-compose.yml`).

In PowerShell, from project root:

```powershell
python .\phase8_4_diagnostics\install.py .
python .\phase8_4_diagnostics\install.py . --apply
docker compose build --pull=false frontend
docker compose up -d --no-build --force-recreate frontend
```

Refresh http://localhost:5174 using Ctrl+F5. Look for **Diagnostics** under the WORKSPACE sidebar.

## Expected UI

- White workspace with dark navy cards (matches Knowledge Base and Artifact Studio).
- Counts for account documents, generated artifacts, queued/running jobs and failed jobs within the returned job list.
- Recent job statuses/stages and errors.
- Selected provider and chat routing mode, explicitly **not** service-health claims.
- Refresh diagnostics button (uses existing authenticated functions).
- Scope/limitations notice.

## Safety and compatibility

The installer checks for known navigation and page-branch structures and refuses unexpected files without changing anything. Backups are saved alongside App.tsx (timestamped). It changes only `frontend/src/App.tsx` and adds `frontend/src/phase8-diagnostics.css`. It does not modify the existing handler functions, backend, database or worker.

If the dry run reports a mismatch, do not force the installer: share your current `frontend/src/App.tsx` so it can be adjusted to your local changes.

This first Diagnostics page is an account activity **snapshot**. It does not measure Keycloak/Postgres/Ollama health, latency, tokens, vector similarity or tool traces. No dummy metrics are used. Static frontend installation was tested against a representative frontend pattern, but not compiled or browser-tested against the user's current project.
