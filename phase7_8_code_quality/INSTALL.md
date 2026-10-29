# Phase 7.8 Stage 1 — React/TSX and JavaScript source quality

This add-on changes only `backend/artifacts/generator.py` (adds one branch) and adds `backend/artifacts/code_quality.py`.
It leaves Python, Markdown, Word, PDF, media generation, worker and DB alone.

## Required packages

Add to `backend/requirements.txt` (only once):

```text
tree-sitter>=0.24,<0.26
tree-sitter-javascript>=0.23,<0.26
tree-sitter-typescript>=0.23,<0.26
```

These provide parser-based **syntactic** checks inside your Python backend. They are not a complete `tsc` build or a runtime test, and generated code is not executed.

## Install

1. Unzip the `phase7_8_code_quality` directory to the project root.
2. Stop the manually running generation worker using Ctrl+C.
3. From the project root run:

```powershell
python .\phase7_8_code_quality\install.py .
python .\phase7_8_code_quality\install.py . --apply
```

4. Add the packages above to `backend/requirements.txt` and rebuild backend:

```powershell
docker compose build --pull=false backend
docker compose up -d --no-build backend
docker compose exec backend python manage.py check
docker compose exec backend python -c "import tree_sitter, tree_sitter_javascript, tree_sitter_typescript; print('Parsers OK')"
docker compose run --rm backend python -u manage.py generation_worker
```

## Test prompts

**React / TSX**: `Create a single React TypeScript TSX component implementing a CCTV camera status dashboard with typed example data, filter by online/offline, responsive cards, and accessible buttons. All UI and styling must be self-contained. Export a default component; no third-party UI library.`

**JavaScript**: `Create a standalone browser JavaScript ES module with functions for normalizing CCTV device records, filtering by severity, and exporting a CSV string safely. Include JSDoc annotations and input validation. Do not rely on external dependencies.`

After download, test TSX in your actual React project with `tsc` and Vite, and test JavaScript with `node --check file.js` (checks syntax only).

## Limitations

- The generator produces **one source file** per job; it does not resolve all project imports or dependencies.
- Per-step responses are bounded and retried, but longer files may still fail. It does not concatenate partial model outputs.
- There is **no true code-unit progress integration** yet: the existing worker still reports its general processing milestone. The optional `progress` callback is designed for subsequent integration.
- No database migrations.
- If Docker cannot access registry/package indexes, the rebuild may fail; don't change project runtime versions or delete DB volumes.
