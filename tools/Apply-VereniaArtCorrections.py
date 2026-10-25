"""Controlled final-review replacements. Default/--check never write.

newSource marks a visually approved correction under the user's explicit workflow.
Preserves old records, whole manifests/hashfiles/previews and exact TGA bytes.
Runs the unchanged normal builder in an isolated staging root; commits only the
specified exports and affected manifests/hashfiles/previews. No gameplay writes.
"""
import argparse
import copy
import hashlib
import json
import re
import runpy
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CORRECTIONS = 'art/verenia/final-review/corrections.json'
ARCHIVE = 'art/verenia/final-review/replaced/'
ALLOWED = set('''HSM_VER_REG_a_union_without_a_throne HSM_EYR_avian_association
HSM_VER_IMP_civilian_legacy HSM_ZYP_crown_and_countries overtures_eyrie
HSM_VER_GRO_service HSM_ZYP_commissions_not_orders HSM_VER_FORCE_AVI_commission
HSM_VER_GRO_transition AVI_urbanisation_effort AVI_aviation AVI_livre_1 AVI_livre_2
AVI_treasury avian_socialist_technocracy expand_aviaire_metalworks oil_refineries
HSM_ERI_support_companies HSM_ERI_integrated_staff HSM_ERI_FORCE_not_a_dowry'''.split())
API = runpy.run_path(str(ROOT/'tools/Bind-VereniaIcons.py'))
require = API['require']

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def encoded(value):
    return (json.dumps(value,indent=2,ensure_ascii=False)+'\n').encode('utf-8')

def checked(files,path,digest):
    raw=files.read(path)
    require(raw is not None and isinstance(digest,str) and sha(raw)==digest,
            'Missing or changed pinned file: '+path)
    return raw

def inspect(files):
    corrections=API['read_json'](files,CORRECTIONS)
    require(len(corrections)==20 and {r['id'] for r in corrections}==ALLOWED,'Correction scope must be the exact 20 authorized IDs')
    catalog={}; manifests={}
    for p in sorted((ROOT/'art/verenia').glob('batch-*.json')):
        if not re.fullmatch(r'batch-\d+\.json',p.name):continue
        name=p.relative_to(ROOT).as_posix();rows=API['read_json'](files,name)
        manifests[name]=rows
        for row in rows:
            key=row.get('target',row['id'])
            if key in ALLOWED:
                require(key not in catalog,'Ambiguous canonical target: '+key)
                catalog[key]=(name,row)
    require(set(catalog)==ALLOWED,'Missing canonical targets')
    pending=[];done=[]
    for correction in corrections:
        if not correction.get('newSource'):continue
        key=correction['id'];name,row=catalog[key];source=correction['newSource']
        API['relative'](source,'art/verenia')
        require(source.endswith('.png') and correction.get('prompt'),'Missing PNG/prompt')
        new=files.read(source);require(new is not None,'Missing approved replacement: '+source)
        require(row.get('approved') is True and row.get('kind') in ('focus','spirit') and not row.get('portrait'), 'Unsupported/unapproved canonical record')
        require(len(row['exports'])==1,'Expected one stable export')
        digest=API['read_json'](files,name[:-5]+'-hashes.json')
        checked(files,row['source'],digest.get(row['source']))
        export=row['exports'][0]
        API['relative'](export['path'],'mod/HoISubmod/gfx')
        checked(files,export['path'],digest.get(export['path']))
        if row['source']==source:
            meta=row.get('final_review',{})
            require(meta.get('correction_prompt')==correction['prompt'] and meta.get('source_sha256')==sha(new)
                    and meta.get('runtime_verified') is False,'Applied correction metadata/source drift: '+key)
            backup=meta['backup']
            API['relative'](backup,ARCHIVE)
            old=API['read_json'](files,backup+'/record.json')
            oldhash=API['read_json'](files,backup+'/hashes.json')
            checked(files,backup+'/export.tga',oldhash[old['exports'][0]['path']])
            checked(files,old['source'],oldhash[old['source']])
            done.append(key);continue
        require(not row.get('final_review'),'Further revision requires explicit new transaction policy: '+key)
        require(not correction.get('oldSource') or correction['oldSource']==row['source'],'oldSource mismatch: '+key)
        pending.append((name,row,correction))
    return manifests,pending,done

def run_builder(stage,name,check=False):
    module=runpy.run_path(str(ROOT/'tools/Build-VereniaArt.py'))
    module['main'].__globals__['ROOT']=stage
    saved=sys.argv
    try:
        sys.argv=['Build-VereniaArt.py','--manifest',str(stage/name)]+(['--check'] if check else [])
        module['main']()
    finally:sys.argv=saved

def execute(files,manifests,pending):
    transaction=ARCHIVE+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'-'+uuid.uuid4().hex[:8]
    stage=files.path(transaction+'/staged');affected=sorted({n for n,r,c in pending})
    changed={n:copy.deepcopy(manifests[n]) for n in affected};output_paths=set();backups={}
    receipt={'status':'prepared','corrections_sha256':sha(files.read(CORRECTIONS)),'records':[],'outputs':{}}
    for name,old,c in pending:
        key=c['id'];backup=transaction+'/'+key;hashname=name[:-5]+'-hashes.json'
        backups[backup+'/record.json']=encoded(old)
        backups[backup+'/manifest.json']=files.read(name)
        backups[backup+'/hashes.json']=files.read(hashname)
        export=old['exports'][0]['path'];backups[backup+'/export.tga']=files.read(export);output_paths.add(export)
        row=next(r for r in changed[name] if r.get('target',r['id'])==key)
        row['original_prompt']=old.get('prompt')
        row['source']=c['newSource'];row['prompt']=c['prompt'];row['runtime_verified']=False
        row['final_review']={'approved':True,'review':'Main approved corrected source/native artwork; runtime QA pending.',
            'correction_manifest':CORRECTIONS,'correction_prompt':c['prompt'],'previous_source':old['source'],
            'source_sha256':sha(files.read(c['newSource'])),'backup':backup,'runtime_verified':False}
        receipt['records'].append({'id':key,'manifest':name,'backup':backup,'old_source':old['source'],'new_source':c['newSource'],'export':export})
    # Pin and validate every affected batch before any canonical replacement.
    for name in affected:
        hashes=API['read_json'](files,name[:-5]+'-hashes.json')
        for row in manifests[name]:
            checked(files,row['source'],hashes.get(row['source']))
            for e in row['exports']:checked(files,e['path'],hashes.get(e['path']))
        preview=name[:-5]+'-native-preview.png';old_preview=files.read(preview)
        if old_preview is not None:backups[transaction+'/previews/'+Path(preview).name]=old_preview
    files.verify()
    for path,raw in backups.items():
        dest=files.path(path);dest.parent.mkdir(parents=True,exist_ok=True)
        with dest.open('xb') as stream:stream.write(raw)
        require(dest.read_bytes()==raw,'Backup verification failed: '+path)
    files.path(transaction+'/corrections-snapshot.json').write_bytes(files.read(CORRECTIONS))
    receipt_path=files.path(transaction+'/receipt.json');receipt_path.write_bytes(encoded(receipt))
    outputs={}
    for name in affected:
        # Staging contains full batch input copies; unchanged TGA bytes are checked
        # and later compared. The normal builder never overwrites canonical files.
        for row in changed[name]:
            for path in [row['source']]+[e['path'] for e in row['exports'] if e['path'] not in output_paths]:
                dest=stage/path;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(files.read(path))
        dest=stage/name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(encoded(changed[name]))
        run_builder(stage,name);run_builder(stage,name,True)
        for row in changed[name]:
            for e in row['exports']:
                path=e['path'];raw=(stage/path).read_bytes()
                if path in output_paths:outputs[path]=raw
                else:require(raw==files.read(path),'Normal builder changed unrelated TGA: '+path)
        for path in (name,name[:-5]+'-hashes.json',name[:-5]+'-native-preview.png'):
            files.read(path);outputs[path]=(stage/path).read_bytes()
    class Overlay:
        interfaces=files.interfaces
        def read(self,path):return outputs[path] if path in outputs else files.read(path)
    for name in affected:
        edits,_,_=API['plan'](Overlay(),name)
        require(not edits,'Correction would change gameplay/sprite binding: '+name)
    files.verify()
    for path,raw in outputs.items():receipt['outputs'][path]={'before':sha(files.read(path)) if files.read(path) else None,'after':sha(raw)}
    receipt_path.write_bytes(encoded(receipt))
    API['apply'](files,outputs)
    receipt['status']='applied';receipt_path.write_bytes(encoded(receipt))
    return receipt,transaction

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    mode=parser.add_mutually_exclusive_group();mode.add_argument('--apply',action='store_true');mode.add_argument('--check',action='store_true');mode.add_argument('--self-test',action='store_true')
    args=parser.parse_args()
    if args.self_test:
        self_test();return 0
    files=API['Files'](ROOT);manifests,pending,done=inspect(files)
    print(json.dumps({'ready':[c['id'] for n,r,c in pending],'already_applied':done,'not_generated':20-len(pending)-len(done)},indent=2))
    if args.apply and pending:
        receipt,transaction=execute(files,manifests,pending)
        print('Applied '+str(len(pending))+' corrections; verified backups: '+transaction)
    else:files.verify()
    return int(args.check and bool(pending))

def self_test():
    import unittest
    class Tests(unittest.TestCase):
        def test_reject_changed_tga(self):
            f=API['Files'](ROOT);m,p,d=inspect(f)
            row=next(r for rows in m.values() for r in rows if r.get('target',r['id']) in ALLOWED)
            path=row['exports'][0]['path'];f.snapshots[path]=f.read(path)+b'corruption'
            with self.assertRaisesRegex(ValueError,'pinned file'):inspect(f)
        def test_reject_escaped_source(self):
            f=API['Files'](ROOT);c=API['read_json'](f,CORRECTIONS);c[0]['newSource']='../outside.png';f.snapshots[CORRECTIONS]=encoded(c)
            with self.assertRaises(ValueError):inspect(f)
        def test_reject_duplicate_scope(self):
            f=API['Files'](ROOT);c=API['read_json'](f,CORRECTIONS);c[-1]=c[0];f.snapshots[CORRECTIONS]=encoded(c)
            with self.assertRaisesRegex(ValueError,'exact 20'):inspect(f)
        def test_applied_backup_and_prompt_protected(self):
            f=API['Files'](ROOT);m,p,d=inspect(f);self.assertTrue(d)
            row=next(r for rows in m.values() for r in rows if r.get('target',r['id'])==d[0])
            path=row['final_review']['backup']+'/export.tga';f.snapshots[path]=f.read(path)+b'corruption'
            with self.assertRaisesRegex(ValueError,'pinned file'):inspect(f)
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Tests))
    require(result.wasSuccessful(),'Correction safety tests failed')

if __name__=='__main__':raise SystemExit(main())
