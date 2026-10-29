# Phase 7.8 Stage 3 — PostgreSQL SQL and YAML quality

Adds `backend/artifacts/structured_quality.py` and inserts one new route in `backend/artifacts/generator.py` before its generic text branch. It does **not** replace or change the successful Stage 1 `code_quality.py`, Stage 2 `markup_quality.py`, the document/PDF renderers, frontend, generation worker or database. **No migrations.** Existing generated files remain unchanged.

## Dependencies

Add to `backend/requirements.txt` once:

```text
sqlglot>=25,<30
PyYAML>=6,<7
```

`sqlglot` parses PostgreSQL-dialect SQL without connecting to a database. The upgrade rejects raw/unrecognized SQL commands, `DROP`, `TRUNCATE`, `COPY ... PROGRAM`, and `UPDATE`/`DELETE` without `WHERE`. This is a conservative **static safeguard**, not a SQL sandbox or security guarantee: generated SQL may still alter data, contain schema mistakes, or be expensive. **Never run unreviewed generated SQL against your real PostgreSQL database.**

`PyYAML`'s SafeLoader verifies YAML syntax and safe built-in data structures; an added loader rejects duplicate mapping keys. It does not enforce Docker Compose/Kubernetes/application-specific schemas. Generated YAML is not executed.

## Install (PowerShell)

Extract the ZIP **preserving the `phase7_8_stage3_sql_yaml` folder** in `rag-fullstack-phase1`. Stop your running generation worker using Ctrl+C first.

```powershell
python .\phase7_8_stage3_sql_yaml\install.py .
python .\phase7_8_stage3_sql_yaml\install.py . --apply
```

Dry run checks for the existing Stage 1 and 2 routes and format maps. If it rejects the file format maps, **do not force it**; share the relevant `backend/artifacts/generator.py` mappings so we can make an exact patch. The installer stores `backend/artifacts/generator.py.before_stage3_sql_yaml.bak` and refuses to overwrite prior files.

```powershell
docker compose build --pull=false backend
docker compose up -d --no-build --force-recreate backend
docker compose exec backend python -c "import sqlglot, yaml; print('SQL and YAML parsers OK')"
docker compose exec backend python manage.py check
docker compose run --rm backend python -u manage.py generation_worker
```

If the worker already runs in another terminal, stop it first to avoid parallel workers using different code.

## Test prompts

**SQL — select `SQL .sql` format:**

> Write PostgreSQL SQL to create an `iot_camera_devices` table with a unique camera ID, name, location, online/offline status, created_at and updated_at. Add non-destructive `CREATE TABLE IF NOT EXISTS`, a relevant index, and commented sample SELECT queries to count cameras by status. Do not create or change a live database.

**YAML — select `YAML .yaml` format:**

> Create one Docker Compose YAML configuration for a Django backend, React frontend and PostgreSQL database. Include healthcheck, named volume, environment-variable references rather than hardcoded passwords, restart policy and bridge network. Use illustrative service names and a valid Compose structure. Do not include secrets.

For SQL also test deliberately destructive requests: the new path must reject `DROP` or `TRUNCATE`, not silently save those statements. YAML should reject duplicate keys. For YAML, after download run `python -c "import yaml,sys; print(type(yaml.safe_load(open(sys.argv[1],encoding='utf-8'))).__name__)" .\your-file.yaml` (simple YAML syntax smoke check).

## Limitations

- One text artifact per job. Up to 3 total generation attempts, each limited to 32,000 characters.
- SQL dialect parser is **not PostgreSQL server validation**. Query planning, table/column existence, migrations, schema consistency and safe execution require further checks.
- YAML syntax validation is **not Docker Compose/Kubernetes schema validation**.
- Existing worker progress display remains unchanged; optional internal progress callback is not wired into the worker.
- Installer modifies generator routing only; no React/frontend edits required.
- Restore the timestamp-independent backup to roll back (stop worker first, then rebuild). `structured_quality.py` can be removed if no longer used.
