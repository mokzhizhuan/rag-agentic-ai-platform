"""Staged single-file React/TSX and JavaScript generation, no execution.

Requires tree-sitter, tree-sitter-javascript, tree-sitter-typescript.
"""
from __future__ import annotations

import json
import re
from typing import Callable

from chat.providers import stream_generate


class CodeQualityError(ValueError):
    pass


def _ask(prompt: str, provider: str, *, system: str, limit: int = 18000) -> str:
    parts: list[str] = []
    size = 0
    for item in stream_generate(prompt, [], [], provider, system_override=system):
        size += len(item)
        if size > limit:
            raise CodeQualityError(f'Model exceeded {limit} characters in one code generation step')
        parts.append(item)
    out = ''.join(parts).strip()
    if not out:
        raise CodeQualityError('Model returned empty code')
    return out


def _clean(raw: str) -> str:
    raw = raw.strip()
    match = re.fullmatch(r'```[^\n]*\n([\s\S]*?)\n```', raw)
    return (match.group(1) if match else raw).strip() + '\n'


def _parse_source(source: str, extension: str) -> None:
    try:
        import tree_sitter
        import tree_sitter_javascript
        import tree_sitter_typescript
    except ImportError as exc:
        raise CodeQualityError('Install tree-sitter, tree-sitter-javascript and tree-sitter-typescript in backend requirements') from exc
    language_obj = (tree_sitter_typescript.language_tsx() if extension == 'tsx'
                    else tree_sitter_javascript.language())
    parser = tree_sitter.Parser(tree_sitter.Language(language_obj))
    tree = parser.parse(source.encode('utf-8'))
    if tree.root_node.has_error:
        def find_error(node):
            if node.type == 'ERROR' or node.is_missing:
                return node
            for child in node.children:
                if child.has_error or child.is_missing:
                    found = find_error(child)
                    if found:
                        return found
            return node
        err = find_error(tree.root_node)
        row, col = err.start_point
        snippet = source.splitlines()[row][:130] if row < len(source.splitlines()) else ''
        raise CodeQualityError(f'Syntax error near line {row+1}, column {col+1}: {snippet}')


def _check_optional_filter_map(source: str) -> None:
    """Catch a known AI output bug: optional toArray() result used with .map().

    This is a focused defensive check, not a general JavaScript type checker.
    """
    pattern = re.compile(
        r"\btoArray\s*\([^;\n]*?\)\s*\.\s*map\s*\(",
        flags=re.MULTILINE,
    )
    if pattern.search(source):
        raise CodeQualityError(
            'Optional filter bug: toArray() can return undefined, so do not call '
            '.map() on its result without a nullish guard. Use ?.map() or '
            'a safe default array, and preserve no-filter behavior.'
        )


def _check_single_file(source: str, extension: str) -> None:
    if not source.strip() or len(source) > 150000:
        raise CodeQualityError('Generated code empty or too large')
    _parse_source(source, extension)
    if extension == 'js':
        _check_optional_filter_map(source)
    if extension == 'tsx':
        if not re.search(r'\bexport\s+(?:default\s+)?(?:function|const|class|\{)|\bexport\s+default\s+[A-Za-z]', source):
            raise CodeQualityError('TSX needs an exported component')
        if '<' not in source or '/>' not in source and '</' not in source:
            raise CodeQualityError('TSX component has no JSX markup')


def _repair(source: str, provider: str, extension: str, error: str) -> str:
    return _clean(_ask(
        f'Correct this complete .{extension} file. Preserve the intended UI/API, imports and functionality. '
        'Return only a single complete replacement file, no Markdown or explanations. '
        'When toArray() can return undefined, use optional chaining or default arrays '
        'before calling .map(), .filter(), or .includes(). '
        f'VALIDATION ERROR: {error}\nSOURCE:\n{source}',
        provider,
        system='You repair syntax and single-file code structure. No placeholders. No code execution.',
        limit=32000,
    ))


def generate_frontend_code(prompt: str, provider: str, extension: str,
                           progress: Callable[[str, int], None] | None = None) -> str:
    """Generate one validated TSX or JS file, without executing it.

    progress(stage, percent) is optional. Pass an existing job progress callback
    if available. Percentages are generation milestones, not provider progress.
    """
    if extension not in ('tsx', 'js'):
        raise CodeQualityError('Only .tsx and .js supported by Phase 7.8 Stage 1')

    def notify(stage, pct):
        if progress is not None:
            progress(stage, pct)

    notify('Planning code structure', 14)
    raw = _ask(
        'Plan one self-contained ' + extension + ' source file for this request. Return a JSON object '
        'with {"imports_and_types":"brief", "functions":"brief", "entrypoint":"brief"}. '
        'Do not include code or Markdown. Keep the plan concise.\nREQUEST:\n' + prompt,
        provider, system='Return a valid concise JSON object.', limit=6000)
    try:
        plan = json.loads(_clean(raw))
        if not isinstance(plan, dict):
            raise ValueError()
    except (ValueError, TypeError) as exc:
        raise CodeQualityError('Could not parse code plan') from exc

    notify('Generating source file', 25)
    file_prompt = (
        f'Produce one COMPLETE, self-contained .{extension} source file based on this plan: '
        f'{json.dumps(plan, ensure_ascii=False)}\nREQUEST:\n{prompt}\n'
        'For TSX return one exported React component. Include all imports. '
        'Prefer built-in web APIs and React; avoid extra packages unless requested. '
        'For optional filters, ensure missing options mean no restriction. Never call .map, .filter, '
        'or .includes on a possibly undefined value without guarding or defaulting it. '
        'All tags and strings must be closed. No code fences, placeholders, commentary, '
        'or references to missing companion files. Keep under 300 lines.'
    )
    last_error = ''
    source = ''
    for attempt in range(3):
        notify('Generating code' if attempt == 0 else f'Regenerating code (attempt {attempt+1})', 30 + attempt * 15)
        try:
            source = _clean(_ask(
                file_prompt if attempt == 0 else file_prompt + '\nPREVIOUS ERROR:\n' + last_error +
                '\nRewrite from scratch as one compact complete valid file.',
                provider, system=f'Generate valid {extension} source code only; do not execute.', limit=26000))
            notify('Checking source syntax and structure', 70)
            _check_single_file(source, extension)
            notify('Source structure validated', 90)
            return source
        except CodeQualityError as exc:
            last_error = str(exc)
            # Short corrective rewrite is more reliable than concatenating broken fragments.
            if source and ('Syntax error' in last_error or 'Optional filter bug' in last_error) and len(source) < 14000:
                try:
                    notify('Repairing generated syntax', 78)
                    repaired = _repair(source, provider, extension, last_error)
                    _check_single_file(repaired, extension)
                    notify('Repaired source validated', 90)
                    return repaired
                except CodeQualityError as repair_exc:
                    last_error = str(repair_exc)
    raise CodeQualityError(f'Cannot generate a validated {extension} file after retries: {last_error}')
