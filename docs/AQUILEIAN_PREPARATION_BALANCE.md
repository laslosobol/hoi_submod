# Aquileian preparation: historical balance ledger

Superseded by the user's native-integration redesign on 2026-11-01. The custom
preparation focuses and both custom influence actions described below have been
removed. Native regional decisions are retained; a read-only influence panel and
post-revolution settlements replace the parallel layer. The arithmetic below is
historical evidence, not a description of the current playable system.

Reviewed and accepted 2026-11-01. The two-button settings below supersede the
provisional values and the exhaustive catalog. Main owns runtime implementation;
this ledger records the agreed configuration, not build verification.
**No engine balance validation has been performed.**

## Decision

**Critical mechanical issue found in the reviewed structure: no.**
The installed EaW central interference callbacks transfer **2 support per action,
not 8**. The accepted regional settings use that corrected baseline.

Retain the shared cooldown, immediate paired transfer, clamping and preparation
recheck. Remove the assembly action. Engine execution has not been tested.

## Reviewed and accepted regional settings

Source: [aquileian_influence.py](C:/Users/laslo/RiderProjects/HoISubmod/tools/aquileian_influence.py:16).

| Action | PP | Chosen / opposing | Gate |
| --- | ---: | --- | --- |
| Organise | 35 | +3 / −3 | Chosen support ≤55 |
| Reply | 50 | +5 / −5 | Actual native comparison loses: royal M≤R; revolutionary R<M |

Both actions apply immediately and share one 28-day country cooldown. There is
no assembly/one-shot action. Transfers of 3 and 5 change the margin by 6 and 10.
Royal ties qualify for reply; revolutionary ties do not, because revolution wins
ties at native timeout. Requirements/tooltips must describe losing, not merely
having no lead. Keep the existing preparation-phase checks and clamp both native
support variables to 0–100. No new support counter is introduced.

Latest user specification: shared automatic root plus four 14-day focuses per
chosen path; aggregate +20/−20, 400 rifles, 1,500 manpower and two weak militia.
Do not multiply that aggregate across nodes or permit collecting another path's
complete package.

## Native central baseline

Installed source: C:/shit/Steam/steamapps/workshop/content/394360/1826643372.
All 24 interference callbacks were checked: each transfers **2**, paired.

- [JER_attack_revoloutionary_strongholds](C:/shit/Steam/steamapps/workshop/content/394360/1826643372/common/decisions/JER_decisions.txt:263):
  25 PP, seven active days, 28 re-enable days.
- [aquileia.62](<C:/shit/Steam/steamapps/workshop/content/394360/1826643372/events/Aquileia Events.txt:3621>):
  monarchist +2 / revolutionary −2.
- [aquileia.63](<C:/shit/Steam/steamapps/workshop/content/394360/1826643372/events/Aquileia Events.txt:3661>):
  monarchist +2 / revolutionary −2.

There are two repeaters and one introductory one-shot per camp/region.
A seven-day busy flag is shared across all of that camp's regional actions.

| Comparison | Transfer | Margin swing | PP |
| --- | ---: | ---: | ---: |
| Two repeaters, first 28 days from ready | 4 | 8 | 50 |
| Plus unused introductory action | 6 | 12 | 75 |
| Under a 35-day repeat-cycle assumption, normalized to 28 days | 3.2 | 6.4 | 40 |

The literal seven-day duration and 28-day re-enable fields are verified.
The engine cooldown anchor is untested: the last row is conditional arithmetic,
**4/35, not 16/35**. Event options must be resolved. Native central focus rewards
and regional decisions are additional effects excluded from this comparison.

## Balance arithmetic and limits

Normal costs
11.67 PP per support point versus JER's 12.5; reply costs 10 as a conditional
catch-up concession. Both consume the same cooldown, so they cannot stack.

The focus sequence alone supplies 10 transfer per 28 days for 56 days.
The organising gate prevents this new repeatable from consolidating unchecked
to 100; the losing-only reply remains a catch-up action. Native local actions and
central focus rewards still matter. These are source-arithmetic comparisons,
not validated engine balance or a guarantee of the player's chosen outcome.

## Native regional access

Native regional decisions **work for JER subjects**: original-tag, allegiance,
unlock and preparation gates do not require independence.
See [native categories](C:/shit/Steam/steamapps/workshop/content/394360/1826643372/common/decisions/categories/JER_decision_categories.txt:34).

JRR/JFT have genuine camp-support repeaters. Revolutionary JEB/VIN club repeaters
only redistribute internal faction influence, not monarchist/revolutionary support.
Preserve these native actions and add one bounded namespaced response section;
no native-file override or new support counter is needed.

Validation: source/callback inspection and Python syntax, without builders,
engine launch, UI checks or AI/PP-income simulation. One focused opposing-JER
56-day playtest should record actual timers, spending and both support variables
before any further numerical increase.
