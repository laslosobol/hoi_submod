"""AQR reconstruction and bounded, consensual peripheral accession.

build_reconstruction(L, trig, effect, once, tt, focus, event, option) -> str
uses the main builder's callbacks (which prepend HSM_AQR_ where appropriate)
and returns a complete ideas = { country = { ... } } document.
build_reconstruction_decisions(tt, L) -> list[str] returns decision blocks for
the caller's HSM_AQR_affairs category. Call both builders before writing loc.

Integration: import ROOT_ID into both the regional tree and all native JER
trees, including the initial aquileian_focus. It has no graph prerequisites.
HSM_AQR_REC_reconstruction_active permits independent, peaceful regional
Aquileia or native JER after the revolution has ended and either native opening
focus is complete. Later post-Herzland triumphs are deliberately not required.
Both must exist, remain uncapitulated and own/control Aquileia (377).
Call HSM_AQR_begin_reconstruction after regional proclamation, and from the
eligible JER daily tick. Its once flag prevents reapplying the crisis.
Call HSM_AQR_REC_integrate_owned from the four regional and native JER ticks
or post-peace maintenance so the completed articles cover later conquests too.
That effect is idempotent, peace-only and never transfers territory. Accession
itself invokes it immediately. No existing common focuses or route identities
are replaced. Event numbers 500..504 belong to this helper.

Offers are sent at the conference to eligible POM/FLO/AET/FEZ/HEL only. A free,
30-day recall decision reaches eligible countries not previously approached or
whose unanswered invitation has expired.
War, foreign subjects/factions, subjects of a prospective member, and disputed
control exclude a recipient. Both sender and recipient offer markers expire
after 60 days. Recalls never duplicate a live invitation or erase an explicit,
permanent refusal, and there are no automatic retries.
Acceptance is an explicit game-ending annexation, never a faction-only reward.
Refusal is the first, free option; only a subsequent guarded choice grants a
war goal. No event declares war. Cores are confined to original peripheral
territory actually owned and fully controlled by the national government.

The chain uses x32, local y20..24 (rendered y25..29 with the main builder's +5
offset). Native JER reaches y18 and its conditional offsets are horizontal;
regional authored content is x0..27, and the retained generic tree starts x40.
Imports do no I/O. Running this module performs in-memory syntax/contract checks.
"""
from __future__ import annotations

P = "HSM_AQR_"
R = P + "REC_"
PERIPHERY = ("POM", "FLO", "AET", "FEZ", "HEL")
FOUNDERS = ("JEB", "JRR", "JFT", "VIN", "JER")
ROOT_ID = R + "postwar_housing"
OFFER_DAYS = 60
# Native opening focuses, not the much later post-Herzland victory roots.
NATIVE_ENTRY_FOCUSES = ("JER_state_of_aquileia", "JER_fight_for_freedom")


def build_reconstruction(L, trig, effect, once, tt, focus, event, option) -> str:
    """Append all script/localization definitions; return three crisis ideas."""
    trig("REC_native_postwar", "original_tag = JER\n"
         "OR = { has_global_flag = JER_revolution_ended has_global_flag = JER_revolution_ended_2 }\n"
         "OR = { " + " ".join("has_completed_focus = " + fid for fid in NATIVE_ENTRY_FOCUSES) + " }")
    trig("REC_reconstruction_active", """exists = yes has_capitulated = no
is_subject = no has_war = no
377 = { is_owned_and_controlled_by = PREV }
OR = { HSM_AQR_national = yes HSM_AQR_REC_native_postwar = yes }
""")
    trig("REC_national_peace", "HSM_AQR_REC_reconstruction_active = yes")
    trig("REC_start_ready", """HSM_AQR_REC_reconstruction_active = yes
OR = {
 AND = { HSM_AQR_national = yes has_completed_focus = HSM_AQR_national_services }
 HSM_AQR_REC_native_postwar = yes
}
""")
    # Evaluate each state against the country whose trigger is running. ROOT
    # remains the recipient when this is checked inside an invitation's FROM.
    trig("REC_united", "\n".join(
         f"all_of_scopes = {{ array = {tag}.original_cores is_owned_and_controlled_by = PREV }}"
         for tag in ("JER", "JEB", "JRR", "JFT", "VIN")))
    trig("REC_conference_ready", """HSM_AQR_REC_reconstruction_active = yes
HSM_AQR_REC_united = yes has_country_flag = HSM_AQR_REC_food_networks_done
OR = {
 AND = { HSM_AQR_national = yes has_completed_focus = HSM_AQR_national_settlement }
 HSM_AQR_REC_native_postwar = yes
}
""")
    trig("REC_host", "HSM_AQR_REC_national_peace = yes HSM_AQR_REC_united = yes\n"
         "has_country_flag = HSM_AQR_REC_peripheral_conference_done\nOR = { "
         + " ".join("tag = " + tag for tag in FOUNDERS) + " }")
    trig("REC_periphery", "OR = { " + " ".join("tag = " + tag for tag in PERIPHERY) + " }")
    trig("REC_periphery_state", "OR = { " + " ".join(
        f"is_in_array = {{ state_original_cores = {tag} }}" for tag in PERIPHERY) + " }")
    # PREV within each state loop is the actual country being checked, even when
    # ROOT belongs to the other government in an event or a nested country scope.
    trig("REC_recipient_base", """HSM_AQR_REC_periphery = yes
exists = yes has_capitulated = no has_war = no
NOT = { any_subject_country = { always = yes } }
any_owned_state = { always = yes }
all_owned_state = { is_fully_controlled_by = PREV }
all_controlled_state = { is_owned_by = PREV }
""")

    ideas = []
    for suffix, title, desc, output, construction, stability in (
        ("crisis", ("The Peace Has No Roof", "Миру негде жить"),
         ("The proclamation has reached towns whose roofs, ration lists and workplaces were destroyed long before the delegates arrived. Victory has placed their repair on one government's desk.",
          "Прокламацию прочли в городах, где крыши, продовольственные ведомости и мастерские были уничтожены задолго до приезда делегатов. Победа возложила их восстановление на одно правительство."), -.10, -.10, -.05),
        ("roofs", ("Shelter before Winter", "Кров до наступления зимы"),
         ("Families have somewhere to sleep again. Workshops still lack their workers, and too many soldiers wait for orders which will never come.",
          "У семей снова есть место для ночлега. Мастерским по-прежнему не хватает работников, а слишком многие солдаты ждут приказов, которые уже не придут."), -.10, -.05, -.03),
        ("returning_workers", ("Workers without Deliveries", "Работники без поставок"),
         ("Demobilisation has brought hands back to the workshops. Their first wages will mean little until food can reach the towns regularly.",
          "Демобилизация вернула работников в мастерские. Их первая зарплата мало что изменит, пока продовольствие не начнёт регулярно поступать в города."), -.05, 0, -.02),
    ):
        L(R + suffix, *title)
        L(R + suffix + "_desc", *desc)
        ideas.append(f"""{R}{suffix} = {{
allowed = {{ always = no }}
picture = generic_production_bonus
removal_cost = -1
modifier = {{ industrial_capacity_factory = {output:g}
production_speed_buildings_factor = {construction:g} stability_factor = {stability:g} }}
}}""")

    once("REC_begin", "HSM_AQR_REC_national_peace = yes",
         "add_ideas = HSM_AQR_REC_crisis\ncountry_event = { id = HSM_AQR.500 days = 1 }")
    # The only non-REC public identifier is the proclamation hook requested by main.
    effect("begin_reconstruction", "HSM_AQR_REC_begin = yes")
    event(500, ("The First Peace-Time Ledger", "Первая мирная ведомость"),
          ("The victory proclamations are still hanging outside the ministry. Inside, the first common register lists families in railway sheds, soldiers awaiting discharge and towns buying bread from army depots. The government has survived the struggle; now it must make the country habitable. The clerks have left three folders on the table: shelter, the return from service, and food deliveries.",
           "У министерства ещё висят победные прокламации. Внутри первая общая ведомость перечисляет семьи в железнодорожных сараях, солдат, ожидающих увольнения, и города, покупающие хлеб на армейских складах. Правительство пережило борьбу; теперь ему предстоит сделать страну пригодной для жизни. Писари оставили на столе три папки: жильё, возвращение со службы и поставки продовольствия."),
          option("HSM_AQR.500.a", ("Put the households first.", "Начнём с домов и семей.")),
          trigger="HSM_AQR_REC_reconstruction_active = yes has_idea = HSM_AQR_REC_crisis")

    stages = (
        ("postwar_housing", ("A Roof for the Returning", "Крыша для возвращающихся"),
         ("Municipal surveyors will distinguish ruined houses from abandoned claims. Timber and brick will go first to buildings which can shelter families before winter. The register will record who received help and who is still waiting.",
          "Муниципальные землемеры отделят разрушенные дома от бесхозных участков. Дерево и кирпич прежде всего направят туда, где семьи смогут укрыться до зимы. В реестре отметят тех, кто получил помощь, и тех, кто ещё ждёт."),
         None, "crisis", "roofs", 75, 20, 6,
         "377 = { add_extra_state_shared_building_slots = 2 }",
         "GFX_goal_generic_construct_civ_factory"),
        ("demobilisation", ("Service Papers and Workshop Keys", "Военные билеты и ключи от мастерских"),
         ("Discharge orders must arrive with recognised service records and a place to report for civilian work. The army will keep its trained reserve; towns will receive their craftspeople without waiting for each colonel to release them at his convenience.",
          "Приказы об увольнении должны сопровождаться признанными послужными списками и адресом для возвращения к гражданской работе. Армия сохранит подготовленный резерв; города получат своих мастеров, не ожидая удобного для каждого полковника срока."),
         "REC_postwar_housing", "roofs", "returning_workers", 50, 21, 5,
         "army_experience = 15", "GFX_goal_generic_army_doctrines"),
        ("food_networks", ("Bread on a Timetable", "Хлеб по расписанию"),
         ("The harvest must travel by contracts which survive the next requisition order. Market towns, mills and railway offices will agree delivery days and storage responsibilities. Empty wagons should no longer leave a full granary while the next district queues for bread.",
          "Урожай должен перевозиться по договорам, которые переживут очередной приказ о реквизиции. Торговые города, мельницы и железнодорожные конторы согласуют дни поставок и обязанности по хранению. Пустые вагоны больше не должны покидать полные амбары, пока соседний округ стоит в очереди за хлебом."),
         "REC_demobilisation", "returning_workers", None, 50, 22, 6,
         "add_stability = 0.05\ncountry_event = { id = HSM_AQR.504 days = 1 }",
         "GFX_goal_generic_construct_infrastructure"),
    )
    for name, title, desc, parent, previous, following, price, y, cost, bonus, icon in stages:
        prerequisite = (f"has_completed_focus = {P}{parent}" if parent
                        else "HSM_AQR_REC_start_ready = yes")
        gate = (f"HSM_AQR_REC_national_peace = yes {prerequisite}\n"
                f"has_idea = {R}{previous} NOT = {{ has_political_power < {price} }}")
        trig("REC_can_" + name, gate)
        change = (f"swap_ideas = {{ remove_idea = {R}{previous} add_idea = {R}{following} }}"
                  if following else f"remove_ideas = {R}{previous}")
        body = f"add_political_power = -{price}\n{change}\n{bonus}"
        once("REC_" + name, "HSM_AQR_REC_can_" + name + " = yes", body)
        req_en = ("The provincial claimant has established a national civil service, or Aquileia has completed its opening political course and the revolution has ended. "
                  if parent is None else "The previous reconstruction stage is complete. ")
        req_ru = ("Областной претендент создал общую гражданскую службу, либо Аквелия завершила начальный политический курс и революция окончилась. "
                  if parent is None else "Предыдущий этап восстановления завершён. ")
        req = tt("REC_" + name + "_req",
                 req_en + f"Independent Aquileia controls its capital and is at peace. The reconstruction crisis is active; reserve {price} political power.",
                 req_ru + f"Независимая Аквелия контролирует столицу и находится в мире. Кризис восстановления продолжается; требуется {price} политической власти.",
                 f"HSM_AQR_REC_can_{name} = yes")
        focus("REC_" + name, title, desc, 32, y, (parent,) if parent else (), req,
              f"effect_tooltip = {{ {body} }} hidden_effect = {{ {R}{name} = yes }}",
              cost=cost, icon=icon)

    event(504, ("The Ordinary Morning", "Обычное утро"),
          ("The ministry's latest dispatch contains no victory speech. It reports that the morning bread train arrived, the discharge office closed its last temporary barracks, and a repaired street has received its residents. The country still has poor districts and schools to build. Those obligations remain with the institutions created by the founding settlement; the immediate emergency no longer prevents them from working.",
           "В последней министерской сводке нет победной речи. Утренний поезд с хлебом прибыл, отдел демобилизации закрыл последнюю временную казарму, а отремонтированная улица приняла жильцов. В стране ещё остаются бедные округа и школы, которые предстоит построить. Эти обязанности сохраняются за учреждениями, созданными основополагающим соглашением; теперь чрезвычайное положение не мешает им работать."),
          option("HSM_AQR.504.a", ("Let this become ordinary.", "Пусть это станет обыденностью.")),
          trigger="HSM_AQR_REC_reconstruction_active = yes has_country_flag = HSM_AQR_REC_food_networks_done")

    # An offer is tied to both actual tags. No global event target can be replaced
    # by another claimant; acceptance requires live matching offer markers.
    sender_match = "OR = { " + " ".join(
        f"AND = {{ FROM = {{ tag = {tag} }} has_country_flag = {R}offer_{tag} "
        f"NOT = {{ has_country_flag = {R}refused_{tag} }} }}" for tag in FOUNDERS) + " }"
    dispatch_match = "OR = { " + " ".join(
        f"AND = {{ tag = {tag} FROM = {{ has_country_flag = {R}sent_{tag} }} }}"
        for tag in PERIPHERY) + " }"
    trig("REC_valid_offer", f"""HSM_AQR_REC_recipient_base = yes
OR = {{ is_subject = no is_subject_of = FROM }}
OR = {{ is_in_faction = no is_in_faction_with = FROM }}
FROM = {{ HSM_AQR_REC_host = yes NOT = {{ tag = ROOT }} }}
{sender_match}
{dispatch_match}
""")
    send = []
    bind_sender = "\n".join(
        f"if = {{ limit = {{ PREV = {{ tag = {tag} }} }} "
        f"set_country_flag = {{ flag = {R}offer_{tag} days = {OFFER_DAYS} }} }}" for tag in FOUNDERS)
    for tag in PERIPHERY:
        refused = "OR = { " + " ".join(
            f"AND = {{ PREV = {{ tag = {founder} }} has_country_flag = {R}refused_{founder} }}"
            for founder in FOUNDERS) + " }"
        # One predicate serves decision availability and execution. Temporarily
        # ineligible countries are not marked sent and remain eligible for recall.
        trig("REC_can_invite_" + tag, f"""HSM_AQR_REC_host = yes
NOT = {{ has_country_flag = {R}sent_{tag} }}
{tag} = {{ HSM_AQR_REC_recipient_base = yes
OR = {{ is_subject = no is_subject_of = PREV }}
OR = {{ is_in_faction = no is_in_faction_with = PREV }}
NOT = {{ {refused} }} }}
""")
        send.append(f"""if = {{ limit = {{ {R}can_invite_{tag} = yes }}
set_country_flag = {{ flag = {R}sent_{tag} days = {OFFER_DAYS} }}
{tag} = {{ {bind_sender} country_event = {{ id = HSM_AQR.501 days = 1 }} }}
}}""")
    trig("REC_can_recall", "OR = { " + " ".join(
         f"{R}can_invite_{tag} = yes" for tag in PERIPHERY) + " }")
    effect("REC_send_invitations", "if = { limit = { HSM_AQR_REC_host = yes }\n"
           + "\n".join(send) + "\n}")
    once("REC_peripheral_conference", "HSM_AQR_REC_conference_ready = yes",
         "HSM_AQR_REC_send_invitations = yes")
    L(R + "conference_tt",
      "Invite eligible Pomovarra, Flowena, Greifwald, Fezera and the Northern Tribes to join one country. Each government can refuse freely. Countries at war, foreign subjects or faction partners, rulers with subjects, and countries with disputed territorial control receive no offer. Invitations expire after 60 days.",
      "Пригласить Помоварру, Фловену, Грайфвальд, Фезеру и Северные племена войти в единое государство. Каждое правительство вправе свободно отказаться. Приглашения не направляются воюющим странам, чужим субъектам и участникам чужих альянсов, правительствам с собственными субъектами и странам со спорным контролем территорий. Срок предложения — 60 дней.")
    focus("REC_peripheral_conference", ("Seats beyond the Old Provinces", "Места для окраин"),
          ("The neighbours have watched the new government restore its own towns. They are entitled to ask whether the founding articles would protect theirs. The conference will set out the courts and local institutions which accession preserves, and the national authority which a signature would recognise. An empty chair will not be counted as consent.",
           "Соседи наблюдали, как новое правительство восстанавливает собственные города. Они вправе спросить, защитят ли основополагающие статьи и их города. Конференция определит суды и местные учреждения, сохраняемые при присоединении, и общегосударственную власть, которую признает подпись. Пустое кресло не будет считаться согласием."),
          32, 23, ("REC_food_networks",),
          tt("REC_conference_req",
             "Independent Aquileia is at peace and owns and fully controls its original heartland and the four provinces. Emergency reconstruction is complete. A provincial claimant must also complete its national settlement; native Aquileia must have completed its opening political course and ended the revolution.",
             "Независимая Аквелия находится в мире, владеет своим первоначальным ядром и четырьмя провинциями и полностью контролирует их. Чрезвычайное восстановление завершено. Областной претендент должен также завершить государственное устройство; сама Аквелия — начальный политический курс и революцию.",
             "HSM_AQR_REC_conference_ready = yes"),
          f"custom_effect_tooltip = {R}conference_tt hidden_effect = {{ {R}peripheral_conference = yes }}",
          cost=5, icon="GFX_goal_generic_improve_relations")

    reject = "\n".join(
        f"if = {{ limit = {{ FROM = {{ tag = {tag} }} }} "
        f"clr_country_flag = {R}offer_{tag} set_country_flag = {R}refused_{tag} }}"
        for tag in FOUNDERS)
    effect("REC_refuse_offer", "if = { limit = { HSM_AQR_REC_valid_offer = yes }\n"
           + reject + "\nFROM = { country_event = { id = HSM_AQR.503 days = 1 } }\n}")
    clear_offer = "\n".join(f"clr_country_flag = {R}offer_{tag}" for tag in FOUNDERS)
    effect("REC_accept_offer", f"""if = {{ limit = {{ HSM_AQR_REC_valid_offer = yes }}
{clear_offer}
FROM = {{
 country_event = {{ id = HSM_AQR.502 days = 1 }}
 annex_country = {{ target = ROOT transfer_troops = yes }}
 HSM_AQR_REC_integrate_owned = yes
}}
}}""")
    L(R + "accession_tt",
      "Transfer our owned territory and armed forces to the inviting Aquileian government. Our separate country and playable campaign end. Acceptance is valid only while both governments meet the invitation's terms; third-party subjects and foreign occupation are excluded.",
      "Передать принадлежащие нам территории и вооружённые силы приглашающему аквелийскому правительству. Наша отдельная страна и игровая кампания прекратятся. Согласие действует лишь при сохранении условий приглашения обоими правительствами; чужие субъекты и иностранная оккупация исключены.")
    event(501, ("Articles from Aquileia", "Статьи из Аквелии"),
          ("[From.GetName] has sent its delegates with a proposal for accession. Municipal courts and local offices would continue their work under the founding articles, while the treasury, foreign policy and armed forces would become national institutions. This would end our separate government. The delegates have brought two copies of the agreement, but no signature has been entered on our behalf.",
           "[From.GetName] направляет делегацию с предложением о присоединении. Муниципальные суды и местные учреждения продолжат работу в соответствии с основополагающими статьями, а казна, внешняя политика и вооружённые силы станут общегосударственными. Наше отдельное правительство прекратит существование. Делегаты привезли два экземпляра договора, но от нашего имени ещё никто не подписался."),
          option("HSM_AQR.501.a", ("We will retain our separate government.", "Мы сохраним отдельное правительство."),
                 "hidden_effect = { HSM_AQR_REC_refuse_offer = yes }", ai=8)
          + option("HSM_AQR.501.b", ("Sign the articles of accession.", "Подписать статьи о присоединении."),
                   f"custom_effect_tooltip = GAME_OVER_TT custom_effect_tooltip = {R}accession_tt "
                   "hidden_effect = { HSM_AQR_REC_accept_offer = yes }",
                   "HSM_AQR_REC_valid_offer = yes", ai=2),
          trigger="HSM_AQR_REC_valid_offer = yes")
    event(502, ("Two Copies, Two Seals", "Два экземпляра, две печати"),
          ("The delegates have returned with the signed articles. The provincial offices will keep a copy beside the founding settlement so that neither a minister nor a local magistrate can quietly rewrite the guarantees. The territorial register must now follow the agreement.",
           "Делегаты вернулись с подписанными статьями. В областных учреждениях экземпляр положат рядом с основополагающим соглашением, чтобы ни министр, ни местный судья не мог незаметно переписать гарантии. Теперь территориальные реестры должны последовать за договором."),
          option("HSM_AQR.502.a", ("Publish both copies.", "Опубликовать оба экземпляра.")),
          trigger="HSM_AQR_REC_reconstruction_active = yes")

    refusal_match = "OR = { " + " ".join(
        f"AND = {{ tag = {tag} FROM = {{ has_country_flag = {R}refused_{tag} }} }}"
        for tag in FOUNDERS) + " }"
    unsanctioned = "OR = { " + " ".join(
        f"AND = {{ FROM = {{ tag = {tag} }} NOT = {{ has_country_flag = {R}goal_{tag} }} }}"
        for tag in PERIPHERY) + " }"
    trig("REC_known_refusal", "HSM_AQR_REC_reconstruction_active = yes\n"
         "FROM = { exists = yes HSM_AQR_REC_periphery = yes }\n" + refusal_match)
    trig("REC_can_coerce", f"""HSM_AQR_REC_host = yes HSM_AQR_REC_known_refusal = yes
FROM = {{ exists = yes has_capitulated = no is_subject = no has_war = no
NOT = {{ is_guaranteed_by = ROOT }} }}
NOT = {{ is_in_faction_with = FROM }}
NOT = {{ has_non_aggression_pact_with = FROM }}
NOT = {{ has_truce_with = FROM }}
{unsanctioned}
""")
    mark_goal = "\n".join(
        f"if = {{ limit = {{ FROM = {{ tag = {tag} }} }} set_country_flag = {R}goal_{tag} }}"
        for tag in PERIPHERY)
    effect("REC_authorise_claim", "if = { limit = { HSM_AQR_REC_can_coerce = yes }\n"
           + mark_goal + "\ncreate_wargoal = { type = annex_everything target = FROM }\n}")
    L(R + "claim_tt",
      "Gain an annexation war goal against the government which refused this invitation. Requires peace, its independence, and no common faction, non-aggression pact, truce or guarantee from us. War is not declared.",
      "Получить цель войны на аннексию против правительства, отказавшегося от этого приглашения. Требуются мир, его независимость и отсутствие общего альянса, пакта о ненападении, перемирия и нашей гарантии. Война не объявляется.")
    event(503, ("A Refusal in Writing", "Письменный отказ"),
          ("[From.GetName] has declined accession. Its reply recognises the conference but reserves authority to its own institutions. The cabinet can leave the matter there. Those who demand compulsion must instead seek an explicit mandate and explain why the claim justifies another war.",
           "[From.GetName] отказывается от присоединения. Ответ признаёт состоявшуюся конференцию, но сохраняет власть за собственными учреждениями. Кабинет может на этом закрыть вопрос. Сторонникам принуждения придётся отдельно добиваться полномочий и объяснить, почему притязание оправдывает новую войну."),
          option("HSM_AQR.503.a", ("Their answer will stand.", "Примем их ответ."), ai=8)
          + option("HSM_AQR.503.b", ("Seek a mandate to enforce the claim.", "Потребовать полномочий для осуществления притязания."),
                   f"custom_effect_tooltip = {R}claim_tt hidden_effect = {{ {R}authorise_claim = yes }}",
                   "HSM_AQR_REC_can_coerce = yes", ai=2),
          trigger="HSM_AQR_REC_known_refusal = yes")

    effect("REC_integrate_owned", """if = { limit = {
HSM_AQR_REC_national_peace = yes
has_country_flag = HSM_AQR_REC_peripheral_articles_done
}
every_owned_state = { limit = {
 HSM_AQR_REC_periphery_state = yes is_fully_controlled_by = PREV
 NOT = { is_core_of = PREV }
} add_core_of = PREV }
}""")
    once("REC_peripheral_articles", "HSM_AQR_REC_national_peace = yes "
         "has_country_flag = HSM_AQR_REC_peripheral_conference_done",
         "HSM_AQR_REC_integrate_owned = yes")
    L(R + "articles_tt",
      "Gain cores only on original Pomovarran, Flowenan, Greifwald, Fezeran and Northern Tribal territory that we own and fully control. The articles also cover later acquisitions when peace and full control return. This transfers no foreign territory and does not integrate subjects automatically.",
      "Получить национальные территории только на первоначальных землях Помоварры, Фловены, Грайфвальда, Фезеры и Северных племён, принадлежащих нам и полностью контролируемых. Статьи распространяются и на последующие приобретения после восстановления мира и полного контроля. Чужие территории не передаются, субъекты автоматически не присоединяются.")
    focus("REC_peripheral_articles", ("Rights Entered in the Register", "Права, внесённые в реестр"),
          ("Accession articles have to survive their ceremonial reading. Courts will recognise municipal records, officials will reconcile service histories, and the treasury will publish the same obligations for old provinces and new districts. A border on a minister's map grants no authority over a town which the government does not actually administer.",
           "Статьи о присоединении должны пережить торжественное чтение. Суды признают муниципальные записи, чиновники сверят послужные списки, а казна опубликует одинаковые обязательства для старых провинций и новых округов. Линия на министерской карте не даёт власти над городом, которым правительство в действительности не управляет."),
          32, 24, ("REC_peripheral_conference",),
          tt("REC_articles_req", "Independent Aquileia is at peace and controls its capital; the peripheral conference has been held.",
             "Независимая Аквелия находится в мире и контролирует столицу; конференция окраин состоялась.",
             "HSM_AQR_REC_national_peace = yes has_country_flag = HSM_AQR_REC_peripheral_conference_done"),
          f"custom_effect_tooltip = {R}articles_tt hidden_effect = {{ {R}peripheral_articles = yes }}",
          cost=6, icon="GFX_goal_generic_neutrality_focus")
    return "ideas = {\ncountry = {\n" + "\n".join(ideas) + "\n}\n}\n"


def build_reconstruction_decisions(tt, L) -> list[str]:
    """Return repeatable recall blocks, without a category wrapper or file I/O."""
    key = R + "recall_conference"
    L(key, "Reconvene the Peripheral Conference", "Возобновить конференцию окраин")
    L(key + "_desc",
      "Some chairs remained empty while neighbouring governments fought their own wars or could not speak for their territory. Other invitations lapsed without an answer. The chancery will send the articles when those obstacles have passed. Replies already received will remain in the record; reopening the hall does not cancel a neighbour's refusal.",
      "Некоторые кресла пустовали, пока соседние правительства вели свои войны или не могли отвечать за собственные земли. Другие приглашения истекли, так и не получив ответа. Канцелярия направит статьи, когда эти препятствия исчезнут. Полученные ответы сохранятся в протоколе: новое заседание не отменяет отказа соседа.")
    requirement = tt("REC_recall_req",
        "The united Aquileian government is independent, at peace and controls its capital; the conference has been held. At least one eligible peripheral government has no live invitation and has not refused us. Unanswered invitations can be renewed after 60 days. The recipient must be at peace, independent or our subject, outside a foreign faction, without subjects, and in full control of its owned territory.",
        "Объединённое аквелийское правительство независимо, находится в мире и контролирует столицу; конференция состоялась. У хотя бы одного подходящего правительства окраин нет действующего приглашения и оно не отказывало нам. Приглашение без ответа можно повторить через 60 дней. Получатель должен находиться в мире, быть независимым либо нашим субъектом, не состоять в чужом альянсе, не иметь субъектов и полностью контролировать принадлежащие ему земли.",
        "HSM_AQR_REC_can_recall = yes")
    return [f"""{key} = {{
icon = generic_political_discourse
visible = {{ HSM_AQR_REC_host = yes }}
available = {{ {requirement} }}
cost = 0
days_re_enable = 30
complete_effect = {{
 custom_effect_tooltip = HSM_AQR_REC_conference_tt
 hidden_effect = {{ HSM_AQR_REC_send_invitations = yes }}
}}
ai_will_do = {{ factor = 10 }}
}}"""]


def self_check() -> None:
    """Capture the actual callback contract; parse all generated blocks in memory."""
    from aquileian_base_tree import _parse, _walk, _one

    loc, triggers, effects, focuses, events = {}, {}, {}, {}, {}
    focus_meta = {}

    def L(key, en, ru):
        if key in loc and loc[key] != (en, ru):
            raise AssertionError("Conflicting localization: " + key)
        loc[key] = (en, ru)
        return key

    def record(dest, name, body):
        if name in dest:
            raise AssertionError("Duplicate definition: " + name)
        dest[name] = body

    def trig(name, body): record(triggers, P + name, body)
    def effect(name, body): record(effects, P + name, body)
    def once(name, condition, body):
        effect(name, f"if = {{ limit = {{ {condition} NOT = {{ has_country_flag = {P}{name}_done }} }} "
               f"set_country_flag = {P}{name}_done {body} }}")
    def tt(name, en, ru, condition):
        L(P + name + "_tt", en, ru)
        return f"custom_trigger_tooltip = {{ tooltip = {P}{name}_tt {condition} }}"
    def focus(name, title, desc, x, y, parents=(), available="", reward="", **kwargs):
        L(P + name, *title); L(P + name + "_desc", *desc)
        focus_meta[P + name] = (x, y, parents)
        record(focuses, P + name, f"x = {x} y = {y} available = {{ {available} }} completion_reward = {{ {reward} }}")
    def event(number, title, desc, options, trigger="always = yes", immediate=""):
        L(f"HSM_AQR.{number}.t", *title); L(f"HSM_AQR.{number}.d", *desc)
        record(events, str(number), f"trigger = {{ {trigger} }} immediate = {{ {immediate} }} {options}")
    def option(key, title, body="", condition="", ai=1):
        L(key, *title)
        return f"option = {{ name = {key} trigger = {{ {condition} }} ai_chance = {{ factor = {ai} }} {body} }}"

    ideas = build_reconstruction(L, trig, effect, once, tt, focus, event, option)
    decisions = build_reconstruction_decisions(tt, L)
    parsed = _parse(ideas) + _parse("\n".join(decisions))
    for collection in (triggers, effects, focuses, events):
        for key, body in collection.items():
            parsed += _parse(f"{key} = {{ {body} }}")
    nodes = tuple(_walk(parsed))
    forbidden = {"declare_war_on", "set_politics", "set_popularities", "puppet", "transfer_state_to",
                 "create_country_leader", "add_country_leader_role", "retire_character", "kill_country_leader",
                 "decrease_poverty", "decrease_illiteracy", "set_variable", "add_to_variable"}
    assert not forbidden.intersection(n.key for n in nodes)
    assert len(focuses) == 5 and set(events) == {"500", "501", "502", "503", "504"}
    assert len(_parse(ideas)[0].children[0].children) == 3
    assert sum(n.key == "annex_country" for n in nodes) == 1
    assert effects[R + "accept_offer"].startswith("if = { limit = { HSM_AQR_REC_valid_offer = yes }")
    assert effects[R + "refuse_offer"].startswith("if = { limit = { HSM_AQR_REC_valid_offer = yes }")
    assert "HSM_AQR_REC_can_coerce = yes" in effects[R + "authorise_claim"]
    assert "GAME_OVER_TT" in events["501"]
    assert events["501"].index("HSM_AQR.501.a") < events["501"].index("HSM_AQR.501.b")
    assert "all_owned_state" in triggers[R + "recipient_base"]
    assert "all_controlled_state" in triggers[R + "recipient_base"]
    assert "any_subject_country" in triggers[R + "recipient_base"]
    assert all(f"state_original_cores = {tag}" in triggers[R + "periphery_state"] for tag in PERIPHERY)
    assert "every_owned_state" in effects[R + "integrate_owned"]
    assert "is_fully_controlled_by = PREV" in effects[R + "integrate_owned"]
    assert focus_meta[ROOT_ID] == (32, 20, ())
    assert all(x == 32 for x, _, _ in focus_meta.values())
    assert {y for _, y, _ in focus_meta.values()} == set(range(20, 25))
    assert all(P + parent in focuses for _, _, parents in focus_meta.values() for parent in parents)
    assert "HSM_AQR_united" not in "\n".join(triggers.values())
    assert triggers[R + "united"].count("is_owned_and_controlled_by = PREV") == 5
    assert "offer_JER" in triggers[R + "valid_offer"]
    assert "refused_JER" in triggers[R + "known_refusal"]
    assert len(decisions) == 1 and "days_re_enable = 30" in decisions[0]
    assert "HSM_AQR_REC_can_recall = yes" in decisions[0]
    assert all(f"{R}can_invite_{tag} = yes" in effects[R + "send_invitations"] for tag in PERIPHERY)
    assert not any(n.key == "clr_country_flag" and n.value.startswith(R + "refused_") for n in nodes)
    dispatch = _parse(effects[R + "send_invitations"])
    dispatch_branches = [n for n in dispatch[0].children if n.key == "if"]
    assert len(dispatch_branches) == len(PERIPHERY)
    for tag, branch in zip(PERIPHERY, dispatch_branches):
        sent = _one(branch, "set_country_flag")
        assert _one(sent, "flag").value == R + "sent_" + tag
        assert _one(sent, "days").value == "60"
        # In the recipient scope PREV is the inviting country. Verify each
        # founder check and its offer marker together, not unrelated substrings.
        recipient = _one(branch, tag)
        bindings = [n for n in recipient.children if n.key == "if"]
        assert len(bindings) == len(FOUNDERS)
        for founder, binding in zip(FOUNDERS, bindings):
            assert _one(_one(_one(binding, "limit"), "PREV"), "tag").value == founder
            offer = _one(binding, "set_country_flag")
            assert _one(offer, "flag").value == R + "offer_" + founder
            assert _one(offer, "days").value == "60"
    refuse = _parse(effects[R + "refuse_offer"])
    for founder, branch in zip(FOUNDERS, (n for n in refuse[0].children if n.key == "if")):
        assert _one(_one(_one(branch, "limit"), "FROM"), "tag").value == founder
        refusal = _one(branch, "set_country_flag")
        assert refusal.value == R + "refused_" + founder and refusal.children is None

    # Bounded recipient-selection fixtures. The existing host and territorial
    # predicates are inputs here; this tests the actual new dispatch guards.
    def selection_fixture():
        countries = {tag: {"flags": set(), "expires": {}, "leader": tag + "_incumbent",
                           "eligible": False, "war": False,
                           "subject": None, "faction": None} for tag in (*FOUNDERS, *PERIPHERY)}
        countries["JER"]["host"] = True
        countries["POM"]["eligible"] = True
        return countries

    countries = selection_fixture()

    def matches(nodes, current="JER", previous=None, event_from=None, event_root=None):
        event_root = event_root or current

        def resolve(value):
            return {"PREV": previous, "FROM": event_from, "ROOT": event_root}.get(value, value)

        def nested(children, who=current, before=previous):
            return matches(children, who, before, event_from, event_root)

        def check(node):
            country = countries[current]
            children = node.children or ()
            if node.key == "AND": return nested(children)
            if node.key == "OR": return any(nested((n,)) for n in children)
            if node.key == "NOT": return not any(nested((n,)) for n in children)
            if node.key == R + "host": return country.get("host", False)
            if node.key == R + "recipient_base": return country["eligible"] and not country["war"]
            if node.key in triggers: return nested(_parse(triggers[node.key]))
            if node.key in countries or node.key in {"PREV", "FROM", "ROOT"}:
                return nested(children, resolve(node.key), current)
            if node.key == "tag": return current == resolve(node.value)
            if node.key == "has_country_flag": return node.value in country["flags"]
            if node.key == "is_subject": return (country["subject"] is not None) == (node.value == "yes")
            if node.key == "is_subject_of": return country["subject"] == resolve(node.value)
            if node.key == "is_in_faction": return (country["faction"] is not None) == (node.value == "yes")
            if node.key == "is_in_faction_with":
                return country["faction"] is not None and country["faction"] == countries[resolve(node.value)]["faction"]
            raise AssertionError("Unmodeled selection operation: " + node.key)
        return all(check(n) for n in nodes)

    recall = _parse(triggers[R + "can_recall"])
    countries["POM"]["war"] = True
    assert not matches(recall)
    countries["POM"]["war"] = False
    assert matches(recall)  # The originally blocked country can now be invited.
    countries["JER"]["flags"].add(R + "sent_POM")
    assert not matches(recall)  # No duplicate invitations on repeated decisions.
    countries = selection_fixture()
    countries["POM"]["flags"].add(R + "refused_JER")
    assert not matches(recall)  # Explicit refusal remains binding even without sent history.
    countries = selection_fixture()
    countries["POM"]["subject"] = "FLO"
    assert not matches(recall)
    countries["POM"]["subject"] = "JER"
    assert matches(recall)
    countries["JER"]["host"] = False
    assert not matches(recall)  # Lost sender eligibility invalidates a queued click.

    # Execute the actual dispatch/refusal flag operations and their source TTLs.
    # Only selection predicates are mocked; this is not an engine scheduler.
    day, queued = 0, []

    def execute(nodes, current="JER", previous=None, event_from=None, event_root=None):
        event_root = event_root or current
        for node in nodes:
            if node.key == "if":
                if matches(_one(node, "limit").children, current, previous, event_from, event_root):
                    execute(tuple(n for n in node.children if n.key != "limit"), current,
                            previous, event_from, event_root)
            elif node.key in countries or node.key == "FROM":
                target = event_from if node.key == "FROM" else node.key
                execute(node.children, target, current, event_from, event_root)
            elif node.key == "set_country_flag":
                flag = _one(node, "flag").value if node.children else node.value
                countries[current]["flags"].add(flag)
                if node.children:
                    countries[current]["expires"][flag] = day + int(_one(node, "days").value)
            elif node.key == "clr_country_flag":
                countries[current]["flags"].discard(node.value)
                countries[current]["expires"].pop(node.value, None)
            elif node.key == "country_event":
                queued.append((current, _one(node, "id").value))
            else:
                raise AssertionError("Unmodeled invitation operation: " + node.key)

    def advance(days):
        nonlocal day
        day += days
        for country in countries.values():
            for flag, expiry in tuple(country["expires"].items()):
                if expiry <= day:
                    country["flags"].discard(flag)
                    del country["expires"][flag]

    valid_offer = _parse(triggers[R + "valid_offer"])
    countries = selection_fixture()
    leaders_before = {tag: country["leader"] for tag, country in countries.items()}
    execute(dispatch)
    assert countries["JER"]["expires"][R + "sent_POM"] == 60
    assert countries["POM"]["expires"][R + "offer_JER"] == 60
    assert matches(valid_offer, "POM", event_from="JER")
    assert not matches(recall)  # No duplicate dispatch while the offer is live.
    # Another founder's sent marker must not authorize the original invitation.
    countries["JEB"]["host"] = True
    countries["JEB"]["flags"].add(R + "sent_POM")
    assert not matches(valid_offer, "POM", event_from="JEB")
    countries["POM"]["war"] = True  # War begins between sending and delivery.
    assert not matches(valid_offer, "POM", event_from="JER")
    advance(59)
    assert not matches(recall)
    advance(1)
    assert R + "offer_JER" not in countries["POM"]["flags"]
    assert not matches(recall)  # Expiry does not override the continuing war.
    countries["POM"]["war"] = False
    assert matches(recall)  # The unanswered offer can be renewed after expiry.
    execute(dispatch)
    assert queued.count(("POM", "HSM_AQR.501")) == 2
    assert countries["JER"]["expires"][R + "sent_POM"] == 120
    assert countries["POM"]["expires"][R + "offer_JER"] == 120
    assert all(country["leader"] == leaders_before[tag] for tag, country in countries.items())

    countries = selection_fixture()
    day, queued = 0, []
    leaders_before = {tag: country["leader"] for tag, country in countries.items()}
    execute(dispatch)
    execute(refuse, "POM", event_from="JER")
    assert R + "refused_JER" in countries["POM"]["flags"]
    assert R + "refused_JER" not in countries["POM"]["expires"]
    advance(60)
    assert not matches(recall)
    advance(600)
    execute(dispatch)
    assert not matches(recall) and queued.count(("POM", "HSM_AQR.501")) == 1
    assert all(country["leader"] == leaders_before[tag] for tag, country in countries.items())
    # Evaluate the native eligibility expression itself, without manufacturing
    # a post-Herzland completed focus or any regional-national claimant flags.
    native = _parse(triggers[R + "native_postwar"])

    def native_eligible(tag, completed, global_flags):
        def check(node):
            if node.key == "OR":
                return any(check(n) for n in node.children)
            if node.key == "original_tag":
                return node.value == tag
            if node.key == "has_completed_focus":
                return node.value in completed
            if node.key == "has_global_flag":
                return node.value in global_flags
            raise AssertionError("Unmodeled native eligibility operation: " + node.key)
        return all(check(n) for n in native)

    for end in ("JER_revolution_ended", "JER_revolution_ended_2"):
        for entry in NATIVE_ENTRY_FOCUSES:
            assert native_eligible("JER", {entry}, {end})
    assert not native_eligible("JER", set(), {"JER_revolution_ended"})
    assert not native_eligible("JER", set(NATIVE_ENTRY_FOCUSES), set())
    assert not native_eligible("JEB", set(NATIVE_ENTRY_FOCUSES), {"JER_revolution_ended"})
    assert not native_eligible("JER", {"JER_viviene_triumphant"}, {"JER_revolution_ended"})
    assert all(en and ru for en, ru in loc.values())
    print(f"PASS: 5 focuses, 3 crisis stages, 5 events, 1 recall decision; {len(triggers)} triggers, "
          f"{len(effects)} effects, {len(loc)} EN/RU keys. Syntax, early native eligibility, "
          "recall expiry/refusal/identity fixtures and scope contracts; no engine execution.")


if __name__ == "__main__":
    self_check()
