"""Conservatively detect explicitly required presentation slide counts."""
import re


def requested_slide_count(prompt):
    text = str(prompt or '')[:5000]
    patterns = (
        r'\b(?:exactly|total of|make|create|generate|produce|build|with)\s+(\d{1,2})\s+(?:editable\s+)?slides?\b',
        r'\b(\d{1,2})\s*[- ]slide\s+(?:presentation|deck|powerpoint)\b',
        r'\b(?:slides?|pages?)\s*:\s*(\d{1,2})\b',
    )
    found = [int(m.group(1)) for pattern in patterns for m in re.finditer(pattern, text, flags=re.I)]
    found = [n for n in found if 2 <= n <= 16]
    return found[0] if found and all(x == found[0] for x in found) else None
