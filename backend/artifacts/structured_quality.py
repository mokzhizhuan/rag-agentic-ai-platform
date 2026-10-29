"""Phase 7.8 Stage 3: bounded single-file SQL / YAML generation.

Static parsing only. Never execute SQL or generated YAML.
"""
from __future__ import annotations

import re
from typing import Callable
from chat.providers import stream_generate


class StructuredQualityError(ValueError):
    pass


def validate_sql(source: str) -> None:
    """Parse PostgreSQL SQL and reject especially dangerous / misleading statements.

    Parsing validates *syntax structure*, NOT DB schema, full PostgreSQL semantics,
    runtime safety, migrations, query performance, or SQL permissions.
    """
    if not source.strip() or len(source) > 150_000:
        raise StructuredQualityError('SQL must be nonempty and at most 150000 characters')
    if re.search(r'(?im)^\s*(?:```|\\copy\b|\\i\b|\\!\b)', source):
        raise StructuredQualityError('SQL must be plain source without code fences or psql shell commands')
    try:
        import sqlglot
        from sqlglot import exp
        from sqlglot.errors import ParseError, UnsupportedError
    except ImportError as exc:
        raise StructuredQualityError('Missing sqlglot. Add sqlglot>=25,<30 to backend/requirements.txt') from exc
    try:
        statements = sqlglot.parse(source, read='postgres', error_level='RAISE')
    except (ParseError, UnsupportedError, ValueError) as exc:
        raise StructuredQualityError(f'PostgreSQL SQL parse failed: {str(exc)[:350]}') from exc
    statements = [stmt for stmt in statements if stmt is not None]
    if not statements:
        raise StructuredQualityError('SQL has no statements')
    if len(statements) > 50:
        raise StructuredQualityError('SQL exceeds 50 statements')
    for i, stmt in enumerate(statements, 1):
        # Unknown raw commands are not trustworthy parser validation.
        if isinstance(stmt, exp.Command):
            raise StructuredQualityError(f'Statement {i} uses an unvalidated SQL command')
        if any(isinstance(n, tuple(t for t in (getattr(exp, "Drop", None), getattr(exp, "Truncate", None)) if t is not None)) for n in stmt.walk()):
            raise StructuredQualityError(f'Statement {i} contains DROP or TRUNCATE; destructive SQL blocked')
        for n in stmt.walk():
            if isinstance(n, (exp.Update, exp.Delete)) and n.args.get('where') is None:
                raise StructuredQualityError(f'Statement {i} has UPDATE/DELETE without WHERE')
        # Protect against server-side file and program I/O embedded in generated SQL.
        if re.search(r'(?i)\bCOPY\b[\s\S]{0,250}?\bPROGRAM\b', stmt.sql(dialect='postgres')):
            raise StructuredQualityError(f'Statement {i} contains COPY PROGRAM')
    return None


class _UniqueKeyLoader:  # Build on demand to avoid adding a dependency for SQL-only installations.
    @staticmethod
    def create():
        try:
            import yaml
        except ImportError as exc:
            raise StructuredQualityError('Missing PyYAML. Add PyYAML>=6,<7 to backend/requirements.txt') from exc

        class UniqueSafeLoader(yaml.SafeLoader):
            def construct_mapping(self, node, deep=False):
                mapping = {}
                for key_node, value_node in node.value:
                    key = self.construct_object(key_node, deep=deep)
                    try:
                        duplicate = key in mapping
                    except TypeError as exc:
                        raise yaml.constructor.ConstructorError(None, None, 'Unhashable YAML key', key_node.start_mark) from exc
                    if duplicate:
                        raise yaml.constructor.ConstructorError(None, None, f'Duplicate YAML key: {key!r}', key_node.start_mark)
                    mapping[key] = self.construct_object(value_node, deep=deep)
                return mapping

        return yaml, UniqueSafeLoader


def validate_yaml(source: str) -> None:
    if not source.strip() or len(source) > 150_000:
        raise StructuredQualityError('YAML must be nonempty and at most 150000 characters')
    if source.lstrip().startswith('```'):
        raise StructuredQualityError('YAML must not contain Markdown fences')
    # Cap alias count before parse: safe_load is safe from Python object instantiation,
    # but deeply recursive or massively aliased data can still consume resources.
    if len(re.findall(r'(?<!\w)\*[A-Za-z0-9_-]+', source)) > 30:
        raise StructuredQualityError('YAML contains too many aliases')
    yaml, loader = _UniqueKeyLoader.create()
    try:
        documents = list(yaml.load_all(source, Loader=loader))
    except (yaml.YAMLError, RecursionError, ValueError) as exc:
        raise StructuredQualityError(f'YAML parsing failed: {str(exc)[:350]}') from exc
    if not documents or all(doc is None for doc in documents):
        raise StructuredQualityError('YAML has no nonempty documents')
    if len(documents) > 10:
        raise StructuredQualityError('YAML exceeds 10 documents')
    def check_depth(value, depth=0):
        if depth > 40:
            raise StructuredQualityError('YAML nesting exceeds 40 levels')
        if isinstance(value, dict):
            for k, v in value.items():
                check_depth(k, depth + 1)
                check_depth(v, depth + 1)
        elif isinstance(value, list):
            for v in value:
                check_depth(v, depth + 1)
    for doc in documents:
        check_depth(doc)


def _clean(raw: str, ext: str) -> str:
    text = raw.strip()
    match = re.fullmatch(r'```(?:' + re.escape(ext) + r'|postgresql|postgres|yml)?\s*\n([\s\S]*?)\n```', text, re.I)
    return (match.group(1) if match else text).strip() + '\n'


def _ask(prompt: str, provider: str, system: str, max_chars: int = 32000) -> str:
    chunks = []
    length = 0
    for part in stream_generate(prompt, [], [], provider, system_override=system):
        length += len(part)
        if length > max_chars:
            raise StructuredQualityError(f'Model output exceeds {max_chars} characters')
        chunks.append(part)
    answer = ''.join(chunks).strip()
    if not answer:
        raise StructuredQualityError('Model returned empty output')
    return answer


def generate_structured_file(prompt: str, provider: str, extension: str,
                             progress: Callable[[str, int], None] | None = None) -> str:
    ext = extension.lower().lstrip('.')
    if ext == 'yml':
        ext = 'yaml'
    if ext not in {'sql', 'yaml'}:
        raise StructuredQualityError(f'Unsupported structured format: {extension}')
    notify = progress or (lambda stage, pct: None)
    validator = validate_sql if ext == 'sql' else validate_yaml
    rules = (
        'Write PostgreSQL-compatible SQL. Use explicit schema/table/column names, transactions where needed, '
        'idempotent CREATE IF NOT EXISTS where suitable, parameter placeholders for dynamic values, and safe examples. '
        'Do NOT output DROP, TRUNCATE, UPDATE/DELETE without WHERE, COPY PROGRAM, psql shell commands, '
        'or execute external programs. Return SQL only.'
        if ext == 'sql' else
        'Write valid standalone YAML. Use consistent indentation, unique mapping keys, safe plain YAML values, '
        'and no arbitrary Python/object tags. Do not output Markdown or commentary. Do not invent passwords or credentials.'
    )
    system = f'You generate a complete single .{ext} file. Return only valid file content. {rules}'
    original = prompt
    current = f'USER REQUEST:\n{original}\n\nFORMAT REQUIREMENTS:\n{rules}'
    last = None
    for attempt in range(3):
        notify(f'{"Generating" if attempt == 0 else "Repairing"} {ext.upper()} ({attempt + 1}/3)', 20 + attempt * 18)
        try:
            source = _clean(_ask(current, provider, system), ext)
            notify(f'Validating {ext.upper()}', 70 + attempt * 8)
            validator(source)
            notify(f'{ext.upper()} validated', 94)
            return source
        except StructuredQualityError as exc:
            last = exc
            if attempt == 2 or str(exc).startswith('Missing '):
                break
            current = ('Regenerate the COMPLETE file from scratch. Prior output failed validation: '
                       + str(exc)[:400] + '\n' + rules + '\nORIGINAL REQUEST:\n' + original)
    raise StructuredQualityError(f'{ext.upper()} generation failed after validation: {last}')
