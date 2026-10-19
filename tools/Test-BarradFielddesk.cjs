"use strict";

// Source-driven fixtures and installed-engine contracts, not an HOI4 runtime.
// Run: node tools/Test-BarradFielddesk.cjs
const fs = require("node:fs");
const path = require("node:path");
const assert = require("node:assert/strict");
const native = require("./Test-BarradCases.cjs");
const skin = require("./Test-BarradArchiveSkin.cjs");
const { parse, prop, dictionary, read, mod } = native;
const game = process.env.HOI4_PATH || "C:/shit/Steam/steamapps/common/Hearts of Iron IV";
const eaw = process.env.EAW_PATH || "C:/shit/Steam/steamapps/workshop/content/394360/1826643372";
const triggers = { ...native.triggers, ...dictionary(read("common/scripted_triggers/HSM_BAR_fielddesk.txt")) };
const effects = { ...native.effects, ...dictionary(read("common/scripted_effects/HSM_BAR_fielddesk.txt")) };
const events = Object.fromEntries(read("events/HSM_BAR_fielddesk.txt").filter(n => n.key === "country_event").map(n => [prop(n.value, "id"), n.value]));
const missions = dictionary(prop(read("common/decisions/HSM_BAR_fielddesk.txt"), "HSM_BAR_fielddesk_missions"));
const ops = [{id:"recon",kind:1,pp:20,days:14,fact:1}, {id:"archive",kind:2,pp:30,days:21,fact:2}, {id:"relic",kind:3,pp:60,days:30,fact:3}, {id:"remains",kind:4,pp:60,days:21,fact:2}];
const prefix = "HSM_BAR_fielddesk_";
const flag = (w, ...names) => names.forEach(n => w.countries.BAR.flags.add("HSM_BAR_" + n));
const has = (w, n) => w.countries.BAR.flags.has(prefix + n);
const vars = w => w.countries.BAR.vars;
const walk = nodes => nodes.flatMap(n => [n, ...(Array.isArray(n.value) ? walk(n.value) : [])]);
function world(dlcs = []) {
    const w = native.world();
    w.day = 0; w.calls = []; w.dlc = new Set(dlcs); w.serviceRefreshes = 0;
    for (const c of Object.values(w.countries)) Object.assign(c, {ai:false, civilWar:false, dates:{}, arrays:{}, missions:new Map(), factories:8, modifierUse:0});
    w.global = {vars:w.vars, flags:w.flags, arrays:{HSM_BAR_case_crowns:w.crowns}};
    flag(w, "region_griffonia_open", "case_grover_rumor");
    w.flags.add("HSM_BAR_case_grover_bones_confirmed"); w.vars.HSM_BAR_case_grover_site = "398";
    vars(w).HSM_BAR_service_gui_region = 3; vars(w)[prefix + "open"] = 1;
    w.from = null;
    return w;
}
function value(v, w, stack) {
    if (typeof v === "number" || /^-?\d+(?:\.\d+)?$/.test(v)) return Number(v);
    if (v.startsWith("var:")) return value(v.slice(4), w, stack);
    const s = stack[0];
    if (v === "ROOT") return w.root.id;
    if (v === "FROM") return w.from?.id;
    if (v === "THIS") return s.id;
    if (/^PREV(?:\.PREV)*$/.test(v)) return stack[v.split(".").length]?.id;
    const match = v.match(/^(global|ROOT|FROM|BAR|YAL|CRY|DED|AAA)\.(.+)$/);
    if (match) return value(match[2], w, [scope(match[1], w, stack)]);
    if (v.includes("^")) {
        const [key, index] = v.split("^"); const list = s.arrays[key] || [];
        return index === "num" ? list.length : list[value(index, w, stack)];
    }
    return s.vars[v] ?? (w.countries[v] || w.states[v] ? v : 0);
}
function scope(key, w, stack) {
    if (key === "ROOT") return w.root;
    if (key === "FROM") return w.from;
    if (key === "THIS") return stack[0];
    if (key === "global") return w.global;
    if (/^PREV(?:\.PREV)*$/.test(key)) return stack[key.split(".").length];
    if (key.startsWith("var:")) { const id = value(key, w, stack); return w.countries[id] || w.states[id]; }
    return w.countries[key] || w.states[key];
}
function compare(a, op, b) {
    switch (op) { case "=": return a === b; case ">": return a > b; case "<": return a < b; case ">=": return a >= b; case "<=": return a <= b; default: throw Error("Unknown comparison " + op); }
}
function checkVariableSyntax(nodes) {
    assert(Array.isArray(nodes) && nodes.length === 1, "Expected one short-form check_variable comparison");
    const n = nodes[0];
    assert(["=", "<", ">"].includes(n.op), "Unsupported short-form check_variable operator: " + n.op);
    assert.equal(typeof n.value, "string", "check_variable requires a number or variable");
}
function test(nodes, w, stack = [w.root]) {
    assert(Array.isArray(nodes), "Missing trigger block");
    return nodes.every(n => {
        const {key:k, op, value:v} = n, s = stack[0];
        if (k === "AND") return test(v,w,stack);
        if (k === "OR") return v.some(x => test([x],w,stack));
        if (k === "NOT") return !v.some(x => test([x],w,stack));
        if (k === "always") return v === "yes";
        if (k === "has_country_flag") return Array.isArray(v) ? s.flags.has(prop(v,"flag")) && v.filter(x=>x.key!=="flag").every(x=>compare(w.day-(s.dates[prop(v,"flag")]??0),x.op,Number(x.value))) : s.flags.has(v);
        if (k === "has_global_flag") return w.flags.has(v);
        if (k === "has_variable") return Object.hasOwn(s.vars,v);
        if (k === "check_variable") { checkVariableSyntax(v); return v.every(x=>compare(value(x.key,w,stack),x.op,value(x.value,w,stack))); }
        if (k === "tag") return s.id === scope(v,w,stack)?.id;
        if (k === "original_tag") return s.originalTag === v;
        if (["exists","has_capitulated","is_ai","has_civil_war"].includes(k)) return !!s[{exists:"exists",has_capitulated:"capitulated",is_ai:"ai",has_civil_war:"civilWar"}[k]] === (v === "yes");
        if (k === "has_political_power") return compare(s.pp,op,Number(v));
        if (k === "num_of_civilian_factories_available_for_projects") return compare(s.factories-s.modifierUse,op,Number(v));
        if (k === "controls_state") return w.states[v]?.controller === s.id;
        if (k === "is_controlled_by") return s.controller === scope(v,w,stack)?.id;
        if (k === "is_on_continent") return s.continent === v;
        if (k === "has_country_leader") return s.leader === prop(v,"character");
        if (k === "is_in_array") return (s.arrays[prop(v,"array")] || []).includes(value(prop(v,"value"),w,stack));
        if (k === "any_country") return Object.values(w.countries).some(c=>c.exists && test(v,w,[c,...stack]));
        if (k === "any_of_scopes") {
            assert.equal(prop(v,"array"),"global.HSM_BAR_case_crowns");
            return w.crowns.some(c=>test(v.filter(x=>x.key!=="array"),w,[c,...stack]));
        }
        if (triggers[k]) return test(triggers[k],w,stack) === (v === "yes");
        const target = scope(k,w,stack);
        if (target) return test(v,w,[target,...stack]);
        if (k.startsWith("var:")) return false;
        throw Error("Unsupported trigger " + k);
    });
}
function fire(id, w, target, sender = w.root, deliver = false) {
    if (w.eventQueue && !deliver) { w.eventQueue.push({id,target:target.id,sender:sender?.id}); return; }
    w.calls.push({id,root:target.id,from:sender?.id});
    if (!events[id]) return;
    const previous = {root:w.root, from:w.from};
    w.root = target; w.from = sender;
    run(prop(events[id],"immediate"),w,[target]);
    Object.assign(w,previous);
}
// An adversarial delivery model, not a claim about the engine's scheduler.
function drainEvents(w, reverse = false) {
    let deliveries = 0;
    while (w.eventQueue.length) {
        assert(deliveries++ < 200, "Unbounded event relay");
        const next = reverse ? w.eventQueue.pop() : w.eventQueue.shift();
        fire(next.id,w,w.countries[next.target],w.countries[next.sender],true);
    }
}
function run(nodes, w, stack = [w.root]) {
    for (let i=0;i<nodes.length;i++) {
        const {key:k, value:v} = nodes[i], s = stack[0];
        if (k === "if") {
            let taken = false;
            do {
                const branch = nodes[i];
                if (!taken && (branch.key === "else" || test(prop(branch.value,"limit"),w,stack))) { run(branch.value.filter(x=>x.key!=="limit"),w,stack); taken=true; }
                if (!["else_if","else"].includes(nodes[i+1]?.key)) break;
                i++;
            } while (true);
        } else if (["set_country_flag","clr_country_flag","set_global_flag"].includes(k)) {
            const target = k === "set_global_flag" ? w.global : s;
            if (k === "clr_country_flag") {target.flags.delete(v);delete s.dates[v];}
            else {target.flags.add(v); if(target.dates) target.dates[v]=w.day;}
        } else if (["set_variable","set_temp_variable","add_to_variable","add_to_temp_variable","subtract_from_variable"].includes(k)) {
            assert.equal(v.length,1);
            let target = s, name = v[0].key;
            if(name.startsWith("global.")) {target=w.global;name=name.slice(7);}
            const amount=value(v[0].value,w,stack);
            target.vars[name] = k.startsWith("set_") ? amount : (target.vars[name]||0) + (k.startsWith("subtract") ? -amount : amount);
        } else if (k === "clear_variable") delete s.vars[v];
        else if (k === "clear_array") s.arrays[v] = [];
        else if (k === "add_to_array") {assert.equal(v.length,1); (s.arrays[v[0].key] ||= []).push(value(v[0].value,w,stack));}
        else if (k === "add_political_power") s.pp += value(v,w,stack);
        else if (k === "activate_mission") {assert(!s.missions.has(v),"Duplicate native mission");s.missions.set(v,w.day+Number(prop(missions[v],"days_mission_timeout")));}
        else if (k === "remove_mission") s.missions.delete(v);
        else if (k === "add_dynamic_modifier") {s.modifiers.add(prop(v,"modifier"));s.modifierUse=s.vars[prefix+"factories"]||0;}
        else if (k === "remove_dynamic_modifier") {s.modifiers.delete(prop(v,"modifier"));s.modifierUse=0;}
        else if (k === "force_update_dynamic_modifier") {s.modifierUse=s.modifiers.has(prefix+"assignment") ? s.vars[prefix+"factories"]||0 : 0;}
        else if (k === "country_event") fire(prop(v,"id"),w,s);
        else if (k === "every_country") {for(const c of Object.values(w.countries)) if(c.exists && test(prop(v,"limit"),w,[c,...stack])) run(v.filter(x=>x.key!=="limit"),w,[c,...stack]);}
        else if (k === "for_each_scope_loop") {assert.equal(prop(v,"array"),"global.HSM_BAR_case_crowns"); for(const c of w.crowns) run(v.filter(x=>x.key!=="array"),w,[c,...stack]);}
        else if (k === "capital_scope") {const capital=Object.values(w.states).find(x=>x.owner===s.id);assert(capital);run(v,w,[capital,...stack]);}
        else if (k === "hidden_effect") run(v,w,stack);
        else if (k === "custom_effect_tooltip") continue;
        else if (k === "add_opinion_modifier") s.opinions = (s.opinions||0)+1;
        else if (k === "HSM_BAR_service_gui_refresh") w.serviceRefreshes++;
        else if (effects[k]) {
            if (/^HSM_BAR_operation_\w+_complete$/.test(k)) {assert.equal(w.root.id,"BAR"); assert(w.from && w.from.id!=="BAR");w.calls.push({id:k,root:w.root.id,from:w.from.id});}
            run(effects[k],w,stack);
        } else {const target=scope(k,w,stack);assert(target,"Unsupported effect "+k);run(v,w,[target,...stack]);}
    }
}
const effect = (name,w) => {assert(effects[prefix+name]);run(effects[prefix+name],w);};
function select(w,target="YAL") {vars(w)[prefix+"selected"]=target;effect("refresh_selection",w);}
function finish(w,o) {w.day += o.days;run(prop(missions[prefix+o.id+"_mission"],"timeout_effect"),w);}
function prepare(w,o) {
    if(o.kind>=2) w.countries.YAL.flags.add("HSM_BAR_case_surveyed");
    if(o.id==="remains") flag(w,"forensic_mandate","project_forensics_done","case_grover_investigated");
    if(o.id==="relic") {
        const c=w.countries.AAA;w.crowns.push(c);
        for(const n of ["exists","rumor","known","investigated","museum"]) c.flags.add("HSM_BAR_case_crown_"+n);
        c.vars.HSM_BAR_case_crown_site="398";flag(w,"project_containment_done");
    }
    select(w);
}
if(process.argv.includes("--preview-json")) {
    const window=prop(read("interface/HSM_BAR_fielddesk.gui"),"guiTypes")[0].value;
    const script=prop(read("common/scripted_guis/HSM_BAR_fielddesk.txt"),"scripted_gui")[0].value;
    const getters=Object.fromEntries(read("common/scripted_localisation/HSM_BAR_fielddesk.txt").map(n=>[prop(n.value,"name"),n.value.filter(x=>x.key==="text").map(x=>x.value)]));
    const snapshots=[];
    for(const language of ["english","russian"]) for(const state of ["ready","running","empty"]) {
        const w=world();effect("refresh",w);select(w);
        if(state==="running") effect("recon_request",w);
        if(state==="empty") {vars(w).HSM_BAR_service_gui_region=5;delete vars(w)[prefix+"selected"];effect("refresh",w);}
        const locale=Object.fromEntries([...fs.readFileSync(path.join(mod,`localisation/${language}/HSM_BAR_fielddesk_l_${language}.yml`),"utf8").matchAll(/^ (\w+):0 "([^"\r\n]*)"\r?$/gm)].map(m=>[m[1],m[2]]));
        const names=fs.readFileSync(path.join(eaw,`localisation/${language}/country_YAL_l_${language}.yml`),"utf8");
        const targetName=names.match(/^ YAL_neutrality:0 "([^"]+)"/m)[1];
        function expand(text) {
            if(locale[text]) return expand(locale[text]);
            return text.replace(/\[(Get\w+)\]/g,(_,getter)=>{const entry=getters[getter].find(b=>test(prop(b,"trigger")||[],w));assert(entry,getter);return expand(prop(entry,"localization_key"));})
                .replace(/\$(\w+)\$/g,(_,key)=>expand(key))
                .replace(/\[\?([^\]]+)\.GetName\]/g,()=>targetName)
                .replace(/\[\?days_mission_timeout@([^|]+)\|0\]/g,(_,mission)=>String((w.countries.BAR.missions.get(mission)||w.day)-w.day))
                .replace(/\[\?([^|\]]+)(?:\|0)?\]/g,(_,name)=>String(value(name,w,[w.root])))
                .replace(/\\n/g,"\n");
        }
        const items=[];
        for(const n of window.filter(n=>["buttonType","instantTextboxType"].includes(n.key))) {
            const b=n.value,name=prop(b,"name");
            if(!test(prop(prop(script,"triggers"),name+"_visible")||[],w)) continue;
            const p=prop(b,"position");
            const image=prop(prop(script,"properties"),name);
            items.push({kind:n.key,name,x:Number(prop(p,"x")),y:Number(prop(p,"y")),width:Number(prop(b,"maxWidth")),height:Number(prop(b,"maxHeight")),font:prop(b,"font")||prop(b,"buttonFont"),text:expand(prop(b,"text")||prop(b,"buttonText")||""),sprite:image?expand(prop(image,"image")):prop(b,"quadTextureSprite"),disabled:!test(prop(prop(script,"triggers"),name+"_click_enabled")||[],w)});
        }
        snapshots.push({language,state,items});
    }
    console.log(JSON.stringify(snapshots));process.exit(0);
}
let passed=0, failed=0;
function scenario(name,fn) {try {fn();passed++;console.log("PASS: "+name);} catch(e) {failed++;console.error("FAIL: "+name+"\n"+e.stack);}}

scenario("native check_variable grammar accepts array lengths but rejects compound shorthand operators",()=>{
    const docs=fs.readFileSync(path.join(game,"documentation/triggers_documentation.md"),"utf8");
    const contract=docs.split("## check_variable")[1].split("\n## ")[0];
    assert.match(contract,/check_variable = \{ varname < 42 \}/);
    assert.match(contract,/greater_than_or_equals/);
    const ces=parse(fs.readFileSync(path.join(eaw,"common/scripted_effects/EAW_CES_effect.txt"),"utf8"));
    assert(walk(ces).some(n=>n.key==="check_variable" && n.value.some(x=>x.op==="<" && x.value==="CES_quest_array^num")),"Installed EaW compares against array^num directly");
    for(const op of [">=","<="]) {
        const invalid=prop(parse(`check_variable = { offset ${op} targets^num }`),"check_variable");
        assert.throws(()=>checkVariableSyntax(invalid),/Unsupported short-form/);
    }
    checkVariableSyntax(prop(parse("check_variable = { offset < targets^num }"),"check_variable"));
    // Scan even branches the fixtures never execute: the engine parses them at load.
    for(const n of walk(read("common/scripted_effects/HSM_BAR_fielddesk.txt"))) if(n.key==="check_variable") checkVariableSyntax(n.value);
});
scenario("pagination handles empty, exact-boundary, overshot and partial pages without stale rows",()=>{
    for(const count of [0,1,4,5,8,9]) for(const offset of [undefined,0,4,8,count,count+4]) {
        const w=world(),targets=Array.from({length:count},(_,i)=>"target_"+i);
        w.countries.BAR.arrays[prefix+"targets"]=targets;
        if(offset!==undefined) vars(w)[prefix+"offset"]=offset;
        for(let row=1;row<=4;row++) vars(w)[prefix+"row_"+row]="stale";
        effect("rows",w);
        const expected=offset===undefined||offset>=count?0:offset;
        assert.equal(vars(w)[prefix+"offset"],expected,`count=${count}, offset=${offset}`);
        assert.equal(vars(w)[prefix+"next_offset"],expected+4);
        for(let row=1;row<=4;row++) {
            assert.equal(vars(w)[prefix+"row_"+row],targets[expected+row-1]);
            assert.equal(Object.hasOwn(vars(w),prefix+"row_"+row),expected+row-1<count,"Unused rows must be cleared");
        }
    }
});

scenario("installed native recipient relay, variable targets, mission removal and remaining-day contracts",()=>{
    const doc=fs.readFileSync(path.join(game,"documentation/effects_documentation.md"),"utf8");
    for(const name of ["country_event","activate_mission","remove_mission","set_variable","add_to_array","clear_array","add_to_temp_variable","force_update_dynamic_modifier"]) assert(doc.includes("## "+name));
    assert.match(doc,/Removes mission without running complete or timeout effects/);
    assert.match(doc,/Activates mission, ignoring its normal trigger conditions/);
    const cea=parse(fs.readFileSync(path.join(eaw,"events/Celestial_State.txt"),"utf8"));
    const relay=cea.find(n=>n.key==="state_event" && prop(n.value,"id")==="daring_adventure.100");
    assert.equal(prop(prop(prop(relay.value,"option"),"FROM"),"country_event"),"daring_adventure.101");
    const receiver=cea.find(n=>n.key==="country_event" && prop(n.value,"id")==="daring_adventure.103");
    assert(walk(receiver.value).some(n=>n.value==="FROM.CES_quest_array^num"));
    const changeling=parse(fs.readFileSync(path.join(eaw,"events/ChangelingHarmony.txt"),"utf8"));
    const countryRelay=changeling.find(n=>n.key==="country_event" && prop(n.value,"id")==="thoraxian.4");
    const countryReceiver=changeling.find(n=>n.key==="country_event" && prop(n.value,"id")==="thoraxian.5");
    assert(walk(countryRelay.value).some(n=>n.key==="FROM" && walk(n.value).some(x=>x.key==="id"&&x.value==="thoraxian.5")));
    assert(walk(countryReceiver.value).some(n=>n.key==="give_military_access"&&n.value==="FROM"));
    const varsDoc=fs.readFileSync(path.join(game,"documentation/dynamic_variables_documentation.md"),"utf8");
    assert.match(varsDoc,/days_mission_timeout@GER_mefo_bills_mission/);
    assert.match(fs.readFileSync(path.join(eaw,"common/scripted_effects/operation_strat_effects.txt"),"utf8"),/tag = var:generic_operation_target/);
    for(const ev of Object.values(events)) {assert.equal(prop(ev,"hidden"),"yes");assert.equal(prop(ev,"is_triggered_only"),"yes");for(const call of walk(ev).filter(n=>n.key==="country_event")) assert.deepEqual(call.value.map(n=>n.key),["id"]);}
});
scenario("native operations retain AI callbacks; human visibility is the sole operation change",()=>{
    const operations=dictionary(read("common/operations/HSM_BAR_operations.txt"));
    for(const o of ops) {
        const op=operations["HSM_BAR_operations_"+o.id];
        assert.equal(prop(prop(op,"visible"),"is_ai"),"yes");
        assert(!walk(prop(op,"available")).some(n=>n.key==="is_ai"));
        assert(!walk(prop(op,"outcome_execute")).some(n=>n.key==="is_ai"));
        assert(walk(prop(op,"outcome_execute")).some(n=>n.key==="HSM_BAR_operation_"+o.id+"_complete"));
    }
    const deskFiles=["common/scripted_triggers","common/scripted_effects","common/decisions","common/scripted_guis","events"];
    for(const dir of deskFiles) assert(!walk(read(dir+"/HSM_BAR_fielddesk.txt")).some(n=>["has_dlc","has_intelligence_agency","HSM_BAR_operations_actor"].includes(n.key)),dir);
    for(const m of Object.values(missions)) {assert.equal(prop(prop(m,"visible"),"always"),"no");assert.equal(prop(prop(m,"activation"),"always"),"no");assert.equal(prop(prop(m,"available"),"always"),"no");}
});
scenario("integrated initialized guards run daily outside active and teardown after MTC before flags",()=>{
    const onActions=prop(read("common/on_actions/HSM_BAR_core_on_actions.txt"),"on_actions");
    const daily=prop(prop(onActions,"on_daily_BAR"),"effect");
    const dissolve=prop(read("common/scripted_effects/HSM_BAR_core_effects.txt"),"HSM_BAR_dissolve_institutions");
    function guardedCall(nodes,name) {
        assert.equal(walk(nodes).filter(n=>n.key===name).length,1,"Exactly one hook for "+name);
        const hooks=nodes.filter(n=>n.key==="if"&&prop(n.value,name)==="yes");
        assert.equal(hooks.length,1,"Hook must be directly in its lifecycle, not inside an active-route gate");
        assert.deepEqual(prop(hooks[0].value,"limit"),parse("has_country_flag = HSM_BAR_fielddesk_initialized"));
        return hooks[0];
    }
    const pulse=guardedCall(daily,prefix+"pulse"),teardown=guardedCall(dissolve,prefix+"teardown");
    const activeGate=daily.find(n=>n.key==="if"&&prop(prop(n.value,"limit")||[],"has_country_flag")==="HSM_BAR_active");
    assert(activeGate && daily.indexOf(pulse)<daily.indexOf(activeGate));
    const mtc=dissolve.findIndex(n=>n.key==="if"&&prop(n.value,"HSM_BAR_mtk_projects_teardown")==="yes");
    const firstRouteClear=dissolve.findIndex(n=>n.key==="clr_country_flag"&&["HSM_BAR_active","HSM_BAR_directorate","HSM_BAR_service_founded"].includes(n.value));
    assert(mtc>=0&&mtc<dissolve.indexOf(teardown)&&dissolve.indexOf(teardown)<firstRouteClear);
    assert.equal(prop(effects[prefix+"refresh"],"set_country_flag"),prefix+"initialized");
    assert(effects[prefix+"teardown"].some(n=>n.key==="clr_country_flag"&&n.value===prefix+"initialized"));
    const w=world();assert(!test(prop(pulse.value,"limit"),w));effect("refresh",w);select(w);effect("recon_request",w);effect("close",w);
    w.countries.BAR.flags.delete("HSM_BAR_active");assert(test(prop(pulse.value,"limit"),w));
    run([pulse],w);assert(!has(w,"running"));assert.equal(w.countries.BAR.pp,200);assert.equal(w.countries.BAR.modifierUse,0);
    run([teardown],w);assert(!has(w,"initialized"));assert(!test(prop(pulse.value,"limit"),w));
    run([teardown],w);assert.equal(w.countries.BAR.pp,200);
});
scenario("queued and reordered relay delivery preserves frozen targets, costs and single completion",()=>{
    for(const reverse of [false,true]) for(const o of ops) {
        const w=world();prepare(w,o);effect("refresh",w);w.eventQueue=[];
        effect(o.id+"_request",w);assert(!has(w,"running"));assert.equal(w.countries.BAR.pp,200);
        effect(o.id+"_request",w);assert.equal(w.eventQueue.length,1,"Pending lock allowed a duplicate dispatch");
        select(w,"CRY");vars(w).HSM_BAR_service_gui_region=2;effect("close",w);drainEvents(w,reverse);
        assert(has(w,"running"));assert.equal(vars(w)[prefix+"order_target"],"YAL");assert.equal(vars(w)[prefix+"order_region"],3);
        assert.equal(w.countries.BAR.pp,200-o.pp);assert.equal(w.countries.BAR.modifierUse,o.fact);
        w.day=o.days;effect(o.id+"_timeout",w);effect(o.id+"_timeout",w);drainEvents(w,reverse);
        assert(!has(w,"running"));assert.equal(w.countries.BAR.modifierUse,0);
        assert.deepEqual(w.calls.filter(c=>c.id==="HSM_BAR_operation_"+o.id+"_complete"),[{id:"HSM_BAR_operation_"+o.id+"_complete",root:"BAR",from:"YAL"}]);
    }
});
scenario("queued stale selection, lost recipient and teardown cannot grant an old order",()=>{
    for(const stage of ["recipient","receiver"]) for(const invalidate of [w=>w.countries.YAL.exists=false,w=>w.countries.YAL.capitulated=true,w=>w.states[398].controller="CRY",w=>w.countries.BAR.flags.delete("HSM_BAR_active"),w=>effect("teardown",w)]) {
        const w=world();effect("refresh",w);select(w);w.eventQueue=[];effect("recon_request",w);
        if(stage==="receiver") {const next=w.eventQueue.shift();fire(next.id,w,w.countries[next.target],w.countries[next.sender],true);}
        invalidate(w);drainEvents(w);effect("pulse",w);drainEvents(w);
        assert(!has(w,"running"));assert.equal(vars(w)[prefix+"request_kind"],undefined);assert.equal(w.countries.BAR.pp,200);
        assert(!w.calls.some(c=>c.id==="HSM_BAR_operation_recon_complete"));
    }
    const w=world();effect("refresh",w);w.eventQueue=[];select(w,"YAL");select(w,"CRY");drainEvents(w,true);
    assert(!has(w,"recon_available"),"Old selection response restored stale availability");
    select(w,"YAL");drainEvents(w);effect("recon_request",w);drainEvents(w);w.day=14;effect("recon_timeout",w);
    effect("teardown",w);drainEvents(w);assert.equal(w.countries.BAR.pp,200);assert(!has(w,"running"));
    assert(!w.calls.some(c=>c.id==="HSM_BAR_operation_recon_complete"));
});
scenario("only known regional leads are listed; local/Riverlands do not invent foreign work",()=>{
    const w=world();effect("refresh",w);
    assert.deepEqual(w.countries.BAR.arrays[prefix+"targets"],["YAL"]);
    assert.equal(vars(w)[prefix+"row_1"],"YAL");assert.equal(vars(w)[prefix+"row_2"],undefined);
    for(const region of [1,2,4,5,6]) {vars(w).HSM_BAR_service_gui_region=region;effect("refresh",w);assert.deepEqual(w.countries.BAR.arrays[prefix+"targets"],[]);}
    vars(w).HSM_BAR_service_gui_region=3;w.countries.BAR.flags.delete("HSM_BAR_case_grover_rumor");effect("refresh",w);assert.deepEqual(w.countries.BAR.arrays[prefix+"targets"],[]);
});
scenario("crown follows its physical continent and current controller, including vanished origin",()=>{
    const w=world(),c=w.countries.AAA;
    w.crowns.push(c);c.exists=false;
    for(const f of ["exists","rumor","museum"]) c.flags.add("HSM_BAR_case_crown_"+f);
    c.vars.HSM_BAR_case_crown_site="344";flag(w,"region_equus_open");
    vars(w).HSM_BAR_service_gui_region=2;effect("refresh",w);
    assert.deepEqual(w.countries.BAR.arrays[prefix+"targets"],["CRY"]);
    select(w,"CRY");assert(has(w,"recon_available"));
    w.states[344].controller="DED";effect("refresh",w);assert.deepEqual(w.countries.BAR.arrays[prefix+"targets"],["DED"]);assert(!has(w,"recon_available"));
    c.flags.add("HSM_BAR_case_crown_missing");effect("refresh",w);assert.deepEqual(w.countries.BAR.arrays[prefix+"targets"],[]);
});
for(const o of ops) scenario(o.id+": exact no-DLC/both-DLC and single-DLC parity, frozen target, one reward",()=>{
    const outcomes=[];
    for(const dlcs of [[],["La Resistance"],["Gotterdammerung"],["La Resistance","Gotterdammerung"]]) {
        const w=world(dlcs);prepare(w,o);assert(has(w,o.id+"_available"));
        effect(o.id+"_request",w);
        assert(has(w,"running"));assert.equal(w.countries.BAR.pp,200-o.pp);assert.equal(w.countries.BAR.modifierUse,o.fact);
        assert.equal(vars(w)[prefix+"order_target"],"YAL");
        effect(o.id+"_request",w);assert.equal(w.countries.BAR.pp,200-o.pp);
        select(w,"CRY");effect("close",w);assert.equal(w.serviceRefreshes,1);assert.equal(vars(w).HSM_BAR_service_gui_open,1);
        effect("pulse",w);assert(has(w,"running"));
        effect(o.id+"_timeout",w);assert(has(w,"running"),"Early callback consumed assignment");
        finish(w,o);assert(!has(w,"running"));assert.equal(w.countries.BAR.modifierUse,0);assert.equal(w.countries.BAR.missions.size,0);
        effect(o.id+"_timeout",w);fire("HSM_BAR_fielddesk.6",w,w.countries.BAR,w.countries.YAL);
        const calls=w.calls.filter(c=>c.id==="HSM_BAR_operation_"+o.id+"_complete");
        assert.deepEqual(calls,[{id:"HSM_BAR_operation_"+o.id+"_complete",root:"BAR",from:"YAL"}]);
        if(o.id==="recon") assert(w.countries.BAR.flags.has("HSM_BAR_case_grover_known"));
        if(o.id==="archive") assert(w.countries.BAR.flags.has("HSM_BAR_case_grover_investigated"));
        if(o.id==="relic") assert.equal(w.countries.AAA.vars.HSM_BAR_case_crown_site,"624");
        if(o.id==="remains") assert(w.flags.has("HSM_BAR_case_grover_bones_removed"));
        const pp=w.countries.BAR.pp;effect("teardown",w);assert.equal(w.countries.BAR.pp,pp,"Completed order refunded");
        outcomes.push({pp,flags:[...w.countries.BAR.flags].sort(),globals:[...w.flags].sort(),site:w.vars.HSM_BAR_case_grover_site,crown:w.countries.AAA.vars.HSM_BAR_case_crown_site});
    }
    outcomes.slice(1).forEach(x=>assert.deepEqual(x,outcomes[0]));
});
scenario("stale target, capitulation, territory loss and route death refund once with menu closed",()=>{
    for(const invalidate of [w=>w.countries.YAL.exists=false,w=>w.countries.YAL.capitulated=true,w=>w.states[398].controller="CRY",w=>w.countries.BAR.flags.delete("HSM_BAR_active"),w=>w.countries.BAR.flags.delete("HSM_BAR_directorate"),w=>w.countries.BAR.capitulated=true,w=>w.countries.BAR.civilWar=true,w=>w.countries.BAR.ai=true]) {
        const w=world();select(w);effect("recon_request",w);effect("close",w);invalidate(w);effect("pulse",w);
        assert(!has(w,"running"));assert.equal(w.countries.BAR.pp,200);assert.equal(w.countries.BAR.modifierUse,0);assert.equal(w.countries.BAR.missions.size,0);
        effect("teardown",w);effect("recon_timeout",w);assert.equal(w.countries.BAR.pp,200);
        assert(!w.calls.some(c=>c.id==="HSM_BAR_operation_recon_complete"));
    }
});
scenario("changed resources and control are rechecked after a cached button; no phantom refund",()=>{
    for(const invalidate of [w=>w.countries.BAR.pp=19.99,w=>w.countries.BAR.factories=0,w=>w.states[398].controller="CRY",w=>w.countries.BAR.flags.delete("HSM_BAR_foreign_mandate"),w=>w.countries.YAL.exists=false,w=>w.countries.YAL.capitulated=true]) {
        const w=world();select(w);assert(has(w,"recon_available"));invalidate(w);const pp=w.countries.BAR.pp;
        effect("recon_request",w);assert(!has(w,"running"));assert.equal(w.countries.BAR.pp,pp);effect("cancel",w);assert.equal(w.countries.BAR.pp,pp);assert.equal(w.countries.BAR.modifierUse,0);
    }
});
scenario("disappearing recipient cannot strand a pending request or charge the next target",()=>{
    const w=world();vars(w)[prefix+"request_kind"]=1;vars(w)[prefix+"request_target"]="YAL";vars(w)[prefix+"request_region"]=3;
    w.countries.YAL.exists=false;effect("pulse",w);
    assert.equal(vars(w)[prefix+"request_kind"],undefined);assert.equal(w.countries.BAR.pp,200);
    fire("HSM_BAR_fielddesk.11",w,w.countries.BAR,w.countries.YAL);assert(!has(w,"running"));
});
scenario("restart rejects early stale timeout and unrelated sender; lost valid predicates cancel on return",()=>{
    const w=world();select(w);effect("recon_request",w);w.day=13;effect("cancel",w);effect("recon_request",w);w.day=14;
    effect("recon_timeout",w);assert(has(w,"running"));
    fire("HSM_BAR_fielddesk.6",w,w.countries.BAR,w.countries.CRY);assert(has(w,"running"));
    w.day=27;w.countries.BAR.flags.delete("HSM_BAR_case_grover_rumor");effect("recon_timeout",w);
    assert(!has(w,"running"));assert.equal(w.countries.BAR.pp,200);
});
scenario("forensic mandate, real bones, resurrection and worn-crown exclusions remain authoritative",()=>{
    const w=world();prepare(w,ops[3]);assert(has(w,"remains_available"));
    w.countries.BAR.flags.delete("HSM_BAR_forensic_mandate");select(w);assert(!has(w,"remains_available"));
    flag(w,"forensic_mandate");w.flags.add("HSM_BAR_case_grover_returned");select(w);assert(!has(w,"remains_available"));
    w.flags.delete("HSM_BAR_case_grover_returned");w.countries.CRY.leader="YAL_emperor_grover_ii";select(w);assert(!has(w,"remains_available"));
    delete w.countries.CRY.leader;w.flags.delete("HSM_BAR_case_grover_bones_confirmed");select(w);assert(!has(w,"remains_available"));
    const crown=world();prepare(crown,ops[2]);crown.countries.AAA.flags.add("HSM_BAR_case_crown_leader");select(crown);assert(!has(crown,"relic_available"));
});
scenario("persistent order state survives a fixture snapshot; pagination clears stale rows",()=>{
    const w=world();select(w);effect("recon_request",w);w.day=7;effect("close",w);
    const loaded=structuredClone(w);assert.equal(vars(loaded)[prefix+"order_target"],"YAL");
    loaded.day=14;effect("recon_timeout",loaded);assert(!has(loaded,"running"));assert.equal(loaded.countries.BAR.pp,180);
    const list=world();
    for(let i=0;i<5;i++) {
        const id="T"+i,c=structuredClone(list.countries.CRY);c.id=id;c.originalTag=id;
        c.vars.HSM_BAR_case_crown_site=String(910+i);
        for(const f of ["exists","rumor","museum"]) c.flags.add("HSM_BAR_case_crown_"+f);
        list.countries[id]=c;list.crowns.push(c);list.states[910+i]={id:String(910+i),owner:id,controller:id,continent:"asia"};
    }
    effect("refresh",list);assert.equal(list.countries.BAR.arrays[prefix+"targets"].length,6);
    vars(list)[prefix+"offset"]=4;effect("rows",list);assert.equal(vars(list)[prefix+"row_1"],"T3");assert.equal(vars(list)[prefix+"row_2"],"T4");assert.equal(vars(list)[prefix+"row_3"],undefined);
    for(const c of list.crowns) c.flags.add("HSM_BAR_case_crown_missing");
    effect("refresh",list);assert.equal(vars(list)[prefix+"offset"],0);assert.equal(vars(list)[prefix+"row_1"],"YAL");assert.equal(vars(list)[prefix+"row_2"],undefined);
});

// Layout and localisation checks use the actual installed bitmap-font metrics.
const sg=prop(read("common/scripted_guis/HSM_BAR_fielddesk.txt"),"scripted_gui");
const gui=prop(read("interface/HSM_BAR_fielddesk.gui"),"guiTypes")[0].value;
const widgets=gui.filter(n=>["buttonType","instantTextboxType"].includes(n.key));
const texts=Object.fromEntries(read("common/scripted_localisation/HSM_BAR_fielddesk.txt").map(n=>[prop(n.value,"name"),n.value.filter(x=>x.key==="text").map(x=>prop(x.value,"localization_key"))]));
const locales=["english","russian"].map(lang=>{
    const source=fs.readFileSync(path.join(mod,`localisation/${lang}/HSM_BAR_fielddesk_l_${lang}.yml`),"utf8");
    assert(source.startsWith("\uFEFFl_"+lang+":"));
    return Object.fromEntries([...source.matchAll(/^ (\w+):0 "([^"\r\n]*)"\r?$/gm)].map(m=>[m[1],m[2]]));
});
scenario("EN/RU labels, all GUI callbacks, native assets, bounds and text wrapping",()=>{
    assert.deepEqual(Object.keys(locales[0]).sort(),Object.keys(locales[1]).sort());
    const {sprites,fonts}=skin.loadArchiveAssets();
    const handlers=prop(sg[0].value,"effects"), guards=prop(sg[0].value,"triggers");
    const dimensions=skin.spriteDimensions;
    assert.equal(prop(prop(gui,"size"),"width"),"1000");assert.equal(prop(prop(gui,"size"),"height"),"700");
    for(const n of widgets) {
        const b=n.value,name=prop(b,"name"),position=prop(b,"position"),x=Number(prop(position,"x")),y=Number(prop(position,"y"));
        const button=n.key==="buttonType";
        const size=button ? dimensions(sprites,prop(b,"quadTextureSprite")) : {w:Number(prop(b,"maxWidth")),h:Number(prop(b,"maxHeight"))};
        assert(x>=0&&y>=0&&x+size.w<=1000&&y+size.h<=700,name+": out of bounds");
        if(button&&!name.includes("input_")) assert(prop(handlers,name+"_click"),name+": missing handler");
        const literal=prop(b,"text")||prop(b,"buttonText");
        if(!literal) continue;
        const keys=literal.startsWith("[") ? texts[literal.slice(1,-1)] : [literal];assert(keys,literal);
        for(let lang=0;lang<2;lang++) {
            const font=skin.fontDefinition(fonts,prop(b,"font")||prop(b,"buttonFont"),["english","russian"][lang]);
            let lineHeight=0;const advances=new Map();
            for(const entry of prop(font,"fontfiles")) {
                const data=fs.readFileSync(skin.resolveAsset(entry.value+".fnt"),"utf8");
                lineHeight=Math.max(lineHeight,Number(data.match(/common lineHeight=(\d+)/)[1]));
                for(const m of data.matchAll(/^char id=(\d+)\s+.*?xadvance=(-?\d+)/gm)) if(!advances.has(Number(m[1]))) advances.set(Number(m[1]),Number(m[2]));
            }
            const width=text=>[...text].reduce((sum,c)=>{assert(advances.has(c.codePointAt(0)),"Missing glyph "+c);return sum+advances.get(c.codePointAt(0));},0);
            function expand(text) {return text.replace(/\$(\w+)\$/g,(_,k)=>expand(locales[lang][k])).replace(/\[\?[^\]]+\.GetName\]/g,lang?"Кристальная империя":"Crystal Empire").replace(/\[\?[^\]]+\]/g,"100");}
            for(const key of keys) {
                assert(locales[lang][key],"Missing "+key);const text=expand(locales[lang][key]);
                const maxWidth=size.w-(button?16:0);let lines=0;
                for(const paragraph of text.split("\\n")) {
                    let current="";lines++;
                    for(const word of paragraph.split(" ")) {assert(width(word)<=maxWidth,key+": word too wide");const next=current?current+" "+word:word;if(width(next)>maxWidth){lines++;current=word;}else current=next;}
                }
                assert(lines*lineHeight<=size.h,key+"/"+lang+": "+lines+" lines of "+lineHeight+" in "+size.h);
            }
        }
    }
    for(const o of ops) assert(prop(guards,prefix+o.id+"_click_enabled"));
});
console.log(`Barrad fielddesk: ${passed} scenario groups passed, ${failed} failed. Source/fixture validation only; live HOI4 relay and hidden mission acceptance remain a playtest.`);
if(failed) process.exitCode=1;
