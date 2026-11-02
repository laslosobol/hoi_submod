"""Voluntary return from a victorious province to the native national movement.

The regional tag keeps its campaign unless the player explicitly chooses the
handover. Only a living native leader held by the victor or dormant JER may be
restored. Characters held by another country are never recruited or stolen.
"""
P='HSM_AQR_'

def build_restoration(L,trig,effect,once,tt,focus,event,option):
    trig('RESTORE_ready','''HSM_AQR_national = yes has_war = no
JER = { exists = no }
all_owned_state = { is_fully_controlled_by = PREV }
any_owned_state = { NOT = { state = 377 } }
''')
    leaders=('JER_king_moriset_discret','JER_vivienne_discret','JER_theodore_verany')
    for leader in leaders:
        trig('RESTORE_has_'+leader,f'OR = {{ has_character = {leader} JER = {{ has_character = {leader} }} }}')
    trig('RESTORE_existing_royal','''JER = {
has_completed_focus = JER_state_of_aquileia has_country_flag = JER_is_monarchist has_government = neutrality
OR = { has_country_leader = { character = JER_king_moriset_discret ruling_only = yes }
 has_country_leader = { character = JER_vivienne_discret ruling_only = yes } }
}''')
    trig('RESTORE_existing_republic','''JER = {
has_completed_focus = JER_fight_for_freedom has_country_flag = JER_democracy_established
OR = {
 has_country_leader = { character = JER_theodore_verany ruling_only = yes }
 has_country_leader = { character = JER_grand_cru ruling_only = yes }
 has_country_leader = { character = JER_cecile_gaudreau ruling_only = yes }
 has_country_leader = { character = JER_leonard_rodier ruling_only = yes }
 has_country_leader = { character = JER_sugar_crepe ruling_only = yes }
 has_country_leader = { character = JER_thibault_devereux ruling_only = yes }
 has_country_leader = { character = JER_victor_allard ruling_only = yes }
 has_country_leader = { character = JER_the_peoples_assemblee ruling_only = yes }
}
}''')
    trig('RESTORE_royal_ready','''HSM_AQR_RESTORE_ready = yes HSM_AQR_won_royal = yes
OR = { HSM_AQR_RESTORE_has_JER_king_moriset_discret = yes HSM_AQR_RESTORE_has_JER_vivienne_discret = yes }''')
    trig('RESTORE_republic_ready','''HSM_AQR_RESTORE_ready = yes HSM_AQR_won_rev = yes
OR = { HSM_AQR_RESTORE_has_JER_theodore_verany = yes HSM_AQR_RESTORE_existing_republic = yes }''')
    trig('RESTORE_possible','OR = { HSM_AQR_RESTORE_royal_ready = yes HSM_AQR_RESTORE_republic_ready = yes }')

    # Preserve the already paid reconstruction, without replaying its rewards.
    carry='''if = { limit = { ROOT = { has_country_flag = HSM_AQR_REC_begin_done } }
remove_ideas = HSM_AQR_REC_crisis
remove_ideas = HSM_AQR_REC_roofs
remove_ideas = HSM_AQR_REC_returning_workers
'''
    for stage in ('begin','postwar_housing','demobilisation','food_networks','peripheral_conference','peripheral_articles'):
        carry+=f'if = {{ limit = {{ ROOT = {{ has_country_flag = {P}REC_{stage}_done }} }} set_country_flag = {P}REC_{stage}_done }}\n'
    for idea in ('crisis','roofs','returning_workers'):
        carry+=f'if = {{ limit = {{ ROOT = {{ has_idea = {P}REC_{idea} }} }} add_ideas = {P}REC_{idea} }}\n'
    for stage in ('postwar_housing','demobilisation','food_networks','peripheral_conference','peripheral_articles'):
        carry+=f'if = {{ limit = {{ ROOT = {{ has_completed_focus = {P}REC_{stage} }} }} complete_national_focus = {P}REC_{stage} }}\n'
    carry+='}'

    for camp,root,opposite,party,endflag in (
        ('royal','JER_state_of_aquileia','JER_fight_for_freedom','neutrality','JER_revolution_ended'),
        ('republic','JER_fight_for_freedom','JER_state_of_aquileia','democratic','JER_revolution_ended_2'),
    ):
        chars=leaders[:2] if camp=='royal' else leaders[2:]
        move='\n'.join(f'if = {{ limit = {{ has_character = {char} }} {char} = {{ set_nationality = JER }} }}' for char in chars)
        if camp=='royal':
            government='''set_country_flag = JER_is_monarchist
clr_country_flag = JER_democracy_established
drop_cosmetic_tag = yes
if = { limit = { ROOT = { has_country_flag = HSM_AQR_RESTORE_moriset } }
 promote_character = JER_king_moriset_discret
}
else = {
 if = { limit = { has_character = JER_king_moriset_discret } retire_character = JER_king_moriset_discret }
 promote_character = JER_vivienne_discret
 # Moriset's fall has already happened: do not select the focus that shoots him.
 if = { limit = { NOT = { has_completed_focus = JER_to_kill_an_idea } }
  complete_national_focus = JER_to_kill_an_idea
 }
}
remove_ideas = JER_revolutionary
'''
        else:
            government='''clr_country_flag = JER_is_monarchist
set_country_flag = JER_democracy_established
set_cosmetic_tag = JER_REPUBLIC
promote_character = { character = JER_theodore_verany ideology = liberalism }
set_popularities = { democratic = 50 communism = 20 fascism = 20 neutrality = 10 }
set_country_flag = have_regular_puppets
clr_country_flag = JER_cant_do_war_focuses
remove_ideas = JER_memories
remove_ideas = JER_memories_2
'''
        other_end='JER_revolution_ended_2' if camp=='royal' else 'JER_revolution_ended'
        handover='\n'.join(f'''{"if" if i == 0 else "else_if"} = {{ limit = {{ tag = {tag} original_tag = {tag} }}
 if = {{ limit = {{ is_ai = no }} JER = {{ change_tag_from = {tag} }} }}
 JER = {{ annex_country = {{ target = {tag} transfer_troops = yes }} }}
}}''' for i,tag in enumerate(('JEB','JRR','JFT','VIN')))
        effect('RESTORE_'+camp,f'''if = {{ limit = {{ HSM_AQR_RESTORE_{camp}_ready = yes }}
set_country_flag = HSM_AQR_RESTORE_signed
if = {{ limit = {{ HSM_AQR_RESTORE_existing_{camp} = yes }} set_country_flag = HSM_AQR_RESTORE_preserve_national_campaign }}
if = {{ limit = {{ HSM_AQR_RESTORE_has_JER_king_moriset_discret = yes }} set_country_flag = HSM_AQR_RESTORE_moriset }}
377 = {{ transfer_state_to = JER }}
{move}
JER = {{
 if = {{ limit = {{ is_subject = yes }} overlord = {{ end_puppet = PREV }} }}
 set_capital = {{ state = 377 remember_old_capital = no }}
 inherit_technology = ROOT
 clr_global_flag = JER_revolution_begun
 clr_global_flag = {other_end}
 set_global_flag = {endflag}
 # Retain completed economic and military work; remove the opposing political
 # prerequisites so that the restored movement's own native route can proceed.
 if = {{ limit = {{ ROOT = {{ NOT = {{ has_country_flag = HSM_AQR_RESTORE_preserve_national_campaign }} }} }}
  uncomplete_national_focus = {{ focus = {opposite} uncomplete_children = yes refund_political_power = no }}
  load_focus_tree = {{ tree = aquileian_focus keep_completed = yes }}
  if = {{ limit = {{ NOT = {{ has_completed_focus = {root} }} }} complete_national_focus = {root} }}
  set_politics = {{ ruling_party = {party} elections_allowed = no }}
  {government}
 }}
 {carry}
}}
{handover}
JER = {{
 core_aquileian_heartland = yes
 HSM_AQR_begin_reconstruction = yes
}}
}}''')
    L(P+'RESTORE_transfer_tt',
      'Continue as Aquileia with its original political focus tree. All our territory and armed forces join it. The national movement retains its own succession or republican political contest; our provincial government ends. No foreign territory or character is taken.',
      'Продолжить игру за Аквелию с её оригинальным политическим деревом. Все наши территории и вооружённые силы войдут в её состав. Общегосударственное движение сохранит собственное престолонаследие или республиканскую политическую борьбу; наше областное правительство прекратит существование. Чужие территории и персонажи не передаются.')
    L(P+'RESTORE_open_tt','The assembly considers restoring the original national movement or retaining our own Aquileian government. This does not transfer power by itself.',
      'Собрание рассмотрит возвращение исходного общегосударственного движения или сохранение нашего аквелийского правительства. Само обсуждение не передаёт власть.')
    event(480,('Who Receives the National Seal?','Кому передать государственную печать?'),
      ('The capital has been secured, but victory leaves an older promise unanswered. Some delegates carried the banners of the national movement throughout the fighting; others expected their province to supply a new government for the whole country. The difference can no longer be hidden behind a common enemy. The seal lies on the table. Whoever receives it will govern Aquileia, and the delegates must decide whether their task was to restore an authority or to replace it.',
       'Столица удержана, но победа оставила без ответа давнее обещание. Одни делегаты всю войну несли знамёна общегосударственного движения; другие ожидали, что именно их провинция даст новое правительство всей стране. Больше нельзя скрывать это различие за общим врагом. Печать лежит на столе. Получивший её будет править Аквелией, а делегатам предстоит решить, состояла ли их задача в восстановлении власти или в её замене.'),
      option('HSM_AQR.480.a',('Our programme will govern Aquileia.','Аквелией будет править наше движение.'),ai=4)
      +option('HSM_AQR.480.b',('Return the seal to the lawful Discrets.','Вернуть печать законным Дискре.'),'custom_effect_tooltip = HSM_AQR_RESTORE_transfer_tt hidden_effect = { HSM_AQR_RESTORE_royal = yes }','HSM_AQR_RESTORE_royal_ready = yes',ai=8)
      +option('HSM_AQR.480.c',('Rejoin the national republican movement.','Вернуться к общереспубликанскому движению.'),'custom_effect_tooltip = HSM_AQR_RESTORE_transfer_tt hidden_effect = { HSM_AQR_RESTORE_republic = yes }','HSM_AQR_RESTORE_republic_ready = yes',ai=8),
      trigger='HSM_AQR_RESTORE_possible = yes')
    effect('RESTORE_convene','if = { limit = { HSM_AQR_RESTORE_possible = yes } country_event = { id = HSM_AQR.480 days = 1 } }')
    focus('restore_national_movement',('The Promise behind the Victory','Обещание, стоящее за победой'),
      ('The delegates who followed us to the capital did not all swear the same oath. The national administration must hear them before its first appointments make a temporary arrangement permanent. Restoring an old authority and building a new one both demand a public answer.',
       'Делегаты, последовавшие за нами в столицу, давали разные клятвы. Общегосударственное управление должно выслушать их, прежде чем первые назначения превратят временный порядок в постоянный. И восстановление прежней власти, и создание новой требуют открытого ответа.'),
      25,8,('proclaim',),tt('RESTORE_req','Independent Aquileia at peace; the former centre is gone. A living leader of our victorious national movement is available to us. Own and fully control the capital and retain another province.',
      'Независимая Аквелия в мире; прежний центр прекратил существование. Нам доступен живой лидер победившего общегосударственного движения. Столица принадлежит нам и полностью контролируется; у нас остаётся другая область.',
      'HSM_AQR_RESTORE_possible = yes'),'effect_tooltip = { country_event = { id = HSM_AQR.480 days = 1 } } hidden_effect = { HSM_AQR_RESTORE_convene = yes }',cost=3)
