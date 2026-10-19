"use strict";
const fs=require("node:fs"),path=require("node:path"),assert=require("node:assert/strict");
const {parse,prop,field,resolveAsset,loadArchiveAssets,spriteDimensions,readTga,fontDefinition,fontColor,assertContrast,assertArtwork,assertDistinct}=require("./Test-BarradArchiveSkin.cjs");
const {projects,departments,faculties,preparations,factories}=require("./Build-BarradCollegiumProjects.cjs");
const root=path.resolve(__dirname,".."),mod=path.join(root,"mod/HoISubmod");
const read=f=>fs.readFileSync(path.join(mod,f),"utf8");
const experiments=JSON.parse(fs.readFileSync(path.join(__dirname,"data/barrad-collegium-experiments.json"),"utf8").replace(/^\uFEFF/,""));
const dict=n=>{assert.equal(new Set(n.map(x=>x.key)).size,n.length);return Object.fromEntries(n.map(x=>[x.key,x.value]));};
const gui=prop(parse(read("interface/HSM_BAR_mtk.gui")),"guiTypes");
const windows=Object.fromEntries(gui.map(x=>[prop(x.value,"name"),x.value]));
const script=dict(prop(parse(read("common/scripted_guis/HSM_BAR_mtk.txt")),"scripted_gui"));
const window=windows.HSM_BAR_mtk_window,sg=script.HSM_BAR_mtk_window;
const triggers=dict([...parse(read("common/scripted_triggers/HSM_BAR_mtk_projects.txt")),...parse(read("common/scripted_triggers/HSM_BAR_mtk_ui.txt"))]);
const widgets=window.filter(x=>Array.isArray(x.value)&&prop(x.value,"name"));
const selectors=Object.fromEntries(parse(read("common/scripted_localisation/HSM_BAR_mtk.txt")).map(x=>[prop(x.value,"name"),x.value.filter(n=>n.key==="text").map(n=>n.value)]));
const widgetTriggers=dict(prop(sg,"triggers")),effects=dict(prop(sg,"effects")),properties=dict(prop(sg,"properties"));
const backend=dict(parse(read("common/scripted_effects/HSM_BAR_mtk_projects.txt")));
const assets=loadArchiveAssets();
const dimensionCache=new Map();
const dimensions=sprite=>{if(!dimensionCache.has(sprite))dimensionCache.set(sprite,spriteDimensions(assets.sprites,sprite));return dimensionCache.get(sprite);};
function fresh(p=projects[0]){
 const flags=new Set(["HSM_BAR_active","HSM_BAR_collegium","HSM_BAR_collegium_initialized",...Object.values(departments).map(x=>x.alive)]);
 return {tag:"BAR",original:"BAR",exists:true,ai:false,capitulated:false,owner:true,controller:true,pp:1000,factories:4,flags,characters:new Set(Object.values(departments).map(x=>x.character)),focuses:new Set(["HSM_BAR_collegium_oath"]),missions:new Set(),vars:{HSM_BAR_mtk_open:1,HSM_BAR_mtk_department:Object.keys(departments).indexOf(p.department)+1,HSM_BAR_mtk_project:p.number,HSM_BAR_mtk_document:1},calls:[]};
}
function condition(nodes,s){return nodes.every(({key:k,value:v,op})=>{
 if(k==="AND")return condition(v,s);if(k==="OR")return v.some(n=>condition([n],s));if(k==="NOT")return !v.some(n=>condition([n],s));
 if(triggers[k]){assert(["yes","no"].includes(v),"Unsupported trigger argument block: "+k);return condition(triggers[k],s)===(v==="yes");}
 if(k==="always")return v==="yes";if(k==="tag")return s.tag===v;if(k==="original_tag")return s.original===v;
 if(k==="exists")return s.exists===(v==="yes");if(k==="is_ai")return s.ai===(v==="yes");if(k==="has_capitulated")return s.capitulated===(v==="yes");
 if(k==="has_country_flag")return s.flags.has(v);if(k==="has_character")return s.characters.has(v);if(k==="has_completed_focus")return s.focuses.has(v);
 if(k==="has_active_mission")return s.missions.has(v);if(k==="owns_state")return s.owner;if(k==="controls_state")return s.controller;
 if(k==="has_political_power"){assert.equal(op,"<");return s.pp<Number(v);}
 if(k==="num_of_civilian_factories_available_for_projects"){assert.equal(op,">");return s.factories>Number(v);}
 if(k==="has_variable")return Object.hasOwn(s.vars,v);
 if(k==="check_variable"){assert.equal(v.length,1);return (s.vars[v[0].key]??0)===Number(v[0].value);}
 throw Error("Unhandled predicate "+k);
});}
function execute(nodes,s){for(const {key:k,value:v}of nodes){
 if(k==="if"){if(condition(prop(v,"limit"),s))execute(v.filter(x=>x.key!=="limit"),s);}
 else if(k==="set_variable")for(const n of v)s.vars[n.key]=Number(n.value);
 else if(k==="clear_variable")delete s.vars[v];
 else if(backend[k])s.calls.push(k);
 else throw Error("Unhandled UI effect "+k);
}}
const visible=(name,s)=>!widgetTriggers[name+"_visible"]||condition(widgetTriggers[name+"_visible"],s);
const enabled=(name,s)=>!widgetTriggers[name+"_click_enabled"]||condition(widgetTriggers[name+"_click_enabled"],s);
const choose=(name,s)=>{assert(selectors[name],name);return prop(selectors[name].find(x=>!prop(x,"trigger")||condition(prop(x,"trigger"),s)),"localization_key");};
function localization(language){
 const out={};
 for(const file of fs.readdirSync(path.join(mod,"localisation",language)).filter(x=>x.endsWith(".yml"))){
  const source=fs.readFileSync(path.join(mod,"localisation",language,file),"utf8");
  for(const match of source.matchAll(/^\s*([A-Za-z0-9_.-]+):\d*\s+"((?:\\.|[^"\\])*)"\s*$/gm)){
   if(match[1].startsWith("HSM_BAR_mtk_"))assert(!Object.hasOwn(out,match[1]),"Duplicate key "+match[1]);
   out[match[1]]=match[2].replace(/\\n/g,"\n").replace(/\\"/g,'"').replace(/\\\\/g,"\\");
  }
 }
 return out;
}
const locales={english:localization("english"),russian:localization("russian")};
function expand(key,s,lang){
 if(!key)return "";
 if(key.startsWith("[Get"))key=choose(key.slice(1,-1),s);
 if(key.startsWith("GFX_"))return key;
 assert(Object.hasOwn(locales[lang],key),"Missing "+lang+" "+key);
 return locales[lang][key].replace(/\[\?(\w+)\|0\]/g,(_,v)=>String(s.vars[v]??0)).replace(/\$(HSM_BAR_\w+)\$/g,(_,v)=>expand(v,s,lang)).replace(/\[(Get\w+)\]/g,(_,v)=>expand(choose(v,s),s,lang));
}
function sceneState(p,stage,document,options={}){
 const s=fresh(p);s.vars.HSM_BAR_mtk_document=document;
 if(options.department)s.vars.HSM_BAR_mtk_department=Object.keys(departments).indexOf(options.department)+1;
 if(options.instrumented)s.flags.add(`HSM_BAR_mtk_${p.department}_instrumented`);
 if(stage==="theory")s.flags.add(`HSM_BAR_mtk_${p.id}_theory`);
 if(stage==="running")s.flags.add(`HSM_BAR_mtk_${p.id}_theory_running`);
 if(stage==="paid"){s.flags.add(`HSM_BAR_mtk_${p.id}_theory`);s.flags.add(`HSM_BAR_mtk_${p.id}_trials_running`);}
 if(stage==="done"){for(const q of projects.filter(x=>faculties(x).includes(p.department))){s.flags.add(`HSM_BAR_mtk_${q.id}_theory`);s.flags.add(`HSM_BAR_mtk_${q.id}_done`);}s.vars[`HSM_BAR_mtk_${p.department}_completed`]=5;}
 if(stage==="instrumented"){s.flags.add(`HSM_BAR_mtk_${p.id}_done`);s.flags.add(`HSM_BAR_mtk_${p.id}_instrumented`);}
 if(["prepared","observing","checkpoint","verifying","experiment_done"].includes(stage)){
  const id=`HSM_BAR_mtk_${p.id}`,combo=options.combo??0,response=options.response??"a";
  if(p.opus)for(const q of preparations(p.department))s.flags.add(`HSM_BAR_mtk_${q.id}_done`);
  for(const q of p.prerequisites||[])s.flags.add(`HSM_BAR_mtk_${q}_done`);
  s.flags.add(id+"_theory");s.flags.add(id+"_rig_"+(combo>=2?"b":"a"));s.flags.add(id+"_control_"+(combo%2?"b":"a"));
  if(stage!=="prepared"){
   if(combo>=2)s.flags.add(id+"_paid_rig_b");if(combo%2)s.flags.add(id+"_paid_control_b");
   if(stage==="experiment_done"){s.flags.add(id+"_done");s.flags.add(id+"_experiment_record");}
   else{s.flags.add(id+"_experiment_active");s.flags.add(id+"_trials_running");for(const d of faculties(p))s.flags.add(`HSM_BAR_mtk_${d}_busy`);}
   if(stage==="checkpoint")s.flags.add(id+"_observation_ready");
   if(stage==="verifying")s.flags.add(id+"_verify_running");
   if(["verifying","experiment_done"].includes(stage))s.flags.add(id+"_response_"+response);
  }
 }
 for(const d of Object.keys(departments))s.vars[`HSM_BAR_mtk_${d}_completed`]=preparations(d).filter(q=>s.flags.has(`HSM_BAR_mtk_${q.id}_done`)).length;
 return s;
}
function scene(p,lang,stage,document,options={}){
 const s=sceneState(p,stage,document,options),rendered=[];
 for(const n of widgets){const b=n.value,name=prop(b,"name");if(!visible(name,s))continue;
  const pos=prop(b,"position");if(!pos)continue;
  const record={name,kind:n.key,x:Number(prop(pos,"x")),y:Number(prop(pos,"y"))};
  if(n.key==="instantTextboxType")Object.assign(record,{w:Number(prop(b,"maxWidth")),h:Number(prop(b,"maxHeight")),font:prop(b,"font"),text:expand(prop(b,"text"),s,lang),scroll:!!prop(b,"scrollbartype")});
  else if(n.key==="buttonType"){
   const selector=properties[name]&&prop(properties[name],"image"),sprite=selector?expand(selector,s,lang):prop(b,"quadTextureSprite");
   Object.assign(record,{...dimensions(sprite),sprite,enabled:enabled(name,s),text:prop(b,"buttonText")?expand(prop(b,"buttonText"),s,lang):"",font:prop(b,"buttonFont")});
  }else throw Error(n.key);
  rendered.push(record);
 }
 return {department:options.department||p.department,project:p.id,language:lang,stage,document,...options,width:1000,height:700,widgets:rendered};
}
const measuredFonts=new Map();
function nativeFont(name,lang){
 const key=name+"/"+lang;if(measuredFonts.has(key))return measuredFonts.get(key);
 const f={glyphs:new Map(),kerning:new Map(),lineHeight:0},owners=new Map();
 for(const {value:base}of prop(fontDefinition(assets.fonts,name,lang),"fontfiles")){
  const rows=fs.readFileSync(resolveAsset(base+".fnt"),"utf8").split(/\r?\n/).filter(Boolean).map(line=>({kind:line.split(/\s/)[0],values:Object.fromEntries([...line.matchAll(/(\w+)=("[^"]*"|[^\s]+)/g)].map(m=>[m[1],Number(m[2])]))}));
  f.lineHeight ||= rows.find(r=>r.kind==="common").values.lineHeight;
  for(const {kind,values:v}of rows){
   if(kind==="char"&&!f.glyphs.has(v.id)){f.glyphs.set(v.id,v);owners.set(v.id,base);}
   if(kind==="kerning"&&owners.get(v.first)===base&&owners.get(v.second)===base&&!f.kerning.has(`${v.first}/${v.second}`))f.kerning.set(`${v.first}/${v.second}`,v.amount);
  }
 }
 assert(f.lineHeight>0,key);measuredFonts.set(key,f);return f;
}
function textHeight(text,font,width,label,checkInk=true){
 const f=font,measure=chars=>{let previous;return chars.reduce((total,c)=>{const code=c.codePointAt(0),g=f.glyphs.get(code);assert(g,`${label}: missing native glyph ${code}`);const size=g.xadvance+(f.kerning.get(`${previous}/${code}`)||0);previous=code;return total+size;},0);};
 const lines=[];let line=[],word=[];
 function flush(){
  if(line.length&&measure([...line,...word])>width){while(line.length&&/\s/.test(line.at(-1)))line.pop();lines.push(line);line=[];}
  for(const c of word){assert(measure([c])<=width,label+": glyph exceeds width");if(line.length&&measure([...line,c])>width){lines.push(line);line=[];}line.push(c);}word=[];
 }
 for(const c of text.replace(/§./g,"")){if(/\s/.test(c)){flush();if(c==="\n"){lines.push(line);line=[];}else if(line.length)line.push(c);}else word.push(c);}
 flush();lines.push(line);
 if(checkInk)for(const chars of lines){let x=0,previous;for(const c of chars){const code=c.codePointAt(0),g=f.glyphs.get(code);x+=f.kerning.get(`${previous}/${code}`)||0;if(g.width&&g.height)assert(x+g.xoffset+g.width<=width,`${label}: U+${code.toString(16)} ends at ${x+g.xoffset+g.width}px beyond ${width}px`);x+=g.xadvance;previous=code;}}
 return lines.length*f.lineHeight;
}
if(process.argv.includes("--fixtures")){
 const out=[];for(const lang of ["english","russian"])for(const p of projects)for(let d=1;d<=4;d++)out.push(scene(p,lang,"done",d));
 for(const lang of ["english","russian"])for(const p of projects.filter(p=>!p.partners&&(p.number-1)%6===0))for(const stage of ["proposal","running","theory"])out.push(scene(p,lang,stage,stage==="theory"?2:1));
 for(const lang of ["english","russian"])for(const p of projects){for(const instrumented of [false,true])out.push(scene(p,lang,"proposal",5,{instrumented}));if(p.opus)for(const stage of ["proposal","done"])out.push(scene(p,lang,stage,6));}
 for(const lang of ["english","russian"])for(const p of projects.filter(p=>p.partners))for(const document of [1,5])out.push(scene(p,lang,"paid",document,{instrumented:true,department:p.partners[0]}));
 for(const lang of ["english","russian"])out.push(scene(projects.find(p=>p.id==="revolver_howitzer"),lang,"instrumented",3));
 for(const lang of ["english","russian"])for(const p of projects){
  out.push(scene(p,lang,"proposal",7));out.push(scene(p,lang,"done",7));
  for(let combo=0;combo<4;combo++){
   for(const stage of ["prepared","observing"])out.push(scene(p,lang,stage,5,{combo}));
   for(const document of [3,5,7])out.push(scene(p,lang,"checkpoint",document,{combo}));
   for(const stage of ["verifying","experiment_done"])for(const response of ["a","b"])for(const document of [3,5,7])out.push(scene(p,lang,stage,document,{combo,response}));
  }
 }
 process.stdout.write(JSON.stringify(out));
}else{
 let passed=0,failed=0;function test(name,fn){try{fn();passed++;console.log("PASS "+name);}catch(e){failed++;console.error("FAIL "+name+"\n"+e.stack);}}
 test("owner-only independent launcher, no dirty cache, static click shields",()=>{
  assert.equal(prop(script.HSM_BAR_mtk_launcher,"context_type"),"player_context");assert.equal(prop(script.HSM_BAR_mtk_launcher,"parent_window_token"),"politics_tab");assert.equal(prop(sg,"context_type"),"player_context");assert.equal(prop(sg,"dirty"),undefined);
  assert.equal(prop(window,"orientation"),"center");assert.equal(prop(window,"origo"),"center");
  for(const [w,h]of [[1280,720],[1366,768],[1600,900],[1920,1080]]){assert(w>=1000+20);assert(h>=700+20);}
  assert.deepEqual(widgets.slice(0,2).map(n=>prop(n.value,"name")),["HSM_BAR_mtk_input_floor","HSM_BAR_mtk_input_shield"]);
  for(const k of ["floor","shield"]){const n=widgets.find(n=>prop(n.value,"name")==="HSM_BAR_mtk_input_"+k).value;assert.deepEqual(prop(n,"size"),parse("x = 1000 y = 700"));assert(!effects["HSM_BAR_mtk_input_"+k+"_click"]);}
 });
 test("opening, department switching and close reset document navigation",()=>{
  const s=fresh();execute(prop(script.HSM_BAR_mtk_launcher,"effects")[0].value,s);assert.equal(s.vars.HSM_BAR_mtk_project,1);
  for(const [i,d]of Object.keys(departments).entries()){s.vars.HSM_BAR_mtk_document=4;execute(effects[`HSM_BAR_mtk_dept_${d}_click`],s);assert.equal(s.vars.HSM_BAR_mtk_department,i+1);assert.equal(s.vars.HSM_BAR_mtk_project,i*6+1);assert.equal(s.vars.HSM_BAR_mtk_document,1);}
  execute(effects.HSM_BAR_mtk_close_click,s);assert(!Object.hasOwn(s.vars,"HSM_BAR_mtk_open"));assert(!condition(prop(sg,"visible"),s));
 });
 for(const p of projects)test(p.id+": disclosure, clickable stages, retained reports and independent department",()=>{
  const s=fresh(p);assert(condition(prop(sg,"visible"),s));
  for(const [flags,allowed]of [[[],[true,false,false,false]],[["theory"],[true,true,false,false]],[["done"],[true,true,true,true]],[["theory_running"],[true,false,false,false]],[["theory","trials_running"],[true,true,false,false]]]){
   for(const f of ["theory","done","theory_running","trials_running"])s.flags.delete(`HSM_BAR_mtk_${p.id}_${f}`);for(const f of flags)s.flags.add(`HSM_BAR_mtk_${p.id}_${f}`);
   for(let d=1;d<=4;d++){s.vars.HSM_BAR_mtk_document=d;assert.equal(enabled("HSM_BAR_mtk_doc_"+d,s),allowed[d-1]);assert.equal(choose("GetHSMBARMtkDocument",s),allowed[d-1]?`HSM_BAR_mtk_${p.id}_${["idea","theory","tests","conclusion"][d-1]}`:"HSM_BAR_mtk_document_pending");}
   assert.equal(choose("GetHSMBARMtkEffects",s),flags.includes("done")?`HSM_BAR_mtk_${p.id}_effects`:"HSM_BAR_mtk_no_application");
  }
  const other=projects.find(x=>!faculties(p).includes(x.department));s.vars.HSM_BAR_mtk_department=Object.keys(departments).indexOf(other.department)+1;assert.equal(choose("GetHSMBARMtkDocument",s),"HSM_BAR_mtk_document_pending");
  assert(!visible(`HSM_BAR_mtk_start_${p.id}_theory`,s));
  execute(effects[`HSM_BAR_mtk_start_${p.id}_theory_click`],s);assert.equal(s.calls.length,0);
 });
 test("revoked scope blocks window, documents, actions and project selection",()=>{
  for(const mutate of [s=>s.tag="EQS",s=>s.ai=true,s=>s.capitulated=true,s=>s.flags.delete("HSM_BAR_active"),s=>s.flags.delete("HSM_BAR_collegium"),s=>s.flags.add("HSM_BAR_directorate"),s=>s.focuses.clear(),s=>delete s.vars.HSM_BAR_mtk_open])for(const p of projects){const s=fresh(p);s.flags.add(`HSM_BAR_mtk_${p.id}_done`);s.vars.HSM_BAR_mtk_document=4;mutate(s);assert(!condition(prop(sg,"visible"),s));assert.equal(choose("GetHSMBARMtkDocument",s),"HSM_BAR_mtk_document_pending");assert(!enabled(`HSM_BAR_mtk_start_${p.id}_theory`,s));execute(effects[`HSM_BAR_mtk_start_${p.id}_theory_click`],s);assert.equal(s.calls.length,0);}
 });
 for(const p of projects.filter(p=>p.partners))test(p.id+": either faculty opens one dossier with the lead faculty's controls",()=>{
  for(const d of faculties(p)){
   const s=fresh(p);s.vars.HSM_BAR_mtk_department=Object.keys(departments).indexOf(d)+1;
   const button=`HSM_BAR_mtk_project_${p.id}_${d}`;assert(visible(button,s));execute(effects[button+"_click"],s);assert.equal(s.vars.HSM_BAR_mtk_project,p.number);
   assert.equal(choose("GetHSMBARMtkDocument",s),`HSM_BAR_mtk_${p.id}_idea`);
   execute(effects.HSM_BAR_mtk_protocol_click,s);assert.equal(s.vars.HSM_BAR_mtk_document,5);
   assert(scene(p,"english","proposal",5,{department:d}).widgets.some(w=>w.name===`HSM_BAR_mtk_${p.id}_prepare_rig_a`&&w.sprite===`GFX_HSM_BAR_mtk_experiment_${p.department}`));
   for(const faculty of Object.keys(departments))for(const choice of ["replication","instrumentation"]){
    const name=`HSM_BAR_mtk_policy_${faculty}_${choice}`;assert.equal(visible(name,s),faculty===p.department);
    s.calls=[];execute(effects[name+"_click"],s);assert.equal(s.calls.length,faculty===p.department?1:0);
   }
  }
 });
 for(const p of projects.filter(p=>p.opus))test(p.id+": origin dossier references exactly five earned conclusions across all subsets",()=>{
  const prep=preparations(p.department);assert.equal(prep.length,5);
  for(let mask=0;mask<32;mask++)for(const lang of ["english","russian"]){
   const s=fresh(p);execute(effects.HSM_BAR_mtk_origins_click,s);assert.equal(s.vars.HSM_BAR_mtk_document,6);
   for(const [i,q]of prep.entries())if(mask&(1<<i))s.flags.add(`HSM_BAR_mtk_${q.id}_done`);
   const body=expand("[GetHSMBARMtkOrigins]",s,lang);
   assert(!/\[Get|\$HSM_BAR_/.test(body));
   for(const [i,q]of prep.entries()){
    assert(body.includes(locales[lang][`HSM_BAR_mtk_${q.id}_title`]));
    assert.equal(body.includes(locales[lang][`HSM_BAR_mtk_${q.id}_conclusion`]),!!(mask&(1<<i)),q.id);
   }
   assert.equal(body.split(locales[lang].HSM_BAR_mtk_origin_pending).length-1,5-prep.filter((_,i)=>mask&(1<<i)).length);
   s.flags.delete("HSM_BAR_collegium");assert.equal(choose("GetHSMBARMtkOrigins",s),"HSM_BAR_mtk_document_pending");
  }
 });
 test("exactly two method controls per faculty highlight choices and lock on paid work",()=>{
  const names=widgets.filter(n=>n.key==="buttonType").map(n=>prop(n.value,"name"));
  assert.deepEqual(names.filter(name=>name.startsWith("HSM_BAR_mtk_policy_")).sort(),Object.keys(departments).flatMap(d=>["replication","instrumentation"].map(choice=>`HSM_BAR_mtk_policy_${d}_${choice}`)).sort());
  for(const lang of ["english","russian"])assert(!Object.keys(locales[lang]).some(key=>/^HSM_BAR_mtk_(?:application_|policy_(?:civilian|field)$)|_choose_(?:civilian|field)(?:_desc)?$/.test(key)));
  assert(!Object.keys(selectors).some(key=>key.startsWith("GetHSMBARMtkApplication_")));
  for(const d of Object.keys(departments))for(const instrumented of [false,true]){
   const p=projects.find(p=>p.department===d),s=fresh(p);s.vars.HSM_BAR_mtk_document=5;
   if(instrumented)s.flags.add(`HSM_BAR_mtk_${d}_instrumented`);
   s.flags.add(`HSM_BAR_mtk_${d}_civilian`);s.flags.add(`HSM_BAR_mtk_${d}_field`);
   assert(!visible("HSM_BAR_mtk_document",s));assert(!visible("HSM_BAR_mtk_accounting",s));
   for(const [choice,picked]of [["replication",!instrumented],["instrumentation",instrumented]]){
    const name=`HSM_BAR_mtk_policy_${d}_${choice}`;assert(visible(name,s));assert(enabled(name,s));
    assert.equal(choose(`GetHSMBARMtkPolicy_${d}_${choice}`,s),`GFX_HSM_BAR_mtk_experiment_${d}${picked?"_selected":""}`);
    s.flags.add(`HSM_BAR_mtk_${p.id}_trials_running`);assert(!enabled(name,s));s.flags.delete(`HSM_BAR_mtk_${p.id}_trials_running`);
   }
  }
 });
 test("narrative and laboratory questions preserve their exact writing-area bounds",()=>{
  for(const [name,x,y,w,h]of [["document",334,310,612,296],["rig_question",334,306,612,36],["control_question",334,400,612,36]]){
   const widget=widgets.find(n=>prop(n.value,"name")==="HSM_BAR_mtk_"+name).value;
   assert.deepEqual(prop(widget,"position"),parse(`x = ${x} y = ${y}`));
   assert.equal(Number(prop(widget,"maxWidth")),w);assert.equal(Number(prop(widget,"maxHeight")),h);
  }
 });
 test("instrumented howitzer report follows the paid method, never leaks early or changes the failed conclusion",()=>{
  const p=projects.find(p=>p.id==="revolver_howitzer"),s=fresh(p);s.vars.HSM_BAR_mtk_document=3;
  s.flags.add(`HSM_BAR_mtk_${p.id}_instrumented`);assert.equal(choose("GetHSMBARMtkDocument",s),"HSM_BAR_mtk_document_pending");
  s.flags.add(`HSM_BAR_mtk_${p.id}_done`);assert.equal(choose("GetHSMBARMtkDocument",s),"HSM_BAR_mtk_revolver_howitzer_tests_instrumented");
  s.flags.add("HSM_BAR_mtk_leopold_instrumented");s.flags.delete(`HSM_BAR_mtk_${p.id}_instrumented`);assert.equal(choose("GetHSMBARMtkDocument",s),"HSM_BAR_mtk_revolver_howitzer_tests");
  s.vars.HSM_BAR_mtk_document=4;assert.equal(choose("GetHSMBARMtkDocument",s),"HSM_BAR_mtk_revolver_howitzer_conclusion");
  for(const lang of ["english","russian"]){const prose=locales[lang].HSM_BAR_mtk_revolver_howitzer_tests_instrumented;assert(prose.split(/\s+/).length>=65);assert(!/\[|\$HSM_BAR_|§/.test(prose));}
 });
 test("running stage offers guarded cancellation instead of overlapping start controls",()=>{
  for(const p of projects)for(const stage of ["theory","trials"]){
   const s=fresh(p),name=`HSM_BAR_mtk_cancel_${p.id}_${stage}`;s.vars.HSM_BAR_mtk_document=5;assert(!visible(name,s));assert(!enabled(name,s));
   s.flags.add(`HSM_BAR_mtk_${p.id}_${stage}_running`);assert(visible(name,s));assert(enabled(name,s));assert(!visible(`HSM_BAR_mtk_start_${p.id}_${stage}`,s));
   execute(effects[name+"_click"],s);assert.deepEqual(s.calls,[`HSM_BAR_mtk_${p.id}_cancel_${stage}`]);
   s.flags.add(`HSM_BAR_mtk_${p.id}_done`);assert(!visible(name,s));s.calls=[];execute(effects[name+"_click"],s);assert.equal(s.calls.length,0);
  }
 });
 for(const p of projects)test(p.id+": two live trial budgets and one reward ignore old application flags",()=>{
  const id=`HSM_BAR_mtk_${p.id}`,dept=`HSM_BAR_mtk_${p.department}`;
  for(const lang of ["english","russian"]){
   assert.deepEqual(Object.keys(locales[lang]).filter(key=>key.startsWith(id+"_budget_")).sort(),[id+"_budget_instrumented",id+"_budget_replication"]);
   assert.deepEqual(Object.keys(locales[lang]).filter(key=>key.startsWith(id+"_effects")),[id+"_effects"]);
  }
  assert.deepEqual(selectors[`GetHSMBARMtkTrialBudget_${p.id}`].map(nodes=>prop(nodes,"localization_key")).sort(),[id+"_budget_instrumented",id+"_budget_replication"]);
  for(const instrumented of [false,true])for(let mask=0;mask<16;mask++){
   const s=fresh(p);s.vars.HSM_BAR_mtk_document=5;s.flags.add(id+"_theory");s.flags.add(id+"_rig_a");s.flags.add(id+"_control_a");
   if(p.opus)for(const q of preparations(p.department))s.flags.add(`HSM_BAR_mtk_${q.id}_done`);
   for(const q of p.prerequisites||[])s.flags.add(`HSM_BAR_mtk_${q}_done`);
   if(instrumented)s.flags.add(dept+"_instrumented");
   [dept+"_civilian",dept+"_field",id+"_civilian",id+"_field"].forEach((f,i)=>{if(mask&(1<<i))s.flags.add(f);});
   const method=instrumented?"instrumented":"replication";
   const budgetKey=`${id}_budget_${method}`,payment=instrumented?p.instrumentedCost:p.trialCost,days=instrumented?p.instrumentedDays:p.trialDays;
   assert.equal(choose(`GetHSMBARMtkTrialBudget_${p.id}`,s),budgetKey);
   for(const lang of ["english","russian"]){
    const tt=expand(id+"_start_trials_tt",s,lang),budget=expand(budgetKey,s,lang);
    assert(tt.startsWith(budget));assert.deepEqual(budget.match(/\d+/g).map(Number),[payment,days,factories(p,method)]);
    assert(tt.includes(expand("HSM_BAR_mtk_method_"+(instrumented?"instrumentation":"replication"),s,lang)));
    assert(!/\[Get/.test(tt));
   }
   const button=`HSM_BAR_mtk_start_${p.id}_trials`;
   s.pp=payment-0.01;assert(!enabled(button,s));s.pp=payment;assert(enabled(button,s));
   const required=(p.opus?2:1)+Number(instrumented);
   for(let count=0;count<required;count++){s.factories=count;assert(!enabled(button,s));}
   s.factories=required;assert(enabled(button,s));
   assert.equal(choose("GetHSMBARMtkEffects",s),"HSM_BAR_mtk_no_application");
   s.flags.add(id+"_done");assert.equal(choose("GetHSMBARMtkEffects",s),id+"_effects");
   // Department policy for the next project cannot rewrite a completed report.
   s.flags.delete(dept+"_civilian");s.flags.delete(dept+"_instrumented");
   assert.equal(choose("GetHSMBARMtkEffects",s),id+"_effects");
   s.flags.delete(id+"_civilian");s.flags.delete(id+"_field");assert.equal(choose("GetHSMBARMtkEffects",s),id+"_effects");
  }
 });
 for(const p of projects)test(p.id+": theory needs its exact base factory count under either trial method",()=>{
  for(const instrumented of [false,true])for(const department of faculties(p)){
   const s=fresh(p),button=`HSM_BAR_mtk_start_${p.id}_theory`;s.vars.HSM_BAR_mtk_document=5;
   s.vars.HSM_BAR_mtk_department=Object.keys(departments).indexOf(department)+1;
   if(p.opus)for(const q of preparations(p.department))s.flags.add(`HSM_BAR_mtk_${q.id}_done`);
   for(const q of p.prerequisites||[])s.flags.add(`HSM_BAR_mtk_${q}_done`);
   if(instrumented)s.flags.add(`HSM_BAR_mtk_${p.department}_instrumented`);
   s.flags.add(`HSM_BAR_mtk_${p.department}_civilian`);s.flags.add(`HSM_BAR_mtk_${p.id}_field`);
   const required=p.opus?2:1;
   s.pp=p.theoryCost-0.01;assert(!enabled(button,s));s.pp=p.theoryCost;
   for(let count=0;count<required;count++){s.factories=count;assert(!enabled(button,s));}
   s.factories=required;assert(enabled(button,s));
   for(const lang of ["english","russian"]){
    const tooltip=expand(`HSM_BAR_mtk_${p.id}_start_theory_tt`,s,lang);
    assert.deepEqual(tooltip.match(/\d+/g).slice(0,3).map(Number),[p.theoryCost,p.theoryDays,required]);
   }
  }
 });
 test("every button has a handler; 52 starts delegate only to guarded backend effects",()=>{
  for(const n of widgets.filter(x=>x.key==="buttonType")){const name=prop(n.value,"name");if(name.includes("_input_"))continue;assert(effects[name+"_click"],name);assert(prop(n.value,"pdx_tooltip"),name);}
  for(const p of projects)for(const st of ["theory","trials"]){const operation=st==="theory"?"start_theory":"begin_experiment",key=`HSM_BAR_mtk_${p.id}_${operation}`,start=backend[key];assert(start,key);assert(prop(prop(start,"if"),"limit").some(n=>n.key===`HSM_BAR_mtk_${p.id}_can_${st==="theory"?"theory":"begin_experiment"}`));const s=fresh(p);s.vars.HSM_BAR_mtk_document=5;execute(effects[`HSM_BAR_mtk_start_${p.id}_${st}_click`],s);assert.deepEqual(s.calls,[key]);}
 });
 test("all 26 projects, protocols and origins preserve hitboxes and writing-area bounds",()=>{
  for(const p of projects)for(const lang of ["english","russian"])for(const d of p.opus?[1,2,3,4,5,6,7]:[1,2,3,4,5,7]){
   const draw=scene(p,lang,"done",d).widgets.filter(x=>!x.name.includes("_input_"));
   assert.equal(draw.filter(x=>/^HSM_BAR_mtk_project_\w+$/.test(x.name)&&x.kind==="buttonType").length,7);
   for(const a of draw){assert(a.x>=20&&a.x+a.w<=980&&a.y>=20&&a.y+a.h<=680,a.name);if(a.x>=300&&a.y>=160)assert(a.x>=334&&a.x+a.w<=946&&a.y>=184&&a.y+a.h<=654,a.name+": outside flat paper");}
   for(const a of draw.filter(a=>a.x<300&&a.y>=160))assert(a.y+a.h<=506,a.name+": overlaps faculty apparatus");
   for(let i=0;i<draw.length;i++)for(let j=i+1;j<draw.length;j++){const a=draw[i],b=draw[j];assert(!(a.x<b.x+b.w&&b.x<a.x+a.w&&a.y<b.y+b.h&&b.y<a.y+a.h),`${a.name} overlaps ${b.name}`);}
  }
 });
 test("laboratory and ledger navigation are separate; narrative pages never contain inline rewards",()=>{
  assert.equal(locales.english.HSM_BAR_mtk_protocol,"Laboratory");
  const ledger=widgets.find(n=>prop(n.value,"name")==="HSM_BAR_mtk_ledger");assert.equal(ledger.key,"buttonType");
  assert.deepEqual(prop(ledger.value,"position"),parse("x = 910 y = 222"));assert.deepEqual(dimensions(prop(ledger.value,"quadTextureSprite")),{w:32,h:32});
  assert(!widgets.some(n=>prop(n.value,"name")==="HSM_BAR_mtk_effects"));
  for(const p of projects)for(const lang of ["english","russian"]){
   const s=fresh(p);execute(effects.HSM_BAR_mtk_protocol_click,s);assert.equal(s.vars.HSM_BAR_mtk_document,5);
   execute(effects.HSM_BAR_mtk_ledger_click,s);assert.equal(s.vars.HSM_BAR_mtk_document,7);
   assert(visible("HSM_BAR_mtk_accounting",s));assert(!visible("HSM_BAR_mtk_document",s));
   for(const stage of ["proposal","done"]){
    const shown=scene(p,lang,stage,7).widgets,accounting=shown.find(w=>w.name==="HSM_BAR_mtk_accounting");assert(accounting?.scroll);
    if(stage==="done"){
     assert(accounting.text.includes(locales[lang][`HSM_BAR_mtk_${p.id}_effects`]));
     assert(!/political power|политической власти/.test(accounting.text),"Completed ledger must not quote a new contract");
    }else for(const amount of [p.theoryCost,p.theoryDays,p.trialCost,p.trialDays])assert(accounting.text.includes(String(amount)));
    for(const w of shown)assert(!/^HSM_BAR_mtk_(start|cancel)_/.test(w.name));
   }
   for(const doc of [1,2,3,4])for(const w of scene(p,lang,"done",doc).widgets.filter(w=>w.x>=300&&w.y>=310&&w.kind==="instantTextboxType"))
    assert(!/%|\[GetHSMBARMtkEffects\]|political power|политическ.{0,10}власти/i.test(w.text),w.name+": inline accounting");
  }
 });
 test("all new choice controls are preview-compatible buttons with stable 294 by 40 skins",()=>{
  for(const d of Object.keys(departments))for(const suffix of ["","_selected"])assert.deepEqual(dimensions(`GFX_HSM_BAR_mtk_experiment_${d}${suffix}`),{w:294,h:40});
  for(const p of projects)for(const operation of ["prepare_rig_a","prepare_rig_b","prepare_control_a","prepare_control_b","respond_a","respond_b"]){
   const name=`HSM_BAR_mtk_${p.id}_${operation}`,widget=widgets.find(n=>prop(n.value,"name")===name);assert(widget,name);assert.equal(widget.key,"buttonType");
   if(operation.startsWith("prepare_"))assert(properties[name],name);
   assert.deepEqual(dimensions(prop(widget.value,"quadTextureSprite")),{w:294,h:40});assert(effects[name+"_click"],name);assert(prop(widget.value,"pdx_tooltip"),name);
   const pos=prop(widget.value,"position");assert.equal(Number(prop(pos,"x")),operation.endsWith("_a")?334:652);
   assert.equal(Number(prop(pos,"y")),operation.startsWith("prepare_rig")?344:operation.startsWith("prepare_control")?438:528);
  }
  for(const d of Object.keys(departments))for(const choice of ["replication","instrumentation"]){const w=widgets.find(n=>prop(n.value,"name")===`HSM_BAR_mtk_policy_${d}_${choice}`);assert.equal(Number(prop(prop(w.value,"position"),"y")),528);}
 });
 for(const p of projects)test(p.id+": preparation selection is explicit; action controls exist only on laboratory page",()=>{
  const id=`HSM_BAR_mtk_${p.id}`,s=sceneState(p,"theory",5);
  if(p.opus)for(const q of preparations(p.department))s.flags.add(`HSM_BAR_mtk_${q.id}_done`);
  for(const q of p.prerequisites||[])s.flags.add(`HSM_BAR_mtk_${q}_done`);
  assert(!enabled(`HSM_BAR_mtk_start_${p.id}_trials`,s));
  for(const axis of ["rig","control"]){
   for(const option of ["a","b"]){
    const name=`${id}_prepare_${axis}_${option}`;assert(visible(name,s));assert(enabled(name,s));
    assert.equal(choose(`GetHSMBARMtkChoice_${p.id}_${axis}_${option}`,s),`GFX_HSM_BAR_mtk_experiment_${p.department}`);
    s.calls=[];execute(effects[name+"_click"],s);assert.deepEqual(s.calls,[name]);
   }
   s.flags.add(id+"_"+axis+"_a");assert.equal(enabled(`HSM_BAR_mtk_start_${p.id}_trials`,s),axis==="control");
  }
  for(const document of [1,2,3,4,6,7])for(const stage of ["theory","trials"]){
   const other=structuredClone(s);other.vars.HSM_BAR_mtk_document=document;
   for(const operation of ["start","cancel"]){
    if(operation==="cancel")other.flags.add(`${id}_${stage}_running`);
    const name=`HSM_BAR_mtk_${operation}_${p.id}_${stage}`;assert(!visible(name,other));assert(!enabled(name,other));
    other.calls=[];execute(effects[name+"_click"],other);assert.deepEqual(other.calls,[]);
   }
  }
  for(const stage of ["prepared","observing","checkpoint","verifying","experiment_done"]){
   const other=sceneState(p,stage,5,{combo:3});
   for(const axis of ["rig","control"])for(const option of ["a","b"]){
    const name=`${id}_prepare_${axis}_${option}`;assert.equal(visible(name,other),["prepared","observing"].includes(stage));
    if(stage!=="prepared")assert(!enabled(name,other));
   }
   for(const response of ["a","b"])assert.equal(visible(`${id}_respond_${response}`,other),stage==="checkpoint");
  }
 });
 for(const p of projects)test(p.id+": every new UI handler blocks foreign, closed, wrong-project and wrong-page dispatch",()=>{
  for(const operation of ["prepare_rig_a","prepare_rig_b","prepare_control_a","prepare_control_b","respond_a","respond_b"]){
   const name=`HSM_BAR_mtk_${p.id}_${operation}`;
   for(const mutate of [s=>s.tag="WIT",s=>s.ai=true,s=>delete s.vars.HSM_BAR_mtk_open,s=>s.vars.HSM_BAR_mtk_project=0,s=>s.vars.HSM_BAR_mtk_department=0,
    ...[1,2,3,4,6,7].map(d=>s=>s.vars.HSM_BAR_mtk_document=d)]){
    const s=sceneState(p,operation.startsWith("respond")?"checkpoint":"prepared",5);mutate(s);
    assert(!visible(name,s));assert(!enabled(name,s));execute(effects[name+"_click"],s);assert.deepEqual(s.calls,[]);
   }
  }
 });
 for(const p of projects)for(let combo=0;combo<4;combo++)for(const response of ["a","b"])test(`${p.id}/${combo}/${response}: observation, ordered verification and final report disclosure`,()=>{
  const id=`HSM_BAR_mtk_${p.id}`,data=experiments.find(e=>e.id===p.id),r=data.responses[response==="a"?0:1];
  for(const [index,lang]of ["english","russian"].entries()){
   const s=sceneState(p,"observing",3,{combo,response});assert(!enabled("HSM_BAR_mtk_doc_3",s));assert.equal(choose("GetHSMBARMtkDocument",s),"HSM_BAR_mtk_document_pending");
   for(const stage of ["checkpoint","verifying","experiment_done"]){
    const state=sceneState(p,stage,3,{combo,response});
    const key=stage==="checkpoint"?`${id}_observation_${combo}`:stage==="verifying"?`${id}_verification_${response}_${combo}`:`${id}_experiment_report_${response}_${combo}`;
    assert(enabled("HSM_BAR_mtk_doc_3",state));assert.equal(choose("GetHSMBARMtkLabRecord",state),key);
    assert.equal(choose("GetHSMBARMtkDocument",state),"HSM_BAR_mtk_experiment_document");
    const text=expand("[GetHSMBARMtkDocument]",state,lang);assert(text.includes(data.observations[combo][index]));
    assert.equal(text.includes(r.reports[combo][index]),stage==="experiment_done");
    if(stage==="verifying"){assert(text.includes(r.label[index]));assert(text.includes(r.note[index]));}
    if(stage==="experiment_done")for(const [axis,j]of [["rig",combo>>1],["control",combo&1]])assert(text.includes(data[axis].options[j].label[index]));
    assert(!/\[Get|\$HSM_BAR_|§|%/.test(text));
    state.vars.HSM_BAR_mtk_document=4;assert.equal(enabled("HSM_BAR_mtk_doc_4",state),stage==="experiment_done");
    assert.equal(choose("GetHSMBARMtkDocument",state),stage==="experiment_done"?id+"_conclusion":"HSM_BAR_mtk_document_pending");
    // Paid parameters remain authoritative after live apparatus selections change.
    for(const axis of ["rig","control"]){state.flags.delete(id+"_"+axis+"_a");state.flags.delete(id+"_"+axis+"_b");state.flags.add(id+"_"+axis+"_"+((combo&(axis==="rig"?2:1))?"a":"b"));}
    assert.equal(choose("GetHSMBARMtkLabRecord",state),key);
    state.tag="WIT";assert.equal(choose("GetHSMBARMtkLabRecord",state),"HSM_BAR_mtk_document_pending");
   }
   const state=sceneState(p,"checkpoint",5,{combo,response}),button=`${id}_respond_${response}`;
   assert.equal(choose(`GetHSMBARMtkResponseBudget_${p.id}_${response}`,state),`${id}_response_${response}_${combo}_budget`);
   const tooltip=expand(button+"_tt",state,lang);assert(tooltip.includes(r.note[index]));assert(tooltip.includes(String(r.cost[combo])));assert(tooltip.includes(String(r.days[combo])));
   state.pp=r.cost[combo]-0.01;assert(!enabled(button,state));state.pp=r.cost[combo];assert(enabled(button,state));
   state.calls=[];execute(effects[button+"_click"],state);assert.deepEqual(state.calls,[button]);
  }
 });
 test("all bilingual experiment questions, choices and 208 reports fit or use their bounded native scrollbars",()=>{
  const checked=new Set();let completed=0;
  for(const p of projects)for(const lang of ["english","russian"])for(let combo=0;combo<4;combo++)for(const response of ["a","b"]){
   for(const stage of ["prepared","observing","checkpoint","verifying","experiment_done"])for(const document of [3,5,7]){
    const draw=scene(p,lang,stage,document,{combo,response}).widgets.filter(w=>!w.name.includes("_input_"));
    for(const a of draw){assert(a.x>=20&&a.x+a.w<=980&&a.y>=20&&a.y+a.h<=680,a.name);if(a.x>=300&&a.y>=160)assert(a.x>=334&&a.x+a.w<=946&&a.y>=184&&a.y+a.h<=654,a.name);}
    for(let i=0;i<draw.length;i++)for(let j=i+1;j<draw.length;j++){const a=draw[i],b=draw[j];assert(!(a.x<b.x+b.w&&b.x<a.x+a.w&&a.y<b.y+b.h&&b.y<a.y+a.h),`${p.id}/${stage}/${document}: ${a.name} overlaps ${b.name}`);}
    for(const w of draw.filter(w=>w.text&&w.font)){
     const key=JSON.stringify([lang,w.name,w.text,w.font,w.w,w.h]);if(checked.has(key))continue;checked.add(key);
     const width=w.w-(w.kind==="buttonType"?16:0),height=textHeight(w.text,nativeFont(w.font,lang),width,`${p.id}/${lang}/${stage}/${w.name}`,!w.scroll);
     if(!w.scroll)assert(height<=w.h,`${p.id}/${lang}/${stage}/${w.name}: ${height}px text in ${w.h}px box`);
     else assert(["HSM_BAR_mtk_document","HSM_BAR_mtk_lab_record","HSM_BAR_mtk_accounting","HSM_BAR_mtk_observation"].includes(w.name),w.name);
    }
    if(stage==="experiment_done"&&document===3){const body=draw.find(w=>w.name==="HSM_BAR_mtk_document");assert(body.scroll);assert.equal(body.h,296);completed++;}
   }
  }
  assert.equal(completed,26*4*2*2);
 });
 test("all skins are local nonblank 32-bit textures; unique backgrounds and equal selection dimensions",()=>{
  const hashes=new Set();for(const d of Object.keys(departments)){const b=assets.sprites[`GFX_HSM_BAR_mtk_${d}`];assert.equal(field(b,"effectFile"),"gfx/FX/static_button.lua");const bytes=fs.readFileSync(path.join(mod,field(b,"texturefile"))),im=readTga(bytes);assert.deepEqual([im.w,im.h],[1000,700]);hashes.add(require("node:crypto").createHash("sha256").update(bytes).digest("hex"));
   for(const role of ["dept","project"]){const ids=[`GFX_HSM_BAR_mtk_${role}_${d}`,`GFX_HSM_BAR_mtk_${role}_${d}_selected`];assert.deepEqual(spriteDimensions(assets.sprites,ids[0]),{w:228,h:36});assert.deepEqual(spriteDimensions(assets.sprites,ids[1]),{w:228,h:36});assert.notEqual(field(assets.sprites[ids[0]],"texturefile"),field(assets.sprites[ids[1]],"texturefile"));}
  }assert.equal(hashes.size,4);
 });
 test("208 substantive bilingual document pages, no redactions or mod-manual prose",()=>{
  const sets=[];for(const lang of ["english","russian"]){const keys=[];for(const p of projects)for(const st of ["idea","theory","tests","conclusion"]){const key=`HSM_BAR_mtk_${p.id}_${st}`,t=locales[lang][key];assert(t,key);assert(t.split(/\s+/).length>=65,key+": placeholder prose");assert(!/HSM_BAR_|\[REDACTED\]|\[УДАЛЕНО\]|£HSM_BAR_redact|§|political power|политическ.{0,10}власти/i.test(t),key);keys.push(key);}sets.push(keys);for(const file of fs.readdirSync(path.join(mod,"localisation",lang)).filter(x=>x.startsWith("HSM_BAR_mtk_"))){assert.deepEqual([...fs.readFileSync(path.join(mod,"localisation",lang,file)).subarray(0,3)],[239,187,191],file);}}
  assert.deepEqual(sets[0],sets[1]);
 });
 test("all 32 sprites have opaque artwork, native state shaders and visibly distinct selections",()=>{
  const names=Object.keys(assets.sprites).filter(n=>n.startsWith("GFX_HSM_BAR_mtk_"));assert.equal(names.length,32);
  const texture=name=>readTga(fs.readFileSync(path.join(mod,field(assets.sprites[name],"texturefile"))),name);
  for(const name of names){const b=assets.sprites[name],im=texture(name);assertArtwork(im,name);assert.equal(Number(field(b,"noOfFrames")??1),1);
   assert.equal(field(b,"effectFile"),Object.keys(departments).some(d=>name==="GFX_HSM_BAR_mtk_"+d)?"gfx/FX/static_button.lua":"gfx/FX/buttonstate.lua");
   if(name.endsWith("_selected"))assertDistinct(texture(name.slice(0,-9)),im,name);
  }
 });
 test("both language fonts remain readable on every department paper and project button",()=>{
  for(const lang of ["english","russian"])for(const d of Object.keys(departments)){
   const name="GFX_HSM_BAR_mtk_"+d,im=readTga(fs.readFileSync(path.join(mod,field(assets.sprites[name],"texturefile"))),name);
   const ink=fontColor(fontDefinition(assets.fonts,"HSM_BAR_archive_body",lang));
   assertContrast(im,{x:334,y:310,w:612,h:296},{ink},d+" document/"+lang);
   const white=fontColor(fontDefinition(assets.fonts,"hoi_16mbs",lang));
   for(const suffix of ["","_selected"]){const sprite=assets.sprites[`GFX_HSM_BAR_mtk_project_${d}${suffix}`],button=readTga(fs.readFileSync(path.join(mod,field(sprite,"texturefile"))));assertContrast(button,{x:8,y:8,w:212,h:20},{white},d+" project/"+suffix,false);}
  }
 });
 console.log(`Barrad Collegium menu: ${passed} groups passed; ${failed} failed. Native rendering and input remain unverified.`);process.exitCode=failed?1:0;
}
