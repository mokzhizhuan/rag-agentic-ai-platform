"""Phase 8.3 frontend-only installer, tolerant of customized page headings.
Dry run unless --apply. Only adds page classes and the studios stylesheet.
"""
from pathlib import Path
from datetime import datetime
import argparse
import re
import shutil

parser = argparse.ArgumentParser()
parser.add_argument('project_root', nargs='?', default='.')
parser.add_argument('--apply', action='store_true')
args = parser.parse_args()
root = Path(args.project_root).resolve()
app = root / 'frontend/src/App.tsx'
css = root / 'frontend/src/phase8-studios.css'
src = Path(__file__).with_name('phase8-studios.css')
if not app.is_file() or not (root/'frontend/src/phase8-shell.css').is_file():
    raise SystemExit('Missing Phase 8 frontend App.tsx or shell stylesheet.')
s = app.read_text(encoding='utf-8')
if "import './phase8-shell.css';" not in s:
    raise SystemExit('Phase 8 shell import missing; no files changed.')

# Match by functional content/branch, never by the user-visible heading text.
create_anchor = "tab==='create'?<section"
if create_anchor not in s and 'tab===\'create\'?<section className="artifact-studio"' not in s:
    raise SystemExit('Cannot locate Create Files tab section; no files changed.')
updated = s.replace(create_anchor+'>', create_anchor+' className="artifact-studio">', 1)

# Knowledge Base section is recognized by its upload control, regardless of
# whether its title is "Phase 2 · Knowledge Base", "Knowledge Base", etc.
pattern = re.compile(r'(<section)(\s*>)\s*(<h2>[^<]*</h2>\s*<article>\s*<h3>Upload knowledge document</h3>)')
if '<section className="knowledge-studio">' not in updated:
    matches=list(pattern.finditer(updated))
    if len(matches) != 1:
        raise SystemExit(f'Expected one Knowledge Base upload section; found {len(matches)}; no files changed.')
    updated=pattern.sub(lambda m:'<section className="knowledge-studio">'+m.group(3),updated,count=1)

imp="import './phase8-studios.css';"
if imp not in updated:
    updated=updated.replace("import './phase8-shell.css';", "import './phase8-shell.css';\n"+imp,1)
if updated==s and css.is_file() and css.read_bytes()==src.read_bytes():
    print('Already installed.');raise SystemExit(0)
print('Targets:',app,css)
print('App source will change:',updated != s)
if not args.apply:
    print('Dry run OK; use --apply to install.');raise SystemExit(0)
stamp=datetime.now().strftime('%Y%m%d-%H%M%S')
shutil.copy2(app,app.with_name(app.name+'.bak-'+stamp))
if css.is_file():
    shutil.copy2(css,css.with_name(css.name+'.bak-'+stamp))
app.write_text(updated,encoding='utf-8')
shutil.copy2(src,css)
print('Installed Phase 8.3. Custom headings, chat and backend functions preserved.')
