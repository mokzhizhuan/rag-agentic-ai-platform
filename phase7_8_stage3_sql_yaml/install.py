"""Stage 3 additive installer. Dry-run by default. Does not replace existing quality modules."""
import argparse
import ast
from pathlib import Path
import shutil

BRANCH = '''    if fmt in ('sql', 'yaml', 'yml'):
        from .structured_quality import generate_structured_file, StructuredQualityError
        try:
            output = generate_structured_file(prompt, provider, FORMAT_EXT[fmt])
        except StructuredQualityError as exc:
            raise ArtifactGenerationError(str(exc)) from exc
        return fmt, output.encode('utf-8')
'''


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('root', nargs='?', default='.')
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    root = Path(args.root).resolve()
    generator = root / 'backend/artifacts/generator.py'
    new_module = root / 'backend/artifacts/structured_quality.py'
    source = Path(__file__).with_name('structured_quality.py')
    if not generator.is_file():
        raise SystemExit(f'Generator missing: {generator}')
    code = generator.read_text(encoding='utf-8')
    if 'from .structured_quality import generate_structured_file, StructuredQualityError' in code:
        print('Stage 3 branch already installed; no files changed.')
        return
    marker = '    if fmt in TEXT_FORMATS:'
    if code.count(marker) != 1:
        raise SystemExit('Expected exactly one TEXT_FORMATS branch; aborting without changes.')
    if 'from .markup_quality import generate_markup_file, MarkupQualityError' not in code:
        raise SystemExit('Stage 2 HTML/CSS branch not found. No files changed.')
    if 'from .code_quality import' not in code:
        raise SystemExit('Stage 1 JS/TSX quality branch not found. No files changed.')
    if "'sql': 'sql'" not in code:
        raise SystemExit('SQL file extension mapping missing; no files changed.')
    # YAML may be mapped as 'yaml' or 'yml' depending on project.
    if not any(f"'{x}': '{y}'" in code for x,y in [('yaml','yaml'),('yaml','yml'),('yml','yml'),('yml','yaml')]):
        raise SystemExit('YAML file extension mapping missing; no files changed. Add mapping manually after review.')
    patched = code.replace(marker, BRANCH + marker, 1)
    ast.parse(patched)
    ast.parse(source.read_text(encoding='utf-8'))
    print('Compatible: additive SQL/YAML branch, before generic text generation.')
    print('JS/TSX, HTML/CSS and document generation remain unchanged.')
    if not args.apply:
        print('Dry run only; pass --apply to install.')
        return
    if new_module.exists():
        raise SystemExit('structured_quality.py exists; refusing overwrite.')
    backup = generator.with_name('generator.py.before_stage3_sql_yaml.bak')
    if backup.exists():
        raise SystemExit(f'Backup exists: {backup}; refusing overwrite.')
    shutil.copy2(generator, backup)
    shutil.copy2(source, new_module)
    generator.write_text(patched, encoding='utf-8')
    print('Installed Stage 3. Backup:', backup)

if __name__ == '__main__':
    main()
