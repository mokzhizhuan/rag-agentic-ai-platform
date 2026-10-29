"""Phase 8.4 failed-job cleanup: dry-run by default; fail closed on unexpected code."""
from pathlib import Path
from datetime import datetime
import argparse, shutil, re, ast

p=argparse.ArgumentParser()
p.add_argument('project_root',nargs='?',default='.')
p.add_argument('--apply',action='store_true')
a=p.parse_args()
root=Path(a.project_root).resolve()
job=root/'backend/artifacts/job_views.py'
urls=root/'backend/artifacts/urls.py'
app=root/'frontend/src/App.tsx'
css=root/'frontend/src/phase8-failed-cleanup.css'
files=(job,urls,app)
if any(not f.is_file() for f in files): raise SystemExit('Missing expected project files. No changes made.')
old={f:f.read_text(encoding='utf-8') for f in files}
s={f:old[f] for f in files}

# New owner-scoped endpoints, keeping the existing cancellation endpoint intact.
backend_marker='def remove_failed_generation_job(request, pk):'
if backend_marker not in s[job]:
    extra='''

# PHASE8_4_FAILED_JOB_CLEANUP_V1: cleanup is distinct from cancellation.
@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def remove_failed_generation_job(request, pk):
    """Remove only the current user's failed job, never a live or successful job."""
    with transaction.atomic():
        job = get_object_or_404(
            GenerationJob.objects.select_for_update(), pk=pk, owner_sub=request.user.sub
        )
        if job.status != 'failed' or job.artifact_id is not None:
            return Response({'detail': 'Only failed jobs without an artifact can be removed.'}, status=409)
        paths = [upload.file.name for upload in job.uploads.all() if upload.file.name]
        storage = GenerationJobInput._meta.get_field('file').storage
        job.delete()
        # Delete private uploaded-input files only after DB commit succeeds.
        transaction.on_commit(lambda: _delete_job_uploads(storage, paths))
    return Response({'deleted': 1, 'job_id': pk})


def _delete_job_uploads(storage, paths):
    for path in paths:
        try:
            storage.delete(path)
        except Exception:
            import logging
            logging.getLogger(__name__).exception('Unable to clean up failed-job input %s', path)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def remove_all_failed_generation_jobs(request):
    """Remove all failed jobs owned by this account; no dependency on a 30-job listing."""
    with transaction.atomic():
        queryset = GenerationJob.objects.select_for_update().filter(
            owner_sub=request.user.sub, status='failed', artifact_id__isnull=True
        )
        job_ids = list(queryset.values_list('id', flat=True))
        uploads = GenerationJobInput.objects.filter(job_id__in=job_ids)
        paths = [upload.file.name for upload in uploads if upload.file.name]
        storage = GenerationJobInput._meta.get_field('file').storage
        GenerationJob.objects.filter(id__in=job_ids).delete()
        transaction.on_commit(lambda: _delete_job_uploads(storage, paths))
    return Response({'deleted': len(job_ids)})
'''
    s[job]+=extra
ast.parse(s[job])

route1='path("jobs/failed/", job_views.remove_all_failed_generation_jobs),'
route2='path("jobs/<int:pk>/remove-failed/", job_views.remove_failed_generation_job),'
if route1 not in s[urls]:
    anchor='path("jobs/", job_views.generation_jobs),'
    if s[urls].count(anchor)!=1:raise SystemExit('Cannot find jobs route exactly once. No changes made.')
    s[urls]=s[urls].replace(anchor,route1+'\n    '+route2+'\n    '+anchor,1)

# Frontend handlers are added before the stable generation function.
func_marker='async function removeFailedGenerationJob(id:number)'
if func_marker not in s[app]:
    anchor='async function generateArtifact(){'
    if s[app].count(anchor)!=1:raise SystemExit('Cannot find generateArtifact() anchor. No changes made.')
    handlers='''async function removeFailedGenerationJob(id:number){
    if(!window.confirm(`Remove failed generation job #${id}? This removes its failed-job history and uploaded inputs, not generated files.`))return;
    try{
      await api(`/api/artifacts/jobs/${id}/remove-failed/`,{method:'DELETE'});
      await refreshGenerationJobs();
    }catch(e){setError(String(e));}
  }

  async function removeAllFailedGenerationJobs(){
    if(!window.confirm('Remove ALL failed generation jobs belonging to your account, including older jobs not displayed here? Generated files and completed jobs will be kept.'))return;
    try{
      const result=await api('/api/artifacts/jobs/failed/',{method:'DELETE'});
      await refreshGenerationJobs();
      setNotice(`Removed ${result.deleted} failed generation job(s).`);
    }catch(e){setError(String(e));}
  }

  '''
    s[app]=s[app].replace(anchor,handlers+anchor,1)

# Insert both actions only on Diagnostics; the job row can remain compact.
css_import="import './phase8-failed-cleanup.css';"
if css_import not in s[app]: s[app]=css_import+'\n'+s[app]
header='<article className="diagnostics-card"><h3>Generation activity</h3><ul>'
new_header='''<article className="diagnostics-card"><div className="failed-cleanup-toolbar"><h3>Generation activity</h3>{generationJobs.some(j=>j.status==='failed')&&<button type="button" className="failed-cleanup-all" onClick={()=>void removeAllFailedGenerationJobs()}>Remove All Failed Jobs</button>}</div><ul>'''
if new_header not in s[app]:
    if s[app].count(header)!=1:raise SystemExit('Diagnostics activity anchor missing; Phase 8.4 must be installed. No changes made.')
    s[app]=s[app].replace(header,new_header,1)
old_row='<span className="diagnostics-tag">#{j.id} · {j.status}</span> {j.stage||\'No stage reported\'} · {j.percent??0}%{j.error&&<p>Reported error: {j.error}</p>}'
new_row='<span className="diagnostics-tag">#{j.id} · {j.status}</span> {j.stage||\'No stage reported\'} · {j.percent??0}%{j.error&&<p>Reported error: {j.error}</p>}{j.status===\'failed\'&&<button type="button" className="failed-cleanup-one" onClick={()=>void removeFailedGenerationJob(j.id)} aria-label={`Remove failed job ${j.id}`}>Remove</button>}'
if new_row not in s[app]:
    if s[app].count(old_row)!=1:raise SystemExit('Diagnostics job-row anchor missing; no files changed.')
    s[app]=s[app].replace(old_row,new_row,1)

print('Dry-run checks passed.')
for f in files:print(f.relative_to(root), 'change' if old[f]!=s[f] else 'unchanged')
print(css.relative_to(root),'update')
if not a.apply:
    print('No files changed. Run with --apply to install.')
    raise SystemExit(0)
stamp=datetime.now().strftime('%Y%m%d-%H%M%S')
for f in files:
    if old[f]!=s[f]:
        shutil.copy2(f,f.with_name(f.name+'.bak-'+stamp))
        f.write_text(s[f],encoding='utf-8')
if css.exists():shutil.copy2(css,css.with_name(css.name+'.bak-'+stamp))
shutil.copy2(Path(__file__).with_name('phase8-failed-cleanup.css'),css)
print('Phase 8.4 failed-job cleanup installed. Existing cancel endpoint untouched.')
