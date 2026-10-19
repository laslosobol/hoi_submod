#Requires -Version 7.2
param(
    [string] $GameRoot = 'C:/shit/Steam/steamapps/common/Hearts of Iron IV',
    [string] $EaWRoot = 'C:/shit/Steam/steamapps/workshop/content/394360/1826643372'
)
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$mod = Join-Path $root 'mod/HoISubmod'
$passed = 0
function Assert([bool] $condition, [string] $message) {
    if (-not $condition) { throw $message }
    $script:passed++
}

# Parse Clausewitz blocks, retaining repeated keys such as prerequisites and options.
function Parse-Code([string] $text) {
    $state = @{
        Tokens = @([regex]::Matches($text, '"(?:\\.|[^"\\])*"|#[^\r\n]*|[{}=<>]|[^\s{}=<>#"]+') |
            ForEach-Object { $_.Value } | Where-Object { -not $_.StartsWith('#') })
        Position = 0
    }
    return ,(Read-Block $state $false)
}
function Read-Block($state, [bool] $nested) {
    $items = [System.Collections.Generic.List[object]]::new()
    while ($state.Position -lt $state.Tokens.Count) {
        $key = $state.Tokens[$state.Position++]
        if ($key -eq '}') {
            if (-not $nested) { throw 'Unexpected closing brace' }
            return ,$items.ToArray()
        }
        $op = $state.Tokens[$state.Position++]
        if ($op -notin @('=', '<', '>')) { throw "Missing operator after $key" }
        $value = $state.Tokens[$state.Position++]
        if ($value -eq '{') { $value = Read-Block $state $true }
        $items.Add([pscustomobject]@{ Key = $key; Op = $op; Value = $value })
    }
    if ($nested) { throw 'Unclosed block' }
    return ,$items.ToArray()
}
function Nodes($body, [string] $key) { @($body | Where-Object Key -eq $key) }
function Scalar($body, [string] $key) { (Nodes $body $key | Select-Object -First 1).Value }
function Walk($body) {
    foreach ($node in $body) {
        $node
        if ($node.Value -is [array]) { Walk $node.Value }
    }
}

$files = @(Get-ChildItem $mod -Recurse -Filter 'HSM_BAR_collegium*.txt')
$parsed = @{}
foreach ($file in $files) { $parsed[$file.Name] = Parse-Code ([IO.File]::ReadAllText($file.FullName)) }
Assert ($files.Count -eq 8) 'Expected eight owned Clausewitz files'
$allNodes = @($parsed.Values | ForEach-Object { Walk $_ })
$focusFile = $parsed['HSM_BAR_collegium.txt']
$focus = @{}
foreach ($node in (Nodes $focusFile 'shared_focus')) {
    $id = Scalar $node.Value 'id'
    Assert (-not $focus.ContainsKey($id)) "Duplicate focus $id"
    $focus[$id] = $node.Value
}
$trees = @{}
foreach ($node in (Nodes $focusFile 'focus_tree')) { $trees[(Scalar $node.Value 'id')] = $node.Value }
Assert ($focus.Count -eq 37 -and $trees.Count -eq 2) 'Expected 37 Collegium focuses and two trees'
$first = @((Nodes $trees.HSM_BAR_collegium_tree 'shared_focus').Value)
$future = @((Nodes $trees.HSM_BAR_collegium_future_tree 'shared_focus').Value)
Assert ($first.Count -eq 21 -and $future.Count -eq 40) 'Tree membership count changed'
Assert (@($first | Where-Object { $_ -notin $future }).Count -eq 0) 'Future tree loses first-stage content'
foreach ($tree in $trees.Values) {
    Assert (@((Nodes $tree 'shared_focus') | Where-Object Value -eq 'HSM_BAR_common_reconstruction').Count -eq 1) 'Common root missing or duplicated'
    foreach ($external in @('HSM_BAR_civic_republic', 'HSM_BAR_mtc_frontiers')) {
        Assert (@((Nodes $tree 'shared_focus') | Where-Object Value -eq $external).Count -eq 1) "$external root missing or duplicated"
    }
}
$positions = @{}
foreach ($id in $focus.Keys) {
    $body = $focus[$id]
    Assert ((Scalar $body 'cost') -in @('4','5')) "$id is not 28/35 days"
    $x = [int](Scalar $body 'x')
    $y = [int](Scalar $body 'y')
    Assert ($x -ge 0 -and $x -le 20) "$id encroaches on the common branch"
    Assert (-not $positions.ContainsKey("$x,$y")) "Overlapping focus coordinates: $id"
    $positions["$x,$y"] = $id
    foreach ($prerequisite in (Nodes $body 'prerequisite')) {
        foreach ($ref in $prerequisite.Value) { Assert ($focus.ContainsKey($ref.Value)) "Missing prerequisite $($ref.Value)" }
    }
}
Assert ((Nodes $focus.HSM_BAR_collegium_future_root 'prerequisite').Count -eq 0) 'Second-stage root must not auto-attach to the first stage'
$closure = [Collections.Generic.HashSet[string]]::new([string[]]@($first))
do {
    $changed = $false
    foreach ($id in $focus.Keys) {
        $parents = @((Nodes $focus[$id] 'prerequisite') | ForEach-Object { $_.Value.Value })
        if (@($parents | Where-Object { $closure.Contains($_) }).Count -gt 0) {
            if ($closure.Add($id)) { $changed = $true }
        }
    }
} while ($changed)
Assert (@($closure | Where-Object { $_ -notin $first }).Count -eq 0) 'Stage-two content leaks into shared descendants of stage one'
$loads = @($allNodes | Where-Object Key -eq 'load_focus_tree')
Assert ($loads.Count -eq 1 -and (Scalar $loads[0].Value 'keep_completed') -eq 'yes') 'Stage transition must preserve completion'

$events = @{}
foreach ($node in (Nodes $parsed['HSM_BAR_collegium_events.txt'] 'country_event')) {
    $id = Scalar $node.Value 'id'
    Assert (-not $events.ContainsKey($id)) "Duplicate scene $id"
    $events[$id] = $node.Value
}
Assert ($events.Count -eq 24) 'Expected 24 meaningful scenes'
$eventCalls = @($allNodes | Where-Object { $_.Key -eq 'country_event' -and (Scalar $_.Value 'title') -eq $null })
foreach ($call in $eventCalls) { Assert ($events.ContainsKey((Scalar $call.Value 'id'))) 'Unresolved scene call' }
foreach ($id in $events.Keys) {
    Assert (@($eventCalls | Where-Object { (Scalar $_.Value 'id') -eq $id }).Count -gt 0) "Unreachable scene $id"
    Assert ((Scalar $events[$id] 'is_triggered_only') -eq 'yes') "Uncontrolled event $id"
}
$decisions = (Nodes $parsed['HSM_BAR_collegium_decisions.txt'] 'HSM_BAR_collegium_programs')[0].Value
Assert ($decisions.Count -eq 11) 'Expected eleven programmes/policy decisions, with petition grinding removed'
Assert (@($decisions | Where-Object Key -eq 'HSM_BAR_collegium_hear_petitions').Count -eq 0) 'Retired petition grinder remains'
Assert (@($allNodes | Where-Object { $_.Key -match '^(set_global_flag|clr_global_flag|set_politics|promote_character|retire_character|add_country_leader_role)$' }).Count -eq 0) 'Owned files changed global state or leadership'

$locales = @{}
foreach ($language in @('english','russian')) {
    $path = Join-Path $mod "localisation/$language/HSM_BAR_collegium_l_$language.yml"
    $bytes = [IO.File]::ReadAllBytes($path)
    Assert ([Convert]::ToHexString($bytes[0..2]) -eq 'EFBBBF') "$language needs a UTF-8 BOM"
    $text = [Text.UTF8Encoding]::new($false, $true).GetString($bytes)
    $entries = @{}
    foreach ($line in ($text -split '\r?\n' | Select-Object -Skip 1)) {
        if (-not $line.Trim()) { continue }
        Assert ($line -match '^ ([A-Za-z0-9_.]+):0 "(.*)"$') "Malformed localisation: $line"
        $key = $Matches[1]
        Assert (-not $entries.ContainsKey($key)) "Duplicate localisation $key"
        $entries[$key] = $Matches[2]
    }
    $locales[$language] = $entries
}
Assert (@(Compare-Object @($locales.english.Keys) @($locales.russian.Keys)).Count -eq 0) 'EN/RU keys differ'
$required = [Collections.Generic.HashSet[string]]::new()
foreach ($id in $focus.Keys) { [void]$required.Add($id); [void]$required.Add($id + '_desc') }
foreach ($d in $decisions) { [void]$required.Add($d.Key); [void]$required.Add($d.Key + '_desc') }
foreach ($n in $allNodes) {
    if ($n.Key -in @('title','desc','text','name','tooltip','custom_effect_tooltip','has_country_flag','set_country_flag','clr_country_flag','flag','add_ideas','remove_ideas')) {
        if ($n.Value -is [string] -and $n.Value -match '^HSM_BAR_collegium[_.]') { [void]$required.Add($n.Value) }
    }
}
foreach ($key in $required) { Assert ($locales.english.ContainsKey($key)) "Missing owned localisation: $key" }

# Resolve inherited and local artwork in dependency order.
$sprites = @{}
$textures = @{}
foreach ($base in @($GameRoot, $EaWRoot, $mod)) {
    foreach ($file in (Get-ChildItem (Join-Path $base 'interface') -Recurse -Filter '*.gfx')) {
        $text = [IO.File]::ReadAllText($file.FullName)
        foreach ($match in [regex]::Matches($text, '(?i)\bname\s*=\s*"?([A-Za-z0-9_]+)"?')) { $sprites[$match.Groups[1].Value] = $true }
        foreach ($match in [regex]::Matches($text, '(?is)\bname\s*=\s*"?([A-Za-z0-9_]+)"?[^{}]*?\btexturefile\s*=\s*"([^"]+)"')) {
            $textures[$match.Groups[1].Value] = Join-Path $base $match.Groups[2].Value
        }
    }
}
foreach ($body in $focus.Values) {
    $icon = Scalar $body 'icon'
    Assert ($sprites.ContainsKey($icon) -and $sprites.ContainsKey($icon + '_shine')) "Missing focus sprite or shine: $icon"
    Assert ($textures.ContainsKey($icon) -and (Test-Path -LiteralPath $textures[$icon])) "Missing focus bitmap: $icon"
}
foreach ($icon in @('GFX_idea_BAR_science_party','GFX_idea_BAR_science_party2','GFX_event_gothic_interior')) {
    Assert ($sprites.ContainsKey($icon)) "Missing inherited art: $icon"
}

# Small interpreter for owned effects/conditions; this is a static model, not the game engine.
$effects = @{}
foreach ($node in $parsed['HSM_BAR_collegium_effects.txt']) { $effects[$node.Key] = $node.Value }
$triggers = @{}
foreach ($node in $parsed['HSM_BAR_collegium_triggers.txt']) { $triggers[$node.Key] = $node.Value }
$dynamicModifiers = @{}
foreach ($node in $parsed['HSM_BAR_collegium_modifiers.txt']) { $dynamicModifiers[$node.Key] = $node.Value }
function Reset-Model([string] $choice = 'first') {
    $script:model = @{
        Vars = @{}
        Manpower = 1000; Equipment = 1000; Factories = 3; PP = 10000; Stability = 0
        TechBonuses = [Collections.Generic.List[string]]::new()
        Flags = @{ HSM_BAR_active = -1; HSM_BAR_collegium = -1 }
        Ideas = [Collections.Generic.HashSet[string]]::new()
        Done = [Collections.Generic.HashSet[string]]::new()
        # The shared social survey and civic government have their own strict suites.
        ExternalDone = [Collections.Generic.HashSet[string]]::new([string[]]@('HSM_BAR_common_reconstruction','HSM_BAR_civic_cabinet'))
        Tag = 'BAR'; OriginalTag = 'BAR'; Capitulated = $false; Subject = $false
        Owned = [Collections.Generic.HashSet[string]]::new([string[]]@('624'))
        Controlled = [Collections.Generic.HashSet[string]]::new([string[]]@('624'))
        Infrastructure = 0; StateScope = $null
        Modifiers = @{}; ModifierUpdates = 0
        Day = 0; War = $false; Tree = 'HSM_BAR_collegium_tree'; Choice = $choice; Dynamic = 0
    }
}
function Has-Flag([string] $key) {
    $model.Flags.ContainsKey($key) -and ($model.Flags[$key] -eq -1 -or $model.Flags[$key] -gt $model.Day)
}
function Number($value) {
    $n = 0.0
    if ([double]::TryParse([string]$value, [Globalization.NumberStyles]::Float, [Globalization.CultureInfo]::InvariantCulture, [ref]$n)) { return $n }
    if ($model.Vars.ContainsKey($value)) { return $model.Vars[$value] }
    return 0.0
}
function Cache-Modifier([string] $name) {
    if (-not $dynamicModifiers.ContainsKey($name)) { throw "Unmodelled dynamic modifier $name" }
    $values = @{}
    foreach ($n in $dynamicModifiers[$name]) {
        if ($n.Key -in @('icon','enable','remove_trigger')) { continue }
        if ($n.Value -is [array]) { throw "Unmodelled modifier value $($n.Key)" }
        $values[$n.Key] = Number $n.Value
    }
    $model.Modifiers[$name] = $values
}
function Assert-ModifierCache {
    foreach ($name in @($model.Modifiers.Keys)) {
        foreach ($n in $dynamicModifiers[$name]) {
            if ($n.Key -in @('icon','enable','remove_trigger')) { continue }
            Assert ([Math]::Abs($model.Modifiers[$name][$n.Key] - (Number $n.Value)) -lt 0.000000001) "Stale cached modifier: $name / $($n.Key)"
        }
    }
}
function Conditions($body) {
    foreach ($n in $body) { if (-not (Condition $n)) { return $false } }
    return $true
}
function Condition($n) {
    switch ($n.Key) {
        'OR' { return @($n.Value | Where-Object { Condition $_ }).Count -gt 0 }
        'AND' { return Conditions $n.Value }
        'NOT' { return @($n.Value | Where-Object { Condition $_ }).Count -eq 0 }
        'custom_trigger_tooltip' { return Conditions @($n.Value | Where-Object Key -ne 'tooltip') }
        'has_country_flag' { return Has-Flag $n.Value }
        'has_dynamic_modifier' {
            $name = if ($n.Value -is [array]) { Scalar $n.Value 'modifier' } else { $n.Value }
            return $model.Modifiers.ContainsKey($name)
        }
        'original_tag' { return $n.Value -eq $model.OriginalTag }
        'tag' { return $n.Value -eq $model.Tag }
        'has_capitulated' { return $model.Capitulated -eq ($n.Value -eq 'yes') }
        'is_subject' { return $model.Subject -eq ($n.Value -eq 'yes') }
        'owns_state' { return $model.Owned.Contains($n.Value) }
        'controls_state' { return $model.Controlled.Contains($n.Value) }
        'has_completed_focus' { return $model.Done.Contains($n.Value) -or $model.ExternalDone.Contains($n.Value) }
        'has_war' { return $model.War -eq ($n.Value -eq 'yes') }
        'always' { return $n.Value -eq 'yes' }
        'has_manpower' { Assert ($n.Op -eq '>') 'Unknown manpower operator'; return $model.Manpower -gt [int]$n.Value }
        'has_equipment' { Assert ($n.Value[0].Key -eq 'support_equipment' -and $n.Value[0].Op -eq '>') 'Unknown equipment check'; return $model.Equipment -gt [int]$n.Value[0].Value }
        'num_of_civilian_factories_available_for_projects' { Assert ($n.Op -eq '>') 'Unknown factory operator'; return $model.Factories -gt [int]$n.Value }
        'check_variable' {
            $a = Number (Scalar $n.Value 'var')
            $b = Number (Scalar $n.Value 'value')
            switch (Scalar $n.Value 'compare') {
                'greater_than_or_equals' { return $a -ge $b }
                'less_than' { return $a -lt $b }
                default { throw 'Unsupported comparison in static model' }
            }
        }
        default {
            if ($triggers.ContainsKey($n.Key)) { Assert ($n.Value -in @('yes','no')) 'Unsupported scripted-trigger argument block'; return (Conditions $triggers[$n.Key]) -eq ($n.Value -eq 'yes') }
            throw "Unmodelled trigger $($n.Key)"
        }
    }
}
function Apply($body) {
    $lastIf = $false
    foreach ($n in $body) {
        switch ($n.Key) {
            'if' {
                $lastIf = Conditions (Scalar $n.Value 'limit')
                if ($lastIf) { Apply @($n.Value | Where-Object Key -ne 'limit') }
            }
            'else' { if (-not $lastIf) { Apply $n.Value } }
            'hidden_effect' { Apply $n.Value }
            '624' {
                $previousScope = $model.StateScope
                $model.StateScope = '624'
                Apply $n.Value
                $model.StateScope = $previousScope
            }
            'add_building_construction' {
                Assert ($model.StateScope -eq '624') 'Land works must remain in the homeland'
                Assert ((Scalar $n.Value 'type') -eq 'infrastructure') 'Unexpected building in the Collegium model'
                Assert ((Scalar $n.Value 'instant_build') -eq 'yes') 'Unmodelled construction schedule'
                $model.Infrastructure += [int](Scalar $n.Value 'level')
            }
            'set_country_flag' {
                if ($n.Value -is [array]) {
                    $days = Scalar $n.Value 'days'
                    $model.Flags[(Scalar $n.Value 'flag')] = if ($days) { $model.Day + [int]$days } else { -1 }
                } else { $model.Flags[$n.Value] = -1 }
            }
            'clr_country_flag' { $model.Flags.Remove($n.Value) }
            'set_variable' { $model.Vars[$n.Value[0].Key] = Number $n.Value[0].Value }
            'clear_variable' {
                if ($n.Value -isnot [string] -or $n.Value -notmatch '^HSM_BAR_\w+$') { throw 'Expected scalar Barrad variable name' }
                $model.Vars.Remove($n.Value)
            }
            'add_to_variable' { $model.Vars[$n.Value[0].Key] = (Number $n.Value[0].Key) + (Number $n.Value[0].Value) }
            'subtract_from_variable' { $model.Vars[$n.Value[0].Key] = (Number $n.Value[0].Key) - (Number $n.Value[0].Value) }
            'multiply_variable' { $model.Vars[$n.Value[0].Key] = (Number $n.Value[0].Key) * (Number $n.Value[0].Value) }
            'clamp_variable' {
                $key = Scalar $n.Value 'var'
                $model.Vars[$key] = [Math]::Clamp((Number $key), (Number (Scalar $n.Value 'min')), (Number (Scalar $n.Value 'max')))
            }
            'add_ideas' { [void]$model.Ideas.Add($n.Value) }
            'remove_ideas' { [void]$model.Ideas.Remove($n.Value) }
            'add_dynamic_modifier' { Cache-Modifier (Scalar $n.Value 'modifier'); $model.Dynamic++ }
            'force_update_dynamic_modifier' {
                if ($n.Value -ne 'yes') { throw 'Expected force_update_dynamic_modifier = yes' }
                foreach ($name in @($model.Modifiers.Keys)) { Cache-Modifier $name }
                $model.ModifierUpdates++
            }
            'load_focus_tree' { $model.Tree = Scalar $n.Value 'tree' }
            'country_event' {
                $options = @((Nodes $events[(Scalar $n.Value 'id')] 'option') | Where-Object {
                    Conditions (Scalar $_.Value 'trigger')
                })
                Assert ($options.Count -gt 0) 'Event has no available option'
                $pick = if ($model.Choice -eq 'first') { $options[0] } else { $options[-1] }
                Apply @($pick.Value | Where-Object { $_.Key -notin @('name','trigger','ai_chance') })
            }
            'add_political_power' { $model.PP += [double]$n.Value }
            'add_stability' { $model.Stability += [double]$n.Value }
            'add_manpower' { $model.Manpower += [int]$n.Value }
            'add_equipment_to_stockpile' { Assert ((Scalar $n.Value 'type') -eq 'support_equipment') 'Unknown stockpile'; $model.Equipment += [int](Scalar $n.Value 'amount') }
            'add_tech_bonus' { $model.TechBonuses.Add((Scalar $n.Value 'name')) }
            'custom_effect_tooltip' {}
            default {
                if ($effects.ContainsKey($n.Key)) { Apply $effects[$n.Key] }
                else { throw "Unmodelled effect $($n.Key)" }
            }
        }
    }
}
function Can-Complete([string] $id) {
    if ($model.Done.Contains($id)) { return $false }
    $body = $focus[$id]
    foreach ($group in (Nodes $body 'prerequisite')) {
        if (@($group.Value | Where-Object { $model.Done.Contains($_.Value) }).Count -eq 0) { return $false }
    }
    foreach ($group in (Nodes $body 'mutually_exclusive')) {
        if (@($group.Value | Where-Object { $model.Done.Contains($_.Value) }).Count -gt 0) { return $false }
    }
    return Conditions (Scalar $body 'available')
}

foreach ($choice in @('first','last')) {
    foreach ($ending in @('open','republic','tutelage')) {
        Reset-Model $choice
        Apply $effects.HSM_BAR_collegium_initialize
        Apply $effects.HSM_BAR_collegium_initialize
        Assert ($model.Dynamic -eq 1) 'Initialize is not idempotent'
        $rounds = 0
        while (-not $model.Done.Contains('HSM_BAR_collegium_students') -and $rounds++ -lt 50) {
            $progress = $false
            foreach ($id in @((Nodes $trees[$model.Tree] 'shared_focus').Value)) {
                if ($id -in @('HSM_BAR_common_reconstruction','HSM_BAR_civic_republic','HSM_BAR_mtc_frontiers')) { continue }
                if ($id -in @('HSM_BAR_collegium_open','HSM_BAR_collegium_republic','HSM_BAR_collegium_tutelage') -and $id -ne "HSM_BAR_collegium_$ending") { continue }
                if (Can-Complete $id) {
                    [void]$model.Done.Add($id)
                    Apply (Scalar $focus[$id] 'completion_reward')
                    Assert-ModifierCache
                    $model.Day += [int](Scalar $focus[$id] 'cost') * 7
                    $progress = $true
                }
            }
            Assert $progress "$choice/$ending stalled without meter grinding or optional paid decisions"
        }
        Assert ($model.Done.Contains('HSM_BAR_collegium_students')) "$choice/$ending cannot reach the epilogue without DLC"
        Assert ($model.Done.Count -eq 31) "$choice/$ending lost earlier content or skipped a required focus"
        Assert ($model.Ideas.Count -eq 1 -and $model.Ideas.Contains("HSM_BAR_collegium_${ending}_spirit")) 'Constitution spirits stack or fail to replace'
        Assert ($model.Tree -eq 'HSM_BAR_collegium_future_tree') 'Transition did not load the future tree'
    }
}
# No usable shared meters, hidden substitutes or numeric progress gates in owned runtime.
foreach ($file in $files) {
    $source = [IO.File]::ReadAllText($file.FullName)
    Assert ($source -notmatch 'HSM_BAR_(public_trust|capacity)\b|HSM_BAR_collegium_(trust|capacity)_(plus|minus)_\d+_tt|HSM_BAR_collegium_monthly_tick') "Retired meter reference in $($file.Name)"
}
foreach ($language in @('english','russian')) {
    Assert (@($locales[$language].Keys | Where-Object { $_ -match '^HSM_BAR_(public_trust|capacity)$|^HSM_BAR_collegium_(trust|capacity)_(plus|minus)_\d+_tt$' }).Count -eq 0) 'Retired meter localization survives'
    Assert ($locales[$language].HSM_BAR_collegium_programs_desc -notmatch '\[\?|/100') 'Category still displays a score'
}
Assert (@($allNodes | Where-Object Key -eq 'check_variable').Count -eq 0) 'Institutional progress still depends on a numeric variable'
$outputs = @('HSM_BAR_collegium_stability','HSM_BAR_collegium_research','HSM_BAR_collegium_construction','HSM_BAR_collegium_supply','HSM_BAR_collegium_recovery')
foreach ($n in @($allNodes | Where-Object { $_.Key -in @('set_variable','add_to_variable','subtract_from_variable','multiply_variable','clamp_variable') })) {
    Assert ($n.Key -in @('set_variable','add_to_variable') -and $n.Value.Count -eq 1 -and $n.Value[0].Key -in $outputs) 'Hidden replacement score or upkeep'
}
Reset-Model
Apply $effects.HSM_BAR_collegium_initialize
foreach ($v in $outputs) { Assert ((Number $v) -eq 0) 'Unbuilt service grants a benefit' }
$milestones = @{
    HSM_BAR_collegium_independent_archive = @('HSM_BAR_collegium_stability', 0.03, 'archive')
    HSM_BAR_collegium_inspectors = @('HSM_BAR_collegium_stability', 0.03, 'inspection')
    HSM_BAR_collegium_clinic_access = @('HSM_BAR_collegium_stability', 0.04, 'access')
    HSM_BAR_collegium_clinic_followup = @('HSM_BAR_collegium_research', 0.02, 'followup')
    HSM_BAR_collegium_school_open = @('HSM_BAR_collegium_research', 0.03, 'school')
    HSM_BAR_collegium_research_board = @('HSM_BAR_collegium_research', 0.02, 'board')
    HSM_BAR_collegium_peer_review = @('HSM_BAR_collegium_research', 0.03, 'review')
    HSM_BAR_collegium_cohort_trained = @('HSM_BAR_collegium_research', 0.03, 'cohort')
    HSM_BAR_collegium_grid_workshops = @('HSM_BAR_collegium_research', 0.02, 'workshop_hours')
    HSM_BAR_grid_program = @('HSM_BAR_collegium_construction', 0.05, 'grid')
    HSM_BAR_collegium_grid_households = @('HSM_BAR_collegium_construction', 0.05, 'households')
    HSM_BAR_collegium_civil_reserve = @('HSM_BAR_collegium_construction', 0.05, 'reserve')
    HSM_BAR_collegium_workshops_equipped = @('HSM_BAR_collegium_construction', 0.05, 'workshops')
    HSM_BAR_collegium_fields_repaired = @('HSM_BAR_collegium_construction', 0.05, 'fields')
}
foreach ($flag in $milestones.Keys) {
    Reset-Model; Apply $effects.HSM_BAR_collegium_initialize
    $model.Flags[$flag] = -1
    Apply $effects.HSM_BAR_collegium_refresh
    foreach ($v in $outputs) {
        $expected = if ($v -eq $milestones[$flag][0]) { $milestones[$flag][1] } else { 0 }
        Assert ([Math]::Abs((Number $v) - $expected) -lt 0.000001) "Incorrect concrete contribution: $flag / $v"
    }
    Assert-ModifierCache
}
Reset-Model
Apply $effects.HSM_BAR_collegium_initialize
foreach ($flag in $milestones.Keys) { $model.Flags[$flag] = -1 }
$model.Flags.HSM_BAR_collegium_defence_protocol = -1
$model.Flags.HSM_BAR_collegium_reserve_equipped = -1
$model.Flags.HSM_BAR_collegium_clinic_rounds_done = -1
$model.Flags.HSM_BAR_collegium_standing_emergency = -1
$model.War = $true
Apply (Scalar ($decisions | Where-Object Key -eq 'HSM_BAR_collegium_war_allocation').Value 'complete_effect')
Assert ($model.Vars.HSM_BAR_collegium_construction -eq 0) 'Military allocation stacks civilian building benefits'
Assert ([Math]::Abs($model.Vars.HSM_BAR_collegium_supply + 0.13) -lt 0.000001 -and [Math]::Abs($model.Vars.HSM_BAR_collegium_recovery - 0.13) -lt 0.000001) 'Prepared logistics and district care do not apply'
$before = $model.Vars.Clone(); $ppBefore = $model.PP
foreach ($day in @(1,30,60,180,360)) {
    $model.Day = $day
    Apply $effects.HSM_BAR_collegium_pulse
    foreach ($v in $outputs) { Assert ($model.Vars[$v] -eq $before[$v]) 'Wartime upkeep or stacking remains' }
    Assert ($model.PP -eq $ppBefore) 'Pulse imposes an unadvertised payment'
}
$model.Flags.HSM_BAR_collegium_emergency_mandate = -1
Apply $effects.HSM_BAR_collegium_refresh
Assert ([Math]::Abs($model.Vars.HSM_BAR_collegium_stability - $before.HSM_BAR_collegium_stability - 0.02) -lt 0.000001) 'Mandate does not remove only the emergency penalty'
$model.War = $false
Apply $effects.HSM_BAR_collegium_pulse
Assert (-not (Has-Flag 'HSM_BAR_collegium_wartime')) 'Peace failed to restore civilian allocation'
Assert ([Math]::Abs($model.Vars.HSM_BAR_collegium_construction - 0.25) -lt 0.000001 -and $model.Vars.HSM_BAR_collegium_supply -eq 0 -and $model.Vars.HSM_BAR_collegium_recovery -eq 0) 'Peace retained wartime effects'
Assert (Has-Flag 'HSM_BAR_collegium_return_reported') 'Return scene was not recorded'
Assert-ModifierCache
$model.Flags.Remove('HSM_BAR_collegium')
Apply $effects.HSM_BAR_collegium_refresh
foreach ($v in $outputs) { Assert ((Number $v) -eq 0) 'Inactive route retains an institutional benefit' }

Reset-Model
[void]$model.ExternalDone.Remove('HSM_BAR_common_reconstruction')
Assert (-not (Conditions (Scalar $focus.HSM_BAR_collegium_oath 'available'))) 'The oath must wait for the social survey'
[void]$model.ExternalDone.Add('HSM_BAR_common_reconstruction')
Assert (Conditions (Scalar $focus.HSM_BAR_collegium_oath 'available')) 'Completed survey must release the oath'
Assert ((Nodes $focus.HSM_BAR_collegium_oath 'prerequisite').Count -eq 0) 'The oath must not auto-attach to other reconstruction trees'

foreach ($field in @('Tag','OriginalTag','Capitulated','Subject','Owned','Controlled')) {
    Reset-Model
    switch ($field) {
        'Tag' { $model.Tag = 'WIT' }
        'OriginalTag' { $model.OriginalTag = 'WIT' }
        'Capitulated' { $model.Capitulated = $true }
        'Subject' { $model.Subject = $true }
        'Owned' { $model.Owned.Clear() }
        'Controlled' { $model.Controlled.Clear() }
    }
    Assert (-not (Conditions $triggers.HSM_BAR_collegium_focus_access)) "Focus access accepts $field loss"
    foreach ($id in $focus.Keys) { Assert (-not (Conditions (Scalar $focus[$id] 'available'))) "$id bypasses $field guard" }
}
Reset-Model
$model.Flags.HSM_BAR_directorate = -1
Assert (-not (Conditions $triggers.HSM_BAR_collegium_focus_access)) 'Service route accepts Collegium focuses'
Reset-Model
foreach ($flag in @('report_answered','peer_review','patient_rights','consent')) { $model.Flags["HSM_BAR_collegium_$flag"] = -1 }
$model.ExternalDone.Clear()
Assert (-not (Conditions (Scalar $focus.HSM_BAR_collegium_assembly 'available'))) 'A scholarly charter replaces the missing civilian cabinet'
[void]$model.ExternalDone.Add('HSM_BAR_civic_cabinet')
Assert (Conditions (Scalar $focus.HSM_BAR_collegium_assembly 'available')) 'A civilian cabinet cannot negotiate the charter'
foreach ($project in @('chorus','manufactory','last_minute','contact')) {
    Reset-Model
    $id = "HSM_BAR_collegium_applied_$project"
    Assert (-not (Conditions (Scalar $focus[$id] 'available'))) "$id does not need a finished Magnum Opus"
    $model.Flags["HSM_BAR_mtk_${project}_theory"] = -1
    Assert (-not (Conditions (Scalar $focus[$id] 'available'))) "$id accepts theory without trials"
    $model.Flags["HSM_BAR_mtk_${project}_done"] = -1
    Assert (Conditions (Scalar $focus[$id] 'available')) "$id rejects finished trials"
    Assert (@((Walk (Scalar $focus[$id] 'completion_reward')) | Where-Object { $_.Key -in @('set_country_flag','set_technology') }).Count -eq 0) "$id grants research completion"
}
# One-time outcomes use recorded starts. Native decisions own costs, factories and time.
$programmeFixtures = @(
    @('train_cohort','HSM_BAR_collegium_school_open','cohort_trained',200,0,0),
    @('equip_workshops','HSM_BAR_grid_program','workshops_equipped',0,25,0),
    @('clinic_rounds','HSM_BAR_clinic_program','clinic_rounds_done',0,25,0),
    @('repair_fields','HSM_BAR_collegium_land_program','fields_repaired',100,0,0),
    @('settlement_houses','HSM_BAR_collegium_refugee_settlement','houses_ready',0,0,500),
    @('onward_travel','HSM_BAR_collegium_refugee_transit','tickets_honoured',0,20,0),
    @('seek_mandate','HSM_BAR_collegium_standing_emergency','emergency_mandate',0,0,0),
    @('maintain_reserve','HSM_BAR_collegium_civil_reserve','reserve_equipped',0,50,0)
)
foreach ($fixture in $programmeFixtures) {
    $id = "HSM_BAR_collegium_$($fixture[0])"
    $body = ($decisions | Where-Object Key -eq $id).Value
    $done = "HSM_BAR_collegium_$($fixture[2])"
    Reset-Model; Apply $effects.HSM_BAR_collegium_initialize
    $model.Flags[$fixture[1]] = -1
    $model.Factories = 1
    Assert (Conditions (Scalar $body 'visible')) "$id is hidden before its first programme"
    Assert (Conditions (Scalar $body 'available')) "$id rejects a funded programme"
    $factory = Scalar (Scalar $body 'modifier') 'civilian_factory_use'
    if ($factory) {
        $model.Factories = 0
        Assert (-not (Conditions (Scalar $body 'available'))) "$id needs no free factory"
        # Native selection already reserves it before complete_effect runs.
    }
    $model.PP -= [int](Scalar $body 'cost')
    Apply (Scalar $body 'complete_effect')
    Assert (Has-Flag "$($id)_pending") "$id failed to record the paid start"
    Assert ($model.Manpower -eq 1000 - $fixture[3]) "$id reserves the wrong personnel"
    Assert ($model.Equipment -eq 1000 - $fixture[4]) "$id consumes the wrong stock"
    Apply (Scalar $body 'complete_effect')
    Assert ($model.Manpower -eq 1000 - $fixture[3] -and $model.Equipment -eq 1000 - $fixture[4]) "$id double-charges its start"
    $model.Day += [int](Scalar $body 'days_remove')
    Apply (Scalar $body 'remove_effect')
    Assert (Has-Flag $done) "$id grants no concrete completion"
    Assert ($model.Manpower -eq 1000 + $fixture[5]) "$id loses or creates assigned staff"
    Assert (-not (Has-Flag "$($id)_pending")) "$id retains its pending marker"
    Assert (-not (Conditions (Scalar $body 'visible')) -and -not (Conditions (Scalar $body 'available'))) "$id remains a repeatable grinder"
    $mp = $model.Manpower; $equipment = $model.Equipment; $bonusCount = $model.TechBonuses.Count; $vars = $model.Vars.Clone()
    Apply (Scalar $body 'remove_effect')
    Apply (Scalar $body 'cancel_effect')
    Apply (Scalar $body 'complete_effect')
    Assert ($model.Manpower -eq $mp -and $model.Equipment -eq $equipment -and $model.TechBonuses.Count -eq $bonusCount) "$id replays its reward or refund"
    foreach ($v in $outputs) { Assert ($model.Vars[$v] -eq $vars[$v]) "$id stacks its permanent result" }
    Assert-ModifierCache

    foreach ($loss in @('route','capitulation','homeland','Service','subject')) {
        Reset-Model; Apply $effects.HSM_BAR_collegium_initialize
        $model.Flags[$fixture[1]] = -1
        Apply (Scalar $body 'complete_effect')
        switch ($loss) {
            'route' { $model.Flags.Remove('HSM_BAR_collegium') }
            'capitulation' { $model.Capitulated = $true }
            'homeland' { $model.Controlled.Clear() }
            'Service' { $model.Flags.HSM_BAR_directorate = -1 }
            'subject' { $model.Subject = $true }
        }
        Assert (Conditions (Scalar $body 'cancel_trigger')) "$id does not cancel on $loss"
        Apply (Scalar $body 'cancel_effect')
        Apply (Scalar $body 'cancel_effect')
        Apply (Scalar $body 'remove_effect')
        Assert ($model.Manpower -eq 1000 -and $model.Equipment -eq 1000 - $fixture[4]) "$id invalid refund on $loss"
        Assert (-not (Has-Flag $done) -and -not (Has-Flag "$($id)_pending")) "$id grants a result after $loss"
    }

    Reset-Model; Apply $effects.HSM_BAR_collegium_initialize
    $model.Flags[$fixture[1]] = -1
    Apply (Scalar $body 'complete_effect')
    # Shared dissolution calls this before clearing its route flags.
    Apply $effects.HSM_BAR_collegium_cancel_programs
    Apply $effects.HSM_BAR_collegium_cancel_programs
    Apply (Scalar $body 'remove_effect')
    Apply (Scalar $body 'cancel_effect')
    Assert ($model.Manpower -eq 1000 -and $model.Equipment -eq 1000 - $fixture[4]) "$id cleanup invents a refund"
    Assert (-not (Has-Flag $done) -and -not (Has-Flag "$($id)_pending")) "$id stale callback grants work after cleanup"
}
Reset-Model
$model.Manpower = 800 # A legacy save may have paid this, but carries no assignment evidence.
$legacy = ($decisions | Where-Object Key -eq 'HSM_BAR_collegium_train_cohort').Value
Apply (Scalar $legacy 'remove_effect'); Apply (Scalar $legacy 'cancel_effect')
Apply $effects.HSM_BAR_collegium_cancel_programs
Assert ($model.Manpower -eq 800) 'Compatibility fabricated an unproven legacy refund'
Assert (-not (Has-Flag 'HSM_BAR_collegium_cohort_trained')) 'Legacy callback silently converted retired points into a milestone'

# Both mandate paths have a real tradeoff, but neither is needed for a peaceful ending.
Reset-Model; Apply $effects.HSM_BAR_collegium_initialize
$model.War = $true; $model.Flags.HSM_BAR_collegium_defence_protocol = -1
$mandateOption = (Nodes $events['HSM_BAR_collegium.20'] 'option')[0].Value
Apply @($mandateOption | Where-Object { $_.Key -notin @('name','trigger','ai_chance') })
Assert (-not (Conditions $triggers.HSM_BAR_collegium_war_allocation_ready)) 'Public mandate skips its deliberation'
$model.Day = 21
Assert (Conditions $triggers.HSM_BAR_collegium_war_allocation_ready) 'Finished mandate cannot activate field service'
Apply (Scalar ($decisions | Where-Object Key -eq 'HSM_BAR_collegium_war_allocation').Value 'complete_effect')
Assert ($model.Vars.HSM_BAR_collegium_stability -eq 0) 'Public mandate still pays emergency penalty'
foreach ($id in @('war_allocation','civil_allocation','seek_mandate','review_complaint')) {
    Assert ((Scalar ($decisions | Where-Object Key -eq "HSM_BAR_collegium_$id").Value 'cost') -eq '0') "$id still sells retired points"
}
foreach ($name in @('clinic','grid','wards')) {
    Reset-Model
    Assert (-not (Conditions $triggers["HSM_BAR_collegium_$($name)_ready"])) "$name has no substantive gate"
    $model.Flags["HSM_BAR_project_$($name)_done"] = -1
    Assert (Conditions $triggers["HSM_BAR_collegium_$($name)_ready"]) "$name rejects the existing institute alternative"
}
# Exact visible contributions, including the non-funded constitutional tradeoffs.
$tooltipValues = @{}
foreach ($entry in $milestones.Values) { $tooltipValues["HSM_BAR_collegium_$($entry[2])_services_tt"] = @([double]$entry[1] * 100) }
$tooltipValues.HSM_BAR_collegium_rounds_services_tt = @(5)
$tooltipValues.HSM_BAR_collegium_equipment_services_tt = @(-5)
$tooltipValues.HSM_BAR_collegium_war_services_tt = @(-8, 8, -2)
$tooltipValues.HSM_BAR_collegium_mandate_services_tt = @(-2)
$tooltipValues.HSM_BAR_collegium_standing_services_tt = @(-2)
foreach ($language in @('english','russian')) {
    foreach ($key in $tooltipValues.Keys) {
        $values = @([regex]::Matches($locales[$language][$key], '\u00a7[GR]([+-][0-9.]+)%\u00a7!') | ForEach-Object {
            [double]::Parse($_.Groups[1].Value, [Globalization.CultureInfo]::InvariantCulture)
        })
        Assert ($values.Count -eq $tooltipValues[$key].Count) "$language $key hides or adds a numerical reward"
        for ($i = 0; $i -lt $values.Count; $i++) {
            Assert ([Math]::Abs($values[$i] - $tooltipValues[$key][$i]) -lt 0.000001) "$language $key disagrees with its reward"
        }
    }
}
$charters = @{
    open = @{ research_speed_factor = 0.05; stability_factor = 0.05 }
    republic = @{ political_power_gain = 0.20; production_factory_max_efficiency_factor = 0.08 }
    tutelage = @{ research_speed_factor = 0.10; political_power_gain = -0.15 }
}
$ideaBodies = Scalar (Scalar $parsed['HSM_BAR_collegium_ideas.txt'] 'ideas') 'country'
foreach ($charter in $charters.Keys) {
    $body = Scalar (Scalar $ideaBodies "HSM_BAR_collegium_$($charter)_spirit") 'modifier'
    Assert ($body.Count -eq $charters[$charter].Count) "Unexpected charter statistic: $charter"
    foreach ($key in $charters[$charter].Keys) {
        Assert ([Math]::Abs((Number (Scalar $body $key)) - $charters[$charter][$key]) -lt 0.000001) "Incorrect charter reward: $charter/$key"
    }
}
# Reachable clinic/grid alternatives, paid/unpaid programmes and allocation modes.
$totals = [Collections.Generic.List[object]]::new()
foreach ($charter in $charters.Keys) { foreach ($clinic in @(0,1)) { foreach ($grid in @(0,1)) {
    foreach ($paid in @($false,$true)) { foreach ($war in @($false,$true)) {
        Reset-Model; Apply $effects.HSM_BAR_collegium_initialize
        foreach ($flag in @('independent_archive','inspectors','school_open','research_board','peer_review','civil_reserve')) {
            $model.Flags["HSM_BAR_collegium_$flag"] = -1
        }
        $model.Flags.HSM_BAR_grid_program = -1
        foreach ($choice in @(@('HSM_BAR_collegium.7',$clinic),@('HSM_BAR_collegium.8',$grid))) {
            $option = (Nodes $events[$choice[0]] 'option')[$choice[1]].Value
            Apply @($option | Where-Object { $_.Key -notin @('name','ai_chance','trigger') })
        }
        if ($paid) {
            foreach ($flag in @('cohort_trained','workshops_equipped','fields_repaired','reserve_equipped','clinic_rounds_done')) {
                $model.Flags["HSM_BAR_collegium_$flag"] = -1
            }
        }
        $model.War = $war
        $model.Flags.HSM_BAR_collegium_wartime = -1
        $model.Flags.HSM_BAR_collegium_defence_protocol = -1
        $model.Flags.HSM_BAR_collegium_emergency_mandate = -1
        Apply $effects.HSM_BAR_collegium_refresh
        $expectedResearch = 0.08 + 0.02 * $clinic + 0.02 * $grid + 0.03 * [int]$paid
        $expectedConstruction = if ($war) { 0 } else { 0.10 + 0.05 * (1 - $grid) + 0.10 * [int]$paid }
        $expectedSupply = if ($war) { -0.08 - 0.05 * [int]$paid } else { 0 }
        $expectedRecovery = -$expectedSupply
        Assert ([Math]::Abs($model.Vars.HSM_BAR_collegium_research - $expectedResearch) -lt 0.000001) 'Research choices stack incorrectly'
        Assert ([Math]::Abs($model.Vars.HSM_BAR_collegium_construction - $expectedConstruction) -lt 0.000001) 'Civilian construction choices stack incorrectly'
        Assert ([Math]::Abs($model.Vars.HSM_BAR_collegium_supply - $expectedSupply) -lt 0.000001) 'Paid reserve has no incremental logistics reward'
        Assert ([Math]::Abs($model.Vars.HSM_BAR_collegium_recovery - $expectedRecovery) -lt 0.000001) 'Funded district rounds have no incremental medical reward'
        $stable = $model.Vars.Clone()
        1..10 | ForEach-Object { Apply $effects.HSM_BAR_collegium_refresh }
        foreach ($key in $outputs) { Assert ($model.Vars[$key] -eq $stable[$key]) 'Repeated refresh increases programme benefit' }
        Assert-ModifierCache
        $totals.Add([pscustomobject]@{
            Charter = $charter; Clinic = $clinic; Grid = $grid; Funded = $paid; War = $war
            Research = $expectedResearch + $charters[$charter]['research_speed_factor']
            Stability = $model.Vars.HSM_BAR_collegium_stability + $charters[$charter]['stability_factor']
            Construction = $expectedConstruction; Supply = $expectedSupply; Recovery = $expectedRecovery
        })
    } }
} } }
Assert ($totals.Count -eq 48) 'Incomplete reachable services/charter matrix'
$ceilings = @{ Research = 0.25; Stability = 0.15; Construction = 0.25; Recovery = 0.13 }
foreach ($key in $ceilings.Keys) {
    $maximum = ($totals | Measure-Object -Property $key -Maximum).Maximum
    Assert ([Math]::Abs($maximum - $ceilings[$key]) -lt 0.000001) "Unexpected $key stacking ceiling"
}
Assert ([Math]::Abs(($totals | Measure-Object Supply -Minimum).Minimum + 0.13) -lt 0.000001) 'Unexpected supply floor'
Write-Output ('Reachable Collegium ceilings, excluding civic/shared/project rewards: ' + ($ceilings | ConvertTo-Json -Compress) + '; supply floor -0.13; 48 combinations.')
Write-Output "PASS: $passed assertions; 37 focuses, 24 scenes, 11 decisions, EN/RU, sprites, six no-DLC institutional ending walks, four optional project applications and concrete milestone/policy model."
Write-Output 'Static validation only. In-game rendering, save/load and combat balance still require a game session.'
