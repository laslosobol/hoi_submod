"use strict";
// The catalog owns project identities. This builder emits only presentation and guarded UI dispatch.
const fs = require("node:fs"), path = require("node:path");
const root = path.resolve(__dirname, ".."), mod = path.join(root, "mod/HoISubmod");
const projects = JSON.parse(fs.readFileSync(path.join(__dirname, "data/barrad-collegium-projects.json"), "utf8"));
const experiments = JSON.parse(fs.readFileSync(path.join(__dirname, "data/barrad-collegium-experiments.json"), "utf8"));
require("node:assert/strict").deepEqual(experiments.map(p => p.id), projects.map(p => p.id));
const experimentText = {};
const departments = ["viira", "leopold", "silver", "asinti"];
const faculties = p => [p.department, ...(p.partners || [])];
const preparations = d => projects.filter(p => p.department === d && !p.opus && !p.partners);
const write = (file, text) => {
    const p = path.join(mod, file), content = text + "\n";
    if (process.argv.includes("--check")) require("node:assert/strict").equal(fs.readFileSync(p, "utf8"), content, "Generated file drift: " + file);
    else { fs.mkdirSync(path.dirname(p), {recursive: true}); fs.writeFileSync(p, content); }
};
const at = (x, y) => `position = { x = ${x} y = ${y} }`;
const eq = (variable, value) => `check_variable = { ${variable} = ${value} }`;
const dept = d => eq("HSM_BAR_mtk_department", departments.indexOf(d) + 1);
const inFaculty = p => `OR = { ${faculties(p).map(dept).join(" ")} }`;
const selected = p => `${inFaculty(p)} ${eq("HSM_BAR_mtk_project", p.number)}`;
const active = "HSM_BAR_mtk_available = yes has_variable = HSM_BAR_mtk_open";
const flag = (p, stage) => `has_country_flag = HSM_BAR_mtk_${p.id}_${stage}`;
const stages = ["idea", "theory", "tests", "conclusion"];
const policyView = eq("HSM_BAR_mtk_document", 5), originView = eq("HSM_BAR_mtk_document", 6), ledgerView = eq("HSM_BAR_mtk_document", 7);
const combo = (p, n) => [n >= 2 ? flag(p, "paid_rig_b") : `NOT = { ${flag(p, "paid_rig_b")} }`, n % 2 ? flag(p, "paid_control_b") : `NOT = { ${flag(p, "paid_control_b")} }`].join(" ");
const buttons = [], texts = [], effects = [], triggers = [], properties = [], loc = [];
function button(name, x, y, sprite, label, tip, font = "hoi_16mbs") {
    const node = `buttonType = { name = "${name}" ${at(x,y)} quadTextureSprite = "${sprite}" ${label ? `buttonText = "${label}" buttonFont = "${font}"` : ""} ${tip ? `pdx_tooltip = "${tip}"` : ""} clicksound = click_ok ${name.endsWith("_close") ? 'shortcut = "ESCAPE"' : ""} }`;
    buttons.push(node); return node;
}
function text(name, x, y, w, h, key, font = "HSM_BAR_archive_ink", scroll = false) {
    const node = `instantTextboxType = { name = "${name}" ${at(x,y)} maxWidth = ${w} maxHeight = ${h} text = "${key}" font = "${font}" format = left alwaystransparent = ${scroll ? "no scrollbartype = standardtext_slider" : "yes"} }`;
    texts.push(node); return node;
}
function choice(name, options, fallback) {
    loc.push(`defined_text = { name = ${name}\n${options.map(([condition, key]) => ` text = { trigger = { ${condition} } localization_key = ${key} }`).join("\n")}\n text = { localization_key = ${fallback} }\n}`);
}
const window = [];
// Two static buttons stop clicks from reaching the map, as in the existing archive.
for (const layer of ["floor", "shield"]) {
    const name = "HSM_BAR_mtk_input_" + layer;
    window.push(`buttonType = { name = "${name}" ${at(0,0)} size = { x = 1000 y = 700 } quadTextureSprite = "GFX_HSM_BAR_mtk_viira" alwaystransparent = no }`);
    properties.push(`${name} = { image = "[GetHSMBARMtkBackground]" }`);
}
choice("GetHSMBARMtkBackground", departments.map(d => [dept(d), "GFX_HSM_BAR_mtk_" + d]), "GFX_HSM_BAR_mtk_viira");
window.push(text("HSM_BAR_mtk_heading", 26, 22, 874, 32, "HSM_BAR_mtk_heading", "hoi_24header"));
window.push(text("HSM_BAR_mtk_subheading", 26, 62, 900, 24, "[GetHSMBARMtkSubheading]", "hoi_16mbs"));
window.push(button("HSM_BAR_mtk_close", 944, 20, "GFX_HSM_BAR_archive_close", null, "HSM_BAR_archive_close_tt"));
effects.push("HSM_BAR_mtk_close_click = { clear_variable = HSM_BAR_mtk_open clear_variable = HSM_BAR_mtk_department clear_variable = HSM_BAR_mtk_project clear_variable = HSM_BAR_mtk_document }");
choice("GetHSMBARMtkSubheading", departments.map(d => [dept(d), "HSM_BAR_mtk_" + d + "_heading"]), "HSM_BAR_mtk_viira_heading");
window.push(text("HSM_BAR_mtk_index_heading", 26, 160, 250, 20, "[GetHSMBARMtkProgress]", "hoi_16mbs"));
choice("GetHSMBARMtkProgress", departments.map(d => [dept(d), "HSM_BAR_mtk_" + d + "_progress"]), "HSM_BAR_mtk_viira_progress");
for (const [i, d] of departments.entries()) {
    const name = "HSM_BAR_mtk_dept_" + d, base = "GFX_HSM_BAR_mtk_dept_" + d;
    window.push(button(name, 26 + i * 240, 108, base, "HSM_BAR_mtk_" + d, "HSM_BAR_mtk_" + d + "_heading"));
    properties.push(`${name} = { image = "[GetHSMBARMtkDept${i}Skin]" }`);
    choice(`GetHSMBARMtkDept${i}Skin`, [[dept(d), base + "_selected"]], base);
    effects.push(`${name}_click = { if = { limit = { ${active} } set_variable = { HSM_BAR_mtk_department = ${i+1} } set_variable = { HSM_BAR_mtk_project = ${i*6+1} } set_variable = { HSM_BAR_mtk_document = 1 } } }`);
}
for (const p of projects) {
    const index = p.partners ? 6 : (p.number - 1) % 6;
    // One shared dossier, reachable from either faculty without duplicating its progress.
    for (const d of faculties(p)) {
        const name = "HSM_BAR_mtk_project_" + p.id + (p.partners ? "_" + d : ""), base = `GFX_HSM_BAR_mtk_project_${d}`;
        window.push(button(name, 26, 182 + 40 * index, base, `HSM_BAR_mtk_${p.id}_title`, `HSM_BAR_mtk_${p.id}_index_tt`));
        properties.push(`${name} = { image = "[GetHSMBARMtkProject${p.number}_${d}Skin]" }`);
        choice(`GetHSMBARMtkProject${p.number}_${d}Skin`, [[selected(p), base + "_selected"]], base);
        triggers.push(`${name}_visible = { ${active} ${dept(d)} }`);
        effects.push(`${name}_click = { if = { limit = { ${active} ${dept(d)} } set_variable = { HSM_BAR_mtk_project = ${p.number} } set_variable = { HSM_BAR_mtk_document = 1 } } }`);
    }
    const options = [[flag(p,"done"), `HSM_BAR_mtk_status_${p.outcome}`], [flag(p,"observation_ready"), "HSM_BAR_mtk_status_observation"], [flag(p,"verify_running"), "HSM_BAR_mtk_status_verifying"], [flag(p,"trials_running"), "HSM_BAR_mtk_status_trials"],
        [flag(p,"theory_running"), "HSM_BAR_mtk_status_research"], [flag(p,"theory"), "HSM_BAR_mtk_status_ready"]];
    choice(`GetHSMBARMtkProject${p.number}Status`, options, p.opus ? "HSM_BAR_mtk_status_opus" : "HSM_BAR_mtk_status_proposal");
    for (const stage of ["theory", "trials"]) {
        const b = `HSM_BAR_mtk_start_${p.id}_${stage}`;
        window.push(button(b, stage === "theory" ? 334 : 652, 618, "GFX_HSM_BAR_mtk_action", "HSM_BAR_mtk_start_" + stage, `HSM_BAR_mtk_${p.id}_start_${stage}_tt`));
        triggers.push(`${b}_visible = { ${active} ${selected(p)} ${policyView} NOT = { ${flag(p,stage + "_running")} ${flag(p,"done")} ${stage === "theory" ? flag(p,"theory") : ""} } ${stage === "trials" ? flag(p,"theory") : ""} }`);
        triggers.push(`${b}_click_enabled = { ${active} ${selected(p)} ${policyView} HSM_BAR_mtk_${p.id}_${stage === "theory" ? "can_theory" : "can_begin_experiment"} = yes }`);
        effects.push(`${b}_click = { if = { limit = { ${active} ${selected(p)} ${policyView} } HSM_BAR_mtk_${p.id}_${stage === "theory" ? "start_theory" : "begin_experiment"} = yes } }`);
        const cancel = `HSM_BAR_mtk_cancel_${p.id}_${stage}`;
        const cancelGuard = `${active} ${selected(p)} ${policyView} ${flag(p,stage + "_running")} NOT = { ${flag(p,"done")} }`;
        window.push(button(cancel, stage === "theory" ? 334 : 652, 618, "GFX_HSM_BAR_mtk_action", "HSM_BAR_mtk_cancel_" + stage, "HSM_BAR_mtk_cancel_tt"));
        triggers.push(`${cancel}_visible = { ${cancelGuard} }`);
        triggers.push(`${cancel}_click_enabled = { ${cancelGuard} }`);
        effects.push(`${cancel}_click = { if = { limit = { ${cancelGuard} } HSM_BAR_mtk_${p.id}_cancel_${stage} = yes } }`);
    }
}
window.push(text("HSM_BAR_mtk_project_title", 334, 184, 456, 34, "[GetHSMBARMtkTitle]", "HSM_BAR_archive_heading"));
window.push(text("HSM_BAR_mtk_project_status", 334, 224, 560, 24, "[GetHSMBARMtkStatus]"));
choice("GetHSMBARMtkTitle", projects.map(p => [selected(p), `HSM_BAR_mtk_${p.id}_title`]), "HSM_BAR_mtk_select_project");
const statusOptions = [];
for (const p of projects) {
    for (const [f,key] of [["done",`HSM_BAR_mtk_status_${p.outcome}`],["observation_ready","HSM_BAR_mtk_status_observation"],["verify_running","HSM_BAR_mtk_status_verifying"],["trials_running","HSM_BAR_mtk_status_trials"],["theory_running","HSM_BAR_mtk_status_research"],["theory","HSM_BAR_mtk_status_ready"]]) statusOptions.push([`${selected(p)} ${flag(p,f)}`,key]);
    statusOptions.push([selected(p),p.opus ? "HSM_BAR_mtk_status_opus" : "HSM_BAR_mtk_status_proposal"]);
}
choice("GetHSMBARMtkStatus", statusOptions, "HSM_BAR_mtk_select_project");
const helpers = ["HSM_BAR_mtk_ui_selected = { " + active + " OR = { " + projects.map(p => `AND = { ${selected(p)} }`).join(" ") + " } }"];
for (const stage of ["theory", "done", "observation_ready", "verify_running"]) helpers.push(`HSM_BAR_mtk_ui_${stage} = { ${active} OR = { ${projects.map(p => `AND = { ${selected(p)} ${stage === "theory" ? `OR = { ${flag(p,"theory")} ${flag(p,"done")} }` : flag(p,stage)} }`).join(" ")} } }`);
for (let n = 1; n <= 4; n++) {
    const name = "HSM_BAR_mtk_doc_" + n, base = "GFX_HSM_BAR_mtk_doc";
    window.push(button(name, 334 + (n-1)*156, 260, base, "HSM_BAR_mtk_doc_" + n, "HSM_BAR_mtk_doc_" + n, "HSM_BAR_archive_ink"));
    properties.push(`${name} = { image = "[GetHSMBARMtkDoc${n}Skin]" }`);
    choice(`GetHSMBARMtkDoc${n}Skin`, [[eq("HSM_BAR_mtk_document",n),base+"_selected"]],base);
    const guard = n === 1 ? "HSM_BAR_mtk_ui_selected = yes" : n === 2 ? "HSM_BAR_mtk_ui_theory = yes" : n === 3 ? "OR = { HSM_BAR_mtk_ui_done = yes HSM_BAR_mtk_ui_observation_ready = yes HSM_BAR_mtk_ui_verify_running = yes }" : "HSM_BAR_mtk_ui_done = yes";
    triggers.push(`${name}_click_enabled = { ${guard} }`);
    effects.push(`${name}_click = { if = { limit = { ${guard} } set_variable = { HSM_BAR_mtk_document = ${n} } } }`);
}
window.push(text("HSM_BAR_mtk_document", 334, 310, 612, 296, "[GetHSMBARMtkDocument]", "HSM_BAR_archive_body", true));
window.push(text("HSM_BAR_mtk_accounting", 334, 310, 612, 296, "[GetHSMBARMtkAccounting]", "HSM_BAR_archive_body", true));
triggers.push(`HSM_BAR_mtk_document_visible = { NOT = { ${policyView} ${originView} ${ledgerView} } }`);
triggers.push(`HSM_BAR_mtk_accounting_visible = { ${active} ${ledgerView} }`);
window.push(button("HSM_BAR_mtk_ledger", 910, 222, "GFX_HSM_BAR_mtk_ledger", null, "HSM_BAR_mtk_ledger_tt"));
triggers.push("HSM_BAR_mtk_ledger_click_enabled = { HSM_BAR_mtk_ui_selected = yes }");
effects.push(`HSM_BAR_mtk_ledger_click = { if = { limit = { HSM_BAR_mtk_ui_selected = yes } set_variable = { HSM_BAR_mtk_document = 7 } } }`);
choice("GetHSMBARMtkAccounting", projects.flatMap(p => [[`${selected(p)} ${flag(p,"done")}`, "HSM_BAR_mtk_accounting_complete"], [selected(p), `HSM_BAR_mtk_${p.id}_accounting`]]), "HSM_BAR_mtk_select_project");
window.push(button("HSM_BAR_mtk_protocol", 26, 470, "GFX_HSM_BAR_mtk_project_viira", "HSM_BAR_mtk_protocol", "HSM_BAR_mtk_protocol_tt"));
properties.push('HSM_BAR_mtk_protocol = { image = "[GetHSMBARMtkProtocolSkin]" }');
choice("GetHSMBARMtkProtocolSkin", departments.flatMap(d => [[`${dept(d)} ${policyView}`,`GFX_HSM_BAR_mtk_project_${d}_selected`],[dept(d),`GFX_HSM_BAR_mtk_project_${d}`]]), "GFX_HSM_BAR_mtk_project_viira");
effects.push(`HSM_BAR_mtk_protocol_click = { if = { limit = { HSM_BAR_mtk_ui_selected = yes } set_variable = { HSM_BAR_mtk_document = 5 } } }`);
triggers.push("HSM_BAR_mtk_protocol_click_enabled = { HSM_BAR_mtk_ui_selected = yes }");
window.push(button("HSM_BAR_mtk_origins", 802, 184, "GFX_HSM_BAR_mtk_doc", "HSM_BAR_mtk_origins", "HSM_BAR_mtk_origins_tt", "HSM_BAR_archive_ink"));
properties.push('HSM_BAR_mtk_origins = { image = "[GetHSMBARMtkOriginsSkin]" }');
choice("GetHSMBARMtkOriginsSkin", [[originView,"GFX_HSM_BAR_mtk_doc_selected"]], "GFX_HSM_BAR_mtk_doc");
const opusSelected = `${active} OR = { ${projects.filter(p => p.opus).map(p => `AND = { ${selected(p)} }`).join(" ")} }`;
triggers.push(`HSM_BAR_mtk_origins_visible = { ${opusSelected} }`);
triggers.push(`HSM_BAR_mtk_origins_click_enabled = { ${opusSelected} }`);
effects.push(`HSM_BAR_mtk_origins_click = { if = { limit = { ${opusSelected} } set_variable = { HSM_BAR_mtk_document = 6 } } }`);
window.push(text("HSM_BAR_mtk_origins_body", 334, 310, 612, 296, "[GetHSMBARMtkOrigins]", "HSM_BAR_archive_body", true));
triggers.push(`HSM_BAR_mtk_origins_body_visible = { ${opusSelected} ${originView} }`);
const setupView = `${active} ${policyView} NOT = { HSM_BAR_mtk_ui_observation_ready = yes HSM_BAR_mtk_ui_verify_running = yes HSM_BAR_mtk_ui_done = yes }`;
window.push(text("HSM_BAR_mtk_rig_question", 334, 306, 612, 36, "[GetHSMBARMtkRigQuestion]", "HSM_BAR_archive_body"));
window.push(text("HSM_BAR_mtk_control_question", 334, 400, 612, 36, "[GetHSMBARMtkControlQuestion]", "HSM_BAR_archive_body"));
for (const axis of ["rig", "control"]) {
    triggers.push(`HSM_BAR_mtk_${axis}_question_visible = { ${setupView} }`);
    choice(`GetHSMBARMtk${axis === "rig" ? "Rig" : "Control"}Question`, projects.map(p => [selected(p), `HSM_BAR_mtk_${p.id}_${axis}_question`]), "HSM_BAR_mtk_select_project");
}
window.push(text("HSM_BAR_mtk_method_heading", 334, 492, 612, 26, "HSM_BAR_mtk_method_heading", "HSM_BAR_archive_body"));
triggers.push(`HSM_BAR_mtk_method_heading_visible = { ${setupView} }`);
window.push(text("HSM_BAR_mtk_lab_record", 334, 310, 612, 296, "[GetHSMBARMtkLabRecord]", "HSM_BAR_archive_body", true));
triggers.push(`HSM_BAR_mtk_lab_record_visible = { ${active} ${policyView} OR = { HSM_BAR_mtk_ui_done = yes HSM_BAR_mtk_ui_verify_running = yes } }`);
window.push(text("HSM_BAR_mtk_observation", 334, 310, 612, 202, "[GetHSMBARMtkLabRecord]", "HSM_BAR_archive_body", true));
triggers.push(`HSM_BAR_mtk_observation_visible = { ${active} ${policyView} HSM_BAR_mtk_ui_observation_ready = yes NOT = { HSM_BAR_mtk_ui_done = yes HSM_BAR_mtk_ui_verify_running = yes } }`);
for (const d of departments) for (const [choiceName, enabled, x] of [
    ["replication",false,334], ["instrumentation",true,652]
]) {
    const name = `HSM_BAR_mtk_policy_${d}_${choiceName}`, base = `GFX_HSM_BAR_mtk_experiment_${d}`;
    const chosen = `${enabled ? "" : "NOT = { "}has_country_flag = HSM_BAR_mtk_${d}_instrumented${enabled ? "" : " }"}`;
    const ownsPolicy = `OR = { ${projects.filter(p => p.department === d).map(p => `AND = { ${selected(p)} }`).join(" ")} }`;
    const guard = `${setupView} ${ownsPolicy}`;
    window.push(button(name,x,528,base,"HSM_BAR_mtk_policy_" + choiceName,`HSM_BAR_mtk_${d}_choose_${choiceName}_desc`));
    properties.push(`${name} = { image = "[GetHSMBARMtkPolicy_${d}_${choiceName}]" }`);
    choice(`GetHSMBARMtkPolicy_${d}_${choiceName}`, [[chosen,base+"_selected"]],base);
    triggers.push(`${name}_visible = { ${guard} }`);
    triggers.push(`${name}_click_enabled = { ${guard} HSM_BAR_mtk_${d}_work_access = yes NOT = { HSM_BAR_mtk_${d}_busy = yes } }`);
    effects.push(`${name}_click = { if = { limit = { ${guard} } HSM_BAR_mtk_${d}_select_${choiceName} = yes } }`);
}
const labRecords = [];
for (const [i, p] of projects.entries()) {
    const data = experiments[i], id = `HSM_BAR_mtk_${p.id}`, base = `GFX_HSM_BAR_mtk_experiment_${p.department}`;
    for (const axis of ["rig", "control"]) {
        experimentText[`${id}_${axis}_question`] = data[axis].question;
        for (const [j, letter] of ["a","b"].entries()) {
            const name = `${id}_prepare_${axis}_${letter}`, guard = `${setupView} ${selected(p)}`;
            experimentText[name] = data[axis].options[j].label;
            experimentText[name+"_tt"] = data[axis].options[j].note;
            window.push(button(name,j ? 652 : 334,axis === "rig" ? 344 : 438,base,name,name+"_tt"));
            const paidChoice = letter === "b" ? flag(p,"paid_"+axis+"_b") : `NOT = { ${flag(p,"paid_"+axis+"_b")} }`;
            const chosen = `OR = { AND = { ${flag(p,"experiment_active")} ${paidChoice} } AND = { NOT = { ${flag(p,"experiment_active")} } ${flag(p,axis+"_"+letter)} } }`;
            choice(`GetHSMBARMtkChoice_${p.id}_${axis}_${letter}`, [[chosen,base+"_selected"]],base);
            properties.push(`${name} = { image = "[GetHSMBARMtkChoice_${p.id}_${axis}_${letter}]" }`);
            triggers.push(`${name}_visible = { ${guard} }`);
            triggers.push(`${name}_click_enabled = { ${guard} ${id}_can_prepare_experiment = yes }`);
            effects.push(`${name}_click = { if = { limit = { ${guard} } ${name} = yes } }`);
        }
    }
    for (let n=0; n<4; n++) {
        const chosen = combo(p,n), observation = `${id}_observation_${n}`;
        experimentText[observation] = [0,1].map(l => data.observations[n][l]);
        for (const [r, letter] of ["a","b"].entries()) {
            const report = `${id}_experiment_report_${letter}_${n}`;
            experimentText[report] = [0,1].map(l => `${l ? "УСТАНОВКА" : "APPARATUS"}: ${data.rig.options[n>=2?1:0].label[l]}. ${data.control.options[n%2].label[l]}.\n\n${data.observations[n][l]}\n\n${l ? "Дополнение к журналу испытаний" : "Trial log addendum"}\n${data.responses[r].reports[n][l]}`);
            labRecords.push([`${active} ${selected(p)} ${flag(p,"done")} ${flag(p,"experiment_record")} ${flag(p,"response_"+letter)} ${chosen}`,report]);
            const workOrder = `${id}_verification_${letter}_${n}`;
            experimentText[workOrder] = [0,1].map(l => `${data.observations[n][l]}\n\n${l ? "НАЗНАЧЕНА ПРОВЕРКА" : "VERIFICATION ORDERED"}: ${data.responses[r].label[l]}\n${data.responses[r].note[l]}`);
            labRecords.push([`${active} ${selected(p)} ${flag(p,"verify_running")} ${flag(p,"response_"+letter)} ${chosen}`,workOrder]);
        }
        labRecords.push([`${active} ${selected(p)} OR = { ${flag(p,"observation_ready")} ${flag(p,"verify_running")} } ${chosen}`, observation]);
    }
    labRecords.push([`${active} ${selected(p)} ${flag(p,"done")}`, `${id}_tests`]);
    for (const [r, letter] of ["a","b"].entries()) {
        const name = `${id}_respond_${letter}`, guard = `${active} ${policyView} ${selected(p)} ${flag(p,"observation_ready")} NOT = { ${flag(p,"done")} ${flag(p,"verify_running")} }`;
        experimentText[name] = data.responses[r].label;
        experimentText[name+"_tt"] = [0,1].map(l => data.responses[r].note[l] + `\n\n[GetHSMBARMtkResponseBudget_${p.id}_${letter}]`);
        choice(`GetHSMBARMtkResponseBudget_${p.id}_${letter}`, [0,1,2,3].map(n => [combo(p,n), `${id}_response_${letter}_${n}_budget`]), `${id}_response_${letter}_0_budget`);
        window.push(button(name,r ? 652 : 334,528,base,name,name+"_tt"));
        triggers.push(`${name}_visible = { ${guard} }`);
        triggers.push(`${name}_click_enabled = { ${guard} ${id}_can_respond_${letter} = yes }`);
        effects.push(`${name}_click = { if = { limit = { ${guard} } ${name} = yes } }`);
    }
}
choice("GetHSMBARMtkLabRecord",labRecords,"HSM_BAR_mtk_document_pending");
const documents = [], rewards = [];
for (const d of departments) {
    choice(`GetHSMBARMtkMethod_${d}`, [[`has_country_flag = HSM_BAR_mtk_${d}_instrumented`, "HSM_BAR_mtk_method_instrumentation"]], "HSM_BAR_mtk_method_replication");
}
for (const p of projects) {
    choice(`GetHSMBARMtkTrialBudget_${p.id}`, [[`has_country_flag = HSM_BAR_mtk_${p.department}_instrumented`, `HSM_BAR_mtk_${p.id}_budget_instrumented`]], `HSM_BAR_mtk_${p.id}_budget_replication`);
    for (const [index, stage] of stages.entries()) {
        if (stage === "tests") documents.push([`${active} ${selected(p)} ${eq("HSM_BAR_mtk_document",3)} OR = { ${flag(p,"experiment_record")} ${flag(p,"observation_ready")} ${flag(p,"verify_running")} }`, "HSM_BAR_mtk_experiment_document"]);
        const knowledge = index === 0 ? "" : index === 1 ? `OR = { ${flag(p,"theory")} ${flag(p,"done")} }` : flag(p,"done");
        if (p.id === "revolver_howitzer" && stage === "tests") documents.push([`${active} ${selected(p)} ${eq("HSM_BAR_mtk_document",3)} ${knowledge} ${flag(p,"instrumented")}`, "HSM_BAR_mtk_revolver_howitzer_tests_instrumented"]);
        documents.push([`${active} ${selected(p)} ${eq("HSM_BAR_mtk_document", index+1)} ${knowledge}`, `HSM_BAR_mtk_${p.id}_${stage}`]);
    }
    rewards.push([`${active} ${selected(p)} ${flag(p,"done")}`, `HSM_BAR_mtk_${p.id}_effects`]);
}
choice("GetHSMBARMtkDocument", documents, "HSM_BAR_mtk_document_pending");
choice("GetHSMBARMtkEffects", rewards, "HSM_BAR_mtk_no_application");
choice("GetHSMBARMtkOrigins", projects.filter(p => p.opus).map(p => [`${active} ${selected(p)} ${originView}`, `HSM_BAR_mtk_${p.id}_origins`]), "HSM_BAR_mtk_document_pending");
for (const d of departments) for (const p of preparations(d)) choice(`GetHSMBARMtkPrep_${p.id}`, [[`${active} ${flag(p,"done")}`,`HSM_BAR_mtk_${p.id}_conclusion`]], "HSM_BAR_mtk_origin_pending");
write("interface/HSM_BAR_mtk.gui", `# Generated by tools/Build-BarradCollegiumMenu.cjs. Layout is shared; department material is not.\nguiTypes = {\n containerWindowType = { name = "HSM_BAR_mtk_launcher" ${at(0,0)} buttonType = { name = "HSM_BAR_mtk_open_button" ${at(372,3)} quadTextureSprite = "GFX_state_lore_button" pdx_tooltip = "HSM_BAR_mtk_open_tt" clicksound = click_ok } }\n containerWindowType = { name = "HSM_BAR_mtk_window" ${at(0,0)} size = { width = 1000 height = 700 } orientation = center origo = center moveable = yes click_to_front = yes clipping = no show_sound = menu_open_window hide_sound = menu_close_window\n${window.join("\n")}\n }\n}`);
write("common/scripted_guis/HSM_BAR_mtk.txt", `# Generated; all gameplay actions revalidate in backend start effects.\nscripted_gui = {\n HSM_BAR_mtk_launcher = { context_type = player_context parent_window_token = politics_tab window_name = "HSM_BAR_mtk_launcher" visible = { HSM_BAR_mtk_available = yes } effects = { HSM_BAR_mtk_open_button_click = { if = { limit = { HSM_BAR_mtk_available = yes } set_variable = { HSM_BAR_mtk_open = 1 } set_variable = { HSM_BAR_mtk_department = 1 } set_variable = { HSM_BAR_mtk_project = 1 } set_variable = { HSM_BAR_mtk_document = 1 } } } } }\n HSM_BAR_mtk_window = { context_type = player_context window_name = "HSM_BAR_mtk_window" visible = { ${active} }\n properties = { ${properties.join("\n")} }\n triggers = { ${triggers.join("\n")} }\n effects = { ${effects.join("\n")} }\n }\n}`);
write("common/scripted_localisation/HSM_BAR_mtk.txt", "# Generated; document disclosure reads state only.\n" + loc.join("\n"));
write("common/scripted_triggers/HSM_BAR_mtk_ui.txt", "# Generated; presentation-only guards.\n" + helpers.join("\n"));
const strings = {
 ...experimentText,
 HSM_BAR_mtk_experiment_document: ["[GetHSMBARMtkLabRecord]", "[GetHSMBARMtkLabRecord]"],
 HSM_BAR_mtk_status_observation: ["Observation awaiting review", "Наблюдение требует решения"],
 HSM_BAR_mtk_status_verifying: ["Control series in progress", "Идёт проверочная серия"],
 HSM_BAR_mtk_method_heading: ["Workshop schedule", "Режим работы мастерских"],
 HSM_BAR_mtk_ledger_tt: ["Technical summary: costs and gameplay effects", "Техническая сводка: затраты и игровые эффекты"],
 HSM_BAR_mtk_accounting_complete: ["TECHNICAL SUMMARY\n\n[GetHSMBARMtkEffects]\n\nWork is complete. Its laboratory and workshop reservations have ended. The accepted contribution is included once in Collegium Research Results; there is no permanent upkeep.", "ТЕХНИЧЕСКАЯ СВОДКА\n\n[GetHSMBARMtkEffects]\n\nРабота завершена. Кафедры и мастерские освобождены. Принятый результат однократно учтён в результатах исследований Коллегиума; постоянного содержания нет."],
 HSM_BAR_mtk_heading: ["Magotechnical Collegium | Research programmes", "Маго-Технический Коллегиум | Исследования"],
 HSM_BAR_mtk_open_tt: ["Open the Collegium's research journals", "Открыть исследовательские журналы Коллегиума"],
 HSM_BAR_mtk_viira: ["Viira", "Виира"], HSM_BAR_mtk_leopold: ["Leopold", "Леопольд"], HSM_BAR_mtk_silver: ["Silver Star", "Сильвер Стар"], HSM_BAR_mtk_asinti: ["Asinti", "Асинти"],
 HSM_BAR_mtk_viira_heading: ["Viira Lehtola | Magic, perception and shared cognition", "Виира Лехтола | Магия, восприятие и совместное мышление"],
 HSM_BAR_mtk_leopold_heading: ["Leopold Schmeller | Applied engineering and mechanical systems", "Леопольд Шмеллер | Прикладная инженерия и механические системы"],
 HSM_BAR_mtk_silver_heading: ["Silver Star | Clinical thaumaturgy and the boundaries of life", "Сильвер Стар | Клиническая тауматургия и границы жизни"],
 HSM_BAR_mtk_asinti_heading: ["Asinti | Ritual methods and otherworld contact", "Асинти | Ритуальные методы и контакт с иными мирами"],
 HSM_BAR_mtk_start_theory: ["Begin research", "Начать исследование"], HSM_BAR_mtk_start_trials: ["Begin trials", "Начать испытания"],
 HSM_BAR_mtk_cancel_theory: ["Withdraw research", "Отозвать исследование"], HSM_BAR_mtk_cancel_trials: ["Halt trials", "Остановить испытания"],
 HSM_BAR_mtk_cancel_tt: ["Stop this stage and release its laboratory and workshop reservations. Paid costs are not refunded. Signed earlier reports remain; restarting requires full payment.", "Прервать этап и освободить кафедры и занятую мастерскую. Оплата не возвращается. Подписанные ранее отчёты сохраняются; повторный запуск оплачивается полностью."],
 HSM_BAR_mtk_protocol: ["Laboratory", "Лаборатория"],
 HSM_BAR_mtk_protocol_tt: ["Prepare the apparatus and control procedure, then respond to observations from the trial.", "Подготовить установку и контрольную проверку, затем отреагировать на наблюдения во время испытаний."],
 HSM_BAR_mtk_origins: ["Origins", "Истоки"],
 HSM_BAR_mtk_origins_tt: ["The five signed conclusions on which this Magnum Opus rests, including rejected hypotheses.", "Пять подписанных заключений, на которых основан Magnum Opus, включая отвергнутые гипотезы."],
 HSM_BAR_mtk_origin_pending: ["The conclusion is not yet signed. This dossier remains open.", "Заключение ещё не подписано. Дело остаётся открытым."],
 HSM_BAR_mtk_policy_replication: ["Sequential trials", "Последовательно"], HSM_BAR_mtk_policy_instrumentation: ["Instrumented trials", "С приборами"],
 HSM_BAR_mtk_policy_note: ["Both methods require workshops. Instrumentation adds a factory and costs more to shorten the trial schedule. The method is fixed when trials begin. Findings are implemented once, without separate applications or daily upkeep. A failed experiment still leaves a signed conclusion for later work.", "Оба метода требуют мастерских. Приборные испытания занимают дополнительную фабрику и стоят дороже, но завершаются быстрее. Метод фиксируется при запуске. Результат внедряется один раз, без разделения применений и ежедневного содержания. Неудачный опыт оставляет подписанное заключение для последующих работ."],
 HSM_BAR_mtk_doc_1: ["Proposal", "Замысел"], HSM_BAR_mtk_doc_2: ["Theory", "Исследование"], HSM_BAR_mtk_doc_3: ["Trials", "Испытания"], HSM_BAR_mtk_doc_4: ["Conclusion", "Заключение"],
 HSM_BAR_mtk_status_proposal: ["Proposal registered", "Заявка зарегистрирована"],
 HSM_BAR_mtk_status_opus: ["Magnum Opus", "Magnum Opus"],
 HSM_BAR_mtk_status_research: ["Research in progress", "Исследование ведётся"], HSM_BAR_mtk_status_trials: ["Trials in progress", "Испытания идут"],
 HSM_BAR_mtk_status_ready: ["Ready for trials", "Готово к испытаниям"], HSM_BAR_mtk_status_success: ["Completed | Applied", "Завершено | Внедрено"],
 HSM_BAR_mtk_status_partial: ["Limited application", "Частичный успех"], HSM_BAR_mtk_status_failure: ["Closed | No application", "Закрыто | Без применения"],
 HSM_BAR_mtk_select_project: ["Research register", "Реестр исследований"],
 HSM_BAR_mtk_document_pending: ["No signed report has been entered on this leaf. The proposal remains in the register; observations will be attached after the work is completed.", "На этом листе ещё нет подписанного отчёта. Заявка сохранена в реестре; записи наблюдений будут подшиты после завершения работы."],
 HSM_BAR_mtk_no_application: ["APPLICATIONS | No accepted result yet.", "ПРИМЕНЕНИЕ | Подтверждённых результатов пока нет."]
};
for (const d of departments) strings["HSM_BAR_mtk_" + d + "_progress"] = [`Reports: [?HSM_BAR_mtk_${d}_completed|0]/5 + Magnum Opus`, `Отчёты: [?HSM_BAR_mtk_${d}_completed|0]/5 + Magnum Opus`];
for (const d of departments) strings[`HSM_BAR_mtk_policy_owner_${d}`] = [`Protocol lead: $HSM_BAR_mtk_${d}$`, `Ведущая кафедра: $HSM_BAR_mtk_${d}$`];
for (const p of projects) strings[`HSM_BAR_mtk_${p.id}_accounting`] = [0,1].map(l => `${l ? "ТЕХНИЧЕСКАЯ СВОДКА" : "TECHNICAL SUMMARY"}\n\n[GetHSMBARMtkEffects]\n\n${l ? "Новый этап исследования" : "New theory stage"}: ${p.theoryCost} ${l ? "политической власти" : "political power"}; ${p.theoryDays} ${l ? "дн." : "days"}; ${p.opus ? 2 : 1} ${l ? "фабр." : "factories"}.\n\n[GetHSMBARMtkTrialBudget_${p.id}]\n\n${l ? "После первой серии потребуется выбрать дополнительную проверку. Её стоимость и срок указаны в подсказке соответствующего действия. Фабрики остаются заняты до завершения или отмены." : "The first series requires a follow-up procedure. Its cost and duration are listed on that action. Workshops stay reserved until completion or cancellation."}`);
for (const p of projects) strings[`HSM_BAR_mtk_${p.id}_index_tt`] = [0,1].map(i => `$HSM_BAR_mtk_${p.id}_title$\n[GetHSMBARMtkProject${p.number}Status]` + (p.partners ? `\n${i ? "Совместная работа" : "Joint project"}: ${faculties(p).map(d => `$HSM_BAR_mtk_${d}$`).join(" + ")}` : ""));
const origins = {
    chorus: ["Viira's binding note: the atlas gives a common reference, shared senses a narrow channel, and the sleeping lecture an indispensable refusal. Crystal traces fade; notation lets a participant correct the author. The Chorus begins where these limits meet, not where they disappear.", "Переплётная записка Вииры: атлас даёт общий ориентир, обмен ощущениями узкий канал, а спящая лекция необходимый отказ. Кристаллические следы гаснут; нотация позволяет участнику исправить автора. Хор начинается на пересечении этих границ, а не с их исчезновения."],
    manufactory: ["Leopold's assembly note: approved prosthetic patterns, staffed repair and a failed gun that stopped everything together. Add a drive with a reliable stop and a sorter permitted to hesitate. The line must inherit all five conclusions, especially the one nobody wished to sign.", "Сборочная записка Леопольда: проверенные чертежи протезов, обслуживаемый ремонт и неудачная пушка, в которой всё останавливалось разом. Затем привод с надёжной остановкой и сортировщик, которому позволено сомневаться. Линия наследует все пять заключений, особенно то, которое никто не хотел подписывать."],
    last_minute: ["Silver's covering letter: support is not healing, a tissue store is not an inexhaustible body, and stillness is not youth. Sterile instruments and relief from pain matter because a patient must return to ordinary life. The Last Minute buys time for treatment; these five casebooks set its boundaries.", "Сопроводительное письмо Сильвера: поддержка не равна исцелению, запас тканей не равен неисчерпаемому телу, а неподвижность не равна молодости. Чистый инструмент и облегчение боли важны потому, что пациенту предстоит вернуться к обычной жизни. Последняя минута даёт время для лечения; эти пять журналов определяют её пределы."],
    contact: ["Asinti's forwarding note: an ending, a rejected witness, a trace that is not history, a boundary that can be measured, and a vessel that cannot keep its visitor. Contact requires all five. The silence of one unsuccessful study must not be filled with another's promise.", "Передаточная записка Асинти: завершение, отвергнутый свидетель, след, который не является историей, измеримая граница и сосуд, который не может удержать гостя. Контакту нужны все пять. Молчание неудачного исследования нельзя заполнять обещаниями другого."]
};
for (const p of projects.filter(p => p.opus)) strings[`HSM_BAR_mtk_${p.id}_origins`] = [0,1].map(i => origins[p.id][i] + "\n\n" + preparations(p.department).map((q,n) => `${n+1}. $HSM_BAR_mtk_${q.id}_title$\n[GetHSMBARMtkPrep_${q.id}]`).join("\n\n"));
for (const [i, language] of ["english", "russian"].entries()) write(`localisation/${language}/HSM_BAR_mtk_ui_l_${language}.yml`, `\ufeffl_${language}:\n` + Object.entries(strings).map(([k, v]) => ` ${k}:0 ${JSON.stringify(v[i])}`).join("\n"));
console.log(`Collegium menu: ${departments.length} departments, ${projects.length} projects, ${projects.length * stages.length} gated document pages per language.`);
