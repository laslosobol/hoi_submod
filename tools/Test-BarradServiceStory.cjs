"use strict";
// Script-level regression checks, not an HOI4 runtime simulation.
const fs = require("node:fs");
const path = require("node:path");
const assert = require("node:assert/strict");
const root = path.resolve(__dirname, "../mod/HoISubmod");
function parse(source) {
 const tokens = source.match(/"(?:\\.|[^"\\])*"|#[^\r\n]*|[{}]|[<>=!]+|[^\s{}<>=!#"]+/g).filter(t => !t.startsWith("#"));
 let i = 0;
 function block(inner = false) {
  const out = [];
  while (i < tokens.length && tokens[i] !== "}") {
   const key = tokens[i++], op = tokens[i++];
   assert(["=", "<", ">"].includes(op), "Unexpected syntax for " + key);
   let value = tokens[i++];
   if (value === "{") { value = block(true); assert.equal(tokens[i++], "}"); }
   out.push({key, value, op});
  }
  if (!inner) assert.equal(i, tokens.length);
  return out;
 }
 return block();
}
const read = file => parse(fs.readFileSync(path.join(root, file), "utf8"));
const get = (b, k) => b.find(n => n.key === k)?.value;
const story = read("events/HSM_BAR_service_story.txt");
const events = Object.fromEntries(story.filter(n => n.key === "country_event").map(n => [get(n.value,"id"), n.value]));
const focuses = Object.fromEntries(read("common/national_focus/HSM_BAR_directorate.txt").filter(n => n.key === "shared_focus").map(n => [get(n.value,"id"), n.value]));
const decisions = get(read("common/decisions/HSM_BAR_core.txt"), "HSM_BAR_service_affairs");
let passed = 0;
function check(name, fn) { fn(); passed++; console.log("PASS: " + name); }
function fresh() { return { flags: new Set(["HSM_BAR_active", "HSM_BAR_directorate", "HSM_BAR_service_founded"]), ideas: new Set(), vars: {}, pp: 0, scheduled: [], refresh: 0 }; }
function test(nodes, s) {
 return nodes.every(({key:k,value:v}) => {
  if(k === "tag") return v === "BAR";
  if(k === "NOT") return !v.some(n => test([n],s));
  if(k === "OR") return v.some(n => test([n],s));
  if(k === "has_country_flag") return s.flags.has(v);
  if(k === "HSM_BAR_case_review_ready") return s.reviewReady === true;
  throw Error("Unknown condition " + k);
 });
}
function run(nodes,s) {
 for(const {key:k,value:v} of nodes) {
  if(k === "if") { if(test(get(v,"limit"),s)) run(v.filter(n => n.key !== "limit"),s); }
  else if(k === "set_country_flag") { assert.equal(typeof v, "string"); s.flags.add(v); }
  else if(k === "clr_country_flag") s.flags.delete(v);
  else if(k === "add_political_power") s.pp += Number(v);
  else if(k === "add_to_variable") { assert.equal(v.length,1); s.vars[v[0].key] = (s.vars[v[0].key] || 0) + Number(v[0].value); }
  else if(k === "add_ideas") s.ideas.add(v);
  else if(k === "remove_ideas") s.ideas.delete(v);
  else if(k === "country_event") s.scheduled.push({id:get(v,"id"),days:Number(get(v,"days"))});
  else if(k === "HSM_BAR_core_refresh") s.refresh++;
  else throw Error("Unknown effect " + k);
 }
}
function choose(n, option, s) {
 const evt = events["hsm_bar_service." + n];
 const opts = evt.filter(n => n.key === "option");
 run(opts[option].value.filter(n => !["name","ai_chance"].includes(n.key)), s);
}
function snapshot(s) { return JSON.stringify({...s, flags:[...s.flags], ideas:[...s.ideas]}); }
check("Twenty authored scenes have active-route and replay guards", () => {
 assert.equal(Object.keys(events).length,20);
 for(const [id,e] of Object.entries(events)) {
  const n=id.split(".")[1], state=fresh();
  if(n==="15")state.flags.add("HSM_BAR_replication_pending");
  assert(test(get(e,"trigger"),state));
  state.flags.delete("HSM_BAR_service_founded"); assert(!test(get(e,"trigger"),state));
  state.flags.add("HSM_BAR_service_founded");
  state.flags.delete("HSM_BAR_active"); assert(!test(get(e,"trigger"),state));
  state.flags.add("HSM_BAR_active");state.flags.add("HSM_BAR_story_"+n+"_done");
  assert(!test(get(e,"trigger"),state));
 }
});
for(const [id,e] of Object.entries(events)) for(const [i] of e.filter(n => n.key==="option").entries()) {
 const n=Number(id.split(".")[1]);
 check(id+" option "+i+" is once-only and inert after defeat",()=>{
  const s=fresh();if(n===15)s.flags.add("HSM_BAR_replication_pending");
  choose(n,i,s);assert(s.flags.has("HSM_BAR_story_"+n+"_done"));
  const after=snapshot(s);choose(n,i,s);assert.equal(snapshot(s),after);
  const defeated=fresh();defeated.flags.delete("HSM_BAR_active");
  const before=snapshot(defeated);choose(n,i,defeated);assert.equal(snapshot(defeated),before);
 });
}
check("Retrieval choice persists, then can be reviewed without duplicating ideas",()=>{
 const s=fresh();choose(4,1,s);
 assert(s.ideas.has("HSM_BAR_expedited_retrieval"));assert(!s.ideas.has("HSM_BAR_careful_retrieval"));
 assert.deepEqual(s.scheduled,[{id:"hsm_bar_service.13",days:45}]);
 choose(13,0,s);
 const decision=get(decisions,"HSM_BAR_review_retrieval_order");
 assert(test(get(decision,"visible"),s));assert.equal(get(decision,"days_remove"),"21");
 run(get(decision,"remove_effect"),s);
 assert(s.ideas.has("HSM_BAR_careful_retrieval"));assert(!s.ideas.has("HSM_BAR_expedited_retrieval"));
 assert(!test(get(decision,"visible"),s));
 const end=snapshot(s);run(get(decision,"remove_effect"),s);assert.equal(snapshot(s),end);
});
check("The injured worker's account follows the actual retrieval order",()=>{
 const descriptions=events["hsm_bar_service.13"].filter(n=>n.key==="desc");
 for (const [choice, expected] of [[0,"careful"],[1,"priority"]]) {
  const s=fresh();choose(4,choice,s);
  const matches=descriptions.filter(n=>test(get(n.value,"trigger"),s));
  assert.equal(matches.length,1);
  assert.equal(get(matches[0].value,"text"),"hsm_bar_service.13.d_"+expected);
 }
});
check("Shared accounts create delayed narrative exposure and a free repair choice",()=>{
 const s=fresh();choose(7,1,s);
 assert.deepEqual(s.scheduled,[{id:"hsm_bar_service.14",days:75}]);
 choose(14,0,s);assert(!s.flags.has("HSM_BAR_shared_clearing"));assert(s.flags.has("HSM_BAR_separate_clearing"));assert.equal(s.pp,0);
 const other=fresh();choose(7,1,other);choose(14,1,other);
 assert(other.flags.has("HSM_BAR_accounting_exposure"));assert(!Object.hasOwn(other.vars,"HSM_BAR_cover_integrity"));
});
check("Former meter-only story choices are free while unrelated story fees remain exact",()=>{
 for(const id of [1,2,3,7,10,14]) {
  const s=fresh();choose(id,0,s);assert.equal(s.pp,0,"Obsolete fee on service."+id+".a");
  assert(s.flags.has("HSM_BAR_story_"+id+"_done"));
 }
 for(const [id,cost] of [[4,30],[9,10],[12,30]]) {
  const s=fresh();choose(id,0,s);assert.equal(s.pp,-cost,"Retained service."+id+".a cost changed");
  if(id===4)assert(s.ideas.has("HSM_BAR_careful_retrieval"));
  if(id===9)assert(s.flags.has("HSM_BAR_ruler_access_protocol"));
  if(id===12)assert(s.ideas.has("HSM_BAR_applied_findings"));
 }
});
check("Replication delays civilian benefit until the funded programme finishes",()=>{
 const s=fresh();choose(12,1,s);
 assert(!s.ideas.has("HSM_BAR_applied_findings"));assert(!s.flags.has("HSM_BAR_returned_findings"));
 const d=get(decisions,"HSM_BAR_replicate_bulletin");assert(test(get(d,"visible"),s));assert(!test(get(d,"available"),s));
 s.reviewReady=true;assert(test(get(d,"available"),s));assert.equal(get(d,"cost"),"35");assert.equal(get(d,"days_remove"),"35");
 run(get(d,"remove_effect"),s);assert(s.scheduled.some(e=>e.id==="hsm_bar_service.15"));
 choose(15,0,s);assert(s.ideas.has("HSM_BAR_applied_findings"));assert(s.flags.has("HSM_BAR_returned_findings"));
 assert(!test(get(d,"visible"),s));
});
check("Defeated institutions cannot finish queued follow-up decisions",()=>{
 for(const name of ["HSM_BAR_replicate_bulletin","HSM_BAR_review_retrieval_order"]) {
  const s=fresh();s.flags.add("HSM_BAR_replication_pending");s.flags.add("HSM_BAR_delivery_priority");s.flags.delete("HSM_BAR_directorate");
  const before=snapshot(s);run(get(get(decisions,name),"remove_effect"),s);assert.equal(snapshot(s),before);
 }
});
check("Focuses do not award study knowledge or completed technology",()=>{
 assert.equal(Object.keys(focuses).length,34);
 for(const f of Object.values(focuses)) {
  const reward=JSON.stringify(get(f,"completion_reward"));
  assert(!/HSM_BAR_study_\w+_done/.test(reward));
  assert(!/HSM_BAR_project_\w+_done/.test(reward));
 }
 assert(JSON.stringify(get(focuses.HSM_BAR_dir_commission,"available")).includes("HSM_BAR_case_review_ready"));
 assert(JSON.stringify(get(focuses.HSM_BAR_dir_commission,"available")).includes("HSM_BAR_cult_network_broken"));
 for(const f of ["suppression_lab","activation"])assert(JSON.stringify(get(focuses["HSM_BAR_dir_"+f],"available")).includes("HSM_BAR_suppression_knowledge_ready"));
 assert(JSON.stringify(get(focuses.HSM_BAR_dir_quiet_watch,"available")).includes("HSM_BAR_project_containment_done"));
 assert(JSON.stringify(get(focuses.HSM_BAR_dir_quiet_watch,"available")).includes("HSM_BAR_returned_findings"));
});
check("Regional offices are alternatives and never require contingent foreign events",()=>{
 for(const region of ["equus","griffonia","north","riverlands","zebrica"]) {
  const f=focuses["HSM_BAR_dir_"+region];
  assert.equal(get(f,"available"),undefined);
  assert.equal(get(get(f,"prerequisite"),"focus"),"HSM_BAR_dir_world");
  assert(JSON.stringify(get(f,"completion_reward")).includes("HSM_BAR_region_"+region+"_open"));
 }
 for(const name of ["liaison","trafficking","rulers"]) {
  const prerequisites=focuses["HSM_BAR_dir_"+name].filter(n=>n.key==="prerequisite");
  assert.equal(prerequisites.length,1);assert.equal(prerequisites[0].value.length,2);
 }
});
check("New institutional ideas are removed on dissolution",()=>{
 const teardown=get(read("common/scripted_effects/HSM_BAR_core_effects.txt"),"HSM_BAR_dissolve_institutions");
 for(const idea of ["HSM_BAR_careful_retrieval","HSM_BAR_expedited_retrieval","HSM_BAR_applied_findings"])
  assert(teardown.some(n=>n.key==="remove_ideas"&&n.value===idea));
});
console.log("Barrad Service story: "+passed+" scenario groups passed; 0 failed.");
