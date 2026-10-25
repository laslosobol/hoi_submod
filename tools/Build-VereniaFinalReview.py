"""Reconcile visual approvals, corrected sources, exports and technical audit."""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / 'art/verenia'
OUT = ART / 'final-review'

def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

visual = {}
for filename, key in [('visual-main.json', 'reviewed_assets'),
                      ('visual-10-35.json', 'reviewed_assets'),
                      ('visual-36-60.json', 'reviewedAssets')]:
    for row in read(OUT/filename)[key]:
        source = row['source']
        assert source not in visual, source
        visual[source] = (row.get('source_sha256', row.get('sha256')), filename)
assert len(visual) == 632
replacement_report = read(OUT/'replacement-review.json')
replacements = {r['source']: r for r in replacement_report['assets']}
corrections = read(OUT/'corrections.json')
assert len(replacements) == len(corrections) == 20
for fix in corrections:
    row = replacements[fix['newSource']]
    assert row['result'] == 'pass' and row['fullsizeInspected'] and row['nativeInspected'], row['id']
    assert sha(ROOT/row['source']) == row['sha256'], row['id']
technical = read(OUT/'technical-final.json')
assert technical['sources'] == 632 and technical['exports'] == 638
assert not technical['failures'] and not technical['active_sprite_collisions']

manifests = sorted(ART.glob('batch-??.json')) + [ART/n for n in (
    'company-exports.json', 'company-neutral-exports.json', 'mio-exports.json',
    'generated-advisors-01.json', 'generated-advisors-02.json', 'generated-advisors-03.json')]
records = []
changed_records = []
seen = set()
exports = 0
for manifest in manifests:
    hashes = read(manifest.with_name(manifest.stem+'-hashes.json'))
    for row in read(manifest):
        source = row['source']
        assert source not in seen, source
        seen.add(source)
        digest = sha(ROOT/source)
        assert hashes[source] == digest, source
        if source in replacements:
            approval = 'replacement-review.json'
            assert replacements[source]['sha256'] == digest
            assert row['final_review']['approved'] is True
            assert row['final_review']['runtime_verified'] is False
            changed_records.append(row)
        else:
            expected, approval = visual[source]
            assert expected == digest, 'Changed after visual review: '+source
        targets = []
        for export in row['exports']:
            export_hash = sha(ROOT/export['path'])
            assert hashes[export['path']] == export_hash, export['path']
            targets.append(dict(export, sha256=export_hash))
            exports += 1
        records.append({'id': row['id'], 'source': source, 'sha256': digest,
                        'visual_approval': approval, 'corrected': source in replacements,
                        'exports': targets})
assert len(records) == 632 and exports == 638
report = {
    'status': 'final_art_review_passed_runtime_pending',
    'created_utc': datetime.now(timezone.utc).isoformat(),
    'scope': 'ERI, EYR, AVI and shared Verenia active generated artwork',
    'sources_reviewed': 632, 'game_exports_verified': 638,
    'corrected_icons': 20, 'unchanged_sources': 612,
    'named_portraits_reviewed': 24, 'generic_advisor_templates_reviewed': 30,
    'visual_review': 'All source/native contact sheets inspected; suspect images enlarged. Named identities compared with original references. All 20 replacements individually reviewed at source and native sizes on contrasting backgrounds.',
    'requirements': ['canonical heraldry and orientation', 'character identity and anatomy',
                     'material palettes', 'period equipment', 'readability at game size',
                     'complete silhouettes and transparency', 'game sprite and portrait bindings'],
    'correction_method': 'Built-in image generation; exact final prompts in corrections.json, original prompts and texture backups retained.',
    'technical_audit': 'technical-final.json',
    'replacement_review': 'replacement-review.json',
    'correction_prompts': 'corrections.json',
    'limitations': ['HOI4 engine rendering has not been verified in a running game.',
                    'Unused/rejected source variants are retained as history and are not active game assets.'],
    'runtime_verified': False,
    'records': records,
}
(OUT/'final-audit.json').write_text(json.dumps(report, indent=2, ensure_ascii=False)+'\n', encoding='utf-8')
preview = Image.new('RGB', (1300, 750), '#3b4145')
draw = ImageDraw.Draw(preview)
for i, row in enumerate(changed_records):
    x, y = i%5*260, i//5*187
    label = row['id']
    for line in range(0, len(label), 35):
        draw.text((x+5,y+4+line//35*12), label[line:line+35], fill='white')
    draw.text((x+5,y+42), 'BEFORE                 AFTER', fill='#c3c8cc')
    for col, path in enumerate((ROOT/row['final_review']['backup']/'export.tga', ROOT/row['exports'][0]['path'])):
        with Image.open(path) as raw:
            native = raw.convert('RGBA')
            preview.paste(native, (x+10+col*130,y+64), native)
preview.save(OUT/'corrections-before-after.png')
print('Final review: 632 sources / 638 exports, 20 corrected, 612 unchanged; runtime pending.')
