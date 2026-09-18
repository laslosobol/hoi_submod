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
