#!/usr/bin/env python3
"""Safe opt-in Phase 8.1 shell installer. Dry-run by default."""
import argparse
from pathlib import Path
import re
import shutil
from datetime import datetime

ROOT = Path(__file__).resolve().parent

def patch_app(src: str) -> str:
    if "className=\"rag-shell\"" in src or "className='rag-shell'" in src:
        raise ValueError('Phase 8.1 shell already present; no changes made.')
    if 'className="tabs"' not in src or 'export default function App' not in src:
        raise ValueError('Unsupported App.tsx layout: could not locate original tabs and App component.')
    pat = re.compile(r'\breturn\s*<main\s*>')
    src, n = pat.subn('return <main className="rag-shell">', src, count=1)
    if n != 1:
        raise ValueError('Could not find the main JSX element; refused to patch.')
    src = "import './phase8-shell.css';\n" + src
    return src

def main():
    parser=argparse.ArgumentParser(description='Phase 8.1 React shell installer')
    parser.add_argument('project',help='rag-fullstack-phase1 project root')
    parser.add_argument('--apply',action='store_true')
    args=parser.parse_args()
    project=Path(args.project).expanduser().resolve()
    app=project/'frontend'/'src'/'App.tsx'
    css=project/'frontend'/'src'/'phase8-shell.css'
    if not app.is_file():
        raise SystemExit(f'App.tsx not found: {app}')
    original=app.read_text(encoding='utf-8')
    updated=patch_app(original)
    print('Compatible frontend found:',app)
    print('Plan: add CSS import, set main className=rag-shell, write phase8-shell.css')
    print('No changes to backend, state handlers, or other formats')
    if css.exists():
        raise SystemExit(f'CSS destination exists: {css}. Refusing overwrite.')
    if not args.apply:
        print('DRY RUN. Re-run with --apply to install.')
        return
    stamp=datetime.now().strftime('%Y%m%d-%H%M%S')
    backup=app.with_name(f'App.tsx.phase8-1.{stamp}.bak')
    shutil.copy2(app,backup)
    try:
        app.write_text(updated,encoding='utf-8')
        shutil.copy2(ROOT/'phase8-shell.css',css)
    except Exception:
        shutil.copy2(backup,app)
        if css.exists(): css.unlink()
        raise
    print('Installed. Backup:',backup)
    print('Next: docker compose build --pull=false frontend')
if __name__ == '__main__': main()
