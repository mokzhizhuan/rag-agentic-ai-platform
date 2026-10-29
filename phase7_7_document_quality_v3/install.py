"""Renderer-only upgrade, dry-run unless --apply is supplied."""
import argparse
import ast
from datetime import datetime, timezone
from pathlib import Path
import shutil

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('root', nargs='?', default='.')
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    root = Path(args.root).resolve()
    artifacts = root / 'backend' / 'artifacts'
    target = artifacts / 'document_quality.py'
    generator = artifacts / 'generator.py'
    source = Path(__file__).with_name('document_quality.py')
    if not (target.is_file() and generator.is_file()):
        raise SystemExit('Missing backend/artifacts/document_quality.py or generator.py. No changes made.')
    old = target.read_text(encoding='utf-8')
    new = source.read_text(encoding='utf-8')
    ast.parse(old); ast.parse(new)
    for signature in ('def normalize_sections(', 'def markdown_document(', 'def render_word(', 'def render_pdf('):
        if signature not in old:
            raise SystemExit(f'Current renderer lacks {signature}; no changes made.')
    generated = generator.read_text(encoding='utf-8')
    if not ('document_quality import' in generated and 'render_pdf' in generated and 'render_word' in generated):
        raise SystemExit('Generator does not appear connected to the quality renderer. No changes made.')
    if old == new:
        print('ALREADY INSTALLED: Document Quality V3'); return
    print('COMPATIBLE: only document_quality.py will be replaced; job pipeline and generator unchanged.')
    if not args.apply:
        print('DRY RUN. Execute again with --apply to install.'); return
    backup = target.with_name('document_quality.py.'+datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')+'.bak')
    shutil.copy2(target, backup)
    try:
        target.write_text(new, encoding='utf-8')
    except BaseException:
        shutil.copy2(backup,target)
        raise
    print('INSTALLED:',target)
    print('BACKUP:',backup)

if __name__ == '__main__':
    main()
