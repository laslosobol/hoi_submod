"use strict";
// Actual Clausewitz scripts in bounded deterministic fixtures, not an engine playtest.
// node tools/Test-BarradCivic.cjs [--native]
const fs = require("node:fs"), path = require("node:path"), assert = require("node:assert/strict");
const { parse, prop } = require("./Test-BarradArchiveSkin.cjs");
const mod = path.resolve(__dirname, "../mod/HoISubmod"), p = "HSM_BAR_civic_";
const read = f => fs.readFileSync(path.join(mod, f), "utf8");
const parsed = f => parse(read(f));
const walk = ns => ns.flatMap(n => [n, ...(Array.isArray(n.value) ? walk(n.value) : [])]);
function dict(ns) {
 const out = {};
 for (const n of ns) { assert(!Object.hasOwn(out, n.key), "Duplicate definition " + n.key); out[n.key] = n.value; }
 return out;
}
const triggers = dict(parsed("common/scripted_triggers/HSM_BAR_civic_triggers.txt"));
const effects = dict(parsed("common/scripted_effects/HSM_BAR_civic_effects.txt"));
const focusFile = parsed("common/national_focus/HSM_BAR_civic.txt");
const focuses = dict(focusFile.map(n => { assert.equal(n.key, "shared_focus"); return {key: prop(n.value, "id"), value: n.value}; }));
const eventFile = parsed("events/HSM_BAR_civic_events.txt");
const events = dict(eventFile.filter(n => n.key === "country_event").map(n => ({key: prop(n.value, "id"), value: n.value})));
const modifier = prop(parsed("common/dynamic_modifiers/HSM_BAR_civic_modifiers.txt"), p + "government");
const actions = prop(parsed("common/on_actions/HSM_BAR_civic_on_actions.txt"), "on_actions");

// Independent balance contract, deliberately not inferred from the production writes.
const stats = {
 pp: "political_power_factor", stability: "stability_factor", construction: "production_speed_buildings_factor",
 mobilization: "mobilization_speed", resistance: "resistance_target", compliance: "compliance_growth",
 core_defence: "army_core_defence_factor", training: "training_time_factor", supply: "supply_consumption_factor",
 recovery: "army_org_regain", efficiency_gain: "production_factory_efficiency_gain_factor",
 output: "industrial_capacity_factory", max_efficiency: "production_factory_max_efficiency_factor",
 infrastructure: "production_speed_infrastructure_factor", relations: "improve_relations_maintain_cost_factor"
};
const awards = {
 republic: {}, municipalities: {}, registry: {mobilization: .1}, courts: {},
 civil_service: {pp: .08}, accounts: {pp: .05}, cabinet: {pp: .05}, defence: {}, procurement: {},
 foreign_office: {relations: -.1}, appeals: {resistance: -.02, stability: .03}, local_works: {infrastructure: .1},
 inspectors: {pp: .05}, territorial_representation: {}, equal_services: {compliance: .02}, ordinary_state: {stability: .05, pp: .05}
};
const policies = [
 ["municipalities", "local_mandates", {construction: .05, pp: -.03}, "district_mandates", {pp: .05, stability: -.02}],
 ["courts", "circuit_courts", {resistance: -.05, pp: -.02}, "permanent_bench", {stability: .04, compliance: -.02}],
 ["defence", "local_reserve", {core_defence: .10, training: .03}, "central_depots", {supply: -.08, recovery: .05, pp: -.03}],
 ["procurement", "open_tenders", {construction: .07, efficiency_gain: -.03}, "framework_orders", {output: .08, supply: -.05, max_efficiency: -.02}],
 ["territorial_representation", "local_statutes", {compliance: .04, pp: -.03}, "equal_franchise", {stability: .03, resistance: -.03, output: -.01}]
];
const parents = {
 republic: [], municipalities: ["republic"], registry: ["republic"], courts: ["republic"],
 civil_service: ["municipalities"], accounts: ["registry"], cabinet: ["civil_service", "accounts", "courts"],
 defence: ["cabinet"], procurement: ["cabinet"], foreign_office: ["cabinet"], appeals: ["defence"],
 local_works: ["procurement"], inspectors: ["foreign_office", "procurement"],
 territorial_representation: ["appeals", "local_works", "inspectors"], equal_services: ["territorial_representation"], ordinary_state: ["equal_services"]
};
const zero = () => Object.fromEntries(Object.keys(stats).map(k => [k, 0]));
const close = (a, b, label) => assert(Math.abs(a - b) < 1e-9, `${label}: ${a} != ${b}`);
function world() {
 return {tag: "BAR", original: "BAR", exists: true, capitulated: false, subject: false, owner: "BAR", controller: "BAR",
  flags: new Set(["HSM_BAR_active", "HSM_BAR_collegium"]), focuses: new Set(["HSM_BAR_collegium_oath"]),
  vars: {}, modifiers: new Set(), cache: {}, installs: 0, events: [], leader: "BAR_gasienica", cores: [624], research: [], pp: 75};
}
function condition(ns, w) {
 return ns.every(({key:k, value:v}) => {
  if (k === "AND") return condition(v,w);
  if (k === "OR") return v.some(n => condition([n],w));
  if (k === "NOT") return !v.some(n => condition([n],w));
  if (k === "custom_trigger_tooltip") return condition(v.filter(n=>n.key!=="tooltip"),w);
  if (k === "tag") return w.tag === v;
  if (k === "original_tag") return w.original === v;
  if (k === "exists") return w.exists === (v === "yes");
  if (k === "has_capitulated") return w.capitulated === (v === "yes");
  if (k === "is_subject") return w.subject === (v === "yes");
  if (k === "owns_state") { assert.equal(v,"624"); return w.owner === w.tag; }
  if (k === "controls_state") { assert.equal(v,"624"); return w.controller === w.tag; }
  if (k === "has_country_flag") return w.flags.has(v);
  if (k === "has_completed_focus") return w.focuses.has(v);
  if (k === "has_dynamic_modifier") return w.modifiers.has(v);
  if (triggers[k]) { assert(["yes","no"].includes(v)); return condition(triggers[k],w) === (v === "yes"); }
  throw Error("Unsupported predicate " + k);
 });
}
function cache(w) {
 w.cache = Object.fromEntries(Object.entries(stats).map(([key,native]) => [native, w.vars[p+key] || 0]));
}
function run(ns,w) {
 for (let i=0;i<ns.length;i++) {
  const {key:k,value:v}=ns[i];
  if (k === "if") {
   let taken = false;
   do {
    const n = ns[i], yes = n.key === "else" || condition(prop(n.value,"limit"),w);
    if (!taken && yes) { run(n.value.filter(x=>x.key!=="limit"),w); taken=true; }
    if (!["else","else_if"].includes(ns[i+1]?.key)) break;
    i++;
   } while (true);
  } else if (k === "hidden_effect") run(v,w);
  else if (k === "custom_effect_tooltip") assert.equal(typeof v,"string");
  else if (k === "set_country_flag") w.flags.add(v);
  else if (k === "clr_country_flag") w.flags.delete(v);
  else if (["set_variable","add_to_variable"].includes(k)) {
   assert.equal(v.length,1); assert(v[0].key.startsWith(p)); assert(Number.isFinite(Number(v[0].value)));
   w.vars[v[0].key] = (k === "set_variable" ? 0 : w.vars[v[0].key] || 0) + Number(v[0].value);
  } else if (k === "add_dynamic_modifier") {
   assert.equal(prop(v,"modifier"),p+"government"); assert.equal(v.length,1);
   assert(condition(prop(modifier,"enable"),w)); w.modifiers.add(p+"government"); w.installs++; cache(w);
  } else if (k === "remove_dynamic_modifier") {
   assert.equal(prop(v,"modifier"),p+"government"); w.modifiers.delete(p+"government"); w.cache={};
  } else if (k === "force_update_dynamic_modifier") { assert.equal(v,"yes"); if(w.modifiers.has(p+"government")) cache(w); }
  else if (k === "country_event") {
   assert.equal(v.length,1,"Civic events must be immediate"); const id=prop(v,"id");
   assert(events[id]); assert(condition(prop(events[id],"trigger"),w),"Queued unreachable event "+id); w.events.push(id);
  } else if (effects[k]) { assert.equal(v,"yes"); run(effects[k],w); }
  else throw Error("Unsupported effect " + k);
 }
}
const effect = (id,w) => { assert(effects[p+id],id); run(effects[p+id],w); };
function ready(id,w) {
 for(const parent of parents[id]) w.focuses.add(p+parent);
 for(const s of policies) w.flags.add(p+s[0]+"_settled");
 w.flags.add(p+"republic_awarded");
}
function finish(id,w) {
 assert(condition(prop(focuses[p+id],"available"),w),"Unavailable focus "+id);
 run(prop(focuses[p+id],"completion_reward"),w);
 assert(w.flags.has(p+id+"_awarded"));
 w.focuses.add(p+id);
}
function answer(index,choice,w) {
 const body=events["HSM_BAR_civic."+(index+1)], option=body.filter(n=>n.key==="option")[choice].value;
 run(option.filter(n=>!["name","ai_chance"].includes(n.key)),w);
}
function expected(ids=[],mask=0,includePolicies=false) {
 const result=zero(), add=values=>{ for(const[k,v]of Object.entries(values)) result[k]+=v; };
 for(const id of ids) add(awards[id]);
 if(includePolicies) for(const[i,c]of policies.entries()) add(c[(mask>>i)&1 ? 4 : 2]);
 return result;
}
function assertStats(w,result) {
 for(const[k,v]of Object.entries(result)) { close(w.vars[p+k],v,"Variable "+k); close(w.cache[stats[k]],v,"Cache "+k); }
}
let passed=0,failed=0;
function scenario(name,fn) { try {fn();passed++;console.log("PASS: "+name);} catch(e){failed++;console.error("FAIL: "+name+"\n"+e.stack);} }

scenario("16 bounded 28/35-day focuses, independent root, cabinet/foreign-office contract, unique spaced positions",()=>{
 assert.deepEqual(Object.keys(focuses).map(k=>k.slice(p.length)),Object.keys(awards));
 const positions=new Set();
 for(const[id,b]of Object.entries(focuses)) {
  const name=id.slice(p.length), x=Number(prop(b,"x")),y=Number(prop(b,"y"));
  assert(x>=40&&x<=48&&y>=0&&y<=12); assert([4,5].includes(Number(prop(b,"cost"))));
  assert(!positions.has(`${x}:${y}`)); positions.add(`${x}:${y}`);
  assert.equal(prop(b,"cancel_if_invalid"),"yes"); assert.equal(prop(b,"continue_if_invalid"),"no");
  assert.deepEqual(b.filter(n=>n.key==="prerequisite").map(n=>prop(n.value,"focus")),parents[name].map(q=>p+q));
  for(const q of parents[name]) assert(Number(prop(focuses[p+q],"y"))<y,"Non-forward prerequisite");
  for(const[other,body]of Object.entries(focuses)) if(other!==id&&Number(prop(body,"y"))===y) assert(Math.abs(x-Number(prop(body,"x")))>=4);
 }
 assert.equal(focuses[p+"republic"].filter(n=>n.key==="prerequisite").length,0);
 assert.deepEqual(parents.foreign_office,["cabinet"]);
 assert(!JSON.stringify(triggers).match(/collegium_(assembly|second_stage|future)|has_war|has_war_with/));
});
scenario("all native modifier fields bind to separate derived civic variables",()=>{
 assert.deepEqual(Object.fromEntries(modifier.filter(n=>!["icon","enable","remove_trigger"].includes(n.key)).map(n=>[n.key,n.value])),Object.fromEntries(Object.entries(stats).map(([k,v])=>[v,p+k])));
});
for(const id of Object.keys(awards)) scenario(`actual focus reward ${id}: exact isolated bonus and one-time completion`,()=>{
 const w=world(); ready(id,w); w.flags.delete(p+id+"_awarded");
 run(prop(focuses[p+id],"completion_reward"),w);
 assert(w.flags.has(p+id+"_awarded")); assertStats(w,expected([id]));
 const before=structuredClone(w); effect("finish_"+id,w); assert.deepEqual(w,before);
 assert.equal(w.flags.has("HSM_BAR_diplomacy_open"),id==="foreign_office");
 assert.equal(w.pp,75); assert.equal(w.leader,"BAR_gasienica"); assert.deepEqual(w.cores,[624]); assert.deepEqual(w.research,[]);
});
for(const [id,requirements]of Object.entries(parents)) for(const missing of requirements) scenario(`${id} rejects absent prerequisite ${missing}`,()=>{
 const w=world(); ready(id,w); w.flags.delete(p+id+"_awarded"); w.focuses.delete(p+missing);
 assert(!condition(prop(focuses[p+id],"available"),w)); const before=structuredClone(w); effect("finish_"+id,w); assert.deepEqual(w,before);
});
const revoked=[
 ["foreign tag",w=>w.tag="WIT"],["foreign origin",w=>w.original="WIT"],["nonexistent",w=>w.exists=false],
 ["inactive",w=>w.flags.delete("HSM_BAR_active")],["no College",w=>w.flags.delete("HSM_BAR_collegium")],
 ["Directorate",w=>w.flags.add("HSM_BAR_directorate")],["no oath",w=>w.focuses.delete("HSM_BAR_collegium_oath")],
 ["capitulated",w=>w.capitulated=true],["subject",w=>w.subject=true],["home not owned",w=>w.owner="WIT"],["home not controlled",w=>w.controller="WIT"]
];
for(const[name,mutate]of revoked) scenario(`${name}: all focus rewards, choices and modifier are guarded; pulse suspends pending scenes`,()=>{
 const w=world(); for(const id of Object.keys(awards)) ready(id,w);
 for(const c of policies){w.flags.delete(p+c[0]+"_settled");w.flags.add(p+c[0]+"_awarded");w.flags.add(p+c[0]+"_pending");}
 effect("refresh",w); mutate(w);
 for(const id of Object.keys(awards)) {
  const before=structuredClone(w); assert(!condition(prop(focuses[p+id],"available"),w)); effect("finish_"+id,w); assert.deepEqual(w,before);
 }
 for(let i=0;i<policies.length;i++) for(const choice of [0,1]) answer(i,choice,w);
 for(const c of policies) {assert(!w.flags.has(p+c[1]));assert(!w.flags.has(p+c[3]));assert(!w.flags.has(p+c[0]+"_settled"));}
 assert(!condition(prop(modifier,"enable"),w)); assert(condition(prop(modifier,"remove_trigger"),w));
 effect("pulse",w); assert(!w.modifiers.has(p+"government")); assert.deepEqual(w.cache,{});
 for(const k of Object.keys(stats)) assert.equal(w.vars[p+k],0);
 for(const c of policies) assert(!w.flags.has(p+c[0]+"_pending"));
});
for(const [i,c]of policies.entries()) for(const choice of [0,1]) scenario(`${c[0]} choice ${choice}: requires the scene, exact durable tradeoff, cannot replay or reverse`,()=>{
 const w=world(); ready(c[0],w); w.flags.delete(p+c[0]+"_settled");
 answer(i,choice,w); assert(!w.flags.has(p+c[choice?3:1]));
 finish(c[0],w); assert.deepEqual(w.events,["HSM_BAR_civic."+(i+1)]);
 for(let j=0;j<5;j++) effect("pulse",w); assert.equal(w.events.length,1,"Repeated pending event");
 answer(i,choice,w); const want=zero(); Object.assign(want,c[choice?4:2]); assertStats(w,want);
 assert(w.flags.has(p+c[0]+"_settled")); assert(!w.flags.has(p+c[0]+"_pending"));
 const before=structuredClone(w); answer(i,choice,w); answer(i,1-choice,w); effect("refresh",w); assert.deepEqual(w,before);
});
scenario("unresolved municipal and court policies block cabinet, never demand second-stage or foreign wars",()=>{
 const w=world(); finish("republic",w); finish("municipalities",w); finish("registry",w); finish("courts",w); finish("accounts",w);
 assert(!condition(prop(focuses[p+"civil_service"],"available"),w));
 answer(0,0,w); finish("civil_service",w); assert(!condition(prop(focuses[p+"cabinet"],"available"),w));
 answer(1,0,w); finish("cabinet",w); finish("foreign_office",w);
 assert(w.flags.has("HSM_BAR_diplomacy_open"));
 assert(![...w.focuses].some(f=>f.includes("assembly")||f.includes("future")));
});
for(let mask=0;mask<32;mask++) scenario(`complete civic path ${mask}: all choices reachable, precise bounded total, 100 refreshes do not stack`,()=>{
 const w=world();
 for(const id of Object.keys(awards)) {
  finish(id,w); const index=policies.findIndex(c=>c[0]===id); if(index>=0) answer(index,(mask>>index)&1,w);
 }
 assert.equal(w.events.length,5); assert.equal(w.installs,1); const want=expected(Object.keys(awards),mask,true); assertStats(w,want);
 const before=structuredClone(w);
 for(let j=0;j<100;j++) effect("pulse",w);
 assert.deepEqual(w,before);
 assert(want.pp>=.169999&&want.pp<=.330001); assert(want.stability>=.059999&&want.stability<=.150001);
 assert(want.compliance>=-.000001&&want.compliance<=.060001); assert(want.resistance>=-.100001&&want.resistance<=-.019999);
});
scenario("daily refresh repairs legacy -700% resistance without changing recorded progress",()=>{
 const w=world(); w.flags.add(p+"republic_awarded"); w.flags.add(p+"appeals_awarded");
 w.flags.add(p+"courts_settled"); w.flags.add(p+"circuit_courts");
 w.vars[p+"resistance"]=-7; w.modifiers.add(p+"government"); cache(w);
 const flags=structuredClone(w.flags); effect("pulse",w);
 close(w.cache.resistance_target,-.07,"Corrected -7% resistance target");
 assert.deepEqual(w.flags,flags); const before=structuredClone(w);
 effect("pulse",w); assert.deepEqual(w,before);
});
scenario("suspended government retains policies and progress and reissues an unresolved scene on return",()=>{
 const w=world(); finish("republic",w); finish("municipalities",w); answer(0,1,w); finish("courts",w);
 const flags=[...w.flags].filter(f=>!f.endsWith("_pending")); w.capitulated=true; effect("pulse",w);
 assert.deepEqual([...w.flags],flags); assert.equal(w.events.length,2);
 answer(1,0,w); assert(!w.flags.has(p+"courts_settled"));
 w.capitulated=false; effect("pulse",w); assert.equal(w.events.length,3); assert.equal(w.events[2],"HSM_BAR_civic.2");
 answer(1,0,w); assert(w.flags.has(p+"circuit_courts")); assert(w.flags.has(p+"district_mandates"));
 effect("pulse",w); assert.equal(w.events.length,3);
});
scenario("teardown removes only civic derived state and pending scenes, preserving historical choices",()=>{
 const w=world(); finish("republic",w); finish("municipalities",w); answer(0,0,w);
 const flags=structuredClone(w.flags),leader=w.leader; w.flags.add("unrelated"); w.vars.unrelated=34;
 effect("teardown",w); effect("teardown",w);
 assert(!w.modifiers.has(p+"government")); assert.equal(w.leader,leader); assert.equal(w.vars.unrelated,34);
 for(const flag of flags) assert(w.flags.has(flag)); assert(w.flags.has("unrelated"));
 effect("refresh",w); assertStats(w,{...zero(),construction:.05,pp:-.03});
});
scenario("institutional dissolution invokes civic cleanup immediately and blocks restoration",()=>{
 const body=prop(parsed("common/scripted_effects/HSM_BAR_core_effects.txt"),"HSM_BAR_dissolve_institutions");
 const hooks=body.filter(n=>walk([n]).some(q=>q.key===p+"teardown"));
 assert.equal(hooks.length,1);
 const w=world(); finish("republic",w); finish("municipalities",w); answer(0,0,w); finish("courts",w);
 assert(w.modifiers.has(p+"government")); assert(w.flags.has(p+"courts_pending"));
 run(hooks,w);
 assert(!w.modifiers.has(p+"government")); assert(!w.flags.has(p+"courts_pending"));
 assert(w.flags.has(p+"local_mandates"));
 run(body.filter(n=>n.key==="clr_country_flag"),w);
 effect("pulse",w); answer(1,0,w);
 assert(!w.modifiers.has(p+"government")); assert(!w.flags.has(p+"courts_settled"));
 const untouched=world(),before=structuredClone(untouched); run(hooks,untouched); assert.deepEqual(untouched,before);
});
scenario("corrupt simultaneous policy flags still cannot award both alternatives or unratified policies",()=>{
 const w=world(); w.flags.add(p+"republic_awarded");
 for(const c of policies){w.flags.add(p+c[1]);w.flags.add(p+c[3]);}
 effect("refresh",w); assertStats(w,zero());
 for(const c of policies)w.flags.add(p+c[0]+"_settled");
 effect("refresh",w); assertStats(w,expected([],0,true));
});
scenario("three scientific constitutions remain compatible with an unchanged civilian head",()=>{
 for(const charter of ["open","republic","tutelage"]){
  const w=world(); w.flags.add("HSM_BAR_collegium_"+charter+"_charter"); finish("republic",w); assert.equal(w.leader,"BAR_gasienica");
 }
 const all=walk(Object.values(effects).flat());
 assert(!all.some(n=>["add_state_core","set_politics","recruit_character","retire_character","set_country_leader","create_wargoal","add_tech_bonus","add_stability","add_political_power"].includes(n.key)));
 for(const n of all.filter(n=>["set_country_flag","clr_country_flag"].includes(n.key))) assert(n.value.startsWith(p)||n.value==="HSM_BAR_diplomacy_open");
});
scenario("daily native hook calls the public civic pulse exactly once",()=>{
 assert.equal(actions.length,1); assert.equal(actions[0].key,"on_daily_BAR");
 assert.deepEqual(prop(actions[0].value,"effect"),[{key:p+"pulse",op:"=",value:"yes"}]);
 const w=world(); run(prop(actions[0].value,"effect"),w); assert.equal(w.events.length,0);
});

const locales={};
scenario("complete EN/RU keys, UTF-8 BOM, substantive prose, no duplicate keys or missing event/focus tooltips",()=>{
 for(const language of ["english","russian"]){
  const raw=read(`localisation/${language}/HSM_BAR_civic_l_${language}.yml`);
  assert.equal(raw.charCodeAt(0),0xFEFF); assert(raw.startsWith("\uFEFFl_"+language+":"));
  const pairs=[...raw.matchAll(/^ ([A-Za-z0-9_.]+):0 "((?:\\.|[^"\\])*)"\s*$/gm)].map(m=>[m[1],m[2]]);
  assert.equal(new Set(pairs.map(a=>a[0])).size,pairs.length); locales[language]=Object.fromEntries(pairs);
  assert.equal(pairs.length,86);
  for(const[id]of Object.entries(focuses)){assert(locales[language][id]);assert(locales[language][id+"_desc"].split(/\s+/).length>=40);}
  // Russian naturally uses fewer words than the corresponding English scene.
  for(const id of Object.keys(events)){
   const scene=locales[language][id+".d"];
   assert(scene.split(/\s+/).length >= (language==="english"?120:100),language+" "+id);
   assert.equal(scene.split("\\n\\n").length,3,"Three substantive scene paragraphs: "+id);
  }
  const refs=walk([...focusFile,...eventFile,...Object.values(effects).flat(),...Object.values(triggers).flat()]).filter(n=>["title","desc","name","tooltip","custom_effect_tooltip"].includes(n.key)&&typeof n.value==="string"&&n.value.startsWith("HSM_BAR_civic"));
  for(const n of refs) assert(locales[language][n.value],"Missing "+language+" "+n.value);
  for(const value of Object.values(locales[language])) assert(!/TODO|PLACEHOLDER|\[REDACTED\]|\[УДАЛЕНО\]/.test(value));
 }
 assert.deepEqual(Object.keys(locales.english).sort(),Object.keys(locales.russian).sort());
});
scenario("every numerical tooltip agrees with the independent per-focus and per-policy balance contract",()=>{
 for(const lang of ["english","russian"]){
  assert(locales[lang],"Localization validation must succeed first");
  for(const[id,values]of [...Object.entries(awards),...policies.flatMap(c=>[[c[1],c[2]],[c[3],c[4]]])]){
   const text=locales[lang][p+id+"_tt"];
   const actual=[...text.matchAll(/§[GR]([+-]\d+\.\d+)(%?)§!/g)].map(m=>[Number(m[1]),m[2]]);
   const wanted=Object.entries(values).map(([k,v])=>[Number((v*(k==="compliance"?1:100)).toFixed(2)),k==="compliance"?"":"%"]);
   assert.deepEqual(actual,wanted,lang+" "+id);
  }
 }
});
scenario("visible focus conditions never expose unlocalized internal policy flags",()=>{
 function inspect(ns){
  for(const n of ns){
   if(n.key==="custom_trigger_tooltip"){
    const key=prop(n.value,"tooltip");
    for(const language of ["english","russian"])assert(locales[language][key],"Missing visible gate "+key);
   } else if(triggers[n.key])inspect(triggers[n.key]);
   else {
    assert.notEqual(n.key,"has_country_flag","Visible unwrapped internal flag "+n.value);
    if(Array.isArray(n.value))inspect(n.value);
   }
  }
 }
 for(const body of Object.values(focuses))inspect(prop(body,"available"));
});

if(process.argv.includes("--native")){
 const game=process.env.HOI4_GAME_ROOT||"C:/shit/Steam/steamapps/common/Hearts of Iron IV";
 const eaw=process.env.EAW_ROOT||"C:/shit/Steam/steamapps/workshop/content/394360/1826643372";
 scenario("installed native resistance tooltip uses percentages and both occupation-law sources use fractions",()=>{
  const loc=fs.readFileSync(path.join(game,"localisation/english/modifiers_l_english.yml"),"utf8");
  assert(/^\s*resistance_target_tt:.*\$RIGHT\|-=%1\$/m.test(loc));
  for(const root of [game,eaw]) {
   const laws=parse(fs.readFileSync(path.join(root,"common/occupation_laws/occupation_laws.txt"),"utf8"));
   assert(walk(laws).some(n=>n.key==="resistance_target"&&Number(n.value)===-.15),root);
  }
  const writes=walk(Object.values(effects).flat()).filter(n=>n.key===p+"resistance"&&Number(n.value)!==0);
  assert.deepEqual(writes.map(n=>Number(n.value)),[-.02,-.05,-.03]);
 });
 scenario("installed engine documents every civic trigger/effect/modifier or its generated building modifier",()=>{
  const modifiers=fs.readFileSync(path.join(game,"documentation/modifiers_documentation.md"),"utf8");
  for(const name of Object.values(stats).filter(n=>n!=="production_speed_infrastructure_factor")) assert(modifiers.includes("## "+name+"\r\n")||modifiers.includes("## "+name+"\n"),name);
  const buildings=fs.readFileSync(path.join(game,"common/buildings/00_buildings.txt"),"utf8"); assert(/\binfrastructure\s*=\s*\{/.test(buildings));
  for(const[type,names]of Object.entries({triggers:["tag","original_tag","exists","has_capitulated","is_subject","owns_state","controls_state","has_country_flag","has_completed_focus","has_dynamic_modifier"],effects:["set_country_flag","clr_country_flag","set_variable","add_to_variable","add_dynamic_modifier","remove_dynamic_modifier","force_update_dynamic_modifier","country_event"]})){
   const text=fs.readFileSync(path.join(game,`documentation/${type}_documentation.md`),"utf8");
   for(const name of names) assert(new RegExp("^## "+name+"\\r?$","m").test(text),type+" "+name);
  }
 });
 scenario("installed graphical sprites resolve including focus shine variants and civic/event illustrations",()=>{
  const gfx=[];
  function collect(dir){for(const entry of fs.readdirSync(dir,{withFileTypes:true})){const f=path.join(dir,entry.name);if(entry.isDirectory())collect(f);else if(entry.name.endsWith(".gfx"))gfx.push(fs.readFileSync(f,"utf8"));}}
  for(const root of [game,eaw,mod]) collect(path.join(root,"interface"));
  const names=new Set([...gfx.join("\n").matchAll(/\bname\s*=\s*"?(GFX_\w+)/g)].map(m=>m[1]));
  for(const body of Object.values(focuses)){const name=prop(body,"icon");assert(names.has(name),"Missing sprite "+name);assert(names.has(name+"_shine"),"Missing shine "+name);}
  assert(names.has(prop(modifier,"icon")));for(const body of Object.values(events))assert(names.has(prop(body,"picture")));
 });
 scenario("installed EaW confirms Gasienica's public spelling without changing his character",()=>{
  const ru=fs.readFileSync(path.join(eaw,"localisation/russian/country_BAR_l_russian.yml"),"utf8");
  assert(/bar_cpt_gasienica:0 "Капитан Гасеница"/.test(ru));
  assert(!read("localisation/russian/HSM_BAR_civic_l_russian.yml").includes("Гонсениц"));
 });
}
console.log(`Barrad civic: ${passed} passed, ${failed} failed.`);
const totals=Array.from({length:32},(_,mask)=>expected(Object.keys(awards),mask,true));
console.log("Civic full-path raw modifier ranges: "+JSON.stringify(Object.fromEntries(Object.keys(stats).map(k=>[k,[Math.min(...totals.map(t=>t[k])),Math.max(...totals.map(t=>t[k]))]]))));
if(!process.argv.includes("--native"))console.log("Installed engine/EaW checks not requested; use --native.");
process.exitCode=failed?1:0;
