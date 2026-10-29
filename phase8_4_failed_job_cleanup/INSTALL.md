# Phase 8.4 — Failed generation job cleanup

Adds **Remove** beside each failed job in **Diagnostics**, and **Remove All Failed Jobs** above the generation activity. No phase numbers are inserted into your UI titles.

## Install (project root in PowerShell)

Unzip the upgrade into your existing `rag-fullstack-phase1` directory. Stop the generation worker before rebuilding the backend (Ctrl+C); this avoids an old worker running against the newly deployed code.

```powershell
python .\phase8_4_failed_job_cleanup\install.py .
python .\phase8_4_failed_job_cleanup\install.py . --apply
docker compose build --pull=false backend frontend
docker compose up -d --no-build --force-recreate backend frontend
docker compose exec backend python manage.py check
```

If you normally run the generation worker manually, start it again in a separate terminal:

```powershell
docker compose run --rm backend python -u manage.py generation_worker
```

Refresh `http://localhost:5174` using Ctrl+F5.

## Behaviour

- **Remove** prompts for confirmation and calls `DELETE /api/artifacts/jobs/{id}/remove-failed/`.
- **Remove All Failed Jobs** prompts for confirmation and calls `DELETE /api/artifacts/jobs/failed/`.
- Both endpoints use the authenticated user's `request.user.sub`, only delete rows with `status='failed'`, and reject/skip rows that reference an artifact.
- Bulk removal deletes all eligible failed rows in the account, not just the last 30 returned by the jobs list API.
- Any private uploaded inputs attached to deleted jobs are removed after transaction commit. No generated artifacts are deleted. Other users' rows are not deleted.
- The existing `DELETE /api/artifacts/jobs/{id}/` cancellation endpoint is **not changed**.
- UI refreshes the jobs list after each removal. The failed count is labeled "in loaded history," reflecting the backend's 30-row listing limit.

## Files changed

- `backend/artifacts/job_views.py` — additional cleanup views
- `backend/artifacts/urls.py` — new routes
- `frontend/src/App.tsx` — handlers and controls inside Diagnostics only
- `frontend/src/phase8-failed-cleanup.css` — styling for cleanup buttons

Existing modified files are backed up with `.bak-YYYYMMDD-HHMMSS` suffixes. The installer is dry-run by default and is repeatable.

## Verification and limitations

Local checks: Python syntax and installer dry-run/apply/reinstall tests against a representative app were successful. Actual Docker Django checks, React TypeScript compile, and live endpoint tests still need to run on your project. No database migrations are required.

Test by removing a known failed job, then use Remove All on remaining failed jobs. Verify completed jobs and My Generated Files remain unchanged.
