"""Conservative Phase 7.7 document quality installer. Run from project root.
Supports --dry-run; writes .bak timestamped copies only after all checks pass.
"""
import argparse
import ast
import datetime
import pathlib
import re
import shutil

START = '# PHASE7_7_DOCUMENT_QUALITY_START'
END = '# PHASE7_7_DOCUMENT_QUALITY_END'


def patch_generator(original):
    if START in original:
        return original, False
    # Match actual word/PDF branch, leave the generated sections, progress and
    # all other formats untouched.
    begin = re.search(r'^    elif fmt == [\'"]word[\'"]:\s*$', original, re.M)
    finish = re.search(r'^    elif fmt == [\'"]powerpoint[\'"]:\s*$', original, re.M)
    if not begin or not finish or finish.start() <= begin.start():
        raise RuntimeError('Could not uniquely locate existing Word/PDF rendering branches; no files changed.')
    if len(re.findall(r'^    elif fmt == [\'"]word[\'"]:',original,re.M)) != 1 or len(re.findall(r'^    elif fmt == [\'"]powerpoint[\'"]:',original,re.M)) != 1:
        raise RuntimeError('Ambiguous render branches; no files changed.')
    block='''    elif fmt == 'word':
        # PHASE7_7_DOCUMENT_QUALITY_START
        from .document_quality import render_word
        buf.write(render_word(title, sections))
    elif fmt == 'pdf':
        from .document_quality import render_pdf
        buf.write(render_pdf(title, sections))
        # PHASE7_7_DOCUMENT_QUALITY_END
'''
    updated=original[:begin.start()]+block+original[finish.start():]
    # Markdown is generated in a prior custom branch. Normalize the return
    # on that branch only, without changing staged progress or other formats.
    md_branch=re.search(r"^    if fmt == ['\"]markdown['\"]:\s*$",updated,re.M)
    if md_branch:
        next_branch=re.search(r'^    (?:if|elif) fmt\b', updated[md_branch.end():],re.M)
        if not next_branch:
            raise RuntimeError('Markdown branch boundary cannot be determined; no files changed.')
        first=md_branch.end(); last=first+next_branch.start()
        fragment=updated[first:last]
        # Look for markdown document returned directly by the previous staged branch.
        returned=re.search(r'^(\s*)return fmt, (\w+)\.encode\([\'"]utf-8[\'"]\)\s*$',fragment,re.M)
        if returned:
            pad=returned.group(1)
            var=returned.group(2)
            replacement=(f'{pad}from .document_quality import markdown_document, normalize_sections\n'
                         f'{pad}title, sections = normalize_sections(title, sections)\n'
                         f'{pad}return fmt, markdown_document(title, sections)')
            fragment=fragment[:returned.start()]+replacement+'\n'+fragment[returned.end():].lstrip('\n')
            updated=updated[:first]+fragment+updated[last:]
        else:
            raise RuntimeError('Markdown branch found but unexpected return statement; no files changed.')
    else:
        print('NOTICE: no standalone Markdown branch. Word/PDF patched; Markdown left unchanged.')
    ast.parse(updated)
    return updated, True


def main():
    p=argparse.ArgumentParser()
    p.add_argument('root',nargs='?',default='.')
    p.add_argument('--dry-run',action='store_true')
    args=p.parse_args()
    root=pathlib.Path(args.root).resolve()
    generator=root/'backend'/'artifacts'/'generator.py'
    target=root/'backend'/'artifacts'/'document_quality.py'
    src=pathlib.Path(__file__).with_name('document_quality.py')
    if not generator.exists() or not (root/'backend'/'artifacts'/'longform.py').exists():
        raise SystemExit('Project root not found: expected backend/artifacts/generator.py and longform.py')
    original=generator.read_text(encoding='utf-8')
    updated,changed=patch_generator(original)
    module=src.read_text(encoding='utf-8')
    ast.parse(module)
    if target.exists() and target.read_text(encoding='utf-8') != module:
        raise SystemExit('document_quality.py already exists but differs; backup and reconcile manually.')
    print('Generator: '+('patch needed' if changed else 'already patched'))
    print('Formatter: '+('already present' if target.exists() else 'will install'))
    if args.dry_run:return
    stamp=datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    if changed:
        backup=generator.with_name(generator.name+'.'+stamp+'.bak')
        shutil.copy2(generator,backup)
        generator.write_text(updated,encoding='utf-8')
        print('Backup:',backup)
    if not target.exists():
        shutil.copy2(src,target)
    print('Installed. No schema changes. Restart/rebuild backend AND worker.')

if __name__=='__main__':main()
