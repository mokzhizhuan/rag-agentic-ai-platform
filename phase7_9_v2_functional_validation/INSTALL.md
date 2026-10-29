# Phase 7.9 V2 — Cross-File Functional Validation

**Backend-only targeted upgrade** to the Phase 7.9 V1 universal ZIP project generator. Does not touch other generators, the React dropdown, the database, or the worker. No new pip dependencies.

## Install (PowerShell, from rag-fullstack-phase1)

Extract `phase7_9_v2_functional_validation_upgrade.zip` to the project root; stop the currently running worker with Ctrl+C.

```powershell
python .\phase7_9_v2_functional_validation\install.py .
python .\phase7_9_v2_functional_validation\install.py . --apply
docker compose build --pull=false backend
docker compose up -d --no-build --force-recreate backend
docker compose exec backend python manage.py check
docker compose exec backend python -c "from artifacts.functional_quality import inspect_project; print('V2 checker OK')"
docker compose run --rm backend python -u manage.py generation_worker
```

Do not run `docker compose down -v` or delete migrations. The installer backs up `backend/artifacts/universal_zip.py` automatically. **Only apply if the compatibility check passes.**

## New validation

- Cross-file matching of static `getElementById('x')` / `querySelector('#x')` calls in linked JavaScript with actual HTML `id="x"` elements. Missing IDs trigger a focused AI repair, maximum two passes. Dynamic selectors are not fully covered.
- Detection of unresolved explicit relative Python imports.
- Detection of a common CSV overflow mistake: `csv.DictReader` extra-column validation via `row.values()` without checking the `None` key or specifying `restkey`. This triggers repair (the earlier CCTV Python/CSV issue).
- Configuration warnings: missing `.env.example` entries for variables referenced in Docker Compose; `REACT_APP_` in a Vite project.
- Warnings and validation scope recorded under `validation_advisories` in `project-manifest.json`.
- Preserves the existing V1 import/asset checks, safe path rules, format parsers, ZIP limits and archive verification.

## Tests

Generate two new ZIPs with the same prior prompts: (a) standalone HTML/CSS/JS CCTV monitoring site with functioning search/status filters and (b) Python/SQL/YAML/CSV CCTV validator including detection of CSV rows with too many fields. Upload the ZIPs for review.

## Limitations

These are **targeted static checks**, not actual functional tests. The generator does not run generated code, compile projects, install dependencies, execute SQL, start Docker services or connect to real cameras. It cannot prove cross-language API contract compatibility, detect all logical bugs, or distinguish all simulated data from genuine integrations. The existing per-file job progress remains unchanged. Any project should be reviewed and tested in an isolated environment before deployment.
