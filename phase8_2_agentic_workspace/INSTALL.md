# Phase 8.2 — Agentic Workspace

Frontend-only appearance upgrade. This builds on Phase 8.1 and the white canvas / navy panel layout selected for AI Chat and Knowledge Base.

## Changes

- Adds `frontend/src/phase8-agentic.css`.
- Adds one import line to `frontend/src/App.tsx`, immediately after the Phase 8.1 CSS import.
- Styles conversation list, provider/mode controls, message stream, citation cards, file attachments, AI Memory, and composer.
- Does **not** touch Django, Keycloak, chat handlers, artifact generation, ZIP validation, or user data.

## Install

Unzip the package into the **project root** so `phase8_2_agentic_workspace/install.py` is present.

```powershell
python .\phase8_2_agentic_workspace\install.py .
python .\phase8_2_agentic_workspace\install.py . --apply
docker compose build --pull=false frontend
docker compose up -d --no-build --force-recreate frontend
```

Hard refresh `http://localhost:5174` with Ctrl+F5.

## Verify

Check AI Chat on desktop and mobile widths. Confirm sidebar selection and new conversations, provider/mode selects, message streaming, citations, attachment input, memory mode and composer still operate. Only appearance should change.

The installer backs up the original `App.tsx` and any previous Phase 8.2 stylesheet with a timestamp. If the actual project differs from the previously supplied layout, the installer exits rather than attempting a blind patch.

## Scope

This is **8.2 visual integration**, not new agent tools or live diagnostics. An end-to-end browser build in your local Docker environment remains necessary.
