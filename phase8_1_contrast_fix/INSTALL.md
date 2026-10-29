# Phase 8.1 — Readability / contrast fix

This frontend-only patch appends contrast overrides to `frontend/src/phase8-shell.css`. The main issue is the white AI Memory area containing faint text. It changes the AI Memory background to dark navy and improves text, placeholder, file upload, and details contrast without modifying App.tsx or Django.

1. Extract this directory into the `rag-fullstack-phase1` project root.
2. Dry run: `python .\phase8_1_contrast_fix\install.py .`
3. Apply: `python .\phase8_1_contrast_fix\install.py . --apply`
4. Rebuild: `docker compose build --pull=false frontend`
5. Recreate: `docker compose up -d --no-build --force-recreate frontend`
6. Hard refresh at http://localhost:5174 with Ctrl+F5.

The installer creates a timestamped backup of the original CSS. It will refuse to apply twice. It does not change any React functionality, Keycloak, generation jobs, or backend files.
