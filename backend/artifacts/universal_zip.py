"""Phase 7.9: bounded, universal multi-file project generation.

No generated code is executed, and generated files cannot escape their ZIP root.
"""
from __future__ import annotations
import ast
import io
import json
import os
import posixpath
import re
import zipfile
from pathlib import PurePosixPath
from typing import Callable
from chat.providers import stream_generate

class UniversalZipError(ValueError):
    pass

MAX_FILES = 35
MAX_FILE_BYTES = 110_000
MAX_TOTAL_BYTES = 1_500_000
MAX_PLAN_CHARS = 30000
ALLOWED_EXT = {'.py','.js','.jsx','.ts','.tsx','.html','.htm','.css','.scss','.json','.yaml','.yml','.sql','.md','.txt','.toml','.ini','.cfg','.env','.sh','.ps1','.bat','.xml','.svg','.csv','.gitignore','.dockerignore'}
ALLOWED_BASENAMES = {'Dockerfile','Makefile','LICENSE','README','requirements.txt','Procfile','.env.example','.gitignore','.dockerignore'}
SECRET_PAT = re.compile(r'(?i)(?:sk-[A-Za-z0-9_-]{20,}|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----|AKIA[0-9A-Z]{16})')


def _ask(query: str, provider: str, system: str, limit: int) -> str:
    chunks, total = [], 0
    for piece in stream_generate(query, [], [], provider, system_override=system):
        total += len(piece)
        if total > limit:
            raise UniversalZipError(f'AI output exceeded {limit} characters')
        chunks.append(piece)
    output = ''.join(chunks).strip()
    if not output:
        raise UniversalZipError('AI returned empty output')
    return output


def _json(raw: str):
    raw = raw.strip()
    if raw.startswith('```'):
        raw = re.sub(r'^```(?:json)?\s*|\s*```$', '', raw, flags=re.I).strip()
    try:
        return json.loads(raw)
    except (ValueError, TypeError) as exc:
        raise UniversalZipError('AI project plan was not valid JSON') from exc


def _safe_path(raw: str) -> str:
    if not isinstance(raw, str) or not raw or len(raw)>180 or '\\' in raw or '\x00' in raw:
        raise UniversalZipError(f'Invalid project path: {str(raw)[:70]}')
    path = PurePosixPath(raw)
    if (path.is_absolute() or len(path.parts)>9 or any(p in ('', '.', '..') or p.startswith('~') for p in raw.split('/'))
        or re.match(r'^[a-zA-Z]:', raw) or ':' in raw or any(ord(c)<32 for c in raw)):
        raise UniversalZipError(f'Unsafe project path: {raw}')
    if path.suffix.lower() not in ALLOWED_EXT and path.name not in ALLOWED_BASENAMES:
        raise UniversalZipError(f'Unsupported project file: {raw}')
    if path.name == '.env' or path.name.endswith(('.pem','.key','.p12','.pfx')):
        raise UniversalZipError(f'Credentials/private keys must not be packaged: {raw}')
    return str(path)


def validate_plan(plan):
    if not isinstance(plan, dict) or not isinstance(plan.get('files'), list):
        raise UniversalZipError('Plan needs a files array')
    raw_files = plan['files']
    if not 2 <= len(raw_files) <= MAX_FILES:
        raise UniversalZipError(f'Project must have 2–{MAX_FILES} files')
    files, names = [], set()
    for obj in raw_files:
        if not isinstance(obj, dict):
            raise UniversalZipError('File-plan item must be an object')
        name = _safe_path(obj.get('path'))
        if name.casefold() in names:
            raise UniversalZipError(f'Duplicate path: {name}')
        names.add(name.casefold())
        purpose = str(obj.get('purpose','')).strip()[:200]
        if not purpose:
            raise UniversalZipError(f'Missing file purpose: {name}')
        dependencies = obj.get('depends_on', [])
        if not isinstance(dependencies, list) or len(dependencies)>MAX_FILES:
            raise UniversalZipError(f'Invalid dependencies: {name}')
        files.append({'path':name, 'purpose':purpose,'depends_on':dependencies})
    paths = {f['path'] for f in files}
    for f in files:
        checked=[]
        for dep in f['depends_on']:
            dep = _safe_path(dep)
            if dep not in paths or dep == f['path']:
                raise UniversalZipError(f'Unknown/self dependency {dep} in {f["path"]}')
            checked.append(dep)
        f['depends_on']=checked
    # "depends_on" is a generation-order hint, not a runtime import graph.
    # HTML referencing app.js, while app.js references HTML element IDs, is a
    # valid project but forms a circular *planning* relationship. Keep shared
    # contracts, remove only back-edges for generation ordering, and record it.
    ordered, visited, visiting, breaks = [], set(), set(), []
    bypath={f['path']: f for f in files}

    def visit(path):
        if path in visited:
            return
        visiting.add(path)
        file = bypath[path]
        kept = []
        for dependency in file['depends_on']:
            if dependency in visiting:
                breaks.append({'file': path, 'dependency': dependency})
                continue
            visit(dependency)
            kept.append(dependency)
        file['depends_on'] = kept
        visiting.remove(path)
        visited.add(path)
        ordered.append(file)

    for f in files:
        visit(f['path'])
    contracts = plan.get('contracts', [])
    if not isinstance(contracts,list): contracts=[]
    return {'name': str(plan.get('name','Generated project'))[:85],
            'contracts': [str(c)[:240] for c in contracts[:20]],
            'files': ordered, 'generation_cycle_breaks': breaks}


def _sanity_content(path: str, content: str):
    if not isinstance(content,str) or not content.strip():
        raise UniversalZipError(f'Empty file: {path}')
    raw=content.encode('utf-8')
    if len(raw)>MAX_FILE_BYTES:
        raise UniversalZipError(f'File too large: {path}')
    if SECRET_PAT.search(content):
        raise UniversalZipError(f'Potential credential/private key in {path}; use environment placeholders')
    ext=PurePosixPath(path).suffix.lower()
    if ext=='.py':
        try: ast.parse(content)
        except SyntaxError as e: raise UniversalZipError(f'{path}: Python syntax line {e.lineno}: {e.msg}') from e
    if ext=='.json':
        try: json.loads(content)
        except ValueError as e: raise UniversalZipError(f'{path}: invalid JSON: {str(e)[:100]}') from e
    if ext in {'.yaml','.yml'}:
        try:
            from .structured_quality import validate_yaml
            validate_yaml(content)
        except ImportError:
            try:
                import yaml
                yaml.safe_load(content)
            except ImportError:
                raise UniversalZipError('PyYAML required for YAML validation')
            except Exception as e: raise UniversalZipError(f'{path}: YAML invalid: {e}') from e
    if ext=='.sql':
        try:
            from .structured_quality import validate_sql
            validate_sql(content)
        except ImportError:
            raise UniversalZipError('Stage 3 structured_quality.py required for SQL validation')
    if ext in {'.js','.tsx'}:
        try:
            from .code_quality import _parse_source
            _parse_source(content, ext)
        except ImportError:
            raise UniversalZipError('Stage 1 code_quality.py required for JS/TSX validation')
    if ext in {'.html','.css'}:
        try:
            from .markup_quality import validate_html, validate_css
            (validate_html if ext=='.html' else validate_css)(content)
        except ImportError:
            # HTML/CSS checker names depend on Stage 2 version; avoid assuming validation succeeded.
            pass


def _strip_fence(raw):
    m=re.fullmatch(r'```[^\n]*\n([\s\S]*?)\n```',raw.strip())
    return (m.group(1) if m else raw).rstrip()+'\n'


def _candidate_paths(current: str, ref: str):
    if not ref.startswith('.') or ref.startswith(('..\\','.\\')): return []
    base=posixpath.dirname(current)
    target=posixpath.normpath(posixpath.join(base,ref))
    if target.startswith('../') or target=='..': return []
    return [target]+[target+e for e in ('.js','.jsx','.ts','.tsx','.json','.css','.py')]+[posixpath.join(target,'index'+e) for e in ('.js','.jsx','.ts','.tsx')]


def cross_file_issues(files: dict[str,str], prompt: str = ""):
    """Check local JS/TSX imports, HTML asset refs and Docker compose local build paths.

    Not a full compiler; no network calls or code execution.
    """
    issues=[]
    paths=set(files)
    for name,source in files.items():
        ext=PurePosixPath(name).suffix.lower()
        if ext in {'.js','.jsx','.ts','.tsx'}:
            refs=re.findall(r'''(?:\bfrom\s*|\bimport\s*\(|\brequire\s*\()\s*['"](\.[^'"]+)['"]''',source)
            refs+=re.findall(r'''\bimport\s*['"](\.[^'"]+)['"]''',source)
            for ref in refs:
                if not any(p in paths for p in _candidate_paths(name,ref)):
                    issues.append(f'{name}: unresolved local import {ref}')
        elif ext in {'.html','.htm'}:
            refs=re.findall(r'''\b(?:src|href)\s*=\s*['"](\.[^'"?#]+)['"]''',source)
            for ref in refs:
                if not any(p in paths for p in _candidate_paths(name,ref)):
                    issues.append(f'{name}: unresolved relative asset {ref}')
        elif PurePosixPath(name).name.lower() in ('docker-compose.yml','compose.yaml','compose.yml'):
            for context in re.findall(r'(?m)^\s*context:\s*(\./[A-Za-z0-9_./-]+)\s*$',source):
                target=posixpath.normpath(posixpath.join(posixpath.dirname(name),context))
                if not any(p.startswith(target.rstrip('/')+'/') for p in paths):
                    issues.append(f'{name}: missing build context directory {context}')
    from .functional_quality import inspect_project
    functional_errors, _ = inspect_project(files, prompt)
    issues.extend(functional_errors)
    return sorted(set(issues))


def package_zip(files: dict[str,str], manifest: dict) -> bytes:
    if not 2 <= len(files) <= MAX_FILES+2:
        raise UniversalZipError('Invalid file count')
    if sum(len(v.encode('utf-8')) for v in files.values()) > MAX_TOTAL_BYTES:
        raise UniversalZipError('Project exceeds total size limit')
    dest=io.BytesIO()
    with zipfile.ZipFile(dest,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=7) as z:
        for path in sorted(files):
            _safe_path(path)
            data=files[path].encode('utf-8')
            info=zipfile.ZipInfo(path, date_time=(2026,1,1,0,0,0))
            info.compress_type=zipfile.ZIP_DEFLATED
            info.external_attr=(0o100644 << 16)
            z.writestr(info,data)
    blob=dest.getvalue()
    with zipfile.ZipFile(io.BytesIO(blob)) as z:
        if z.testzip() is not None or len(z.namelist())!=len(files):
            raise UniversalZipError('ZIP integrity check failed')
    return blob


def generate_universal_zip(prompt: str, provider: str, progress: Callable[[str,int],None]|None=None) -> bytes:
    if not isinstance(prompt,str) or not 10 <= len(prompt) <= 20000:
        raise UniversalZipError('Project request must be 10–20000 characters')
    def status(message, percent):
        if progress: progress(message,percent)
    status('Planning multi-file project',5)
    schema='''Return ONLY JSON: {"name":"project name","contracts":["shared API/interface/config fact"],"files":[{"path":"relative/file.ext","purpose":"precise purpose","depends_on":["other/file.ext"]}]}. Plan 2-35 text/source/config files, with explicit cross-file contracts (API routes, JSON fields, ports, env names, dependencies), Use depends_on only for files that must be generated first; runtime imports/assets may be cyclic and will be validated after generation. Choose any technology requested, not just React. Include README.md and .env.example where appropriate. Use only relative POSIX paths, never secrets, binaries or generated lockfiles. Keep total project focused and feasible; each file should be reasonably short. Never claim tests run.'''
    plan=None
    for attempt in range(3):
        try:
            raw=_ask(f'USER REQUEST:\n{prompt}\n\nPROJECT PLAN RULES:\n{schema}',provider,'You design compact, internally consistent project structures. Output valid JSON only.',MAX_PLAN_CHARS)
            plan=validate_plan(_json(raw)); break
        except UniversalZipError:
            if attempt==2: raise
    generated={}
    overview=json.dumps({'name':plan['name'],'contracts':plan['contracts'], 'files':plan['files']},ensure_ascii=False)
    for index,file in enumerate(plan['files']):
        path=file['path']
        status(f'Generating {index+1}/{len(plan["files"])}: {path}',10+int(72*index/len(plan['files'])))
        deps='\n'.join(f'--- {p} ---\n{generated[p][:8500]}' for p in file['depends_on'] if p in generated)
        error=None
        for attempt in range(3):
            query=(f'PROJECT REQUEST:\n{prompt}\nPROJECT PLAN:\n{overview[:15000]}\nFILE TO WRITE: {path}\nPURPOSE: {file["purpose"]}\n'
                   f'GENERATED DEPENDENCIES:\n{deps[:19000]}\n'
                   'Write ONE complete file only. Follow project contracts, imports, filenames, API fields, ports and env vars exactly. '
                   'No markdown fences, explanations, fake secrets, incomplete TODO code or extra files. '
                   'Use placeholder values for unavailable real information.\n'
                   +(f'PREVIOUS VALIDATION ERROR: {error}\nRepair and output the WHOLE FILE.\n' if error else ''))
            raw=_ask(query,provider,'You implement correct single-file source code/configurations. Never add markdown fences. Never execute code.',MAX_FILE_BYTES+2000)
            source=_strip_fence(raw)
            try:
                _sanity_content(path,source)
                generated[path]=source
                break
            except (UniversalZipError, ValueError) as e:
                error=str(e)[:400]
        else:
            raise UniversalZipError(f'Unable to validate {path}: {error}')
        if sum(len(v.encode('utf-8')) for v in generated.values())>MAX_TOTAL_BYTES:
            raise UniversalZipError('Project exceeds archive size limit')
    status('Checking cross-file references',88)
    issues=cross_file_issues(generated, prompt)
    # Repair offending files with explicit reference problems, maximum two passes.
    for pass_no in range(2):
        if not issues: break
        affected={line.split(': ',1)[0] for line in issues}
        for path in affected:
            detail='\n'.join(x for x in issues if x.startswith(path+': '))
            raw=_ask(f'Fix this file for cross-file consistency. Return the COMPLETE corrected file only, no fences.\n'
                     f'FILE: {path}\nERRORS: {detail}\nAVAILABLE PATHS: {list(generated)}\n'
                     f'CONTRACTS: {plan["contracts"]}\nCURRENT CONTENT:\n{generated[path]}',provider,
                     'Repair references only using existing paths and interfaces. Never invent extra files.',MAX_FILE_BYTES+2000)
            source=_strip_fence(raw)
            _sanity_content(path,source)
            generated[path]=source
        issues=cross_file_issues(generated, prompt)
    if issues:
        raise UniversalZipError('Unresolved cross-file references: '+'; '.join(issues[:8]))
    from .functional_quality import inspect_project
    _, advisories = inspect_project(generated, prompt)
    manifest={'generator':'Phase 7.9 V2 Universal ZIP','project':plan['name'],'contracts':plan['contracts'],
              'files':[{'path':f['path'],'purpose':f['purpose'],'depends_on':f['depends_on']} for f in plan['files']],
              'validation':'Static checks only; not compiled or executed. Review before deployment.',
              'validation_advisories':advisories,
              'generation_cycle_breaks':plan.get('generation_cycle_breaks', [])}
    # Include machine-readable inventory; no credentials or generated files outside project.
    generated['project-manifest.json']=json.dumps(manifest,indent=2,ensure_ascii=False)+'\n'
    status('Packaging ZIP and checking integrity',96)
    blob=package_zip(generated,manifest)
    status('ZIP project complete',100)
    return blob
