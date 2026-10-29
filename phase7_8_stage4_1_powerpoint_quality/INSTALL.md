# Phase 7.8 Stage 4.1 — PowerPoint quality enhancement

This is a **backend-only** update of the existing Stage 4 PowerPoint renderer. It does not change `generator.py`, `code_quality.py`, other format generators, database migrations, or the generation worker.

## Included
- More purposeful deck layouts: title, closing, bullets, two-column, editable tables, metrics, workflow/architecture flow, and risk comparison.
- Splits bullet slides above 5 items, wide/long tables over 6 data rows (risk tables over 5), and two-column panels over 4 items per side, using numbered continuation titles.
- Content-aware table column weighting, alternating table rows, consistent 16:9 typography and footer.
- Reopen/shape bounds checks; conservative text-cell length safeguards. This is **not** a pixel-accurate text clipping or browser/Office render test.
- Capped 24 slides after expansion; if exceeded, raises a clear error. Existing model call/retry logic remains.

## Installation (PowerShell from project root)
1. Extract ZIP so the folder `phase7_8_stage4_1_powerpoint_quality` sits in your project root.
2. Stop the current worker (Ctrl+C).
3. Check existing Stage 4 renderer:

```powershell
python .\phase7_8_stage4_1_powerpoint_quality\install.py .
```

4. If compatible, apply (timestamped backup created):

```powershell
python .\phase7_8_stage4_1_powerpoint_quality\install.py . --apply
```

5. Deploy:

```powershell
docker compose build --pull=false backend
docker compose up -d --no-build --force-recreate backend
docker compose exec backend python manage.py check
docker compose run --rm backend python -u manage.py generation_worker
```

If your backend code is bind-mounted, rebuilding may not be necessary; rebuilding is the most reliable approach. Ensure `python-pptx>=1.0,<2` remains in `backend/requirements.txt`.

## Test prompt
Create a professional 10-slide CCTV design and delivery deck with a title slide, architecture flow diagram, camera table with 12 sample TBD rows, PoE/network requirements, 8 commissioning checks, 6 risks with mitigations and TBD status, phased workflow, and handover actions. Keep unknown real-world values as TBD and never state that inspections were completed.

**Expected:** table/long bullet content produces additional continuation slides as needed; architecture flow and risk table use editable PowerPoint shapes. The final deck may exceed 10 slides due to automatic splitting.

## Limits
This package was tested locally with synthetic slide plans; the actual OpenAI-to-Django route must be checked in your environment. PowerPoint fonts and auto-layout may still differ between Office versions. No images, logos, network calls, or live CCTV connections are inserted.
