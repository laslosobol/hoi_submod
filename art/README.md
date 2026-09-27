# Cyanolisia art sources

The PNGs in `art/source` are the generated high-resolution sources. The game
loads the TGA exports under `mod/HoISubmod/gfx`. The images were generated
with the built-in image generation tool, then resized with
`tools/Convert-ToHoi4Tga.ps1`.

## Icon replacement progress

The visual target is one original emblem per Cyanolisian focus and national
spirit, with a consistent painted style: dark iron, antique gold, ivory, royal
blue, restrained crimson, and transparent backgrounds. Do not treat a newly
chosen EaW icon as a finished replacement.

As of this series, 116 of 350 focus definitions use a Cyanolisian GFX sprite.
26 of 137 HSM idea blocks use a Cyanolisian image.
The remaining icons are still provisional EaW or generic assets. The two uses
of the `HSM_CYA_grover_regency` idea intentionally share one image.

`docs/icon-generation-manifest.md` is the authoritative focus and national-spirit
status and art-direction register. The descriptions below are historical source notes,
not proof that an asset was integrated or visually approved. Consult the
manifest before selecting a batch and update only its affected rows afterward.
The manifest scripts require PowerShell 7.2+ on Windows (`pwsh`). The manifest
stores SHA-256 baselines for visually approved PNG/TGA pairs;
routine sync does not renew approval after an image changes. See its Working
rules for `-MarkDone`, `-ResolveFix`, and read-only `-Check`.
Run `tools/Get-CyanolisiaIconCoverage.ps1 -ListPending` for a quick independent
check of provisional focus and idea sprites.

New focus sources (99x86 exports):

- `HSM_CYA_joint_general_staff.png`: Three theater maps under one plotting compass.
- `HSM_CYA_national_development_plan.png`: Rail, school and factory on a shared plan.
- `HSM_CYA_port_foundries.png`: A ship propeller cast in a waterfront foundry.
- `HSM_CYA_southern_fleet_yards.png`: An old hull restored on a southern slip.
- `HSM_CYA_naval_air_school.png`: Seaplane training above a convoy chart.
- `HSM_CYA_dockyard_program.png`: Three slips at successive build stages.
- `HSM_CYA_raise_austernfischer.png`: Salvage of the sunken battlecruiser.
- `HSM_CYA_seaborne_corps.png`: Griffon marines in a landing craft.
- `HSM_CYA_admiralty_compact.png`: Naval, air and shore plans on one chart.
- `HSM_CYA_crown_military_colleges.png`: A regency academy and filled course register.
- `HSM_CYA_dawnclaw_war_college.png`: Dawnclaw's atlas of multiple fronts.
- `HSM_CYA_imperial_officer_exchange.png`: Two officer traditions and shared exercises.

- `HSM_CYA_frontier_supply_corps.png`: a loaded supply lorry follows a mapped
  road from a frontier depot.
- `HSM_CYA_combined_arms_school.png`: artillery and griffon cadets train
  against one tactical exercise plan.
- `HSM_CYA_border_defense_staff.png`: two pass bunkers match defensive and
  supply routes on a contour staff map.
- `HSM_CYA_griffonian_armament_standard.png`: captured rifles and cartridges
  are checked against one common gauge.
- `HSM_CYA_crown_credit_authority.png`: the Countess's credit ledger and
  Cyanolisian seal finance towns and workshops.
- `HSM_CYA_dawnclaw_procurement_office.png`: Dawnclaw's iron-cross purchase
  order links rifle and truck blueprints to an arms factory.
- `HSM_CYA_frontier_development_board.png`: surveyed road and railway routes
  connect a frontier village, bridge, and warehouse.
- `HSM_CYA_imperial_supply_grid.png`: a rail switch joins Cyanolisian and
  old-capital freight depots beneath their distinct marks.
- `HSM_CYA_coastal_patrols.png`: a cutter searches an inlet watched from the
  coast, separate from the convoy-escort motif.
- `HSM_CYA_continental_ordnance.png`: an old-capital arsenal turns its lines
  toward standardized rifles and artillery shells.
- `HSM_CYA_codify_household_compact.png`: a written court charter sealed by
  the Cyanolisian cross and Dawnclaw's iron cross beneath the Countess's circlet.
- `HSM_CYA_the_hidden_assistant.png`: a written court decree with the
  Cyanolisian seal on a public lectern, with a concealed griffon shadow.
- `HSM_CYA_the_countess_alone.png`: the Countess's griffon talon grips the
  court chair beneath her ermine mantle and simple gold circlet.
- `HSM_CYA_the_revealed_exile.png`: Dawnclaw emerging before the court.
- `HSM_CYA_hide_the_fugitive.png`: a cloak concealing a sealed dossier at the
  palace entrance; the Cyanolisian seal protects the GRI-marked file.
- `HSM_CYA_an_unlikely_marriage.png`: the Countess's and Dawnclaw's claws
  joining over a charter.
- `HSM_CYA_frontier_march_plan.png`: a border marker, survey ruler, saber, and
  campaign map.
- `HSM_CYA_delegate_security_to_dawnclaw.png`: a palace key passing from the
  Countess to Dawnclaw.
- `HSM_CYA_expand_countess_cabinet.png`: a wing protecting the regency council
  and its blue-sealed charter.
- `HSM_CYA_palace_security_directorate.png`: a guarded palace gate on a dark
  shield.
- `HSM_CYA_reform_field_command.png`: officer's helmet and crossed command
  batons.
- `HSM_CYA_standardise_field_equipment.png`: matched rifles, equipment crates,
  and a measuring gauge, with the Cyanolisian cross on the crates.
- `HSM_CYA_officer_academy.png`: tactics atlas and cadet epaulettes before an
  academy bearing the Cyanolisian cross.
- `HSM_CYA_crown_field_staff.png`: Grover's pointed coronet above an army
  order ledger and two officer batons.
- `HSM_CYA_dawnclaw_operational_staff.png`: a rail-route campaign map beneath
  Dawnclaw's armored claw, with an authentic GRI archival tab.
- `HSM_CYA_coastal_reconstruction.png`: a harbor crane lifting a cog above a
  foundry and waves.
- `HSM_CYA_coastal_transport_authority.png`: a signal lever coordinating a
  harbor ship, railway, and freight map.
- `HSM_CYA_technical_institute.png`: a machine prototype, laboratory lamp,
  technical books, and engineering drawings.
- `HSM_CYA_arsenal_network.png`: three dispersed arms workshops linked by rail
  around a shell-and-cog symbol.
- `HSM_CYA_quartermaster_service.png`: regimented food, kit, and transport
  stores with the Cyanolisian cross on the main supply crate.
- `HSM_CYA_railway_battalions.png`: a military track-repair engine with rail
  gauge and spanners.
- `HSM_CYA_signal_companies.png`: field radio and aerial with a correctly
  medallioned Cyanolisian signal pennant.
- `HSM_CYA_field_hospitals.png`: field medical tent, stretcher, kit, and
  bandages.
- `HSM_CYA_frontier_artillery.png`: field howitzer by a frontier parapet and
  range map.
- `HSM_CYA_engineer_brigades.png`: reinforced pillbox with engineer's shovel
  and spirit level.
- `HSM_CYA_aerial_reconnaissance.png`: observation plane and aerial camera
  above a frontier map.
- `HSM_CYA_motorised_reserves.png`: two military trucks crossing a road map.
- `HSM_CYA_port_customs_houses.png`: a customs gatehouse, inspected shipping
  manifest with the Cyanolisian seal, and cargo at the quay.
- `HSM_CYA_coastal_quarries.png`: an ore rail cart, stone terraces, and a
  coastal lifting crane.
- `HSM_CYA_electrify_the_workshops.png`: a dynamo cabled to two lit workshops.
- `HSM_CYA_apprenticeship_halls.png`: craft benches, an anvil, and an open
  technical manual; its banners carry no invented heraldry.
- `HSM_CYA_rural_cooperatives.png`: shared threshing machine, grain, and
  cooperative ledger.
- `HSM_CYA_industrial_standards_board.png`: gear measured with a micrometer
  beside an inspection checklist.
- `HSM_CYA_crown_municipal_loans.png`: civic building plans and credit under
  the Countess's protective white wing.
- `HSM_CYA_dawnclaw_factory_contracts.png`: iron procurement dossier and
  military baton before an arms factory, now with Dawnclaw's iron-cross seal.
- `HSM_CYA_griffenheim_rail_hub.png`: capital railway station with converging
  tracks and a switch lever.
- `HSM_CYA_herzland_industrial_survey.png`: ore samples and planned works on
  a Herzland survey map.
- `HSM_CYA_convoy_escorts.png`: destroyer protecting a merchant steamer.
- `HSM_CYA_naval_signals_school.png`: shipboard signal lantern, maritime
  code pennants, and training chart.
- `HSM_CYA_evi_freight_corridor.png`: freight train and repaired valley bridge
  over the Evi route map.
- `HSM_CYA_imperial_research_exchange.png`: Cyanolisian workshop and Herzland
  academy exchanging industrial research.
- `HSM_CYA_seaplane_stations.png`: floatplane, coastal hangar, and observation
  mast.
- `HSM_CYA_marine_training_ground.png`: landing craft and mock pier at a
  beach training site.
- `HSM_CYA_coastal_defence_batteries.png`: fixed harbor guns with an inland
  bunker behind them.
- `HSM_CYA_bluewater_shipyards.png`: long-range hull under construction in a
  two-crane drydock.
- `HSM_CYA_imperial_convoy_authority.png`: three provincial ports sharing a
  central route chart and timetable.
- `HSM_CYA_expeditionary_fleet.png`: troop transport and two escorts on a
  long-distance route.

New national spirit sources (64x64 exports):

- `HSM_CYA_countess_civilian_court.png`: civilian quill and court seal take
  precedence over the officer's baton.
- `HSM_CYA_household_compact.png`: the Cyanolisian court seal and Dawnclaw's
  iron-cross seal bound by a blue cord, with the Countess's seal higher.
- `HSM_CYA_hidden_assistant_court.png`: Dawnclaw's insignia tucked behind a
  written, Cyanolisian-sealed court report in a filing drawer.
- `HSM_CYA_countess_alone_court.png`: court signet press, circlet, and ermine
  mantle around the Cyanolisian seal.
- `HSM_CYA_security_directorate_court.png`: a barred security screen holds a
  written, Cyanolisian-sealed court petition away from the palace chamber.
- `HSM_CYA_colonels_household.png`: Dawnclaw's command baton bound to a
  palace key by a courier cord.
- `HSM_CYA_revealed_exile_regime.png`: an unmarked crimson field pennant and
  white feather over a cracked Cyanolisian court seal.
- `HSM_CYA_revealed_exile_regime_secure.png`: the same pennant and feather
  fixed before a riveted plain-iron administrative shield.
- `HSM_CYA_development_board.png`: a public-works blueprint above three
  ministry emblems for industry, transport, and finance.
- `HSM_CYA_frontier_signals_network.png`: three frontier relay towers linked
  above a Cyanolisian dispatch pouch.
- `HSM_CYA_frontier_drill_standards.png`: helmet, drill manual, and field
  command batons above a low frontier wall.
- `HSM_CYA_local_supply_depots.png`: a permanent warehouse linked to two
  outlying supply points.
- `HSM_CYA_public_works_relief.png`: repaired bridge, stone cart, and shovel.
- `HSM_CYA_polytechnic_exchange.png`: two engineering manuals connected by
  interlocking gears.
- `HSM_CYA_regency_land_credit.png`: land and port credit tied to a neutral
  grain-sealed deed; no invented dynastic emblem.
- `HSM_CYA_corporate_mobilisation_plan.png`: factory roofs feeding a bound
  industrial gear beneath a sealed contract.
- `HSM_CYA_dawnclaw_griffonian_files.png`: a red, iron-bound intelligence
  dossier with a Griffonian campaign map.
- `HSM_CYA_frontier_march_policy.png`: a Cyanolisian-cross border-defense
  shield backed by a stone wall and stakes.
- `HSM_CYA_unlikely_marriage.png`: blue and red signet rings on a written
  marriage contract with the Cyanolisian seal, distinct from its focus icon.
- `HSM_CYA_countess_dominant_court.png`: the Countess's white claw seals an
  appointment ledger while a military gauntlet is pushed aside.
- `HSM_CYA_dawnclaw_dominant_court.png`: Dawnclaw's iron claw controls military
  orders and displaces the civilian charter.

## Heraldry reference

Check the dependency's actual flags before placing a coat of arms in an icon.
`EaW/gfx/flags/CYA_neutrality.tga` shows the Cyanolisian slate-blue field,
gold-edged dark cross, and central gold medallion. The Countess's civil and
Cyanolisian military institutions use this motif. Dawnclaw's personal iron
cross is visible on `art/source/HSM_CYA_ferdinand_dawnclaw_portrait.png`; it
is a separate factional mark, not a replacement for the Cyanolisian state
arms. `EaW/gfx/flags/GRI_neutrality.tga`
shows the black imperial griffon on a quartered cream-and-orange field; reserve
it for actual imperial documents, banners, or claims. The Directorate has its
own `mod/HoISubmod/gfx/flags/HSM_CYA_DIRECTORATE.tga`. Do not substitute an
unrelated gold or white griffon, fleur-de-lis, or other generic heraldic symbol.
If the focus is about a workshop, transport, or social policy, omit heraldry
unless it helps identify a specific institution.
Court seals and important documents should not be blank by default. Put the
appropriate existing emblem on a large seal and a few restrained ink strokes
on written orders; keep the mark broad enough to survive a 64x64 export.
Deliberately unsigned papers are an exception only when the story calls for it.

`EaW/gfx/leaders/GRI/Grover_VI_good.tga` is the reference for adult Grover's
gold coronet: a simple band with tall points, not fleur-de-lis finials.
For neighbor-focused art, inspect the relevant ideology's flag rather than
guessing a shared emblem: `EaW/gfx/flags/MIT_*.tga` (Minotauria),
`EaW/gfx/flags/SIC_*.tga` (Sicameon), and `EaW/gfx/flags/JAS_*.tga`
(Asterion). Their heraldry changes markedly across political paths.

The early Cyanolisian institution icons and the military/legitimacy spirits
use the local cross and medallion. Grover's crown in the regency, succession,
and unification icons follows his in-game portrait rather than a generic
fleur-de-lis crown. Dawnclaw's unification icon uses plain military pennants
instead of invented imperial flags.

## Character portraits

- `HSM_CYA_ferdinand_dawnclaw_portrait.png`: Dawnclaw's civilian leader
  portrait, exported at 156x210 to `gfx/leaders/CYA/`. A cropped version in
  the EaW advisor frame is saved as `HSM_CYA_ferdinand_dawnclaw_advisor.png`
  and exported at 65x67.
- `HSM_CYA_countess_taillow_portrait.png`: Countess Taillow's leader portrait,
  repainted with mature griffon proportions to match Dawnclaw's style and
  exported at 156x210 to `gfx/leaders/CYA/redbirb.tga` so the existing EaW
  character definition displays it without a duplicate character override.

Both portraits were based on the original EaW character portraits for
recognizable plumage, beaks, attire, and insignia.

## Prompt set

- `cya_directorate_flag.png`: Flat 82:52 fictional Cyanolisian Directorate
  flag; iron-charcoal field, old-gold cross inherited from Cyanolisia, crimson
  shield at the crossing, simplified ivory griffon wing and talon. No text,
  folds, pole, border, or real-world political emblems. The export composites
  the generated image over opaque `#17191b`.
- `evi_governorate_codes.png`: HOI4-style transparent focus icon of an
  iron-bound military law ledger, crimson griffon-wing seal, Evi valley maps,
  antique gold and charcoal.
- `countess_regency_for_grover.png`: Transparent focus icon of Grover's small
  golden pointed coronet on a blue-and-ivory regency charter, protected by a
  white griffon wing. The Countess safeguards the crown rather than claiming it.
- `question_of_grover.png`: Transparent focus icon of a golden crown on dark
  iron balance scales, with a blue royal charter and a red sealed military
  decree in the pans.
- `one_griffonia_under_the_crown.png`: Transparent focus icon of a golden
  imperial crown above a united Griffonian map, white wings and blue ribbon;
  lawful unification for Grover VI.
- `one_griffonia_under_claw.png`: Transparent focus icon of an armored griffon
  talon gripping Grover's crown over a map, with plain crimson military pennants;
  Dawnclaw's command of united Griffonia.
- `countess_union_mandate.png`: Transparent focus icon of three provincial
  charters with blue seals beneath a protective white griffon wing and compass;
  the Countess's lawful mandate to unite Griffonia.
- `imperial_interregnum.png`: Transparent focus icon of an empty iron throne,
  crimson banner, map, and marshal's baton; Dawnclaw's post-Grover interregnum.
- `cya_industrial_program.png`: Transparent national spirit icon with an iron
  cog, railway wheel, foundry chimney, and rails for the industrial programme.
- `cya_military_program.png`: Transparent national spirit icon with the
  Cyanolisian cross on a shield, crossed officer batons, and a crimson command
  pennant for the military programme.
- `cya_imperial_legitimacy.png`: Transparent national spirit icon with a
  provincial charter, Cyanolisian-cross wax seal, and judicial balance. It
  avoids Grover's portrait and crown.

All icon prompts requested one centered, hand-painted grand-strategy emblem,
transparent background, clear silhouette at 99x86, and no lettering or frame.
The three national spirit prompts requested the same treatment at 64x64.
The Grover regency spirit reuses `countess_regency_for_grover.png` at 64x64.

Example export:

```powershell
pwsh -NoProfile -File tools/Convert-ToHoi4Tga.ps1 -Source art/source/evi_governorate_codes.png -Destination mod/HoISubmod/gfx/interface/goals/HSM_CYA_evi_governorate_codes.tga -Width 99 -Height 86
pwsh -NoProfile -File tools/Convert-ToHoi4Tga.ps1 -Source art/source/cya_imperial_legitimacy.png -Destination mod/HoISubmod/gfx/interface/ideas/cya_imperial_legitimacy.tga -Width 64 -Height 64
```
