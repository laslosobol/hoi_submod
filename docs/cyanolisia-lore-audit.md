# Cyanolisia: Narrative, Localization and Lore Audit

Date: 2026-09-29. Submod snapshot: `1f7eb9df` (descriptor version `0.4.0`).

**Historical snapshot:** the findings and quotations below describe the pre-correction files. The author subsequently authorized corrections. The implementation record at the end distinguishes those changes from the original read-only audit.

## Scope and Evidence

This is an editorial audit, not an authorization to implement corrections. Only this report was created. Gameplay, localization, history, artwork and approval manifests were not changed.

The authority used here is the actual local `EaW/` dependency, not recollection, a wiki, or old screenshots. Its descriptor specifies game compatibility `1.19.*`, but does not identify an EaW release number. Consequently, conclusions apply to this dependency snapshot; they do not certify compatibility with a different Workshop installation.

The review covered the three focus-definition files, national spirits and their consolidation into dynamic modifiers, all 38 submod event definitions, decisions and relevant base-decision overrides, the additive country history, character/adviser setup, manufacturers, and both localization files. There are 350 focus definitions: 209 `HSM_` definitions and 141 retained `CYA_` definitions. Definition counts are not a claim that every legacy focus is visible simultaneously. Both submod localization files contain the same 1,031 keys, with no empty values; all 209 new focus descriptions are present. Presence alone does not establish editorial quality.

Canon was established before evaluating the new narrative. Scripted prerequisites, effects and event calls were then compared with the prose. Existing adult-Grover variants and previously consolidated spirits were checked rather than treated as missing. No game session or save was executed. Conditional findings below are source-demonstrable scenarios, not claims of a reproduced in-game playthrough.

Heraldry received a targeted provenance and visual check: the base CYA, GRI, JER, JAS and democratic MIT flags, and the exported Directorate flag, Asterion Assembly and Western Concord icons. This was not a fresh pixel-by-pixel review of every approved icon. Temporary decoded previews were outside the repository.

### Classification

- **Confirmed contradiction:** mutually incompatible statements/actions in the installed base and submod, without an implemented divergence separating them.
- **Internal inconsistency:** the submod's own chronology, text, prerequisites or effects disagree.
- **Naming/localization problem:** an identifiable naming, translation or editorial problem, not evidence of impossible history.
- **Plausibility concern:** a possible development whose presentation needs stronger causal or cultural grounding.
- **Requires author decision:** more than one coherent interpretation is available; choosing between them changes the intended story.

Priority is editorial: **High** affects a central story or materially misrepresents an outcome; **Medium** affects a regional arc or recurring terminology; **Low** is limited wording/polish. Proposed sentences are editorial drafts, not new canonical facts.

### File Aliases

Every location below resolves through this table. Line numbers refer to the audited snapshot; IDs remain the primary anchors.

| Alias | Exact file |
| --- | --- |
| EN | [mod/HoISubmod/localisation/english/hsm_cyanolisia_l_english.yml](<C:/Users/laslo/RiderProjects/HoISubmod/mod/HoISubmod/localisation/english/hsm_cyanolisia_l_english.yml>) |
| RU | [mod/HoISubmod/localisation/russian/hsm_cyanolisia_l_russian.yml](<C:/Users/laslo/RiderProjects/HoISubmod/mod/HoISubmod/localisation/russian/hsm_cyanolisia_l_russian.yml>) |
| F | [mod/HoISubmod/common/national_focus/CYA.txt](<C:/Users/laslo/RiderProjects/HoISubmod/mod/HoISubmod/common/national_focus/CYA.txt>) |
| DEV | [mod/HoISubmod/common/national_focus/HSM_CYA_development.txt](<C:/Users/laslo/RiderProjects/HoISubmod/mod/HoISubmod/common/national_focus/HSM_CYA_development.txt>) |
| EXP | [mod/HoISubmod/common/national_focus/HSM_CYA_development_expansion.txt](<C:/Users/laslo/RiderProjects/HoISubmod/mod/HoISubmod/common/national_focus/HSM_CYA_development_expansion.txt>) |
| EV | [mod/HoISubmod/events/HSM_Cyanolisia.txt](<C:/Users/laslo/RiderProjects/HoISubmod/mod/HoISubmod/events/HSM_Cyanolisia.txt>) |
| IDEA | [mod/HoISubmod/common/ideas/HSM_CYA_ideas.txt](<C:/Users/laslo/RiderProjects/HoISubmod/mod/HoISubmod/common/ideas/HSM_CYA_ideas.txt>) |
| OA | [mod/HoISubmod/common/on_actions/HSM_CYA_on_actions.txt](<C:/Users/laslo/RiderProjects/HoISubmod/mod/HoISubmod/common/on_actions/HSM_CYA_on_actions.txt>) |
| FX | [mod/HoISubmod/common/scripted_effects/HSM_CYA_scripted_effects.txt](<C:/Users/laslo/RiderProjects/HoISubmod/mod/HoISubmod/common/scripted_effects/HSM_CYA_scripted_effects.txt>) |
| TR | [mod/HoISubmod/common/scripted_triggers/HSM_CYA_scripted_triggers.txt](<C:/Users/laslo/RiderProjects/HoISubmod/mod/HoISubmod/common/scripted_triggers/HSM_CYA_scripted_triggers.txt>) |
| DEC | [mod/HoISubmod/common/decisions/HSM_CYA_decisions.txt](<C:/Users/laslo/RiderProjects/HoISubmod/mod/HoISubmod/common/decisions/HSM_CYA_decisions.txt>) |
| GDEC | [mod/HoISubmod/common/decisions/GRI_decisions.txt](<C:/Users/laslo/RiderProjects/HoISubmod/mod/HoISubmod/common/decisions/GRI_decisions.txt>) |
| CHAR | [mod/HoISubmod/common/characters/HSM_CYA_characters.txt](<C:/Users/laslo/RiderProjects/HoISubmod/mod/HoISubmod/common/characters/HSM_CYA_characters.txt>) |

## Canonical Baseline

These references establish what the installed mod actually says. They are also the supporting source references used by the findings.

| Ref | Established background and exact source |
| --- | --- |
| C1 | Cyanolisia is an imperial colonial county, not a blank frontier. Its lands were taken from the **Kingdom of Asterion**; minotaurs were expelled from lucrative coastal towns, and the total minotaur population outnumbers griffons ten to one. See `CYA_minotaurian_indigenes_desc`, [EaW/localisation/english/country_CYA_l_english.yml:465](<C:/Users/laslo/RiderProjects/HoISubmod/EaW/localisation/english/country_CYA_l_english.yml:465>). Initial rule is neutral, with poverty and an underdeveloped interior: [EaW/history/countries/CYA - Cyanolisia.txt](<C:/Users/laslo/RiderProjects/HoISubmod/EaW/history/countries/CYA - Cyanolisia.txt>). This is not properly summarized as a small indigenous minority. |
| C2 | Taillow Sumpfkiel belongs to the **von Livani** family (written `von Liváni` in the source), whose members were appointed imperial stewards and educated at Bruma. Sumpfkiel is her late husband's surname. She has ruled for three decades; failed reconciliation and assassination attempts hardened her, but she dislikes the authoritarian methods she considers necessary. See `thatcher_birb_desc`, [base CYA EN:631](<C:/Users/laslo/RiderProjects/HoISubmod/EaW/localisation/english/country_CYA_l_english.yml:631>) and [base CYA RU:631](<C:/Users/laslo/RiderProjects/HoISubmod/EaW/localisation/russian/country_CYA_l_russian.yml:631>). A later strategic marriage or renewed accommodation is possible, but is an extension, not established biography. |
| C3 | The capital city is **Thymíaustadt / Таймайштадт**: `VICTORY_POINTS_7342`, [English victory points:333](<C:/Users/laslo/RiderProjects/HoISubmod/EaW/localisation/english/victory_points_l_english.yml:333>) and [Russian:341](<C:/Users/laslo/RiderProjects/HoISubmod/EaW/localisation/russian/victory_points_l_russian.yml:341>). State 671 is **Thymíaushafen / Таймайхафен**, not the same label: [English state names:673](<C:/Users/laslo/RiderProjects/HoISubmod/EaW/localisation/english/state_names_l_english.yml:673>) and [Russian:673](<C:/Users/laslo/RiderProjects/HoISubmod/EaW/localisation/russian/state_names_l_russian.yml:673>). The old ID `CYA_direct_rule_from_evosmoshafen` displays “Direct Rule from Thymíaustadt” ([base CYA EN:458](<C:/Users/laslo/RiderProjects/HoISubmod/EaW/localisation/english/country_CYA_l_english.yml:458>)). The conference with an `evosmoshafen` ID actually meets in **Salmarkt**, `cyan.15.d` ([base CYA EN:688](<C:/Users/laslo/RiderProjects/HoISubmod/EaW/localisation/english/country_CYA_l_english.yml:688>)). Technical IDs are not reliable current place names. |
| C4 | Dawnclaw was born in Griffenheim in 965, raised by the Arcturian priesthood, educated at Vinnin and promoted to **Oberstleutnant** in 1004. His biography stresses analytical ability, attraction to violence and ambition: `GRI_ferdinand_desc`, [EaW/localisation/english/country_GRI_l_english.yml:1405](<C:/Users/laslo/RiderProjects/HoISubmod/EaW/localisation/english/country_GRI_l_english.yml:1405>). The failed coup leads to a public hanging, not an escape: `imperial.99.d`, [same file:246](<C:/Users/laslo/RiderProjects/HoISubmod/EaW/localisation/english/country_GRI_l_english.yml:246>); `imperial.73` schedules that event three days after the crushed revolt, and `imperial.99` retires his base character: [EaW/events/GriffonianEmpire Events.txt:2010](<C:/Users/laslo/RiderProjects/HoISubmod/EaW/events/GriffonianEmpire Events.txt:2010>) and [3121](<C:/Users/laslo/RiderProjects/HoISubmod/EaW/events/GriffonianEmpire Events.txt:3121>). Base narration also sometimes calls him a general, so that casual label alone is not a reliable contradiction. |
| C5 | Grover VI was born **21 May 1003**. The default adult biography says he was crowned at eighteen immediately upon coming of age: `grover_vi_desc`, [base GRI EN:1400](<C:/Users/laslo/RiderProjects/HoISubmod/EaW/localisation/english/country_GRI_l_english.yml:1400>). Other guardianships are supported: Bronzehill has its own regency, upbringing and post-coronation events in [EaW/events/Bronzehill.txt](<C:/Users/laslo/RiderProjects/HoISubmod/EaW/events/Bronzehill.txt>), including `bronzehill_grover_coronation.1` at 8950. Its coronation check uses `date > 1021.5.21`, possession of Grover and a control check: [EaW/common/on_actions/eaw_BRZ_on_actions.txt:692](<C:/Users/laslo/RiderProjects/HoISubmod/EaW/common/on_actions/eaw_BRZ_on_actions.txt:692>). This supports alternative guardians, not an obligation to copy their exact plot. |
| C6 | Asterion's current republican culture and anti-imperial cause are explicit: `MIT_democratic_victory_desc`, `MIT_end_martial_law_desc`, `MIT_divided_society_desc`, `MIT_neveragain_desc`, [EaW/localisation/english/country_MIT_l_english.yml:166](<C:/Users/laslo/RiderProjects/HoISubmod/EaW/localisation/english/country_MIT_l_english.yml:166>), 173, 360, 366. It also has alternative political outcomes. Aster's Landing is its capital; Kyanoia is its lost mainland. These sources do not establish an “old mainland republic” before the imperial conquest. |
| C7 | Sicameon's parishes and decentralized militia institutions are genuine, not invented medieval decoration: `SIC_army_reform_category_desc`, [EaW/localisation/english/country_SIC_l_english.yml:1876](<C:/Users/laslo/RiderProjects/HoISubmod/EaW/localisation/english/country_SIC_l_english.yml:1876>). The source specifies the Federal Charter of 773 and later amendments. Midoria is the capital; corsair politics are also part of its actual content. |
| C8 | Kaiv's Rada, elected hetmanate and Cossack traditions are genuine. The historical regional name is **Zaphzia**, not “the Zaphz”: `GRY_the_kingdom_question_desc`, `GRY_a_crowned_hetman_desc`, `gryphianhost.140.d`, [EaW/localisation/english/country_GRY_l_english.yml:186](<C:/Users/laslo/RiderProjects/HoISubmod/EaW/localisation/english/country_GRY_l_english.yml:186>), 188, 547. The installed Russian-language file deliberately contains Ukrainian-colored Gryphian text, including **Зафія / зафійці**: [EaW/localisation/russian/country_GRY_l_russian.yml:186](<C:/Users/laslo/RiderProjects/HoISubmod/EaW/localisation/russian/country_GRY_l_russian.yml:186>). Do not flatten that cultural voice into a generic imperial register. |
| C9 | Gryphus has free towns, the **Order of Opinicus** founded under Grover II, and the **Gryphus Southern Continent Company**, whose imperial charter dates to 874. See `GRU_the_riaporto_congress_desc`, `GRU_knightly_orders_desc`, `GRU_southcont_company_desc`, [EaW/localisation/english/country_GRU_l_english.yml:6](<C:/Users/laslo/RiderProjects/HoISubmod/EaW/localisation/english/country_GRU_l_english.yml:6>), 358, 364. Established Russian names are **Военный орден Опиника** and **Грифусская Компания Южного Континента**, [Russian GRU:357](<C:/Users/laslo/RiderProjects/HoISubmod/EaW/localisation/russian/country_GRU_l_russian.yml:357>) and 363. Renewing its charter is a particularly well-grounded creative extension. |
| C10 | **Blackhollow** is the county/polity; **Blackrock** is the female bandit ruler, not an interchangeable place name. See `BAN_civilize_blackhollow` and the Cyrille/Blackrock restoration material in [EaW/localisation/english/country_BAN_l_english.yml](<C:/Users/laslo/RiderProjects/HoISubmod/EaW/localisation/english/country_BAN_l_english.yml>), especially 56 and 78; `MIT_operation_aegis_desc` explicitly distinguishes Blackrock from Blackhollow ([MIT EN:202](<C:/Users/laslo/RiderProjects/HoISubmod/EaW/localisation/english/country_MIT_l_english.yml:202>)). |
| C11 | Imperial succession by a new conquering country is supported by `form_griffon_empire`, [EaW/common/decisions/griffon_decisions.txt:2](<C:/Users/laslo/RiderProjects/HoISubmod/EaW/common/decisions/griffon_decisions.txt:2>). It requires ownership of state 382 and handles capital, cosmetic identity and imperial cores. **382 is Griffenheim; 389 is Griffonstone**: [English state names:384](<C:/Users/laslo/RiderProjects/HoISubmod/EaW/localisation/english/state_names_l_english.yml:384>) and 391. A misleading comment elsewhere is not evidence that these are reversed. Base `release_RIV` and related mandates are in [EaW/common/decisions/GRI_decisions.txt](<C:/Users/laslo/RiderProjects/HoISubmod/EaW/common/decisions/GRI_decisions.txt>); the submod extends eligibility in GDEC. |
| C12 | **Löwenstein** supplies cars/trucks; **Reichswaffen** is an umbrella organization of arms manufacturers. See `GRI_lowstein_motorized_contract_desc`, `GRI_crona_industry_desc`, and designer names `lionstone` / `imperial_arms_co`, [base GRI EN:915](<C:/Users/laslo/RiderProjects/HoISubmod/EaW/localisation/english/country_GRI_l_english.yml:915>), 827, 1570, 1568. A team of expatriate engineers is a plausible extension; an entire firm defecting is not established canon. |

## Findings: Chronology and Political Continuity

### A01. The failed coup can both kill Dawnclaw and deliver him alive

**Confirmed contradiction | High**

**Location/current wording:** EN/RU:3, `hsm_cyanolisia.1.d`: “The purge in Griffenheim has scattered officers and informants ... identify him as Ferdinand Dawnclaw”; “Чистка в Грифенхейме ... бумаги под его плащом выдают Фердинанда Донкло.” EV:3 implements the arrival. OA's asylum scheduler accepts `GRI_industry_modern` or several CYA focuses; CHAR defines the separate `HSM_CYA_ferdinand_dawnclaw`. The additive [history file](<C:/Users/laslo/RiderProjects/HoISubmod/mod/HoISubmod/history/countries/CYA - HSM Dawnclaw.txt>) recruits that separate character.

**Explanation/source:** C4 explicitly executes and retires `GRI_ferdinand_dawnclaw`. No inspected override interrupts `imperial.73 -> imperial.99`; the custom `HSM_GRI_dawnclaw_hidden_in_cyanolisia` flag is set by EV but has no base-event consumer in the inspected dependency. The submod checks that Dawnclaw is not ruling GRI, which does not distinguish an exile from an executed prisoner. Conversely, a CYA focus can satisfy the scheduler without the imperial purge having occurred, although arrival prose treats the purge as fact.

**Proposed correction:** Preserve the escape premise, but establish one explicit alternate-history departure: a failed arrest/escape variant of the purge, with the imperial execution outcome excluded for that variant and a shared fact recording his fate. Gate the purge-specific arrival text on that fact, or write a distinct pre-purge defection introduction. A mere change from “purge” to “trouble” cannot reconcile the later base execution. Do not erase the escape route because it differs from canon; reconcile the two event histories.

### A02. The socialist opening has no political bridge to the Countess's household route

**Requires author decision | High**

**Location/current wording:** F:5955, `CYA_the_group_of_twenty`, calls base `cyan.5`; OA also uses that focus to schedule asylum. EV:3/EN-RU:4 offer “Hide him as the Countess' assistant” / “Спрятать его как помощника графини.” Subsequent `hsm_cyanolisia.2` and `.3` speak exclusively through the Countess's court and marriage.

**Explanation/source:** Base `cyan.5.d` explicitly organizes the Countess's overthrow ([CYA EN:653](<C:/Users/laslo/RiderProjects/HoISubmod/EaW/localisation/english/country_CYA_l_english.yml:653>)); `CYA_the_officers_putsch_desc` and `cyan.10` describe/implement removing her regime ([CYA EN:152](<C:/Users/laslo/RiderProjects/HoISubmod/EaW/localisation/english/country_CYA_l_english.yml:152>), [EaW/events/Cyanolisia Events.txt:394](<C:/Users/laslo/RiderProjects/HoISubmod/EaW/events/Cyanolisia Events.txt:394>)). Selecting the conspiratorial opening does not itself depose her, so this is not proof of a dead or exiled Countess in every run. The missing element is what the socialist initiative becomes when the household plot takes over; arrival also lacks a government/leadership-specific narrative.

**Proposed correction:** Keep access from the communist and military openings, as intended. Decide whether the conspiracy is exposed, splits over Dawnclaw, infiltrates the court, or survives beside it. Give the transition one explicit paragraph. For a genuinely post-revolutionary arrival, distinguish the Countess's private/exiled household from the government, and require a narrated restoration before she again exercises public sovereign authority. Do not silently retcon the player's previous political choice.

### A03. Regency and Grover's “return” are asserted before custody is established

**Internal inconsistency | High**

**Location/current wording:** EN/RU:221, `HSM_CYA_countess_border_modernisation_desc`: “The Countess' regency begins ...” / “Регентство графини начинается ...”; EN/RU:239, `HSM_CYA_regency_prepares_for_herzland_desc`: “carry Grover VI back to Griffenheim” / “вернуть Гровера VI в Грифенхейм.” Relevant F IDs begin at 1610 and 2507. These descriptions also do not adapt to `GRI_grover_vi_dead` or an already ruling Grover.

**Explanation/source:** C1-C2 establish a countess/governor, not an existing imperial regent. In this branch, Grover's transfer/ward spirit is handled later by `HSM_CYA_restore_imperial_courts` and `HSM_CYA_countess_regency_for_grover` (F:2705, 2756), after the imperial capital campaign. The text supplies neither a prior departure from Griffenheim nor prior Cyanolisian custody. Calling an announced rival claim a “regency” is possible, but must be introduced as a claim rather than an already recognized office.

**Proposed correction:** Early modernization: “The Countess begins preparing the county for responsibilities beyond its coast” / “Графиня готовит графство к задачам за пределами побережья.” Offensive: “Secure Griffenheim and preserve the imperial succession” / “Взять под защиту Грифенхейм и сохранить имперскую преемственность.” Introduce her regency claim explicitly, then use ward, adult-restoration and bereaved versions when those facts diverge. Preserve her refusal to take the crown for herself.

### A04. Grover's custody is global, but the story assumes local physical possession

**Internal inconsistency | High**

**Location/current wording:** EN/RU:668, `hsm_cyanolisia.34.d`: “The Countess has brought him beneath her protection” / “Графиня уже взяла его под защиту”; EN/RU:271, `HSM_CYA_execute_the_child_emperor_desc`: “Dawnclaw can end Grover's claim with a single order.” F:2705, 2756, 4725 and EV `.40`, `.42`, `.43` transfer the character from `every_possible_country`; F:4881 retires him globally.

**Explanation/source:** These operations locate whichever country has `GRI_emperor_grover_vi`, not necessarily the defeated holder of Griffenheim, a subject, or a consenting host. C5 establishes other legitimate guardianship routes. Capturing the capital therefore does not by itself explain obtaining a prince sheltered elsewhere, removing an independent country's reigning emperor, or executing him abroad. This is a missing custody/transfer story, not an objection to the restoration ending.

**Proposed correction:** Establish how he arrives: recovered from the defeated court, surrendered under a settlement, returned by a friendly guardian, or captured in a specific operation. Condition the local scenes on that outcome. An adult restored from abroad needs a negotiated return/abdication account; a remote assassination needs an assassination narrative and conditions, not the text of a local execution. Keep the existing distinction between puppet coronation and real transfer of government.

### A05. Childhood, adulthood and prior reign are treated as one state

**Internal inconsistency | High**

**Location/current wording:** EN/RU:668, `hsm_cyanolisia.34.d`, says he must grow into a ruler; EN/RU:681, `.37.d`, calls him a child and lists school routines. F:2470 (`HSM_CYA_princely_lesson_books`) and F:4511 (`HSM_CYA_grover_black_files`) exclude prior reign but have no age deadline. EV `.40` and `.43` assign base `grover_vi_desc`, whose current wording includes “ascended to the throne at the age of 18” and “as soon as he came of age.” EN/RU:401, `HSM_CYA_grover_reigned_elsewhere`, says “in another country.”

**Explanation/source:** C5 fixes his eighteenth birthday. An uncrowned twenty-year-old is not a child merely because he never ruled elsewhere. The submod can deliberately delay accession until continental unification, so the default age-eighteen biography can then become false. The adult-return descriptions at EN/RU:872-874 are already present and appropriate for former rulers, but do not solve delayed first accession. Additionally, TR:76 checks any country's reigning Grover, including ROOT; OA:15 sets the “elsewhere” flag from it, potentially labeling his own first local reign as a foreign one.

**Proposed correction:** Distinguish age, custody and prior foreign reign in the narrative conditions. Retain the adult-return variants. Recast late lessons as political briefings or constitutional discussions, and late intelligence files as dossiers on an adult claimant. Use a route-appropriate biography that preserves birth date without inventing an exact coronation age. Correct the “elsewhere” condition or its displayed meaning. Delayed coronation is a legitimate alternate history; the inaccurate biography is the defect.

### A06. The Countess hands over power, then legislates an apparently continuing regency

**Internal inconsistency | High**

**Location/current wording:** `hsm_cyanolisia.40.d`, EN/RU:717, says the Countess “gives up the authority she could have kept”; `.40.adult.d` at 872 releases the army from its oath to her regency. `HSM_CYA_regency_constitution_desc`, EN/RU:323, then promises to define “the regency's emergency powers” / “чрезвычайные полномочия регентства.” F:3297 requires `HSM_CYA_crown_in_trust`; EV:766 has already promoted Grover.

**Explanation/source:** The effect and coronation story agree that Grover now governs. The next focus sounds like the creation or perpetuation of the outgoing sovereign office. `HSM_CYA_grover_first_council_desc` (EN/RU:859) likewise repeats a transfer of emergency authority. Administrative handover can take time, and a law for future minorities is sensible, but neither distinction is currently stated. C5 provides a clear regency/post-coronation division, not a requirement for a particular constitution.

**Proposed correction:** Prefer “The Imperial Settlement” / “Основные законы Империи”: delimit the emperor's government, provincial rights, accountability for inherited emergency offices, and rules for any *future* regency. Have the first council implement that settlement, not transfer the same sovereign authority twice. The retained `HSM_CYA_regency_constitution_idea_desc` (349) should follow the same terminology if reused; it is not evidence that this separate legacy spirit is currently awarded.

### A07. A file prepared after Griffenheim falls is sealed “until Griffenheim”

**Internal inconsistency | Medium**

**Location/current wording:** `hsm_cyanolisia.37.c`, EN/RU:684: “Seal it until Griffenheim.” / “Запечатать до Грифенхейма.” EV:741; F:4511, `HSM_CYA_grover_black_files`.

**Explanation/source:** The focus requires the emergency Griffenheim command and purge of the imperial apparatus, and its branch requires declared imperial succession. The supposed future destination has already been reached. This is a leftover from an earlier position in the tree, not a disputed canonical fact.

**Proposed correction:** “Seal it until the succession is settled.” / “Запечатать до решения вопроса о престолонаследии.” Preserve the neutral/deferred preparation choice and its existing meaning.

### A08. Choosing administration actually leaves its opening dependent on an unannounced death

**Internal inconsistency | Medium**

**Location/current wording:** `hsm_cyanolisia.2.c`, EN/RU:22: “Turn his papers over to an administration.” / “Передать его бумаги администрации.” EV `.2` sets `HSM_CYA_path_imperial_administration`. F:1207, `HSM_CYA_install_imperial_cabinet`, is visible only with `HSM_CYA_dawnclaw_dead`. `hsm_cyanolisia.12.d`, EN/RU:40, begins “Dawnclaw's death has left the court ...”.

**Explanation/source:** The choice does not itself kill or surrender Dawnclaw, and the player can keep paying to protect him. The resulting political promise and actual route entry are different. Event `.12` does not incorrectly assert death while he is alive, because the focus guards it; the problem is the unexplained interval and dependency.

**Proposed correction:** Decide what the option promises. If it is an accommodation route contingent on his loss, say so clearly and narrate the provisional administration. If it is a conscious handover, make the fate of the guest explicit in the scene. Avoid a neutral paperwork option that covertly requires allowing a later assassination. This needs a narrative/route decision before any script change.

### A09. A defunct imperial government can still be narrated as the cabinet's active patron

**Internal inconsistency | Medium**

**Location/current wording:** `.10.d`, EN/RU:33: “Someone in Griffenheim has decided ...”; `.12.d`, EN/RU:40: “Griffenheim has moved quickly. Advisers arrive under diplomatic seals ...”. DEC's hiding mission, OA's exposure loop, EV `.10` and F `HSM_CYA_install_imperial_cabinet` do not require an extant GRI government at resolution. Later descriptions `HSM_CYA_rationalise_proxy_quotas_desc` (100) and `HSM_CYA_gri_proxy_rule_desc` (182) continue the same relationship.

**Explanation/source:** GRI must exist at asylum, not throughout this later chain. Another country can destroy it in the meantime. C11 explicitly permits replacement imperial claimants. Surviving secret-service cells are plausible; fresh official diplomatic direction and factory quotas from the old government are a different claim.

**Proposed correction:** Distinguish surviving loyalist agents from a functioning patron. Resolve the cabinet around an actual surviving imperial claimant, an explicitly stranded mission, or a local emergency administration. For example, “The surviving imperial mission offers its officials to the court” / “Оставшаяся имперская миссия предлагает двору своих чиновников” fits a stranded mission, but should not still promise active GRI market access. The faction-entry decision itself already checks that GRI exists; this criticism concerns the surrounding political story.

### A10. “One Griffonia” can mean that someone else annexed the relevant states

**Internal inconsistency | High**

**Location/current wording:** `HSM_CYA_one_griffonia_under_claw_desc`, EN/RU:313: “now commands a continent” / “теперь повелевает континентом”; `HSM_CYA_one_griffonia_under_the_crown_desc`, 857: “the provinces now answer to one capital.” F:5843 and 3148 follow the circuit focuses. TR:1 and 45 implement `HSM_CYA_western_griffonia_secured` / `HSM_CYA_eastern_griffonia_secured`; their tooltip keys are EN/RU:314-315.

**Explanation/source:** These predicates exclude the continued existence of listed independent countries. They do not establish that ROOT or its subjects own all the land those countries used to possess. An unlisted foreign conqueror can eliminate the listed countries without submitting the continent to Cyanolisia. The tooltip's “destroyed or made our subject” is literally closer to the predicate than the victorious narration is. This affects both paths and the foundation of the final succession story.

**Proposed correction:** Preserve continental unification as the intended achievement. Define it in terms of the relevant territory being within the imperial realm, with the intended treatment of subjects and pony mandates, before asserting continental rule. Do not solve this solely by weakening the ending to “our rivals disappeared.” C11 supports imperial claims and mandates, but does not make third-party conquests Cyanolisian achievements.

### A11. Current political regimes are frozen at their early-game assumptions

**Internal inconsistency | Medium**

**Location/current wording:** `HSM_CYA_prepare_asterion_protectorate_desc`, EN/RU:227: “Minotauria is democratic ... friendly to Sicameon” / “Минотаврия демократична ... дружит с Сикамеоном.” `hsm_cyanolisia.50.dawnclaw.d`, EN/RU:909, presents Aquileia and the principalities seeing “the end of their crowns”; `.50.countess.d` at 908 speaks to their courts. F:1793 and the western campaign focuses do not require those governments to remain in office.

**Explanation/source:** C6 explicitly includes competing Asterionese political factions. Regional campaigns can occur long after regime changes, revolutions or prior conquest. A focus title such as “western crowns” can be historical rhetoric; a narrator describing actual current governments and negotiations should not indiscriminately treat a republic as a royal court. Similar caution applies to the continued authority of Gryphus's company and Kaiv's traditional notables after their own political transformations.

**Proposed correction:** Use durable motives unless a variant is needed: “Asterion's claim to the mainland and its armed forces threaten our coast” / “Притязания Астериона на материк и его вооруженные силы угрожают побережью.” Describe “Aquileian representatives and western governments”; retain old crowns as *claims, symbols or former dynasties*. If restoring a dissolved institution is intended, state that it is being restored, not merely continuing untouched.

### A12. Asterion is promised a protectorate even when the outcome remains direct annexation

**Internal inconsistency | Medium**

**Location/current wording:** `HSM_CYA_countess_integrate_south_desc`, EN/RU:423: “Asterion must remain a dependent protectorate”; `HSM_CYA_dawnclaw_integrate_south_desc`, 445: “Asterion will be held as a puppet protectorate.” F:1919 and 3822 implement these focuses.

**Explanation/source:** The availability tests accept either direct control of state 386 or a subject MIT. Completion adjusts autonomy only if MIT already exists as a subject; it does not establish a protectorate when the player annexed the islands. The earlier puppet war goal supports the intended route, but bypasses also accept owned territory. Consequently the promised institutional outcome is not guaranteed. C6 supplies strong reasons to prefer indirect rule, but not an automatic protectorate.

**Proposed correction:** Either make establishing/preserving the protectorate the explicit settlement, or describe a temporary occupation pending that settlement and expose a separate release step. Do not describe direct occupation as an already existing subject state. This is separate from the pony mandates, whose narrative correctly points to subsequent decisions.

### A13. The new railway history contradicts another description in the same development branch

**Internal inconsistency | Low**

**Location/current wording:** `HSM_CYA_imperial_supply_grid_desc`, EN/RU:966: warehouses and southern railways “were built for rival states” / “строились для враждующих государств.” `HSM_CYA_griffenheim_rail_hub_desc`, 1010, instead says the lines served “a capital that commanded the south” / “столице, которой подчинялся юг.” DEV:450 and EXP:322 are the associated focuses.

**Explanation/source:** C1 and C11 establish the former imperial relationship. Networks could have developed differently after secession, so this need not be an impossible history, but the two descriptions make incompatible unqualified origin claims without identifying a period.

**Proposed correction:** “Imperial collapse left the capital's warehouses and southern railways under rival administrations” / “Распад Империи разделил столичные склады и южные железные дороги между соперничающими властями.” This preserves the useful integration problem without inventing contradictory origins.

## Findings: Motivation and Worldbuilding

### B01. The Countess's minotaur settlement needs a concrete concession, not another registry

**Plausibility concern | High**

**Location/current wording:** `HSM_CYA_countess_minotaur_charter_desc`, EN/RU:225: “controlled autonomy: local councils, registered privileges, and obligations the outback can live with.” F:1695 removes the principal outback/indigenous spirits and replaces their condition with aggregate gains. Compare `HSM_CYA_regularise_minotaur_administration_desc`, 136, which also promises registered councils and predictable offices but produces suppression in F:1249.

**Explanation/source:** C1 describes dispossession, exclusion from towns, a ten-to-one majority and allegiance to Asterion. C2 makes the Countess a disillusioned former conciliator. A limited charter can be credible, but the text does not identify what makes it materially different from the neighboring coercive administration route or why either side now accepts it. Removing the separate spirits is an intentional UI design and need not be reversed.

**Proposed correction:** Name one substantive bargain and its limits, chosen by the author: access to coastal markets, protected village land, enforceable limits on garrison searches, or representation in tax disputes. Show why Taillow now accepts a concession she previously resisted and why particular minotaur councils distrust but use it. Example draft: “The councils will collect an agreed levy; in return, coastal courts must hear their complaints against the governors.” This is proposed new content, not claimed canon. Preserve the distinction between conditional accommodation and Dawnclaw's coercion; no extra stack of spirits or token stability penalties is required.

### B02. Dawnclaw's sincere surrender of power lacks the decisive motivation

**Requires author decision | High**

**Location/current wording:** `HSM_CYA_the_child_may_rule_desc`, EN/RU:275: “finish the conquest in Grover's name and then surrender the throne”; `hsm_cyanolisia.43.d` at 726 acknowledges that Dawnclaw's offices survive, but does not explain his decision. F:4987 leads to the actual handover in EV:910.

**Explanation/source:** C4 and base `imperial.75.d` / `imperial.88.d` establish violent ambition and imperial conquest. Exile can change him; institutions surviving him can serve his interests. Neither makes abdication impossible. The problem is that the central reversal is announced as a policy rather than earned as a character choice. Treating the sincere ending as secretly identical to the puppet ending would also erase the player's meaningful distinction.

**Proposed correction:** Choose his reason: an institutional bargain securing his life's work, exhaustion and recognition of his limits, a genuinely altered belief, or a binding promise made before victory. Plant it during exile or the Grover decision, test it once, and let Grover issue an order Dawnclaw would not have chosen. Preserve the authored genuine-rule outcome and distinguish it from the existing supervised puppet court.

### B03. Concealment, public marriage and visibly exiled manufacturers need one shared cover story

**Plausibility concern | Medium**

**Location/current wording:** `hsm_cyanolisia.2.d`, EN/RU:19, keeps Dawnclaw absent from ledgers; `.3.d` at 24 and `.3.a` at 25 invite court gossip about the marriage. `HSM_CYA_lowenstein_motor_pool`, 10, displays “Lowenstein Exile Motor Pool”; `.1.a` activates the adviser and contractors while concealment decisions remain active. See EV `.1`/`.3`, CHAR, DEC, and [HSM_CYA_dawnclaw_organizations.txt](<C:/Users/laslo/RiderProjects/HoISubmod/mod/HoISubmod/common/military_industrial_organization/organizations/HSM_CYA_dawnclaw_organizations.txt>).

**Explanation/source:** C2 permits remarriage and C12 permits contractor connections. A secret identity can survive a court marriage or foreign engineering team, but the text never says whether he marries under an alias, whether the marriage is sealed, or what the engineers tell customers. The public-facing “Exile” name works against that premise. Player knowledge and in-world knowledge need not be identical; the prose should distinguish them.

**Proposed correction:** State that the marriage uses the cover identity or remains sealed, identify the narrow circle that knows, and give the workshop a commercial cover name. Let exposure concern the discovery of the true identity, not whether everybody somehow missed an openly advertised exile. No requirement to remove the marriage or companies follows from canon.

### B04. The “old mainland republic” is unsupported history, not established Asterionese background

**Plausibility concern | Medium**

**Location/current wording:** `HSM_CYA_asterion_assembly_compact_desc`, EN/RU:518: “Aster's Landing remembers the old mainland republic” / “Астерская Гавань помнит старую материковую республику.” F:1965 and EV `.24` implement the assembly settlement.

**Explanation/source:** C1 names the pre-colonial **Kingdom of Asterion**. C6 supports the present republic, its independence struggle and longing for Kyanoia. Those facts do not establish the particular lost mainland republic asserted here. They also do not prove that no earlier republic could ever have existed, so this is deliberately not classified as a confirmed contradiction.

**Proposed correction:** “Aster's Landing remembers the struggle for independence and the mainland still held by griffons” / “Астерская Гавань помнит борьбу за независимость и материковые земли, оставшиеся под властью грифонов.” If an older republic is important to the author's plan, define its period and relationship to the documented kingdom rather than presenting it as already established lore.

### B05. The heirless ending promises a succession process without defining its endpoint

**Requires author decision | Medium**

**Location/current wording:** `HSM_CYA_countess_succession_council_desc`, EN/RU:865: “until a lawful succession can be settled”; `hsm_cyanolisia.46.d`, 879: “A council will govern in his memory and seek a lawful successor.” Compare `HSM_CYA_heirless_provincial_compact_desc`, 871: representation in an empire “whose dynasty can no longer unite them.” F:3426 and 5179 provide the corresponding institutional endings.

**Explanation/source:** The story correctly distinguishes another country's killing of Grover from Dawnclaw's own execution. Neither C5 nor the inspected submod establishes that every possible dynastic successor has disappeared. A permanent custodial council, an interregnum awaiting a candidate, and a new elective constitution are all coherent but different conclusions. The present ending leaves their constitutional relationship unspecified.

**Proposed correction:** Decide whether this is intentionally an unresolved interregnum or the birth of a lasting council regime. Then close on a concrete rule: who can nominate/recognize a successor, what the provinces consent to, and what the Countess refuses to do. Do not invent a canonical relative or crown her to fill the gap. An explicitly provisional ending is sufficient; an extra gameplay branch is not inherently necessary.

### B06. Regional cultures have distinct names, but too often the same narrative machinery

**Plausibility concern | Medium**

**Location/current wording:** `HSM_CYA_countess_evosmoshafen_ministries_desc` (EN/RU:417) supplies “clerks, ledgers, and a quieter legal face”; `HSM_CYA_frontier_aristocratic_league_desc` (235) binds “landed houses, merchant credit, and loyal officers”; `HSM_CYA_evi_notables_council_desc` (526) collects “useful families, guild clerks, and frontier officers”; `hsm_cyanolisia.32.d` (660) makes pardon another register. Associated F focuses are at 1667, 2109, 2418 and 2137; EV `.32` resolves the last.

**Explanation/source:** These are defensible institutions, not four lore errors. The repeated list of roads, seals, clerks, ledgers and officers makes reforms, occupation and reconciliation sound interchangeable. C7-C9 provide much more differentiated political material: parish military obligations, a contentious elected Rada, an imperial commercial monopoly. The newer development descriptions, such as the spare-part problem in `HSM_CYA_quartermaster_service_desc` (970), are stronger because they explain a concrete obstacle rather than enumerating props.

**Proposed correction:** Keep the administrative theme but give each major regional event one local demand, one identifiable speaker/office, and one consequence acknowledged later. Kaiv should dispute who can reject a levy; Midoria who controls parish militia or harbor law; Gryphus whose charter can override whose court. These are proposed scene directions, not additional canonical events. Reuse the existing choice flags for narrative callbacks where practical. More words alone, new spirit clutter or punitive modifiers would not fix the repetition.

## Findings: Names and Localization

These are grouped by root cause to avoid repeating an issue for every focus, legacy idea and tooltip. A retained legacy idea is identified as such; its existence in IDEA does not prove that a current focus awards it.

### L01. Capital names were reconstructed from obsolete IDs

**Naming/localization problem | High**

**Locations/current wording:**

| EN/RU lines and key | Current EN / RU | Proposed display wording |
| --- | --- | --- |
| 183-184, `HSM_CYA_imperial_cabinet_direct_rule` and `_desc` | “Direct Rule From Tymshadt”; apparatus “answers to Tymshadt” / “Прямое управление из Таймштадта” | “Imperial Supervision in Thymíaustadt” / “Имперский надзор в Таймайштадте”; explain that local offices answer to the imperial patron in Griffenheim, if that is the intended hierarchy. |
| 416, `HSM_CYA_countess_evosmoshafen_ministries` | “Evosmoshafen Ministries” / “Министерства Эвосмошафена” | “Thymíaustadt Ministries” / “Министерства Таймайштадта”. |
| 460, `HSM_CYA_evosmoshafen_ministries` | Same old name in a retained idea | Match the focus terminology if the idea remains documented or is reused. |
| 668, `hsm_cyanolisia.34.d` | “books arrive from Evosmoshafen” / “Из Эвосмошафена привозят учебники” | “from Thymíaustadt” / “из Таймайштадта”. |

**Explanation/source:** C3 directly distinguishes the actual labels from technical IDs, and distinguishes city from harbor/state. Event `.12` says the new cabinet answers to imperial hands, so the present “now answers to [its own local capital]” also fails to communicate what changed. Do not globally rename every occurrence to the harbor name, and do not rename the Salmarkt conference based on its ID. Internal IDs can remain stable.

### L02. Regional names and cultural terminology drift away from their sources

**Naming/localization problem | Medium**

| Exact location/key | Current wording | Explanation, source and proposed correction |
| --- | --- | --- |
| EN/RU:498, `hsm_cyanolisia.21.d` | “holds the Zaphz” / “держит Зафз” | C8 establishes Zaphzia and the installed Ukrainian-colored form Зафія. “Zaphz” is not the documented regional name. Use “rules Zaphzia” in EN. In Russian narration use “властвует над Грифией”, or consciously adopt “Зафия” from the installed regional vocabulary; do not invent a claimed canonical “Зафзия” spelling. |
| RU:521-522, `HSM_CYA_lushland_border_commission` / `_desc`; 531-532, `HSM_CYA_lushland_reprisals` / `_desc`; 597-598 and 605-606, their result flags; 697-698, retained commission idea | “Лашленд” and inflections | Map `STATE_608` is **Люшленд**, [EaW/localisation/russian/state_names_l_russian.yml:610](<C:/Users/laslo/RiderProjects/HoISubmod/EaW/localisation/russian/state_names_l_russian.yml:610>). Normalize this cluster to Люшленд; English Lushland is already correct. |
| RU:534, `HSM_CYA_gryphus_company_audit_desc` | “капитулы Опиникуса”; “Южноконтинентальная компания” | C9 supplies **Орден Опиника** and the established company name. Use “капитулы Ордена Опиника”; identify “Грифусскую компанию Южного континента” once, then use “компания”. The shortened company name is not a different fictional organization, but currently obscures the connection. |
| RU:311, `HSM_CYA_eastern_imperial_circuits_desc` | “стране пагорбовых пони” | In this context use “землям пони холмов”. Compare `FBK_seperate_but_equal_desc` and `FBK_hillpony_dominance`, [EaW/localisation/russian/country_FBK_l_russian.yml:136](<C:/Users/laslo/RiderProjects/HoISubmod/EaW/localisation/russian/country_FBK_l_russian.yml:136>) and 243. This is not a mandate to remove intentional Ukrainian cultural voice from Gryphia. |
| EN/RU:214, `HSM_CYA_blackrock_wasteland_surveys`; 217, `HSM_CYA_restore_frontier_county_desc`; 414, `HSM_CYA_blackrock_autonomy_statute` | “Blackrock Wasteland Surveys” / “пустошей Блэкрока”; “Blackrock Autonomy Statute” | C10 distinguishes Blackhollow from its bandit ruler. Prefer “Survey the Blackhollow Frontier” / “Обследовать пограничье Блэкхоллоу” and “Blackhollow Autonomy Statute” / “Статут автономии Блэкхоллоу”. If the outlaw's name is intentionally an occupation-era nickname, introduce it as such; the current RU inflection also reads as a male proper name. Do not imply that populated bandit-ruled districts were literally empty land. |

The Blackhollow restoration decision in [HSM_CYA_blackhollow_override.txt](<C:/Users/laslo/RiderProjects/HoISubmod/mod/HoISubmod/common/decisions/HSM_CYA_blackhollow_override.txt>) actually uses BAN and a restored county. Its existence is not authorization to remove it during this audit.

### L03. Several institution names translate words rather than functions

**Naming/localization problem | Medium**

| Exact EN/RU location/key | Current wording | Proposed correction and supporting context |
| --- | --- | --- |
| 169, `HSM_CYA_countess_civilian_court` | “Civilian Liaison Court” / “Гражданский двор связи” | “Civilian Oversight at Court” / “Гражданский надзор при дворе”. Its own `_desc` at 170 and F `HSM_CYA_civilian_liaison_offices` describe civilian oversight of security, not a communications court. This is an active early spirit, unlike many consolidated legacy spirits. |
| 45, `HSM_CYA_proxy_rule_trade`; 99, `HSM_CYA_rationalise_proxy_quotas`; 139, `HSM_CYA_consolidate_proxy_cabinet`; 181, `HSM_CYA_gri_proxy_rule`; 191, `HSM_CYA_rationalised_proxy_quotas`; 213, `HSM_CYA_gri_proxy_rule_installed` | “Прокси-торговая администрация”, “прокси-квоты”, “прокси-кабинет”, “Прокси-правление Грифенхейма” | Use “Имперский торговый надзор”, “Согласовать имперские производственные квоты”, “Укрепить поднадзорный кабинет”, “Кабинет под надзором Грифенхейма”; match result/idea forms. English can use “Imperial-Supervised Cabinet” or “Imperial Trade Administration”. EV `.12` and these entries' own descriptions define informal control; DEC permits an independent state to join GRI's faction, so do not promise a formal puppet status that is not applied. |
| 456 and 559, `HSM_CYA_security_polytechnic_cells` / `_idea` | “Security Polytechnic Cells” / “Политехнические ячейки безопасности” | “Supervised Technical Schools” / “Поднадзорные технические училища”. `_desc` at 457 explicitly teaches radio operators, mechanics and engineers under police supervision. “Cells” otherwise implies a clandestine network or compartments, not the described schools. Apply to the retained idea if reused. |
| 410, `HSM_CYA_frontier_war_games` | “Пограничные военные игры” | “Пограничные штабные учения”. `_desc` at 411 describes defensive rehearsal, not public games. English “Frontier War Games” is idiomatic and can stay. |
| 61, `HSM_CYA_reorganise_border_forces` | “Reorganization And Restandardization” / “Реорганизация и рестандартизация” | “Standardise the Border Forces” / “Единые уставы пограничных войск”. F:588 and the description concern practical military organization; the current abstract pair conceals the subject. |
| 737, `HSM_CYA_purge_imperial_remainders` | “Purge Imperial Remainders” / “Чистка имперских остатков” | “Purge the Old Imperial Apparatus” / “Чистка старого имперского аппарата”. F:4776 and `_desc` identify surviving officials/networks, not mathematical remainders or miscellaneous remains. |
| 773, `HSM_CYA_strained_minotaurian_indigenes` | “Strained Minotaur Indigenes” / “Напряженные минотаврийские туземцы” | “Restive Minotaur Communities” / “Недовольство минотаврских общин”. `_desc` at 774 describes hostile, underrepresented communities. The strained relationship is not a bodily condition of the people. This is retained legacy-spirit wording; no fresh award was found in the current route. |

These are editorial judgments supported by each institution's implemented function and its own description. They are not claims that EaW forbids new institutional names.

### L04. Literal sentence translations obscure what characters actually do

**Naming/localization problem | Medium**

| Exact EN/RU location/key | Current wording | Explanation and proposed correction |
| --- | --- | --- |
| 671, `hsm_cyanolisia.34.c` | “Teach him the frontier first.” / “Сначала учить его фронтиру.” | A place/region is not naturally the indirect object of this Russian construction. “Let him learn how the border provinces live.” / “Пусть сначала узнает жизнь пограничных провинций.” EV `.34` and `.40` link this to his frontier education, not a literal academic subject called Frontier. |
| 532, `HSM_CYA_lushland_reprisals_desc` | “make selective examples ... make the survivors explain the roads” / “создаст выборочные примеры ... объяснить дороги” | The intended action is exemplary punishment followed by coerced intelligence. “Dawnclaw will single out suspected rebel supporters for punishment, then force survivors to reveal routes and hiding places.” / “Донкло выберет подозреваемых пособников для показательного наказания, а выживших заставит выдать маршруты и укрытия.” EV `.30` supports repression/intelligence alternatives. This preserves the brutality rather than euphemizing it into incoherence. |
| 502, `hsm_cyanolisia.22.d` | “The estates ... are summoned one by one” / “Поместья ... Их вызывают по одному” | “Estates” shifts between properties and their owners; Russian literally summons buildings. “The landowners are summoned one by one; their accounts are audited and their estates searched.” / “Землевладельцев вызывают по одному, проверяют их счета и обыскивают поместья.” EV `.22` offers suppression or seizure of tax records, so owners, holdings and records should remain distinct. |
| 659-660, `hsm_cyanolisia.32.t` / `.d` | “The Amnesty Tables” / “Столы амнистии”; “реестр, достаточно острый, чтобы резать позже” | The described objects are lists of pardoned people and political leverage, not clearly literal desks. Prefer “The Pardon Registers” / “Списки помилованных”; end with “or retain the pardons as leverage over their recipients” / “или сохранить списки как средство давления на помилованных”. If a scene at amnesty desks is intended, describe those desks and applicants instead. |
| 619 and 680-681, `HSM_CYA_grover_black_files`, `hsm_cyanolisia.37.t` / `.d` | “The Grover Black Files”, “The Grover File” / “Черные файлы Гровера”, “Файл Гровера”, “Сначала файл тонок” | The scene is a paper intelligence dossier; RU reads like a computer file or a file owned by Grover. Prefer “The Grover Dossier” / “Тайное досье на Гровера”; “At first the dossier contains only a few pages” / “Поначалу в досье всего несколько страниц”. This also makes Dawnclaw's clinical viewpoint clearer. |

The language proposals above are grounded in EV `.22`, `.30`, `.32`, `.34`, `.37` and their paired EN/RU text. No external historical claim is needed to identify these calques.

### L05. Constitutional “trust” becomes emotional trust, and other political abstractions become opaque

**Naming/localization problem | Medium**

**Locations/current wording and corrections:**

- `hsm_cyanolisia.46.a`, EN/RU:880: “The trust outlives its heir.” / “Доверие пережило наследника.” In `.46.d` the Countess is custodian of an entrusted crown, not describing a feeling. Prefer “Our duty did not die with him.” / “Наш долг не умер вместе с наследником.” Alternatively use “доверенная нам власть” if the legal custodianship must remain explicit.
- `HSM_CYA_heirless_provincial_compact`, EN/RU:870: “The Heirless Provincial Compact” / “Соглашение провинций без наследника.” Russian attaches heirlessness to the provinces. Prefer “The Interregnum Compact” / “Провинциальное соглашение о междуцарствии”; `_desc` at 871 and F:5179 establish the intended succession context.
- `HSM_CYA_reconciled_imperial_oaths`, EN/RU:292, and retained `_idea` at 388: “Reconciled Imperial Oaths” / “Примиренные имперские клятвы.” The factions are reconciled through an oath; the oaths themselves are not. Prefer “A Common Oath to the Emperor” / “Общая присяга императору”; `_desc` at 293 and 389 describe that arrangement.
- `HSM_CYA_regency_constitution_desc`, RU:323: “наследование императора” literally makes the emperor the inherited object. Prefer “порядок престолонаследия”. Its broader post-coronation institutional problem is A06, not a second finding here.

**Supporting source:** EV `.46`, F `HSM_CYA_heirless_provincial_compact` / `HSM_CYA_reconciled_imperial_oaths`, and the paired localization entries above establish the intended legal meaning. Whether the interregnum is permanent remains the separate author decision in B05.

### L06. Contractor and autonomy names need small but meaningful English corrections

**Naming/localization problem | Low**

**Locations/current wording:** EN:10-13, `HSM_CYA_lowenstein_motor_pool` / `_desc` and `HSM_CYA_reichswaffen_fieldworks` / `_desc`; EN:487, `HSM_CYA_kaiv_autonomy_promise`: “Promise The Kaiv Autonomy.”

**Explanation/source:** C12 spells the firm **Löwenstein**, while the submod drops the umlaut without using the conventional `oe` transliteration. “Motor Pool” ordinarily names an operating vehicle pool, whereas this is a manufacturer/contractor providing transport. “Fieldworks” strongly suggests fortifications, while the description and [manufacturer definitions](<C:/Users/laslo/RiderProjects/HoISubmod/mod/HoISubmod/common/ideas/HSM_CYA_dawnclaw_manufacturers.txt>) concern support-equipment workshops. None of this disproves a new corporate branch. The autonomy title has an unnecessary definite article.

**Proposed correction:** “Löwenstein Cyanolisian Workshops” / “Цианолизийские мастерские Левенштайна”; “Reichswaffen Support Workshops” / “Мастерские снаряжения «Рейхсваффен»”; “Guarantee Kaiv's Autonomy” / existing “Пообещать автономию Каиву” if the promise is deliberately less binding. Preserve IDs. Keep the expatriate team as an extension of the source firms, not an unexplained transfer of their entire corporate ownership. The secrecy issue is B03.

## What Is Not a Lore Error

- **The basic alternative-history direction is viable.** A Cyanolisian successor empire, a strategic marriage, Taillow becoming Grover's guardian, and Dawnclaw choosing between murder, puppet rule and real restoration can all be authored. The required work is causal transition and consistent outcomes, not forcing the base route back onto the submod.
- **The Countess's intended refusal of the crown is present.** `HSM_CYA_one_griffonia_under_the_crown_desc`, `.40`, `.46` and the succession-council branch support it. Do not replace this with self-coronation as a convenience fix.
- **A puppet coronation is not the same as executive rule.** EV `.42` deliberately leaves the controlling regime in place; `.40` and `.43` actually add/promote Grover's leader role. Earlier screenshots of another implementation are not proof that the current real-restoration event still lacks that effect.
- **Adult restoration and death elsewhere already have text.** `.40.adult.d`, `.42.adult.d`, `.43.adult.d`, `.45` and `.46` should be preserved. A05 concerns a different case: an adult who has never yet reigned.
- **Regional event options now have different effects.** EV `.20`-`.33` distribute distinct industrial, military or legitimacy changes through the choices. `.34` stores education choices with later coronation consequences. They are not simply two empty informational buttons. The remaining weakness is literary specificity and later acknowledgement, not absence of all choice effects.
- **Three dynamic spirits are intentional abstraction.** Their current definitions use occupation-facing `resistance_growth` and `compliance_growth` in [HSM_CYA_dynamic_modifiers.txt](<C:/Users/laslo/RiderProjects/HoISubmod/mod/HoISubmod/common/dynamic_modifiers/HSM_CYA_dynamic_modifiers.txt>), not the earlier occupied-home-country modifiers. Many old idea descriptions remain as definitions/localization after consolidation. Their presence on disk is not proof of current spirit spam or a lore contradiction.
- **Pony mandates are an appropriate distinction.** `HSM_CYA_eastern_imperial_circuits_desc` (EN/RU:311), `.48`, and `.49` describe dependent administrations rather than automatic core integration. GDEC's `release_RIV` continues the base decision mechanism, with explicit CYA eligibility extensions. Extending those institutions to an alternative imperial regime is an intentional political choice, not automatically a canonical mistake.
- **Regional heraldry is allowed to be regional.** The inspected Western Concord export uses an imperial black griffon with orange/cream fields alongside Aquileian gold lilies on burgundy, consistent in identity with `EaW/gfx/flags/GRI_neutrality.tga` and `JER_neutrality.tga`. The base JAS imperial Asterion flag also contains small lilies; democratic MIT instead has a different bull device. A blanket ban on lilies, crosses or all decorative details would be wrong. The new Directorate's exported opaque black/gold/red flag is an authored regime emblem, not required to duplicate CYA's blue cross flag. No specific heraldic contradiction was established in the inspected sample; this is not certification of every image or every regime-specific flag variant.
- **Asterion/Minotauria, griffon religious offices, and human-language idioms need contextual judgment.** Not every alternate name, priestly term, or use of “people” is a lore error. Established multilingual Gryphian and Gryphussian conventions should not be standardized out of existence.

## Editorial Direction and Next Authorization

Address A01 first: the point of divergence supports the entire exile plot. Then agree the political/custody timeline (A02-A06), so prose is not polished around incompatible state transitions. Resolve the protectorate and continental-achievement promises (A10-A12) without reducing the intended scale of the campaign.

The strongest author decisions are why Dawnclaw genuinely yields power, what material concession makes Taillow's minotaur charter credible, and what the heirless settlement means. Existing motives and institutions are sufficient foundations; unsupported ancient history or a new pile of minor modifiers is not needed.

After those decisions, apply a single terminology pass using L01-L06 and revise the corresponding focus, event, idea and tooltip together. Keep mechanical IDs stable unless a separately authorized technical correction requires otherwise. Favor a concrete local grievance and visible political consequence over another list of seals, roads and registries.

This audit does **not** authorize removing the Blackhollow decision, changing focus positions, changing coronation rules, regenerating icons, or implementing any proposed rewrite. Those are separate corrections. Runtime focus visibility, save-specific outcomes and full asset QA remain outside this source-based editorial verification.

## Authorized Implementation: 2026-09-29

The author subsequently requested implementation of the audit proposals. The table records that follow-up, not a claim that the new alternate-history developments are base-mod canon.

| Findings | Implemented correction |
| --- | --- |
| A01 | `imperial.99` explicitly records an escape after the failed coup if Cyanolisia and the Countess are available. Otherwise the vanilla execution remains. Arrival now requires that escape; completing an unrelated Cyanolisian opening no longer creates a fugitive before the coup. The successful imperial coup is unchanged. |
| A02 | Accepting asylum from the socialist opening explicitly abandons the revolutionary programme and restores the Countess's executive authority. Refusal preserves the original route. Guards on queued `cyan.9/.10/.11` prevent an obsolete coup from overwriting this choice. |
| A03 | Early development and Herzland preparations no longer presume an established imperial regency or a child already in Cyanolisian custody. Corresponding legacy spirit descriptions were reconciled. |
| A04 | A shared household-transfer effect accepts a subject or an extinct former host whose original cores are fully owned and controlled by Cyanolisia. It excludes independent foreign holders. Execution and coronation require local custody. Event `.52` explains the transfer; daily reevaluation allows a later conquest to establish custody after the relevant focus. |
| A05 | Foreign reign detection excludes ROOT. Childhood lessons and the childhood dossier require a minor in local custody. Coronations retain separate previous-reign text and add delayed first-accession text. Real rule uses a route-appropriate biography instead of the base age-eighteen biography. The childhood spirit is not retained after majority. |
| A06 | The post-coronation constitution governs the Empire and any future lawful regency; it does not restore Taillow's surrendered powers. Grover's first council exercises authority already transferred. |
| A07 | The dossier is sealed until the succession is settled, not until the already-conquered Griffenheim is reached. |
| A08-A09 | Choosing administration can end asylum without killing Dawnclaw; he leaves office, concealment ends and the administration branch opens. The cabinet event distinguishes a surviving imperial sponsor from an orphaned mission. Assassins can be surviving imperial networks rather than agents of a government that necessarily still exists. |
| A10 | Territorial completion uses the dependency's `original_cores` arrays, restricted to Griffonia. Both ownership and control must belong to Cyanolisia or its subjects; unrelated third-party annexation no longer qualifies. Mandates can satisfy the requirement without pony core integration. |
| A11-A13 | Asterion and Aquileia descriptions use durable territorial and political interests instead of assuming a permanent government. Southern settlement actually releases an annexed Asterion as a puppet at peace, protects pre-owned Cyanolisian homeland states and retains an existing subject. Rail descriptions agree about the imperial network's fragmentation. |
| B01 | The minotaur charter describes protected communal land, coastal market access, mixed courts and negotiated taxes, explaining why it can succeed where earlier conciliation failed. Existing consolidated effects remain; no new minor spirit or arbitrary stability penalty was added. |
| B02 | Genuine restoration rests on Dawnclaw accepting institutions that can outlive him and Grover's right to dismiss his appointees. First-decree and military-statute descriptions distinguish that settlement from puppet rule. |
| B03-B05 | Marriage uses a sealed register; expatriate workshops use civilian commercial partners rather than publicly advertising the exile. Unsupported ancient mainland republican history was removed. The heirless compact is a provisional interregnum with juristic scrutiny and provincial recognition, not an invented relative or Taillow's self-coronation. |
| B06 | Regional events give distinct stakes to estates, the Rada, parish authorities, merchants and municipalities. Event `.53` recalls the actual Kaiv, Midoria and Gryphus choices at Grover's council, with explicit fallbacks if no settlement was recorded. |
| L01-L06 | EN/RU terminology and institutions were reconciled, including Thymiaustadt (with the established accent in localization), Blackhollow, Lushland, Zaphzia/Gryphia, the Order of Opinicus and contractor names. Literal frontier-teaching, road-explaining, summoned-estate and succession phrases were replaced. Mechanical IDs remain stable. |

The two base event files are same-path overrides because the divergence and pending-event guards must replace the actual upstream definitions, not rely on duplicate event-ID load order. All other country-event blocks match the installed reference snapshot. These overrides require an upstream comparison when EaW is updated.

### Verification

PowerShell `7.6.5` on Windows:

| Command | Result |
| --- | --- |
| `pwsh -NoProfile -File tools/Test-CyanolisiaNarrative.ps1 -CompareHead` | 32 passed, 0 failed. Script balance, scoped transfers, chronology guards, event variants, base overrides, localization references/BOM/duplicate keys, regional callbacks and preservation checks. |
| `pwsh -NoProfile -File tools/Test-CyanolisiaIconManifest.ps1` | 49 passed, 0 failed. |
| `pwsh -NoProfile -File tools/Update-CyanolisiaIconManifest.ps1 -Check` | PASS: 350 focuses, all DONE. |
| `pwsh -NoProfile -File tools/Update-CyanolisiaSpiritManifest.ps1 -Check` | PASS: 137 spirit uses, all DONE. |
| `git diff --check` | PASS. |

Only 31 manifest display-name cells changed. Approval hashes, review statuses, artistic notes, images, focus coordinates, graph and costs were preserved. No hash migration or art regeneration was performed.

No HOI4 runtime session was executed. The static suite is not an engine simulator. A new-game smoke test is still needed for the failed/successful GRI coup split, socialist acceptance/refusal, voluntary departure, child/adult/dead Grover, independent versus subject custodians, delayed coronation, regional callbacks and annexed Asterion release. Independent foreign custody intentionally blocks local execution/coronation until the custody condition is met; there is no automatic diplomatic kidnapping.
