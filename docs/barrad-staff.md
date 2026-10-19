# Barrad Staff and Companies

Audit and cosmetic repair, 2026-10-10. Scope: the MTC and Service continuations. No recruitment, traits, advisor slots, costs, technology bonuses, MIO traits or eligibility changes. No generated artwork.

## Installed Sources

Checked against EaW at `C:/shit/Steam/steamapps/workshop/content/394360/1826643372`:

- [BAR characters](C:/shit/Steam/steamapps/workshop/content/394360/1826643372/common/characters/BAR.txt): nine military/theory characters have `GFX_idea_unknown_advisor`; their names already resolve. Multiple high-command roles deliberately belong to the same characters.
- [BAR history](<C:/shit/Steam/steamapps/workshop/content/394360/1826643372/history/countries/BAR - Baard.txt>): recruits these characters and sets `has_custom_advisors`. It does not require an invented replacement officer pool.
- [BAR ideas](C:/shit/Steam/steamapps/workshop/content/394360/1826643372/common/ideas/zzz_BAR_ideas.txt): ten living-designer/industry entries have placeholder pictures; Aelfraed Bealdbeorn already has Barrad-specific artwork. Undead designers are separate entries and remain untouched.
- [BAR MIOs](C:/shit/Steam/steamapps/workshop/content/394360/1826643372/common/military_industrial_organization/organizations/BAR_organization.txt): eight placeholder icons; artillery artwork and all template inclusions/bonuses are retained.
- [MIO exclusions](C:/shit/Steam/steamapps/workshop/content/394360/1826643372/common/scripted_triggers/EAW_MIO_triggers.txt) and [generic templates](C:/shit/Steam/steamapps/workshop/content/394360/1826643372/common/military_industrial_organization/organizations/00_generic_organization.txt): generic templates are not intrinsically defects. No global template names or assets were changed.
- [English names](C:/shit/Steam/steamapps/workshop/content/394360/1826643372/localisation/english/country_BAR_l_english.yml:1901) and [Russian names](C:/shit/Steam/steamapps/workshop/content/394360/1826643372/localisation/russian/country_BAR_l_russian.yml:1903): original names are retained, including exact Russian spellings in native-route fallbacks.
- [Portrait sprites](C:/shit/Steam/steamapps/workshop/content/394360/1826643372/interface/eaw_portraits.gfx) and [Barrad sprites](C:/shit/Steam/steamapps/workshop/content/394360/1826643372/interface/eaw_BAR_stuff.gfx:2548): reused assets, not canonical portraits invented for these officers.

## Changes

Nine existing characters receive distinct, reusable EaW pony officer portraits on the new paths: Leofric Stearcstan, Beorhtsige Sigespere, Ceadda Sigeweald, Godric Hereweald, Wigmund Sunnespere, Stithulf Frostdun, Hrothgar Fiscford, Wilfrith Faegerwell and Cyneweard Stangaet. Their canonical names, roles and attributes stay in the native character file. Five missing high-command localization aliases now resolve to the same existing people, not five additional officers.

For the two expansion routes, existing designer identities are presented as civilian firms or workshops. These company names are **submod fiction**, not claims about EaW canon:

| Existing ID | New-route English name | New-route Russian name |
|---|---|---|
| `bar_tank` | Grenedael Motor Works | Моторные мастерские Грендэл |
| `bar_tank2` | Stearcstan Heavy Engineering | Тяжёлое машиностроение Старкстана |
| `BAR_pen_arty` | Bealdbeorn Artillery Works | Артиллерийские мастерские Болдбьорна |
| `BAR_pen_guns` | Hwitstan Armoury | Оружейные мастерские Хвитстана |
| `BAR_magic_guns` | Weisgriff Arcane Instruments | Магические приборы Вайсгрифф |
| `BAR_pen_industry` | Heahstan Machine Works | Механические мастерские Хэйстана |
| `BAR_pen_refinery` | Dunnstan Chemical Works | Химические мастерские Данстэн |
| `BAR_pen_light_planes` | Osbeorn Aelfstan Aviation | Авиамастерские Осбьорна Эльфстана |
| `BAR_pen_cas` | Eadburg Aircraft Works | Авиамастерские Эдберг |
| `BAR_pen_medium_planes` | Eadgar Aelfstan Design Bureau | Конструкторское бюро Эдгара Эльфстана |
| `BAR_pen_shipyard` | Batwyrhta Boatworks | Судовые мастерские Батвирты |

Names resolve through BAR-scoped scripted localization, so legacy ideas and MIOs agree without modifying shared generic names. Native routes retain their original designer names. Corporate labels do not expose the secret Service.

Ten company pictures and eight MIO icons now use installed, unbranded HOI4 company emblems. These static placeholder-image repairs also appear on native Barrad routes; they do not change eligibility or statistics. Artillery keeps its original EaW portrait. Existing political-advisor images are retained and checked, not replaced merely for being generic or stylistically different. Reused emblems are functional approved-game assets, not bespoke Barrad logos.

## Integration and Compatibility

- `HSM_BAR_staff_new_paths` requires tag/original tag BAR, `HSM_BAR_active`, and either expansion-route flag.
- `HSM_BAR_staff_refresh` is presentation-only. It never recruits or resurrects an absent advisor. It is idempotent and restores the native placeholder portrait on route exit.
- Own `on_startup` and `on_daily_BAR` hooks handle existing campaigns and new entries. No shared-core hook is required. Portraits appear by the next daily tick after choosing a route; an optional direct call to `HSM_BAR_staff_refresh = yes` at entry would make this immediate.
- The two same-path overrides (`zzz_BAR_ideas.txt`, `BAR_organization.txt`) replace the installed files in the virtual filesystem. They do not append duplicate IDs. Regression tests compare their parsed contents to installed EaW, allowing only the specified picture/icon substitutions. A future EaW update that changes these files requires review rather than silently masking the changes.
- Original availability remains authoritative, including the tank designers' `BAR_ambrosius_wants_a_car_id` requirement and undead-advisor restrictions. This patch does not unlock anything early or revive staff killed before the new route.
- No character/history/global-MIO-template overrides, no gameplay/focus/GUI changes, no new resource counters.

## Verification

PowerShell 7.6.5. Commands executed successfully:

| Command | Result |
|---|---|
| `node tools/Test-BarradStaff.cjs --preview` | 14 groups passed; 28 resolved images physically decoded; static contact sheet generated |
| `pwsh -NoProfile -File tools/Test-BarradContent.ps1` | 357 checks passed at this integration snapshot |
| `node tools/Test-BarradNativeContracts.cjs` | 23 scenarios passed |

Staff tests cover both routes, native/foreign negatives, absent characters, repeat calls, exit/reentry, exact balance preservation, definition uniqueness, UTF-8 BOM, EN/RU key parity, original-name fallbacks and physical texture existence/decoding. A first expanded-image test exposed Pillow's unsupported DXGI 87 decoder, not corrupt EaW artwork. The preview utility now explicitly decodes this documented [BGRA8 DDS format](https://learn.microsoft.com/en-us/windows/win32/api/dxgiformat/ne-dxgiformat-dxgi_format); native assets are untouched.

[Inspected contact sheet](C:/Users/laslo/RiderProjects/HoISubmod/art/previews/HSM_BAR_staff_native.png).

**Not verified in a running HOI4 session:** actual advisor-screen refresh timing, legacy designer UI, MIO name formatting, and localized display width. Check a new MTC and Service campaign, plus a native Barrad route, with/without Arms Against Tyranny. Tests establish installed-source and asset compatibility, not a substitute for engine rendering or save-load acceptance.
