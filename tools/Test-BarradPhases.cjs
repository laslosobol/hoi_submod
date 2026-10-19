"use strict";

// node tools/Test-BarradPhases.cjs [--game-root PATH] [--eaw-root PATH]
// Strict script fixtures, not HOI4 or a rendered focus-tree test. Only phase logic
// executes here. Registry, diplomacy, outcome aggregation and core refresh are
// explicit call-boundary stubs; their separate suites own those implementations.
const fs = require("node:fs");
const path = require("node:path");
const assert = require("node:assert/strict");
const mod = path.resolve(__dirname, "../mod/HoISubmod");
function argument(key, fallback) {
 const index = process.argv.indexOf(key);
 if (index < 0) return fallback;
 assert(process.argv[index + 1] && !process.argv[index + 1].startsWith("--"), "Missing " + key + " path");
 return process.argv[index + 1];
}
const game = argument("--game-root", process.env.HOI4_GAME_ROOT || "C:/shit/Steam/steamapps/common/Hearts of Iron IV");
const eaw = argument("--eaw-root", process.env.EAW_ROOT || "C:/shit/Steam/steamapps/workshop/content/394360/1826643372");
function parse(source) {
 const tokens = source.replace(/^\uFEFF/, "").match(/"(?:\\.|[^"\\])*"|#[^\r\n]*|[{}]|[<>!=]=?|[^\s{}<>=!#"]+/g)
  ?.filter(token => !token.startsWith("#")) || [];
 let i = 0;
 function block(inner = false) {
  const nodes = [];
  while (i < tokens.length && tokens[i] !== "}") {
   const key = tokens[i++];
   assert.notEqual(key, "{", "Unexpected anonymous block");
   if (!["=", "<", ">", "<=", ">=", "!="].includes(tokens[i])) {
    nodes.push({ key, op: null, value: null });
    continue;
   }
   const op = tokens[i++];
   let value = tokens[i++];
   assert(value && value !== "}", "Missing value after " + key);
   if (value === "{") { value = block(true); assert.equal(tokens[i++], "}", "Unclosed " + key); }
   nodes.push({ key, op, value });
  }
  if (!inner) assert.equal(i, tokens.length, "Unexpected closing brace");
  return nodes;
 }
 return block();
}
const read = file => parse(fs.readFileSync(path.join(mod, file), "utf8"));
const get = (nodes, key) => nodes.find(node => node.key === key)?.value;
const many = (nodes, key) => nodes.filter(node => node.key === key);
function one(nodes, key) {
 const matches = many(nodes, key);
 assert.equal(matches.length, 1, "Expected one " + key);
 return matches[0].value;
}
const walk = nodes => nodes.flatMap(node => [node, ...(Array.isArray(node.value) ? walk(node.value) : [])]);
function indexed(nodes, keyOf = node => node.key, valueOf = node => node.value) {
 const map = new Map();
 for (const node of nodes) {
  const key = keyOf(node);
  assert(!map.has(key), "Duplicate definition " + key);
  map.set(key, valueOf(node));
 }
 return map;
}
const phaseEffects = read("common/scripted_effects/HSM_BAR_phases.txt");
const coreEffects = read("common/scripted_effects/HSM_BAR_core_effects.txt");
const effects = indexed([...phaseEffects, ...coreEffects, ...read("common/scripted_effects/HSM_BAR_service_rewards.txt"),
 ...read("common/scripted_effects/HSM_BAR_social_survey.txt")]);
const phaseTriggers = read("common/scripted_triggers/HSM_BAR_phases.txt");
const triggers = indexed([...phaseTriggers, ...read("common/scripted_triggers/HSM_BAR_development.txt"), ...read("common/scripted_triggers/HSM_BAR_service_gui.txt")
 .filter(n => n.key === "HSM_BAR_service_legacy_visible")]);
const decisions = indexed(one(read("common/decisions/HSM_BAR_republic.txt"), "HSM_BAR_republic_recovery"));
const category = one(read("common/decisions/categories/HSM_BAR_republic.txt"), "HSM_BAR_republic_recovery");
const eventNodes = read("events/HSM_BAR_republic.txt");
const events = indexed(many(eventNodes, "country_event"), node => one(node.value, "id"));
const republic = read("common/national_focus/HSM_BAR_republic.txt");
const directorate = read("common/national_focus/HSM_BAR_directorate.txt");
const common = read("common/national_focus/HSM_BAR_common.txt");
const focusNodes = [...republic, ...directorate, ...common];
const focuses = indexed(many(focusNodes, "shared_focus"), node => one(node.value, "id"));
const trees = indexed(many(focusNodes, "focus_tree"), node => one(node.value, "id"));
const boundaryEffects = new Set(["HSM_BAR_anomalies_initialize", "HSM_BAR_dip_initialize",
 "HSM_BAR_core_refresh", "HSM_BAR_refresh_case_outcomes", "HSM_BAR_collegium_remove_constitution",
 "HSM_BAR_anomalies_pulse"]);
const boundaryTriggers = new Set(["HSM_BAR_case_review_ready", "HSM_BAR_suppression_knowledge_ready"]);
const deathEffects = new Set(["bar_kill_ambrosius", "barrad_kill_leopold", "barrad_kill_asinti",
 "barrad_kill_viira", "barrad_kill_silver"]);
function fresh() {
 return {
  tag: "BAR", originalTag: "BAR", capitulated: false, flags: new Set(), ideas: new Set(),
  dynamic: new Set(), dlc: new Set(), vars: {}, pp: 500, stability: 0.5, warSupport: 0.5, manpower: 1000,
  day: 0, tree: null, done: new Set(), pending: new Map(), scheduled: [], calls: [],
  facts: {}, states: new Map([624, 625, 626, 777].map(id => [id, {
   id, owner: "BAR", controller: "BAR", flags: new Set(["BAR_climate"]),
   modifiers: new Set(["barrad_climate", "barrad_climate2", "barrad_climate3", "unrelated_modifier"])
  }]))
 };
}
function actor() {
 const s = fresh();
 s.flags = new Set(["HSM_BAR_active", "HSM_BAR_directorate", "HSM_BAR_republic_transition"]);
 return s;
}
function service() {
 // Native decision payloads remain the AI route; human adapter coverage lives in ServiceGui.
 const s = actor(); s.ai = true; s.flags.delete("HSM_BAR_republic_transition"); s.flags.add("HSM_BAR_service_founded"); return s;
}
function dispositionFlag(id, choice) {
 return "HSM_BAR_" + (["protect", "restrict"].includes(choice) ? "case_" : "study_") + id + "_" + choice;
}
function localReady(rock = "applied", plants = "reserved") {
 const s = service();
 for (const id of ["rock", "plants"]) s.flags.add("HSM_BAR_study_" + id + "_done");
 s.flags.add(dispositionFlag("rock", rock));
 s.flags.add(dispositionFlag("plants", plants));
 return s;
}
function finalReady(marsh = "applied") {
 const s = localReady();
 for (const flag of ["land_partly_healed", "foreign_mandate", "study_marsh_done",
  "study_amulet_done", "project_wards_done", "study_marsh_" + marsh]) s.flags.add("HSM_BAR_" + flag);
 return s;
}
function conditions(nodes, s, state = null) {
 assert(Array.isArray(nodes), "Expected trigger block");
 return nodes.every(node => condition(node, s, state));
}
function condition({ key, op, value }, s, state) {
 assert.equal(op, "=", "Unsupported trigger operator: " + key);
 if (key === "AND") return conditions(value, s, state);
 if (key === "OR") return value.some(node => condition(node, s, state));
 // HOI4 NOT is NOR over its entries, not the negation of an implicit AND.
 if (key === "NOT") return !value.some(node => condition(node, s, state));
 if (key === "custom_trigger_tooltip") return conditions(value.filter(node => node.key !== "tooltip"), s, state);
 if (triggers.has(key)) {
  assert.equal(value, "yes");
  return conditions(triggers.get(key), s, state);
 }
 if (boundaryTriggers.has(key)) { assert.equal(value, "yes"); return s.facts[key] === true; }
 switch (key) {
  case "tag": return s.tag === value;
  case "original_tag": return s.originalTag === value;
  case "has_country_flag":
   if (!Array.isArray(value)) return s.flags.has(value);
   assert.deepEqual(value.map(n => n.key), ["flag", "value"]);
   assert.equal(value[1].op, "=");
   return s.flags.has(one(value, "flag")) && s.flagValues?.[one(value, "flag")] === Number(one(value, "value"));
  case "is_ai": return (s.ai === true) === (value === "yes");
  case "is_debug": return (s.debug === true) === (value === "yes");
  case "has_capitulated": return s.capitulated === (value === "yes");
  case "has_completed_focus": return s.done.has(value);
  case "has_idea": return s.ideas.has(value);
  case "has_dlc": return s.dlc.has(value.replace(/^"|"$/g, ""));
  case "has_dynamic_modifier": return s.dynamic.has(Array.isArray(value) ? one(value, "modifier") : value);
  case "owns_state": return s.states.get(Number(value))?.owner === s.tag;
  case "controls_state": return s.states.get(Number(value))?.controller === s.tag;
  case "is_controlled_by": assert(state, "is_controlled_by needs STATE scope"); return state.controller === (value === "ROOT" ? s.tag : value);
  case "state": assert(state, "state needs STATE scope"); return state.id === Number(value);
  default: throw Error("Unmodelled trigger: " + key);
 }
}
function execute(nodes, s, state = null) {
 assert(Array.isArray(nodes), "Expected effect block");
 let branch = false;
 for (const { key, op, value } of nodes) {
  assert.equal(op, "=", "Unexpected effect operator: " + key);
  if (key === "if" || key === "else_if") {
   if (key === "if") branch = false;
   if (!branch && conditions(one(value, "limit"), s, state)) {
    branch = true; execute(value.filter(node => node.key !== "limit"), s, state);
   }
  } else if (key === "else") {
   if (!branch) execute(value, s, state);
   branch = true;
  } else if (key === "hidden_effect") {
   execute(value, s, state);
  } else if (boundaryEffects.has(key) || deathEffects.has(key)) {
   assert.equal(value, "yes"); s.calls.push(key);
  } else if (effects.has(key)) {
   assert.equal(value, "yes"); execute(effects.get(key), s, state);
  } else if (/^\d+$/.test(key)) {
   assert(s.states.has(Number(key)), "Missing fixture state " + key);
   execute(value, s, s.states.get(Number(key)));
  } else if (key === "every_owned_state") {
   assert.equal(state, null, "every_owned_state needs COUNTRY scope");
   for (const selected of s.states.values()) {
    if (selected.owner === s.tag && conditions(one(value, "limit"), s, selected))
     execute(value.filter(node => node.key !== "limit"), s, selected);
   }
  } else switch (key) {
   case "set_country_flag": s.flags.add(Array.isArray(value) ? one(value, "flag") : value); break;
   case "clr_country_flag": s.flags.delete(value); break;
   case "add_ideas": s.ideas.add(value); break;
   case "remove_ideas": s.ideas.delete(value); break;
   case "add_dynamic_modifier": s.dynamic.add(one(value, "modifier")); break;
   case "remove_dynamic_modifier": s.dynamic.delete(one(value, "modifier")); break;
   case "clear_variable":
    assert.equal(state, null, "clear_variable fixture needs COUNTRY scope");
    assert.equal(typeof value, "string", "Expected a variable name");
    delete s.vars[value]; break;
   case "set_variable": case "add_to_variable": case "multiply_variable": {
    assert.equal(value.length, 1);
    const entry = value[0], literal = Number(entry.value);
    if (!Number.isFinite(literal)) assert(/^HSM_BAR_\w+$/.test(entry.value), "Unsupported variable reference");
    const amount = Number.isFinite(literal) ? literal : s.vars[entry.value] || 0;
    const before = s.vars[entry.key] || 0;
    s.vars[entry.key] = key === "set_variable" ? amount : key === "add_to_variable" ? before + amount : before * amount;
    break;
   }
   case "add_political_power": s.pp += Number(value); break;
   case "add_stability": s.stability += Number(value); break;
   case "add_war_support": s.warSupport += Number(value); break;
   case "add_manpower": s.manpower += Number(value); break;
   case "country_event": s.scheduled.push({ id: one(value, "id"), day: s.day + Number(get(value, "days") || 0) }); break;
   case "load_focus_tree":
    assert.equal(one(value, "keep_completed"), "yes"); s.tree = one(value, "tree"); break;
   case "add_province_modifier": case "remove_province_modifier": {
    assert(state, key + " needs STATE scope");
    assert.equal(one(one(value, "province"), "all_provinces"), "yes");
    for (const entry of one(value, "static_modifiers")) {
     assert.equal(entry.op, null);
     if (key === "add_province_modifier") state.modifiers.add(entry.key);
     else state.modifiers.delete(entry.key);
    }
    break;
   }
   case "set_state_flag": assert(state); state.flags.add(value); break;
   case "clr_state_flag": assert(state); state.flags.delete(value); break;
   // Native presentation/political commands are outside this phase-state fixture.
   case "set_cosmetic_tag": case "add_popularity": case "add_country_leader_role":
   case "set_politics": case "BAR_captain_gasienica": case "remove_opinion_modifier":
   case "custom_effect_tooltip": case "add_tech_bonus":
    s.calls.push(key); break;
   case "EQS": case "WIT": case "ZES": case "OLV": s.calls.push("foreign:" + key); break;
   default: throw Error("Unmodelled effect: " + key);
  }
 }
}
function snapshot(s) {
 const { calls, ...durable } = s;
 return JSON.stringify(durable, (_, value) => value instanceof Set ? [...value].sort()
  : value instanceof Map ? [...value.entries()] : value);
}
function focusReady(id, s) {
 const focus = focuses.get(id);
 assert(focus, id);
 return many(focus, "prerequisite").every(group => group.value.some(node => s.done.has(node.value))) &&
  many(focus, "mutually_exclusive").every(group => group.value.every(node => !s.done.has(node.value))) &&
  conditions(get(focus, "available") || [], s);
}
function completeFocus(id, s) {
 assert(focusReady(id, s), "Focus unavailable: " + id);
 assert(!s.done.has(id), "Focus already completed: " + id);
 s.done.add(id);
 execute(one(focuses.get(id), "completion_reward"), s);
}
function decisionReady(id, s) {
 const d = decisions.get(id);
 return conditions(one(category, "visible"), s) && conditions(one(d, "visible"), s) &&
  conditions(one(d, "available"), s) && !s.pending.has(id) && s.pp >= Number(one(d, "cost"));
}
function startDecision(id, s) {
 assert(decisionReady(id, s), "Decision unavailable: " + id);
 const d = decisions.get(id);
 s.pp -= Number(one(d, "cost"));
 s.pending.set(id, s.day + Number(one(d, "days_remove")));
}
function finishDecision(id, s) {
 assert(s.pending.has(id));
 s.day = s.pending.get(id);
 s.pending.delete(id);
 const d = decisions.get(id);
 if (!conditions(one(d, "cancel_trigger"), s)) execute(one(d, "remove_effect"), s);
}
function optionEffects(option) { return option.filter(node => !["name", "ai_chance", "trigger"].includes(node.key)); }
function choose(id, index, s) {
 const e = events.get(id);
 assert(conditions(one(e, "trigger"), s), "Scene unavailable: " + id);
 execute(optionEffects(many(e, "option")[index].value), s);
}
function throughDescent() {
 const s = fresh(); execute(effects.get("HSM_BAR_start_directorate"), s);
 assert(!focusReady("HSM_BAR_transition_republic", s), "The survey must be the first focus");
 completeFocus("HSM_BAR_common_reconstruction", s);
 assert(s.ideas.has("poverty1") && s.ideas.has("lack_of_scientists1"));
 completeFocus("HSM_BAR_transition_republic", s);
 for (const name of ["councils", "relief", "survey", "bread", "patients"])
  completeFocus("HSM_BAR_transition_" + name, s);
 startDecision("HSM_BAR_public_survey", s); finishDecision("HSM_BAR_public_survey", s);
 completeFocus("HSM_BAR_transition_cabinet", s);
 startDecision("HSM_BAR_decode_records", s); finishDecision("HSM_BAR_decode_records", s);
 completeFocus("HSM_BAR_transition_descent", s);
 startDecision("HSM_BAR_first_descent", s); finishDecision("HSM_BAR_first_descent", s);
 return s;
}
const decisionFixtures = {
 HSM_BAR_public_survey: { days: 21, cost: 25, flag: "HSM_BAR_survey_recorded", event: 2, make() {
  const s = actor(); s.flags.add("HSM_BAR_public_survey_open"); return s;
 } },
 HSM_BAR_decode_records: { days: 28, cost: 30, flag: "HSM_BAR_records_decoded", event: 3, make() {
  const s = actor(); s.flags.add("HSM_BAR_cabinet_open"); s.flags.add("HSM_BAR_survey_recorded"); return s;
 } },
 HSM_BAR_first_descent: { days: 21, cost: 25, flag: "HSM_BAR_first_descent_returned", event: 4, make() {
  const s = actor(); s.flags.add("HSM_BAR_first_descent_open"); s.flags.add("HSM_BAR_records_decoded"); return s;
 } },
 HSM_BAR_recover_science: { days: 45, cost: 45, flag: "HSM_BAR_recovered_archives", event: 8, make() {
  const s = service(); for (const name of ["archives_open", "records_decoded"]) s.flags.add("HSM_BAR_" + name); return s;
 } },
 HSM_BAR_reclaim_fields: { days: 45, cost: 45, flag: "HSM_BAR_land_partly_healed", event: 6, make: localReady },
 HSM_BAR_heal_homeland: { days: 75, cost: 75, flag: "HSM_BAR_land_healed", event: 7, make: finalReady }
};
const invalidations = {
 "lost control of 624": s => { s.states.get(624).controller = "WIT"; },
 "lost ownership of 624": s => { s.states.get(624).owner = "WIT"; },
 "inactive": s => { s.flags.delete("HSM_BAR_active"); },
 "route lost": s => { s.flags.delete("HSM_BAR_directorate"); },
 "capitulated": s => { s.capitulated = true; },
 "dissolved": s => { execute(effects.get("HSM_BAR_dissolve_institutions"), s); },
 "wrong country": s => { s.tag = "WIT"; }
};
let passed = 0, failed = 0;
function check(name, action) {
 try { action(); passed++; console.log("PASS: " + name); }
 catch (error) { failed++; console.error("FAIL: " + name + "\n" + error.stack); }
}

check("parser handles comments, quoted braces and bare modifier lists; rejects malformed blocks", () => {
 const p = parse('x = { name = "{ # not syntax }" # comment }\n values = { a b } x = 1 x = 2 }');
 assert.equal(one(one(p, "x"), "name"), '"{ # not syntax }"');
 assert.equal(many(one(p, "x"), "x").length, 2);
 assert.equal(one(one(p, "x"), "values")[0].op, null);
 assert.throws(() => parse("x = { y = 1"));
 assert.throws(() => parse("x = }"));
 assert.throws(() => parse("x = 1 }"));
 assert.throws(() => conditions(parse("political_power = 1"), actor()), /Unmodelled/);
 assert.throws(() => execute(parse("invented_effect = yes"), actor()), /Unmodelled/);
});
check("NOT has native NOR semantics; NOT AND expresses failure of any requirement", () => {
 const s = actor(); s.flags.add("A");
 assert(!conditions(parse("NOT = { has_country_flag = A has_country_flag = B }"), s));
 assert(conditions(parse("NOT = { AND = { has_country_flag = A has_country_flag = B } }"), s));
 s.flags.delete("A");
 assert(conditions(parse("NOT = { has_country_flag = A has_country_flag = B }"), s));
});
check("entry and dissolution delete retired meters without touching unrelated saved variables", () => {
 for (const effect of ["HSM_BAR_initialize_common", "HSM_BAR_dissolve_institutions"]) {
  const s = fresh();
  s.vars = { HSM_BAR_public_trust: 57, HSM_BAR_capacity: 83, unrelated: 19 };
  execute(effects.get(effect), s);
  assert(!Object.hasOwn(s.vars, "HSM_BAR_public_trust"));
  assert(!Object.hasOwn(s.vars, "HSM_BAR_capacity"));
  assert.equal(s.vars.unrelated, 19);
 }
 assert.throws(() => execute(parse("clear_variable = { var = invented }"), fresh()), /variable name/);
});
check("Republic entry loads the civil tree without founding or activating the Service", () => {
 const s = fresh(); execute(effects.get("HSM_BAR_start_directorate"), s);
 assert.equal(s.tree, "HSM_BAR_republic_tree");
 for (const flag of ["HSM_BAR_active", "HSM_BAR_directorate", "HSM_BAR_republic_transition"]) assert(s.flags.has(flag));
 for (const flag of ["HSM_BAR_service_founded", "HSM_BAR_covert_structure_initialized",
  "HSM_BAR_field_research_open", "HSM_BAR_region_local_open", "HSM_BAR_recovered_archives"])
  assert(!s.flags.has(flag), flag);
 assert(!s.ideas.has("HSM_BAR_provisional_watch"));
 assert(!s.dynamic.has("HSM_BAR_service_capacity"));
 assert.equal(s.vars.HSM_BAR_cover_integrity, undefined);
 assert(!focusReady("HSM_BAR_dir_charter", s));
 assert(s.scheduled.some(event => event.id === "hsm_bar_republic.1" && event.day === 3));
});
check("human Republic decisions remain visible until founding, then move to the dedicated GUI", () => {
 const s = actor();
 assert(conditions(one(category, "visible"), s));
 s.flags.add("HSM_BAR_service_founded");
 assert(!conditions(one(category, "visible"), s));
 s.ai = true;
 assert(conditions(one(category, "visible"), s));
});
check("discovery, decoded records, returned expedition and incident choice precede founding", () => {
 const s = fresh(); execute(effects.get("HSM_BAR_start_directorate"), s);
 assert(!focusReady("HSM_BAR_transition_cabinet", s));
 assert(!decisionReady("HSM_BAR_decode_records", s));
 assert(!decisionReady("HSM_BAR_first_descent", s));
 const before = snapshot(s); execute(effects.get("HSM_BAR_found_service"), s); assert.equal(snapshot(s), before);
 const returned = throughDescent();
 assert(returned.flags.has("HSM_BAR_survey_recorded"));
 assert(returned.flags.has("HSM_BAR_records_decoded"));
 assert(returned.flags.has("HSM_BAR_first_descent_returned"));
 assert(!returned.flags.has("HSM_BAR_first_incident_resolved"));
 assert(!focusReady("HSM_BAR_transition_commission", returned));
 assert(!returned.flags.has("HSM_BAR_service_founded"));
 assert(!returned.flags.has("HSM_BAR_recovered_archives"));
});
for (const option of [0, 1]) check("first-descent outcome " + option + " permits one guarded founding", () => {
 const s = throughDescent(); choose("hsm_bar_republic.4", option, s);
 completeFocus("HSM_BAR_transition_commission", s);
 assert.equal(s.tree, "HSM_BAR_directorate_tree");
 assert(s.done.has("HSM_BAR_transition_republic"));
 assert(s.flags.has("HSM_BAR_service_founded"));
 assert(!s.flags.has("HSM_BAR_republic_transition"));
 assert(!Object.hasOwn(s.vars, "HSM_BAR_cover_integrity"));
 assert(!Object.hasOwn(s.vars, "HSM_BAR_service_coordination"));
 assert(s.flags.has("HSM_BAR_case_rock_known"));
 assert(![...s.flags].some(flag => /^HSM_BAR_study_.*_done$/.test(flag)));
 assert(s.ideas.has("HSM_BAR_provisional_watch"));
 assert(s.dynamic.has("HSM_BAR_service_capacity"));
 const after = snapshot(s); execute(effects.get("HSM_BAR_found_service"), s); assert.equal(snapshot(s), after);
});
check("founding rechecks both its story prerequisites and current field access", () => {
 for (const missing of ["HSM_BAR_records_decoded", "HSM_BAR_first_incident_resolved"]) {
  const s = throughDescent(); choose("hsm_bar_republic.4", 0, s); s.flags.delete(missing);
  const before = snapshot(s); execute(effects.get("HSM_BAR_found_service"), s); assert.equal(snapshot(s), before);
 }
 for (const invalidate of Object.values(invalidations)) {
  const s = throughDescent(); choose("hsm_bar_republic.4", 0, s); invalidate(s);
  const before = snapshot(s); execute(effects.get("HSM_BAR_found_service"), s); assert.equal(snapshot(s), before);
 }
});

for (const [id, fixture] of Object.entries(decisionFixtures)) {
 check(id + ": paid timed completion awards its result once and hides retry", () => {
  const s = fixture.make(); const d = decisions.get(id);
  assert.equal(Number(one(d, "cost")), fixture.cost);
  assert.equal(Number(one(d, "days_remove")), fixture.days);
  const pp = s.pp; startDecision(id, s);
  assert.equal(s.pp, pp - fixture.cost);
  assert(!s.flags.has(fixture.flag)); assert(!decisionReady(id, s));
  finishDecision(id, s);
  assert.equal(s.day, fixture.days); assert(s.flags.has(fixture.flag));
  assert(s.scheduled.some(event => event.id === "hsm_bar_republic." + fixture.event));
  assert(!decisionReady(id, s));
  const after = snapshot(s); execute(one(d, "remove_effect"), s); assert.equal(snapshot(s), after);
 });
 check(id + ": each access loss cancels a running decision", () => {
  for (const [label, invalidate] of Object.entries(invalidations)) {
   const s = fixture.make(); startDecision(id, s); invalidate(s);
   assert(conditions(one(decisions.get(id), "cancel_trigger"), s), id + ": " + label + " must cancel");
  }
 });
 check(id + ": stale completion is inert and restored access permits a fresh paid retry", () => {
  for (const [label, invalidate] of Object.entries(invalidations)) {
   const s = fixture.make(); startDecision(id, s); invalidate(s);
   const before = snapshot(s); execute(one(decisions.get(id), "remove_effect"), s);
   assert.equal(snapshot(s), before, label + " must not award completion");
  }
  const s = fixture.make(); startDecision(id, s);
  s.states.get(624).controller = "WIT";
  finishDecision(id, s); assert(!s.flags.has(fixture.flag));
  s.states.get(624).controller = "BAR";
  assert(decisionReady(id, s)); startDecision(id, s); finishDecision(id, s);
  assert(s.flags.has(fixture.flag)); assert.equal(s.pp, 500 - fixture.cost * 2);
 });
}
check("loss of each individual required flag cancels, blocks stale completion and permits retry", () => {
 for (const [id, fixture] of Object.entries(decisionFixtures)) {
  const initial = fixture.make();
  for (const flag of [...initial.flags].filter(flag => flag !== "HSM_BAR_republic_transition")) {
   const s = fixture.make(); startDecision(id, s); s.flags.delete(flag);
   assert(!conditions(one(decisions.get(id), "available"), s), id + ": fixture flag must be required: " + flag);
   assert(conditions(one(decisions.get(id), "cancel_trigger"), s), id + ": loss of " + flag + " must cancel");
   const before = snapshot(s); execute(one(decisions.get(id), "remove_effect"), s);
   assert.equal(snapshot(s), before, id + ": missing " + flag);
   finishDecision(id, s); assert(!s.flags.has(fixture.flag));
   s.flags.add(flag);
   assert(!conditions(one(decisions.get(id), "cancel_trigger"), s));
   assert(decisionReady(id, s)); startDecision(id, s); finishDecision(id, s);
   assert(s.flags.has(fixture.flag));
  }
 }
});
for (const [id, e] of events) check(id + ": options are once-only and stale scenes are inert", () => {
 assert.equal(one(e, "is_triggered_only"), "yes");
 for (const option of many(e, "option")) {
  const s = finalReady(); s.flags.add("HSM_BAR_first_descent_returned");
  assert(conditions(one(e, "trigger"), s));
  execute(optionEffects(option.value), s);
  assert(s.flags.has("HSM_BAR_republic_event_" + id.split(".")[1] + "_done"));
  assert(!conditions(one(e, "trigger"), s));
  const after = snapshot(s);
  for (const other of many(e, "option")) execute(optionEffects(other.value), s);
  assert.equal(snapshot(s), after, "A later option must not overwrite the first choice");
  for (const mode of ["inactive", "route lost", "dissolved", "capitulated", "wrong country"]) {
   const stale = finalReady(); stale.flags.add("HSM_BAR_first_descent_returned"); invalidations[mode](stale);
   assert(!conditions(one(e, "trigger"), stale));
   const before = snapshot(stale); execute(optionEffects(option.value), stale); assert.equal(snapshot(stale), before);
  }
 }
});
check("all 16 interim/final disposition combinations satisfy local healing without bypassing studies", () => {
 for (const rock of ["applied", "reserved", "protect", "restrict"])
 for (const plants of ["applied", "reserved", "protect", "restrict"]) {
  const s = localReady(rock, plants);
  assert(conditions(triggers.get("HSM_BAR_local_reclamation_ready"), s));
  for (const missing of ["HSM_BAR_service_founded", "HSM_BAR_study_rock_done", "HSM_BAR_study_plants_done",
   dispositionFlag("rock", rock), dispositionFlag("plants", plants)]) {
   s.flags.delete(missing); assert(!conditions(triggers.get("HSM_BAR_local_reclamation_ready"), s), missing);
   s.flags.add(missing);
  }
  startDecision("HSM_BAR_reclaim_fields", s); finishDecision("HSM_BAR_reclaim_fields", s);
  assert(s.flags.has("HSM_BAR_land_partly_healed"));
  for (const flag of ["HSM_BAR_foreign_mandate", "HSM_BAR_study_marsh_done", "HSM_BAR_study_marsh_reserved",
   "HSM_BAR_study_amulet_done", "HSM_BAR_project_wards_done"]) s.flags.add(flag);
  startDecision("HSM_BAR_heal_homeland", s); finishDecision("HSM_BAR_heal_homeland", s);
  assert(s.flags.has("HSM_BAR_land_healed"));
 }
});
check("final object choices made before interim outcomes do not softlock either healing programme", () => {
 for (const rock of ["protect", "restrict"]) for (const plants of ["protect", "restrict"]) {
  const s = localReady(rock, plants);
  for (const id of ["rock", "plants"]) for (const interim of ["applied", "reserved"])
   assert(!s.flags.has(dispositionFlag(id, interim)));
  startDecision("HSM_BAR_reclaim_fields", s);
  const required = dispositionFlag("rock", rock);
  s.flags.delete(required);
  assert(conditions(one(decisions.get("HSM_BAR_reclaim_fields"), "cancel_trigger"), s));
  finishDecision("HSM_BAR_reclaim_fields", s); assert(!s.flags.has("HSM_BAR_land_partly_healed"));
  s.flags.add(required); startDecision("HSM_BAR_reclaim_fields", s); finishDecision("HSM_BAR_reclaim_fields", s);
  for (const flag of ["HSM_BAR_foreign_mandate", "HSM_BAR_study_marsh_done", "HSM_BAR_study_marsh_applied",
   "HSM_BAR_study_amulet_done", "HSM_BAR_project_wards_done"]) s.flags.add(flag);
  startDecision("HSM_BAR_heal_homeland", s); finishDecision("HSM_BAR_heal_homeland", s);
  assert(s.flags.has("HSM_BAR_land_healed"));
 }
});
check("first recovery changes only state 624 and preserves unrelated province modifiers", () => {
 const s = localReady(); const other = JSON.stringify([...s.states].filter(([id]) => id !== 624), (_, v) => v instanceof Set ? [...v] : v);
 execute(effects.get("HSM_BAR_reclaim_first_fields"), s);
 assert.deepEqual([...s.states.get(624).modifiers].sort(), ["HSM_BAR_recovering_soil", "unrelated_modifier"]);
 assert.equal(JSON.stringify([...s.states].filter(([id]) => id !== 624), (_, v) => v instanceof Set ? [...v] : v), other);
 assert.equal(s.stability, 0.53);
 const after = snapshot(s); execute(effects.get("HSM_BAR_reclaim_first_fields"), s); assert.equal(snapshot(s), after);
});
check("archive recovery cannot grant technologies, revive people or fake alive markers", () => {
 const sources = [...phaseEffects, ...phaseTriggers, ...eventNodes, ...republic,
  ...read("common/decisions/HSM_BAR_republic.txt")];
 const forbidden = new Set(["set_technology", "recruit_character", "promote_character",
  "add_country_leader_role", "create_country_leader", "activate_advisor"]);
 for (const node of walk(sources)) {
  assert(!forbidden.has(node.key), node.key);
  if (["set_country_flag", "clr_country_flag"].includes(node.key)) {
   const flag = Array.isArray(node.value) ? get(node.value, "flag") : node.value;
   assert(!/^barrad_.*_alive$/.test(flag), flag);
  }
 }
 const d = decisions.get("HSM_BAR_recover_science"), s = decisionFixtures.HSM_BAR_recover_science.make();
 execute(one(d, "remove_effect"), s);
 assert(s.flags.has("HSM_BAR_recovered_archives"));
 assert(!s.flags.has("HSM_BAR_study_rock_done"));
 const archiveFocus = one(focuses.get("HSM_BAR_dir_archives"), "completion_reward");
 assert(!walk(archiveFocus).some(node => node.key === "set_country_flag" && node.value === "HSM_BAR_recovered_archives"));
});
check("foreign mandate requires recovered archives and partial healing, and preserves earlier focuses", () => {
 const id = "HSM_BAR_dir_foreign_mandate", s = service();
 for (const group of many(focuses.get(id), "prerequisite")) for (const node of group.value) s.done.add(node.value);
 assert(!focusReady(id, s)); s.flags.add("HSM_BAR_land_partly_healed"); assert(!focusReady(id, s));
 s.flags.delete("HSM_BAR_land_partly_healed"); s.flags.add("HSM_BAR_recovered_archives"); assert(!focusReady(id, s));
 s.flags.add("HSM_BAR_land_partly_healed"); assert(focusReady(id, s));
 s.done.add("HSM_BAR_transition_commission"); completeFocus(id, s);
 assert(s.flags.has("HSM_BAR_foreign_mandate")); assert.equal(s.tree, "HSM_BAR_directorate_world_tree");
 assert(s.done.has("HSM_BAR_transition_commission"));
});
check("final healing needs foreign marsh findings, amulet study, wards and local recovery", () => {
 for (const disposition of ["applied", "reserved"]) {
  const s = finalReady(disposition); assert(conditions(triggers.get("HSM_BAR_final_reclamation_ready"), s));
  for (const suffix of ["land_partly_healed", "foreign_mandate", "study_marsh_done", "study_amulet_done",
   "project_wards_done", "study_marsh_" + disposition, "study_rock_done", "study_plants_done"]) {
   const flag = "HSM_BAR_" + suffix; s.flags.delete(flag);
   assert(!conditions(triggers.get("HSM_BAR_final_reclamation_ready"), s), flag); s.flags.add(flag);
  }
 }
});
check("final healing affects only owned controlled homeland states, never occupations or other land", () => {
 for (const exclusion of ["none", "owned but occupied", "controlled but foreign owned"]) {
  const s = finalReady(); s.states.get(624).modifiers.add("HSM_BAR_recovering_soil");
  if (exclusion === "owned but occupied") s.states.get(625).controller = "WIT";
  if (exclusion === "controlled but foreign owned") s.states.get(625).owner = "WIT";
  execute(effects.get("HSM_BAR_reclaim_homeland"), s);
  assert(s.flags.has("HSM_BAR_land_healed"));
  for (const id of [624, 625, 626, 777]) {
   const target = s.states.get(id), expected = id !== 777 && (id !== 625 || exclusion === "none");
   assert.equal(target.flags.has("HSM_BAR_land_restored"), expected, id + ": " + exclusion);
   assert.equal(target.flags.has("BAR_climate"), !expected);
   assert(target.modifiers.has("unrelated_modifier"));
   assert.equal(target.modifiers.has("barrad_climate"), !expected);
   if (expected) assert(!target.modifiers.has("HSM_BAR_recovering_soil"));
  }
  const after = snapshot(s); execute(effects.get("HSM_BAR_reclaim_homeland"), s); assert.equal(snapshot(s), after);
 }
});
check("doctrinal commission cannot bypass homeland healing or previous evidence requirements", () => {
 const id = "HSM_BAR_dir_commission", s = service();
 for (const group of many(focuses.get(id), "prerequisite")) for (const node of group.value) s.done.add(node.value);
 s.facts.HSM_BAR_case_review_ready = true; s.flags.add("HSM_BAR_cult_network_broken");
 assert(!focusReady(id, s)); s.flags.add("HSM_BAR_land_healed"); assert(focusReady(id, s));
 s.facts.HSM_BAR_case_review_ready = false; assert(!focusReady(id, s));
 s.facts.HSM_BAR_case_review_ready = true; s.flags.delete("HSM_BAR_cult_network_broken"); assert(!focusReady(id, s));
});
check("institutional focuses never directly award study knowledge or completed projects", () => {
 for (const [id, focus] of focuses) {
  for (const node of walk(one(focus, "completion_reward"))) {
   assert.notEqual(node.key, "set_technology", id);
   if (node.key === "set_country_flag") {
    const flag = Array.isArray(node.value) ? get(node.value, "flag") : node.value;
    assert(!/^HSM_BAR_(study_.*_(done|applied|reserved)|project_.*_done|recovered_archives)$/.test(flag), id + ": " + flag);
   }
   assert(!/^HSM_BAR_(cases_.*_complete|research_.*_complete|reclaim_first_fields|reclaim_homeland)$/.test(node.key), id);
  }
 }
 for (const id of ["HSM_BAR_dir_suppression_lab", "HSM_BAR_dir_activation"])
  assert(walk(one(focuses.get(id), "available")).some(node => node.key === "HSM_BAR_suppression_knowledge_ready"));
});

const originalPositions = {
 charter: [8,0], names: [5,1], seal_labs: [11,1], watchmen: [3,2], evidence: [7,2], training: [11,2],
 register: [7,3], radio: [3,3], archives: [11,3], agency: [5,4], storage: [11,4], foreign_mandate: [8,5],
 world: [8,7], equus: [0,8], griffonia: [4,8], north: [8,8], riverlands: [12,8], zebrica: [16,8],
 liaison: [3,10], trafficking: [8,10], rulers: [13,10], countercult: [8,11], foreign_protocol: [3,11],
 remains: [13,11], commission: [8,12], coexistence: [5,13], normalization: [11,13], custody_law: [3,14],
 open_report: [7,14], quiet_watch: [5,15], sealed_orders: [11,14], suppression_lab: [11,15], activation: [11,16], aftermath: [11,17]
};
check("all 34 existing Directorate nodes retain their horizontal position and six-row offset", () => {
 assert.equal(many(directorate, "shared_focus").length, 34);
 for (const [short, [x,y]] of Object.entries(originalPositions)) {
  const focus = focuses.get("HSM_BAR_dir_" + short);
  assert.equal(Number(one(focus, "x")), x, short); assert.equal(Number(one(focus, "y")), y + 6, short);
 }
});
function members(tree) {
 const included = new Set(many(tree, "shared_focus").map(node => node.value));
 let changed;
 do {
  changed = false;
  for (const [id, focus] of focuses) {
   const parents = many(focus, "prerequisite").flatMap(node => node.value.map(ref => ref.value));
   if (!included.has(id) && parents.some(parent => included.has(parent))) { included.add(id); changed = true; }
  }
 } while (changed);
 return included;
}
check("three trees resolve every shared, prerequisite and exclusive reference without cycles", () => {
 assert.equal(trees.size, 3); assert.equal(focuses.size, 71);
 assert.equal(many(common, "shared_focus").length, 28);
 for (const [id, focus] of focuses) for (const key of ["prerequisite", "mutually_exclusive"])
  for (const block of many(focus, key)) for (const ref of block.value) assert(focuses.has(ref.value), id + ": " + ref.value);
 const seen = new Set(), visiting = new Set();
 function visit(id) {
  assert(!visiting.has(id), "Prerequisite cycle: " + id); if (seen.has(id)) return;
  visiting.add(id);
  for (const p of many(focuses.get(id), "prerequisite")) for (const ref of p.value) visit(ref.value);
  visiting.delete(id); seen.add(id);
 }
 for (const id of focuses.keys()) visit(id);
 for (const [id, tree] of trees) {
  const refs = many(tree, "shared_focus").map(node => node.value);
  assert.equal(new Set(refs).size, refs.length, id + " duplicate tree member");
  for (const ref of refs) assert(focuses.has(ref), ref);
  for (const member of members(tree)) for (const p of many(focuses.get(member), "prerequisite"))
   for (const ref of p.value) assert(members(tree).has(ref.value), id + ": missing parent " + ref.value);
 }
});
check("Republic and local trees do not leak later-stage descendants; transitions remain visible", () => {
 const first = members(trees.get("HSM_BAR_republic_tree"));
 const second = members(trees.get("HSM_BAR_directorate_tree"));
 const third = members(trees.get("HSM_BAR_directorate_world_tree"));
 assert.equal(first.size, 37); assert.equal(second.size, 49); assert.equal(third.size, 71);
 for (const id of first) { assert(second.has(id)); assert(third.has(id)); assert(!id.startsWith("HSM_BAR_dir_")); }
 for (const id of second) assert(third.has(id));
 assert(!second.has("HSM_BAR_dir_world"));
 assert.equal(many(focuses.get("HSM_BAR_dir_charter"), "prerequisite").length, 0);
 assert.equal(many(focuses.get("HSM_BAR_dir_world"), "prerequisite").length, 0);
});
check("resolved tree coordinates do not overlap and every prerequisite is above its child", () => {
 const resolved = new Map();
 function position(id, ancestry = new Set()) {
  if (resolved.has(id)) return resolved.get(id);
  assert(!ancestry.has(id), "Relative-position cycle: " + id); ancestry.add(id);
  const f = focuses.get(id), relative = get(f, "relative_position_id");
  const [ox, oy] = relative ? position(relative, ancestry) : [0, 0];
  const p = [Number(one(f, "x")) + ox, Number(one(f, "y")) + oy];
  assert(p.every(Number.isFinite), id); resolved.set(id, p); return p;
 }
 for (const [treeId, tree] of trees) {
  const placed = [];
  for (const id of members(tree)) {
   const [x,y] = position(id);
   for (const [other, ox, oy] of placed)
    assert(y !== oy || Math.abs(x - ox) >= 2, `${treeId}: ${id} overlaps ${other} at row ${y}`);
   placed.push([id,x,y]);
   for (const p of many(focuses.get(id), "prerequisite")) for (const ref of p.value)
    assert(position(ref.value)[1] < y, id + " is not below " + ref.value);
  }
 }
});
check("new scene calls and phase helpers resolve; scene inventory remains ten", () => {
 assert.equal(events.size, 10); assert.equal(decisions.size, 6);
 const nodes = walk([...phaseEffects, ...republic, ...read("common/decisions/HSM_BAR_republic.txt"), ...coreEffects]);
 for (const node of nodes) {
  if (node.key === "country_event" && String(get(node.value, "id")).startsWith("hsm_bar_republic."))
   assert(events.has(get(node.value, "id")), get(node.value, "id"));
  if (node.key === "load_focus_tree" && String(get(node.value, "tree")).startsWith("HSM_BAR_directorate"))
   assert(trees.has(get(node.value, "tree")));
 }
 for (const id of events.keys()) assert(nodes.some(node => node.key === "country_event" && get(node.value, "id") === id), id + " is unreachable");
});
check("state/province commands and static modifiers match installed engine and EaW definitions", () => {
 const doc = fs.readFileSync(path.join(game, "documentation/effects_documentation.md"), "utf8");
 const tdoc = fs.readFileSync(path.join(game, "documentation/triggers_documentation.md"), "utf8");
 function section(source, key) {
  const start = source.indexOf("## " + key + "\n") >= 0 ? source.indexOf("## " + key + "\n") : source.indexOf("## " + key + "\r\n");
  assert(start >= 0, "Undocumented command " + key);
  const end = source.indexOf("\n## ", start + 3);
  return source.slice(start, end < 0 ? undefined : end);
 }
 for (const key of ["add_province_modifier", "remove_province_modifier", "set_state_flag", "clr_state_flag"])
  assert(section(doc, key).includes("Supported Scopes: STATE"), key);
 assert(section(doc, "every_owned_state").includes("Supported Scopes: COUNTRY"));
 for (const [key, scope] of [["state", "STATE"], ["is_controlled_by", "STATE"], ["owns_state", "COUNTRY"],
  ["controls_state", "COUNTRY"], ["has_capitulated", "COUNTRY"]])
  assert(section(tdoc, key).includes("Supported Scopes: " + scope), key);
 const inherited = parse(fs.readFileSync(path.join(eaw, "common/modifiers/eaw_static_modifiers.txt"), "utf8"));
 for (const name of ["barrad_climate", "barrad_climate2", "barrad_climate3"]) assert(one(inherited, name));
 const soil = one(read("common/modifiers/HSM_BAR_land.txt"), "HSM_BAR_recovering_soil");
 assert(soil.length > 0);
 const mdoc = fs.readFileSync(path.join(game, "documentation/modifiers_documentation.md"), "utf8");
 for (const modifier of soil) assert(mdoc.includes(modifier.key), modifier.key);
 for (const effect of walk(phaseEffects).filter(node => ["add_province_modifier", "remove_province_modifier"].includes(node.key))) {
  assert.equal(one(one(effect.value, "province"), "all_provinces"), "yes");
  for (const modifier of one(effect.value, "static_modifiers")) assert(["barrad_climate", "barrad_climate2", "barrad_climate3", "HSM_BAR_recovering_soil"].includes(modifier.key));
 }
 assert.throws(() => execute(parse("add_province_modifier = { static_modifiers = { barrad_climate } province = { all_provinces = yes } }"), actor()), /STATE/);
});

check("debug friendship shortcut dispatches the real two-choice ending once without route or resource writes", () => {
 const d = one(one(read("common/decisions/HSM_BAR_debug.txt"), "debug_decisions"), "HSM_BAR_debug_friendship_ending");
 const s = fresh(); s.debug = true; s.flags.add("barrad_endgame"); s.flagValues = { barrad_endgame: 0 };
 for (const gate of ["allowed", "visible", "available"]) assert(conditions(one(d, gate), s));
 assert.equal(one(d, "cost"), "0"); assert.equal(one(d, "fire_only_once"), "yes");
 assert.equal(one(one(d, "ai_will_do"), "factor"), "0");
 assert.equal(get(d, "days_remove"), undefined);
 const before = structuredClone(s);
 execute(one(d, "complete_effect"), s);
 before.flags.add("HSM_BAR_debug_friendship_requested");
 before.scheduled.push({ id: "barrad_end.2", day: 0 });
 assert.deepEqual(s, before);
 execute(one(d, "complete_effect"), s);
 assert.deepEqual(s, before);
 assert(!conditions(one(d, "visible"), s));
 const ending = many(read("events/Barrad Events.txt"), "country_event").find(n => get(n.value, "id") === "barrad_end.2").value;
 assert.deepEqual(many(ending, "option").map(n => get(n.value, "name")), ["HSM_BAR_core_fall_collegium", "HSM_BAR_core_fall_directorate"]);
});
check("debug shortcut is hidden, disabled and inert for normal play, AI, foreign tags and ended routes", () => {
 const d = one(one(read("common/decisions/HSM_BAR_debug.txt"), "debug_decisions"), "HSM_BAR_debug_friendship_ending");
 const changes = [s => { s.debug = false; }, s => { s.ai = true; }, s => { s.tag = "EQS"; },
  s => { s.capitulated = true; }, s => { s.flagValues.barrad_endgame = 1; },
  s => { s.flagValues.barrad_endgame = 2; }, s => { s.flags.delete("barrad_endgame"); },
  ...["HSM_BAR_active", "BAR_end_of_pentarchy", "HSM_BAR_debug_friendship_requested"].map(f => s => s.flags.add(f))];
 for (const change of changes) {
  const s = fresh(); s.debug = true; s.flags.add("barrad_endgame"); s.flagValues = { barrad_endgame: 0 };
  change(s); const before = structuredClone(s);
  for (const gate of ["visible", "available"]) assert(!conditions(one(d, gate), s));
  execute(one(d, "complete_effect"), s); assert.deepEqual(s, before);
 }
 const history = parse(fs.readFileSync(path.join(eaw, "history/countries/BAR - Baard.txt"), "utf8"));
 assert(many(history, "set_country_flag").some(n => Array.isArray(n.value) && get(n.value, "flag") === "barrad_endgame" && get(n.value, "value") === "0"));
 const tdoc = fs.readFileSync(path.join(game, "documentation/triggers_documentation.md"), "utf8");
 assert.match(tdoc, /## is_debug[\s\S]*?launched with -debug argument/);
});

console.log(`Barrad phases: ${passed} passed, ${failed} failed scenario groups.`);
console.log("Static fixtures only: external registries/rewards are call boundaries; no in-game timing, UI or combat validation.");
if (failed) process.exitCode = 1;
