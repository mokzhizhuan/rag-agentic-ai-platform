"""Patch only backend/artifacts/code_quality.py. No generated files are changed."""
from __future__ import annotations
import argparse
import ast
from pathlib import Path
import shutil
import hashlib

EXPECTED_ORIGINAL_SHA256 = "e5a72e670d7d6bd935b42498fcb860cc4000a911a313c160cfe2dd7987d265a5"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('root', nargs='?', default='.')
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    root = Path(args.root).resolve()
    target = root / 'backend/artifacts/code_quality.py'
    replacement = Path(__file__).with_name('code_quality.py')
    if not target.is_file():
        raise SystemExit(f'NOT FOUND: {target}\nInstall Phase 7.8 first.')
    existing = target.read_text(encoding='utf-8')
    patched = replacement.read_text(encoding='utf-8')
    ast.parse(existing)
    ast.parse(patched)
    if '_check_optional_filter_map' in existing:
        print('Optional-filter protection already present. No changes made.')
        return
    if hashlib.sha256(existing.encode("utf-8")).hexdigest() != EXPECTED_ORIGINAL_SHA256:
        raise SystemExit("UNSUPPORTED: backend code_quality.py differs from the Phase 7.8 Stage 1 baseline. No changes made; review before applying.")
    print('Compatible: add optional-filter safety validation to Phase 7.8 JS generator.')
    if not args.apply:
        print('Dry run only. Use --apply to install.')
        return
    backup = target.with_name('code_quality.py.before_optional_filter.bak')
    if backup.exists():
        raise SystemExit(f'Backup already exists: {backup}. No changes made; inspect before retry.')
    shutil.copy2(target, backup)
    shutil.copy2(replacement, target)
    print(f'Installed. Backup: {backup}')


if __name__ == '__main__':
    main()
