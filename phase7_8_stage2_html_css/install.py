"""Dry-run by default; installs separate HTML/CSS branch without changing TSX/JS path."""
import argparse
import ast
from pathlib import Path
import shutil

BRANCH = '''    if fmt in ('html', 'css'):
        from .markup_quality import generate_markup_file, MarkupQualityError
        try:
            output = generate_markup_file(prompt, provider, FORMAT_EXT[fmt])
        except MarkupQualityError as exc:
            raise ArtifactGenerationError(str(exc)) from exc
        return fmt, output.encode('utf-8')
'''

def main():
    p = argparse.ArgumentParser()
    p.add_argument('root', nargs='?', default='.')
    p.add_argument('--apply', action='store_true')
    a = p.parse_args()
    root = Path(a.root).resolve()
    generator = root / 'backend/artifacts/generator.py'
    module = root / 'backend/artifacts/markup_quality.py'
    source = Path(__file__).with_name('markup_quality.py')
    if not generator.is_file():
        raise SystemExit(f'Not found: {generator}')
    code = generator.read_text(encoding='utf-8')
    marker = '    if fmt in TEXT_FORMATS:'
    installed = 'from .markup_quality import generate_markup_file, MarkupQualityError' in code
    if installed:
        print('HTML/CSS branch already installed. Existing generation branches unchanged.')
        if a.apply and not module.exists():
            shutil.copy2(source, module)
            print('Restored missing markup_quality.py')
        return
    if code.count(marker) != 1:
        raise SystemExit(f'Expected one TEXT_FORMATS branch, found {code.count(marker)}; no files changed.')
    if "if fmt in ('typescript', 'javascript'):" not in code:
        raise SystemExit('Stage 1 TSX/JavaScript branch missing. No files changed.')
    # Ensure HTML and CSS are still part of FORMAT_EXT; don't modify format selection.
    if "'html': 'html'" not in code or "'css': 'css'" not in code:
        raise SystemExit('HTML/CSS format mappings missing. No files changed.')
    patched = code.replace(marker, BRANCH + marker, 1)
    ast.parse(patched)
    ast.parse(source.read_text(encoding='utf-8'))
    print('Compatible: HTML/CSS branch will be inserted before generic text generation.')
    print('JavaScript, TSX, Python and document branches will not be changed.')
    if not a.apply:
        print('Dry run only. Add --apply to install.')
        return
    backup = generator.with_name(generator.name + '.before_html_css_stage2.bak')
    if backup.exists():
        raise SystemExit('Existing backup found; review it before applying again. No changes made.')
    if module.exists():
        raise SystemExit('Existing markup_quality.py found; no changes made.')
    shutil.copy2(generator, backup)
    shutil.copy2(source, module)
    generator.write_text(patched, encoding='utf-8')
    print('Installed. Original generator backup:', backup)

if __name__ == '__main__':
    main()
