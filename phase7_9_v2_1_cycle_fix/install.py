"""Phase 7.9 V2.1 -- back up and update universal_zip.py only."""
from __future__ import annotations
import argparse
import ast
import shutil
from datetime import datetime
from pathlib import Path


def main():
    p = argparse.ArgumentParser()
    p.add_argument('root', nargs='?', default='.')
    p.add_argument('--apply', action='store_true')
    a = p.parse_args()
    root = Path(a.root).resolve()
    target = root / 'backend' / 'artifacts' / 'universal_zip.py'
    helper = root / 'backend' / 'artifacts' / 'functional_quality.py'
    source = Path(__file__).with_name('universal_zip.py')
    if not target.is_file() or not helper.is_file():
        raise SystemExit('Phase 7.9 V2 backend modules are missing; no changes made.')
    old = target.read_text(encoding='utf-8')
    required = ('Cyclic file-plan dependency:', 'from .functional_quality import inspect_project', 'def generate_universal_zip(', 'validation_advisories')
    if not all(token in old for token in required):
        raise SystemExit('Unexpected or already patched universal_zip.py version; refusing to overwrite.')
    ast.parse(source.read_text(encoding='utf-8'))
    print('Compatible: will update only backend/artifacts/universal_zip.py. No other modules modified.')
    if not a.apply:
        print('Dry run only. Add --apply after checking compatibility.')
        return
    backup = target.with_name('universal_zip.py.before_v2_1_' + datetime.now().strftime('%Y%m%d_%H%M%S_%f') + '.bak')
    shutil.copy2(target, backup)
    try:
        shutil.copy2(source, target)
    except Exception:
        shutil.copy2(backup, target)
        raise
    print('Applied Phase 7.9 V2.1. Backup:', backup)


if __name__ == '__main__':
    main()
