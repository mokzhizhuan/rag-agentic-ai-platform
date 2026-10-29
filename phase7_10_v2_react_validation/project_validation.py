"""Phase 7.10 opt-in, no-execution validation of untrusted generated ZIP projects.

This module does not extract the ZIP, execute project code, install packages,
connect to databases, or run browser tests. Reports are advisory and bounded.
"""
from __future__ import annotations
import ast
import csv
import hashlib
import io
import json
import posixpath
import re
import zipfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import PurePosixPath

MAX_FILES = 200
MAX_FILE_SIZE = 1_000_000
MAX_TOTAL_SIZE = 10_000_000
MAX_ZIP_SIZE = 12_000_000
SECRET = re.compile(r'(?i)(?:sk-[A-Za-z0-9_-]{20,}|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----|AKIA[0-9A-Z]{16})')
JS_IMPORT = re.compile(r'''(?:\bfrom\s*|\bimport\s*\(|\brequire\s*\()\s*['"](\.[^'"\s]+)['"]''')
HTML_ASSET = re.compile(r'''\b(?:src|href)\s*=\s*['"]([^'"#?]+)''', re.I)
DOM_ID = re.compile(r'''\bgetElementById\s*\(\s*['"]([^'"]+)['"]''')
HTML_ID = re.compile(r'''\bid\s*=\s*['"]([^'"]+)['"]''', re.I)
ENV_REF = re.compile(r'\$\{([A-Za-z_][A-Za-z_0-9]*)(?::?[-?][^}]*)?\}')


def inspect_zip_bytes(blob: bytes) -> dict:
    findings = []
    def add(level, rule, path, detail):
        findings.append({'severity': level, 'rule': rule, 'file': path, 'message': detail})
    if len(blob) > MAX_ZIP_SIZE:
        raise ValueError('ZIP exceeds validation download size limit (12 MB)')
    sources = {}
    try:
        z = zipfile.ZipFile(io.BytesIO(blob))
    except (zipfile.BadZipFile, OSError) as e:
        raise ValueError('Invalid ZIP archive') from e
    with z:
        info = z.infolist()
        if len(info) > MAX_FILES:
            raise ValueError(f'ZIP has more than {MAX_FILES} entries')
        total = 0
        for member in info:
            if member.is_dir():
                continue
            name = member.filename
            p = PurePosixPath(name)
            if (not name or '\\' in name or p.is_absolute() or '..' in p.parts or ':' in name
                or any(ord(c)<32 for c in name) or len(name)>200):
                add('error','unsafe_archive_path',name[:180],'Archive path is unsafe or malformed')
                continue
            if name in sources:
                add('error','duplicate_archive_path',name,'Duplicate archive entry')
                continue
            mode = (member.external_attr >> 16) & 0o170000
            if mode == 0o120000:
                add('error','archive_symlink',name,'Symlink entries are not allowed')
                continue
            if member.flag_bits & 1:
                add('error','encrypted_entry',name,'Encrypted entries cannot be validated')
                continue
            if member.file_size > MAX_FILE_SIZE:
                add('error','file_size_limit',name,'File is too large for optional validation')
                continue
            total += member.file_size
            if total > MAX_TOTAL_SIZE:
                raise ValueError('ZIP uncompressed contents exceed 10 MB safety limit')
            try:
                data = z.read(member)
            except (OSError, RuntimeError, zipfile.BadZipFile):
                add('error','corrupt_entry',name,'Unable to read ZIP entry')
                continue
            try:
                decoded = data.decode('utf-8')
            except UnicodeDecodeError:
                decoded = None
                add('info','binary_not_parsed',name,'Binary file not analyzed as source text')
            sources[name] = decoded
    names = set(sources)
    manifest = None
    for name, src in sources.items():
        suffix = PurePosixPath(name).suffix.lower()
        if src is None:
            continue
        if SECRET.search(src):
            add('error','possible_secret',name,'Credential or private-key pattern detected; review before sharing')
        if suffix == '.py':
            try: ast.parse(src)
            except SyntaxError as e:
                add('error','python_syntax',name,f'Line {e.lineno}: {e.msg}')
        if suffix == '.json':
            try:
                parsed = json.loads(src)
                if PurePosixPath(name).name == 'project-manifest.json': manifest = parsed
            except ValueError as e: add('error','json_syntax',name,str(e)[:180])
        if suffix in ('.yaml','.yml'):
            try:
                import yaml
                yaml.safe_load(src)
            except ImportError:
                add('info','yaml_parser_unavailable',name,'Install PyYAML for YAML parsing')
            except Exception as e: add('error','yaml_syntax',name,str(e)[:180])
        if suffix == '.csv':
            try:
                rows = list(csv.reader(io.StringIO(src)))
                if rows and any(len(row)!=len(rows[0]) for row in rows[1:]):
                    add('warning','csv_row_columns',name,'CSV rows have inconsistent column counts')
            except csv.Error as e: add('error','csv_parse',name,str(e))
        if suffix in ('.js','.jsx','.ts','.tsx'):
            for ref in JS_IMPORT.findall(src):
                _validate_reference(name,ref,names,add,'missing_local_import')
            for identifier in DOM_ID.findall(src):
                # Check only if there is an HTML file in the project; IDs may be dynamically created.
                htmls = [v for n,v in sources.items() if n.endswith(('.html','.htm')) and v is not None]
                if htmls and not any(identifier in HTML_ID.findall(h) for h in htmls):
                    add('warning','missing_dom_id',name,f'getElementById("{identifier}") not found in static HTML (may be dynamic)')
        if suffix in ('.html','.htm'):
            for asset in HTML_ASSET.findall(src):
                if asset.startswith(('http:','https:','data:','mailto:','tel:','//','/')): continue
                _validate_reference(name,asset,names,add,'missing_html_asset', allow_bare=True)
        if PurePosixPath(name).name in ('docker-compose.yml','compose.yml','compose.yaml'):
            for context in re.findall(r'(?m)^\s*context:\s*["\']?(\./[A-Za-z0-9./_-]+)',src):
                base = posixpath.dirname(name)
                target = posixpath.normpath(posixpath.join(base,context)).rstrip('/')+'/'
                if not any(n.startswith(target) for n in names):
                    add('warning','compose_build_context',name,f'Build context {context} has no packaged files')
            envvars = set(ENV_REF.findall(src))
            example = '\n'.join(v or '' for n,v in sources.items() if PurePosixPath(n).name == '.env.example')
            declared = set(re.findall(r'(?m)^\s*([A-Za-z_][A-Za-z_0-9]*)\s*=',example))
            for var in sorted(envvars-declared):
                add('warning','env_example_missing',name,f'{var} is referenced but not in .env.example')
    if not manifest:
        add('info','manifest_missing','','No valid project-manifest.json found')
    if not any(PurePosixPath(n).name.lower().startswith('readme') for n in names):
        add('warning','readme_missing','','No README documentation found')
    counts = dict(Counter(x['severity'] for x in findings))
    return {
        'schema_version': '7.10.1',
        'mode': 'static_only_no_execution',
        'generated_utc': datetime.now(timezone.utc).isoformat(timespec='seconds'),
        'archive_sha256': hashlib.sha256(blob).hexdigest(),
        'files_analyzed': len(sources),
        'files': sorted(sources),
        'summary': {k:counts.get(k,0) for k in ('error','warning','info')},
        'findings': findings,
        'limitations': [
            'This is static analysis; generated application code is never executed.',
            'No browser rendering, package installation, database connections, or deployment are performed.',
            'Local reference checks and configuration warnings can produce false positives.',
            'Passing checks does not imply runtime correctness, security, or production readiness.'
        ],
    }


def _validate_reference(name, ref, names, add, rule, allow_bare=False):
    ref = ref.split('?',1)[0].split('#',1)[0]
    if not ref or (not allow_bare and not ref.startswith('.')): return
    resolved = posixpath.normpath(posixpath.join(posixpath.dirname(name), ref))
    candidates = [resolved]+[resolved+ext for ext in ('.js','.jsx','.ts','.tsx','.json','.css','.py','.html')]
    candidates += [posixpath.join(resolved,'index'+ext) for ext in ('.js','.jsx','.ts','.tsx')]
    if not any(c in names for c in candidates):
        add('warning',rule,name,f'Relative reference {ref} was not found in ZIP')


def markdown_report(report: dict) -> str:
    s = report['summary']
    rows = ['# Phase 7.10 — ZIP Project Validation Report','',
            f'**Mode:** Static checks only (no execution)',
            f'**Files analyzed:** {report["files_analyzed"]}',
            f'**Errors:** {s["error"]}  |  **Warnings:** {s["warning"]}  |  **Info:** {s["info"]}',
            f'**SHA-256:** `{report["archive_sha256"]}`','', '## Findings','']
    if not report['findings']:
        rows.append('No findings from the implemented static checks.')
    for x in report['findings']:
        rows.append(f'- **{x["severity"].upper()}** `{x["rule"]}` in `{x["file"] or "(project)"}`: {x["message"]}')
    rows += ['', '## Limitations','']+[f'- {x}' for x in report['limitations']]
    return '\n'.join(rows)+'\n'
