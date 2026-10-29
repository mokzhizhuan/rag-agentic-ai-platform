# Phase 7.10 — Optional ZIP Project Validation Reports (V1)

This is an **opt-in local validator**, not an automatic generator replacement. It does not modify your Django backend, React frontend, generation worker, or existing generated files. It does not execute code from the input ZIP.

## Installation

Extract the folder `phase7_10_optional_validation` into your `rag-fullstack-phase1` directory. No Docker rebuild, migrations, or frontend changes are needed. The validator uses the Python standard library; `PyYAML` is optional for parsing YAML.

From PowerShell, after downloading a generated ZIP to your computer:

```powershell
python .\phase7_10_optional_validation\validate_project.py .\generated-project.zip
```

Optionally choose where reports are saved:

```powershell
python .\phase7_10_optional_validation\validate_project.py .\generated-project.zip --output-dir .\validation-reports
```

This creates `generated-project.validation.json` and `generated-project.validation.md` without altering the ZIP. The JSON includes a SHA-256 fingerprint, file inventory, findings and severity totals.

## What the tool checks

- ZIP archive readability, unsafe paths, symlinks, duplicate entries, per-file and total size limits
- Python syntax, JSON syntax, optional YAML parsing, and basic CSV row consistency
- Relative JS/TS/TSX imports, HTML local assets, and static JavaScript-to-HTML IDs
- Docker Compose build-context presence and `.env.example` variables
- Obvious secret/private-key patterns, presence of README and project manifest

It does **not** install packages, launch a browser, run tests or services, access a database, or deploy the project. It does not guarantee that the generated code functions. Potential false positives are advisory warnings. To obtain actual compilation, test or browser results, test in a separate trusted sandbox after reviewing the generated code.

## Example

`sample_web.validation.md` and `sample_python.validation.md` in this package are reports produced from two previously generated CCTV ZIP projects.
