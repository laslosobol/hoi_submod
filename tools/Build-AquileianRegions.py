"""Build the four provincial Aquileian campaigns; --check never writes.

Route prose is authored in data/aquileian-regions. Native preparation and its
outcome remain authoritative. This builder does not execute any game effects.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
MOD = ROOT / 'mod/HoISubmod'
P = 'HSM_AQR_'
TAGS = ('JEB', 'JRR', 'JFT', 'VIN')
# id, native camp, initial prerequisite, character, ideology, party
CONFIG = [
 ('JEB_royal','royal','JER_JEB_monarchist','JEB_duke_michel_discret','constitutional_monarchism','neutrality'),
 ('JEB_constitutional','rev','JER_JEB_revolutionary','JEB_duke_michel_discret','harmonic_constitutionalism','democratic'),
 ('JEB_moderate','rev','JER_JEB_revolutionary','HSM_AQR_JEB_moderate','liberalism','democratic'),
 ('JEB_cocardiers','rev','JER_JEB_revolutionary','HSM_AQR_JEB_cocardiers','republicanism','neutrality'),
 ('JRR_absolutist','royal','JRR_absolutist','HSM_AQR_jeanne_discret','despotism','neutrality'),
 ('JRR_coalition','royal','JRR_reformism','HSM_AQR_jeanne_discret','harmonic_constitutionalism','democratic'),
 ('JRR_colette','rev','JER_JRR_revolutionary','JRR_colonel_colette_solide','ultranationalism','fascism'),
 ('JFT_dennis','royal','JER_JFT_monarchist','JFT_baron_dennis_discret','despotism','neutrality'),
 ('JFT_communes','rev','JER_JFT_commie_supp','HSM_AQR_JFT_communes','anarchist_communism','communism'),
 ('JFT_enfants','rev','JER_JFT_fash_supp','HSM_AQR_JFT_enfants','ultranationalism','fascism'),
 ('JFT_fja','rev','JER_JFT_dem_supp','HSM_AQR_JFT_fja','socialism','democratic'),
 ('VIN_gadiffer','royal','JER_VIN_monarchist','VIN_duke_gadiffer_discret','despotism','neutrality'),
 ('VIN_abc','rev','JER_VIN_movements1','HSM_AQR_VIN_abc','democratic_socialism','communism'),
 ('VIN_chevaliers','rev','JER_VIN_movements2','HSM_AQR_VIN_chevaliers','conservative_liberalism','neutrality'),
 ('VIN_sis','rev','JER_VIN_movements3','HSM_AQR_VIN_sis','liberalism','democratic'),
]
ROUTE_MODS = [
 {'army_org_factor':.05,'stability_factor':.05},
 {'political_power_factor':.10,'stability_factor':.05},
 {'consumer_goods_factor':-.05,'production_speed_buildings_factor':.10},
 {'mobilization_speed':.15,'industrial_capacity_factory':.10},
 {'political_power_factor':.10,'army_org_factor':.05},
 {'production_speed_buildings_factor':.10,'supply_consumption_factor':-.05},
 {'army_org_factor':.10,'max_planning_factor':.15},
 {'industrial_capacity_dockyard':.15,'supply_consumption_factor':-.05},
 {'industrial_capacity_factory':.10,'consumer_goods_factor':-.05},
 {'production_factory_max_efficiency_factor':.10,'mobilization_speed':.15},
 {'research_speed_factor':.05,'consumer_goods_factor':-.05},
 {'local_resources_factor':.10,'production_speed_buildings_factor':.10},
 {'research_speed_factor':.10,'mobilization_speed':.10},
 {'army_defence_factor':.10,'army_org_factor':.05},
 {'political_power_factor':.10,'research_speed_factor':.05},
]
COLLECTIVE_NAMES = {
 'HSM_AQR_JEB_moderate':('Rilan Constitutional Committee','Рильский конституционный комитет'),
 'HSM_AQR_JEB_cocardiers':('Cocardier Executive Committee','Исполнительный комитет кокардистов'),
 'HSM_AQR_jeanne_discret':('Marquise Jeanne Discret','Маркиза Жанна Дискре'),
 'HSM_AQR_JFT_communes':('Council of Communes','Совет коммун'),
 'HSM_AQR_JFT_enfants':('Les Enfants Terribles Directorate','Директория Les Enfants Terribles'),
 'HSM_AQR_JFT_fja':('FJA Coalition Government','Коалиционное правительство МАФ'),
 'HSM_AQR_VIN_abc':('ABC Civic Council','Гражданский совет ABC'),
 'HSM_AQR_VIN_chevaliers':('Vinovian Council of Communities','Виновийский совет общин'),
 'HSM_AQR_VIN_sis':('Council of Law and Education','Совет права и образования'),
}
PARTY_NAMES = [
 ('Rilan Royalists','Рильские роялисты'),('Constitutional Bloc','Конституционный блок'),
 ('Union of Moderate Clubs','Союз умеренных клубов'),('Cocardiers','Кокардисты'),
 ('Jeanne\'s Court','Двор Жанны'),('Westkeep Civic Coalition','Гражданская коалиция Весткипа'),
 ('Military and Civic Coalition','Военно-гражданская коалиция'),
 ('Dennis\' Loyalists','Лоялисты Денниса'),('Federation of Communes','Федерация коммун'),
 ('Les Enfants Terribles','Les Enfants Terribles'),('FJA Coalition','Коалиция МАФ'),
 ('Gadiffer\'s Court','Двор Гадиффера'),('Friends of the ABC','Друзья ABC'),
 ('Chevaliers of Fidelity','Рыцари верности'),('Society of Intellectual Students','Общество студентов-интеллектуалов'),
]

def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--eaw', type=Path, default=Path('C:/shit/Steam/steamapps/workshop/content/394360/1826643372'))
    parser.add_argument('--check', action='store_true')
    opt = parser.parse_args()
    data = {}
    for tag in TAGS:
        payload = json.loads((ROOT / f'tools/data/aquileian-regions/{tag}.json').read_text(encoding='utf-8-sig'))
        assert payload['tag'] == tag
        for r in payload['routes']:
            assert r['id'] not in data and len(r['focuses']) == 3
            data[r['id']] = r
    assert set(data) == {r[0] for r in CONFIG}
    loc = {}
    output = {}
    triggers, effects, events, focuses, decisions = [], [], ['add_namespace = HSM_AQR'], [], []
    def L(key,en,ru):
        assert key not in loc or loc[key] == (en,ru), key
        loc[key] = (en,ru)
        return key
    def block(dest,name,body): dest.append(f'{name} = {{\n{body}\n}}')
    def trig(name,body): block(triggers,P+name,body)
    def effect(name,body): block(effects,P+name,body)
    def once(name,condition,body):
        effect(name,f'if = {{ limit = {{ {condition} NOT = {{ has_country_flag = {P}{name}_done }} }}\nset_country_flag = {P}{name}_done\n{body}\n}}')
    def tt(name,en,ru,condition):
        L(P+name+'_tt',en,ru)
        return f'custom_trigger_tooltip = {{ tooltip = {P}{name}_tt {condition} }}'
    def focus(name,title,desc,x,y,parents=(),available='',reward='',cost=5,icon='GFX_goal_generic_political_pressure',branch='',ai=4,parents_and=False,exclusive=()):
        L(P+name,*title); L(P+name+'_desc',*desc)
        if name.startswith('REC_'):
            y += 5
        prereq = '' if not parents else 'prerequisite = { '+' '.join('focus = '+P+p for p in parents)+' }'
        if parents_and: prereq='\n'.join(f'prerequisite = {{ focus = {P}{p} }}' for p in parents)
        block(focuses,'shared_focus',f'id = {P}{name}\nicon = {icon}\nx = {x} y = {y}\ncost = {cost}\n{prereq}\n'+
              (('mutually_exclusive = { '+' '.join('focus = '+P+p for p in exclusive)+' }\n') if exclusive else '')+
              (f'allow_branch = {{ {branch} }}\n' if branch else '')+
              f'available = {{ {available} }}\ncancel_if_invalid = yes\ncompletion_reward = {{ {reward} }}\nai_will_do = {{ factor = {ai} }}')
    def event(number,title,desc,options,trigger='always = yes',immediate=''):
        key=f'HSM_AQR.{number}'
        L(key+'.t',*title)
        if isinstance(desc,tuple) or isinstance(desc,list): L(key+'.d',*desc); desc=f'desc = {key}.d'
        block(events,'country_event',f'id = {key}\ntitle = {key}.t\n{desc}\npicture = GFX_report_event_generic_parliament\nis_triggered_only = yes\ntrigger = {{ {trigger} }}\nimmediate = {{ {immediate} }}\n{options}')
    def option(key,title,body='',condition='',ai=1):
        L(key,*title)
        return f'option = {{ name = {key}\n'+(f'trigger = {{ {condition} }}\n' if condition else '')+f'ai_chance = {{ factor = {ai} }}\n{body}\n}}'

    trig('participant','OR = { '+' '.join('original_tag = '+t for t in TAGS)+' }')
    trig('alive','HSM_AQR_participant = yes exists = yes has_capitulated = no')
    trig('active','HSM_AQR_alive = yes has_country_flag = HSM_AQR_started')
    trig('local_rule','HSM_AQR_active = yes OR = { is_subject = no is_subject_of = JER }')
    trig('settled','HSM_AQR_local_rule = yes has_country_flag = HSM_AQR_ratified')
    trig('preparation','HSM_AQR_mechanic_active = yes')
    # Local alignment outranks the global victor. Immediate peaceful outcomes have no local flag.
    for camp,native,global_end in [('royal','monarchist','JER_revolution_ended'),('rev','revolutionary','JER_revolution_ended_2')]:
        trig('won_'+camp,f'OR = {{ has_country_flag = REVOLUTION_is_a_{native} AND = {{ NOT = {{ has_country_flag = REVOLUTION_is_a_monarchist }} NOT = {{ has_country_flag = REVOLUTION_is_a_revolutionary }} has_global_flag = {global_end} }} }}')
    trig('outcome','OR = { HSM_AQR_won_royal = yes HSM_AQR_won_rev = yes }')
    trig('no_route','NOT = { OR = { '+' '.join(f'has_country_flag = {P}route_{r[0]}' for r in CONFIG)+' } }')
    trig('can_proclaim','HSM_AQR_settled = yes is_subject = no has_war = no JER = { exists = no } 377 = { is_owned_and_controlled_by = PREV } NOT = { has_country_flag = HSM_AQR_nation }')
    trig('national','HSM_AQR_settled = yes is_subject = no has_country_flag = HSM_AQR_nation 377 = { is_owned_and_controlled_by = PREV }')
    trig('rupture', '''HSM_AQR_settled = yes is_subject = no JER = { exists = yes }
NOT = { is_in_faction_with = JER } NOT = { has_non_aggression_pact_with = JER } NOT = { has_truce_with = JER }
OR = {
 has_war_with = JER
 has_country_flag = HSM_AQR_former_subject
 has_country_flag = HSM_AQR_national_countermandate_done
 AND = { HSM_AQR_won_royal = yes JER = { has_completed_focus = JER_fight_for_freedom } }
 AND = { HSM_AQR_won_rev = yes JER = { NOT = { has_completed_focus = JER_fight_for_freedom } } }
}''')
    # FROM is the offer's sender. An unrelated subject is never a valid recipient.
    trig('valid_invitation', '''HSM_AQR_alive = yes has_war = no
OR = { is_subject = no is_subject_of = FROM }
FROM = { HSM_AQR_national = yes has_war = no NOT = { tag = ROOT } }
NOT = { has_war_with = FROM }
NOT = { has_country_flag = HSM_AQR_offer_refused }
''')
    clear = '\n'.join(f'clr_country_flag = {P}route_{r[0]}\nclr_country_flag = {P}ratified_{r[0]}' for r in CONFIG)
    effect('clear_mandate',clear+'\nclr_country_flag = HSM_AQR_ratified\nclr_country_flag = HSM_AQR_constitution_a\nclr_country_flag = HSM_AQR_constitution_b')
    components = [(f'ratified_{r[0]}',mods) for r,mods in zip(CONFIG,ROUTE_MODS)] + [
        ('constitution_a',{'stability_factor':.05,'political_power_factor':.10}),
        ('constitution_b',{'industrial_capacity_factory':.10,'army_org_factor':.05,'stability_factor':-.05}),
        ('regional_articles_done',{'political_power_factor':.05}),
        ('supply_contracts_done',{'supply_consumption_factor':-.10}),
        ('common_market_done',{'production_speed_buildings_factor':.10}),
        ('national_services_done',{'industrial_capacity_factory':.10,'production_factory_max_efficiency_factor':.10}),
        ('national_army_done',{'army_org_factor':.05,'army_defence_factor':.05}),
        ('national_settlement_done',{'stability_factor':.05,'consumer_goods_factor':-.05}),
    ]
    modifiers = sorted({m for _,v in components for m in v})
    refresh='\n'.join(f'set_variable = {{ {P}mod_{m} = 0 }}' for m in modifiers)
    for flag,values in components:
        refresh+=f'\nif = {{ limit = {{ has_country_flag = {P}{flag} }} '+ ' '.join(f'add_to_variable = {{ {P}mod_{m} = {v} }}' for m,v in values.items())+' }'
    refresh+='\nif = { limit = { NOT = { has_dynamic_modifier = HSM_AQR_compact } } add_dynamic_modifier = { modifier = HSM_AQR_compact } }'
    effect('refresh','hidden_effect = {\n'+refresh+'\n}')
    dyn='HSM_AQR_compact = {\nicon = GFX_idea_generic_constitutional_guarantees\nenable = { has_country_flag = HSM_AQR_started }\n'+'\n'.join(f'{m} = {P}mod_{m}' for m in modifiers)+'\n}'
    L(P+'compact','The Provincial Settlement','Провинциальное устройство')
    L(P+'compact_desc','The founding programme and the institutions built since the revolution shape the state.','Основополагающая программа и учреждения, созданные после революции, определяют облик государства.')
    L(P+'opening_effect_tt','The provincial assembly will discuss the surviving postwar programmes.','Областное собрание рассмотрит послевоенные программы сохранившихся политических сил.')
    focus('opening',('After the Revolution','После революции'),('The fighting has settled who holds the province, but the victorious camp still owes its neighbours an answer. Delegates bring the promises made in clubs, town halls and officers’ quarters to the same table. They must decide which of those promises can now become a government.','Борьба определила, кто удержал провинцию, но победившая сторона ещё должна дать ответ её жителям. Делегаты приносят за общий стол обещания, звучавшие в клубах, ратушах и офицерских собраниях. Теперь предстоит решить, какие из этих обещаний станут основой власти.'),9,0,available=tt('opening_req','Completes automatically after the revolution; our local government remains in place.','Выполняется автоматически после революции, если сохраняется местное управление.','always = no'),reward='custom_effect_tooltip = HSM_AQR_opening_effect_tt hidden_effect = { HSM_AQR_opening = yes }',cost=1,ai=0)
    from aquileian_native_phase import build_native_phase
    build_native_phase(trig,effect)
    from aquileian_native_settlement import build_native_settlement
    decisions.extend(build_native_settlement(L,trig,effect,once,tt,event,option,CONFIG,data))
    L(P+'defer','Reconvene when the treasury is ready.','Соберёмся вновь, когда казна будет готова.')
    L(P+'postpone_tt','The proposal remains available in provincial affairs. No political power is spent.','Предложение останется в делах провинции. Политическая власть не расходуется.')
    from aquileian_tooltips import spirit_changes
    L(P+'constitution_a_tt',*spirit_changes({'stability_factor':.05,'political_power_factor':.10}))
    L(P+'constitution_b_tt',*spirit_changes({'industrial_capacity_factory':.10,'army_org_factor':.05,'stability_factor':-.05}))
    characters={}
    for i,(rid,camp,initial,char,ideology,party) in enumerate(CONFIG):
        r=data[rid]; tag=rid[:3]; tagroutes=[c[0] for c in CONFIG if c[0][:3]==tag]; x=3+tagroutes.index(rid)*4
        trig('eligible_'+rid,f'original_tag = {tag} HSM_AQR_revolution_finished = yes HSM_AQR_won_{camp} = yes HSM_AQR_native_eligible_{rid} = yes')
        person_guard='' if char.startswith(P) else f'has_character = {char}'
        trig('can_pledge_'+rid,f'HSM_AQR_local_rule = yes HSM_AQR_eligible_{rid} = yes HSM_AQR_no_route = yes {person_guard}')
        trig('can_settle_'+rid,f'HSM_AQR_local_rule = yes HSM_AQR_won_{camp} = yes has_country_flag = {P}route_{rid} OR = {{ has_war = no AND = {{ has_country_flag = HSM_AQR_leadership_war_started has_war_with = JER }} }} NOT = {{ has_country_flag = HSM_AQR_ratified }} {person_guard}')
        trig('can_ratify_'+rid,f'HSM_AQR_can_settle_{rid} = yes has_completed_focus = {P}{rid}_settle NOT = {{ has_political_power < 50 }}')
        effect('finish_'+rid+'_pledge',f'if = {{ limit = {{ HSM_AQR_can_pledge_{rid} = yes }} set_country_flag = {P}route_{rid} }}')
        once('finish_'+rid+'_organise',f'HSM_AQR_local_rule = yes HSM_AQR_eligible_{rid} = yes has_country_flag = {P}route_{rid}','add_political_power = 35')
        effect('finish_'+rid+'_settle',f'if = {{ limit = {{ HSM_AQR_can_settle_{rid} = yes }} country_event = {{ id = HSM_AQR.{100+i} days = 1 }} }}')
        for j,suffix in enumerate(('pledge','organise','settle')):
            cond=f'HSM_AQR_can_pledge_{rid} = yes' if j==0 else (f'HSM_AQR_can_settle_{rid} = yes' if j==2 else f'HSM_AQR_local_rule = yes has_country_flag = {P}route_{rid}')
            if j==0:
                win=('monarchist','монархистов') if camp=='royal' else ('revolutionary','революционеров')
                text_req=('The victorious regional movement has endorsed this programme; no competing programme is active.','Победившее областное движение поддержало эту программу; другая программа не принята.')
            elif j==1:
                text_req=('This programme is active and our regional administration is functioning.','Эта программа выбрана, областное управление продолжает работу.')
            else:
                winner=('monarchist','монархическая') if camp=='royal' else ('revolutionary','революционная')
                text_req=('The chosen programme can form a government in peacetime or during our war for Aquileia.','Выбранная программа может учредить правительство в мирное время или во время нашей войны за Аквелию.')
            req=tt(rid+'_'+suffix+'_req',*text_req,cond)
            L(P+rid+'_'+suffix+'_effect',*(('Adopt the post-revolutionary programme.','Принять послереволюционную программу.') if j==0 else ('Political power: §G+35§!.','Политическая власть: §G+35§!.') if j==1 else ('The constituent assembly will meet. Ratification costs §Y50§! political power and establishes the government and its programme.','Будет созвано учредительное собрание. Утверждение требует §Y50§! политической власти и учреждает правительство с его программой.')))
            preview=(f'custom_effect_tooltip = {P}{rid}_{suffix}_effect' if j==0 else
                     'effect_tooltip = { add_political_power = 35 }' if j==1 else
                     f'effect_tooltip = {{ country_event = {{ id = HSM_AQR.{100+i} days = 1 }} }}')
            focus(rid+'_'+suffix,r['focuses'][j]['title'],r['focuses'][j]['desc'],x,j+1,('opening',) if j==0 else (rid+'_'+('pledge' if j==1 else 'organise'),),req,f'{preview} hidden_effect = {{ {P}finish_{rid}_{suffix} = yes }}',cost=2 if j==0 else 3,branch=f'original_tag = {tag}',ai=60 if j==0 else 40)
        # Existing people must still be present. Authored administrations are recruited once.
        if char.startswith(P): characters[char]=(COLLECTIVE_NAMES[char],ideology)
        install=(f'if = {{ limit = {{ NOT = {{ has_character = {char} }} }} recruit_character = {char} }}\n' if char.startswith(P) else '')
        install+=f'''if = {{ limit = {{ has_character = {char} }}
 if = {{ limit = {{ {char} = {{ has_ideology = {ideology} }} }}
  promote_character = {{ character = {char} ideology = {ideology} }}
 }}
 else = {{ add_country_leader_role = {{ character = {char} country_leader = {{ ideology = {ideology} expire = "1060.1.1" }} promote_leader = yes }} }}
 set_politics = {{ ruling_party = {party} elections_allowed = {"yes" if party=="democratic" else "no"} }}
}}'''
        L(P+rid+'_party',*PARTY_NAMES[i])
        install+=f'\nset_party_name = {{ ideology = {party} name = {P}{rid}_party long_name = {P}{rid}_party }}'
        install+='\nset_popularities = { '+' '.join(f'{p} = {55 if p==party else 15}' for p in ('democratic','communism','fascism','neutrality'))+' }'
        for choice in ('a','b'):
            effect('ratify_'+rid+'_'+choice,f'''if = {{ limit = {{ HSM_AQR_can_ratify_{rid} = yes }}
add_political_power = -50
set_country_flag = HSM_AQR_ratified
set_country_flag = {P}ratified_{rid}
set_country_flag = {P}constitution_{choice}
{install}
HSM_AQR_refresh = yes
mark_focus_tree_layout_dirty = yes
}}''')
        opts=option(P+'defer',loc[P+'defer'],f'custom_effect_tooltip = {P}postpone_tt',ai=0)
        for choice in ('a','b'):
            opts+=option(f'HSM_AQR.{100+i}.{choice}',r['debate'][choice],f'effect_tooltip = {{ add_political_power = -50 }} custom_effect_tooltip = {P}constitution_{choice}_tt\ncustom_effect_tooltip = {P}{rid}_government_tt\ncustom_effect_tooltip = {P}{rid}_programme_tt\nhidden_effect = {{ HSM_AQR_ratify_{rid}_{choice} = yes }}',f'HSM_AQR_can_ratify_{rid} = yes',ai=5)
        gov={'democratic':('Democratic / Harmony','Демократия / Гармония'),'communism':('Communist','Коммунизм'),'fascism':('Supremacist','Превосходство'),'neutrality':('Non-aligned','Нейтралитет')}[party]
        L(P+rid+'_government_tt',f'Government: {gov[0]}. Leader: ${char}$. Ruling support: §Y55%§!; other currents: §Y15%§! each. '+('Elections permitted.' if party=='democratic' else 'No scheduled national elections.'),f'Правительство: {gov[1]}. Правитель: ${char}$. Поддержка правящей силы: §Y55%§!; остальных течений: по §Y15%§!. '+('Выборы разрешены.' if party=='democratic' else 'Общегосударственные выборы не назначаются.'))
        from aquileian_tooltips import spirit_changes
        L(P+rid+'_programme_tt',*spirit_changes(ROUTE_MODS[i]))
        event(100+i,r['debate']['title'],r['debate']['desc'],opts,trigger=f'HSM_AQR_can_settle_{rid} = yes')
        for offset,scene in ((200,'epilogue'),(300,'border')):
            for c in ('a','b'): L(f'HSM_AQR.{offset+i}.{c}_desc',*r[scene][c+'_desc'])
            ds=f'desc = {{ trigger = {{ has_country_flag = HSM_AQR_constitution_b }} text = HSM_AQR.{offset+i}.b_desc }}\ndesc = {{ trigger = {{ NOT = {{ has_country_flag = HSM_AQR_constitution_b }} }} text = HSM_AQR.{offset+i}.a_desc }}'
            event(offset+i,r[scene]['title'],ds,option('HSM_AQR.acknowledge',('The work continues.','Работа продолжается.')),trigger=f'has_country_flag = {P}ratified_{rid}')
        decisions.append(f'''{P}resume_{rid} = {{
 icon = generic_political_discourse
 visible = {{ original_tag = {tag} has_completed_focus = {P}{rid}_pledge HSM_AQR_no_route = yes }}
 available = {{ {tt(rid+'_resume_req',*r['native_hint'],f'HSM_AQR_can_pledge_{rid} = yes')} }}
 cost = 0
 complete_effect = {{ {P}finish_{rid}_pledge = yes }}
 ai_will_do = {{ factor = 10 }}
}}
{P}ratify_again_{rid} = {{
 icon = generic_political_discourse
 visible = {{ has_country_flag = {P}route_{rid} has_completed_focus = {P}{rid}_settle NOT = {{ has_country_flag = HSM_AQR_ratified }} }}
 available = {{ {tt(rid+'_ratify_again_req','The winning programme can be ratified; reserve 50 political power.','Победившую программу можно утвердить; требуется 50 политической власти.',f'HSM_AQR_can_ratify_{rid} = yes')} }}
 cost = 0 days_re_enable = 7
 complete_effect = {{ {P}finish_{rid}_settle = yes }}
 ai_will_do = {{ factor = 30 }}
}}''')
        L(P+'resume_'+rid,'Resume: '+r['title'][0],'Возобновить: '+r['title'][1]); L(P+'resume_'+rid+'_desc','The programme can return to the assembly without repeating its earlier grants.','Программа может вернуться на рассмотрение собрания, сохранив результаты прежней работы.')
        L(P+'ratify_again_'+rid,'Reconvene: '+r['title'][0],'Собрать собрание: '+r['title'][1]); L(P+'ratify_again_'+rid+'_desc',*r['focuses'][2]['desc'])

    tick='HSM_AQR_record_native_outcome = yes\nHSM_AQR_open_postwar = yes\nif = { limit = { is_subject_of = JER } set_country_flag = HSM_AQR_former_subject }\n'
    for rid,camp,initial,char,ideology,party in CONFIG:
        tick+=f'if = {{ limit = {{ has_country_flag = {P}route_{rid} HSM_AQR_outcome = yes NOT = {{ HSM_AQR_won_{camp} = yes }} }} HSM_AQR_clear_mandate = yes HSM_AQR_refresh = yes }}\n'
        tick+=f'if = {{ limit = {{ has_country_flag = {P}route_{rid} has_country_flag = {P}native_outcome_recorded NOT = {{ has_country_flag = {P}ratified }} NOT = {{ HSM_AQR_native_eligible_{rid} = yes }} }} HSM_AQR_clear_mandate = yes HSM_AQR_refresh = yes }}\n'
        if not char.startswith(P):
            tick+=f'if = {{ limit = {{ has_country_flag = {P}route_{rid} NOT = {{ has_country_flag = HSM_AQR_ratified }} NOT = {{ has_character = {char} }} }} HSM_AQR_clear_mandate = yes HSM_AQR_refresh = yes }}\n'
    tick+='HSM_AQR_refresh_national_identity = yes\nHSM_AQR_refresh_campaign = yes\n'
    effect('tick',tick)
    decisions.extend(build_common(loc,L,trig,effect,once,tt,focus,event,option,CONFIG))
    from aquileian_reconstruction import build_reconstruction, build_reconstruction_decisions, ROOT_ID as recovery_root
    recovery_ideas=build_reconstruction(L,trig,effect,once,tt,focus,event,option)
    decisions.extend(build_reconstruction_decisions(tt,L))
    from aquileian_restoration import build_restoration
    build_restoration(L,trig,effect,once,tt,focus,event,option)
    from aquileian_campaigns import build_campaigns
    campaign_roots,campaign_ideas=build_campaigns(ROOT,L,trig,effect,once,tt,focus,event,option,CONFIG)
    import re
    roots=(*campaign_roots,recovery_root)
    tree='focus_tree = {\nid = HSM_AQR_regional_tree\ndefault = no\nreset_on_civilwar = no\ncountry = { factor = 0 modifier = { add = 1000 HSM_AQR_participant = yes } }\ncontinuous_focus_position = { x = 2400 y = 2200 }\nshared_focus = HSM_AQR_opening\n'+'\n'.join('shared_focus = '+r for r in roots)+'\n}\n'+ '\n\n'.join(focuses)+'\n'
    chartext='characters = {\n'
    for char,(name,ideology) in characters.items():
        if char == P+'jeanne_discret': name=('Marquise Jeanne Discret','Маркиза Жанна Дискре')
        L(char,*name)
        chartext+=f'{char} = {{ name = {char} portraits = {{ civilian = {{ large = "gfx/leaders/Asia/Unknown_Griffon.dds" }} }} country_leader = {{ ideology = {ideology} expire = "1060.1.1" }} }}\n'
    chartext+='}\n'
    def emit(path,text): output[path]=('# Generated by tools/Build-AquileianRegions.py.\n'+text.strip()+'\n').encode('utf-8')
    # JER_formed names harmonic constitutional monarchies republics and has no
    # national flag files. Reuse the actual Discret kingdom flag, in every size,
    # under a namespaced cosmetic so native republican governments stay intact.
    # Its colour is registered beside the existing VER entries in cosmetic.txt.
    for ideology in ('neutrality','democratic','communism','fascism'):
        for suffix,en,ru in (('', 'Kingdom of Aquileia', 'Королевство Аквелия'),
                             ('_DEF', 'the Kingdom of Aquileia', 'Королевство Аквелия'),
                             ('_ADJ', 'Aquileian', 'Аквелийск')):
            L(P+'KINGDOM_'+ideology+suffix,en,ru)
        for size in ('','medium','small'):
            folder=Path('gfx/flags')/size
            output[(folder/(P+'KINGDOM_'+ideology+'.tga')).as_posix()]=(opt.eaw/folder/'JER_neutrality.tga').read_bytes()
    emit('common/national_focus/HSM_AQR_regions.txt',tree)
    emit('common/scripted_triggers/HSM_AQR_regions.txt','\n\n'.join(triggers))
    emit('common/scripted_effects/HSM_AQR_regions.txt','\n\n'.join(effects))
    emit('common/dynamic_modifiers/HSM_AQR_regions.txt',dyn)
    emit('common/characters/HSM_AQR_regions.txt',chartext)
    emit('events/HSM_AQR_regions.txt','\n\n'.join(events))
    emit('common/ideas/HSM_AQR_reconstruction.txt',recovery_ideas)
    emit('common/ideas/HSM_AQR_campaigns.txt',campaign_ideas)
    maintenance='HSM_AQR_start_regions = yes\n'+'\n'.join(f'{tag} = {{ if = {{ limit = {{ has_country_flag = HSM_AQR_started }} HSM_AQR_tick = yes HSM_AQR_REC_integrate_owned = yes }} }}' for tag in TAGS)+'\nJER = { HSM_AQR_dispatch_postwar_choice = yes HSM_AQR_begin_reconstruction = yes HSM_AQR_REC_integrate_owned = yes }'
    emit('common/on_actions/HSM_AQR_regions.txt','on_actions = { on_daily = { effect = { '+maintenance+' } } }')
    emit('common/decisions/HSM_AQR_regions.txt','HSM_AQR_affairs = {\n'+'\n'.join(decisions)+'\n}')
    emit('common/decisions/categories/HSM_AQR_regions.txt','HSM_AQR_affairs = { icon = generic_political_actions allowed = { OR = { HSM_AQR_participant = yes original_tag = JER } } visible = { OR = { AND = { HSM_AQR_active = yes HSM_AQR_revolution_finished = yes } HSM_AQR_REC_reconstruction_active = yes } } }')
    L(P+'affairs','Provincial Affairs','Дела провинции')
    L(P+'affairs_desc','The assembly can return to unfinished constitutional business. The revolution and the province\'s relations with the capital determine which mandates remain viable.','Собрание может вернуться к незавершённым государственным делам. Исход революции и отношения провинции со столицей определяют, какие программы ещё могут быть осуществлены.')
    from aquileian_support_gui import build_support_gui
    gui_files,gui_loc=build_support_gui(opt.eaw)
    for path,body in gui_files.items(): emit(path,body)
    for key,pair in gui_loc.items(): L(key,*pair)
    from aquileian_native_phase import build_native_category_overlay
    category_path,category_body=build_native_category_overlay(opt.eaw)
    emit(category_path,category_body)
    category_target=MOD/category_path
    if category_target.exists():
        assert category_target.read_bytes() in (output[category_path],(opt.eaw/category_path).read_bytes()), 'Unreviewed native category override; refusing to overwrite'
    for lang,idx in [('english',0),('russian',1)]:
        def esc(s): return s.replace('\\','\\\\').replace('"','\\"').replace('\n','\\n')
        content='l_'+lang+':\n'+'\n'.join(f' {key}:0 "{esc(pair[idx])}"' for key,pair in sorted(loc.items()))+'\n'
        output[f'localisation/{lang}/HSM_AQR_regions_l_{lang}.yml']=content.encode('utf-8-sig')
    stale=[]
    # This generated file belonged only to the removed parallel preparation.
    # Refuse to delete a hand-edited/unrelated file on future rebuilds.
    for path in ('common/ideas/HSM_AQR_regions.txt',):
        target=MOD/path
        if target.exists():
            assert target.read_text(encoding='utf-8').startswith('# Generated by tools/Build-AquileianRegions.py.'), path
            stale.append(path+' (obsolete)')
            if not opt.check: target.unlink()
    for path,content in output.items():
        target=MOD/path
        if not target.exists() or target.read_bytes()!=content:
            stale.append(path)
            if not opt.check: target.parent.mkdir(parents=True,exist_ok=True); target.write_bytes(content)
    print(f'Aquileian regions: {len(CONFIG)} routes; {len(focuses)} new focuses; {len(loc)} keys/language; {len(output)} files; {len(stale)} '+('stale' if opt.check else 'updated'))
    if opt.check and stale: print('\n'.join(stale)); return 1
    return 0


def build_common(loc,L,trig,effect,once,tt,focus,event,option,config):
    from aquileian_common import build
    return build(loc,L,trig,effect,once,tt,focus,event,option,config)


if __name__ == '__main__':
    raise SystemExit(main())

