"use strict";

// Windows: node tools/Test-BarradContentIcons.cjs
// Builds only a disposable fixture. Never builds or changes workspace content.
const fs=require("node:fs");
const path=require("node:path");
const os=require("node:os");
const assert=require("node:assert/strict");
const {spawnSync}=require("node:child_process");
const {document,definitions,patchDocument,prepare,audit,build,hash,registries}=require("./Build-BarradContentIcons.cjs");
const repo=path.resolve(__dirname,".."),fixture=fs.mkdtempSync(path.join(os.tmpdir(),"barrad-icons-test-"));
const mod="mod/HoISubmod/",catalogPath="tools/data/barrad-content-icons.json",reviewed="docs/barrad-icon-manifest.md";
const focusFile=mod+"common/national_focus/HSM_BAR_fixture.txt",ideaFile=mod+"common/ideas/HSM_BAR_fixture.txt",modifierFile=mod+"common/dynamic_modifiers/HSM_BAR_fixture.txt";
const generatedFile=mod+"common/dynamic_modifiers/HSM_BAR_mtk_projects.txt";
const read=file=>fs.readFileSync(path.join(fixture,file));
function put(file,data) {const target=path.join(fixture,file);fs.mkdirSync(path.dirname(target),{recursive:true});fs.writeFileSync(target,data);}
function copy(file) {put(file,fs.readFileSync(path.join(repo,file)));}
function snapshot(dir=fixture) {
    return Object.fromEntries(fs.readdirSync(dir,{withFileTypes:true}).flatMap(e=>{
        const f=path.join(dir,e.name);if(e.isDirectory())return Object.entries(snapshot(f));
        const stat=fs.statSync(f);return [[path.relative(fixture,f).replaceAll("\\","/"),{hash:hash(fs.readFileSync(f)),mtime:stat.mtimeMs}]];
    }));
}
let passed=0,failed=0;
function test(name,fn) {try{fn();passed++;console.log("PASS: "+name);}catch(e){failed++;console.error("FAIL: "+name+"\n"+e.stack);}}
function mutation(file,change,check) {const original=read(file);try{put(file,change(original));check();}finally{put(file,original);}}
function diagnose(pattern) {const errors=audit(prepare(fixture));assert(errors.some(e=>pattern.test(e)),"Expected "+pattern+"; got "+errors.join("\n"));}
try {
    copy(catalogPath);copy(reviewed);copy("tools/Build-BarradCollegiumProjects.cjs");copy("tools/data/barrad-collegium-projects.json");copy("tools/data/barrad-collegium-experiments.json");copy(generatedFile);
    for(const file of ["HSM_BAR_service_icons.gfx","HSM_BAR_service_icons_shine.gfx"])copy(mod+"interface/"+file);
    const rows=[...read(reviewed).toString().matchAll(/^\| `(HSM_BAR_(?:dir|cover)_\w+)` \|/gm)];
    for(const [,id] of rows) {copy(`art/source/${id}.png`);copy(mod+`gfx/interface/goals/${id}.tga`);}
    const catalog=JSON.parse(read(catalogPath)),ids=[];
    for(const [group,entries] of Object.entries(catalog.focuses))for(const suffix of Object.keys(entries))ids.push("HSM_BAR_"+(group==="common"?suffix:group+(suffix?"_"+suffix:"")));
    const conditional='shared_focus = { id = HSM_BAR_untouched icon = { GFX_HSM_BAR_dir_charter = { always = yes } GFX_HSM_BAR_cover_charter = yes } }';
    put(focusFile,"\uFEFF# icon = GFX_comment { }\r\n"+ids.map(id=>`shared_focus = { id = ${id} icon = GFX_goal_fixture completion_reward = { icon = GFX_nested text = "icon = GFX_quoted }" } }`).join("\r\n")+"\r\n"+conditional);
    put(ideaFile,"ideas = { country = {\n"+Object.keys(catalog.ideas).map(id=>`${id} = { picture = foreign_fixture modifier = { picture = nested_fixture } }`).join("\n")+"\n} }");
    put(modifierFile,Object.keys(catalog.modifiers).filter(id=>id!=="HSM_BAR_mtk_research").map(id=>`${id} = { icon = GFX_idea_foreign enable = { icon = GFX_nested } }`).join("\n"));
    const plan=prepare(fixture);assert.deepEqual(plan.errors,[]);
    // Real transparent artwork copied under fixture names, never workspace exports.
    for(const motif of plan.art)put(`art/source/HSM_BAR_${motif}.png`,read("art/source/HSM_BAR_cover_accounts.png"));
    const initial=snapshot(),png=`art/source/HSM_BAR_${plan.art[0]}.png`;

    test("81 ID-based scalar patches preserve BOM, comments, nested values and conditional focuses",()=>{
        const changes=plan.outputs.get(focusFile);assert(changes.startsWith("\uFEFF# icon = GFX_comment { }\r\n"));
        assert(changes.endsWith(conditional));assert.equal((changes.match(/icon = GFX_nested/g)||[]).length,81);
        assert.equal((changes.match(/icon = GFX_quoted/g)||[]).length,81);
        assert.equal(definitions(document(changes),"focuses").length,82);
        assert(plan.mappings.focuses.HSM_BAR_mtc_frontiers);assert(plan.mappings.focuses.HSM_BAR_public_works);
        assert(!plan.outputs.has(generatedFile));assert.deepEqual(snapshot(),initial);
    });
    test("a nested field cannot stand in for a missing direct field",()=>{
        const doc=document('shared_focus = { id = HSM_BAR_probe nested = { icon = GFX_foreign } }');
        assert.equal(definitions(doc,"focuses")[0].body.filter(n=>n.key==="icon").length,0);
        assert.throws(()=>patchDocument(doc,[{node:doc.nodes[0],value:"invalid"}]),/Only scalar/);
    });
    test("missing PNG aborts build before any fixture write",()=>{
        const bytes=read(png);fs.unlinkSync(path.join(fixture,png));
        try {const before=snapshot();assert.throws(()=>build(fixture),/Source PNG missing/);assert.deepEqual(snapshot(),before);}finally{put(png,bytes);}
    });
    test("corrupt PNG aborts build before any fixture write",()=>mutation(png,()=>Buffer.from("not a PNG"),()=>{
        const before=snapshot();assert.throws(()=>build(fixture),/not a PNG/);assert.deepEqual(snapshot(),before);
    }));
    test("mapped conditional fields and duplicate definitions are rejected",()=>{
        mutation(focusFile,b=>b.toString().replace("icon = GFX_goal_fixture","icon = { GFX_HSM_BAR_dir_charter = yes }"),()=>assert(prepare(fixture).errors.some(e=>e.includes("Mapped field must be scalar"))));
        mutation(focusFile,b=>b.toString()+`\nshared_focus = { id = ${ids[0]} icon = GFX_goal_fixture }`,()=>assert.throws(()=>prepare(fixture),/Duplicate definition/));
    });
    test("generated MTC modifier mismatch fails instead of patching the owner output",()=>mutation(generatedFile,b=>b.toString().replace("GFX_idea_HSM_BAR_art_collegium","GFX_idea_foreign"),()=>{
        const p=prepare(fixture);assert(p.errors.some(e=>e.includes("Generated MTC icon drift")));assert(!p.outputs.has(generatedFile));
    }));
    test("complete fixture builds through the existing Windows converter with Service assets preserved",()=>{
        const before=snapshot(),built=build(fixture),after=snapshot(),allowed=new Set([...built.outputs.keys(),...built.exports.map(j=>j.file)]);
        for(const [file,value] of Object.entries(before))if(!allowed.has(file))assert.deepEqual(after[file],value,file+" changed outside ownership");
        for(const file of Object.keys(after))if(!Object.hasOwn(before,file))assert(allowed.has(file),"Unexpected output: "+file);
        assert.deepEqual(audit(prepare(fixture)),[]);
    });
    test("successful --check is strictly read-only, including file timestamps",()=>{
        const before=snapshot(),result=spawnSync(process.execPath,[path.join(__dirname,"Build-BarradContentIcons.cjs"),"--root",fixture,"--check"],{encoding:"utf8"});
        assert.equal(result.status,0,result.stderr);assert(result.stdout.includes("read-only"));assert.deepEqual(snapshot(),before);
    });
    test("second fixture build is idempotent and preserves file timestamps",()=>{const before=snapshot();build(fixture);assert.deepEqual(snapshot(),before);});
    test("missing standard sprite is diagnosed",()=>mutation(registries[0],b=>b.toString().replace(`name = "GFX_HSM_BAR_${plan.art[0]}"`,'name = "GFX_removed_fixture"'),()=>diagnose(/Missing registered sprite/)));
    test("missing shine and incorrect masks are diagnosed",()=>{
        mutation(registries[1],b=>b.toString().replace(`name = "GFX_HSM_BAR_${plan.art[0]}_shine"`,'name = "GFX_removed_fixture_shine"'),()=>diagnose(/Missing shine/));
        mutation(registries[1],b=>b.toString().replace("animationmaskfile =", "wrongmaskfile ="),()=>diagnose(/GFX_HSM_BAR_.*Expected values to be strictly equal/));
    });
    test("truncated TGA and missing transparency are diagnosed",()=>{
        const tga=plan.exports[0].file;
        mutation(tga,b=>b.subarray(0,20),()=>diagnose(/truncated or excess pixel data/));
        mutation(tga,b=>{const copy=Buffer.from(b);for(let i=21;i<copy.length;i+=4)copy[i]=255;return copy;},()=>diagnose(/Missing transparent\/opaque alpha/));
    });
    test("new unmapped HSM_BAR focus, idea and modifier cannot hide behind covered mappings",()=>{
        const originals=[focusFile,ideaFile,modifierFile].map(f=>[f,read(f)]);
        try {
            put(focusFile,read(focusFile)+'\nshared_focus = { id = HSM_BAR_new_focus icon = GFX_foreign }');
            put(ideaFile,read(ideaFile)+'\nideas = { country = { HSM_BAR_new_idea = { picture = foreign } } }');
            put(modifierFile,read(modifierFile)+'\nHSM_BAR_new_modifier = { icon = GFX_idea_foreign }');
            const errors=audit(prepare(fixture));for(const id of ["focus","idea","modifier"])assert(errors.some(e=>e.startsWith("HSM_BAR_new_"+id+": Foreign icon remains")));
        }finally{for(const [f,b] of originals)put(f,b);}
    });
    test("parent can append an idea mapping without changing builder code",()=>{
        const original=read(catalogPath),ideas=read(ideaFile);
        try {
            const added=JSON.parse(original);added.ideas.HSM_BAR_new_idea="art_collegium";put(catalogPath,JSON.stringify(added));
            put(ideaFile,ideas+'\nideas = { country = { HSM_BAR_new_idea = { picture = foreign } } }');
            const p=prepare(fixture);assert.deepEqual(p.errors,[]);assert(p.outputs.get(ideaFile).includes("HSM_BAR_new_idea = { picture = HSM_BAR_art_collegium"));
        }finally{put(catalogPath,original);put(ideaFile,ideas);}
    });
    test("reviewed PNG hash drift is diagnosed without rewriting the manifest",()=>mutation("art/source/HSM_BAR_cover_accounts.png",()=>read("art/source/HSM_BAR_cover_charter.png"),()=>{
        const before=snapshot();diagnose(/Reviewed PNG hash changed/);assert.deepEqual(snapshot(),before);
    }));
    test("failing --check remains read-only and exits nonzero",()=>mutation(png,()=>Buffer.from("broken"),()=>{
        const before=snapshot(),result=spawnSync(process.execPath,[path.join(__dirname,"Build-BarradContentIcons.cjs"),"--root",fixture,"--check"],{encoding:"utf8"});
        assert.equal(result.status,1);assert(result.stderr.includes("not a PNG"));assert.deepEqual(snapshot(),before);
    }));
} finally {
    assert.equal(path.dirname(path.resolve(fixture)),path.resolve(os.tmpdir()));assert(path.basename(fixture).startsWith("barrad-icons-test-"));
    fs.rmSync(fixture,{recursive:true,force:true});
}
console.log(`Barrad content icon tooling: ${passed} passed, ${failed} failed. Fixture build only; workspace art is checked separately.`);
process.exitCode=failed?1:0;
