"use strict";

// Reuse the existing decision definitions as the authored action contract.
// Only the generated, human-facing Service adapter is owned by this builder.
const fs = require("node:fs");
const path = require("node:path");
const assert = require("node:assert/strict");
const { parse, prop } = require("./Test-BarradArchiveSkin.cjs");
const root = path.resolve(__dirname, "..");
const mod = path.join(root, "mod/HoISubmod");
const P = "HSM_BAR_service_gui_";
const investigationIds = Object.fromEntries(["rock","titan","entity","amulet","plants","echo","compass"].map(c=>[["echo","compass"].includes(c)?"HSM_BAR_rumor_"+c:`HSM_BAR_case_${c}_investigate`,c]));
const regions = ["local", "equus", "griffonia", "north", "riverlands", "zebrica"];
const cases = ["rock", "titan", "entity", "amulet", "reactor", "crown", "chalice", "phylactery", "darkheart", "grover", "rosa", "herald", "sombra", "echo", "marsh", "compass", "plants", "zebrica"];
const caseRegion = { darkheart: 2, sombra: 2, grover: 3, herald: 3, chalice: 4, phylactery: 4, rosa: 4, marsh: 5, zebrica: 6 };
const sources = ["anomalies", "cases_rumors", "cases_studies", "core", "residencies", "normalization", "republic", "research_decisions"];
const read = rel => parse(fs.readFileSync(path.join(mod, rel), "utf8"), true);
const scalar = v => /^[^\s{}#"=<>]+$/.test(v) ? v : JSON.stringify(v);
function script(nodes) {
    return nodes.map(n => n.key === null ? scalar(n.value) : `${n.key} ${n.op} ${Array.isArray(n.value) ? `{ ${script(n.value)} }` : scalar(n.value)}`).join("\n");
}
function emulateFallback(nodes) {
    return nodes.map(n => n.key === "has_dlc" && n.value === "Gotterdammerung"
        ? {key:"always", op:"=", value:"no"}
        : {...n, value: Array.isArray(n.value) ? emulateFallback(n.value) : n.value});
}
const categoryMap = new Map();
for (const file of fs.readdirSync(path.join(mod, "common/decisions/categories")).filter(f => /^HSM_BAR.*\.txt$/.test(f))) {
    for (const cat of read("common/decisions/categories/" + file)) categoryMap.set(cat.key, cat.value);
}
const actions = [];
for (const source of sources) for (const category of read(`common/decisions/HSM_BAR_${source}.txt`)) for (const node of category.value) {
    if (!Array.isArray(node.value) || !node.key?.startsWith("HSM_BAR_")) continue;
    if (prop(node.value, "target_trigger")) continue; // Fielddesk owns targeted operations.
    if (source === "republic" && !["HSM_BAR_recover_science", "HSM_BAR_reclaim_fields", "HSM_BAR_heal_homeland"].includes(node.key)) continue;
    if (/^HSM_BAR_research_(clinic|grid)_/.test(node.key)) continue;
    const categoryDef = categoryMap.get(category.key);
    assert(categoryDef, "Missing category " + category.key);
    const subject = cases.find(c => new RegExp(`_(?:case_|study_|rumor_)?${c}(?:_|$)`).test(node.key));
    const region = regions.findIndex(r => new RegExp(`_${r}(?:_|$)`).test(node.key)) + 1 || caseRegion[subject] || 1;
    const fallback = source === "cases_studies" || /_fallback$/.test(node.key);
    const body = fallback ? emulateFallback(node.value) : node.value;
    const categoryVisible = (prop(categoryDef, "visible") || []).filter(n => n.key !== "HSM_BAR_service_legacy_visible");
    const get = key => script(prop(body, key) || []);
    const cost = Number(prop(body, "cost") || 0), days = Number(prop(body, "days_remove") || 0);
    assert(Number.isFinite(cost) && cost >= 0 && Number.isFinite(days) && days >= 0, node.key + ": unsupported cost/duration");
    const modifier = prop(body, "modifier") || [];
    assert(modifier.every(n => n.key === "civilian_factory_use"), node.key + ": adapter must explicitly support each modifier");
    actions.push({id: node.key, number: actions.length + 1, key: P + node.key.slice(8), source, category:category.key,
        subject: subject ? cases.indexOf(subject) + 1 : 0, case: subject, region, investigation: investigationIds[node.key],
        categoryVisible: script(categoryVisible), visible:get("visible"), available:get("available"),
        complete:get("complete_effect"), finish:get("remove_effect"), cancel:get("cancel_effect"), cancelWhen:get("cancel_trigger"),
        cost, days, factories:Number(prop(modifier, "civilian_factory_use") || 0), cooldown:Number(prop(body, "days_re_enable") || 0), once:prop(body,"fire_only_once") === "yes"});
}
assert(actions.length > 100, "Service action inventory unexpectedly reduced");
const outputs = {};
const out = (file, body) => { outputs[file] = body.trimEnd() + "\n"; };
let triggers = `${P}actor = { tag = BAR has_country_flag = HSM_BAR_active has_country_flag = HSM_BAR_directorate has_country_flag = HSM_BAR_service_founded has_capitulated = no is_subject = no controls_state = 624 }
${P}available = { ${P}actor = yes is_ai = no }
HSM_BAR_service_legacy_visible = { NOT = { AND = { is_ai = no has_country_flag = HSM_BAR_directorate has_country_flag = HSM_BAR_service_founded } } }
`;
let effects = "", missions = "", selectors = "";
const loc = {english:{}, russian:{}};
const localeKeys = Object.fromEntries(["english", "russian"].map(lang => [lang, new Set(fs.readdirSync(path.join(mod,"localisation",lang))
    .filter(f=>f.endsWith(".yml")).flatMap(f=>[...fs.readFileSync(path.join(mod,"localisation",lang,f),"utf8").matchAll(/^\s*([^\s:#]+):\d*\s*"/gm)].map(m=>m[1])))]));
const put = (key,en,ru) => { loc.english[key]=en; loc.russian[key]=ru; };
function selector(name, entries, fallback) {
    return `defined_text = { name = ${name}\n${entries.map(([condition,text]) => `text = { trigger = { ${condition} } localization_key = ${text} }`).join("\n")}\ntext = { localization_key = ${fallback} } }\n`;
}
const field = (key,font,text,x,y,w,h) => `instantTextboxType = { name = "${key}" position = { x = ${x} y = ${y} } font = "${font}" text = "${text}" maxWidth = ${w} maxHeight = ${h} format = left alwaystransparent = yes }`;
const button = (key,sprite,x,y,label,tooltip) => `buttonType = { name = "${key}" position = { x = ${x} y = ${y} } quadTextureSprite = "${sprite}" ${label ? `buttonText = "${label}" buttonFont = "HSM_BAR_archive_ink"` : ""} pdx_tooltip = "${tooltip}" clicksound = click_ok }`;
let refresh = `clear_array = ${P}subjects\nclear_array = ${P}actions\n`;
for (let r=1;r<=6;r++) triggers += `${P}region_${r}_open = { has_country_flag = HSM_BAR_region_${regions[r-1]}_open }\n`;
for (const a of actions) {
    const running = `${a.key}_running`, done=`${a.key}_done`, cooldown=`${a.key}_cooldown`;
    const slotRegion = a.case === "crown" && a.source !== "cases_rumors"
        ? `OR = { ${[2,3,6].map(r=>`check_variable = { ${P}region = ${r} }`).join(" ")} }`
        : `check_variable = { ${P}region = ${a.region} }`;
    triggers += `${a.key}_visible = { ${P}actor = yes ${a.categoryVisible} ${a.visible} ${a.once ? `NOT = { has_country_flag = ${done} }` : ""} }
${a.key}_listed = { ${slotRegion} OR = { ${a.key}_visible = yes has_country_flag = ${running} ${a.investigation?`HSM_BAR_investigation_${a.investigation}_can_open = yes`:""} } }
${a.key}_can_start = { ${P}available = yes ${a.key}_visible = yes ${a.available}
 ${a.investigation?"always = no":""}
 NOT = { has_political_power < ${a.cost} } NOT = { has_country_flag = ${running} } NOT = { has_country_flag = ${cooldown} }
 ${a.days ? `NOT = { has_active_mission = ${a.key}_mission }` : ""}
 ${a.factories ? `num_of_civilian_factories_available_for_projects > ${a.factories-1}` : ""} }
`;
    const end = `clr_country_flag = ${running}\n${a.cooldown ? `set_country_flag = { flag = ${cooldown} days = ${a.cooldown} }` : ""}`;
    const cancel = `${a.cancel}\n${end}\n${P}refresh_factories = yes`;
    effects += `${a.key}_start = { if = { limit = { ${a.key}_can_start = yes }
 add_political_power = ${-a.cost}
 ${a.days ? `set_country_flag = ${running}` : ""}
 ${a.complete}
 ${a.days ? `activate_mission = ${a.key}_mission` : `${a.once ? `set_country_flag = ${done}` : ""}\n${a.cooldown ? `set_country_flag = { flag = ${cooldown} days = ${a.cooldown} }` : ""}`}
 ${P}refresh_factories = yes
 } }
${a.key}_cancel = { if = { limit = { has_country_flag = ${running} }
 ${a.days ? `remove_mission = ${a.key}_mission` : ""} ${cancel} } }
`;
    if (a.days) {
        missions += `${a.key}_mission = { allowed = { original_tag = BAR } visible = { always = no } activation = { always = no } available = { always = no }
 days_mission_timeout = ${a.days} is_good = no
 cancel_trigger = { OR = { ${P}actor = no ${a.cancelWhen ? `AND = { ${a.cancelWhen} }` : ""} } }
 cancel_effect = { hidden_effect = { ${a.key}_cancel = yes } }
 timeout_effect = { hidden_effect = { if = { limit = { has_country_flag = ${running} NOT = { has_country_flag = { flag = ${running} days < ${a.days} } } }
 if = { limit = { ${P}actor = yes ${a.cancelWhen ? `NOT = { AND = { ${a.cancelWhen} } }` : ""} }
 ${a.finish} ${a.once ? `set_country_flag = ${done}` : ""}
 } else = { ${a.cancel} }
 ${end} ${P}refresh_factories = yes
 } } }
 }\n`;
    }
    put(a.key+"_price", `${a.cost} political power${a.days ? ` / ${a.days} days` : ""}${a.factories ? ` / ${a.factories} civilian factory` : ""}`, `${a.cost} политвласти${a.days ? ` / ${a.days} дн.` : ""}${a.factories ? ` / ${a.factories} гражд. фабрика` : ""}`);
    if (a.days) put(a.key+"_remaining", `IN PROGRESS / [?days_mission_timeout@${a.key}_mission|0] days remaining`, `ВЫПОЛНЯЕТСЯ / осталось [?days_mission_timeout@${a.key}_mission|0] дн.`);
    const desc = ["english","russian"].map(lang=>localeKeys[lang].has(a.id+"_desc") ? `\\n\\n$${a.id}_desc$` : "");
    if (a.investigation) put(a.key+"_tooltip", `$${a.id}$\\nOpen the evidence file, compare enclosures and select an expedition protocol. Opening the file spends nothing.`, `$${a.id}$\\nОткрыть материалы дела, сопоставить приложения и выбрать протокол экспедиции. Чтение дела ничего не стоит.`);
    else put(a.key+"_tooltip", `$${a.id}$\\n$${a.key}_price$${desc[0]}`, `$${a.id}$\\n$${a.key}_price$${desc[1]}`);
}
// Both lists contain only currently visible or already-running work. Rebuild on navigation and daily maintenance.
for (let s=0;s<=cases.length;s++) {
    const matching=actions.filter(a=>a.subject===s);
    if (!matching.length) continue;
    refresh += `if = { limit = { OR = { ${matching.map(a=>a.key+"_listed = yes").join(" ")} } } add_to_array = { ${P}subjects = ${s} } }\n`;
}
refresh += `if = { limit = { NOT = { is_in_array = { array = ${P}subjects value = ${P}subject } } } set_variable = { ${P}subject = 0 } }\n`;
for (const a of actions) refresh += `if = { limit = { OR = {
 AND = { NOT = { has_country_flag = ${P}queue } check_variable = { ${P}subject = ${a.subject} } ${a.key}_listed = yes }
 AND = { has_country_flag = ${P}queue OR = { has_country_flag = ${a.key}_running ${a.investigation?`has_country_flag = HSM_BAR_investigation_${a.investigation}_running`:""} } }
 } } add_to_array = { ${P}actions = ${a.number} } }\n`;
effects += `${P}refresh = { if = { limit = { ${P}available = yes }
 if = { limit = { has_variable = ${P}open } clear_variable = HSM_BAR_investigation_open }
 set_country_flag = ${P}initialized
 if = { limit = { NOT = { has_variable = ${P}region } } set_variable = { ${P}region = 1 } }
 if = { limit = { NOT = { has_variable = ${P}subject } } set_variable = { ${P}subject = 0 } }
 ${refresh} } }
${P}refresh_factories = { hidden_effect = {
 set_variable = { ${P}factories = 0 }
 ${actions.filter(a=>a.factories).map(a=>`if = { limit = { has_country_flag = ${a.key}_running } add_to_variable = { ${P}factories = ${a.factories} } }`).join("\n")}
 if = { limit = { has_dynamic_modifier = { modifier = HSM_BAR_service_capacity } } force_update_dynamic_modifier = yes }
 } }
${P}teardown = { hidden_effect = {
 ${actions.filter(a=>a.days).map(a=>`${a.key}_cancel = yes`).join("\n")}
 clear_variable = ${P}open clear_variable = ${P}region clear_variable = ${P}subject
 clear_array = ${P}subjects clear_array = ${P}actions clr_country_flag = ${P}queue clr_country_flag = ${P}initialized
 ${P}refresh_factories = yes
 } }
${P}pulse = { hidden_effect = {
 if = { limit = { ${P}actor = no } ${P}teardown = yes }
 else_if = { limit = { has_variable = ${P}open } ${P}refresh = yes }
 } }
`;
const strings = [
 ["title","S.C.P. | Operations register","S.C.P. | Оперативные дела"],
 ["subtitle","Regional offices / field assignments and laboratory work","Региональные отделения / полевые задания и лабораторные работы"],
 ["office","Office programmes","Программы отделения"],
 ["office_body","The regional office collects requests for field teams, laboratory time and agreements with outside contacts. Each signed assignment remains with its case until the report returns.","Отделение собирает заявки на полевые работы, лабораторные исследования и соглашения с внешними контактами. Подписанное поручение остаётся в деле до возвращения отчёта."],
 ["archive","Documents","Документы"], ["fielddesk","Foreign assignments","Зарубежные задания"],
 ["start","Authorize assignment","Утвердить задание"], ["cancel","Recall assignment. Spent political power and supplies are not refunded.","Отозвать задание. Потраченные политвласть и снаряжение не возвращаются."],
 ["running","IN PROGRESS","ВЫПОЛНЯЕТСЯ"], ["ready","Awaiting authorization","Ожидает утверждения"],
 ["locked","Requirements not met","Условия не выполнены"], ["empty","No assignments in this file.","В этом деле нет поручений."],
 ["close","Close","Закрыть"], ["queue","Active assignments","Текущие задания"], ["files","Case files","Дела отделения"],
 ["region_locked","The regional office has not been established.","Региональное отделение ещё не создано."],
 ["none","Regional file","Региональная папка"],
 ["investigate","Investigation","Расследование"], ["protocol_price","Evidence / expedition protocol","Материалы / протокол экспедиции"]
];
for(const [k,en,ru] of strings) put(P+k,en,ru);
const regionLabels=[ ["Barrad","Баррад"],["Equus","Эквус"],["Griffonia","Грифония"],["The North","Север"],["Riverlands","Речные земли"],["Zebrica","Зебрика"] ];
regionLabels.forEach(([en,ru],i)=>put(P+"region_"+(i+1),en,ru));
selectors += selector("GetHSMBARServiceSubjectEntry", cases.map((c,i)=>[`check_variable = { ${P}subject_entry = ${i+1} }`,`HSM_BAR_archive_${c}_title`]),P+"office");
selectors += selector("GetHSMBARServiceSubjectTitle", cases.map((c,i)=>[`check_variable = { ${P}subject = ${i+1} }`,`HSM_BAR_archive_${c}_title`]),P+"office");
selectors += selector("GetHSMBARServiceSubjectBody", cases.map((c,i)=>[`check_variable = { ${P}subject = ${i+1} }`,`HSM_BAR_archive_${c}_intake`]),P+"office_body");
selectors += selector("GetHSMBARServiceActionName",actions.map(a=>[`check_variable = { ${P}entry = ${a.number} }`,a.id]),P+"none");
selectors += selector("GetHSMBARServiceActionPrice",actions.map(a=>[`check_variable = { ${P}entry = ${a.number} }`,a.investigation?P+"protocol_price":a.key+"_price"]),P+"none");
selectors += selector("GetHSMBARServiceActionTip",actions.map(a=>[`check_variable = { ${P}entry = ${a.number} }`,a.key+"_tooltip"]),P+"none");
selectors += selector("GetHSMBARServiceActionState",[
 ...actions.filter(a=>a.days).map(a=>[`check_variable = { ${P}entry = ${a.number} } has_country_flag = ${a.key}_running`,a.key+"_remaining"]),
 ...actions.filter(a=>a.investigation).map(a=>[`check_variable = { ${P}entry = ${a.number} }`,`HSM_BAR_investigation_${a.investigation}_status`]),
 ...actions.map(a=>[`check_variable = { ${P}entry = ${a.number} } ${a.key}_can_start = yes`,P+"ready"])
],P+"locked");
selectors += selector("GetHSMBARServiceRowSkin",[[`check_variable = { ${P}subject = ${P}subject_entry }`,"GFX_HSM_BAR_archive_index_selected"]],"GFX_HSM_BAR_archive_index");
const caseopen = `set_variable = { HSM_BAR_archive_region = ${P}region } set_variable = { HSM_BAR_archive_page = 1 } set_variable = { HSM_BAR_archive_case = ${P}subject } set_variable = { HSM_BAR_archive_document = 1 } clear_variable = HSM_BAR_archive_copy clear_variable = ${P}open set_variable = { HSM_BAR_archive_open = 1 }`;
let uiEffects=`${P}close_click = { clear_variable = ${P}open }
${P}subject_button_click = { if = { limit = { ${P}available = yes is_in_array = { array = ${P}subjects value = ${P}subject_entry } } set_variable = { ${P}subject = ${P}subject_entry } clr_country_flag = ${P}queue ${P}refresh = yes } }
${P}archive_click = { if = { limit = { ${P}available = yes } ${caseopen} HSM_BAR_archive_refresh = yes } }
${P}fielddesk_click = { if = { limit = { ${P}available = yes } clear_variable = ${P}open set_variable = { HSM_BAR_fielddesk_open = 1 } HSM_BAR_fielddesk_refresh = yes } }
${P}investigate_click = { if = { limit = { ${P}available = yes } ${actions.filter(a=>a.investigation).map(a=>`if = { limit = { check_variable = { ${P}subject = ${a.subject} } } HSM_BAR_investigation_${a.investigation}_open = yes }`).join("\n")} } }
${P}queue_click = { if = { limit = { has_country_flag = ${P}queue } clr_country_flag = ${P}queue } else = { set_country_flag = ${P}queue } ${P}refresh = yes }
${P}start_click = { hidden_effect = { if = { limit = { ${P}available = yes is_in_array = { array = ${P}actions value = ${P}entry } }
 ${actions.map(a=>`if = { limit = { check_variable = { ${P}entry = ${a.number} } } ${a.investigation?`HSM_BAR_investigation_${a.investigation}_open`:`${a.key}_start`} = yes }`).join("\n")}
 ${P}refresh = yes } } }
${P}cancel_click = { hidden_effect = { if = { limit = { ${P}available = yes }
 ${actions.filter(a=>a.days).map(a=>`if = { limit = { check_variable = { ${P}entry = ${a.number} } } ${a.key}_cancel = yes }`).join("\n")}
 ${P}refresh = yes } } }
`;
let uiTriggers=`${P}start_click_enabled = { OR = { ${actions.map(a=>`AND = { check_variable = { ${P}entry = ${a.number} } ${a.investigation?`HSM_BAR_investigation_${a.investigation}_can_open`:`${a.key}_can_start`} = yes }`).join("\n")} } }
${P}investigate_visible = { OR = { ${actions.filter(a=>a.investigation).map(a=>`AND = { check_variable = { ${P}subject = ${a.subject} } HSM_BAR_investigation_${a.investigation}_can_open = yes }`).join("\n")} } }
${P}cancel_visible = { OR = { ${actions.filter(a=>a.days).map(a=>`AND = { check_variable = { ${P}entry = ${a.number} } has_country_flag = ${a.key}_running }`).join("\n")} } }
${P}empty_visible = { check_variable = { ${P}actions^num = 0 } }
${P}fielddesk_click_enabled = { has_country_flag = HSM_BAR_foreign_mandate }
`;
let tabs="";
for(let i=1;i<=6;i++){
 tabs += button(P+"region_"+i,"GFX_HSM_BAR_archive_tab",24+(i-1)*154,104,P+"region_"+i,P+"region_"+i)+"\n";
 uiTriggers+=`${P}region_${i}_click_enabled = { ${P}region_${i}_open = yes }\n`;
 uiEffects+=`${P}region_${i}_click = { if = { limit = { ${P}available = yes ${P}region_${i}_open = yes } set_variable = { ${P}region = ${i} } set_variable = { ${P}subject = 0 } clr_country_flag = ${P}queue ${P}refresh = yes } }\n`;
 selectors+=selector("GetHSMBARServiceRegion"+i,[[`check_variable = { ${P}region = ${i} }`,"GFX_HSM_BAR_archive_tab_selected"]],"GFX_HSM_BAR_archive_tab");
}
out("common/scripted_guis/HSM_BAR_service_gui.txt",`scripted_gui = {
 ${P}launcher = { context_type = player_context parent_window_token = politics_tab window_name = "${P}launcher"
 visible = { ${P}available = yes } effects = { ${P}open_click = { if = { limit = { ${P}available = yes }
 set_variable = { ${P}open = 1 } clear_variable = HSM_BAR_archive_open clear_variable = HSM_BAR_fielddesk_open ${P}refresh = yes } } } }
 ${P}window = { context_type = player_context window_name = "${P}window"
 visible = { ${P}available = yes has_variable = ${P}open }
 dynamic_lists = { ${P}subject_list = { array = ${P}subjects value = ${P}subject_entry entry_container = "${P}subject_row" }
 ${P}action_list = { array = ${P}actions value = ${P}entry entry_container = "${P}action_row" } }
 properties = { ${P}subject_button = { image = "[GetHSMBARServiceRowSkin]" }
 ${regions.map((_,i)=>`${P}region_${i+1} = { image = "[GetHSMBARServiceRegion${i+1}]" }`).join("\n")} }
 triggers = { ${uiTriggers} } effects = { ${uiEffects} }
 } }
`);
out("interface/HSM_BAR_service_gui.gui",`guiTypes = {
 containerWindowType = { name = "${P}launcher" position = { x = 0 y = 0 }
 ${button(P+"open","GFX_state_lore_button",330,3,null,P+"title")} }
 containerWindowType = { name = "${P}window" position = { x = 0 y = 0 } size = { width = 1000 height = 700 } orientation = center origo = center moveable = yes click_to_front = yes clipping = no
 background = { name = "${P}background" quadTextureSprite = "GFX_HSM_BAR_archive_folder" }
 buttonType = { name = "${P}input_floor" position = { x = 0 y = 0 } size = { x = 1000 y = 700 } quadTextureSprite = "GFX_HSM_BAR_archive_folder" alwaystransparent = no }
 buttonType = { name = "${P}input_shield" position = { x = 0 y = 0 } size = { x = 1000 y = 700 } quadTextureSprite = "GFX_HSM_BAR_archive_folder" alwaystransparent = no }
 ${field(P+"title","hoi_24header",P+"title",24,20,860,30)}
 ${field(P+"subtitle","hoi_16mbs",P+"subtitle",24,60,900,32)}
 ${button(P+"close","GFX_HSM_BAR_archive_close",944,20,null,P+"close")}
 ${tabs}
 containerWindowType = { name = "${P}subject_scroll" position = { x = 24 y = 160 } size = { width = 278 height = 424 } clipping = yes verticalScrollbar = "right_vertical_slider" scroll_wheel_factor = 40 smooth_scrolling = yes autohide_scrollbars = yes
 gridboxType = { name = "${P}subject_list" position = { x = 0 y = 0 } size = { width = 263 height = 424 } slotsize = { width = 263 height = 42 } max_slots_horizontal = 1 } }
 ${button(P+"queue","GFX_HSM_BAR_archive_index",24,590,P+"queue",P+"queue")}
 ${button(P+"archive","GFX_HSM_BAR_archive_tab",330,634,P+"archive",P+"archive")}
 ${button(P+"investigate","GFX_HSM_BAR_archive_edition",492,634,P+"investigate",P+"investigate")}
 ${button(P+"fielddesk","GFX_HSM_BAR_archive_edition",744,634,P+"fielddesk",P+"fielddesk")}
 ${field(P+"subject_title","HSM_BAR_archive_heading","[GetHSMBARServiceSubjectTitle]",354,160,578,55)}
 containerWindowType = { name = "${P}brief_scroll" position = { x = 354 y = 220 } size = { width = 590 height = 140 } clipping = yes verticalScrollbar = "right_vertical_slider" scroll_wheel_factor = 35 smooth_scrolling = yes autohide_scrollbars = yes
 ${field(P+"subject_body","HSM_BAR_archive_ink","[GetHSMBARServiceSubjectBody]",0,0,570,1500)} }
 containerWindowType = { name = "${P}action_scroll" position = { x = 354 y = 376 } size = { width = 594 height = 240 } clipping = yes verticalScrollbar = "right_vertical_slider" scroll_wheel_factor = 72 smooth_scrolling = yes autohide_scrollbars = yes
 gridboxType = { name = "${P}action_list" position = { x = 0 y = 0 } size = { width = 580 height = 240 } slotsize = { width = 580 height = 88 } max_slots_horizontal = 1 } }
 ${field(P+"empty","HSM_BAR_archive_ink",P+"empty",354,386,560,64)}
 }
 containerWindowType = { name = "${P}subject_row" size = { width = 263 height = 42 }
 ${button(P+"subject_button","GFX_HSM_BAR_archive_index",0,0,"[GetHSMBARServiceSubjectEntry]","[GetHSMBARServiceSubjectEntry]")} }
 containerWindowType = { name = "${P}action_row" size = { width = 580 height = 88 }
 ${field(P+"action_title","HSM_BAR_archive_ink","[GetHSMBARServiceActionName]",0,0,490,38)}
 ${field(P+"action_price","HSM_BAR_archive_ink","[GetHSMBARServiceActionPrice]",0,40,490,20)}
 ${field(P+"action_state","HSM_BAR_archive_ink","[GetHSMBARServiceActionState]",0,62,490,20)}
 ${button(P+"start","GFX_HSM_BAR_archive_next",496,4,null,"[GetHSMBARServiceActionTip]")}
 ${button(P+"cancel","GFX_HSM_BAR_archive_close",540,4,null,P+"cancel")}
 }
}`);
out("common/scripted_triggers/HSM_BAR_service_gui.txt",triggers);
out("common/scripted_effects/HSM_BAR_service_gui.txt",effects);
out("common/decisions/HSM_BAR_service_gui.txt",`${P}timers = {\n${missions}}`);
out("common/decisions/categories/HSM_BAR_service_gui.txt",`${P}timers = { allowed = { original_tag = BAR } visible = { always = no } }`);
out("common/scripted_localisation/HSM_BAR_service_gui.txt",selectors);
for (const lang of ["english","russian"]) out(`localisation/${lang}/HSM_BAR_service_gui_l_${lang}.yml`,"\uFEFFl_"+lang+":\n"+Object.entries(loc[lang]).map(([k,v])=>` ${k}:0 "${v.replace(/"/g,'\\"')}"`).join("\n"));
function build(check = false) {
    const errors=[];
    for(const [file,text] of Object.entries(outputs)) {
        const target=path.join(mod,file);
        if(check) {
            if(!fs.existsSync(target)||fs.readFileSync(target,"utf8").replace(/\r\n/g,"\n")!==text) errors.push(file);
        } else { fs.mkdirSync(path.dirname(target),{recursive:true}); fs.writeFileSync(target,text,"utf8"); }
    }
    assert(!errors.length,"Stale Service GUI outputs: "+errors.join(", "));
    console.log(`${check ? "Verified" : "Built"} ${actions.length} Service actions, ${actions.filter(a=>a.days).length} hidden timers, six regions, ${Object.keys(outputs).length} files.`);
}
module.exports={actions,regions,cases,outputs,parse,prop,script,build,root,mod,P};
if(require.main===module) build(process.argv.includes("--check"));
