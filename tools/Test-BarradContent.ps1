#Requires -Version 7.2
param([string] $GameRoot = 'C:/shit/Steam/steamapps/common/Hearts of Iron IV')
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$mod = Join-Path $root 'mod/HoISubmod'
$base = Join-Path $root 'EaW'
. (Join-Path $PSScriptRoot 'CyanolisiaIconManifest.Common.ps1')
$passed = 0
$failed = [Collections.Generic.List[string]]::new()
function Check([string] $name, [scriptblock] $test) {
    try { & $test; $script:passed++; Write-Output "PASS: $name" }
    catch { $script:failed.Add("$name : $($_.Exception.Message)"); Write-Output "FAIL: $name : $($_.Exception.Message)" }
}
function Assert([bool] $ok, [string] $message) { if (-not $ok) { throw $message } }
# Small block reader: quoted strings and comments are already isolated by the shared tokenizer.
function Blocks([string] $text, [string] $kind) {
    $t = Get-ClausewitzTokens $text
    $result = @{}
    for ($i = 0; $i -lt $t.Count - 2; $i++) {
        if ($t[$i] -ne $kind -or $t[$i+1] -ne '=' -or $t[$i+2] -ne '{') { continue }
        $start = $i; $depth = 1; $id = $null
        for ($i += 3; $i -lt $t.Count; $i++) {
            if ($depth -eq 1 -and $t[$i] -eq 'id' -and $t[$i+1] -eq '=') { $id = $t[$i+2] }
            if ($t[$i] -eq '{') { $depth++ }
            if ($t[$i] -eq '}') { $depth-- }
            if ($depth -eq 0) { break }
        }
        if (-not $id -or $depth -ne 0) { throw "Malformed $kind block" }
        if ($result.ContainsKey($id)) { throw "Duplicate $kind : $id" }
        $result[$id] = $t[$start..$i] -join ' '
    }
    return $result
}
function Raw([string] $relative) { [IO.File]::ReadAllText((Join-Path $mod $relative)) }
function FocusIcons([string] $definition) {
    $tokens = Get-ClausewitzTokens $definition
    $depth = 0
    for ($i = 0; $i -lt $tokens.Count - 2; $i++) {
        if ($tokens[$i] -eq '{') { $depth++ }
        if ($tokens[$i] -eq '}') { $depth-- }
        if ($depth -ne 1 -or $tokens[$i] -ne 'icon' -or $tokens[$i+1] -ne '=') { continue }
        if ($tokens[$i+2] -ne '{') { return @($tokens[$i+2]) }
        $icons = [Collections.Generic.List[string]]::new()
        $inner = 1
        for ($j = $i+3; $j -lt $tokens.Count -and $inner -gt 0; $j++) {
            if ($inner -eq 1 -and $tokens[$j] -match '^GFX_\w+$' -and $tokens[$j+1] -eq '=') { $icons.Add($tokens[$j]) }
            if ($tokens[$j] -eq '{') { $inner++ }
            if ($tokens[$j] -eq '}') { $inner-- }
        }
        Assert ($icons.Count -gt 0 -and $inner -eq 0) 'Empty or malformed dynamic icon selector'
        Assert ($definition -match '\bdynamic = yes\b') 'Dynamic icons need dynamic = yes'
        return $icons.ToArray()
    }
    throw 'Missing focus icon'
}
$files = @(Get-ChildItem $mod -Recurse -Filter 'HSM_BAR*.txt')
$all = ($files | ForEach-Object { [IO.File]::ReadAllText($_.FullName) }) -join "`n"
foreach ($file in $files) {
    Check "Balanced script $($file.FullName.Substring($mod.Length+1))" {
        $depth = 0
        foreach ($t in (Get-ClausewitzTokens ([IO.File]::ReadAllText($file.FullName)))) {
            if ($t -eq '{') { $depth++ }; if ($t -eq '}') { $depth-- }
            Assert ($depth -ge 0) 'Unexpected closing brace'
        }
        Assert ($depth -eq 0) 'Unclosed block'
    }
}
$focus = @{}; $trees = @{}; $events = @{}
foreach ($file in (Get-ChildItem (Join-Path $mod 'common/national_focus') -Filter 'HSM_BAR*.txt')) {
    foreach ($kind in @('shared_focus','focus_tree')) {
        $defs = Blocks ([IO.File]::ReadAllText($file.FullName)) $kind
        $dest = if ($kind -eq 'shared_focus') { $focus } else { $trees }
        foreach ($id in $defs.Keys) { Assert (-not $dest.ContainsKey($id)) "Duplicate $id"; $dest[$id] = $defs[$id] }
    }
}
foreach ($file in (Get-ChildItem (Join-Path $mod 'events') -Filter 'HSM_BAR*.txt')) {
    foreach ($kind in @('country_event', 'news_event')) {
        $defs = Blocks ([IO.File]::ReadAllText($file.FullName)) $kind
        foreach ($id in $defs.Keys) { Assert (-not $events.ContainsKey($id)) "Duplicate event $id"; $events[$id] = $defs[$id] }
    }
}
$loc = @{}
foreach ($language in @('english','russian')) {
    $keys = @{}
    foreach ($file in (Get-ChildItem (Join-Path $mod "localisation/$language") -Filter 'HSM_BAR*.yml')) {
        Check "BOM and unique localization $($file.Name)" {
            $bytes = [IO.File]::ReadAllBytes($file.FullName)
            Assert ([Convert]::ToHexString($bytes[0..2]) -eq 'EFBBBF') 'Missing UTF-8 BOM'
            foreach ($line in [IO.File]::ReadAllLines($file.FullName)) {
                if ($line -match '^\s*([^ #:\s]+):\d*\s+"(.*)"\s*$') {
                    Assert (-not $keys.ContainsKey($Matches[1])) "Duplicate localization $($Matches[1])"
                    $keys[$Matches[1]] = $Matches[2]
                } elseif ($line.Trim() -and $line -notmatch '^\s*(#|l_(english|russian):)') { throw "Malformed localization: $line" }
            }
        }
    }
    $loc[$language] = $keys
}
Check 'English and Russian key parity' {
    Assert (@(Compare-Object @($loc.english.Keys | Sort-Object) @($loc.russian.Keys | Sort-Object)).Count -eq 0) 'Localization languages differ'
}
foreach ($id in $focus.Keys) {
    Check "Focus graph and text $id" {
        Assert ($loc.english.ContainsKey($id) -and $loc.english.ContainsKey("${id}_desc")) 'Missing focus text'
        Assert ($focus[$id] -match 'cost = (4|5) ') 'Expected 28/35-day focus'
        foreach ($m in [regex]::Matches($focus[$id], '\bfocus = (HSM_BAR_\w+)')) { Assert ($focus.ContainsKey($m.Groups[1].Value)) "Unknown prerequisite/exclusive $($m.Groups[1].Value)" }
    }
}
foreach ($id in $trees.Keys) {
    Check "Tree closure and coordinates $id" {
        $members = [Collections.Generic.HashSet[string]]::new()
        foreach ($m in [regex]::Matches($trees[$id], 'shared_focus = (HSM_BAR_\w+)')) { Assert ($focus.ContainsKey($m.Groups[1].Value)) 'Unknown shared focus'; [void]$members.Add($m.Groups[1].Value) }
        do {
            $changed = $false
            foreach ($f in $focus.Keys) {
                foreach ($m in [regex]::Matches($focus[$f], 'prerequisite = \{ focus = (HSM_BAR_\w+)')) {
                    if ($members.Contains($m.Groups[1].Value) -and $members.Add($f)) { $changed = $true }
                }
            }
        } while ($changed)
        $positions = @{}
        foreach ($f in $members) {
            $x = [regex]::Match($focus[$f], '\bx = (-?\d+)').Groups[1].Value
            $y = [regex]::Match($focus[$f], '\by = (-?\d+)').Groups[1].Value
            Assert (-not $positions.ContainsKey("$x,$y")) "Focus overlap: $f / $($positions["$x,$y"]) at $x,$y"
            $positions["$x,$y"] = $f
        }
        if ($id -eq 'HSM_BAR_directorate_tree') { Assert (-not $members.Contains('HSM_BAR_dir_world')) 'World branch leaks into stage one' }
        if ($id -eq 'HSM_BAR_collegium_tree') { Assert (-not $members.Contains('HSM_BAR_collegium_future_root')) 'Collegium future leaks into stage one' }
    }
}
Check 'All local event calls and texts resolve' {
    foreach ($m in [regex]::Matches($all, '\bid\s*=\s*((?:hsm_bar|HSM_BAR)[\w]*\.\d+)')) {
        Assert ($events.ContainsKey($m.Groups[1].Value)) "Missing event $($m.Groups[1].Value)"
    }
    foreach ($event in $events.Values) {
        foreach ($m in [regex]::Matches($event, '\b(?:title|desc|name|text) = ((?:hsm_bar|HSM_BAR)[\w.]+)')) { Assert ($loc.english.ContainsKey($m.Groups[1].Value)) "Missing event text $($m.Groups[1].Value)" }
    }
}
Check 'All custom effect and trigger calls resolve' {
    $defs = [Collections.Generic.HashSet[string]]::new()
    foreach ($dir in @('scripted_effects','scripted_triggers')) {
        foreach ($file in (Get-ChildItem (Join-Path $mod "common/$dir") -Filter 'HSM_BAR*.txt')) {
            foreach ($m in [regex]::Matches([IO.File]::ReadAllText($file.FullName), '(?m)^\s*(HSM_BAR_\w+)\s*=\s*\{')) { [void]$defs.Add($m.Groups[1].Value) }
        }
    }
    foreach ($m in [regex]::Matches($all, '\b(HSM_BAR_\w+)\s*=\s*(?:yes|no)\b')) { Assert ($defs.Contains($m.Groups[1].Value)) "Undefined helper $($m.Groups[1].Value)" }
}
Check 'Focus and event sprites exist in the installed content' {
    $names = [Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
    foreach ($dir in @("$GameRoot/interface", "$base/interface", "$mod/interface")) {
        if (-not (Test-Path $dir)) { continue }
        foreach ($file in (Get-ChildItem $dir -Recurse -Filter '*.gfx')) {
            foreach ($m in [regex]::Matches([IO.File]::ReadAllText($file.FullName), '\bname\s*=\s*"?(GFX_[\w]+)')) { [void]$names.Add($m.Groups[1].Value) }
        }
    }
    foreach ($m in [regex]::Matches($all, '\b(?:icon|picture)\s*=\s*(GFX_[\w]+)')) { Assert ($names.Contains($m.Groups[1].Value)) "Unknown sprite $($m.Groups[1].Value)" }
    foreach ($f in $focus.Values) {
        foreach ($icon in (FocusIcons $f)) {
            Assert ($names.Contains($icon)) "Missing focus icon $icon"
            Assert ($names.Contains("${icon}_shine")) "Missing focus shine $icon"
        }
    }
    foreach ($file in (Get-ChildItem (Join-Path $mod 'common/ideas') -Filter 'HSM_BAR*.txt')) {
        foreach ($m in [regex]::Matches([IO.File]::ReadAllText($file.FullName), '\bpicture\s*=\s*(\w+)')) {
            Assert ($names.Contains("GFX_idea_$($m.Groups[1].Value)")) "Missing idea sprite $($m.Groups[1].Value)"
        }
    }
    foreach ($file in (Get-ChildItem (Join-Path $mod 'common/decisions') -Filter 'HSM_BAR*.txt')) {
        foreach ($m in [regex]::Matches([IO.File]::ReadAllText($file.FullName), '\bicon\s*=\s*(?!GFX_)(\w+)')) {
            Assert ($names.Contains("GFX_decision_$($m.Groups[1].Value)")) "Missing decision sprite $($m.Groups[1].Value)"
        }
    }
}
$core = (Get-ClausewitzTokens (Raw 'common/scripted_effects/HSM_BAR_core_effects.txt')) -join ' '
$actions = (Get-ClausewitzTokens (Raw 'common/on_actions/HSM_BAR_core_on_actions.txt')) -join ' '
Check 'Entry clears obsolete laws and relationship spirits without killing the Collegium' {
    Assert ($core -match 'clr_country_flag = trade_laws_blocked' -and $core -match 'remove_ideas = BAR_no_volunteers') 'Old law/volunteer restrictions persist'
    Assert ([regex]::Matches($core, 'remove_ideas = BAR_relations_').Count -eq 12) 'Relationship ideas not fully cleared'
    $body = [regex]::Match($core, 'HSM_BAR_start_collegium = \{ (.*?)HSM_BAR_start_directorate', 'Singleline').Value
    Assert ($body -notmatch 'barrad_kill_') 'Collegium kills a surviving member'
    Assert ($body -match 'keep_completed = yes') 'Collegium entry loses completed history'
}
Check 'Critical hooks and Sombra lifecycle are wired' {
    foreach ($effect in @('HSM_BAR_anomalies_initialize','HSM_BAR_dip_initialize','HSM_BAR_collegium_initialize','HSM_BAR_dip_daily_pulse','HSM_BAR_anomalies_pulse')) { Assert ($core -match "$effect = yes") "Unwired $effect" }
    Assert ($actions -match 'on_daily_EQS' -and $actions -match 'remove_ideas = HSM_BAR_anti_sombra') 'Foreign buff survives disappearance of BAR'
    $trigger = (Get-ClausewitzTokens (Raw 'common/scripted_triggers/HSM_BAR_core_triggers.txt')) -join ' '
    Assert ($trigger -match 'has_war_with = CRY' -and $trigger -match 'character = CRY_sombra ruling_only = yes') 'Sombra aid is not tied to current war and ruler'
}
Check 'Research slot reward uses the documented engine trigger' {
    Assert ($focus.HSM_BAR_technical_school -match 'amount_research_slots < 5') 'Invalid research-slot trigger'
    Assert ($all -notmatch '\bnum_of_research_slots\b') 'Undocumented research-slot trigger remains'
}
Check 'Defeat dissolves institutions without rewriting neighbour history' {
    foreach ($hook in @('on_annex','on_puppet','on_release_as_free','on_liberate')) { Assert ($actions.Contains("$hook =")) "Missing teardown hook $hook" }
    Assert ($actions -match 'FROM = \{ HSM_BAR_dissolve_institutions = yes' -and $actions -match 'ROOT = \{ HSM_BAR_dissolve_institutions = yes') 'Incorrect teardown scopes'
    foreach ($flag in @('active','collegium','directorate','diplomacy_open','smile_partner')) { Assert ($core.Contains("clr_country_flag = HSM_BAR_$flag")) "Stale $flag after defeat" }
    Assert ($core -notmatch 'clr_country_flag = HSM_BAR_dip_settled') 'Neighbour settlement history erased'
    $teardownMatch = [regex]::Match($core, '^HSM_BAR_dissolve_institutions = \{ (?<body>.*?) \} HSM_BAR_initialize_common = \{')
    Assert $teardownMatch.Success 'Cannot isolate institution teardown'
    $teardown = $teardownMatch.Groups['body'].Value
    Assert ($teardown -match 'remove_dynamic_modifier = \{ modifier = HSM_BAR_collegium_services \}') 'Collegium modifier survives teardown'
    Assert ($teardown -match 'clr_country_flag = HSM_BAR_active .*clr_country_flag = HSM_BAR_service_founded .*HSM_BAR_refresh_service_training = yes') 'Service cleanup is not called after invalidating its lifecycle'
    $training = (Get-ClausewitzTokens (Raw 'common/scripted_effects/HSM_BAR_service_rewards.txt')) -join ' '
    Assert ($training -match 'limit = \{ tag = BAR has_country_flag = HSM_BAR_active has_country_flag = HSM_BAR_directorate has_country_flag = HSM_BAR_service_founded has_capitulated = no \}') 'Service refresh has an incomplete lifecycle guard'
    Assert ($training -match 'else = \{ if = \{ limit = \{ has_dynamic_modifier = \{ modifier = HSM_BAR_service_capacity \} \} remove_dynamic_modifier = \{ modifier = HSM_BAR_service_capacity \} \} \} \} \}$') 'Service invalid-state branch does not remove the modifier'
}
Check 'Open S.M.I.L.E. windows revalidate acceptance and evidence sharing' {
    $smile = Blocks (Raw 'events/HSM_BAR_smile.txt') 'country_event'
    Assert ($smile['hsm_bar_smile.1'] -match 'option = \{ name = hsm_bar_smile.1.a .*? if = \{ limit = \{ has_government = democratic NOT = \{ has_war_with = BAR') 'Acceptance has no live regime/war check'
    Assert ([regex]::Matches($smile['hsm_bar_smile.1'], 'HSM_BAR_smile_contact_relevant = yes has_country_flag = HSM_BAR_smile_request_pending NOT = \{ has_country_flag = HSM_BAR_smile_compromised').Count -eq 2) 'Contact and acceptance must both recheck relevance, pending request and partner safety'
    Assert ($smile['hsm_bar_smile.3'] -match 'option = \{ name = hsm_bar_smile.3.a .*? if = \{ limit = \{ has_country_flag = HSM_BAR_active') 'Sharing lacks completion-time validity checks'
}
Check 'An aborted trial cannot collect a delayed opening fee' {
    Assert ([regex]::Matches($events['hsm_bar_core.13'], 'has_country_flag = HSM_BAR_suppression_live NOT = \{ has_country_flag = HSM_BAR_suppression_resolved \}').Count -eq 2) 'Trial fee requires both display and option-time guards'
}
Check 'Secret service no longer uses public terror as its governing mechanic' {
    Assert ($all -notmatch 'add_ideas\s*=\s*HSM_BAR_displaced_families|set_country_flag\s*=\s*HSM_BAR_(?:repressive_methods|collective_classification|cult_mass_arrests)') 'Retired persecution policy is still awarded'
    Assert ((Raw 'common/national_focus/HSM_BAR_directorate.txt') -notmatch 'HSM_BAR_(public_trust|capacity)\b') 'Service focuses still use retired meters'
    Assert ((Raw 'events/HSM_BAR_core.txt') -notmatch 'HSM_BAR_(public_trust|capacity)\b') 'Service story still uses retired meters'
    Assert ((Raw 'common/dynamic_modifiers/HSM_BAR_core.txt') -notmatch 'political_power_gain|HSM_BAR_service_coordination') 'Retired cover still contributes service political power'
    Assert ((Raw 'common/dynamic_modifiers/HSM_BAR_core.txt') -match 'research_speed_factor = HSM_BAR_service_research') 'Service milestones lost their research effect'
    Assert ($events['hsm_bar_core.15'] -match 'clr_country_flag = HSM_BAR_normalization' -and $events['hsm_bar_core.15'] -match 'set_country_flag = HSM_BAR_coexistence') 'Accountability ending retains the wrong active doctrine'
}
Check 'Suppression has research, time and consequence gates' {
    Assert ($focus.HSM_BAR_dir_activation -match 'has_country_flag = HSM_BAR_project_suppression_done') 'Suppression bypasses research'
    Assert ($focus.HSM_BAR_dir_aftermath -match 'has_country_flag = HSM_BAR_suppression_resolved') 'Hearing bypasses trial'
    Assert ($focus.HSM_BAR_dir_activation -match 'days = 30' -and $focus.HSM_BAR_dir_activation -match 'add_ideas = HSM_BAR_suppression_crisis') 'Trial has no duration or cost'
    Assert ($events['hsm_bar_core.12'] -match 'remove_ideas = HSM_BAR_suppression_crisis' -and $events['hsm_bar_core.12'] -match 'HSM_BAR_suppression_escalated') 'Trial lacks stop/continue fork'
}
Check 'Native friendship ending exposes exactly two continuations' {
    $native = Blocks (Raw 'events/Barrad Events.txt') 'country_event'
    Assert ($native['barrad_end.2'] -match 'HSM_BAR_start_collegium = yes' -and $native['barrad_end.2'] -match 'HSM_BAR_start_directorate = yes') 'Missing entry option'
    Assert ($native['barrad_end.2'] -match 'trigger = \{ NOT = \{ has_country_flag = HSM_BAR_active \} \}') 'Duplicate queued friendship events can restart the route'
}
Check 'Native Barrad override preserves events apart from entry and queued-ending guards' {
    $native = Blocks ([IO.File]::ReadAllText((Join-Path $base 'events/Barrad Events.txt'))) 'country_event'
    $updated = Blocks (Raw 'events/Barrad Events.txt') 'country_event'
    Assert ($native.Count -eq $updated.Count) 'Native events added or removed'
    $guard = 'trigger = { NOT = { has_country_flag = HSM_BAR_active } } '
    $relationshipGuards = @('barrad_monthy_relation_hit_event.1', 'barrad_monthy_relation_hit_event.2', 'barrad_monthy_relation_hit_event.3', 'barrad_monthy_relation_hit_event.4', 'barrad_monthy_relation_hit_event.5', 'barrad_monthy_relation_hit_event.6', 'barrad_silver_star.1', 'barrad_silver_star.11', 'barrad_leopold_carousing.1', 'barrad_leopold_carousing.11', 'barrad_leopold_carousing.2', 'barrad_leopold_carousing.22', 'barrad_leopold_carousing.3', 'barrad_leopold_carousing.33', 'barrad_friends.1', 'barrad_friends.2', 'barrad_friends.3', 'barrad_ambrosius.1', 'barrad_first.6')
    foreach ($id in $native.Keys) {
        if ($id -eq 'barrad_end.2') { continue }
        Assert ($updated.ContainsKey($id)) "Missing native event $id"
        if ($id -in @('barrad_wit.1','barrad_ccamb.8','barrad_ccamb.81')) {
            # Unwrap only the precise BAR-scoped active-route guard. Compare the
            # complete remaining event, not just selected effects or substrings.
            $tokens = [Collections.Generic.List[string]]::new([string[]]($updated[$id] -split ' '))
            $prefix = 'if = { limit = { BAR = { NOT = { has_country_flag = HSM_BAR_active } } }'
            $count = 0
            $prefixLength = ($prefix -split ' ').Count
            for ($i = $tokens.Count - $prefixLength; $i -ge 0; $i--) {
                if ($i + $prefixLength -gt $tokens.Count) { continue }
                if (($tokens.GetRange($i,$prefixLength) -join ' ') -ne $prefix) { continue }
                $depth = 1; $end = $i + $prefixLength
                for (; $end -lt $tokens.Count; $end++) {
                    if ($tokens[$end] -eq '{') { $depth++ }
                    if ($tokens[$end] -eq '}') { $depth-- }
                    if ($depth -eq 0) { break }
                }
                Assert ($depth -eq 0) 'Unbalanced native callback guard'
                $tokens.RemoveAt($end); $tokens.RemoveRange($i,$prefixLength); $count++
            }
            $expected = if ($id -eq 'barrad_ccamb.8') { 1 } else { 2 }
            Assert ($count -eq $expected) "Missing queued diplomacy callback guard: $id"
            Assert (($tokens -join ' ') -eq $native[$id]) "Unexpected native callback changes: $id"
        } elseif ($id -eq 'barrad_raid.1') {
            Assert ([regex]::Matches($updated[$id], 'NOT = \{ has_country_flag = HSM_BAR_active \}').Count -eq 3) 'Raid rewards can restore obsolete spirits'
            Assert ($updated[$id].Replace(' NOT = { has_country_flag = HSM_BAR_active }', '') -eq $native[$id]) 'Raid cleanup was changed'
        } elseif ($native[$id] -match 'load_focus_tree =|barrad_kill_|bar_kill_ambrosius' -or $id -in $relationshipGuards) {
            Assert ($updated[$id].Contains($guard)) "Queued destructive event not guarded: $id"
            Assert ($updated[$id].Replace($guard, '') -eq $native[$id]) "Unexpected changes inside $id"
        } else { Assert ($updated[$id] -eq $native[$id]) "Unexpected native change: $id" }
    }
}
Write-Output "Barrad integration: $passed passed; $($failed.Count) failed; $($focus.Count) focuses; $($events.Count) new events; $($loc.english.Count) English keys."
if ($failed.Count) { throw ($failed -join "`n") }
