"""Phase 7.9 installer. Dry-run by default, timestamped backup on apply."""
from __future__ import annotations
import argparse
import ast
import re
import shutil
from datetime import datetime
from pathlib import Path

BRANCH = '''    if fmt == 'zip':
        from .universal_zip import generate_universal_zip, UniversalZipError
        try:
            return fmt, generate_universal_zip(prompt, provider)
        except UniversalZipError as exc:
            raise ArtifactGenerationError(str(exc)) from exc
'''

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('root',nargs='?',default='.')
    parser.add_argument('--apply',action='store_true')
    a=parser.parse_args()
    root=Path(a.root).resolve()
    generator=root/'backend/artifacts/generator.py'
    source=Path(__file__).with_name('universal_zip.py')
    module=root/'backend/artifacts/universal_zip.py'
    if not generator.is_file():
        raise SystemExit('Cannot find backend/artifacts/generator.py; no changes.')
    code=generator.read_text(encoding='utf-8')
    if 'from .universal_zip import generate_universal_zip' in code:
        print('ZIP generation route already installed; nothing changed.'); return
    marker='    if fmt in TEXT_FORMATS:'
    if code.count(marker)!=1:
        raise SystemExit('Cannot locate unique generic TEXT_FORMATS route. No changes.')
    if 'from .presentation_quality import generate_presentation' not in code:
        raise SystemExit('Stage 4 PowerPoint generation route is missing. No changes.')
    if module.exists():
        raise SystemExit('universal_zip.py exists already. Refusing overwrite.')
    # Add ZIP extension to FORMAT_EXT without modifying existing mappings.
    match=re.search(r'(?m)^FORMAT_EXT\s*=\s*\{',code)
    if not match:
        raise SystemExit('FORMAT_EXT dictionary was not found. No changes.')
    patched=code
    if not re.search(r"['\"]zip['\"]\s*:\s*['\"]zip['\"]",patched):
        insert=match.end()
        patched=patched[:insert]+"\n    'zip': 'zip',"+patched[insert:]
    patched=patched.replace(marker, BRANCH+marker,1)
    ast.parse(patched); ast.parse(source.read_text(encoding='utf-8'))
    print('Compatible: adding ZIP format mapping, route, and new universal_zip module.')
    print('Existing JS/TSX, HTML/CSS, SQL/YAML, Word/PDF/PPTX routes remain untouched.')
    print('IMPORTANT: Confirm the frontend File format selector exposes zip; see INSTALL.md.')
    if not a.apply:
        print('Dry-run; nothing modified. Use --apply to install.');return
    backup=generator.with_name('generator.py.before_phase7_9_'+datetime.now().strftime('%Y%m%d_%H%M%S_%f')+'.bak')
    shutil.copy2(generator,backup)
    try:
        shutil.copy2(source,module)
        generator.write_text(patched,encoding='utf-8')
    except Exception:
        shutil.copy2(backup,generator)
        if module.exists(): module.unlink()
        raise
    print('Installed Phase 7.9. Backup:',backup)

if __name__=='__main__':main()
