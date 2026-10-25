"""Comparison sheets for identity QA only; source images remain untouched."""
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageOps

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / 'art/verenia'
rows = [r for p in sorted(ART.glob('batch-0?.json'))
        for r in json.loads(p.read_text()) if r.get('portrait')]
for page in range(3):
    canvas = Image.new('RGB', (1280, 600), '#3b4145')
    draw = ImageDraw.Draw(canvas)
    for i, r in enumerate(rows[page*8:page*8+8]):
        x, y = i % 4 * 320, i // 4 * 300
        draw.text((x+5,y+5), r['id']+' / reference > generated', fill='white')
        refid = 'grover_adult' if r['id']=='grover' else r['id']
        reference = ART / 'references' / (refid+'.png')
        for j, path in enumerate((reference, ROOT/r['source'])):
            if not path.exists():
                draw.text((x+5,y+50), 'Original new character', fill='white')
                continue
            with Image.open(path) as raw:
                thumb = ImageOps.contain(raw.convert('RGBA'), (150,260), Image.Resampling.LANCZOS)
                canvas.paste(thumb, (x+j*160+(160-thumb.width)//2,y+30), thumb)
    canvas.save(ART/'final-review'/f'portrait-reference-{page+1}.png')
print('3 identity comparison sheets created')
