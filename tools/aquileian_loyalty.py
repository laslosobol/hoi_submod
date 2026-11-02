"""One postwar choice: join the existing Aquileia or fight for its leadership.

Public API: build_loyalty(L,trig,effect,once,tt,focus,event,option,config) -> [].
Main must call JER = { HSM_AQR_dispatch_postwar_choice = yes } daily.
Hidden JER event 456 establishes ROOT=JER before sending regional event 30.
Native JER integration hooks can send event 30 directly. Delivery freezes the
centre for that episode; every mutation rechecks the live context. Unanswered
invalid episodes can be retired safely and reoffered with a fresh snapshot.
No visible congress/war focus, approval chain, fee, or peaceful takeover of JER.

Legacy scripted names remain resolvable. Old approval effects/events are inert.
Main owns programme progression, national_mandate, proclamation and restoration.
"""
P = "HSM_AQR_"
TAGS = ("JEB", "JRR", "JFT", "VIN")
ROYAL_DEFAULTS = ("JEB_royal", "JRR_absolutist", "JRR_coalition", "JFT_dennis", "VIN_gadiffer")
REPUBLIC_DEFAULTS = ("JEB_moderate", "JRR_colette", "JFT_fja", "VIN_sis")
OWN_MODEL_DEFAULTS = ("JEB_constitutional", "JEB_cocardiers", "JFT_communes", "JFT_enfants", "VIN_abc", "VIN_chevaliers")
GOVERNMENTS = ("neutrality", "democratic", "fascism", "communism")
CENTRE_FLAGS = ("JER_is_monarchist", "JER_democracy_established")


def build_loyalty(L, trig, effect, once, tt, focus, event, option, config):
    routes = tuple(row[0] for row in config)
    assert set(routes) == set(ROYAL_DEFAULTS + REPUBLIC_DEFAULTS + OWN_MODEL_DEFAULTS)
    identity = "OR = { " + " ".join(
        f"AND = {{ tag = {tag} original_tag = {tag} }}" for tag in TAGS) + " }"
    def any_flag(prefix, members):
        return "OR = { " + " ".join(f"has_country_flag = {P}{prefix}{rid}" for rid in members) + " }"

    ratified = any_flag("ratified_", routes)
    selected = any_flag("native_mandate_", routes)

    def preference(members):
        candidates = "OR = { " + " ".join(f"{P}native_candidate_{rid} = yes" for rid in members) + " }"
        other = "OR = { " + " ".join(f"{P}native_candidate_{rid} = yes" for rid in routes if rid not in members) + " }"
        # Ratification outranks a selected native mandate, which outranks an
        # unambiguous candidate family. Cross-family ties retain neutral weights.
        return f"""OR = {{
 {any_flag('ratified_', members)}
 AND = {{ NOT = {{ {ratified} }} {any_flag('native_mandate_', members)} }}
 AND = {{ NOT = {{ {ratified} }} NOT = {{ {selected} }} {candidates} NOT = {{ {other} }} }}
}}"""

    for name, members in (("national_royal_default", ROYAL_DEFAULTS),
                          ("national_republic_default", REPUBLIC_DEFAULTS),
                          ("national_model_default", OWN_MODEL_DEFAULTS),
                          ("national_dennis_default", ("JFT_dennis",))):
        trig(name, preference(members))
    trig("support_source_identity", identity)
    # A first provincial refusal must not invalidate the other provinces' offers.
    centre = "exists = yes original_tag = JER is_subject = no has_capitulated = no"
    # Local rule includes registration and a living participant. A province
    # fighting another region can still decide; only war with JER blocks it.
    # No ratification or friendship gate: eligible controllers get both choices.
    context = f"""HSM_AQR_local_rule = yes HSM_AQR_revolution_finished = yes HSM_AQR_outcome = yes
{identity}
exists = yes has_capitulated = no
NOT = {{ has_war_with = JER }}
OR = {{ is_subject = no is_subject_of = JER }}
JER = {{ {centre} }}
NOT = {{ has_country_flag = HSM_AQR_nation }}
NOT = {{ has_country_flag = HSM_AQR_postwar_choice_answered }}
NOT = {{ has_country_flag = HSM_AQR_leadership_war_started }}
"""
    trig("postwar_choice_context", context)
    trig("postwar_choice_ready", """HSM_AQR_postwar_choice_context = yes
NOT = { has_country_flag = HSM_AQR_postwar_choice_requested }
""")
    # Freeze government and both native regime markers. A queued/open offer must
    # not silently change its political addressee. Never refresh an old snapshot.
    snapshot = []
    same = ["OR = { " + " ".join(
        f"AND = {{ has_country_flag = {P}transition_centre_{g} JER = {{ has_government = {g} }} }}"
        for g in GOVERNMENTS) + " }"]
    for g in GOVERNMENTS:
        snapshot.append(f"if = {{ limit = {{ JER = {{ has_government = {g} }} }} set_country_flag = {P}transition_centre_{g} }}")
    for flag in CENTRE_FLAGS:
        saved = P + "transition_" + flag
        snapshot.append(f"if = {{ limit = {{ JER = {{ has_country_flag = {flag} }} }} set_country_flag = {saved} }}")
        same.append(f"""OR = {{
 AND = {{ has_country_flag = {saved} JER = {{ has_country_flag = {flag} }} }}
 AND = {{ NOT = {{ has_country_flag = {saved} }} JER = {{ NOT = {{ has_country_flag = {flag} }} }} }}
}}""")
    effect("snapshot_transition_centre", "\n".join(snapshot))
    trig("transition_centre_unchanged", "\n".join(same))
    sender = f"FROM = {{ tag = JER {centre} }}"
    trig("can_deliver_postwar_choice", f"""{identity} exists = yes
FROM = {{ tag = JER original_tag = JER }}
NOT = {{ has_country_flag = HSM_AQR_postwar_choice_answered }}
NOT = {{ has_country_flag = HSM_AQR_postwar_choice_delivered }}
OR = {{
 has_country_flag = HSM_AQR_postwar_choice_requested
 AND = {{ HSM_AQR_postwar_choice_context = yes {sender} }}
}}
""")
    # A packet that becomes stale after its hidden relay may still open, but
    # only with dismissal. Mark it delivered so daily maintenance cannot replace
    # its snapshot under an open dialog. Invalid new native calls stay blocked.
    effect("begin_postwar_choice", """if = { limit = { HSM_AQR_can_deliver_postwar_choice = yes }
 if = { limit = { NOT = { has_country_flag = HSM_AQR_postwar_choice_requested } }
  HSM_AQR_snapshot_transition_centre = yes
 }
 set_country_flag = HSM_AQR_postwar_choice_requested
 set_country_flag = HSM_AQR_postwar_choice_delivered
 clr_country_flag = HSM_AQR_postwar_choice_queued
}
""")
    # Separate delivery and click guards: immediate has already set delivered
    # when the option is clicked, whereas another delivery must now be rejected.
    valid = f"""HSM_AQR_postwar_choice_context = yes
{sender}
has_country_flag = HSM_AQR_postwar_choice_requested
has_country_flag = HSM_AQR_postwar_choice_delivered
HSM_AQR_transition_centre_unchanged = yes
"""
    trig("valid_central_demand", valid)
    trig("valid_national_support", "HSM_AQR_valid_central_demand = yes")
    trig("can_continue_at_centre", "HSM_AQR_valid_central_demand = yes is_ai = no JER = { is_ai = yes }")
    trig("can_merge_into_centre", "HSM_AQR_valid_central_demand = yes OR = { is_ai = yes JER = { is_ai = no } }")
    trig("can_countermandate", "HSM_AQR_valid_central_demand = yes")

    reset = "\n".join(f"clr_country_flag = {P}{flag}" for flag in (
        "postwar_choice_requested", "postwar_choice_queued", "postwar_choice_delivered",
        *("transition_centre_" + g for g in GOVERNMENTS),
        *("transition_" + flag for flag in CENTRE_FLAGS)))
    invalid = "NOT = { AND = { HSM_AQR_postwar_choice_context = yes HSM_AQR_transition_centre_unchanged = yes } }"
    effect("cleanup_postwar_choice", "if = { limit = { "
           "has_country_flag = HSM_AQR_postwar_choice_requested "
           "NOT = { has_country_flag = HSM_AQR_postwar_choice_delivered } "
           "NOT = { has_country_flag = HSM_AQR_postwar_choice_answered } "
           + invalid + " }\n" + reset + "\n}")
    effect("dismiss_postwar_choice", "if = { limit = { "
           "has_country_flag = HSM_AQR_postwar_choice_delivered "
           "NOT = { has_country_flag = HSM_AQR_postwar_choice_answered } "
           "NOT = { HSM_AQR_valid_central_demand = yes } }\n" + reset + "\n}")

    dispatch, relay = [], []
    for i, tag in enumerate(TAGS):
        dispatch.append(f"""if = {{ limit = {{ {tag} = {{ HSM_AQR_postwar_choice_ready = yes }} }}
 {tag} = {{
  HSM_AQR_snapshot_transition_centre = yes
  set_country_flag = HSM_AQR_postwar_choice_requested
  set_country_flag = HSM_AQR_postwar_choice_queued
 }}
 country_event = {{ id = HSM_AQR.456 hours = 1 }}
}}""")
        # One hidden packet consumes one queued recipient. A native delivery can
        # win the race and clear queued; extra hidden packets then do nothing.
        branch = "if" if i == 0 else "else_if"
        relay.append(f"""{branch} = {{ limit = {{ {tag} = {{ has_country_flag = HSM_AQR_postwar_choice_queued }} }}
 {tag} = {{
  HSM_AQR_cleanup_postwar_choice = yes
  if = {{ limit = {{
   has_country_flag = HSM_AQR_postwar_choice_queued
   HSM_AQR_postwar_choice_context = yes HSM_AQR_transition_centre_unchanged = yes
   NOT = {{ has_country_flag = HSM_AQR_postwar_choice_delivered }}
  }}
   clr_country_flag = HSM_AQR_postwar_choice_queued
   country_event = {{ id = HSM_AQR.30 hours = 1 }}
  }}
 }}
}}""")
    # Cleanup also runs while the centre is temporarily subject/capitulated.
    # It never resets an answered choice or rewrites an already open snapshot.
    cleanup = "\n".join(f"{tag} = {{ HSM_AQR_cleanup_postwar_choice = yes }}" for tag in TAGS)
    effect("dispatch_postwar_choice", "if = { limit = { tag = JER original_tag = JER }\n"
           + cleanup + f"\nif = {{ limit = {{ {centre} }}\n"
           + "\n".join(dispatch) + "\n}\n}")
    # event() accepts native description blocks as strings; hidden events need
    # no prose or options. ROOT is now JER, so the newly sent .30 has FROM=JER.
    event(456, ("Postwar Delegations", "Послевоенные делегации"), "hidden = yes", "",
          "tag = JER original_tag = JER", "\n".join(relay))

    # Mark answered BEFORE any switch/annexation; do not read ROOT or re-evaluate
    # source identity after change_tag_from. Each preselected branch reacquires
    # a fresh literal JER country scope for the literal regional annexation.
    transfer, absorb = [], []
    for i, tag in enumerate(TAGS):
        branch = "if" if i == 0 else "else_if"
        transfer.append(f"""{branch} = {{ limit = {{ tag = {tag} original_tag = {tag} }}
 JER = {{ change_tag_from = {tag} }}
 JER = {{
  if = {{ limit = {{ exists = yes original_tag = JER {tag} = {{ exists = yes }} }}
   annex_country = {{ target = {tag} transfer_troops = yes }}
  }}
 }}
}}""")
        absorb.append(f"""{branch} = {{ limit = {{ tag = {tag} original_tag = {tag} }}
 JER = {{ annex_country = {{ target = {tag} transfer_troops = yes }} }}
}}""")
    # Primitive guards at the mutation boundary remain useful if another file's
    # scripted triggers fail to parse. The live political snapshot is also checked.
    boundary = f"""HSM_AQR_valid_central_demand = yes
{context}
{sender}
has_country_flag = HSM_AQR_postwar_choice_delivered
HSM_AQR_transition_centre_unchanged = yes
"""
    answered = "set_country_flag = HSM_AQR_postwar_choice_answered\nclr_country_flag = HSM_AQR_postwar_choice_queued"
    effect("continue_at_centre", "if = { limit = { " + boundary
           + " is_ai = no JER = { is_ai = yes } }\n" + answered
           + "\n" + "\n".join(transfer) + "\n}")
    effect("merge_into_centre", "if = { limit = { " + boundary
           + " OR = { is_ai = yes JER = { is_ai = no } } }\n" + answered
           + "\n" + "\n".join(absorb) + "\n}")
    # The generic legacy accept alias cannot end a human's campaign. Only the
    # explicit GAME_OVER_TT option below may merge a human into a human JER.
    effect("accept_central_demand", """if = { limit = { HSM_AQR_can_merge_into_centre = yes is_ai = yes }
 HSM_AQR_merge_into_centre = yes
}
else_if = { limit = { HSM_AQR_can_continue_at_centre = yes }
 HSM_AQR_continue_at_centre = yes
}
""")

    # Native declaration syntax; only ROOT/JER bilateral relationships change.
    # If the region leads their faction, expel JER instead of dismantling it.
    war = """if = { limit = { is_subject_of = JER } JER = { end_puppet = ROOT } }
if = { limit = { is_in_faction_with = JER }
 if = { limit = { is_faction_leader = yes } remove_from_faction = JER }
 else = { leave_faction = yes }
}
if = { limit = { has_non_aggression_pact_with = JER }
 diplomatic_relation = { country = JER relation = non_aggression_pact active = no }
}
if = { limit = { has_truce_with = JER } set_truce = { target = JER days = 0 } }
diplomatic_relation = { country = JER relation = guarantee active = no }
JER = { diplomatic_relation = { country = ROOT relation = guarantee active = no } }
declare_war_on = { target = JER type = annex_everything }
"""
    effect("national_countermandate", "if = { limit = { " + boundary + " }\n"
           + answered + "\nset_country_flag = HSM_AQR_central_refusal\n" + war + """
 if = { limit = { has_war_with = JER }
  set_country_flag = HSM_AQR_leadership_war_started
  set_country_flag = HSM_AQR_national_countermandate_done
  set_country_flag = HSM_AQR_national_mandate_done
  if = { limit = { NOT = { has_completed_focus = HSM_AQR_national_mandate } }
   complete_national_focus = HSM_AQR_national_mandate
  }
 }
}
""")
    effect("refuse_central_demand", "HSM_AQR_national_countermandate = yes")
    # Kept callable for a main-owned fallback, but no longer a visible focus.
    effect("central_convention", """if = { limit = { HSM_AQR_settled = yes HSM_AQR_postwar_choice_ready = yes }
 JER = { HSM_AQR_dispatch_postwar_choice = yes }
}
""")
    trig("can_convene", "HSM_AQR_settled = yes HSM_AQR_postwar_choice_ready = yes")
    trig("congress_context", "HSM_AQR_postwar_choice_context = yes")
    trig("can_support_centre", "HSM_AQR_valid_central_demand = yes")
    trig("friendly_centre", "HSM_AQR_postwar_choice_context = yes")

    L(P + "continue_centre_tt",
      "Continue playing as Aquileia. Our territory and armed forces join it; its incumbent, political course and national focus progress are preserved.",
      "Продолжить игру за Аквелию. Наши территории и вооружённые силы войдут в её состав; её действующее руководство, политический курс и пройденные национальные фокусы сохранятся.")
    L(P + "merge_centre_tt",
      "Join Aquileia with our territory and armed forces. Its present leadership and national campaign continue.",
      "Войти в состав Аквелии вместе с нашими территориями и вооружёнными силами. Её нынешнее руководство и общегосударственная кампания сохранятся.")
    support_ai = "20 modifier = { factor = 0.05 HSM_AQR_national_model_default = yes }"
    war_ai = "1 modifier = { factor = 30 HSM_AQR_national_model_default = yes } modifier = { factor = 3 HSM_AQR_national_dennis_default = yes }"
    options = option("HSM_AQR.30.continue",
        ("Join the national movement; continue as Aquileia.", "Присоединиться к общегосударственному движению; продолжить за Аквелию."),
        "custom_effect_tooltip = HSM_AQR_continue_centre_tt hidden_effect = { HSM_AQR_continue_at_centre = yes }",
        "HSM_AQR_can_continue_at_centre = yes", ai=support_ai)
    options += option("HSM_AQR.30.incorporate",
        ("Join the national movement.", "Присоединиться к общегосударственному движению."),
        "custom_effect_tooltip = HSM_AQR_merge_centre_tt hidden_effect = { if = { limit = { is_ai = yes } HSM_AQR_merge_into_centre = yes } }",
        "HSM_AQR_can_merge_into_centre = yes is_ai = yes", ai=support_ai)
    options += option("HSM_AQR.30.game_over",
        ("Join Aquileia and end our separate campaign.", "Войти в состав Аквелии и завершить нашу отдельную кампанию."),
        "custom_effect_tooltip = GAME_OVER_TT custom_effect_tooltip = HSM_AQR_merge_centre_tt hidden_effect = { if = { limit = { is_ai = no JER = { is_ai = no } } HSM_AQR_merge_into_centre = yes } }",
        "HSM_AQR_can_merge_into_centre = yes is_ai = no JER = { is_ai = no }", ai=0)
    # Native previews contain only real diplomatic effects; no prose fees,
    # internal flags, approval stages, or claims of an automatic victory.
    options += option("HSM_AQR.30.lead",
        ("Refuse. We will fight to lead Aquileia.", "Отказать. Мы будем сражаться за руководство Аквелией."),
        "effect_tooltip = { " + war + " complete_national_focus = HSM_AQR_national_mandate } "
        "hidden_effect = { HSM_AQR_national_countermandate = yes }",
        "HSM_AQR_can_countermandate = yes", ai=war_ai)
    options += option("HSM_AQR.30.dismiss",
        ("Circumstances have changed. Close these talks.", "Обстоятельства изменились. Закрыть переговоры."),
        "hidden_effect = { HSM_AQR_dismiss_postwar_choice = yes }",
        "NOT = { HSM_AQR_valid_central_demand = yes }", ai=1)
    event(30, ("One Aquileia", "Одна Аквелия"),
          ("The revolution is over, and the envoys from Aquileia have come for an answer. They bring orders placing our garrisons and provincial offices under the national government. Those who sign will carry their supporters into the movement already governing the capital. Across the table, opponents argue that the country must instead be led from here. The envoys will leave with our signatures or with a declaration of war.",
           "Революция окончена, и посланники Аквелии прибыли за ответом. Они привезли приказы о передаче наших гарнизонов и областного управления национальному правительству. Подписавшие приведут своих сторонников в движение, уже управляющее столицей. По другую сторону стола возражают: страну должны возглавить здесь. Посланники уедут с нашими подписями либо с объявлением войны."),
          options, "HSM_AQR_can_deliver_postwar_choice = yes", "HSM_AQR_begin_postwar_choice = yes")

    # No saved approval can annex a country or turn old consent into a war.
    for name in ("can_propose_leadership", "centre_provisional", "leadership_political_match",
                 "ai_leadership_terms", "valid_leadership_request", "valid_leadership_confirmation",
                 "valid_support_request", "valid_support_confirmation",
                 "congress_mandate_unchanged", "congress_centre_unchanged"):
        trig(name, "always = no")
    for name in ("request_leadership", "reject_leadership", "accept_leadership",
                 "accept_leadership_human", "take_national_leadership", "request_support",
                 "reject_support", "authorise_support", "cancel_congress", "clear_congress"):
        effect(name, "# Retired approval protocol: intentionally inert.")
    for number in range(450, 456):
        event(number, ("An Earlier Petition", "Прежнее прошение"),
              "hidden = yes", "", "always = no")
    return []
