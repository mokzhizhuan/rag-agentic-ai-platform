# Phase 7.7 — Document Quality V3.1 (contents validation fix)

Fixes false-positive `DocumentQualityError: Contents page missing a section heading` when the PDF extractor inserts line breaks/extra whitespace into long TOC entries. It also checks all contents pages when the TOC spans multiple pages. The renderer still verifies PDF structure, bookmarks and clickable links.

Only `backend/artifacts/document_quality.py` changes. It does not modify the generator, worker, React, progress tracking, or database.

1. Stop the running `generation_worker` terminal using Ctrl+C.
2. Extract this ZIP into your `rag-fullstack-phase1` project root.
3. Dry-run (does not change project files):
   `python .\phase7_7_document_quality_v3\install.py .`
4. Apply (creates a timestamped `.bak` copy):
   `python .\phase7_7_document_quality_v3\install.py . --apply`
5. `docker compose build --pull=false backend`
6. `docker compose up -d --no-build backend`
7. `docker compose exec backend python manage.py check`
8. `docker compose run --rm backend python -u manage.py generation_worker`
9. Generate another PDF with 8 descriptive headings. It should complete and preserve clickable TOC links and actual page numbers.

If the Docker build cannot reach Docker Hub, check whether your backend source folder is bind mounted before using a restart instead. Do not reset Docker volumes or PostgreSQL.

Tested locally with ReportLab + pypdf using an 8-section report and a 16-section report with long, wrapping TOC entries. Full integration with your Docker app has not been performed.
