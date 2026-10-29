"""Install Phase 7.8 Stage 4.2 renderer only. Dry-run unless --apply."""
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
        raise SystemExit('Stage 4 renderer not found; no files changed.')
    routing = generator.read_text(encoding='utf-8')
    if 'from .presentation_quality import generate_presentation, PresentationQualityError' not in routing:
        raise SystemExit('Expected PowerPoint routing is missing; no files changed.')
    candidate = source.read_text(encoding='utf-8')
    current = dest.read_text(encoding='utf-8')
    ast.parse(candidate); ast.parse(current)
    if 'def render_presentation(' not in current or 'def validate_plan(' not in current:
        raise SystemExit('Unexpected PowerPoint renderer; no files changed.')
    if candidate == current:
        print('Already installed.'); return
    print('Compatible. Only backend/artifacts/presentation_quality.py will change.')
    if not args.apply:
        print('Dry-run. Use --apply to install.'); return
    backup = dest.with_name('presentation_quality.py.before_stage4_2_' + datetime.now().strftime('%Y%m%d_%H%M%S_%f') + '.bak')
    shutil.copy2(dest, backup)
    shutil.copy2(source, dest)
    print('Installed. Backup:', backup)

if __name__ == '__main__':
    main()
