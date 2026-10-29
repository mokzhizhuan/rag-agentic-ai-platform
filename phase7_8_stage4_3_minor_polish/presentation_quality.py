"""Bounded, editable PowerPoint generation for Phase 7.8 Stage 4.

Does not execute model output, fetch remote media or mutate project data.
"""
from __future__ import annotations

import io
import json
import re
from typing import Callable

from chat.providers import stream_generate


class PresentationQualityError(ValueError):
    pass


MAX_SLIDES = 24
MAX_BULLETS = 5
MAX_TABLE_ROWS = 6
MAX_OUTPUT = 45000
NAVY = (23, 42, 66)
BLUE = (34, 99, 164)
LIGHT = (240, 245, 250)
MUTED = (93, 108, 125)


def _model(prompt: str, provider: str) -> str:
    schema = '''Return exactly one JSON object, no Markdown, with keys:
{"title":"...","subtitle":"...","slides":[{"layout":"title|bullets|two_column|table|metrics|flow|risk|closing","title":"...","subtitle":"...","bullets":["..."],"left":["..."],"right":["..."],"headers":["..."],"rows":[["..."]],"metrics":[{"label":"...","value":"...","note":"..."}]}]}.
Avoid duplicating step numbers inside flow labels because the slide renderer adds numbers. Prefer tables for structured commissioning checks. Produce 6–12 coherent slides (maximum 16 planned slides). Give concise titles (max 70 chars), 2–5 bullets ideally below 95 chars, 2–4 items per two-column side, tables with 2–6 headers and up to 16 rows (renderer will split), and up to 4 metrics. Use flow layout for process/architecture: bullets is an ordered sequence of 3–6 short step names. Use risk layout for risk comparisons: rows contains up to 8 entries, each [Risk, Mitigation, Status]; headers should be [Risk, Mitigation, Status]. Choose layout appropriately. Use only facts provided; use TBD for unknown numbers. Avoid unnecessary duplicate intro slides. No Markdown/code fences, image URLs, or other keys. Every slide must contain meaningful content. Design for 16:9 and concise on-slide copy.'''
    chunks = []
    total = 0
    for part in stream_generate('REQUEST:\n' + prompt + '\n\nOUTPUT SCHEMA:\n' + schema,
                                [], [], provider,
                                system_override='You are a professional slide-deck planner. Return valid JSON only. Never invent verified data.'):
        total += len(part)
        if total > MAX_OUTPUT:
            raise PresentationQualityError('Slide plan exceeds model output limit')
        chunks.append(part)
    raw = ''.join(chunks).strip()
    if raw.startswith('```'):
        raw = re.sub(r'^```(?:json)?\s*|\s*```$', '', raw, flags=re.I).strip()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise PresentationQualityError('Model produced invalid slide-plan JSON') from exc
    return data


def _strings(value, limit, length=160):
    if not isinstance(value, list):
        return []
    return [str(x).strip()[:length] for x in value[:limit] if isinstance(x, str) and x.strip()]


def validate_plan(plan):
    if not isinstance(plan, dict):
        raise PresentationQualityError('Slide plan is not an object')
    slides = plan.get('slides')
    if not isinstance(slides, list) or not 2 <= len(slides) <= MAX_SLIDES:
        raise PresentationQualityError('Slide plan must contain 2–16 slides')
    allowed = {'title', 'bullets', 'two_column', 'table', 'metrics', 'flow', 'risk', 'closing'}
    cleaned = []
    for idx, item in enumerate(slides, 1):
        if not isinstance(item, dict):
            raise PresentationQualityError(f'Slide {idx} is not an object')
        layout = item.get('layout', 'bullets')
        title = str(item.get('title') or '').strip()
        if layout not in allowed or not title or len(title) > 95:
            raise PresentationQualityError(f'Slide {idx} has an invalid layout/title')
        slide = {'layout': layout, 'title': title,
                 'subtitle': str(item.get('subtitle') or '').strip()[:160],
                 'bullets': _strings(item.get('bullets'), 24, 220),
                 'left': _strings(item.get('left'), 12, 180),
                 'right': _strings(item.get('right'), 12, 180)}
        if layout in ('bullets', 'flow') and not slide['bullets']:
            raise PresentationQualityError(f'Slide {idx} has no bullets')
        if layout == 'two_column' and (not slide['left'] or not slide['right']):
            raise PresentationQualityError(f'Slide {idx} lacks column content')
        if layout in ('table', 'risk'):
            headers = _strings(item.get('headers'), 6, 45)
            raw_rows = item.get('rows', [])
            if not 2 <= len(headers) <= 6 or not isinstance(raw_rows, list) or not 1 <= len(raw_rows) <= 32:
                raise PresentationQualityError(f'Slide {idx} has invalid table dimensions')
            rows = []
            for r in raw_rows:
                if not isinstance(r, list) or len(r) != len(headers):
                    raise PresentationQualityError(f'Slide {idx} has mismatched table cells')
                rows.append([str(c or '')[:240] for c in r])
            slide['headers'], slide['rows'] = headers, rows
        if layout == 'metrics':
            metrics = item.get('metrics', [])
            if not isinstance(metrics, list) or not 1 <= len(metrics) <= 4:
                raise PresentationQualityError(f'Slide {idx} has invalid metrics')
            slide['metrics'] = []
            for metric in metrics:
                if not isinstance(metric, dict) or not str(metric.get('value', '')).strip():
                    raise PresentationQualityError(f'Slide {idx} has an empty metric')
                slide['metrics'].append({k: str(metric.get(k) or '')[:(65 if k != 'note' else 100)]
                                         for k in ('label', 'value', 'note')})
        cleaned.append(slide)
    return {'title': str(plan.get('title') or 'Presentation')[:95],
            'slides': _expand_slides(cleaned)}



def _chunks(items, count):
    return [items[i:i+count] for i in range(0, len(items), count)]


def _balanced_chunks(items, maximum):
    """Split into nearly equal parts while respecting the per-slide row limit."""
    import math
    count = max(1, math.ceil(len(items) / maximum))
    q, remainder = divmod(len(items), count)
    sizes = [q + (1 if i < remainder else 0) for i in range(count)]
    result, offset = [], 0
    for size in sizes:
        result.append(items[offset:offset + size])
        offset += size
    return result


def _expand_slides(slides):
    """Split content before rendering rather than discarding extra rows/bullets."""
    expanded = []
    for slide in slides:
        layout = slide['layout']
        if layout == 'bullets':
            parts = _balanced_chunks(slide['bullets'], MAX_BULLETS)
            for i, part in enumerate(parts):
                item = dict(slide, bullets=part)
                if len(parts) > 1:
                    item['title'] = f"{slide['title']} ({i+1}/{len(parts)})"
                expanded.append(item)
        elif layout in ('table','risk'):
            # Risk comparisons are narrower; use fewer rows for legibility.
            per_page = 5 if layout == 'risk' else MAX_TABLE_ROWS
            parts = _balanced_chunks(slide['rows'], per_page)
            for i, part in enumerate(parts):
                item = dict(slide, rows=part)
                if len(parts)>1:
                    item['title'] = f"{slide['title']} ({i+1}/{len(parts)})"
                expanded.append(item)
        elif layout == 'two_column':
            left, right = _chunks(slide['left'], 4), _chunks(slide['right'], 4)
            parts = max(len(left),len(right))
            for i in range(parts):
                item = dict(slide,left=left[i] if i < len(left) else [],right=right[i] if i < len(right) else [])
                if parts>1:
                    item['title']=f"{slide['title']} ({i+1}/{parts})"
                expanded.append(item)
        elif layout == 'flow':
            parts = _balanced_chunks(slide['bullets'],6)
            for i, part in enumerate(parts):
                item=dict(slide,bullets=part)
                if len(parts)>1:
                    item['title']=f"{slide['title']} ({i+1}/{len(parts)})"
                expanded.append(item)
        else:
            expanded.append(slide)
    if len(expanded) > MAX_SLIDES:
        raise PresentationQualityError(f'Planned content needs {len(expanded)} slides; limit is {MAX_SLIDES}. Reduce requested content.')
    return expanded


def _text_risk(text, width, size):
    """Conservative character/line heuristic; PowerPoint does not expose actual laid-out glyphs."""
    import math
    max_chars = max(10, int(width * 11.5 * 18 / max(size,1)))
    return max(1,math.ceil(len(text)/max_chars))


def _rgb(rgb):
    from pptx.dml.color import RGBColor
    return RGBColor(*rgb)


def _textbox(slide, x, y, w, h, text, size=18, bold=False, color=NAVY, align=None):
    from pptx.util import Inches, Pt
    from pptx.enum.text import MSO_AUTO_SIZE, PP_ALIGN, MSO_ANCHOR
    shape = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = shape.text_frame
    tf.clear()
    tf.word_wrap = True
    tf.auto_size = MSO_AUTO_SIZE.NONE
    tf.margin_left = tf.margin_right = Inches(.04)
    tf.margin_top = tf.margin_bottom = Inches(.025)
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    p = tf.paragraphs[0]
    p.alignment = align or PP_ALIGN.LEFT
    p.text = text
    p.font.name = 'Aptos'
    p.font.size = Pt(size)
    p.font.bold = bold
    p.font.color.rgb = _rgb(color)
    return shape


def _rect(slide, x, y, w, h, fill, radius=False):
    from pptx.util import Inches
    from pptx.enum.shapes import MSO_SHAPE
    kind = MSO_SHAPE.ROUNDED_RECTANGLE if radius else MSO_SHAPE.RECTANGLE
    shape = slide.shapes.add_shape(kind, Inches(x), Inches(y), Inches(w), Inches(h))
    shape.fill.solid(); shape.fill.fore_color.rgb = _rgb(fill)
    shape.line.fill.background()
    return shape


def _bullets(slide, texts, x, y, w, width=5.8, size=19):
    from pptx.util import Inches, Pt
    from pptx.enum.text import MSO_AUTO_SIZE
    line_h = min(.85, 4.9 / max(len(texts), 1))
    for i, text in enumerate(texts):
        _rect(slide, x, y + i * line_h + .22, .075, .075, BLUE)
        _textbox(slide, x+.23, y+i*line_h, width-.25, line_h-.04, text, size=size)


def render_presentation(plan):
    from pptx import Presentation
    from pptx.util import Inches, Pt
    from pptx.enum.text import PP_ALIGN
    from pptx.enum.shapes import MSO_SHAPE
    from pptx.dml.color import RGBColor
    plan = validate_plan(plan)
    prs = Presentation()
    prs.slide_width, prs.slide_height = Inches(13.333), Inches(7.5)
    n = len(plan['slides'])
    for idx, data in enumerate(plan['slides'], 1):
        slide = prs.slides.add_slide(prs.slide_layouts[6])
        layout, title = data['layout'], data['title']
        cover = layout in ('title', 'closing')
        _rect(slide, 0, 0, 13.333, 7.5, NAVY if cover else (255, 255, 255))
        if cover:
            _rect(slide, .8, 2.05, .11, 2.3, (85, 178, 238))
            _textbox(slide, 1.15, 2.05, 11.0, 1.35, title, size=37, bold=True, color=(255,255,255))
            _textbox(slide, 1.15, 3.55, 10.6, 1.0, data['subtitle'], size=20, color=(204,225,240))
        else:
            _rect(slide, 0, 0, 13.333, .13, BLUE)
            _textbox(slide, .78, .45, 11.8, .87, title, size=27, bold=True)
            if data['subtitle']:
                _textbox(slide, .8, 1.28, 11.7, .55, data['subtitle'], size=14, color=MUTED)
            top = 1.95 if data['subtitle'] else 1.65
            if layout == 'bullets':
                _bullets(slide, data['bullets'], .92, top+.2, 11.5, width=11.0, size=20 if len(data['bullets']) <= 4 else 18)
            elif layout == 'two_column':
                _rect(slide, .8, top, 5.74, 4.85, LIGHT, radius=True)
                _rect(slide, 6.8, top, 5.74, 4.85, LIGHT, radius=True)
                _bullets(slide, data['left'], 1.05, top+.3, 5.2, width=5.0, size=17)
                _bullets(slide, data['right'], 7.05, top+.3, 5.2, width=5.0, size=17)
            elif layout == 'flow':
                steps = data['bullets']
                count = len(steps)
                # Reserve space for visible, editable directional connectors.
                gap = .44
                blockw = min(3.1, (11.75-gap*(count-1))/count)
                left = (13.333-(blockw*count+gap*(count-1)))/2
                for j, step in enumerate(steps):
                    x=left+j*(blockw+gap)
                    # The block already carries its step number. Strip duplicated
                    # leading labels like '1.', '01 -', or 'Step 1:' from AI text.
                    step = re.sub(r'^\s*(?:(?:step\s*)?\d{1,2}\s*[.):-]\s*)', '', step, flags=re.I).strip() or step
                    _rect(slide,x,top+1.05,blockw,2.6,LIGHT, radius=True)
                    _textbox(slide,x+.18,top+1.28,blockw-.36,.55,str(j+1).zfill(2),22,True,BLUE)
                    _textbox(slide,x+.18,top+2.00,blockw-.36,1.15,step,15 if count <= 4 else 14,True)
                    if j < count - 1:
                        # Native PowerPoint chevron, not a raster illustration.
                        connector = slide.shapes.add_shape(
                            MSO_SHAPE.CHEVRON, Inches(x+blockw+.10),
                            Inches(top+2.13), Inches(gap-.20), Inches(.40))
                        connector.fill.solid()
                        connector.fill.fore_color.rgb = RGBColor(*BLUE)
                        connector.line.fill.background()
            elif layout in ('table', 'risk'):
                headers, rows = data['headers'], data['rows']
                # A balanced table gets generous, predictable height and larger fonts.
                # All table objects remain native/editable PowerPoint objects.
                table_shape = slide.shapes.add_table(len(rows)+1, len(headers), Inches(.75), Inches(top+.1), Inches(11.83), Inches(4.7))
                t = table_shape.table
                weights = [min(3.0, max(1.0, len(h)/14)) for h in headers]
                for row in rows:
                    for c, value in enumerate(row):
                        weights[c] = max(weights[c], min(4.2, len(value)/48 + .9))
                total = sum(weights)
                col_widths = [11.83 * w/total for w in weights]
                for c, col in enumerate(t.columns):
                    col.width = Inches(col_widths[c])
                sizes = {2: 17, 3: 16, 4: 15, 5: 13, 6: 12}
                base_font = sizes.get(len(headers), 12)
                # Wider cells can support bigger fonts; reduce only if text is dense.
                def row_units(values):
                    import math
                    max_lines = 1
                    for col_i, value in enumerate(values):
                        capacity = max(12, int(col_widths[col_i] * 10.5 * 16 / base_font))
                        max_lines = max(max_lines, math.ceil(len(str(value))/capacity))
                    return min(3, max_lines)
                units = [1.25] + [max(1.0, row_units(row) * .64) for row in rows]
                available = 4.7
                # Fill the allotted table region without overstretching a few rows.
                # Short tables get extra vertical space and are centered on the slide.
                natural_height = sum(units) * .69
                target_height = min(available, max(2.75, natural_height))
                unit_scale = target_height / sum(units)
                row_heights = [u * unit_scale for u in units]
                table_top = top + .1 + max(0.0, (available - target_height) / 2)
                table_shape.top = Inches(table_top)
                table_shape.height = Inches(target_height)
                for r, values in enumerate([headers]+rows):
                    t.rows[r].height = Inches(row_heights[r])
                    for c, val in enumerate(values):
                        cell = t.cell(r,c)
                        cell.text = val
                        cell.margin_left = cell.margin_right = Inches(.11)
                        cell.margin_top = cell.margin_bottom = Inches(.06)
                        cell.fill.solid()
                        cell.fill.fore_color.rgb = _rgb(BLUE if r == 0 else ((248,250,252) if r%2==0 else (234,242,248)))
                        for paragraph in cell.text_frame.paragraphs:
                            paragraph.font.name = 'Aptos'
                            paragraph.font.size = Pt(base_font)
                            paragraph.font.bold = (r == 0)
                            paragraph.font.color.rgb = _rgb((255,255,255) if r==0 else NAVY)
            elif layout == 'metrics':
                metrics = data['metrics']; spacing=.18
                cardw = min(3.9,(11.8-spacing*(len(metrics)-1))/len(metrics))
                x0=(13.333-(cardw*len(metrics)+spacing*(len(metrics)-1)))/2
                for m_idx, m in enumerate(metrics):
                    x=x0+m_idx*(cardw+spacing)
                    _rect(slide,x,top+.65,cardw,3.25,LIGHT,radius=True)
                    _textbox(slide,x+.18,top+.92,cardw-.36,.6,m['label'],15,color=MUTED)
                    _textbox(slide,x+.18,top+1.5,cardw-.36,1.1,m['value'],33,True,BLUE)
                    _textbox(slide,x+.18,top+2.66,cardw-.36,.64,m['note'],12,color=MUTED)
            else:
                raise PresentationQualityError('Unrecognized slide layout')
            _textbox(slide, .75, 7.06, 9.1, .25, plan['title'][:75], 9, color=(202,220,235) if cover else MUTED)
            _textbox(slide, 12.0, 7.03, .5, .3, f'{idx}/{n}', 9, color=(202,220,235) if cover else MUTED, align=PP_ALIGN.RIGHT)
    output = io.BytesIO()
    prs.save(output)
    result = output.getvalue()
    validate_pptx(result, n)
    return result


def validate_pptx(contents: bytes, expected_slides: int):
    from pptx import Presentation
    from pptx.util import Inches
    try:
        prs = Presentation(io.BytesIO(contents))
    except Exception as exc:
        raise PresentationQualityError('Generated PowerPoint cannot be reopened') from exc
    if len(prs.slides) != expected_slides:
        raise PresentationQualityError('Presentation slide count mismatch')
    tol = Inches(.03)
    for i, slide in enumerate(prs.slides, 1):
        if len(slide.shapes) < 3:
            raise PresentationQualityError(f'Slide {i} has too little content')
        for shape in slide.shapes:
            if shape.has_text_frame and shape.text.strip():
                if len(shape.text)>380:
                    raise PresentationQualityError(f'Slide {i} has an excessively long text box')
            if shape.has_table:
                for row in shape.table.rows:
                    for cell in row.cells:
                        if len(cell.text)>240:
                            raise PresentationQualityError(f'Slide {i} contains an oversized table cell')
            if shape.left < -tol or shape.top < -tol or shape.left + shape.width > prs.slide_width + tol or shape.top + shape.height > prs.slide_height + tol:
                raise PresentationQualityError(f'Slide {i} contains a shape outside the canvas')
    return True


def generate_presentation(prompt: str, provider: str,
                          progress: Callable[[str, int], None] | None = None) -> bytes:
    notify = progress or (lambda stage, pct: None)
    last = None
    instructions = prompt
    for attempt in range(3):
        notify('Planning slides' if attempt == 0 else 'Repairing slide plan', 18 + attempt*20)
        try:
            plan = validate_plan(_model(instructions, provider))
            notify('Rendering editable slides', 73)
            output = render_presentation(plan)
            notify('PowerPoint validated', 95)
            return output
        except PresentationQualityError as exc:
            last = exc
            instructions = (f'Generate the entire presentation again. Previous validation error: {str(exc)[:250]}.\nOriginal request: {prompt}')
    raise PresentationQualityError(f'PowerPoint generation failed: {last}')
