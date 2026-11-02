"""Authored provincial foundations and fifteen postwar economic/military programmes.

Prose lives in tools/data/aquileian-campaigns. This module does no import-time I/O.
Rewards use native effect previews; flags and replay guards remain hidden.
"""
from pathlib import Path
import json

P = 'HSM_AQR_'
SLOTS = tuple('e'+str(i) for i in range(1,6)) + tuple('m'+str(i) for i in range(1,6)) + ('c1','c2')
RESEARCH = {
    'industry': ('industry',), 'electronics': ('electronics',),
    'infantry': ('infantry_weapons',), 'artillery': ('artillery',),
    'support': ('engineers_tech','recon_tech'), 'air': ('light_air',),
}


def reward(code, name):
    ordinary = {
        'pp50':'add_political_power = 50', 'pp75':'add_political_power = 75',
        'stability5':'add_stability = 0.05', 'war_support5':'add_war_support = 0.05',
        'manpower1500':'add_manpower = 1500',
        'rifles500':'add_equipment_to_stockpile = { type = infantry_equipment_0 amount = 500 producer = ROOT }',
        'army_xp20':'army_experience = 20', 'air_xp15':'air_experience = 15', 'navy_xp15':'navy_experience = 15',
        'poverty':'decrease_poverty = yes', 'literacy':'decrease_illiteracy = yes',
        'society':'increase_society_development = yes',
    }
    if code in ordinary:
        return ordinary[code]
    if code == 'research_slot':
        return research_capacity(name, 2)
    buildings = {'civ_factory':'industrial_complex','mil_factory':'arms_factory','dockyard':'dockyard','infrastructure':'infrastructure'}
    if code in buildings:
        kind = buildings[code]
        extra = ' is_coastal = yes' if code == 'dockyard' else ' infrastructure < 5' if code == 'infrastructure' else ''
        slots = '' if code == 'infrastructure' else 'add_extra_state_shared_building_slots = 1'
        return f'random_owned_controlled_state = {{ limit = {{ is_core_of = ROOT{extra} }} {slots} add_building_construction = {{ type = {kind} level = 1 instant_build = yes }} }}'
    if code.startswith('research_') and code[9:] in RESEARCH:
        categories = ' '.join('category = '+c for c in RESEARCH[code[9:]])
        return f'add_tech_bonus = {{ name = {P}{name} bonus = 1.0 uses = 1 {categories} }}'
    raise ValueError('Unknown campaign reward: '+code)


def research_capacity(name, slots=1):
    # Science-led programmes may reach five slots; other routes gain one.
    # A save that already has five retains a useful research bonus, never a
    # locked final focus. Conditions are native numerical requirements.
    bonus=f'add_tech_bonus = {{ name = {P}{name} bonus = 1.0 uses = 2 category = industry category = electronics }}'
    extra='if = { limit = { amount_research_slots < 4 } add_research_slot = 2 } else_' if slots==2 else ''
    return extra+f'if = {{ limit = {{ amount_research_slots < 5 }} add_research_slot = 1 }} else = {{ {bonus} }}'


def build_campaigns(root, L, trig, effect, once, tt, focus, event, option, config):
    data = {}
    foundations = {}
    for tag in ('JEB','JRR','JFT','VIN'):
        source = json.loads((Path(root)/f'tools/data/aquileian-campaigns/{tag}.json').read_text(encoding='utf-8-sig'))
        assert source['tag'] == tag
        foundations[tag] = source['foundations']
        assert [f['slot'] for f in foundations[tag]] == ['f1','f2','f3','f4']
        for route in source['routes']:
            assert route['id'].startswith(tag+'_') and route['id'] not in data
            assert set(f['slot'] for f in route['focuses']) == set(SLOTS)
            assert len(route['focuses']) == 12 and len(route['scenes']) == 3
            assert {s['after'] for s in route['scenes']} == {'e2','m3','c2'}
            data[route['id']] = route
    assert set(data) == {r[0] for r in config}
    roots, ideas, refresh = [], [], []
    available = tt('campaign_req','Our ratified provincial government remains in power.','Наше утверждённое областное правительство сохраняет власть.','HSM_AQR_settled = yes')
    national = tt('campaign_national_req','Our government has proclaimed Aquileia and controls its capital.','Наше правительство провозгласило Аквелию и контролирует её столицу.','HSM_AQR_national = yes')

    # Four local foundations replace generic starting activity. These do not
    # move revolutionary support, choose a camp or create preparation forces.
    for tag, records in foundations.items():
        for i, f in enumerate(records):
            name = 'LOCAL_'+tag+'_'+f['slot']
            body = reward(f['reward'],name)
            guard = f'original_tag = {tag} exists = yes has_capitulated = no'
            once(name,guard,body)
            parents = () if i in (0,2) else ('LOCAL_'+tag+'_f'+str(i),)
            if not parents: roots.append(P+name)
            focus(name,f['title'],f['desc'],33 if i<2 else 37,0 if i in (0,2) else 1,
                  parents,tt('foundation_req','Our regional administration is functioning.','Областное управление продолжает работу.','exists = yes has_capitulated = no'),
                  f'effect_tooltip = {{ {body} }} hidden_effect = {{ {P}{name} = yes }}',
                  cost=f['days']/7,branch='original_tag = '+tag,
                  icon='GFX_goal_generic_construct_civ_factory' if i<2 else 'GFX_goal_generic_army_motorized')

    for index, (rid,*_) in enumerate(config):
        route = data[rid]
        active = f'HSM_AQR_settled = yes has_country_flag = {P}ratified_{rid}'
        # Only one programme occupies these columns; ratification refreshes the
        # layout so four competing paths do not make an unreadable giant tree.
        branch = f'original_tag = {rid[:3]} has_country_flag = {P}ratified_{rid}'
        records = {f['slot']:f for f in route['focuses']}
        scene_ids = {scene['after']:600+index*3+j for j,scene in enumerate(route['scenes'])}
        for family in ('economy','military'):
            assert len(route['ideas'][family]) == 3
            for stage, record in enumerate(route['ideas'][family],1):
                idea = P+'CAM_'+rid+'_'+family+str(stage)
                L(idea,*record['title']); L(idea+'_desc',*record['desc'])
                assert 1 <= len(record['modifiers']) <= 3
                modifiers = '\n'.join(f'{key} = {value}' for key,value in record['modifiers'].items())
                ideas.append(f'{idea} = {{ picture = generic_constitutional_guarantees allowed = {{ always = no }} removal_cost = -1 modifier = {{ {modifiers} }} }}')
                refresh.append(f'if = {{ limit = {{ has_idea = {idea} NOT = {{ AND = {{ has_country_flag = {P}ratified has_country_flag = {P}ratified_{rid} }} }} }} remove_ideas = {idea} }}')

        for slot in SLOTS:
            f = records[slot]; name = 'CAM_'+rid+'_'+slot
            body = reward(f['reward'],name)
            if slot in ('e3','e5'):
                body += '\nincrease_society_development = yes'
            if slot == 'e5' and f['reward'] != 'research_slot':
                body += '\n'+research_capacity(name)
            ordinal = int(slot[1])
            if slot[0] in ('e','m') and ordinal in (1,3,5):
                family = 'economy' if slot[0]=='e' else 'military'
                stage = (ordinal+1)//2
                idea = P+'CAM_'+rid+'_'+family+str(stage)
                body += ('\nadd_ideas = '+idea if stage==1 else
                         f'\nswap_ideas = {{ remove_idea = {P}CAM_{rid}_{family}{stage-1} add_idea = {idea} }}')
            if slot in scene_ids:
                body += f'\ncountry_event = {{ id = HSM_AQR.{scene_ids[slot]} days = 1 }}'
            requires_nation = slot in ('e4','e5','m4','m5','c2')
            guard = active + (' HSM_AQR_national = yes' if requires_nation else '')
            once(name,guard,body)
            parent = rid+'_settle' if ordinal==1 else 'CAM_'+rid+'_'+slot[0]+str(ordinal-1)
            req = available + (national if requires_nation else '')
            focus(name,f['title'],f['desc'],{'e':33,'c':37,'m':41}[slot[0]],5+ordinal*2,
                  (parent,),req,f'effect_tooltip = {{ {body} }} hidden_effect = {{ {P}{name} = yes }}',
                  cost=f['days']/7,branch=branch,
                  icon={'e':'GFX_goal_generic_construct_civ_factory','m':'GFX_goal_generic_army_motorized','c':'GFX_goal_generic_scientific_exchange'}[slot[0]])
        for scene in route['scenes']:
            number=scene_ids[scene['after']]
            done=P+'CAM_'+rid+'_'+scene['after']+'_done'
            answered=P+'CAM_scene_'+str(number)+'_answered'
            guard=active+f' has_country_flag = {done} NOT = {{ has_country_flag = {answered} }}'
            assert len(scene['options']) == 2
            options=''
            for idx, opt in enumerate(scene['options']):
                name='CAM_scene_'+str(number)+'_'+str(idx)
                body=reward(opt['reward'],name)
                effect(name,f'if = {{ limit = {{ {guard} }} set_country_flag = {answered} {body} }}')
                options+=option(f'HSM_AQR.{number}.{idx}',opt['title'],
                                f'effect_tooltip = {{ {body} }} hidden_effect = {{ {P}{name} = yes }}',guard,ai=5)
            options+=option(f'HSM_AQR.{number}.lapsed',
                            ('File the report with the former government\'s papers.',
                             'Подшить отчёт к бумагам прежнего правительства.'),
                            condition=f'NOT = {{ AND = {{ {guard} }} }}')
            event(number,scene['title'],scene['desc'],options,guard)

    # Presentation-only migration: one layout refresh for existing campaigns.
    # It neither imports rewards from the removed generic tree nor replays any.
    refresh.append('''if = { limit = { has_focus_tree = HSM_AQR_regional_tree NOT = { has_country_flag = HSM_AQR_campaign_layout_v1 } }
 set_country_flag = HSM_AQR_campaign_layout_v1
 mark_focus_tree_layout_dirty = yes
}''')
    effect('refresh_campaign','\n'.join(refresh))
    return roots, 'ideas = { country = {\n'+'\n'.join(ideas)+'\n} }'
