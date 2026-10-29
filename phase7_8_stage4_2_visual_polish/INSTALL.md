# Phase 7.8 Stage 4.2 — PowerPoint Visual Polish

Backend-only refinement of the existing Phase 7.8 Stage 4.1 renderer.

## Improvements

- Balance continuation slides instead of leaving one or two rows on the last slide. For example, an 8-row commissioning table becomes 4+4; a 6-row risk table becomes 3+3.
- Add editable chevron arrows between ordered architecture/workflow blocks.
- Increase table font sizes where space permits and use content-aware row heights.
- Preserve editable PowerPoint tables, text, shapes, footer, and existing generation progress notifications.

## Installation (PowerShell, from `rag-fullstack-phase1`)

Extract ZIP into the project root. Stop the existing generation worker with Ctrl+C. Verify that Stage 4.1 was already installed.

```powershell
python .\phase7_8_stage4_2_visual_polish\install.py .
python .\phase7_8_stage4_2_visual_polish\install.py . --apply

docker compose build --pull=false backend
docker compose up -d --no-build --force-recreate backend
docker compose exec backend python manage.py check
```

Then start a new worker:

```powershell
docker compose run --rm backend python -u manage.py generation_worker
```

No new dependencies or database migrations. The installer creates a timestamped `.bak` file next to the renderer. No changes to `generator.py`, code generators, models, worker, frontend, or database.

## Validation test prompt

Select OpenAI -> PowerPoint:

> Create a professional CCTV engineering deck with a title slide, five-step editable system architecture flow, twelve sample TBD camera rows, eight commissioning checks, six delivery risks with mitigations and TBD status, a five-step delivery workflow, and handover actions. Do not invent completed inspections.

Check tables split evenly, workflow arrows are visible, table text is readable, and footer slide counts are correct. Structural validation cannot guarantee perfect text fit across different Office fonts; inspect generated slides visually.

## Rollback

Copy the latest `backend/artifacts/presentation_quality.py.before_stage4_2_*.bak` back to `backend/artifacts/presentation_quality.py`, rebuild the backend and restart the worker. Do not delete database volumes.
