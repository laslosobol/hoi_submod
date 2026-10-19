# Barrad Art Batch B

## Scope

Art-only worker: 11 public cover icons and the final 17 internal icons (zebrica through aftermath) from `art/barrad-service-art-brief.md`. No focus, GFX, gameplay, localization or shared manifest edits.

Status: complete. All 28 PNG sources and 28 native-size TGA exports saved and reviewed. Technical validation: 28 passed, 0 failed. In-game sprite integration remains the parent's responsibility.

## Workflow

- Built-in `image_gen.imagegen`, one call per distinct asset, genuine transparent background. No CLI/API fallback.
- Viewed `art/source/HSM_CYA_crown_in_trust.png` for painterly metal/material quality only; no royal subject copied.
- Prompt subjects: the owned entries in `art/barrad-service-art-brief.md`.
- Subject clarifications: liaison uses geometric code marks; trafficking has no real-world religious emblem; rulers uses a schematic beaked griffon profile, not a human portrait; countercult depicts courier routes, not a literal web; remains uses a dry unidentified shard; custody has independent keys; the healing instrument is a brass medical lamp; trial equipment is mechanical/analog.
- Shared prompt: Use case: stylized-concept. Asset type: single Hearts of Iron IV national-focus miniature, not an illustration panel. Create one exquisitely painted dimensional emblem on genuinely transparent alpha background. Materials match a richly hand-painted metal miniature: engraved antique brass, dark iron, ivory paper, restrained muted teal, realistic bevel highlights and detailed wear, crisp bold silhouette readable at 99x86 pixels. Tightly composed centered assembly fills 86% canvas with safe transparent margins, roughly 1.15:1 landscape proportions. No frame, no backdrop, no drop-shadow plane, no people, no hands, no limbs, no animals, no flags, no fleur-de-lis, no coat of arms, no crowns unless subject explicitly requires one. Documents must contain fine ink entries, measured diagrams or rows, not blank sheets; stamps engraved with specified simple motif, not empty holes. No large lettering, caption, watermark or modern logo. Fully rendered painterly HOI4 strategy art, not flat vector, not cartoon. Any geographic chart is schematic, with survey grid and route lines only; never depict Earth continents or recognizable real-world geography. 
- Saved original PNGs under `art/source/HSM_BAR_<suffix>.png`.
- Added prompt constraints during review: no broad background haze; no invented legible calendar years or personal names. The rulers diagram is the deliberate exception to the generic no-animal-figure constraint; it is evidence, not heraldry.
- Exported using `pwsh -NoProfile -File tools/Convert-ToHoi4Tga.ps1 -Source art/source/HSM_BAR_<suffix>.png -Destination mod/HoISubmod/gfx/interface/goals/HSM_BAR_<suffix>.tga -Width 99 -Height 86`.

## Resources

Each suffix below identifies both paths in the workflow above.

| Suffix | Status | Review |
| --- | --- | --- |
| `cover_charter` | Ready: PNG + TGA | Filled charter and compass stamp; clear miniature silhouette. |
| `cover_accounts` | Ready: PNG + TGA | Commercial ledger, weights and coins; no classified markings. |
| `cover_survey` | Ready: PNG + TGA | Survey tripod and populated contour chart. |
| `cover_post` | Ready: PNG + TGA | Telegraph and populated post-horn stamps. |
| `cover_workshop` | Ready: PNG + TGA | Distinct wrench, hammer and engineering drawing. |
| `cover_office` | Ready: PNG + TGA | Plain commercial insignia; repaired globe geography. |
| `cover_warehouse` | Ready: PNG + TGA | Civilian warehouse, crates and delivery notes. |
| `cover_shipping` | Ready: PNG + TGA | Cargo vessel, schedule and corrected navigation grid. |
| `cover_archives` | Ready: PNG + TGA | Three numbered public ledgers; no classified markings. |
| `cover_clinic` | Ready: PNG + TGA | Sterilizer, cloth and stethoscope; no human anatomy. |
| `cover_laboratory` | Ready: PNG + TGA | Microscope, flask and ordinary measuring gauge. |
| `dir_zebrica` | Ready: PNG + TGA | Cargo chest and distinct black specimen case. |
| `dir_liaison` | Ready: PNG + TGA | Two separate sealed contacts and keys; intentionally wide silhouette. |
| `dir_trafficking` | Ready: PNG + TGA | Bronze reliquary and three populated provenance labels. |
| `dir_rulers` | Ready: PNG + TGA | Cracked crown, measuring glass, griffon silhouette; haze removed. |
| `dir_countercult` | Ready: PNG + TGA | Intercepted packet, clock and diverted courier routes. |
| `dir_foreign_protocol` | Ready: PNG + TGA | Two distinct interlocking document locks. |
| `dir_remains` | Ready: PNG + TGA | Dry bone shard and provenance form; invented date/name redacted. |
| `dir_commission` | Ready: PNG + TGA | Three complete dossiers and separate scientific samples. |
| `dir_coexistence` | Ready: PNG + TGA | Protected teal specimen and functioning warm medical lamp. |
| `dir_normalization` | Ready: PNG + TGA | Dark test ring, violet specimen and warning switch. |
| `dir_custody_law` | Ready: PNG + TGA | Two separate keys and two-keyhole authorization lock. |
| `dir_open_report` | Ready: PNG + TGA | Repaired lamp, populated technical diagram and compass seal. |
| `dir_quiet_watch` | Ready: PNG + TGA | Closed dossier, unlit investigator lamp and warm civilian window. |
| `dir_sealed_orders` | Ready: PNG + TGA | Distinct tunnel plans, isolation valve and sealed order. |
| `dir_suppression_lab` | Ready: PNG + TGA | Stone sample, test coil, analog trace and emergency breaker. |
| `dir_activation` | Ready: PNG + TGA | Closed switch, red warning light and fading geometric ward. |
| `dir_aftermath` | Ready: PNG + TGA | Fractured ring, annotated report and mourning ribbon. |

## Corrections

- `cover_shipping`: removed recognizable Earth continents from the decorative navigation plate with a targeted built-in edit; final plate uses a nautical grid.
- `cover_office`: removed Earth-like landmasses from the small decorative globe with a targeted built-in edit; final globe has coordinate lines only.
- Added a no-Earth-geography constraint to subsequent prompts.
- `dir_rulers`: removed the broad brown/gray background haze while preserving the apparatus and griffon diagram.
- `dir_remains`: replaced a generator-invented Earth calendar year and collector name with targeted redactions.
- All four corrections used the built-in image tool, were inspected again and were re-exported. No unresolved blocking defect found in the final review.

## Verification

- PowerShell 7.6.5; every final PNG successfully decoded through System.Drawing, with RGBA PNG headers, full transparent regions, near-opaque content and intermediate alpha. Source dimensions range from 1330 to 1449 pixels wide and 1086 to 1182 pixels high. Generated alpha was preserved, not flattened or keyed.
- Every TGA validated: type 2, 99x86, 32 bits, 8 alpha bits, bottom-left origin, exact 34,074-byte payload. All have transparent pixels and antialiased edges; none has an alpha >=250 pixel on the outermost border.
- An initial exact-alpha-255 density assertion rejected valid near-opaque generated interiors (many pixels use alpha 252/253). Validation was corrected to count alpha >=250 as near-opaque; no image was changed to satisfy the check.
- All 28 sources were visually inspected. Every actual TGA was independently decoded and inspected at native 99x86 on dark and light backgrounds: `docs/barrad-art-batch-b-review.png`. The contact sheet is not a simulation of the game renderer.
- No human hands/anatomy, arbitrary fleur-de-lis, unwanted national heraldry, opaque rectangular backgrounds or visible clipping found. Stamps and documents contain contextual markings.
- Fine micro-lettering and dial numerals remain illustrative texture, not verified localized text; tiny details naturally disappear at 99x86. The liaison icon deliberately has a wider, lower silhouette than the equipment icons.
- Standard/shine sprite registration, focus bindings, dynamic public/internal switching and actual HOI4 rendering were not tested or edited by this art worker. No commit, gameplay edit, shared approval reset or scope expansion.

## Handoff

Parent reviewed the completed native TGA sheet and accepted all 28 as coherent/readable, with no additional corrections requested. Parent separately reported `Test-BarradArt.ps1`: 45 passed, 0 failed; this worker did not rerun that integration test. Final SHA-256 verification confirmed all 56 delivered PNG/TGA files remained unchanged after batch QA. Generation stopped.

