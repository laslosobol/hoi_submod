# HoISubmod

HoI4 Equestria at War submod development workspace.

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

## Narrative Validation

Run with PowerShell 7.2+ on Windows, with the reference dependency in `EaW/`:

```powershell
pwsh -NoProfile -File tools/Test-CyanolisiaNarrative.ps1
```

Add `-CompareHead` before committing to check that the editorial changes preserve focus layout, icons and art approvals. These are static regression checks, not an in-game playthrough.

The same-path event overrides `GriffonianEmpire Events.txt` and `Cyanolisia Events.txt` preserve the reference files except for `imperial.99` and the entry guards of `cyan.9`, `cyan.10`, `cyan.11`. Reconcile them with upstream when updating EaW; do not replace them with duplicate event IDs in a differently named file. See `docs/cyanolisia-lore-audit.md` for the audit and authorized implementation notes.
