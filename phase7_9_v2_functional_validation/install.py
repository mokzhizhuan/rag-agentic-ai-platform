"""Dry-run by default. Replace only Phase 7.9 universal_zip.py and install functional_quality.py."""
from __future__ import annotations
import argparse
import ast
import shutil
from datetime import datetime
from pathlib import Path

def main():
    p=argparse.ArgumentParser();p.add_argument('root',nargs='?',default='.');p.add_argument('--apply',action='store_true');a=p.parse_args()
    root=Path(a.root).resolve();target=root/'backend/artifacts/universal_zip.py';helper=root/'backend/artifacts/functional_quality.py'
    source=Path(__file__).with_name('universal_zip.py'); helper_source=Path(__file__).with_name('functional_quality.py')
    if not target.is_file():raise SystemExit('Phase 7.9 V1 backend/artifacts/universal_zip.py not found; no changes.')
    old=target.read_text(encoding='utf-8')
    required=('def generate_universal_zip(', 'def cross_file_issues(', 'def package_zip(', 'Phase 7.9: bounded')
    if not all(x in old for x in required):raise SystemExit('Unexpected universal_zip.py version; refusing to overwrite.')
    if helper.exists():raise SystemExit('functional_quality.py already exists; refusing to overwrite.')
    ast.parse(source.read_text(encoding='utf-8'));ast.parse(helper_source.read_text(encoding='utf-8'))
    print('Compatible: V2 replaces only universal_zip.py and adds functional_quality.py.')
    print('generator.py, React UI, worker and individual file generators remain unchanged.')
    if not a.apply:print('Dry-run only. Add --apply to install.');return
    backup=target.with_name('universal_zip.py.before_phase7_9_v2_'+datetime.now().strftime('%Y%m%d_%H%M%S_%f')+'.bak')
    shutil.copy2(target,backup)
    try:
        shutil.copy2(helper_source,helper)
        shutil.copy2(source,target)
    except Exception:
        shutil.copy2(backup,target)
        helper.unlink(missing_ok=True)
        raise
    print('Installed. Backup:',backup)
if __name__=='__main__':main()
