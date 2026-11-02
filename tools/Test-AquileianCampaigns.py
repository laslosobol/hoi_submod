"""Expanded regional campaigns: parsed source scenarios, not an engine test."""
import copy
import json
import re
import runpy
import unittest
from pathlib import Path

API=runpy.run_path(str(Path(__file__).with_name('Test-AquileianRegions.py')))
Fixture, ROUTES, P, ROOT, MOD, OPT, walk, parse=(API[k] for k in ('Fixture','ROUTES','P','ROOT','MOD','OPT','walk','parse'))


class Campaigns(Fixture):
    def test_every_programme_has_distinct_economic_military_and_national_stages(self):
        p=self.production
        expected={P+'CAM_'+r.key+'_'+s+str(i) for r in ROUTES for s,count in [('e',5),('m',5),('c',2)] for i in range(1,count+1)}
        actual={f for f in p.focuses if f.startswith(P+'CAM_')}
        self.assertEqual(actual,expected)
        self.assertFalse(any(f.startswith(P+'BASE_') or f.startswith('griffon_') for f in p.focuses))
        titles=[]
        for tag in ('JEB','JRR','JFT','VIN'):
            data=json.loads((ROOT/f'tools/data/aquileian-campaigns/{tag}.json').read_text(encoding='utf-8-sig'))
            self.assertEqual(len(data['foundations']),4)
            for route in data['routes']:
                self.assertGreaterEqual(sum(f['days'] for f in route['focuses']),420)
                self.assertLessEqual(sum(f['days'] for f in route['focuses']),600)
                self.assertEqual(len(route['scenes']),3)
                for focus in route['focuses']:
                    titles.append(focus['title'][1])
                    fid=P+'CAM_'+route['id']+'_'+focus['slot']
                    self.assertTrue(p.focuses[fid].all('allow_branch'))
                    for desc in focus['desc']:
                        self.assertNotRegex(desc,r'\d\s*%|\bHSM_|\bAI\b|\bШИ\b|§[GRY]')
                for scene in route['scenes']:
                    self.assertEqual(len(scene['options']),2)
                    for desc in scene['desc']:
                        self.assertGreaterEqual(len(desc.split()),110)
        self.assertEqual(len(titles),len(set(titles)),'Each political programme needs its own focus titles')

    def test_all_routes_complete_both_branches_without_stacking_idea_stages_or_replaying_rewards(self):
        for route in ROUTES:
            with self.subTest(route=route.key):
                w=self.national(route)
                c=w.countries[route.tag]
                c.research_slots=3
                c.ideas.update({'poverty','lack_of_scientists2','pre_industrial_society'})
                for family,count in [('e',5),('m',5),('c',2)]:
                    for stage in range(1,count+1):
                        fid=P+'CAM_'+route.key+'_'+family+str(stage)
                        self.assertTrue(w.available(fid,route.tag),fid)
                        w.complete(fid,route.tag)
                        before=w.snapshot()
                        w.effect(fid,route.tag)
                        self.assertEqual(before,w.snapshot(),'Completion effects must be replay-safe')
                for family in ('economy','military'):
                    self.assertEqual({i for i in c.ideas if i.startswith(P+'CAM_'+route.key+'_'+family)},
                                     {P+'CAM_'+route.key+'_'+family+'3'})
                self.assertLessEqual(c.research_slots,5)
                self.assertGreaterEqual(c.research_slots,4)
                self.assertIn('modern_society',c.ideas)
                self.assertNotIn('pre_industrial_society',c.ideas)
                w.advance_days(1)
                packets=[p for p in w.scheduled if p[1]==route.tag and re.fullmatch(r'HSM_AQR\.6\d\d',p[2])]
                self.assertEqual(len(packets),3)
                for packet in packets:
                    self.assertTrue(w.deliver(packet[2],route.tag))
                    for choice in ('0','1'):
                        branch=copy.deepcopy(w)
                        branch.click(packet[2],packet[2]+'.'+choice,route.tag)
                        before=branch.snapshot()
                        branch.click(packet[2],packet[2]+'.'+choice,route.tag,stale=True)
                        self.assertEqual(before,branch.snapshot())

    def test_national_stages_wait_for_unification_and_other_programmes_remain_closed(self):
        for route in ROUTES:
            w=self.ratified(route)
            for family in ('e','m'):
                for stage in range(1,4): w.complete(P+'CAM_'+route.key+'_'+family+str(stage),route.tag)
                self.assertFalse(w.available(P+'CAM_'+route.key+'_'+family+'4',route.tag))
            w.complete(P+'CAM_'+route.key+'_c1',route.tag)
            self.assertFalse(w.available(P+'CAM_'+route.key+'_c2',route.tag))
            for other in ROUTES:
                if other != route:
                    self.assertFalse(w.available(P+'CAM_'+other.key+'_e1',route.tag))

    def test_foundations_work_before_revolution_without_changing_allegiance(self):
        for tag in ('JEB','JRR','JFT','VIN'):
            route=next(r for r in ROUTES if r.tag==tag)
            w=self.world(route)
            c=w.countries[tag]
            native_flags=set(c.flags)
            native_values=copy.deepcopy(c.variables)
            for i in range(1,5):
                fid=P+'LOCAL_'+tag+'_f'+str(i)
                w.complete(fid,tag)
                before=w.snapshot(); w.effect(fid,tag); self.assertEqual(before,w.snapshot())
            self.assertEqual(c.flags-{f for f in c.flags if f.startswith(P+'LOCAL_')},native_flags)
            self.assertEqual(c.variables,native_values)

    def test_focus_previews_use_real_rewards_and_no_internal_guard_flags(self):
        for fid,focus in self.production.focuses.items():
            if not (fid.startswith(P+'CAM_') or fid.startswith(P+'LOCAL_')): continue
            preview=focus.get('completion_reward',[])
            shown=[n for n in preview if n.key!='hidden_effect']
            self.assertTrue(any(n.key=='effect_tooltip' for n in shown),fid)
            self.assertFalse(any(n.key in ('has_country_flag','set_country_flag','custom_effect_tooltip') for n in walk(shown)),fid)
            self.assertTrue(any(n.key=='hidden_effect' for n in preview),fid)

    def test_lost_government_removes_its_old_programme_spirits(self):
        for lost in (P+'ratified',P+'ratified_'+ROUTES[0].key,'all'):
            w=self.ratified(ROUTES[0]); tag=ROUTES[0].tag
            for family in ('e','m'): w.complete(P+'CAM_'+ROUTES[0].key+'_'+family+'1',tag)
            if lost=='all': w.effect(P+'clear_mandate',tag)
            else: w.countries[tag].flags.discard(lost)
            w.effect(P+'refresh_campaign',tag)
            self.assertFalse(any(i.startswith(P+'CAM_') for i in w.countries[tag].ideas))

    def test_temporary_capitulation_does_not_erase_earned_programme_spirits(self):
        w=self.ratified(ROUTES[0]); tag=ROUTES[0].tag
        w.complete(P+'CAM_'+ROUTES[0].key+'_m1',tag)
        c=w.countries[tag]; before=set(c.ideas)
        c.capitulated=True
        w.effect(P+'refresh_campaign',tag)
        self.assertEqual(c.ideas,before)

    def test_existing_five_slots_do_not_lock_final_focus_or_grant_a_sixth(self):
        for key in ('VIN_abc','VIN_sis','JFT_enfants'):
            route=next(r for r in ROUTES if r.key==key)
            w=self.national(route); c=w.countries[route.tag]; c.research_slots=5
            for i in range(1,6): w.complete(P+'CAM_'+key+'_e'+str(i),route.tag)
            self.assertEqual(c.research_slots,5)
            self.assertTrue(c.bonuses)

    def test_research_slot_conditions_use_the_native_trigger(self):
        # Independently check EaW syntax: a permissive model must not conceal
        # an invented engine command in generated effects again.
        native=(OPT.eaw/'common/national_focus/generic_griffon.txt').read_text(encoding='utf-8-sig')
        self.assertRegex(native,r'\bamount_research_slots\s*[<=>]')
        effects=(MOD/'common/scripted_effects/HSM_AQR_regions.txt').read_text(encoding='utf-8-sig')
        self.assertIn('amount_research_slots < 5',effects)
        self.assertNotIn('num_of_research_slots',effects)

    def test_open_scene_can_be_closed_after_its_government_is_lost(self):
        route=ROUTES[0]; w=self.national(route); tag=route.tag
        w.complete(P+'CAM_'+route.key+'_e1',tag)
        w.complete(P+'CAM_'+route.key+'_e2',tag)
        w.advance_days(1)
        packet=next(p for p in w.scheduled if re.fullmatch(r'HSM_AQR\.6\d\d',p[2]))
        eid=packet[2]; self.assertTrue(w.deliver(eid,tag))
        w.effect(P+'clear_mandate',tag)
        visible=[o.get('name') for o in w.events[eid].all('option')
                 if w.check(o.get('trigger',[]),tag)]
        self.assertEqual(visible,[eid+'.lapsed'])
        before=w.snapshot()
        w.click(eid,eid+'.lapsed',tag)
        self.assertEqual(before,w.snapshot())


if __name__=='__main__': unittest.main(argv=[__file__,*API['BASE']['REST']],verbosity=2)
