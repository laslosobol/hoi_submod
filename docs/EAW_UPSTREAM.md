# EaW Upstream Reference

Upstream development repo:

```text
https://github.com/EaW-Team/equestria_dev
```

Local installed workshop reference:

```text
C:/shit/Steam/steamapps/workshop/content/394360/1826643372
```

Use it as the style and compatibility reference for this submod. The repo root includes the expected HoI4 content folders plus EaW-specific project folders such as:

```text
common/
country_metadata/
events/
gfx/
history/
interface/
localisation/
map/
music/
portraits/
scenario_tests/
scripts/
sound/
tutorial/
```

When adding submod content, prefer matching EaW's existing naming, country tags, scripted trigger/effect style, localisation prefixes, portrait layout, and folder placement.

Prefer the local installed workshop reference when validating the exact tokens loaded by the user's current game install. Confirmed useful Dawnclaw/Cyanolisia references include:

```text
common/characters/GRI.txt
common/national_focus/GRI.txt
common/ideas/zzz_CYA_ideas.txt
interface/eaw_ideas.gfx
localisation/english/country_GRI_l_english.yml
localisation/english/country_CYA_l_english.yml
```
