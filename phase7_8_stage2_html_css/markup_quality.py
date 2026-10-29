"""Phase 7.8 Stage 2 — bounded HTML/CSS generation and static validation.

Generated code is NEVER executed, rendered, fetched or imported here.
"""
from __future__ import annotations

import re
from html.parser import HTMLParser
from typing import Callable

from chat.providers import stream_generate


class MarkupQualityError(ValueError):
    pass


_VOID = frozenset('area base br col embed hr img input link meta param source track wbr'.split())
_RAW = frozenset({'script', 'style'})


class _HTMLAudit(HTMLParser):
    """Conservative structural verifier: document, matching tags and critical assets."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack: list[str] = []
        self.errors: list[str] = []
        self.counts: dict[str, int] = {}
        self.ids: set[str] = set()
        self.scripts = 0

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        self.counts[tag] = self.counts.get(tag, 0) + 1
        attr = dict(attrs)
        if attr.get('id'):
            if attr['id'] in self.ids:
                self.errors.append('Duplicate HTML id: ' + attr['id'])
            self.ids.add(attr['id'])
        if tag == 'img' and not ('alt' in attr):
            self.errors.append('Image is missing alt attribute')
        if tag == 'script':
            self.scripts += 1
        if tag not in _VOID:
            self.stack.append(tag)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag.lower() not in _VOID:
            self.handle_endtag(tag)

    def handle_endtag(self, tag):
        tag = tag.lower()
        if tag in _VOID:
            self.errors.append('Void element has closing tag: ' + tag)
        elif not self.stack:
            self.errors.append('Unexpected closing tag: ' + tag)
        elif self.stack[-1] == tag:
            self.stack.pop()
        else:
            self.errors.append(f'Expected </{self.stack[-1]}> before </{tag}>')
            # Recover conservatively; mismatched nesting will still fail validation.
            if tag in self.stack:
                while self.stack and self.stack[-1] != tag:
                    self.stack.pop()
                if self.stack:
                    self.stack.pop()


def validate_html(source: str) -> None:
    if not re.search(r'(?i)<!doctype\s+html\b', source):
        raise MarkupQualityError('HTML must start with <!DOCTYPE html>')
    parser = _HTMLAudit()
    try:
        parser.feed(source)
        parser.close()
    except Exception as exc:
        raise MarkupQualityError(f'HTML parsing failed: {exc}') from exc
    for tag in ('html', 'head', 'title', 'body'):
        if parser.counts.get(tag) != 1:
            parser.errors.append(f'Expected exactly one <{tag}> element')
    if parser.stack:
        parser.errors.append('Unclosed tags: ' + ', '.join(parser.stack[-8:]))
    if parser.errors:
        raise MarkupQualityError('HTML structure: ' + '; '.join(parser.errors[:5]))


def validate_css(source: str) -> None:
    try:
        import tinycss2
    except ImportError as exc:
        raise MarkupQualityError('Missing tinycss2. Add tinycss2>=1.2,<2 to backend/requirements.txt') from exc
    rules = tinycss2.parse_stylesheet(source, skip_whitespace=True, skip_comments=True)
    if not rules:
        raise MarkupQualityError('CSS contains no rules')
    errors = [r for r in rules if r.type == 'error']
    rule_count = 0
    for rule in rules:
        if rule.type == 'qualified-rule':
            rule_count += 1
            declarations = tinycss2.parse_declaration_list(rule.content, skip_whitespace=True, skip_comments=True)
            errors += [x for x in declarations if x.type == 'error' or (x.type == 'declaration' and not tinycss2.serialize(x.value).strip())]
        elif rule.type == 'at-rule' and rule.content is not None:
            # @media, @supports, @container etc. contain nested stylesheets.
            if rule.lower_at_keyword in {'media', 'supports', 'container', 'layer', 'scope'}:
                nested = tinycss2.parse_rule_list(rule.content, skip_comments=True, skip_whitespace=True)
                errors += [r for r in nested if r.type == 'error']
                for nested_rule in nested:
                    if nested_rule.type == 'qualified-rule':
                        rule_count += 1
                        decl = tinycss2.parse_declaration_list(nested_rule.content, skip_whitespace=True, skip_comments=True)
                        errors += [d for d in decl if d.type == 'error' or (d.type == 'declaration' and not tinycss2.serialize(d.value).strip())]
    if errors:
        first = errors[0]
        raise MarkupQualityError(f'CSS syntax error line {getattr(first,"source_line","?")}: {getattr(first,"message","parse error")}')
    if rule_count == 0:
        raise MarkupQualityError('CSS must define at least one style rule')
    # tinycss2 intentionally parses grammar, not semantic validity of vendor properties or values.


def _clean_response(raw: str) -> str:
    text = raw.strip()
    match = re.fullmatch(r'```(?:html|css)?\s*\n([\s\S]*?)\n```', text, flags=re.I)
    return (match.group(1) if match else text).strip() + '\n'


def _ask(prompt: str, provider: str, *, system: str, limit: int) -> str:
    pieces = []
    total = 0
    for item in stream_generate(prompt, [], [], provider, system_override=system):
        total += len(item)
        if total > limit:
            raise MarkupQualityError(f'Model output exceeded the per-step limit ({limit} characters)')
        pieces.append(item)
    result = ''.join(pieces).strip()
    if not result:
        raise MarkupQualityError('Model returned empty content')
    return result


def generate_markup_file(prompt: str, provider: str, extension: str,
                         progress: Callable[[str, int], None] | None = None) -> str:
    """One HTML or CSS file; validate and retry twice; no execution of generated code."""
    if extension not in {'html', 'css'}:
        raise MarkupQualityError('Only HTML and CSS are supported by this generator')
    def notify(stage: str, pct: int):
        if progress:
            progress(stage, pct)
    kind = 'HTML5 standalone page' if extension == 'html' else 'standalone CSS stylesheet'
    rules = (
        'Provide <!DOCTYPE html>, html lang, head with charset and viewport meta, title, body. '
        'Match opening/closing tags, use semantic HTML, accessible controls and image alt text. '
        'Keep CSS in a <style> tag if requested. Do not require external dependencies or external network resources.'
        if extension == 'html' else
        'Provide valid CSS, scoped appropriately, responsive @media rules where suitable, no HTML or Markdown. '
        'Avoid empty blocks and use simple compatible properties.'
    )
    system = f'Produce exactly one complete {kind}. Return only source, no Markdown fences or commentary. No placeholders. No external access.'
    validator = validate_html if extension == 'html' else validate_css
    notify(f'Generating {extension.upper()} source', 18)
    current_prompt = f'Write a complete {kind}. {rules}\nUSER REQUEST:\n{prompt}'
    last_error = None
    for attempt in range(3):
        notify(f'{"Generating" if attempt == 0 else "Repairing"} {extension.upper()} (attempt {attempt + 1}/3)', 24 + attempt * 15)
        try:
            source = _clean_response(_ask(current_prompt, provider, system=system, limit=32000))
            if len(source) > 150000:
                raise MarkupQualityError('Generated file exceeded maximum file size')
            notify('Validating HTML structure' if extension == 'html' else 'Validating CSS syntax', 68 + attempt * 8)
            validator(source)
            notify(f'{extension.upper()} validated — preparing artifact', 94)
            return source
        except MarkupQualityError as exc:
            last_error = exc
            if attempt == 2:
                break
            current_prompt = (f'Generate a COMPLETE corrected {kind} for the original task. '
                              f'Previous attempt failed: {str(exc)[:450]}. '
                              'Do not return only a fragment. ' + rules + '\nORIGINAL REQUEST:\n' + prompt)
    raise MarkupQualityError(f'{extension.upper()} validation failed after 3 attempts: {last_error}')
