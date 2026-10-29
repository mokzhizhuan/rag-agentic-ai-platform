"""Patch Phase 7.7 document-progress hooks into an EXISTING project.

Usage: python install_patch.py "path/to/rag-fullstack-phase1"
Backs up every changed file and checks Python syntax before writing.
"""
from pathlib import Path
import ast
import re
import shutil
import sys
from datetime import datetime

ROOT = Path(sys.argv[1]).resolve() if len(sys.argv)>1 else Path.cwd().resolve()
ART = ROOT / 'backend' / 'artifacts'
LONG = ART / 'longform.py'
GEN = ART / 'generator.py'
WORKER = ART / 'management' / 'commands' / 'generation_worker.py'
FRONT = ROOT / 'frontend' / 'src' / 'App.tsx'
THIS = Path(__file__).resolve().parent
MARK = 'PHASE77_SECTION_PROGRESS_V1'


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def replace_one(source, old, new, filename):
    n=source.count(old)
    require(n==1, f'{filename}: expected exactly one occurrence of {old[:85]!r}, got {n}. No changes written.')
    return source.replace(old, new, 1)


def modify_long(s):
    if MARK in s: return s
    require('def generate_report_sections(' in s and 'def _ask(' in s, 'longform.py not recognized')
    s = 'from artifacts.progress import report_progress  # '+MARK+'\n'+s if not s.lstrip().startswith(('"""',"'''")) else s
    # Keep leading module docstrings intact, place import alongside existing imports.
    if 'from artifacts.progress import report_progress' not in s:
        s=replace_one(s,'from chat.providers import stream_generate',
              'from chat.providers import stream_generate\nfrom artifacts.progress import report_progress  # '+MARK, 'longform.py')
    # Scope injection to just report generator by splitting at function def.
    head, tail = s.split('def generate_report_sections(',1)
    tail = 'def generate_report_sections(' + tail
    require('    sections = []' in tail and '    for ' in tail and '    return title, sections' in tail, 'report generator structure differs from the known version')
    # Use exact commonly present stage boundaries; indented variable name may vary by version.
    tail = replace_one(tail, '    raw = _ask(', '    report_progress("Planning report outline", 12)\n    raw = _ask(', 'longform.py report')
    tail = replace_one(tail, '    sections = []',
        '    report_progress(f"Outline ready — {len(names)} sections", 18)\n    sections = []', 'longform.py report')
    if '    for n, heading in enumerate(names):' in tail:
        tail=replace_one(tail,'    for n, heading in enumerate(names):',
            '    for n, heading in enumerate(names):\n'
            '        report_progress(f"Generating section {n+1} of {len(names)}: {str(heading)[:75]}", 18 + (n * 67 // len(names)))', 'longform.py report')
        tail=replace_one(tail,"        sections.append({'heading':heading,'body':body})",
            "        sections.append({'heading':heading,'body':body})\n"
            "        report_progress(f\"Completed section {n+1} of {len(names)}\", 18 + ((n+1) * 67 // len(names)))", 'longform.py report')
    elif '    for index, heading in enumerate(names, start=1):' in tail:
        tail=replace_one(tail,'    for index, heading in enumerate(names, start=1):',
            '    for index, heading in enumerate(names, start=1):\n'
            '        report_progress(f"Generating section {index} of {len(names)}: {str(heading)[:75]}", 18 + ((index-1) * 67 // len(names)))', 'longform.py report')
        target="        sections.append({\n            \"heading\": heading,\n            \"body\": body,\n        })"
        # For the more recent retry-based report generator.
        if target not in tail:
            target="        sections.append({'heading': heading, 'body': body})"
        tail=replace_one(tail,target,target+'\n        report_progress(f"Completed section {index} of {len(names)}", 18 + (index * 67 // len(names)))','longform.py report')
    else:
        raise RuntimeError('Unrecognized report-section loop; no changes written')
    tail=replace_one(tail, '    return title, sections',
        '    report_progress("All sections generated — assembling document", 87)\n    return title, sections', 'longform.py report')
    return head+tail


def modify_generator(s):
    if MARK in s: return s
    require('def create_artifact(' in s, 'generator.py not recognized')
    s=replace_one(s,'from .longform import generate_long_code, generate_report_sections, LongformError',
        'from .longform import generate_long_code, generate_report_sections, LongformError\n'
        'from .progress import report_progress  # '+MARK, 'generator.py')
    # Reportlab and DOCX generate_report_sections in shared path; signal actual file save next.
    s=replace_one(s, "    elif fmt == 'word':", "    elif fmt == 'word':\n        report_progress('Formatting Word document', 91)", 'generator.py')
    s=replace_one(s, "    elif fmt == 'pdf':", "    elif fmt == 'pdf':\n        report_progress('Rendering PDF pages', 91)", 'generator.py')
    # Avoid saying 100% until artifact view has persisted output.
    s=replace_one(s, "    if not contents:\n", "    if fmt in ('word', 'pdf', 'markdown'):\n        report_progress('File generated — saving artifact', 97)\n    if not contents:\n", 'generator.py')
    return s


def modify_worker(s):
    if MARK in s: return s
    require('def process_job(job_id):' in s, 'worker process_job not found')
    # Some installations contain a duplicate import or mention this import in a comment.
    # Match the exact standalone import statement, and update only the first one.
    import_pattern = r'(?m)^from artifacts\.jobs import GenerationJob[ \t]*$'
    matches = list(re.finditer(import_pattern, s))
    require(bool(matches), 'worker: cannot find a standalone GenerationJob import. No changes written.')
    s = re.sub(
        import_pattern,
        'from artifacts.jobs import GenerationJob\n'
        'from artifacts.progress import bind_progress, reset_progress  # ' + MARK,
        s,
        count=1,
    )
    if len(matches) > 1:
        print(f'NOTICE: worker has {len(matches)} matching imports; patched the first one.')
    # Do not reset started_at when already claimed.
    s=s.replace(",started_at=timezone.now())\n    try:", ")\n    try:", 1)
    # Instrument each actual endpoint invocation, including workers with
    # multiple branches. Ignore comments and non-invocation text.
    endpoint_pattern = re.compile(
        r'(?m)^([ \t]*)result[ \t]*=[ \t]*create_artifact_endpoint\(req\)[ \t]*$'
    )
    matches = list(endpoint_pattern.finditer(s))
    require(matches, 'worker: no endpoint invocation lines found. No changes written.')

    def wrap_endpoint(match):
        indent = match.group(1)
        lines = [
            'def on_progress(stage, percent):',
            '    # Save actual milestones, never mark complete until artifact persistence.',
            "    GenerationJob.objects.filter(pk=job_id, status='running').update(",
            '        stage=stage, percent=percent',
            '    )',
            "    log.info('Job #%s [%s%%] %s', job_id, percent, stage)",
            'progress_token = bind_progress(on_progress)',
            'try:',
            '    result=create_artifact_endpoint(req)',
            'finally:',
            '    reset_progress(progress_token)',
        ]
        # This replacement uses each original call's indentation.
        return '\n'.join(indent + line for line in lines)

    s = endpoint_pattern.sub(wrap_endpoint, s)
    if len(matches) > 1:
        print(f'NOTICE: worker has {len(matches)} endpoint call sites; instrumented each one.')
    return s


def modify_front(s):
    if MARK in s: return s
    old="{job.status==='running'&&<progress style={{width:'100%',marginTop:6}} aria-label=\"Generation in progress\" />}"
    new="{job.status==='running'&&<progress style={{width:'100%',marginTop:6}} value={job.percent??0} max={100} aria-label=\"Completed workflow milestones\" />}"
    if old not in s:
        print('NOTICE: App.tsx progress element differs; frontend left unchanged.')
        return s
    prior=s
    s=replace_one(s,old,new,'App.tsx')
    old="{job.status==='running'?'Working — percentage unavailable from the model':`${job.percent??0}%`}"
    new="{job.status==='running'?`${job.percent??0}% — completed workflow milestones (not model thinking)`:`${job.percent??0}%`}"
    if old not in s:
        print('NOTICE: App.tsx progress label differs; frontend left unchanged.')
        return prior
    s=replace_one(s,old,new,'App.tsx')
    return '// '+MARK+'\n'+s


def main():
    for f in (LONG,GEN,WORKER):
        require(f.is_file(), f'Missing file: {f}')
    patches={LONG:modify_long,GEN:modify_generator,WORKER:modify_worker}
    if FRONT.exists(): patches[FRONT]=modify_front
    ready={}
    for f, func in patches.items():
        original=f.read_text(encoding='utf-8')
        updated=func(original)
        if updated != original and f.suffix=='.py': ast.parse(updated,filename=str(f))
        ready[f]=(original,updated)
    stamp=datetime.now().strftime('%Y%m%d-%H%M%S')
    for f,(original,updated) in ready.items():
        if updated==original:
            print('ALREADY PATCHED:', f.relative_to(ROOT)); continue
        backup=f.with_name(f.name+'.backup-'+stamp)
        shutil.copy2(f, backup)
        f.write_text(updated,encoding='utf-8')
        print('PATCHED:',f.relative_to(ROOT),'backup:',backup.name)
    target=ART/'progress.py'
    if target.exists():
        require('def bind_progress(' in target.read_text(encoding='utf-8'), 'Existing progress.py conflict')
        print('EXISTS:',target.relative_to(ROOT))
    else:
        shutil.copy2(THIS/'progress.py',target)
        print('ADDED:',target.relative_to(ROOT))
    print('Finished. Rebuild backend and restart worker. No migrations required.')

if __name__=='__main__':
    main()
