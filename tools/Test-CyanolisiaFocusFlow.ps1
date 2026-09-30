#Requires -Version 7.2
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
. (Join-Path $PSScriptRoot 'CyanolisiaIconManifest.Common.ps1')
$passed = 0
$failures = [System.Collections.Generic.List[string]]::new()

function Assert-That([bool] $condition, [string] $message) {
    if (-not $condition) { throw $message }
}
function Test-Case([string] $name, [scriptblock] $body) {
    try { & $body; $script:passed++; Write-Output "PASS: $name" }
    catch { $script:failures.Add("$name -- $($_.Exception.Message)"); Write-Output "FAIL: $name -- $($_.Exception.Message)" }
}

# Keep ordered properties: repeated prerequisites and NOT clauses are significant.
function Read-Block([string[]] $tokens, [ref] $index, [bool] $nested = $false) {
    $nodes = [System.Collections.Generic.List[object]]::new()
    while ($index.Value -lt $tokens.Count) {
        $key = $tokens[$index.Value++]
        if ($key -eq '}') {
            if (-not $nested) { throw 'Unexpected closing brace' }
            return ,$nodes.ToArray()
        }
        $node = [pscustomobject]@{ Key = $key; Op = ''; Value = ''; Children = @() }
        if ($index.Value -lt $tokens.Count -and $tokens[$index.Value] -in @('=', '<', '>', '<=', '>=')) {
            $node.Op = $tokens[$index.Value++]
            if ($index.Value -ge $tokens.Count) { throw "Missing value: $key" }
            if ($tokens[$index.Value] -eq '{') {
                $index.Value++
                $node.Children = Read-Block $tokens $index $true
            } else { $node.Value = $tokens[$index.Value++] }
        }
        $nodes.Add($node)
    }
    if ($nested) { throw 'Unclosed block' }
    return ,$nodes.ToArray()
}
function Parse-Code([string] $text) {
    $index = 0
    return ,(Read-Block (Get-ClausewitzTokens $text) ([ref] $index))
}
function Read-Code([string] $path) {
    return ,(Parse-Code ([IO.File]::ReadAllText((Join-Path $root $path))))
}
function Prop($node, [string] $key) { return @($node.Children | Where-Object Key -eq $key) }
function Value($node, [string] $key) { return (Prop $node $key | Select-Object -First 1).Value }

$focus = @{}
$trees = @()
foreach ($file in @('CYA.txt', 'HSM_CYA_development.txt', 'HSM_CYA_development_expansion.txt')) {
    foreach ($node in (Read-Code "mod/HoISubmod/common/national_focus/$file")) {
        if ($node.Key -eq 'shared_focus') {
            $id = Value $node 'id'
            if ($focus.ContainsKey($id)) { throw "Duplicate focus: $id" }
            $focus[$id] = $node
        } elseif ($node.Key -eq 'focus_tree') { $trees += $node }
    }
}
$triggers = @{}
foreach ($file in @('HSM_CYA_scripted_triggers.txt', 'HSM_CYA_story.txt')) {
    foreach ($node in (Read-Code "mod/HoISubmod/common/scripted_triggers/$file")) { $triggers[$node.Key] = $node }
}
$effects = @{}
foreach ($file in @('HSM_CYA_scripted_effects.txt', 'HSM_CYA_story.txt')) {
    foreach ($node in (Read-Code "mod/HoISubmod/common/scripted_effects/$file")) { $effects[$node.Key] = $node }
}
$events = @{}
foreach ($file in @('HSM_Cyanolisia.txt', 'HSM_CYA_story.txt')) {
    foreach ($node in (Read-Code "mod/HoISubmod/events/$file")) {
        if ($node.Key -eq 'country_event') {
            $id = Value $node 'id'
            if ($events.ContainsKey($id)) { throw "Duplicate event: $id" }
            $events[$id] = $node
        }
    }
}

function New-World {
    $cya = @{ Tag = 'CYA'; Flags = @(); Ideas = @(); Characters = @(); Goals = @(); Wars = @(); Events = @() }
    return @{ Root = $cya; Countries = @{ CYA = $cya }; States = @{}; Global = @(); Completed = @(); Hide = $true; Date = [datetime]::new(1021, 5, 22) }
}
function Add-State($world, [int] $id, [string] $owner = 'CYA', [string] $controller = 'CYA', [string] $continent = 'asia', [bool] $impassable = $false) {
    $world.States["$id"] = @{ Owner = $owner; Controller = $controller; Continent = $continent; Impassable = $impassable }
}

# A deliberately limited evaluator for the predicates under test, not an HOI4 simulator.
# Unknown predicates fail loudly rather than being assumed true.
function Test-Conditions($nodes, $world, $scope = $world.Root, $previous = $null) {
    foreach ($node in $nodes) {
        $v = $node.Value
        $ok = switch ($node.Key) {
            'tooltip' { $true }
            'AND' { Test-Conditions $node.Children $world $scope $previous }
            'OR' { @($node.Children | Where-Object { Test-Conditions @($_) $world $scope $previous }).Count -gt 0 }
            'NOT' { @($node.Children | Where-Object { Test-Conditions @($_) $world $scope $previous }).Count -eq 0 }
            'if' { -not (Test-Conditions (Prop $node 'limit').Children $world $scope $previous) -or (Test-Conditions @($node.Children | Where-Object Key -ne 'limit') $world $scope $previous) }
            'custom_trigger_tooltip' { Test-Conditions $node.Children $world $scope $previous }
            'always' { $v -eq 'yes' }
            'has_country_flag' { $v -in $scope.Flags }
            'has_global_flag' { $v -in $world.Global }
            'has_completed_focus' { $v -in $world.Completed }
            'has_game_rule' { $world.Hide }
            'has_idea' { $v -in $scope.Ideas }
            'has_character' { $v -in $scope.Characters }
			'has_country_leader' { $scope.Leader -eq (Value $node 'character') }
			'has_capitulated' { [bool] $scope.Capitulated -eq ($v -eq 'yes') }
			'has_focus_tree' { $scope.Tree -eq $v }
			'has_government' { $scope.Government -eq $v }
			'is_in_faction' { [bool] $scope.Faction -eq ($v -eq 'yes') }
			'any_country' { @($world.Countries.Values | Where-Object { $_.Exists -and (Test-Conditions $node.Children $world $_ $scope) }).Count -gt 0 }
            'has_war' { [bool] $scope.AtWar -eq ($v -eq 'yes') }
            'has_war_with' {
                $target = switch ($v) { 'ROOT' { $world.Root.Tag }; 'FROM' { $world.Sender.Tag }; default { $v } }
                $target -in $scope.Wars
            }
            'has_wargoal_against' { $previous.Tag -in $scope.Goals }
            'exists' { [bool] $scope.Exists -eq ($v -eq 'yes') }
            'is_subject' { [bool] $scope.Overlord -eq ($v -eq 'yes') }
            'is_faction_leader' { [bool] $scope.FactionLeader -eq ($v -eq 'yes') }
            'is_in_faction_with' {
                $target = if ($v -eq 'FROM') { $world.Sender } else { $world.Root }
                [bool] $scope.Faction -and $scope.Faction -eq $target.Faction
            }
            'has_full_control_of_state' { $world.States[$v].Controller -eq $scope.Tag }
            'owns_state' { $world.States[$v].Owner -eq $scope.Tag }
            'controls_state' { $world.States[$v].Controller -eq $scope.Tag }
            'is_on_continent' { $scope.Continent -eq $v }
            'impassable' { [bool] $scope.Impassable -eq ($v -eq 'yes') }
            'tag' { $scope.Tag -eq $(if ($v -eq 'ROOT') { $world.Root.Tag } else { $v }) }
            'original_tag' { $(if ($scope.OriginalTag) { $scope.OriginalTag } else { $scope.Tag }) -eq $v }
            'is_subject_of' { $scope.Overlord -eq $world.Root.Tag }
            'owner' { Test-Conditions $node.Children $world $world.Countries[$scope.Owner] $scope }
            'controller' { Test-Conditions $node.Children $world $world.Countries[$scope.Controller] $scope }
            'ROOT' { Test-Conditions $node.Children $world $world.Root $scope }
            'FROM' { Test-Conditions $node.Children $world $world.Sender $scope }
            'all_state' { @($world.States.Values | Where-Object { -not (Test-Conditions $node.Children $world $_ $scope) }).Count -eq 0 }
            'any_owned_state' { @($world.States.Values | Where-Object { $_.Owner -eq $scope.Tag -and (Test-Conditions $node.Children $world $_ $scope) }).Count -gt 0 }
            'all_of_scopes' {
                Assert-That ((Value $node 'array') -eq 'original_cores') 'Unexpected scope array'
                $conditions = @($node.Children | Where-Object Key -ne 'array')
                @($scope.Cores | Where-Object { -not (Test-Conditions $conditions $world $world.States["$_"] $scope) }).Count -eq 0
            }
            'date' {
                $parts = $v.Split('.')
                $date = [datetime]::new([int] $parts[0], [int] $parts[1], [int] $parts[2])
                switch ($node.Op) { '>' { $world.Date -gt $date }; '<' { $world.Date -lt $date }; default { throw 'Unexpected date comparison' } }
            }
            default {
                if ($triggers.ContainsKey($node.Key)) { (Test-Conditions $triggers[$node.Key].Children $world $scope $previous) -eq ($v -eq 'yes') }
                elseif ($world.Countries.ContainsKey($node.Key)) { Test-Conditions $node.Children $world $world.Countries[$node.Key] $scope }
                elseif ($world.States.ContainsKey($node.Key)) { Test-Conditions $node.Children $world $world.States[$node.Key] $scope }
                else { throw "Unsupported predicate: $($node.Key)" }
            }
        }
        if (-not $ok) { return $false }
    }
    return $true
}
function Test-Available([string] $id, $world) {
    foreach ($p in (Prop $focus[$id] 'prerequisite')) {
        if (@($p.Children | Where-Object { $_.Value -in $world.Completed }).Count -eq 0) { return $false }
    }
    return Test-Conditions (Prop $focus[$id] 'available').Children $world
}

Test-Case 'Parser ignores comments and quoted braces, preserving repeated blocks' {
    $sample = Parse-Code "shared_focus = { id = real icon = actual log = `"id = fake }`" # }`n prerequisite = { focus = a } prerequisite = { focus = b } }"
    Assert-That ((Value $sample[0] 'id') -eq 'real' -and (Prop $sample[0] 'prerequisite').Count -eq 2) 'Incorrect extraction'
}
Test-Case 'All 383 focus references exist and mutually exclusive links are symmetric' {
    Assert-That ($focus.Count -eq 383) 'Unexpected focus inventory'
    foreach ($id in $focus.Keys) {
        foreach ($key in @('prerequisite', 'mutually_exclusive')) {
            foreach ($p in (Prop $focus[$id] $key)) {
                foreach ($ref in $p.Children.Value) {
                    Assert-That ($focus.ContainsKey($ref)) "Missing $key reference: $id -> $ref"
                    if ($key -eq 'mutually_exclusive') { Assert-That ($id -in (Prop $focus[$ref] $key).Children.Value) "Asymmetric exclusion: $id -> $ref" }
                }
            }
        }
        $anchor = Value $focus[$id] 'relative_position_id'
        Assert-That (-not $anchor -or $focus.ContainsKey($anchor)) "Missing coordinate anchor: $id"
    }
}
foreach ($pair in @(
    @('HSM_CYA_proclaim_cyanolisian_march', 'HSM_CYA_frontier_march_formed'),
    @('HSM_CYA_regency_coronation_preparations', 'HSM_CYA_countess_crown_prepared')
)) {
    Test-Case "Focus refresh follows visibility flag: $($pair[0])" {
        $reward = (Prop $focus[$pair[0]] 'completion_reward').Children
        $seen = $false; $refreshed = $false
        foreach ($n in $reward) {
            if ($n.Key -eq 'set_country_flag' -and $n.Value -eq $pair[1]) { $seen = $true }
            if ($seen -and $n.Key -eq 'mark_focus_tree_layout_dirty') { $refreshed = $true }
        }
        Assert-That $refreshed 'No refresh after the flag change'
    }
}
foreach ($spec in @(@('10', 'HSM_CYA_path_imperial_administration'), @('40', 'HSM_CYA_1021_crown_in_trust'), @('2', 'HSM_CYA_path_imperial_administration'))) {
    Test-Case "Event refresh follows visibility flag: $($spec[0])" {
        $seen = $false; $refreshed = $false
        foreach ($option in (Prop $events["hsm_cyanolisia.$($spec[0])"] 'option')) {
            foreach ($n in $option.Children) {
                if ($n.Key -eq 'set_country_flag' -and $n.Value -eq $spec[1]) { $seen = $true }
                if ($seen -and $n.Key -eq 'mark_focus_tree_layout_dirty') { $refreshed = $true }
            }
        }
        Assert-That $refreshed 'No refresh after the flag change'
    }
}
Test-Case 'Living foreign Grover does not block campaigns or allow a local execution' {
    $w = New-World; Add-State $w 382
    $w.Root.Flags = @('HSM_CYA_empire_descendant_declared')
    $w.Completed = @('HSM_CYA_question_of_grover')
    Assert-That (Test-Available 'HSM_CYA_empire_after_grover' $w) 'Campaigns still depend on custody'
    foreach ($id in @('HSM_CYA_execute_the_child_emperor', 'HSM_CYA_the_puppet_emperor', 'HSM_CYA_the_child_may_rule', 'HSM_CYA_grover_lost_to_others')) {
        Assert-That (-not (Test-Available $id $w)) "Foreign ruler can be disposed of: $id"
    }
}
Test-Case 'Countess coronation is reachable before continental unification, with age and custody guards' {
    $w = New-World; Add-State $w 382; Add-State $w 389
    $w.Root.Characters = @('GRI_emperor_grover_vi')
    $w.Completed = @('HSM_CYA_countess_regency_for_grover')
    Assert-That (Test-Available 'HSM_CYA_regency_coronation_preparations' $w) 'Preparation still waits for conquest'
    $w.Completed += 'HSM_CYA_regency_coronation_preparations'
    Assert-That (Test-Available 'HSM_CYA_crown_in_trust' $w) 'Adult in custody cannot be crowned'
    $w.Date = [datetime]::new(1020, 1, 1)
    Assert-That (-not (Test-Available 'HSM_CYA_crown_in_trust' $w)) 'Minor can be crowned as adult'
    $w.Root.Flags += 'HSM_CYA_grover_reigned_elsewhere'
    Assert-That (Test-Available 'HSM_CYA_crown_in_trust' $w) 'Prior ruler return no longer works'
    $w.Root.Characters = @()
    Assert-That (-not (Test-Available 'HSM_CYA_crown_in_trust' $w)) 'Foreign Grover can be crowned locally'
}
Test-Case 'Existing outback policy does not lock administrative consolidation' {
    $w = New-World
    $w.Root.Flags = @('HSM_CYA_imperial_cabinet_installed'); $w.Root.Ideas = @('CYA_policed_outback')
    $w.Completed = @('HSM_CYA_install_imperial_cabinet')
    Assert-That (Test-Available 'HSM_CYA_regularise_minotaur_administration' $w) 'Existing policy blocks reform'
}
Test-Case 'Herzland bypass requires every targeted territory, not just Griffenheim' {
    $w = New-World; Add-State $w 382
    $i = 1000
    foreach ($tag in @('GRI', 'STW', 'FEA', 'PYT', 'ROU', 'YAL', 'ANG', 'KAT', 'BRZ')) {
        $w.Countries[$tag] = @{ Tag = $tag; Cores = @($i) }; Add-State $w $i; $i++
    }
    foreach ($id in @('HSM_CYA_restore_imperial_provinces', 'HSM_CYA_march_on_imperial_provinces')) {
        $bypass = (Prop $focus[$id] 'bypass').Children
        Assert-That (Test-Conditions $bypass $w) 'Completed conquest cannot bypass'
        $w.States['1008'].Owner = 'BRZ'; $w.States['1008'].Controller = 'BRZ'
        Assert-That (-not (Test-Conditions $bypass $w)) 'Capital alone skips remaining principalities'
        $w.Countries.BRZ.Overlord = 'CYA'
        Assert-That (Test-Conditions $bypass $w) 'Subject territory not recognized'
        $w.Countries.BRZ.Remove('Overlord'); $w.States['1008'].Owner = 'CYA'; $w.States['1008'].Controller = 'CYA'
    }
}
foreach ($id in @('HSM_CYA_one_griffonia_under_the_crown', 'HSM_CYA_one_griffonia_under_claw')) {
    Test-Case "Finale rechecks Evi, HLR, ownership and hostile occupation: $id" {
        $w = New-World
        $w.Completed = @((Prop $focus[$id] 'prerequisite').Children.Value)
        $w.Countries.HLR = @{ Tag = 'HLR' }; $w.Countries.MIT = @{ Tag = 'MIT'; Overlord = 'CYA' }
        foreach ($state in @(382, 425, 590, 386)) { Add-State $w $state }
        Assert-That (Test-Available $id $w) 'United map rejected'
        foreach ($state in @('425', '590')) {
            $w.States[$state].Owner = 'HLR'
            Assert-That (-not (Test-Available $id $w)) "Occupation without ownership accepted: $state"
            $w.States[$state].Owner = 'CYA'; $w.States[$state].Controller = 'HLR'
            Assert-That (-not (Test-Available $id $w)) "Lost territory accepted: $state"
            $w.States[$state].Controller = 'CYA'
        }
        $w.States['386'].Owner = 'MIT'; $w.States['386'].Controller = 'MIT'
        Assert-That (Test-Available $id $w) 'Commissariat or protectorate rejected'
        Add-State $w 9998 'HLR' 'HLR' 'europe'
        Add-State $w 9999 'HLR' 'HLR' 'asia' $true
        Assert-That (Test-Available $id $w) 'Overseas or impassable territory is mandatory'
    }
}
Test-Case 'Remaining claims target territorial owners, not extinct original tags or our subjects' {
    $limit = (Prop (Prop $effects.HSM_CYA_claim_remaining_griffonia 'every_other_country') 'limit').Children
    $w = New-World; $w.Countries.HLR = @{ Tag = 'HLR' }; Add-State $w 425 'HLR' 'HLR'
    Assert-That (Test-Conditions $limit $w $w.Countries.HLR) 'Independent territorial holder missed'
    $w.Countries.HLR.Overlord = 'CYA'
    Assert-That (-not (Test-Conditions $limit $w $w.Countries.HLR)) 'Claim targets our subject'
    $w.Countries.HLR.Remove('Overlord'); $w.Root.Goals = @('HLR')
    Assert-That (-not (Test-Conditions $limit $w $w.Countries.HLR)) 'Existing claim repeated'
    $w.Root.Goals = @(); $w.Countries.HLR.Wars = @('CYA')
    Assert-That (-not (Test-Conditions $limit $w $w.Countries.HLR)) 'Existing war targeted'
}
foreach ($pair in @(@('countess_western_circuits', 'countess_eastern_circuits'), @('western_imperial_circuits', 'eastern_imperial_circuits'))) {
    Test-Case "Remaining claims unlock whichever regional circuit finishes last: $($pair[0])" {
        for ($i = 0; $i -lt 2; $i++) {
            $reward = Prop $focus["HSM_CYA_$($pair[$i])"] 'completion_reward'
            $branch = @(Prop $reward 'if' | Where-Object { (Prop $_ 'HSM_CYA_claim_remaining_griffonia').Count })
            Assert-That ($branch.Count -eq 1) 'Missing completion hook'
            $w = New-World
            Assert-That (-not (Test-Conditions (Prop $branch[0] 'limit').Children $w)) 'Claims unlock before both circuits'
            $w.Completed = @("HSM_CYA_$($pair[1 - $i])")
            Assert-That (Test-Conditions (Prop $branch[0] 'limit').Children $w) 'Claims require the focus still being completed'
        }
    }
}
Test-Case 'Imperial navy accepts the base-game imperial proclamation on every route' {
    $w = New-World; Add-State $w 382
    $w.Completed = @('HSM_CYA_coastal_defence_batteries', 'HSM_CYA_bluewater_shipyards')
    Assert-That (-not (Test-Available 'HSM_CYA_imperial_convoy_authority' $w)) 'No proclamation required'
    $w.Root.Flags = @('holds_griffon_capital')
    Assert-That (Test-Available 'HSM_CYA_imperial_convoy_authority' $w) 'Legacy imperial route rejected'
}

# Exercise the same small scope chain used by regional war-goal effects.
function Invoke-Claims($nodes, $world, $scope = $world.Root, $previous = $null) {
    foreach ($node in $nodes) {
        switch ($node.Key) {
            'custom_effect_tooltip' { }
            'hidden_effect' { Invoke-Claims $node.Children $world $scope $previous }
            'every_of_scopes' {
                Assert-That ((Value $node 'array') -eq 'original_cores') 'Unexpected claim array'
                foreach ($state in $scope.Cores) {
                    $target = $world.States["$state"]
                    if (Test-Conditions (Prop $node 'limit').Children $world $target $scope) {
                        Invoke-Claims @($node.Children | Where-Object { $_.Key -notin @('array', 'limit') }) $world $target $scope
                    }
                }
            }
            'owner' { Invoke-Claims $node.Children $world $world.Countries[$scope.Owner] $scope }
            'ROOT' { Invoke-Claims $node.Children $world $world.Root $scope }
            'if' {
                if (Test-Conditions (Prop $node 'limit').Children $world $scope $previous) {
                    Invoke-Claims @($node.Children | Where-Object Key -ne 'limit') $world $scope $previous
                }
            }
            'create_wargoal' {
                Assert-That ((Value $node 'target') -eq 'PREV' -and (Value $node 'type') -eq 'annex_everything') 'Wrong claim scope/type'
                $scope.Goals += $previous.Tag
            }
            default {
                if ($effects.ContainsKey($node.Key)) { Invoke-Claims $effects[$node.Key].Children $world $scope $previous }
                elseif ($world.Countries.ContainsKey($node.Key)) { Invoke-Claims $node.Children $world $world.Countries[$node.Key] $scope }
                else { throw "Unsupported claim effect: $($node.Key)" }
            }
        }
    }
}

$campaignRoutes = @(
    @{ Route = 'countess'; Root = 'countess_union_mandate'; West = 'countess_western_circuits'; East = 'countess_eastern_circuits'; Final = 'one_griffonia_under_the_crown';
       Campaigns = @{ north = 'countess_northern_charters'; central = 'countess_lake_charters'; west = 'countess_western_concord'; south = 'countess_southern_compacts'; frontier = 'countess_frontier_mandate'; river = 'countess_river_missions'; hills = 'countess_hill_compacts' };
       Settlements = @{ north = 'countess_northern_assizes'; central = 'countess_lake_reconstruction'; west = 'countess_western_reconstruction'; south = 'countess_karthin_settlement'; frontier = 'countess_frontier_ports' } },
    @{ Route = 'dawnclaw'; Root = 'empire_after_grover'; West = 'western_imperial_circuits'; East = 'eastern_imperial_circuits'; Final = 'one_griffonia_under_claw';
       Campaigns = @{ north = 'the_northern_submission'; central = 'break_the_lake_countries'; west = 'crush_the_western_crowns'; south = 'claim_the_southern_crowns'; frontier = 'reclaim_the_griffon_frontier'; river = 'cross_the_river_frontier'; hills = 'subdue_the_hillponies' };
       Settlements = @{ north = 'northern_garrison_network'; central = 'lake_transit_authority'; west = 'western_reconstruction_office'; south = 'karthin_war_industry'; frontier = 'frontier_supply_ports' } }
)

foreach ($route in $campaignRoutes) {
    foreach ($region in $route.Campaigns.Keys | Sort-Object) {
        Test-Case "$($route.Route) $($region): territorial bypass, staged prerequisites and actual-owner claims" {
            $campaign = $route.Campaigns[$region]
            $settlement = $route.Settlements[$region]
            $parent = if ($region -in @('north', 'central', 'west')) { $route.Root }
                elseif ($region -eq 'south') { $route.Settlements.west }
                elseif ($region -eq 'frontier') { $route.Settlements.central } else { $route.Settlements.frontier }
            $w = New-World
            $w.Countries.INV = @{ Tag = 'INV'; Wars = @() }
            $tags = @((Prop $triggers["HSM_CYA_campaign_$($region)_secured"] 'custom_trigger_tooltip').Children |
                Where-Object Key -ne 'tooltip' | ForEach-Object Key)
            $state = 2000
            foreach ($tag in $tags) {
                $w.Countries[$tag] = @{ Tag = $tag; Cores = @($state) }
                Add-State $w $state; $state++
            }
            $n = $focus["HSM_CYA_$campaign"]
            Assert-That (((Prop $n 'prerequisite').Children.Value -join ',') -eq "HSM_CYA_$parent") 'Campaign in the wrong wave'
            Assert-That (Test-Conditions (Prop $n 'bypass').Children $w) 'Secured region does not bypass'
            $w.States['2000'].Owner = 'INV'; $w.States['2000'].Controller = 'INV'
            Assert-That (-not (Test-Conditions (Prop $n 'bypass').Children $w)) 'Third-party conquest incorrectly skips war goal'
            Invoke-Claims $effects["HSM_CYA_claim_$region"].Children $w
            Assert-That (($w.Root.Goals -join ',') -eq 'INV') 'War goal does not target actual owner exactly once'
            Invoke-Claims $effects["HSM_CYA_claim_$region"].Children $w
            Assert-That ($w.Root.Goals.Count -eq 1) 'Duplicate war goal'
            $w.Root.Goals = @(); $w.Countries.INV.Overlord = 'CYA'
            Invoke-Claims $effects["HSM_CYA_claim_$region"].Children $w
            Assert-That ($w.Root.Goals.Count -eq 0) 'War goal against our subject'
            Assert-That (Test-Conditions (Prop $n 'bypass').Children $w) 'Subject region rejected'
            $w.Countries.INV.Remove('Overlord'); $w.Countries.INV.Wars = @('CYA')
            Invoke-Claims $effects["HSM_CYA_claim_$region"].Children $w
            Assert-That ($w.Root.Goals.Count -eq 0) 'War goal against current enemy'
            if ($settlement) {
                $settlementNode = $focus["HSM_CYA_$settlement"]
                $w.Completed = @("HSM_CYA_$campaign")
                Assert-That (-not (Test-Available "HSM_CYA_$settlement" $w)) 'Reconstruction available before ownership'
                $w.States['2000'].Owner = 'CYA'; $w.States['2000'].Controller = 'CYA'
                Assert-That (Test-Available "HSM_CYA_$settlement" $w) 'Reconstruction unavailable after conquest'
                Assert-That ((Prop (Prop $settlementNode 'completion_reward') "HSM_CYA_integrate_$region").Count -eq 1) 'Integration not awarded locally'
                Assert-That ((Prop $settlementNode 'bypass').Count -eq 0) 'Settlement bypass loses reconstruction reward'
            }
        }
    }
}

Test-Case 'Griffonian integration excludes pony countries and Asterion' {
    $forbidden = @('LCT', 'RCT', 'NIM', 'WIT', 'BAK', 'DEP', 'FRE', 'DMT', 'FBK', 'FIR', 'WAT', 'NCH', 'JRV', 'JHP', 'MIT')
    foreach ($region in @('north', 'central', 'west', 'south', 'frontier')) {
        $tags = @((Prop $effects["HSM_CYA_integrate_$region"] 'hidden_effect').Children | ForEach-Object Key)
        Assert-That (@($tags | Where-Object { $_ -in $forbidden }).Count -eq 0) "Forbidden integration in $region"
        Assert-That ($tags.Count -gt 0) "Empty integration: $region"
    }
    foreach ($id in @('countess_eastern_circuits', 'eastern_imperial_circuits')) {
        $reward = Prop $focus["HSM_CYA_$id"] 'completion_reward'
        Assert-That (@($reward.Children | Where-Object Key -cmatch '^[A-Z]{3}$').Count -eq 0) 'Eastern circuits still core countries'
        Assert-That ((Value (Prop $reward 'country_event') 'id') -eq 'hsm_cyanolisia.49') 'Commissariat notification missing'
    }
}
Test-Case 'Blackhollow override blocks both paths, including an already-running decision' {
    $code = Read-Code 'mod/HoISubmod/common/decisions/CYA_decisions.txt'
    $category = @($code | Where-Object Key -eq 'CYA_deal_with_blackhollow')[0]
    $decision = Prop $category 'CYA_blackhollow_republic'
    $w = New-World; $w.Countries.BAN = @{ Tag = 'BAN'; Exists = $false }
    foreach ($s in @(490, 606, 489, 532)) { Add-State $w $s }
    foreach ($flag in @('', 'HSM_CYA_path_frontier_march', 'HSM_CYA_path_marriage', 'HSM_CYA_path_imperial_administration')) {
        $w.Root.Flags = @($flag)
        $blocked = $flag -in @('HSM_CYA_path_marriage', 'HSM_CYA_path_imperial_administration')
        foreach ($key in @('visible', 'available')) {
            Assert-That ((Test-Conditions (Prop $decision $key).Children $w) -eq (-not $blocked)) "$flag / $key"
        }
        Assert-That ((Test-Conditions (Prop $decision 'cancel_trigger').Children $w) -eq $blocked) "No cancellation: $flag"
        $guard = (Prop (Prop (Prop $decision 'remove_effect') 'if') 'limit').Children
        Assert-That ((Test-Conditions $guard $w) -eq (-not $blocked)) "Pending release not guarded: $flag"
    }
    Assert-That (-not (Test-Path (Join-Path $root 'mod/HoISubmod/common/decisions/HSM_CYA_blackhollow_override.txt'))) 'Duplicate old decision override'
    $base = Read-Code 'EaW/common/decisions/CYA_decisions.txt'
    foreach ($cat in $base) {
        $replacement = @($code | Where-Object Key -eq $cat.Key)[0]
        foreach ($decision in $cat.Children | Where-Object Key -ne 'CYA_blackhollow_republic') {
            $other = Prop $replacement $decision.Key
            Assert-That ($other.Count -eq 1) "Missing decision: $($decision.Key)"
            Assert-That (($decision | ConvertTo-Json -Depth 100 -Compress) -ceq ($other[0] | ConvertTo-Json -Depth 100 -Compress)) "Unrelated decision changed: $($decision.Key)"
        }
    }
}

function Position([string] $id, $world, $chain = @()) {
    Assert-That ($id -notin $chain) "Coordinate cycle: $id"
    $n = $focus[$id]; $x = [int] (Value $n 'x'); $y = [int] (Value $n 'y')
    $anchor = Value $n 'relative_position_id'
    if ($anchor) { $p = Position $anchor $world ($chain + $id); $x += $p.X; $y += $p.Y }
    foreach ($offset in (Prop $n 'offset')) {
        if (Test-Conditions (Prop $offset 'trigger').Children $world) { $x += [int] (Value $offset 'x'); $y += [int] (Value $offset 'y') }
    }
    return @{ X = $x; Y = $y }
}
function Visible([string] $id, $world, $chain = @()) {
    Assert-That ($id -notin $chain) "Prerequisite cycle: $id"
    $allow = @(Prop $focus[$id] 'allow_branch')
    if ($allow.Count) { return Test-Conditions $allow[0].Children $world }
    foreach ($p in (Prop $focus[$id] 'prerequisite')) {
        if (@($p.Children | Where-Object { Visible $_.Value $world ($chain + $id) }).Count -eq 0) { return $false }
    }
    return $true
}
Test-Case 'Campaign opening is beside custody choices, not connected through them' {
    $w = New-World
    $campaign = Position 'HSM_CYA_empire_after_grover' $w
    foreach ($id in @('HSM_CYA_execute_the_child_emperor', 'HSM_CYA_the_puppet_emperor', 'HSM_CYA_the_child_may_rule', 'HSM_CYA_grover_lost_to_others')) {
        $choice = Position $id $w
        Assert-That ($campaign.Y -eq $choice.Y -and $campaign.X - $choice.X -ge 2) "Campaign edge crosses custody choice: $id"
    }
}
Test-Case 'Death exits either dominance route and exposes only the administrative continuation' {
    foreach ($route in @('dawnclaw', 'countess')) {
        $w = New-World
        $w.Root.Flags = @('HSM_CYA_dawnclaw_branch_unlocked', 'HSM_CYA_path_marriage', "HSM_CYA_$($route)_dominant")
        foreach ($n in (Prop $events['hsm_cyanolisia.10'] 'option').Children) {
            if ($n.Key -eq 'set_country_flag') { $w.Root.Flags += $n.Value }
            if ($n.Key -eq 'clr_country_flag') { $w.Root.Flags = @($w.Root.Flags | Where-Object { $_ -ne $n.Value }) }
        }
        Assert-That (Visible 'HSM_CYA_install_imperial_cabinet' $w) 'Administrative route hidden'
        foreach ($id in @('HSM_CYA_empire_after_grover', 'HSM_CYA_the_countess_alone', 'HSM_CYA_countess_union_mandate', 'HSM_CYA_crown_field_staff', 'HSM_CYA_dawnclaw_operational_staff')) {
            Assert-That (-not (Visible $id $w)) "Obsolete dominance route remains visible: $id"
        }
        Assert-That (Visible 'HSM_CYA_border_defense_staff' $w) 'Administrative military continuation hidden'
    }
}
$membership = @{}
foreach ($tree in $trees) {
    $ids = [System.Collections.Generic.HashSet[string]]::new([string[]] (Prop $tree 'shared_focus').Value)
    do {
        $changed = $false
        foreach ($id in $focus.Keys) {
            if (-not $ids.Contains($id) -and @((Prop $focus[$id] 'prerequisite').Children.Value | Where-Object { $ids.Contains($_) }).Count) { [void] $ids.Add($id); $changed = $true }
        }
    } while ($changed)
    $membership[(Value $tree 'id')] = @($ids)
}
$scenarios = @{
    initial = @(); asylum = @('dawnclaw_branch_unlocked')
    frontier = @('dawnclaw_branch_unlocked', 'path_frontier_march')
    march = @('dawnclaw_branch_unlocked', 'path_frontier_march', 'frontier_march_formed')
    countess = @('dawnclaw_branch_unlocked', 'path_marriage', 'countess_dominant')
    dawnclaw = @('dawnclaw_branch_unlocked', 'path_marriage', 'dawnclaw_dominant')
    administration = @('dawnclaw_branch_unlocked', 'path_imperial_administration', 'dawnclaw_dead')
    departure = @('dawnclaw_branch_unlocked', 'path_imperial_administration', 'dawnclaw_departed')
	refusal = @('path_imperial_administration')
	exile = @('path_imperial_administration', 'exile_court_received')
	exile_crowned = @('path_imperial_administration', 'exile_court_received', 'exile_coronation_done')
}
foreach ($settlement in @('countess_crown_prepared', '1021_crown_in_trust', '1021_memorial_regency')) {
    $scenarios[$settlement] = $scenarios.countess + @('empire_descendant_declared', 'countess_crown_prepared', $settlement)
}
foreach ($pair in @(@('1021_caged_coronation', 'grover_puppet'), @('1021_grover_restored', 'grover_restored'), @('1021_empty_throne', 'grover_executed'), @('1021_empty_throne', 'grover_absent'))) {
    $scenarios[$pair[1]] = $scenarios.dawnclaw + @('empire_descendant_declared') + $pair
}
$scenarios.right = @(); $scenarios.left = @(); $scenarios.secret = @()
foreach ($name in ($scenarios.Keys | Sort-Object)) {
    Test-Case "Layout has no overlaps or same-row prerequisites: $name" {
        $w = New-World; $w.Root.Flags = @($scenarios[$name] | ForEach-Object { "HSM_CYA_$_" })
        if ($name -eq 'right') { $w.Completed = @('CYA_the_conference_at_evosmoshafen') }
        if ($name -eq 'left') { $w.Completed = @('CYA_the_group_of_twenty') }
        if ($name -in @('1021_memorial_regency', 'grover_executed', 'grover_absent')) { $w.Global = @('GRI_grover_vi_dead') }
        $tree = if ($name -eq 'secret') { 'cyan_secret' } else { 'cyan_original' }
        $positions = @{}
        foreach ($id in $membership[$tree]) { if (Visible $id $w) { $positions[$id] = Position $id $w } }
        $ids = @($positions.Keys)
        for ($i = 0; $i -lt $ids.Count; $i++) {
            $a = $positions[$ids[$i]]
            for ($j = $i + 1; $j -lt $ids.Count; $j++) {
                $b = $positions[$ids[$j]]
                Assert-That ($a.Y -ne $b.Y -or [Math]::Abs($a.X - $b.X) -ge 2) "Overlap: $($ids[$i]) / $($ids[$j])"
            }
            foreach ($parent in (Prop $focus[$ids[$i]] 'prerequisite').Children.Value) {
                if ($positions.ContainsKey($parent)) { Assert-That ($positions[$parent].Y -lt $a.Y) "Non-downward edge: $parent -> $($ids[$i])" }
            }
        }
    }
}

# Exercise policy effects directly; this remains a small scenario interpreter.
function Invoke-Policy($nodes, $world, $scope = $world.Root) {
    $branchTaken = $false
    foreach ($n in $nodes) {
        switch ($n.Key) {
            { $_ -in @('name', 'trigger', 'ai_chance', 'custom_effect_tooltip', 'log') } { continue }
            'set_country_flag' {
                $flag = if ($n.Children.Count) { Value $n 'flag' } else { $n.Value }
                $scope.Flags = @($scope.Flags) + $flag
            }
            'clr_country_flag' { $scope.Flags = @($scope.Flags | Where-Object { $_ -ne $n.Value }) }
            'add_to_variable' {
                if (-not $scope.Variables) { $scope.Variables = @{} }
                $v = @($n.Children | Where-Object Key -ne 'tooltip')[0]
                $scope.Variables[$v.Key] = [decimal] $scope.Variables[$v.Key] + [decimal] $v.Value
            }
            'remove_ideas' { $scope.Ideas = @($scope.Ideas | Where-Object { $_ -ne $n.Value }) }
            'add_ideas' { $scope.Ideas = @($scope.Ideas) + $n.Value }
            'recruit_character' { $scope.Characters = @($scope.Characters) + $n.Value }
            'if' {
                $branchTaken = Test-Conditions (Prop $n 'limit').Children $world $scope
                if ($branchTaken) {
                    Invoke-Policy @($n.Children | Where-Object Key -ne 'limit') $world $scope
                }
            }
            'else_if' {
                if (-not $branchTaken -and (Test-Conditions (Prop $n 'limit').Children $world $scope)) {
                    $branchTaken = $true
                    Invoke-Policy @($n.Children | Where-Object Key -ne 'limit') $world $scope
                }
            }
            'else' { if (-not $branchTaken) { Invoke-Policy $n.Children $world $scope }; $branchTaken = $true }
            'ROOT' { Invoke-Policy $n.Children $world $world.Root }
            'swap_ideas' {
                $scope.Ideas = @($scope.Ideas | Where-Object { $_ -ne (Value $n 'remove_idea') }) + (Value $n 'add_idea')
            }
            'mark_focus_tree_layout_dirty' { $world.LayoutDirty = $true }
            'promote_character' { $scope.Leader = $n.Value }
            'set_politics' { $scope.Government = Value $n 'ruling_party' }
            'set_portraits' { $scope.Portraits = $n }
            'add_country_leader_role' {
                Assert-That ((Value $n 'promote_leader') -eq 'yes') 'Unexpected leader role without promotion'
                $scope.Leader = Value $n 'character'
            }
            'add_dynamic_modifier' { $scope.Programs = @($scope.Programs) + (Value $n 'modifier') }
            'FROM' { Invoke-Policy $n.Children $world $world.Sender }
            'set_autonomy' {
                Assert-That ((Value $n 'target') -eq 'ROOT') 'Unexpected autonomy target'
                $world.Root.Overlord = $scope.Tag
            }
            'country_event' { $scope.Events = @($scope.Events) + (Value $n 'id') }
            'add_building_construction' { $scope.Buildings = @($scope.Buildings) + $n }
            'add_extra_state_shared_building_slots' { $scope.Slots = [int] $scope.Slots + [int] $n.Value }
            'add_tech_bonus' { $scope.Research = @($scope.Research) + $n }
            { $_ -in @('add_political_power', 'army_experience', 'add_command_power', 'add_stability') } { $scope[$n.Key] = [decimal] $scope[$n.Key] + [decimal] $n.Value }
            default {
                if ($effects.ContainsKey($n.Key)) { Invoke-Policy $effects[$n.Key].Children $world $scope }
                elseif ($world.Countries.ContainsKey($n.Key)) { Invoke-Policy $n.Children $world $world.Countries[$n.Key] }
                elseif ($n.Key -in $scope.Characters) {
                    Assert-That ($n.Children.Count -eq 1 -and (Value $n 'set_nationality') -eq 'ROOT') 'Unexpected character effect'
                    $scope.Characters = @($scope.Characters | Where-Object { $_ -ne $n.Key })
                    $world.Root.Characters += $n.Key
                }
                elseif ($world.States.ContainsKey($n.Key)) { Invoke-Policy $n.Children $world $world.States[$n.Key] }
                else { throw "Unsupported policy effect: $($n.Key)" }
            }
        }
    }
}
function Eligible-Options($event, $world) {
    @(Prop $event 'option' | Where-Object { Test-Conditions (Prop $_ 'trigger').Children $world })
}
$settlement = @(Read-Code 'mod/HoISubmod/common/decisions/HSM_CYA_imperial_settlement.txt')[0]
function Peace-World([string] $route = 'countess') {
    $w = New-World
    $w.Root.Flags = @("HSM_CYA_$($route)_dominant",
        $(if ($route -eq 'countess') { 'HSM_CYA_countess_griffonia_unified' } else { 'HSM_CYA_griffonia_claimed' }))
    $w.Completed = @($(if ($route -eq 'countess') { 'HSM_CYA_countess_union_mandate' } else { 'HSM_CYA_empire_after_grover' }))
    foreach ($s in @(382, 485, 470, 377)) { Add-State $w $s }
    return $w
}
foreach ($region in @('north', 'central', 'west', 'south', 'frontier', 'river', 'hills')) {
    Test-Case "Renewed $region claims follow changed owners after a completed campaign" {
        $d = Prop $settlement "HSM_CYA_renew_$($region)_claims"
        foreach ($r in $campaignRoutes) {
            $w = New-World
            $w.Countries.INV = @{ Tag = 'INV'; Cores = @(); Wars = @() }
            $tags = @((Prop $triggers["HSM_CYA_campaign_$($region)_secured"] 'custom_trigger_tooltip').Children |
                Where-Object Key -ne 'tooltip' | ForEach-Object Key)
            $i = 2000
            foreach ($tag in $tags) { $w.Countries[$tag] = @{ Tag = $tag; Cores = @($i) }; Add-State $w $i; $i++ }
            $w.States['2000'].Owner = 'INV'; $w.States['2000'].Controller = 'INV'
            Assert-That (-not (Test-Conditions (Prop $d 'visible').Children $w)) 'Claims exposed before the campaign'
            $w.Completed = @("HSM_CYA_$($r.Campaigns[$region])")
            Assert-That (Test-Conditions (Prop $d 'visible').Children $w) 'No recovery from third-party ownership'
            Invoke-Claims (Prop $d 'complete_effect').Children $w
            Assert-That (($w.Root.Goals -join ',') -eq 'INV') 'Recovery targets the former owner'
            $w.Root.Goals = @(); $w.Countries.INV.Overlord = 'CYA'
            Assert-That (-not (Test-Conditions (Prop $d 'visible').Children $w)) 'Recovered subject remains a target'
            $w.Countries.INV.Remove('Overlord')
            Assert-That (Test-Conditions (Prop $d 'visible').Children $w) 'Subject independence leaves a deadlock'
        }
    }
}
foreach ($n in @(54, 55, 56)) {
    Test-Case "Regional settlement $n has route-specific exclusive, one-shot choices" {
        foreach ($route in @('countess', 'dawnclaw')) {
            foreach ($choice in @(0, 1)) {
                $w = Peace-World $route
                $e = $events["hsm_cyanolisia.$n"]
                Assert-That (Test-Conditions (Prop $e 'trigger').Children $w) 'Settlement cannot open'
                $options = Eligible-Options $e $w
                Assert-That ($options.Count -eq 2) 'Wrong number of route choices'
                Invoke-Policy $options[$choice].Children $w
                Assert-That (-not (Test-Conditions (Prop $e 'trigger').Children $w)) 'Settlement can award twice'
                $other = @(Prop $options[1 - $choice] 'set_country_flag')[-1].Value
                Assert-That ($other -notin $w.Root.Flags) 'Conflicting institution selected'
            }
        }
    }
}
Test-Case 'Grover policies remain selectable without schooling and retain institutional callbacks' {
    foreach ($crown in @('1021_crown_in_trust', '1021_grover_restored')) {
        foreach ($lesson in @('', 'grover_lesson_mercy', 'grover_lesson_authority', 'grover_lesson_frontier')) {
            foreach ($choice in @(0, 1, 2)) {
                $w = Peace-World
                $w.Root.Characters = @('GRI_emperor_grover_vi')
                $w.Root.Flags += @("HSM_CYA_$crown", "HSM_CYA_$lesson", 'HSM_CYA_northern_charters', 'HSM_CYA_lake_military_administration')
                $e = $events['hsm_cyanolisia.53']
                Assert-That (Test-Conditions (Prop $e 'trigger').Children $w) 'Personal council unavailable'
                $options = Eligible-Options $e $w
                Assert-That ($options.Count -eq 3) 'Education locks a policy'
                Invoke-Policy $options[$choice].Children $w
                Assert-That (-not (Test-Conditions (Prop $e 'trigger').Children $w)) 'Council rewards repeat'
                if ($choice -eq 0) { Assert-That ($w.Root.add_political_power -ge 50) 'Charter callback has no effect' }
                if ($choice -eq 1) { Assert-That ($w.Root.army_experience -eq 25) 'Military oversight callback has no effect' }
            }
        }
    }
    $w.Global = @('GRI_grover_vi_dead')
    Assert-That (-not (Test-Conditions (Prop $e 'trigger').Children $w)) 'Dead Grover holds a council'
}
Test-Case 'Puppet audiences change policy without handing over executive authority' {
    $e = $events['hsm_cyanolisia.57']
    foreach ($choice in @(0, 1)) {
        $w = Peace-World 'dawnclaw'
        $w.Root.Flags += 'HSM_CYA_1021_caged_coronation'
        $w.Root.Characters = @('GRI_emperor_grover_vi')
        Assert-That (Test-Conditions (Prop $e 'trigger').Children $w) 'Puppet audience unavailable'
        $options = Eligible-Options $e $w
        Invoke-Policy $options[$choice].Children $w
        Assert-That (-not (Test-Conditions (Prop $e 'trigger').Children $w)) 'Puppet rewards repeat'
    }
    Assert-That (($e | ConvertTo-Json -Depth 40) -notmatch 'promote_leader|set_politics') 'Puppet silently becomes ruler'
}
foreach ($step in @('demobilization', 'reconstruction', 'constitution')) {
    Test-Case "Peace commission $step cancels on war/lost territory and cannot repeat rewards" {
        $number = 58 + [array]::IndexOf(@('demobilization', 'reconstruction', 'constitution'), $step)
        $d = Prop $settlement "HSM_CYA_peace_$step"
        $e = $events["hsm_cyanolisia.$number"]
        $w = Peace-World
        if ($step -eq 'reconstruction') { $w.Root.Flags += 'HSM_CYA_peace_demobilization_done' }
        if ($step -eq 'constitution') { $w.Root.Flags += 'HSM_CYA_peace_reconstruction_done' }
        Assert-That (Test-Conditions (Prop $d 'visible').Children $w) 'Commission unavailable in order'
        Assert-That (Test-Conditions (Prop $d 'available').Children $w) 'Peace rejected'
        $w.Root.AtWar = $true
        Assert-That (Test-Conditions (Prop $d 'cancel_trigger').Children $w) 'War does not cancel'
        Invoke-Policy (Prop $d 'remove_effect').Children $w
        Assert-That (-not $w.Root.Events) 'Cancelled commission grants an event'
        $w.Root.AtWar = $false; $w.Countries.INV = @{ Tag = 'INV' }; $w.States['382'].Controller = 'INV'
        Assert-That (Test-Conditions (Prop $d 'cancel_trigger').Children $w) 'Hostile occupation does not cancel'
        $w.States['382'].Controller = 'CYA'
        Invoke-Policy (Prop $d 'remove_effect').Children $w
        Assert-That (Test-Conditions (Prop $e 'trigger').Children $w) 'Finished commission has no event'
        Assert-That (-not (Test-Conditions (Prop $d 'visible').Children $w)) 'Pending choice permits another commission'
        $w.Root.AtWar = $true
        $options = Eligible-Options $e $w
        Assert-That (($options.Count -eq 1) -and (Value $options[0] 'name') -eq "hsm_cyanolisia.$number.defer") 'Changed conditions still grant rewards'
        Invoke-Policy $options[0].Children $w
        $w.Root.AtWar = $false
        Assert-That (Test-Conditions (Prop $d 'visible').Children $w) 'Deferred commission cannot retry'
        Invoke-Policy (Prop $d 'remove_effect').Children $w
        $options = Eligible-Options $e $w
        Invoke-Policy $options[0].Children $w
        Assert-That (-not (Test-Conditions (Prop $d 'visible').Children $w)) 'Completed commission visible'
        Assert-That (-not (Test-Conditions (Prop $e 'trigger').Children $w)) 'Completed event repeats'
    }
}
Test-Case 'Constitution supports both living routes and succession without inventing a ruler' {
    foreach ($route in @('countess', 'dawnclaw')) {
        foreach ($dead in @($false, $true)) {
            $w = Peace-World $route
            if ($dead) { $w.Global = @('GRI_grover_vi_dead') }
            $e = $events['hsm_cyanolisia.60']
            $choices = Eligible-Options $e $w
            Assert-That ($choices.Count -eq $(if ($dead) { 2 } else { 1 })) 'Missing or inappropriate institutional choice'
            Assert-That (@($choices | Where-Object { (Value $_ 'name') -eq 'hsm_cyanolisia.60.c' }).Count -eq [int] $dead) 'Succession choice has the wrong life-state'
        }
    }
    Assert-That (($e | ConvertTo-Json -Depth 40) -notmatch 'recruit_character|promote_leader|clr_global_flag') 'Settlement resurrects or invents a ruler'
}
Test-Case 'Accession requires consent and rechecks independence, peace, alliance and faction leadership' {
    $w = Peace-World
    $w.Sender = $w.Root; $w.Sender.Exists = $true; $w.Sender.Faction = 'imperial'
    $w.Root = @{ Tag = 'ALLY'; Exists = $true; Faction = 'imperial'; Flags = @() }
    $w.Countries.ALLY = $w.Root
    Add-State $w 999 'ALLY' 'ALLY'
    $e = $events['hsm_cyanolisia.61']
    $accept = (Prop $e 'option')[0]
    Assert-That (Test-Conditions (Prop $accept 'trigger').Children $w) 'Valid allied compact rejected'
    foreach ($field in @('AtWar', 'FactionLeader', 'Overlord')) {
        $w.Root[$field] = $(if ($field -eq 'Overlord') { 'THIRD' } else { $true })
        Assert-That (-not (Test-Conditions (Prop $accept 'trigger').Children $w)) "Stale offer accepted: $field"
        $w.Root.Remove($field)
    }
    $w.Root.Faction = 'other'
    Assert-That (-not (Test-Conditions (Prop $accept 'trigger').Children $w)) 'Broken alliance ignored'
    $w.Root.Faction = 'imperial'; $w.Sender.AtWar = $true
    Assert-That (-not (Test-Conditions (Prop $accept 'trigger').Children $w)) 'Sender war ignored'
    $w.Sender.AtWar = $false
    Invoke-Policy (Prop $e 'option')[1].Children $w
    Assert-That (-not $w.Root.Overlord) 'Refusal forces subject status'
    Invoke-Policy $accept.Children $w
    Assert-That ($w.Root.Overlord -eq 'CYA') 'Accepted subject belongs to the wrong country'
    Assert-That ($w.States['999'].Owner -eq 'ALLY') 'Compact annexes territory'
}
function Descendants($nodes) {
    foreach ($n in $nodes) {
        $n
        if ($n.Children.Count) { Descendants $n.Children }
    }
}
Test-Case 'Campaign rewards no longer stack generic permanent modifiers; new variables are bound' {
    foreach ($r in $campaignRoutes) {
        foreach ($id in (@($r.Settlements.Values) + @($r.West, $r.East, $r.Final))) {
            $reward = Prop $focus["HSM_CYA_$id"] 'completion_reward'
            Assert-That (@(Descendants $reward | Where-Object Key -eq 'add_to_variable').Count -eq 0) "Unconditional modifier stack remains: $id"
        }
    }
    $modifiers = [IO.File]::ReadAllText((Join-Path $root 'mod/HoISubmod/common/dynamic_modifiers/HSM_CYA_dynamic_modifiers.txt'))
    foreach ($id in @(53..60)) {
        $json = $events["hsm_cyanolisia.$id"] | ConvertTo-Json -Depth 40
        Assert-That ($json -notmatch '"Key": "(add_ideas|add_dynamic_modifier)"') "Extra spirit added by event $id"
        foreach ($n in @(Descendants @($events["hsm_cyanolisia.$id"]) | Where-Object Key -eq 'add_to_variable')) {
            foreach ($v in @($n.Children | Where-Object Key -ne 'tooltip')) {
                Assert-That ($modifiers.Contains("= $($v.Key)")) "Unbound modifier variable: $($v.Key)"
            }
        }
    }
}

# Regressions from the Dawnclaw playtest: inspect effects as well as prerequisites.
foreach ($initial in @('CYA_minotaurian_indigenes', 'CYA_suppressed_indigenes', 'CYA_defeated_indigenes')) {
    Test-Case "Prewar logistics replaces harsh minority policy: $initial" {
        $w = New-World; $w.Root.Ideas = @($initial, 'CYA_minotaurian_outback')
        Invoke-Policy (Prop $focus.HSM_CYA_minotaurian_logistics_board 'completion_reward').Children $w
        Assert-That (($w.Root.Ideas -join ',') -eq 'HSM_CYA_strained_minotaurian_indigenes') 'Old penalties remain or new policy missing'
        $ideas = (Read-Code 'mod/HoISubmod/common/ideas/HSM_CYA_ideas.txt')[0]
        $policy = Prop (Prop $ideas 'country') 'HSM_CYA_strained_minotaurian_indigenes'
        Assert-That ([decimal] (Value (Prop $policy 'modifier') 'conscription_factor') -eq -0.20) 'Prewar recruitment penalty is not -20%'
        Assert-That ((Prop $focus.HSM_CYA_operation_against_asterion 'prerequisite').Children.Value -contains 'HSM_CYA_minotaurian_logistics_board') 'Mitigation is not before the war goal'
        Assert-That (-not $w.Completed -and -not $w.Root.AtWar) 'Fixture accidentally required a conquered south'
    }
}
Test-Case 'Prewar minority settlement is idempotent and never worsens a better policy' {
    foreach ($idea in @('', 'CYA_radicalised_indigenes', 'CYA_recognised_minotaurian_rights', 'CYA_true_equality', 'CYA_seperate_but_equal', 'HSM_CYA_registered_minotaurian_communities', 'HSM_CYA_strained_minotaurian_indigenes')) {
        $w = New-World; $w.Root.Ideas = @($idea | Where-Object { $_ })
        $before = $w.Root.Ideas -join ','
        1..2 | ForEach-Object { Invoke-Policy $effects.HSM_CYA_prewar_minotaur_settlement.Children $w }
        Assert-That (($w.Root.Ideas -join ',') -eq $before) "Policy worsened or duplicated: $idea"
    }
}
Test-Case 'Asterion minority follow-up does not require Sicameon and replaces rather than stacks ideas' {
    $w = New-World; Add-State $w 386 'MIT' 'MIT'
    $w.Countries.MIT = @{ Tag = 'MIT'; Exists = $true; Overlord = 'CYA' }
    $w.Completed = @('HSM_CYA_military_governorate_asterion')
    Assert-That (Test-Available 'HSM_CYA_asterion_hostage_bureau' $w) 'Asterion follow-up still needs Sicameon'
    $w.Completed += 'HSM_CYA_asterion_hostage_bureau'
    Assert-That (Test-Available 'HSM_CYA_minotaurian_security_registry' $w) 'Registry still needs Sicameon'
    $w.Root.Ideas = @('HSM_CYA_strained_minotaurian_indigenes')
    Invoke-Policy (Prop $focus.HSM_CYA_minotaurian_security_registry 'completion_reward').Children $w
    Assert-That (($w.Root.Ideas -join ',') -eq 'HSM_CYA_registered_minotaurian_communities') 'Postwar policy stacks or removes the wrong idea'
}
Test-Case 'Asterion protectorate preserves existing autonomy and is not repeated by Sicameon' {
    $w = New-World; $w.Countries.MIT = @{ Tag = 'MIT'; Exists = $true; Overlord = 'CYA'; Autonomy = 'autonomy_dominion' }
    Invoke-Policy $effects.HSM_CYA_establish_asterion_protectorate.Children $w
    Assert-That ($w.Countries.MIT.Autonomy -eq 'autonomy_dominion') 'Existing subject autonomy changed'
    Assert-That (@(Descendants $effects.HSM_CYA_establish_asterion_protectorate.Children | Where-Object Key -eq 'set_autonomy').Count -eq 0) 'Protectorate reimposes autonomy'
    Assert-That ((Prop (Prop $focus.HSM_CYA_dawnclaw_integrate_south 'completion_reward') 'HSM_CYA_establish_asterion_protectorate').Count -eq 0) 'Sicameon still establishes Asterion'
    Assert-That ((Prop (Prop $focus.HSM_CYA_military_governorate_asterion 'completion_reward') 'HSM_CYA_establish_asterion_protectorate').Count -eq 1) 'First settlement no longer releases annexed Asterion'
}
Test-Case 'Evi ends minority penalties regardless of the registry order, preserving better policies' {
    $cleanup = @(Prop (Prop $focus.HSM_CYA_evi_governorate_codes 'completion_reward') 'if' | Where-Object { (Prop $_ 'remove_ideas').Count })
    Assert-That ($cleanup.Count -eq 6) 'Evi does not cover every negative minority policy'
    foreach ($initial in @('', 'CYA_minotaurian_indigenes', 'CYA_suppressed_indigenes', 'CYA_defeated_indigenes', 'CYA_radicalised_indigenes', 'HSM_CYA_strained_minotaurian_indigenes', 'HSM_CYA_registered_minotaurian_communities')) {
        foreach ($registryFirst in @($true, $false)) {
            $w = New-World; $w.Root.Ideas = @($initial | Where-Object { $_ })
            $registry = (Prop $focus.HSM_CYA_minotaurian_security_registry 'completion_reward').Children
            if ($registryFirst) { Invoke-Policy $registry $w }
            Invoke-Policy $cleanup $w
            $w.Completed += 'HSM_CYA_evi_governorate_codes'
            if (-not $registryFirst) { Invoke-Policy $registry $w }
            Assert-That ($w.Root.Ideas.Count -eq 0) "Minority penalty survives Evi: $initial, registry first=$registryFirst"
        }
    }
    foreach ($policy in @('CYA_recognised_minotaurian_rights', 'CYA_true_equality', 'CYA_seperate_but_equal')) {
        $w = New-World; $w.Root.Ideas = @($policy)
        Invoke-Policy $cleanup $w
        Assert-That (($w.Root.Ideas -join ',') -eq $policy) "Evi erases a better minority settlement: $policy"
    }
}
Test-Case 'Late minority reforms cannot restore penalties after Evi consolidation' {
    foreach ($initial in @('CYA_minotaurian_indigenes', 'CYA_suppressed_indigenes', 'CYA_defeated_indigenes')) {
        $w = New-World; $w.Completed = @('HSM_CYA_evi_governorate_codes')
        $w.Root.Ideas = @($initial)
        Invoke-Policy $effects.HSM_CYA_prewar_minotaur_settlement.Children $w
        Assert-That ($w.Root.Ideas.Count -eq 0) 'Logistics reintroduces the prewar penalty'
        $w.Root.Ideas = @($initial)
        Invoke-Policy (Prop $focus.HSM_CYA_minotaurian_security_registry 'completion_reward').Children $w
        Assert-That ($w.Root.Ideas.Count -eq 0) 'Registry reintroduces the postwar penalty'
        Assert-That ($w.Root.Variables.HSM_CYA_compliance_growth -eq 0.02) 'Late registry lost its administrative reward'
    }
}
Test-Case 'Playtest tooltips attribute every variable to its actual national program' {
    $binding = @{}
    foreach ($m in (Read-Code 'mod/HoISubmod/common/dynamic_modifiers/HSM_CYA_dynamic_modifiers.txt')) {
        foreach ($v in $m.Children | Where-Object Value -like 'HSM_CYA_*') { $binding[$v.Value] = "$($m.Key)_dummy_idea" }
    }
    foreach ($id in @('the_revealed_exile', 'security_districts', 'dawnclaw_war_room', 'minotaurian_logistics_board', 'minotaurian_security_registry', 'evi_governorate_codes', 'continental_ordnance')) {
        $header = ''; $hasDelta = $false
        foreach ($n in (Prop $focus["HSM_CYA_$id"] 'completion_reward').Children) {
            if ($n.Key -eq 'custom_effect_tooltip' -and (Value $n 'localization_key') -eq 'modify_idea_tt') {
                Assert-That (-not $header -or $hasDelta) "Empty modifier header: $id"
                $header = Value $n 'IDEA'; $hasDelta = $false
            } elseif ($n.Key -eq 'add_to_variable') {
                $v = @($n.Children | Where-Object Key -ne 'tooltip')[0].Key
                Assert-That ($binding[$v] -eq $header) "Wrong program heading for $id / $v"
                $hasDelta = $true
            }
        }
        Assert-That (-not $header -or $hasDelta) "Trailing empty modifier header: $id"
    }
}
Test-Case 'Inactive minority and outback removals are guarded individually' {
    function Assert-GuardedRemoval($nodes, $guards = @()) {
        foreach ($n in $nodes) {
            if ($n.Key -eq 'remove_ideas') { Assert-That ($n.Value -in $guards) "Unguarded removal: $($n.Value)" }
            if ($n.Key -eq 'if') {
                $direct = @((Prop $n 'limit').Children | Where-Object Key -eq 'has_idea' | ForEach-Object Value)
                Assert-GuardedRemoval @($n.Children | Where-Object Key -ne 'limit') ($guards + $direct)
            }
        }
    }
    foreach ($id in @('the_revealed_exile', 'minotaurian_logistics_board', 'minotaurian_security_registry', 'evi_governorate_codes')) {
        Assert-GuardedRemoval (Prop $focus["HSM_CYA_$id"] 'completion_reward').Children
    }
    Assert-GuardedRemoval $effects.HSM_CYA_prewar_minotaur_settlement.Children
}
Test-Case 'Dawnclaw receives a leader trait without an arbitrary political-power penalty' {
    $role = Prop (Prop (Prop $focus.HSM_CYA_the_revealed_exile 'completion_reward') 'add_country_leader_role') 'country_leader'
    Assert-That ((Prop $role 'traits').Children.Key -contains 'HSM_CYA_military_state_builder') 'Leader trait missing'
    $trait = Prop (Read-Code 'mod/HoISubmod/common/country_leader/HSM_CYA_traits.txt')[0] 'HSM_CYA_military_state_builder'
    Assert-That ($trait.Count -eq 1 -and (Prop $trait 'political_power_factor').Count -eq 0) 'Leader trait absent or PP penalty added'
}
Test-Case 'Continental ordnance uses current equipment and preserves factories and a lasting production benefit' {
    $r = Prop $focus.HSM_CYA_continental_ordnance 'completion_reward'
    $equipment = @(Prop $r 'add_equipment_to_stockpile')
    Assert-That (@($equipment | Where-Object { (Value $_ 'type') -eq 'infantry_equipment_0' }).Count -eq 0) 'Obsolete fixed rifle model remains'
    Assert-That (@($equipment | Where-Object { (Value $_ 'type') -eq 'infantry_equipment' -and (Value $_ 'amount') -eq '2000' }).Count -eq 1) 'Current rifle delivery missing'
    Assert-That ((Prop $r 'add_to_variable').Children.Key -contains 'HSM_CYA_production_factory_max_efficiency_factor') 'Production reward missing'
    Assert-That (@(Descendants $r.Children | Where-Object { $_.Key -eq 'add_building_construction' -and (Value $_ 'type') -eq 'arms_factory' -and (Value $_ 'level') -eq '2' }).Count -eq 1) 'Factory reward lost'
}
Test-Case 'All eight aviation focuses are early, shared, localized and have nonempty rewards' {
    $air = @('independent_air_service', 'flight_instructors', 'aircraft_workshops', 'interceptor_contracts', 'battlefield_aircraft', 'air_warning_network', 'air_ground_liaison', 'unified_air_command')
    $w = New-World
    foreach ($name in $air) {
        $id = "HSM_CYA_$name"; $f = $focus[$id]
        Assert-That ($f -and $id -in $membership.cyan_original) "Unlinked aviation focus: $id"
        Assert-That (Visible $id $w) "Aviation hidden before Dawnclaw: $id"
        Assert-That ((Prop $f 'available').Count -eq 0 -and (Value $f 'cost') -in @('4', '5')) "Late or overlong aviation focus: $id"
        Assert-That ((Prop $f 'completion_reward').Children.Count -gt 0) "Empty aviation reward: $id"
        foreach ($lang in @('english', 'russian')) {
            $loc = [IO.File]::ReadAllText((Join-Path $root "mod/HoISubmod/localisation/$lang/hsm_cyanolisia_l_$lang.yml"))
            Assert-That ($loc -match "(?m)^ $($id):0 " -and $loc -match "(?m)^ $($id)_desc:0 ") "Missing $lang aviation text: $id"
        }
    }
    foreach ($name in @('aircraft_workshops', 'interceptor_contracts', 'battlefield_aircraft')) {
        $reward = (Prop $focus["HSM_CYA_$name"] 'completion_reward').Children
        Assert-That (@($reward | Where-Object Key -eq 'else').Count -eq 1) "No non-BBA research fallback: $name"
    }
}
Test-Case 'Aviation research categories, doctrine helpers and shine sprites exist' {
    $categories = Get-ClausewitzTokens ([IO.File]::ReadAllText((Join-Path $root 'EaW/common/technology_tags/00_technology.txt')))
    $doctrines = Read-Code 'EaW/common/scripted_effects/EAW_doctrine_mastery_effect.txt'
    $shine = [IO.File]::ReadAllText((Join-Path $root 'mod/HoISubmod/interface/focus/shine/HSM_CYA_focus_shine.gfx'))
    foreach ($name in @('independent_air_service', 'flight_instructors', 'aircraft_workshops', 'interceptor_contracts', 'battlefield_aircraft', 'air_warning_network', 'air_ground_liaison', 'unified_air_command')) {
        $f = $focus["HSM_CYA_$name"]
        foreach ($bonus in @(Descendants (Prop $f 'completion_reward').Children | Where-Object Key -eq 'add_tech_bonus')) {
            foreach ($category in (Prop $bonus 'category').Value) { Assert-That ($category -in $categories) "Unknown aviation category: $category" }
        }
        foreach ($effect in @(Descendants (Prop $f 'completion_reward').Children | Where-Object Key -like 'air_*_mastery_doctrine_*')) {
            Assert-That ($effect.Key -in $doctrines.Key) "Missing EaW doctrine effect: $($effect.Key)"
        }
        $sprite = Value $f 'icon'
        Assert-That ($shine -match "\bname\s*=\s*$($sprite)_shine\b") "Missing shine sprite: $sprite"
    }
}
foreach ($pair in @(@('otto_wagenfels', 'frontier_supply_corps'), @('marta_eisenfeder', 'arsenal_network'), @('klara_morgenflug', 'flight_instructors'))) {
    Test-Case "New political advisor unlocks through a common focus: $($pair[0])" {
        $id = "HSM_CYA_$($pair[0])"; $unlock = "HSM_CYA_$($pair[1])"
        $character = Prop (Read-Code 'mod/HoISubmod/common/characters/HSM_CYA_characters.txt')[0] $id
        $advisor = Prop $character 'advisor'
        Assert-That ((Value $advisor 'slot') -eq 'political_advisor' -and (Value $advisor 'cost') -eq '125') 'Wrong advisor slot/cost'
        Assert-That ((Value (Prop $advisor 'available') 'has_completed_focus') -eq $unlock) 'Wrong unlock requirement'
        $traitId = (Prop $advisor 'traits').Children[0].Key
        $trait = Prop (Read-Code 'mod/HoISubmod/common/country_leader/HSM_CYA_traits.txt')[0] $traitId
        Assert-That ($trait.Count -eq 1) "Unknown advisor trait: $traitId"
        foreach ($lang in @('english', 'russian')) {
            $loc = [IO.File]::ReadAllText((Join-Path $root "mod/HoISubmod/localisation/$lang/hsm_cyanolisia_l_$lang.yml"))
            foreach ($key in @($id, "$($id)_desc", $traitId)) { Assert-That ($loc -match "(?m)^ $($key):0 ") "Missing $lang advisor text: $key" }
        }
        $recruit = @(Prop (Prop $focus[$unlock] 'completion_reward') 'if' | Where-Object { (Value $_ 'recruit_character') -eq $id })
        Assert-That ($recruit.Count -eq 1) 'Missing recruitment hook'
        $w = New-World
        1..2 | ForEach-Object { Invoke-Policy $recruit $w }
        Assert-That (($w.Root.Characters -join ',') -eq $id) 'Recruitment absent or repeated'
    }
}

function Exile-World([string] $regent = 'GRI_archon_eros_vii') {
    $w = New-World
    $w.Date = [datetime]::new(1015, 1, 1)
    $w.Root.Exists = $true
    $w.Root.Flags = @('HSM_CYA_path_imperial_administration')
    $w.Root.Characters = @('CYA_countess_taillow_sumpfkiel')
    $w.Root.Leader = 'CYA_countess_taillow_sumpfkiel'
    $w.Countries.GRI = @{ Tag = 'GRI'; Exists = $false; Leader = $regent; Characters = @($regent, 'GRI_emperor_grover_vi'); Ideas = @('GRI_grover_vi'); Flags = @() }
    $w.Countries.INV = @{ Tag = 'INV'; Exists = $true; Flags = @('holds_griffon_capital'); Characters = @(); Government = 'neutrality' }
    Add-State $w 382 'INV' 'INV'
    return $w
}
foreach ($regent in @('GRI_archon_eros_vii', 'STW_gabriela_eagleclaw')) {
    Test-Case "Exile transfers the actual living household once, leaving the Countess in office: $regent" {
        $w = Exile-World $regent
        Assert-That (Test-Conditions $triggers.HSM_CYA_displaced_court_available.Children $w) 'Valid exile blocked'
        Invoke-Policy $effects.HSM_CYA_receive_exiled_court.Children $w
        Assert-That ($regent -in $w.Root.Characters -and 'GRI_emperor_grover_vi' -in $w.Root.Characters) 'Household not transferred'
        Assert-That ($w.Countries.GRI.Characters.Count -eq 0) 'Source retains duplicate characters'
        Assert-That ('GRI_grover_vi' -notin $w.Countries.GRI.Ideas -and 'GRI_grover_vi' -in $w.Root.Ideas) 'Child spirit in wrong country'
        Assert-That ($w.Root.Leader -eq 'CYA_countess_taillow_sumpfkiel') 'Regent displaced the host ruler'
        Invoke-Policy $effects.HSM_CYA_receive_exiled_court.Children $w
        Assert-That ($w.Root.add_political_power -eq -50 -and $w.Root.Characters.Count -eq 3) 'Repeated arrival charged or duplicated'
        Assert-That ([bool] $w.LayoutDirty) 'Arrival did not refresh the tree'
    }
}
$exileDenials = @{
    march = { param($w) $w.Root.Flags = @('HSM_CYA_path_frontier_march') }
    subject = { param($w) $w.Root.Overlord = 'INV' }
    capitulated_host = { param($w) $w.Root.Capitulated = $true }
    adult = { param($w) $w.Date = [datetime]::new(1021, 5, 21) }
    dead_child = { param($w) $w.Global += 'GRI_grover_vi_dead' }
    dead_archon = { param($w) $w.Global += 'GRI_eros_dead' }
    retired_regent = { param($w) $w.Countries.GRI.Characters = @('GRI_emperor_grover_vi') }
    unrelated_ruler = { param($w) $w.Countries.GRI.Leader = 'GRI_ferdinand_dawnclaw' }
    empire_still_fighting = { param($w) $w.Countries.GRI.Exists = $true }
    dawnclaw_present = { param($w) $w.Root.Characters += 'HSM_CYA_ferdinand_dawnclaw' }
    hostile_host = { param($w) $w.Root.Wars += 'GRI' }
    already_refused = { param($w) $w.Root.Flags += 'HSM_CYA_exile_court_resolved' }
    previous_adult_reign = { param($w) $w.Root.Flags += 'HSM_CYA_grover_reigned_elsewhere' }
    foreign_custody = { param($w) $w.Countries.GRI.Characters = @('GRI_archon_eros_vii'); $w.Countries.INV.Characters += 'GRI_emperor_grover_vi' }
    foreign_coronation = { param($w) $w.Countries.INV.Leader = 'GRI_emperor_grover_vi' }
    successor_not_declared = { param($w) $w.Countries.INV.Flags = @() }
    capital_contested = { param($w) $w.States['382'].Controller = 'GRI' }
    successor_already_regent = { param($w) $w.Countries.INV.Ideas = @('GRI_grover_vi') }
    pending_blackclaw_custody = { param($w) $w.Countries.INV.Tree = 'angriver_focus_blackclaw_imperial' }
    pending_leer_execution = { param($w) $w.Countries.INV.Leader = 'ANG_baron_leer_the_vicious' }
    bronzehill_custody = { param($w) $w.Countries.INV.Tag = 'BRZ' }
    pending_yale_custody = { param($w) $w.Countries.INV.Tag = 'YAL'; $w.Countries.INV.Government = 'fascism' }
    pending_yale_execution = { param($w) $w.Countries.INV.Tag = 'YAL'; $w.Countries.INV.Government = 'communism' }
    pending_yale_coalition = { param($w) $w.Countries.INV.Tag = 'YAL'; $w.Countries.INV.Flags += 'YAL_right_coalition_chosen' }
    pending_grover_ii_custody = { param($w) $w.Countries.INV.Tag = 'YAL'; $w.Countries.INV.Leader = 'YAL_emperor_grover_ii' }
    pending_greifenmarschen_custody = { param($w) $w.Countries.INV.Tag = 'PYT'; $w.Countries.INV.Government = 'fascism' }
    pending_greifenmarschen_execution = { param($w) $w.Countries.INV.Tag = 'PYT'; $w.Countries.INV.Government = 'communism' }
}
foreach ($denialName in $exileDenials.Keys | Sort-Object) {
    Test-Case "Exile guard: $denialName" {
        $w = Exile-World
        & ($exileDenials[$denialName]) $w
        Assert-That (-not (Test-Conditions $triggers.HSM_CYA_displaced_court_available.Children $w)) 'Unsafe asylum permitted'
        Invoke-Policy $effects.HSM_CYA_receive_exiled_court.Children $w
        Assert-That ('HSM_CYA_exile_court_received' -notin $w.Root.Flags) 'Arrival bypasses its own guard'
    }
}
Test-Case 'Asylum is revalidated on acceptance after a queued offer' {
    $w = Exile-World; $w.Global += 'GRI_grover_vi_dead'
    $choices = Eligible-Options $events['hsm_cyanolisia.73'] $w
    Assert-That ($choices.Count -eq 1 -and (Value $choices[0] 'name') -eq 'hsm_cyanolisia.73.b') 'Stale offer can resurrect Grover'
}
Test-Case 'Exile coronation respects age, custody and peace but not possession of the capital' {
    $w = Exile-World
    Invoke-Policy $effects.HSM_CYA_receive_exiled_court.Children $w
    $w.Completed = @('HSM_CYA_court_in_exile')
    Assert-That (-not (Test-Available 'HSM_CYA_exile_coronation' $w)) 'Minor can be crowned'
    $w.Date = [datetime]::new(1021, 5, 21)
    Assert-That (Test-Available 'HSM_CYA_exile_coronation' $w) 'Adult coronation requires reconquest'
    $w.Root.AtWar = $true
    Assert-That (-not (Test-Available 'HSM_CYA_exile_coronation' $w)) 'Coronation during war'
    $choices = Eligible-Options $events['hsm_cyanolisia.74'] $w
    Assert-That ($choices.Count -eq 1 -and (Value $choices[0] 'name') -eq 'hsm_cyanolisia.74.b') 'No defer option after conditions change'
    $w.Root.AtWar = $false
    Invoke-Policy (Eligible-Options $events['hsm_cyanolisia.74'] $w)[0].Children $w
    Assert-That ($w.Root.Leader -eq 'GRI_emperor_grover_vi' -and $w.Root.Government -eq 'neutrality') 'Grover not the actual ruler'
    Assert-That ('GRI_grover_vi' -notin $w.Root.Ideas) 'Child spirit survived coronation'
    Assert-That (-not (Test-Conditions (Prop $events['hsm_cyanolisia.74'] 'trigger').Children $w)) 'Coronation repeats'
}
Test-Case 'Blackhollow reconstruction requires ownership and control, including our subjects' {
    $w = New-World; $w.Root.Flags = @('HSM_CYA_path_frontier_march')
    $w.Countries.BAN = @{ Tag = 'BAN'; Overlord = 'CYA' }
    foreach ($s in @(490, 606, 489, 532)) { Add-State $w $s 'BAN' 'BAN' }
    $w.Completed = @('HSM_CYA_restore_frontier_county')
    Assert-That (Test-Available 'HSM_CYA_frontier_county_garrisons' $w) 'Subject county rejected'
    $w.Countries.BAN.Remove('Overlord')
    Assert-That (-not (Test-Available 'HSM_CYA_frontier_county_garrisons' $w)) 'Independent county can be administered'
    $w.Countries.BAN.Overlord = 'CYA'; $w.States['489'].Controller = 'INV'; $w.Countries.INV = @{ Tag = 'INV' }
    Assert-That (-not (Test-Available 'HSM_CYA_frontier_county_garrisons' $w)) 'Enemy occupation ignored'
    $w.Completed = @('HSM_CYA_march_market_roads', 'HSM_CYA_march_volunteer_reserves')
    Assert-That (Test-Available 'HSM_CYA_march_frontier_compact' $w) 'Peaceful March finale requires Blackhollow conquest'
}
Test-Case 'Blackhollow claims are limited to the county and exclude allies, subjects and duplicate goals' {
    $branch = Prop (Prop $effects.HSM_CYA_claim_blackhollow_state 'owner') 'if'
    $limit = (Prop $branch 'limit').Children
    $goal = Prop (Prop $branch 'ROOT') 'create_wargoal'
    Assert-That ((Value $goal 'type') -eq 'take_state_focus') 'County dispute grants total annexation'
    Assert-That (((Prop $goal 'generator').Children.Key -join ',') -eq '490,606,489,532') 'Wrong county states'
    $w = New-World; $w.Countries.INV = @{ Tag = 'INV' }
    Assert-That (Test-Conditions $limit $w $w.Countries.INV) 'Independent owner rejected'
    $w.Root.Faction = 'league'; $w.Countries.INV.Faction = 'league'
    Assert-That (-not (Test-Conditions $limit $w $w.Countries.INV)) 'War goal against ally'
    $w.Countries.INV.Remove('Faction'); $w.Countries.INV.Overlord = 'CYA'
    Assert-That (-not (Test-Conditions $limit $w $w.Countries.INV)) 'War goal against subject'
    $w.Countries.INV.Remove('Overlord'); $w.Root.Goals = @('INV')
    Assert-That (-not (Test-Conditions $limit $w $w.Countries.INV)) 'Duplicate county claim'
}
Test-Case 'Secondary civic settlement preserves better rights and removes all exceptional conscription penalties' {
    foreach ($rights in @('', 'CYA_true_equality', 'CYA_seperate_but_equal', 'CYA_recognised_minotaurian_rights')) {
        $w = New-World
        $w.Root.Ideas = @('CYA_minotaurian_indigenes', 'CYA_suppressed_indigenes', 'CYA_radicalised_indigenes',
            'CYA_defeated_indigenes', 'HSM_CYA_strained_minotaurian_indigenes', 'HSM_CYA_registered_minotaurian_communities')
        if ($rights) { $w.Root.Ideas += $rights }
        1..2 | ForEach-Object { Invoke-Policy $effects.HSM_CYA_secondary_civic_settlement.Children $w }
        $expected = if ($rights) { $rights } else { 'CYA_recognised_minotaurian_rights' }
        Assert-That (($w.Root.Ideas -join ',') -eq $expected) 'Rights replaced, penalties retained or idea duplicated'
    }
}
Test-Case 'Administrative regularisation cannot restore suppressed minorities' {
    foreach ($rights in @('CYA_true_equality', 'CYA_recognised_minotaurian_rights', 'HSM_CYA_registered_minotaurian_communities')) {
        $w = New-World; $w.Root.Ideas = @($rights, 'CYA_opened_outback')
        Invoke-Policy (Prop $focus.HSM_CYA_regularise_minotaur_administration 'completion_reward').Children $w
        Assert-That ($rights -in $w.Root.Ideas -and 'CYA_suppressed_indigenes' -notin $w.Root.Ideas) 'Earlier reform regressed'
    }
}
Test-Case 'Administrative programmes survive both death and voluntary departure' {
    $daily = (Prop @(Read-Code 'mod/HoISubmod/common/on_actions/HSM_CYA_on_actions.txt')[0] 'on_daily_CYA')
    $branches = Prop (Prop $daily 'effect') 'if'
    $removal = @($branches | Where-Object { (Prop $_ 'remove_dynamic_modifier').Count -gt 0 })[0]
    $install = @($branches | Where-Object { (Prop $_ 'HSM_CYA_install_national_programs').Count -gt 0 })[0]
    foreach ($state in @('HSM_CYA_dawnclaw_dead', 'HSM_CYA_dawnclaw_departed')) {
        $w = New-World; $w.Root.Flags = @('HSM_CYA_path_imperial_administration', $state, 'HSM_CYA_dynamic_modifiers_installed')
        Assert-That (-not (Test-Conditions (Prop $removal 'limit').Children $w)) 'Daily cleanup removes administrative reforms'
        $w.Root.Flags = @('HSM_CYA_path_imperial_administration', $state)
        Assert-That (Test-Conditions (Prop $install 'limit').Children $w) 'Missing administrative programmes cannot be installed'
    }
}
Test-Case 'March policy and county choices change shared programmes, not permanent micro-ideas' {
    foreach ($id in @('reorganise_border_forces', 'frontier_drill_standards', 'modernise_internal_intelligence',
        'frontier_signals_network', 'local_supply_depots', 'fortify_against_minotauria', 'watch_sicameon',
        'blackrock_wasteland_surveys', 'frontier_county_garrisons', 'reopen_military_workshops', 'cabinet_procurement_board',
        'consolidate_proxy_cabinet', 'rationalise_proxy_quotas')) {
        $reward = Prop $focus["HSM_CYA_$id"] 'completion_reward'
        Assert-That (@(Descendants $reward | Where-Object { $_.Key -in @('add_ideas', 'swap_ideas') }).Count -eq 0) "Micro-idea persists: $id"
        Assert-That (@(Prop $reward 'add_to_variable').Count -gt 0) "No programme effect: $id"
    }
    foreach ($number in @(71, 72)) {
        foreach ($choice in @(0, 1)) {
            $w = New-World; $w.Root.Flags = @('HSM_CYA_path_frontier_march')
            foreach ($s in @(490, 606, 489, 532)) { Add-State $w $s }
            $e = $events["hsm_cyanolisia.$number"]
            Invoke-Policy (Prop $e 'option')[$choice].Children $w
            Assert-That ($w.Root.Variables.Count -gt 0) 'Choice has no programme consequences'
            Assert-That (-not (Test-Conditions (Prop $e 'trigger').Children $w)) 'Settlement awards twice'
        }
    }
}

function Story-World([int] $number) {
    $w = New-World
    $w.Root.Characters = @('GRI_emperor_grover_vi')
    if ($number -in @(3, 4, 9, 10, 11)) {
        $w.Root.Flags = @('HSM_CYA_dawnclaw_dominant')
        $w.Root.Leader = 'HSM_CYA_ferdinand_dawnclaw'
    } else {
        $w.Root.Flags = @('HSM_CYA_countess_dominant')
        $w.Root.Leader = 'CYA_countess_taillow_sumpfkiel'
    }
    switch ($number) {
        1 { $w.Completed = @('HSM_CYA_countess_integrate_evi_valley') }
        2 { $w.Root.Flags += 'HSM_CYA_story_1_resolved' }
        3 { $w.Completed = @('HSM_CYA_evi_governorate_codes') }
        4 { $w.Root.Flags += 'HSM_CYA_story_3_resolved' }
        { $_ -in @(5, 6) } {
            $w.Date = [datetime]::new(1020, 1, 1)
            if ($number -eq 6) { $w.Root.Flags += 'HSM_CYA_story_5_resolved' }
        }
        { $_ -in @(7, 8) } {
            $w.Root.Leader = 'GRI_emperor_grover_vi'
            $w.Root.Flags += 'HSM_CYA_1021_crown_in_trust'
            if ($number -eq 8) { $w.Root.Flags += @('HSM_CYA_story_7_resolved', 'HSM_CYA_peace_constitution_done') }
        }
        { $_ -in @(9, 10) } {
            $w.Root.Flags += @('HSM_CYA_1021_caged_coronation', 'HSM_CYA_puppet_petitions_resolved')
            if ($number -eq 10) { $w.Root.Flags += @('HSM_CYA_story_9_resolved', 'HSM_CYA_peace_constitution_done') }
        }
        { $_ -in @(11, 12) } {
            $w.Global += 'GRI_grover_vi_dead'
            $w.Root.Characters = @()
            $w.Root.Flags += 'HSM_CYA_peace_constitution_done'
        }
    }
    return $w
}
foreach ($number in 1..12) {
    Test-Case "Character scene $number opens once, records its outcome and spaces further scenes" {
        $w = Story-World $number
        $e = $events["hsm_cya_story.$number"]
        Assert-That (Test-Conditions (Prop $e 'trigger').Children $w) 'Valid scene blocked'
        Invoke-Policy (Prop $e 'immediate').Children $w
        Assert-That (-not (Test-Conditions (Prop $e 'trigger').Children $w)) 'Scene can repeat'
        Assert-That ('HSM_CYA_story_cooldown' -in $w.Root.Flags) 'Missing global scene spacing'
        $options = @(Eligible-Options $e $w)
        Assert-That ($options.Count -eq $(if ($number -in @(1, 3, 5, 7)) { 2 } else { 1 })) 'Wrong story options'
        Invoke-Policy $options[0].Children $w
        Assert-That ("HSM_CYA_story_$($number)_resolved" -in $w.Root.Flags) 'Outcome lost'
        Assert-That ($w.Root.Ideas.Count -eq 0) 'Story adds a micro-spirit'
    }
    Test-Case "Character scene $number offers only a harmless fallback after presence or authority changes" {
        $w = Story-World $number; $e = $events["hsm_cya_story.$number"]
        Invoke-Policy (Prop $e 'immediate').Children $w
        $w.Root.Leader = 'unrelated_leader'; $w.Root.Characters = @()
        $options = @(Eligible-Options $e $w)
        Assert-That ($options.Count -eq 1 -and (Value $options[0] 'name') -eq 'HSM_CYA_story_circumstances_changed') 'Stale character choice still active'
        Invoke-Policy $options[0].Children $w
        Assert-That ("HSM_CYA_story_$($number)_resolved" -notin $w.Root.Flags -and -not $w.Root.Variables) 'Fallback awards effects'
    }
}
Test-Case 'A route flag cannot make a retired Countess or departed Dawnclaw speak as ruler' {
    $w = Story-World 1; $w.Root.Leader = 'GRI_emperor_grover_vi'
    Assert-That (-not (Test-Conditions $triggers.HSM_CYA_story_1_ready.Children $w)) 'Countess remains ruler in scene'
    foreach ($flag in @('HSM_CYA_dawnclaw_dead', 'HSM_CYA_dawnclaw_departed')) {
        $w = Story-World 3; $w.Root.Flags += $flag
        Assert-That (-not (Test-Conditions $triggers.HSM_CYA_story_3_ready.Children $w)) 'Absent Dawnclaw appears'
    }
}
Test-Case 'New budget promises cannot be made after the corresponding post-war settlement' {
    foreach ($spec in @(@(1, 'HSM_CYA_peace_reconstruction_done'), @(3, 'HSM_CYA_peace_demobilization_done'))) {
        $w = Story-World $spec[0]; $w.Root.Flags += $spec[1]
        Assert-That (-not (Test-Conditions $triggers["HSM_CYA_story_$($spec[0])_ready"].Children $w)) 'Retroactive promise'
    }
}
Test-Case 'Child scenes reject death, foreign custody, a previous reign and the majority birthday' {
    foreach ($number in @(5, 6)) {
        foreach ($change in @('dead', 'abroad', 'reigned', 'adult', 'ruler')) {
            $w = Story-World $number
            switch ($change) {
                dead { $w.Global += 'GRI_grover_vi_dead' }
                abroad { $w.Root.Characters = @() }
                reigned { $w.Root.Flags += 'HSM_CYA_grover_reigned_elsewhere' }
                adult { $w.Date = [datetime]::new(1021, 5, 21) }
                ruler { $w.Root.Leader = 'GRI_emperor_grover_vi' }
            }
            Assert-That (-not (Test-Conditions $triggers["HSM_CYA_story_$($number)_ready"].Children $w)) "Unsafe childhood: $number / $change"
        }
    }
}
Test-Case 'Every real coronation variant opens the adult ruler story, including the court in exile' {
    foreach ($flag in @('HSM_CYA_1021_crown_in_trust', 'HSM_CYA_1021_grover_restored', 'HSM_CYA_exile_coronation_done')) {
        $w = Story-World 7; $w.Root.Flags = @($flag)
        Assert-That (Test-Conditions $triggers.HSM_CYA_story_7_ready.Children $w) "Coronation excluded: $flag"
        $w.Root.Leader = 'CYA_countess_taillow_sumpfkiel'
        Assert-That (-not (Test-Conditions $triggers.HSM_CYA_story_7_ready.Children $w)) 'Title mistaken for actual authority'
    }
    $w = Story-World 7; $w.Global += 'GRI_grover_vi_dead'
    Assert-That (-not (Test-Conditions $triggers.HSM_CYA_story_7_ready.Children $w)) 'Dead ruler appears'
}
Test-Case 'Puppet and independent Grover scenes are mutually exclusive and preserve authority' {
    $w = Story-World 9
    Assert-That (-not (Test-Conditions $triggers.HSM_CYA_story_7_ready.Children $w)) 'Puppet gets executive power'
    Invoke-Policy (Prop $events['hsm_cya_story.9'] 'option')[0].Children $w
    Assert-That ($w.Root.Leader -eq 'HSM_CYA_ferdinand_dawnclaw') 'Puppet scene silently replaces ruler'
    $w.Root.Leader = 'GRI_emperor_grover_vi'
    Assert-That (-not (Test-Conditions $triggers.HSM_CYA_story_9_ready.Children $w)) 'Independent ruler still caged'
}
foreach ($spec in @(@(2, 1, 45), @(4, 3, 45), @(6, 5, 45), @(8, 7, 60), @(10, 9, 45))) {
    Test-Case "Follow-up $($spec[0]) waits for a resolved choice and the declared interval" {
        $w = Story-World $spec[0]
        $ready = $triggers["HSM_CYA_story_$($spec[0])_ready"].Children
        $w.Root.Flags = @($w.Root.Flags | Where-Object { $_ -ne "HSM_CYA_story_$($spec[1])_resolved" })
        Assert-That (-not (Test-Conditions $ready $w)) 'Follow-up without a choice'
        $w.Root.Flags += @("HSM_CYA_story_$($spec[1])_resolved", "HSM_CYA_story_$($spec[1])_wait")
        Assert-That (-not (Test-Conditions $ready $w)) 'Follow-up during waiting period'
        foreach ($o in (Prop $events["hsm_cya_story.$($spec[1])"] 'option' | Where-Object { (Value $_ 'name') -ne 'HSM_CYA_story_circumstances_changed' })) {
            $wait = @(Prop $o 'set_country_flag' | Where-Object { (Value $_ 'flag') -eq "HSM_CYA_story_$($spec[1])_wait" })
            Assert-That ($wait.Count -eq 1 -and (Value $wait[0] 'days') -eq "$($spec[2])") 'Wrong declared delay'
        }
    }
}
Test-Case 'Final scenes wait for peace and settlement; exile ruler has a reachable alternative' {
    foreach ($number in @(8, 10, 11, 12)) {
        $w = Story-World $number; $w.Root.AtWar = $true
        Assert-That (-not (Test-Conditions $triggers["HSM_CYA_story_$($number)_ready"].Children $w)) 'Wartime epilogue'
        $w.Root.AtWar = $false
        $w.Root.Flags = @($w.Root.Flags | Where-Object { $_ -ne 'HSM_CYA_peace_constitution_done' })
        Assert-That (-not (Test-Conditions $triggers["HSM_CYA_story_$($number)_ready"].Children $w)) 'Epilogue before settlement'
        if ($number -eq 8) {
            $w.Root.Flags += 'HSM_CYA_path_imperial_administration'
            Assert-That (Test-Conditions $triggers.HSM_CYA_story_8_ready.Children $w) 'Exile ruler trapped behind unavailable settlement'
        }
    }
    foreach ($number in @(11, 12)) {
        $w = Story-World $number; $w.Global = @()
        Assert-That (-not (Test-Conditions $triggers["HSM_CYA_story_$($number)_ready"].Children $w)) 'Mourning a living Grover'
    }
}
Test-Case 'Weekly dispatcher prioritizes one scene and respects cooldown, occupation and country' {
    $w = Story-World 5; $w.Completed += 'HSM_CYA_countess_integrate_evi_valley'
    Invoke-Policy $effects.HSM_CYA_story_tick.Children $w
    Assert-That ((@($w.Root.Events) -join ',') -eq 'hsm_cya_story.5') 'Several simultaneous scenes or wrong priority'
    Invoke-Policy (Prop $events['hsm_cya_story.5'] 'immediate').Children $w
    Invoke-Policy $effects.HSM_CYA_story_tick.Children $w
    Assert-That (@($w.Root.Events).Count -eq 1) 'Cooldown ignored'
    foreach ($change in @('capitulated', 'subject', 'foreign')) {
        $w = Story-World 1
        switch ($change) {
            capitulated { $w.Root.Capitulated = $true }
            subject { $w.Root.Overlord = 'GRI' }
            foreign { $w.Root.OriginalTag = 'GRI' }
        }
        Invoke-Policy $effects.HSM_CYA_story_tick.Children $w
        Assert-That (-not $w.Root.Events) "Wrong dispatch: $change"
    }
    $actions = @(Read-Code 'mod/HoISubmod/common/on_actions/HSM_CYA_on_actions.txt')[0]
    $weekly = Prop (Prop $actions 'on_weekly_CYA') 'effect'
    Assert-That ((Value $weekly 'HSM_CYA_story_tick') -eq 'yes') 'Story dispatcher not wired to weekly action'
}
foreach ($spec in @(
    @{ Number = 1; Promise = 'provincial'; Variable = 'HSM_CYA_compliance_growth'; Delta = [decimal]0.03; Event = 59; Option = 1; KeptOption = 0; Settled = 'provinces' },
    @{ Number = 3; Promise = 'officer'; Variable = 'HSM_CYA_training_time_factor'; Delta = [decimal]-0.05; Event = 58; Option = 0; KeptOption = 1; Settled = 'officers' }
)) {
    Test-Case "The $($spec.Promise) guarantee has a reversible benefit and a one-time conflicting settlement" {
        $w = Peace-World; $w.Root.Variables = @{ $spec.Variable = [decimal]0.12 }
        Invoke-Policy (Prop $events["hsm_cya_story.$($spec.Number)"] 'option')[0].Children $w
        Assert-That ($w.Root.Variables[$spec.Variable] -eq (0.12 + $spec.Delta)) 'Promise benefit missing'
        $policy = (Prop $events["hsm_cyanolisia.$($spec.Event)"] 'option')[$spec.Option]
        Invoke-Policy $policy.Children $w
        Assert-That ($w.Root.add_political_power -eq -75) 'Settlement fee missing'
        Assert-That ($w.Root.Variables[$spec.Variable] -eq 0.12) 'Other programme bonuses damaged'
        Assert-That ("HSM_CYA_story_$($spec.Settled)_compensated" -in $w.Root.Flags) 'Settlement not recorded'
        Assert-That ("HSM_CYA_story_$($spec.Promise)_guarantee" -in $w.Root.Flags) 'Promise history erased'
        Invoke-Policy $effects["HSM_CYA_story_release_$($spec.Promise)_guarantee"].Children $w
        Assert-That ($w.Root.Variables[$spec.Variable] -eq 0.12) 'Benefit removed twice'
        Assert-That (-not (Test-Conditions $triggers["HSM_CYA_story_$($spec.Promise)_compensation_due"].Children $w)) 'Fee still due'
    }
    Test-Case "Honouring the $($spec.Promise) guarantee preserves its benefit without a settlement fee" {
        $w = Peace-World
        Invoke-Policy (Prop $events["hsm_cya_story.$($spec.Number)"] 'option')[0].Children $w
        Invoke-Policy (Prop $events["hsm_cyanolisia.$($spec.Event)"] 'option')[$spec.KeptOption].Children $w
        Assert-That (-not $w.Root.add_political_power) 'Honoured commitment charged'
        Assert-That ("HSM_CYA_story_$($spec.Promise)_support_active" -in $w.Root.Flags) 'Honoured benefit lost'
    }
    Test-Case "No extra settlement fee without the $($spec.Promise) guarantee" {
        $w = Peace-World
        Invoke-Policy (Prop $events["hsm_cyanolisia.$($spec.Event)"] 'option')[$spec.Option].Children $w
        Assert-That (-not $w.Root.add_political_power) 'Ordinary post-war policy penalized'
        Assert-That (-not $w.Root.Variables -or -not $w.Root.Variables[$spec.Variable]) 'Nonexistent bonus subtracted'
    }
}
Test-Case 'Grover can retain inherited commitments without altering them' {
    $w = Story-World 7
    Invoke-Policy (Prop $events['hsm_cya_story.1'] 'option')[0].Children $w
    Invoke-Policy (Prop $events['hsm_cya_story.7'] 'option')[0].Children $w
    Assert-That (Test-Conditions $triggers.HSM_CYA_story_provincial_compensation_due.Children $w) 'Guarantee silently cancelled'
    Assert-That ($w.Root.Variables.HSM_CYA_compliance_growth -eq 0.03 -and -not $w.Root.add_political_power) 'Confirmation changes benefits or charges a fee'
}
Test-Case 'Public renegotiation charges once, removes only its own benefits, and prevents later settlement fees' {
    $w = Peace-World
    foreach ($number in @(1, 3)) { Invoke-Policy (Prop $events["hsm_cya_story.$number"] 'option')[0].Children $w }
    Invoke-Policy (Prop $events['hsm_cya_story.7'] 'option')[1].Children $w
    Assert-That ($w.Root.add_political_power -eq -50) 'Public negotiation charged incorrectly'
    Assert-That ($w.Root.Variables.HSM_CYA_compliance_growth -eq 0 -and $w.Root.Variables.HSM_CYA_training_time_factor -eq 0) 'Renegotiated benefits persist'
    Invoke-Policy (Prop $events['hsm_cyanolisia.58'] 'option')[0].Children $w
    Invoke-Policy (Prop $events['hsm_cyanolisia.59'] 'option')[1].Children $w
    Assert-That ($w.Root.add_political_power -eq -50) 'Double settlement charge'
    $w = Story-World 7
    Invoke-Policy (Prop $events['hsm_cya_story.7'] 'option')[1].Children $w
    Assert-That (-not $w.Root.add_political_power -and -not $w.Root.Variables) 'Negotiation invents obligations'
}

foreach ($spec in @(
    @(2, 'HSM_CYA_story_provincial_guarantee', 'HSM_CYA_story_provinces_compensated', 'discretion', 'bound', 'settled'),
    @(4, 'HSM_CYA_story_officer_guarantee', 'HSM_CYA_story_officers_compensated', 'term', 'bound', 'settled')
)) {
    Test-Case "Scene $($spec[0]) remembers a promise, a refusal and a settlement before its delayed follow-up" {
        $w = Story-World $spec[0]
        foreach ($index in 0..2) {
            if ($index -eq 1) { $w.Root.Flags += $spec[1] }
            if ($index -eq 2) { $w.Root.Flags += $spec[2] }
            $matching = @(Prop $events["hsm_cya_story.$($spec[0])"] 'desc' | Where-Object { Test-Conditions (Prop $_ 'trigger').Children $w })
            Assert-That ($matching.Count -eq 1 -and (Value $matching[0] 'text') -eq "hsm_cya_story.$($spec[0]).$($spec[3 + $index]).d") 'Narrative ignores actual settlement'
        }
    }
}
Test-Case 'Adult memories, inherited obligations and epilogue text follow actual outcomes' {
    $getters = @{}
    foreach ($getter in (Read-Code 'mod/HoISubmod/common/scripted_localisation/HSM_CYA_story.txt')) { $getters[(Value $getter 'name')] = $getter }
    foreach ($spec in @(
        @('Childhood', '', 'memory_adult'),
        @('Childhood', 'HSM_CYA_story_unedited_reports', 'memory_open'),
        @('Childhood', 'HSM_CYA_story_filtered_reports', 'memory_filtered'),
        @('Inheritance', 'HSM_CYA_story_provincial_guarantee', 'inheritance_provinces'),
        @('Inheritance', 'HSM_CYA_story_officer_guarantee', 'inheritance_officers'),
        @('Inheritance', 'HSM_CYA_story_provincial_guarantee,HSM_CYA_story_provinces_compensated', 'inheritance_unpledged'),
        @('Settlement', 'HSM_CYA_story_reviewed_mandates', 'settlement_reviewed'),
        @('Settlement', 'HSM_CYA_story_officers_compensated', 'settlement_adjusted'),
        @('Settlement', 'HSM_CYA_story_inherited_mandates', 'settlement_inherited')
    )) {
        $w = New-World; $w.Root.Flags = $spec[1].Split(',')
        $match = @(Prop $getters["GetHSMCyaStory$($spec[0])"] 'text' | Where-Object { Test-Conditions (Prop $_ 'trigger').Children $w })[0]
        Assert-That ((Value $match 'localization_key') -eq "HSM_CYA_story_$($spec[2])") "Wrong callback: $($spec -join '/')"
    }
}

Write-Output "PowerShell $($PSVersionTable.PSVersion): $passed passed; $($failures.Count) failed."
if ($failures.Count) { throw ($failures -join "`n") }
