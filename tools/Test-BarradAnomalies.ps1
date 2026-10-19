#Requires -Version 7.2
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$mod = Join-Path $root 'mod/HoISubmod'
$passed = 0
$failed = [Collections.Generic.List[string]]::new()

function Assert($condition, [string] $message) { if (-not $condition) { throw $message } }
function Case([string] $name, [scriptblock] $body) {
    try { & $body; $script:passed++; Write-Output "PASS: $name" }
    catch { $script:failed.Add("${name}: $($_.Exception.Message)"); Write-Output "FAIL: ${name}: $($_.Exception.Message)" }
}
function Parse([string] $text) {
    $tokens = @([regex]::Matches($text, '"(?:\\.|[^"\\])*"|#[^\r\n]*|<=|>=|[{}=<>]|[^\s{}=<>]+') | Where-Object { -not $_.Value.StartsWith('#') } | ForEach-Object Value)
    $index = 0
    return ,(Read-Nodes $tokens ([ref]$index))
}
function Read-Nodes($tokens, [ref] $index, [bool] $nested = $false) {
    $nodes = [Collections.Generic.List[object]]::new()
    while ($index.Value -lt $tokens.Count) {
        $key = $tokens[$index.Value++]
        if ($key -eq '}') { Assert $nested 'Unexpected closing brace'; return ,$nodes.ToArray() }
        $node = @{ Key = $key; Op = ''; Value = ''; Children = @() }
        if ($index.Value -lt $tokens.Count -and $tokens[$index.Value] -in @('=', '<', '>', '<=', '>=')) {
            $node.Op = $tokens[$index.Value++]
            Assert ($index.Value -lt $tokens.Count) "Missing value after $key"
            if ($tokens[$index.Value] -eq '{') { $index.Value++; $node.Children = Read-Nodes $tokens $index $true }
            else { $node.Value = $tokens[$index.Value++] }
        }
        $nodes.Add($node)
    }
    Assert (-not $nested) 'Unclosed block'
    return ,$nodes.ToArray()
}
function Read-Code([string] $path) { return ,(Parse ([IO.File]::ReadAllText($path))) }
function Prop($node, $key) { return @($node.Children | Where-Object Key -eq $key) }
function Val($node, $key) { return (Prop $node $key | Select-Object -First 1).Value }
$triggers = @{}
foreach ($node in (Read-Code (Join-Path $mod 'common/scripted_triggers/HSM_BAR_anomalies.txt'))) { Assert (-not $triggers.ContainsKey($node.Key)) "Duplicate trigger $($node.Key)"; $triggers[$node.Key] = $node }
foreach ($node in (Read-Code (Join-Path $mod 'common/scripted_triggers/HSM_BAR_cases.txt'))) { Assert (-not $triggers.ContainsKey($node.Key)) "Duplicate trigger $($node.Key)"; $triggers[$node.Key] = $node }
$effects = @{}
foreach ($node in (Read-Code (Join-Path $mod 'common/scripted_effects/HSM_BAR_anomalies.txt'))) { Assert (-not $effects.ContainsKey($node.Key)) "Duplicate effect $($node.Key)"; $effects[$node.Key] = $node }
# Evaluate seal callbacks; the aggregate modifier is checked by Test-BarradCaseOutcomes.cjs.
foreach ($node in (Read-Code (Join-Path $mod 'common/scripted_effects/HSM_BAR_case_outcomes.txt'))) {
    if ($node.Key -ne 'HSM_BAR_refresh_case_outcomes') { Assert (-not $effects.ContainsKey($node.Key)) "Duplicate effect $($node.Key)"; $effects[$node.Key] = $node }
}
$decisions = @{}
foreach ($node in (Read-Code (Join-Path $mod 'common/decisions/HSM_BAR_anomalies.txt'))[0].Children) { $decisions[$node.Key] = $node }
foreach ($node in (Read-Code (Join-Path $mod 'common/scripted_triggers/HSM_BAR_operations_triggers.txt'))) { $triggers[$node.Key] = $node }
$events = @{}
foreach ($node in (Read-Code (Join-Path $mod 'events/HSM_BAR_anomalies.txt'))) { if ($node.Key -eq 'country_event') { $events[(Val $node 'id')] = $node } }

function Country($tag, $capital) { return @{ Type = 'country'; Id = $tag; Capital = "$capital"; Exists = $true; Capitulated = $false; AI = $false; Flags = @{}; Vars = @{}; Ideas = @(); Leader = ''; LeaderIdeology = ''; Traits = @(); PP = 0; Manpower = 0; Stability = 0; Events = @(); Incidents = 0 } }
function New-World {
    $w = @{ Countries = @{}; States = @{}; Flags = @{}; Vars = @{}; Arrays = @{}; Root = $null; From = $null; Dlc = @('La Resistance','Gotterdammerung') }
    foreach ($entry in @(@('BAR',624),@('YAL',398),@('DED',415),@('CRY',344),@('AAA',900),@('BBB',901),@('CCC',902))) {
        $w.Countries[$entry[0]] = Country $entry[0] $entry[1]
        $w.States["$($entry[1])"] = @{ Type = 'state'; Id = "$($entry[1])"; Controller = $entry[0]; Reactor = 0; Flags = @{}; Vars = @{} }
    }
    $w.States['665'] = @{ Type = 'state'; Id = '665'; Controller = 'YAL'; Reactor = 0; Flags = @{}; Vars = @{} }
    $w.Root = $w.Countries.BAR; $w.From = $w.Countries.YAL
    foreach ($flag in @('active','directorate','service_founded','field_research_open','foreign_mandate','forensic_mandate','project_containment_done','project_forensics_done','project_wards_done')) { $w.Root.Flags["HSM_BAR_$flag"] = $true }
    # Custody fixtures begin after the regional lead checks and laboratory work.
    # Test-BarradCases.cjs independently checks that these cannot be skipped.
    foreach ($region in @('local','equus','griffonia','north','riverlands','zebrica')) { $w.Root.Flags["HSM_BAR_region_${region}_open"] = $true }
    foreach ($id in @('grover','herald','rosa','chalice','phylactery','darkheart','sombra')) { $w.Root.Flags["HSM_BAR_case_${id}_rumor"] = $true }
    foreach ($id in @('rock','titan','entity','amulet','plants','grover','rosa','herald','sombra','chalice','phylactery','darkheart')) { $w.Root.Flags["HSM_BAR_study_${id}_done"] = $true }
    return $w
}
function Resolve($key, $w, $stack) {
    if ($key -eq 'ROOT') { return $w.Root }
    if ($key -eq 'FROM') { return $w.From }
    if ($key -eq 'THIS') { return $stack[0] }
    if ($key -match '^PREV(?:\.PREV)*$') { return $stack[($key.Split('.').Count)] }
    if ($w.Countries.ContainsKey($key)) { return $w.Countries[$key] }
    if ($w.States.ContainsKey($key)) { return $w.States[$key] }
    if ($key.StartsWith('var:')) {
        $v = Get-VariableValue $key.Substring(4) $w $stack
        if ($null -eq $v) { return $null }
        if ($v -is [hashtable]) { return $v }
        if ($w.States.ContainsKey("$v")) { return $w.States["$v"] }
        throw "Unknown scope variable $key=$v"
    }
    return $null
}
function Get-VariableValue($key, $w, $stack) {
    if ($key.StartsWith('global.')) { return $w.Vars[$key.Substring(7)] }
    return $stack[0].Vars[$key]
}
function Test-Nodes($nodes, $w, $stack) {
    foreach ($n in $nodes) {
        $s = $stack[0]; $v = $n.Value; $ok = $false
        switch ($n.Key) {
            'AND' { $ok = Test-Nodes $n.Children $w $stack }
            'OR' { foreach ($c in $n.Children) { if (Test-Nodes @($c) $w $stack) { $ok = $true; break } } }
            'NOT' { $ok = $true; foreach ($c in $n.Children) { if (Test-Nodes @($c) $w $stack) { $ok = $false; break } } }
            'custom_trigger_tooltip' { $ok = Test-Nodes @($n.Children | Where-Object Key -ne 'tooltip') $w $stack }
            'has_dlc' { $ok = $v.Trim('"') -in $w.Dlc }
            'has_intelligence_agency' { $ok = $v -eq 'yes' }
            'has_civil_war' { $ok = $v -eq 'no' }
            'tag' { $other = Resolve $v $w $stack; $ok = $s.Id -eq $other.Id }
            'exists' { $ok = $s.Exists -eq ($v -eq 'yes') }
            'has_capitulated' { $ok = $s.Capitulated -eq ($v -eq 'yes') }
            'is_ai' { $ok = $s.AI -eq ($v -eq 'yes') }
            'has_country_flag' { $ok = $s.Flags.ContainsKey($v) }
            'has_global_flag' { $ok = $w.Flags.ContainsKey($v) }
            'has_variable' { $ok = $s.Vars.ContainsKey($v) }
            'has_idea' { $ok = $v -in $s.Ideas }
            'has_country_leader_with_trait' { $ok = $v -in $s.Traits }
            'has_country_leader_ideology' { $ok = $v -eq $s.LeaderIdeology }
            'has_country_leader' { $ok = $s.Leader -eq (Val $n 'character') }
            'controls_state' { $ok = $w.States[$v].Controller -eq $s.Id }
            'is_controlled_by' { $other = Resolve $v $w $stack; $ok = $s.Controller -eq $other.Id }
            'nuclear_reactor' { $ok = $s.Reactor -gt [int]$v }
            'check_variable' {
                $c = $n.Children[0]
                if ($c.Key -eq 'var') {
                    $actual = Get-VariableValue (Val $n 'var') $w $stack
                    $value = [double](Val $n 'value')
                    $ok = switch (Val $n 'compare') {
                        'less_than_or_equals' { $actual -le $value }
                        'greater_than_or_equals' { $actual -ge $value }
                        default { throw "Unsupported comparison $(Val $n 'compare')" }
                    }
                } else {
                    $actual = Get-VariableValue $c.Key $w $stack
                    $ok = switch ($c.Op) { '>' { $actual -gt [double]$c.Value } '=' { $actual -eq [double]$c.Value } default { throw "Unsupported native comparison $($c.Op)" } }
                }
            }
            'any_country' { foreach ($c in $w.Countries.Values) { if ($c.Exists -and (Test-Nodes $n.Children $w (@($c) + $stack))) { $ok = $true; break } } }
            'any_of_scopes' {
                $array = Val $n 'array'; $body = @($n.Children | Where-Object Key -ne 'array')
                foreach ($c in $w.Arrays[$array]) { if (Test-Nodes $body $w (@($c) + $stack)) { $ok = $true; break } }
            }
            default {
                if ($triggers.ContainsKey($n.Key)) { $ok = (Test-Nodes $triggers[$n.Key].Children $w $stack) -eq ($v -eq 'yes') }
                else {
                    $scope = Resolve $n.Key $w $stack
                    if ($null -ne $scope) { $ok = Test-Nodes $n.Children $w (@($scope) + $stack) }
                    elseif ($n.Key.StartsWith('var:')) { $ok = $false }
                    else { throw "Unsupported predicate $($n.Key)" }
                }
            }
        }
        if (-not $ok) { return $false }
    }
    return $true
}
function Run-Nodes($nodes, $w, $stack) {
    $branch = $false
    foreach ($n in $nodes) {
        $s = $stack[0]; $v = $n.Value
        switch ($n.Key) {
            'if' {
                $limit = Prop $n 'limit' | Select-Object -First 1
                $branch = Test-Nodes $limit.Children $w $stack
                if ($branch) { Run-Nodes @($n.Children | Where-Object Key -ne 'limit') $w $stack }
            }
            'else' { if (-not $branch) { Run-Nodes $n.Children $w $stack }; $branch = $false }
            'set_country_flag' { $key = if ($v) { $v } else { Val $n 'flag' }; $s.Flags[$key] = $true }
            'clr_country_flag' { $s.Flags.Remove($v) }
            'set_global_flag' { $w.Flags[$v] = $true }
            'clr_global_flag' { $w.Flags.Remove($v) }
            'set_variable' {
                $c = $n.Children[0]; $value = Resolve $c.Value $w $stack
                if ($null -eq $value) { $value = [double]$c.Value }
                if ($c.Key.StartsWith('global.')) { $w.Vars[$c.Key.Substring(7)] = $value } else { $s.Vars[$c.Key] = $value }
            }
            'add_to_variable' { $c = $n.Children[0]; $s.Vars[$c.Key] = [double]$s.Vars[$c.Key] + [double]$c.Value }
            'add_to_array' {
                $c = $n.Children[0]; $value = Resolve $c.Value $w $stack
                $w.Arrays[$c.Key] = @(@($w.Arrays[$c.Key]) + @($value) | Where-Object { $null -ne $_ })
            }
            'for_each_scope_loop' {
                $array = Val $n 'array'; $body = @($n.Children | Where-Object Key -ne 'array')
                foreach ($c in $w.Arrays[$array]) { Run-Nodes $body $w (@($c) + $stack) }
            }
            'capital_scope' { Run-Nodes $n.Children $w (@($w.States[$s.Capital]) + $stack) }
            'add_political_power' { $s.PP += [double]$v }
            'add_manpower' { $s.Manpower += [double]$v }
            'add_country_leader_trait' { if ($v -notin $s.Traits) { $s.Traits += $v } }
            'add_stability' { $s.Stability += [double]$v }
            'country_event' { $s.Events += (Val $n 'id') }
            'add_opinion_modifier' { Assert ((Val $n 'modifier') -eq 'stole_gift_opinion') 'Unknown incident modifier'; $s.Incidents++ }
            'custom_effect_tooltip' { }
            'hidden_effect' { Run-Nodes $n.Children $w $stack }
            'add_tech_bonus' { $s.Vars['Bonuses'] = [int]$s.Vars['Bonuses'] + 1 }
            'HSM_BAR_refresh_case_outcomes' {
                Assert ($v -eq 'yes' -and $n.Children.Count -eq 0) 'Invalid outcome helper call'
                $s.Vars['OutcomeRefreshes'] = [int]$s.Vars['OutcomeRefreshes'] + 1
            }
            default {
                if ($effects.ContainsKey($n.Key)) {
                    Assert ($n.Value -eq 'yes' -and $n.Children.Count -eq 0) "Unsupported scripted-effect arguments: $($n.Key)"
                    Run-Nodes $effects[$n.Key].Children $w $stack
                } else {
                    $scope = Resolve $n.Key $w $stack
                    if ($null -eq $scope) { throw "Unsupported effect $($n.Key)" }
                    Run-Nodes $n.Children $w (@($scope) + $stack)
                }
            }
        }
    }
}
function Run($id, $w, $scope = $w.Root) { Run-Nodes $effects[$id].Children $w @($scope) }
function Valid($id, $w, $scope = $w.From) { return Test-Nodes $triggers[$id].Children $w @($scope) }
function Crown($w, $tag, $mode) {
    Run "HSM_BAR_case_crown_custody_$mode" $w $w.Countries[$tag]
    $w.Countries[$tag].Flags.HSM_BAR_case_crown_known = $true
    $w.Countries[$tag].Flags.HSM_BAR_case_crown_investigated = $true
    $w.Countries[$tag].Flags.HSM_BAR_case_crown_rumor = $true
}

function Decision-Allowed($id, $w) {
    foreach ($key in @('visible','available')) {
        $condition = Prop $decisions[$id] $key | Select-Object -First 1
        if ($condition -and -not (Test-Nodes $condition.Children $w @($w.Root))) { return $false }
    }
    return $true
}
function Finish-Decision($id, $w, $phase = 'remove_effect') {
    $body = Prop $decisions[$id] $phase | Select-Object -First 1
    Assert ($null -ne $body) "Missing $phase in $id"
    Run-Nodes $body.Children $w @($w.Root)
}
function Walk($nodes) {
    foreach ($node in $nodes) { $node; Walk $node.Children }
}
function Assert-NativeSyntax($nodes) {
    foreach ($node in (Walk $nodes)) {
        Assert (($node.Key + $node.Value) -notmatch '\$[A-Z_]+\$') 'Unsupported dollar parameter substitution'
        if ($effects.ContainsKey($node.Key)) {
            Assert ($node.Value -eq 'yes' -and $node.Children.Count -eq 0) "Unsupported scripted-effect arguments: $($node.Key)"
        }
        if ($node.Key -eq 'check_variable') {
            Assert (@($node.Children | Where-Object Op -in @('<=','>=')).Count -eq 0) 'Use native compare = less_than_or_equals / greater_than_or_equals'
        }
    }
}

Case 'exact-source overrides contain only tagged additive blocks' {
    foreach ($name in @('FantasyFlavorEvents.txt','Yale.txt','DreadLeague_Events.txt','CrystalEmpire.txt')) {
        $source = [IO.File]::ReadAllText((Join-Path $root "EaW/events/$name")).Replace("`r`n","`n")
        $copy = [IO.File]::ReadAllText((Join-Path $mod "events/$name")).Replace("`r`n","`n")
        $stripped = [regex]::Replace($copy, '(?ms)^[\t ]*# HSM_BAR_ANOMALY_BEGIN[^\n]*\n.*?^[\t ]*# HSM_BAR_ANOMALY_END[^\n]*\n', '')
        # A patch may add the missing final newline; native script content must still match exactly.
        Assert ($source.TrimEnd("`n") -ceq $stripped.TrimEnd("`n")) "Unmarked source changes: $name"
        $baseNodes = Read-Code (Join-Path $root "EaW/events/$name")
        $newNodes = Read-Code (Join-Path $mod "events/$name")
        $baseIds = @($baseNodes | Where-Object Key -in @('country_event','news_event') | ForEach-Object { Val $_ 'id' })
        $newIds = @($newNodes | Where-Object Key -in @('country_event','news_event') | ForEach-Object { Val $_ 'id' })
        Assert ($baseIds.Count -gt 10) "Source event enumeration failed: $name"
        Assert (($baseIds -join '|') -ceq ($newIds -join '|')) "Changed event IDs: $name"
    }
}
Case 'owned files parse; unique namespace; no native IDs duplicated by registry' {
    $ids = @{}
    foreach ($file in @(Get-ChildItem (Join-Path $mod 'common') -Recurse -Filter 'HSM_BAR_anomalies*.txt') + @(Get-ChildItem (Join-Path $mod 'events') -Filter 'HSM_BAR_anomalies*.txt')) {
        $nodes = Read-Code $file.FullName
        foreach ($n in $nodes | Where-Object Key -eq 'country_event') {
            $id = Val $n 'id'; Assert ($id.StartsWith('hsm_bar_anomaly.')) "Foreign namespace $id"
            Assert (-not $ids.ContainsKey($id)) "Duplicate $id"; $ids[$id] = $true
        }
    }
}
Case 'EN/RU UTF-8 BOM, key parity, descriptions and event references' {
    $sets = @()
    foreach ($lang in @('english','russian')) {
        $path = Join-Path $mod "localisation/$lang/HSM_BAR_anomalies_l_$lang.yml"
        $bytes = [IO.File]::ReadAllBytes($path)
        Assert (($bytes[0..2] -join ',') -eq '239,187,191') "Missing BOM: $lang"
        $text = [Text.UTF8Encoding]::new($false,$true).GetString($bytes)
        $keys = @{}
        foreach ($m in [regex]::Matches($text, '(?m)^ ([A-Za-z0-9_.]+):0 "(.+)"\r?$')) { Assert (-not $keys.ContainsKey($m.Groups[1].Value)) 'Duplicate localization'; $keys[$m.Groups[1].Value] = $m.Groups[2].Value }
        Assert ($keys.Count -ge 140) "Incomplete $lang"
        if ($lang -eq 'russian') {
            $outcomeText = [IO.File]::ReadAllText((Join-Path $mod "localisation/$lang/HSM_BAR_case_outcomes_l_$lang.yml"))
            $references = @{}
            foreach ($m in [regex]::Matches($outcomeText, '(?m)^ ([A-Za-z0-9_.]+):0 "(.+)"\r?$')) { $references[$m.Groups[1].Value] = $m.Groups[2].Value }
            foreach ($value in $keys.Values) {
                $resolved = [regex]::Replace($value, '\$(HSM_BAR_\w+)\$', {
                    param($match)
                    Assert ($references.ContainsKey($match.Groups[1].Value)) "Missing Russian reference: $($match.Value)"
                    return $references[$match.Groups[1].Value]
                })
                Assert ($resolved -match '[А-Яа-яЁё]') "Untranslated Russian: $value"
                Assert ($resolved -notmatch '\$HSM_BAR_') "Unresolved Russian reference: $resolved"
            }
        }
        $sets += ,$keys
    }
    Assert ((@($sets[0].Keys | Sort-Object) -join '|') -ceq (@($sets[1].Keys | Sort-Object) -join '|')) 'EN/RU key mismatch'
    $decisions = (Read-Code (Join-Path $mod 'common/decisions/HSM_BAR_anomalies.txt'))[0].Children
    foreach ($d in $decisions) { Assert ($sets[0].ContainsKey($d.Key)) "Missing decision name $($d.Key)"; Assert ($sets[0].ContainsKey($d.Key + '_desc')) "Missing description $($d.Key)" }
    $text = [IO.File]::ReadAllText((Join-Path $mod 'events/HSM_BAR_anomalies.txt'))
    foreach ($m in [regex]::Matches($text, '(?:title|text|name|desc)\s*=\s*(hsm_bar_anomaly\.[\w.]+)')) { Assert ($sets[0].ContainsKey($m.Groups[1].Value)) "Missing event localization $($m.Value)" }
}
Case 'initialization is idempotent and never gives BAR omniscient knowledge' {
    $w = New-World; Run 'HSM_BAR_anomalies_initialize' $w; Run 'HSM_BAR_anomalies_initialize' $w
    Assert ($w.Root.Events.Count -eq 0) 'Registry scheduled a redundant pulse'
    Assert (@($w.Root.Flags.Keys | Where-Object { $_ -match '_known|_investigated' }).Count -eq 0) 'Omniscient knowledge'
    Assert (-not $w.Flags.ContainsKey('HSM_BAR_case_phylactery_created')) 'Phylactery conjured'
    Assert (-not $w.Flags.ContainsKey('HSM_BAR_case_darkheart_created')) 'Dark Heart conjured'
    Assert (-not $w.Flags.ContainsKey('HSM_BAR_case_grover_returned')) 'Grover conjured'
    Assert ($w.States['624'].Reactor -eq 0) 'Reactor conjured'
}
Case 'field research focus gates operations and local surveys' {
    $w = New-World; $w.Root.Flags.Remove('HSM_BAR_field_research_open')
    Assert (-not (Valid 'HSM_BAR_operation_recon_target' $w)) 'Recon before field research'
    Run 'HSM_BAR_case_local_survey' $w
    Assert (-not $w.Root.Flags.ContainsKey('HSM_BAR_case_local_surveyed')) 'Survey before focus'
}
Case 'advanced focus mandates gate relic and remains work independently' {
    $w = New-World; Crown $w AAA museum; $w.From = $w.Countries.AAA
    $w.Root.Flags.Remove('HSM_BAR_foreign_mandate')
    Assert (-not (Valid 'HSM_BAR_operation_relic_target' $w)) 'Relics before foreign mandate'
    Assert (-not (Valid 'HSM_BAR_operation_recon_target' $w)) 'Recon before foreign mandate'
    $w.Root.Flags.HSM_BAR_foreign_mandate = $true
    $w.From = $w.Countries.YAL; $w.Root.Flags.HSM_BAR_case_grover_investigated = $true
    Run 'HSM_BAR_case_grover_bones_found' $w $w.From
    $w.Root.Flags.Remove('HSM_BAR_forensic_mandate')
    Assert (-not (Valid 'HSM_BAR_operation_remains_target' $w)) 'Remains before forensic mandate'
    $w.Root.Flags.HSM_BAR_forensic_mandate = $true
    Assert (Valid 'HSM_BAR_operation_remains_target' $w) 'Forensic mandate does not open confirmed remains'
}
Case 'local decision timers set concrete flags, report events and unlock one disposition' {
    foreach ($case in @('rock','titan','entity','amulet','plants')) {
        foreach ($outcome in @('protect','restrict')) {
            $w = New-World
            Finish-Decision 'HSM_BAR_case_local_survey' $w
            $id = "HSM_BAR_case_${case}_investigate"
            Assert (Decision-Allowed $id $w) "Investigation unavailable: $case"
            $w.States['624'].Controller = 'AAA'; Finish-Decision $id $w
            Assert (-not $w.Root.Flags.ContainsKey("HSM_BAR_case_${case}_investigated")) 'Investigation completed without access'
            Assert ($w.Root.Events[-1] -eq 'hsm_bar_anomaly.2') 'Failure lacks runtime report'
            $w.States['624'].Controller = 'BAR'
            Finish-Decision $id $w
            Assert $w.Root.Flags.ContainsKey("HSM_BAR_case_${case}_investigated") 'Investigation flag absent'
            Assert $w.Root.Flags.ContainsKey('HSM_BAR_case_last_operation_success') 'Success status absent'
            Assert (-not $w.Root.Flags.ContainsKey('HSM_BAR_case_last_operation_expired')) 'Success retained stale failure'
            $eventId = 'hsm_bar_anomaly.' + (11 + [array]::IndexOf(@('rock','titan','entity','amulet','plants'), $case))
            Assert ($w.Root.Events[-1] -eq $eventId -and $events.ContainsKey($eventId)) "Missing concrete report: $case"
            Assert (-not (Decision-Allowed $id $w)) 'Completed investigation remains available'
            $doctrine = if ($outcome -eq 'protect') { 'coexistence' } else { 'normalization' }
            $w.Root.Flags["HSM_BAR_$doctrine"] = $true
            $dispose = "HSM_BAR_case_${case}_$outcome"
            Assert (Decision-Allowed $dispose $w) 'Investigation did not unlock disposition'
            Finish-Decision $dispose $w 'complete_effect'; Finish-Decision $dispose $w 'complete_effect'
            Assert ($w.Root.Vars.HSM_BAR_case_completed -eq 1 -and $w.Root.Vars.OutcomeRefreshes -eq 1) 'Disposition reward repeated'
            Assert ($w.Root.Stability -eq 0 -and -not $w.Root.Vars.ContainsKey('Bonuses')) 'Retired lump-sum reward bypassed the aggregate spirit'
            Assert $w.Root.Flags.ContainsKey("HSM_BAR_case_${case}_$outcome") 'Disposition outcome missing'
        }
    }
}
Case 'recon and archives require occurred events and expire after custody changes' {
    $w = New-World
    Assert (-not (Valid 'HSM_BAR_operation_recon_target' $w)) 'Yale future plot exposed at start'
    Run 'HSM_BAR_case_grover_bones_found' $w $w.From
    Run 'HSM_BAR_operation_recon_complete' $w
    Assert $w.Root.Flags.ContainsKey('HSM_BAR_case_grover_known') 'Recon did not discover evidenced dossier'
    Assert (-not $w.Root.Flags.ContainsKey('HSM_BAR_case_herald_known')) 'Bones predicted the Herald'
    Assert (-not $w.Root.Flags.ContainsKey('HSM_BAR_case_grover_investigated')) 'Recon replaced archive investigation'
    $w.States['398'].Controller = 'AAA'; $w.States['665'].Controller = 'AAA'
    Run 'HSM_BAR_operation_archive_complete' $w
    Assert (-not $w.Root.Flags.ContainsKey('HSM_BAR_case_grover_investigated')) 'Expired archive target granted research'
    Assert $w.Root.Flags.ContainsKey('HSM_BAR_case_last_operation_expired') 'Expired archives not recorded'
    $w.From = $w.Countries.AAA; Run 'HSM_BAR_operation_recon_complete' $w; Run 'HSM_BAR_operation_archive_complete' $w
    Assert $w.Root.Flags.ContainsKey('HSM_BAR_case_grover_investigated') 'Current custodian archives unavailable'
}
Case 'artifact disposition requires the current storage site, not a stale secured flag' {
    $w = New-World; $w.Root.Flags.HSM_BAR_case_phylactery_investigated = $true
    $w.Flags.HSM_BAR_case_phylactery_secured = $true; $w.Vars.HSM_BAR_case_phylactery_site = $w.States['624']
    $nodes = Read-Code (Join-Path $mod 'common/decisions/HSM_BAR_anomalies.txt')
    $decision = $nodes[0].Children | Where-Object Key -eq 'HSM_BAR_case_phylactery_seal'
    $available = Prop $decision 'available' | Select-Object -First 1
    Assert (Test-Nodes $available.Children $w @($w.Root)) 'Owned vault inaccessible'
    $w.States['624'].Controller = 'AAA'
    Assert (-not (Test-Nodes $available.Children $w @($w.Root))) 'Captured vault still accessible'
}
Case 'crown archive receives a field report without acquiring any instance' {
    $w = New-World
    Run 'HSM_BAR_case_crown_custody_museum' $w $w.Countries.AAA
    Run 'HSM_BAR_case_crown_custody_sealed' $w $w.Countries.BBB
    $w.Countries.AAA.Flags.HSM_BAR_case_crown_rumor = $true
    $w.From = $w.Countries.AAA
    Run 'HSM_BAR_operation_recon_complete' $w
    Assert (-not $w.Root.Flags.ContainsKey('HSM_BAR_case_crown_investigated')) 'Recon granted an unearned field report'
    Run 'HSM_BAR_operation_archive_complete' $w
    Assert $w.Root.Flags.ContainsKey('HSM_BAR_case_crown_investigated') 'BAR archive did not receive the field report'
    Assert $w.Countries.AAA.Flags.ContainsKey('HSM_BAR_case_crown_investigated') 'Instance investigation was lost'
    Assert (-not $w.Countries.AAA.Flags.ContainsKey('HSM_BAR_case_crown_secured')) 'Archive operation acquired the crown'
    Assert ($w.Countries.AAA.Vars.HSM_BAR_case_crown_site.Id -eq '900') 'Archive operation moved the crown'
    Assert (-not $w.Countries.BBB.Flags.ContainsKey('HSM_BAR_case_crown_investigated')) 'An unrelated crown was investigated'
    $w = New-World
    Run 'HSM_BAR_case_crown_custody_museum' $w $w.Countries.AAA
    $w.Countries.AAA.Flags.HSM_BAR_case_crown_rumor = $true
    $w.From = $w.Countries.AAA
    Run 'HSM_BAR_operation_recon_complete' $w
    $w.Countries.AAA.Flags.HSM_BAR_case_crown_missing = $true
    Run 'HSM_BAR_operation_archive_complete' $w
    Assert (-not $w.Root.Flags.ContainsKey('HSM_BAR_case_crown_investigated')) 'Expired lead unlocked a field report'
}
Case 'museum and sealed crowns are independent, worn crown cannot be stolen' {
    $w = New-World; Crown $w AAA museum; Crown $w BBB sealed; Crown $w CCC leader
    $w.From = $w.Countries.AAA; Run 'HSM_BAR_operation_relic_complete' $w
    Assert ($w.Countries.AAA.Vars.HSM_BAR_case_crown_site.Id -eq '624') 'Museum not transferred'
    Assert ($w.Countries.BBB.Vars.HSM_BAR_case_crown_site.Id -eq '901') 'Other crown moved'
    Assert ($w.Countries.AAA.Incidents -eq 1) 'Custodian incident absent'
    $w.From = $w.Countries.BBB; Run 'HSM_BAR_operation_relic_complete' $w
    Assert ($w.Countries.BBB.Vars.HSM_BAR_case_crown_site.Id -eq '624') 'Sealed crown not transferred'
    $w.From = $w.Countries.CCC
    Assert (-not (Valid 'HSM_BAR_operation_relic_target' $w)) 'Worn crown stealable'
}
Case 'annexed crown origin retains record; live territorial custodian is targeted' {
    $w = New-World; Crown $w AAA museum; $w.Countries.AAA.Exists = $false; $w.States['900'].Controller = 'BBB'; $w.From = $w.Countries.BBB
    Assert (Valid 'HSM_BAR_operation_relic_target' $w) 'Annexation lost crown record'
    Run 'HSM_BAR_operation_relic_complete' $w
    Assert ($w.Countries.BBB.Incidents -eq 1) 'Incident targeted origin instead of custodian'
    Assert ($w.Countries.AAA.Vars.HSM_BAR_case_crown_site.Id -eq '624') 'Custody failed'
}
Case 'lost BAR vault removes access and does not collapse multiple crowns' {
    $w = New-World; Crown $w AAA museum; Crown $w BBB sealed
    $w.From = $w.Countries.AAA; Run 'HSM_BAR_operation_relic_complete' $w
    $w.From = $w.Countries.BBB; Run 'HSM_BAR_operation_relic_complete' $w
    $w.States['624'].Controller = 'CCC'; $w.From = $w.Countries.CCC
    Assert (Valid 'HSM_BAR_operation_relic_target' $w) 'Vault treated as eternally accessible to BAR'
    Assert ($w.Arrays['global.HSM_BAR_case_crowns'].Count -eq 2) 'Crowns collapsed'
}
Case 'leader loss makes worn crown unlocated, never a museum or a corpse' {
    $w = New-World; Crown $w AAA leader; Run 'HSM_BAR_anomalies_pulse' $w
    Assert $w.Countries.AAA.Flags.ContainsKey('HSM_BAR_case_crown_missing') 'Missing crown not invalidated'
    Assert (-not $w.Countries.AAA.Flags.ContainsKey('HSM_BAR_case_crown_museum')) 'Automatic museum'
    $w.From = $w.Countries.AAA; Assert (-not (Valid 'HSM_BAR_operation_remains_target' $w)) 'Leader became corpse'
}
Case 'changed target control produces no relic, reward or incident' {
    $w = New-World; Crown $w AAA museum; $w.From = $w.Countries.AAA
    Assert (Valid 'HSM_BAR_operation_relic_target' $w) 'Initial target invalid'
    $w.States['900'].Controller = 'BBB'; Run 'HSM_BAR_operation_relic_complete' $w
    Assert $w.Root.Flags.ContainsKey('HSM_BAR_case_last_operation_expired') 'Expired status absent'
    Assert ($w.Root.PP -eq 0 -and $w.Countries.AAA.Incidents -eq 0) 'False reward/incident'
    Assert ($w.Countries.AAA.Vars.HSM_BAR_case_crown_site.Id -eq '900') 'Expired extraction succeeded'
}
Case 'capitulation, annexation and office loss alone never create remains' {
    foreach ($mode in @('capitulation','annexation','office_loss')) {
        $w = New-World; $w.Root.Flags.HSM_BAR_case_grover_investigated = $true
        if ($mode -eq 'capitulation') { $w.From.Capitulated = $true }
        if ($mode -eq 'annexation') { $w.From.Exists = $false }
        $w.From.Leader = ''
        Run 'HSM_BAR_anomalies_pulse' $w; Run 'HSM_BAR_operation_remains_complete' $w
        Assert (-not $w.Flags.ContainsKey('HSM_BAR_case_grover_bones_secured')) "Body from $mode"
        Assert ($w.Root.PP -eq 0 -and $w.From.Incidents -eq 0) "False remains reward from $mode"
    }
}
Case 'positive Gamia bones can be recovered exactly once before resurrection' {
    $w = New-World; $w.Root.Flags.HSM_BAR_case_grover_investigated = $true
    Run 'HSM_BAR_case_grover_bones_found' $w $w.From
    Assert (Valid 'HSM_BAR_operation_remains_target' $w) 'Confirmed bones unavailable'
    Run 'HSM_BAR_operation_remains_complete' $w
    Assert $w.Flags.ContainsKey('HSM_BAR_case_grover_bones_secured') 'Bones not secured'
    Assert ($w.Root.PP -eq -20 -and $w.From.Incidents -eq 1) 'Theft incident missing'
    Run 'HSM_BAR_operation_remains_complete' $w
    Assert ($w.Root.PP -eq -20 -and $w.From.Incidents -eq 1) 'Repeated rewards/incident'
    Assert (-not $w.Flags.ContainsKey('HSM_BAR_case_grover_returned')) 'Registry resurrected Grover'
}
Case 'resurrection during preparation expires remains operation without rewards' {
    $w = New-World; $w.Root.Flags.HSM_BAR_case_grover_investigated = $true
    Run 'HSM_BAR_case_grover_bones_found' $w $w.From
    Run 'HSM_BAR_case_grover_returned' $w $w.From
    $w.From.Leader = 'YAL_emperor_grover_ii'
    Run 'HSM_BAR_operation_remains_complete' $w
    Assert (-not $w.Flags.ContainsKey('HSM_BAR_case_grover_bones_secured')) 'Living Grover kidnapped'
    Assert ($w.Root.PP -eq 0 -and $w.From.Incidents -eq 0) 'Expired remains reward'
}
Case 'native resurrection cannot reuse stolen bones, even in an already open event' {
    $w = New-World; $w.Flags.HSM_BAR_case_grover_bones_removed = $true
    $nodes = Read-Code (Join-Path $mod 'events/Yale.txt')
    $event = $nodes | Where-Object { $_.Key -eq 'country_event' -and (Val $_ 'id') -eq 'yale.30' }
    Assert ($null -ne $event) 'Missing yale.30'
    $trigger = Prop $event 'trigger' | Select-Object -First 1
    Assert (-not (Test-Nodes $trigger.Children $w @($w.From))) 'Queued native return unguarded'
    $option = Prop $event 'option' | Where-Object { (Val $_ 'name') -eq 'yale.30.a' }
    $trigger = Prop $option 'trigger' | Select-Object -First 1
    Assert (-not (Test-Nodes $trigger.Children $w @($w.From))) 'Open native option unguarded'
}
Case 'Herald disappearance, Sombra removal, Rosa execution, Grover retirement have no body' {
    foreach ($hook in @('HSM_BAR_case_herald_vanished','HSM_BAR_case_sombra_removed','HSM_BAR_case_rosa_executed','HSM_BAR_case_rosa_final_rest','HSM_BAR_case_grover_retired')) {
        $w = New-World; $w.Root.Flags.HSM_BAR_case_grover_investigated = $true; $w.Flags.HSM_BAR_case_sombra_returned = $true
        Run $hook $w $w.From; Run 'HSM_BAR_anomalies_pulse' $w
        Assert (-not (Valid 'HSM_BAR_operation_remains_target' $w)) "False corpse from $hook"
    }
}
Case 'creation is separate from existence, knowledge and live artifact custody' {
    $w = New-World; $w.From = $w.Countries.DED
    Run 'HSM_BAR_anomalies_initialize' $w
    Assert $w.Flags.ContainsKey('HSM_BAR_case_chalice_exists') 'Ancient Chalice absent'
    Assert (-not $w.Flags.ContainsKey('HSM_BAR_case_chalice_found')) 'Ancient Chalice already owned'
    Run 'HSM_BAR_case_chalice_found' $w $w.From; Run 'HSM_BAR_case_rosa_lich' $w $w.From
    Assert (-not (Valid 'HSM_BAR_operation_relic_target' $w)) 'Created means known'
    $w.Root.Flags.HSM_BAR_case_phylactery_investigated = $true
    Assert (Valid 'HSM_BAR_operation_relic_target' $w) 'Investigated physical phylactery unavailable'
    Run 'HSM_BAR_operation_relic_complete' $w
    Assert ($w.Vars.HSM_BAR_case_phylactery_site.Id -eq '624') 'Phylactery not transferred'
    Assert (-not $w.Flags.ContainsKey('HSM_BAR_case_rosa_executed')) 'Artifact extraction killed ruling Rosa'
    $w.States['624'].Controller = 'AAA'; $w.From = $w.Countries.AAA
    Assert (Valid 'HSM_BAR_operation_relic_target' $w) 'Phylactery custody stale after conquest'
}
Case 'destroyed Magehold and restored Crystal Empire invalidate unlocated relics' {
    $w = New-World; $w.From = $w.Countries.DED
    Run 'HSM_BAR_case_chalice_found' $w $w.From; Run 'HSM_BAR_case_rosa_lich' $w $w.From
    $w.Root.Flags.HSM_BAR_case_phylactery_investigated = $true
    Run 'HSM_BAR_case_magehold_destroyed' $w $w.From
    Assert (-not (Valid 'HSM_BAR_operation_relic_target' $w)) 'Destroyed cache still available'
    $w.From = $w.Countries.CRY; $w.Root.Flags.HSM_BAR_case_darkheart_investigated = $true
    Run 'HSM_BAR_case_sombra_returned' $w $w.From; Run 'HSM_BAR_case_sombra_removed' $w $w.From
    Assert (-not (Valid 'HSM_BAR_operation_relic_target' $w)) 'Unlocated Dark Heart available'
}
Case 'Titan defeat is not dismantling, and neither rebuilds a construct' {
    $w = New-World; $w.Root.Vars.titanHPmax = 200; $w.Root.Vars.titanHP = 0
    Run 'HSM_BAR_anomalies_pulse' $w
    Assert $w.Flags.ContainsKey('HSM_BAR_case_titan_defeated') 'Defeat ignored'
    Assert (-not $w.Flags.ContainsKey('HSM_BAR_case_titan_dismantled')) 'Defeat conflated with dismantling'
    $w.Root.Flags.HSM_BAR_titan_was_dismantled = $true; Run 'HSM_BAR_anomalies_pulse' $w
    Assert $w.Flags.ContainsKey('HSM_BAR_case_titan_dismantled') 'Confirmed dismantling ignored'
}
Case 'no resurrection, leader transfer, reactor construction or unsupported corpse producer in registry' {
    foreach ($file in @(Get-ChildItem (Join-Path $mod 'common/scripted_effects') -Filter 'HSM_BAR_anomalies*.txt') + @(Get-ChildItem (Join-Path $mod 'events') -Filter 'HSM_BAR_anomalies*.txt') + @(Get-ChildItem (Join-Path $mod 'common/decisions') -Filter 'HSM_BAR_anomalies*.txt')) {
        $code = [regex]::Replace([IO.File]::ReadAllText($file.FullName), '(?m)#.*$', '')
        Assert ($code -notmatch '\b(promote_character|recruit_character|create_country_leader|add_country_leader_role|set_nationality|kill_country_leader|construct_building|set_building_level|complete_national_focus)\s*=') "Forbidden manufacture/abduction in $($file.Name)"
    }
    $code = [IO.File]::ReadAllText((Join-Path $mod 'common/scripted_effects/HSM_BAR_anomalies.txt'))
    Assert ($code -notmatch 'set_(country|global)_flag\s*=\s*HSM_BAR_case_(rosa|herald|sombra)_(corpse|body|remains)_') 'Unsupported body producer'
}

Case 'native syntax audit rejects fixture-only parameter and comparison forms' {
    foreach ($effect in $effects.Values) { Assert-NativeSyntax $effect.Children }
    foreach ($decision in $decisions.Values) { Assert-NativeSyntax $decision.Children }
    foreach ($path in @('common/scripted_triggers/HSM_BAR_anomalies.txt','events/HSM_BAR_anomalies.txt')) {
        Assert-NativeSyntax (Read-Code (Join-Path $mod $path))
    }
    foreach ($bad in @('HSM_BAR_case_investigate_rock = { CASE = rock EVENT = 11 }','set_country_flag = HSM_BAR_case_$CASE$_investigated','check_variable = { titanHP <= 0 }','check_variable = { HSM_BAR_fixture_value >= 40 }')) {
        $rejected = $false
        try { Assert-NativeSyntax (Parse $bad) } catch { $rejected = $true }
        Assert $rejected "Invalid native syntax accepted: $bad"
    }
}
Case 'documented inclusive check_variable forms include equality at the boundary' {
    $w = New-World
    foreach ($value in @(39.99,40,40.01)) {
        $w.Root.Vars.HSM_BAR_fixture_value = $value
        foreach ($comparison in @('less_than_or_equals','greater_than_or_equals')) {
            $code = Parse "check_variable = { var = HSM_BAR_fixture_value value = 40 compare = $comparison }"
            Assert-NativeSyntax $code
            $expected = if ($comparison -eq 'less_than_or_equals') { $value -le 40 } else { $value -ge 40 }
            Assert ((Test-Nodes $code $w @($w.Root)) -eq $expected) "Incorrect $comparison boundary at $value"
        }
    }
}
Case 'all timed decisions separate explicit previews from runtime effects' {
    $timed = @($decisions.Values | Where-Object { Val $_ 'days_remove' })
    Assert ($timed.Count -eq 13) 'Timed decision coverage changed'
    $localization = [IO.File]::ReadAllText((Join-Path $mod 'localisation/english/HSM_BAR_anomalies_l_english.yml'))
    foreach ($decision in $timed) {
        $remove = Prop $decision 'remove_effect' | Select-Object -First 1
        Assert ($remove.Children.Count -eq 2) "Mixed preview and execution: $($decision.Key)"
        Assert ($remove.Children[0].Key -eq 'custom_effect_tooltip') 'Missing explicit completion preview'
        Assert ($remove.Children[1].Key -eq 'hidden_effect') 'Runtime branches leak into preview'
        Assert ($remove.Children[0].Value -eq ($decision.Key + '_result_tt')) 'Wrong preview'
        Assert ($localization.Contains(' ' + $remove.Children[0].Value + ':0 "')) 'Unlocalized preview'
    }
    Assert (@(Walk $effects.HSM_BAR_case_failed.Children | Where-Object Key -eq 'custom_effect_tooltip').Count -eq 0) 'Failure leaks into ordinary completion preview'
}
Case 'survey expiry permits retry and clears a stale success status' {
    $w = New-World; $w.Root.Flags.HSM_BAR_case_last_operation_success = $true
    $w.States['624'].Controller = 'AAA'; Finish-Decision 'HSM_BAR_case_local_survey' $w
    Assert (-not $w.Root.Flags.ContainsKey('HSM_BAR_case_last_operation_success')) 'Stale survey success'
    Assert (-not (Val $decisions.HSM_BAR_case_local_survey 'fire_only_once')) 'Expired survey permanently locked'
    $w.States['624'].Controller = 'BAR'
    Assert (Decision-Allowed 'HSM_BAR_case_local_survey' $w) 'Survey cannot be retried'
    Finish-Decision 'HSM_BAR_case_local_survey' $w
    Assert ($w.Root.Events[-1] -eq 'hsm_bar_anomaly.10') 'Survey report missing'
}
Case 'initial countries and historical existence never seed foreign recon' {
    $w = New-World; Run 'HSM_BAR_anomalies_initialize' $w
    foreach ($target in $w.Countries.Values) {
        $w.From = $target
        Assert (-not (Valid 'HSM_BAR_operation_recon_target' $w)) "Unfounded recon: $($target.Id)"
    }
    $w.From = $w.Countries.DED; Finish-Decision 'HSM_BAR_case_recon_expedition' $w
    Assert (-not $w.From.Flags.ContainsKey('HSM_BAR_case_surveyed')) 'Empty search marked as successful recon'
    Assert (@($w.Root.Flags.Keys | Where-Object { $_ -match '_known$' }).Count -eq 0) 'Future dossiers seeded'
    Assert $w.Root.Flags.ContainsKey('HSM_BAR_case_last_operation_expired') 'Empty recon did not fail'
}
Case 'new native events reopen recon without predicting phylactery, Herald or Sombra' {
    $w = New-World; $w.From = $w.Countries.DED
    Run 'HSM_BAR_case_chalice_found' $w $w.From
    Run 'HSM_BAR_operation_recon_complete' $w; Run 'HSM_BAR_operation_archive_complete' $w
    Assert $w.Root.Flags.ContainsKey('HSM_BAR_case_chalice_known') 'Existing Chalice undiscovered'
    Assert (-not $w.Root.Flags.ContainsKey('HSM_BAR_case_phylactery_known')) 'Chalice predicted phylactery'
    Assert (-not (Valid 'HSM_BAR_operation_recon_target' $w)) 'Completed lead endlessly reappears'
    Run 'HSM_BAR_case_rosa_lich' $w $w.From
    Assert (Valid 'HSM_BAR_operation_recon_target' $w) 'New phylactery hidden behind old survey'
    Run 'HSM_BAR_operation_recon_complete' $w; Run 'HSM_BAR_operation_archive_complete' $w
    Assert $w.Root.Flags.ContainsKey('HSM_BAR_case_phylactery_known') 'Manufactured phylactery undiscovered'
    Assert $w.Root.Flags.ContainsKey('HSM_BAR_case_rosa_investigated') 'New Rosa records blocked'
    $w.From = $w.Countries.YAL; Run 'HSM_BAR_case_grover_bones_found' $w $w.From
    Run 'HSM_BAR_operation_recon_complete' $w; Run 'HSM_BAR_operation_archive_complete' $w
    Assert (-not $w.Root.Flags.ContainsKey('HSM_BAR_case_herald_known')) 'Bones predicted Herald'
    Run 'HSM_BAR_case_herald_transformed' $w $w.From
    Assert (Valid 'HSM_BAR_operation_recon_target' $w) 'New Herald evidence hidden'
    Run 'HSM_BAR_operation_recon_complete' $w; Run 'HSM_BAR_operation_archive_complete' $w
    Assert $w.Root.Flags.ContainsKey('HSM_BAR_case_herald_investigated') 'New Herald archives blocked'
    $w.From = $w.Countries.CRY; Run 'HSM_BAR_case_darkheart_created' $w $w.From
    Run 'HSM_BAR_operation_recon_complete' $w; Run 'HSM_BAR_operation_archive_complete' $w
    Assert (-not $w.Root.Flags.ContainsKey('HSM_BAR_case_sombra_known')) 'Crystal predicted bodily return'
    Run 'HSM_BAR_case_sombra_returned' $w $w.From
    Assert (Valid 'HSM_BAR_operation_recon_target' $w) 'Actual Sombra return hidden'
}
Case 'recon follows sites through annexation and expires when the lead disappears' {
    $w = New-World; Run 'HSM_BAR_case_crown_custody_museum' $w $w.Countries.AAA
    $w.Countries.AAA.Flags.HSM_BAR_case_crown_rumor = $true
    $w.Countries.AAA.Exists = $false; $w.States['900'].Controller = 'BBB'; $w.From = $w.Countries.BBB
    Assert (Valid 'HSM_BAR_operation_recon_target' $w) 'Current crown custodian lacks recon'
    Finish-Decision 'HSM_BAR_case_recon_expedition' $w; Finish-Decision 'HSM_BAR_case_archive_expedition' $w
    Assert $w.Countries.AAA.Flags.ContainsKey('HSM_BAR_case_crown_investigated') 'Annexed-origin crown lost'
    Run 'HSM_BAR_case_crown_custody_sealed' $w $w.Countries.CCC; $w.States['902'].Controller = 'BBB'
    $w.Countries.CCC.Flags.HSM_BAR_case_crown_rumor = $true
    Assert (Valid 'HSM_BAR_operation_recon_target' $w) 'New crown in surveyed territory hidden'
    $w.Countries.CCC.Flags.HSM_BAR_case_crown_missing = $true
    Finish-Decision 'HSM_BAR_case_recon_expedition' $w
    Assert $w.Root.Flags.ContainsKey('HSM_BAR_case_last_operation_expired') 'Lost crown did not expire recon'
    Assert (-not $w.Countries.CCC.Flags.ContainsKey('HSM_BAR_case_crown_known')) 'Missing crown discovered'
    $w = New-World; Run 'HSM_BAR_case_darkheart_created' $w $w.Countries.CRY
    $w.Vars.HSM_BAR_case_darkheart_site = $w.States['901']; $w.From = $w.Countries.BBB
    Assert (Valid 'HSM_BAR_operation_recon_target' $w) 'Relocated artifact invisible'
    $w.From = $w.Countries.CRY
    Assert (-not (Valid 'HSM_BAR_operation_recon_target' $w)) 'Former artifact site gives recon'
}
Case 'native wrappers and fallback filters share actual target eligibility' {
    $operations = Read-Code (Join-Path $mod 'common/operations/HSM_BAR_operations.txt')
    foreach ($scenario in @('empty','crown','lost','capitulated','mandate','bones','returned','phylactery','unlocated','archives')) {
        $w = New-World
        switch ($scenario) {
            'crown' { Crown $w AAA museum; $w.From = $w.Countries.AAA }
            'lost' { Crown $w AAA museum; $w.From = $w.Countries.AAA; $w.States['900'].Controller = 'BBB' }
            'capitulated' { Crown $w AAA museum; $w.From = $w.Countries.AAA; $w.From.Capitulated = $true }
            'mandate' { Crown $w AAA museum; $w.From = $w.Countries.AAA; $w.Root.Flags.Remove('HSM_BAR_foreign_mandate') }
            'bones' { Run 'HSM_BAR_case_grover_bones_found' $w $w.From; $w.Root.Flags.HSM_BAR_case_grover_investigated = $true }
            'returned' { Run 'HSM_BAR_case_grover_returned' $w $w.From; $w.Root.Flags.HSM_BAR_case_grover_investigated = $true }
            'phylactery' { Run 'HSM_BAR_case_rosa_lich' $w $w.Countries.DED; $w.From = $w.Countries.DED; $w.Root.Flags.HSM_BAR_case_phylactery_investigated = $true }
            'unlocated' { Run 'HSM_BAR_case_rosa_lich' $w $w.Countries.DED; $w.From = $w.Countries.DED; $w.Flags.HSM_BAR_case_phylactery_unlocated = $true }
            'archives' { Run 'HSM_BAR_case_grover_bones_found' $w $w.From; Run 'HSM_BAR_operation_recon_complete' $w }
        }
        foreach ($kind in @('recon','archive','relic','remains')) {
            $expected = Valid "HSM_BAR_operation_$($kind)_target" $w
            $native = $operations | Where-Object Key -eq "HSM_BAR_operations_$kind"
            $visible = Prop $native 'visible' | Select-Object -First 1
            Assert (-not (Test-Nodes $visible.Children $w @($w.Root))) 'Human native duplicate remains visible'
            $w.Root.AI = $true
            foreach ($key in @('visible','requirements')) {
                $condition = Prop $native $key | Select-Object -First 1
                Assert ((Test-Nodes $condition.Children $w @($w.Root)) -eq $expected) "Native $kind/$key differs in $scenario"
            }
            $w.Root.AI = $false
            $w.Dlc = @()
            foreach ($key in @('target_trigger','visible','available')) {
                $condition = Prop $decisions["HSM_BAR_case_$($kind)_expedition"] $key | Select-Object -First 1
                Assert ((Test-Nodes $condition.Children $w @($w.Root)) -eq $expected) "Fallback $kind/$key differs in $scenario"
            }
            $w.Dlc = @('La Resistance','Gotterdammerung')
            $visible = Prop $decisions["HSM_BAR_case_$($kind)_expedition"] 'visible' | Select-Object -First 1
            Assert (-not (Test-Nodes $visible.Children $w @($w.Root))) 'DLC owner bypassed the agency through an expedition'
        }
    }
}
Case 'forensic timers report concrete results; expired evidence gives no credit or custody' {
    foreach ($case in @('chalice','phylactery','darkheart')) {
        foreach ($expire in @($false,$true)) {
            $w = New-World; $w.From = $w.Countries.DED
            $hook = if ($case -eq 'chalice') { 'chalice_found' } elseif ($case -eq 'phylactery') { 'rosa_lich' } else { 'darkheart_created' }
            if ($case -eq 'darkheart') { $w.From = $w.Countries.CRY }
            Run "HSM_BAR_case_$hook" $w $w.From
            Run 'HSM_BAR_operation_recon_complete' $w; Run 'HSM_BAR_operation_archive_complete' $w
            $id = "HSM_BAR_case_$($case)_investigate"
            Assert (Decision-Allowed $id $w) "Forensic decision unavailable: $case"
            if ($expire) {
                if ($case -eq 'chalice') { $w.Flags.Remove('HSM_BAR_case_chalice_found') }
                else { $w.Flags["HSM_BAR_case_$($case)_unlocated"] = $true }
            }
            Finish-Decision $id $w
            Assert ($w.Root.Flags.ContainsKey("HSM_BAR_case_$($case)_investigated") -eq (-not $expire)) "False forensic result: $case"
            $eventId = if ($expire) { 'hsm_bar_anomaly.2' } else { 'hsm_bar_anomaly.' + (16 + [array]::IndexOf(@('chalice','phylactery','darkheart'),$case)) }
            Assert ($w.Root.Events[-1] -eq $eventId -and $events.ContainsKey($eventId)) "Wrong forensic report: $case"
            Assert (-not $w.Flags.ContainsKey("HSM_BAR_case_$($case)_secured")) 'Forensics granted custody'
        }
    }
}
Case 'controlled archives require evidence and never seed future cases' {
    $w = New-World; $w.From = $w.Root; $w.States['415'].Controller = 'BAR'
    Assert (-not (Decision-Allowed 'HSM_BAR_case_occupied_archives' $w)) 'Empty occupied archive predicts plot'
    Run 'HSM_BAR_case_chalice_found' $w $w.Countries.DED
    Assert (Decision-Allowed 'HSM_BAR_case_occupied_archives' $w) 'Evidenced occupied archive unavailable'
    $immediate = Prop $events['hsm_bar_anomaly.4'] 'immediate' | Select-Object -First 1
    Run-Nodes $immediate.Children $w @($w.Root)
    Assert $w.Root.Flags.ContainsKey('HSM_BAR_case_chalice_known') 'Local archives missed Chalice'
    Assert (-not $w.Root.Flags.ContainsKey('HSM_BAR_case_phylactery_known')) 'Occupied archive predicted phylactery'
}
Case 'secret network effects never use retired institutional meters or repression flags' {
    $nodes = @($effects.Values | ForEach-Object { $_.Children }) + @($decisions.Values | ForEach-Object { $_.Children }) + @($events.Values | ForEach-Object { $_.Children })
    foreach ($node in (Walk $nodes)) {
        Assert (($node.Key + $node.Value) -notmatch 'HSM_BAR_(public_trust|capacity|repressive_methods)\b') 'Anomaly effect uses a retired Directorate meter or flag'
    }
}
Case 'all concrete report effects reference existing triggered events' {
    $nodes = @($effects.Values | ForEach-Object { $_.Children }) + @($decisions.Values | ForEach-Object { $_.Children })
    foreach ($node in (Walk $nodes | Where-Object Key -eq 'country_event')) {
        $id = Val $node 'id'
        Assert ($events.ContainsKey($id)) "Missing event $id"
        Assert ((Val $events[$id] 'is_triggered_only') -eq 'yes') "Untriggered report $id"
    }
}

Case 'native anomaly hooks use defined literal effects with no MODE argument blocks' {
    foreach ($file in @('FantasyFlavorEvents.txt','Yale.txt','DreadLeague_Events.txt','CrystalEmpire.txt')) {
        $hooks = @(Walk (Read-Code (Join-Path $mod "events/$file")) | Where-Object { $_.Key -match '^HSM_BAR_case_' })
        Assert ($hooks.Count -gt 0) "Missing anomaly hooks in $file"
        foreach ($hook in $hooks) {
            Assert $effects.ContainsKey($hook.Key) "Undefined anomaly effect $($hook.Key) in $file"
            Assert-NativeSyntax @($hook)
        }
    }
    $rejected = $false
    try { Assert-NativeSyntax (Parse 'HSM_BAR_case_crown_custody = { MODE = museum }') } catch { $rejected = $true }
    Assert $rejected 'Legacy MODE argument block accepted'
}
Case 'native Crown options select exclusive custody and preserve their original outcomes' {
    $native = Read-Code (Join-Path $mod 'events/FantasyFlavorEvents.txt')
    $discovery = $native | Where-Object { $_.Key -eq 'country_event' -and (Val $_ 'id') -eq 'fantasyflavor.14' }
    $discoveryHooks = @(Prop $discovery 'immediate' | ForEach-Object { $_.Children } | Where-Object Key -eq 'HSM_BAR_case_crown_found')
    Assert ($discoveryHooks.Count -eq 1) 'Missing or duplicate native Crown discovery hook'
    foreach ($case in @(
        @{ Event = 'fantasyflavor.15'; Option = 'fantasyflavor.15.a'; Mode = 'museum'; PP = 25; Manpower = 0; Stability = 0 },
        @{ Event = 'fantasyflavor.16'; Option = 'fantasyflavor.16.a'; Mode = 'sealed'; PP = -25; Manpower = -1; Stability = -0.025 },
        @{ Event = 'fantasyflavor.16'; Option = 'fantasyflavor.16.b'; Mode = 'leader'; PP = 50; Manpower = -1; Stability = 0 }
    )) {
        $event = $native | Where-Object { $_.Key -eq 'country_event' -and (Val $_ 'id') -eq $case.Event }
        $options = @(Prop $event 'option' | Where-Object { (Val $_ 'name') -eq $case.Option })
        Assert ($options.Count -eq 1) "Missing or duplicate native option $($case.Option)"
        $option = $options[0]
        $hook = @($option.Children | Where-Object { $_.Key -like 'HSM_BAR_case_crown_custody*' })
        Assert ($hook.Count -eq 1 -and $hook[0].Key -eq "HSM_BAR_case_crown_custody_$($case.Mode)") "Wrong custody hook in $($case.Option)"
        $w = New-World; $holder = $w.Countries.AAA; $w.Root = $holder
        Run-Nodes $discoveryHooks $w @($holder)
        foreach ($mode in @('museum','sealed','leader','missing')) { $holder.Flags["HSM_BAR_case_crown_$mode"] = $true }
        $gate = Prop $option 'trigger' | Select-Object -First 1
        if ($gate) {
            $holder.LeaderIdeology = 'magocracy'
            Assert ((Test-Nodes $gate.Children $w @($holder)) -eq ($case.Mode -eq 'leader')) 'Magocracy option gate changed'
            $holder.LeaderIdeology = 'conservatism'
            Assert ((Test-Nodes $gate.Children $w @($holder)) -eq ($case.Mode -eq 'sealed')) 'Non-magocracy option gate changed'
        }
        if ($case.Mode -eq 'leader') { $holder.LeaderIdeology = 'magocracy' }
        Run-Nodes @($option.Children | Where-Object Key -notin @('name','trigger')) $w @($holder)
        foreach ($mode in @('museum','sealed','leader','missing')) {
            Assert ($holder.Flags.ContainsKey("HSM_BAR_case_crown_$mode") -eq ($mode -eq $case.Mode)) "Non-exclusive $mode custody in $($case.Option)"
        }
        Assert ($holder.PP -eq $case.PP -and $holder.Manpower -eq $case.Manpower -and $holder.Stability -eq $case.Stability) 'Original native rewards changed'
        Assert (('crown_of_mind_control' -in $holder.Traits) -eq ($case.Mode -eq 'leader')) 'Native leader trait changed'
        Assert ($holder.Vars.HSM_BAR_case_crown_site.Id -eq '900') 'Crown site not recorded at recipient capital'
        Run-Nodes $hook $w @($holder)
        Assert ($w.Arrays['global.HSM_BAR_case_crowns'].Count -eq 1) 'Repeated custody hook duplicated the Crown'
        Assert (-not $holder.Flags.ContainsKey('HSM_BAR_case_crown_known')) 'Native event granted BAR knowledge'
        $w.Root = $w.Countries.BAR; $w.From = $holder
        $holder.Flags.HSM_BAR_case_crown_rumor = $true
        Run 'HSM_BAR_operation_recon_complete' $w; Run 'HSM_BAR_operation_archive_complete' $w
        Assert $holder.Flags.ContainsKey('HSM_BAR_case_crown_investigated') 'Native Crown did not reach the investigation chain'
        Assert ((Valid 'HSM_BAR_operation_relic_target' $w) -eq ($case.Mode -ne 'leader')) 'Crown extraction eligibility disagrees with native custody'
    }
}
Write-Output "Barrad anomaly checks: $passed passed; $($failed.Count) failed."
if ($failed.Count) { throw ($failed -join "`n") }
