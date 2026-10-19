"use strict";
// Run: node tools/Test-BarradNormalization.cjs
// Bounded script interpreter: validates this module's transitions, not HOI4 AI,
// combat or equipment recalculation. Unknown syntax fails instead of passing.
// Native syntax is checked separately against the locally installed game/EaW.
const fs = require("node:fs");
const path = require("node:path");
const assert = require("node:assert/strict");
const root = path.resolve(__dirname, "../mod/HoISubmod");
const game = process.env.HOI4_PATH || "C:/shit/Steam/steamapps/common/Hearts of Iron IV";
const eaw = process.env.EAW_PATH || "C:/shit/Steam/steamapps/workshop/content/394360/1826643372";
const regions = ["equus", "griffonia", "north", "riverlands", "zebrica"];
const sites = [625, 102, 558];
const prefix = "HSM_BAR_world_";
function parse(text) {
    const tokens = text.match(/"(?:\\.|[^"\\])*"|#[^\r\n]*|[{}]|[<>=!]+|[^\s{}<>=!#"]+/g) || [];
    const t = tokens.filter(x => !x.startsWith("#")); let i = 0;
    const atom = v => v.startsWith('"') ? JSON.parse(v) : v;
    function block(inner) {
        const nodes = [];
        while (i < t.length && t[i] !== "}") {
            const k = atom(t[i++]);
            if (!["=", ">", "<", ">=", "<="].includes(t[i])) { nodes.push({k, op: null, v: null}); continue; }
            const op = t[i++]; let v = t[i++]; assert(v !== undefined, "Missing value: " + k);
            if (v === "{") { v = block(true); assert.equal(t[i++], "}"); }
            else v = atom(v);
            nodes.push({k, op, v});
        }
        if (!inner) assert.equal(i, t.length, "Unexpected closing brace");
        return nodes;
    }
    return block(false);
}
const text = p => fs.readFileSync(path.join(root, p), "utf8");
const read = p => parse(text(p));
const get = (b,k) => b.find(n => n.k === k)?.v;
const map = b => Object.fromEntries(b.map(n => [n.k,n.v]));
const effectPath = "common/scripted_effects/HSM_BAR_normalization.txt";
const triggerPath = "common/scripted_triggers/HSM_BAR_normalization.txt";
const effects = map(read(effectPath));
const triggers = map(read(triggerPath));
for (const n of read("common/scripted_triggers/HSM_BAR_cases.txt")) {
    if (["HSM_BAR_containment_knowledge_ready", "HSM_BAR_forensics_knowledge_ready", "HSM_BAR_suppression_knowledge_ready"].includes(n.k)) triggers[n.k] = n.v;
}
const categories = read("common/decisions/HSM_BAR_normalization.txt");
const decisions = Object.fromEntries(categories.flatMap(n => n.v.map(d => [d.k,d.v])));
const ideas = map(get(read("common/ideas/HSM_BAR_normalization.txt"), "ideas").flatMap(n => n.v));
const actions = get(read("common/on_actions/HSM_BAR_normalization.txt"), "on_actions");
const events = read("events/HSM_BAR_normalization.txt").filter(n => ["country_event","news_event"].includes(n.k));
const templates = Object.fromEntries(read("history/units/HSM_BAR_normalization.txt").filter(n=>n.k==="division_template").map(n=>[get(n.v,"name"),n.v]));
const nameGroups = map(read("common/units/names_divisions/HSM_BAR_normalization.txt"));
const forward = "The First Footfalls", line = "The Hollow Line", siege = "The Weight Behind";
let passed = 0, failed = 0;
function check(name, fn) {
    try { fn(); passed++; console.log("PASS: " + name); }
    catch (err) { failed++; console.error("FAIL: " + name + "\n" + err.stack); }
}
function fresh() {
    const w = {day:0, flags:new Map(), countries:{}, states:{}, targets:{}, events:[], wars:[], units:[], calls:{}};
    for (const tag of ["BAR","EQS","ZES","NML","NEW"]) w.countries[tag] = {kind:"country", tag, exists:!["NML","NEW"].includes(tag), flags:new Set(), ideas:new Set(), capitulated:false, subject:false, divisions:["NML","NEW"].includes(tag)?0:10, manpower:0, stock:{}, techs:new Set(), pp:1000, stability:0, oob:false};
    for (const [id,owner] of [[624,"BAR"],[625,"BAR"],[626,"BAR"],[102,"EQS"],[103,"EQS"],[104,"EQS"],[558,"ZES"],[578,"ZES"],[680,"ZES"]]) w.states[id] = {kind:"state",id,owner,controller:owner,capital:[624,103,578].includes(id),cores:new Set([owner])};
    const c=w.countries.BAR;
    for (const f of ["active","directorate","service_founded","normalization","global_authorized","project_suppression_done"]) c.flags.add("HSM_BAR_"+f);
    for (const r of regions) c.flags.add("HSM_BAR_region_"+r+"_open");
    for (const k of ["rock","entity","echo","titan","compass","amulet"]) c.flags.add("HSM_BAR_study_"+k+"_done");
    return w;
}
function scope(w,k,s,root) {
    if (k === "ROOT") return root;
    if (k === "owner") { assert.equal(s.kind,"state"); return w.countries[s.owner]; }
    if (k.startsWith("event_target:")) return w.targets[k.slice(13)];
    return w.countries[k] || w.states[k];
}
function compare(a,op,b) { if(op === "=")return a===b; if(op===">")return a>b; if(op==="<")return a<b; if(op===">=")return a>=b; if(op==="<=")return a<=b; throw Error("Comparison "+op); }
function existsValue(v) {
    assert(["yes","no"].includes(v), "exists requires yes/no in country scope, not a country tag");
    return v === "yes";
}
function capitalState(v) {
    assert(Array.isArray(v), "set_capital requires a block containing state");
    assert(v.every(n=>["state","remember_old_capital"].includes(n.k)&&n.op==="="), "Unknown set_capital parameter");
    assert.equal(v.filter(n=>n.k==="state").length,1,"set_capital needs exactly one state");
    const state=Number(get(v,"state"));
    assert(Number.isInteger(state)&&state>0,"set_capital state must be a positive state ID in these fixtures");
    if(get(v,"remember_old_capital")!==undefined) assert(["yes","no"].includes(get(v,"remember_old_capital")));
    return state;
}
function test(nodes,w,s,root=s) {
    return nodes.every(({k,v,op}) => {
        if (k === "tooltip") return true;
        if (k === "AND" || k === "custom_trigger_tooltip") return test(v,w,s,root);
        if (k === "OR") return v.some(n=>test([n],w,s,root));
        if (k === "NOT") return !v.some(n=>test([n],w,s,root));
        if (triggers[k]) return test(triggers[k],w,s,root) === (v === "yes");
        if (Array.isArray(v) && scope(w,k,s,root)) return test(v,w,scope(w,k,s,root),root);
        if (k === "tag") return s.tag === v;
        if (k === "exists") { assert.equal(s.kind,"country"); return s.exists === existsValue(v); }
        if (k === "has_country_flag") return s.flags.has(v);
        if (k === "has_global_flag") {
            if (!Array.isArray(v)) return w.flags.has(v);
            if (!w.flags.has(get(v,"flag"))) return false;
            const d=v.find(n=>n.k==="days"); return compare(w.day-w.flags.get(get(v,"flag")),d.op,Number(d.v));
        }
        if (k === "has_idea") return s.ideas.has(v);
        if (k === "has_capitulated") return s.capitulated === (v === "yes");
        if (k === "is_subject") return s.subject === (v === "yes");
        if (k === "is_capital") return s.capital === (v === "yes");
        if (k === "state") return s.id === Number(v);
        if (k === "any_owned_state") return Object.values(w.states).some(st=>st.owner===s.tag&&test(v,w,st,root));
        if (k === "num_of_controlled_states") return compare(Object.values(w.states).filter(x=>x.controller===s.tag).length,op,Number(v));
        if (k === "num_divisions") return compare(s.divisions,op,Number(v));
        if (k === "controls_state") return w.states[v].controller === s.tag;
        if (k === "has_full_control_of_state") return w.states[v].controller === s.tag && !w.states[v].partial;
        if (k === "is_fully_controlled_by") return s.controller === (v==="OWNER"?s.owner:v) && !s.partial;
        if (k === "has_war_with") return w.wars.some(([a,b])=>(a===s.tag&&b===v)||(a===v&&b===s.tag));
        throw Error("Unknown trigger: "+k);
    });
}
function run(nodes,w,s,root=s) {
    let previousIf;
    for (const {k,v} of nodes) {
        if (k === "if") { previousIf=test(get(v,"limit"),w,s,root); if(previousIf)run(v.filter(n=>n.k!=="limit"),w,s,root); continue; }
        if (k === "else") { assert.notEqual(previousIf,undefined); if(!previousIf)run(v,w,s,root); continue; }
        if (effects[k]) { w.calls[k]=(w.calls[k]||0)+1; run(effects[k],w,s,root); continue; }
        if (k === "every_country") { for(const c of Object.values(w.countries))if(c.exists)run(v,w,c,root); continue; }
        if (Array.isArray(v) && scope(w,k,s,root)) { run(v,w,scope(w,k,s,root),root); continue; }
        if (k === "set_country_flag") s.flags.add(v);
        else if (k === "clr_country_flag") s.flags.delete(v);
        else if (k === "set_global_flag") w.flags.set(v,w.day);
        else if (k === "clr_global_flag") w.flags.delete(v);
        else if (k === "add_ideas") s.ideas.add(v);
        else if (k === "remove_ideas") s.ideas.delete(v);
        else if (k === "add_stability") s.stability += Number(v);
        else if (k === "country_event" || k === "news_event") w.events.push({id:get(v,"id"),scope:s.tag,kind:k});
        else if (k === "save_global_event_target_as") w.targets[v]=s;
        else if (k === "transfer_state") { w.states[v].owner=s.tag;w.states[v].controller=s.tag;s.exists=true; }
        else if (k === "set_capital") {
            assert.equal(s.kind,"country");const state=capitalState(v);
            assert.equal(w.states[state]?.owner,s.tag,"Capital must be transferred to the invader first");
            for(const st of Object.values(w.states)) if(st.owner===s.tag) st.capital=false;
            s.capital=state;w.states[state].capital=true;
        }
        else if (k === "add_core_of") s.cores.add(v);
        else if (k === "add_manpower") s.manpower+=Number(v);
        else if (k === "add_equipment_to_stockpile") { const type=get(v,"type"),amount=Number(get(v,"amount"));assert(amount>0);assert.equal(get(v,"producer"),s.tag);s.stock[type]=(s.stock[type]||0)+amount; }
        else if (k === "load_oob") { assert.equal(v,"HSM_BAR_normalization");s.oob=true; }
        else if (k === "declare_war_on") { const target=scope(w,get(v,"target"),s,root);assert(target&&target.exists);assert.notEqual(s.tag,target.tag);w.wars.push([s.tag,target.tag]); }
        else if (k === "create_unit") {
            const owner=w.countries[get(v,"owner")];assert(owner.exists&&owner.oob);assert.equal(s.kind,"state");assert.equal(s.controller,owner.tag);assert(!s.partial);
            const division=parse(get(v,"division")),template=get(division,"division_template");assert(templates[template],"Unknown spawn template: "+template);
            assert.deepEqual(division.map(n=>n.k),["division_template","start_experience_factor","start_equipment_factor"]);
            assert.equal(get(division,"start_equipment_factor"),"1");assert.equal(get(division,"start_experience_factor"),"0.35");
            const n=Number(get(v,"count"));assert(Number.isInteger(n)&&n>0);w.units.push({owner:owner.tag,state:s.id,count:n,template,day:w.day});owner.divisions+=n;
        }
        else if (k === "set_technology") { for(const n of v){assert.equal(n.v,"1");s.techs.add(n.k);}w.calls[k]=(w.calls[k]||0)+1; }
        else if (["set_popularities","set_politics","set_rule","add_ai_strategy","set_stability","set_war_support","actually_fix_weapon_techs"].includes(k)) { w.calls[k]=(w.calls[k]||0)+1; }
        else throw Error("Unknown effect: "+k);
    }
}
const call=(id,w,tag="BAR")=>run(effects[id],w,w.countries[tag]);
const has=(w,f)=>w.flags.has(prefix+f);
function startDecision(id,w,tag="BAR") {
    const d=decisions[id],c=w.countries[tag]; assert(test(get(d,"available"),w,c)); c.pp-=Number(get(d,"cost"));run(get(d,"complete_effect"),w,c);
}
function endDecision(id,w,tag="BAR") { run(get(decisions[id],"remove_effect"),w,w.countries[tag]); }
function prepared(w) { for(const r of regions) {startDecision("HSM_BAR_normalization_grid_"+r,w);w.day+=35;endDecision("HSM_BAR_normalization_grid_"+r,w);} }
function activated() {const w=fresh();prepared(w);startDecision("HSM_BAR_normalization_activate",w);w.day+=14;endDecision("HSM_BAR_normalization_activate",w);return w;}
function tick(w,day) {w.day=day;for(const c of Object.values(w.countries))if(c.exists)call("HSM_BAR_normalization_world_tick",w,c.tag);}
function breached() {const w=activated();const d=w.day;tick(w,d+21);tick(w,d+42);return w;}
function count(w) {return w.units.reduce((n,x)=>n+x.count,0);}
function composition(w,day) {const result={};for(const u of w.units.filter(u=>u.day===day))result[u.template]=(result[u.template]||0)+u.count;return result;}
function defeat(w) {w.countries.NML.capitulated=true;for(const s of Object.values(w.states))if(s.controller==="NML")s.controller="BAR";tick(w,w.day+1);}
function walk(nodes,fn) {for(const n of nodes){fn(n);if(Array.isArray(n.v))walk(n.v,fn);}}

check("native exists grammar rejects a tag operand in every branch",()=>{
    const docs=fs.readFileSync(path.join(game,"documentation/triggers_documentation.md"),"utf8");
    assert.match(docs.split("## exists")[1].split("\n## ")[0],/DEN = \{ exists = yes \}/);
    const w=fresh();
    assert.throws(()=>test(parse("exists = NML"),w,w.countries.BAR),/exists requires yes\/no/);
    for(const file of [effectPath,triggerPath]) walk(read(file),n=>{if(n.k==="exists") existsValue(n.v);});
});
check("native set_capital grammar requires state blocks at all three breach sites",()=>{
    const docs=fs.readFileSync(path.join(game,"documentation/effects_documentation.md"),"utf8");
    assert.match(docs.split("## set_capital")[1].split("\n## ")[0],/set_capital = \{\s*state = 1234/);
    for(const invalid of ["set_capital = 625","set_capital = {}","set_capital = { province = 625 }"]) {
        assert.throws(()=>capitalState(get(parse(invalid),"set_capital")),/set_capital/);
    }
    const capitals=[];
    walk(read(effectPath),n=>{if(n.k==="set_capital") capitals.push(capitalState(n.v));});
    assert.deepEqual(capitals,sites);
});
check("pre-existing NML blocks a breach; dormant NML receives the selected capital after transfer",()=>{
    const existing=activated();existing.countries.NML.exists=true;tick(existing,existing.day+42);
    assert(!has(existing,"breached"));assert.equal(existing.wars.length,0);assert.equal(count(existing),0);
    for(const site of sites) {
        const w=activated();
        for(const earlier of sites.slice(0,sites.indexOf(site))) w.states[earlier].capital=true;
        tick(w,w.day+42);
        assert.equal(w.targets.HSM_BAR_norm_breach.id,site);
        assert.equal(w.countries.NML.capital,site);
        assert.equal(w.states[site].owner,"NML");assert.equal(w.states[site].capital,true);
        assert.equal(w.wars.length,1);assert.equal(count(w),4);
    }
});

check("five timed regional works and a timed activation, not focus rewards",()=>{
    const w=fresh();assert(!test(triggers.HSM_BAR_global_network_ready,w,w.countries.BAR));
    for(const r of regions) {const d=decisions["HSM_BAR_normalization_grid_"+r];assert.equal(get(d,"days_remove"),"35");assert.equal(get(d,"cost"),"50");call("HSM_BAR_normalization_complete_"+r,w);assert(!w.countries.BAR.flags.has("HSM_BAR_norm_grid_"+r+"_done"));}
    prepared(w);assert(test(triggers.HSM_BAR_global_network_ready,w,w.countries.BAR));
    call("HSM_BAR_begin_global_normalization",w);assert(!has(w,"normalization_started"));
    assert.equal(get(decisions.HSM_BAR_normalization_activate,"days_remove"),"14");
});
for(const missing of ["global_authorized","project_suppression_done","normalization","active","directorate","service_founded",...regions.map(r=>"region_"+r+"_open"),...regions.map(r=>"norm_grid_"+r+"_done"),...['rock','entity','echo','titan','compass','amulet'].map(k=>"study_"+k+"_done")]) {
    check("launch refuses missing "+missing,()=>{const w=fresh();prepared(w);w.countries.BAR.flags.delete("HSM_BAR_"+missing);w.countries.BAR.flags.add("HSM_BAR_norm_activation_working");call("HSM_BAR_begin_global_normalization",w);assert(!has(w,"normalization_started"));});
}
check("coexistence, puppeting, capitulation and loss of central installation block launch",()=>{
    for(const mutate of [c=>c.flags.add("HSM_BAR_coexistence"),c=>c.subject=true,c=>c.capitulated=true]) {const w=fresh();prepared(w);mutate(w.countries.BAR);assert(!test(triggers.HSM_BAR_global_network_ready,w,w.countries.BAR));}
    const w=fresh();prepared(w);w.states[624].controller="EQS";assert(!test(triggers.HSM_BAR_global_network_ready,w,w.countries.BAR));
});
check("stale region completion/cancellation never grants readiness; retry is possible",()=>{
    const w=fresh(),c=w.countries.BAR,id="HSM_BAR_normalization_grid_equus";startDecision(id,w);c.flags.delete("HSM_BAR_active");endDecision(id,w);assert(!c.flags.has("HSM_BAR_norm_grid_equus_done"));assert(!c.flags.has("HSM_BAR_norm_grid_equus_working"));
    c.flags.add("HSM_BAR_active");startDecision(id,w);run(get(decisions[id],"cancel_effect"),w,c);endDecision(id,w);assert(!c.flags.has("HSM_BAR_norm_grid_equus_done"));startDecision(id,w);endDecision(id,w);assert(c.flags.has("HSM_BAR_norm_grid_equus_done"));
});
check("activation cancellation cannot launch, and loss of research during it is guarded",()=>{
    const w=fresh();prepared(w);startDecision("HSM_BAR_normalization_activate",w);run(get(decisions.HSM_BAR_normalization_activate,"cancel_effect"),w,w.countries.BAR);endDecision("HSM_BAR_normalization_activate",w);assert(!has(w,"normalization_started"));
    startDecision("HSM_BAR_normalization_activate",w);w.countries.BAR.flags.delete("HSM_BAR_project_suppression_done");endDecision("HSM_BAR_normalization_activate",w);assert(!has(w,"normalization_started"));
});
check("initial success includes BAR and every extant country, and launch is idempotent",()=>{
    const w=activated();assert(has(w,"magic_suppressed"));for(const c of Object.values(w.countries))if(c.exists)assert(c.ideas.has("HSM_BAR_normalization_magic_failure"));
    const n=w.events.length,day=w.flags.get(prefix+"normalization_started");w.day+=3;w.countries.BAR.flags.add("HSM_BAR_norm_activation_working");call("HSM_BAR_begin_global_normalization",w);assert.equal(w.events.length,n);assert.equal(w.flags.get(prefix+"normalization_started"),day);assert.equal(w.countries.BAR.stability,.05);
});
check("delayed failures and actual war do not depend on event acknowledgement",()=>{
    const w=activated(),d=w.day;tick(w,d+20);assert(!has(w,"barriers_failing"));tick(w,d+21);assert(has(w,"barriers_failing"));assert.equal(count(w),0);tick(w,d+41);assert.equal(count(w),0);tick(w,d+42);assert(has(w,"breached"));assert.equal(w.states[625].owner,"NML");assert(w.states[625].cores.has("BAR"));assert(w.states[625].cores.has("NML"));assert.deepEqual(w.wars,[["NML","BAR"]]);assert.equal(count(w),4);
});
check("clock survives BAR annexation and its institutional flags being removed",()=>{
    const w=activated(),d=w.day;w.countries.BAR.exists=false;w.countries.BAR.flags.clear();for(const s of Object.values(w.states))if(s.owner==="BAR")s.owner=s.controller="EQS";
    tick(w,d+42);assert(has(w,"breached"));assert.deepEqual(w.wars,[["NML","EQS"]]);assert.equal(count(w),4);assert(test(triggers.HSM_BAR_normalization_choice_open,w,w.countries.EQS));
});
check("only finite safe fallback sites; no seizure of last state, capital or occupied land",()=>{
    const w=activated(),d=w.day;w.states[625].capital=true;w.states[102].controller="ZES";tick(w,d+42);assert.equal(w.targets.HSM_BAR_norm_breach.id,558);assert.deepEqual(w.wars,[["NML","ZES"]]);
    const blocked=activated(),b=blocked.day;for(const s of sites)blocked.states[s].capital=true;tick(blocked,b+42);assert(!has(blocked,"breached"));assert.equal(count(blocked),0);blocked.states[102].capital=false;tick(blocked,b+43);assert.equal(blocked.targets.HSM_BAR_norm_breach.id,102);
    const last=activated();for(const s of Object.values(last.states))if(s.owner==="BAR"&&s.id!==625)s.controller="EQS";tick(last,last.day+42);assert.equal(last.targets.HSM_BAR_norm_breach.id,102);
    const occupied=activated();occupied.states[624].owner="EQS";occupied.states[626].owner="EQS";assert(Object.values(occupied.states).filter(s=>s.controller==="BAR").length>1);tick(occupied,occupied.day+42);assert.equal(occupied.targets.HSM_BAR_norm_breach.id,102,"Occupied foreign land is not retained owned land");
});
check("three idempotent waves total 8 or 12 divisions, never an all-country war loop",()=>{
    for(const large of [false,true]) {const w=activated();if(large)w.countries.BAR.divisions=80;tick(w,w.day+42);const d=w.day;tick(w,d+28);tick(w,d+56);assert.equal(count(w),large?12:8);const wars=w.wars.length;tick(w,d+365);assert.equal(count(w),large?12:8);assert.equal(w.wars.length,wars);assert.equal(w.calls.set_technology,1);}
});
check("lost aperture consumes waves without relocating or reopening them",()=>{
    const w=breached(),d=w.day;w.states[625].controller="BAR";w.states[626].controller="NML";tick(w,d+28);assert(has(w,"wave_two"));assert(has(w,"aperture_closed"));assert.equal(count(w),4);w.states[625].controller="NML";tick(w,d+29);assert.equal(count(w),4);tick(w,d+56);assert(has(w,"wave_three"));assert.equal(count(w),4);assert(!has(w,"incursions_defeated"));
});
check("wave timing and composition respond to 39/40 division boundary and territorial expansion",()=>{
    for(const size of [39,40])for(const expanded of [false,true]) {
        const w=activated();w.countries.BAR.divisions=size;tick(w,w.day+42);const d=w.day,large=size===40;
        assert.deepEqual(composition(w,d),{[forward]:large?4:3,[line]:large?2:1});
        w.countries.BAR.divisions=large?1:100; // Scaling is fixed at the original transfer.
        tick(w,d+27);assert.equal(count(w),large?6:4);tick(w,d+28);
        assert.deepEqual(composition(w,d+28),{[line]:large?2:1,[siege]:1});
        if(expanded)w.states[626].controller="NML";
        tick(w,d+55);assert.equal(count(w),large?9:6);tick(w,d+56);
        assert.deepEqual(composition(w,d+56),{[expanded?siege:line]:large?3:2});
        tick(w,d+365);assert.equal(count(w),large?12:8);
        assert(w.units.every(u=>u.state===625));assert.equal(w.wars.length,1);
    }
});
check("expansion lost before final deadline yields holders, not siege reinforcements",()=>{
    const w=breached(),d=w.day;w.states[626].controller="NML";tick(w,d+28);w.states[626].controller="BAR";tick(w,d+56);
    assert.deepEqual(composition(w,d+56),{[line]:2});
});
check("partial aperture loss between deadlines permanently cuts reinforcements without awarding victory",()=>{
    const w=breached(),d=w.day;w.states[625].partial=true;tick(w,d+7);assert(has(w,"aperture_closed"));assert(!has(w,"incursions_defeated"));
    w.states[625].partial=false;w.states[626].controller="NML";tick(w,d+56);assert.equal(count(w),4);assert(!has(w,"normalization_victory"));
    startDecision("HSM_BAR_normalization_restore",w);endDecision("HSM_BAR_normalization_restore",w);assert(has(w,"barriers_restored"));
});
check("capture on either reinforcement deadline wins before spawning, in either country tick order",()=>{
    for(const offset of [28,56])for(const reverse of [false,true]) {
        const w=breached(),d=w.day;if(offset===56)tick(w,d+28);const n=count(w);
        w.states[625].controller="BAR";w.states[626].controller="NML";w.day=d+offset;
        const tags=Object.keys(w.countries).filter(t=>w.countries[t].exists);if(reverse)tags.reverse();
        for(const tag of tags)call("HSM_BAR_normalization_world_tick",w,tag);
        assert.equal(count(w),n);assert(has(w,"aperture_closed"));
        w.states[625].controller="NML";tick(w,d+365);assert.equal(count(w),n);
    }
});
check("each fallback uses its actual owner's force size and retains a single aperture",()=>{
    for(const site of sites) {
        const w=activated();for(const prior of sites.slice(0,sites.indexOf(site)))w.states[prior].capital=true;
        const victim=w.states[site].owner;w.countries[victim].divisions=40;tick(w,w.day+42);const d=w.day;
        assert.equal(w.targets.HSM_BAR_norm_victim.tag,victim);assert.deepEqual(w.wars,[["NML",victim]]);assert.equal(count(w),6);
        tick(w,d+56);assert.equal(count(w),12);assert(w.units.every(u=>u.state===site));
    }
});
check("subjects and partially occupied sites are skipped; blocked retries never create troops or wars",()=>{
    const w=activated(),d=w.day;w.countries.BAR.subject=true;w.states[102].partial=true;w.countries.ZES.subject=true;
    tick(w,d+42);tick(w,d+100);assert.equal(count(w),0);assert.equal(w.wars.length,0);assert(!has(w,"breached"));
    w.states[102].partial=false;tick(w,d+101);assert.equal(w.targets.HSM_BAR_norm_breach.id,102);assert.equal(count(w),4);
});
check("defeated invaders never resurrect on later pulses or after release",()=>{
    const w=breached();defeat(w);assert(has(w,"incursions_defeated"));const n=count(w);w.countries.NML.capitulated=false;w.countries.NML.exists=true;w.states[625].controller="NML";tick(w,w.day+365);assert.equal(count(w),n);assert.equal(w.wars.length,1);
});
check("all neutralization routes stop waves and clean NML's spirit, including dormant releases",()=>{
    for(const outcome of ["annexed","capitulated","subject","landless"]) {
        const w=breached(),c=w.countries.NML,n=count(w);
        if(outcome==="annexed")c.exists=false;
        if(outcome==="capitulated")c.capitulated=true;
        if(outcome==="subject")c.subject=true;
        if(outcome==="landless")w.states[625].controller="BAR";
        tick(w,w.day+28);assert(has(w,"incursions_defeated"));assert.equal(count(w),n);
        c.exists=true;c.capitulated=false;c.subject=false;w.states[625].controller="NML";
        run(get(get(actions,"on_release_as_free"),"effect"),w,c);assert(!c.ideas.has("HSM_BAR_normalization_beyond"));
        tick(w,w.day+365);call("HSM_BAR_normalization_first_wave",w);assert.equal(count(w),n);assert.equal(w.wars.length,1);
    }
});
check("initialization is idempotent and reserves never replenish on later waves",()=>{
    const w=breached(),c=w.countries.NML,initial={...c.stock},manpower=c.manpower;
    assert.deepEqual(initial,{infantry_equipment_2:14000,artillery_equipment_1:480,support_equipment_1:600});
    c.stock={};c.manpower=0;call("HSM_BAR_normalization_prepare_invader",w,"NML");tick(w,w.day+56);
    assert.deepEqual(c.stock,{});assert.equal(c.manpower,0);assert(manpower>0);assert.equal(w.calls.set_technology,1);
});
check("restoration removes magic debuffs worldwide but preserves wars and troops",()=>{
    const w=breached(),id="HSM_BAR_normalization_restore",d=w.day;startDecision(id,w);tick(w,d+28);tick(w,d+35);assert.equal(count(w),6);
    const army=JSON.stringify(w.units),wars=JSON.stringify(w.wars),land=JSON.stringify(w.states);endDecision(id,w);assert(has(w,"barriers_restored"));assert(!has(w,"magic_suppressed"));for(const c of Object.values(w.countries))if(c.exists)assert(!c.ideas.has("HSM_BAR_normalization_magic_failure"));assert.equal(JSON.stringify(w.units),army);assert.equal(JSON.stringify(w.wars),wars);assert.equal(JSON.stringify(w.states),land);tick(w,w.day+180);assert.equal(JSON.stringify(w.units),army);assert(w.countries.NML.ideas.has("HSM_BAR_normalization_beyond"),"Restoration is not defeat");
});
check("pressing normalization keeps costs until actual defeat, then unlocks ending",()=>{
    const w=breached(),id="HSM_BAR_normalization_press";startDecision(id,w);w.day+=28;endDecision(id,w);assert(has(w,"press_normalization"));assert(!has(w,"normalization_victory"));assert(w.countries.BAR.ideas.has("HSM_BAR_normalization_steel_defence"));tick(w,w.day+1);assert(!has(w,"normalization_victory"));defeat(w);assert(has(w,"normalization_victory"));assert(has(w,"magic_suppressed"));assert(!w.countries.BAR.ideas.has("HSM_BAR_normalization_steel_defence"));
});
check("choices are exclusive, late callbacks guarded and foreign country cannot choose early",()=>{
    const w=activated();assert(!test(triggers.HSM_BAR_normalization_choice_open,w,w.countries.BAR));tick(w,w.day+42);assert(!test(triggers.HSM_BAR_normalization_choice_open,w,w.countries.EQS));
    startDecision("HSM_BAR_normalization_restore",w);w.countries.BAR.flags.add("HSM_BAR_norm_escalation_working");endDecision("HSM_BAR_normalization_restore",w);endDecision("HSM_BAR_normalization_press",w);assert(!has(w,"press_normalization"));
    const lost=breached();startDecision("HSM_BAR_normalization_restore",lost);lost.countries.BAR.flags.clear();endDecision("HSM_BAR_normalization_restore",lost);assert(!has(lost,"barriers_restored"));
});
check("post-defeat choice still allows both endings without pretending magic already returned",()=>{
    for(const which of ["restore","press"]) {const w=breached();defeat(w);assert(has(w,"magic_suppressed"));const id="HSM_BAR_normalization_"+which;startDecision(id,w);endDecision(id,w);tick(w,w.day+1);assert(has(w,which==="restore"?"barriers_restored":"normalization_victory"));}
});
check("successor controlling central station can restore after BAR dissolution",()=>{
    const w=breached();w.countries.BAR.exists=false;w.countries.BAR.flags.clear();w.states[624].controller="EQS";assert(test(triggers.HSM_BAR_normalization_choice_open,w,w.countries.EQS));startDecision("HSM_BAR_normalization_restore",w,"EQS");endDecision("HSM_BAR_normalization_restore",w,"EQS");assert(has(w,"barriers_restored"));assert.equal(count(w),4);
});
check("newly released countries receive active penalty, and stale dormant copies are cleaned",()=>{
    const w=breached(),c=w.countries.NEW;c.exists=true;for(const name of ["on_release_as_free","on_release_as_puppet","on_liberate"]) {c.ideas.clear();run(get(get(actions,name),"effect"),w,c);assert(c.ideas.has("HSM_BAR_normalization_magic_failure"));}
    c.exists=false;startDecision("HSM_BAR_normalization_restore",w);endDecision("HSM_BAR_normalization_restore",w);assert(c.ideas.has("HSM_BAR_normalization_magic_failure"));c.exists=true;call("HSM_BAR_normalization_sync",w,"NEW");assert(!c.ideas.has("HSM_BAR_normalization_magic_failure"));
});
check("wartime conventional programme is paid, guarded and globally cleaned after defeat",()=>{
    const w=breached(),id="HSM_BAR_normalization_arm_without_magic";w.wars.push(["NML","EQS"]);startDecision(id,w,"EQS");endDecision(id,w,"EQS");assert(w.countries.EQS.ideas.has("HSM_BAR_normalization_steel_defence"));assert.equal(w.countries.EQS.pp,950);defeat(w);assert(!w.countries.EQS.ideas.has("HSM_BAR_normalization_steel_defence"));endDecision(id,w,"EQS");assert(!w.countries.EQS.ideas.has("HSM_BAR_normalization_steel_defence"));
});
check("equipment weakening is restricted to exactly three real magical archetypes",()=>{
    const bonuses=get(ideas.HSM_BAR_normalization_magic_failure,"equipment_bonus");assert.deepEqual(bonuses.map(n=>n.k).sort(),["magical_artillery_equipment","magical_equipment","magical_tank_equipment"]);
    for(const b of bonuses){assert.equal(get(b.v,"instant"),"yes");assert.equal(get(b.v,"soft_attack"),"-0.40");}
    assert.equal(get(ideas.HSM_BAR_normalization_magic_failure,"modifier"),undefined);
    assert.deepEqual(get(ideas.HSM_BAR_normalization_steel_defence,"equipment_bonus").map(n=>n.k),["infantry_equipment","artillery_equipment"]);
});
check("no open-ended spawning loops, no all-country wars and no world reset on annex",()=>{
    walk(read(effectPath),n=>{assert(!["while","random_country","every_state","every_owned_state","random_owned_state"].includes(n.k));if(n.k==="every_country")assert.deepEqual(n.v,[{k:"HSM_BAR_normalization_sync",op:"=",v:"yes"}]);});
    assert.equal(get(actions,"on_annex"),undefined);
    assert.equal(text(effectPath).match(/declare_war_on =/g).length,3);
    assert.equal(text(effectPath).match(/transfer_state =/g).length,3);
    assert(!/delete_unit|white_peace|annex_country/.test(text(effectPath)));
});
check("events are presentation-only and EN/RU keys are complete, unique and literal",()=>{
    const locals={};for(const lang of ["english","russian"]){const raw=text("localisation/"+lang+"/HSM_BAR_normalization_l_"+lang+".yml");assert.equal(raw.charCodeAt(0),0xFEFF);const entries=[...raw.matchAll(/^ ([\w.]+):0 "((?:\\.|[^"\\])*)"$/gm)];assert.equal(entries.length,new Set(entries.map(m=>m[1])).size);locals[lang]=new Map(entries.map(m=>[m[1],m[2]]));}
    assert.deepEqual([...locals.english.keys()].sort(),[...locals.russian.keys()].sort());
    for(const e of events){assert.equal(get(e.v,"is_triggered_only"),"yes");assert.equal(get(e.v,"fire_only_once"),"yes");assert.equal(get(e.v,"immediate"),undefined);for(const k of ["title","desc"])assert(locals.english.has(get(e.v,k)));for(const o of e.v.filter(n=>n.k==="option")){assert.deepEqual(o.v.map(n=>n.k),["name"]);assert(locals.english.has(get(o.v,"name")));}assert(!/\[[^\]]+\]|political power|политическ|equipment archetype/i.test(locals.english.get(get(e.v,"desc"))+locals.russian.get(get(e.v,"desc"))));}
    for(const id of Object.keys(decisions))for(const suffix of ["","_desc"])assert(locals.english.has(id+suffix),id+suffix);
});
check("dormant tag has no start army; three locked formations have distinct native roles and names",()=>{
    const history=read("history/countries/NML - Beyond the Last Light.txt");assert.equal(get(history,"oob"),undefined);assert.equal(get(history,"add_core_of"),undefined);
    assert(read("history/units/HSM_BAR_normalization.txt").every(n=>n.k==="division_template"));assert.deepEqual(Object.keys(templates),[forward,line,siege]);
    const expected={ [forward]:[6,0,["recon"]], [line]:[8,0,["engineer"]], [siege]:[6,1,["engineer","artillery"]] };
    for(const [name,template] of Object.entries(templates)) {
        assert.equal(get(template,"is_locked"),"yes");assert.equal(get(template,"template_counter"),"1");
        const regiments=get(template,"regiments"),support=get(template,"support");
        assert.deepEqual([regiments.filter(n=>n.k==="infantry").length,regiments.filter(n=>n.k==="artillery_brigade").length,support.map(n=>n.k)],expected[name]);
        for(const section of [regiments,support])assert.equal(new Set(section.map(n=>get(n.v,"x")+","+get(n.v,"y"))).size,section.length);
        const group=nameGroups[get(template,"division_names_group")];assert(group);assert.equal(get(group,"name"),name);
        assert.deepEqual(get(group,"for_countries").map(n=>n.k),["NML"]);assert.equal((get(group,"fallback_name").match(/%d/g)||[]).length,1);
    }
});
check("all module flags and custom trigger tooltips have EN/RU labels",()=>{
    const keys=new Set();
    for(const file of [effectPath,triggerPath,"common/decisions/HSM_BAR_normalization.txt","common/decisions/categories/HSM_BAR_normalization.txt","common/on_actions/HSM_BAR_normalization.txt"]) {
        for(const match of text(file).matchAll(/\bHSM_BAR_(?:norm_|world_)[a-z_]+/g)) {
            if(!["HSM_BAR_norm_breach","HSM_BAR_norm_victim"].includes(match[0]))keys.add(match[0]);
        }
        walk(read(file),n=>{if(n.k==="tooltip")keys.add(n.v);});
    }
    for(const lang of ["english","russian"]) {
        const raw=text("localisation/"+lang+"/HSM_BAR_normalization_l_"+lang+".yml");
        for(const key of keys)assert(raw.includes(" "+key+":0"),lang+": "+key);
    }
});
check("native syntax, archetypes, technologies, state IDs and gfx verified against installed sources",()=>{
    const source=(base,file)=>fs.readFileSync(path.join(base,file),"utf8");
    const effectDocs=source(game,"documentation/effects_documentation.md"),triggerDocs=source(game,"documentation/triggers_documentation.md");
    const createUnitDocs=effectDocs.slice(effectDocs.indexOf("## create_unit"),effectDocs.indexOf("## create_wargoal"));
    assert(createUnitDocs.includes("count = 1"),"create_unit count must be a documented native parameter");
    assert(source(eaw,"common/decisions/KIR_decisions.txt").includes("can_puppet = no"),"Native EaW precedent for can_puppet");
    for(const key of ["create_unit","load_oob","transfer_state","add_equipment_to_stockpile","division_template","set_global_flag","save_global_event_target_as","declare_war_on","set_capital"])assert(effectDocs.includes("## "+key+"\r\n")||effectDocs.includes("## "+key+"\n"),key);
    for(const key of ["has_global_flag","is_capital","num_divisions","num_of_controlled_states","has_full_control_of_state","is_fully_controlled_by"])assert(triggerDocs.includes("## "+key+"\r\n")||triggerDocs.includes("## "+key+"\n"),key);
    const equip=map(get(parse(source(eaw,"common/units/equipment/magical_eq.txt")),"equipments"));for(const id of get(ideas.HSM_BAR_normalization_magic_failure,"equipment_bonus").map(n=>n.k))assert.equal(get(equip[id],"is_archetype"),"yes");
    assert(/instant = yes/.test(source(eaw,"common/ideas/zzz_SOL_ideas.txt")));
    const tech=source(eaw,"common/technologies/infantry.txt");for(const id of ["melee_weapons","melee_weapons1","infantry_weapons","infantry_weapons2","improved_infantry_weapons"])assert(new RegExp("\\b"+id+"\\s*=\\s*\\{").test(tech),id);
    for(const id of sites){const f=fs.readdirSync(path.join(eaw,"history/states")).find(f=>f.startsWith(id+"-"));assert(f);assert.equal(get(get(parse(source(eaw,"history/states/"+f)),"state"),"id"),String(id));}
    const ideologies=parse(source(eaw,"common/ideologies/00_ideologies.txt"));assert(source(eaw,"common/ideologies/00_ideologies.txt").includes("fascism_ideology"));assert(ideologies.length);
    const gfx=source(game,"interface/eventpictures.gfx");for(const e of events)assert(gfx.includes(get(e.v,"picture")),get(e.v,"picture"));
    const nativeActions=fs.readdirSync(path.join(eaw,"common/on_actions")).filter(f=>f.endsWith(".txt")).map(f=>source(eaw,"common/on_actions/"+f)).join("\n");for(const a of actions)assert(nativeActions.includes(a.k+" ="),a.k);
});
check("native template units and stockpile models are enabled; finite reserves cover the largest scripted force",()=>{
    const source=file=>fs.readFileSync(path.join(eaw,file),"utf8");
    const nativeTechs=map(["infantry","artillery","support"].flatMap(f=>get(parse(source("common/technologies/"+f+".txt")),"technologies")));
    const nativeEquipment=map(["infantry","artillery","support"].flatMap(f=>get(parse(source("common/units/equipment/"+f+".txt")),"equipments")));
    const subunits=map(["infantry","artillery_brigade","artillery","engineer","recon"].flatMap(f=>get(parse(source("common/units/"+f+".txt")),"sub_units")));
    const w=breached(),c=w.countries.NML,unlocks={enable_equipments:new Set(),enable_subunits:new Set()};
    for(const id of c.techs) {
        assert(nativeTechs[id],"Missing installed technology: "+id);
        for(const field of Object.keys(unlocks))for(const block of nativeTechs[id].filter(n=>n.k===field)) {
            if(get(block.v,"limit"))continue; // Only unconditional unlocks prove DLC-independent support.
            for(const entry of block.v)unlocks[field].add(entry.k);
        }
    }
    const reserves={};
    for(const [id,amount] of Object.entries(c.stock)) {
        assert(nativeEquipment[id],"Missing installed equipment: "+id);assert(unlocks.enable_equipments.has(id),"Equipment not enabled: "+id);
        reserves[get(nativeEquipment[id],"archetype")]=amount;
    }
    for(const template of Object.values(templates))for(const unit of [...get(template,"regiments"),...get(template,"support")]) {
        assert(subunits[unit.k],"Missing installed subunit: "+unit.k);
        assert(get(subunits[unit.k],"active")==="yes"||unlocks.enable_subunits.has(unit.k),"Inactive subunit: "+unit.k);
    }
    for(const expanded of [false,true]) {
        const large=activated();large.countries.BAR.divisions=40;tick(large,large.day+42);const d=large.day;
        tick(large,d+28);if(expanded)large.states[626].controller="NML";tick(large,d+56);
        let manpower=0;const demand={};
        for(const division of large.units)for(const unit of [...get(templates[division.template],"regiments"),...get(templates[division.template],"support")]) {
            const def=subunits[unit.k];manpower+=Number(get(def,"manpower"))*division.count;
            for(const need of get(def,"need"))demand[need.k]=(demand[need.k]||0)+Number(need.v)*division.count;
        }
        assert(manpower<=c.manpower,"Manpower grant is smaller than the largest full contingent");
        for(const [id,amount] of Object.entries(demand))assert(reserves[id]>=amount,"Missing/insufficient reserve for "+id);
    }
    const example=source("common/units/names_divisions/WIT_names_divisions.txt");
    for(const key of ["for_countries","division_types","fallback_name"])assert(example.includes(key+" ="));
    assert(source("history/units/WIT_1007.txt").includes("division_names_group = WIT_INF_01"));
});
check("module audit distinguishes static magical components from penalized archetypes",()=>{
    const source=(base,file)=>fs.readFileSync(path.join(base,file),"utf8");
    const modifiers=source(game,"documentation/modifiers_documentation.md");
    assert(modifiers.includes("module_<EquipmentModule>_design_cost_factor"));
    for(const [file,id] of [["00_tank_modules","tank_magic_auto_cannon"],["00_plane_modules","plane_crystal_projectile_module"],["00_ship_modules","ship_light_crystal_projectile_module"]]) {
        const module=get(get(parse(source(eaw,"common/units/equipment/modules/"+file+".txt")),"equipment_modules"),id);
        assert(module,id);assert(Array.isArray(get(module,"add_stats")));assert(get(module,"category"));
        assert(!get(ideas.HSM_BAR_normalization_magic_failure,"equipment_bonus").some(n=>n.k===id));
    }
    // These checks establish source contracts, not proof that undocumented engine APIs cannot exist.
    for(const lang of ["english","russian"]) {
        const loc=text("localisation/"+lang+"/HSM_BAR_normalization_l_"+lang+".yml");
        for(const id of ["HSM_BAR_normalization_activate_desc","HSM_BAR_normalization_magic_failure_desc"]) {
            const entry=loc.split(/\r?\n/).find(line=>line.startsWith(" "+id+":"));assert(/module|модул/.test(entry),id+": missing scope limitation");
        }
    }
});
check("country presentation reuses complete existing assets, not missing flag/portrait keys",()=>{
    for(const [size,width,height] of [["",82,52],["medium",41,26],["small",10,7]]) {
        const rel=path.join("gfx/flags",size,"NML.tga");
        const data=fs.readFileSync(path.join(root,rel));
        assert.deepEqual(data,fs.readFileSync(path.join(game,"gfx/flags",size,"REB.tga")));
        assert.equal(data.readUInt16LE(12),width);assert.equal(data.readUInt16LE(14),height);
    }
    const leader=get(read("history/countries/NML - Beyond the Last Light.txt"),"create_country_leader");
    assert(fs.existsSync(path.join(eaw,get(leader,"picture"))));
    assert.equal(get(leader,"ideology"),"fascism_ideology");
    assert(text("localisation/english/HSM_BAR_normalization_l_english.yml").includes(" "+get(leader,"name")+":0"));
    const countries=fs.readdirSync(path.join(eaw,"common/country_tags")).filter(f=>f.endsWith(".txt")).map(f=>fs.readFileSync(path.join(eaw,"common/country_tags",f),"utf8")).join("\n");
    assert(!/^\s*NML\s*=/m.test(countries),"Dedicated NML tag must not shadow EaW");
});
console.log(`Normalization: ${passed} passed, ${failed} failed. Script/static checks only; native combat and UI require an in-game playtest.`);
process.exitCode=failed?1:0;
