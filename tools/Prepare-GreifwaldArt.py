"""Mechanically prepare Greifwald art; never generate pictures or bind gameplay.

Default is a read-only plan. --export copies original PNG bytes, exports native
RGBA TGAs, writes all inventory records (including pending/unapproved ones),
and creates paginated dark/light QA sheets. Original generated files stay intact.

After visually reviewing the sheets, a separate --approve ID [ID ...] command
approves only the exact source/export bytes represented on those sheets. This
tool cannot perform visual review and never infers approval from valid pixels.
It does not call Bind-GreifwaldArt.py --apply or modify any gameplay definition.

Examples:
    python tools/Prepare-GreifwaldArt.py
    python tools/Prepare-GreifwaldArt.py --export
    python tools/Prepare-GreifwaldArt.py --approve opening refuge
    python tools/Prepare-GreifwaldArt.py --export --margin 3

Inputs: art/greifwald/briefs.json {assets:[{id,kind,title,brief,targets}]};
generation/<id>.json {id,prompt,provider,generated:absolutePNG,revision}.
Focus size is 99x86; spirit/dynamic size is 64x64. --margin is native pixels.
Cropping removes only fully transparent borders, then uses a contained resize.
--keep-canvas preserves the full input canvas instead. No recoloring, masking,
background removal, alpha thresholding, sharpening or creative edits occur.
"""
from __future__ import annotations

import argparse
import copy
import functools
import hashlib
import io
import json
import math
import os
import re
import runpy
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps

ROOT = Path(__file__).resolve().parents[1]
BASE = 'art/greifwald'
BRIEFS = BASE + '/briefs.json'
MANIFEST = BASE + '/manifest.json'
PREVIEWS = BASE + '/previews'
INDEX = PREVIEWS + '/index.json'
MOD = 'mod/HoISubmod'
SAFE_ID = re.compile(r'[A-Za-z0-9_]+')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def json_bytes(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode('utf-8')


@functools.lru_cache(maxsize=1)
def binder():
    """Reuse its exact schema validation, but never its binding/apply functions."""
    saved = sys.argv
    try:
        sys.argv = [str(ROOT / 'tools/Bind-GreifwaldArt.py')]
        return runpy.run_path(sys.argv[0])
    finally:
        sys.argv = saved


class Snapshot:
    """Read pins prevent overwriting inputs changed while a plan was prepared."""
    def __init__(self, root):
        self.root = Path(root).resolve()
        self.inputs = {}

    def path(self, relative):
        path = (self.root / relative).resolve()
        require(path.is_relative_to(self.root), f'Path escapes workspace: {relative}')
        return path

    def read_path(self, path):
        path = Path(path).resolve()
        if path not in self.inputs:
            self.inputs[path] = path.read_bytes() if path.exists() else None
        return self.inputs[path]

    def read(self, relative):
        return self.read_path(self.path(relative))

    def document(self, relative, optional=False):
        raw = self.read(relative)
        require(optional or raw is not None, f'Missing {relative}')
        return json.loads(raw.decode('utf-8-sig')) if raw is not None else None

    def write(self, outputs):
        """Validate every input first; atomic replacement for each owned output."""
        for name in outputs:
            self.read(name)
        for path, old in self.inputs.items():
            now = path.read_bytes() if path.exists() else None
            require(now == old, f'Concurrent change; rerun preparation: {path}')
        changed = 0
        for name, raw in outputs.items():
            path = self.path(name)
            if self.inputs[path] == raw:
                continue
            path.parent.mkdir(parents=True, exist_ok=True)
            fd, temporary = tempfile.mkstemp(prefix=path.name + '.', suffix='.tmp', dir=path.parent)
            try:
                with os.fdopen(fd, 'wb') as stream:
                    stream.write(raw)
                os.replace(temporary, path)
            finally:
                if os.path.exists(temporary):
                    os.unlink(temporary)
            changed += 1
        return changed


def validate_manifest(document):
    class Memory:
        def read(self, name):
            require(name == MANIFEST, f'Unexpected schema read: {name}')
            return json_bytes(document)
    return binder()['load_manifest'](Memory())


def inventory(snapshot):
    document = snapshot.document(BRIEFS)
    require(isinstance(document, dict) and isinstance(document.get('assets'), list),
            'briefs.json must contain an assets list')
    rows = []
    for asset in document['assets']:
        require(isinstance(asset, dict), 'Brief asset must be an object')
        aid, kind = asset.get('id'), asset.get('kind')
        require(isinstance(aid, str) and SAFE_ID.fullmatch(aid), f'Invalid brief id: {aid}')
        require(kind in ('focus', 'spirit', 'dynamic'), f'Invalid kind for {aid}: {kind}')
        require(isinstance(asset.get('title'), str) and isinstance(asset.get('brief'), str),
                f'Missing title/brief: {aid}')
        folder = 'goals' if kind == 'focus' else 'ideas'
        rows.append({
            'id': aid, 'kind': kind, 'title': asset['title'], 'brief': asset['brief'],
            'targets': copy.deepcopy(asset.get('targets')),
            'source': f'{BASE}/source/{aid}.png',
            'export': f'{MOD}/gfx/interface/{folder}/HSM_AET_{aid}.tga',
            'gfx': ('GFX_' if kind == 'focus' else 'GFX_idea_') + 'HSM_AET_' + aid,
            'approved': False, 'source_sha256': None, 'export_sha256': None,
        })
    validate_manifest({'assets': rows})
    return rows


def generation(snapshot, aid):
    name = f'{BASE}/generation/{aid}.json'
    record = snapshot.document(name, optional=True)
    if record is None:
        return None
    require(isinstance(record, dict) and record.get('id') == aid,
            f'Generation ID does not match filename: {name}')
    for key in ('prompt', 'provider', 'generated'):
        require(isinstance(record.get(key), str) and record[key].strip(),
                f'Missing generation {key}: {aid}')
    require(type(record.get('revision')) is int and record['revision'] >= 1,
            f'Expected positive integer revision: {aid}')
    path = Path(record['generated'])
    require(path.is_absolute() and path.suffix.lower() == '.png',
            f'Expected absolute generated PNG: {aid}')
    return record


def open_source(raw, aid):
    with Image.open(io.BytesIO(raw)) as opened:
        require(opened.format == 'PNG' and not getattr(opened, 'is_animated', False),
                f'Expected single PNG source: {aid}')
        require(min(opened.size) > 0 and max(opened.size) <= 8192,
                f'Invalid source dimensions: {aid}')
        opened.load()
        original = opened.convert('RGBA')
    low, high = original.getchannel('A').getextrema()
    require(low == 0 and high >= 240, f'Source needs transparent exterior and opaque artwork: {aid}')
    return original


def render(raw, kind, margin=2, keep_canvas=False, aid='image'):
    size = (99, 86) if kind == 'focus' else (64, 64)
    require(type(margin) is int and 0 <= margin < min(size) // 2,
            f'Invalid native-pixel margin for {aid}: {margin}')
    original = open_source(raw, aid)
    box = original.getchannel('A').getbbox()
    require(box is not None, f'Empty source: {aid}')
    bounds = (0, 0, original.width, original.height) if keep_canvas else box
    inner = (size[0] - 2 * margin, size[1] - 2 * margin)
    fitted = ImageOps.contain(original.crop(bounds), inner, Image.Resampling.LANCZOS)
    result = Image.new('RGBA', size, (0, 0, 0, 0))
    result.alpha_composite(fitted, ((size[0] - fitted.width) // 2, (size[1] - fitted.height) // 2))
    alpha = result.getchannel('A')
    low, high = alpha.getextrema()
    require(low == 0 and high >= 240 and sum(alpha.histogram()[128:]) >= size[0] * size[1] // 100,
            f'Export lacks transparent exterior or opaque visible artwork: {aid}; increase margin if needed')
    stream = io.BytesIO()
    result.save(stream, format='TGA', compression=None)
    exported = stream.getvalue()
    binder()['BASE']['native_tga'](exported, size)
    recipe = {'crop': 'canvas' if keep_canvas else 'alpha_bbox', 'source_bounds': list(bounds),
              'margin': margin, 'size': list(size), 'resample': 'LANCZOS',
              'encoding': 'uncompressed RGBA TGA'}
    return result, exported, recipe


def prepare(snapshot, margin=2, keep_canvas=False):
    rows = inventory(snapshot)
    previous = snapshot.document(MANIFEST, optional=True)
    old = {r['id']: r for r in validate_manifest(previous)} if previous else {}
    require(set(old) <= {r['id'] for r in rows},
            'Inventory removed existing manifest assets; reconcile explicitly before exporting')
    outputs, images = {}, {}
    for row in rows:
        aid = row['id']
        earlier = old.get(aid, {})
        gen = generation(snapshot, aid)
        cached = snapshot.read(row['source'])
        raw = snapshot.read_path(Path(gen['generated'])) if gen else None
        if raw is None and cached is not None:
            if gen:
                same_record = earlier.get('generation') == gen
                require(same_record and digest(cached) == earlier.get('source_sha256'),
                        f'Generated PNG missing and cached source cannot verify current revision: {aid}')
            raw = cached
            row['status'] = 'cached_source'
        elif raw is None:
            row['status'] = 'pending_generation'
        else:
            row['status'] = 'exported_unreviewed'
        if gen:
            row['generation'] = gen
        elif earlier.get('generation'):
            row['generation'] = earlier['generation']
        if raw is None:
            continue
        image, exported, recipe = render(raw, row['kind'], margin, keep_canvas, aid)
        row.update(source_sha256=digest(raw), export_sha256=digest(exported), render=recipe)
        unchanged = all(earlier.get(key) == row[key] for key in
                        ('source_sha256', 'export_sha256', 'id', 'kind', 'targets', 'source', 'export', 'gfx'))
        row['approved'] = earlier.get('approved') is True and unchanged
        if row['approved']:
            row['status'] = 'approved'
            if earlier.get('approval'):
                row['approval'] = earlier['approval']
        outputs[row['source']] = raw  # Exact original PNG bytes; never resave source.
        outputs[row['export']] = exported
        images[aid] = image
    document = {'schema_version': 1, 'assets': rows}
    validate_manifest(document)
    return document, outputs, images


def preview_font(size=14):
    for path in ('C:/Windows/Fonts/segoeui.ttf', 'C:/Windows/Fonts/arial.ttf', 'DejaVuSans.ttf'):
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            pass
    return ImageFont.load_default()


def sheets(document, images, page_size=18):
    require(type(page_size) is int and 1 <= page_size <= 18, 'Page size must be 1..18')
    outputs, entries = {}, []
    font, small = preview_font(15), preview_font(12)
    for group in ('focus', 'spirit'):
        rows = [r for r in document['assets'] if r['id'] in images
                and (r['kind'] == 'focus') == (group == 'focus')]
        width, height = (99, 86) if group == 'focus' else (64, 64)
        cell_w, cell_h = 6 * width + 48, 4 * height + 116
        for start in range(0, len(rows), page_size):
            page = rows[start:start + page_size]
            columns = min(3, len(page))
            sheet = Image.new('RGB', (columns * cell_w, math.ceil(len(page) / columns) * cell_h), '#151b23')
            draw = ImageDraw.Draw(sheet)
            name = f'{PREVIEWS}/{group}-{start // page_size + 1:02d}.png'
            page_entries = []
            for index, row in enumerate(page):
                x, y = (index % columns) * cell_w, (index // columns) * cell_h
                # Approval is stored in the manifest, not baked into the preview:
                # approving unchanged art must not invalidate its QA-page hash.
                label = f"{row['kind']} | {row['id']} | TECHNICAL PREVIEW"
                draw.text((x + 10, y + 7), label, font=font, fill='white')
                title = row['title']
                while title and draw.textbbox((0, 0), title, font=small)[2] > cell_w - 20:
                    title = title[:-2]
                draw.text((x + 10, y + 29), title, font=small, fill='#c9d1d9')
                image = images[row['id']]
                for scale, top in ((1, y + 64), (3, y + 94 + height)):
                    sample = image if scale == 1 else image.resize((width * 3, height * 3), Image.Resampling.NEAREST)
                    draw.text((x + 10, top - 17), f'{scale}x | dark / light', font=small, fill='#c9d1d9')
                    for side, color in enumerate(('#25292e', '#e8e5df')):
                        left = x + 10 + side * (3 * width + 20)
                        draw.rectangle((left, top, left + sample.width - 1, top + sample.height - 1), fill=color)
                        sheet.paste(sample, (left, top), sample)
                page_entries.append({'id': row['id'], 'kind': row['kind'],
                                     'source_sha256': row['source_sha256'], 'export_sha256': row['export_sha256'],
                                     'page': name, 'cell': index})
            stream = io.BytesIO()
            sheet.save(stream, format='PNG')
            raw = outputs[name] = stream.getvalue()
            for item in page_entries:
                item['page_sha256'] = digest(raw)
            entries.extend(page_entries)
    outputs[INDEX] = json_bytes({'schema_version': 1, 'page_size': page_size,
                                'scales': [1, 3], 'backgrounds': ['dark', 'light'],
                                'note': 'Technical preview only. No visual approval is inferred. Listed pages are current; unlisted older files are not review evidence.',
                                'assets': entries})
    return outputs


def approve(snapshot, ids):
    """Explicit main/human attestation, restricted to a previously exported sheet."""
    document = snapshot.document(MANIFEST)
    rows = validate_manifest(document)
    inventory_by_id = {r['id']: r for r in inventory(snapshot)}
    current_ids = set(inventory_by_id)
    require({r['id'] for r in rows} == current_ids, 'Export the current inventory before approval')
    selected = {part for value in ids for part in value.split(',') if part}
    require(selected and selected <= current_ids, f'Unknown approval IDs: {sorted(selected - current_ids)}')
    index = snapshot.document(INDEX)
    require(isinstance(index, dict) and isinstance(index.get('assets'), list), 'Invalid preview index')
    reviewed = {r['id']: r for r in index['assets']}
    for row in rows:
        if row['id'] not in selected:
            continue
        aid = row['id']
        require(all(row.get(key) == inventory_by_id[aid][key] for key in
                    ('kind', 'title', 'brief', 'targets', 'source', 'export', 'gfx')),
                f'Brief or binding target changed; export and review again: {aid}')
        evidence = reviewed.get(aid)
        require(evidence is not None, f'No exported contact sheet for {aid}')
        require(evidence.get('kind') == row['kind'], f'Preview kind differs: {aid}')
        page = evidence.get('page', '')
        require(re.fullmatch(re.escape(PREVIEWS) + r'/(focus|spirit)-\d{2,}\.png', page),
                f'Invalid preview page: {aid}')
        page_raw = snapshot.read(page)
        require(page_raw is not None and digest(page_raw) == evidence.get('page_sha256'),
                f'Preview changed; export and review again: {aid}')
        for key in ('source', 'export'):
            raw = snapshot.read(row[key])
            require(raw is not None and digest(raw) == row.get(key + '_sha256') == evidence.get(key + '_sha256'),
                    f'{key} differs from reviewed preview: {aid}')
        gen = generation(snapshot, aid)
        if gen:
            require(gen == row.get('generation'), f'Generation metadata changed; export and review again: {aid}')
            original = snapshot.read_path(Path(gen['generated']))
            require(original is None or digest(original) == row['source_sha256'],
                    f'Generated PNG changed; export and review again: {aid}')
        # Use binder's full PNG/TGA/hash validation with a temporary approval,
        # without calling its gameplay rewrite or writing anything yet.
        candidate = dict(row, approved=True)
        binder()['verified_asset'](snapshot, candidate)
        row['approved'] = True
        row['status'] = 'approved'
        row['approval'] = {'basis': 'Explicit --approve after main/human visual review',
                           'source_sha256': row['source_sha256'], 'export_sha256': row['export_sha256'],
                           'preview_page': page, 'preview_page_sha256': evidence['page_sha256']}
    # Schema validation reparses JSON; its rows are detached from document.
    document['assets'] = rows
    return {MANIFEST: json_bytes(document)}, len(selected)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    actions = parser.add_mutually_exclusive_group()
    actions.add_argument('--export', action='store_true', help='Write source copies, TGAs, manifest and QA sheets')
    actions.add_argument('--approve', nargs='+', metavar='ID', help='Explicitly approve IDs after reviewing exported sheets')
    parser.add_argument('--margin', type=int, default=2, help='Transparent inset in native pixels (default: 2)')
    parser.add_argument('--keep-canvas', action='store_true', help='Keep full source canvas instead of alpha bounding box')
    parser.add_argument('--page-size', type=int, default=18, help='Maximum assets per sheet, 1..18 (default: 18)')
    args = parser.parse_args()
    require(0 <= args.margin < 32, 'Margin must be 0..31 native pixels')
    require(1 <= args.page_size <= 18, 'Page size must be 1..18')
    snapshot = Snapshot(ROOT)
    if args.approve:
        outputs, count = approve(snapshot, args.approve)
        changed = snapshot.write(outputs)
        print(f'{count} explicitly approved; {changed} manifest updated. No binding/gameplay changes.')
        return
    document, outputs, images = prepare(snapshot, args.margin, args.keep_canvas)
    ready = len(images)
    approved = sum(r['approved'] for r in document['assets'])
    pending = len(document['assets']) - ready
    if args.export:
        outputs.update(sheets(document, images, args.page_size))
        outputs[MANIFEST] = json_bytes(document)
        changed = snapshot.write(outputs)
        print(f'{ready} ready, {pending} pending generation, {approved} prior approvals preserved; {changed} files updated.')
        print(f'Visual review: {PREVIEWS}/. Explicit approval is separate; no bindings changed.')
    else:
        print(f'READ-ONLY: {len(document["assets"])} records; {ready} ready, {pending} pending generation, {approved} approvals preservable.')
        print('Use --export to write mechanical outputs. Review the sheets before a separate --approve ID command.')


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, AssertionError) as error:
        raise SystemExit(str(error))
