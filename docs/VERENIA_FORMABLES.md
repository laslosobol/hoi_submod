# Verenia Native Formable Exclusions

Implemented 2026-10-24. ERI and EYR cannot use the native generic Griffonian
Empire successor decision/category. ERI and AVI cannot use the native Aquileia
formation decision/category. These exclusions use `original_tag`, so a cosmetic
identity or a changed current tag does not remove them. They apply independently
of Verenia route flags, government, or the new Grover regency mechanics.

## Owned Files

- `mod/HoISubmod/common/decisions/griffon_decisions.txt`
- `mod/HoISubmod/common/decisions/categories/eaw_formable_categories.txt`
- `tools/Test-VereniaFormables.py`
- `docs/VERENIA_FORMABLES.md`

The two script files are complete same-path overrides of installed EaW. A partial
file would hide other entries from that upstream file. No launcher, descriptor,
native EaW source, Grover mechanic, or other existing mod file is changed here.

## Upstream Baseline

Source: `C:/shit/Steam/steamapps/workshop/content/394360/1826643372`.
The repository's `EaW/` copies matched these installed files byte-for-byte when
the overrides were created.

| Upstream File | SHA-256 |
| --- | --- |
| `common/decisions/griffon_decisions.txt` | `d3235e83a14ce1ddba9a3710e2d395297eabb764f60bc604c85f3198b3078828` |
| `common/decisions/categories/eaw_formable_categories.txt` | `50974fa6b1df366f78eea82eeccb2bd0bb02554b3498f7a8ac1297a859203f77` |

The regression suite compares against the selected upstream directory at runtime.
After an EaW update, review any failure, rebase the complete overrides, and update
the recorded hashes. Do not discard newly added upstream entries.

## Exact Delta

`griffon_decisions.txt` adds ten lines:

- `form_griffon_empire.allowed.NOT` adds `original_tag = ERI` and
  `original_tag = EYR` to the existing exclusions.
- `form_griffon_empire.visible` adds separate `NOT` guards for those two origins.
- `form_aquileia` gains an `allowed` block excluding ERI and AVI, and matching
  guards at the start of its existing `visible` block.

`eaw_formable_categories.txt` adds twelve lines:

- `form_griffon_empire_category.allowed` keeps the native continent predicate
  and adds ERI/EYR exclusions. Its new `visible` block repeats the exclusions.
- `form_aquileia_category.allowed` adds ERI/AVI exclusions alongside the existing
  native candidate list. Its new `visible` block repeats the exclusions.

The category file also receives a final newline. All original lines and parsed
entries are retained. The `allowed` guards enforce eligibility, and the `visible`
guards independently hide the entries even when prior eligibility is assumed.
Availability, costs, rewards, AI weights, and country-specific Empire decisions
remain exactly upstream.

## Other Paths

AVI and CYA retain native generic Empire access. AVI's
`puppet_kingdoms_n_stuff` category, native Zypressen focus, and
`HSM_ZYP_victory_roll` continuation remain intact. CYA's own content is untouched.

The remaining Aquileia candidates are JFT, JEB, JRR, VIN, POM, FLO, AET, FEZ and
FRN, subject to their original government, territory, independence, and JER
existence conditions. EYR and CYA remain ineligible for this category, as upstream.

The category exclusion also covers `unite_aquileia_proper`,
`reclaim_northwest_peripherie`, `reclaim_eastern_peripherie`, and
`aquileia_strikes_back`. The effective decision files were scanned for the native
Aquileia core/claim helpers and `global.aquileia_var` assignments. The only other
formation decision found was `JES_move_capital_decision` in `JES_decisions.txt`,
which already requires `original_tag = JES` and remains available to JES.

## Verification

From the repository root:

```powershell
python -B tools/Test-VereniaFormables.py
python -B tools/Test-VereniaZypressen.py
```

Both commands passed on 2026-10-24: 12 formables tests and 22 Zypressen tests.
On this machine they were run using the bundled executable at
`C:/Users/laslo/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe`.
The formables suite accepts `--eaw PATH` to select another upstream baseline.

Coverage includes complete structural and textual upstream preservation,
eligibility comparisons for every upstream country tag across all four standard
governments, separate allowed/visible checks, cosmetic/current-tag variations,
unchanged native prerequisites, effective-definition uniqueness, alternate
Aquileia entries, and AVI/CYA access. In-memory mutations verify the delta
contract detects missing guards, current-tag substitutions, wrong-country
exclusions, and unrelated reward edits. Zypressen's existing suite checks the
imperial route and its continuation.

These are static and bounded script fixtures. Formation effects are preserved
structurally, not executed by the new suite. No game was launched, and engine
loading, rendering, and existing-save behavior were not playtested.
