# Phase 7.8 Stage 2 — HTML and CSS quality validation

This upgrade adds a **separate** `backend/artifacts/markup_quality.py` module and a small HTML/CSS branch to `backend/artifacts/generator.py`. It does **not** replace `code_quality.py`, the Stage 1 TSX/JavaScript generator, the Python generator, Word/PDF/Markdown renderers, or worker/job tracking. No migrations are required.

## Dependency

Add this to `backend/requirements.txt` if it is not already there:

```text
tinycss2>=1.2,<2
```

HTML structure checking uses Python's standard-library `html.parser`. CSS parsing uses `tinycss2`. Parsing cannot establish real browser rendering, semantic accessibility compliance, or runtime behavior of embedded JavaScript.

## Install (Windows PowerShell)

Extract the ZIP into the `rag-fullstack-phase1` root, keeping the `phase7_8_stage2_html_css` directory. Stop the manually running worker first.

```powershell
python .\phase7_8_stage2_html_css\install.py .
python .\phase7_8_stage2_html_css\install.py . --apply
```

The installer aborts if the expected Stage 1 code or patch marker is missing. It creates `backend/artifacts/generator.py.before_html_css_stage2.bak` before applying the patch. Keep that backup. For a rollback, stop the worker, copy the backup over `generator.py`, and remove the added `markup_quality.py` only if you no longer need it. Rebuild afterward.

```powershell
docker compose build --pull=false backend
docker compose up -d --no-build backend
docker compose exec backend python manage.py check
docker compose exec backend python -c "import tinycss2; print('tinycss2 OK', tinycss2.__version__)"
docker compose run --rm backend python -u manage.py generation_worker
```

Rebuild after updating requirements; restarting without rebuilding will not install a new dependency. The generation worker must also be restarted to pick up code changes.

## Test prompts

**HTML:** Set File format to HTML and request: `Create one complete responsive standalone HTML5 CCTV monitoring status page with a header, summary metrics, 4 sample camera cards, online/offline badges, a labeled search input, semantic HTML, accessible image alternatives, and embedded CSS. No external assets or libraries.`

**CSS:** Set File format to CSS and request: `Create a responsive standalone CSS stylesheet for a CCTV dashboard. Include dashboard header, responsive camera card grid, online/offline badges, filter toolbar, focus-visible states, table design and @media breakpoints. No HTML and no external dependencies.`

For both, confirm the generated file can be downloaded and inspect its completeness. For CSS, valid parsing does not prove every CSS property is semantically correct. For HTML, validation checks tag pairing, doctype, main document structure and duplicate ids; it is intentionally stricter than browser HTML error recovery.

## Limitations

* A **single file** is generated, not a multi-file website.
* Each attempt is capped at 32,000 characters; up to two complete regeneration attempts are made if parsing or structure fails.
* The worker still owns existing progress and elapsed-time display; generator-level progress callbacks are optional and **not yet connected**.
* The generated source is **never executed** in the Django backend. Test HTML rendering in an isolated browser, not inside your production backend.
* Existing downloaded files are not modified.
