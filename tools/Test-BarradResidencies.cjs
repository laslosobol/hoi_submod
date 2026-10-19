"use strict";
// node tools/Test-BarradResidencies.cjs [--native]
// Executes production scripts with bounded fixtures; not a game-engine playtest.
const fs=require("node:fs"),path=require("node:path"),assert=require("node:assert/strict");
const {parse,prop}=require("./Test-BarradArchiveSkin.cjs");
const mod=path.resolve(__dirname,"../mod/HoISubmod"),p="HSM_BAR_residencies_";
const raw=f=>fs.readFileSync(path.join(mod,f),"utf8"),read=f=>parse(raw(f));
const walk=ns=>ns.flatMap(n=>[n,...(Array.isArray(n.value)?walk(n.value):[])]);
function dict(ns){const out={};for(const n of ns){assert(!Object.hasOwn(out,n.key),"Duplicate "+n.key);out[n.key]=n.value;}return out;}
const triggers=dict(read("common/scripted_triggers/HSM_BAR_residencies.txt"));
const effects=dict(read("common/scripted_effects/HSM_BAR_residencies.txt"));
const groups=read("common/decisions/HSM_BAR_residencies.txt"),decisions=dict(groups.flatMap(n=>n.value));
const eventNodes=read("events/HSM_BAR_residencies.txt");
const events=dict(eventNodes.filter(n=>n.key==="country_event").map(n=>({key:prop(n.value,"id"),value:n.value})));
const modifier=prop(read("common/dynamic_modifiers/HSM_BAR_residencies.txt"),p+"methods");
const actions=prop(read("common/on_actions/HSM_BAR_residencies.txt"),"on_actions");
const dissolve=prop(read("common/scripted_effects/HSM_BAR_core_effects.txt"),"HSM_BAR_dissolve_institutions");
const dissolveHooks=dissolve.filter(n=>n.key==="if"&&walk([n]).some(c=>c.key===p+"teardown"));
const reports=["equus","griffonia","north","riverlands","zebrica","comparison","contact","exchange","aftermath","review"];
const jobs={equus:["equus",25,28],griffonia:["griffonia",30,28],north:["north",30,35],riverlands:["riverlands",25,28],zebrica:["zebrica",35,28],comparison:["comparison",40,42],reply:["contact",40,28],papers:["contact",50,35],exchange:["exchange",50,35],aftermath:["aftermath",35,28],review:["review",25,21]};
const stats={attrition:"attrition",recon:"recon_factor",dig_in:"dig_in_speed_factor",supply:"supply_consumption_factor",network:"intel_network_gain_factor",capture:"own_operative_capture_chance_factor",cost:"operation_cost",outcome:"operation_outcome",defence:"intelligence_agency_defense",upkeep:"political_power_gain"};
const zero=()=>Object.fromEntries(Object.keys(stats).map(k=>[k,0]));
function world(lar=true,retained=true){
 const w={tag:"BAR",original:"BAR",exists:true,cap:false,subject:false,owner:"BAR",controller:"BAR",now:0,lar,flags:new Map(),vars:{},pp:1000,events:[],coupons:[],modifiers:new Set(),cache:{},installs:0,tooltips:[],cases:{core:624,known:[],studied:[],custody:[]}};
 for(const f of ["HSM_BAR_active","HSM_BAR_directorate","HSM_BAR_service_founded","HSM_BAR_core_6_done","HSM_BAR_cult_network_broken"])setflag(w,f);
 if(retained)setflag(w,"HSM_BAR_cult_channel_retained");
 for(const [i,r]of reports.slice(0,5).entries()){setflag(w,"HSM_BAR_region_"+r+"_open");setflag(w,"HSM_BAR_story_"+(20+i)+"_done");}
 return w;
}
function setflag(w,f,days){w.flags.set(f,{at:w.now,until:days===undefined?Infinity:w.now+Number(days)});}
function has(w,f){return w.flags.has(f)&&w.flags.get(f).until>w.now;}
function condition(ns,w){return ns.every(({key:k,value:v})=>{
 if(k==="AND")return condition(v,w);if(k==="OR")return v.some(n=>condition([n],w));if(k==="NOT")return !v.some(n=>condition([n],w));
 if(k==="custom_trigger_tooltip")return condition(v.filter(n=>n.key!=="tooltip"),w);
 if(k==="has_country_flag"){
  if(typeof v==="string")return has(w,v);
  const f=prop(v,"flag"),d=v.find(n=>n.key==="days");assert.equal(d.op,"<");return has(w,f)&&w.now-w.flags.get(f).at<Number(d.value);
 }
 if(k==="tag")return w.tag===v;if(k==="original_tag")return w.original===v;
 if(k==="exists")return w.exists===(v==="yes");if(k==="has_capitulated")return w.cap===(v==="yes");if(k==="is_subject")return w.subject===(v==="yes");
 if(k==="owns_state"){assert.equal(v,"624");return w.owner===w.tag;}if(k==="controls_state"){assert.equal(v,"624");return w.controller===w.tag;}
 if(k==="has_dlc"){assert.equal(v,"La Resistance");return w.lar;}if(k==="has_dynamic_modifier")return w.modifiers.has(v);
 if(triggers[k])return condition(triggers[k],w)===(v==="yes");
 throw Error("Unsupported trigger "+k);
});}
function cache(w){w.cache=Object.fromEntries(Object.keys(stats).map(k=>[k,w.vars[p+k]||0]));}
function run(ns,w){for(let i=0;i<ns.length;i++){
 const {key:k,value:v}=ns[i];
 if(k==="if"){
  let taken=false;
  do{const n=ns[i],yes=n.key==="else"||condition(prop(n.value,"limit"),w);if(!taken&&yes){run(n.value.filter(c=>c.key!=="limit"),w);taken=true;}if(!["else","else_if"].includes(ns[i+1]?.key))break;i++;}while(true);
 }else if(k==="hidden_effect"||k==="ROOT")run(v,w);
 else if(k==="set_country_flag"){if(typeof v==="string")setflag(w,v);else setflag(w,prop(v,"flag"),prop(v,"days"));}
 else if(k==="clr_country_flag")w.flags.delete(v);
 else if(k==="custom_effect_tooltip")w.tooltips.push(v);
 else if(k==="set_variable"||k==="add_to_variable"){assert.equal(v.length,1);assert(v[0].key.startsWith(p));const value=Number(v[0].value);assert(Number.isFinite(value));w.vars[v[0].key]=(k==="set_variable"?0:w.vars[v[0].key]||0)+value;}
 else if(k==="add_dynamic_modifier"){assert.equal(prop(v,"modifier"),p+"methods");assert(condition(prop(modifier,"enable"),w));w.modifiers.add(p+"methods");w.installs++;cache(w);}
 else if(k==="remove_dynamic_modifier"){assert.equal(prop(v,"modifier"),p+"methods");w.modifiers.delete(p+"methods");w.cache={};}
 else if(k==="force_update_dynamic_modifier"){if(w.modifiers.has(p+"methods"))cache(w);}
 else if(k==="country_event"){assert.equal(v.length,1,"No delayed reward event");const id=prop(v,"id");assert(events[id]);assert(condition(prop(events[id],"trigger"),w));w.events.push(id);}
 else if(k==="add_tech_bonus"){assert.equal(Number(prop(v,"bonus")),.5);assert.equal(prop(v,"uses"),"1");w.coupons.push({name:prop(v,"name"),category:prop(v,"category"),bonus:.5,uses:1});}
 else if(effects[k]){assert.equal(v,"yes");run(effects[k],w);}
 else throw Error("Unsupported effect "+k);
}}
const effect=(name,w)=>{assert(effects[p+name],name);run(effects[p+name],w);};
const can=(id,w)=>condition(prop(decisions[p+id],"available"),w);
function activate(id,w){assert(can(id,w),"Cannot start "+id);const d=decisions[p+id],cost=Number(prop(d,"cost"));assert(w.pp>=cost);w.pp-=cost;run(prop(d,"complete_effect"),w);}
function finish(id,w){w.now+=jobs[id][2];run(prop(decisions[p+id],"remove_effect"),w);}
function answer(report,choice,w){const e=events["HSM_BAR_residencies."+(reports.indexOf(report)+1)],opt=e.filter(n=>n.key==="option")[choice].value;run(opt.filter(n=>!["name","ai_chance"].includes(n.key)),w);}
function dojob(id,choice,w){activate(id,w);finish(id,w);answer(jobs[id][0],choice,w);}
function sameStats(w,wanted){for(const k of Object.keys(stats))assert(Math.abs((w.vars[p+k]||0)-wanted[k])<1e-9,`${k}: ${w.vars[p+k]} != ${wanted[k]}`);if(w.modifiers.has(p+"methods"))for(const k of Object.keys(stats))assert(Math.abs(w.cache[k]-wanted[k])<1e-9,"Cached "+k);}
const snapshot=w=>{const c=structuredClone(w);delete c.tooltips;return c;};
let passed=0,failed=0;
function scenario(name,fn){try{fn();passed++;console.log("PASS: "+name);}catch(e){failed++;console.error("FAIL: "+name+"\n"+e.stack);}}

scenario("eleven priced timed assignments, ten scenes, retryable cancellation, no world-conquest gates",()=>{
 assert.deepEqual(Object.keys(decisions).map(k=>k.slice(p.length)),Object.keys(jobs));assert.equal(Object.keys(events).length,10);
 for(const [id,[,cost,days]]of Object.entries(jobs)){const b=decisions[p+id];assert.equal(Number(prop(b,"cost")),cost);assert.equal(Number(prop(b,"days_remove")),days);assert.equal(prop(b,"fire_only_once"),"no");assert.equal(prop(b,"days_re_enable"),"1");assert(prop(b,"cancel_effect"));}
 assert(!JSON.stringify(triggers).match(/has_war_with|has_government|has_country_leader|global\.|has_completed_focus/));
});
scenario("original core6 choices call begin without modifying their previous rewards",()=>{
 const core=read("events/HSM_BAR_core.txt").find(n=>n.key==="country_event"&&prop(n.value,"id")==="hsm_bar_core.6").value;
 const options=core.filter(n=>n.key==="option");assert.equal(options.length,2);
 for(const o of options){const all=walk(o.value);assert.equal(all.filter(n=>n.key===p+"begin").length,1);assert(all.some(n=>n.key==="set_country_flag"&&n.value==="HSM_BAR_cult_network_broken"));}
 assert(walk(options[1].value).some(n=>n.key==="set_country_flag"&&n.value==="HSM_BAR_cult_channel_retained"));
 for(const retained of [false,true]){const w=world(true,retained);effect("begin",w);assert(has(w,p+"started"));assert.equal(can("reply",w),retained);assert.equal(can("papers",w),!retained);const before=snapshot(w);effect("begin",w);assert.deepEqual(snapshot(w),before);}
 const w=world();w.flags.delete("HSM_BAR_core_6_done");effect("begin",w);assert(!has(w,p+"started"));
});
for(const [i,id]of reports.slice(0,5).entries())scenario(`${id}: region and its original conversation are required, not unrelated world states`,()=>{
 const w=world();assert(can(id,w));w.flags.delete("HSM_BAR_region_"+id+"_open");assert(!can(id,w));setflag(w,"HSM_BAR_region_"+id+"_open");w.flags.delete("HSM_BAR_story_"+(20+i)+"_done");assert(!can(id,w));
});
for(const id of reports.slice(0,5))scenario(`${id}: revoked residency cancels a paid investigation and restored access permits a fresh attempt`,()=>{
 const w=world();activate(id,w);w.flags.delete("HSM_BAR_region_"+id+"_open");assert(condition(prop(decisions[p+id],"cancel_trigger"),w));
 run(prop(decisions[p+id],"cancel_effect"),w);finish(id,w);assert(!has(w,p+id+"_ready"));assert.equal(w.coupons.length,0);assert.equal(w.pp,1000-jobs[id][1]);
 setflag(w,"HSM_BAR_region_"+id+"_open");assert(can(id,w));activate(id,w);finish(id,w);assert(has(w,p+id+"_ready"));assert.equal(w.pp,1000-2*jobs[id][1]);
});
for(const id of Object.keys(jobs))scenario(`${id}: exact duration, start replay, no early reward, cancellation and paid retry`,()=>{
 const w=world();effect("begin",w);for(const r of ["zebrica","contact","exchange","aftermath"])setflag(w,p+r+"_done");
 w.flags.delete(p+jobs[id][0]+"_done");if(id==="papers")w.flags.delete("HSM_BAR_cult_channel_retained");
 activate(id,w);assert(has(w,p+"initialized"));const charged=w.pp,clock=w.flags.get(p+id+"_running").at;effect(id+"_start",w);assert.equal(w.flags.get(p+id+"_running").at,clock);assert.equal(w.pp,charged);
 w.now+=jobs[id][2]-1;effect(id+"_finish",w);assert(!has(w,p+jobs[id][0]+"_ready"));assert.equal(w.coupons.length,0);
 if(id==="review")w.now+=180;
 activate(id,w);run(prop(decisions[p+id],"cancel_effect"),w);finish(id,w);assert(!has(w,p+jobs[id][0]+"_ready"));assert.equal(w.coupons.length,0);assert.equal(w.pp,1000-2*jobs[id][1]);
 if(id==="review")w.now+=180;
 activate(id,w);finish(id,w);assert(has(w,p+jobs[id][0]+"_ready"));assert.equal(w.pp,1000-3*jobs[id][1]);const eventsBefore=w.events.length;effect(id+"_finish",w);assert.equal(w.events.length,eventsBefore);
});
const coupons={equus:"hospital_tech",griffonia:"industry",north:"electronics",riverlands:"logistics_tech"};
for(const lar of [false,true])for(const id of Object.keys(coupons))for(const choice of [0,1])scenario(`${id}, ${lar?"LaR":"no LaR"}, option ${choice}: exact once-only scientific or practical result`,()=>{
 const w=world(lar),beforeCases=structuredClone(w.cases);dojob(id,choice,w);const want=zero();
 if(!choice){assert.equal(w.coupons.length,1);assert.equal(w.coupons[0].category,coupons[id]);}
 else{assert.equal(w.coupons.length,0);if(id==="equus")want.attrition=-.01;if(id==="griffonia")want[lar?"cost":"recon"]=lar?-.03:.005;if(id==="north")want.recon=.01;if(id==="riverlands")want.dig_in=.05;}
 sameStats(w,want);const before=snapshot(w);answer(id,1-choice,w);answer(id,choice,w);effect("pulse",w);assert.deepEqual(snapshot(w),before);assert.deepEqual(w.cases,beforeCases);
});
for(const lar of [false,true])for(const source of [0,1])for(const choice of [0,1])scenario(`Zebrica ${lar?"LaR":"no LaR"}, source ${source}, result ${choice}: two stages with genuinely different findings`,()=>{
 const w=world(lar);assert(!can("comparison",w));dojob("zebrica",source,w);assert.equal(w.coupons.length,0);assert(!w.modifiers.size);dojob("comparison",choice,w);
 const want=zero();if(!choice){assert.equal(w.coupons.length,1);assert.equal(w.coupons[0].category,source?"electronics":"logistics_tech");}else if(!source)want.supply=-.02;else want[lar?"outcome":"recon"]=lar?.03:.01;
 sameStats(w,want);const descs=events["HSM_BAR_residencies.6"].filter(n=>n.key==="desc"&&condition(prop(n.value,"trigger"),w));assert.equal(descs.length,1);assert.equal(prop(descs[0].value,"text"),"HSM_BAR_residencies.6."+(source?"broker":"listeners"));
});
for(const lar of [false,true])for(const retained of [false,true])for(let mask=0;mask<8;mask++)scenario(`antagonist ${lar?"LaR":"no LaR"}, ${retained?"retained":"closed"}, choices ${mask}: continuation, cooldowns, replacement and repeat review`,()=>{
 const w=world(lar,retained);effect("pulse",w);const c=mask&1,e=(mask>>1)&1,a=(mask>>2)&1;
 dojob(retained?"reply":"papers",c,w);let want=zero();
 if(c){if(lar){want.network=retained?.05:.025;want.capture=retained?.05:0;}else want.recon=.01;}else want[lar?"defence":"recon"]=lar?1:.005;
 sameStats(w,want);assert(!can("exchange",w));w.now+=29;assert(!can("exchange",w));w.now++;assert(can("exchange",w));
 dojob("exchange",e,w);if(e){want.upkeep=-.02;want[lar?"outcome":"recon"]+=lar?.05:.005;}else want.supply=-.01;sameStats(w,want);
 assert(!can("aftermath",w));w.now+=60;dojob("aftermath",a,w);want=zero();if(a){want.upkeep=-.03;if(lar){want.network=.05;want.outcome=.05;}else want.recon=.02;}else{want.supply=-.01;want[lar?"defence":"recon"]=lar?1:.01;}sameStats(w,want);assert.equal(w.vars[p+"capture"],0);
 assert(!can("review",w));w.now+=179;assert(!can("review",w));w.now++;assert(can("review",w));
 for(let cycle=0;cycle<3;cycle++){
  dojob("review",cycle%2,w);assert.equal(w.coupons.length,0);want=zero();if(cycle%2){want.upkeep=-.03;if(lar){want.network=.05;want.outcome=.05;}else want.recon=.02;}else{want.supply=-.01;want[lar?"defence":"recon"]=lar?1:.01;}sameStats(w,want);
  const before=snapshot(w);answer("review",1-cycle%2,w);for(let j=0;j<100;j++)effect("pulse",w);assert.deepEqual(snapshot(w),before);w.now+=180;
 }
 assert.equal(w.pp,1000-(retained?40:50)-50-35-3*25);assert.equal(w.installs,1);assert.equal(has(w,"HSM_BAR_cult_channel_retained"),retained);
});
const revoked=[
 ["foreign tag",w=>w.tag="WIT"],["foreign origin",w=>w.original="WIT"],["absent",w=>w.exists=false],
 ["inactive",w=>w.flags.delete("HSM_BAR_active")],["no Directorate",w=>w.flags.delete("HSM_BAR_directorate")],["no Service",w=>w.flags.delete("HSM_BAR_service_founded")],["College",w=>setflag(w,"HSM_BAR_collegium")],
 ["capitulated",w=>w.cap=true],["subject",w=>w.subject=true],["not owner",w=>w.owner="WIT"],["not controller",w=>w.controller="WIT"]
];
for(const[name,mutate]of revoked)scenario(`${name}: running work cancels, pending choices cannot reward, ready findings survive suspension`,()=>{
 const w=world();dojob("equus",1,w);activate("north",w);finish("north",w);activate("riverlands",w);const couponsBefore=w.coupons.length,flagsBefore=[...w.flags.keys()].filter(f=>f.endsWith("_done")||f.endsWith("_method"));assert(condition(prop(modifier,"enable"),w));assert(!condition(prop(modifier,"remove_trigger"),w));mutate(w);
 assert(!condition(prop(modifier,"enable"),w));assert(condition(prop(modifier,"remove_trigger"),w));
 assert(condition(prop(decisions[p+"riverlands"],"cancel_trigger"),w));run(prop(decisions[p+"riverlands"],"cancel_effect"),w);finish("riverlands",w);answer("north",0,w);assert.equal(w.coupons.length,couponsBefore);assert(!has(w,p+"riverlands_ready"));assert(has(w,p+"north_ready"));assert(!has(w,p+"north_done"));
 effect("pulse",w);assert(!w.modifiers.size);sameStats(w,zero());for(const f of flagsBefore)assert(has(w,f));for(const id of Object.keys(jobs))assert(!can(id,w));
});
for(const[name,mutate]of revoked)scenario(`${name}: all eleven assignments reject invalid starts and late completion callbacks`,()=>{
 for(const id of Object.keys(jobs)){
  const w=world(true,id!=="papers");effect("begin",w);
  for(const r of ["zebrica","contact","exchange","aftermath"])setflag(w,p+r+"_done");
  w.flags.delete(p+jobs[id][0]+"_done");
  const denied=structuredClone(w);mutate(denied);const before=snapshot(denied);
  assert(!can(id,denied));effect(id+"_start",denied);assert.deepEqual(snapshot(denied),before);assert(!has(denied,p+"initialized"));
  activate(id,w);mutate(w);assert(condition(prop(decisions[p+id],"cancel_trigger"),w));finish(id,w);
  assert(!has(w,p+id+"_running"));assert(!has(w,p+jobs[id][0]+"_ready"));assert.equal(w.coupons.length,0);assert.equal(w.events.length,0);assert.equal(w.pp,1000-jobs[id][1]);
 }
});
scenario("core teardown is flag-guarded, follows the MTC-first boundary, and precedes route clearing",()=>{
 assert.equal(dissolveHooks.length,1);assert.equal(dissolve[0].key,"if");assert(walk([dissolve[0]]).some(n=>n.key==="HSM_BAR_mtk_projects_teardown"));
 assert(dissolve.indexOf(dissolveHooks[0])<dissolve.findIndex(n=>n.key==="clr_country_flag"&&n.value==="HSM_BAR_active"));
 assert.deepEqual(walk(prop(dissolveHooks[0].value,"limit")).filter(n=>n.key==="has_country_flag").map(n=>n.value),[p+"initialized",p+"started"]);
 const w=world(),before=snapshot(w);run(dissolveHooks,w);assert.deepEqual(snapshot(w),before,"No residency writes before initialization");
 assert.equal(prop(modifier,"icon"),"GFX_idea_HSM_BAR_dir_world");
});
for(const state of ["running","report","method","research"])scenario(`core dissolution before the convoy ending: ${state} lifecycle and replay safety`,()=>{
 const w=world();w.flags.delete("HSM_BAR_core_6_done");w.flags.delete("HSM_BAR_cult_network_broken");
 activate("equus",w);if(state!=="running")finish("equus",w);if(state==="method"||state==="research")answer("equus",state==="method"?1:0,w);
 assert(!has(w,p+"started"));assert(has(w,p+"initialized"));
 const before=structuredClone(w),originalCases=structuredClone(w.cases);w.modifiers.add("unrelated_modifier");
 run(dissolveHooks,w);run(dissolve.filter(n=>n.key==="clr_country_flag"),w);
 assert(!w.modifiers.has(p+"methods"));assert(w.modifiers.has("unrelated_modifier"));sameStats(w,zero());
 for(const id of Object.keys(jobs))assert(!has(w,p+id+"_running"));for(const r of reports)assert(!has(w,p+r+"_pending"));
 for(const suffix of ["equus_ready","equus_done","equus_method"])assert.equal(has(w,p+suffix),has(before,p+suffix));
 assert.deepEqual(w.coupons,before.coupons);assert.deepEqual(w.cases,originalCases);
 const after=snapshot(w);run(dissolveHooks,w);effect("pulse",w);answer("equus",0,w);answer("equus",1,w);effect("equus_finish",w);assert.deepEqual(snapshot(w),after);
 for(const id of Object.keys(jobs))assert(!can(id,w));assert(!condition(prop(modifier,"enable"),w));assert(condition(prop(modifier,"remove_trigger"),w));
});
scenario("legacy antagonist marker alone still invokes immediate teardown",()=>{
 const w=world();effect("begin",w);assert(has(w,p+"started"));assert(!has(w,p+"initialized"));
 setflag(w,p+"contact_done");setflag(w,p+"contact_follow");effect("refresh",w);assert(w.modifiers.has(p+"methods"));
 run(dissolveHooks,w);assert(!w.modifiers.size);sameStats(w,zero());assert(has(w,p+"contact_done"));assert(has(w,p+"contact_follow"));assert(has(w,"HSM_BAR_cult_channel_retained"));
});
scenario("resuming after capitulation reissues completed report but never resumes an aborted field job",()=>{
 const w=world();activate("north",w);finish("north",w);activate("equus",w);w.cap=true;effect("pulse",w);const count=w.events.length;w.cap=false;effect("pulse",w);assert.equal(w.events.length,count+1);assert(has(w,p+"north_pending"));assert(!has(w,p+"equus_running"));finish("equus",w);assert(!has(w,p+"equus_ready"));answer("north",0,w);assert.equal(w.coupons.length,1);
});
scenario("preserved regional commercial evidence changes the second consignment's narrative without gating it",()=>{
 for(const source of ["none","museum","broker"]){const w=world();setflag(w,p+"exchange_ready");setflag(w,p+"exchange_pending");if(source==="museum")setflag(w,p+"griffonia_method");if(source==="broker"){setflag(w,p+"comparison_done");setflag(w,p+"zebrica_broker");}const ds=events["HSM_BAR_residencies.8"].filter(n=>n.key==="desc"&&condition(prop(n.value,"trigger"),w));assert.equal(ds.length,1);assert.equal(prop(ds[0].value,"text"),"HSM_BAR_residencies.8."+(source==="none"?"independent":"linked"));}
});
for(const lar of [false,true])for(const source of [0,1])for(const watch of [0,1])scenario(`combined regional methods and final ${watch?"watch":"protection"}, ${lar?"LaR":"no LaR"}, Zebrican source ${source}: independent bounded contributions`,()=>{
 const w=world(lar);effect("begin",w);
 for(const id of ["equus","griffonia","north","riverlands"])dojob(id,1,w);
 dojob("zebrica",source,w);dojob("comparison",1,w);dojob("reply",1,w);w.now+=30;dojob("exchange",1,w);w.now+=60;dojob("aftermath",watch,w);
 const want={...zero(),attrition:-.01,recon:.01,dig_in:.05};
 if(lar)want.cost=-.03;else want.recon+=.005;
 if(source){if(lar)want.outcome+=.03;else want.recon+=.01;}else want.supply-=.02;
 if(watch){want.upkeep=-.03;if(lar){want.network=.05;want.outcome+=.05;}else want.recon+=.02;}
 else{want.supply-=.01;if(lar)want.defence=1;else want.recon+=.01;}
 sameStats(w,want);assert.equal(w.coupons.length,0);assert.equal(w.vars[p+"capture"],0);assert.equal(w.installs,1);
 const flags=structuredClone(w.flags);effect("teardown",w);assert(!w.modifiers.size);effect("refresh",w);sameStats(w,want);assert.deepEqual(w.flags,flags);
});
scenario("new flags are read; only component flags/variables are written; no case, archive, corpse, ruler or suppression awards",()=>{
 const script=[...Object.values(effects).flat(),...Object.values(triggers).flat(),...eventNodes,...groups];const all=walk(script);
 const written=new Set(all.filter(n=>n.key==="set_country_flag").map(n=>typeof n.value==="string"?n.value:prop(n.value,"flag")));
 const readFlags=new Set([...all,...walk(dissolveHooks)].filter(n=>n.key==="has_country_flag").map(n=>typeof n.value==="string"?n.value:prop(n.value,"flag")));
 for(const f of written){assert(f.startsWith(p));assert(readFlags.has(f),"Orphan flag "+f);}
 assert(readFlags.has("HSM_BAR_cult_channel_retained"));
 const forbidden=["add_state_core","set_country_leader","retire_character","create_wargoal","add_political_power","add_stability","set_global_flag","transfer_state"];
 assert(!all.some(n=>forbidden.includes(n.key)));
 for(const n of all.filter(n=>n.key==="set_variable"||n.key==="add_to_variable"))assert(n.value[0].key.startsWith(p));
 assert(!all.some(n=>n.key==="set_country_flag"&&typeof n.value==="string"&&/HSM_BAR_(study_|case_|project_)/.test(n.value)));
});
scenario("daily and defeat hooks are present and limited to the component",()=>{
 assert.equal(prop(prop(actions,"on_daily_BAR"),"effect")[0].key,p+"pulse");const w=world();dojob("equus",1,w);run(prop(prop(actions,"on_capitulation"),"effect"),w);assert(!w.modifiers.size);assert(has(w,p+"equus_done"));
});
const loc={};
scenario("EN/RU BOM, key parity, all event/decision/tooltip references and no mixed-language fragments",()=>{
 for(const language of ["english","russian"]){const text=raw(`localisation/${language}/HSM_BAR_residencies_l_${language}.yml`);assert.equal(text.charCodeAt(0),0xFEFF);const pairs=[...text.matchAll(/^ ([\w.]+):0 "((?:\\.|[^"\\])*)"\s*$/gm)].map(m=>[m[1],m[2]]);assert.equal(pairs.length,new Set(pairs.map(a=>a[0])).size);loc[language]=Object.fromEntries(pairs);
  for(const id of Object.keys(decisions)){assert(loc[language][id]);assert(loc[language][id+"_desc"]);}
  for(const n of walk([...eventNodes,...Object.values(effects).flat(),...Object.values(triggers).flat()]).filter(n=>["name","title","desc","text","tooltip","custom_effect_tooltip"].includes(n.key)&&typeof n.value==="string"&&n.value.startsWith("HSM_BAR_residencies")))assert(loc[language][n.value],"Missing "+language+" "+n.value);
  for(const[k,v]of pairs)if(/\.\d+\.(d|listeners|broker|retained|closed|linked|independent|exposed|protected)$/.test(k)){assert(v.split(/\s+/).length>=85,k);assert.equal(v.split("\\n\\n").length,3,k);}
  if(language==="russian")assert(!/[іїєґ]/i.test(text),"Ukrainian fragment in Russian");
 }
 assert.deepEqual(Object.keys(loc.english).sort(),Object.keys(loc.russian).sort());
});
scenario("conditional tooltips expose only the actual source/DLC result and mutate no game state",()=>{
 for(const lar of [false,true])for(const retained of [false,true])for(const listeners of [false,true]){
  const w=world(lar,retained);if(listeners)setflag(w,p+"zebrica_listeners");else setflag(w,p+"zebrica_broker");
  for(const r of reports)for(const o of ["a","b"]){w.tooltips=[];const before=snapshot(w);effect(r+"_tooltip_"+o,w);assert.deepEqual(snapshot(w),before);for(const key of w.tooltips)assert(loc.english[key]&&loc.russian[key],key);}
  w.tooltips=[];effect("comparison_tooltip_a",w);assert.deepEqual(w.tooltips,[p+"comparison_a_"+(listeners?"log":"ele")+"_tt"]);
  w.tooltips=[];effect("contact_tooltip_b",w);assert.equal(w.tooltips[1],p+"contact_b_"+(lar?(retained?"retained":"closed"):"legacy")+"_tt");
 }
});
if(process.argv.includes("--native"))scenario("installed engine documents modifiers, timer syntax and technology categories",()=>{
 const game=process.env.HOI4_GAME_ROOT||"C:/shit/Steam/steamapps/common/Hearts of Iron IV",eaw=process.env.EAW_ROOT||"C:/shit/Steam/steamapps/workshop/content/394360/1826643372";
 const text=fs.readFileSync(path.join(game,"documentation/modifiers_documentation.md"),"utf8");for(const k of Object.values(stats))assert(new RegExp("^## "+k+"\\r?$","m").test(text),k);
 const tags=fs.readFileSync(path.join(eaw,"common/technology_tags/00_technology.txt"),"utf8");for(const k of ["hospital_tech","logistics_tech","industry","electronics"])assert(new RegExp("\\b"+k+"\\b").test(tags));
 const triggerDoc=fs.readFileSync(path.join(game,"documentation/triggers_documentation.md"),"utf8");assert(triggerDoc.includes("days > <int>"));assert(triggerDoc.includes("## has_country_flag"));
 const nativeFlags=fs.readFileSync(path.join(game,"common/scripted_triggers/BUL_scripted_triggers.txt"),"utf8");assert(/has_country_flag\s*=\s*\{[^}]*days\s*</.test(nativeFlags),"Native less-than flag-age comparison");
 const canon=fs.readFileSync(path.join(eaw,"localisation/english/country_GRI_l_english.yml"),"utf8");assert(canon.includes("imperial.128.d:"));assert(canon.includes("Maarites"));
});
console.log(`Barrad residencies: ${passed} passed, ${failed} failed.`);process.exitCode=failed?1:0;
