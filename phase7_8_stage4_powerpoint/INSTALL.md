# Phase 7.8 Stage 4 — Editable PowerPoint quality

Adds `backend/artifacts/presentation_quality.py` and **one early PowerPoint routing branch** in `backend/artifacts/generator.py`. The old PowerPoint branch remains unchanged but is bypassed. Stage 1 JavaScript/TSX, Stage 2 HTML/CSS, Stage 3 SQL/YAML, Python, documents and frontend are **not modified**. Existing generated artifacts are untouched. **No migrations.**

## Requirements

Make sure `backend/requirements.txt` includes once:

```text
python-pptx>=1.0,<2
```

`python-pptx` may already be installed. The new output uses editable shapes, editable text and native PowerPoint tables, with a 16:9 canvas. The renderer performs a structural check that every shape stays within slide boundaries, but **does not measure text wrapping in PowerPoint**, check fonts installed on the client's machine, or guarantee there is no visual text overflow. No external images, charts, template asset upload, animation or live data yet.

## Install on Windows / PowerShell

Unzip while preserving the `phase7_8_stage4_powerpoint` directory inside your `rag-fullstack-phase1` project. Stop the existing worker using Ctrl+C before rebuilding. From project root:

```powershell
python .\phase7_8_stage4_powerpoint\install.py .
python .\phase7_8_stage4_powerpoint\install.py . --apply
```

The first command is a dry-run and checks that the Stage 3 SQL/YAML routing is already present. If it fails, **do not force changes**: share the error and current `backend/artifacts/generator.py`. Applying creates `backend/artifacts/generator.py.before_stage4_powerpoint.bak` for rollback and copies the new module, refusing to overwrite an existing copy.

Rebuild just the backend image and recreate backend container:

```powershell
docker compose build --pull=false backend
docker compose up -d --no-build --force-recreate backend
docker compose exec backend python -c "from pptx import Presentation; print('PowerPoint library OK')"
docker compose exec backend python manage.py check
```

Start the worker in its own PowerShell window, ensuring the previous worker was stopped:

```powershell
docker compose run --rm backend python -u manage.py generation_worker
```

## Test

Choose **OpenAI → PowerPoint / PPTX** in Create Files:

> Create a professional 8-slide CCTV engineering presentation. Include a title slide, overview, system architecture, camera schedule table with 4 columns and sample TBD entries, network and PoE requirements, commissioning checks, risk/mitigation comparison, and handover/next steps. Use TBD instead of inventing real camera counts or tested results. Design concise professional slides.

Download `.pptx`, open it in Microsoft PowerPoint, check 16:9 dimensions and that all text/table entries are editable. Confirm slide ordering, contrast, no clipped text and correct content. Upload the output for further review.

## Implementation and limits

- Up to 16 slides, up to 3 complete plan attempts, model response capped at 45,000 characters.
- Slide types: `title`, `bullets`, `two_column`, `table`, `metrics`, `closing`.
- Model returns a JSON slide plan; renderer validates schema, layouts, field lengths and table dimensions before producing editable PowerPoint shapes.
- Layouts have conservative word limits; table width adapts to column count and text is bounded, but **text overflow can still happen visually**. The PowerPoint validation checks file opening, slide count, and geometry only.
- No remote images or untrusted code executed; no PostgreSQL/database changes.
- Existing job progress stages are unchanged. Internal presentation progress callback is available but not integrated with the background worker UI yet.
- If generation fails, copy the job error message and backend/worker logs for diagnosis.

## Rollback

Stop worker. Restore `generator.py.before_stage4_powerpoint.bak` over `generator.py`, remove `presentation_quality.py`, rebuild the backend and restart backend and worker. Do not delete database volumes.
