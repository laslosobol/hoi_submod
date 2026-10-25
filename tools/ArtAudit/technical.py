"""Read-only active Verenian artwork audit; writes only final-review/technical.json.
Pixel heuristics identify review candidates, not semantic or visual QA failures.
"""
import hashlib
import json
import re
import runpy
import subprocess
import sys
from collections import deque
from pathlib import Path
import numpy as np
from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'art/verenia/final-review/technical.json'

def load(path):
    return json.loads((ROOT/path).read_text(encoding='utf-8-sig'))

def sha(path):
    return hashlib.sha256((ROOT/path).read_bytes()).hexdigest()

def metrics(image, portrait):
    rgba = np.asarray(image.convert('RGBA'))
    a = rgba[:,:,3]
    edge = np.concatenate((a[0], a[-1], a[1:-1,0], a[1:-1,-1]))
    corners = [int(a[y,x]) for y,x in ((0,0),(0,-1),(-1,0),(-1,-1))]
    scaled = image.convert('RGBA').copy();scaled.thumbnail((160,160))
    small = np.asarray(scaled)[:,:,3]
    occupied = small > 16
    interior = occupied.copy()
    # Exclude silhouette anti-aliasing from interior-transparency estimate.
    for dy,dx in ((0,2),(0,-2),(2,0),(-2,0),(2,2),(-2,-2),(2,-2),(-2,2)):
        interior &= np.roll(np.roll(occupied,dy,axis=0),dx,axis=1)
    interior[:2]=False;interior[-2:]=False;interior[:,:2]=False;interior[:,-2:]=False
    low = small < 16
    outside = np.zeros_like(low)
    h,w=low.shape;q=deque()
    for y in range(h):
        for x in (0,w-1):
            if low[y,x] and not outside[y,x]:outside[y,x]=True;q.append((y,x))
    for x in range(w):
        for y in (0,h-1):
            if low[y,x] and not outside[y,x]:outside[y,x]=True;q.append((y,x))
    while q:
        y,x=q.popleft()
        for yy,xx in ((y-1,x),(y+1,x),(y,x-1),(y,x+1)):
            if 0<=yy<h and 0<=xx<w and low[yy,xx] and not outside[yy,xx]:
                outside[yy,xx]=True;q.append((yy,xx))
    holes=low & ~outside
    m={'size':list(image.size),'original_mode':image.mode,
       'alpha_extrema':[int(a.min()),int(a.max())],
       'transparent_fraction':round(float((a==0).mean()),5),
       'semi_transparent_fraction':round(float(((a>0)&(a<255)).mean()),5),
       'edge_opaque_fraction':round(float((edge>=240).mean()),5),
       'corner_alpha':corners,
       'interior_semi_fraction':round(float(((small<230)&interior).sum()/max(1,interior.sum())),5),
       'enclosed_transparent_fraction':round(float(holes.mean()),5),
       'alpha_bbox':image.convert('RGBA').getchannel('A').getbbox()}
    flags=[]
    if portrait:
        if m['transparent_fraction']>.02:flags.append('portrait_transparency_review')
        # Opaque rectangular backgrounds and edge contact are expected for portraits.
    else:
        if image.mode not in ('RGBA','LA','P') or a.min()>0:flags.append('missing_transparent_exterior')
        if sum(v>=240 for v in corners)>=3:flags.append('opaque_corner_background_review')
        if m['edge_opaque_fraction']>.025:flags.append('edge_contact_review_not_proven_clipping')
        if m['interior_semi_fraction']>.08:flags.append('interior_translucency_review')
        if m['enclosed_transparent_fraction']>.025:flags.append('enclosed_gaps_review_may_be_intentional')
    return m,flags

def main():
    records={};failures=[];checks=[]
    def add(row,manifest,hashes=None):
        source=row['source'];exports=row['exports'];portrait=bool(row.get('portrait',row.get('kind')=='generated_advisor'))
        entry=records.setdefault(source,{'ids':[],'manifests':[],'source':source,'portrait':portrait,'exports':{},'expected_source_hashes':set()})
        entry['ids'].append(row.get('target',row['id']));entry['manifests'].append(manifest)
        digest=(hashes or {}).get(source,row.get('source_sha256'))
        entry['expected_source_hashes'].add(digest)
        for e in exports:
            value=dict(e);value['sha256']=(hashes or {}).get(e['path'],e.get('sha256'))
            if e['path'] in entry['exports'] and entry['exports'][e['path']]!=value:
                failures.append({'source':source,'error':'Conflicting export evidence'})
            entry['exports'][e['path']]=value
    manifests=sorted(p for p in (ROOT/'art/verenia').glob('batch-*.json') if re.fullmatch(r'batch-\d+\.json',p.name))
    for p in manifests:
        name=p.relative_to(ROOT).as_posix();hashes=load(name[:-5]+'-hashes.json')
        for row in load(name):add(row,name,hashes)
    for name in ('company-bindings.json','generated-advisor-bindings.json','mio-bindings.json'):
        for row in load('art/verenia/'+name)['records']:
            if row.get('approved'):add(row,'art/verenia/'+name)
    all_exports=set();results=[]
    for i,(source,r) in enumerate(records.items(),1):
        errors=[];actual=sha(source)
        if r.pop('expected_source_hashes')!={actual}:errors.append('Source hash mismatch or absent pin')
        r['source_sha256']=actual
        with Image.open(ROOT/source) as original:
            r['source_metrics'],r['source_flags']=metrics(original,r['portrait'])
            rgba=original.convert('RGBA');exports=[]
            for path,e in r['exports'].items():
                all_exports.add(path);item=dict(e)
                if sha(path)!=e['sha256']:errors.append('Export hash mismatch: '+path)
                size=(e['width'],e['height'])
                raw=(ROOT/path).read_bytes()
                if raw[1:3]!=bytes((0,2)) or raw[16]!=32 or raw[17]&15!=8:errors.append('Invalid native RGBA TGA: '+path)
                with Image.open(ROOT/path) as image:
                    item['metrics'],item['flags']=metrics(image,r['portrait'])
                    if image.size!=size:errors.append('Export dimensions mismatch: '+path)
                    if r['portrait']:
                        expected=ImageOps.fit(rgba,size,Image.Resampling.LANCZOS)
                        ratio=(size[0]/size[1])/(rgba.width/rgba.height)
                        item['intentional_fit_crop_fraction']=round(1-min(ratio,1/ratio),5)
                    else:
                        fit=ImageOps.contain(rgba,size,Image.Resampling.LANCZOS);expected=Image.new('RGBA',size)
                        expected.alpha_composite(fit,((size[0]-fit.width)//2,(size[1]-fit.height)//2))
                    if image.convert('RGBA').tobytes()!=expected.tobytes():errors.append('Native resampling mismatch: '+path)
                exports.append(item)
        r['exports']=exports;r['errors']=errors
        for error in errors:failures.append({'ids':r['ids'],'error':error})
        results.append(r)
        if i%100==0:print(f'Pixels/hashes checked: {i}/{len(records)}',flush=True)
    print('Checking complete live binding evidence...',flush=True)
    progress=runpy.run_path(str(ROOT/'tools/Update-VereniaArtProgress.py'))
    snapshot=progress['Snapshot']();reconciled=progress['reconcile'](snapshot);snapshot.verify()
    if reconciled['integrated_sources']!=len(records) or reconciled['game_exports']!=len(all_exports):failures.append({'error':'Active inventory differs from live reconciliation'})
    for key in ('unintegrated_records','company_diagnostics','runtime_art_diagnostics'):
        if reconciled[key]:failures.append({'error':key,'details':reconciled[key]})
    # Exact binder plans cover shine definitions and native field preservation.
    icon=runpy.run_path(str(ROOT/'tools/Bind-VereniaIcons.py'));files=icon['Files'](ROOT)
    for p in manifests:
        rows=load(p.relative_to(ROOT).as_posix())
        if not all(r.get('kind') in ('focus','spirit') for r in rows):continue
        name=p.relative_to(ROOT).as_posix()
        try:
            pending,approved,skipped=icon['plan'](files,name)
            checks.append({'manifest':name,'approved':approved,'skipped':skipped,'pending':list(pending)})
            if pending:failures.append({'error':'Pending icon bindings','manifest':name})
        except Exception as e:failures.append({'error':str(e),'manifest':name})
    files.verify()
    # Detect duplicate live sprite names associated with active export paths.
    aliases={};active_paths={p.removeprefix('mod/HoISubmod/') for p in all_exports}
    mod=snapshot.glob('mod/HoISubmod/interface','**/*.gfx');shadowed={p.removeprefix('mod/HoISubmod/') for p in mod}
    live=[p for p in snapshot.glob('EaW/interface','**/*.gfx') if p.removeprefix('EaW/') not in shadowed]+mod
    for path in live:
        for n in progress['walk'](progress['nodes'](snapshot,path)):
            if n.key.lower()=='spritetype':
                fields={c.key.lower():c.value for c in n.children}
                aliases.setdefault(fields.get('name'),[]).append({'file':path,'texture':str(fields.get('texturefile','')).replace('\\','/')})
    collisions={a:v for a,v in aliases.items() if len(v)>1 and any(e['texture'] in active_paths for e in v)}
    if collisions:failures.append({'error':'Active sprite alias collision','details':collisions})
    snapshot.verify()
    cli_checks=[]
    for tool in ('Bind-VereniaCompanies.py','Bind-VereniaRuntimeArt.py','Bind-VereniaPortraits.py'):
        process=subprocess.run([sys.executable,'-B','-X','utf8',str(ROOT/'tools'/tool),'--check'],
                               cwd=ROOT,capture_output=True,text=True,encoding='utf-8')
        cli_checks.append({'tool':tool,'exit_code':process.returncode,'output':process.stdout+process.stderr})
        if process.returncode:failures.append({'error':'Binder check failed','tool':tool})
    suspects=[]
    for r in results:
        flags=set(r['source_flags'])
        for e in r['exports']:flags.update(e['flags'])
        if flags:suspects.append({'ids':r['ids'],'source':r['source'],'flags':sorted(flags)})
    report={'scope':'Active approved/bound artwork only; no images or gameplay changed.',
        'limitations':'Heuristics do not establish visual defects. Enclosed gaps may be handles, machinery gaps or spaces between objects. Portrait backgrounds and ImageOps.fit crops are expected; visual agents must inspect heads/crests. No semantic/heraldry or engine-runtime verification.',
        'sources':len(records),'exports':len(all_exports),'failures':failures,'icon_binder_checks':checks,
        'active_sprite_collisions':collisions,'review_candidates':suspects,'records':results,'binder_cli_checks':cli_checks,
        'reconciliation':{k:reconciled[k] for k in ('status','integrated_sources','game_exports','pending_counts','completed_generated_advisor_templates','completed_mio_records')}}
    notes=OUT.with_name('technical-review-notes.json')
    if notes.exists():report['visual_spot_checks']=json.loads(notes.read_text())
    OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'sources':len(records),'exports':len(all_exports),'failures':failures,'review_candidates':len(suspects),'report':str(OUT)},indent=2),flush=True)

if __name__=='__main__':main()
