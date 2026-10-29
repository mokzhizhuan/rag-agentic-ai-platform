# Phase 7.7 — Automatic PDF Table Layout (V4)

This is a **renderer-only** upgrade based on the Document Quality V3.1 renderer. It replaces only `backend/artifacts/document_quality.py`; it does not modify database migrations, `longform.py`, the worker, React, or generator routing.

## Features

- Uses portrait for narrow/simple tables and switches verbose 4–5-column tables or 6–12-column tables to landscape A4 appendix pages.
- Uses column widths weighted by sample content instead of identical widths.
- Repeats table header on additional pages and returns to portrait for subsequent report sections.
- Retains the V3.1 cover, clickable/bookmarked contents, page numbers, and structural checks.
- Tables appear only if the model actually supplies Markdown tables; no engineering values are invented.

## Install (PowerShell from project root)

1. Stop the active generation worker using Ctrl+C. Do not start a second worker.
2. Extract ZIP so `phase7_7_auto_table_v4/` exists in the project root.
3. Check compatibility without making changes:

   `python .\phase7_7_auto_table_v4\install.py .`

4. Apply (creates a timestamped backup of `document_quality.py`):

   `python .\phase7_7_auto_table_v4\install.py . --apply`

5. Build and start backend:

   `docker compose build --pull=false backend`
   `docker compose up -d --no-build backend`
   `docker compose exec backend python manage.py check`

6. Restart the worker:

   `docker compose run --rm backend python -u manage.py generation_worker`

## Test prompt

Choose **OpenAI → PDF** and ask:

"Create an eight-section CCTV engineering report. Include a Markdown table with columns Item, Test Method, Expected Result, Actual Result, and Status, with at least ten realistic commissioning checks. Use TBD for all unverified project values and results. Also include a small two-column status table. Do not invent completed inspections."

Confirm the contents page still works; the five-column table is on landscape pages, and the two-column table and report body stay portrait. For a long landscape table, the header should repeat on every table page. Page numbers should remain continuous.

## Limitations

- Landscape tables start on a dedicated page. This may increase total page count, but improves readability and avoids overly narrow columns.
- Word (.docx) rendering is unchanged in this upgrade; its tables remain Word-managed. This patch targets the PDF table problem observed in the 10-page CCTV report.
- A very long unbreakable table cell may still require shorter source content; it is not silently truncated beyond existing 800-character per-cell safeguard.
- Full integration in your Docker application has not been executed here. Local renderer checks used ReportLab and pypdf.

## Rollback

The installer prints the exact `.bak` path created next to `backend/artifacts/document_quality.py`. To revert, copy that `.bak` file back to `document_quality.py`, rebuild backend, and restart the worker. No migration or database reset required.
