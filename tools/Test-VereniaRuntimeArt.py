"""Read-only fault injection and structural tests for country-scoped art bindings."""
import copy
import json
import runpy
import unittest

B = runpy.run_path(__file__.replace('Test-VereniaRuntimeArt.py', 'Bind-VereniaRuntimeArt.py'))

class Memory(B['Files']):
    def __init__(self):
        super().__init__(B['ROOT'])

    def alter(self, name, fn):
        data = json.loads(self.read(name))
        fn(data)
        self.snapshots[name] = json.dumps(data).encode()

class RuntimeArtTests(unittest.TestCase):
    def test_scope_and_art_only(self):
        outputs, rows = B['plan'](Memory())
        text = outputs[B['EFFECT']].decode()
        self.assertIn(B['SCOPE'], text)
        self.assertIn('include_invisible = yes', text)
        self.assertIn('on_weekly', outputs[B['HOOK']].decode())
        allowed = {'HSM_VER_reconcile_runtime_art', 'if', 'limit', 'OR', 'original_tag',
                   'every_military_industrial_organization', 'include_invisible',
                   'is_military_industrial_organization', 'set_mio_icon', 'every_character',
                   'has_character_flag', 'has_advisor_role', 'has_trait', 'is_female',
                   'set_portraits', 'army', 'small'}
        for _, node in B['API']['walk'](B['API']['spans'](text)):
            self.assertIn(node.key, allowed)
        self.assertEqual(sum(k == 'mio' for k,r in rows), 10)
        self.assertIn('generic_infantry_equipment_organization', text)

    def test_native_pin(self):
        f = Memory(); f.snapshots[B['NATIVE']] = f.read(B['NATIVE']) + b'\n'
        with self.assertRaisesRegex(ValueError, 'pin drift'): B['plan'](f)

    def test_selector_drift_even_unapproved(self):
        f = Memory()
        f.alter(B['ART']+'generated-advisor-bindings.json', lambda d: d['records'][0]['selector'].update(trait='wrong'))
        with self.assertRaisesRegex(ValueError, 'selector drift'): B['plan'](f)

    def test_bad_hash(self):
        f = Memory()
        path = B['ART']+'HSM_VER_MIO_general_aircraft.png'
        f.snapshots[path] = f.read(path) + b'corrupt'
        with self.assertRaisesRegex(ValueError, 'hash mismatch'): B['plan'](f)

    def test_wrong_mapping(self):
        f = Memory()
        f.alter(B['ART']+'mio-bindings.json', lambda d: d['records'][0].update(sprite='GFX_foreign'))
        with self.assertRaisesRegex(ValueError, 'mapping'): B['plan'](f)

    def test_approval_gate(self):
        f = Memory()
        f.alter(B['ART']+'mio-bindings.json', lambda d: d['records'][0].update(approved=False))
        outputs, rows = B['plan'](f)
        self.assertEqual(sum(k == 'mio' for k,r in rows), 9)
        self.assertNotIn('generic_tank_organization', outputs[B['EFFECT']].decode())

    def test_advisor_variants(self):
        f = Memory()
        data = json.loads(f.read(B['ART']+'generated-advisor-bindings.json'))
        for row in data['records']:
            row['approved'] = False
        selected = [data['records'][0], *[r for r in data['records'] if r['id'].startswith('generic_military_theorist')]]
        raw = bytearray(18 + 65*67*4); raw[2]=2;raw[12:14]=(65).to_bytes(2,'little');raw[14:16]=(67).to_bytes(2,'little');raw[16]=32;raw[17]=8
        for r in selected:
            r.update(approved=True, review='Synthetic test only', source_sha256=B['sha'](b'synthetic'))
            r['exports'][0]['sha256']=B['sha'](raw)
            f.snapshots[r['source']]=b'synthetic';f.snapshots[r['exports'][0]['path']]=bytes(raw)
        f.snapshots[B['ART']+'generated-advisor-bindings.json']=json.dumps(data).encode()
        out, rows = B['plan'](f)
        text=out[B['EFFECT']].decode()
        self.assertEqual(sum(k=='generated_advisor' for k,r in rows),3)
        self.assertIn('is_female = yes',text);self.assertIn('is_female = no',text)
        neutral=next(line for line in text.splitlines() if 'has_trait = communist_revolutionary' in line)
        self.assertNotIn('is_female',neutral)
        self.assertIn('has_character_flag = is_generic',neutral)

    def test_foreign_output(self):
        f=Memory();f.snapshots[B['EFFECT']]=b'foreign = {}'
        with self.assertRaisesRegex(ValueError,'foreign output'): B['plan'](f)

if __name__ == '__main__':
    unittest.main()
