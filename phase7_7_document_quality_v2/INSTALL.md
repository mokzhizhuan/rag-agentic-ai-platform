# Phase 7.7 — Document quality v2 (renderer-only)

This upgrade adds a separate **cover page**, **contents page**, draft/version-awareness labeling, Word footer page numbers, and more consistent presentation to the existing PDF and Word renderers. It preserves the existing document headings, Markdown parsing, tables, and file integrity checks.

## Requirements

The previous Phase 7.7 document-quality patch must already be installed, with `backend/artifacts/document_quality.py` and `generator.py` using its `render_word` and `render_pdf` functions. Python-docx and ReportLab must be installed in the backend.

## PowerShell instructions

1. Extract `phase7_7_document_quality_v2/` into your `rag-fullstack-phase1` project root.
2. Stop the running generation worker (`Ctrl+C` in its terminal).
3. Dry-run from the project root:

   ```powershell
   python .\phase7_7_document_quality_v2\install.py .
   ```

4. If `READY` appears, apply:

   ```powershell
   python .\phase7_7_document_quality_v2\install.py . --apply
   ```

5. Rebuild backend, verify Django, and restart worker:

   ```powershell
   docker compose up -d --build backend
   docker compose exec backend python manage.py check
   docker compose run --rm backend python -u manage.py generation_worker
   ```

6. Generate a new Word and PDF technical report. Verify cover page, contents, page numbering, all report sections, and download/preview.

## Safeguards / rollback

- The script only replaces `backend/artifacts/document_quality.py` and writes a timestamped `.bak` copy in the same folder.
- It refuses installation when the renderer or `generator.py` don't have the expected integration points.
- To roll back, stop worker, copy the timestamped backup over `document_quality.py`, rebuild backend and restart the worker.
- No migrations, table changes, Keycloak changes, changes to `longform.py`, `generation_worker.py`, `App.tsx`, existing generated files, or job progress updates.
- Contents entries list sections but **are not dynamically linked to final PDF page numbers**. For this version, do not interpret them as a fully paginated table of contents.
- Document checks are structural, not engineering fact verification; inspect generated assumptions, calculations, and designs before operational use.
