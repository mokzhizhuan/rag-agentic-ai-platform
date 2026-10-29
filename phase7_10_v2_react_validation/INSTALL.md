# Phase 7.10 V2 — React Validate Project integration

**Preserves existing ZIP generation and single-file formats.** Adds an authenticated, owner-scoped Django endpoint and a Validate Project control for ZIP artifacts only. No database migrations, no generated code execution.

## Install
Extract this folder into the root of `rag-fullstack-phase1`, stop any running worker only if you plan to rebuild its image, and run:

```powershell
python .\phase7_10_v2_react_validation\install.py .
python .\phase7_10_v2_react_validation\install.py . --apply
docker compose build --pull=false backend frontend
docker compose up -d --no-build --force-recreate backend frontend
docker compose exec backend python manage.py check
```

The installer requires your **current** `frontend/src/App.tsx` and `backend/artifacts/urls.py`, `views.py`, `models.py`; it checks text anchors before editing and makes timestamped `.bak` files. If it declines compatibility, provide those files instead of forcing the patch.

## Use
Under Create Files > My generated files, each ZIP shows **Validate Project**. Click to see counts and findings beneath that ZIP, then **Download report (.md)** if desired. Other formats remain unchanged. The report is computed on demand; it is not permanently stored.

## Server details
- `POST /api/artifacts/<id>/validate-project/`: JSON report.
- `GET /api/artifacts/<id>/validate-project/`: Markdown report download.
- Both require the existing authenticated user and check `owner_sub` on the stored artifact.
- Maximum ZIP size 12 MB; no archive extraction, execution, package installation, database access, or browser test.
- Source code is **static-checked only**. Zero findings cannot guarantee runtime or security correctness.

## Known limits
Validated with the previous Phase 7.10 static checker and a representative App.tsx structure from your uploaded code. Full Docker application integration and TypeScript compilation in your exact live checkout remain to be verified. Existing project frontend may have evolved; install refuses missing anchors rather than overwriting unrelated components.
