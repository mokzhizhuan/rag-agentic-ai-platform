from pathlib import Path
import argparse, datetime, shutil, sys

START = '/* BEGIN PHASE8_1_CONTRAST_FIX */'
END = '/* END PHASE8_1_CONTRAST_FIX */'

p = argparse.ArgumentParser(description='Add dark-mode contrast overrides to Phase 8.1 CSS')
p.add_argument('project', nargs='?', default='.')
p.add_argument('--apply', action='store_true')
args = p.parse_args()
target = Path(args.project).resolve() / 'frontend' / 'src' / 'phase8-shell.css'
source = Path(__file__).with_name('contrast-fix.css')
if not target.is_file():
    sys.exit('ERROR: Cannot find frontend/src/phase8-shell.css; install Phase 8.1 first.')
old = target.read_text(encoding='utf-8')
if START in old or END in old:
    sys.exit('Already applied; no changes made.')
print('Target:', target)
print('Change: append readability overrides only; no App.tsx changes.')
if not args.apply:
    print('DRY RUN: no changes made. Run again with --apply.')
else:
    backup = target.with_name(target.name + '.' + datetime.datetime.now().strftime('%Y%m%d-%H%M%S') + '.bak')
    shutil.copy2(target, backup)
    target.write_text(old.rstrip() + '\n\n' + START + '\n' + source.read_text(encoding='utf-8').rstrip() + '\n' + END + '\n', encoding='utf-8')
    print('Applied. Backup:', backup)
