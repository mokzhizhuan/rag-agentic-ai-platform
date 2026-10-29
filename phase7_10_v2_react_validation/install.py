"""Patch existing project safely; dry-run unless --apply."""
from pathlib import Path
import argparse
import shutil
from datetime import datetime

p = argparse.ArgumentParser()
p.add_argument('root', nargs='?', default='.')
p.add_argument('--apply', action='store_true')
a = p.parse_args()
root = Path(a.root).resolve()
source = Path(__file__).resolve().parent
backend = root/'backend/artifacts'
urls = backend/'urls.py'
frontend = root/'frontend/src/App.tsx'
required = [urls, frontend, backend/'models.py', backend/'views.py']
missing = [str(x) for x in required if not x.is_file()]
if missing:
    raise SystemExit('Missing required project files: '+', '.join(missing))
urltext = urls.read_text(encoding='utf-8')
uitext = frontend.read_text(encoding='utf-8')
if 'urlpatterns' not in urltext:
    raise SystemExit('Unexpected artifacts/urls.py; no files changed')
if 'artifacts.map(a=>' not in uitext or 'downloadArtifact(a)' not in uitext:
    raise SystemExit('Unexpected App.tsx layout; no files changed. Please share latest App.tsx.')
# Don't guess if source differs: only patch unique anchor points.
if uitext.count('artifacts.map(a=>') != 1 or uitext.count('downloadArtifact(a)') != 1:
    raise SystemExit('Ambiguous App.tsx anchors; no files changed')
if 'project_validation_views' not in urltext:
    urltext = 'from . import project_validation_views\n' + urltext
    anchor = 'urlpatterns = ['
    urltext = urltext.replace(anchor, anchor+"\n    path('<int:pk>/validate-project/', project_validation_views.validate_zip_artifact),", 1)
if 'validateZipProject' not in uitext:
    anchor = '  async function downloadArtifact(a:Artifact){'
    if anchor not in uitext:
        raise SystemExit('Missing downloadArtifact function anchor; no changes')
    state_anchor = "  const [artifacts,setArtifacts]=useState<Artifact[]>([]);"
    if state_anchor not in uitext:
        raise SystemExit('Missing artifacts state anchor; no changes')
    uitext = uitext.replace(state_anchor, state_anchor+"\n  const [zipReports,setZipReports]=useState<Record<number,ZipValidationReport>>({});\n  const [zipValidating,setZipValidating]=useState<number|null>(null);\n  const [zipValidationErrors,setZipValidationErrors]=useState<Record<number,string>>({});",1)
    type_anchor = 'type Artifact='
    pos = uitext.find(type_anchor)
    if pos < 0:
        raise SystemExit('Missing Artifact type; no changes')
    uitext = uitext[:pos] + "type ZipValidationFinding={severity:string;rule:string;file:string;message:string};\ntype ZipValidationReport={summary:{error:number;warning:number;info:number};files_analyzed:number;findings:ZipValidationFinding[];limitations:string[]};\n" + uitext[pos:]
    fn = '''  async function validateZipProject(a:Artifact){
    if(zipValidating!==null)return;
    setZipValidating(a.id);
    setZipValidationErrors(v=>({...v,[a.id]:''}));
    try{
      const result=await api(`/api/artifacts/${a.id}/validate-project/`,{method:'POST'});
      setZipReports(v=>({...v,[a.id]:result.report as ZipValidationReport}));
    }catch(e){setZipValidationErrors(v=>({...v,[a.id]:String(e)}));}
    finally{setZipValidating(null);}
  }
  async function downloadZipReport(a:Artifact){
    try{
      await keycloak.updateToken(30);
      const response=await fetch(API+`/api/artifacts/${a.id}/validate-project/`,{headers:{Authorization:`Bearer ${keycloak.token}`}});
      if(!response.ok)throw new Error('Report download failed: HTTP '+response.status);
      const blob=await response.blob();const url=URL.createObjectURL(blob);
      const link=document.createElement('a');link.href=url;link.download=a.filename.replace(/\\.zip$/i,'')+'.validation.md';document.body.append(link);link.click();link.remove();
      setTimeout(()=>URL.revokeObjectURL(url),30000);
    }catch(e){setZipValidationErrors(v=>({...v,[a.id]:String(e)}));}
  }
'''
    uitext = uitext.replace(anchor, fn+anchor,1)
    button_anchor = '<button onClick={()=>void downloadArtifact(a)}>Download</button>'
    if button_anchor not in uitext:
        raise SystemExit('Missing download button; no changes')
    uitext = uitext.replace(button_anchor, "{(a.format==='zip'||a.filename.toLowerCase().endsWith('.zip'))&&<button type=\"button\" disabled={zipValidating!==null} onClick={()=>void validateZipProject(a)}>{zipValidating===a.id?'Validating...':'Validate Project'}</button>}"+button_anchor,1)
    # Place report below the artifact action line, before the existing preview section.
    report_anchor = '{previewArtifactId===a.id&&<div'
    if report_anchor not in uitext:
        raise SystemExit('Missing preview anchor; no changes')
    panel = '''{zipValidationErrors[a.id]&&<div role="alert" style={{flexBasis:'100%',color:'#ba2525',overflowWrap:'anywhere'}}>{zipValidationErrors[a.id]}</div>}
            {zipReports[a.id]&&<div style={{flexBasis:'100%',padding:12,marginTop:8,background:'#f5f8fc',border:'1px solid #d7e0ea',borderRadius:8}}>
              <strong>Project validation: {zipReports[a.id].summary.error} errors · {zipReports[a.id].summary.warning} warnings · {zipReports[a.id].summary.info} info</strong>
              <p className="muted">{zipReports[a.id].files_analyzed} files checked · Static analysis only; project code was not executed.</p>
              {zipReports[a.id].findings.length===0?<p>No findings from the implemented checks.</p>:<ul>{zipReports[a.id].findings.map((f,i)=><li key={i}><strong>{f.severity.toUpperCase()}</strong> · {f.file||'(project)'} · {f.message}</li>)}</ul>}
              <details><summary>Validation limitations</summary><ul>{zipReports[a.id].limitations.map((s,i)=><li key={i}>{s}</li>)}</ul></details>
              <button type="button" onClick={()=>void downloadZipReport(a)}>Download report (.md)</button>
            </div>}
            '''
    uitext = uitext.replace(report_anchor,panel+report_anchor,1)
print('Compatible project:',root)
print('Changes: add 2 validation modules, add Django route, patch frontend ZIP action/report panel.')
if not a.apply:
    print('Dry-run only; add --apply to install.')
    raise SystemExit(0)
changes={urls:urltext,frontend:uitext,backend/'project_validation.py':(source/'project_validation.py').read_text(encoding='utf-8'),backend/'project_validation_views.py':(source/'project_validation_views.py').read_text(encoding='utf-8')}
backup_tag=datetime.now().strftime('%Y%m%d-%H%M%S')
for target,content in changes.items():
    if target.exists() and target.read_text(encoding='utf-8')==content:
        continue
    if target.exists():
        shutil.copy2(target,target.with_name(target.name+'.bak-'+backup_tag))
    target.write_text(content,encoding='utf-8')
    print('Updated:',target)
print('Installed. Rebuild backend + frontend and restart worker only if needed.')
