# Phase 7.7: Section-by-section progress (Word, PDF, Markdown)

This is a **patch** for the existing project, not a replacement application.

## Changes
- Adds `backend/artifacts/progress.py`: isolated, job-scoped progress callback using Python `ContextVar`.
- Adds section-start and section-finished updates to the existing `generate_report_sections` in `backend/artifacts/longform.py`. Supports the earlier version and the newer 3-attempt section generator.
- Adds formatting/rendering progress stages in `backend/artifacts/generator.py`.
- Wires the callback to the existing `GenerationJob.percent`/`GenerationJob.stage` database fields from `generation_worker.py` during the artifact endpoint call.
- Updates the React running-job bar to show actual completed **workflow milestone** percentage, if the known React source matches.
- Makes timestamp in the worker retain the original claimed-job `started_at` instead of resetting when processing begins.

## Installation (Windows PowerShell, from project root)
1. Unzip into a separate temporary folder, e.g. `phase7_7_section_progress`.
2. Stop any manually running generation workers using Ctrl+C (and any additional active worker services).
3. From your project root, run:

   ```powershell
   python .\phase7_7_section_progress\install_patch.py .
   docker compose exec backend python manage.py check
   docker compose up -d --build backend frontend
   docker compose exec backend python manage.py check
   ```

   If the project is not mounted into the running container, the first `check` before rebuilding may only see the old code, which is fine.

4. Start exactly one worker:

   ```powershell
   docker compose run --rm backend python -u manage.py generation_worker
   ```

5. Generate an 8-section Word or PDF report or a Markdown technical report. Progress should advance approximately 12% (outline), 18% (outline finished), then across completed sections to 85%, and 87–97% as the file is built/saved; only completed artifact persistence sets 100%.

## Important notes
- **No database migrations** and no database resets are required.
- Existing `GeneratorJob` statuses, files, and history are preserved.
- This measures **report-section milestones**, not tokens or the model's internal reasoning. The percent may remain unchanged while OpenAI processes a section.
- For Python, image, and video formats, the existing coarse progress behavior is retained.
- The current worker is synchronous. Cancelling a running provider call is best-effort and does not stop it mid-request.
- Every altered source file gets a `.backup-YYYYmmdd-HHMMSS` sibling before being written.
- The installer checks all recognized patterns and parses each modified Python file before it writes any changes. If your source differs from those provided in this conversation, it will stop with an error rather than guessing where to patch.
- Markdown uses section progress only if its generator calls `generate_report_sections`, as in the earlier Markdown fix.

## Troubleshooting
- If installer says `App.tsx progress element differs`, backend progress will still be stored, but update the React `<progress>` running state manually: set `value={job.percent??0}` and `max={100}` instead of an empty `<progress />`.
- If job remains queued, confirm worker is running and the job has `cancel_requested=False`.
- If status is `running` but percentage stays at 10%, verify your installed `longform.py` is using the instrumented report function, not an old copy.
- If the worker uses a baked image, restart it after rebuilding. An already-running temporary worker still uses its original image.


## V3 installer compatibility
The installer handles duplicate standalone `GenerationJob` imports and multiple literal `result=create_artifact_endpoint(req)` call sites without failing on a single-occurrence check. It validates all generated Python patches before writing and backs up changed files.
