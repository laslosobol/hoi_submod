# Equestria at War: Expanded Stories

HoI4 Equestria at War submod development workspace. Internal paths and script IDs
retain the historical `HoISubmod` / `HSM` prefix.

Current release: **0.6.0**. See [PATCH_NOTES.md](PATCH_NOTES.md) for release history.

In development: **Aquileian Provinces** — Rila, Westkeep, Pridea and Vinovia.
Pre-revolution politics use EaW's original regional decisions and movements.
Each region receives one read-only split bar adapted from Aquileia's influence display.
After the revolution, native allegiances and the surviving movements' influence
lead into provincial settlements and fifteen postwar programmes, choosing between backing
an existing national movement and fighting for leadership of Aquileia. A national
settlement, optional restoration of the native movement, common reconstruction and
peripheral accession extend the campaign. The regional tree contains 265 authored
focuses, including twelve distinct economic, military and civic focuses per path
and four local foundations per region. The 44 copied generic focuses are removed.
The 112 event definitions include 45 new narrative scenes and inert compatibility
events. Central incorporation now gives one direct choice: join the incumbent
government or refuse and immediately fight for national leadership. Matching EN/RU
text uses native effect previews. No new artwork or player resource meters were added.
See [expanded campaign and test notes](docs/AQUILEIAN_POSTWAR_CAMPAIGNS.md).
Use `python -B -X utf8 tools/Test-AquileianRegions.py --eaw EaW` and
`python -B -X utf8 tools/Build-AquileianRegions.py --check` for source validation.
Campaign and transition regressions: `tools/Test-AquileianCampaigns.py` and
`tools/Test-AquileianTransition.py`. Source scenarios do not replace HOI4 playtests.

In development: **Greifwald — Debt to the Crown**. The pragmatic county gains a
Grover guardianship and independent Herzland restoration, a treaty union after
his confirmed death, and a four-focus identity crisis when Trimmel impersonates
Cloudet. The programme adds no continental war goals or player resource meters
and includes 31 new focus icons and 41 national-spirit icons. Native focus art
and portraits are preserved. See the [implementation contract](docs/GREIFWALD_IMPLEMENTATION.md)
and [art register](art/greifwald/README.md).
Use `python tools/Test-Greifwald.py --eaw EaW` for the source scenario suite and
`python tools/Build-Greifwald.py --check` for generated-source consistency.

The playable mod root is:

```text
mod/HoISubmod/
```

Put game content under that folder, then create a local launcher descriptor from:

```text
launcher/HoISubmod.mod.example
```

Copy it to your Hearts of Iron IV user mod directory as `HoISubmod.mod`, update the `path` value to your local `mod/HoISubmod` folder, and enable both `Equestria at War` and this submod in the launcher. Keep EaW above this submod in the playset.

## Layout

```text
mod/HoISubmod/
  descriptor.mod              # packaged mod descriptor, no local path
  common/                     # shared game database files currently used by the submod
  events/                     # event files
  history/                    # country startup hooks
  localisation/english/       # text shown in-game

launcher/
  HoISubmod.mod.example       # local launcher descriptor template

docs/
  STRUCTURE.md                # folder purpose and modding notes
  EAW_UPSTREAM.md             # upstream EaW reference
```

## Notes

- This template declares `Equestria at War` as a dependency in both descriptors.
- Upstream EaW development repo: https://github.com/EaW-Team/equestria_dev
- No `replace_path` entries are included by default. Prefer same-path file overrides or new files first; add `replace_path` only when you intentionally replace a whole loaded directory.
- Localization files should use HoI4's expected encoding for your game version. If text fails to load, check `Documents/Paradox Interactive/Hearts of Iron IV/logs/error.log`.

## Narrative and Focus Validation

Run with PowerShell 7.2+ on Windows, with the reference dependency in `EaW/`:

```powershell
pwsh -NoProfile -File tools/Test-CyanolisiaNarrative.ps1
pwsh -NoProfile -File tools/Test-CyanolisiaFocusFlow.ps1
```

For purely editorial changes, the narrative test also accepts `-CompareHead` to check that focus layout, icons and art approvals are unchanged. Do not use that option for intentional focus-graph changes. The focus-flow suite checks graph references, route layouts and selected progression predicates using deterministic fixtures; neither suite replaces an in-game playthrough.

The same-path event overrides `GriffonianEmpire Events.txt` and `Cyanolisia Events.txt` preserve the reference files except for `imperial.99` and the entry guards of `cyan.9`, `cyan.10`, `cyan.11`. Reconcile them with upstream when updating EaW; do not replace them with duplicate event IDs in a differently named file. See `docs/cyanolisia-lore-audit.md` for the audit and authorized implementation notes.

## Verenia Content

### Country Selection

The fourth **Expanded Stories** tab in EaW's country selector features Cyanolisia, Erie,
Eyrie and Avian. The three native continent tabs and the 1007 scenario are
unchanged. Barrad is not included while its content remains on another branch.
Featured cards use existing leaders, three focus previews, localized narrative
introductions and native-style atlas maps. Their selector status does not make them
gameplay majors.

This requires two same-path overrides: `common/bookmarks/z_scenario_main.txt`
and `interface/frontendgamesetupview.gui`. The only changes to EaW are four cards,
one appended label and its tooltip; do not add a second copy of the scenario.
Reconcile these files after an EaW update with:

```powershell
python tools/Build-CountrySelection.py --check
python tools/Build-CountrySelection.py
python tools/Render-CountrySelectionMaps.py
python tools/Render-CountrySelectionIntro.py
python tools/Test-CountrySelection.py
```

The selector builder, tests and map exporter accept `--eaw`; graphics export
needs Pillow. Templates live in `tools/country-selection/`. Map sources use
the original EaW atlas with separately edited selection highlights and tighter
country-specific framing, not live campaign borders. The exporter packs these
reviewed images beneath EaW's own map template; it no longer redraws flat
political diagrams or uses country tags as labels. Upstream SHA-256 at
integration: bookmark `b25280a5467a9cf54ad39319662b56b18b2ae4b7e86e4af0fef951e1338d9268`,
GUI `2643af9063243d8731cd72c1c66cb5e762a4b0918d3462792221fd7088184085`.
Restart HOI4 to load front-end changes. Verify tab click targets, all four cards,
maps and Russian/English descriptions in-game; automated checks are source-level.

**File priority matters:** Ghosts of Yore also overrides `z_scenario_main.txt`.
Reordering the launcher playset did not resolve the reported conflict: its
featured cards remained visible while only our static tooltip was loaded.
The attempted GoY dependency has been removed at the user's request. EaW is
the only declared dependency. The user confirmed the tab appears without GoY;
compatibility with its selector is deferred, not resolved. No compatibility
patch or automatic enabling/disabling of mods is provided.
`tools/CountrySelectionPlayset.py --user-dir <HOI4-user-folder>` reports all
enabled selector providers and checks explicit dependency relationships. It
does not treat JSON ordering as runtime proof. Its explicit `--apply` mode
backs up launcher settings and synchronizes this mod's name and dependencies,
preserving local-only dependencies, enabled mods, playset order and other
playsets. It never edits Workshop files. Close the game and launcher first.
The updated icon and atlas graphics still need a restart and in-game visual check.

The fourth tooltip uses the original continent-tooltip layout with generated
chronicle artwork and a narrative introduction in English and Russian. The
source is `art/source/HSM_country_selection_intro.png`; its prompt is retained
in `art/country-selection-prompt.txt`. No generated text is baked into the art.

The tab now uses a transparent 78x70 painted chronicle-and-quill icon instead
of a text label. Source: `art/source/HSM_country_selection_icon.png`. The four
map sources are `art/source/HSM_CSS_<TAG>_atlas.png`. Native atlas artwork is by
**Deer (lunar_explorator)**; country-selection development by **Scars and Egil
of the Equestria at War team**. Source links, generation prompts and crop
coordinates are in `art/country-selection-atlas-sources.txt`.

### Campaigns

The Verenia package adds mutually exclusive diplomatic and military campaigns plus independent domestic development for Erie and Eyrie. Diplomatic signing focuses conclude prepared agreements directly with an eligible AI counterpart; human counterparts retain explicit responses. A common institutional campaign now leads to one Verenian state under Erie, Eyrie or Avian, rather than ending at a defensive league. Avian relations occupy a separate ducal branch: Intergigantes permits negotiated accession, while true neutrality opens conquest and postwar integration. Erie and Eyrie also have distinct cultural-identity branches. Avian's constitutional campaign, limited postwar regency/civil compact and separate Zypressen continuation remain distinct. The new [ducal Grover campaign](docs/VERENIA_GROVER.md) replaces Erie's civilian-only Griffenheim import and adds a route-aware regency to Eyrie: temporary Herzland cores, a Verenian Regency identity, and an adult succession restoring independent allied GRI without ceding Verenian homes. Generic Empire succession is disabled for ERI/EYR, and Aquileia formation for ERI/AVI. See [implementation and playtest checklist](docs/VERENIA_IMPLEMENTATION.md), [upstream overrides](docs/VERENIA_UPSTREAM.md), [legacy Erie settlement](docs/VERENIA_IMPERIAL.md), [Avian regency](docs/VERENIA_REGENCY_CONTRACT.md) and [Zypressen continuation](docs/VERENIA_ZYPRESSEN.md). The package includes reviewed generated portraits, company art, focus icons and national-spirit art; source manifests and export hashes are retained under `art/verenia/`.

```powershell
python tools/Test-Verenia.py
python tools/Test-VereniaAvian.py
python tools/Test-VereniaRegency.py
python tools/Test-VereniaZypressen.py
python tools/Test-VereniaForce.py
python tools/Test-VereniaCrisis.py
python tools/Test-VereniaRoutes.py
python tools/Test-VereniaFlags.py
python tools/Test-VereniaAvianRelations.py
python tools/Test-VereniaIdentity.py
python tools/Test-VereniaUnification.py
python tools/Test-VereniaCooperation.py
python tools/Test-VereniaRomance.py
python tools/Test-VereniaWelcome.py
python tools/Test-VereniaFormables.py
python tools/Test-VereniaGrover.py
pwsh -NoProfile -File tools/Test-VereniaImperial.ps1
```

The Python suites accept `--eaw` and `--game` for other installed dependency paths. The imperial suite uses the local installed paths documented in its source. These validate source and selected modeled scenarios; a new-campaign in-game check remains necessary.

The ducal diplomatic campaign also follows Rosaline Erie and Montague Eyrie from their correspondence to a joint constitutional office after peaceful unification. Military settlements and Avian presidencies retain their own rulers. Four institutional projects use the engine's joint-focus mechanism; participating Houses can divide the economic and administrative preparations between them. Final ratification remains a separate decision for each signatory. The couple's three portrait sources, prompts and native exports have a separate reviewed manifest at `art/verenia/romance/portraits.json`; the earlier 632-source art audit remains a historical snapshot of the preceding package.

Erie and Eyrie now have individual opening histories and a shared Verenian campaign guide in EaW's existing welcome window (country and region tabs, English/Russian). Four localization adapters preserve EaW's original dispatch for every other country; the window and its startup/help controls remain native. Their cultural-identity branches also recognise the lawful joint court, including reward execution, without widening the old-duke military eligibility checks. Restart the game to load the new localization and trigger definitions; the identity fix needs no new campaign or state migration.

Erie and Eyrie also have [forceful alternatives with distinct postwar settlements](docs/VERENIA_FORCE_CONTRACT.md): binding district rights or central ducal administration for Erie, civilian demobilisation or continuing military tutelage for Eyrie. Both can continue against Avian through war-goal, settlement and integration focuses. Real agreements block hostile claims; an optional non-aggression accord and a defeated subject's incorporation require separate consent. Territorial integration follows genuine victory and a transition period, cores only Avian's homeland, and adds no numerical meters. Core bilateral diplomacy now advances through explicit guarantees and counteroffers instead of repeated random AI vetoes.

The [Avian crisis and isolation responses](docs/VERENIA_CRISIS_CONTRACT.md) close the regional integration: emergency help, lawful-government support, separate dealings with the victors, civilian border compacts, reactions to elections and Foundation admission, and delayed endings. Native vassalisation remains a consenting alternative and can be proposed again after refusal; shared negotiations recover from lost delivery, and a renewed charter can restore Erie's previously completed union. Content implementation is complete within the agreed scope; runtime playtesting and balance verification are still outstanding.
