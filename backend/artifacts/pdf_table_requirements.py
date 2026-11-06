"""PDF-only output contract for tables explicitly requested by the user.

Only inspects generated Markdown; it never executes model content or modifies
another output format. The renderer remains the authority for table layout.
"""
import re


_TABLE_REQUEST = re.compile(r'\b(?:table|tables|tabular|matrix)\b', re.I)
_SEPARATOR = re.compile(r'^\s*\|?\s*:?-{3,}:?\s*(?:\|\s*:?-{3,}:?\s*)+\|?\s*$')
_WORD = re.compile(r'[a-z][a-z0-9_-]*', re.I)
_STOP = {'a', 'an', 'the', 'include', 'add', 'create', 'with', 'for', 'and',
         'of', 'to', 'in', 'at', 'on', 'this', 'that', 'should', 'be', 'as'}


def table_requested(prompt):
    """Explicit tabular deliverable, not an implied need inferred from topic."""
    return bool(_TABLE_REQUEST.search(str(prompt)))


def count_tables(body):
    """Count genuine Markdown table blocks accepted by document_quality._blocks.

    Avoid treating prose containing pipes or a plain bulleted list as a table.
    """
    from .document_quality import _blocks
    return sum(1 for block in _blocks(str(body))
               if block[0] == 'table' and len(block[1]) >= 3
               and len(block[1][0]) >= 2
               and all(any(str(cell).strip() for cell in row)
                       for row in block[1][1:]))


def _target_section(sections, prompt):
    """Match table subject to a section title; ignore generic words like 'table'."""
    terms = []
    for match in re.finditer(r'\b(?:[a-z][a-z0-9-]*\s+){0,5}(?:table|matrix)\b',
                             str(prompt).lower()):
        prefix = match.group(0).rsplit(' ', 1)[0]
        terms.extend(w for w in _WORD.findall(prefix) if w not in _STOP)
    # Also consider keywords in section headings, rather than hardcoding domains.
    scores = []
    for index, section in enumerate(sections):
        heading = str(section.get('heading', '')).lower()
        words = set(_WORD.findall(heading))
        score = 3 * sum(t in words for t in terms)
        score += 2 if {'table', 'assessment', 'comparison', 'matrix'} & words else 0
        score -= 3 if {'conclusion', 'summary', 'references', 'appendix'} & words else 0
        scores.append(score)
    if not scores:
        raise ValueError('No report sections available for the requested table.')
    return max(range(len(scores)), key=lambda i: (scores[i], -i))


def ensure_pdf_tables(prompt, sections, provider, *, ask):
    """Preserve existing tables or restore a missing explicitly requested one.

    `ask` is the caller's existing bounded model adapter. At most two extra
    requests are made, and no generated artifact is saved on recovery failure.
    """
    if not table_requested(prompt) or any(count_tables(s.get('body', '')) for s in sections):
        return sections
    idx = _target_section(sections, prompt)
    original = str(sections[idx].get('body', '')).strip()
    heading = str(sections[idx].get('heading', '')).strip()
    if not original or not heading:
        raise ValueError('Cannot restore a table without a substantive section.')
    prompt_text = (
        'Revise only this report section to satisfy the user\'s explicitly requested table.\n'
        'Keep its existing factual content and qualifications. Turn relevant listed items '
        'into a REAL Markdown table with a header row, a delimiter row using |---|---|, '
        'and data rows. At least two columns and two data rows are required. '
        'Preserve any specified number of items, risk severities, field names, and '
        'mitigations from the user request and existing draft. Do not invent findings, '
        'measurements, citations, or unprovided facts. Keep the section introduction '
        'short and keep all other important content. Do not use code fences.\n'
        f'FULL USER REQUEST:\n{str(prompt)[:3500]}\n'
        f'SECTION HEADING: {heading}\n'
        f'EXISTING SECTION BODY:\n{original[:9500]}'
    )
    for _attempt in range(2):
        candidate = str(ask(prompt_text, provider,
                            system=('You write safe, document-grounded report sections. '
                                    'Return ONLY a complete Markdown section body with a '
                                    'properly formatted Markdown table.'),
                            limit=12000)).strip()
        candidate = re.sub(r'^```(?:markdown|md)?\s*\n|\n```\s*$', '', candidate,
                           flags=re.I).strip()
        if len(candidate) >= 100 and count_tables(candidate):
            result = list(sections)
            result[idx] = {**sections[idx], 'body': candidate}
            return result
        prompt_text = (
            'Your prior response omitted a valid Markdown table. '
            'Return the COMPLETE section body again, including the literal '
            'Markdown header separator, for example:\n'
            '| Field | Description |\n|---|---|\n| Item A | Explanation |\n'
            '| Item B | Explanation |\n'
            'Use the requested subject and preserve all relevant existing facts.\n' +
            prompt_text
        )[:15000]
    raise ValueError('The PDF request requires a table, but the model did not '
                     'return a valid Markdown table after two repair attempts. '
                     'No PDF was saved.')
