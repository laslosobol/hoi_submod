#Requires -Version 7.2
param(
    [string] $GameRoot = 'C:/shit/Steam/steamapps/common/Hearts of Iron IV',
    [string] $NodeCommand = 'node'
)
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$nodeRuntime = Get-Command $NodeCommand -CommandType Application -ErrorAction Stop
if (-not (Test-Path -LiteralPath (Join-Path $GameRoot 'interface/decisions.gfx') -PathType Leaf)) {
    throw 'Missing game interface/decisions.gfx. Supply the installed game directory with -GameRoot.'
}

# Persist the original 38 validation groups and their ordered Clausewitz parser.
# Requires Node.js on PATH (or -NodeCommand) and the reference dependency in EaW/.
# The limited evaluator rejects unknown predicates/effects; it is not an HOI4 runtime.
# Pass paths as arguments and source through stdin; no temporary fixture files are used.
$javascript = @'
const fs = require('fs');
const path = require('path');
const assert = require('assert/strict');
const root = process.argv[2];
const gameRoot = process.argv[3];
const read = p => fs.readFileSync(path.join(root,p),'utf8');
function parse(text) {
  const tokens = (text.match(/"(?:\\.|[^"\\])*"|#[^\r\n]*|[{}]|[<>!=?]+|[^\s{}=<>!?#]+/g)||[]).filter(t=>!t.startsWith('#'));
  let i=0;
  function block(nested=false) {
    const out=[];
    while(i<tokens.length) {
      const key=tokens[i++];
      if(key==='}') { assert(nested,'unexpected closing brace'); return out; }
      assert(key!=='{','unexpected opening brace');
      const n={key,op:'',value:''};
      if(/^[<>!=?]+$/.test(tokens[i]||'')) {
        n.op=tokens[i++]; assert(i<tokens.length,'missing value');
        if(tokens[i]==='{') {i++;n.children=block(true);}
        else n.value=tokens[i++];
      }
      out.push(n);
    }
    assert(!nested,'unclosed block');
    return out;
  }
  return block();
}
const prop=(nodes,key)=>(nodes||[]).find(n=>n.key===key);
const val=(nodes,key)=>prop(nodes,key)?.value;
const body=(nodes,key)=>prop(nodes,key)?.children||[];
const definitions=p=>Object.fromEntries(parse(read('mod/HoISubmod/'+p)).map(n=>[n.key,n.children]));
const effects=definitions('common/scripted_effects/HSM_BAR_diplomacy.txt');
const triggers=definitions('common/scripted_triggers/HSM_BAR_diplomacy.txt');
const decisionRoots=parse(read('mod/HoISubmod/common/decisions/HSM_BAR_diplomacy.txt'));
const decisions=Object.fromEntries(decisionRoots[0].children.map(n=>[n.key,n.children]));
const events=Object.fromEntries(parse(read('mod/HoISubmod/events/HSM_BAR_diplomacy.txt')).filter(n=>n.key==='country_event').map(n=>[val(n.children,'id'),n.children]));
const focus={}, native={};
let passed=0;
function test(name,fn) {fn();passed++;console.log('PASS '+name);}
const changed={
 'common/national_focus/WIT.txt':['WIT_save_barrad','WIT_barrad_ultimatum','WIT_reclaim_barrad','WIT_liberate_barrad','WIT_fate_of_barrad','WIT_barrad_question','WIT_integrate_barrad','WIT_grand_griffking_canal'],
 'common/national_focus/ZES.txt':['ZES_to_north','ZES_noblest_cause','ZES_emergency_aid','ZES_secure_mountain_holds','ZES_cleanse_monsters','ZES_establish_havens','ZES_hang_them','ZES_barrad_comission'],
 'common/decisions/ZES_decisions.txt':['ZES_diplomacy_barrad_attack'],
 'common/decisions/OLV_decisions.txt':['OLV_coqnuer_BAR'],
 'common/decisions/GRU_decisions.txt':['GRU_claims'],
 'events/Wittenland.txt':['wittenland.65','wittenland.80','wittenland.81','wittenland.82']
};
test('all unrelated upstream AST nodes preserved in six same-path overrides',()=>{
 for(const [p,ids] of Object.entries(changed)) {
  const upstream=parse(read('EaW/'+p)),current=parse(read('mod/HoISubmod/'+p));
  const strip=nodes=>nodes.filter(n=>!ids.includes(val(n.children||[],'id'))&&!ids.includes(n.key)).map(n=>n.children?{...n,children:strip(n.children)}:n);
  assert.deepEqual(strip(current),strip(upstream),p);
  function collect(nodes) { for(const n of nodes) {
    if(n.key==='shared_focus'&&n.children) focus[val(n.children,'id')]=n.children;
    if(ids.includes(n.key)) native[n.key]=n.children;
    if(n.children)collect(n.children);
  }}
  collect(current);
  if(p.includes('national_focus'))for(const n of upstream) {
    const id=val(n.children||[],'id');
    if(['WIT_save_barrad','WIT_barrad_ultimatum','WIT_reclaim_barrad','WIT_liberate_barrad','ZES_to_north','ZES_noblest_cause'].includes(id)) {
      const old=body(n.children,'completion_reward').filter(n=>n.key!=='log');
      assert.deepEqual(body(body(focus[id],'completion_reward'),'else'),old,id+' original fallback');
    }
  }
 }
});
test('native countdown durations and one-shot behaviour preserved',()=>{
 assert.equal(val(native.ZES_diplomacy_barrad_attack,'days_remove'),'15');
 assert.equal(val(native.OLV_coqnuer_BAR,'days_remove'),'30');
 assert.equal(val(native.GRU_claims,'days_remove'),'15');
 assert.equal(val(native.ZES_diplomacy_barrad_attack,'fire_only_once'),'yes');
 assert.equal(val(native.OLV_coqnuer_BAR,'fire_only_once'),'yes');
});
test('localisation key parity, UTF-8 BOM, and all own visible references resolved',()=>{
 const sets=[];
 for(const lang of ['english','russian']) {
  const p='mod/HoISubmod/localisation/'+lang+'/HSM_BAR_diplomacy_l_'+lang+'.yml';
  const bytes=fs.readFileSync(path.join(root,p));assert.equal(bytes.subarray(0,3).toString('hex'),'efbbbf');
  const s=read(p);assert(!s.includes('\uFFFD'));
  const keys=[...s.matchAll(/^ ([\w.]+):\d+ "/gm)].map(m=>m[1]);
  assert.equal(new Set(keys).size,keys.length);sets.push(new Set(keys));
  if(lang==='russian')assert(/[\u0410-\u044f]/.test(s));
 }
 assert.deepEqual([...sets[0]].sort(),[...sets[1]].sort());
 function check(nodes) { for(const n of nodes) {
   if(['title','desc','text','name','custom_effect_tooltip'].includes(n.key)&&n.value.startsWith('HSM_BAR_dip')) assert(sets[0].has(n.value),n.value);
   if(n.children)check(n.children);
 }}
 for(const nodes of Object.values(events))check(nodes);
 for(const nodes of Object.values(effects))check(nodes);
 for(const id of Object.keys(decisions)) {assert(sets[0].has(id),id);assert(sets[0].has(id+'_desc'));}
});
test('all new effects, triggers, events and native assets resolve',()=>{
 function check(nodes) {for(const n of nodes) {
  if(n.key.startsWith('HSM_BAR_dip_'))assert(effects[n.key]||triggers[n.key],n.key);
  if(n.key==='country_event')assert(events[val(n.children,'id')],val(n.children,'id'));
  if(n.children)check(n.children);
 }}
 for(const n of Object.values(effects))check(n);
 for(const n of Object.values(events))check(n);
 for(const n of Object.values(decisions))check(n);
 const gfx=read('EaW/interface/eaw_eventpictures.gfx')+fs.readFileSync(path.join(gameRoot,'interface/decisions.gfx'),'utf8');
 for(const id of ['GFX_event_river_coalition_summit','GFX_event_pony_soldiers_sunset','GFX_decision_generic_political_discourse','GFX_decision_generic_civil_support','GFX_decision_generic_intelligence_operation','GFX_decision_generic_prepare_civil_war'])assert(gfx.includes('"'+id+'"'),id);
 for(const n of Object.values(effects))assert(!JSON.stringify(n).match(/white_peace|set_autonomy|puppet/));
});
const tags=['BAR','WIT','ZES','OLV','GRU'];
function world(route='collegium') {
 const w={countries:{},queue:[],declarations:[],root:'BAR',from:'BAR'};
 for(const tag of tags)w.countries[tag]={tag,exists:true,subject:false,flags:new Set(),wars:new Set(),pacts:new Set(),goals:new Set(),focus:new Set(),decisions:new Set(),ideas:new Set(),owned:new Set(),government:'democratic',tree:'',pp:0,stability:0,canWar:true};
 w.countries.BAR.flags.add('HSM_BAR_active');w.countries.BAR.flags.add('HSM_BAR_'+route);
 return w;
}
const resolve=(s,w)=>s==='ROOT'?w.root:s==='FROM'?w.from:s;
function cond(nodes,w,scope) {
 return nodes.every(n=>{
  const c=w.countries[scope],v=n.value;
  if(n.key==='AND')return cond(n.children,w,scope);
  if(n.key==='OR')return n.children.some(x=>cond([x],w,scope));
  if(n.key==='NOT')return !n.children.some(x=>cond([x],w,scope));
  if(tags.includes(n.key)||['ROOT','FROM'].includes(n.key))return cond(n.children,w,resolve(n.key,w));
  if(triggers[n.key])return cond(triggers[n.key],w,scope)===(v==='yes');
  if(n.key==='always')return v==='yes';
  if(n.key==='tag'||n.key==='original_tag')return scope===v;
  if(n.key==='exists')return c.exists===(v==='yes');
  if(n.key==='is_subject')return c.subject===(v==='yes');
  if(n.key==='has_country_flag')return c.flags.has(v);
  if(n.key==='has_completed_focus')return c.focus.has(v);
  if(n.key==='has_focus_tree')return c.tree===v;
  if(n.key==='has_government')return c.government===v;
  if(n.key==='has_war_with')return c.wars.has(resolve(v,w));
  if(n.key==='has_war')return (c.wars.size>0)===(v==='yes');
  if(n.key==='has_decision')return c.decisions.has(v);
  if(n.key==='has_idea')return c.ideas.has(v);
  if(n.key==='has_character'||n.key==='has_guaranteed')return false;
  if(n.key==='is_in_faction_with')return false;
  if(n.key==='has_wargoal_against')return c.goals.has(resolve(v,w));
  if(n.key==='can_declare_war_on')return c.canWar&&!c.wars.has(resolve(v,w))&&!c.pacts.has(resolve(v,w));
  if(n.key==='owns_state'||n.key==='has_full_control_of_state')return c.owned.has(v);
  if(/^\d+$/.test(n.key))return n.children.every(x=>x.key==='is_owned_and_controlled_by'&&w.countries[resolve(x.value,w)].owned.has(n.key));
  throw Error('Unimplemented test predicate '+n.key);
 });
}
function run(nodes,w,scope) {
 let matched=false;
 for(const n of nodes) {
  const c=w.countries[scope],v=n.value;
  if(n.key==='if'||n.key==='else_if') {
    if(n.key==='if')matched=false;
    if(!matched&&cond(body(n.children,'limit'),w,scope)) {matched=true;run(n.children.filter(x=>x.key!=='limit'),w,scope);}
    continue;
  }
  if(n.key==='else'){if(!matched)run(n.children,w,scope);matched=true;continue;}
  if(tags.includes(n.key)||['ROOT','FROM'].includes(n.key)){run(n.children,w,resolve(n.key,w));continue;}
  if(effects[n.key]){run(effects[n.key],w,scope);continue;}
  if(n.key==='hidden_effect'){run(n.children,w,scope);continue;}
  if(n.key==='set_country_flag'){c.flags.add(n.children?val(n.children,'flag'):v);continue;}
  if(n.key==='clr_country_flag'){c.flags.delete(v);continue;}
  if(n.key==='country_event'){w.queue.push({country:scope,id:val(n.children,'id'),days:val(n.children,'days')});continue;}
  if(n.key==='create_wargoal'){c.goals.add(resolve(val(n.children,'target'),w));continue;}
  if(n.key==='remove_wargoal'){c.goals.delete(resolve(val(n.children,'target'),w));continue;}
  if(n.key==='declare_war_on'){const t=resolve(val(n.children,'target'),w);c.wars.add(t);w.countries[t].wars.add(scope);w.declarations.push(scope);continue;}
  if(n.key==='diplomatic_relation'){const t=val(n.children,'country');if(val(n.children,'active')==='yes'){c.pacts.add(t);w.countries[t].pacts.add(scope);}else{c.pacts.delete(t);w.countries[t].pacts.delete(scope);}continue;}
  if(n.key==='load_focus_tree'){c.tree=val(n.children,'tree');continue;}
  if(n.key==='add_political_power'){c.pp+=Number(v);continue;}
  if(n.key==='add_stability'){c.stability+=Number(v);continue;}
  if(n.key==='add_ideas'){c.ideas.add(v);continue;}
  if(['log','custom_effect_tooltip','add_opinion_modifier','remove_opinion_modifier','add_ai_strategy','ai_chance','name','trigger'].includes(n.key)||n.key.startsWith('eaw_'))continue;
  throw Error('Unimplemented test effect '+n.key);
 }
}
const effect=(id,w,tag='BAR')=>run(effects[id],w,tag);
const options=id=>events[id].filter(n=>n.key==='option').map(n=>n.children);
for(const route of ['collegium','directorate'])for(const tag of ['WIT','ZES','OLV']) {
 const ev=tag==='WIT'?10:tag==='ZES'?20:30;
 test(route+'/'+tag+': duplicate-safe offer, inspected treaty, repeat threat, historical progression',()=>{
  const w=world(route);effect('HSM_BAR_dip_'+tag+'_challenge',w,tag);effect('HSM_BAR_dip_'+tag+'_challenge',w,tag);
  assert.equal(w.queue.length,1);run(options('hsm_bar_diplomacy.'+ev)[0],w,tag);
  run(options('hsm_bar_diplomacy.'+(ev+1))[0],w,'BAR');
  assert(w.countries.BAR.flags.has('HSM_BAR_'+tag+'_agreement'));
  assert(w.countries.BAR.pacts.has(tag));assert.equal(w.countries.BAR.pp,-35);
  assert(w.countries[tag].flags.has('HSM_BAR_dip_settled'));
  const count=w.queue.length;effect('HSM_BAR_dip_'+tag+'_challenge',w,tag);assert.equal(w.queue.length,count);
  assert.equal(w.declarations.length,0);
 });
 test(route+'/'+tag+': strict terms and explicit refusal permit war',()=>{
  const w=world(route);effect('HSM_BAR_dip_'+tag+'_challenge',w,tag);run(options('hsm_bar_diplomacy.'+ev)[1],w,tag);
  effect('HSM_BAR_dip_'+tag+'_accept',w);assert.equal(w.countries.BAR.pp,-75);assert.equal(w.countries.BAR.stability,-0.03);
  const x=world(route);effect('HSM_BAR_dip_'+tag+'_challenge',x,tag);effect('HSM_BAR_dip_'+tag+'_refuse',x);
  assert(x.queue.some(e=>e.id==='hsm_bar_diplomacy.90'));run(options('hsm_bar_diplomacy.90')[0],x,tag);
  assert(x.countries[tag].wars.has('BAR'));assert(x.countries[tag].goals.has('BAR'));
 });
 test(route+'/'+tag+': war, annexation and subjugation invalidate delayed acceptance',()=>{
  for(const invalid of ['war','annexed','bar_subject','neighbour_subject','neighbour_gone']) {
   const w=world(route);effect('HSM_BAR_dip_'+tag+'_challenge',w,tag);w.countries.BAR.flags.add('HSM_BAR_dip_'+tag+'_terms');
   if(invalid==='war')w.countries.BAR.wars.add(tag);
   if(invalid==='annexed')w.countries.BAR.exists=false;
   if(invalid==='bar_subject')w.countries.BAR.subject=true;
   if(invalid==='neighbour_subject')w.countries[tag].subject=true;
   if(invalid==='neighbour_gone')w.countries[tag].exists=false;
   effect('HSM_BAR_dip_'+tag+'_accept',w);assert(!w.countries.BAR.flags.has('HSM_BAR_'+tag+'_agreement'));
   effect('HSM_BAR_dip_daily_pulse',w);assert(!w.countries.BAR.flags.has('HSM_BAR_dip_'+tag+'_pending'));
  }
 });
}
for(const [tag,id] of [['ZES','ZES_diplomacy_barrad_attack'],['OLV','OLV_coqnuer_BAR']]) {
 test(tag+': native timer gates refusal and expires once',()=>{
  const w=world();w.root=tag;run(body(native[id],'complete_effect'),w,tag);
  effect('HSM_BAR_dip_'+tag+'_refuse',w);assert(!w.queue.some(e=>e.id==='hsm_bar_diplomacy.90'));
  run(body(native[id],'remove_effect'),w,tag);assert.equal(w.queue.filter(e=>e.id==='hsm_bar_diplomacy.90').length,1);
  assert.equal(w.declarations.length,0);
 });
 test(tag+': old in-flight timer resolves through talks even during its removal callback',()=>{
  const w=world('directorate');w.root=tag;w.countries[tag].decisions.add(id);
  run(body(native[id],'remove_effect'),w,tag);
  assert(!w.countries.BAR.flags.has('HSM_BAR_dip_'+tag+'_timer'));
  assert(w.countries.BAR.flags.has('HSM_BAR_dip_'+tag+'_pending'));
  effect('HSM_BAR_dip_'+tag+'_refuse',w);assert(w.queue.some(e=>e.id==='hsm_bar_diplomacy.90'));
  assert.equal(w.declarations.length,0);
 });
 test(tag+': agreement suppresses a running countdown war, legacy regime still declares',()=>{
  const w=world();w.root=tag;run(body(native[id],'complete_effect'),w,tag);
  w.countries.BAR.flags.add('HSM_BAR_dip_'+tag+'_terms');effect('HSM_BAR_dip_'+tag+'_accept',w);
  run(body(native[id],'remove_effect'),w,tag);assert.equal(w.declarations.length,0);
  const legacy=world();legacy.root=tag;legacy.countries.BAR.flags.clear();
  run(body(native[id],'remove_effect'),legacy,tag);assert(legacy.countries[tag].wars.has('BAR'));
 });
}
test('legacy Barrad excluded and double route flags rejected',()=>{
 const w=world();w.countries.BAR.flags.clear();assert(!cond(triggers.HSM_BAR_dip_route,w,'BAR'));
 w.countries.BAR.flags=new Set(['HSM_BAR_active','HSM_BAR_collegium','HSM_BAR_directorate']);assert(!cond(triggers.HSM_BAR_dip_route,w,'BAR'));
});
test('Kasa treaties before/after both invasion focuses preserve post-Barrad progression',()=>{
 for(const [id,ready,tree,next] of [['ZES_to_north','yrmthu','ZES_yrmthu_tree','ZES_post_barrad_yrmthu_tree'],['ZES_noblest_cause','altu','ZES_altu_kexa_tree','ZES_post_barrad_altu_kexa_tree']]) {
  for(const early of [true,false]) {
   const w=world();w.root='ZES';w.countries.ZES.tree=tree;
   if(early) {effect('HSM_BAR_dip_ZES_challenge',w,'ZES');w.countries.BAR.flags.add('HSM_BAR_dip_ZES_terms');effect('HSM_BAR_dip_ZES_accept',w);}
   run(body(focus[id],'completion_reward'),w,'ZES');
   if(!early) {w.countries.BAR.flags.add('HSM_BAR_dip_ZES_terms');effect('HSM_BAR_dip_ZES_accept',w);}
   assert.equal(w.countries.ZES.tree,next);assert.equal(w.declarations.length,0);
   assert(![...w.countries.ZES.flags].some(f=>f.endsWith('_conquered')));
  }
  const w=world();w.root='ZES';w.countries.ZES.tree=tree;
  run(body(focus[id],'completion_reward'),w,'ZES');effect('HSM_BAR_dip_ZES_refuse',w);
  run(options('hsm_bar_diplomacy.90')[0],w,'ZES');assert(w.countries.ZES.flags.has('ZES_'+ready+'_barrad_war'));
 }
});
test('Kasa occupation focuses bypass on settlement without occupation rewards',()=>{
 const w=world();w.root='ZES';w.countries.ZES.flags.add('HSM_BAR_dip_settled');
 for(const id of ['ZES_emergency_aid','ZES_secure_mountain_holds','ZES_cleanse_monsters','ZES_establish_havens','ZES_hang_them']){
  assert(cond(body(focus[id],'bypass'),w,'ZES'),id);
  assert(cond(body(focus[id],'allow_branch'),w,'ZES'),id);
 }
 run(body(focus.ZES_barrad_comission,'completion_reward'),w,'ZES');assert.equal(w.countries.ZES.pp,50);
});
test('Wittenland settlement bypasses integration focuses and allows canal',()=>{
 const w=world();w.countries.WIT.flags.add('HSM_BAR_dip_settled');w.countries.BAR.flags.add('HSM_BAR_WIT_agreement');w.countries.WIT.owned=new Set(['617','627']);
 for(const id of ['WIT_fate_of_barrad','WIT_barrad_question','WIT_integrate_barrad'])assert(cond(body(focus[id],'bypass'),w,'WIT'));
 assert(cond(body(focus.WIT_grand_griffking_canal,'available'),w,'WIT'));
});
test('Gryphus retains conquest goal after bounded warning; existing war unaffected',()=>{
 const w=world();w.root='GRU';run(body(native.GRU_claims,'remove_effect'),w,'GRU');
 assert(w.queue.some(e=>e.id==='hsm_bar_diplomacy.40'));assert(!w.countries.GRU.goals.has('BAR'));
 run(body(events['hsm_bar_diplomacy.41'],'immediate'),w,'GRU');assert(w.countries.GRU.goals.has('BAR'));
 const x=world();x.root='GRU';x.countries.BAR.wars.add('GRU');run(body(native.GRU_claims,'remove_effect'),x,'GRU');assert.equal(x.queue.length,0);assert(x.countries.BAR.wars.has('GRU'));
});
test('initialization imports outstanding claims and in-flight native timers',()=>{
 const w=world();w.countries.WIT.goals.add('BAR');w.countries.ZES.decisions.add('ZES_diplomacy_barrad_attack');w.countries.OLV.decisions.add('OLV_coqnuer_BAR');
 effect('HSM_BAR_dip_initialize',w);
 for(const t of ['WIT','ZES','OLV'])assert(w.countries.BAR.flags.has('HSM_BAR_dip_'+t+'_pending'));
 for(const t of ['ZES','OLV'])assert(w.countries.BAR.flags.has('HSM_BAR_dip_'+t+'_timer'));
 assert(w.countries.WIT.goals.has('BAR'),'no blanket removal of pre-existing goals');
 assert.equal(w.queue.length,3);effect('HSM_BAR_dip_initialize',w);assert.equal(w.queue.length,3);
});
test('mission timeout refuses, renunciation reopens talks, war invalidates treaties',()=>{
 for(const t of ['WIT','ZES','OLV']) {
  const w=world();effect('HSM_BAR_dip_'+t+'_challenge',w,t);
  assert.equal(val(decisions['HSM_BAR_dip_'+t+'_deadline'],'days_mission_timeout'),'45');
  run(body(decisions['HSM_BAR_dip_'+t+'_deadline'],'timeout_effect'),w,'BAR');
  assert(w.queue.some(e=>e.id==='hsm_bar_diplomacy.90'));
  const x=world();effect('HSM_BAR_dip_'+t+'_challenge',x,t);x.countries.BAR.flags.add('HSM_BAR_dip_'+t+'_terms');effect('HSM_BAR_dip_'+t+'_accept',x);
  run(body(decisions['HSM_BAR_dip_'+t+'_renounce'],'complete_effect'),x,'BAR');
  assert(!x.countries.BAR.flags.has('HSM_BAR_'+t+'_agreement'));assert(!x.countries.BAR.pacts.has(t));assert(x.countries.BAR.flags.has('HSM_BAR_dip_'+t+'_pending'));
  const y=world();y.countries.BAR.flags.add('HSM_BAR_'+t+'_agreement');y.countries.BAR.wars.add(t);
  effect('HSM_BAR_dip_daily_pulse',y);assert(!y.countries.BAR.flags.has('HSM_BAR_'+t+'_agreement'));assert(y.countries.BAR.wars.has(t));
 }
});
test('refusal keeps a war goal when immediate declaration is blocked, withdrawal costs authority',()=>{
 for(const t of ['WIT','ZES','OLV']) {
  const w=world();effect('HSM_BAR_dip_'+t+'_challenge',w,t);effect('HSM_BAR_dip_'+t+'_refuse',w);
  w.countries[t].canWar=false;run(options('hsm_bar_diplomacy.90')[0],w,t);
  assert(w.countries[t].goals.has('BAR'));assert.equal(w.declarations.length,0);
  run(options('hsm_bar_diplomacy.90')[1],w,t);
  assert(!w.countries[t].goals.has('BAR'));assert.equal(w.countries[t].pp,-50);
  assert(w.countries.BAR.flags.has('HSM_BAR_dip_'+t+'_cooldown'));assert(!w.countries.BAR.flags.has('HSM_BAR_'+t+'_agreement'));
 }
});
test('legacy Kasa direct-war focus effects remain intact for old Barrad',()=>{
 for(const id of ['ZES_to_north','ZES_noblest_cause']) {
  const w=world();w.root='ZES';w.countries.BAR.flags.clear();w.countries.BAR.government='fascism';
  run(body(focus[id],'completion_reward'),w,'ZES');assert(w.countries.ZES.wars.has('BAR'),id);
 }
});
test('only new-route Wittenland event options redirect; all queued responses preserve the new tree',()=>{
 const all=parse(read('mod/HoISubmod/events/Wittenland.txt'));
 for(const id of ['wittenland.65','wittenland.80','wittenland.81','wittenland.82']){
  const e=all.find(n=>n.key==='country_event'&&val(n.children,'id')===id);
  const opts=e.children.filter(n=>n.key==='option');
  const w=world();w.countries.BAR.tree='HSM_new_route';w.root=id==='wittenland.80'?'BAR':id==='wittenland.65'?'ZES':'WIT';w.from='WIT';
  run(opts[0].children,w,w.root);assert.equal(w.countries.BAR.tree,'HSM_new_route');
  assert(w.countries.BAR.flags.has('HSM_BAR_dip_'+(id==='wittenland.65'?'ZES':'WIT')+'_pending'));
 }
});
assert.equal(passed,38,'Expected the original 38 deterministic validation groups');
console.log('RESULT '+passed+' validation groups passed; deterministic script checks, not an HOI4 runtime test.');
'@
$javascript | & $nodeRuntime.Source - $root $GameRoot
if ($LASTEXITCODE -ne 0) {
    throw "Barrad diplomacy validation failed (Node exit code $LASTEXITCODE)."
}
