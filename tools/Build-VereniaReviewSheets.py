"""Read-only image inspection composites; never changes source or game pixels."""
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageOps

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / 'art/verenia'
OUT = ART / 'final-review'
OUT.mkdir(exist_ok=True)
manifests = sorted(ART.glob('batch-??.json')) + [ART / n for n in (
    'company-exports.json', 'company-neutral-exports.json', 'mio-exports.json',
    'generated-advisors-01.json', 'generated-advisors-02.json', 'generated-advisors-03.json')]
index = []
for manifest in manifests:
    rows = json.loads(manifest.read_text(encoding='utf-8-sig'))
    sheet = Image.new('RGB', (1280, 380 * ((len(rows)+3)//4)), '#3b4145')
    draw = ImageDraw.Draw(sheet)
    for i, row in enumerate(rows):
        x,y = (i%4)*320, (i//4)*380
        label = row['id']
        for j in range(0,len(label),43):
            draw.text((x+6,y+5+(j//43)*12),label[j:j+43],fill='white')
        with Image.open(ROOT/row['source']) as raw:
            preview = ImageOps.contain(raw.convert('RGBA'), (300,250), Image.Resampling.LANCZOS)
            sheet.paste(preview,(x+(320-preview.width)//2,y+40),preview)
        ex = row['exports'][0]
        with Image.open(ROOT/ex['path']) as raw:
            raw = raw.convert('RGBA')
            if raw.height > 80:
                if row.get('portrait'):
                    raw = ImageOps.contain(raw,(60,80),Image.Resampling.LANCZOS)
            sheet.paste(raw,(x+10,y+292),raw)
        index.append({'manifest':manifest.name,'id':row['id'],'source':row['source'],
                      'exports':row['exports'],'sheet':manifest.stem+'.png'})
    sheet.save(OUT/(manifest.stem+'.png'))
(OUT/'index.json').write_text(json.dumps(index,indent=2)+'\n',encoding='utf-8')
print(f'{len(manifests)} sheets, {len(index)} records')
