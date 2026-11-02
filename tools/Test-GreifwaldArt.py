"""Greifwald art validation. --self-test uses temporary fixture images only.

Default/--check audits the finished manifest, exact hashes, native image formats,
bindings, unique sprite names, gameplay preservation and full target coverage.
Run final-art checks after production files exist; fixtures do not require them.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import io
import json
import runpy
import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
ART = runpy.run_path(str(ROOT / 'tools/Bind-GreifwaldArt.py'))
MOD, MANIFEST, NATIVE, OVERRIDE, GFX = [ART[k] for k in ('MOD', 'MANIFEST', 'NATIVE', 'OVERRIDE', 'GFX')]
FOCUS = MOD + '/common/national_focus/HSM_AET_campaign.txt'
RESTORED = MOD + '/common/national_focus/HSM_AET_restored.txt'
IDEAS = MOD + '/common/ideas/HSM_AET_campaign.txt'
DYNAMIC = MOD + '/common/dynamic_modifiers/HSM_AET_campaign.txt'


def png_or_tga(size, fmt, color=(120, 180, 200, 255), opaque=False):
    image = Image.new('RGBA', size, color if opaque else (0, 0, 0, 0))
    ImageDraw.Draw(image).rectangle((4, 4, size[0] - 5, size[1] - 5), fill=color)
    stream = io.BytesIO()
    image.save(stream, format=fmt)
    return stream.getvalue()


class FixtureTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='greifwald-art-test-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.initial = {
            FOCUS: b'\xef\xbb\xbf# keep BOM/CRLF\r\nshared_focus={ id=HSM_AET_one icon="GFX_old" # same name elsewhere\r\n cost=5 completion_reward={ add_stability=0.1 } }\r\nshared_focus={ id=HSM_AET_two icon=GFX_old cost=10 }\r\n',
            RESTORED: b'focus_tree={ id=HSM_AET_restored focus={ id=HSM_AET_GRI_one icon=GFX_old cost=5 } }\n',
            IDEAS: b'ideas={ country={ HSM_AET_new_spirit={ picture=old modifier={ stability_factor=0.05 } } } }\n',
            DYNAMIC: b'HSM_AET_compact={ icon=GFX_idea_old enable={ always=yes } stability_factor=HSM_AET_value }\n',
            NATIVE: b'\xef\xbb\xbf# native comment\r\nideas={ country={ AET_one={ picture="old" modifier={ army_org_factor=0.1 } }\r\n AET_two={ picture=old modifier={ research_speed_factor=0.1 } } } industrial_concern={ company={ picture=old } } }\r\n',
            MOD + '/common/national_focus/AET.txt': b'shared_focus={ id=AET_old icon=GFX_old }\n',
        }
        for path, raw in self.initial.items():
            self.write(path, raw)
        (self.root / MOD / 'interface').mkdir(parents=True)
        specs = [
            ('one', 'focus', [(FOCUS, 'HSM_AET_one'), (RESTORED, 'HSM_AET_GRI_one')]),
            ('two', 'focus', [(FOCUS, 'HSM_AET_two')]),
            ('new_spirit', 'spirit', [(IDEAS, 'HSM_AET_new_spirit')]),
            ('compact', 'dynamic', [(DYNAMIC, 'HSM_AET_compact')]),
            ('native_one', 'spirit', [(NATIVE, 'AET_one')]),
            ('native_two', 'spirit', [(OVERRIDE, 'AET_two')]),
        ]
        self.rows = []
        for aid, kind, targets in specs:
            row = {'id': aid, 'kind': kind,
                   'targets': [{'id': tid, 'file': file} for file, tid in targets],
                   'source': f'art/greifwald/source/{aid}.png',
                   'export': f'{MOD}/gfx/interface/{"goals" if kind == "focus" else "ideas"}/HSM_AET_{aid}.tga',
                   'gfx': ('GFX_' if kind == 'focus' else 'GFX_idea_') + 'HSM_AET_' + aid,
                   'approved': True}
            self.asset(row, 'source', png_or_tga((120, 100), 'PNG'))
            self.asset(row, 'export', png_or_tga((99, 86) if kind == 'focus' else (64, 64), 'TGA'))
            self.rows.append(row)
        self.save_manifest()

    def write(self, path, raw):
        file = self.root / path
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_bytes(raw)

    def asset(self, row, key, raw):
        self.write(row[key], raw)
        row[key + '_sha256'] = hashlib.sha256(raw).hexdigest()

    def save_manifest(self):
        self.write(MANIFEST, json.dumps({'assets': self.rows}).encode('utf-8'))

    def plan(self):
        files = ART['Files'](self.root)
        return files, ART['plan'](files)

    def apply(self):
        files, (outputs, _, _) = self.plan()
        ART['apply'](files, outputs)
        return outputs

    def test_distinct_ids_share_old_icon_without_global_replacement(self):
        outputs = self.apply()
        self.assertEqual(outputs[FOCUS], self.initial[FOCUS].replace(
            b'icon="GFX_old"', b'icon="GFX_HSM_AET_one"').replace(
            b'icon=GFX_old', b'icon=GFX_HSM_AET_two'))
        self.assertEqual(outputs[DYNAMIC], self.initial[DYNAMIC].replace(b'icon=GFX_idea_old', b'icon=GFX_idea_HSM_AET_compact'))
        self.assertEqual(outputs[IDEAS], self.initial[IDEAS].replace(b'picture=old', b'picture=HSM_AET_new_spirit'))
        native = self.initial[NATIVE].replace(b'picture="old"', b'picture="HSM_AET_native_one"').replace(
            b'AET_two={ picture=old', b'AET_two={ picture=HSM_AET_native_two')
        self.assertEqual(outputs[OVERRIDE], native)
        self.assertIn(b'company={ picture=old }', native)
        self.assertEqual((self.root / NATIVE).read_bytes(), self.initial[NATIVE])
        self.assertEqual((self.root / MOD / 'common/national_focus/AET.txt').read_bytes(),
                         self.initial[MOD + '/common/national_focus/AET.txt'])
        self.assertEqual(self.plan()[1], ({}, 6, 0))
        files = ART['Files'](self.root)
        self.assertEqual(ART['coverage'](files, self.rows), 7)

    def test_shared_target_asset_has_one_sprite_and_standard_shine(self):
        outputs = self.apply()
        sprites = ART['BASE']['sprite_nodes'](outputs[GFX])
        self.assertEqual(len(sprites), len(self.rows) + 2)
        self.assertEqual(sprites['GFX_HSM_AET_one'].get('textureFile'),
                         'gfx/interface/goals/HSM_AET_one.tga')
        shine = sprites['GFX_HSM_AET_one_shine']
        self.assertEqual(shine.get('effectFile'), 'gfx/FX/buttonstate.lua')
        self.assertEqual([a.get('animationrotation') for a in shine.all('animation')], ['-90.0', '90.0'])
        self.assertNotIn('GFX_HSM_AET_GRI_one', sprites)

    def test_generator_lookup_remaps_with_approval_and_exact_hashes(self):
        lookup = ART['approved_icon']
        self.assertEqual(lookup('HSM_AET_one', 'GFX_old', self.root), 'GFX_HSM_AET_one')
        self.assertEqual(lookup('HSM_AET_new_spirit', 'old', self.root), 'HSM_AET_new_spirit')
        self.assertEqual(lookup('HSM_AET_compact', 'GFX_idea_old', self.root), 'GFX_idea_HSM_AET_compact')
        self.assertEqual(lookup('absent', 'fallback', self.root), 'fallback')
        self.rows[0]['approved'] = False
        self.save_manifest()
        (self.root / self.rows[0]['source']).unlink()
        self.assertEqual(lookup('HSM_AET_one', 'fallback', self.root), 'fallback')
        self.rows[0]['approved'] = True
        self.save_manifest()
        with self.assertRaisesRegex(ValueError, 'Missing approved source'):
            lookup('HSM_AET_one', 'fallback', self.root)
        (self.root / MANIFEST).unlink()
        self.assertEqual(lookup('HSM_AET_one', 'fallback', self.root), 'fallback')

    def test_unapproved_native_does_not_copy_baseline(self):
        for row in self.rows:
            row['approved'] = False
        self.save_manifest()
        (self.root / NATIVE).unlink()
        self.assertEqual(self.plan()[1], ({}, 0, 6))
        self.assertFalse((self.root / OVERRIDE).exists())

    def test_native_override_is_not_recopied_or_gameplay_modified(self):
        self.apply()
        old = (self.root / OVERRIDE).read_bytes()
        self.write(OVERRIDE, old.replace(b'army_org_factor=0.1', b'army_org_factor=0.2'))
        with self.assertRaisesRegex(ValueError, 'outside approved pictures'):
            self.plan()
        self.assertIn(b'army_org_factor=0.2', (self.root / OVERRIDE).read_bytes())
        self.write(OVERRIDE, old + b'# unrelated edit\r\n')
        with self.assertRaisesRegex(ValueError, 'outside approved pictures'):
            self.plan()

    def test_hashes_fail_closed_and_write_nothing(self):
        for key in ('source', 'export'):
            with self.subTest(key=key):
                path = self.rows[0][key]
                old = (self.root / path).read_bytes()
                self.write(path, old + b'changed')
                with self.assertRaisesRegex(ValueError, 'SHA256'):
                    self.plan()
                self.assertFalse((self.root / GFX).exists())
                self.assertEqual((self.root / FOCUS).read_bytes(), self.initial[FOCUS])
                self.write(path, old)

    def test_bad_image_dimensions_format_and_alpha_rejected_even_if_reapproved(self):
        row = self.rows[0]
        images = [png_or_tga((64, 64), 'TGA'), png_or_tga((99, 86), 'PNG'),
                  png_or_tga((99, 86), 'TGA', opaque=True),
                  png_or_tga((99, 86), 'TGA', color=(0, 0, 0, 0))]
        for index, raw in enumerate(images):
            with self.subTest(case=index):
                self.asset(row, 'export', raw)
                self.save_manifest()
                with self.assertRaises(ValueError):
                    self.plan()

    def test_paths_native_focus_and_duplicate_targets_rejected(self):
        original = copy.deepcopy(self.rows)
        mutations = [
            lambda: self.rows[0].update(source='../outside.png'),
            lambda: self.rows[0].update(export=MOD + '/gfx/interface/goals/../bad.tga'),
            lambda: self.rows[0].update(gfx='GFX_goal_generic_old'),
            lambda: self.rows[0].update(approved='true'),
            lambda: self.rows[0]['targets'][0].update(file=MOD + '/common/national_focus/AET.txt'),
            lambda: self.rows[1]['targets'][0].update(id='HSM_AET_one'),
            lambda: self.rows[1].update(id='ONE'),
            lambda: self.rows[1].update(gfx=self.rows[0]['gfx'] + '_shine'),
            lambda: self.rows[4]['targets'][0].update(id='company'),
        ]
        for index, mutate in enumerate(mutations):
            with self.subTest(case=index):
                self.rows = copy.deepcopy(original)
                mutate()
                self.save_manifest()
                with self.assertRaises(ValueError):
                    self.plan()

    def test_duplicate_and_missing_source_fields_rejected(self):
        for raw in (self.initial[DYNAMIC] * 2,
                    self.initial[DYNAMIC].replace(b'icon=GFX_idea_old', b'icon={ name=GFX_old }'),
                    self.initial[DYNAMIC].replace(b'icon=GFX_idea_old', b'')):
            with self.subTest(source=raw):
                self.write(DYNAMIC, raw)
                with self.assertRaises(ValueError):
                    self.plan()

    def test_external_sprite_collision_rejected(self):
        self.write(MOD + '/interface/other.gfx', b'spriteTypes={spriteType={name=GFX_HSM_AET_one textureFile="elsewhere.tga"}}')
        with self.assertRaisesRegex(ValueError, 'Sprite collision'):
            self.plan()

    def test_cannot_withdraw_approval_and_leave_live_bindings(self):
        self.apply()
        self.rows[0]['approved'] = False
        self.save_manifest()
        with self.assertRaisesRegex(ValueError, 'previously bound sprites'):
            self.plan()

    def test_concurrent_source_change_aborts_apply(self):
        files, (outputs, _, _) = self.plan()
        self.write(FOCUS, self.initial[FOCUS] + b'# changed concurrently\n')
        with self.assertRaisesRegex(ValueError, 'Concurrent change'):
            ART['apply'](files, outputs)
        self.assertFalse((self.root / GFX).exists())

    def test_gameplay_signature_keeps_effects_and_modifiers(self):
        raw = self.initial[FOCUS]
        selector, _ = ART['field'](raw, 'focus', 'HSM_AET_one')
        patched = ART['rewrite'](raw, [('focus', 'HSM_AET_one', 'GFX_HSM_AET_one')])
        self.assertEqual(ART['signature'](raw.decode('utf-8'), {selector}),
                         ART['signature'](patched.decode('utf-8'), {selector}))
        changed = patched.replace(b'add_stability=0.1', b'add_stability=0.2')
        self.assertNotEqual(ART['signature'](raw.decode('utf-8'), {selector}),
                            ART['signature'](changed.decode('utf-8'), {selector}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', default=MANIFEST)
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument('--self-test', action='store_true')
    modes.add_argument('--check', action='store_true')
    args = parser.parse_args()
    if args.self_test:
        result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(FixtureTests))
        raise SystemExit(0 if result.wasSuccessful() else 1)
    files = ART['Files'](ROOT)
    outputs, approved, skipped = ART['plan'](files, args.manifest)
    ART['require'](not skipped, f'{skipped} art assets remain unapproved')
    count = ART['coverage'](files, ART['load_manifest'](files, args.manifest))
    ART['require'](not outputs, 'Bindings pending; run Bind-GreifwaldArt.py --apply: ' + ', '.join(sorted(outputs)))
    files.verify()
    print(f'PASS: {approved} approved assets, {count} targets; hashes, PNG/TGA, alpha, sprites and gameplay signature checked')


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, AssertionError) as error:
        raise SystemExit(str(error))
