"""Conservative, header-guided Excel cell typing. Never evaluates AI-produced formulas."""
import re
from datetime import date
from decimal import Decimal, InvalidOperation

_DATE_HINT = re.compile(r'\b(date|due date|deadline|birthday|timestamp)\b', re.I)
_NUM_HINT = re.compile(r'\b(amount|cost|price|total|subtotal|balance|revenue|expense|quantity|qty|count|units|rate|percent|percentage|discount|tax|profit|salary|weight|temperature)\b', re.I)
_ID_HINT = re.compile(r'\b(id|identifier|code|sku|postal|zip|account|telephone|phone|serial|version|reference|number)\b', re.I)
_NUMBER = re.compile(r'^[-+]?(?:\d+(?:,\d{3})*|\d*)(?:\.\d+)?$')


def typed_cell(header, raw):
    """Return (typed value, Excel number format).

    Only known numeric/date columns convert; identifiers and ambiguous text stay text.
    Values starting with formula operators remain literal text.
    """
    if raw is None:
        return '', None
    if isinstance(raw, bool):
        return str(raw), None
    name = str(header or '').strip()
    if _ID_HINT.search(name):
        return str(raw), None
    if _DATE_HINT.search(name):
        if isinstance(raw, date):
            return raw, 'yyyy-mm-dd'
        if isinstance(raw, str) and re.fullmatch(r'\d{4}-\d{2}-\d{2}', raw.strip()):
            try:
                return date.fromisoformat(raw.strip()), 'yyyy-mm-dd'
            except ValueError:
                pass
    if _NUM_HINT.search(name):
        if isinstance(raw, (int, float, Decimal)) and not isinstance(raw, bool):
            number = Decimal(str(raw))
        elif isinstance(raw, str):
            value = raw.strip()
            is_percent = value.endswith('%')
            cleaned = value.rstrip('%').strip()
            if cleaned.startswith(('$', '£', '€')):
                cleaned = cleaned[1:].strip()
            if not _NUMBER.fullmatch(cleaned) or cleaned in ('', '.', '+', '-'):
                return raw, None
            try:
                number = Decimal(cleaned.replace(',', ''))
            except InvalidOperation:
                return raw, None
        else:
            return str(raw), None
        if not number.is_finite() or abs(number) > Decimal('1e14'):
            return str(raw), None
        if isinstance(raw, str) and raw.strip().endswith('%'):
            return float(number / 100), '0.00%'
        if number == number.to_integral_value():
            numeric = int(number)
        else:
            numeric = float(number)
        return numeric, '#,##0.00' if number != number.to_integral_value() else '#,##0'
    return str(raw), None
