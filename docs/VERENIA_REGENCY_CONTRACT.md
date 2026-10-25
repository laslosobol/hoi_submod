# Avian: The Limited Herzland Settlement

## Scope

Continuation of the preserved Katrina union, not the Zypressen route. New files use `HSM_VER_regency.txt`, prefix `HSM_VER_REG_`, namespace `hsm_ver_regency`. No new art, counters, continental claims, automatic foreign annexations or workbook edits. Existing regency elsewhere is respected; CYA files and custody are untouched.

Planning source: workbook `outputs/01a0cedc-8cc7-7800-b208-c4b9449f4226/griffonia-regional-paths-and-policy.xlsx`, West/Verenia row12. Native sources: `common/characters/GRI.txt` (the original Grover character), `events/Grover_Events.txt` (death, custody and majority after 1021.5.21), `common/scripted_effects/00_scripted_effects.txt:core_all_herzland_states` (GRI BRZ STW KAT ANG YAL ROU PYT FEA original-core arrays). Existing ERI defensive-provenance module supplies the pattern, not AVI's certificates.

## Boundaries

Record original GRI's actual declaration against a charter signatory while AVI participates in the preserved union. AVI must actually defend, defeat GRI alongside the recorded victim and receive a qualifying peace-conference certificate. Offensive wars, occupation and unrelated victories do not qualify. A 45-day post-conference settling period prevents immediate interference with native custody events. Entry requires all original Herzland cores owned/controlled by AVI, its subjects or actual independent ERI/EYR charter partners; AVI itself owns and controls Griffenheim. No backfill for older saves.

Katrina remains Avian's executive during the regency. An adult Grover becomes the constitutional head of the composite Avian-Herzland state, with Verenia's reserved institutions represented by the continuing charter and a constitutional-guarantees spirit. ERI and EYR remain independent; neither is annexed, puppeted or forced into a faction. This is a new authored constitutional settlement, not a claim that the base mod already provides it. No new GRI country is released and no territories are silently reassigned.

Custody: recognise the original living local character, never the idea alone. Recover from an annexed original GRI only if all GRI original cores are actually owned/controlled by AVI and no living foreign country has Grover. A living ERI/EYR host can voluntarily transfer the non-ruling minor under separate consent. Other hosts, including CYA, are acknowledged but not solicited or modified. A dead or already reigning Grover is never recruited, restored, seized or made a minor again. A minor transferred by a consenting House is never transferred a second time. The court-file event and optional later decision can revisit availability; neither requires granting a regency.

## Focus Contract

12 focuses, absolute x48..52/y12..19, imported only into initial avian tree.

| Suffix | Position | Outcome |
| --- | --- | --- |
| after_defence | 50,12 | Requires completed regional settlement and genuine defensive Herzland victory. Starts talks, event1. |
| household_file | 48,13 | Confirm Grover's factual status; try strictly eligible recovery/consenting House request. Event2 status variants. |
| civilian_contracts | 52,13 | One civilian factory/slot in owned controlled Griffenheim, fallback industry research; once only. |
| agreement_for_herzland | 50,14 | Event3: propose limited regency when local living minor, or civilian compact without royal claim. ERI/EYR receive event10 with separate assent/refusal for either proposal. |
| schools_and_witnesses | 48,15 | Once agreement effective: two75%industry bonuses, event4 child scene if actual local minor; otherwise civic scene. |
| defence_articles | 52,15 | Event5: joint logistics (+10% planning speed,-8% supply use,-.10 dailyPP) or territorial reserves (+10% core defence,+10% recovery,-5% planning speed). Replaces alternative, once. |
| petitions_to_the_council | 50,16 | Event6: local child observes an inconvenient petition (records memory) or civilian council analogue, no fake child appearance. |
| rebuilding_the_quarters | 48,17 | Two100%construction bonuses, +25armyXP. |
| reserved_house_rights | 52,17 | Constitutional guarantees (+6% stability,+10% industry efficiency gain,-5%PPfactor), conditional on live settlement. |
| a_finite_guardianship | 48,18 | Regency or completed majority only. Event7 explains expiry; no age-delay lock or extra regency extension. |
| a_union_without_a_throne | 52,18 | Civil compact only. Event8 varies confirmed death vs living unavailable/unknown. No personal union or fictitious monarch. |
| the_settled_frontier | 50,19 | Either preceding finale. Record completion/event9; no further territorial goals. |

## Events and Lifecycles

Events1intro;2household report (localminor/localadult/dead/abroad/unknown);3proposal(regency conditional/civil universally);4schoolscene(child/civic);5defencepolicy2options;6petition(child/civic);7finiteguardianship;8civilcompact(dead/other);9finale(regency/adult/civil);10partnerconsent(sign/refuse);11response AVI(accepted/refused);12livingERI/EYRhost custodyconsent(transfer/refuse);13interruptedregency/death/lostcustody;14majority, follows education/petition memories;15expiry notification if diplomatic replies undelivered. All13day response windows, replay-safe meaningful options. Pending guards45days, invitation retry90days. Daily retries missed domestic scenes without charging twice.

Agreement does not take effect without both Houses' consent. Both routes use same independent consent; one refusal offers a new civil proposal after cooldown, not automatic signature. Refusal never changes charter or imposes a penalty. Timed pending fallback handles dropped delivery. Joint regency benefit(+8% stability,+8%PPfactor,-.15dailyPP) requires actual local minor and live signatories; ended on death, loss of custody or adulthood, never restored from history. Common civic settlement(+15% repair,+10% infrastructure construction) needs actual compact assent, not false royal legitimacy.

Majority ends regency automatically after1021.5.21. If still present, alive, independent and under the agreed government, Grover receives the native constitutional_monarchism leader role and adult portrait. EaW places that subtype in neutrality; the succession explicitly selects that ruling group before promoting the original character. This is the agreed constitutional succession, not a coup against a different native regime. No empire-wide cores are granted. Existing AVI government checks accept this specific recorded succession to preserve its regional charter and budget. If another regime, death or custody change intervenes, the regency ends without appointment. Institutions may pause during occupation; appointment waits for peace, the live charter and both settlement signatures, without extending minority. A civilian pact can be renegotiated after a terminated regency.

Decisions: reconsider agreement (90-day retry), request House-held household (90-day retry), reopen household file/strict recovery. No decisions to conquer or fabricate an imperial victory.

## Verification

`tools/Test-VereniaRegency.py` contains 51 parsed-source regression tests. It extends the existing Avian fixture with explicit country/state/character scopes, all original-core arrays, war sides, dates, leader roles and event choices. Unsupported predicates and effects fail instead of silently succeeding. Verified cases include legitimate defensive entry, false victory rejection, House assent/refusal/expiry, no foreign theft or resurrection, custody transfer only once, majority during interrupted institutions, government changes, original character promotion and continuing regional-budget benefits.

Both localizations contain 147 matching keys with UTF-8 BOM. The selected source/scenario checks do not emulate HOI4's event scheduling, original-character retirement on annexation, rendering or save/reload. The new-campaign checklist in `VERENIA_IMPLEMENTATION.md` remains required before release.
