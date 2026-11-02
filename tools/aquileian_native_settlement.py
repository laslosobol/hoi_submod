"""Postwar programme selection from a once-frozen native political settlement.

Pure callback builder: importing/calling this module writes no files. Main calls
snapshot_native_politics immediately after recording the actual native outcome,
then queue_native_settlement after the postwar opening. Returned decision blocks
belong in the existing provincial-affairs category. No native counters, rewards,
leaders, route/ratification flags or completed focuses are changed here.
"""

P = 'HSM_AQR_'
TAGS = ('JEB', 'JRR', 'JFT', 'VIN')
MOVEMENTS = {
    'JEB': (
        ('JEB_constitutional', 'JEB_michel', None),
        ('JEB_moderate', 'JEB_moderate_revolutionary_clubs', None),
        ('JEB_cocardiers', 'JEB_extremist_revolutionary_clubs', None),
    ),
    'JFT': (
        ('JFT_communes', 'JFT_second_commune_influence', 'JER_JFT_commie_supp'),
        ('JFT_enfants', 'JFT_les_enfants_terribles', 'JER_JFT_fash_supp'),
        ('JFT_fja', 'JFT_FJA_socdems', 'JER_JFT_dem_supp'),
    ),
    'VIN': (
        ('VIN_abc', 'VIN_abc_influence', 'JER_VIN_movements1'),
        ('VIN_chevaliers', 'VIN_chevaliers_influence', 'JER_VIN_movements2'),
        ('VIN_sis', 'VIN_students_influence', 'JER_VIN_movements3'),
    ),
}
POLITICAL_FLAGS = {
    'JEB': ('JER_JEB_monarchist', 'JER_JEB_revolutionary', 'JEB_enable_clubs'),
    'JRR': ('JER_JRR_monarchist', 'JER_JRR_revolutionary', 'JRR_absolutist', 'JRR_reformism'),
    'JFT': ('JER_JFT_monarchist', 'JER_JFT_revolutionary',
            'JER_JFT_commie_supp', 'JER_JFT_fash_supp', 'JER_JFT_dem_supp'),
    'VIN': ('JER_VIN_monarchist', 'JER_VIN_revolutionary',
            'JER_VIN_movements1', 'JER_VIN_movements2', 'JER_VIN_movements3'),
}
ROUTE_IDS = frozenset((
    'JEB_royal', 'JEB_constitutional', 'JEB_moderate', 'JEB_cocardiers',
    'JRR_absolutist', 'JRR_coalition', 'JRR_colette',
    'JFT_dennis', 'JFT_communes', 'JFT_enfants', 'JFT_fja',
    'VIN_gadiffer', 'VIN_abc', 'VIN_chevaliers', 'VIN_sis',
))


def _flag(name):
    return f'has_country_flag = {P}native_flag_{name}'


def _value(name):
    return P + 'native_value_' + name


def _or(conditions):
    return 'OR = { ' + ' '.join(conditions) + ' }'


def build_native_settlement(L, trig, effect, once, tt, event, option, config, route_data):
    """Register exports and events 410..413; return four retry decision blocks.

    Callbacks have the signatures used by Build-AquileianRegions.py. config rows
    are (rid, camp, native_prerequisite, character, ideology, party); route_data
    is keyed by rid and supplies bilingual titles. native_eligible_<RID> means a
    selected mandate or a compatible existing ratified route, NOT mere candidacy.
    Main retains its actual-camp and native-character guards. Migration of old
    unratified main-owned route locks is deliberately left to main.
    """
    routes = {row[0]: row for row in config}
    if len(routes) != len(config) or set(routes) != ROUTE_IDS:
        raise ValueError('Native settlement requires the agreed fifteen route IDs')
    if any(rid not in route_data or len(route_data[rid]['title']) != 2 for rid in routes):
        raise ValueError('Missing bilingual programme titles')
    for camp in ('royal', 'rev'):
        other = 'rev' if camp == 'royal' else 'royal'
        trig('native_won_' + camp,
             f'{P}won_{camp} = yes NOT = {{ {P}won_{other} = yes }}')

    snapshot = []
    for camp in ('royal', 'rev'):
        snapshot.append(f'if = {{ limit = {{ {P}native_won_{camp} = yes }} '
                        f'set_country_flag = {P}native_snapshot_{camp} }}')
    for tag in TAGS:
        values = [row[1] for row in MOVEMENTS.get(tag, ())]
        if tag == 'JEB':
            values.append('JEB_other_clubs')
        body = []
        for name in values:
            # Uninitialised VIN influence is zero; preserve real negative scores.
            body.append(f'if = {{ limit = {{ has_variable = {name} }} '
                        f'set_variable = {{ {_value(name)} = {name} }} }} '
                        f'else = {{ set_variable = {{ {_value(name)} = 0 }} }}')
        for name in POLITICAL_FLAGS[tag]:
            body.append(f'if = {{ limit = {{ has_country_flag = {name} }} '
                        f'set_country_flag = {P}native_flag_{name} }}')
        snapshot.append(f'if = {{ limit = {{ original_tag = {tag} }} '
                        + '\n'.join(body) + ' }')
    once('snapshot_native_politics',
         f'{P}participant = yes has_country_flag = {P}native_outcome_recorded '
         + _or([f'{P}native_won_{camp} = yes' for camp in ('royal', 'rev')]),
         '\n'.join(snapshot))

    trig('native_settlement_context', f'''{P}local_rule = yes
has_country_flag = {P}native_outcome_recorded
has_country_flag = {P}snapshot_native_politics_done
{P}revolution_finished = yes
OR = {{ has_war = no AND = {{ has_country_flag = HSM_AQR_leadership_war_started has_war_with = JER }} }}
has_completed_focus = {P}opening
NOT = {{ has_country_flag = {P}ratified }}''')

    for rid, camp, _initial, character, _ideology, _party in config:
        person = '' if character.startswith(P) else f'has_character = {character}'
        trig('native_live_' + rid,
             f'original_tag = {rid[:3]} {P}native_won_{camp} = yes {person}')
        trig('native_eligible_' + rid, f'''original_tag = {rid[:3]}
{P}native_won_{camp} = yes
OR = {{
 AND = {{ has_country_flag = {P}ratified has_country_flag = {P}ratified_{rid} }}
 AND = {{ has_country_flag = {P}native_mandate_{rid}
  has_country_flag = {P}snapshot_native_politics_done
  has_country_flag = {P}native_snapshot_{camp} {person} }}
}}''')

    # A movement flag is evidence even at zero influence (VIN introductions do
    # not initialise their influence). Positive scores can preserve old saves
    # lacking an otherwise expected flag; negative/zero unflagged rivals cannot.
    for tag, movements in MOVEMENTS.items():
        for rid, variable, flag in movements:
            evidence = 'always = yes' if tag == 'JEB' else _or([
                _flag(flag), f'check_variable = {{ {_value(variable)} > 0 }}'])
            # Rank the recorded movements, even if a prospective leader is now
            # absent. Losing that character cannot promote a zero-seat rival.
            # Current character availability is checked separately at candidacy.
            trig('native_pool_' + rid,
                 f'original_tag = {tag} {P}native_won_rev = yes {evidence}')
        if tag == 'JEB':
            evidence = [f'check_variable = {{ {_value(v)} > 0 }}'
                        for v in [m[1] for m in movements] + ['JEB_other_clubs']]
            no_preparation = 'NOT = { ' + _or(evidence) + ' }'
        else:
            no_preparation = 'NOT = { ' + _or([
                f'{P}native_pool_{rid} = yes' for rid, _, _ in movements]) + ' }'
        trig('native_unprepared_' + tag, no_preparation)
        for rid, variable, _flag_name in movements:
            comparisons = [f'{P}native_pool_{rid} = yes']
            for other, other_var, _ in movements:
                if other != rid:
                    comparisons.append(_or([
                        f'NOT = {{ {P}native_pool_{other} = yes }}',
                        f'check_variable = {{ var = {_value(variable)} value = {_value(other_var)} compare = greater_than_or_equals }}']))
            trig('native_top_' + rid, '\n'.join(comparisons))

    marais = ['NOT = { HSM_AQR_native_unprepared_JEB = yes }']
    for rid, variable, _ in MOVEMENTS['JEB']:
        marais.append(_or([f'NOT = {{ {P}native_pool_{rid} = yes }}',
                           f'check_variable = {{ var = {_value("JEB_other_clubs")} value = {_value(variable)} compare = greater_than_or_equals }}']))
    trig('native_marais_coalition', '\n'.join(marais))
    royal_choices = _or([_flag('JRR_absolutist'), _flag('JRR_reformism')])
    trig('native_unprepared_JRR', 'NOT = { ' + royal_choices + ' }')

    for rid, camp, _initial, _character, _ideology, _party in config:
        tag = rid[:3]
        if tag in MOVEMENTS and camp == 'rev':
            # The native preparation owns the mandate. Marais can negotiate
            # with the strongest named clubs, not unlock every political path.
            # Missing organisation evidence must never become an all-path menu.
            basis = (f'NOT = {{ {P}native_unprepared_{tag} = yes }} '
                     f'{P}native_top_{rid} = yes')
        elif rid in ('JRR_absolutist', 'JRR_coalition'):
            native_flag = 'JRR_absolutist' if rid == 'JRR_absolutist' else 'JRR_reformism'
            basis = _flag(native_flag)
        else:
            # The actual winning camp, not its former allegiance, admits these
            # sole native personalities. Character presence is checked above.
            basis = 'always = yes'
        trig('native_candidate_' + rid, f'''{P}native_settlement_context = yes
{P}native_live_{rid} = yes
has_country_flag = {P}native_snapshot_{camp}
{basis}''')

    trig('native_choice_valid', _or([
        f'AND = {{ has_country_flag = {P}native_mandate_{rid} {P}native_live_{rid} = yes }}'
        for rid in routes]))
    trig('native_has_candidate', _or([f'{P}native_candidate_{rid} = yes' for rid in routes]))
    trig('native_settlement_ready', f'''{P}native_settlement_context = yes
{P}native_has_candidate = yes
NOT = {{ {P}native_choice_valid = yes }}''')
    trig('native_can_reopen', f'''{P}native_settlement_ready = yes
NOT = {{ has_country_flag = {P}native_settlement_queued }}
NOT = {{ has_country_flag = {P}native_settlement_pending }}''')

    clear_mandates = '\n'.join(f'clr_country_flag = {P}native_mandate_{rid}' for rid in routes)
    for rid in routes:
        effect('native_select_' + rid, f'''if = {{ limit = {{
 {P}native_candidate_{rid} = yes NOT = {{ {P}native_choice_valid = yes }}
}}
 {clear_mandates}
 set_country_flag = {P}native_mandate_{rid}
 set_country_flag = {P}native_settlement_requested
 set_country_flag = {P}native_settlement_presented
 clr_country_flag = {P}native_settlement_pending
 clr_country_flag = {P}native_settlement_queued
}}''')

    queue = []
    for index, tag in enumerate(TAGS):
        queue.append(f'if = {{ limit = {{ original_tag = {tag} }} '
                     f'country_event = {{ id = HSM_AQR.{410 + index} days = 1 }} }}')
    effect('queue_native_settlement', f'''if = {{ limit = {{
 {P}native_can_reopen = yes
 NOT = {{ has_country_flag = {P}native_settlement_requested }}
 NOT = {{ has_country_flag = {P}native_settlement_presented }}
}}
 set_country_flag = {P}native_settlement_requested
 set_country_flag = {{ flag = {P}native_settlement_queued days = 7 }}
 {' '.join(queue)}
}}''')
    # Latch BEFORE scheduling: expiry or a failed delivery cannot cause an
    # automatic requeue every seven days. Only the explicit retry can reset it.
    immediate = f'''clr_country_flag = {P}native_settlement_queued
set_country_flag = {P}native_settlement_presented
set_country_flag = {{ flag = {P}native_settlement_pending days = 30 }}'''
    L(P + 'native_selection_tt',
      'Confirm the programme supported during the revolution. Its focus branch becomes available; the constituent assembly will establish the government.',
      'Подтвердить программу, поддержанную во время революции. Откроется её ветка фокусов; правительство будет учреждено учредительным собранием.')
    titles = {
        'JEB': ('The Rila Meeting', 'Рильское собрание'),
        'JRR': ('Beyond the Barracks', 'За стенами казарм'),
        'JFT': ('A Meeting by the Quays', 'Собрание у причалов'),
        'VIN': ('Letters from the Districts', 'Письма из округов'),
    }
    descriptions = {
        'JEB': {
            'royal': (
                "Michel's captains have brought their reports to the palace. A town delegate lays a bundle of requisition receipts beside them and waits while the last account of the royal victory is read. The duke asks his secretary to open the bundle.\n\nThe first receipt bears a signature nobody at the table recognises. The captain responsible promises an inquiry; the delegate asks where her neighbours should take the others.\n\nMichel keeps the papers before him. Rila has held for the crown. Its government must now give the people who endured the fighting a reason to trust the peace.",
                'Капитаны Мишеля принесли во дворец донесения. Представительница города кладёт рядом пачку расписок о реквизициях и ждёт, пока дочитают последний отчёт о победе роялистов. Герцог просит секретаря развязать пачку.\n\nНа первой расписке стоит подпись, которой никто за столом не узнаёт. Ответственный капитан обещает разобраться; делегатка спрашивает, куда её соседям нести остальные бумаги.\n\nМишель оставляет расписки перед собой. Рила удержалась на стороне короны. Теперь её правительству предстоит дать пережившим бои жителям основания доверять наступившему миру.'),
            'rev': (
                "The clubs meet in a hall whose windows still bear strips of paper from the fighting. Their messengers bring petitions from streets that helped the revolution, asking when the promises on the walls will reach their homes.\n\nA delegate raises the name of the exiled Michel. The room grows quiet. Any reconciliation with the duke would require an invitation and terms acceptable to the assembly; nobody has yet brought him back.\n\nThe chair calls the speakers to order. Rila's revolutionaries must agree what they will ask of a government before carrying their arguments into Aquileia's wider debate.",
                'Клубы собираются в зале, где на окнах ещё остались бумажные полосы времён боёв. Посыльные приносят прошения с улиц, поддержавших революцию: жители спрашивают, когда обещания со стен дойдут до их домов.\n\nОдин из делегатов произносит имя изгнанного Мишеля. В зале становится тихо. Примирение с герцогом потребует приглашения и условий, приемлемых для собрания; пока никто не вернул его в Рилу.\n\nПредседатель призывает выступающих к порядку. Прежде чем участвовать в общем споре о будущем Аквелии, рильским революционерам предстоит договориться о том, чего они потребуют от правительства.'),
        },
        'JRR': {
            'royal': (
                "Bassot's officers have kept the commandant's office since the loyalist countercoup. Today Jeanne's envoys arrive carrying petitions which have passed through the garrison twice without an answer. An officer reaches for the familiar military stamp. They ask him to wait.\n\nThe marquise wants a civilian administration able to receive such complaints in its own name. Bassot still holds command, and her supporters must negotiate the authority she would exercise.\n\nTwo copies of the proposed terms are laid on the desk, one for the commander and one for Jeanne. The signatures must wait until their obligations are settled.",
                'После контрпереворота лоялистов комендатура остаётся в руках офицеров Бассо. Сегодня посланники Жанны принесли прошения, уже дважды прошедшие через гарнизон без ответа. Офицер тянется за привычной военной печатью. Его просят подождать.\n\nМаркиза хочет создать гражданскую администрацию, способную принимать такие жалобы от собственного имени. Командование по-прежнему принадлежит Бассо, и её сторонникам предстоит договориться о полномочиях, которые она получит.\n\nНа стол кладут два экземпляра предложенных условий: один командующему, другой Жанне. Прежде чем ставить подписи, обеим сторонам придётся определить свои обязательства.'),
            'rev': (
                "A civilian organiser arrives at Colette's headquarters with a list of missing flour deliveries. The sentry knows her from the rising, but the clerk sends her to an officer who has already left for the railway yard. She sits down and refuses to leave.\n\nColette finds her still waiting when the morning reports are finished. The army has held its command through victory; its civilian allies now want someone who can answer for the work of peace.\n\nThe colonel tells her adjutant to find chairs for the delegates. Their proposals must give the towns a voice the headquarters will hear.",
                'Гражданская организаторка приходит в штаб Колетт со списком недоставленных грузов муки. Часовой помнит её по восстанию, но писарь направляет к офицеру, уже уехавшему на станцию. Она садится и отказывается уходить.\n\nЗакончив утренние доклады, Колетт застаёт её всё ещё в ожидании. Армия сохранила командование после победы; теперь её гражданские союзники хотят знать, кто будет отвечать за мирную работу.\n\nПолковница велит адъютанту найти стулья для делегатов. Их предложения должны дать городам голос, который услышат в штабе.'),
        },
        'JFT': {
            'royal': (
                "The royal banner hangs above Pridea's harbour, but the dockyard foremen have come to Dennis with unfinished repairs and crews asking when they can go home. His veterans make room around a table still covered by a naval chart.\n\nAn old marine begins with the defence of the quays. A foreman answers with the names of families living beside them. Dennis rolls back the chart so the petition can lie flat.\n\nThe admiral has kept his harbour. The men and women who work it need terms they can live under when the patrols have passed. His supporters must decide what promises to carry into those talks.",
                'Над гаванью Придеи развевается королевское знамя, но мастера верфей пришли к Деннису с перечнем незаконченных ремонтов и вопросами экипажей о возвращении домой. Ветераны освобождают места вокруг стола, ещё покрытого морской картой.\n\nСтарый морской пехотинец начинает с обороны причалов. Мастер отвечает именами семей, живущих рядом. Деннис сворачивает край карты, чтобы расправить прошение.\n\nАдмирал удержал гавань. Тем, кто в ней работает, нужны условия мирной жизни после ухода патрулей. Его сторонникам предстоит решить, с какими обещаниями они начнут переговоры.'),
            'rev': (
                "The harbour meeting begins before the night shift has gone home. Delegates from the organisations that carried the rising arrive with folded petitions and messages passed between workshops during the fighting. The doors remain open for the latecomers.\n\nA sailor asks who will speak for the crews. A dockworker wants the same answer for those on shore. The organisers have won a hearing, but their wartime promises leave plenty to argue over.\n\nSomeone clears a space for the first draft. Pridea's contribution to the new Aquileia will begin here, with a programme its supporters are prepared to defend together.",
                'Собрание у гавани начинается прежде, чем ночная смена успевает разойтись по домам. Представители организаций, поднявших восстание, приносят сложенные прошения и записки, которыми мастерские обменивались во время боёв. Двери оставляют открытыми для опоздавших.\n\nМоряк спрашивает, кто будет говорить от имени экипажей. Рабочий с причала задаёт тот же вопрос о людях на берегу. Организаторы добились права быть услышанными, но обещания военных дней оставили немало поводов для спора.\n\nНа столе освобождают место для первого проекта. Вклад Придеи в новую Аквелию начнётся здесь — с программы, которую её сторонники готовы защищать сообща.'),
        },
        'VIN': {
            'royal': (
                "Gadiffer's secretary brings in the letters which waited while the roads were unsafe. The duke recognises the seal on the first: a district whose volunteers marched under his colours. Its council is asking for the return of borrowed carts.\n\nAn adviser begins to explain how much the victory has cost. Gadiffer asks him to read the rest of the letter. The carts are needed for a harvest that will not wait for the treasury.\n\nAround the table, the duke's supporters turn from congratulations to proposals. Serving the Discret crown now means finding obligations that Vinovia and its ruler can both honour.",
                'Секретарь Гадиффера приносит письма, задержавшиеся, пока дороги были небезопасны. Герцог узнаёт первую печать: добровольцы этого округа выступили под его знамёнами. Местный совет просит вернуть одолженные подводы.\n\nСоветник начинает объяснять, во сколько обошлась победа. Гадиффер просит дочитать письмо. Подводы нужны для урожая, который не станет ждать казначейство.\n\nЗа столом сторонники герцога переходят от поздравлений к предложениям. Служить короне Дискре теперь означает определить обязательства, которые смогут исполнить и Виновия, и её правитель.'),
            'rev': (
                "The delegates have propped their society banners against the wall to make room for letters from the districts. A village teacher has come to hear her own letter read; the courier could not tell her which office would answer it.\n\nThe movements that sustained the revolution now face neighbours who expect them to govern. One speaker asks for a common declaration. Another unfolds a petition whose signatories want to know who can be called to account when a promise is broken.\n\nThe teacher waits while they amend the opening paragraph. Before Vinovia offers Aquileia a programme, its advocates must be able to answer her.",
                'Делегаты прислонили знамёна своих обществ к стене, освобождая место для писем из округов. Сельская учительница приехала послушать, как прочтут её письмо: курьер не смог сказать, какое учреждение на него ответит.\n\nПеред движениями, поддержавшими революцию, теперь стоят соседи, ожидающие от них умения управлять. Один оратор предлагает общую декларацию. Другой разворачивает прошение: подписавшиеся хотят знать, кого можно призвать к ответу за нарушенное обещание.\n\nУчительница ждёт, пока в первый абзац вносят поправки. Прежде чем предложить Аквелии свою программу, её сторонникам в Виновии предстоит ответить этой женщине.'),
        },
    }
    fallback = (
        "The delegates arrive with petitions, but no common programme to put before the meeting. The people who carried messages during the fighting are still being asked to settle disputes they have no authority to decide.\n\nA clerk leaves the heading of the agreement blank. Each group can explain what it wanted to end; agreement on what should follow proves harder. The chair asks them to begin with the complaints waiting outside.\n\nThey must find partners willing to share responsibility for the peace. Any approach to an old opponent will need terms their own supporters can accept.",
        'Делегаты приносят прошения, но общей программы для собрания у них нет. Людей, передававших сообщения во время боёв, всё ещё просят разрешать споры, на которые у них нет полномочий.\n\nПисарь оставляет заголовок соглашения пустым. Каждая группа может объяснить, с чем хотела покончить; договориться о будущем оказывается труднее. Председатель предлагает начать с жалоб тех, кто ждёт за дверью.\n\nИм предстоит найти партнёров, готовых разделить ответственность за мирную жизнь. Для переговоров с прежним противником потребуются условия, приемлемые для собственных сторонников.')
    marais_text = (
        "The Marais delegates take their seats together, with several smaller clubs gathered around them. When another speaker begins to count their support among his own, their spokeswoman asks him to read the agreement they have supposedly signed. There is none.\n\nShe lays their proposals on the table. The committee will need their consent, and they intend to bargain over the promises made in its name. Other delegates pull their chairs closer.\n\nMichel's name is raised among the possible approaches. Reconciliation with the exiled duke would still require an invitation and agreed conditions. For now, the clubs must decide with whom they can negotiate a common programme.",
        'Делегаты Марэ занимают места вместе; вокруг собираются представители нескольких небольших клубов. Когда очередной оратор начинает причислять их голоса к своим, представительница Марэ просит прочесть соглашение, которое они якобы подписали. Такого соглашения нет.\n\nОна кладёт на стол их предложения. Комитету понадобится их согласие, и они намерены обсуждать обещания, даваемые от его имени. Остальные делегаты подвигают стулья ближе.\n\nСреди возможных шагов звучит и имя Мишеля. Примирение с изгнанным герцогом всё ещё потребует приглашения и согласованных условий. Пока клубам предстоит решить, с кем они смогут договориться об общей программе.')

    decisions = []
    for index, tag in enumerate(TAGS):
        number = 410 + index
        scene_keys = {camp: L(f'HSM_AQR.{number}.{camp}', *descriptions[tag][camp])
                      for camp in ('royal', 'rev')}
        fallback_text = fallback
        if tag == 'JRR':
            fallback_text = (
                "Jeanne's supporters reach Bassot's office carrying different drafts. The loyalist countercoup has secured the march, but nobody can produce an agreement on the civilian authority that should follow. The commander's secretary sets out another chair.\n\nAn old court ally asks who will answer to the marquise. A town delegate asks who will answer to the towns. Both have brought grievances against the military offices through which their petitions still pass.\n\nBassot retains command while they argue. Before Jeanne can return to government, her supporters must agree what powers they will seek for her and what obligations they will accept themselves.",
                'Сторонники Жанны приходят в кабинет Бассо с разными проектами. Контрпереворот лоялистов обеспечил контроль над маркой, но никто не может предъявить соглашение о будущей гражданской власти. Секретарь командующего ставит ещё один стул.\n\nСтарый союзник двора спрашивает, кто будет отвечать перед маркизой. Представитель города спрашивает, кто будет отвечать перед горожанами. Оба принесли жалобы на военные учреждения, через которые по-прежнему проходят их прошения.\n\nПока они спорят, командование остаётся у Бассо. Прежде чем Жанна вернётся к управлению, её сторонникам предстоит договориться о полномочиях, которых они будут для неё добиваться, и об обязательствах, которые примут на себя.')
        fallback_key = L(f'HSM_AQR.{number}.unprepared', *fallback_text)
        camp = 'royal' if tag == 'JRR' else 'rev'
        missing = f'{P}native_won_{camp} = yes {P}native_unprepared_{tag} = yes'
        desc = f'desc = {{ trigger = {{ {missing} }} text = {fallback_key} }}\n'
        exclusions = f'NOT = {{ AND = {{ {missing} }} }}'
        if tag == 'JEB':
            marais_key = L(f'HSM_AQR.{number}.marais', *marais_text)
            condition = f'{P}native_won_rev = yes {P}native_marais_coalition = yes'
            desc += f'desc = {{ trigger = {{ {condition} }} text = {marais_key} }}\n'
            exclusions += f' NOT = {{ AND = {{ {condition} }} }}'
        for scene_camp in ('royal', 'rev'):
            desc += (f'desc = {{ trigger = {{ {P}native_won_{scene_camp} = yes '
                     f'{exclusions} }} text = {scene_keys[scene_camp]} }}\n')
        opts = ''
        for rid, *_ in config:
            if rid[:3] != tag:
                continue
            title = route_data[rid]['title']
            if rid == 'JEB_constitutional':
                title = ('Authorise reconciliation with Michel under a charter.',
                         'Разрешить переговоры о примирении с Мишелем на основе хартии.')
            elif rid == 'JRR_absolutist':
                title = ("Negotiate Jeanne's return with the royalist assembly.",
                         'Обсудить возвращение Жанны с собранием роялистов.')
            elif rid == 'JRR_coalition':
                title = ("Negotiate Jeanne's return through a coalition.",
                         'Обсудить возвращение Жанны на основе коалиции.')
            elif rid == 'JRR_colette':
                title = ("Negotiate the civil obligations of Colette's command.",
                         'Определить гражданские обязательства командования Колетт.')
            opts += option(f'HSM_AQR.{number}.{rid}', title,
                           f'custom_effect_tooltip = {P}native_selection_tt '
                           f'hidden_effect = {{ {P}native_select_{rid} = yes }}',
                           f'{P}native_candidate_{rid} = yes NOT = {{ {P}native_choice_valid = yes }}', ai=5)
        opts += option(f'HSM_AQR.{number}.later',
                       ('Continue these talks later.', 'Продолжить переговоры позднее.'),
                       f'clr_country_flag = {P}native_settlement_pending', ai=1)
        event(number, titles[tag], desc, opts,
              trigger=(f'original_tag = {tag} {P}native_settlement_ready = yes '
                       f'NOT = {{ has_country_flag = {P}native_settlement_presented }}'),
              immediate=immediate)
        name = P + 'native_settlement_retry_' + tag
        L(name, 'Reconvene the Provincial Settlement', 'Возобновить переговоры об устройстве провинции')
        L(name + '_desc',
          'The delegates can return to the unfinished discussion. Their original preparations remain the basis of the talks; later committee manoeuvres do not rewrite that record.',
          'Делегаты могут вернуться к незавершённому обсуждению. Основой переговоров останется первоначальная подготовка; позднейшие манёвры в комитетах не изменят её итогов.')
        req = tt('native_settlement_retry_' + tag,
                 'The native outcome is recorded, peace has returned and the postwar opening is complete. An available programme can be discussed; no settlement is already ratified, selected or awaiting an answer.',
                 'Исход борьбы зафиксирован, наступил мир, послевоенное вступление завершено. Есть доступная программа для обсуждения; устройство власти ещё не утверждено и не выбрано, другое обсуждение не ожидает ответа.',
                 f'{P}native_can_reopen = yes')
        decisions.append(f'''{name} = {{
 icon = generic_political_discourse
 visible = {{ original_tag = {tag} has_country_flag = {P}native_outcome_recorded
  OR = {{ has_country_flag = {P}native_settlement_presented has_country_flag = {P}native_settlement_requested }}
  NOT = {{ has_country_flag = {P}ratified }} NOT = {{ {P}native_choice_valid = yes }} }}
 available = {{ {req} }}
 cost = 0
 days_re_enable = 7
 complete_effect = {{ if = {{ limit = {{ {P}native_can_reopen = yes }}
  clr_country_flag = {P}native_settlement_presented
  clr_country_flag = {P}native_settlement_requested {P}queue_native_settlement = yes }} }}
 ai_will_do = {{ factor = 10 }}
}}''')
    return decisions
