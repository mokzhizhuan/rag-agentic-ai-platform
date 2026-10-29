"""Safely install Phase 8.4 diagnostics. Dry-run by default; no backend edits."""
from pathlib import Path
from datetime import datetime
import argparse, shutil, re

p=argparse.ArgumentParser()
p.add_argument('project_root',nargs='?',default='.')
p.add_argument('--apply',action='store_true')
a=p.parse_args()
root=Path(a.project_root).resolve()
app=root/'frontend/src/App.tsx'
shell=root/'frontend/src/phase8-shell.css'
css=root/'frontend/src/phase8-diagnostics.css'
src=Path(__file__).with_name('phase8-diagnostics.css')
if not app.is_file() or not shell.is_file(): raise SystemExit('Requires existing Phase 8 App.tsx and phase8-shell.css. No changes made.')
s=app.read_text(encoding='utf-8')
if 'className="diagnostics-studio"' in s:
    print('Diagnostics already installed; no App.tsx changes needed.')
    updated=s
else:
    # Preserve all handlers and only add an independent fourth tab.
    tag="useState<'chat'|'documents'|'create'>('chat')"
    if s.count(tag)!=1: raise SystemExit('Unexpected tab state; no changes made.')
    updated=s.replace(tag,"useState<'chat'|'documents'|'create'|'diagnostics'>('chat')",1)
    nav_end="onClick={()=>setTab('create')}>Create Files</button>"
    if updated.count(nav_end)!=1: raise SystemExit('Could not uniquely identify Create Files navigation; no changes made.')
    updated=updated.replace(nav_end,nav_end+"<button className={tab==='diagnostics'?'selected':''} onClick={()=>setTab('diagnostics')}>Diagnostics</button>",1)
    # Insert separate ternary branch immediately before the knowledge section.
    # Does not depend on the Knowledge Base page heading.
    pat=r'(</section>\s*:\s*)(<section(?:\s+className="knowledge-studio")?\s*>\s*<h2>[^<]*Knowledge Base</h2>)'
    matches=list(re.finditer(pat,updated))
    if len(matches)!=1: raise SystemExit(f'Could not uniquely locate Knowledge Base branch ({len(matches)}); no changes made.')
    diag='''<section className="diagnostics-studio">
      <h2>Diagnostics</h2>
      <p className="diagnostics-intro">Account activity and artifact-generation status from existing API responses. This page does not probe infrastructure or execute generated code.</p>
      <div className="diagnostics-actions"><button type="button" onClick={()=>{void Promise.all([refresh(),refreshArtifacts(),refreshGenerationJobs()]).catch(e=>setError(String(e)));}}>Refresh diagnostics</button><span className="diagnostics-intro">Displayed data is a snapshot of the latest successful requests.</span></div>
      <div className="diagnostics-grid">
        <div className="diagnostics-stat"><span>Knowledge documents</span><strong>{docs.length}</strong></div>
        <div className="diagnostics-stat"><span>Generated artifacts</span><strong>{artifacts.length}</strong></div>
        <div className="diagnostics-stat"><span>Running / queued jobs</span><strong>{generationJobs.filter(j=>j.status==='running'||j.status==='queued').length}</strong></div>
        <div className="diagnostics-stat"><span>Failed jobs in loaded history</span><strong>{generationJobs.filter(j=>j.status==='failed').length}</strong></div>
      </div>
      <div className="diagnostics-cards">
        <article className="diagnostics-card"><h3>Generation activity</h3><ul>{generationJobs.length===0?<li>No generation jobs returned.</li>:generationJobs.slice(0,10).map(j=><li key={j.id}><span className="diagnostics-tag">#{j.id} · {j.status}</span> {j.stage||'No stage reported'} · {j.percent??0}%{j.error&&<p>Reported error: {j.error}</p>}</li>)}</ul></article>
        <article className="diagnostics-card"><h3>Current workspace settings</h3><ul><li>Selected AI provider: <strong>{provider==='openai'?'OpenAI':'Ollama'}</strong> (selection only; connectivity not tested)</li><li>Chat routing mode: <strong>{mode}</strong> (selection only)</li><li>Knowledge documents indexed/ready: <strong>{docs.filter(d=>d.status==='ready').length}</strong> of {docs.length}</li><li>Available ZIP artifacts: <strong>{artifacts.filter(a=>a.format==='zip'||a.filename.toLowerCase().endsWith('.zip')).length}</strong></li><li>Most recent job: <strong>{generationJobs.length?`#${generationJobs[0].id} (${generationJobs[0].status})`:'None reported'}</strong></li></ul></article>
      </div>
      <div className="diagnostics-note"><strong>Scope of diagnostics:</strong> Counts describe records returned for the signed-in account; the jobs API may return a limited history. This is not a real-time health monitor. Keycloak session health, PostgreSQL availability, Ollama connectivity, response latency, model tokens and pgvector similarity are not measured here. No simulated metrics are shown.</div>
    </section>:'''
    updated=re.sub(pat,lambda m:m.group(1).replace(':',":tab==='diagnostics'?",1)+diag+m.group(2),updated,count=1)
    imp="import './phase8-diagnostics.css';"
    if imp not in updated: updated=imp+'\n'+updated
# No partial edits if dry run.
print('App.tsx modification:',updated!=s)
print('CSS target:',css)
if not a.apply:
    print('Dry run OK; use --apply to install.');raise SystemExit(0)
stamp=datetime.now().strftime('%Y%m%d-%H%M%S')
if updated!=s:
    shutil.copy2(app,app.with_name(app.name+'.bak-'+stamp))
    app.write_text(updated,encoding='utf-8')
if css.is_file(): shutil.copy2(css,css.with_name(css.name+'.bak-'+stamp))
shutil.copy2(src,css)
print('Phase 8.4 installed. Backend untouched.')
