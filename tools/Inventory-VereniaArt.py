"""Read-only content scan; writes a resumable artwork inventory, never gameplay."""
import json
import re
import runpy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MOD = ROOT / 'mod/HoISubmod'
EAW = ROOT / 'EaW'
api = runpy.run_path(str(ROOT / 'tools/Test-Verenia.py'))
read, walk = api['read'], api['walk']
loc = {}
for root in (EAW, MOD):
    for path in (root / 'localisation/english').rglob('*.yml'):
        for line in path.read_text(encoding='utf-8-sig').splitlines():
            match = re.match(r'\s*([^ #][^:]*):\d*\s*"(.*)"\s*$', line)
            if match:
                loc[match[1]] = match[2]
records = []
for folder, kind in [('national_focus', 'focus'), ('ideas', 'spirit')]:
    for path in (MOD / 'common' / folder).glob('*.txt'):
        if not (path.stem.startswith(('HSM_VER', 'HSM_ERI', 'HSM_EYR')) or path.name == 'AVI.txt'):
            continue
        for node in walk(read(path)):
            if kind == 'focus' and node.key in ('focus', 'shared_focus', 'joint_focus') and node.children:
                key, icon = node.get('id'), node.get('icon')
            elif kind == 'spirit' and node.get('picture'):
                key, icon = node.key, node.get('picture')
            else:
                continue
            records.append(dict(id=key, kind=kind, file=path.relative_to(ROOT).as_posix(),
                                name=loc.get(key, key), description=loc.get(key+'_desc', ''),
                                current_icon=icon, status='INTEGRATED' if str(icon).startswith('GFX_HSM_VER_') else 'PENDING'))
for tag in ('ERI', 'EYR', 'AVI'):
    path = MOD / f'common/characters/{tag}.txt'
    if not path.exists():
        path = EAW / f'common/characters/{tag}.txt'
    for node in read(path)[0].children:
        portraits = [dict(role=p.key, value=p.value) for p in walk(node.children) if p.key in ('large', 'small')]
        records.append(dict(id=node.key, kind='portrait', file=path.relative_to(ROOT).as_posix(),
                            name=loc.get(node.get('name'), node.key), portraits=portraits, status='PENDING'))
done = {row['target'] for row in json.loads((ROOT / 'art/verenia/batch-01.json').read_text())}
for row in records:
    if row['id'] in done:
        row['status'] = 'INTEGRATED'
out = ROOT / 'art/verenia/inventory.json'
out.write_text(json.dumps(records, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
for kind in sorted({row['kind'] for row in records}):
    rows = [row for row in records if row['kind'] == kind]
    print(kind, len(rows), 'pending', sum(row['status']=='PENDING' for row in rows))
