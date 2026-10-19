# Collegium Frontiers

Bounded MTC military/diplomatic extension. Eleven shared focuses under one independent root, 28/35 days, occupy x54..64/y0..8. The 2026-10-10 revision changes only this component's runtime files, localization, focused test and this document. IDs, prerequisites, coordinates and existing art are retained; all focus sprites have standard/shine definitions.

## Integration Hooks

In **both** `HSM_BAR_collegium_tree` and `HSM_BAR_collegium_future_tree`, explicitly include:

```text
shared_focus = HSM_BAR_mtc_frontiers
```

The root has no external `prerequisite`; its `available` checks `HSM_BAR_civic_foreign_office` plus institutional access. Descendants remain within this root, avoiding phase leakage. No change to the three existing Collegium governance charters is required.

Institutional dissolution calls the following in BAR scope when frontier focuses or
active defensive-war evidence exist:

```text
HSM_BAR_mtc_frontiers_teardown = yes
```

Immediately after setting `HSM_BAR_ZES_agreement` or `HSM_BAR_OLV_agreement`, the existing acceptance effects now conditionally call this when the corresponding frontier-issued goal exists:

```text
HSM_BAR_mtc_frontiers_maintain = yes
```

This immediately withdraws a still-unused offensive goal issued by this component. Its own `on_daily_BAR` hook also reconciles changed circumstances. Goals not issued here are left alone. Existing paid treaty-renunciation decisions remain the way out; this extension never silently renounces treaties. No extra daily hook is needed.

## Content and Rules

- Civilian authority, supply standardisation and accountable staff work precede the two optional offensive branches. The root opens the existing diplomatic channel and grants **one 50% `recon_tech` research bonus**, even when diplomacy was already open. Supply retains one 50% `support_tech` bonus; staff retains 25 army experience; Wittenland's defensive planning retains one 50% `engineers_tech` bonus.
- Kasa (`ZES`) and Austurland (`OLV`) hearings each immediately grant **one 50% `logistics_tech` research bonus**, then offer a civilian envoy through the existing diplomacy system or acknowledgment without talks. Research no longer depends on declining diplomacy. Reopening the event cannot duplicate the research reward. Envoys recheck access and suppress no-op or unwanted escalation choices during an agreement, pending talks, cooldown or a previously rejected negotiation.
- The two **mandate focuses themselves grant a 180-day `annex_everything` war goal**. There is no separate decision, additional 50-PP fee, approval event or automatic declaration. Both obsolete `*_debate` decisions and their voting helpers are removed. Events `.2` and `.3` retain their IDs but now only report a mandate already granted; clicking them cannot issue or renew goals. AI still does not select these optional offensive mandates.
- Target checks are **literal ZES/OLV scripted triggers**, called only with `yes/no`. No parameter blocks or nested argument forwarding. Both selection and completion recheck alive independent countries, route, homeland access, adjacency, war, treaties, pending talks, factions, pacts, guarantees and friendly opinion (50+ in either direction). The completed hearing is required; an existing goal, still-live goal marker or persistent consumed-mandate marker prevents duplication. The reward does not require its own completing focus to be marked completed yet. The target-validity check used by maintenance does not include the duplicate-goal exclusion, so a newly issued goal does not revoke itself.
- The old label "Southern Deer" obscured the actual target. Installed EaW maps `OLV` to **Austurland / Эйстюрланд**, with `OLV_kingdom` and `OLV_rike` cosmetics named **Hreindýraland / Хрейндираланд**. This is the same country tag, not an `HRE` dependency. OLV titles and descriptions now use `[OLV.GetName]` / `[OLV.GetNameDef]` to match the country displayed by native requirement tooltips. A living country is required for a campaign reward; an extinct country instead follows the guarded native bypass below. These optional branches do not gate Wittenland's branch or the domestic tree.
- Wittenland has no offensive goal. Defensive planning leads to civilian settlement, local councils and a citizenship charter only after a recorded defensive victory. The family scene uses Silver Star only while he is present and alive; it does not assume White Star still rules, is captured, or is even present. Otherwise a civilian-delegation scene is used.
- Local councils unlock real provincial registration **before** the citizenship charter (50 PP, 60 days, compliance >=25, resistance <=35; +10 compliance). The later charter unlocks citizenship only for already registered provinces (100 PP, 120 days, compliance >=60, resistance <=10; adds BAR core). Other states cannot block an owned province. Peace, route, independence, homeland access and ownership/control must remain valid. Reconciliation with remaining Wittenland does not revoke citizenship rights in provinces already awarded to BAR. Cancellation/forced early completion grants nothing; repeated completion cannot stack rewards. Existing foreign cores are retained.
- The decision category now contains only these **14 provincial programmes** and appears after the recorded victory and councils focus. It no longer advertises parliamentary war votes before any integration can be undertaken.

## Once-Only Old-Save Recovery

The existing `HSM_BAR_mtc_frontiers_maintain` hook handles recovery; there is no new on-action, decision or shared-core dependency.

- Each new focus reward first sets `HSM_BAR_mtc_frontiers_ZES_goal_issued` or `HSM_BAR_mtc_frontiers_OLV_goal_issued` permanently, then grants the normal 180-day goal. The marker means the mandate is consumed, not that its war goal remains active. It is never timed or cleared by teardown. Expiry, a treaty, loss of access or route dissolution cannot renew a consumed mandate.
- Before maintenance revokes a goal or teardown clears old flags, `HSM_BAR_mtc_frontiers_record_mandates` adopts any surviving legacy `*_vote` or `*_goal` flag as consumed. A completed mandate with any existing goal against its target is also consumed conservatively. An unrelated existing goal is not claimed as frontier-issued, replaced or removed by this adoption.
- A completed old mandate with no such evidence receives its goal once when the normal `*_can_authorize` conditions pass. It uses the same authorization effect as a newly completed focus, including its passive notice, expiry and revocation rules. There is no PP charge or automatic declaration. Incomplete focuses are not completed by this recovery.
- Pact, agreement, pending talks, friendly opinion, war, subjugation, capitulation, missing homeland access, missing hearing/foreign office and other ordinary invalid conditions postpone recovery without consuming the unused mandate. Each target is handled independently. Extinction is deliberately different, as described below.
- EN/RU labels for the two legacy vote flags are retained because the migration now explicitly checks those flags. Localization validation is not weakened or bypassed.

**Limits of old evidence:** the legacy vote flag lasted 30 days and could be cleared by authorization, refusal or teardown. The old goal marker lasted 180 days and could also be cleared on revocation or teardown. There was no permanent issuance record. If all those clues and the old goal had already disappeared **before upgrading**, a previously used/declined mandate is indistinguishable from a never-used one. Such a save can receive one recovery goal, after which the new permanent marker prevents any further renewal. The fixture explicitly demonstrates this limitation. The migration does not invent missing history; its strict no-renewal guarantee applies to new issues and legacy evidence actually observed after upgrading. An old pending vote is conservatively consumed even if it had not yet been approved.

## Extinct-Target Bypass

When Collegium Barrad has reached frontier staff, its corresponding hearing, or its already-completed mandate, maintenance records an absent `ZES`/`OLV` target as permanently resolved. Both optional focuses have a native `bypass` requiring the Collegium route, completed frontier staff, the persistent consumed marker and an actually absent target. Recording therefore happens **before** bypass is possible; bypass itself has no reward. There may be a daily-maintenance delay before the nodes bypass.

This covers both Barrad's annexation and annexation by another country, without a war goal against the annexer, automatic war, research rewards for skipped hearings or new cores. Owning/occupying only the target's capital while the target still exists is not extinction and does not bypass it. An absent country before this branch has been reached is not prematurely consumed. Other Barrad routes cannot use the bypass.

If the target is later restored, the permanent marker still blocks recovery and new authorization. Even restoration between recording and the engine's bypass evaluation cannot create a goal. This deliberately closes an obsolete campaign instead of reviving it against a newly restored state. Existing focus IDs, positions and normal prerequisites remain unchanged.

## Live Parser Correction

The supplied HOI4 `logs/error.log` records frontier trigger errors at the original lines 82 and 90 (15:20:33): `Invalid trigger '25'`, `Invalid trigger '<'`, then the equivalent errors around `60`. The source used `compliance >= 25/60` and `resistance <= 35/10`. The fixture's general comparison parser accepted them, which failed to detect this native syntax problem.

The actual script now uses:

```text
# Registration: compliance at least 25, resistance at most 35.
NOT = { compliance < 25 }
NOT = { resistance > 35 }
# Citizenship: compliance at least 60, resistance at most 10.
NOT = { compliance < 60 }
NOT = { resistance > 10 }
```

These preserve exact and fractional boundaries without rounding or replacing 25 by 24. Installed EaW itself uses `NOT = { compliance < 40 }` in `common/scripted_effects/EAW_resistance_effect.txt:172`. The focused fixture now rejects inclusive comparison tokens for these native state triggers and checks all owned script ASTs for unsupported compound operators. Existing exact/fractional threshold scenarios remain. This fixes the identified source defect; clearing the historic log or claiming a successful new live-engine load would not be verification, and neither was done.

## Defensive Evidence

1. Native `on_declare_war`, ROOT WIT / FROM BAR, creates a one-day direct-declaration token only for sovereign, non-capitulated MTC Barrad. A historical attack marker is not itself victory or integration permission. Starting ownership of the seven historical WIT states is recorded.
2. Native `on_war_relation_added`, ROOT WIT / FROM BAR, consumes that token and marks the specific conflict as defensive. A proxy entry without it clears transient candidacy. BAR-initiated war also clears candidacy.
3. BAR capitulation or being a losing participant clears candidacy, even if BAR later returns. Temporary occupation of Barrad without capitulation does not.
4. Native `on_peaceconference_started`, ROOT BAR / FROM WIT, marks a winning conference. `on_peaceconference_ended` requires that marker, the defensive conflict marker, continuing sovereign MTC status and no remaining BAR-WIT war. Only then is victory recorded. No delayed victory event grants permissions.
5. At that callback, only newly obtained, owned **and** controlled historical WIT states receive settlement eligibility. Pre-war BAR possessions, non-WIT states, merely occupied enemy territory and third-party awards are excluded. The callback transfers nothing. All transient war markers are consumed; replay cannot regrant eligibility.
6. Peace without this conference chain never becomes victory. Daily maintenance clears stale transient markers outside war; a later direct declaration/proxy relation also resets them. Old campaigns without native evidence are not retroactively credited.

Teardown invalidates running integration and unused goals from this component. Historical attack/victory records, completed civil registration and already granted cores remain permanent results, not an active modifier. All further access requires the live route; dissolution cannot collect a queued reward.

## Verified Native Sources

Paths below are relative to the installed EaW or HOI4 roots, not inferred from a wiki.

- EaW `common/country_tags/00_countries.txt:65-66,93`: ZES, OLV, WIT tags. `map/provinces.bmp`, `map/definition.csv` and `history/states/*` were read to verify actual land adjacency: BAR borders ZES, OLV and WIT (also FRE/GRU).
- EaW `localisation/english/countries_griffonia_l_english.yml:830,846` and matching Russian lines: Kasa/Austurland names. `localisation/english/country_OLV_l_english.yml:1726,1739` and matching Russian lines: the two Hreindyraland cosmetics. `events/Austurland Events.txt:4978,5602` applies `OLV_rike` / `OLV_kingdom`; `history/countries/OLV - OleniaVikings.txt:1` retains capital 412. The focused native suite checks these actual definitions, not a separate invented tag.
- EaW starting WIT-owned/core states: `614-Darnish Highlands.txt`, `615-Kurai.txt`, `616-Come.txt`, `617-With.txt`, `627-Papapap.txt`, `628-Mountain Friends.txt`, `629-Mountain Neighbors.txt`. These seven IDs are the whitelist; no future expanded WIT cores qualify automatically.
- EaW `localisation/english/country_WIT_l_english.yml:1397`, `POLITICS_WHITE_STAR_DESC`; `country_BAR_l_english.yml:27`, `BAR_silver_star_cat_desc`: White Star/Silver Star relationship, estrangement and flight to Barrad. The new postwar scene is an authored continuation, not a claim that it exists in native EaW.
- HOI4 `common/on_actions/00_on_actions.txt:709`: direct declaration target; `:931`: capitulation scopes; `:4911-4914`: war-relation attacker/defender scopes. EaW `common/on_actions/07_nsb_on_actions.txt:282` explicitly orders relation-added after declaration.
- HOI4 `common/on_actions/_documentation.md:26-28`: conference callbacks run for winner/loser pairs. This explicit contract is used instead of the older, imprecise comment above `00_on_actions.txt:5020`.
- EaW `common/technology_tags/00_technology.txt:76-84`: `support_tech`, `engineers_tech`, `recon_tech`, `logistics_tech`. The installed HOI4 `documentation/triggers_documentation.md:2281,7387` documents state-scoped compliance/resistance comparisons. Existing local art registrations and native definitions supply focus icons and their shine variants. No art files or sprite registrations were changed.

## Files and Verification

All runtime files are named `HSM_BAR_mtc_frontiers.txt` under `common/national_focus`, `common/scripted_triggers`, `common/scripted_effects`, `common/on_actions`, `common/decisions`, `common/decisions/categories`, and `events`. EN/RU localization is in `localisation/<language>/HSM_BAR_mtc_frontiers_l_<language>.yml` (**98 matching keys** each, UTF-8 BOM), including readable labels for state/country flags. The only other files are this document and `tools/Test-BarradCollegiumFrontiers.cjs`. The existing frontier `on_actions` file was read but **not changed** in this revision; shared core/civic/diplomacy files, GUI builders and assets were not edited. No commit.

Commands executed against the working repository:

```powershell
node tools/Test-BarradCollegiumFrontiers.cjs
node tools/Test-BarradCollegiumFrontiers.cjs --native
node tools/Test-BarradNativeContracts.cjs
pwsh -NoProfile -File tools/Test-BarradDiplomacy.ps1
pwsh -NoProfile -File tools/Test-BarradLegacyDecisions.ps1
pwsh -NoProfile -File tools/Test-BarradContent.ps1
```

2026-10-10 final recovery/bypass results, PowerShell **7.6.5**: Frontiers **200/0** standalone and **207/0** with installed-source checks; NativeContracts **23/0**; Diplomacy **38/0**; LegacyDecisions **50/0**; Content **365/0** (135 focuses, 179 events, 3845 English keys at invocation). All six commands exited successfully. Other agents were integrating separate content concurrently, so whole-content totals describe this run rather than a frozen repository revision. The earlier mid-edit missing-vote-label observation is resolved by the matching EN/RU legacy labels, not a skipped assertion.

The frontier fixture parses and executes actual scripts, including the existing diplomacy entry called by the envoy. It rejects unknown conditions/effects and argument-block helper calls, checks text/metadata separately, and covers direct focus rewards, absence of voting decisions, late target invalidation, goal revocation without deleting unrelated goals, passive event replay, guaranteed research, actual envoy dispatch, victory ordering, stale/white-peace callbacks, independent provinces, council/charter stage separation, cancellation, exact/fractional thresholds, actual dissolution/acceptance hooks and no premature history permissions. Added recovery tests cover eligible completed saves, every ordinary waiting guard, surviving legacy votes/goals, adoption before teardown, goal expiry/revocation without renewal, independence of the two targets, absent-target consumption before bypass, restoration, non-Collegium exclusion, and erased-history limitations. Native-source checks also verify the country names/cosmetics, adjacency bitmap, supported comparison form and standard/shine art references.

Limits: deterministic fixtures and installed-source checks are not a running HOI4 test. A fresh engine load after the comparison correction, daily recovery and focus-bypass UI refresh, callback ordering around a real multiplayer peace conference, dynamic country-name width and focus selection still need an in-game playtest. Migration does not reconstruct earlier wars or defensive victory from ownership. Only the explicitly bounded mandate recovery above grants a retroactive goal. Existing focus IDs and completed defensive settlement history remain intact.
