"""Safe Phase 8.2 stylesheet installer; dry-run by default."""
from pathlib import Path
import argparse
import shutil
from datetime import datetime

p = argparse.ArgumentParser()
p.add_argument('project_root', nargs='?', default='.')
p.add_argument('--apply', action='store_true')
a = p.parse_args()
root = Path(a.project_root).resolve()
app = root / 'frontend/src/App.tsx'
css = root / 'frontend/src/phase8-agentic.css'
source = Path(__file__).with_name('phase8-agentic.css')
if not app.is_file() or not (root/'frontend/src/phase8-shell.css').is_file():
    raise SystemExit('Incompatible project: expected frontend/src/App.tsx and phase8-shell.css')
s = app.read_text(encoding='utf-8')
if "import './phase8-shell.css';" not in s or 'className="chat-layout"' not in s:
    raise SystemExit('Incompatible App.tsx: Phase 8.1 import/chat-layout anchors missing')
import_line = "import './phase8-agentic.css';"
if import_line in s and css.exists() and css.read_bytes() == source.read_bytes():
    print('Already installed — no changes.'); raise SystemExit(0)
print('Target:', app, 'and', css)
if not a.apply:
    print('Dry run OK. Use --apply to install.'); raise SystemExit(0)
stamp = datetime.now().strftime('%Y%m%d-%H%M%S')
shutil.copy2(app,app.with_name(app.name+'.bak-'+stamp))
if css.exists():
    shutil.copy2(css,css.with_name(css.name+'.bak-'+stamp))
if import_line not in s:
    s = s.replace("import './phase8-shell.css';", "import './phase8-shell.css';\n"+import_line,1)
    app.write_text(s,encoding='utf-8')
shutil.copy2(source,css)
print('Installed Phase 8.2. Existing chat functions unchanged.')
