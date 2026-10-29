# Phase 7.9 — Universal ZIP Project Generation

A **backend-only, additive** generator. Uses the same OpenAI/Ollama provider machinery as existing formats, plans a mixed-format project, generates associated files sequentially, checks local import/asset and Compose build-path references, and returns a `.zip` byte stream. **No framework is assumed.** No generated code is executed.

## Install in PowerShell

1. Extract `phase7_9_universal_zip_upgrade.zip` into your `rag-fullstack-phase1` folder.
2. Stop the running generation worker using Ctrl+C.
3. Check the installer and apply:

```powershell
python .\phase7_9_universal_zip\install.py .
python .\phase7_9_universal_zip\install.py . --apply
```

4. The backend should already have Stage 1–3 parsers (`tree-sitter`, `tree-sitter-javascript`, `tree-sitter-typescript`, `tinycss2`, `sqlglot`, `PyYAML`). No additional dependencies are required beyond the earlier phases. Rebuild and restart:

```powershell
docker compose build --pull=false backend
docker compose up -d --no-build --force-recreate backend
docker compose exec backend python manage.py check
docker compose exec backend python -c "from artifacts.universal_zip import validate_plan; print('Universal ZIP module OK')"
docker compose run --rm backend python -u manage.py generation_worker
```

5. **Frontend selector:** The installer doesn't modify frontend code. If `.zip` isn't offered in the Create Files dropdown, add an entry for the existing format list, using value **`zip`**, label **`ZIP Project (.zip)`**. Also ensure the backend format allow-list (if separate from `FORMAT_EXT`) includes `zip`. These parts vary among frontend/backend versions and cannot be patched blindly. If ZIP is listed and the job returns “unsupported format,” share the current format validation code so it can be connected safely.

## Test prompts

- "Create a standalone responsive task board project with index.html, CSS and JavaScript as linked files, sample tasks, README and no external dependencies. Package as ZIP."
- "Create a Django and React CCTV admin project with a consistent camera API contract, PostgreSQL config, Docker Compose, .env.example, requirements and README; keep the project compact with no secrets or claims of tested integration."
- "Create a mixed ZIP containing Python data processing, a sample CSV, SQL table schema, YAML configuration and a README; ensure filenames and fields agree."

## What is checked

- AI produces one JSON project plan, with 2–35 text/source/config files and dependency ordering.
- Paths are relative and checked for traversal, absolute paths, duplicate names, unusual filename types, and credential filenames.
- Bounded text generation (110 KB/file, 1.5 MB archive, 35 planned files).
- Static Python/JSON/YAML/SQL and JavaScript/TSX parser checks when the relevant previous modules are installed.
- Local JS/TSX imports, HTML relative assets, Docker Compose build context folder references. Up to two focused cross-file repair passes.
- ZIP CRC/integrity checked after writing, includes `project-manifest.json`.
- Existing single-file generators, progress job model, worker, database and earlier file formats are not changed.

## Known limits

- **No execution, compilation, network installation, browser testing, database execution or full runtime compatibility verification**. A successful ZIP does not guarantee a functioning project.
- Path/reference checks cannot prove API route or schema consistency semantically. The shared-contract prompt reduces drift but is not formal type checking.
- The generator uses existing *job-level* progress. File-level progress callbacks are supported internally but are **not yet wired through the existing worker**; don't expect live "file 4/18" updates without additional job-layer integration.
- Some formats like DOCX/PDF/PPTX, images and binaries are **not supported as child files yet**; the ZIP itself can contain multiple supported text files. ZIP expansion to mixed binary documents requires integrating the existing artifact renderers as sub-generators.
- Model output limits are more likely to occur for large requested projects; start with small-to-medium projects.
- The generated ZIP is intended for review, not automatic production deployment.
