$ErrorActionPreference = 'Stop'
$root = (Get-Location).Path
. ./tools/CyanolisiaIconManifest.Common.ps1
$src = Get-Content ./tools/Test-CyanolisiaFocusFlow.ps1 -Raw
$start = $src.IndexOf('function Read-Block')
. ([scriptblock]::Create($src.Substring($start, $src.IndexOf('$focus = @{}') - $start)))
function Assert($ok, $why) { if (-not $ok) { throw $why } }
$script:passed=0
function Case($name,[scriptblock]$body) { & $body; $script:passed++; Write-Output "PASS $name" }
function Walk($nodes) { foreach($n in $nodes) { $n; Walk $n.Children } }
$p='mod/HoISubmod'
$triggers=@{};$effects=@{};$focus=@{};$events=@{}
foreach($n in (Read-Code "$p/common/scripted_triggers/HSM_VER_imperial.txt")){$triggers[$n.Key]=$n}
foreach($n in (Read-Code "$p/common/scripted_effects/HSM_VER_imperial.txt")){$effects[$n.Key]=$n}
foreach($n in (Read-Code "$p/common/national_focus/HSM_VER_imperial.txt")){$focus[(Value $n 'id')]=$n}
foreach($n in (Read-Code "$p/events/HSM_VER_imperial.txt")){if($n.Key -eq 'country_event'){$events[(Value $n 'id')]=$n}}
foreach($n in (Read-Code "$p/common/scripted_triggers/HSM_VER_diplomacy.txt")){$triggers[$n.Key]=$n}
foreach($n in (Read-Code "$p/common/scripted_triggers/HSM_VER_avian_relations.txt")){$triggers[$n.Key]=$n}
$actions=(Read-Code "$p/common/on_actions/HSM_VER_imperial.txt")[0]
$ideas=(Read-Code "$p/common/ideas/HSM_VER_imperial.txt")[0].Children[0].Children
$all=@()
foreach($f in Get-ChildItem $p -Recurse -Filter 'HSM_VER_imperial*.txt'){$all+=@(Walk (Parse-Code (Get-Content $f.FullName -Raw)))}
Case 'syntax, eight focuses, seven events, shifted absolute layout' {
 Assert ($focus.Count -eq 8 -and $events.Count -eq 7) 'wrong counts'
 Assert ((Value $focus.HSM_VER_IMP_settlement 'x') -eq 54 -and (Value $focus.HSM_VER_IMP_settlement 'y') -eq 0) 'wrong root'
 $expected=@{settlement=@(54,0);household_record=@(52,1);city_contracts=@(56,1);open_archives=@(52,2);technical_agreement=@(56,2);public_accounts=@(54,3);last_year=@(52,4);return_the_keys=@(56,4)}
 $positions=@{}
 foreach($f in $focus.Values){
  $x=[int](Value $f 'x');$y=[int](Value $f 'y')
  $position=$expected[(Value $f 'id').Replace('HSM_VER_IMP_','')]
  Assert ($x -eq $position[0] -and $y -eq $position[1]) 'incorrect six-column shift'
  Assert (-not $positions.ContainsKey("$x,$y")) 'overlap'
  $positions["$x,$y"]=$true
  Assert ((Prop $f 'relative_position_id').Count -eq 0) 'relative position'
  Assert ((Value $f 'cancel_if_invalid') -eq 'yes') 'focus not cancellable'
  foreach($q in Prop $f 'prerequisite'){Assert ($focus.ContainsKey((Value $q 'focus'))) 'broken prerequisite'}
 }
}
Case 'local references resolve; no territorial, character, global or war mutations' {
 $forbidden=@('annex_country','transfer_state','add_state_core','add_state_claim','set_cosmetic_tag','set_country_name','set_nationality','recruit_character','create_country_leader','add_country_leader_role','promote_character','retire_character','generate_character','set_portraits','create_wargoal','declare_war_on','set_global_flag','clr_global_flag','set_politics','set_autonomy','add_to_faction','set_variable','add_to_variable')
 foreach($n in $all){
  Assert ($n.Key -notin $forbidden) "forbidden $($n.Key)"
  if($n.Key -like 'HSM_VER_IMP_*' -and $n.Value -in @('yes','no')){Assert ($triggers.ContainsKey($n.Key) -or $effects.ContainsKey($n.Key)) "missing $($n.Key)"}
  if($n.Key -eq 'country_event' -and $n.Children.Count){Assert ($events.ContainsKey((Value $n 'id'))) 'missing event'}
  if($n.Key -eq 'add_timed_idea'){Assert ((Value $n 'idea') -in $ideas.Key) 'missing idea'}
 }
}
$loc=@{}
foreach($lang in @('english','russian')){
 $file=Join-Path $root "$p/localisation/$lang/HSM_VER_imperial_l_$lang.yml"
 $bytes=[IO.File]::ReadAllBytes($file)
 Assert ([Convert]::ToHexString($bytes[0..2]) -eq 'EFBBBF') "BOM $lang"
 $keys=@{}
 foreach($line in (Get-Content $file -Encoding UTF8 | Select-Object -Skip 1)){
  Assert ($line -match '^\s+([A-Za-z0-9_.]+):0 "(?:\\.|[^"\\])*"$') "bad loc $line"
  $key=$Matches[1];Assert (-not $keys.ContainsKey($key)) "duplicate $key";$keys[$key]=$true
 }
 $loc[$lang]=$keys
}
Case 'EN/RU BOM, quoting, parity and full localization coverage' {
 Assert (@(Compare-Object @($loc.english.Keys) @($loc.russian.Keys)).Count -eq 0) 'parity'
 $required=@()
 foreach($id in $focus.Keys){$required+=$id;$required+=($id+'_desc')}
 foreach($id in $ideas.Key){$required+=$id;$required+=($id+'_desc')}
 foreach($n in $all){if($n.Key -in @('tooltip','custom_effect_tooltip','title','text','name','desc') -and $n.Value -match '^(HSM_VER_IMP_|hsm_ver_imperial\.)'){$required+=$n.Value}}
 foreach($key in $required){Assert ($loc.english.ContainsKey($key)) "missing $key"}
}
$base='C:/shit/Steam/steamapps/workshop/content/394360/1826643372'
Case 'modifier keys and all art tokens validated against installed docs/assets' {
 $docs=Get-Content "$base/documentation/modifiers_documentation.md" -Raw
 foreach($idea in $ideas){foreach($m in (Prop $idea 'modifier')[0].Children){Assert ($docs -match ('(?m)^## '+[regex]::Escape($m.Key)+'\r?$')) "unknown modifier $($m.Key)"}}
 $names=@{}
 foreach($dir in @("$base/interface",'C:/shit/Steam/steamapps/common/Hearts of Iron IV/interface')){
  foreach($file in Get-ChildItem $dir -Recurse -Filter '*.gfx'){
   foreach($match in [regex]::Matches([IO.File]::ReadAllText($file.FullName),'\bname\s*=\s*"?([A-Za-z0-9_]+)')){$names[$match.Groups[1].Value]=$true}
  }
 }
 foreach($f in $focus.Values){Assert ($names.ContainsKey((Value $f 'icon'))) "icon $(Value $f 'icon')"}
 foreach($e in $events.Values){Assert ($names.ContainsKey((Value $e 'picture'))) 'event picture'}
 foreach($i in $ideas){Assert ($names.ContainsKey("GFX_idea_$(Value $i 'picture')")) 'idea picture'}
}
function Country($tag){return @{Tag=$tag;Original=$tag;Exists=$true;Subject=$false;Capitulated=$false;War=$false;Wars=@();Defensive=@();Offensive=@();Together=@();Flags=@{};Characters=@();Ideas=@{};PP=0;Stability=0;Events=@();Tech=@()}}
function World{
 $w=@{Countries=@{};States=@{'382'=@{Owner='ERI';Controller='ERI';Slots=5;Buildings=0}};Global=@();Date=[datetime]::new(1020,1,1);Root='ERI';From='GRI'}
 foreach($tag in @('ERI','EYR','AVI','GRI','CYA','FAT')){$w.Countries[$tag]=Country $tag}
 foreach($id in @('391','400','401','500','673','470')){$w.States[$id]=@{Owner='ERI';Controller='ERI'}}
 $w.Countries.ERI.Flags.HSM_VER_treaty_signed=$true;$w.Countries.EYR.Flags.HSM_VER_treaty_signed=$true;$w.Countries.ERI.Flags.HSM_VER_charter_signed=$true;$w.Countries.ERI.Flags.HSM_VER_union_established=$true;$w.Countries.EYR.Flags.HSM_VER_charter_signed=$true
 return $w
}
function Resolve($v,$w){if($v -eq 'ROOT'){return $w.Root};if($v -eq 'FROM'){return $w.From};return $v}
function Conditions($nodes,$w,$scope){
 foreach($n in $nodes){
  $v=$n.Value
  $ok=switch($n.Key){
   'tooltip' {$true}
   'custom_trigger_tooltip' {Conditions $n.Children $w $scope}
   'AND' {Conditions $n.Children $w $scope}
   'OR' {@($n.Children|Where-Object{Conditions @($_) $w $scope}).Count -gt 0}
   'NOT' {@($n.Children|Where-Object{Conditions @($_) $w $scope}).Count -eq 0}
   'always' {$v -eq 'yes'}
   'tag' {$scope.Tag -eq (Resolve $v $w)}
   'original_tag' {$scope.Original -eq (Resolve $v $w)}
   'exists' {$scope.Exists -eq ($v -eq 'yes')}
   'is_subject' {$scope.Subject -eq ($v -eq 'yes')}
   'has_capitulated' {$scope.Capitulated -eq ($v -eq 'yes')}
   'has_war' {($scope.War -or $scope.Wars.Count -gt 0) -eq ($v -eq 'yes')}
   'has_war_with' {(Resolve $v $w) -in $scope.Wars}
   'has_defensive_war_with' {(Resolve $v $w) -in $scope.Defensive}
   'has_offensive_war_with' {(Resolve $v $w) -in $scope.Offensive}
   'has_war_together_with' {(Resolve $v $w) -in $scope.Together}
   'has_country_flag' {$scope.Flags.ContainsKey($v)}
   'has_idea' {$scope.Ideas.ContainsKey($v)}
   'has_global_flag' {$v -in $w.Global}
   'has_character' {$v -in $scope.Characters}
   'owns_state' {$w.States[$v].Owner -eq $scope.Tag}
   'controls_state' {$w.States[$v].Controller -eq $scope.Tag}
   'is_fully_controlled_by' {$scope.Controller -eq (Resolve $v $w)}
   'date' {$w.Date -gt [datetime]::ParseExact($v,'yyyy.M.d',$null)}
   'free_building_slots' {$scope.Slots -gt 0}
   'any_country' {@($w.Countries.Values|Where-Object{$_.Exists -and (Conditions $n.Children $w $_)}).Count -gt 0}
   'ROOT' {Conditions $n.Children $w $w.Countries[$w.Root]}
   'FROM' {Conditions $n.Children $w $w.Countries[$w.From]}
   default{
    if($triggers.ContainsKey($n.Key)){(Conditions $triggers[$n.Key].Children $w $scope) -eq ($v -eq 'yes')}
    elseif($w.Countries.ContainsKey($n.Key)){Conditions $n.Children $w $w.Countries[$n.Key]}
    elseif($w.States.ContainsKey($n.Key)){Conditions $n.Children $w $w.States[$n.Key]}
    else{throw "Unsupported trigger $($n.Key)"}
   }
  }
  if(-not $ok){return $false}
 }
 return $true
}
function RunEffects($nodes,$w,$scope){
 for($idx=0;$idx -lt $nodes.Count;$idx++){
  $n=$nodes[$idx];$v=$n.Value
  if($n.Key -eq 'if'){
   $taken=Conditions (Prop $n 'limit')[0].Children $w $scope
   if($taken){RunEffects @($n.Children|Where-Object Key -ne 'limit') $w $scope}
   while($idx+1 -lt $nodes.Count -and $nodes[$idx+1].Key -in @('else_if','else')){
    $branch=$nodes[++$idx]
    if(-not $taken -and ($branch.Key -eq 'else' -or (Conditions (Prop $branch 'limit')[0].Children $w $scope))){
     RunEffects @($branch.Children|Where-Object Key -ne 'limit') $w $scope;$taken=$true
    }
   }
   continue
  }
  switch($n.Key){
   'custom_effect_tooltip' {}
   'show_ideas_tooltip' {}
   'hidden_effect' {RunEffects $n.Children $w $scope}
   'set_country_flag' {$flag=if($v){$v}else{Value $n 'flag'};$scope.Flags[$flag]=$true}
   'clr_country_flag' {$scope.Flags.Remove($v)}
   'add_political_power' {$scope.PP+=[double]$v}
   'add_stability' {$scope.Stability+=[double]$v}
   'add_timed_idea' {$scope.Ideas[(Value $n 'idea')]=[int](Value $n 'days')}
   'remove_ideas' {$scope.Ideas.Remove($v)}
   'country_event' {$scope.Events+=(Value $n 'id')}
   'add_tech_bonus' {$scope.Tech+=(Value $n 'name')}
   'add_extra_state_shared_building_slots' {$scope.Slots+=[int]$v}
   'add_building_construction' {$scope.Buildings+=[int](Value $n 'level')}
   'FROM' {RunEffects $n.Children $w $w.Countries[$w.From]}
   'ROOT' {RunEffects $n.Children $w $w.Countries[$w.Root]}
   default{
    if($effects.ContainsKey($n.Key)){RunEffects $effects[$n.Key].Children $w $scope}
    elseif($w.Countries.ContainsKey($n.Key)){RunEffects $n.Children $w $w.Countries[$n.Key]}
    elseif($w.States.ContainsKey($n.Key)){RunEffects $n.Children $w $w.States[$n.Key]}
    else{throw "Unsupported effect $($n.Key)"}
   }
  }
 }
}
function Trigger($id,$w,$tag='ERI'){Conditions $triggers[$id].Children $w $w.Countries[$tag]}
function Effect($id,$w,$tag='ERI'){RunEffects $effects[$id].Children $w $w.Countries[$tag]}
function Action($name,$w,$rt,$ft){$w.Root=$rt;$w.From=$ft;RunEffects (Prop (Prop $actions $name)[0] 'effect')[0].Children $w $w.Countries[$rt]}
function Defence($w){foreach($tag in @('ERI','EYR')){$w.Countries[$tag].Wars=@('GRI');$w.Countries[$tag].Defensive=@('GRI');$w.Countries[$tag].Together=@('ERI','EYR')};$w.Countries.GRI.Wars=@('ERI','EYR')}
function Peace($w){foreach($c in $w.Countries.Values){$c.War=$false;$c.Wars=@();$c.Defensive=@();$c.Offensive=@();$c.Together=@()}}
function Victory{$w=World;Action 'on_declare_war' $w 'GRI' 'EYR';Defence $w;Action 'on_capitulation_immediate' $w 'GRI' 'ERI';Peace $w;Action 'on_peaceconference_ended' $w 'ERI' 'GRI';$w.Root='ERI';return $w}

Case 'genuine GRI attack, defensive defeat and ERI peace victory unlock settlement' {
 $w=Victory;Assert (Trigger 'HSM_VER_IMP_settlement_context' $w) 'positive victory'
 Action 'on_daily_ERI' $w 'ERI' 'GRI'
 Assert (Trigger 'HSM_VER_IMP_settlement_context' $w) 'proof lost after peace'
}
Case 'unsigned target, foreign attacker and GRI successor cannot create proof' {
 foreach($s in @('unsigned','foreign','successor')){
  $w=World
  if($s -eq 'unsigned'){$w.Countries.EYR.Flags.Clear()}
  if($s -eq 'successor'){$w.Countries.GRI.Original='CYA'}
  $attacker=if($s -eq 'foreign'){'FAT'}else{'GRI'}
  Action 'on_declare_war' $w $attacker 'EYR'
  Assert (-not $w.Countries.ERI.Flags.ContainsKey('HSM_VER_IMP_defensive_war_recorded')) $s
 }
}
Case 'ERI absence, offensive war and unrelated victor cannot certify defeat' {
 foreach($s in @('absent','offensive','thirdparty')){
  $w=World;Action 'on_declare_war' $w 'GRI' 'EYR';Defence $w
  if($s -eq 'absent'){$w.Countries.ERI.Defensive=@()}
  if($s -eq 'offensive'){$w.Countries.ERI.Offensive=@('GRI')}
  $victor=if($s -eq 'thirdparty'){'FAT'}else{'ERI'}
  Action 'on_capitulation_immediate' $w 'GRI' $victor
  Assert (-not $w.Countries.ERI.Flags.ContainsKey('HSM_VER_IMP_defeat_recorded')) $s
 }
}
Case 'white peace, wrong conference scopes and uncapitulation do not unlock' {
 $w=World;Action 'on_declare_war' $w 'GRI' 'EYR';Action 'on_peaceconference_ended' $w 'ERI' 'GRI'
 Assert (-not $w.Countries.ERI.Flags.ContainsKey('HSM_VER_IMP_peace_recorded')) 'white peace'
 Defence $w;Action 'on_capitulation_immediate' $w 'GRI' 'ERI'
 Action 'on_peaceconference_ended' $w 'FAT' 'GRI';Action 'on_peaceconference_ended' $w 'ERI' 'FAT'
 Assert (-not $w.Countries.ERI.Flags.ContainsKey('HSM_VER_IMP_peace_recorded')) 'wrong conference'
 Action 'on_uncapitulation' $w 'GRI' 'ERI'
 Assert (-not $w.Countries.ERI.Flags.ContainsKey('HSM_VER_IMP_defeat_recorded')) 'uncapitulation'
}
Case 'later charter aggression invalidates old defensive defeat and peace' {
 $w=Victory;Action 'on_declare_war' $w 'EYR' 'GRI'
 Assert (-not (Trigger 'HSM_VER_IMP_settlement_context' $w)) 'stale victory'
}
Case 'occupation, proxy capital, war, missing union or suspended charter deny entry' {
 foreach($s in @('occupation','proxy','war','partnerwar','griwar','union','suspended')){
  $w=Victory
  switch($s){
   occupation{$w.States.'382'.Owner='GRI'}
   proxy{$w.States.'382'.Owner='EYR';$w.States.'382'.Controller='EYR'}
   war{$w.Countries.ERI.War=$true}
   partnerwar{$w.Countries.EYR.War=$true}
   griwar{$w.Countries.GRI.War=$true}
   union{$w.Countries.ERI.Flags.Remove('HSM_VER_union_established')}
   suspended{$w.Countries.ERI.Flags.HSM_VER_charter_suspended=$true}
  }
  Assert (-not (Trigger 'HSM_VER_IMP_settlement_context' $w)) $s
 }
}
Case 'historical ERI signatures cannot replace live independent EYR treaty' {
 foreach($s in @('annexed','subject','capitulated','treaty','charter','suspended')){
  $w=Victory
  switch($s){
   annexed{$w.Countries.EYR.Exists=$false}
   subject{$w.Countries.EYR.Subject=$true}
   capitulated{$w.Countries.EYR.Capitulated=$true}
   treaty{$w.Countries.EYR.Flags.Remove('HSM_VER_treaty_signed')}
   charter{$w.Countries.EYR.Flags.Remove('HSM_VER_charter_signed')}
   suspended{$w.Countries.EYR.Flags.HSM_VER_charter_suspended=$true}
  }
  Assert (-not (Trigger 'HSM_VER_IMP_institutions_available' $w)) $s
 }
}
Case 'mandate optional, initial cost once, finite and no refusal bypass' {
 $w=Victory;Effect 'HSM_VER_IMP_begin_mandate' $w;Effect 'HSM_VER_IMP_begin_mandate' $w
 Assert ($w.Countries.ERI.PP -eq -50 -and $w.Countries.ERI.Ideas.HSM_VER_IMP_reconstruction_mandate -eq 730) 'repeated start'
 $w=Victory;$w.Countries.ERI.Flags.HSM_VER_IMP_offer_resolved=$true;Effect 'HSM_VER_IMP_begin_mandate' $w
 Assert (-not $w.Countries.ERI.Flags.ContainsKey('HSM_VER_IMP_mandate_active')) 'refusal bypass'
}
Case 'Grover state partition, death overrides residue, annexed host unknown, native age boundary' {
 foreach($s in @('dead','minor','adult','foreign','unknown','annexedhost')){
  $w=World
  switch($s){
   dead{$w.Global=@('GRI_grover_vi_dead');$w.Countries.ERI.Characters=@('GRI_emperor_grover_vi')}
   minor{$w.Countries.ERI.Characters=@('GRI_emperor_grover_vi')}
   adult{$w.Countries.ERI.Characters=@('GRI_emperor_grover_vi');$w.Date=[datetime]::new(1021,5,22)}
   foreign{$w.Countries.CYA.Characters=@('GRI_emperor_grover_vi')}
   annexedhost{$w.Countries.GRI.Characters=@('GRI_emperor_grover_vi');$w.Countries.GRI.Exists=$false}
  }
  $matches=@('dead','local_minor','local_adult','abroad','unknown')|Where-Object{Trigger "HSM_VER_IMP_grover_$_" $w}
  Assert (@($matches).Count -eq 1) "ambiguous $s"
  $expected=@{dead='dead';minor='local_minor';adult='local_adult';foreign='abroad';unknown='unknown';annexedhost='unknown'}[$s]
  Assert ($matches -eq $expected) "wrong fate $s"
 }
 $w=World;$w.Countries.ERI.Characters=@('GRI_emperor_grover_vi');$w.Date=[datetime]::new(1021,5,21)
 Assert (Trigger 'HSM_VER_IMP_grover_local_minor' $w) 'minor boundary'
 $w.Date=[datetime]::new(1021,5,22)
 Assert (Trigger 'HSM_VER_IMP_grover_local_adult' $w) 'adult boundary'
}
Case 'only actual signatories receive invitation and stale consent fails' {
 $w=Victory;Effect 'HSM_VER_IMP_begin_mandate' $w;Effect 'HSM_VER_IMP_offer_protocol' $w
 Assert ($w.Countries.EYR.Events -contains 'hsm_ver_imperial.4') 'missing invite'
 Assert ($w.Countries.AVI.Events.Count -eq 0) 'unsigned AVI invited'
 $w.Countries.EYR.War=$true;Effect 'HSM_VER_IMP_sign_protocol' $w 'EYR'
 Assert ($w.Countries.EYR.Ideas.Count -eq 0 -and $w.Countries.ERI.Ideas.Count -eq 1) 'stale acceptance'
}
Case 'two partners do not refresh ERI bonus; live idea cancellation uses protocol validity' {
 $w=Victory;$w.Countries.AVI.Flags.HSM_VER_charter_signed=$true
 Effect 'HSM_VER_IMP_begin_mandate' $w;Effect 'HSM_VER_IMP_offer_protocol' $w;Effect 'HSM_VER_IMP_sign_protocol' $w 'EYR'
 $w.Countries.ERI.Ideas.HSM_VER_IMP_technical_protocol=700
 Effect 'HSM_VER_IMP_sign_protocol' $w 'AVI'
 Assert ($w.Countries.ERI.Ideas.HSM_VER_IMP_technical_protocol -eq 700) 'refreshed timer'
 $idea=$ideas|Where-Object Key -eq 'HSM_VER_IMP_technical_protocol'
 Assert (-not (Conditions (Prop $idea 'cancel')[0].Children $w $w.Countries.ERI)) 'valid treaty cancelled'
 $w.Countries.EYR.Exists=$false
 Assert (Conditions (Prop $idea 'cancel')[0].Children $w $w.Countries.ERI) 'ERI bonus survived lost EYR'
 Assert (Conditions (Prop $idea 'cancel')[0].Children $w $w.Countries.AVI) 'AVI bonus survived lost EYR'
}
Case 'civilian handover replaces mandate with one finite reward and epilogue' {
 $w=Victory;Effect 'HSM_VER_IMP_begin_mandate' $w;$w.Countries.ERI.Flags.HSM_VER_IMP_audit_published=$true
 Effect 'HSM_VER_IMP_civilian_handover' $w;Effect 'HSM_VER_IMP_civilian_handover' $w
 Assert ($w.Countries.ERI.PP -eq 25 -and $w.Countries.ERI.Stability -eq 0.02) 'repeat reward'
 Assert ($w.Countries.ERI.Ideas.Count -eq 1 -and $w.Countries.ERI.Ideas.HSM_VER_IMP_civilian_legacy -eq 730) 'wrong legacy'
 Assert (-not (Trigger 'HSM_VER_IMP_mandate_work_allowed' $w)) 'still active'
}
Case 'final year replaces initial spirit then expires into one legacy' {
 $w=Victory;Effect 'HSM_VER_IMP_begin_mandate' $w;$w.Countries.ERI.Flags.HSM_VER_IMP_audit_published=$true
 Effect 'HSM_VER_IMP_extend_mandate' $w
 Assert ($w.Countries.ERI.Ideas.Count -eq 1 -and $w.Countries.ERI.Ideas.HSM_VER_IMP_final_programme -eq 365) 'wrong term'
 $w.Countries.ERI.Flags.Remove('HSM_VER_IMP_mandate_deadline')
 Effect 'HSM_VER_IMP_check_mandate' $w;Effect 'HSM_VER_IMP_check_mandate' $w
 Assert ($w.Countries.ERI.Ideas.Count -eq 1 -and $w.Countries.ERI.Ideas.HSM_VER_IMP_civilian_legacy -eq 730) 'legacy'
 Assert ($w.Countries.ERI.Events.Count -eq 1) 'repeated epilogue'
}
Case 'unreviewed expiry, loss of capital, war or failed live union gives no legacy' {
 foreach($s in @('expiry','capital','war','eyr')){
  $w=Victory;Effect 'HSM_VER_IMP_begin_mandate' $w
  switch($s){
   expiry{$w.Countries.ERI.Flags.Remove('HSM_VER_IMP_mandate_deadline')}
   capital{$w.States.'382'.Controller='CYA'}
   war{$w.Countries.ERI.War=$true}
   eyr{$w.Countries.EYR.Exists=$false}
  }
  Effect 'HSM_VER_IMP_check_mandate' $w
  Assert ($w.Countries.ERI.Ideas.Count -eq 0 -and $w.Countries.ERI.Flags.ContainsKey('HSM_VER_IMP_mandate_ended')) $s
 }
}
Case 'repair contract is one-time, uses owned city and falls back at building cap' {
 foreach($s in @('factory','full','stale')){
  $w=Victory;Effect 'HSM_VER_IMP_begin_mandate' $w
  if($s -eq 'full'){$w.States.'382'.Slots=0}
  if($s -eq 'stale'){$w.States.'382'.Owner='CYA'}
  $option=(Prop $events.'hsm_ver_imperial.3' 'option')[0]
  $body=@($option.Children|Where-Object Key -notin @('name','ai_chance'))
  RunEffects $body $w $w.Countries.ERI
  RunEffects $body $w $w.Countries.ERI
  switch($s){
   factory{Assert ($w.States.'382'.Buildings -eq 1 -and $w.States.'382'.Slots -eq 6) 'repeated construction'}
   full{Assert ($w.States.'382'.Buildings -eq 0 -and $w.Countries.ERI.Tech.Count -eq 1) 'missing capped fallback'}
   stale{Assert ($w.States.'382'.Buildings -eq 0 -and $w.Countries.ERI.Tech.Count -eq 0) 'stale construction'}
  }
 }
}
Case 'fate event has exactly one narrative and option for each live status' {
 foreach($s in @('dead','minor','adult','foreign_minor','foreign_adult','unknown')){
  $w=World
  if($s -eq 'dead'){$w.Global=@('GRI_grover_vi_dead')}
  if($s -in @('minor','adult')){$w.Countries.ERI.Characters=@('GRI_emperor_grover_vi')}
  if($s -like 'foreign_*'){$w.Countries.CYA.Characters=@('GRI_emperor_grover_vi')}
  if($s -in @('adult','foreign_adult')){$w.Date=[datetime]::new(1021,5,22)}
  $descs=@(Prop $events.'hsm_ver_imperial.2' 'desc'|Where-Object{Conditions (Prop $_ 'trigger')[0].Children $w $w.Countries.ERI})
  $opts=@(Prop $events.'hsm_ver_imperial.2' 'option'|Where-Object{Conditions (Prop $_ 'trigger')[0].Children $w $w.Countries.ERI})
  Assert ($descs.Count -eq 1 -and $opts.Count -eq 1) "ambiguous event $s"
 }
}
function Unify($w){
 $w.Countries.ERI.Flags.HSM_VER_UNI_founded=$true
 $w.Countries.AVI.Flags.HSM_VER_charter_signed=$true
 foreach($tag in @('EYR','AVI')){$w.Countries[$tag].Exists=$false;$w.Countries.ERI.Flags["HSM_VER_UNI_absorbed_$tag"]=$true}
}
function Choose($id,$index,$w,$tag='ERI'){
 $option=(Prop $events[$id] 'option')[$index]
 RunEffects @($option.Children|Where-Object Key -notin @('name','trigger','ai_chance')) $w $w.Countries[$tag]
}
Case 'legitimate unification retains original defensive proof and local research effects' {
 $w=Victory;Unify $w
 Assert (Trigger 'HSM_VER_IMP_settlement_context' $w) 'unified context'
 Effect 'HSM_VER_IMP_begin_mandate' $w
 Effect 'HSM_VER_IMP_offer_protocol' $w
 Effect 'HSM_VER_IMP_offer_protocol' $w
 Assert ($w.Countries.ERI.Events.Count -eq 1 -and $w.Countries.ERI.Events[0] -eq 'hsm_ver_imperial.7') 'domestic invitation'
 foreach($tag in @('EYR','AVI')){Assert ($w.Countries[$tag].Events.Count -eq 0) 'event sent to dead country'}
 Choose 'hsm_ver_imperial.7' 0 $w
 $w.Countries.ERI.Ideas.HSM_VER_IMP_technical_protocol=700
 Choose 'hsm_ver_imperial.7' 0 $w
 Assert ($w.Countries.ERI.Ideas.HSM_VER_IMP_technical_protocol -eq 700) 'replayed research reward'
 Assert (Trigger 'HSM_VER_IMP_protocol_valid' $w) 'domestic protocol invalid'
 foreach($tag in @('EYR','AVI')){Assert (-not $w.Countries[$tag].Flags.ContainsKey('HSM_VER_IMP_protocol_signed')) 'forged foreign signature'}
 $w.Countries.ERI.Flags.HSM_VER_IMP_audit_published=$true
 Effect 'HSM_VER_IMP_civilian_handover' $w
 Assert (Trigger 'HSM_VER_IMP_protocol_valid' $w) 'research lost on civilian handover'
}
Case 'protocol already offered abroad can be continued internally without refreshing live benefit' {
 foreach($cancelled in @($false,$true)){
  $w=Victory;Effect 'HSM_VER_IMP_begin_mandate' $w;Effect 'HSM_VER_IMP_offer_protocol' $w;Effect 'HSM_VER_IMP_sign_protocol' $w 'EYR'
  $w.Countries.ERI.Ideas.HSM_VER_IMP_technical_protocol=500
  Unify $w
  if($cancelled){$w.Countries.ERI.Ideas.Remove('HSM_VER_IMP_technical_protocol')}
  Action 'on_daily_ERI' $w 'ERI' 'GRI'
  Assert ($w.Countries.ERI.Events -contains 'hsm_ver_imperial.7') 'lost post-absorption hearing'
  Choose 'hsm_ver_imperial.7' 0 $w
  $expected=if($cancelled){730}else{500}
  Assert ($w.Countries.ERI.Ideas.HSM_VER_IMP_technical_protocol -eq $expected) 'incorrect research duration'
 }
}
Case 'bilateral charter survives Eyrie absorption without inventing external Avian membership' {
 $w=Victory
 $w.Countries.ERI.Flags.HSM_VER_UNI_founded=$true
 $w.Countries.ERI.Flags.HSM_VER_UNI_absorbed_EYR=$true
 $w.Countries.EYR.Exists=$false
 Assert (Trigger 'HSM_VER_IMP_settlement_context' $w) 'bilateral unified charter rejected'
 Effect 'HSM_VER_IMP_begin_mandate' $w;Effect 'HSM_VER_IMP_offer_protocol' $w
 Choose 'hsm_ver_imperial.7' 0 $w
 Assert (Trigger 'HSM_VER_IMP_protocol_valid' $w) 'internal bilateral research rejected'
 Assert ($w.Countries.AVI.Events.Count -eq 0 -and -not $w.Countries.AVI.Flags.ContainsKey('HSM_VER_charter_signed')) 'external AVI made a signatory'
}
Case 'civilian services can continue an existing protocol after later absorption' {
 $w=Victory;Effect 'HSM_VER_IMP_begin_mandate' $w;Effect 'HSM_VER_IMP_offer_protocol' $w;Effect 'HSM_VER_IMP_sign_protocol' $w 'EYR'
 $w.Countries.ERI.Flags.HSM_VER_IMP_audit_published=$true
 Effect 'HSM_VER_IMP_civilian_handover' $w
 Unify $w
 $w.Countries.ERI.Ideas.Remove('HSM_VER_IMP_technical_protocol')
 Action 'on_daily_ERI' $w 'ERI' 'GRI'
 Assert ($w.Countries.ERI.Events -contains 'hsm_ver_imperial.7') 'post-handover continuation missing'
 Choose 'hsm_ver_imperial.7' 0 $w
 Assert ($w.Countries.ERI.Ideas.HSM_VER_IMP_technical_protocol -eq 730) 'civilian continuation not funded'
 Assert (-not $w.Countries.ERI.Flags.ContainsKey('HSM_VER_IMP_mandate_active')) 'continuation revived mandate'
}
Case 'neutral Avian conquest or late AVR consent preserve a real ducal charter and defensive settlement' {
 foreach($proof in @('HSM_VER_FORCE_AVI_integrated','HSM_VER_AVR_ratified')){
  $w=Victory;Unify $w
  $w.Countries.AVI.Flags.Remove('HSM_VER_charter_signed')
  $w.Countries.ERI.Flags[$proof]=$true
  Assert (Trigger 'HSM_VER_IMP_settlement_context' $w) "admission rejected: $proof"
  Effect 'HSM_VER_IMP_begin_mandate' $w;Effect 'HSM_VER_IMP_offer_protocol' $w
  Choose 'hsm_ver_imperial.7' 0 $w
  Assert ($w.Countries.ERI.PP -eq -50 -and $w.Countries.ERI.Ideas.HSM_VER_IMP_technical_protocol -eq 730) 'missing actual mandate/research reward'
  Assert ($w.Countries.AVI.Events.Count -eq 0 -and -not $w.Countries.AVI.Flags.ContainsKey('HSM_VER_charter_signed')) 'invented Avian signature or invitation'
  foreach($tag in @('ERI','EYR')){foreach($history in @('HSM_VER_treaty_signed','HSM_VER_charter_signed')){
   $w.Countries[$tag].Flags.Remove($history)
   Assert (-not (Trigger 'HSM_VER_IMP_settlement_context' $w)) "admission bypassed $tag $history"
   $w.Countries[$tag].Flags[$history]=$true
  }}
  foreach($attribute in @('Owner','Controller')){
   $w.States.'470'[$attribute]='CYA'
   Assert (-not (Trigger 'HSM_VER_IMP_protocol_valid' $w)) "admission bypassed 470 $attribute"
   $w.States.'470'[$attribute]='ERI'
  }
  $w.Countries.AVI.Exists=$true
  Assert (-not (Trigger 'HSM_VER_IMP_settlement_context' $w)) 'released AVI retained absorbed status'
  $w=World;Unify $w;$w.Countries.AVI.Flags.Remove('HSM_VER_charter_signed');$w.Countries.ERI.Flags[$proof]=$true
  Action 'on_capitulation_immediate' $w 'GRI' 'ERI';Action 'on_peaceconference_ended' $w 'ERI' 'GRI'
  Effect 'HSM_VER_IMP_begin_mandate' $w
  Assert (-not $w.Countries.ERI.Flags.ContainsKey('HSM_VER_IMP_mandate_active')) 'Avian admission manufactured GRI defensive victory'
 }
}
Case 'conquest or a peaceful founding alone cannot manufacture imperial defensive history' {
 foreach($offensive in @($false,$true)){
  $w=World;Unify $w
  if($offensive){Action 'on_declare_war' $w 'ERI' 'GRI';$w.Countries.ERI.Offensive=@('GRI')}
  Action 'on_capitulation_immediate' $w 'GRI' 'ERI';Peace $w;Action 'on_peaceconference_ended' $w 'ERI' 'GRI'
  Effect 'HSM_VER_IMP_begin_mandate' $w
  Assert (-not $w.Countries.ERI.Flags.ContainsKey('HSM_VER_IMP_mandate_active')) 'unearned mandate'
  Assert ($w.Countries.ERI.PP -eq 0) 'nonqualifying settlement charged'
 }
}
Case 'post-unification GRI aggression still records actual declaration defeat and conference' {
 $w=World;Unify $w;Action 'on_declare_war' $w 'GRI' 'ERI'
 $w.Countries.ERI.Wars=@('GRI');$w.Countries.ERI.Defensive=@('GRI');$w.Countries.GRI.Wars=@('ERI')
 Action 'on_capitulation_immediate' $w 'GRI' 'ERI';Peace $w;Action 'on_peaceconference_ended' $w 'ERI' 'GRI'
 Assert (Trigger 'HSM_VER_IMP_settlement_context' $w) 'genuine unified defence rejected'
}
Case 'ducal states and absorbed Avian homeland require host ownership and control; stale rewards stop' {
 foreach($id in @('391','400','401','500','673','470')){foreach($attribute in @('Owner','Controller')){
  $w=Victory;Unify $w;Effect 'HSM_VER_IMP_begin_mandate' $w;Effect 'HSM_VER_IMP_offer_protocol' $w
  $w.States[$id][$attribute]='CYA'
  Choose 'hsm_ver_imperial.7' 0 $w
  Assert (-not $w.Countries.ERI.Ideas.ContainsKey('HSM_VER_IMP_technical_protocol')) 'stale research acceptance'
  Effect 'HSM_VER_IMP_check_mandate' $w
  Assert ($w.Countries.ERI.Flags.ContainsKey('HSM_VER_IMP_mandate_interrupted') -and $w.Countries.ERI.Ideas.Count -eq 0) 'lost homeland retained mandate'
 }}
}
Case 'founding absorption and original charter proofs are all required' {
 foreach($scenario in @('founding','absorption','foreignannex','released','subject','capitulated','wronghost','oldhostannex','treatyERI','treatyEYR','charterERI','charterEYR','charterAVI','suspended')){
  $w=Victory;Unify $w
  switch($scenario){
   founding{$w.Countries.ERI.Flags.Remove('HSM_VER_UNI_founded')}
   absorption{$w.Countries.ERI.Flags.Remove('HSM_VER_UNI_absorbed_EYR')}
   foreignannex{$w.Countries.ERI.Flags.Remove('HSM_VER_UNI_absorbed_AVI')}
   released{$w.Countries.EYR.Exists=$true}
   subject{$w.Countries.ERI.Subject=$true}
   capitulated{$w.Countries.ERI.Capitulated=$true}
   wronghost{$w.Countries.ERI.Original='CYA'}
   oldhostannex{Action 'on_annex' $w 'CYA' 'ERI'}
   treatyERI{$w.Countries.ERI.Flags.Remove('HSM_VER_treaty_signed')}
   treatyEYR{$w.Countries.EYR.Flags.Remove('HSM_VER_treaty_signed')}
   charterERI{$w.Countries.ERI.Flags.Remove('HSM_VER_charter_signed')}
   charterEYR{$w.Countries.EYR.Flags.Remove('HSM_VER_charter_signed')}
   charterAVI{$w.Countries.AVI.Flags.Remove('HSM_VER_charter_signed')}
   suspended{$w.Countries.EYR.Flags.HSM_VER_charter_suspended=$true}
  }
  Effect 'HSM_VER_IMP_begin_mandate' $w
  Assert (-not (Trigger 'HSM_VER_IMP_settlement_context' $w)) $scenario
  Assert ($w.Countries.ERI.Ideas.Count -eq 0) "reward despite $scenario"
 }
}
Case 'domestic refusal and delayed invalid offer cannot award research' {
 $w=Victory;Unify $w;Effect 'HSM_VER_IMP_begin_mandate' $w;Effect 'HSM_VER_IMP_offer_protocol' $w
 Choose 'hsm_ver_imperial.7' 1 $w;Choose 'hsm_ver_imperial.7' 0 $w
 Assert (-not $w.Countries.ERI.Ideas.ContainsKey('HSM_VER_IMP_technical_protocol')) 'refusal bypass'
}
Case 'all timed flags specify value one' {
 foreach($n in $all|Where-Object{$_.Key -eq 'set_country_flag' -and $_.Children.Count}){
  Assert ((Value $n 'value') -eq '1') 'missing explicit flag value'
 }
}
Write-Output "Completed $script:passed cases; $($loc.english.Count) paired localization keys."
