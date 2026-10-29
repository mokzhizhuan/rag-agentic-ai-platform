"""Conservative patch: add TSX/JS branch to generator.py; preserve other paths."""
from pathlib import Path
import argparse
import ast
import shutil


def main():
    p = argparse.ArgumentParser()
    p.add_argument('root', nargs='?', default='.')
    p.add_argument('--apply', action='store_true')
    args = p.parse_args()
    root = Path(args.root).resolve()
    target = root / 'backend/artifacts/generator.py'
    source = Path(__file__).with_name('code_quality.py')
    if not target.exists():
        raise SystemExit(f'Not found: {target}')
    old = target.read_text(encoding='utf-8')
    if "if fmt in ('typescript', 'javascript'):" in old and 'generate_frontend_code' in old:
        print('Already installed: skipping patch')
        return
    marker = '    if fmt in TEXT_FORMATS:'
    if old.count(marker) != 1:
        raise SystemExit(f'Expected exactly one {marker!r}; found {old.count(marker)}. No changes made.')
    insertion = '''    if fmt in ('typescript', 'javascript'):
        from .code_quality import generate_frontend_code, CodeQualityError
        try:
            output = generate_frontend_code(prompt, provider, FORMAT_EXT[fmt])
        except CodeQualityError as exc:
            raise ArtifactGenerationError(str(exc)) from exc
        return fmt, output.encode('utf-8')
'''
    new = old.replace(marker, insertion + marker)
    ast.parse(new)
    print('Compatible: code-quality branch can be inserted without modifying existing formats')
    if args.apply:
        backup = target.with_suffix('.py.before_phase7_8.bak')
        if not backup.exists():
            shutil.copy2(target, backup)
        shutil.copy2(source, root / 'backend/artifacts/code_quality.py')
        target.write_text(new, encoding='utf-8')
        print('Installed. Backup:', backup)


if __name__ == '__main__':
    main()
