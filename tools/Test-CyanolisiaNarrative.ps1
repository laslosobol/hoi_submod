#Requires -Version 7.2
param([switch] $CompareHead)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
. (Join-Path $PSScriptRoot 'CyanolisiaIconManifest.Common.ps1')
$passed = 0
$failures = [System.Collections.Generic.List[string]]::new()

function Read-Code([string] $path) {
    [System.IO.File]::ReadAllText((Join-Path $root $path))
}

function Assert-That([bool] $condition, [string] $message) {
    if (-not $condition) { throw $message }
}

function Test-Case([string] $name, [scriptblock] $body) {
    try {
        & $body
        $script:passed++
        Write-Output "PASS: $name"
    } catch {
        $script:failures.Add("$name -- $($_.Exception.Message)")
        Write-Output "FAIL: $name -- $($_.Exception.Message)"
    }
}

# Extract only named focus/event blocks; comments and quoted braces are tokens.
function Get-Definitions([string] $content, [string] $kind) {
    $tokens = Get-ClausewitzTokens $content
    $definitions = @{}
    for ($i = 0; $i -lt $tokens.Count - 2; $i++) {
        if ($tokens[$i] -ne $kind -or $tokens[$i + 1] -ne '=' -or $tokens[$i + 2] -ne '{') { continue }
        $depth = 1
        $id = $null
        $start = $i
        for ($i += 3; $i -lt $tokens.Count; $i++) {
            if ($depth -eq 1 -and $tokens[$i] -eq 'id' -and $tokens[$i + 1] -eq '=') {
                $id = $tokens[$i + 2]
            }
            if ($tokens[$i] -eq '{') { $depth++ }
            if ($tokens[$i] -eq '}') { $depth-- }
            if ($depth -eq 0) { break }
        }
        if (-not $id -or $depth -ne 0) { throw "Malformed $kind block" }
        if ($definitions.ContainsKey($id)) { throw "Duplicate $kind ID: $id" }
        $definitions[$id] = $tokens[$start..$i] -join ' '
    }
    return $definitions
}

$focusPath = 'mod/HoISubmod/common/national_focus/CYA.txt'
$eventPath = 'mod/HoISubmod/events/HSM_Cyanolisia.txt'
$triggerPath = 'mod/HoISubmod/common/scripted_triggers/HSM_CYA_scripted_triggers.txt'
$effectPath = 'mod/HoISubmod/common/scripted_effects/HSM_CYA_scripted_effects.txt'
$onActionPath = 'mod/HoISubmod/common/on_actions/HSM_CYA_on_actions.txt'
$dynamicLocPath = 'mod/HoISubmod/common/scripted_localisation/HSM_CYA_narrative.txt'
$paths = @($focusPath, $eventPath, $triggerPath, $effectPath, $onActionPath, $dynamicLocPath,
    'mod/HoISubmod/events/GriffonianEmpire Events.txt', 'mod/HoISubmod/events/Cyanolisia Events.txt',
    'mod/HoISubmod/common/decisions/HSM_CYA_imperial_settlement.txt',
    'mod/HoISubmod/common/decisions/categories/HSM_CYA_decision_categories.txt')
foreach ($path in $paths) {
    Test-Case "Balanced script: $path" {
        $depth = 0
        foreach ($token in (Get-ClausewitzTokens (Read-Code $path))) {
            if ($token -eq '{') { $depth++ }
            if ($token -eq '}') { $depth-- }
            Assert-That ($depth -ge 0) 'Unexpected closing brace'
        }
        Assert-That ($depth -eq 0) 'Unclosed block'
    }
}

$focus = Get-Definitions (Read-Code $focusPath) 'shared_focus'
$events = Get-Definitions (Read-Code $eventPath) 'country_event'
$triggers = (Get-ClausewitzTokens (Read-Code $triggerPath)) -join ' '
$effects = (Get-ClausewitzTokens (Read-Code $effectPath)) -join ' '
$actions = (Get-ClausewitzTokens (Read-Code $onActionPath)) -join ' '

foreach ($spec in @(
    @{ File = 'GriffonianEmpire Events.txt'; Changed = @('imperial.99') },
    @{ File = 'Cyanolisia Events.txt'; Changed = @('cyan.9', 'cyan.10', 'cyan.11') }
)) {
    Test-Case "Base override limited to intended events: $($spec.File)" {
        $base = Get-Definitions (Read-Code "EaW/events/$($spec.File)") 'country_event'
        $mod = Get-Definitions (Read-Code "mod/HoISubmod/events/$($spec.File)") 'country_event'
        Assert-That ((($base.Keys | Sort-Object) -join ',') -ceq (($mod.Keys | Sort-Object) -join ',')) 'Event inventory changed'
        foreach ($id in $base.Keys) {
            if ($id -notin $spec.Changed) { Assert-That ($base[$id] -ceq $mod[$id]) "Unintended override: $id" }
        }
    }
}

Test-Case 'Failed coup has an explicit escape divergence; success is not redirected' {
    $gri = Get-Definitions (Read-Code 'mod/HoISubmod/events/GriffonianEmpire Events.txt') 'country_event'
    Assert-That ($gri['imperial.99'].Contains('CYA = { set_country_flag = HSM_CYA_dawnclaw_escaped_execution }')) 'Escape not recorded in CYA'
    Assert-That ($gri['imperial.99'].Contains('text = imperial.99.d')) 'Vanilla execution fallback lost'
    Assert-That ($gri['imperial.99'].Contains('text = HSM_CYA_imperial_escape_desc')) 'Escape description missing'
    Assert-That ($actions -match 'has_country_flag = HSM_CYA_dawnclaw_escaped_execution } set_country_flag = HSM_CYA_dawnclaw_asylum_scheduled') 'Asylum not gated by escape'
    Assert-That ($events['hsm_cyanolisia.1'].Contains('has_country_flag = HSM_CYA_dawnclaw_escaped_execution')) 'Arrival lacks escape guard'
}

Test-Case 'Socialist entry explicitly restores the Countess and cancels obsolete coup events' {
    Assert-That ($events['hsm_cyanolisia.1'].Contains('promote_character = CYA_countess_taillow_sumpfkiel')) 'Countess not restored'
    Assert-That ($events['hsm_cyanolisia.1'].Contains('set_politics = { ruling_party = neutrality elections_allowed = no }')) 'Wrong government after restoration'
    $cya = Get-Definitions (Read-Code 'mod/HoISubmod/events/Cyanolisia Events.txt') 'country_event'
    foreach ($id in @('cyan.9', 'cyan.10', 'cyan.11')) {
        Assert-That ($cya[$id].Contains('trigger = { NOT = { has_country_flag = HSM_CYA_dawnclaw_branch_unlocked } }')) "Queued old coup still fires: $id"
    }
}

Test-Case 'Voluntary departure opens administration without inventing a death' {
    $option = $events['hsm_cyanolisia.2'].Split('name = hsm_cyanolisia.2.c')[1]
    Assert-That ($option.Contains('set_country_flag = HSM_CYA_dawnclaw_departed')) 'Departure not recorded'
    Assert-That (-not $option.Contains('set_country_flag = HSM_CYA_dawnclaw_dead')) 'Departure falsely kills Dawnclaw'
    Assert-That ($option.Contains('clr_country_flag = HSM_CYA_dawnclaw_hidden_in_court')) 'Concealment remains active'
    foreach ($block in $focus.Values | Where-Object { $_.Contains('has_country_flag = HSM_CYA_path_imperial_administration') }) {
        Assert-That (-not $block.Contains('has_country_flag = HSM_CYA_dawnclaw_dead')) 'Administration still requires a death'
    }
    Assert-That ($actions.Contains('has_country_flag = HSM_CYA_dawnclaw_departed')) 'Departure leaves dynamic programmes active'
}

Test-Case 'Grover transfer excludes independent foreign holders' {
    Assert-That ($triggers.Contains('OR = { is_subject_of = ROOT AND = { exists = no any_original_cores_controlled_by_ROOT = yes all_original_cores_owned_and_controlled_by_ROOT = yes } }')) 'Custody restrictions weakened'
    Assert-That ($effects.Contains('limit = { HSM_CYA_grover_household_can_transfer = yes }')) 'Unrestricted transfer loop'
    Assert-That (-not (Read-Code $focusPath).Contains('set_nationality = ROOT')) 'Focus still transfers arbitrary foreign characters'
    Assert-That (-not (Read-Code $eventPath).Contains('set_nationality = ROOT')) 'Coronation still transfers arbitrary foreign characters'
}
foreach ($id in @('HSM_CYA_execute_the_child_emperor', 'HSM_CYA_the_puppet_emperor', 'HSM_CYA_the_child_may_rule', 'HSM_CYA_crown_in_trust')) {
    Test-Case "Local custody required: $id" {
        Assert-That ($focus[$id] -match 'available = { HSM_CYA_grover_in_our_custody = yes') 'Missing custody prerequisite'
    }
}
Test-Case 'Execution is local; remembrance does not retire Grover worldwide' {
    Assert-That ($focus['HSM_CYA_execute_the_child_emperor'].Contains('retire_character = GRI_emperor_grover_vi')) 'Local execution missing'
    Assert-That (-not $events['hsm_cyanolisia.41'].Contains('every_possible_country')) 'Remote execution remains'
}
Test-Case 'Prior reign excludes ROOT; settlement waits for custody or confirmed death' {
    Assert-That ($triggers.Contains('HSM_CYA_grover_reigns_abroad = { any_country = { NOT = { tag = ROOT }')) 'Local reign misclassified as foreign'
    Assert-That ($actions.Contains('HSM_CYA_grover_reigns_abroad = yes')) 'Daily action uses wrong reign trigger'
    Assert-That ($actions.Contains('OR = { has_global_flag = GRI_grover_vi_dead AND = { has_character = GRI_emperor_grover_vi')) 'Settlement can resolve before custody'
}
Test-Case 'Childhood content requires a minor in local custody' {
    Assert-That ($focus['HSM_CYA_princely_lesson_books'].Contains('available = { HSM_CYA_grover_in_our_custody = yes date < 1021.5.21 }')) 'Adult schooling remains'
    foreach ($id in @('hsm_cyanolisia.34', 'hsm_cyanolisia.37')) {
        Assert-That ($events[$id].Contains('trigger = { HSM_CYA_grover_in_our_custody = yes date < 1021.5.21 }')) "Unsafe childhood event: $id"
    }
}
foreach ($id in @('40', '42', '43')) {
    Test-Case "Coronation variant and custody guards: $id" {
        $block = $events["hsm_cyanolisia.$id"]
        Assert-That ($block.Contains('trigger = { HSM_CYA_grover_in_our_custody = yes }')) 'Unsafe coronation'
        Assert-That ($block.Contains("hsm_cyanolisia.$id.late.d") -and $block.Contains("hsm_cyanolisia.$id.adult.d")) 'Missing late first accession or previous reign variant'
        if ($id -eq '42') {
            Assert-That (-not $block.Contains('promote_leader = yes')) 'Puppet became executive ruler'
        } else {
            Assert-That ($block.Contains('promote_leader = yes') -and $block.Contains('HSM_CYA_grover_ruler_desc')) 'Real ruler or bespoke biography missing'
        }
    }
}
Test-Case 'Continental unification checks original territory, ownership and control' {
    Assert-That (-not $triggers.Contains('any_possible_country')) 'Unsupported trigger iterator'
    Assert-That ($triggers.Contains('array = original_cores OR = { NOT = { is_on_continent = asia } HSM_CYA_state_in_imperial_sphere = yes }')) 'Wrong territorial inventory'
    Assert-That ($triggers.Contains('owner = { OR = { tag = ROOT is_subject_of = ROOT } } controller = { OR = { tag = ROOT is_subject_of = ROOT } }')) 'Occupation or third-party annexation can count as unification'
}
Test-Case 'Asterion protectorate is actually released after annexation, with homeland safeguards' {
    Assert-That ($effects.Contains('release_autonomy = { target = MIT autonomy_state = autonomy_puppet }')) 'Protectorate never released'
    foreach ($id in @('HSM_CYA_countess_integrate_south', 'HSM_CYA_dawnclaw_integrate_south', 'HSM_CYA_military_governorate_asterion')) {
        Assert-That ($focus[$id].Contains('HSM_CYA_establish_asterion_protectorate = yes')) "No protectorate effect: $id"
        Assert-That ($focus[$id].Contains('HSM_CYA_all_asterion_territory_owned = yes has_war = no')) "Incomplete wartime annexation accepted: $id"
    }
    Assert-That ($effects.Contains('has_state_flag = HSM_CYA_retained_homeland')) 'No protection for pre-owned Cyanolisian land'
}

$locales = @{}
foreach ($language in @('english', 'russian')) {
    Test-Case "Localization encoding, quoting and unique keys: $language" {
        $path = "mod/HoISubmod/localisation/$language/hsm_cyanolisia_l_$language.yml"
        $bytes = [System.IO.File]::ReadAllBytes((Join-Path $root $path))
        Assert-That ($bytes[0] -eq 239 -and $bytes[1] -eq 187 -and $bytes[2] -eq 191) 'Missing UTF-8 BOM'
        $map = @{}
        foreach ($line in (Read-Code $path) -split '\r?\n') {
            if ($line.Trim() -eq '' -or $line.TrimStart().StartsWith('#') -or $line -match '^l_\w+:') { continue }
            Assert-That ($line -match '^\s+([\w.]+):\d*\s+"((?:[^"\\]|\\.)*)"\s*$') "Malformed localization: $line"
            $key = $Matches[1]
            Assert-That (-not $map.ContainsKey($key)) "Duplicate key: $key"
            $map[$key] = $Matches[2]
        }
        $locales[$language] = $map
    }
}
Test-Case 'EN/RU keys and all new narrative references agree' {
    Assert-That ((($locales.english.Keys | Sort-Object) -join ',') -ceq (($locales.russian.Keys | Sort-Object) -join ',')) 'Locale inventories differ'
    foreach ($path in $paths) {
        foreach ($m in [regex]::Matches((Read-Code $path), '\b(?:title|desc|text|name|tooltip|localization_key|custom_effect_tooltip)\s*=\s*"?((?:HSM_CYA_|hsm_cyanolisia\.)[\w.]+)')) {
            Assert-That ($locales.english.ContainsKey($m.Groups[1].Value)) "Unlocalized reference: $($m.Groups[1].Value)"
        }
    }
}
Test-Case 'Imperial decision titles, descriptions and new visible flags are localized' {
    $decisions = Read-Code 'mod/HoISubmod/common/decisions/HSM_CYA_imperial_settlement.txt'
    foreach ($m in [regex]::Matches($decisions, '(?m)^\t(HSM_CYA_\w+) = \{')) {
        foreach ($language in @('english', 'russian')) {
            foreach ($key in @($m.Groups[1].Value, "$($m.Groups[1].Value)_desc")) {
                Assert-That ($locales[$language].ContainsKey($key)) "Missing decision localization: $language / $key"
            }
        }
    }
    $newEvents = (53..63 | ForEach-Object { $events["hsm_cyanolisia.$_"] }) -join ' '
    foreach ($m in [regex]::Matches("$decisions $newEvents", '\bhas_country_flag\s*=\s*(HSM_CYA_\w+)')) {
        foreach ($language in @('english', 'russian')) {
            Assert-That ($locales[$language].ContainsKey($m.Groups[1].Value)) "Raw flag tooltip: $language / $($m.Groups[1].Value)"
        }
    }
}
Test-Case 'Regional callbacks use recorded choices and have an unsettled fallback' {
    $dynamic = Read-Code $dynamicLocPath
    foreach ($m in [regex]::Matches($dynamic, 'has_country_flag = (\w+)')) {
        Assert-That ((Read-Code $eventPath).Contains("set_country_flag = $($m.Groups[1].Value)")) "Callback flag never set: $($m.Groups[1].Value)"
    }
    foreach ($region in @('Kaiv', 'Midoria', 'Gryphus')) {
        Assert-That ($dynamic.Contains("name = GetHSMCya$($region)Settlement")) "Missing dynamic text: $region"
        Assert-That ($dynamic.Contains("HSM_CYA_petitions_$($region.ToLowerInvariant())_unsettled")) "Missing fallback: $region"
    }
}
if ($CompareHead) {
    Test-Case 'Focus IDs, layout, icons, costs and graph match HEAD' {
        $oldText = (& git -C $root show "HEAD:$focusPath") -join "`n"
        if ($LASTEXITCODE) { throw 'Cannot read HEAD focus baseline' }
        $old = Get-Definitions $oldText 'shared_focus'
        Assert-That ((($old.Keys | Sort-Object) -join ',') -ceq (($focus.Keys | Sort-Object) -join ',')) 'Focus IDs changed'
        $pattern = '(?:\b(?:x|y|icon|cost|relative_position_id) = [^ {}]+|(?:prerequisite|mutually_exclusive) = { focus = [^ {}]+ })'
        foreach ($id in $old.Keys) {
            $a = [regex]::Matches($old[$id], $pattern).Value -join '|'
            $b = [regex]::Matches($focus[$id], $pattern).Value -join '|'
            Assert-That ($a -ceq $b) "Layout, art, cost or graph changed: $id"
        }
    }
    Test-Case 'Art manifest changed only display names, not reviews, notes or approval hashes' {
        $path = 'docs/icon-generation-manifest.md'
        $old = (& git -C $root show "HEAD:$path") -join "`n"
        if ($LASTEXITCODE) { throw 'Cannot read HEAD manifest baseline' }
        $new = Read-Code $path
        $pattern = '(?m)^(\| `[^|`]+` \|)[^|]+\|'
        Assert-That (($old -replace $pattern, '$1 NAME |').TrimEnd() -ceq (($new -replace '\r\n', "`n") -replace $pattern, '$1 NAME |').TrimEnd()) 'Art review data or metadata beyond names changed'
    }
}

Write-Output "PowerShell $($PSVersionTable.PSVersion): $passed passed; $($failures.Count) failed."
if ($failures.Count) { throw ($failures -join "`n") }
