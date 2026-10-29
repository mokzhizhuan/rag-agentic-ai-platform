"""Non-destructive additive installer: dry run default."""
import argparse
import ast
import shutil
from pathlib import Path

BRANCH = '''    if fmt == 'powerpoint':
        from .presentation_quality import generate_presentation, PresentationQualityError
        try:
            return fmt, generate_presentation(prompt, provider)
        except PresentationQualityError as exc:
            raise ArtifactGenerationError(str(exc)) from exc
'''


def main():
    p = argparse.ArgumentParser()
    p.add_argument('root', nargs='?', default='.')
    p.add_argument('--apply', action='store_true')
    args = p.parse_args()
    root = Path(args.root).resolve()
    generator = root / 'backend/artifacts/generator.py'
    target = root / 'backend/artifacts/presentation_quality.py'
    source = Path(__file__).with_name('presentation_quality.py')
    if not generator.is_file():
        raise SystemExit(f'Cannot find generator.py: {generator}')
    code = generator.read_text(encoding='utf-8')
    if 'from .presentation_quality import generate_presentation, PresentationQualityError' in code:
        print('PowerPoint route already installed. No changes.'); return
    if "'powerpoint': 'pptx'" not in code:
        raise SystemExit('PowerPoint format mapping missing; refusing installation')
    if 'from .structured_quality import generate_structured_file, StructuredQualityError' not in code:
        raise SystemExit('Stage 3 SQL/YAML quality routing not found; refusing installation')
    if code.count('    if fmt in TEXT_FORMATS:') != 1:
        raise SystemExit('Cannot safely locate generic text branch; refusing installation')
    if target.exists():
        raise SystemExit('presentation_quality.py already exists; refusing overwrite')
    patched = code.replace('    if fmt in TEXT_FORMATS:', BRANCH + '    if fmt in TEXT_FORMATS:', 1)
    ast.parse(patched)
    ast.parse(source.read_text(encoding='utf-8'))
    print('Compatible: only generator.py route and new presentation_quality.py are changed.')
    if not args.apply:
        print('Dry run only. Use --apply to install.'); return
    backup = generator.with_name('generator.py.before_stage4_powerpoint.bak')
    if backup.exists():
        raise SystemExit('Backup already exists; refusing overwrite')
    shutil.copy2(generator, backup)
    shutil.copy2(source, target)
    generator.write_text(patched, encoding='utf-8')
    print('Installed; backup:', backup)

if __name__ == '__main__':
    main()
