"use strict";
// Installed EaW is the comparison authority, not a self-generated golden file.
const fs = require("node:fs");
const path = require("node:path");
const assert = require("node:assert/strict");
const {spawnSync} = require("node:child_process");
const {parse, prop} = require("./Test-BarradArchiveSkin.cjs");
const repo = path.resolve(__dirname, "..");
const mod = path.join(repo, "mod/HoISubmod");
const eaw = process.env.EAW_PATH || "C:/shit/Steam/steamapps/workshop/content/394360/1826643372";
const game = process.env.HOI4_PATH || "C:/shit/Steam/steamapps/common/Hearts of Iron IV";
const read = (root, file) => fs.readFileSync(path.join(root, file), "utf8");
const ast = (root, file) => parse(read(root, file), true);
const dict = nodes => Object.fromEntries(nodes.map(n => [n.key, n.value]));
const walk = function* (nodes) { for (const n of nodes) { yield n; if (Array.isArray(n.value)) yield* walk(n.value); } };
const files = (root, suffix) => fs.readdirSync(root, {recursive:true}).filter(f => f.endsWith(suffix)).map(f => path.join(root, f));
let passed = 0, failed = 0;
function check(name, fn) { try { fn(); passed++; console.log("PASS " + name); } catch (e) { failed++; console.error("FAIL " + name + "\n" + e.stack); } }
const ideaFile = "common/ideas/zzz_BAR_ideas.txt";
const mioFile = "common/military_industrial_organization/organizations/BAR_organization.txt";
const nativeIdeas = ast(eaw, ideaFile), changedIdeas = ast(mod, ideaFile);
const nativeMios = ast(eaw, mioFile), changedMios = ast(mod, mioFile);
const chars = dict(prop(ast(eaw, "common/characters/BAR.txt"), "characters"));
const triggers = dict(ast(mod, "common/scripted_triggers/HSM_BAR_staff.txt"));
const effects = dict(ast(mod, "common/scripted_effects/HSM_BAR_staff.txt"));
const locSelectors = ast(mod, "common/scripted_localisation/HSM_BAR_staff.txt");
const companies = ["bar_tank", "bar_tank2", "BAR_pen_arty", "BAR_pen_guns", "BAR_magic_guns", "BAR_pen_industry", "BAR_pen_refinery", "BAR_pen_light_planes", "BAR_pen_cas", "BAR_pen_medium_planes", "BAR_pen_shipyard"];
const repaired = Object.entries(chars).filter(([,v]) => v.some(n => n.key === "advisor") && prop(prop(prop(v,"portraits"),"army"),"small") === "GFX_idea_unknown_advisor").map(([k]) => k);
const applied = [...walk(prop(effects.HSM_BAR_staff_refresh, "if"))].filter(n => n.key === "set_portraits");
const portraits = Object.fromEntries(applied.map(n => [prop(n.value,"character"), prop(prop(n.value,"army"),"small")]));
function condition(nodes, w) {
    return nodes.every(n => {
        if (n.key === "OR") return n.value.some(x => condition([x], w));
        if (n.key === "AND" || n.key === "hidden_trigger") return condition(n.value, w);
        if (n.key === "NOT") return !n.value.some(x => condition([x], w));
        if (n.key === "BAR") return condition(n.value, w.bar || w);
        if (n.key === "tag") return w.tag === n.value;
        if (n.key === "original_tag") return w.original === n.value;
        if (n.key === "has_country_flag") return w.flags.has(n.value);
        if (n.key === "has_character") return w.characters.has(n.value);
        if (triggers[n.key]) return condition(triggers[n.key], w) === (n.value === "yes");
        throw Error("Unknown staff trigger: " + n.key);
    });
}
function execute(nodes, w) {
    let chosen = false;
    for (const n of nodes) {
        if (n.key === "if" || n.key === "else_if") {
            if (n.key === "if") chosen = false;
            if (!chosen && condition(prop(n.value,"limit"), w)) {
                chosen = true; execute(n.value.filter(x=>x.key!=="limit"), w);
            }
        } else if (n.key === "set_portraits") {
            const id = prop(n.value,"character");
            assert(w.characters.has(id), "Cannot revive an absent character");
            w.portraits[id] = prop(prop(n.value,"army"),"small"); w.writes++;
        } else if (n.key === "set_country_flag") w.flags.add(n.value);
        else if (n.key === "clr_country_flag") w.flags.delete(n.value);
        else throw Error("Unknown staff effect: " + n.key);
    }
}
function world(route) { return {tag:"BAR", original:"BAR", flags:new Set(route ? ["HSM_BAR_active", "HSM_BAR_"+route] : []), characters:new Set(repaired), portraits:Object.fromEntries(repaired.map(k=>[k,"GFX_idea_unknown_advisor"])), writes:0}; }
const spriteFiles = [path.join(eaw,"interface/eaw_portraits.gfx"), path.join(eaw,"interface/eaw_BAR_stuff.gfx"), path.join(game,"interface/ideas.gfx"), path.join(mod,"interface/HSM_BAR_staff.gfx")];
const sprites = Object.fromEntries(spriteFiles.flatMap(f => (prop(parse(fs.readFileSync(f,"utf8"),true),"spriteTypes") || []).map(n=>[prop(n.value,"name"),n.value])));
const texture = name => {
    assert(sprites[name], "Unresolved sprite " + name);
    const p = sprites[name].find(n=>n.key.toLowerCase()==="texturefile")?.value;
    assert(p, "No texture: " + name);
    const resolved = [mod,eaw,game].map(r=>path.join(r,p)).find(p=>fs.existsSync(p));
    assert(resolved, "Missing texture: " + p); return resolved;
};
const loc = (root, file) => Object.fromEntries([...read(root,file).matchAll(/^\s*([A-Za-z0-9_]+):\d*\s+"(.*)"\s*$/gm)].map(m=>[m[1],m[2]]));
const langs = Object.fromEntries(["english","russian"].map(l=>[l,loc(mod,`localisation/${l}/replace/HSM_BAR_staff_l_${l}.yml`)]));

check("whole-file overrides change only 10 idea pictures and 8 MIO icons", ()=> {
    const expectedIdeas = structuredClone(nativeIdeas), expectedMios = structuredClone(nativeMios);
    let ideaCount = 0, mioCount = 0;
    for (const cat of prop(expectedIdeas,"ideas")) if (Array.isArray(cat.value)) for (const idea of cat.value) {
        if (!companies.includes(idea.key) || idea.key === "BAR_pen_arty") continue;
        const replacement = prop(prop(changedIdeas,"ideas"),cat.key).find(n=>n.key===idea.key);
        const pic = prop(replacement.value,"picture"); assert(pic.startsWith("HSM_BAR_staff_"));
        assert.equal(prop(idea.value,"picture"),"unknown_advisor");
        idea.value.find(n=>n.key==="picture").value=pic; ideaCount++;
    }
    for (const mio of expectedMios) {
        if (prop(mio.value,"icon") !== "GFX_idea_unknown_advisor") continue;
        const icon = prop(changedMios.find(n=>n.key===mio.key).value,"icon");
        assert(icon.startsWith("GFX_idea_HSM_BAR_staff_"));
        mio.value.find(n=>n.key==="icon").value=icon; mioCount++;
    }
    assert.equal(ideaCount,10); assert.equal(mioCount,8);
    assert.deepEqual(changedIdeas,expectedIdeas); assert.deepEqual(changedMios,expectedMios);
});
check("no duplicate effective company definitions", ()=> {
    for (const [dir,defs,extract] of [
        ["common/military_industrial_organization/organizations",changedMios,a=>a],
        ["common/ideas",prop(changedIdeas,"ideas").flatMap(n=>Array.isArray(n.value)?n.value:[]).filter(n=>Array.isArray(n.value)),a=>(prop(a,"ideas")||[]).flatMap(n=>Array.isArray(n.value)?n.value:[]).filter(n=>Array.isArray(n.value))]
    ]) {
        const keys = new Set(defs.map(n=>n.key)), seen = new Map();
        for (const f of files(path.join(mod,dir),".txt")) for (const n of extract(parse(fs.readFileSync(f,"utf8"),true))) if(keys.has(n.key)) {
            assert(!seen.has(n.key),`${n.key}: ${f} and ${seen.get(n.key)}`); seen.set(n.key,f);
        }
        assert.equal(seen.size,keys.size);
    }
});
check("exactly nine placeholder advisor portraits, with no character overrides", ()=> {
    assert.equal(repaired.length,9); assert.deepEqual(Object.keys(portraits).sort(),repaired.sort());
    for (const id of repaired) assert(read(eaw,"history/countries/BAR - Baard.txt").includes("recruit_character = "+id));
    for (const f of files(path.join(mod,"common/characters"),".txt")) for (const c of prop(parse(fs.readFileSync(f,"utf8"),true),"characters")||[]) assert(!chars[c.key],"Duplicate BAR character "+c.key);
    assert.equal(new Set(Object.values(portraits)).size,9);
});
for (const route of ["collegium","directorate"]) {
    check(route+": apply once and leave all traits/costs/names to native characters",()=> {
        const w=world(route); execute(effects.HSM_BAR_staff_refresh,w); assert.deepEqual(w.portraits,portraits); assert.equal(w.writes,9);
        execute(effects.HSM_BAR_staff_refresh,w); assert.equal(w.writes,9);
    });
    check(route+": route exit restores native portraits; reentry reapplies",()=> {
        const w=world(route); execute(effects.HSM_BAR_staff_refresh,w); w.flags.delete("HSM_BAR_active"); execute(effects.HSM_BAR_staff_refresh,w);
        assert(Object.values(w.portraits).every(p=>p==="GFX_idea_unknown_advisor"));
        assert(!w.flags.has("HSM_BAR_staff_portraits_applied"));
        w.flags.add("HSM_BAR_active"); execute(effects.HSM_BAR_staff_refresh,w); assert.deepEqual(w.portraits,portraits);
    });
    check(route+": absent advisor never resurrected",()=> {
        const w=world(route); w.characters.delete(repaired[0]); execute(effects.HSM_BAR_staff_refresh,w); assert.equal(w.writes,8); assert(!w.characters.has(repaired[0]));
    });
}
check("native Barrad, other countries and flag-only impostors are unchanged",()=> {
    for (const variant of ["native","other","wrong_original","inactive","no_route"]) {
        const w=world(variant==="native"?null:"collegium");
        if(variant==="other")w.tag="EQS";
        if(variant==="wrong_original")w.original="EQS";
        if(variant==="inactive")w.flags.delete("HSM_BAR_active");
        if(variant==="no_route")w.flags.delete("HSM_BAR_collegium");
        execute(effects.HSM_BAR_staff_refresh,w); assert.equal(w.writes,0);
    }
});
check("EN/RU BOM, parity, unique definitions and exact native-name fallbacks",()=> {
    assert.deepEqual(Object.keys(langs.english).sort(),Object.keys(langs.russian).sort());
    assert.equal(Object.keys(langs.english).length,38);
    for(const lang of ["english","russian"]) {
        const file=`localisation/${lang}/replace/HSM_BAR_staff_l_${lang}.yml`, raw=read(mod,file);
        assert.equal(raw.charCodeAt(0),0xfeff); assert(raw.startsWith("\uFEFFl_"+lang+":"));
        const keys=[...raw.matchAll(/^\s*([A-Za-z0-9_]+):\d*\s+"/gm)].map(m=>m[1]); assert.equal(new Set(keys).size,keys.length);
        const native=loc(eaw,`localisation/${lang}/country_BAR_l_${lang}.yml`);
        for(const id of companies) {
            const selector=locSelectors.find(n=>prop(n.value,"name")===langs[lang][id].slice(1,-1)); assert(selector);
            const texts=selector.value.filter(n=>n.key==="text"); assert.equal(texts.length,2);
            assert.equal(langs[lang][prop(texts[1].value,"localization_key")],native[id]);
            for(const r of [null,"collegium","directorate"]) {
                const selected=texts.find(n=>!prop(n.value,"trigger")||condition(prop(n.value,"trigger"),world(r)));
                const value=langs[lang][prop(selected.value,"localization_key")]; assert(value && !/[\[\]$]/.test(value));
                assert.equal(value===native[id],r===null);
            }
        }
        for(const [id,v] of Object.entries(chars).filter(([,v])=>v.some(n=>n.key==="advisor"))) {
            const name = native[prop(v,"name")]; assert(name,"Unlocalized advisor "+id);
            for(const role of v.filter(n=>n.key==="advisor")) {
                const token=prop(role.value,"idea_token");
                assert.equal(native[token]||langs[lang][token], name, "Role-token name must match the same canonical person: "+token);
            }
        }
    }
});
check("native runtime and inheritance contracts exist in this installation",()=> {
    assert(read(game,"documentation/effects_documentation.md").includes("## set_portraits"));
    const actions=prop(ast(mod,"common/on_actions/HSM_BAR_staff.txt"),"on_actions");
    assert.equal(actions.length,2); assert(prop(actions,"on_daily_BAR")); assert(prop(actions,"on_startup"));
    const templates=dict(ast(eaw,"common/military_industrial_organization/organizations/00_generic_organization.txt"));
    for(const n of changedMios) assert(templates[prop(n.value,"include")],"Missing native MIO template "+n.key);
});
const imageItems=[];
check("all repaired images resolve, and existing Barrad advisor/company art is retained",()=> {
    const native=loc(eaw,"localisation/english/country_BAR_l_english.yml");
    for(const id of repaired) imageItems.push({path:texture(portraits[id]), label:native[prop(chars[id],"name")],kind:"EaW reusable portrait"});
    for(const cat of prop(changedIdeas,"ideas")) if(Array.isArray(cat.value)) for(const n of cat.value) if(companies.includes(n.key)) {
        imageItems.push({path:texture("GFX_idea_"+prop(n.value,"picture")),label:n.key,kind:n.key==="BAR_pen_arty"?"EaW Barrad original":"Native company emblem"});
    }
    for(const n of changedMios) texture(prop(n.value,"icon"));
    assert.equal(imageItems.length,20);
    for(const [id,v] of Object.entries(chars).filter(([id,v])=>!repaired.includes(id)&&v.some(n=>n.key==="advisor"))) {
        const picture=prop(prop(prop(v,"portraits"),"army"),"small");
        imageItems.push({path:texture(picture),label:native[prop(v,"name")],kind:"EaW Barrad original"});
    }
    const own=prop(ast(mod,"interface/HSM_BAR_staff.gfx"),"spriteTypes").map(n=>prop(n.value,"name"));
    assert.equal(new Set(own).size,10);
    for(const f of files(path.join(mod,"interface"),".gfx").filter(f=>!f.endsWith("HSM_BAR_staff.gfx"))) for(const n of prop(parse(fs.readFileSync(f,"utf8"),true),"spriteTypes")||[]) assert(!own.includes(prop(n.value,"name")),"Duplicate staff sprite");
});
check("physical image decode and nonblank pixels",()=> {
    const python=process.env.PYTHON || "C:/Users/laslo/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe";
    const args=[path.join(repo,"tools/Test-BarradStaffAssets.py")]; if(process.argv.includes("--preview"))args.push("--preview");
    const result=spawnSync(python,args,{input:JSON.stringify(imageItems),encoding:"utf8"});
    assert.equal(result.status,0,result.error?.message||result.stderr||result.stdout); console.log(result.stdout.trim());
});
console.log(`Staff: ${passed} passed, ${failed} failed.`);
process.exitCode=failed?1:0;
