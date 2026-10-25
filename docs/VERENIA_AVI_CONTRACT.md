# Avian Treaty Continuation

## Scope and Sources

This stage implements the regional survival of the consenting three-House union under Katrina. It is the political prerequisite for a later, separate defensive-victory imperial/regency continuation, not that continuation itself. No new content for isolationism, technocracy or loyalists; no Zypressen imperial campaign yet. No icons, workbook edits, country-history edits, character transfers or new meters.

Native references: installed EaW `common/national_focus/AVI.txt`, `events/Avian Events.txt`, `common/characters/AVI.txt`, `localisation/english/country_AVI_l_english.yml` and `EAW_WS_AVI_desc` in `eaw_welcomescreen_l_english.yml`. The source supports Katrina's kinship, the divided population, existing inter-House cooperation and the distinction between friendship, vassalisation and the later political crisis. New budget, translation and appropriation disputes are authored fiction.

New shared root imports only into initial `avian` tree, at x50/y0; all new positions x48..55/y0..9, clear of native bounds ending at x45. It is mutually exclusive with native `full_integration`. Entry requires `treaty_of_friendship`, actual bilateral treaty or adoptable unbroken native peace, actual Katrina government, no late regime/ball, independent living ERI/EYR/AVI. Starting this route never releases subjects or revives annexed Houses. Native development, army and earlier cooperation stay available. Full integration and its ball/crisis route remain unchanged when this new alternative was not chosen.

## Focus Contract

All IDs prefixed `HSM_AVI_`; namespace `hsm_ver_avian`. Existing art only.

| Suffix | Coordinate | Outcome |
| --- | --- | --- |
| three_separate_seals | 50,0 | Commit to preserved equal route, adopt existing native treaty only when valid, AVI voluntarily becomes observer; event1. |
| two_legible_copies | 48,1 | Event2: professional translation office costs50PP and gives stability+.06/research+.03/dailyPP-.10; or locally appointed clerks with stability+.03/PPfactor+.08. These are common-administration arrangements, not an automatic cure of all native cultural conflicts. |
| hear_the_towns | 52,1 | Event3 civic petitions, one75%construction bonus. |
| charter_without_submission | 50,2 | Sponsor shared charter negotiation through existing ERI/EYR register; AVI ratifies separately via63. Bypass only actual three-party charter. |
| common_accounts | 48,3 | Invite ERI and EYR to budget protocol, event20 in each actual country. Each may pay35PP and sign or refuse without punishment.30day deadline event29,45day fallback pending expiry,90day retry. AVI contributes by completing focus. |
| roads_between_houses | 52,3 | Shared services and two75%industry bonuses for AVI. No forced foreign construction. |
| limited_joint_staff | 48,4 | Shared staff,20armyXP,one75%support bonus. No automatic faction. |
| a_court_for_hosts | 52,4 | Event4 Katrina acknowledges common court's jurisdiction over host;one75%electronics bonus. |
| the_first_common_budget | 50,5 | Requires both budget replies resolved, even refusals. Event10 varies by both/one/no signatories;no fake unanimity. |
| the_unauthorised_levy | 50,6 | Event30 attempt to use unpaid emergency levy beyond agreed obligations. Honour limits:75PP cost; protect appropriation:100PP immediate+production+.10/stability-.07/consumer goods+.05, suspends ALL charter benefits including budget. |
| honour_the_exemptions | 48,7 | After compliance/repair:one actual ownedcontrolledcore civilian factory+slot;100%construction bonus fallback. |
| common_workshops | 52,7 | After compliance/repair:two100%industry bonuses;no extra research slot. |
| defence_without_a_master | 48,8 |20armyXP,one100%engineers bonus;acknowledge native military arrangements, no forced faction membership or extra alliance system. |
| open_minutes | 52,8 | Event41 public account of disputed levy and chosen language policy, no numerical reward. |
| a_union_worth_keeping | 50,9 | Requires both preceding branches, completed settlement flag,event50;independent Houses, no imperial title. |
| neighbours_without_a_chair | 55,4 | Failed charter peaceful alternative,event51,one100%construction bonus. Later charter retries allowed. |

## Events

1 intro oneoption;2 language twooptions;3 petitions one;4 host jurisdiction one;10 budget outcome three conditional descriptions (`.both.d`, `.one.d`, `.d`),oneoption;20 budget consent eachERI/EYR twooptions;21 AVI report recipientdecision generic text,one;29 timed budget lapse in recipient one;30 levy twooptions;31 recipientreactionERI/EYR (`.breach.d`,`.d`),one;32 AVI recovery one;41 publicminutes (`.breach.d` ifpreviouslydefied,`.d` otherwise),one;50 unionepilogue one;51failedcharter one. All explicit13day timeout. Long narrative scenes1,2,3,4,10,30,32,41,50,51;actual choices not instructions about the mod.

## State

Prefix `HSM_AVI_`: `preserved_union`, `language_resolved`, `translation_office`, `local_clerks`, `language_pending`, `charter_requested`, `membership_retry`, `budget_prepared`, `budget_pending`, `budget_retry`, `budget_signed`, `budget_answered`, `budget_reviewed`, `budget_scene_pending`, `levy_pending`, `levy_resolved`, `levy_exception`, `levy_previously_defied`, `levy_settled`, `works_awarded`, `settlement_completed`, `independent_settlement`, `minutes_seen`. Guards not counters. Signed budget is on each agreeing country. Pending/retry/reply state is on actual recipient.

Budget spirit `HSM_AVI_common_budget`: construction_speed_infrastructure+.15,production_efficiency_gain+.08,political_power_factor-.05. AVI receives it only with at least one actual valid partner signature; partner receives only with its own consent. All require live three-party charter and the preserved Katrina route. Temporary occupation pauses benefits; war between Houses, replacement of Katrina or entry into the native post-ball regimes invalidates this budget protocol. Renewing charter cannot restore a voided budget signature. New budget participation is explicitly negotiated again, with no repeated acceptance cost/reward. If annexation prevents deadline delivery, expiry of the pending guard allows the daily dispatcher to record silence without a signature or benefit.

Shared suspension gains a third cause, AVI's levy exception. Repairing one House never forgives another. A completed focus scene that loses eligibility retries using30day pending guard once valid, until choice resolves. Budgets refused or timed out do not block the main campaign.

## Decisions and Ideas

Category `HSM_AVI_congress_business`; decisions `HSM_AVI_reconvene_charter` (35PP,shared cooldown), `HSM_AVI_reaffirm_membership` (25PP,AVI renewed observer/consent after own refusal), `HSM_AVI_reopen_budget` (35PP,only unresolved/refusing participants,no restarting signed obligations), `HSM_AVI_withdraw_levy` (100PP,once,own breach only).

Ideas: `HSM_AVI_translation_office`, `HSM_AVI_local_clerks`, `HSM_AVI_common_budget`, `HSM_AVI_exceptional_levy` plus_desc. Research labels `HSM_AVI_construction_bonus`, `HSM_AVI_industry_bonus`, `HSM_AVI_support_bonus`, `HSM_AVI_electronics_bonus`, `HSM_AVI_engineers_bonus`. Tooltips `HSM_AVI_charter_offer_tt`, `HSM_AVI_budget_offer_tt`, `HSM_AVI_levy_case_tt`, `HSM_AVI_route_choice_tt`. Add readable newly visible flag names. English/Russian UTF8BOM.

## Ownership

Main edits game scripts and existing integration tests. Localization agent owns only EN/RU `HSM_VER_avian_l_*.yml`. Test agent owns only `tools/Test-VereniaAvian.py`, reusing parser/world from `tools/Test-Verenia.py` without editing that file. Tests must cover root eligibility/native split, bilateral charter sponsorship, each budget response, late/stale replies, timeout, refusal fallback, pauses vs war invalidation, third suspension cause and policy retry/idempotence. Native AVI inventory and coordinate preservation is checked except documented new import and reciprocal mutual exclusion on full_integration.
