"use strict";
// Authored comparisons and expedition protocols, using the existing case-completion authority.
const fs=require("node:fs"), path=require("node:path"), assert=require("node:assert/strict");
const {parse,prop}=require("./Test-BarradArchiveSkin.cjs");
const root=path.resolve(__dirname,".."), mod=path.join(root,"mod/HoISubmod"), P="HSM_BAR_investigation_";
const cases=JSON.parse(fs.readFileSync(path.join(__dirname,"data/barrad-investigations.json"),"utf8").replace(/^\uFEFF/,""));
const read=f=>parse(fs.readFileSync(path.join(mod,f),"utf8"),true);
const scalar=v=>/^[^\s{}#"=<>]+$/.test(v)?v:JSON.stringify(v);
const script=ns=>ns.map(n=>`${n.key} ${n.op} ${Array.isArray(n.value)?`{ ${script(n.value)} }`:scalar(n.value)}`).join("\n");
const sources=[...read("common/decisions/HSM_BAR_anomalies.txt"),...read("common/decisions/HSM_BAR_cases_rumors.txt")].flatMap(n=>n.value);
const expected={rock:1,titan:2,entity:3,amulet:4,plants:17,echo:14,compass:16};
assert.equal(cases.length,7);assert.deepEqual(Object.fromEntries(cases.map(c=>[c.id,c.subject])),expected);
for(const c of cases){
 c.key=P+c.id;
 c.source=["echo","compass"].includes(c.id)?"HSM_BAR_rumor_"+c.id:`HSM_BAR_case_${c.id}_investigate`;
 c.sourceBody=sources.find(n=>n.key===c.source)?.value;assert(c.sourceBody,c.id);
 c.legacy="HSM_BAR_service_gui_"+c.source.slice(8);
 assert.equal(c.documents.length,2);assert(c.documents.every(d=>d.fragments.length===3));
 assert(c.pair.length===2&&c.pair.every(n=>Number.isInteger(n)&&n>=1&&n<=3));
 assert.equal(c.methods.length,3);assert.equal(c.methods.filter(m=>m.qualifies).length,2);
 for(const m of c.methods){assert(/^[a-z_]+$/.test(m.id));assert(m.days>=14&&m.days<=28);assert(m.cost>=20&&m.cost<=35);}
}
const outputs={},loc={en:{},ru:{}};
const put=(key,en,ru)=>{loc.en[key]=en;loc.ru[key]=ru;};
const bilingual=(key,pair)=>{assert(pair.en&&pair.ru,key);put(key,pair.en,pair.ru);};
const out=(file,text)=>{outputs[file]=text.trimEnd()+"\n";};
const select=(name,entries,fallback)=>`defined_text = { name = ${name}\n${entries.map(([gate,key])=>`text = { trigger = { ${gate} } localization_key = ${key} }`).join("\n")} text = { localization_key = ${fallback} } }\n`;
const chosen=c=>`check_variable = { ${P}case = ${c.subject} }`;
let triggers=`${P}actor = { HSM_BAR_service_gui_available = yes HSM_BAR_case_local_access = yes }\n`;
let effects="",missions="",selectors="",clicks="",gates="",properties="";
for(const c of cases){
 const known=`OR = { AND = { ${script(prop(c.sourceBody,"visible")||[])} } has_country_flag = HSM_BAR_case_${c.id}_investigated has_country_flag = HSM_BAR_study_${c.id}_done }`;
 triggers+=`${c.key}_can_open = { ${P}actor = yes ${known} }
${c.key}_live = { ${c.key}_can_open = yes ${script(prop(c.sourceBody,"available")||[])} NOT = { has_country_flag = HSM_BAR_case_${c.id}_investigated } }
${c.key}_idle = { NOT = { has_country_flag = ${c.key}_running has_country_flag = ${c.legacy}_running has_active_mission = ${c.legacy}_mission ${c.methods.map((_,i)=>`has_active_mission = ${c.key}_${i+1}_mission`).join(" ")} } }
${c.key}_can_compare = { ${P}window = yes ${chosen(c)} check_variable = { ${P}page = 1 } check_variable = { ${P}a > 0 } check_variable = { ${P}a < 4 } check_variable = { ${P}b > 0 } check_variable = { ${P}b < 4 } }
`;
 effects+=`${c.key}_open = { if = { limit = { ${c.key}_can_open = yes }
 set_country_flag = ${P}initialized set_variable = { ${P}case = ${c.subject} } set_variable = { ${P}open = 1 }
 set_variable = { ${P}page = 1 } set_variable = { ${P}method = 1 } set_variable = { ${P}report = 1 }
 clear_variable = ${P}a clear_variable = ${P}b clear_variable = ${P}feedback
 ${["a","b","method"].flatMap(v=>[1,2,3].map(i=>`set_variable = { ${P}frame_${v}${i} = ${v==="method"&&i===1?2:1} }`)).join("\n")}
 ${c.methods.map((_,i)=>`if = { limit = { has_country_flag = ${c.key}_${i+1}_running }
 set_variable = { ${P}method = ${i+1} } ${[1,2,3].map(j=>`set_variable = { ${P}frame_method${j} = ${j===i+1?2:1} }`).join(" ")} }`).join("\n")}
 ${c.methods.map((m,i)=>({m,i})).sort((a,b)=>Number(a.m.qualifies)-Number(b.m.qualifies)).map(({i})=>`if = { limit = { has_country_flag = ${c.key}_${i+1}_reported } set_variable = { ${P}report = ${i+1} } }`).join("\n")}
 clear_variable = HSM_BAR_service_gui_open clear_variable = HSM_BAR_archive_open clear_variable = HSM_BAR_fielddesk_open
 } }
${c.key}_compare = { if = { limit = { ${c.key}_can_compare = yes }
 if = { limit = { check_variable = { ${P}a = ${c.pair[0]} } check_variable = { ${P}b = ${c.pair[1]} } }
 set_country_flag = ${c.key}_matched set_variable = { ${P}feedback = 1 }
 } else = { set_variable = { ${P}feedback = 2 } } } }
`;
 c.documents.forEach((d,i)=>{bilingual(`${c.key}_doc_${i+1}`,d.title);d.fragments.forEach((f,j)=>bilingual(`${c.key}_fragment_${i+1}_${j+1}`,f));});
 bilingual(c.key+"_hypothesis",c.hypothesis);bilingual(c.key+"_mismatch",c.mismatch);
 put(c.key+"_status",`[GetHSMBARInvestigationStatus_${c.id}]`,`[GetHSMBARInvestigationStatus_${c.id}]`);
 selectors+=select(`GetHSMBARInvestigationStatus_${c.id}`,c.methods.map((_,i)=>[`has_country_flag = ${c.key}_${i+1}_running`,`${c.key}_${i+1}_remaining`]).concat([[`has_country_flag = HSM_BAR_case_${c.id}_investigated`,P+"row_accepted"],[`OR = { ${c.methods.map((_,i)=>`has_country_flag = ${c.key}_${i+1}_reported`).join(" ")} }`,P+"row_limited"],[`has_country_flag = ${c.key}_matched`,P+"row_ready"]]),P+"row_pending");
 c.methods.forEach((m,i)=>{
  const k=`${c.key}_${i+1}`, running=k+"_running";
  bilingual(k+"_title",m.title);bilingual(k+"_brief",m.brief);bilingual(k+"_report",m.report);
  put(k+"_price",`${m.cost} political power / ${m.days} days`,`${m.cost} политвласти / ${m.days} дн.`);
  put(k+"_remaining",`FIELDWORK / [?days_mission_timeout@${k}_mission|0] days remaining`,`ЭКСПЕДИЦИЯ / осталось [?days_mission_timeout@${k}_mission|0] дн.`);
  put(k+"_mission",`$${k}_title$`,`$${k}_title$`);
  triggers+=`${k}_can_start = { ${c.key}_live = yes ${c.key}_idle = yes has_country_flag = ${c.key}_matched NOT = { has_country_flag = ${k}_reported } NOT = { has_political_power < ${m.cost} } }
`;
  effects+=`${k}_start = { if = { limit = { ${k}_can_start = yes }
 add_political_power = -${m.cost} set_country_flag = ${P}initialized set_country_flag = ${c.key}_running
 clr_country_flag = ${running} set_country_flag = ${running} clr_country_flag = ${c.key}_cancelled
 activate_mission = ${k}_mission
 } }
${k}_cancel = { if = { limit = { has_country_flag = ${running} }
 remove_mission = ${k}_mission clr_country_flag = ${running} clr_country_flag = ${c.key}_running set_country_flag = ${c.key}_cancelled
 } }
`;
  missions+=`${k}_mission = { allowed = { original_tag = BAR } visible = { always = no } activation = { always = no } available = { always = no }
 days_mission_timeout = ${m.days} is_good = no
 cancel_trigger = { ${c.key}_live = no }
 cancel_effect = { hidden_effect = { ${k}_cancel = yes } }
 timeout_effect = { hidden_effect = { if = { limit = { has_country_flag = ${running} NOT = { has_country_flag = { flag = ${running} days < ${m.days} } } }
 if = { limit = { ${c.key}_live = yes }
 clr_country_flag = ${running} clr_country_flag = ${c.key}_running set_country_flag = ${k}_reported
 ${m.qualifies?script(prop(c.sourceBody,"remove_effect")):""}
 } else = { ${k}_cancel = yes }
 } } }
 }
`;
 });
}
triggers+=`${P}selected = { OR = { ${cases.map(c=>`AND = { ${chosen(c)} ${c.key}_can_open = yes }`).join(" ")} } }
${P}window = { ${P}actor = yes has_variable = ${P}open ${P}selected = yes }
${P}idle = { OR = { ${cases.map(c=>`AND = { ${chosen(c)} ${c.key}_idle = yes }`).join(" ")} } }
`;
effects+=`${P}teardown = { ${cases.map(c=>c.methods.map((_,i)=>`${c.key}_${i+1}_cancel = yes`).join("\n")).join("\n")}
 clear_variable = ${P}open clr_country_flag = ${P}initialized }
${P}pulse = { if = { limit = { ${P}actor = no } ${P}teardown = yes } }
${P}back = { clear_variable = ${P}open if = { limit = { HSM_BAR_service_gui_available = yes }
 set_variable = { HSM_BAR_service_gui_open = 1 } set_variable = { HSM_BAR_service_gui_region = 1 }
 set_variable = { HSM_BAR_service_gui_subject = ${P}case } HSM_BAR_service_gui_refresh = yes } }
`;
for(const [key,en,ru] of [
 ["title","S.C.P. | Investigation file","S.C.P. | Материалы расследования"],
 ["hypothesis_title","Working hypothesis","Рабочая гипотеза"],
 ["pending","No comparison note has been signed. Two enclosures remain attached to the initial statement.","Сопоставление не подписано. К первичному сообщению подшиты два приложения."],
 ["compare","Compare excerpts","Сопоставить"],["choose","Mark excerpt","Отметить фрагмент"],
 ["page_1","Evidence","Материалы"],["page_2","Expedition","Экспедиция"],["page_3","Returned reports","Отчёты"],
 ["none","No report has returned under this protocol.","По этому протоколу отчёт ещё не поступил."],
 ["existing","Earlier field findings are preserved in the archive. No new expedition report is reconstructed for them.","Прежние полевые материалы сохранены в архиве. Новый экспедиционный отчёт за них не составляется."],
 ["start","Dispatch expedition","Отправить экспедицию"],["cancel","Recall expedition","Отозвать экспедицию"],
 ["cancel_tip","Recall the selected case's field team. Spent political power is not refunded. Signed reports remain in the file.","Отозвать группу по выбранному делу. Потраченная политвласть не возвращается. Подписанные отчёты остаются в деле."],
 ["ready","Protocol awaits authorization.","Протокол ожидает утверждения."],
 ["locked","A signed comparison, current access and the protocol budget are required.","Требуются подписанное сопоставление, доступ к месту работ и средства на протокол."],
 ["cancelled","The assignment was recalled. No field result was accepted.","Группа отозвана. Полевой результат не принят."],
 ["accepted","The field record is available to the laboratory.","Полевой протокол передан в лабораторию."],
 ["limited","The report records a limitation, not a confirmed conclusion.","В отчёте установлено ограничение опыта, а не подтверждён вывод."],
 ["row_pending","Comparison required","Нужно сопоставление"],
 ["row_ready","Protocol ready","Протокол готов"],
 ["row_accepted","Field evidence recorded","Полевые материалы приняты"],
 ["row_limited","Inconclusive report received","Получен неполный отчёт"],
 ["back","Return to casework","Вернуться к делам"],["close","Close","Закрыть"],
 ["archive","Historical dossier","Архивное досье"]
])put(P+key,en,ru);
for(let i=1;i<=3;i++)put(P+"report_"+i,"Protocol "+i,"Протокол "+i);
selectors+=select("GetHSMBARInvestigationTitle",cases.map(c=>[chosen(c),`HSM_BAR_archive_${c.id}_title`]),P+"title");
selectors+=select("GetHSMBARInvestigationHypothesis",[
 ...cases.map(c=>[`${chosen(c)} check_variable = { ${P}feedback = 2 }`,c.key+"_mismatch"]),
 ...cases.map(c=>[`${chosen(c)} has_country_flag = ${c.key}_matched`,c.key+"_hypothesis"])
],P+"pending");
selectors+=select("GetHSMBARInvestigationStatus",[
 ...cases.flatMap(c=>c.methods.map((_,i)=>[`${chosen(c)} has_country_flag = ${c.key}_${i+1}_running`,`${c.key}_${i+1}_remaining`])),
 ...cases.map(c=>[`${chosen(c)} has_country_flag = HSM_BAR_case_${c.id}_investigated`,P+"accepted"]),
 ...cases.map(c=>[`${chosen(c)} has_country_flag = ${c.key}_cancelled`,P+"cancelled"]),
 ...cases.map(c=>[`${chosen(c)} OR = { ${c.methods.map((_,i)=>`has_country_flag = ${c.key}_${i+1}_reported`).join(" ")} }`,P+"limited"]),
 ...cases.map(c=>[`${chosen(c)} has_country_flag = ${c.key}_matched`,P+"ready"])
],P+"locked");
selectors+=select("GetHSMBARInvestigationReport",[
 ...cases.flatMap(c=>c.methods.map((_,i)=>[`${chosen(c)} check_variable = { ${P}report = ${i+1} } has_country_flag = ${c.key}_${i+1}_reported`,`${c.key}_${i+1}_report`])),
 ...cases.map(c=>[`${chosen(c)} has_country_flag = HSM_BAR_case_${c.id}_investigated`,P+"existing"])
],P+"none");
selectors+=select("GetHSMBARInvestigationReportResult",cases.flatMap(c=>c.methods.map((m,i)=>[`${chosen(c)} check_variable = { ${P}report = ${i+1} } has_country_flag = ${c.key}_${i+1}_reported`,P+(m.qualifies?"accepted":"limited")])),P+"none");
for(let d=1;d<=2;d++){
 selectors+=select("GetHSMBARInvestigationDoc"+d,cases.map(c=>[chosen(c),`${c.key}_doc_${d}`]),P+"none");
 for(let f=1;f<=3;f++)selectors+=select(`GetHSMBARInvestigationFragment${d}${f}`,cases.map(c=>[chosen(c),`${c.key}_fragment_${d}_${f}`]),P+"none");
}
for(let i=1;i<=3;i++)for(const kind of ["title","brief","price"])selectors+=select(`GetHSMBARInvestigationMethod${i}${kind}`,cases.map(c=>[chosen(c),`${c.key}_${i}_${kind}`]),P+"none");
clicks+=`${P}close_click = { clear_variable = ${P}open }
${P}back_click = { ${P}back = yes }
${P}compare_click = { ${cases.map(c=>`if = { limit = { ${chosen(c)} } ${c.key}_compare = yes }`).join("\n")} }
${P}start_click = { if = { limit = { ${P}window = yes check_variable = { ${P}page = 2 } }
 ${cases.flatMap(c=>c.methods.map((_,i)=>`if = { limit = { ${chosen(c)} check_variable = { ${P}method = ${i+1} } } ${c.key}_${i+1}_start = yes }`)).join("\n")} } }
${P}cancel_click = { if = { limit = { ${P}window = yes }
 ${cases.map(c=>`if = { limit = { ${chosen(c)} } ${c.methods.map((_,i)=>`${c.key}_${i+1}_cancel = yes`).join(" ")} }`).join("\n")} } }
${P}archive_click = { if = { limit = { ${P}window = yes }
 clear_variable = ${P}open set_variable = { HSM_BAR_archive_open = 1 } set_variable = { HSM_BAR_archive_region = 1 }
 set_variable = { HSM_BAR_archive_case = ${P}case } HSM_BAR_archive_refresh = yes } }
`;
gates+=`${P}start_click_enabled = { OR = { ${cases.flatMap(c=>c.methods.map((_,i)=>`AND = { ${chosen(c)} check_variable = { ${P}method = ${i+1} } ${c.key}_${i+1}_can_start = yes }`)).join(" ")} } }
${P}cancel_click_enabled = { OR = { ${cases.map(c=>`AND = { ${chosen(c)} has_country_flag = ${c.key}_running }`).join(" ")} } }
${P}compare_click_enabled = { OR = { ${cases.map(c=>c.key+"_can_compare = yes").join(" ")} } }
`;
for(let i=1;i<=3;i++){
 clicks+=`${P}page_${i}_click = { if = { limit = { ${P}window = yes } set_variable = { ${P}page = ${i} } } }
${P}method_${i}_click = { if = { limit = { ${P}window = yes ${P}idle = yes check_variable = { ${P}page = 2 } } set_variable = { ${P}method = ${i} } ${[1,2,3].map(j=>`set_variable = { ${P}frame_method${j} = ${i===j?2:1} }`).join(" ")} } }
${P}report_${i}_click = { if = { limit = { ${P}window = yes check_variable = { ${P}page = 3 } } set_variable = { ${P}report = ${i} } } }
`;
 gates+=`${P}page_${i}_body_visible = { check_variable = { ${P}page = ${i} } }
${P}method_${i}_click_enabled = { ${P}idle = yes }
`;
 for(const v of ["a","b"]){
  clicks+=`${P}clue_${v}${i}_click = { if = { limit = { ${P}window = yes check_variable = { ${P}page = 1 } } set_variable = { ${P}${v} = ${i} } clear_variable = ${P}feedback ${[1,2,3].map(j=>`set_variable = { ${P}frame_${v}${j} = ${i===j?2:1} }`).join(" ")} } }
`;
  properties+=`${P}clue_${v}${i} = { frame = ${P}frame_${v}${i} }\n`;
 }
 properties+=`${P}method_${i} = { frame = ${P}frame_method${i} }
${P}page_${i} = { image = "[GetHSMBARInvestigationPage${i}Skin]" }
${P}report_${i} = { image = "[GetHSMBARInvestigationReport${i}Skin]" }
`;
 for(const [v,sprite] of [["page","edition"],["report","tab"]])selectors+=select(`GetHSMBARInvestigation${v[0].toUpperCase()+v.slice(1)}${i}Skin`,[[`check_variable = { ${P}${v} = ${i} }`,`GFX_HSM_BAR_archive_${sprite}_selected`]],`GFX_HSM_BAR_archive_${sprite}`);
}
const field=(name,text,x,y,w,h,font="HSM_BAR_archive_ink")=>`instantTextboxType = { name = "${P}${name}" position = { x = ${x} y = ${y} } font = "${font}" text = "${text}" maxWidth = ${w} maxHeight = ${h} format = left alwaystransparent = yes }`;
const button=(name,sprite,x,y,text=null,tip=text)=>`buttonType = { name = "${P}${name}" position = { x = ${x} y = ${y} } quadTextureSprite = "${sprite}" ${text?`buttonText = "${text}" buttonFont = "HSM_BAR_archive_ink"`:""} ${tip?`pdx_tooltip = "${tip}"`:""} clicksound = click_ok }`;
const scroll=(name,text,x,y,w,h,font="HSM_BAR_archive_ink")=>`containerWindowType = { name = "${P}${name}_scroll" position = { x = ${x} y = ${y} } size = { width = ${w} height = ${h} } clipping = yes verticalScrollbar = "right_vertical_slider" autohide_scrollbars = yes scroll_wheel_factor = 35 ${field(name,text,0,0,w-18,1500,font)} }`;
let evidence="",methods="",reports="";
for(let d=1;d<=2;d++){
 const x=354+(d-1)*300;
 evidence+=field("doc_"+d,`[GetHSMBARInvestigationDoc${d}]`,x,212,278,54);
 for(let f=1;f<=3;f++){
  const y=278+(f-1)*116;
  evidence+=button(`clue_${d===1?"a":"b"}${f}`,"GFX_checkbox_small",x,y,null,P+"choose");
  evidence+=scroll(`fragment_${d}${f}`,`[GetHSMBARInvestigationFragment${d}${f}]`,x+28,y,264,108);
 }
}
for(let i=1;i<=3;i++){
 const y=212+(i-1)*134;
 methods+=button("method_"+i,"GFX_checkbox_small",354,y+4,null,`[GetHSMBARInvestigationMethod${i}title]`);
 methods+=field("method_title_"+i,`[GetHSMBARInvestigationMethod${i}title]`,382,y,558,38);
 methods+=scroll("method_brief_"+i,`[GetHSMBARInvestigationMethod${i}brief]`,382,y+40,562,66);
 methods+=field("method_price_"+i,`[GetHSMBARInvestigationMethod${i}price]`,382,y+108,558,20);
 reports+=button("report_"+i,"GFX_HSM_BAR_archive_tab",354+(i-1)*196,212,P+"report_"+i);
}
methods+=button("start","GFX_HSM_BAR_archive_edition",534,634,P+"start")+button("cancel","GFX_HSM_BAR_archive_edition",744,634,P+"cancel",P+"cancel_tip");
reports+=scroll("report_text","[GetHSMBARInvestigationReport]",354,266,594,330)+field("report_result","[GetHSMBARInvestigationReportResult]",354,610,582,52);
out("interface/HSM_BAR_investigation.gui",`guiTypes = {
 containerWindowType = { name = "${P}window" position = { x = 0 y = 0 } size = { width = 1000 height = 700 } orientation = center origo = center moveable = yes click_to_front = yes clipping = no
 background = { name = "${P}background" quadTextureSprite = "GFX_HSM_BAR_archive_folder" }
 buttonType = { name = "${P}input_floor" position = { x = 0 y = 0 } size = { x = 1000 y = 700 } quadTextureSprite = "GFX_HSM_BAR_archive_folder" alwaystransparent = no }
 buttonType = { name = "${P}input_shield" position = { x = 0 y = 0 } size = { x = 1000 y = 700 } quadTextureSprite = "GFX_HSM_BAR_archive_folder" alwaystransparent = no }
 ${field("title",P+"title",24,20,890,30,"hoi_24header")}
 ${field("status","[GetHSMBARInvestigationStatus]",24,64,898,32,"hoi_16mbs")}
 ${button("close","GFX_HSM_BAR_archive_close",944,20,null,P+"close")}
 ${field("hypothesis_title",P+"hypothesis_title",30,132,250,30,"hoi_16mbs")}
 ${scroll("hypothesis","[GetHSMBARInvestigationHypothesis]",30,176,264,282,"hoi_16mbs")}
 ${button("compare","GFX_HSM_BAR_archive_index",24,484,P+"compare")}
 ${button("archive","GFX_HSM_BAR_archive_index",24,548,P+"archive")}
 ${button("back","GFX_HSM_BAR_archive_back",24,634,null,P+"back")}
 ${field("case_title","[GetHSMBARInvestigationTitle]",354,122,578,40,"HSM_BAR_archive_heading")}
 ${[1,2,3].map(i=>button("page_"+i,"GFX_HSM_BAR_archive_edition",354+(i-1)*196,170,P+"page_"+i)).join("\n")}
 ${[evidence,methods,reports].map((body,i)=>`containerWindowType = { name = "${P}page_${i+1}_body" position = { x = 0 y = 0 } size = { width = 1000 height = 700 } clipping = no ${body} }`).join("\n")}
 } }
`);
out("common/scripted_guis/HSM_BAR_investigation.txt",`scripted_gui = { ${P}window = { context_type = player_context window_name = "${P}window" visible = { ${P}window = yes } properties = { ${properties} } triggers = { ${gates} } effects = { ${clicks} } } }`);
out("common/scripted_triggers/HSM_BAR_investigation.txt",triggers);
out("common/scripted_effects/HSM_BAR_investigation.txt",effects);
out("common/decisions/HSM_BAR_investigation.txt",`${P}timers = { ${missions} }`);
out("common/decisions/categories/HSM_BAR_investigation.txt",`${P}timers = { allowed = { original_tag = BAR } visible = { always = no } }`);
out("common/scripted_localisation/HSM_BAR_investigation.txt",selectors);
for(const [short,long] of [["en","english"],["ru","russian"]])out(`localisation/${long}/HSM_BAR_investigation_l_${long}.yml`,"\uFEFFl_"+long+":\n"+Object.entries(loc[short]).map(([k,v])=>` ${k}:0 "${v.replace(/\\/g,"\\\\").replace(/\n/g,"\\n").replace(/"/g,'\\"')}"`).join("\n"));
function build(check=false){for(const [file,text] of Object.entries(outputs)){const target=path.join(mod,file);if(check)assert.equal(fs.readFileSync(target,"utf8").replace(/\r\n/g,"\n"),text,"Stale "+file);else{fs.mkdirSync(path.dirname(target),{recursive:true});fs.writeFileSync(target,text,"utf8");}}console.log(`${check?"Verified":"Built"} seven investigations, 42 evidence excerpts, 21 protocols; ${Object.keys(outputs).length} files.`);}
module.exports={cases,outputs,build,read,parse,prop,root,mod,P};
if(require.main===module)build(process.argv.includes("--check"));
