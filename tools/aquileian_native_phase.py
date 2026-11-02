"""Observe EaW's revolution; never grant or resolve a competing preparation."""
TAGS=('JEB','JRR','JFT','VIN')


def build_native_category_overlay(eaw_path):
    """Close only the Rilan club allocator once its political result is frozen."""
    from pathlib import Path
    from hashlib import sha256
    from aquileian_base_tree import _parse
    relative='common/decisions/categories/JER_decision_categories.txt'
    raw=(Path(eaw_path)/relative).read_bytes()
    snapshot=(Path(__file__).resolve().parents[1]/'EaW'/relative).read_bytes()
    assert raw==snapshot and sha256(raw).hexdigest()=='44919731bd90a46320306b4725c0b4896b8d86cfe74c437c9404db33c6afac1d', 'Native JER categories drifted; review before rebuilding'
    source=raw.decode('utf-8-sig')
    matches=[n for n in _parse(source) if n.key=='JER_JEB_committee_of_public_safety_category']
    assert len(matches)==1
    committee=matches[0]
    assert not any(n.key=='visible' for n in committee.children)
    insertion='\n\tvisible = { NOT = { has_country_flag = HSM_AQR_native_outcome_recorded } }\n'
    position=committee.end-1
    result=source[:position]+insertion+source[position:]
    _parse(result)
    assert result.replace(insertion,'',1)==source
    return relative,result


def build_native_phase(trig,effect):
    trig('mechanic_active','''JER = { exists = yes OR = { has_completed_focus = JER_state_of_aquileia has_completed_focus = JER_fight_for_freedom } }
NOT = { has_global_flag = JER_revolution_begun }
NOT = { has_global_flag = JER_revolution_ended }
NOT = { has_global_flag = JER_revolution_ended_2 }''')
    trig('revolution_running','''JER = { exists = yes }
has_global_flag = JER_revolution_begun
NOT = { has_global_flag = JER_revolution_ended }
NOT = { has_global_flag = JER_revolution_ended_2 }''')
    trig('revolution_finished','''OR = {
 has_global_flag = JER_revolution_ended
 has_global_flag = JER_revolution_ended_2
 AND = { has_country_flag = HSM_AQR_native_outcome_recorded JER = { exists = no } }
}''')
    # Register an existing region during preparation, ordinary resolution, or a
    # later release with a recorded native result. Registration grants nothing.
    effect('start_regions','\n'.join(f'''{tag} = {{
 if = {{ limit = {{ HSM_AQR_alive = yes NOT = {{ has_country_flag = HSM_AQR_started }}
  OR = {{ HSM_AQR_mechanic_active = yes HSM_AQR_outcome = yes has_global_flag = JER_revolution_begun }}
 }} set_country_flag = HSM_AQR_started }}
}}''' for tag in TAGS))
    effect('record_native_outcome','''if = { limit = {
 HSM_AQR_active = yes HSM_AQR_outcome = yes
 NOT = { has_country_flag = HSM_AQR_native_outcome_recorded }
}
 # Peaceful native resolution has a global result but no local flag. Freeze it
 # once, before subsequent national restoration changes the global government.
 if = { limit = { NOT = { has_country_flag = REVOLUTION_is_a_monarchist } NOT = { has_country_flag = REVOLUTION_is_a_revolutionary } }
  if = { limit = { HSM_AQR_won_royal = yes } set_country_flag = REVOLUTION_is_a_monarchist }
  else = { set_country_flag = REVOLUTION_is_a_revolutionary }
 }
 set_country_flag = HSM_AQR_native_outcome_recorded
 HSM_AQR_snapshot_native_politics = yes
}''')
    trig('postwar_opening_ready','''HSM_AQR_local_rule = yes
HSM_AQR_revolution_finished = yes
HSM_AQR_outcome = yes
OR = { has_war = no AND = { has_country_flag = HSM_AQR_leadership_war_started has_war_with = JER } }''')
    effect('opening','''if = { limit = { HSM_AQR_postwar_opening_ready = yes }
 HSM_AQR_record_native_outcome = yes
 HSM_AQR_queue_native_settlement = yes
}''')
    effect('open_postwar','''if = { limit = { HSM_AQR_postwar_opening_ready = yes }
 if = { limit = { NOT = { has_completed_focus = HSM_AQR_opening } }
  complete_national_focus = HSM_AQR_opening
 }
 HSM_AQR_opening = yes
}''')
