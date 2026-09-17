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
  common/                     # shared game database files
  events/                     # event files
  history/                    # country, state, unit, general history
  localisation/english/       # text shown in-game
  gfx/                        # flags, portraits, interface art
  interface/                  # .gui and .gfx interface definitions
  music/                      # optional music definitions/assets
  sound/                      # optional sound definitions/assets

launcher/
  HoISubmod.mod.example       # local launcher descriptor template

docs/
  STRUCTURE.md                # folder purpose and modding notes
```

## Notes

- This template declares `Equestria at War` as a dependency in both descriptors.
- No `replace_path` entries are included by default. Prefer same-path file overrides or new files first; add `replace_path` only when you intentionally replace a whole loaded directory.
- Localization files should use HoI4's expected encoding for your game version. If text fails to load, check `Documents/Paradox Interactive/Hearts of Iron IV/logs/error.log`.
