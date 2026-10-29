"""Phase 7.9 V2: conservative, static cross-file functional checks.

Never executes generated project code. Returns actionable hard errors and advisory warnings.
"""
from __future__ import annotations
import ast
import posixpath
import re
from pathlib import PurePosixPath

_JS_ID = re.compile(r'''(?:document\.)?getElementById\s*\(\s*['"]([^'"\n]+)['"]\s*\)|(?:document\.)?querySelector(?:All)?\s*\(\s*['"]#([\w-]+)['"]\s*\)''')
_HTML_ID = re.compile(r'''\bid\s*=\s*['"]([^'"]+)['"]''', re.I)
_HTML_JS = re.compile(r'''<script\b[^>]*\bsrc\s*=\s*['"]([^'"]+)['"]''', re.I)
_ENV = re.compile(r'''\$\{([A-Za-z_][A-Za-z0-9_]*)(?:(?::[-?])[^}]*)?\}''')
_LOCAL_PY = re.compile(r'''(?m)^\s*(?:from\s+(\.[\w.]*)\s+import|import\s+(\w+(?:\.\w+)*))''')


def _linked_js(html_path, html, files):
    basedir=posixpath.dirname(html_path)
    paths=[]
    for src in _HTML_JS.findall(html):
        if src.startswith(('http:', 'https:', '//')): continue
        name=posixpath.normpath(posixpath.join(basedir,src.split('?',1)[0].split('#',1)[0]))
        if name in files: paths.append(name)
    return paths


def inspect_project(files: dict[str,str], prompt: str = '') -> tuple[list[str],list[str]]:
    """Return (repairable_errors, advisories). Only actionable high-confidence errors block output."""
    errors=[]; warnings=[]
    all_html={p:s for p,s in files.items() if p.lower().endswith(('.html','.htm'))}
    all_js={p:s for p,s in files.items() if p.lower().endswith(('.js','.jsx','.ts','.tsx'))}
    for html_path, html in all_html.items():
        ids=set(_HTML_ID.findall(html))
        for js_path in _linked_js(html_path,html,files):
            source=files[js_path]
            for groups in _JS_ID.findall(source):
                element_id=groups[0] or groups[1]
                if element_id not in ids:
                    errors.append(f'{js_path}: DOM element ID "{element_id}" missing from linked {html_path}')
        # A page containing explicit forms/filters but no script is static, not inherently invalid.
        if re.search(r'<(?:input|select)\b',html,re.I) and not re.search(r'<script\b',html,re.I):
            warnings.append(f'{html_path}: form controls have no script; verify whether functionality is intended')
    for path,source in files.items():
        if path.endswith('.py'):
            try: root=ast.parse(source)
            except SyntaxError: continue # V1 parser handles this
            # csv.DictReader stores overflow columns under key None, not in row values only.
            if 'DictReader' in source and re.search(r'''(?:len\s*\(\s*(?:row|record)\.values\s*\(\s*\)\s*\)|(?:row|record)\.values\s*\(\s*\))''',source) and 'None in row' not in source and 'None in record' not in source and 'restkey=' not in source:
                errors.append(f'{path}: CSV extra-column validation may overlook DictReader overflow under key None; check None in row / record or set restkey')
            # Import checks only explicit relative Python imports, not installed packages.
            for node in ast.walk(root):
                if isinstance(node,ast.ImportFrom) and node.level and node.module:
                    base=posixpath.dirname(path)
                    for _ in range(node.level-1):base=posixpath.dirname(base)
                    target=posixpath.normpath(posixpath.join(base,node.module.replace('.','/')))
                    if not any(p in files for p in (target+'.py',target+'/__init__.py')):
                        errors.append(f'{path}: unresolved Python relative import {"."*node.level}{node.module}')
        if PurePosixPath(path).name in ('docker-compose.yml','compose.yml','compose.yaml'):
            # Missing .env is advisory: env variables may be intentionally supplied at runtime.
            envnames=set(_ENV.findall(source))
            examples=[v for k,v in files.items() if PurePosixPath(k).name=='.env.example']
            if examples:
                declared=set()
                for ex in examples:
                    declared.update(re.findall(r'(?m)^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=',ex))
                for env in sorted(envnames-declared):
                    warnings.append(f'{path}: environment variable {env} is absent from .env.example (may be supplied externally)')
            # Check common Vite vs CRA mismatch, only when Vite is explicitly confirmed.
            pkg=[v for k,v in files.items() if PurePosixPath(k).name=='package.json']
            if any('"vite"' in x for x in pkg) and 'REACT_APP_' in source:
                warnings.append(f'{path}: REACT_APP_* variables in a Vite project usually need VITE_* plus matching usage')
    return sorted(set(errors)),sorted(set(warnings))
