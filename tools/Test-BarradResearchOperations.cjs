"use strict";

// Run from any directory: node tools/Test-BarradResearchOperations.cjs
// Deterministic fixtures interpret the tested Clausewitz subset, not the game engine.
// Registry predicates are mocked at the operations boundary. They do not validate
// the main registry's corpse/identity/custody model or engine timing and UI behavior.
// Core refresh is mocked only at its call boundary; variable writes execute normally.
const fs = require("node:fs");
const path = require("node:path");
const root = path.resolve(__dirname, "..");
const modRoot = path.join(root, "mod", "HoISubmod");
const parse = function parse(text){
const raw=text.replace(/^\uFEFF/,"");
const tok=raw.match(/"(?:\\.|[^"\\])*"|#[^\r\n]*|[{}]|[<>!=]=?|[^\s{}=<>!#"]+/g)?.filter(x=>!x.startsWith("#"))??[];
let i=0;
function body(nested=false){
const entries=[];
while(i<tok.length&&tok[i]!=="}"){
const key=tok[i++]; if(key==="{")throw Error("anonymous block not expected");
if(!["=","<",">","<=",">=","!="].includes(tok[i])){entries.push({key,op:null,val:null});continue;}
const op=tok[i++]; let val=tok[i++];
if(val==="{"){val=body(true);if(tok[i++]!=="}")throw Error("unclosed "+key);}
entries.push({key,op,val});
}
if(!nested&&i!==tok.length)throw Error("unexpected closing brace");
return entries;
}
return body();
};
const read = rel => parse(fs.readFileSync(path.join(modRoot, rel), "utf8"));
const get = (a, k) => a.find(n => n.key === k)?.val;
const map = a => Object.fromEntries(a.map(n => [n.key, n.val]));
const effects = map(read("common/scripted_effects/HSM_BAR_research_effects.txt"));
const triggers = {
    ...map(read("common/scripted_triggers/HSM_BAR_collegium_triggers.txt")),
    ...map(read("common/scripted_triggers/HSM_BAR_cases.txt")),
    ...map(read("common/scripted_triggers/HSM_BAR_research_triggers.txt")),
    ...map(read("common/scripted_triggers/HSM_BAR_operations_triggers.txt"))
};
const decisions = map(get(read("common/decisions/HSM_BAR_research_decisions.txt"), "HSM_BAR_research_category"));
const events = Object.fromEntries(read("events/HSM_BAR_research_events.txt")
    .filter(n => n.key === "country_event").map(n => [get(n.val, "id"), n.val]));
const operations = read("common/operations/HSM_BAR_operations.txt");
const fixtures = [
    {
        "id": "clinic",
        "event": 1,
        "route": "collegium",
        "cost": 60,
        "choices": [
            {
                "id": "consent",
                "cost": 25,
                "stability": 0.03
            },
            {
                "id": "expedience",
                "cost": 10,
                "stability": -0.04,
                "days": 365
            }
        ]
    },
    {
        "id": "grid",
        "event": 2,
        "route": "collegium",
        "parent": "clinic",
        "cost": 75,
        "choices": [
            {
                "id": "distributed",
                "cost": 35,
                "stability": 0.02,
                "days": 730
            },
            {
                "id": "central",
                "cost": 20,
                "stability": -0.02,
                "days": 730
            }
        ]
    },
    {
        "id": "wards",
        "event": 3,
        "route": "both",
        "cost": 60,
        "choices": [
            {
                "id": "personal",
                "cost": 25,
                "stability": 0.03,
                "refresh": true
            },
            {
                "id": "monitoring",
                "cost": 15,
                "stability": -0.03,
                "refresh": true
            }
        ]
    },
    {
        "id": "containment",
        "event": 4,
        "route": "directorate",
        "parent": "wards",
        "cost": 80,
        "choices": [
            {
                "id": "layered",
                "cost": 35
            },
            {
                "id": "sealed",
                "cost": 20,
                "refresh": true,
                "days": 730
            }
        ]
    },
    {
        "id": "forensics",
        "event": 5,
        "route": "directorate",
        "parent": "containment",
        "field": true,
        "cost": 75,
        "choices": [
            {
                "id": "reviewed",
                "cost": 35,
                "refresh": true
            },
            {
                "id": "classified",
                "cost": 20,
                "refresh": true
            }
        ]
    },
    {
        "id": "suppression",
        "event": 6,
        "route": "directorate",
        "parent": "forensics",
        "field": true,
        "normalization": true,
        "cost": 100,
        "choices": [
            {
                "id": "reversible",
                "cost": 40,
                "refresh": true
            },
            {
                "id": "permanent",
                "cost": 50,
                "refresh": true,
                "days": 730
            }
        ]
    }
];
const researchVariants = fixtures.flatMap(project => project.route === "both"
    ? ["collegium", "directorate"].map(route => ({ ...project, route }))
    : [project]);
const operationFixtures = [
    {
        "id": "recon"
    },
    {
        "id": "archive"
    },
    {
        "id": "relic",
        "gate": "containment"
    },
    {
        "id": "remains",
        "gate": "forensics"
    }
];

const unquote = value => typeof value === "string" ? value.replace(/^"|"$/g, "") : value;
const yes = value => unquote(value) === "yes";

function evaluate(nodes, state, actor = state) {
    return nodes.every(({ key, val }) => {
        if (key === "tooltip") return true;
        if (["AND", "hidden_trigger", "custom_trigger_tooltip"].includes(key)) {
            return evaluate(val, state, actor);
        }
        if (key === "OR") return val.some(node => evaluate([node], state, actor));
        if (key === "NOT") return !val.some(node => evaluate([node], state, actor));
        if (key === "FROM") return evaluate(val, actor.target, actor);
        if (key === "ROOT") return evaluate(val, actor, actor);
        if (key === "tag" || key === "original_tag") {
            return state.tag === (val === "ROOT" ? actor.tag : unquote(val));
        }
        if (key === "has_country_flag") return state.flags.has(val);
        if (key === "has_dlc") return state.dlc.has(unquote(val));
        if (key === "has_capitulated") return state.capitulated === yes(val);
        if (key === "is_subject") return state.subject === yes(val);
        if (key === "owns_state") return state.ownedStates.has(Number(val));
        if (key === "controls_state") return state.controlledStates.has(Number(val));
        if (key === "has_civil_war") return state.civilwar === yes(val);
        if (key === "has_intelligence_agency") return state.agency === yes(val);
        if (key === "exists") return state.exists === yes(val);
        if (key === "num_of_civilian_factories_available_for_projects") {
            return state.factories > Number(val);
        }
        if (key === "has_equipment") {
            return val.every(equipment => {
                if (equipment.op !== ">") throw new Error("Unsupported equipment comparison");
                return (state.equipment?.[equipment.key] ?? 0) > Number(equipment.val);
            });
        }
        // Institute bootstrap is exercised with an already valid facility.
        // State selection/construction remains an engine integration test.
        if (key === "HSM_BAR_research_has_facility") return state.facility === yes(val);
        if (/^HSM_BAR_operation_.+_target$/.test(key)) return state.registryValid === yes(val);
        if (triggers[key]) return evaluate(triggers[key], state, actor) === yes(val);
        throw new Error("Unsupported fixture trigger: " + key);
    });
}

function execute(nodes, state, actor = state) {
    let branchTaken = false;
    let inChain = false;
    for (const { key, val } of nodes) {
        if (key === "if") {
            inChain = true;
            branchTaken = evaluate(get(val, "limit"), state, actor);
            if (branchTaken) execute(val.filter(n => n.key !== "limit"), state, actor);
            continue;
        }
        if (key === "else_if") {
            if (!inChain) throw new Error("Unpaired else_if");
            if (!branchTaken && evaluate(get(val, "limit"), state, actor)) {
                branchTaken = true;
                execute(val.filter(n => n.key !== "limit"), state, actor);
            }
            continue;
        }
        if (key === "else") {
            if (!inChain) throw new Error("Unpaired else");
            if (!branchTaken) execute(val, state, actor);
            inChain = false;
            continue;
        }
        inChain = false;
        if (key === "ROOT") execute(val, actor, actor);
        else if (effects[key]) execute(effects[key], state, actor);
        else if (key === "hidden_effect") execute(val, state, actor);
        else if (key === "set_country_flag") state.flags.add(val);
        else if (key === "clr_country_flag") state.flags.delete(val);
        else if (key === "add_tech_bonus") state.techBonuses.push(val);
        else if (key === "add_timed_idea") state.ideas.push(val);
        else if (key === "add_political_power") state.pp += Number(val);
        else if (key === "add_stability") state.stability += Number(val);
        else if (key === "add_to_variable") {
            for (const variable of val) {
                if (variable.op !== "=" || !Number.isFinite(Number(variable.val))) {
                    throw new Error("Unsupported fixture variable change");
                }
                state.variables[variable.key] = (state.variables[variable.key] ?? 0) + Number(variable.val);
            }
        }
        else if (key === "HSM_BAR_core_refresh") {
            // Snapshot variables at the boundary so writes cannot disappear in a mock.
            state.coreRefreshVariables.push(structuredClone(state.variables));
        }
        else if (key === "country_event") state.events.push(get(val, "id"));
        else if (key === "custom_effect_tooltip") continue;
        else if (key === "set_technology") state.techUnlocks++;
        else if (key === "add_breakthrough_points") state.breakthroughs += Number(get(val, "value"));
        else if (key === "generate_scientist_character") state.scientists++;
        else if (/^HSM_BAR_operation_.+_complete$/.test(key)) state.callbacks.push(key);
        else throw new Error("Unsupported fixture effect: " + key);
    }
}

function scenario(project, dlc = true) {
    return {
        tag: "BAR",
        flags: new Set([
            "HSM_BAR_active", "HSM_BAR_institute_open",
            ...(project.route === "directorate" ? ["HSM_BAR_service_founded"] : []),
            // These fixtures start after the case-study ladder; its negative paths
            // are exercised separately by Test-BarradCases.cjs.
            "HSM_BAR_study_rock_done", "HSM_BAR_study_entity_done", "HSM_BAR_study_echo_done",
            "HSM_BAR_study_titan_done", "HSM_BAR_study_compass_done", "HSM_BAR_study_amulet_done",
            "HSM_BAR_suppression_authorized",
            "HSM_BAR_" + (project.route === "both" ? "collegium" : project.route),
            ...(project.parent ? ["HSM_BAR_project_" + project.parent + "_done"] : []),
            ...(project.field ? ["HSM_BAR_field_research_open"] : []),
            ...(project.normalization ? ["HSM_BAR_normalization"] : [])
        ]),
        dlc: new Set(dlc ? ["Gotterdammerung", "La Resistance"] : []),
        capitulated: false, civilwar: false, agency: true, exists: true, subject: false,
        ownedStates: new Set([624]), controlledStates: new Set([624]),
        factories: 3, pp: 500, stability: 0.5,
        variables: {}, coreRefreshVariables: [],
        ideas: [], techBonuses: [], events: [], callbacks: [],
        facility: true, techUnlocks: 0, breakthroughs: 0, scientists: 0
    };
}

let passed = 0;
function assert(condition, description) {
    if (!condition) throw new Error(description);
    passed++;
    if (process.argv.includes("--verbose")) console.log("PASS: " + description);
}
const effectOption = option => option.filter(n => !["name", "trigger", "ai_chance"].includes(n.key));

assert(Array.isArray(get(read("common/scripted_effects/HSM_BAR_core_effects.txt"), "HSM_BAR_core_refresh")),
    "Core refresh boundary resolves to an existing scripted effect");

for (const project of researchVariants) {
    for (const choice of project.choices) {
        const prefix = "HSM_BAR_research_" + project.id;
        const done = "HSM_BAR_project_" + project.id + "_done";
        const label = project.route + "/" + project.id + "/" + choice.id;
        const expectedStability = 0.5 + (project.route === "collegium" ? choice.stability ?? 0 : 0);
        const expectedRefresh = project.route === "directorate" && choice.refresh ? [{}] : [];
        const native = scenario(project);
        execute(effects[prefix + "_finish"], native);
        assert(native.techBonuses.length === 0 && Object.keys(native.variables).length === 0 &&
            native.stability === 0.5 && native.coreRefreshVariables.length === 0, "Unearned output blocked: " + label);
        execute(effects[prefix + "_choose_" + choice.id], native);
        assert(native.ideas.length === 0 && native.pp === 500 && Object.keys(native.variables).length === 0 &&
            native.stability === 0.5 && native.coreRefreshVariables.length === 0, "Choice defers benefits/cost: " + label);
        execute(effects[prefix + "_complete"], native);
        assert(native.flags.has(done) && native.techBonuses.length === 1 &&
            native.ideas.length === 1 && native.pp === 500 - choice.cost, "Native completion: " + label);
        assert(get(native.ideas[0], "idea") === prefix + "_" + choice.id + "_idea",
            "Distinct native output: " + label);
        assert(Object.keys(native.variables).length === 0, "Native completion creates no cover or replacement meter: " + label);
        assert(native.stability === expectedStability, "Route-specific stability result: " + label);
        assert(JSON.stringify(native.coreRefreshVariables) === JSON.stringify(expectedRefresh),
            "Existing maintenance refresh timing preserved without meter writes: " + label);
        assert(Number(get(native.ideas[0], "days")) === (choice.days ?? 540) &&
            Number(get(native.techBonuses[0], "bonus")) === 0.5 && Number(get(native.techBonuses[0], "uses")) === 1,
            "Idea duration and research bonus preserved: " + label);
        execute(effects[prefix + "_complete"], native);
        execute(effects[prefix + "_finish"], native);
        execute(effects[prefix + "_choose_" + project.choices.find(c => c.id !== choice.id).id], native);
        assert(native.ideas.length === 1 && native.techBonuses.length === 1 &&
            native.pp === 500 - choice.cost && Object.keys(native.variables).length === 0 &&
            native.stability === expectedStability && JSON.stringify(native.coreRefreshVariables) === JSON.stringify(expectedRefresh),
            "Idempotent replay: " + label);

        const fallback = scenario(project, false);
        const decision = decisions[prefix + "_fallback"];
        assert(evaluate(get(decision, "available"), fallback), "Fallback available: " + label);
        // The engine deducts the decision cost before executing complete_effect.
        fallback.pp -= Number(get(decision, "cost"));
        execute(get(decision, "complete_effect"), fallback);
        assert(fallback.flags.has("HSM_BAR_research_fallback_busy") &&
            !evaluate(get(decision, "available"), fallback), "Parallel fallback blocked: " + label);
        assert(fallback.ideas.length === 0 && Object.keys(fallback.variables).length === 0 &&
            fallback.stability === 0.5 && fallback.coreRefreshVariables.length === 0, "No fallback reward at start: " + label);
        // Advancing to remove_effect is an explicit fixture step, not a timer simulation.
        execute(get(decision, "remove_effect"), fallback);
        assert(fallback.events[0] === "HSM_BAR_research." + project.event &&
            fallback.flags.has(prefix + "_ready"), "Matching fallback event: " + label);
        const option = events[fallback.events[0]].find(n => n.key === "option" &&
            get(n.val, "name") === prefix + "_" + choice.id + "_choice").val;
        assert(evaluate(get(option, "trigger"), fallback), "Fallback choice valid: " + label);
        execute(effectOption(option), fallback);
        assert(fallback.flags.has(done) && fallback.pp === 500 - project.cost - choice.cost,
            "Paid fallback completion: " + label);
        assert(Object.keys(fallback.variables).length === 0 && fallback.stability === expectedStability &&
            JSON.stringify(fallback.coreRefreshVariables) === JSON.stringify(expectedRefresh),
            "Exact fallback stability and refresh parity without a meter: " + label);
        assert(JSON.stringify(fallback.ideas) === JSON.stringify(native.ideas) &&
            JSON.stringify(fallback.techBonuses) === JSON.stringify(native.techBonuses),
            "Native/fallback reward parity: " + label);
    }
}

for (const project of researchVariants) {
    const prefix = "HSM_BAR_research_" + project.id;
    const decision = decisions[prefix + "_fallback"];
    const duration = { clinic: 120, grid: 150, wards: 120, containment: 150, forensics: 150, suppression: 180 }[project.id];
    assert(Number(get(decision, "days_remove")) === duration && Number(get(get(decision, "modifier"), "civilian_factory_use")) === 1,
        "Fallback duration and factory cost preserved: " + project.route + "/" + project.id);
    let state = scenario(project);
    assert(!evaluate(get(decision, "visible"), state) && !evaluate(get(decision, "available"), state),
        "DLC bypass hidden/disabled: " + project.id);
    execute(get(decision, "remove_effect"), state);
    assert(!state.flags.has(prefix + "_ready") && state.ideas.length === 0,
        "DLC stale timer cannot reward: " + project.id);

    state = scenario(project, false);
    execute(get(decision, "complete_effect"), state);
    state.flags.delete("HSM_BAR_active");
    assert(evaluate(get(decision, "cancel_trigger"), state), "Path loss cancels fallback: " + project.id);
    execute(get(decision, "cancel_effect"), state);
    execute(get(decision, "remove_effect"), state);
    assert(!state.flags.has("HSM_BAR_research_fallback_busy") && !state.flags.has(prefix + "_ready"),
        "Cancellation releases laboratory without rewards: " + project.id);

    state = scenario(project);
    state.flags.delete("HSM_BAR_active");
    execute(effects[prefix + "_complete"], state);
    assert(state.flags.has(prefix + "_ready") && state.events.length === 0 && state.ideas.length === 0,
        "Completed result held during ineligibility: " + project.id);
    state.flags.add("HSM_BAR_active");
    execute(get(decisions[prefix + "_resume"], "complete_effect"), state);
    assert(state.events.length === 1, "Earned result resumes: " + project.id);

    state = scenario(project);
    execute(effects[prefix + "_complete"], state);
    state.flags.delete("HSM_BAR_active");
    const option = events["HSM_BAR_research." + project.event].find(n => n.key === "option").val;
    execute(effectOption(option), state);
    assert(state.ideas.length === 0 && !state.flags.has(prefix + "_choice_pending") &&
        Object.keys(state.variables).length === 0 && state.stability === 0.5 && state.coreRefreshVariables.length === 0,
        "Stale event option revalidates: " + project.id);
}

const researchIdeas = map(get(get(read("common/ideas/HSM_BAR_research_ideas.txt"), "ideas"), "country"));
const expectedFacilityModifiers = {
    containment_layered: { research_speed_factor: "0.03", encryption: "1", consumer_goods_factor: "0.02" },
    containment_sealed: { encryption: "2", research_speed_factor: "-0.02", consumer_goods_factor: "0.02" },
    suppression_permanent: { supply_consumption_factor: "-0.05", industrial_capacity_factory: "0.08", research_speed_factor: "-0.04", weekly_manpower: "-50" }
};
for (const [id, expected] of Object.entries(expectedFacilityModifiers)) {
    const actual = map(get(researchIdeas["HSM_BAR_research_" + id + "_idea"], "modifier"));
    assert(JSON.stringify(actual) === JSON.stringify(expected), "Facility modifiers replace policing and preserve other results: " + id);
}

const localizationKeys = [];
for (const language of ["english", "russian"]) {
    const bytes = fs.readFileSync(path.join(modRoot, "localisation", language, "HSM_BAR_research_l_" + language + ".yml"));
    const text = bytes.toString("utf8");
    assert(bytes.subarray(0, 3).toString("hex") === "efbbbf" && !text.includes("\uFFFD"), "Research localization UTF-8 BOM: " + language);
    const keys = [...text.matchAll(/^ ([\w.]+):0 ".*"\r?$/gm)].map(match => match[1]);
    assert(keys.length === new Set(keys).size && keys.length === text.split(/\r?\n/).filter(line => /^ HSM_BAR_/.test(line)).length,
        "Research localization entries valid and unique: " + language);
    localizationKeys.push(keys.sort());
}
assert(JSON.stringify(localizationKeys[0]) === JSON.stringify(localizationKeys[1]), "Research EN/RU key parity");

// Read the actual Collegium producer and ordinary-care decision without owning them.
const trialPause = "HSM_BAR_collegium_trial_pause";
const trialEvent = read("events/HSM_BAR_collegium_events.txt")
    .find(n => n.key === "country_event" && get(n.val, "id") === "HSM_BAR_collegium.21").val;
const suspendOption = trialEvent.find(n => n.key === "option" &&
    get(n.val, "name") === "HSM_BAR_collegium.21.a").val;
const pauseFlag = get(suspendOption, "set_country_flag");
assert(get(pauseFlag, "flag") === trialPause && Number(get(pauseFlag, "days")) === 60,
    "Clinical suspension consumes the actual Collegium 60-day flag");

const clinic = fixtures.find(p => p.id === "clinic");
const nativeClinic = get(read("common/special_projects/projects/HSM_BAR_research_projects.txt"),
    "HSM_BAR_research_clinic");
const clinicFallback = decisions.HSM_BAR_research_clinic_fallback;
const clinicResume = decisions.HSM_BAR_research_clinic_resume;
const clinicOutput = get(get(nativeClinic, "project_output"), "country_effects");
for (const dlc of [true, false]) {
    const label = dlc ? "native" : "fallback";
    const state = scenario(clinic, dlc);
    const canStart = () => dlc
        ? evaluate(get(nativeClinic, "available"), { target: state })
        : evaluate(get(clinicFallback, "available"), state);
    assert(canStart(), "Clinical start before suspension: " + label);
    state.flags.add(trialPause);
    assert(!canStart(), "Clinical suspension blocks a new start: " + label);
    assert(evaluate(triggers.HSM_BAR_research_clinic_eligible, state),
        "Clinical suspension preserves result eligibility: " + label);
    state.flags.delete(trialPause);
    assert(canStart(), "Clinical start restored after suspension expires: " + label);

    for (const choice of clinic.choices) {
        const earned = scenario(clinic, dlc);
        earned.flags.add("HSM_BAR_research_clinic_ready");
        earned.flags.add(trialPause);
        assert(evaluate(get(clinicResume, "visible"), earned) &&
            evaluate(get(clinicResume, "available"), earned),
            "Earned clinical ratification available during suspension: " + label + "/" + choice.id);
        execute(get(clinicResume, "complete_effect"), earned);
        const option = events["HSM_BAR_research.1"].find(n => n.key === "option" &&
            get(n.val, "name") === "HSM_BAR_research_clinic_" + choice.id + "_choice").val;
        const choiceAllowed = evaluate(get(option, "trigger"), earned);
        execute(effectOption(option), earned);
        execute(effectOption(option), earned);
        assert(choiceAllowed && earned.events[0] === "HSM_BAR_research.1" &&
            earned.flags.has("HSM_BAR_project_clinic_done") &&
            earned.ideas.length === 1 && earned.techBonuses.length === 1 &&
            earned.pp === 500 - choice.cost,
            "Suspended earned result ratifies once at the correct cost: " + label + "/" + choice.id);
    }
}

const clinicRounds = get(get(read("common/decisions/HSM_BAR_collegium_decisions.txt"),
    "HSM_BAR_collegium_programs"), "HSM_BAR_collegium_clinic_rounds");
const care = scenario(clinic);
care.flags.add("HSM_BAR_clinic_program");
care.equipment = { support_equipment: 25 };
const careAvailable = () => ["allowed", "visible", "available"]
    .every(key => evaluate(get(clinicRounds, key), care));
assert(careAvailable(), "Ordinary care available before clinical suspension");
care.flags.add(trialPause);
assert(careAvailable(), "Ordinary care remains available during clinical suspension");
for (const [field, unavailable] of [["subject", true], ["capitulated", true],
    ["ownedStates", new Set()], ["controlledStates", new Set()]]) {
    const original = care[field];
    care[field] = unavailable;
    assert(!careAvailable(), "Ordinary care still checks current access during suspension: " + field);
    care[field] = original;
}
care.equipment.support_equipment = 24;
assert(!careAvailable(), "Ordinary care still requires its equipment during suspension");

const prototype = get(get(nativeClinic, "unique_prototype_rewards"), "HSM_BAR_research_clinic_choice");
for (const choice of clinic.choices) {
    const state = scenario(clinic);
    const option = prototype.find(n => n.key === "option" &&
        get(n.val, "token") === "HSM_BAR_research_clinic_" + choice.id + "_choice").val;
    execute(get(get(option, "iteration_output"), "country_effects"), state);
    state.flags.add(trialPause);
    execute(clinicOutput, state);
    assert(state.flags.has("HSM_BAR_project_clinic_done") && state.ideas.length === 1 &&
        state.pp === 500 - choice.cost,
        "Native earned output honors the preselected prototype during suspension: " + choice.id);
}
const underway = scenario(clinic, false);
execute(get(clinicFallback, "complete_effect"), underway);
underway.flags.add(trialPause);
assert(!evaluate(get(clinicFallback, "cancel_trigger"), underway),
    "Start-only suspension does not cancel an already funded clinical term");
execute(get(clinicFallback, "remove_effect"), underway);
assert(underway.flags.has("HSM_BAR_research_clinic_ready") &&
    !underway.flags.has("HSM_BAR_research_fallback_busy") && underway.events[0] === "HSM_BAR_research.1",
    "Already funded clinical term produces a ratifiable result during suspension");
const unearned = scenario(clinic);
unearned.flags.add(trialPause);
execute(get(clinicResume, "complete_effect"), unearned);
execute(effects.HSM_BAR_research_clinic_finish, unearned);
assert(!unearned.flags.has("HSM_BAR_project_clinic_done") && unearned.events.length === 0 &&
    unearned.ideas.length === 0 && unearned.techBonuses.length === 0 && unearned.pp === 500,
    "Clinical suspension does not permit unearned ratification");

for (const [enabled, expected] of [[true, 1], [false, 0]]) {
    const state = scenario(fixtures[0], enabled);
    execute(effects.HSM_BAR_establish_institute, state);
    execute(effects.HSM_BAR_establish_institute, state);
    assert(state.scientists === expected && state.breakthroughs === 2 * expected,
        "Bootstrap DLC/replay guard: " + enabled);
}
const suppression = scenario(fixtures.find(p => p.id === "suppression"));
suppression.flags.add("HSM_BAR_coexistence");
assert(!evaluate(triggers.HSM_BAR_research_suppression_eligible, suppression),
    "Coexistence excludes radical suppression");

for (const operation of operations) {
    const fixture = operationFixtures.find(o => operation.key === "HSM_BAR_operations_" + o.id);
    if (!fixture) throw new Error("Missing operation fixture: " + operation.key);
    const makeActor = () => {
        const state = scenario({ route: "directorate", field: true });
        if (fixture.gate) state.flags.add("HSM_BAR_project_" + fixture.gate + "_done");
        state.target = { tag: "YAL", exists: true, flags: new Set(), registryValid: true };
        return state;
    };
    let state = makeActor();
    execute(get(operation.val, "outcome_execute"), state);
    assert(state.callbacks.length === 1 &&
        state.callbacks[0] === operation.key.replace("operations_", "operation_") + "_complete",
        "Valid operation country callback: " + fixture.id);
    const invalidators = [
        s => s.flags.delete("HSM_BAR_active"),
        s => s.flags.delete("HSM_BAR_directorate"),
        s => s.flags.delete("HSM_BAR_field_research_open"),
        s => s.dlc.delete("La Resistance"),
        s => { s.agency = false; },
        s => { s.capitulated = true; },
        s => { s.civilwar = true; },
        s => { s.target.exists = false; },
        s => { s.target.tag = "BAR"; },
        s => { s.target.registryValid = false; }
    ];
    for (const [index, invalidate] of invalidators.entries()) {
        state = makeActor();
        invalidate(state);
        execute(get(operation.val, "outcome_execute"), state);
        assert(state.callbacks.length === 0 && state.events[0] === "HSM_BAR_operations.1",
            "Stale operation blocked: " + fixture.id + "/" + index);
    }
}
const earlyRepublic = scenario({ route: "directorate" });
earlyRepublic.flags.delete("HSM_BAR_service_founded");
assert(!evaluate(triggers.HSM_BAR_research_actor, earlyRepublic), "A public institute alone cannot start Service research");
earlyRepublic.flags.add("HSM_BAR_service_founded");
assert(evaluate(triggers.HSM_BAR_research_actor, earlyRepublic), "A founded Service may use its public institute");
assert(!evaluate(parse("NOT = { has_country_flag = HSM_BAR_service_founded has_country_flag = absent }"), earlyRepublic), "NOT excludes either matching child");
assert(evaluate(parse("NOT = { AND = { has_country_flag = HSM_BAR_service_founded has_country_flag = absent } }"), earlyRepublic), "NOT AND detects one missing requirement");
if (passed !== 383) throw new Error("Fixture inventory changed: expected 383 assertions, ran " + passed);
console.log("PASS: " + passed + " behavioral assertions.");
console.log("Coverage: 14 native/fallback variants including both wards routes, absent cover writes, exact stability deltas, refresh timing, facility modifiers, EN/RU localization, replay/cost guards, interrupted results, DLC gates, bootstrap, 40 stale operations, 25 clinical-suspension checks and four current-access checks.");
console.log("Limit: this fixture interpreter does not run HOI4, core refresh internals or the main case registry.");
