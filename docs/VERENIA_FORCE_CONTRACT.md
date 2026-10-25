# Verenia: Victory Does Not End the Feud

Implementation contract for the optional ERI/EYR forceful continuations. This is authored fiction extending the native equal rival claims, not a new canonical account of which House is legitimate.

## Shared Boundary

- The military root is reciprocally mutually exclusive with the new diplomatic-settlement root. A chosen diplomatic route cannot switch to conquest after refusal; it has a unilateral development ending instead. An actual armistice, treaty, non-aggression pact, shared faction or native friendship blocks a fresh hostile focus; no focus declares war.
- `HSM_VER_FORCE_eligible_house`: independent, uncapitulated ERI/EYR under its actual original ruling duke.
- `HSM_VER_FORCE_can_prepare`: eligible House, no protected peace, and either a free rival, a recorded settled victory or an ongoing rival war.
- `HSM_VER_FORCE_can_issue_goal`: eligible House, free rival, peace, no agreements or common faction, no native white-peace cooldown. Completion rechecks this predicate.
- `HSM_VER_FORCE_at_war`: actual ERI/EYR war. No foreign opponent is substituted.
- `HSM_VER_FORCE_settlement_context`: eligible House at peace, a recorded bilateral war, rival capitulation and actual peace conference, settling interval elapsed. The victor retains all its original provinces; all the rival's original provinces belong to the victor or its actual defeated rival subject. All five provinces require full control: 391/400 for Eyrie, 401/500/673 for Erie. Mere occupation, third-party annexation, white peace and unrelated puppets do not qualify.
- The root calls `HSM_VER_choose_military` before `HSM_VER_FORCE_prepare`, locking diplomacy and clearing outstanding bilateral invitations. Delayed/native offers recheck this commitment. `HSM_VER_FORCE_issue_goal` grants only the rival war goal. `HSM_VER_FORCE_open_settlement` marks that the political settlement has begun and removes native rivalry from the victor/its defeated rival. It neither annexes nor cores territory.
- `HSM_VER_FORCE_settlement_active` requires the recorded victory, live ruler/territorial conditions (`HSM_VER_FORCE_settlement_held`) and `HSM_VER_FORCE_settlement_started`. Unlike opening negotiations, established institutions remain operational during external wars, so their military bonuses actually work. All choices recheck it. Outcome flags record history; national spirits disappear temporarily if the government or territorial settlement ceases to qualify. A renewed bilateral war clears the old victory proof.
- `HSM_VER_FORCE_approach_avian` first opens the victor's explicit choice (`hsm_ver_force.4`): propose a border accord, or make no commitment. Only the former dispatches the independent, peaceful Avian invitation. The victor must also remain at peace at dispatch and response; war cancels a pending offer. Consent/refusal is explicit; this accord gives no annexation, puppet, faction, crown or marriage. No active wartime neutralisation through a delayed invitation. Older already-signed pacts remain valid and require ordinary diplomatic termination before a new hostile focus.
- Military proof flags are local to the victor: `HSM_VER_FORCE_war_recorded`, `HSM_VER_FORCE_rival_defeated`, `HSM_VER_FORCE_peace_recorded`, `HSM_VER_FORCE_settling` (30 days). A renewed bilateral war clears the old proof. Uncapitulation/white peace cannot preserve stale defeat evidence.

## Ownership

- Parent implements shared triggers/effects/on-actions, common Avian response and ERI focus/event/idea files; imports both new roots into the existing trees.
- EYR implementation owns `HSM_VER_eyrie_force.txt` in national_focus, scripted_effects, ideas and events only. Shared root `HSM_EYR_FORCE_the_last_campaign` follows `HSM_EYR_the_price_of_vigilance`; use x=32..36, y>=1. Call `HSM_VER_EYR_FORCE_maintain` from the shared daily hook. Event namespace `hsm_ver_eyr_force`.
- ERI root `HSM_ERI_FORCE_the_price_of_victory` follows `HSM_ERI_cost_of_feud`; same coordinates in its separate tree. Event namespace `hsm_ver_eri_force`. Maintenance `HSM_VER_ERI_FORCE_maintain`.
- Localization owner writes paired EN/RU `HSM_VER_force_l_*.yml`; derives actual keys from production, no invented upstream facts. Keep explanatory tooltip prose out of narrative scenes. Full narrative focus descriptions, scene text and meaningful choice labels.
- Test owner creates `tools/Test-VereniaForce.py`, reusing the existing parser and exercising actual production predicates/effects with bounded fixtures, plus graph/localization checks already supplied by Test-Verenia.py.

## Narrative Deliverables

ERI: war supporters expect spoils; Rosaline refuses to be part of a settlement as property; Vincent chooses binding rights for the defeated or a centralised winner's administration. A later estate claim tests whether the chosen order binds his own supporters. Development and final scenes reflect that choice, including a separately consenting/refusing Avian.

EYR: Iovinus must decide whether victory ends emergency command. Montague's correspondence and civilian workshop claims carry forward, without assuming a surviving ruler, marriage or captive that the game does not establish. Civilian demobilisation and lasting military tutelage have different obligations, benefits and later consequences. Do not turn Eyrie into the automatically benevolent House.

No counters, generated art, automatic declarations of war, annexation of independent states, imperial expansion, or edits to the user's planning workbook. The military continuation below can incorporate an actually defeated, consenting own subject.

## Avian Military Continuation (2026-10-23)

Each House now has three additional focuses, using existing GFX. The claim runs **parallel** to the old Avian accord, not after it and not mutually exclusive with a previously completed accord focus:

| House | Claim | Postwar Articles | Integration | Coordinates |
| --- | --- | --- | --- | --- |
| ERI | `HSM_ERI_FORCE_avian_claim` follows `reconstruction_contracts` AND `a_regular_levy` | `HSM_ERI_FORCE_avian_articles` | `HSM_ERI_FORCE_avian_integration` | x=38; y=8,10,12 |
| EYR | `HSM_EYR_FORCE_avian_claim` follows `useful_trades` OR `permanent_district_staff` | `HSM_EYR_FORCE_avian_articles` | `HSM_EYR_FORCE_avian_integration` | x=38; y=9,11,13 |

1. The claim grants an `annex_everything` goal against AVI directly from the focus. It never declares war or removes a pact/faction. It rechecks the established two-House settlement, independent peaceful Avian, its ownership of state 470, no outstanding accord, no shared faction/NAP, and `can_declare_war_on`. Its tooltip explicitly instructs the player to terminate old diplomatic commitments normally. An actual recorded ongoing Avian war or proven victory bypasses the now-unnecessary war goal.
2. Victory requires a recorded bilateral war against independent Avian after the two-House military settlement began, capitulation to our side, and a peace-conference result actually leaving the Avian heartland with us or our own defeated Avian subject. The 30-day settling interval and full owner control prevent occupation from masquerading as integration. White peace, another side's victory, gifts and another overlord's puppet do not qualify. Renewed war, uncapitulation and foreign annexation invalidate old evidence. Daily recovery records an ongoing war on loading an update, never invents a previous victory. Diplomatic-only wars do not enter this storyline.
3. The articles spend 75 political power **once**, using the documented `has_political_power > 74` trigger. Annexed Avian presents a choice between protected local courts/contracts and a central ducal commission. A surviving defeated own subject receives a binding local-rights offer, not an involuntary annexation. AI accepts these guarantees deterministically; a human Avian may refuse. Refusal preserves the actual subject relationship and blocks scripted annexation, without an AI dice-roll lock. Ordinary subject integration remains possible; if it subsequently removes AVI, the already-paid focus recovers the annexed-territory articles without charging again.
4. A subject's additional possessions do **not** block this offer. Live consent explicitly covers its government, armed forces and existing holdings. State 470 may be held either by our defeated subject or directly by the victor while the subject retains outlying holdings. The new core is strictly limited to **470**; no loop cores extra acquired lands. This is not permission to annex any unrelated own puppet: the actual AVI war/capitulation/peace proof, current overlord and specific consenting overlord must all match.
5. Ratification starts a 90-day transition and the provisional spirit (-10% political-power gain, -5% construction speed). The 70-day final focus requires the same live victory, territorial ownership and consent, then annexes only a qualifying own subject if one survives. It cores 470, builds one civilian factory there, and replaces the burden with either the charter (+10% construction, +10% production-efficiency growth, -5% political-power gain) or commission (+10% factory output, +5% army organisation, -5% stability). The two outcomes cannot stack. Established benefits survive external wars but pause on loss of the required government/territory. Restoration does not rebuild factories or repeat core/annex rewards.
6. A 60-day follow-up distinguishes the charter's enforceable local judgement from the commission's effective supply system and unrepresented petitioners. No marriage, custody of a named character, death or surviving ruler is invented. Event `.10` is Avian's response to the military demand; `.11/.12` are subject/annexed articles; `.13` reports refusal; `.14` is the policy-dependent epilogue. Narrative text is separate from mechanical tooltips.

Choice/invitation events `.4`, `.1`, `.11` and `.12` use explicit 20-day event timeouts inside 45-day delivery leases. Dropped deliveries can recover; late choices recheck the current parties, war, ownership and consent state. Signed/refused responses and the integration reward are one-shot. No new decisions were added.

### Save Compatibility

The new connected shared focuses appear below the existing reconstruction choices when trees are reloaded. Completing the old third-House or domestic-final focus does not exclude them. A previously accepted Avian pact is deliberately not erased: terminate it legally and leave any shared faction before taking the claim. An update cannot certify an already-finished Avian conquest that predates the new war/peace records. Test a fresh save or a save before the Avian war for this continuation; do not manufacture proof flags from territory alone.

## Installed Source References

All paths below refer to `C:/shit/Steam/steamapps/workshop/content/394360/1826643372`, inspected 2026-10-21 and rechecked for Avian on 2026-10-23.

- `history/states/391-Verenia.txt`, `400-Eyrie.txt`, `401-Erie.txt`, `500-Balefire.txt`, `673-Comrik.txt`: original ownership and cores. Eyrie's capital is 391, not 400 (`history/countries/EYR - HouseEyrie.txt`).
- `history/states/470-Avian.txt`: the only state whose initial owner is AVI in the installed state histories; original core AVI, one civilian and one military factory. New integration deliberately cores only this state.
- `history/countries/ERI - HouseErie.txt` and `EYR - HouseEyrie.txt`: the original ruling characters and the shared rivalry spirit.
- `events/Erie_Events.txt`, `erie.1/.2`: native white-peace bypass flag and two-year rivalry cooldown. New war goals respect that cooldown; a white peace cannot certify a conquest settlement.
- `common/national_focus/AVI.txt`, `ending_the_rivalry`, `treaty_of_friendship`, and `events/Avian Events.txt`: native mediation, relationships and integration boundaries. In the submod's negotiated campaign a completed friendship focus is only an offer; refusal is not a binding treaty.
- `localisation/english/eaw_welcomescreen_l_english.yml`, the Avian introduction: the competing ducal claims and Katrina's relationship to the two Houses. New estate hearings, correspondence disputes, reserve-training cases and administrative endings are authored additions, not pre-existing canonical events.

## Completed Scope And Verification

Each House gains 17 focuses (14 original military + 3 Avian continuation). The package has eight Erie scenes, six Eyrie scenes and nine shared events, including the new victor's border-policy choice, military demand, postwar articles, refusal and epilogue: 23 events in total. This update adds six focuses, six events and three shared spirits, with paired English/Russian localization. No new decisions or art. Avian's refusal or unavailability never blocks a domestic finale. A declined accord is not retried automatically; an undelivered invitation can retry once eligibility returns and the delivery lease expires.

Erie's local-rights ending binds Vincent to the courts and reverses an earlier patron exception, remembering that reversal in the final scene. Its centralised ending retains the chosen estate judgement. Eyrie's civilian and military settlements differ in reserve employment, correspondence, workshops and a delayed inspection. Policy choices replace alternatives rather than stacking both sides' spirits. Losing the governing/territorial conditions suspends the settlement's bonuses and liabilities; recovery restores the recorded outcome without repeating one-time research or construction.

`tools/Test-VereniaForce.py` exercises the actual parsed predicates, hooks and effects: 70 tests, including 18 added for this update. They cover both Houses, old completed trees, conscious NAP offers, pact/faction/engine locks, war provenance, 30/90-day gates, occupation and unrelated gains, live subject consent, additional holdings and split ownership, interrupted deliveries, 75-PP boundary, stale callbacks, idempotent annex/core/factory effects, external-war benefits, and the delayed policy-specific epilogue. It is a bounded fixture interpreter, not the game engine. In-game focus placement, peace-conference scope behaviour, event presentation and AI pacing still require playtesting.
