# Phase 8.1 — Agentic Vector Dark shared React shell

This **frontend-only** upgrade styles the existing three tabs as a dark command workspace with a desktop sidebar, compact header, responsive mobile tabs, consistent cards and navigation. It follows the uploaded `DESIGN.md` palette and typography. It deliberately does not replace the existing React application with Stitch's static HTML.

## Install

1. Extract `phase8_1_react_shell` into the `rag-fullstack-phase1` project root.
2. In PowerShell, from the project root:

```powershell
python .\phase8_1_react_shell\install.py .
python .\phase8_1_react_shell\install.py . --apply
docker compose build --pull=false frontend
docker compose up -d --no-build --force-recreate frontend
```

3. Reload `http://localhost:5174` (hard refresh Ctrl+F5 if cached).

## Changed files

- `frontend/src/App.tsx`: adds one CSS import and `className="rag-shell"` to its existing root `<main>`.
- `frontend/src/phase8-shell.css`: new dark shell styles.

`App.tsx` is backed up before modification. No Django/backend files or database records are changed. There are **no new package dependencies** and no video generation calls.

## Compatibility

The installer expects an existing `frontend/src/App.tsx` whose root is `return <main>` and whose tabs use `className="tabs"`. It refuses incompatible layouts. Run the dry-run first.

## Scope boundaries and verification

This is Stage 8.1 only. The chat, knowledge and artifact content areas retain their underlying markup and functions; Stages 8.2–8.4 can progressively redesign each inner screen. Validate login/logout, chat streaming, document upload, ZIP generation/validation, and mobile navigation on your own app after install.

## Rollback

Restore the timestamped `frontend/src/App.tsx.phase8-1.*.bak` to `App.tsx`, delete `frontend/src/phase8-shell.css`, and rebuild `frontend`.
