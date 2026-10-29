"""Stage 4.1: update only the PowerPoint renderer. Dry run by default."""
import argparse
import ast
import shutil
from datetime import datetime
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('root', nargs='?', default='.')
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    root = Path(args.root).resolve()
    generator = root / 'backend/artifacts/generator.py'
    dest = root / 'backend/artifacts/presentation_quality.py'
    source = Path(__file__).with_name('presentation_quality.py')
    if not generator.is_file() or not dest.is_file():
        raise SystemExit('Stage 4 files not found. Install Stage 4 PowerPoint first; no changes made.')
    existing = generator.read_text(encoding='utf-8')
    if 'from .presentation_quality import generate_presentation, PresentationQualityError' not in existing:
        raise SystemExit('Stage 4 PowerPoint routing missing in generator.py; no changes made.')
    ast.parse(source.read_text(encoding='utf-8'))
    old = dest.read_text(encoding='utf-8')
    ast.parse(old)
    if 'def generate_presentation(' not in old or 'def render_presentation(' not in old:
        raise SystemExit('Unexpected PowerPoint renderer; refusing replacement.')
    if old == source.read_text(encoding='utf-8'):
        print('Stage 4.1 already installed; no changes.'); return
    print('Compatible: only backend/artifacts/presentation_quality.py will change.')
    if not args.apply:
        print('Dry run only. Run with --apply to install.'); return
    backup = dest.with_name('presentation_quality.py.before_stage4_1_' + datetime.now().strftime('%Y%m%d_%H%M%S') + '.bak')
    if backup.exists():
        raise SystemExit('Backup path already exists; retry after one second.')
    shutil.copy2(dest, backup)
    shutil.copy2(source, dest)
    print('Installed. Backup:', backup)


if __name__ == '__main__':
    main()
