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
foreach ($node in (Read-Code 'mod/HoISubmod/common/scripted_triggers/HSM_CYA_scripted_triggers.txt')) { $triggers[$node.Key] = $node }
$effects = @{}
foreach ($node in (Read-Code 'mod/HoISubmod/common/scripted_effects/HSM_CYA_scripted_effects.txt')) { $effects[$node.Key] = $node }
$events = @{}
foreach ($node in (Read-Code 'mod/HoISubmod/events/HSM_Cyanolisia.txt')) {
    if ($node.Key -eq 'country_event') { $events[(Value $node 'id')] = $node }
}

function New-World {
    $cya = @{ Tag = 'CYA'; Flags = @(); Ideas = @(); Characters = @(); Goals = @(); Wars = @() }
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
            'has_war' { [bool] $scope.AtWar -eq ($v -eq 'yes') }
            'has_war_with' { $world.Root.Tag -in $scope.Wars }
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
Test-Case 'All 364 focus references exist and mutually exclusive links are symmetric' {
    Assert-That ($focus.Count -eq 364) 'Unexpected focus inventory'
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
    foreach ($n in $nodes) {
        switch ($n.Key) {
            { $_ -in @('name', 'trigger', 'ai_chance', 'custom_effect_tooltip', 'log') } { continue }
            'set_country_flag' { $scope.Flags = @($scope.Flags) + $n.Value }
            'clr_country_flag' { $scope.Flags = @($scope.Flags | Where-Object { $_ -ne $n.Value }) }
            'add_to_variable' {
                if (-not $scope.Variables) { $scope.Variables = @{} }
                $v = @($n.Children | Where-Object Key -ne 'tooltip')[0]
                $scope.Variables[$v.Key] = [decimal] $scope.Variables[$v.Key] + [decimal] $v.Value
            }
            'if' {
                if (Test-Conditions (Prop $n 'limit').Children $world $scope) {
                    Invoke-Policy @($n.Children | Where-Object Key -ne 'limit') $world $scope
                }
            }
            'FROM' { Invoke-Policy $n.Children $world $world.Sender }
            'set_autonomy' {
                Assert-That ((Value $n 'target') -eq 'ROOT') 'Unexpected autonomy target'
                $world.Root.Overlord = $scope.Tag
            }
            'country_event' { $scope.Events = @($scope.Events) + (Value $n 'id') }
            'add_building_construction' { $scope.Buildings = @($scope.Buildings) + $n }
            'add_extra_state_shared_building_slots' { $scope.Slots = [int] $scope.Slots + [int] $n.Value }
            'add_tech_bonus' { $scope.Research = @($scope.Research) + $n }
            { $_ -in @('add_political_power', 'army_experience') } { $scope[$n.Key] = [decimal] $scope[$n.Key] + [decimal] $n.Value }
            default {
                if ($world.States.ContainsKey($n.Key)) { Invoke-Policy $n.Children $world $world.States[$n.Key] }
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

Write-Output "PowerShell $($PSVersionTable.PSVersion): $passed passed; $($failures.Count) failed."
if ($failures.Count) { throw ($failures -join "`n") }
