# Phase 7.8 — JavaScript optional-filter prevention

This patch changes **only** `backend/artifacts/code_quality.py`, the backend generator/validator for future JS/TSX source. It leaves previously generated files, `App.tsx`, Django routes, migrations, Python generation and document rendering untouched.

The generated JS module demonstrated an optional-filter bug: `toArray(rawStatuses, "status").map(normalizeStatus)` throws if `rawStatuses` is absent. The updated generator gives the model an explicit rule about optional inputs, rejects the known `toArray(...).map(...)` pattern for `.js`, and asks for a full-file repair or retry. It does **not** execute AI output or certify general runtime correctness.

## Install (PowerShell, project root)

Stop the generation worker (Ctrl+C). Extract this folder into your project root.

```powershell
python .\phase7_8_optional_filter_fix\install.py .
python .\phase7_8_optional_filter_fix\install.py . --apply
docker compose build --pull=false backend
docker compose up -d --no-build backend
docker compose exec backend python manage.py check
docker compose run --rm backend python -u manage.py generation_worker
```

## Verify and test

Use **OpenAI → JavaScript** and regenerate the camera device utilities prompt. After download, check using Node.js:

```powershell
node --check .\generated-NEWFILE.js
```

Run a manual functional check in a controlled project using `filterDevices(devices)` **without any options** and confirm it returns all records, not an exception. Also test status and severity filters. The previously generated file remains unchanged.

## Rollback

Stop worker, copy `backend/artifacts/code_quality.py.before_optional_filter.bak` back over `backend/artifacts/code_quality.py`, rebuild the backend and restart worker.
