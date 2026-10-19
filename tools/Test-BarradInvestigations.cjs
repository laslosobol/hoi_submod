"use strict";
// Parsed game scripts and strict deterministic fixtures; not an HOI4 runtime.
const fs=require("node:fs"),path=require("node:path"),assert=require("node:assert/strict");
const B=require("./Build-BarradInvestigations.cjs"),F=require("./Test-BarradCases.cjs");
const {cases,P,read,parse,prop,mod}=B;
const dict=ns=>Object.fromEntries(ns.map(n=>[n.key,n.value]));
const triggers={...dict(read("common/scripted_triggers/HSM_BAR_service_gui.txt")),...dict(read("common/scripted_triggers/HSM_BAR_investigation.txt"))};
const effects={...dict(read("common/scripted_effects/HSM_BAR_service_gui.txt")),...dict(read("common/scripted_effects/HSM_BAR_investigation.txt"))};
const missions=dict(prop(read("common/decisions/HSM_BAR_investigation.txt"),P+"timers"));
const gui=prop(prop(read("common/scripted_guis/HSM_BAR_investigation.txt"),"scripted_gui"),P+"window");
const clicks=dict(prop(gui,"effects")),gates=dict(prop(gui,"triggers"));
const texts=Object.fromEntries(read("common/scripted_localisation/HSM_BAR_investigation.txt").map(n=>[prop(n.value,"name"),n.value.filter(x=>x.key==="text")]));
const walk=ns=>ns.flatMap(n=>[n,...Array.isArray(n.value)?walk(n.value):[]]);
let passed=0,failed=0;
function scenario(name,fn){try{fn();passed++;console.log("PASS: "+name);}catch(e){failed++;console.error("FAIL: "+name+"\n"+e.stack);}}
function world(c,dlc=false){const w=F.world(dlc);w.day=0;Object.assign(w.root,{ai:false,subject:false,arrays:{},flagDays:{},missions:new Set()});F.flag(w,"region_local_open","case_"+c.id+"_known");return w;}
function number(v,s){if(Number.isFinite(Number(v)))return Number(v);assert(/^HSM_BAR_\w+$/.test(v),"Unsupported value "+v);return s.vars[v]||0;}
function test(ns,w){return ns.every(n=>{const v=n.value,s=w.root;
 if(["AND","hidden_trigger"].includes(n.key))return test(v,w);
 if(n.key==="OR")return v.some(x=>test([x],w));
 if(n.key==="NOT")return !v.some(x=>test([x],w));
 if(n.key==="custom_trigger_tooltip")return test(v.filter(x=>x.key!=="tooltip"),w);
 if(n.key==="always")return v==="yes";
 if(n.key==="is_ai")return s.ai===(v==="yes");
 if(n.key==="is_subject")return s.subject===(v==="yes");
 if(n.key==="has_country_flag"&&Array.isArray(v)){assert.equal(v.length,2);assert.equal(v[1].key,"days");assert.equal(v[1].op,"<");const f=prop(v,"flag");return s.flags.has(f)&&w.day-s.flagDays[f]<Number(v[1].value);}
 if(n.key==="check_variable"){assert.equal(v.length,1);const x=v[0],a=number(x.key,s),b=number(x.value,s);if(x.op==="=")return a===b;if(x.op===">")return a>b;if(x.op==="<")return a<b;throw Error("Unsupported comparison "+x.op);}
 if(n.key==="has_active_mission")return s.missions.has(v);
 if(n.key==="is_in_array")return(s.arrays[prop(v,"array")]||[]).includes(number(prop(v,"value"),s));
 if(triggers[n.key])return test(triggers[n.key],w)===(v==="yes");
 return F.test([n],w);
});}
function run(ns,w){const s=w.root;for(let i=0;i<ns.length;i++){const n=ns[i],v=n.value;
 if(n.key==="if"){let taken=false;do{const b=ns[i];if(!taken&&(b.key==="else"||test(prop(b.value,"limit"),w))){run(b.value.filter(x=>x.key!=="limit"),w);taken=true;}if(!["else_if","else"].includes(ns[i+1]?.key))break;i++;}while(true);}
 else if(n.key==="hidden_effect")run(v,w);
 else if(n.key==="set_country_flag"){const f=Array.isArray(v)?prop(v,"flag"):v;if(!s.flags.has(f))s.flagDays[f]=w.day;s.flags.add(f);}
 else if(n.key==="clr_country_flag")s.flags.delete(v);
 else if(n.key==="set_variable"){assert.equal(v.length,1);s.vars[v[0].key]=number(v[0].value,s);}
 else if(n.key==="clear_variable")delete s.vars[v];
 else if(n.key==="clear_array")s.arrays[v]=[];
 else if(n.key==="add_to_array"){assert.equal(v.length,1);(s.arrays[v[0].key]||=[]).push(number(v[0].value,s));}
 else if(n.key==="activate_mission"){assert(missions[v],"Undefined mission "+v);assert(!s.missions.has(v),"Duplicate mission");s.missions.add(v);}
 else if(n.key==="remove_mission")s.missions.delete(v);
 else if(effects[n.key])run(effects[n.key],w);
 else F.run([n],w);
}}
const effect=(key,w)=>{assert(effects[key],key);run(effects[key],w);};
const click=(key,w)=>{assert(clicks[P+key+"_click"],key);run(clicks[P+key+"_click"],w);};
const flag=(w,key)=>w.root.flags.has(key);
const investigated=(w,c)=>flag(w,"HSM_BAR_case_"+c.id+"_investigated");
function open(w,c){effect(c.key+"_open",w);assert.equal(w.root.vars[P+"case"],c.subject);}
function match(w,c){open(w,c);click("clue_a"+c.pair[0],w);click("clue_b"+c.pair[1],w);click("compare",w);assert(flag(w,c.key+"_matched"));}
function dispatch(w,c,i){click("page_2",w);click("method_"+i,w);click("start",w);}
function callback(w,c,i,mature=true){const k=c.key+"_"+i;if(mature){w.day+=c.methods[i-1].days;w.root.missions.delete(k+"_mission");}run(prop(missions[k+"_mission"],"timeout_effect"),w);}
function text(name,w){const block=texts[name].find(n=>!prop(n.value,"trigger")||test(prop(n.value,"trigger"),w));return prop(block.value,"localization_key");}
function gameplay(w){const s=structuredClone(w.root);for(const k of Object.keys(s.vars))if(k.startsWith(P))delete s.vars[k];s.flags.delete(P+"initialized");delete s.flagDays[P+"initialized"];return s;}
scenario("generated source is current, parses, and has no new gameplay counters",()=>{
 B.build(true);for(const [file,source] of Object.entries(B.outputs))if(!file.endsWith(".yml"))parse(source,true);
 const all=walk([...Object.entries(effects).filter(([k])=>k.startsWith(P)).flatMap(([,v])=>v),...Object.values(clicks)]);
 assert(!all.some(n=>["add_to_variable","subtract_from_variable","clamp_variable","random_list","add_ideas","add_dynamic_modifier"].includes(n.key)));
 for(const n of all.filter(n=>n.key==="set_variable"))assert(/^HSM_BAR_investigation_(case|open|page|method|report|a|b|feedback|frame_[ab][123]|frame_method[123])$/.test(n.value[0].key)||n.value[0].key.startsWith("HSM_BAR_archive_")||n.value[0].key.startsWith("HSM_BAR_service_gui_"));
});
for(const c of cases){
 scenario(c.id+": reading and navigation neither pay nor grant evidence",()=>{const w=world(c),before=gameplay(w);open(w,c);for(const i of [1,2,3,1])click("page_"+i,w);assert.deepEqual(gameplay(w),before);assert.equal(text("GetHSMBARInvestigationReport",w),P+"none");assert(!investigated(w,c));});
 for(let a=1;a<=3;a++)for(let b=1;b<=3;b++)scenario(`${c.id}: pair ${a}/${b}`,()=>{const w=world(c);open(w,c);click("clue_a"+a,w);click("clue_b"+b,w);click("compare",w);const correct=a===c.pair[0]&&b===c.pair[1];assert.equal(flag(w,c.key+"_matched"),correct);assert.equal(w.root.vars[P+"feedback"],correct?1:2);assert.equal(w.root.pp,200);assert(!investigated(w,c));assert.equal(w.root.missions.size,0);if(!correct){dispatch(w,c,1);assert.equal(w.root.pp,200);}});
 scenario(c.id+": incomplete comparison and hidden-window commands are inert",()=>{const w=world(c);open(w,c);click("clue_a"+c.pair[0],w);click("compare",w);assert(!flag(w,c.key+"_matched"));click("close",w);w.root.vars[P+"b"]=c.pair[1];click("compare",w);click("start",w);assert(!flag(w,c.key+"_matched"));assert.equal(w.root.pp,200);});
 for(const dlc of [false,true])for(let i=1;i<=3;i++)scenario(`${c.id}: protocol ${i}, DLC=${dlc}`,()=>{
  const w=world(c,dlc),m=c.methods[i-1],k=c.key+"_"+i;match(w,c);dispatch(w,c,i);assert.equal(w.root.pp,200-m.cost);assert(w.root.missions.has(k+"_mission"));
  click("method_"+(i%3+1),w);assert.equal(w.root.vars[P+"method"],i);click("start",w);assert.equal(w.root.pp,200-m.cost);
  open(w,c);assert.equal(w.root.vars[P+"method"],i);assert.equal(w.root.vars[P+"frame_method"+i],2);
  callback(w,c,i,false);assert(!flag(w,k+"_reported"));assert(!investigated(w,c));click("close",w);assert(w.root.missions.has(k+"_mission"));callback(w,c,i);
  assert(flag(w,k+"_reported"));assert.equal(investigated(w,c),m.qualifies);assert(!flag(w,c.key+"_running"));assert(!flag(w,"HSM_BAR_study_"+c.id+"_done"));
  assert.equal(text("GetHSMBARInvestigationStatus_"+c.id,w),P+(m.qualifies?"row_accepted":"row_limited"));
  assert.equal(F.valid("HSM_BAR_cases_"+c.id+"_eligible",w),m.qualifies);const events=w.root.events.length;callback(w,c,i);assert.equal(w.root.events.length,events);
  open(w,c);click("page_3",w);click("report_"+i,w);assert.equal(text("GetHSMBARInvestigationReport",w),k+"_report");effect(k+"_start",w);assert.equal(w.root.pp,200-m.cost);
 });
 scenario(c.id+": inconclusive report survives a paid successful retry and reentry",()=>{const w=world(c),bad=c.methods.findIndex(m=>!m.qualifies)+1,good=c.methods.findIndex(m=>m.qualifies)+1;match(w,c);dispatch(w,c,bad);callback(w,c,bad);assert(!investigated(w,c));dispatch(w,c,good);callback(w,c,good);assert(investigated(w,c));assert.equal(w.root.pp,200-c.methods[bad-1].cost-c.methods[good-1].cost);effect(P+"teardown",w);open(w,c);click("page_3",w);for(const i of [bad,good]){click("report_"+i,w);assert.equal(text("GetHSMBARInvestigationReport",w),c.key+"_"+i+"_report");}assert(flag(w,c.key+"_matched"));});
 scenario(c.id+": cancellation, old callback and restarted method cannot refund or fast-forward",()=>{const w=world(c),i=c.methods.findIndex(m=>m.qualifies)+1,k=c.key+"_"+i;match(w,c);dispatch(w,c,i);click("cancel",w);assert.equal(w.root.missions.size,0);assert.equal(w.root.pp,200-c.methods[i-1].cost);callback(w,c,i);assert(!flag(w,k+"_reported"));dispatch(w,c,i);callback(w,c,i,false);assert(!flag(w,k+"_reported"));callback(w,c,i);assert(investigated(w,c));assert.equal(w.root.pp,200-2*c.methods[i-1].cost);});
 for(const reason of ["territory","capitulation","subject","route","AI","region","field_access"])scenario(c.id+": access loss / "+reason,()=>{const w=world(c),i=c.methods.findIndex(m=>m.qualifies)+1;match(w,c);dispatch(w,c,i);if(reason==="territory")w.states[624].controller="YAL";if(reason==="capitulation")w.root.capitulated=true;if(reason==="subject")w.root.subject=true;if(reason==="route")w.root.flags.delete("HSM_BAR_directorate");if(reason==="AI")w.root.ai=true;if(reason==="region")w.root.flags.delete("HSM_BAR_region_local_open");if(reason==="field_access")w.root.flags.delete("HSM_BAR_field_research_open");callback(w,c,i);assert(!investigated(w,c));assert(!flag(w,c.key+"_"+i+"_reported"));assert(!flag(w,c.key+"_running"));assert.equal(w.root.pp,200-c.methods[i-1].cost);});
 scenario(c.id+": legacy starts are disabled, in-flight legacy work blocks protocol, finished cases remain readable",()=>{const w=world(c);assert(!test(triggers[c.legacy+"_can_start"],w));match(w,c);w.root.flags.add(c.legacy+"_running");dispatch(w,c,1);assert.equal(w.root.pp,200);w.root.flags.delete(c.legacy+"_running");w.root.missions.add(c.legacy+"_mission");dispatch(w,c,1);assert.equal(w.root.pp,200);w.root.missions.clear();F.access(w,c.id);open(w,c);dispatch(w,c,1);assert.equal(w.root.pp,200);assert.equal(text("GetHSMBARInvestigationReport",w),P+"existing");w.root.vars.HSM_BAR_service_gui_region=1;assert(test(triggers[c.legacy+"_listed"],w));});
 scenario(c.id+": insufficient funds and no hypothesis cannot be bypassed by direct effects",()=>{const w=world(c);effect(c.key+"_1_start",w);assert.equal(w.root.pp,200);match(w,c);w.root.pp=c.methods[0].cost-1;effect(c.key+"_1_start",w);assert.equal(w.root.pp,c.methods[0].cost-1);assert.equal(w.root.missions.size,0);});
 scenario(c.id+": erased lead or forged selection cannot reveal another file",()=>{
  const w=world(c);w.root.flags.delete("HSM_BAR_case_"+c.id+"_known");
  if(!["echo","compass"].includes(c.id)){effect(c.key+"_open",w);assert.equal(w.root.vars[P+"open"],undefined);}
  F.flag(w,"case_"+c.id+"_known");open(w,c);w.root.vars[P+"case"]=999;w.root.vars[P+"a"]=c.pair[0];w.root.vars[P+"b"]=c.pair[1];click("compare",w);click("start",w);assert(!flag(w,c.key+"_matched"));assert.equal(w.root.pp,200);assert.equal(w.root.missions.size,0);
 });
}
scenario("daily cleanup runs outside active-route guard and preserves authored findings",()=>{
 const daily=prop(prop(prop(read("common/on_actions/HSM_BAR_core_on_actions.txt"),"on_actions"),"on_daily_BAR"),"effect");const hook=daily.find(n=>n.key==="if"&&prop(n.value,P+"pulse")==="yes");assert(hook);assert.equal(prop(prop(hook.value,"limit"),"has_country_flag"),P+"initialized");
 const c=cases[0],w=world(c);match(w,c);dispatch(w,c,1);w.root.flags.delete("HSM_BAR_active");run([hook],w);assert.equal(w.root.missions.size,0);assert(flag(w,c.key+"_matched"));assert(!flag(w,P+"initialized"));
});
scenario("new case opening closes other windows; archived evidence is not fabricated",()=>{for(const c of cases){const w=world(c);for(const key of ["HSM_BAR_service_gui_open","HSM_BAR_archive_open","HSM_BAR_fielddesk_open"])w.root.vars[key]=1;open(w,c);for(const key of ["HSM_BAR_service_gui_open","HSM_BAR_archive_open","HSM_BAR_fielddesk_open"])assert.equal(w.root.vars[key],undefined);assert(!investigated(w,c));}});
scenario("checkbox properties use numeric variables and page visibility is explicit",()=>{const ps=prop(gui,"properties");for(const v of ["a","b","method"])for(let i=1;i<=3;i++)assert.equal(prop(prop(ps,P+(v==="method"?"method_"+i:"clue_"+v+i)),"frame"),P+"frame_"+v+i);for(let i=1;i<=3;i++)assert(gates[P+"page_"+i+"_body_visible"]);});
scenario("EN/RU documents, results and local references are complete and bounded",()=>{
 const keys=[];for(const lang of ["english","russian"]){const bytes=fs.readFileSync(path.join(mod,`localisation/${lang}/HSM_BAR_investigation_l_${lang}.yml`));assert.equal(bytes.subarray(0,3).toString("hex"),"efbbbf");const source=bytes.toString("utf8");const all=[...source.matchAll(/^\s*([^\s:#]+):\d+\s*"(.*)"$/gm)];assert.equal(new Set(all.map(x=>x[1])).size,all.length);keys.push(all.map(x=>x[1]).sort());for(const n of walk(Object.values(texts).flat()))if(n.key==="localization_key"&&n.value.startsWith(P))assert(all.some(x=>x[1]===n.value),n.value);}
 assert.deepEqual(...keys);for(const c of cases)for(const lang of ["en","ru"]){for(const d of c.documents){assert(d.title[lang].length<=60);for(const f of d.fragments)assert(f[lang].length<=180);}for(const m of c.methods){assert(m.title[lang].length<=60);assert(m.brief[lang].length<=400);assert(m.report[lang].length<=1100);}assert(c.hypothesis[lang].length<=550);assert(c.mismatch[lang].length<=550);}
});
scenario("unknown syntax fails loudly",()=>{assert.throws(()=>test(parse("invented = yes"),world(cases[0])),/Unsupported/);assert.throws(()=>run(parse("invented = yes"),world(cases[0])),/Unsupported/);});
console.log(`Barrad investigations: ${passed} scenarios passed; ${failed} failed; seven cases / 21 protocols. Native interaction still requires playtesting.`);
process.exitCode=failed?1:0;
