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


MAX_SLIDES = 16
MAX_OUTPUT = 45000
NAVY = (23, 42, 66)
BLUE = (34, 99, 164)
LIGHT = (240, 245, 250)
MUTED = (93, 108, 125)


def _model(prompt: str, provider: str) -> str:
    schema = '''Return exactly one JSON object, no Markdown, with keys:
{"title":"...","subtitle":"...","slides":[{"layout":"title|bullets|two_column|table|metrics|closing","title":"...","subtitle":"...","bullets":["..."],"left":["..."],"right":["..."],"headers":["..."],"rows":[["..."]],"metrics":[{"label":"...","value":"...","note":"..."}]}]}.
Produce 5–12 coherent slides (maximum 16). Give concise titles (max 80 chars), 2–5 bullets max 130 chars each, 2–4 items per two-column side, tables with 2–5 headers and 1–8 rows, and up to 4 metrics. Choose layout appropriately. Use only facts provided; use TBD for unknown numbers. Avoid unnecessary duplicate intro slides. No Markdown/code fences, image URLs, or other keys. Every slide must contain meaningful content. Design for 16:9 and concise on-slide copy.'''
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
    allowed = {'title', 'bullets', 'two_column', 'table', 'metrics', 'closing'}
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
                 'bullets': _strings(item.get('bullets'), 6, 160),
                 'left': _strings(item.get('left'), 5, 150),
                 'right': _strings(item.get('right'), 5, 150)}
        if layout == 'bullets' and not slide['bullets']:
            raise PresentationQualityError(f'Slide {idx} has no bullets')
        if layout == 'two_column' and (not slide['left'] or not slide['right']):
            raise PresentationQualityError(f'Slide {idx} lacks column content')
        if layout == 'table':
            headers = _strings(item.get('headers'), 5, 40)
            raw_rows = item.get('rows', [])
            if not 2 <= len(headers) <= 5 or not isinstance(raw_rows, list) or not 1 <= len(raw_rows) <= 9:
                raise PresentationQualityError(f'Slide {idx} has invalid table dimensions')
            rows = []
            for r in raw_rows:
                if not isinstance(r, list) or len(r) != len(headers):
                    raise PresentationQualityError(f'Slide {idx} has mismatched table cells')
                rows.append([str(c or '')[:105] for c in r])
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
            'slides': cleaned}


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
            elif layout == 'table':
                headers, rows = data['headers'], data['rows']
                t = slide.shapes.add_table(len(rows)+1, len(headers), Inches(.75), Inches(top+.1), Inches(11.83), Inches(min(4.9, .46*(len(rows)+1)+.4))).table
                for col in t.columns:
                    col.width = Inches(11.83/len(headers))
                for r, values in enumerate([headers]+rows):
                    t.rows[r].height = Inches(min(.72, 4.85/(len(rows)+1)))
                    for c, val in enumerate(values):
                        cell = t.cell(r,c); cell.text = val
                        cell.margin_left = cell.margin_right = Inches(.1)
                        cell.margin_top = cell.margin_bottom = Inches(.045)
                        cell.fill.solid(); cell.fill.fore_color.rgb = _rgb(BLUE if r == 0 else ((248,250,252) if r%2==0 else (234,242,248)))
                        for paragraph in cell.text_frame.paragraphs:
                            paragraph.font.name = 'Aptos'
                            paragraph.font.size = Pt(12 if len(headers)>=4 or len(rows)>=7 else 14)
                            paragraph.font.bold = (r==0)
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
