"use strict";
// Strict adapter fixtures. Existing case/outcome suites own the original research payloads.
const fs=require("node:fs"), path=require("node:path"), assert=require("node:assert/strict");
const B=require("./Build-BarradServiceGui.cjs"), F=require("./Test-BarradCases.cjs");
const {parse,prop,mod,P,actions}=B;
const read=f=>parse(fs.readFileSync(path.join(mod,f),"utf8"),true);
const dict=nodes=>Object.fromEntries(nodes.map(n=>[n.key,n.value]));
const effects=dict(read("common/scripted_effects/HSM_BAR_service_gui.txt"));
const triggers=dict(read("common/scripted_triggers/HSM_BAR_service_gui.txt"));
const missions=dict(prop(read("common/decisions/HSM_BAR_service_gui.txt"),P+"timers"));
const gui=prop(prop(read("common/scripted_guis/HSM_BAR_service_gui.txt"),"scripted_gui"),P+"window");
const clicks=prop(gui,"effects"), gates=prop(gui,"triggers");
const walk=ns=>ns.flatMap(n=>[n,...Array.isArray(n.value)?walk(n.value):[]]);
let passed=0,failed=0;
function scenario(name,fn){try{fn();passed++;console.log("PASS: "+name);}catch(e){failed++;console.error("FAIL: "+name+"\n"+e.stack);}}
function world(dlc=false){const w=F.world(dlc);w.day=0;Object.assign(w.root,{ai:false,subject:false,arrays:{},flagDays:{},missions:new Set(),factories:4,paid:0});w.root.flags.add("HSM_BAR_region_local_open");return w;}
function number(v,s){if(Number.isFinite(Number(v)))return Number(v);if(v.endsWith("^num"))return(s.arrays[v.slice(0,-4)]||[]).length;assert(/^HSM_BAR_\w+$/.test(v),"Unsupported value "+v);return s.vars[v]||0;}
function test(nodes,w){return nodes.every(n=>{const v=n.value,s=w.root;
 if(["AND","hidden_trigger"].includes(n.key))return test(v,w);
 if(n.key==="OR")return v.some(x=>test([x],w));
 if(n.key==="NOT")return !v.some(x=>test([x],w));
 if(n.key==="custom_trigger_tooltip")return test(v.filter(x=>x.key!=="tooltip"),w);
 if(n.key==="always")return v==="yes";
 if(n.key==="is_ai")return s.ai===(v==="yes");
 if(n.key==="is_subject")return s.subject===(v==="yes");
 if(n.key==="has_country_flag"&&Array.isArray(v)){assert.equal(v.length,2);assert.equal(v[1].key,"days");assert.equal(v[1].op,"<");const f=prop(v,"flag");return s.flags.has(f)&&w.day-s.flagDays[f]<Number(v[1].value);}
 if(n.key==="check_variable"){assert.equal(v.length,1);const x=v[0],a=number(x.key,s),b=number(x.value,s);if(x.op==="=")return a===b;if(x.op===">")return a>b;if(x.op==="<")return a<b;throw Error("Unknown variable operator");}
 if(n.key==="is_in_array")return(s.arrays[prop(v,"array")]||[]).includes(number(prop(v,"value"),s));
 if(n.key==="has_active_mission")return s.missions.has(v);
 if(n.key==="num_of_civilian_factories_available_for_projects"){assert.equal(n.op,">");return s.factories-number(P+"factories",s)>Number(v);}
 if(triggers[n.key])return test(triggers[n.key],w)===(v==="yes");
 return F.test([n],w);
});}
function run(nodes,w){const s=w.root;for(let i=0;i<nodes.length;i++){const n=nodes[i],v=n.value;
 if(n.key==="if"){let taken=false;do{const b=nodes[i];if(!taken&&(b.key==="else"||test(prop(b.value,"limit"),w))){run(b.value.filter(x=>x.key!=="limit"),w);taken=true;}if(!["else_if","else"].includes(nodes[i+1]?.key))break;i++;}while(true);}
 else if(n.key==="hidden_effect")run(v,w);
 else if(n.key==="set_country_flag"){const f=Array.isArray(v)?prop(v,"flag"):v;if(!s.flags.has(f))s.flagDays[f]=w.day;s.flags.add(f);}
 else if(n.key==="clr_country_flag")s.flags.delete(v);
 else if(n.key==="clear_array")s.arrays[v]=[];
 else if(n.key==="add_to_array"){assert.equal(v.length,1);(s.arrays[v[0].key]||=[]).push(number(v[0].value,s));}
 else if(n.key==="clear_variable")delete s.vars[v];
 else if(n.key==="set_variable"||n.key==="add_to_variable"){assert.equal(v.length,1);s.vars[v[0].key]=(n.key==="set_variable"?0:number(v[0].key,s))+number(v[0].value,s);}
 else if(n.key==="add_political_power"){s.pp+=Number(v);s.paid-=Number(v);}
 else if(n.key==="activate_mission"){assert(missions[v],"Undefined mission "+v);assert(!s.missions.has(v),"Duplicate timer");s.missions.add(v);}
 else if(n.key==="remove_mission")s.missions.delete(v);
 else if(effects[n.key])run(effects[n.key],w);
 else F.run([n],w);
}}
function start(a,w){run(effects[a.key+"_start"],w);}
function finish(a,w){w.day+=a.days;w.root.missions.delete(a.key+"_mission");run(prop(missions[a.key+"_mission"],"timeout_effect"),w);}
scenario("generated adapter is current and every output parses",()=>{B.build(true);for(const [file,source] of Object.entries(B.outputs))if(!file.endsWith("yml"))parse(source,true);});
scenario("native documentation supports the list, scheduler and modifier primitives",()=>{
 const game="C:/shit/Steam/steamapps/common/Hearts of Iron IV/";
 const docs=fs.readFileSync(game+"common/scripted_guis/_documentation.md","utf8");for(const term of ["dynamic_lists","entry_container","player_context","change_scope"])assert(docs.includes(term));
 const fx=fs.readFileSync(game+"documentation/effects_documentation.md","utf8");for(const key of ["activate_mission","remove_mission","clear_array","add_to_array","force_update_dynamic_modifier"])assert(fx.includes("## "+key));
 assert(walk(effects[P+"refresh_factories"]).some(n=>n.key==="force_update_dynamic_modifier"&&n.value==="yes"));
});
for(const a of actions)scenario(a.id+": source predicates, costs and completion are preserved",()=>{
 assert(triggers[a.key+"_can_start"]);assert(effects[a.key+"_start"]);
 const startBody=prop(prop(effects[a.key+"_start"],"if"),"limit");assert.equal(prop(startBody,a.key+"_can_start"),"yes");
 assert(walk(effects[a.key+"_start"]).some(n=>n.key==="add_political_power"&&Number(n.value)===-a.cost));
 const can=B.script(triggers[a.key+"_can_start"]);assert(can.includes(a.available));
 if(a.days){const mission=missions[a.key+"_mission"];assert.equal(Number(prop(mission,"days_mission_timeout")),a.days);assert.equal(prop(prop(mission,"visible"),"always"),"no");assert.equal(prop(prop(mission,"activation"),"always"),"no");assert(B.script(prop(mission,"timeout_effect")).includes(a.finish));
 assert(walk(prop(mission,"timeout_effect")).some(n=>n.key==="has_country_flag"&&n.value===a.key+"_running"));assert(walk(prop(mission,"cancel_trigger")).some(n=>n.key===P+"actor"&&n.value==="no"));}
});
// The local survey still uses the legacy timed adapter. The seven case inquiries
// now have their own comparison/protocol regression suite.
const echo=actions.find(a=>a.id==="HSM_BAR_case_local_survey");
for(const dlc of [false,true])scenario("local inquiry, then all seventeen paid studies: DLC="+dlc,()=>{
 const w=world(dlc);start(echo,w);assert.equal(w.root.pp,175);start(echo,w);assert.equal(w.root.pp,175);assert(w.root.missions.has(echo.key+"_mission"));
 finish(echo,w);assert(w.root.flags.has("HSM_BAR_case_local_surveyed"));finish(echo,w);assert.equal(w.root.pp,175);
 for(const a of actions.filter(a=>/^HSM_BAR_study_\w+$/.test(a.id)&&!a.id.endsWith("_disposition"))){const x=world(dlc);F.access(x,a.case);x.root.flags.add("HSM_BAR_region_"+B.regions[a.region-1]+"_open");
 assert(test(triggers[a.key+"_can_start"],x),a.id);start(a,x);const paid=x.root.pp;start(a,x);assert.equal(x.root.pp,paid);finish(a,x);assert(x.root.flags.has("HSM_BAR_study_"+a.case+"_done"),a.id);const count=x.root.events.length;finish(a,x);assert.equal(x.root.events.length,count);}
});
for(const reason of ["money","AI","subject","capitulation","territory","route"])scenario("click handler rejects "+reason+" without payment or timer",()=>{
 const w=world();if(reason==="money")w.root.pp=19;if(reason==="AI")w.root.ai=true;if(reason==="subject")w.root.subject=true;if(reason==="capitulation")w.root.capitulated=true;if(reason==="territory")w.states[624].controller="YAL";if(reason==="route")w.root.flags.delete("HSM_BAR_directorate");
 const before=w.root.pp;start(echo,w);assert.equal(w.root.pp,before);assert.equal(w.root.missions.size,0);
});
scenario("closing the window does not cancel a paid mission; explicit recall cannot refund or reward",()=>{
 const w=world();start(echo,w);w.root.vars[P+"open"]=1;run(prop(clicks,P+"close_click"),w);assert(w.root.missions.has(echo.key+"_mission"));run(effects[echo.key+"_cancel"],w);finish(echo,w);assert.equal(w.root.pp,175);assert(!w.root.flags.has("HSM_BAR_case_local_surveyed"));
});
scenario("lost access on the last day cannot award investigation evidence",()=>{const w=world();start(echo,w);w.states[624].controller="YAL";finish(echo,w);assert(!w.root.flags.has("HSM_BAR_case_local_surveyed"));assert(!w.root.flags.has(echo.key+"_running"));});
scenario("early timeout or a previous attempt's callback cannot complete a freshly paid inquiry",()=>{
 const w=world();start(echo,w);const callback=prop(missions[echo.key+"_mission"],"timeout_effect");run(callback,w);assert(!w.root.flags.has("HSM_BAR_case_local_surveyed"));assert(w.root.flags.has(echo.key+"_running"));
 run(effects[echo.key+"_cancel"],w);w.root.flags.delete(echo.key+"_cooldown");w.day=30;start(echo,w);const pp=w.root.pp;run(callback,w);assert.equal(w.root.pp,pp);assert(!w.root.flags.has("HSM_BAR_case_local_surveyed"));finish(echo,w);assert(w.root.flags.has("HSM_BAR_case_local_surveyed"));
});
scenario("factory reservation rebuild is bounded and releases only tracked assignments",()=>{
 const w=world();const reserved=actions.filter(a=>a.factories);for(const a of reserved.slice(0,2))w.root.flags.add(a.key+"_running");run(effects[P+"refresh_factories"],w);const expected=reserved.slice(0,2).reduce((sum,a)=>sum+a.factories,0);assert.equal(w.root.vars[P+"factories"],expected);run(effects[P+"refresh_factories"],w);assert.equal(w.root.vars[P+"factories"],expected);for(const a of reserved)w.root.flags.delete(a.key+"_running");run(effects[P+"refresh_factories"],w);assert.equal(w.root.vars[P+"factories"],0);
});
scenario("category and native-project gates preserve AI and MTC but hide human Service duplicates",()=>{
 const gate=triggers.HSM_BAR_service_legacy_visible;const w=world();assert(!test(gate,w));w.root.ai=true;assert(test(gate,w));w.root.ai=false;w.root.flags.delete("HSM_BAR_service_founded");assert(test(gate,w));w.root.flags.delete("HSM_BAR_directorate");assert(test(gate,w));
 for(const file of ["HSM_BAR_cases.txt","HSM_BAR_research_projects.txt"])for(const project of read("common/special_projects/projects/"+file))assert(walk(prop(project.value,"visible")).some(n=>n.key==="HSM_BAR_service_legacy_visible"&&n.value==="yes"));
});
scenario("regional navigation and archive links are presentation only",()=>{
 for(let i=1;i<=6;i++){const handler=prop(clicks,P+"region_"+i+"_click");assert(handler);assert(!walk(handler).some(n=>["add_political_power","activate_mission","country_event"].includes(n.key)));assert.equal(prop(prop(gates,P+"region_"+i+"_click_enabled"),P+"region_"+i+"_open"),"yes");}
 assert(!walk(prop(clicks,P+"archive_click")).some(n=>["add_political_power","activate_mission","country_event"].includes(n.key)));
});
scenario("stale dossier selection is reset before actions rebuild; reading never launches a mission",()=>{
 const body=prop(effects[P+"refresh"],"if");
 const selection=body.find(n=>n.key==="if"&&walk(n.value).some(x=>x.key==="is_in_array"));
 assert(selection,"Missing stale-selection guard");
 const w=world();w.root.vars[P+"subject"]=13;w.root.arrays[P+"subjects"]=[0,1,14];
 run([selection],w);assert.equal(w.root.vars[P+"subject"],0);assert.equal(w.root.missions.size,0);assert.equal(w.root.paid,0);
 w.root.vars[P+"subject"]=14;run([selection],w);assert.equal(w.root.vars[P+"subject"],14);
 const on=read("common/on_actions/HSM_BAR_core_on_actions.txt");
 const daily=prop(prop(prop(on,"on_actions"),"on_daily_BAR"),"effect");
 const hook=daily.find(n=>n.key==="if"&&prop(n.value,P+"pulse")==="yes");
 assert(hook);assert.equal(prop(prop(hook.value,"limit"),"has_country_flag"),P+"initialized");
 assert(!walk(prop(hook.value,"limit")).some(n=>n.value==="HSM_BAR_active"),"Route loss must still run cleanup");
});
scenario("unknown native syntax fails rather than being silently accepted",()=>{assert.throws(()=>test(parse("invented_predicate = yes"),world()),/Unsupported/);assert.throws(()=>run(parse("invented_effect = yes"),world()),/Unsupported/);});
console.log(`Barrad Service GUI: ${passed} scenarios passed; ${failed} failed; ${actions.length} action contracts. Native GUI/scheduling still requires playtesting.`);
process.exitCode=failed?1:0;
