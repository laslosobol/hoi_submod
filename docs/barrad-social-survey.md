# Barrad: the first social survey

## Cause and installed-source evidence

Checked against `C:/shit/Steam/steamapps/workshop/content/394360/1826643372` on 2026-10-10:

- `history/countries/BAR - Baard.txt:146`: the starting idea list includes `pre_industrial_society` and `better_science_base`, but no poverty or literacy tier.
- `common/on_actions/eaw_on_startup_general_on_actions.txt:727`: missing literacy traits receive `no_lack_of_scientists`; the poverty setup at line 738 similarly adds `no_poverty`. The apparent prosperity is an inherited default, not a reward granted by either new entry effect.
- `events/Barrad Events.txt:7383`, event `barrad_ccamb.6`: native Barrad already uses `poverty1` and `lack_of_scientists1`. This is a precedent for the selected tiers, not a claim that its unrelated story event happened on the new routes.
- `common/scripted_effects/EAW_misc_effect.txt:725` and `:790`: native literacy and poverty improvement ladders. Existing reconstruction rewards continue using those helpers.
- `localisation/english/eaw_ideas_l_english.yml:76` and `:87`, and matching Russian keys: the precise displayed tier names below.

## Change

`HSM_BAR_common_reconstruction` remains at `(26, 0)`, takes 28 days and retains its existing 50 political power. Its description now introduces an honest village assessment, followed by a short EN/RU narrative report using the existing EaW school illustration. No invented population percentages or new resource meters are used.

| Native starting default | Survey baseline |
| --- | --- |
| `no_poverty`: Negligible Poverty / Отсутствие бедности | `poverty1`: Severe Poverty / Серьёзная бедность |
| `no_lack_of_scientists`: Negligible Illiteracy / Полная грамотность | `lack_of_scientists1`: Broad Illiteracy / Широкая неграмотность |

The assessment replaces better or missing tiers once. It preserves an existing baseline or worse tier independently for each dimension. It neither improves an already worse situation for free nor makes that situation worse. Industry, the scientific base, research slots and unrelated ideas are untouched.

`HSM_BAR_transition_republic` and `HSM_BAR_collegium_oath` require completion of this focus through `available`, not `prerequisite`. This prevents shared-subtree auto-inclusion and preserves all coordinates. The civic branch already requires the oath; the frontier branch already requires the civic foreign office. Neither needs a redundant new gate or a rewrite.

## Persistence and integration

- `HSM_BAR_social_survey_assess` is called only by the common focus reward. Its durable `HSM_BAR_social_survey_assessed` flag is never cleared during entry, dissolution or tree changes.
- No core-effect or on-action integration is needed. Do not add a startup, entry, daily or refresh call: that could impose the correction after earned development.
- Completing later trees, returning to the route or replaying the assessment cannot overwrite later improvements. The report is presentation-only and gives no additional tier change on dismissal.
- Original EaW paths retain their own history and entry logic. No base-mod file or native Barrad event was changed by this correction.
- No retroactive migration: an old save with the common root already completed keeps its current tiers. An unfinished common root receives the assessment when completed. A fresh campaign is required to experience the intended ordering from the start.

## Files in this change

- New: `common/scripted_effects/HSM_BAR_social_survey.txt`, `events/HSM_BAR_social_survey.txt`, EN/RU `HSM_BAR_social_survey` localization, and `tools/Test-BarradSocialSurvey.cjs`.
- Updated: the common root reward, Republic and Collegium root availability, and the existing common-root description in EN/RU `HSM_BAR_core` localization.
- Updated fixtures: `Test-BarradDevelopment.cjs`, `Test-BarradPhases.cjs`, `Test-BarradCollegium.ps1`. They execute the new survey or explicitly model its completed external boundary; unknown syntax still fails.
- Not edited: core effects/on-actions, Service GUI, operations, advisors, companies, civic/frontier content, art or native history.

Content paths above are relative to `mod/HoISubmod`; test paths are relative to the repository.

## Verification

Windows, PowerShell **7.6.5**. All nine commands passed:

| Exact command | Result |
| --- | --- |
| `node tools/Test-BarradSocialSurvey.cjs` | 113 scenarios, 0 failures |
| `node tools/Test-BarradDevelopment.cjs` | 92 scenarios, 0 failures |
| `node tools/Test-BarradPhases.cjs` | 55 groups, 0 failures |
| `pwsh -NoProfile -File tools/Test-BarradCollegium.ps1` | 5832 assertions, 0 failures |
| `node tools/Test-BarradCivic.cjs --native` | 104 scenarios, 0 failures |
| `node tools/Test-BarradCollegiumFrontiers.cjs --native` | 88 scenarios, 0 failures |
| `pwsh -NoProfile -File tools/Test-BarradContent.ps1` | 357 checks, 0 failures |
| `node tools/Test-BarradNativeContracts.cjs` | 23 scenarios, 0 failures |
| `node tools/Test-BarradMeterRetirement.cjs` | 8 scenarios, 0 failures |

The new suite executes installed startup defaults and native improvement helpers, covers every normal poverty/literacy tier pair and absent tiers on both routes, verifies once-only behavior, forbidden contexts, preserved improvements, all five tree layouts and route-branch isolation, BOM/localization references and the installed event sprite. These are deterministic source tests, not live HOI4 execution. In-game focus selection, delayed event display and save/load acceptance remain untested. No commit was made.
