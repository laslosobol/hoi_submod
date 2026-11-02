"""Shared provincial and national institutions. Imported by the AQR builder."""
P='HSM_AQR_'
TAGS=('JEB','JRR','JFT','VIN')

def build(loc,L,trig,effect,once,tt,focus,event,option,config):
    settled=tt('settled_req','Our winning programme has been ratified; the province is independent or autonomous under Aquileia.','Программа победившей стороны утверждена; провинция независима или автономна под властью Аквелии.','HSM_AQR_settled = yes')
    national=tt('national_req','Our regional government has proclaimed Aquileia and remains independent.','Наше областное правительство провозгласило Аквелию и сохраняет независимость.','HSM_AQR_national = yes')
    # Native JER_JFT_formed calls even a fascist Pridean successor a kingdom;
    # JER_formed also calls neutral republican programmes monarchies and harmonic
    # constitutional monarchies republics. Select by the ratified programme.
    republics = [rid for rid,camp,*_ in config if camp == 'rev' and rid != 'JEB_constitutional']
    trig('republican_national_programme', 'OR = { ' + ' '.join(
        f'has_country_flag = {P}ratified_{rid}' for rid in republics) + ' }')
    effect('apply_national_identity','''if = { limit = { HSM_AQR_national = yes }
 if = { limit = { HSM_AQR_republican_national_programme = yes }
  if = { limit = { NOT = { has_cosmetic_tag = JER_REPUBLIC } } set_cosmetic_tag = JER_REPUBLIC }
 }
 else = {
  if = { limit = { NOT = { has_cosmetic_tag = HSM_AQR_KINGDOM } } set_cosmetic_tag = HSM_AQR_KINGDOM }
 }
}''')
    # Repair already-proclaimed saves and a native secondary-tag reapplication.
    # Do not overwrite a later imperial identity or a foreign puppet cosmetic.
    effect('refresh_national_identity','''if = { limit = {
 HSM_AQR_national = yes
 OR = { has_cosmetic_tag = JER_formed has_cosmetic_tag = JER_JFT_formed has_cosmetic_tag = JER_REPUBLIC has_cosmetic_tag = HSM_AQR_KINGDOM }
}
 HSM_AQR_apply_national_identity = yes
}''')
    trig('united','HSM_AQR_national = yes\n'+'\n'.join(f'all_of_scopes = {{ array = {tag}.original_cores is_owned_and_controlled_by = ROOT }}' for tag in ('JER',*TAGS)))
    peaceful=tt('peace_req','The country is at peace.','Страна находится в мире.','has_war = no')
    programme_parents=tuple(r[0]+'_settle' for r in config)
    def reform(name,title,desc,x,y,parents,body,kind='local',days=35,icon='GFX_goal_generic_construct_civ_factory'):
        condition='HSM_AQR_settled = yes' if kind=='local' else 'HSM_AQR_national = yes'
        extra=''
        if name=='national_settlement':
            condition+=' HSM_AQR_united = yes has_war = no'
            body='set_country_flag = uniting_aquileia_proper\n'+body
            extra=tt('united_req','At peace; own and fully control all original territories of Aquileia, Rila, Westkeep, Pridea and Vinovia.','Мир; все первоначальные территории Аквелии, Рилы, Весткипа, Придеи и Виновии принадлежат нам и полностью контролируются.','HSM_AQR_united = yes has_war = no')
        once(name,condition,body+'\nHSM_AQR_refresh = yes')
        from aquileian_tooltips import spirit_changes
        bonus={
            'regional_articles':{'political_power_factor':.05},
            'supply_contracts':{'supply_consumption_factor':-.10},
            'common_market':{'production_speed_buildings_factor':.10},
            'national_services':{'industrial_capacity_factory':.10,'production_factory_max_efficiency_factor':.10},
            'national_army':{'army_org_factor':.05,'army_defence_factor':.05},
            'national_settlement':{'stability_factor':.05,'consumer_goods_factor':-.05},
        }.get(name)
        preview=''
        if bonus:
            L(P+name+'_bonus_tt',*spirit_changes(bonus)); preview=f'custom_effect_tooltip = {P}{name}_bonus_tt '
        if name!='national_settlement': preview+=f'effect_tooltip = {{ {body} }} '
        else:
            L(P+'settlement_story_tt','The founding delegates report on the national settlement.','Учредительные делегаты представят отчёт о государственном устройстве.')
            preview+='custom_effect_tooltip = HSM_AQR_settlement_story_tt '
        focus(name,title,desc,x,y,parents,(settled if kind=='local' else national)+extra,preview+f'hidden_effect = {{ {P}{name} = yes }}',cost=days/7,icon=icon,parents_and=name in ('common_market','national_recovery'))
    reform('regional_articles',('Articles of Provincial Government','Статьи областного управления'),('Petitions have been collected in rooms where the roof still leaks. They will now become rules: who appoints a magistrate, who audits the treasury, and where a village can appeal when the capital refuses to listen.','Прошения собирали в комнатах, где всё ещё течёт крыша. Теперь из них предстоит составить правила: кто назначает судью, кто проверяет казну и куда деревня может обратиться, когда столица отказывается её слушать.'),9,5,programme_parents,'add_political_power = 75')
    reform('provincial_schools',('A Classroom in Every District','Школа в каждом округе'),('Teachers cannot live on promises. Municipal councils will repair classrooms, organise training and agree how to pay the people who stay when the ceremonial visitors have gone.','Учителя не могут жить обещаниями. Муниципальные советы отремонтируют классы, организуют подготовку преподавателей и договорятся об оплате тех, кто останется на месте после отъезда торжественных делегаций.'),5,6,('regional_articles',),'decrease_illiteracy = yes',icon='GFX_goal_generic_scientific_exchange')
    reform('local_credit',('Credit without Patrons','Кредит без покровителей'),('A ruined harvest should not decide which family owns the village for the next generation. Local credit offices will inspect the accounts and make reconstruction loans available beyond the circle of court acquaintances.','Неурожай не должен решать, какая семья будет владеть деревней при следующем поколении. Местные кредитные учреждения проверят счета и откроют восстановительные ссуды тем, у кого нет знакомых при дворе.'),1,6,('regional_articles',),'decrease_poverty = yes')
    reform('supply_contracts',('Accounts for the Garrisons','Счета гарнизонов'),('Quartermasters and mayors will sit at the same table. Regular deliveries must replace improvised requisitions, and an officer who signs for food will be responsible for where it goes.','Интенданты и мэры сядут за один стол. Регулярное снабжение должно заменить случайные реквизиции, а офицер, расписавшийся за продовольствие, будет отвечать за его дальнейшую судьбу.'),13,6,('regional_articles',),'army_experience = 15',icon='GFX_goal_generic_army_motorized')
    reform('common_market',('Roads to the Weekly Market','Дороги к еженедельной ярмарке'),('Every district knows a bridge which exists only in the ministry\'s records. Surveyors will travel the actual roads, settle maintenance obligations and reconnect workshops to the towns which need their products.','В каждом округе знают мост, существующий только в министерских отчётах. Землемеры проедут по настоящим дорогам, распределят обязанности по ремонту и вновь свяжут мастерские с городами, которым нужны их изделия.'),9,7,('provincial_schools','local_credit','supply_contracts'),'random_owned_controlled_state = { limit = { is_core_of = ROOT } add_extra_state_shared_building_slots = 1 add_building_construction = { type = industrial_complex level = 1 instant_build = yes } }')
    # A claim only follows a real rupture. Being an autonomous loyal province is not a casus belli.
    once('national_mandate','HSM_AQR_rupture = yes','create_wargoal = { type = annex_everything target = JER }')
    focus('national_mandate',('Who Speaks for Aquileia?','Кто говорит от имени Аквелии?'),('Relations with the capital have broken down. Provincial delegates now argue that the state must be rebuilt around their settlement. Such a claim needs more than a proclamation: it needs a public account of why the old government has lost the right to command.','Отношения со столицей разорваны. Областные делегаты утверждают, что государство следует восстановить на основе их соглашения. Такому притязанию мало громкой прокламации: необходимо объяснить, почему прежнее правительство утратило право повелевать.'),21,6,('regional_articles',),tt('rupture_req','Independent; relations with Aquileia have broken through revolution, war or the end of subordination. No shared faction, non-aggression pact or truce.','Независимость; разрыв с Аквелией вследствие революции, войны или прекращения подчинения. Нет общего альянса, пакта о ненападении и перемирия.','HSM_AQR_rupture = yes'),'effect_tooltip = { create_wargoal = { type = annex_everything target = JER } } hidden_effect = { HSM_AQR_national_mandate = yes }',cost=5,icon='GFX_goal_generic_demand_territory')
    effect('proclaim','''if = { limit = { HSM_AQR_can_proclaim = yes }
 set_country_flag = HSM_AQR_nation
 set_country_flag = JER_formed
 if = { limit = { original_tag = JFT } set_country_flag = JER_JFT_formed }
 HSM_AQR_apply_national_identity = yes
 set_variable = { global.aquileia_var = THIS }
 set_capital = { state = 377 remember_old_capital = no }
 core_aquileian_heartland = yes
 claim_all_de_jure_aquileia = yes
 add_political_power = 100
 HSM_AQR_begin_reconstruction = yes
 country_event = { id = HSM_AQR.10 days = 1 }
}''')
    L(P+'proclaim_tt','Adopt the name, flag and colour of Aquileia appropriate to our government.','Принять название, флаг и цвет Аквелии, соответствующие нашему государственному устройству.')
    focus('proclaim',('An Aquileian Government','Аквелийское правительство'),('The provincial seal lies beside the seal recovered from the capital. Keeping both would be easy; persuading distant towns that the new administration belongs to them will be harder. The proclamation must carry obligations as well as a name.','Областная печать лежит рядом с печатью, найденной в столице. Сохранить обе несложно; убедить дальние города, что новое правительство принадлежит и им, будет труднее. Прокламация должна содержать обязательства, а не только новое имя.'),21,7,('national_mandate','common_market'),tt('proclaim_req','Ratified government, independence and peace; the old Aquileia no longer exists; own and fully control Aquileia (377).','Утверждённое правительство, независимость и мир; прежняя Аквелия больше не существует; Аквелия (377) принадлежит нам и полностью контролируется.','HSM_AQR_can_proclaim = yes'),'custom_effect_tooltip = HSM_AQR_proclaim_tt effect_tooltip = { set_capital = { state = 377 remember_old_capital = no } core_aquileian_heartland = yes claim_all_de_jure_aquileia = yes add_political_power = 100 country_event = { id = HSM_AQR.10 days = 1 } } hidden_effect = { HSM_AQR_proclaim = yes }',cost=5)
    event(10,('The Provincial Seal in the Capital','Областная печать в столице'),('A clerk brought the provincial registers into the national archive this morning. Their familiar bindings look small between the imperial shelves. Delegates from the towns which supported us want an answer: will the promises made while we were weak survive now that we govern the capital? The first invitations will go to the other provinces. Each must be allowed to answer in its own name.','Сегодня утром писарь принёс областные реестры в государственный архив. Их знакомые переплёты кажутся маленькими между высокими стеллажами. Делегаты поддержавших нас городов требуют ответа: сохранят ли силу обещания, данные во времена нашей слабости, теперь, когда мы управляем столицей? Первые приглашения отправятся в другие провинции. Каждой предстоит ответить от собственного имени.'),option('HSM_AQR.10.a',('We will be held to our articles.','Наши статьи обязывают и нас.')),'HSM_AQR_national = yes')
    send=''
    for tag in TAGS:
        send+=f'''if = {{ limit = {{ NOT = {{ original_tag = {tag} }} {tag} = {{ exists = yes has_war = no OR = {{ is_subject = no is_subject_of = ROOT }} NOT = {{ has_country_flag = HSM_AQR_offer_refused }} NOT = {{ has_country_flag = HSM_AQR_offer_pending }} }} }}
 {tag} = {{ set_country_flag = {{ flag = HSM_AQR_offer_pending days = 30 }} country_event = {{ id = HSM_AQR.20 days = 2 }} }}
}}\n'''
    effect('invite_regions','if = { limit = { HSM_AQR_national = yes has_war = no } '+send+' }')
    L(P+'invite_tt','Send accession proposals to the other independent regions and our regional subjects at peace. Acceptance transfers their territory and armed forces; refusal permits a separate political response.','Направить предложения о присоединении другим независимым областям и нашим областным субъектам, находящимся в мире. Согласие передаст их территории и вооружённые силы; отказ допускает отдельный политический ответ.')
    focus('invite_regions',('Articles for the Other Provinces','Статьи для остальных провинций'),('The invitation carries the same articles that limited our own provincial government. Envoys must explain what will be retained locally, what passes to the national administration, and who will hear a complaint when the agreement is broken.','В приглашении изложены те же статьи, которыми мы ограничили собственное областное правительство. Послам предстоит объяснить, что останется на местах, что перейдёт общему управлению и кто рассмотрит жалобу, если договор нарушат.'),21,8,('proclaim',),national+peaceful,'custom_effect_tooltip = HSM_AQR_invite_tt hidden_effect = { HSM_AQR_invite_regions = yes }',cost=3)
    effect('refuse_invitation','''if = { limit = { HSM_AQR_valid_invitation = yes }
set_country_flag = HSM_AQR_offer_refused
clr_country_flag = HSM_AQR_offer_pending
FROM = { country_event = { id = HSM_AQR.22 days = 1 } }
}''')
    effect('accept_invitation','''if = { limit = { HSM_AQR_valid_invitation = yes }
set_country_flag = HSM_AQR_accession_signed
clr_country_flag = HSM_AQR_offer_pending
FROM = {
 country_event = { id = HSM_AQR.21 days = 1 }
 annex_country = { target = ROOT transfer_troops = yes }
}
}''')
    offerguard=tt('offer_req','Both governments still exist and are at peace; the sender remains independent Aquileia; we are independent or its subject.','Оба правительства существуют и находятся в мире; отправитель остаётся независимой Аквелией; мы независимы либо подчинены ему.','HSM_AQR_valid_invitation = yes')
    event(20,('The Capital Invites Our Delegates','Столица приглашает наших делегатов'),('An envoy has delivered the new Aquileian government\'s articles. Local courts and elected councils would keep their ordinary duties, but foreign policy, the army and the common treasury would pass to the capital. This is an invitation to become part of one country. Our signatures would end the separate authority of the provincial government. The delegates have asked for the doors to be closed while they decide.','Посланник доставил статьи нового аквелийского правительства. Местные суды и выборные советы сохранят повседневные обязанности, но внешняя политика, армия и общая казна перейдут столице. Это приглашение стать частью единого государства. Наши подписи прекратят отдельную власть областного правительства. Делегаты попросили закрыть двери на время обсуждения.'),option('HSM_AQR.20.a',('We cannot endorse this national settlement.','Мы не поддержим такое государственное устройство.'),'hidden_effect = { HSM_AQR_refuse_invitation = yes }',ai=4)+option('HSM_AQR.20.b',('Sign the articles of accession.','Подписать статьи о присоединении.'),'custom_effect_tooltip = GAME_OVER_TT\ncustom_effect_tooltip = HSM_AQR_offer_req_tt\nhidden_effect = { HSM_AQR_accept_invitation = yes }','HSM_AQR_valid_invitation = yes',ai=8),'HSM_AQR_valid_invitation = yes')
    event(21,('A Provincial Seal Joins Ours','Ещё одна областная печать'),('The signed articles have arrived. Behind the wax and ribbons are offices which must be combined, officers whose commissions must be recognised, and villages that expect the agreement to protect them. The envoys will return with copies bearing both seals.','Подписанные статьи прибыли. За воском и лентами стоят учреждения, которые предстоит объединить, офицеры, чьи звания нужно подтвердить, и деревни, ожидающие защиты от нового соглашения. Послы вернутся с экземплярами, скреплёнными обеими печатями.'),option('HSM_AQR.21.a',('Publish the guarantees.','Опубликовать гарантии.')),'HSM_AQR_national = yes')
    event(22,('The Empty Place at the Table','Пустое место за столом'),('The provincial delegates will not come. Their letter rejects the transfer of authority to the capital. Ministers who promised swift unity now have to explain whether they will accept a neighbour\'s refusal or seek a mandate to enforce the national claim.','Областные делегаты не приедут. Их письмо отвергает передачу власти столице. Министрам, обещавшим быстрое объединение, теперь придётся объяснить, примут ли они отказ соседа или потребуют полномочий для осуществления общегосударственного притязания.'),option('HSM_AQR.22.a',('We have their answer.','Мы получили их ответ.')),'HSM_AQR_national = yes')
    resistance=''
    for tag in TAGS:
        resistance+=f'if = {{ limit = {{ NOT = {{ original_tag = {tag} }} {tag} = {{ exists = yes is_subject = no has_country_flag = HSM_AQR_offer_refused }} NOT = {{ is_in_faction_with = {tag} }} NOT = {{ has_non_aggression_pact_with = {tag} }} NOT = {{ has_truce_with = {tag} }} }} create_wargoal = {{ type = annex_everything target = {tag} }} }}\n'
    trig('resisting_region','OR = { '+' '.join(f'AND = {{ NOT = {{ original_tag = {t} }} {t} = {{ exists = yes is_subject = no has_country_flag = HSM_AQR_offer_refused }} NOT = {{ is_in_faction_with = {t} }} NOT = {{ has_non_aggression_pact_with = {t} }} NOT = {{ has_truce_with = {t} }} }}' for t in TAGS)+' }')
    effect('break_resistance','if = { limit = { HSM_AQR_national = yes } '+resistance+' }')
    L(P+'break_resistance_tt','Gain annexation war goals against independent Rila, Westkeep, Pridea or Vinovia which refused accession. No goal is granted against a faction partner or a country protected by our pact or truce. War is not declared automatically.','Получить цели войны на аннексию независимых Рилы, Весткипа, Придеи или Виновии, отказавшихся присоединиться. Цели не выдаются против союзников и стран, с которыми действует пакт или перемирие. Война не объявляется автоматически.')
    focus('break_resistance',('Enforce the National Claim','Осуществить общегосударственное притязание'),('The assembly will hear the case for compulsion. Those who support it must name the government they intend to remove and explain what protections will remain for its people. A national seal cannot excuse an unnamed and endless war.','Собрание рассмотрит доводы в пользу принуждения. Сторонники такого шага должны назвать правительство, которое собираются устранить, и объяснить, какие гарантии останутся у его подданных. Общегосударственная печать не оправдывает безымянную и бесконечную войну.'),27,9,('invite_regions',),national+tt('resisting_req','An independent region has refused accession; no common faction, pact or truce prevents a response.','Независимая область отказалась присоединиться; общая фракция, пакт или перемирие не препятствуют ответу.','HSM_AQR_resisting_region = yes'),'custom_effect_tooltip = HSM_AQR_break_resistance_tt hidden_effect = { HSM_AQR_break_resistance = yes }',cost=5,icon='GFX_goal_generic_demand_territory')
    reform('national_services',('One Civil Service','Общая гражданская служба'),('Provincial clerks have brought incompatible forms and very similar grievances. A common service will recognise their experience while ending the practice of charging a second fee at every former frontier.','Областные писари привезли несовместимые бланки и весьма похожие жалобы. Общая служба признает их опыт и положит конец привычке взимать новую пошлину на каждой прежней границе.'),17,9,('invite_regions',),'add_political_power = 75',kind='national',days=42)
    reform('national_schools',('The Next Generation of Teachers','Следующее поколение учителей'),('The first provincial schools have sent their best pupils to teacher training. They arrive speaking differently and remembering different sides of the revolution. Their classrooms must give the next generation a country it can understand without demanding that every family forget its own history.','Первые областные школы направили лучших учеников на подготовку преподавателей. Они говорят по-разному и помнят революцию с разных сторон. Их классы должны дать следующему поколению понятную страну, не требуя от каждой семьи забыть собственную историю.'),13,10,('national_services',),'decrease_illiteracy = yes',kind='national',days=42,icon='GFX_goal_generic_scientific_exchange')
    reform('national_army',('Commissions Recognised by All','Общие офицерские патенты'),('A regiment should receive its orders through a chain of command which exists on paper as well as in the colonel\'s memory. Provincial veterans will keep their service records; their officers must accept a common training and supply system.','Полк должен получать приказы по цепи подчинения, существующей на бумаге, а не только в памяти полковника. Областные ветераны сохранят послужные списки; их офицерам предстоит принять общую систему подготовки и снабжения.'),21,10,('national_services',),'army_experience = 25',kind='national',days=42,icon='GFX_goal_generic_army_doctrines')
    reform('national_recovery',('Reopen the Workshops','Вновь открыть мастерские'),('The treasury will publish which workshops receive reconstruction credit and why. A minister who can point to a reopened yard or a repaired mill has a stronger answer to the villages than another victory speech.','Казна опубликует перечень мастерских, получивших восстановительный кредит, и основания выдачи ссуд. Министр, способный показать открытый цех или отремонтированную мельницу, ответит деревням убедительнее, чем очередной победной речью.'),17,11,('national_schools','national_army'),'decrease_poverty = yes\nrandom_owned_controlled_state = { limit = { is_core_of = ROOT } add_extra_state_shared_building_slots = 1 add_building_construction = { type = industrial_complex level = 1 instant_build = yes } }',kind='national',days=42)
    dispatch='\n'.join(f'if = {{ limit = {{ has_country_flag = {P}ratified_{r[0]} }} country_event = {{ id = HSM_AQR.{200+i} days = 1 }} }}' for i,r in enumerate(config))
    reform('national_settlement',('Promises beyond the Province','Обещания за пределами провинции'),('The founding delegates return to the capital with letters from their districts. They will compare the first articles with the institutions now governing the whole country. The argument is no longer about who won the revolution, but about what victory has made possible for the people who survived it.','Учредительные делегаты возвращаются в столицу с письмами своих округов. Они сопоставят первые статьи с учреждениями, теперь управляющими всей страной. Спор идёт уже не о том, кто выиграл революцию, а о том, что победа дала пережившим её людям.'),17,12,('national_recovery',),dispatch,kind='national',days=42,icon='GFX_goal_generic_political_pressure')
    # The border policy is a later, optional settlement of a war fought through ordinary diplomacy.
    from aquileian_herzland import build_herzland
    build_herzland(L,trig,effect,once,tt,focus,config,national,peaceful)
    from aquileian_loyalty import build_loyalty
    congress_decisions=build_loyalty(L,trig,effect,once,tt,focus,event,option,config)
    possible='OR = { '+' '.join(f'AND = {{ NOT = {{ original_tag = {t} }} {t} = {{ exists = yes has_war = no OR = {{ is_subject = no is_subject_of = ROOT }} NOT = {{ has_country_flag = HSM_AQR_offer_refused }} NOT = {{ has_country_flag = HSM_AQR_offer_pending }} }} }}' for t in TAGS)+' }'
    trig('can_resend','HSM_AQR_national = yes has_war = no '+possible)
    L(P+'resend','Invite the Remaining Delegates','Пригласить оставшихся делегатов')
    L(P+'resend_desc','The chancery keeps a place for provinces which could not answer while they were at war. Their delegates will receive the same articles and the same right to decline.','Канцелярия сохраняет места для областей, которые не могли ответить во время войны. Их делегаты получат те же статьи и то же право отказаться.')
    return congress_decisions + [f'''HSM_AQR_resend = {{
icon = generic_political_discourse
visible = {{ HSM_AQR_national = yes has_completed_focus = HSM_AQR_invite_regions }}
available = {{ {tt('resend_req','At peace; another independent province or our subject can receive an offer and has not refused it.','Мир; другая независимая область или наш субъект может получить предложение и ещё не отказывался.', 'HSM_AQR_can_resend = yes')} }}
cost = 0 days_re_enable = 30
complete_effect = {{ custom_effect_tooltip = HSM_AQR_invite_tt hidden_effect = {{ HSM_AQR_invite_regions = yes }} }}
ai_will_do = {{ factor = 15 }}
}}''']



