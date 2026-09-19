# Cyanolisia Dawnclaw Path Skeleton

This submod currently wires the Dawnclaw content through events and decisions to avoid overriding the upstream `CYA.txt` focus tree. Future focus files can call the same flags, events, and ideas listed here.

## Shared Entry

Event entry:

```text
GRI completes GRI_industry_modern / Die Kleine Sauberung
If Dawnclaw does not become GRI leader, CYA gets hsm_cyanolisia.1
Accepting asylum hides the vanilla political branch and unlocks HSM_CYA_hide_the_fugitive / Hide The Fugitive
Completing HSM_CYA_hide_the_fugitive unlocks the first route split
```

Accepting asylum recruits and auto-appoints `HSM_CYA_ferdinand_dawnclaw`.

## Path Structure

The Dawnclaw branch has two main choices after `HSM_CYA_hide_the_fugitive`:

```text
HSM_CYA_frontier_march_plan / Passive-defensive default-adjacent path
HSM_CYA_an_unlikely_marriage / Marriage court power struggle path
```

The marriage path later resolves into one of two dominance outcomes:

```text
Countess dominance
Dawnclaw dominance
```

Imperial Administration is not a main political path. It is the fallback/aftermath state if Dawnclaw is rejected, sidelined, or killed.

## Path 1: Passive-Defensive / Default-Adjacent

Flag:

```text
HSM_CYA_path_frontier_march
```

Design role:

```text
Keep Cyanolisia close to the vanilla/default political direction.
Dawnclaw is useful but contained: a hidden defensive adviser, not a ruler.
The branch focuses on border defense, frontier local identity, and cautious native minotaur settlement.
It should be lower drama and lower exposure than the marriage path.
```

Core content:

```text
HSM_CYA_frontier_march_policy
HSM_CYA_reorganise_border_forces
HSM_CYA_frontier_drill_standards
HSM_CYA_modernise_internal_intelligence
HSM_CYA_frontier_signals_network
HSM_CYA_local_supply_depots
HSM_CYA_fortify_against_minotauria
HSM_CYA_watch_sicameon
HSM_CYA_defensive_victory_claims
HSM_CYA_proclaim_cyanolisian_march
HSM_CYA_form_frontier_march
HSM_CYA_prepare_border_claims
HSM_CYA_integrate_minotaur_outback focus
HSM_CYA_recognise_outback_councils focus
```

Focus skeleton:

```text
Hide The Fugitive
The Frontier March Plan
Reorganization And Restandardization
Frontier Drill Standards
Modernise Internal Intelligence
Frontier Signals Network
Local Supply Depots
Fortify Against Minotauria
Watch Sicameon
Defensive Victory Claims
The Cyanolisian March
Native Minotaur Settlement
Recognise Outback Councils
```

Completing `HSM_CYA_modernise_internal_intelligence` sets:

```text
HSM_CYA_dawnclaw_advisor_role_confirmed
```

This ends the assassination exposure loop for the passive-defensive path because GRI agents can plausibly report that Dawnclaw has become a visible adviser/helper for peripheral modernization rather than an active claimant.

## Path 2: Marriage / Court Power Struggle

Flag:

```text
HSM_CYA_path_marriage
```

Design role:

```text
Dawnclaw is bound to the Countess' court instead of merely hidden inside it.
The branch is about who uses whom: the Countess using Dawnclaw as a dangerous asset, or Dawnclaw turning the household into his instrument.
Exposure rises faster here than in the passive-defensive path.
```

Power variables:

```text
HSM_CYA_dawnclaw_dominance
HSM_CYA_countess_dominance
HSM_CYA_dawnclaw_exposure
```

Dominance flags:

```text
HSM_CYA_dawnclaw_dominant
HSM_CYA_countess_dominant
```

Focus skeleton:

```text
An Unlikely Marriage
Security To The Colonel
The Countess' Civil Cabinet
Palace Security Directorate
Civilian Liaison Offices
Codify The Household Compact
The Hidden Assistant
The Countess Alone
Outback Policing
Field Security Battalions
The Colonel's Household
The Revealed Exile
Outback Integration
Recognise Outback Councils
```

### Countess Dominance

Flag:

```text
HSM_CYA_countess_dominant
```

Design role:

```text
The Countess contains Dawnclaw and keeps his usefulness inside civilian rule.
Lower exposure growth.
More industry, administration, civilian legitimacy, and integrative native minotaur policy.
Dawnclaw remains present but politically dependent on her protection.
Early follow-up focuses upgrade the Countess court idea instead of giving flat PP.
```

### Dawnclaw Dominance

Flag:

```text
HSM_CYA_dawnclaw_dominant
```

Design role:

```text
Dawnclaw dominates court security and war policy.
Higher exposure growth and higher assassination pressure.
More army, policing, internal security, and hardline native minotaur policy.
This path is stronger but unstable: the Empire has a much easier time learning where he is.
Follow-up security focuses upgrade the Dawnclaw and hardline minotaur ideas, but increase exposure.
```

## Fallback: Imperial Administration

Flag:

```text
HSM_CYA_path_imperial_administration
```

This route is used if Dawnclaw is rejected, assassinated, or if the player chooses the low-content administrative fallback. It should be short, bureaucratic, and security-focused.

Focus skeleton:

```text
Seal The Room
Imperial Papers, Cyanolisian Hands
Quiet Administrative Reform
No More Foreign Guests
```

Assassination branch:

```text
HSM_CYA_install_imperial_cabinet
HSM_CYA_regularise_minotaur_administration
HSM_CYA_reopen_military_workshops
HSM_CYA_cabinet_procurement_board
HSM_CYA_consolidate_proxy_cabinet
HSM_CYA_rationalise_proxy_quotas
```

Core ideas:

```text
HSM_CYA_gri_proxy_rule
HSM_CYA_imperial_minotaur_administration
HSM_CYA_imperial_workshop_program
HSM_CYA_cabinet_procurement_board_idea
HSM_CYA_consolidated_imperial_cabinet
HSM_CYA_rationalised_proxy_quotas
```

`HSM_CYA_install_imperial_cabinet` fires `hsm_cyanolisia.12`, describing Griffenheim proxy rule. `HSM_CYA_gri_proxy_rule` represents factory output and military procurement being redirected toward GRI through production penalties, higher consumer-goods pressure, stability, and trade opinion.

General focus reward rule for this branch set:

```text
Use 35-day core focuses (cost = 5) and 28-day incremental focuses (cost = 4) as the baseline.
Prefer practical focuses, idea upgrades, XP/CP trickles, small stability/war-support movement, and policy tradeoffs.
Avoid filler focuses that cost a full 70 days and only give large political power.
```

## Exposure / Assassination Loop

Exposure variable:

```text
HSM_CYA_dawnclaw_exposure
```

Initial value:

```text
Asylum accepted: 1
Advisor role confirmed: 0 and loop stops
```

Weekly growth:

```text
Base passive growth while hidden: +1
Defensive path: no extra growth, only the base +1
Countess/Duchess dominance: base +1 and extra +1
Dawnclaw dominance: base +1 and extra +2
```

Decisions:

```text
HSM_CYA_maintain_dawnclaw_cover
HSM_CYA_counterintelligence_sweep
HSM_CYA_stage_loyalist_raids
HSM_CYA_disappear_compromised_witnesses
```

The cover decisions live in `HSM_CYA_dawnclaw_hiding`, whose category description shows current exposure with `[?Root.HSM_CYA_dawnclaw_exposure|0]`.

Harsh cover decisions are only available in Dawnclaw dominance and reduce exposure more strongly in exchange for stability loss.

Important flags:

```text
HSM_CYA_dawnclaw_identity_secured
HSM_CYA_dawnclaw_revealed_to_empire
HSM_CYA_dawnclaw_dead
```

If exposure rises above 7 or Dawnclaw is revealed, `hsm_cyanolisia.10` fires with only the death outcome. The player must spend political power and/or command power on hiding decisions before agents reach him.
