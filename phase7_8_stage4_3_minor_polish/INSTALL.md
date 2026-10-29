# Phase 7.8 Stage 4.3 — PowerPoint minor polish

A **backend-only** upgrade from Stage 4.2. Replaces only `backend/artifacts/presentation_quality.py` and creates a timestamped backup. No database migrations or frontend changes.

## What changes

- Evenly balanced continuation bullet slides (8 items become 4+4, not 5+3).
- More balanced short-table placement: vertically centered within the existing table region, with more usable row heights.
- Flow labels remove duplicate leading numbers (`1.`, `01 -`, `Step 1:`) because the renderer already draws a numbered step marker.
- Table continuation, flow chevrons, model progress and all other file generators are preserved.

## Installation (PowerShell, project root)

1. Extract the ZIP into the `rag-fullstack-phase1` folder.
2. Stop the running generation worker with Ctrl+C.
3. Run the dry-run compatibility check:

```powershell
python .\phase7_8_stage4_3_minor_polish\install.py .
```

4. Apply after the check succeeds:

```powershell
python .\phase7_8_stage4_3_minor_polish\install.py . --apply
docker compose build --pull=false backend
docker compose up -d --no-build --force-recreate backend
docker compose exec backend python manage.py check
docker compose run --rm backend python -u manage.py generation_worker
```

A new generation job is necessary: existing PPTX files are not retroactively changed.

## Suggested test

Ask for: `Create a CCTV engineering presentation with a five-step architecture flow, eight bullet-style commissioning checks, six delivery risks in a table, and twelve sample camera entries. Keep unknown project values as TBD.`

Verify that the commissioning bullets split **4+4**, the risk table **3+3**, and numbered flow cards show only one step number each.

## Limits

Renderer tested locally with python-pptx, not against your running Docker deployment. Text fit varies with installed fonts. The update does not add browser previews or execute any generated code.
