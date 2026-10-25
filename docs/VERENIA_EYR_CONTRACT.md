# Eyrie Campaign Integration Contract

This implemented second-stage contract adds Eyrie's negotiated campaign, not its conquest route or a new imperial regency. Existing ERI/AVI content remains usable. No new art or workbook changes.

## Narrative

Iovinus is another stubborn, militarised claimant, not an inherently benevolent alternative to Vincent. His newly authored story asks how a border army can accept credible peace without claiming the right to govern indefinitely. Montague Eyrie, Earl of Verenia, and Rosaline Erie of Bantry remain highborn scions with an existing interest in one another, not invented children/heirs or automatically married. Katrina is aunt to both dukes. New events about rolls, inspections and requisition disputes are submod fiction, not claims about original EaW history.

Canonical anchors in the installed EaW `1826643372` source:

- `localisation/english/eaw_welcomescreen_l_english.yml`, `EAW_WS_AVI_desc`: ducal succession dispute, equally valid claimants, cadet Erie branch, Katrina Rivertail as aunt of both pretenders, and the civil-war origin of separate House domains.
- `localisation/english/country_AVI_l_english.yml`, `scion_swap_desc`, `treaty_of_friendship_desc`, `avi_news.2.d`, `avi_news.3.d`: the two named scions, existing peaceful rapprochement, mutual stubbornness and the distinct later Avian-led union.
- `common/characters/EYR.txt`, `EYR_duke_iovinus_eyrie`: governing character and field-marshal role. This is a narrative anchor for the military theme, not evidence that the newly written requisition crisis happened in canon.
- `history/countries/EYR - HouseEyrie.txt`: three initial research slots, pre-industrial society, poverty, incomplete literacy, `better_science_base`, the rivalry and the actual starting ruler. Domestic progression preserves these starting conditions.

## Focus IDs

Political tree `HSM_EYR_negotiated_verenia`, common root x24,y0. Diplomatic root `HSM_EYR_diplomatic_settlement` at x14,y1 and military root at x34,y1 are mutually exclusive. Shared domestic roots are `HSM_EYR_borderland_reconstruction` and `HSM_EYR_defensive_service`, x0 and x6 respectively. The route revision in `VERENIA_IMPLEMENTATION.md` supersedes older retry/offer-loop descriptions below: new ducal signing focuses resolve eligible AI agreements directly, while humans retain bilateral choice.

| ID suffix after HSM_EYR_ | Premise and concrete outcome |
| --- | --- |
| the_price_of_vigilance | Start Eyrie campaign; event 1. Existing native peace is adopted, never undone. |
| audit_the_muster | Event 2: public roll review costs 35 PP and adds accountable-muster spirit, or army commission provides 20 army XP and officers' confidence. |
| montagues_correspondence | Event 3: Montague's existing correspondence is a personal opening, not a marriage annexation. |
| diplomatic_settlement | Commit to the peaceful route, excluding military settlement. |
| reciprocal_frontier | After reciprocal guarantees, conclude the ceasefire with eligible AI Erie; human Erie receives an explicit offer. Bypass an existing valid agreement. |
| inspect_both_sides | One 75% engineer research bonus and event 4 about genuine joint inspections. |
| publish_the_rules | Requires both preliminary focuses, before the armistice. Shared scene chooses inspections or restitution; one 75% support-tech bonus. |
| friendship_with_safeguards | Conclude the friendship treaty with eligible AI Erie; a human retains the explicit reply. Bypass actual treaty. |
| limits_of_command | Event 10 chooses civic scrutiny or professional command, with distinct lasting defence/supply benefits and political cost. |
| a_seat_for_avian | Invite AVI as observer, then separate charter consent; never obligatory for EYR/ERI progression. |
| a_charter_we_can_sign | Propose equal council to ERI. ERI can request its limited ducal chair, which EYR can accept or reject. No subordination. Bypass actual charter. |
| officers_at_one_table | Shared staff, 20 army XP and one 75% signals research bonus. |
| shared_workshops | Shared services and one 75% industry bonus for EYR, no automatic research-slot gift. |
| the_return_order | Event 30: Eyrie's officers refuse to release requisitioned civilian workshops. Costs 75 PP to enforce return; protect the officers and all charter benefits are suspended. |
| a_defence_agreement | Military pact offer to ERI; uses an existing consenting House-led faction, or EYR leads a new one. No transfer from a third-party faction. |
| workshops_returned | After resolving EYR's command dispute: owned/core/controlled civilian factory and slot, or research fallback at cap. |
| a_border_without_orders | Completed settlement event 40. No annexation or compulsory continental expansion. |
| neighbours_without_a_council | Reachable directly from the diplomatic entry after a failed conference or lost counterpart, including failure before the armistice; unilateral construction research and event hsm_ver_routes.2, without claiming a foreign signature. |

## Political Events

Namespace `hsm_ver_eyrie`, event IDs below. EN/RU localisation follows `hsm_ver_eyrie.N.t/.d/.a/.b/.c` as required by actual script. Narrative scenes 1,2,3,4,10,30,31,32,40,41 should be substantial character/civic scenes, not explanations of the mod. Diplomatic offers also convey each side's agency.

| ID | Recipient and purpose | Options |
| --- | --- | --- |
| 1 | EYR, price of constant mobilisation | a acknowledge |
| 2 | EYR, false/missing entries in muster rolls | a public review; b army commission |
| 3 | EYR, Montague's correspondence with Rosaline | a permit independent correspondence |
| 4 | EYR, an inspection tests whether both sides will actually open their stores | a accept reciprocal procedure |
| 8 | EYR, AVI's observer answer, conditional acceptance/refusal description | a acknowledge |
| 10 | EYR, limits of military authority under a durable peace | a civic scrutiny; b professional command |
| 110 | ERI, armistice proposed by EYR | a accept; b joint-inspection counteroffer; c refuse |
| 111 | EYR, inspection counteroffer | a pay 35 PP/sign; b refuse |
| 112 | EYR, armistice agreed | a acknowledge |
| 113 | EYR, no armistice agreement | a acknowledge |
| 119 | EYR, armistice talks expired | a acknowledge |
| 120 | ERI, treaty proposed by EYR | a accept; b property arbitration; c refuse |
| 121 | EYR, property-arbitration counteroffer | a pay 50 PP/sign; b refuse |
| 125 | EYR, treaty signed | a acknowledge |
| 129 | EYR, treaty talks failed or expired | a acknowledge |
| 130 | ERI, Eyrie's proposed equal charter | a equal council; b request limited Erie presidency; c refuse |
| 131 | EYR, Erie's chairmanship request | a accept limited chair; b retain independence without charter |
| 132 | EYR, charter signed | a acknowledge |
| 139 | EYR, charter talks failed or expired | a acknowledge |
| 140 | ERI, Eyrie's military agreement | a accept; b refuse |
| 141 | EYR, military agreement answer, conditional accepted/refused description | a acknowledge |
| 30 | EYR, officers refuse to return a requisitioned civilian workshop | a enforce return (75 PP); b protect the command and suspend common institutions |
| 31 | ERI, Eyrie's answer to its own officers, conditional compliance/dispute description | a acknowledge |
| 32 | EYR, withdrawal of exceptional requisition order | a acknowledge |
| 40 | EYR, independent partner with reliable civilian/military limits | a acknowledge |
| 41 | EYR, peace without common government | a acknowledge |

## Shared State

### Playtest Revision: Negotiation Rather Than Repeated Rolls

The AI no longer has a random outright veto at each indispensable ERI/EYR negotiation. Without prepared guarantees it asks for reciprocal inspections (35 PP from the proposer), then property arbitration (50 PP) at the treaty stage. Accepting the counterproposal concludes that agreement; there is no second approval roll. Preparing guarantees in advance satisfies these conditions and produces a direct AI acceptance. Human recipients keep all accept, counteroffer and refuse options.

Inspection commitments place `HSM_VER_frontier_inspections` on both Houses during the armistice, costing 0.10 political power daily. A permanent treaty, expiry or invalidation of the armistice removes the cost. This is an actual reciprocal obligation, not another global meter. An equal charter is accepted by the AI; Erie's proposed presidency instead receives Eyrie's demand for equality. Eyrie's equal proposal is accepted by AI Erie. The core defensive pact also has no random AI refusal, but still needs compatible factions and an explicit recipient response.

Reopening an armistice or treaty now costs no repeat dispatch fee. Existing response deadlines and cooldowns remain; duplicate or wartime replies still cannot sign. `HSM_VER_negotiation_revision_2` releases the cooldown of one already-failed legacy offer on the next daily maintenance tick, without changing a live offer, signing a treaty or issuing a reward. New offers mark the revision immediately, so recovery cannot be farmed. Each new armistice/treaty also protects its 29-day reply window from old queued deadlines: two deliveries plus two 13-day response windows require at most 28 days; the ordinary deadline is day 30. The Eyrie treaty refusal notice remains available immediately after an actual refusal, not during a new pending window. A save in which the other House no longer exists cannot resume bilateral diplomacy.

Targeted `Verenia:` game-log messages record armistice dispatch, delivery, counteroffer delivery, signature and expiry. Treaty dispatch/signature is also logged. They add no daily log spam and help distinguish refusal from failed event delivery during runtime testing.

Existing `HSM_VER_*_pending/retry` flags remain on ERI as the shared negotiation register, regardless of who sends the proposal. Only one offer of each kind may be active. EYR initiations use EYR-specific delivery/timeout events and actual ERI consent; existing ERI offers continue to go to EYR. Cooldowns exceed event lifetimes and cannot be bypassed by native AVI focuses.

Charter failure is a failure to agree, not automatically one country's fault. EYR's command dispute and ERI's ducal exception are independent suspension causes. Settling one may not excuse the other. Both must be resolved before shared benefits return.

EYR can initiate a defence league. An existing House-led common faction is preserved; a new faction follows the initiator. Neither House may be moved out of a foreign faction. AVI gets its own separate consent event.

## Additional Localisation

Ideas: `HSM_EYR_accountable_muster`, `HSM_EYR_officers_confidence`, `HSM_EYR_civic_scrutiny`, `HSM_EYR_professional_command`, `HSM_EYR_exceptional_requisitions` (+ `_desc`). Research labels: `HSM_EYR_inspection_bonus`, `HSM_EYR_support_bonus`, `HSM_EYR_signals_bonus`, `HSM_EYR_industry_bonus`, `HSM_EYR_reconstruction_bonus`.

Decision category `HSM_EYR_diplomatic_business` and decisions `HSM_EYR_reopen_armistice`, `HSM_EYR_reopen_treaty`, `HSM_EYR_reopen_charter`, `HSM_EYR_invite_avian_again`, `HSM_EYR_withdraw_requisitions`, `HSM_EYR_propose_defence`, each with `_desc`. These are recovery/renewal actions, not a parallel progression tree.

Tooltips `HSM_EYR_armistice_offer_tt`, `HSM_EYR_treaty_offer_tt`, `HSM_EYR_charter_offer_tt`, `HSM_EYR_defence_offer_tt`, `HSM_EYR_requisition_case_tt`, `HSM_EYR_no_unresolved_exception_tt`. Readable flags are required for new `has_country_flag` values shown in visible prerequisites; hidden delivery guards are implementation state.
