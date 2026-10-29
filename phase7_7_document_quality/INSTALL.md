# Phase 7.7 — Document formatting and validation patch

This patch changes **only** `backend/artifacts/generator.py` Word/PDF render calls and its existing staged Markdown document branch (when present). It installs `backend/artifacts/document_quality.py` and does not change `longform.py`, progress callbacks, worker, database or API routes.

## Installation (PowerShell, project root)

Stop the generation worker using Ctrl+C, then extract the ZIP to your project root. You should see `phase7_7_document_quality/install_patch.py`.

```powershell
python .\phase7_7_document_quality\install_patch.py . --dry-run
python .\phase7_7_document_quality\install_patch.py .
docker compose up -d --build backend
docker compose exec backend python manage.py check
docker compose run --rm backend python -u manage.py generation_worker
```

The installer creates a timestamped `.bak` copy of `generator.py` if it changes it. Rerunning is safe: it does not duplicate the patch.

## Improvements

- DOCX: styled title, headings, lists, Markdown-style tables, code blocks, margins, footer; checks ZIP package and section headings.
- PDF: A4 margins, readable text, styled headings, tables, lists, code blocks, page numbers and footer; checks PDF signature and EOF. Optional `pypdf` page count validation when installed.
- Markdown: cleaned title and duplicated section-heading prefix, verified substantive sections, original body content retained. Existing progress updates are preserved.
- The system does **not** claim factual correctness or test software generated inside documents.

## Test

Generate an 8-section CCTV report in Word, PDF, and Markdown. Verify the stage-by-stage progress still advances and each file downloads and previews. In particular, the section count should be correct, no duplicated headings should appear at the top of each section, and PDF pages should have page numbers.

## Notes / compatibility

- Requires existing `python-docx` for Word and `reportlab` for PDF (both already used by your generator). Optional `pypdf` for additional PDF page-count verification.
- The patch fails closed if the Word/PDF rendering code has changed beyond its expected branch layout. If that happens, send your current `backend/artifacts/generator.py`; do not force a partial patch.
- The installer expects a section-based Markdown branch with `return fmt, content.encode('utf-8')` or another named content string. If you use a different return statement, it will stop without modifying your files.
- Generated report bodies may contain complex Markdown syntax that this conservative renderer does not fully support (notably nested tables, raw HTML and images). Unsupported syntax is treated as text.
- Reverting: stop worker, restore the timestamped `generator.py.*.bak`, remove `backend/artifacts/document_quality.py`, then rebuild and restart worker.
