# Service Case Progression

Integration contract for the Service route; Collegium research is unchanged.

- Service formation sets `HSM_BAR_service_founded` and `HSM_BAR_region_local_open` after the civilian survey, records and expedition. Foreign regional focuses set `HSM_BAR_region_equus_open`, `HSM_BAR_region_griffonia_open`, `HSM_BAR_region_north_open`, `HSM_BAR_region_riverlands_open`, or `HSM_BAR_region_zebrica_open`.
- Archive evidence uses `HSM_BAR_case_<case>_known`; completed laboratory work uses `HSM_BAR_study_<case>_done`. Founding carries forward the first expedition's rock lead, not a completed investigation. No focus grants a completed study.
- Stable study IDs: `rock`, `titan`, `entity`, `amulet`, `plants`, `reactor`, `crown`, `chalice`, `phylactery`, `darkheart`, `grover`, `rosa`, `herald`, `sombra`, `echo`, `marsh`, `compass`. Existing `plants` is preserved; reactor is an additional conditional study.
- `HSM_BAR_case_review_ready`: rock and echo studied, echo disposition settled (`HSM_BAR_case_echo_closed`).
- `HSM_BAR_containment_knowledge_ready`: rock, entity and echo studied. These support limited wards and containment engineering, not a universal suppression device.
- `HSM_BAR_forensics_knowledge_ready`: containment knowledge plus titan and compass studied.
- `HSM_BAR_suppression_knowledge_ready`: forensics knowledge plus amulet studied. The suppression project additionally requires normalization, completed forensics research, and `HSM_BAR_suppression_authorized` from the laboratory focus. Knowledge never depends on that focus or the suppression project.
- The containment/suppression evidence ladder is obtainable locally without conditional foreign story outcomes. Final land recovery additionally requires openly obtainable riverland marsh samples, not a contingent foreign ruler. Local studies concern records, material behaviour and limited samples; they do not resurrect pentarchs or fabricate operational artefacts.
- Each completed study opens a findings event. Disposition flags are `HSM_BAR_study_<case>_applied` or `HSM_BAR_study_<case>_reserved`, mutually exclusive; the general archive may display them independently from pre-existing field-case closure.
- Echo, marsh and compass are explicitly authored, naturally explained investigations, not claims about EaW canon. Zebrica receives an inconclusive provenance inquiry, not an invented canonical relic.

Research uses one guarded completion effect per case for both native magical-facility projects and no-DLC timed decisions. A failed native completion offers a paid retry once access is restored. Disposition rewards are once-only and require current access when physically applying an object; archived findings remain readable after access is lost.

## Unlocks and Timing

Service formation opens the existing 14-day local survey. Human fieldwork for rock, Titan, entity, amulet, vegetation, echo and compass now uses [document comparison and expedition protocols](barrad-investigations.md): 14-28 days according to the selected method. One method per case may run at once; separate cases may run concurrently. Laboratory study remains a separate paid 60-day GUI assignment, with the existing facility requirement when Gotterdammerung is enabled. The original AI decisions/native projects remain defined. Mandatory study work is not a 17-case sequential counter.

- Equus: Sombra and Dark Heart leads, plus region-specific discovered crown reports.
- Central Griffonia: Grover II and Herald leads, plus region-specific discovered crown reports.
- Northern Griffonia: Rosa, Chalice and phylactery leads.
- Riverlands: openly purchased marsh samples with a scientific explanation.
- Zebrica: an inconclusive caravan provenance inquiry, plus region-specific discovered crown reports.

Foreign leads require an actual native occurrence and a currently located source. A regional focus alone never supplies evidence. Crown rumor flags live on each discovery's origin record and follow its recorded physical site. Human Service assignments use the dedicated Fielddesk with or without La Resistance; native agency operations remain for AI and old callbacks. Targeted callbacks recheck access before granting records, objects or remains.

The additional reactor study requires an actual reactor in state 624. It is optional. The amulet study concerns surviving accounts and boundary observations, not compulsory physical custody of Janosik or his amulet; his possible departure cannot strand the mandatory evidence ladder. Existing local disposition flags do not prevent subsequent study of records and samples.

Zebrica archive contract: `HSM_BAR_case_zebrica_known`, `HSM_BAR_case_zebrica_inconclusive`, `HSM_BAR_case_zebrica_closed`; no `HSM_BAR_study_zebrica_done` or magical-knowledge reward. Plants uses the ordinary study contract. The complete archive therefore has seventeen study dossiers and one inconclusive dossier.

## Rewards and Checks

Study and terminal disposition flags feed `HSM_BAR_refresh_case_outcomes`, an idempotent sum in the single `HSM_BAR_anomalous_research` dynamic spirit. Cases have distinct gains and costs rather than an identical research coupon. Terminal object dispositions take precedence over interim study policy. Access-dependent benefits suspend on access loss, while knowledge and historical choices remain; dissolution removes the spirit. Natural explanations yield practical findings, not magical energy.

`GetHSMBAROutcome_<case>` provides the separate archive Results page for all 17 study cases. It reports exact current modifiers, one-time transactions and suspended/unresolved states. Zebrica has no invented reward. Narrative documents and classification remain separate from these mechanical results.

Regression commands: `node tools/Test-BarradCases.cjs`, `node tools/Test-BarradCaseOutcomes.cjs`, `node tools/Test-BarradResearchOperations.cjs`, `node tools/Test-BarradPhases.cjs`, `pwsh -NoProfile -File tools/Test-BarradAnomalies.ps1`. The case suite walks actual survey/fieldwork/study callbacks from an empty evidence state. The outcome suite checks exact contributions, transaction history, final-policy precedence, access loss, repeat refresh and dissolution for every study. These tests do not run HOI4 or establish in-game project scheduling and GUI behavior.
