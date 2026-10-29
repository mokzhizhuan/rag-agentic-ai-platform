# Phase 7.9 V2.1 — Cyclic Project Plan Fix

This **backend-only** update fixes `Cyclic file-plan dependency: index.html` in the Universal ZIP V2 generator. The model can correctly describe mutual *runtime* references (for example, HTML loads JavaScript and JavaScript references HTML element IDs); these are not necessarily an impossible file-generation order.

The upgraded planner converts circular *generation-order hints* into an acyclic order by removing only DFS back-edges. It retains shared contracts, independently validates cross-file references after generation, and records removed edges in `project-manifest.json` as `generation_cycle_breaks`. Genuine missing/unsafe paths are still rejected, and detected missing cross-file references still go through the existing repair loop.

## Install (PowerShell)

Extract `phase7_9_v2_1_cycle_fix_upgrade.zip` into your `rag-fullstack-phase1` project root. Stop any running generation worker with Ctrl+C, then:

```powershell
python .\phase7_9_v2_1_cycle_fix\install.py .
python .\phase7_9_v2_1_cycle_fix\install.py . --apply
docker compose build --pull=false backend
docker compose up -d --no-build --force-recreate backend
docker compose exec backend python manage.py check
docker compose run --rm backend python -u manage.py generation_worker
```

No database migration or frontend change. No other code-format generators are modified. Do not use `docker compose down -v`.

Test again using your existing ZIP format option and the same HTML/CSS/JavaScript CCTV dashboard prompt. The package was tested with cyclic-plan examples and a mocked generation, not against your actual OpenAI/Docker environment.
