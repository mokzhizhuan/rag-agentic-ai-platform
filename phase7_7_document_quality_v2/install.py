"""Install quality renderer v2 without modifying generator or worker code."""
import argparse
import ast
from datetime import datetime, timezone
from pathlib import Path
import shutil


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('root', nargs='?', default='.')
    parser.add_argument('--apply', action='store_true', help='Back up existing renderer and install replacement')
    args = parser.parse_args()
    root = Path(args.root).resolve()
    artifacts = root / 'backend' / 'artifacts'
    target = artifacts / 'document_quality.py'
    source = Path(__file__).with_name('document_quality.py')
    if not (artifacts / 'generator.py').is_file() or not target.is_file():
        raise SystemExit('Missing generator.py or installed document_quality.py. Install the earlier document quality upgrade first.')
    old = target.read_text(encoding='utf-8')
    new = source.read_text(encoding='utf-8')
    ast.parse(old); ast.parse(new)
    for signature in ('def normalize_sections(', 'def markdown_document(', 'def render_word(', 'def render_pdf('):
        if signature not in old:
            raise SystemExit(f'Existing renderer does not match expected functions: {signature}. Not modifying.')
    generator = (artifacts / 'generator.py').read_text(encoding='utf-8')
    if 'document_quality import render_pdf' not in generator or 'document_quality import render_word' not in generator:
        raise SystemExit('Generator is not wired to document_quality; refusing partial install.')
    if old == new:
        print('ALREADY INSTALLED: document_quality.py matches v2'); return
    print('READY: renderer-only upgrade. No model, worker, frontend, database or migrations changed.')
    if not args.apply:
        print('DRY RUN ONLY. Run again with --apply to install.'); return
    stamp = datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')
    backup = artifacts / f'document_quality.py.{stamp}.bak'
    shutil.copy2(target, backup)
    target.write_text(new, encoding='utf-8')
    print(f'INSTALLED: {target}')
    print(f'BACKUP: {backup}')

if __name__ == '__main__':
    main()
