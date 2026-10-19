"use strict";

// Generate only gameplay-owned files. node tools/Build-BarradCollegiumProjects.cjs [--check]
const fs = require("node:fs");
const path = require("node:path");
const assert = require("node:assert/strict");
const root = path.resolve(__dirname, "..");
const projects = JSON.parse(fs.readFileSync(path.join(__dirname, "data/barrad-collegium-projects.json"), "utf8").replace(/^\uFEFF/, ""));
const prefix = "HSM_BAR_mtk_";
const departments = {
    viira: { character: "BAR_viira_lehtola", alive: "barrad_viira_alive" },
    leopold: { character: "BAR_leopold_schmeller", alive: "barrad_leopold_alive" },
    silver: { character: "BAR_silver_star", alive: "barrad_silver_star_alive" },
    asinti: { character: "BAR_asinti", alive: "barrad_asinti_alive" }
};
// Percentage modifiers use fractions; factory reservations use whole factories.
// Failed experiments advance the faculty's knowledge but yield no permanent modifier.
const rewards = {
    field_atlas: { research_speed_factor: 0.05 },
    shared_senses: { recon_factor: 0.10 },
    sleep_lecture: {},
    crystal_memory: { experience_loss_factor: -0.05 },
    spell_notation: { production_factory_efficiency_gain_factor: 0.05 },
    chorus: { modifier_army_sub_unit_category_magical_infantry_max_org_factor: 0.15, research_speed_factor: 0.05 },
    prosthetics: { army_org_regain: 0.05 },
    self_repair: { attrition: -0.10 },
    revolver_howitzer: {},
    crystal_drive: { industrial_capacity_factory: 0.05 },
    sorting_engine: { production_factory_efficiency_gain_factor: 0.10 },
    manufactory: { industrial_capacity_factory: 0.15, production_factory_efficiency_gain_factor: 0.10 },
    necrotic_suture: { casualty_trickleback: 0.05 },
    tissue_bank: { casualty_trickleback: 0.05 },
    ageless_sleep: {},
    spell_sterilisation: { army_org_regain: 0.05 },
    phantom_pain: { experience_loss_factor: -0.05 },
    last_minute: { casualty_trickleback: 0.15, army_org_regain: 0.10 },
    ritual_brake: { stability_factor: 0.05 },
    silent_witness: {},
    place_memory: { recon_factor: 0.05 },
    threshold_compass: { supply_consumption_factor: -0.05 },
    empty_vessel: { research_speed_factor: 0.03 },
    contact: { research_speed_factor: 0.05, recon_factor: 0.10 },
    sensate_prosthesis: { experience_loss_factor: -0.05, army_org_regain: 0.05 },
    interrupt_notation: { supply_consumption_factor: -0.05, modifier_army_sub_unit_category_magical_infantry_max_org_factor: 0.05 }
};
const factories = (p, method) => (p.opus ? 2 : 1) + (method === "instrumented" ? 1 : 0);
const modifierNames = {
    research_speed_factor: ["Research speed", "Скорость исследований"],
    recon_factor: ["Reconnaissance", "Разведка"],
    experience_loss_factor: ["Experience loss", "Потери опыта"],
    modifier_army_sub_unit_category_magical_infantry_max_org_factor: ["Magical infantry organisation", "Организация магической пехоты"],
    army_org_regain: ["Division recovery rate", "Скорость восстановления дивизий"],
    attrition: ["Attrition", "Истощение"],
    industrial_capacity_factory: ["Factory output", "Объём заводского производства"],
    production_factory_efficiency_gain_factor: ["Production efficiency growth", "Рост эффективности производства"],
    casualty_trickleback: ["Trickleback", "Возвращение раненых в строй"],
    stability_factor: ["Stability", "Стабильность"],
    supply_consumption_factor: ["Supply consumption", "Потребление припасов"],
    production_speed_buildings_factor: ["Construction speed", "Скорость строительства"],
    political_power_gain: ["Daily political power", "Ежедневная политическая власть"],
    civilian_factory_use: ["Reserved civilian factories", "Занятые гражданские фабрики"]
};
const modifiers = Object.keys(modifierNames);
const variable = modifier => prefix + "bonus_" + modifier;
const stem = project => prefix + project.id;
const faculties = p => [p.department, ...(p.partners || [])];
const members = department => projects.filter(p => faculties(p).includes(department));
// Joint work shares both laboratory locks, never a faculty's five-preparation counter.
const preparations = department => projects.filter(p => p.department === department && !p.opus && !p.partners);
const stages = ["theory", "trials"];
const responses = ["a", "b"];
const combinations = [0, 1, 2, 3];
const verifyMethods = responses.flatMap(response => combinations.map(combo => `verify_${response}_${combo}`));
const preparationFlags = ["rig_a", "rig_b", "control_a", "control_b"];
const experimentFlags = ["experiment_active", "observation_ready", "verify_running", "paid_rig_b", "paid_control_b", "response_a", "response_b", "experiment_record"];
const duration = (p, stage) => p[stage === "theory" ? "theoryDays" : "trialDays"];
const cost = (p, stage) => p[stage === "theory" ? "theoryCost" : "trialCost"];
const block = (name, body) => `${name} = {\n${body.split("\n").map(s => " " + s).join("\n")}\n}\n`;
const flag = id => `has_country_flag = ${id}`;
const no = body => `NOT = { ${body} }`;
const owns = "owns_state = 624\ncontrols_state = 624";
const header = "# Generated by tools/Build-BarradCollegiumProjects.cjs. Edit the generator.\n";
const paidCombination = (p, combo) => ["rig", "control"].map((part, index) => {
    const selected = flag(`${stem(p)}_paid_${part}_b`);
    return combo & (index === 0 ? 2 : 1) ? selected : no(selected);
}).join("\n");
const clearFlags = (p, flags) => flags.map(f => `clr_country_flag = ${stem(p)}_${f}`).join("\n");
const removeVerification = p => verifyMethods.map(method => `remove_mission = ${stem(p)}_${method}_mission`).join("\n");
function loadExperiments() {
    return JSON.parse(fs.readFileSync(path.join(__dirname, "data/barrad-collegium-experiments.json"), "utf8").replace(/^\uFEFF/, ""));
}
function validateExperiments(experiments) {
    assert.equal(experiments.length, projects.length);
    assert.deepEqual(experiments.map(p => p.id).sort(), projects.map(p => p.id).sort());
    const bilingual = value => Array.isArray(value) && value.length === 2 && value.every(text => typeof text === "string" && text.trim());
    for (const p of experiments) {
        for (const part of ["rig", "control"]) {
            assert(bilingual(p[part].question), `${p.id}/${part}`);
            assert.equal(p[part].options.length, 2, `${p.id}/${part}`);
            for (const option of p[part].options) assert(bilingual(option.label) && bilingual(option.note), `${p.id}/${part}`);
        }
        assert.equal(p.observations.length, 4, p.id);
        assert(p.observations.every(bilingual), p.id);
        assert.equal(p.responses.length, 2, p.id);
        for (const response of p.responses) {
            assert(bilingual(response.label) && bilingual(response.note), p.id);
            assert.equal(response.reports.length, 4, p.id);
            assert(response.reports.every(bilingual), p.id);
            for (const key of ["days", "cost"]) {
                assert.equal(response[key].length, 4, `${p.id}/${key}`);
                assert(response[key].every(value => Number.isInteger(value) && value >= (key === "days" ? 1 : 0)), `${p.id}/${key}`);
            }
        }
    }
}

function validateCatalog() {
    assert.equal(projects.length, 26);
    assert.equal(new Set(projects.map(p => p.id)).size, 26);
    assert.deepEqual(projects.map(p => p.id), Object.keys(rewards));
    for (const [index, p] of projects.entries()) {
        assert.equal(p.number, index + 1);
        assert(Object.hasOwn(departments, p.department));
        if (p.partners) {
            assert.equal(p.partners.length, 1);
            assert.notEqual(p.partners[0], p.department);
            assert(Object.hasOwn(departments, p.partners[0]));
            assert(!p.opus && p.prerequisites.length >= 2);
            assert.equal(new Set(p.prerequisites).size, p.prerequisites.length);
            for (const prerequisite of p.prerequisites) assert(projects.some(q => q.id === prerequisite && !q.opus && !q.partners && faculties(p).includes(q.department)));
        }
        assert(["success", "partial", "failure"].includes(p.outcome));
        for (const key of ["theoryDays", "trialDays", "theoryCost", "trialCost", "instrumentedDays", "instrumentedCost"]) assert(Number.isInteger(p[key]) && p[key] > 0);
        assert(p.instrumentedDays < p.trialDays && p.instrumentedCost > p.trialCost);
        if (p.outcome === "failure") assert.deepEqual(rewards[p.id], {});
    }
    for (const department of Object.keys(departments)) {
        assert.equal(preparations(department).length, 5);
        assert.equal(members(department).filter(p => p.opus).length, 1);
    }
}

function experimentBackend(p, experiment, access, idle, requiredWork) {
    const id = stem(p);
    let triggers = block(`${id}_can_prepare_experiment`, `${access}\n${idle}\n${flag(id + "_theory")}\n${no(flag(id + "_done"))}${requiredWork}`);
    let effects = "", decisions = "";
    for (const part of ["rig", "control"]) for (const choice of responses) {
        effects += block(`${id}_prepare_${part}_${choice}`, `if = {\n limit = { ${id}_can_prepare_experiment = yes }\n clr_country_flag = ${id}_${part}_${choice === "a" ? "b" : "a"}\n set_country_flag = ${id}_${part}_${choice}\n}`);
    }
    const selections = ["rig", "control"].map(part => `OR = {\n AND = { ${flag(`${id}_${part}_a`)} ${no(flag(`${id}_${part}_b`))} }\n AND = { ${flag(`${id}_${part}_b`)} ${no(flag(`${id}_${part}_a`))} }\n}`).join("\n");
    triggers += block(`${id}_can_begin_experiment`, `${id}_can_trials = yes\n${selections}`);
    // Keep the legacy/AI paid start untouched; only the journal opts into the checkpoint.
    effects += block(`${id}_begin_experiment`, `if = {\n limit = { ${id}_can_begin_experiment = yes }\n ${id}_start_trials = yes\n ${clearFlags(p, experimentFlags).replaceAll("\n", "\n ")}\n set_country_flag = ${id}_experiment_active\n if = { limit = { ${flag(id + "_rig_b")} } set_country_flag = ${id}_paid_rig_b }\n if = { limit = { ${flag(id + "_control_b")} } set_country_flag = ${id}_paid_control_b }\n ${prefix}projects_refresh = yes\n}`);
    triggers += block(`${id}_experiment_valid`, `${id}_trials_valid = yes\n${flag(id + "_experiment_active")}`);
    triggers += block(`${id}_checkpoint_valid`, `${id}_experiment_valid = yes\n${flag(id + "_observation_ready")}\n${no(flag(id + "_verify_running"))}\n${no(flag(id + "_response_a"))}\n${no(flag(id + "_response_b"))}`);
    const responseSelected = response => `${flag(`${id}_response_${response}`)}\n${no(flag(`${id}_response_${response === "a" ? "b" : "a"}`))}`;
    triggers += block(`${id}_verify_valid`, `${id}_experiment_valid = yes\n${flag(id + "_verify_running")}\n${no(flag(id + "_observation_ready"))}\nOR = {\n${responses.map(response => block("AND", responseSelected(response))).join("")}}`);
    for (const [index, response] of responses.entries()) {
        const authored = experiment.responses[index];
        const budget = combinations.map(combo => block("AND", `${paidCombination(p, combo)}\n${no(`has_political_power < ${authored.cost[combo]}`)}`)).join("");
        triggers += block(`${id}_can_respond_${response}`, `${id}_checkpoint_valid = yes\nOR = {\n${budget}}`);
        // The paid workshop remains reserved; responding needs PP, not another free workshop.
        effects += block(`${id}_respond_${response}`, `if = {\n limit = { ${id}_can_respond_${response} = yes }\n ${removeVerification(p).replaceAll("\n", "\n ")}\n clr_country_flag = ${id}_observation_ready\n clr_country_flag = ${id}_verify_running\n set_country_flag = ${id}_verify_running\n set_country_flag = ${id}_response_${response}\n ${combinations.map(combo => block("if", `limit = { ${paidCombination(p, combo)} }\nadd_political_power = -${authored.cost[combo]}\nactivate_mission = ${id}_verify_${response}_${combo}_mission`)).join("").trimEnd().replaceAll("\n", "\n ")}\n ${prefix}projects_refresh = yes\n}`);
        for (const combo of combinations) {
            const method = `verify_${response}_${combo}`, mission = `${id}_${method}_mission`, days = authored.days[combo];
            triggers += block(`${id}_${method}_timer_valid`, `${id}_verify_valid = yes\n${responseSelected(response)}\n${paidCombination(p, combo)}`);
            effects += block(`${id}_finish_${method}`, `if = {\n limit = {\n  ${id}_${method}_timer_valid = yes\n  NOT = { has_country_flag = { flag = ${id}_verify_running days < ${days} } }\n }\n ${removeVerification(p).replaceAll("\n", "\n ")}\n remove_mission = ${id}_trials_mission\n remove_mission = ${id}_instrumented_mission\n ${clearFlags(p, ["experiment_active", "observation_ready", "verify_running", "trials_running", "trials_revised_contract"]).replaceAll("\n", "\n ")}\n set_country_flag = ${id}_done\n set_country_flag = ${id}_experiment_record\n ${prefix}projects_refresh = yes\n}\nelse_if = {\n limit = { ${flag(id + "_trials_running")} ${id}_trials_valid = no }\n ${id}_cancel_trials = yes\n}`);
            decisions += block(mission, `icon = generic_research\nallowed = { original_tag = BAR }\nvisible = { always = no }\nactivation = { always = no }\navailable = { always = no }\nis_good = yes\ncancel_if_not_visible = no\ndays_mission_timeout = ${days}\ncancel_trigger = { ${id}_${method}_timer_valid = no }\n# Native removal may precede timeout; validity uses the dated paid contract, not mission presence.\ncancel_effect = {\n if = { limit = { ${id}_trials_valid = no } ${id}_cancel_trials = yes }\n}\ntimeout_effect = { ${id}_finish_${method} = yes }\nai_will_do = { factor = 0 }`);
        }
    }
    return { triggers, effects, decisions };
}

function generate(experiments = loadExperiments()) {
    validateCatalog();
    validateExperiments(experiments);
    const experimentById = new Map(experiments.map(p => [p.id, p]));
    let triggers = header + `# Country scope throughout: never redirect a foreign GUI caller into BAR.\n# Available is document access; work additionally needs the physical homeland.\n`;
    triggers += block(prefix + "institution", `tag = BAR\noriginal_tag = BAR\nexists = yes\n${flag("HSM_BAR_active")}\n${flag("HSM_BAR_collegium")}\n${flag("HSM_BAR_collegium_initialized")}\n${no(flag("HSM_BAR_directorate"))}`);
    triggers += block(prefix + "programme_access", `${prefix}institution = yes\nhas_capitulated = no\nhas_completed_focus = HSM_BAR_collegium_oath`);
    triggers += block(prefix + "available", `${prefix}programme_access = yes\nis_ai = no`);
    triggers += block(prefix + "work_access", `${prefix}programme_access = yes\n${owns}`);
    for (const [department, faculty] of Object.entries(departments)) {
        triggers += block(prefix + department + "_work_access", `${prefix}work_access = yes\n${flag(faculty.alive)}\nhas_character = ${faculty.character}`);
        const busy = members(department).flatMap(p => [...stages.flatMap(stage => [flag(stem(p) + "_" + stage + "_running"), `has_active_mission = ${stem(p)}_${stage}_mission`]), `has_active_mission = ${stem(p)}_instrumented_mission`, ...verifyMethods.map(method => `has_active_mission = ${stem(p)}_${method}_mission`)]);
        triggers += block(prefix + department + "_busy", `OR = {\n ${busy.join("\n ")}\n}`);
        triggers += block(prefix + department + "_all_preparations", preparations(department).map(p => flag(stem(p) + "_done")).join("\n"));
    }
    let effects = header + `# Native missions own their timers. No delayed country events or GUI activate_decision calls.\n# remove_mission invalidates the old timer without executing completion/timeout effects\n# (installed documentation/effects_documentation.md). Cancellation is not completion.\n# Reset flag dates on every paid attempt; early/replayed old timeouts cannot finish a restart.\n# Interactive checkpoints have no mission; trials_running retains the faculty locks.\n# The paid experiment reserves workshops through the checkpoint and verification.\n`;
    let decisions = "";
    for (const p of projects) {
        const id = stem(p), dept = prefix + p.department;
        const access = faculties(p).map(d => `${prefix}${d}_work_access = yes`).join("\n");
        const idle = faculties(p).map(d => no(`${prefix}${d}_busy = yes`)).join("\n");
        const requiredWork = (p.prerequisites || []).map(q => `\n${flag(prefix + q + "_done")}`).join("") + (p.opus ? `\n${dept}_all_preparations = yes` : "");
        const experiment = experimentBackend(p, experimentById.get(p.id), access, idle, requiredWork);
        triggers += experiment.triggers;
        effects += experiment.effects;
        decisions += experiment.decisions;
        for (const stage of stages) {
            const running = `${id}_${stage}_running`, mission = `${id}_${stage}_mission`;
            const prerequisite = stage === "theory" ? no(flag(id + "_theory")) : flag(id + "_theory");
            // The clinical moratorium blocks new Silver trials, as in the existing clinic.
            const pause = stage === "trials" && faculties(p).includes("silver") ? `\n${no(flag("HSM_BAR_collegium_trial_pause"))}` : "";
            const budget = stage === "theory" ? `${no(`has_political_power < ${p.theoryCost}`)}\nnum_of_civilian_factories_available_for_projects > ${factories(p, "theory") - 1}` : "OR = {\n" + [false, true].map(instrumented => block("AND", [
                instrumented ? flag(dept + "_instrumented") : no(flag(dept + "_instrumented")),
                no(`has_political_power < ${instrumented ? p.instrumentedCost : p.trialCost}`),
                `num_of_civilian_factories_available_for_projects > ${factories(p, instrumented ? "instrumented" : "trials") - 1}`
            ].join("\n"))).join("") + "}";
            triggers += block(`${id}_can_${stage}`, `${access}\n${idle}\n${no(flag(id + "_done"))}\n${prerequisite}\n${budget}${requiredWork}${pause}`);
            triggers += block(`${id}_${stage}_valid`, `${access}\n${flag(running)}\n${no(flag(id + "_done"))}\n${prerequisite}${requiredWork}`);
            let payment = `add_political_power = -${p.theoryCost}\nactivate_mission = ${mission}`;
            if (stage === "trials") payment = `clr_country_flag = ${id}_instrumented\nclr_country_flag = ${id}_civilian\nclr_country_flag = ${id}_field\n` +
                `if = { limit = { ${flag(dept + "_instrumented")} }\n add_political_power = -${p.instrumentedCost}\n set_country_flag = ${id}_instrumented\n activate_mission = ${id}_instrumented_mission\n}\nelse = { add_political_power = -${p.trialCost} activate_mission = ${mission} }`;
            effects += block(`${id}_start_${stage}`, `if = {\n limit = { ${id}_can_${stage} = yes }\n set_country_flag = ${prefix}projects_initialized\n clr_country_flag = ${running}\n set_country_flag = ${running}\n set_country_flag = ${id}_${stage}_revised_contract\n ${payment.replaceAll("\n", "\n ")}\n ${prefix}projects_refresh = yes\n}`);
            const extraCancel = stage === "trials" ? `\nremove_mission = ${id}_instrumented_mission\n${removeVerification(p)}\n${clearFlags(p, ["experiment_active", "observation_ready", "verify_running"])}\nif = { limit = { ${no(flag(id + "_done"))} }\n ${clearFlags(p, ["instrumented", "civilian", "field", ...preparationFlags, ...experimentFlags]).replaceAll("\n", "\n ")}\n}` : "";
            effects += block(`${id}_cancel_${stage}`, `remove_mission = ${mission}\nclr_country_flag = ${running}\nclr_country_flag = ${id}_${stage}_revised_contract${extraCancel}\n${prefix}projects_refresh = yes`);
            // Preserve old timer IDs; the research modifier reserves workshops during the extra timer.
            for (const method of stage === "theory" ? ["theory"] : ["trials", "instrumented"]) {
                const timedMission = `${id}_${method}_mission`, days = method === "instrumented" ? p.instrumentedDays : duration(p, stage);
                const selector = stage === "theory" ? "" : `\n${method === "instrumented" ? flag(id + "_instrumented") : no(flag(id + "_instrumented"))}\n${no(flag(id + "_observation_ready"))}\n${no(flag(id + "_verify_running"))}`;
                triggers += block(`${id}_${method}_timer_valid`, `${id}_${stage}_valid = yes${selector}`);
                const completion = `clr_country_flag = ${running}\nclr_country_flag = ${id}_${stage}_revised_contract\nset_country_flag = ${id}_${stage === "theory" ? "theory" : "done"}`;
                const finish = stage === "theory" ? completion : `if = { limit = { ${flag(id + "_experiment_active")} } set_country_flag = ${id}_observation_ready }\nelse = {\n ${completion.replaceAll("\n", "\n ")}\n}`;
                effects += block(`${id}_finish_${method}`, `if = {\n limit = {\n  ${id}_${method}_timer_valid = yes\n  OR = {\n   AND = { ${flag(id + "_" + stage + "_revised_contract")} NOT = { has_country_flag = { flag = ${running} days < ${days} } } }\n   AND = { ${no(flag(id + "_" + stage + "_revised_contract"))} NOT = { has_country_flag = { flag = ${running} days < ${days - (p.opus ? 28 : 14)} } } }\n  }\n }\n remove_mission = ${timedMission}\n ${finish.replaceAll("\n", "\n ")}\n ${prefix}projects_refresh = yes\n}\nelse_if = {\n limit = { ${flag(running)} ${id}_${stage}_valid = no }\n ${id}_cancel_${stage} = yes\n}`);
                decisions += block(timedMission, `icon = generic_research\nallowed = { original_tag = BAR }\nvisible = { always = no }\nactivation = { always = no }\n# Journal-only presentation; guarded paid starts retain native hidden timers.\navailable = { always = no }\nis_good = yes\ncancel_if_not_visible = no\ndays_mission_timeout = ${days}\ncancel_trigger = { ${id}_${method}_timer_valid = no }\n# An old method's callback cannot cancel a valid restart using the other method.\ncancel_effect = {\n if = { limit = { ${id}_${stage}_valid = no } ${id}_cancel_${stage} = yes }\n}\ntimeout_effect = { ${id}_finish_${method} = yes }\nai_will_do = { factor = 0 }`);
            }
        }
    }
    for (const department of Object.keys(departments)) {
        const dept = prefix + department;
        for (const [choice, property, enabled] of [["replication", "instrumented", false], ["instrumentation", "instrumented", true]]) {
            const eligible = `${dept}_work_access = yes\n${no(`${dept}_busy = yes`)}`;
            effects += block(`${dept}_select_${choice}`, `if = { limit = { ${eligible} }\n ${enabled ? "set" : "clr"}_country_flag = ${dept}_${property}\n}`);
            // Retain legacy IDs, but all player policy selection now belongs to the journal.
            decisions += block(`${dept}_choose_${choice}`, `icon = generic_research\nvisible = { always = no }\navailable = { ${eligible} }\ncost = 0\ncomplete_effect = { ${dept}_select_${choice} = yes }\nai_will_do = { factor = 0 }`);
        }
    }
    const reset = modifiers.map(m => `set_variable = { ${variable(m)} = 0 }`).join("\n");
    const counts = Object.keys(departments).map(d => {
        const id = prefix + d;
        return `set_variable = { ${id}_completed = 0 }\nclr_country_flag = ${id}_busy\nif = { limit = { ${id}_busy = yes } set_country_flag = ${id}_busy }\n` + preparations(d).map(p => `if = { limit = { ${flag(stem(p) + "_done")} } add_to_variable = { ${id}_completed = 1 } }`).join("\n");
    }).join("\n");
    const addRewards = map => Object.entries(map).map(([m, v]) => `add_to_variable = { ${variable(m)} = ${v} }`).join("\n");
    const totals = projects.filter(p => p.outcome !== "failure").map(p => `if = {\n limit = { ${flag(stem(p) + "_done")} }\n ${addRewards(rewards[p.id])}\n}`).join("\n");
    // Mission modifiers belong to a selected decision's days_remove period. Count
    // running work in the existing dynamic modifier instead. No additional currency.
    const workshops = projects.flatMap(p => [
        ...["theory", "trials", "instrumented"].map(method => `if = { limit = { ${stem(p)}_${method}_timer_valid = yes has_active_mission = ${stem(p)}_${method}_mission ${method === "theory" ? "" : no(flag(stem(p) + "_experiment_active"))} } if = { limit = { ${flag(stem(p) + "_" + (method === "theory" ? "theory" : "trials") + "_revised_contract")} } add_to_variable = { ${variable("civilian_factory_use")} = ${factories(p, method)} } } else = { add_to_variable = { ${variable("civilian_factory_use")} = ${method === "instrumented" ? 1 : 0} } } }`),
        // An interactive contract reserves once, including the untimed narrative checkpoint.
        `if = { limit = { ${stem(p)}_experiment_valid = yes }\n if = { limit = { ${flag(stem(p) + "_instrumented")} } add_to_variable = { ${variable("civilian_factory_use")} = ${factories(p, "instrumented")} } }\n else = { add_to_variable = { ${variable("civilian_factory_use")} = ${factories(p, "trials")} } }\n}`
    ]).join("\n");
    effects += block(prefix + "projects_refresh", `hidden_effect = {\n ${reset.replaceAll("\n", "\n ")}\n ${counts.replaceAll("\n", "\n ")}\n if = {\n  limit = { ${prefix}programme_access = yes }\n  ${totals.replaceAll("\n", "\n  ")}\n  ${workshops.replaceAll("\n", "\n  ")}\n  if = {\n   limit = { ${no(`has_dynamic_modifier = ${prefix}research`)} }\n   add_dynamic_modifier = { modifier = ${prefix}research }\n  }\n }\n else = { remove_dynamic_modifier = { modifier = ${prefix}research } }\n force_update_dynamic_modifier = yes\n}`);
    const cancelAll = projects.flatMap(p => [...stages.flatMap(stage => [`remove_mission = ${stem(p)}_${stage}_mission`, `clr_country_flag = ${stem(p)}_${stage}_running`, `clr_country_flag = ${stem(p)}_${stage}_revised_contract`]), `remove_mission = ${stem(p)}_instrumented_mission`, removeVerification(p), clearFlags(p, ["experiment_active", "observation_ready", "verify_running"]), `if = { limit = { ${no(flag(stem(p) + "_done"))} }\n ${clearFlags(p, ["civilian", "field", "instrumented", ...preparationFlags, ...experimentFlags]).replaceAll("\n", "\n ")}\n}`]).join("\n");
    effects += block(prefix + "projects_cancel_all", cancelAll + `\n${prefix}projects_refresh = yes`);
    effects += block(prefix + "projects_teardown", `# Called synchronously by HSM_BAR_dissolve_institutions before its route flags are cleared.\n${cancelAll}\n${projects.map(p => clearFlags(p, ["theory", "done", "civilian", "field", "instrumented", ...preparationFlags, ...experimentFlags])).join("\n")}\n${Object.keys(departments).map(d => `clr_country_flag = ${prefix}${d}_busy\nclr_country_flag = ${prefix}${d}_civilian\nclr_country_flag = ${prefix}${d}_instrumented\nset_variable = { ${prefix}${d}_completed = 0 }`).join("\n")}\n${reset}\nclr_country_flag = ${prefix}ai_dispatch\nclr_country_flag = ${prefix}ai_week_tick\nclr_country_flag = ${prefix}projects_initialized\nremove_dynamic_modifier = { modifier = ${prefix}research }\nforce_update_dynamic_modifier = yes`);
    // Only maintenance checks mission presence: native timeout may remove it before its callback.
    const cancelInvalid = projects.flatMap(p => stages.map(stage => {
        const id = stem(p);
        const present = stage === "theory" ? `has_active_mission = ${id}_theory_mission` : `OR = {\n ${id}_checkpoint_valid = yes\n ${["trials", "instrumented", ...verifyMethods].map(method => `AND = { ${id}_${method}_timer_valid = yes has_active_mission = ${id}_${method}_mission }`).join("\n ")}\n}`;
        const pending = stage === "theory" ? present : [...["experiment_active", "observation_ready", "verify_running"].map(f => flag(`${id}_${f}`)), ...["trials", "instrumented", ...verifyMethods].map(method => `has_active_mission = ${id}_${method}_mission`)].join("\n  ");
        return `if = {\n limit = {\n  OR = { ${flag(`${id}_${stage}_running`)} ${pending} }\n  OR = { ${id}_${stage}_valid = no NOT = { ${present} } }\n }\n ${id}_cancel_${stage} = yes\n}`;
    })).join("\n");
    const orphanVerification = projects.flatMap(p => verifyMethods.map(method => `if = { limit = { has_active_mission = ${stem(p)}_${method}_mission ${stem(p)}_${method}_timer_valid = no } remove_mission = ${stem(p)}_${method}_mission }`)).join("\n");
    effects += block(prefix + "projects_pulse", `if = {\n limit = { ${prefix}programme_access = yes }\n set_country_flag = ${prefix}projects_initialized\n}\nif = {\n limit = { ${flag(prefix + "projects_initialized")} }\n if = {\n  limit = { ${prefix}institution = no }\n  ${prefix}projects_teardown = yes\n }\n else = {\n  ${cancelInvalid.replaceAll("\n", "\n  ")}\n  ${orphanVerification.replaceAll("\n", "\n  ")}\n  ${prefix}projects_refresh = yes\n }\n}`);
    let dynamic = block(prefix + "research", `icon = GFX_idea_HSM_BAR_art_collegium\nenable = { ${prefix}programme_access = yes }\nremove_trigger = { ${prefix}institution = no }\n${modifiers.map(m => `${m} = ${variable(m)}`).join("\n")}`);
    const aiStarts = projects.flatMap(p => stages.slice().reverse().map(stage => `if = {\n limit = { ${no(flag(prefix + "ai_dispatch"))} ${stem(p)}_can_${stage} = yes ${no(`has_political_power < ${cost(p, stage) + 100}`)} }\n ${stem(p)}_start_${stage} = yes\n set_country_flag = ${prefix}ai_dispatch\n}`)).join("\n");
    effects += block(prefix + "projects_ai_week", `if = {\n limit = { is_ai = yes ${prefix}work_access = yes has_war = no OR = { ${no(flag(prefix + "ai_week_tick"))} NOT = { has_country_flag = { flag = ${prefix}ai_week_tick days < 7 } } } }\n clr_country_flag = ${prefix}ai_week_tick\n set_country_flag = ${prefix}ai_week_tick\n clr_country_flag = ${prefix}ai_dispatch\n ${Object.keys(departments).map(d => `${prefix}${d}_select_replication = yes`).join("\n ")}\n ${aiStarts.replaceAll("\n", "\n ")}\n}`);
    const onActions = block("on_actions", `on_daily_BAR = { effect = { ${prefix}projects_pulse = yes } }\non_weekly_BAR = { effect = { ${prefix}projects_ai_week = yes } }\non_capitulation = {\n effect = { ROOT = { if = { limit = { tag = BAR ${flag(prefix + "projects_initialized")} } ${prefix}projects_cancel_all = yes } } }\n}\n# FROM.FROM is the changed state; BAR is explicit because ROOT is the new controller.\non_state_control_changed = {\n effect = {\n  if = {\n   limit = { FROM.FROM = { state = 624 } BAR = { exists = yes ${flag(prefix + "projects_initialized")} } }\n   BAR = { ${prefix}projects_pulse = yes }\n  }\n }\n}`);
    const files = {
        "common/scripted_triggers/HSM_BAR_mtk_projects.txt": triggers,
        "common/scripted_effects/HSM_BAR_mtk_projects.txt": effects,
        "common/decisions/categories/HSM_BAR_mtk_projects.txt": header + block(prefix + "projects_missions", `icon = generic_research\nallowed = { original_tag = BAR }\nvisible = { always = no }`),
        "common/decisions/HSM_BAR_mtk_projects.txt": header + block(prefix + "projects_missions", decisions.trimEnd()),
        "common/dynamic_modifiers/HSM_BAR_mtk_projects.txt": header + dynamic,
        "common/on_actions/HSM_BAR_mtk_projects.txt": header + onActions
    };
    for (const [languageIndex, language] of ["english", "russian"].entries()) {
        const ru = languageIndex === 1;
        const entries = {
            [prefix + "projects_missions"]: ru ? "Исследования коллегиума" : "Collegium Research",
            [prefix + "projects_missions_desc"]: ru ? "Текущие теоретические исследования и испытания кафедр." : "Current departmental theory and trial missions.",
            [prefix + "research"]: ru ? "Результаты исследований коллегиума" : "Collegium Research Results",
            [prefix + "research_desc"]: ru ? "Проверенные разработки кафедр: от клинических процедур до промышленной автоматики. Результаты внедряются без разделения на гражданское и ведомственное применение. Фабрики заняты только на время исследования или испытаний; постоянного содержания нет." : "Validated departmental findings, from clinical procedures to industrial automation. Results are implemented without separate civilian or field applications. Workshops are reserved only during research and trials; completed findings have no upkeep.",
            [prefix + "method_replication"]: ru ? "последовательные испытания" : "sequential replication",
            [prefix + "method_instrumentation"]: ru ? "приборные испытания" : "instrumented trials"
        };
        const facultyNarrative = {
            viira: ["Viira can compare successive observations or reserve a workshop for a parallel array of sensing crystals. More instruments shorten the observation schedule; they cannot make two minds identical.", "Виира может сопоставлять последовательные наблюдения или занять мастерскую параллельной сетью чувствующих кристаллов. Приборы сокращают расписание замеров, но не делают два разума одинаковыми."],
            leopold: ["Leopold can rebuild each test rig in turn or commission dedicated gauges and duplicate benches. A crowded workshop delivers measurements sooner, not a guarantee that the machine will work.", "Леопольд может поочерёдно перестраивать стенд или заказать отдельные измерители и дублирующие установки. Занятая мастерская быстрее выдаст замеры, но не обещание, что машина заработает."],
            silver: ["Silver Star can follow one clinical series at a time or equip parallel diagnostic teams. The extra apparatus reduces delays between observations, not the care owed to an individual patient.", "Сильвер Стар может вести клинические серии по очереди или оснастить параллельные диагностические бригады. Дополнительная аппаратура сокращает задержки между наблюдениями, а не помощь отдельному пациенту."],
            asinti: ["Asinti can repeat the observation at each ritual interval or prepare an instrumented chamber to record several intervals together. A clearer trace still need not be an answer from the other side.", "Асинти может повторять наблюдение в каждый ритуальный промежуток или подготовить приборную камеру для совместной записи нескольких циклов. Более ясный след ещё не обязательно является ответом с другой стороны."]
        };
        for (const [d, faculty] of Object.entries(departments)) {
            for (const choice of ["replication", "instrumentation"]) {
                const term = entries[prefix + (choice === "replication" ? "method_replication" : "method_instrumentation")];
                entries[`${prefix}${d}_choose_${choice}`] = `$${faculty.character}$: ${term}`;
                entries[`${prefix}${d}_choose_${choice}_desc`] = facultyNarrative[d][languageIndex] + (ru
                    ? "\\n\\nПоследовательный протокол занимает одну фабрику (Magnum Opus: две). Приборный сокращает испытания на 7 дней (Magnum Opus: 21), но требует на одну фабрику и на 15 политической власти больше (Magnum Opus: 35). Мастерские освобождаются при завершении или отмене. Метод фиксируется при оплате и не меняет исход проекта."
                    : "\\n\\nSequential trials reserve one factory (Magnum Opus: two). Instrumentation shortens trials by 7 days (Magnum Opus: 21), but needs one additional factory and 15 more political power (Magnum Opus: 35). Workshops are released on completion or cancellation. The paid method is fixed and does not change the outcome.");
            }
        }
        for (const p of projects) {
            const id = stem(p);
            const experiment = experimentById.get(p.id);
            for (const [index, response] of responses.entries()) {
                const authored = experiment.responses[index];
                for (const combo of combinations) {
                    entries[`${id}_response_${response}_${combo}_budget`] = ru
                        ? `Оплата: ${authored.cost[combo]} политической власти. Срок проверки: ${authored.days[combo]} дн. Оплаченные мастерские остаются заняты до подписания заключения или отмены.`
                        : `Payment: ${authored.cost[combo]} political power. Verification: ${authored.days[combo]} days. Paid workshops remain reserved until the conclusion is signed or work is cancelled.`;
                    entries[`${id}_verify_${response}_${combo}_mission`] = `$${id}_title$: ${ru ? "проверка наблюдений" : "Observation verification"}`;
                    entries[`${id}_verify_${response}_${combo}_mission_desc`] = ru
                        ? `${authored.days[combo]} дн. Кафедра проверяет запись наблюдений по выбранному продолжению опыта. Мастерские заняты до подписания заключения или отмены. Потеря доступа или руководителя отменяет текущую работу.`
                        : `${authored.days[combo]} days. The department checks the observation record through the selected follow-up. Workshops remain reserved until the conclusion is signed or work is cancelled. Loss of access or a department head cancels the current work.`;
                }
            }
            for (const method of ["replication", "instrumented"]) {
                const amount = method === "instrumented" ? p.instrumentedCost : p.trialCost;
                const days = method === "instrumented" ? p.instrumentedDays : p.trialDays;
                entries[`${id}_budget_${method}`] = ru
                    ? `Оплата: ${amount} политической власти. Срок: ${days} дн. Занятые фабрики: ${factories(p, method)} до завершения или отмены.`
                    : `Payment: ${amount} political power. Duration: ${days} days. Reserved factories: ${factories(p, method)} until completion or cancellation.`;
            }
            const lines = Object.entries(rewards[p.id]).map(([m, v]) => `${modifierNames[m][languageIndex]}: ${v > 0 ? "+" : ""}${Number((v * 100).toFixed(3))}%`);
            let detail = lines.length ? lines.join("; ") + "." : ru ? "Постоянных бонусов нет. Неудача засчитывается в прогресс кафедры." : "No permanent benefit. Failure counts toward department progress.";
            const limits = {
                chorus: ["Linked magic within trained groups.", "Связанная магия в обученных группах."],
                manufactory: ["Useful automatic manufacturing, not artificial intelligence.", "Полезное автоматическое производство, а не искусственный интеллект."],
                last_minute: ["Emergency necromantic stabilisation, not immortality.", "Экстренная некромантическая стабилизация, а не бессмертие."],
                contact: ["Limited contact without a host; no universal portal or enslavement.", "Ограниченный контакт без носителя; без универсального портала и порабощения."]
            };
            if (limits[p.id]) detail += " " + limits[p.id][languageIndex];
            entries[id + "_effects"] = detail;
            for (const stage of stages) {
                const theory = stage === "theory", days = duration(p, stage), pp = cost(p, stage);
                const faculty = `$${departments[p.department].character}$`;
                let conditions = ru
                    ? `Требуется: Баррад; действующий коллегиум; завершённый фокус $HSM_BAR_collegium_oath$; отсутствие капитуляции; владение и контроль над $STATE_624$. Кафедра свободна; ${faculty} жив и присутствует. Проект ещё не завершён.`
                    : `Requires: Barrad; active Collegium; $HSM_BAR_collegium_oath$ completed; no capitulation; ownership and control of $STATE_624$. Department free; ${faculty} alive and present. Project unfinished.`;
                conditions += theory
                    ? ru ? " Теория ещё не завершена." : " Theory not yet completed."
                    : ru ? " Теория завершена." : " Theory completed.";
                if (p.opus) conditions += ru ? " Завершены все пять подготовительных проектов кафедры, включая неудачные." : " All five departmental preparations finished, including failures.";
                if (p.partners) conditions += (ru ? " Совместная работа: обе кафедры свободны; присутствует также " : " Joint work: both departments free; also alive and present: ") + p.partners.map(d => `$${departments[d].character}$`).join(", ") + (ru ? ". Завершены: " : ". Completed: ") + p.prerequisites.map(q => `$${prefix}${q}_title$`).join(", ") + (ru ? ". Обе кафедры заняты до конца этапа. Протокол ведущей кафедры; одна оплата, одна мастерская." : ". Both departments are occupied until the stage ends. Lead faculty policy; one payment, one workshop.");
                if (!theory && faculties(p).includes("silver")) conditions += ru ? " Запрет на новые клинические испытания снят." : " No moratorium on new clinical trials.";
                entries[`${id}_start_${stage}_tt`] = ru
                    ? `Стоимость: ${pp} политической власти. Срок: ${days} дн. Занятые фабрики: ${factories(p, "theory")}. ${conditions} При отмене этап не засчитывается, затраты не возвращаются. Повторный запуск оплачивается заново.`
                    : `Cost: ${pp} political power. Duration: ${days} days. Reserved factories: ${factories(p, "theory")}. ${conditions} Cancellation does not complete the stage or refund its cost. Restarting costs the same.`;
                entries[`${id}_${stage}_mission`] = `$${id}_title$: ${ru ? theory ? "теория" : "испытания" : theory ? "Theory" : "Trials"}`;
                if (!theory) entries[`${id}_start_${stage}_tt`] = ru
                    ? `[GetHSMBARMtkTrialBudget_${p.id}] ${conditions} Требуются утверждённая теория, выбранные установка и контрольная проба. Первая серия завершится записью наблюдений и ожиданием решения о продолжении; заключение и результат появятся только после последующей проверки. Кафедры и мастерские остаются заняты во время ожидания и проверки. При отмене этап не засчитывается, затраты не возвращаются. Повторный запуск оплачивается заново.\\nТекущий протокол: [GetHSMBARMtkMethod_${p.department}]. Метод фиксируется при запуске.`
                    : `[GetHSMBARMtkTrialBudget_${p.id}] ${conditions} Approved theory, a selected apparatus and a selected control procedure are required. The first series produces observations and waits for a follow-up response; the conclusion and its results are published only after verification. Departments and workshops stay occupied during that wait and verification. Cancellation does not complete the stage or refund its cost. Restarting costs the same.\\nCurrent protocol: [GetHSMBARMtkMethod_${p.department}]. The method is fixed at launch.`;
                entries[`${id}_${stage}_mission_desc`] = ru
                    ? `${days} дн. По завершении кафедра ${theory ? "представит подписанный теоретический отчёт и сможет приступить к испытаниям" : "представит подписанный отчёт об испытаниях и заключение"}. Потеря доступа или руководителя отменяет текущий этап. Подписанные отчёты хранятся в архиве, пока коллегиум существует.`
                    : `${days} days. On completion, the department ${theory ? "files a signed theoretical report and can begin trials" : "files a signed test report and conclusion"}. Loss of access or the department head cancels the current stage. Signed reports remain in the archive while the Collegium exists.`;
            }
        }
        for (const p of projects) {
            entries[stem(p) + "_instrumented_mission"] = `$${stem(p)}_title$: ${ru ? "приборные испытания" : "Instrumented trials"}`;
            entries[stem(p) + "_instrumented_mission_desc"] = ru
                ? `${p.instrumentedDays} дн. Приборная мастерская работает по подписанному протоколу. Занятые гражданские фабрики: ${factories(p, "instrumented")} до завершения или отмены; выводы появятся в заключении после испытаний.`
                : `${p.instrumentedDays} days. The instrument workshop follows the signed protocol. Reserved civilian factories: ${factories(p, "instrumented")} until completion or cancellation; conclusions will appear after the trials.`;
        }
        files[`localisation/${language}/HSM_BAR_mtk_project_effects_l_${language}.yml`] = `\uFEFFl_${language}:\n` + Object.entries(entries).map(([k, v]) => ` ${k}:0 "${v.replaceAll('"', '\\"')}"`).join("\n") + "\n";
    }
    return files;
}

function main() {
    const check = process.argv.includes("--check");
    const files = generate();
    for (const [relative, text] of Object.entries(files)) {
        const file = path.join(root, "mod/HoISubmod", relative);
        if (check) assert.equal(fs.readFileSync(file, "utf8"), text, "Generated file drift: " + relative);
        else {
            fs.mkdirSync(path.dirname(file), { recursive: true });
            fs.writeFileSync(file, text, "utf8");
        }
    }
    console.log(`${check ? "Verified" : "Generated"} ${Object.keys(files).length} gameplay files: ${projects.length} projects, ${projects.length * (3 + verifyMethods.length)} hidden native missions, 8 journal method choices.`);
}
if (require.main === module) main();
module.exports = { generate, projects, departments, faculties, preparations, rewards, factories, modifiers, variable, prefix, loadExperiments, validateExperiments, verifyMethods, paidCombination };
