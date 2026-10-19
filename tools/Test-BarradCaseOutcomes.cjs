"use strict";

// Uses the existing narrow Clausewitz fixture; this is not an HOI4 engine test.
const fs = require("node:fs");
const path = require("node:path");
const assert = require("node:assert/strict");
const F = require("./Test-BarradCases.cjs");
const { read, prop, dictionary, world, access, flag, has, effect, test, parse, mod, run } = F;
const expected = {
  "rock": {
    "cost": 15,
    "applied": {
      "infra": 0.04,
      "supply": 0.01
    },
    "reserved": {
      "dig": 1,
      "pp": -0.01
    },
    "physical": true,
    "terminal": {
      "protect": {
        "infra": 0.02,
        "pp": -0.015
      },
      "restrict": {
        "dig": 1,
        "build": -0.01
      }
    }
  },
  "titan": {
    "cost": 20,
    "applied": {
      "factory": 0.025,
      "efficiency": -0.02
    },
    "reserved": {
      "efficiency": 0.015
    },
    "physical": true,
    "terminal": {
      "protect": {
        "efficiency": 0.02,
        "pp": -0.02
      },
      "restrict": {
        "stability": 0.01,
        "factory": -0.01
      }
    }
  },
  "entity": {
    "cost": 25,
    "applied": {
      "research": 0.01,
      "stability": -0.01
    },
    "reserved": {
      "stability": 0.005,
      "pp": -0.015
    },
    "physical": true,
    "terminal": {
      "protect": {
        "research": 0.01,
        "pp": -0.025
      },
      "restrict": {
        "stability": 0.015,
        "research": -0.005
      }
    }
  },
  "amulet": {
    "cost": 15,
    "applied": {
      "defence": 0.015,
      "pp": -0.02
    },
    "reserved": {
      "stability": 0.015,
      "build": -0.005
    },
    "physical": true,
    "terminal": {
      "protect": {
        "stability": 0.02,
        "pp": -0.02
      },
      "restrict": {
        "defence": 0.015,
        "stability": -0.005
      }
    }
  },
  "plants": {
    "cost": 15,
    "applied": {
      "resources": 0.025,
      "recovery": -0.01
    },
    "reserved": {
      "recovery": 0.015,
      "resources": -0.01
    },
    "physical": true,
    "terminal": {
      "protect": {
        "resources": 0.03,
        "supply": -0.01,
        "pp": -0.02
      },
      "restrict": {
        "recovery": 0.015,
        "resources": -0.015
      }
    }
  },
  "reactor": {
    "cost": 30,
    "applied": {
      "factory": 0.035,
      "stability": -0.015
    },
    "reserved": {
      "factory": -0.01,
      "efficiency": 0.025
    },
    "physical": true,
    "terminal": {}
  },
  "crown": {
    "cost": 25,
    "applied": {
      "reinforce": 0.005,
      "stability": -0.02
    },
    "reserved": {
      "stability": 0.01,
      "pp": -0.01
    },
    "physical": true,
    "terminal": {}
  },
  "chalice": {
    "cost": 20,
    "applied": {
      "recovery": 0.025,
      "pp": -0.025
    },
    "reserved": {
      "supply": -0.01,
      "research": -0.002
    },
    "physical": true,
    "terminal": {
      "sealed": {
        "supply": -0.01,
        "research": -0.002
      }
    }
  },
  "phylactery": {
    "cost": 25,
    "applied": {
      "research": 0.015,
      "stability": -0.015
    },
    "reserved": {
      "stability": 0.01,
      "factory": -0.005
    },
    "physical": true,
    "terminal": {
      "sealed": {
        "stability": 0.01,
        "factory": -0.005
      }
    }
  },
  "darkheart": {
    "cost": 30,
    "applied": {
      "decrypt": 0.05,
      "stability": -0.02
    },
    "reserved": {
      "defence": 0.005,
      "pp": -0.02
    },
    "physical": true,
    "terminal": {
      "sealed": {
        "defence": 0.005,
        "pp": -0.02
      }
    }
  },
  "grover": {
    "cost": 15,
    "applied": {
      "recon": 0.02,
      "pp": -0.015
    },
    "reserved": {
      "planning": 0.015
    },
    "physical": false,
    "terminal": {
      "reviewed": {
        "recon": 0.02
      }
    }
  },
  "rosa": {
    "cost": 15,
    "applied": {
      "research": 0.007,
      "pp": -0.02
    },
    "reserved": {
      "decrypt": 0.015
    },
    "physical": false,
    "terminal": {
      "reviewed": {
        "research": 0.007
      }
    }
  },
  "herald": {
    "cost": 20,
    "applied": {
      "research": 0.01,
      "efficiency": -0.01
    },
    "reserved": {
      "defence": 0.005
    },
    "physical": false,
    "terminal": {
      "reviewed": {
        "research": 0.01
      }
    }
  },
  "sombra": {
    "cost": 20,
    "applied": {
      "defence": 0.015,
      "supply": 0.01
    },
    "reserved": {
      "stability": 0.01
    },
    "physical": false,
    "terminal": {
      "reviewed": {
        "defence": 0.015
      }
    }
  },
  "echo": {
    "cost": 10,
    "applied": {
      "infra": 0.03
    },
    "reserved": {
      "dig": 1
    },
    "physical": false,
    "terminal": {}
  },
  "marsh": {
    "cost": 10,
    "applied": {
      "supply": -0.02
    },
    "reserved": {
      "recovery": 0.01
    },
    "physical": false,
    "terminal": {}
  },
  "compass": {
    "cost": 10,
    "applied": {
      "recon": 0.03
    },
    "reserved": {
      "planning": 0.02
    },
    "physical": false,
    "terminal": {}
  }
};
const modifierNames = {
  "infra": "production_speed_infrastructure_factor",
  "supply": "supply_consumption_factor",
  "dig": "max_dig_in",
  "pp": "political_power_gain",
  "factory": "industrial_capacity_factory",
  "efficiency": "production_factory_efficiency_gain_factor",
  "research": "research_speed_factor",
  "stability": "stability_factor",
  "defence": "army_defence_factor",
  "build": "production_speed_buildings_factor",
  "resources": "local_resources_factor",
  "recovery": "army_org_regain",
  "reinforce": "land_reinforce_rate",
  "decrypt": "decryption_power_factor",
  "recon": "recon_factor",
  "planning": "planning_speed"
};
const totals = w => Object.fromEntries(Object.keys(modifierNames).map(k => [k, w.root.vars["HSM_BAR_outcome_" + k] || 0]));
function expectTotals(w, wanted) {
    for (const k of Object.keys(modifierNames)) assert(Math.abs(totals(w)[k] - (wanted[k] || 0)) < 1e-9, k + ": " + totals(w)[k] + " != " + (wanted[k] || 0));
    const cached = w.root.modifierCache.HSM_BAR_anomalous_research;
    if (w.root.modifiers.has("HSM_BAR_anomalous_research")) {
        assert(cached, "Installed outcome modifier has no cached values");
        for (const [k, name] of Object.entries(modifierNames)) {
            assert(Math.abs(cached[name] - (wanted[k] || 0)) < 1e-9, "Stale cached outcome: " + name);
        }
    } else assert.equal(cached, undefined, "Removed outcome modifier retained cached bonuses");
}
function prepared(id) {
    const w = world(); access(w,id); effect("HSM_BAR_cases_" + id + "_complete",w);
    assert(has(w,"study_" + id + "_done")); return w;
}
const refresh = w => effect("HSM_BAR_refresh_case_outcomes",w);
const choose = (w,id,mode) => effect("HSM_BAR_cases_" + id + "_" + (mode === "applied" ? "apply" : "reserve"), w);
const loc = {};
for (const lang of ["english","russian"]) {
    loc[lang] = {};
    for (const stem of ["HSM_BAR_case_outcomes","HSM_BAR_cases"]) {
        const bytes = fs.readFileSync(path.join(mod,"localisation",lang,stem + "_l_" + lang + ".yml"));
        assert.equal(bytes.subarray(0,3).toString("hex"),"efbbbf");
        for (const line of bytes.toString("utf8").split(/\r?\n/).slice(1).filter(s=>s.trim())) {
            const match = line.match(/^ ([^ :]+):0 "(.*)"$/); assert(match,line);
            assert(!Object.hasOwn(loc[lang],match[1]),"Duplicate " + match[1]); loc[lang][match[1]] = match[2];
        }
    }
}
const getters = Object.fromEntries(read("common/scripted_localisation/HSM_BAR_case_outcomes.txt").map(n=>[prop(n.value,"name"),n.value.filter(x=>x.key==="text").map(x=>x.value)]));
function selected(name,w) {
    assert(getters[name],name);
    const choice = getters[name].find(c=>!prop(c,"trigger") || test(prop(c,"trigger"),w));
    assert(choice,"No fallback " + name); return prop(choice,"localization_key");
}
function renderKey(key,w,lang="english",depth=0) {
    assert(depth<16,"Recursive localization " + key); assert(Object.hasOwn(loc[lang],key),"Missing " + key);
    return loc[lang][key].replace(/\$([^$]+)\$/g,(_,k)=>renderKey(k,w,lang,depth+1)).replace(/\[ROOT\.(GetHSMBAR\w+)\]/g,(_,g)=>renderKey(selected(g,w),w,lang,depth+1));
}
const panel = (id,w,lang) => renderKey(selected("GetHSMBAROutcome_" + id,w),w,lang);
const labels = {
    english: {
        infra: "Infrastructure construction speed", supply: "Supply consumption", dig: "Maximum entrenchment",
        pp: "Daily political power", factory: "Factory output", efficiency: "Production efficiency growth",
        research: "Research speed", stability: "Stability", defence: "Division defence", build: "Construction speed",
        resources: "Resource gain efficiency", recovery: "Division recovery rate", reinforce: "Reinforce rate",
        decrypt: "Decryption power", recon: "Reconnaissance", planning: "Planning speed"
    },
    russian: {
        infra: "Скорость строительства инфраструктуры", supply: "Расход припасов", dig: "Максимальная укреплённость",
        pp: "Политическая власть в день", factory: "Объём заводского производства", efficiency: "Рост эффективности производства",
        research: "Темпы исследований", stability: "Стабильность", defence: "Защита дивизий", build: "Скорость строительства",
        resources: "Эффективность увеличения ресурсов", recovery: "Скорость восстановления организации дивизий", reinforce: "Скорость пополнения",
        decrypt: "Мощность дешифрования", recon: "Разведка", planning: "Скорость планирования"
    }
};
const visible = text => text.replace(/§[GRY!]/g, "");
const lines = text => text.split("\\n");
function resultSections(id, w, lang) {
    const text = panel(id, w, lang);
    const currentHeading = loc[lang].HSM_BAR_outcome_current;
    const historyHeading = loc[lang].HSM_BAR_outcome_history;
    assert.equal(text.split(currentHeading).length, 2, "Exactly one current-effects section");
    const [current, history] = text.split(currentHeading + "\\n")[1].split("\\n\\n" + historyHeading + "\\n");
    return { text, current, history };
}
function expectPresentation(id, w, wanted, lang) {
    const result = resultSections(id, w, lang);
    const expectedLines = Object.entries(wanted).map(([k, v]) => {
        const flat = ["pp", "dig"].includes(k);
        const number = Number((v * (flat ? 1 : 100)).toFixed(3));
        const color = (k === "supply" ? v < 0 : v > 0) ? "G" : "R";
        return labels[lang][k] + ": §" + color + (v > 0 ? "+" : "") + number + (flat ? "" : "%") + "§!";
    });
    assert.deepEqual(lines(result.current), expectedLines.length ? expectedLines : [loc[lang].HSM_BAR_outcome_zero], id + " / " + lang + " exact visible contribution");
    assert(!/[\[\]$]/.test(result.text), "Unresolved localization");
    assert(!/one-time|included once|stack|\bno (?:research|additional|separate).*bonus|replaces|current rules|legacy|contribut|разов|замен|вклад|текущим правилам|бонус.*нет/i.test(result.text), "Accounting prose in Results");
    const rows = lines(result.text);
    assert(rows.length <= 12, "Results exceed the compact document line budget");
    assert(!result.text.includes("\\n\\n\\n"), "Redundant blank rows");
    for (const row of rows) {
        assert(visible(row).length <= 70, "Overlong Results row: " + visible(row));
        let open = false;
        for (const match of row.matchAll(/§(.)/g)) {
            assert("GRY!".includes(match[1]), "Unsupported Results color");
            if (match[1] === "!") { assert(open, "Unmatched color reset"); open = false; }
            else { assert(!open, "Nested color without reset"); open = true; }
        }
        assert(!open, "Color leaks into the next row");
        assert(!visible(row).includes("§"), "Malformed color escape");
    }
    return result;
}
function finalFlag(id, mode) {
    return "case_" + id + "_" + (["sealed", "reviewed"].includes(mode) ? "closed" : mode);
}
let passed=0,failed=0;
function scenario(name,fn){try{fn();passed++;console.log("PASS: "+name);}catch(e){failed++;console.error("FAIL: "+name+"\n"+e.stack);}}
for(const [id,d] of Object.entries(expected)){
    for(const mode of ["applied","reserved"]){
        scenario(id + " / " + mode + ": exact contribution, once-only payment and idempotent refresh",()=>{
            const w=prepared(id), custody=JSON.stringify({flags:[...w.flags],crowns:w.crowns.map(c=>({flags:[...c.flags],vars:c.vars})),vars:w.vars});
            choose(w,id,mode); expectTotals(w,d[mode]);
            assert(has(w,"study_"+id+"_"+mode)); assert(has(w,"outcome_"+id+"_recorded"));
            assert.equal(w.root.pp,mode==="applied"?200-d.cost:200); assert(!Object.hasOwn(w.root.vars,"HSM_BAR_cover_integrity")); assert.equal(w.root.bonuses.length,0);
            assert(w.root.modifiers.has("HSM_BAR_anomalous_research"));
            const frozen=JSON.stringify(totals(w)),pp=w.root.pp;
            const installs=w.root.modifierInstalls.HSM_BAR_anomalous_research;
            for(let i=0;i<5;i++){refresh(w);choose(w,id,mode);choose(w,id,mode==="applied"?"reserved":"applied");}
            assert.equal(JSON.stringify(totals(w)),frozen); assert.equal(w.root.pp,pp); assert(!Object.hasOwn(w.root.vars,"HSM_BAR_cover_integrity"));
            assert.equal(w.root.modifierInstalls.HSM_BAR_anomalous_research,installs,"Refresh reinstalled an existing modifier");
            assert.equal(JSON.stringify({flags:[...w.flags],crowns:w.crowns.map(c=>({flags:[...c.flags],vars:c.vars})),vars:w.vars}),custody,"Policy touched native custody");
            for(const lang of ["english","russian"]){
                const text=panel(id,w,lang); assert(!/\[ROOT\.|\$HSM_/.test(text));
                assert.equal(selected("GetHSMBAROutcomeStatus_"+id,w),"HSM_BAR_outcome_active");
                for(const[k,v]of Object.entries(d[mode])){
                    const number=Number((v*(["dig","pp"].includes(k)?1:100)).toFixed(3)).toString();
                    assert(text.includes(number),lang+" missing "+k+" "+number);
                }
            }
        });
        scenario(id + " / " + mode + ": access loss, recovery and dissolution retain history",()=>{
            const w=prepared(id);choose(w,id,mode);
            w.states[624].controller="YAL";refresh(w);
            expectTotals(w,d.physical?{}:d[mode]);
            assert.equal(selected("GetHSMBAROutcomeStatus_"+id,w),d.physical?"HSM_BAR_outcome_suspended":"HSM_BAR_outcome_active");
            w.states[624].controller="BAR";refresh(w);expectTotals(w,d[mode]);
            for(const f of ["active","directorate","service_founded"]){
                w.root.flags.delete("HSM_BAR_"+f);refresh(w);expectTotals(w,{});
                assert(!w.root.modifiers.has("HSM_BAR_anomalous_research")); assert(has(w,"study_"+id+"_"+mode));
                assert.equal(selected("GetHSMBAROutcomeStatus_"+id,w),"HSM_BAR_outcome_suspended");
                flag(w,f);refresh(w);expectTotals(w,d[mode]);
            }
            w.root.capitulated=true;refresh(w);expectTotals(w,{});assert(!w.root.modifiers.has("HSM_BAR_anomalous_research"));
            w.root.capitulated=false;refresh(w);expectTotals(w,d[mode]);
            assert.equal(w.root.pp,mode==="applied"?200-d.cost:200);assert(!Object.hasOwn(w.root.vars,"HSM_BAR_cover_integrity"));
        });
    }
    scenario(id + ": incomplete research, legacy flags and policy costs",()=>{
        const w=world();access(w,id);
        choose(w,id,"applied");choose(w,id,"reserved");refresh(w);expectTotals(w,{});assert.equal(w.root.pp,200);assert(!Object.hasOwn(w.root.vars,"HSM_BAR_cover_integrity"));
        assert.equal(selected("GetHSMBAROutcome_"+id,w),"HSM_BAR_outcome_no_result");
        flag(w,"study_"+id+"_applied");refresh(w);expectTotals(w,{});
        flag(w,"study_"+id+"_done");refresh(w);expectTotals(w,d.applied);
        assert.equal(selected("GetHSMBAROutcomeHistory_"+id,w),"HSM_BAR_outcome_legacy_cost");
        assert.equal(w.root.pp,200);assert(!Object.hasOwn(w.root.vars,"HSM_BAR_cover_integrity"));assert.equal(w.root.bonuses.length,0);
        const poor=prepared(id);poor.root.pp=d.cost-1;choose(poor,id,"applied");assert(!has(poor,"study_"+id+"_applied"));
        poor.root.pp=d.cost-0.01;choose(poor,id,"applied");assert(!has(poor,"study_"+id+"_applied"));
        poor.root.pp=d.cost;choose(poor,id,"applied");assert(has(poor,"study_"+id+"_applied"));assert.equal(poor.root.pp,0);
        const unfounded=prepared(id);unfounded.root.flags.delete("HSM_BAR_service_founded");choose(unfounded,id,"applied");choose(unfounded,id,"reserved");expectTotals(unfounded,{});
        assert(!has(unfounded,"study_"+id+"_applied"));assert(!has(unfounded,"study_"+id+"_reserved"));
    });
}
for(const[id,d]of Object.entries(expected)){
    for(const[mode,value]of Object.entries(d.terminal)){
        scenario(id+" / final "+mode+": overrides preliminary benefits and reports exact current result",()=>{
            const w=prepared(id);choose(w,id,"applied");
            if(["protect","restrict"].includes(mode)){
                flag(w,"region_local_open",mode==="protect"?"coexistence":"normalization",mode==="protect"?"project_wards_done":"project_containment_done");
                effect("HSM_BAR_case_dispose_"+id+"_"+mode,w);
            }else if(mode==="reviewed")effect("HSM_BAR_case_archive_"+id,w);
            else {flag(w,"case_"+id+"_closed");effect("HSM_BAR_outcome_"+id+"_sealed",w);}
            expectTotals(w,value);assert(has(w,"disposition_"+id+"_recorded"));
            assert.equal(selected("GetHSMBAROutcomePolicy_"+id,w),"HSM_BAR_outcome_"+id+"_"+mode);
            const pp=w.root.pp;
            refresh(w);choose(w,id,"reserved");expectTotals(w,value);assert.equal(w.root.pp,pp);assert(!Object.hasOwn(w.root.vars,"HSM_BAR_cover_integrity"));
            w.states[624].controller="YAL";refresh(w);expectTotals(w,d.physical?{}:value);
            w.states[624].controller="BAR";refresh(w);expectTotals(w,value);
            for(const lang of ["english","russian"])assert(panel(id,w,lang).length>0);
            const first=prepared(id);
            flag(first,"case_"+id+"_"+(["sealed","reviewed"].includes(mode)?"closed":mode));
            refresh(first);choose(first,id,"applied");choose(first,id,"reserved");expectTotals(first,value);
            assert(!has(first,"study_"+id+"_applied"));assert(!has(first,"study_"+id+"_reserved"));
            assert.equal(selected("GetHSMBAROutcomeDisposition_"+id,first),"HSM_BAR_outcome_legacy_disposition");
        });
    }
}
scenario("all seventeen contributions combine once, then vanish without erasing evidence",()=>{
    const w=world(),sum={};
    for(const[id,d]of Object.entries(expected)){access(w,id);flag(w,"study_"+id+"_done","study_"+id+"_applied");for(const[k,v]of Object.entries(d.applied))sum[k]=(sum[k]||0)+v;}
    refresh(w);expectTotals(w,sum);for(let i=0;i<10;i++)refresh(w);expectTotals(w,sum);
    const flags=[...w.root.flags];w.root.flags.delete("HSM_BAR_active");refresh(w);expectTotals(w,{});
    assert.equal(w.root.flags.size,flags.length-1);assert.equal(w.root.pp,200);assert.equal(w.root.bonuses.length,0);
});
scenario("crown custody and reactor existence suspend both policy variants",()=>{
    for(const mode of ["applied","reserved"]){
        const w=prepared("crown");choose(w,"crown",mode);w.crowns[0].flags.add("HSM_BAR_case_crown_missing");refresh(w);expectTotals(w,{});
        w.crowns[0].flags.delete("HSM_BAR_case_crown_missing");refresh(w);expectTotals(w,expected.crown[mode]);
        const r=prepared("reactor");choose(r,"reactor",mode);r.states[624].reactor=0;refresh(r);expectTotals(r,{});
        r.states[624].reactor=1;refresh(r);expectTotals(r,expected.reactor[mode]);
    }
});
scenario("pending, suspended, active, reserved and inconclusive have distinct readable states",()=>{
    const w=world();assert.equal(selected("GetHSMBAROutcome_zebrica",w),"HSM_BAR_outcome_no_result");
    flag(w,"case_zebrica_inconclusive");assert.equal(selected("GetHSMBAROutcome_zebrica",w),"HSM_BAR_outcome_inconclusive");
    for(const id of Object.keys(expected)){const v=prepared(id);assert.equal(selected("GetHSMBAROutcomeStatus_"+id,v),"HSM_BAR_outcome_pending");choose(v,id,"reserved");assert.equal(selected("GetHSMBAROutcomePolicy_"+id,v),"HSM_BAR_outcome_"+id+"_reserved");}
});
scenario("dynamic modifier maps every ledger variable exactly once and refresh has no core recursion",()=>{
    const dynamic=dictionary(read("common/dynamic_modifiers/HSM_BAR_anomalous_research.txt")).HSM_BAR_anomalous_research;
    for(const[k,modifier]of Object.entries(modifierNames))assert.equal(prop(dynamic,modifier),"HSM_BAR_outcome_"+k);
    assert.equal(dynamic.filter(n=>!["icon","enable"].includes(n.key)).length,Object.keys(modifierNames).length);
    const source=fs.readFileSync(path.join(mod,"common/scripted_effects/HSM_BAR_case_outcomes.txt"),"utf8");
    assert(!/HSM_BAR_core_refresh\s*=/.test(source));assert(!/add_tech_bonus|add_political_power|set_global_flag|clr_global_flag|transfer_state|set_country_flag\s*=\s*HSM_BAR_study_/.test(source));
});
scenario("engine-documented trigger and modifier names; old PP predicate must fail",()=>{
    assert.throws(()=>test(parse("political_power > 14"),world()),/Unsupported predicate/);
    const docsRoot=process.env.HOI4_DOCUMENTATION || "C:/shit/Steam/steamapps/common/Hearts of Iron IV/documentation";
    assert(fs.existsSync(docsRoot),"Set HOI4_DOCUMENTATION to installed engine documentation.");
    const triggerDocs=fs.readFileSync(path.join(docsRoot,"triggers_documentation.md"),"utf8");
    assert(triggerDocs.includes("## has_political_power"));assert(!triggerDocs.includes("## political_power\n"));
    const modifierDocs=fs.readFileSync(path.join(docsRoot,"modifiers_documentation.md"),"utf8");
    for(const name of Object.values(modifierNames).filter(n=>n!=="production_speed_infrastructure_factor"))assert(modifierDocs.includes("## "+name+"\n"),name);
    const base=path.resolve(mod,"../../EaW/common/dynamic_modifiers/CVA_dynamic_modifiers.txt");
    assert(fs.readFileSync(base,"utf8").includes("production_speed_infrastructure_factor"),"Building-derived modifier supported by installed EaW pattern");
});
scenario("English/Russian result keys match; reports contain no PP, bonus percentages or unresolved redaction calls",()=>{
    assert.deepEqual(Object.keys(loc.english).sort(),Object.keys(loc.russian).sort());
    for(const lang of ["english","russian"]){
        for(const[k,text]of Object.entries(loc[lang])){
            if(/^hsm_bar_cases\.\d+\.d$/.test(k)||/^HSM_BAR_project_case_.*_desc$/.test(k)){
                assert(!/political power|политическ[а-я]+\s+власт|20%|research bonus|бонус исследований|\[REMOVED|\[УДАЛЕНО|\[НЕИЗВЕСТНО/i.test(text),k);
            }
        }
        for(const id of Object.keys(expected))assert(loc[lang]["hsm_bar_cases."+(Object.keys(expected).indexOf(id)+1)+".b"]);
    }
});
scenario("no focus grants study outcomes and no new outcome function fabricates bodies",()=>{
    for(const name of fs.readdirSync(path.join(mod,"common/national_focus")).filter(x=>x.startsWith("HSM_BAR"))){
        const text=fs.readFileSync(path.join(mod,"common/national_focus",name),"utf8");
        assert(!/set_country_flag\s*=\s*HSM_BAR_study_\w+_(?:applied|reserved)/.test(text),name);
    }
    for(const name of ["HSM_BAR_case_outcomes.txt","HSM_BAR_cases.txt"]){
        const text=fs.readFileSync(path.join(mod,"common/scripted_effects",name),"utf8");
        assert(!/create_country_leader|recruit_character|transfer_state|set_global_flag\s*=\s*HSM_BAR_case_.*(?:body|remains)/.test(text));
    }
});
for (const [id, d] of Object.entries(expected)) {
    for (const mode of ["applied", "reserved"]) {
        scenario(id + " / " + mode + ": compact bilingual presentation, colors and suspension", () => {
            const w = prepared(id);
            choose(w, id, mode);
            const histories = {};
            for (const lang of ["english", "russian"]) {
                const result = expectPresentation(id, w, d[mode], lang);
                histories[lang] = result.history;
                assert(result.text.startsWith(loc[lang].HSM_BAR_anomalous_research + " | " + loc[lang].HSM_BAR_outcome_active + "\\n"));
                assert.equal(lines(result.text)[1], loc[lang]["HSM_BAR_outcome_" + id + "_" + mode]);
                assert(/^§Y[^§]+§!$/.test(lines(result.text)[1]), "Concise yellow choice title");
                if (mode === "applied") {
                    assert.deepEqual([...result.history.matchAll(/§R(-\d+)§!/g)].map(m => Number(m[1])), [-d.cost]);
                    assert(!/§G/.test(result.history), "No invented research bonus");
                } else {
                    assert(!/§[GR]|[+-]\d|cover|прикрыти/i.test(result.history), "No invented reserve reward or payment");
                    assert(/no political power expense|без расхода политической власти/i.test(result.history), "Reserve history must report no payment");
                }
                assert(!/final|итог|35/i.test(result.history), "No unchosen disposition or study payment");
            }
            const checkState = wanted => {
                refresh(w);
                expectTotals(w, wanted);
                for (const lang of ["english", "russian"]) {
                    const result = expectPresentation(id, w, wanted, lang);
                    assert.equal(result.history, histories[lang], "History survives suspension unchanged");
                    assert.equal(lines(result.text)[1], loc[lang]["HSM_BAR_outcome_" + id + "_" + mode], "Choice retained");
                    if (!Object.keys(wanted).length) {
                        assert(!/§[GR]/.test(result.current), "Suspended effects cannot appear active");
                        assert(result.text.includes(loc[lang].HSM_BAR_outcome_suspended));
                    }
                }
            };
            w.states[624].controller = "YAL"; checkState(d.physical ? {} : d[mode]);
            w.states[624].controller = "BAR"; checkState(d[mode]);
            for (const f of ["active", "directorate", "service_founded"]) {
                w.root.flags.delete("HSM_BAR_" + f); checkState({});
                flag(w, f); checkState(d[mode]);
            }
            w.root.capitulated = true; checkState({});
            w.root.capitulated = false; checkState(d[mode]);
        });
    }
    scenario(id + ": pending research, pending choice and unknown history are distinct", () => {
        const w = world(); access(w, id);
        for (const lang of ["english", "russian"]) {
            const result = expectPresentation(id, w, {}, lang);
            assert.equal(result.history, undefined);
            assert.equal(panel(id, w, lang), renderKey("HSM_BAR_outcome_no_result", w, lang));
        }
        flag(w, "study_" + id + "_done");
        for (const lang of ["english", "russian"]) {
            const result = expectPresentation(id, w, {}, lang);
            assert.equal(result.history, undefined);
            assert.equal(result.text.split(loc[lang].HSM_BAR_outcome_pending).length, 2, "Pending status occurs once");
            assert.equal(result.text.split(loc[lang].HSM_BAR_outcome_zero).length, 2, "Zero contribution occurs once");
        }
        for (const mode of ["applied", "reserved"]) {
            const legacy = prepared(id); flag(legacy, "study_" + id + "_" + mode); refresh(legacy);
            for (const lang of ["english", "russian"]) {
                const result = expectPresentation(id, legacy, d[mode], lang);
                assert.equal(result.history, loc[lang].HSM_BAR_outcome_legacy_cost);
                assert(/unknown|неизвестны/.test(result.history));
                assert(!/\d|§[GR]/.test(result.history), "No reconstructed costs or bonuses");
            }
            legacy.root.flags.delete("HSM_BAR_study_" + id + "_done"); refresh(legacy); expectTotals(legacy, {});
            for (const lang of ["english", "russian"]) expectPresentation(id, legacy, {}, lang);
        }
    });
    for (const [mode, value] of Object.entries(d.terminal)) {
        for (const prior of ["applied", "reserved", null]) {
            scenario(id + " / final " + mode + " after " + (prior || "no policy") + ": current effects replace interim; history remains", () => {
                const w = prepared(id);
                if (prior) choose(w, id, prior);
                flag(w, finalFlag(id, mode), "disposition_" + id + "_recorded"); refresh(w); expectTotals(w, value);
                const histories = {};
                for (const lang of ["english", "russian"]) {
                    const result = expectPresentation(id, w, value, lang);
                    histories[lang] = result.history;
                    assert.equal(lines(result.text)[1], loc[lang]["HSM_BAR_outcome_" + id + "_" + mode]);
                    assert(/^§Y(?:Final:|Итог:)/.test(lines(result.text)[1]), "Final choice is explicit");
                    if (prior) assert(!result.text.includes(loc[lang]["HSM_BAR_outcome_" + id + "_" + prior]), "No interim choice presented as current");
                    const historyKey = prior ? "HSM_BAR_outcome_" + id + "_" + (prior === "applied" ? "apply" : "reserve") + "_cost" : "HSM_BAR_outcome_no_cost";
                    assert.equal(result.history, loc[lang][historyKey] + loc[lang]["HSM_BAR_outcome_" + id + "_" + mode + "_cost"]);
                }
                w.states[624].controller = "YAL"; refresh(w); expectTotals(w, d.physical ? {} : value);
                for (const lang of ["english", "russian"]) assert.equal(expectPresentation(id, w, d.physical ? {} : value, lang).history, histories[lang]);
                w.states[624].controller = "BAR"; refresh(w); expectTotals(w, value);
                for (const lang of ["english", "russian"]) expectPresentation(id, w, value, lang);
                w.root.flags.delete("HSM_BAR_disposition_" + id + "_recorded");
                w.root.flags.delete("HSM_BAR_outcome_" + id + "_recorded");
                for (const lang of ["english", "russian"]) {
                    const result = expectPresentation(id, w, value, lang);
                    assert(!/\d|§[GR]/.test(result.history), "Historical final choice cannot fabricate payment");
                    assert(result.history.endsWith(loc[lang].HSM_BAR_outcome_legacy_disposition));
                }
            });
        }
    }
}
scenario("effect display uses the full active-status guard plus completed research", () => {
    for (const id of Object.keys(expected)) {
        const active = getters["GetHSMBAROutcomeStatus_" + id].find(n => prop(n, "localization_key") === "HSM_BAR_outcome_active");
        const gate = getters["GetHSMBAROutcomeEffects_" + id][0];
        const conditions = prop(prop(prop(gate, "trigger"), "NOT"), "AND");
        assert.deepEqual(conditions.slice(0, -1), prop(active, "trigger"));
        assert.deepEqual(conditions.at(-1), { key: "has_country_flag", op: "=", value: "HSM_BAR_study_" + id + "_done" });
        // The shared fixture aliases BAR to ROOT; validate the native tag gate structurally.
        assert.equal(prop(conditions, "tag"), "BAR");
        assert.equal(prop(gate, "localization_key"), "HSM_BAR_outcome_zero");
    }
});
scenario("inconclusive inquiry has zero effects and no invented financial history", () => {
    const w = world(); flag(w, "case_zebrica_inconclusive");
    for (const lang of ["english", "russian"]) {
        const result = expectPresentation("zebrica", w, {}, lang);
        assert.equal(result.history, undefined);
        assert(!/§[GR]|refund|возврат|political|политическ/.test(result.text));
    }
});
scenario("missing crown and absent reactor hide nominal modifiers in both languages", () => {
    for (const mode of ["applied", "reserved"]) {
        const crown = prepared("crown"); choose(crown, "crown", mode);
        crown.crowns[0].flags.add("HSM_BAR_case_crown_missing");
        const reactor = prepared("reactor"); choose(reactor, "reactor", mode); reactor.states[624].reactor = 0;
        for (const [id, w] of [["crown", crown], ["reactor", reactor]]) {
            refresh(w); expectTotals(w, {});
            for (const lang of ["english", "russian"]) expectPresentation(id, w, {}, lang);
        }
    }
});
scenario("reserve history records no meter reward for new and migrated saves", () => {
    for (const id of Object.keys(expected)) {
        for (const before of [undefined, -213.5, 99, 100, 517]) {
            const w = prepared(id);
            if (before !== undefined) {
                w.root.vars.HSM_BAR_cover_integrity = before;
                w.root.vars.HSM_BAR_service_coordination = 0.07;
            }
            choose(w, id, "reserved");
            assert(!Object.hasOwn(w.root.vars, "HSM_BAR_cover_integrity"));
            assert(!Object.hasOwn(w.root.vars, "HSM_BAR_service_coordination"));
            assert.equal(w.root.pp, 200); assert.equal(w.root.bonuses.length, 0);
            for (const lang of ["english", "russian"]) {
                const { history } = expectPresentation(id, w, expected[id].reserved, lang);
                assert(!/§[GR]|[+-]\d|cover|прикрыти/i.test(history), "Obsolete reward or invented expense in reserve history");
                assert(/no political power expense|без расхода политической власти/i.test(history));
            }
        }
    }
});
const finalDecisions = dictionary(read("common/decisions/HSM_BAR_anomalies.txt").flatMap(n => n.value));
scenario("final costs match decisions; repeated archive reviews report a rate, never an invented total", () => {
    for (const [id, d] of Object.entries(expected)) {
        for (const mode of Object.keys(d.terminal)) {
            const suffix = { sealed: "seal", reviewed: "review" }[mode] || mode;
            const decision = finalDecisions["HSM_BAR_case_" + id + "_" + suffix];
            const cost = mode === "reviewed" ? 10 : mode === "sealed" ? 20 : 35;
            assert.equal(Number(prop(decision, "cost")), cost);
            for (const lang of ["english", "russian"]) {
                const text = loc[lang]["HSM_BAR_outcome_" + id + "_" + mode + "_cost"];
                assert.deepEqual([...text.matchAll(/§R(-\d+)§!/g)].map(m => Number(m[1])), [-cost]);
            }
            if (mode !== "reviewed") continue;
            assert.equal(Number(prop(decision, "days_re_enable")), 30);
            const w = prepared(id); choose(w, id, "applied");
            let history;
            for (let reviews = 1; reviews <= 3; reviews++) {
                assert(test(prop(decision, "available"), w));
                w.root.pp -= cost;
                run(prop(decision, "complete_effect"), w);
                assert.equal(w.root.pp, 200 - d.cost - cost * reviews);
                expectTotals(w, d.terminal.reviewed);
                for (const lang of ["english", "russian"]) {
                    const result = expectPresentation(id, w, d.terminal.reviewed, lang);
                    const costText = loc[lang]["HSM_BAR_outcome_" + id + "_reviewed_cost"];
                    assert(/per review|за просмотр/.test(costText));
                    assert(/total: unknown|расходов на просмотры: неизвестна/.test(costText));
                    assert(result.history.endsWith(costText));
                }
                const current = ["english", "russian"].map(lang => resultSections(id, w, lang).history);
                if (history) assert.deepEqual(current, history, "Untracked review count must not become a fabricated total");
                history = current;
            }
        }
    }
});
scenario("all seventeen cases have contextual titles, locale parity and no impossible future instruction", () => {
    assert.equal(Object.keys(expected).length, 17);
    for (const lang of ["english", "russian"]) {
        const titles = [];
        for (const [id, d] of Object.entries(expected)) {
            for (const mode of ["applied", "reserved", ...Object.keys(d.terminal)]) {
                const title = loc[lang]["HSM_BAR_outcome_" + id + "_" + mode];
                assert(/^§Y[^§\\]+§!$/.test(title)); titles.push(title);
                const key = "HSM_BAR_outcome_" + id + "_" + mode + "_effects";
                assert.equal(loc.english[key].match(/§[GR][+-][\d.%]+§!/g).join(), loc.russian[key].match(/§[GR][+-][\d.%]+§!/g).join(), "EN/RU effect and color parity");
            }
            if (Object.keys(d.terminal).length) continue;
            for (const mode of ["applied", "reserved"]) {
                const w = prepared(id); choose(w, id, mode);
                const tooltip = loc[lang]["HSM_BAR_outcome_" + id + "_" + (mode === "applied" ? "apply" : "reserve") + "_tt"];
                assert(!/final disposition|окончательное решение|replac|замен/i.test(panel(id, w, lang) + tooltip), id);
            }
        }
        assert.equal(new Set(titles).size, titles.length, "Case-specific choices must not collapse to generic labels");
    }
});
if (process.argv.includes("--sample")) {
    const w = prepared("amulet"); choose(w, "amulet", "applied");
    for (const lang of ["english", "russian"]) console.log("AMULET / " + lang + "\n" + lines(panel("amulet", w, lang)).join("\n"));
    w.states[624].controller = "YAL"; refresh(w);
    console.log("AMULET / suspended\n" + lines(panel("amulet", w, "english")).join("\n"));
}
console.log(`Barrad case outcomes: ${passed} scenarios passed; ${failed} failed.`);
console.log("Boundary: deterministic script and localization checks; native engine display still requires a playtest.");
process.exitCode=failed?1:0;
