"use strict";

// Run standalone or register with the legacy suite's generated-script interpreter.
const fs = require("node:fs");
const path = require("node:path");
const assert = require("node:assert/strict");

module.exports = function experimentsFixture(h) {
    const { B, P, projects, departments, modifiers, variable, id, test, world, flag, has,
        preparations, select, effect, condition, execute, triggers, effects, missions,
        journalEffects, one, walk, tick, callback, expected, exactTotals, invalidators } = h;
    let catalog, validCatalog = false;
    test("interactive catalog: 26 unique IDs, four combinations and two complete response contracts", () => {
        catalog = JSON.parse(fs.readFileSync(path.join(__dirname, "data/barrad-collegium-experiments.json"), "utf8").replace(/^\uFEFF/, ""));
        assert.equal(catalog.length, 26);
        assert.deepEqual(catalog.map(p => p.id).sort(), projects.map(p => p.id).sort());
        for (const p of catalog) {
            for (const axis of ["rig", "control"]) {
                assert.equal(p[axis].options.length, 2, p.id + "/" + axis);
                assert.equal(p[axis].question.length, 2);
                for (const option of p[axis].options) for (const field of ["label", "note"])
                    assert.equal(option[field].length, 2, `${p.id}/${axis}/${field}`);
            }
            assert.equal(p.observations.length, 4, p.id);
            assert.equal(p.responses.length, 2, p.id);
            for (const response of p.responses) {
                assert.equal(response.reports.length, 4, p.id);
                for (const field of ["cost", "days"]) {
                    assert.equal(response[field].length, 4, `${p.id}/${field}`);
                    assert(response[field].every(v => Number.isInteger(v) && (field === "cost" ? v >= 0 : v > 0)), `${p.id}/${field}`);
                }
            }
        }
        validCatalog = true;
    });
    if (!validCatalog) return;
    const data = p => catalog.find(e => e.id === p.id);
    const responseData = (p, response) => data(p).responses[response === "a" ? 0 : 1];
    const run = (p, operation, s) => effect(id(p) + "_" + operation, s);
    const allowed = (p, operation, s) => {
        const name = id(p) + "_can_" + operation;
        assert(triggers[name], name);
        return condition(triggers[name], s);
    };
    const method = s => s.instrumentation ? "instrumented" : "trials";
    const days = (p, s) => s.instrumentation ? p.instrumentedDays : p.trialDays;
    const cost = (p, s) => s.instrumentation ? p.instrumentedCost : p.trialCost;
    const verify = (p, combo, response) => `${id(p)}_verify_${response}_${combo}_mission`;
    const fire = (mission, type, s) => { assert(missions[mission], mission); execute(one(missions[mission], type + "_effect"), s); };
    const permanent = s => Object.fromEntries(Object.entries(expected(s)).filter(([m]) => m !== "civilian_factory_use"));
    function ui(p, operation, s) {
        const key = id(p) + "_" + operation;
        const handlers = Object.entries(journalEffects).filter(([, nodes]) => walk(nodes).some(n => n.key === key));
        assert.equal(handlers.length, 1, `One UI handler delegates to ${key}`);
        execute(handlers[0][1], s);
    }
    function page(p, s) {
        Object.assign(s.variables, { HSM_BAR_mtk_open: 1, HSM_BAR_mtk_project: p.number,
            HSM_BAR_mtk_department: Object.keys(departments).indexOf(p.department) + 1, HSM_BAR_mtk_document: 5 });
    }
    function prepare(p, combo, s) {
        const pp = s.pp;
        for (const [part, selected] of [["rig", combo >> 1], ["control", combo & 1]]) {
            run(p, `prepare_${part}_${selected ? "b" : "a"}`, s);
            assert(has(s, `${id(p)}_${part}_${selected ? "b" : "a"}`));
            assert(!has(s, `${id(p)}_${part}_${selected ? "a" : "b"}`));
        }
        assert.equal(s.pp, pp, "Preparation is unpaid");
    }
    function ready(p, combo, instrumented = false) {
        const s = world(); s.day = 23; s.instrumentation = instrumented;
        preparations(p, s); flag(s, id(p) + "_theory");
        effect(P + "projects_pulse", s);
        select(p, instrumented ? "instrumentation" : "replication", s);
        prepare(p, combo, s); page(p, s);
        return s;
    }
    function reservation(p, s) {
        const required = B.factories(p, method(s));
        assert.equal(s.variables[variable("civilian_factory_use")], required);
        assert.equal(s.cache[P + "research"].civilian_factory_use, required);
        for (const d of B.faculties(p)) assert(has(s, P + d + "_busy"), d);
        exactTotals(s);
    }
    function begin(p, combo, s) {
        const pp = s.pp, day = s.day;
        assert(allowed(p, "begin_experiment", s));
        run(p, "begin_experiment", s);
        assert.equal(s.pp, pp - cost(p, s));
        assert(has(s, id(p) + "_experiment_active"));
        assert.equal(has(s, id(p) + "_paid_rig_b"), !!(combo & 2));
        assert.equal(has(s, id(p) + "_paid_control_b"), !!(combo & 1));
        assert.equal(s.missions.get(`${id(p)}_${method(s)}_mission`), day + days(p, s));
        reservation(p, s);
    }
    function checkpoint(p, s, removalFirst = true) {
        tick(s, days(p, s), removalFirst);
        assert(has(s, id(p) + "_observation_ready"));
        assert(has(s, id(p) + "_experiment_active"));
        assert(has(s, id(p) + "_trials_running"));
        assert(!has(s, id(p) + "_verify_running"));
        assert(!has(s, id(p) + "_done"));
        assert(!has(s, id(p) + "_experiment_record"));
        assert.equal(s.missions.size, 0);
        reservation(p, s);
    }
    function respond(p, combo, response, s) {
        const pp = s.pp, day = s.day, r = responseData(p, response);
        assert(allowed(p, "respond_" + response, s));
        run(p, "respond_" + response, s);
        assert.equal(s.pp, pp - r.cost[combo]);
        assert.equal(s.flags.get(id(p) + "_verify_running"), day, "Verification has its own dated flag");
        assert(has(s, id(p) + "_response_" + response));
        assert(!has(s, id(p) + "_response_" + (response === "a" ? "b" : "a")));
        assert.equal(s.missions.size, 1);
        assert.equal(s.missions.get(verify(p, combo, response)), day + r.days[combo]);
        reservation(p, s);
    }
    function released(p, s, completed) {
        for (const f of ["experiment_active", "observation_ready", "verify_running", "trials_running", "trials_revised_contract"])
            assert(!has(s, id(p) + "_" + f), f);
        assert.equal(has(s, id(p) + "_done"), completed);
        assert.equal(has(s, id(p) + "_experiment_record"), completed);
        assert.equal(s.missions.size, 0);
        for (const d of B.faculties(p)) assert(!has(s, P + d + "_busy"));
        assert.equal(s.variables[variable("civilian_factory_use")], 0);
        if (!completed) for (const f of ["paid_rig_b", "paid_control_b", "response_a", "response_b"])
            assert(!has(s, id(p) + "_" + f), f);
        exactTotals(s);
    }
    function reload(s) {
        // Exercise a serialized save boundary, including dated flags and mission deadlines.
        return JSON.parse(JSON.stringify(s, (_, value) => value instanceof Map ? { fixtureMap: [...value] } :
            value instanceof Set ? { fixtureSet: [...value] } : value), (_, value) =>
            value && Object.hasOwn(value, "fixtureMap") ? new Map(value.fixtureMap) :
                value && Object.hasOwn(value, "fixtureSet") ? new Set(value.fixtureSet) : value);
    }

    for (const p of projects) for (let combo = 0; combo < 4; combo++) for (const response of ["a", "b"])
        test(`${p.id}/${combo}/${response}: exact interactive PP, both timers, checkpoint, locks and fixed ${p.outcome}`, () => {
            for (const instrumented of [false, true]) for (const removalFirst of [true, false]) {
                const s = ready(p, combo, instrumented), before = permanent(s), pp = s.pp;
                const r = responseData(p, response), mission = verify(p, combo, response);
                begin(p, combo, s);
                const paid = structuredClone(s);
                run(p, "begin_experiment", s);
                for (const part of ["rig", "control"]) for (const option of ["a", "b"]) run(p, `prepare_${part}_${option}`, s);
                for (const d of B.faculties(p)) for (const choice of ["replication", "instrumentation"]) effect(P + d + "_select_" + choice, s);
                for (const answer of ["a", "b"]) run(p, "respond_" + answer, s);
                assert.deepEqual(s, paid, "Paid work cannot be changed or answered before observation");
                s.day += days(p, s) - 0.01;
                callback(p, method(s), "timeout", s);
                assert(!has(s, id(p) + "_observation_ready"));
                assert.deepEqual(permanent(s), before);
                s.day = paid.day;
                checkpoint(p, s, removalFirst);
                assert.deepEqual(permanent(s), before, "Observation grants no permanent bonus");
                const waitingPP = s.pp;
                tick(s, 90); effect(P + "projects_pulse", s);
                assert.equal(s.pp, waitingPP); assert.equal(s.missions.size, 0);
                assert(has(s, id(p) + "_observation_ready")); reservation(p, s);
                assert.deepEqual(permanent(s), before);
                const waiting = structuredClone(s);
                for (const part of ["rig", "control"]) for (const option of ["a", "b"]) run(p, `prepare_${part}_${option}`, s);
                for (const d of B.faculties(p)) for (const choice of ["replication", "instrumentation"]) effect(P + d + "_select_" + choice, s);
                assert.deepEqual(s, waiting, "Checkpoint laboratories and preparation choices remain locked");
                // Live preparation and department flags cannot rewrite the paid combination.
                for (const part of ["rig", "control"]) {
                    s.flags.delete(id(p) + "_" + part + "_a"); s.flags.delete(id(p) + "_" + part + "_b");
                    flag(s, `${id(p)}_${part}_${(combo & (part === "rig" ? 2 : 1)) ? "a" : "b"}`);
                }
                respond(p, combo, response, s);
                const running = structuredClone(s);
                for (const answer of ["a", "b"]) run(p, "respond_" + answer, s);
                assert.deepEqual(s, running);
                callback(p, "trials", "timeout", s); callback(p, "instrumented", "timeout", s);
                callback(p, "trials", "cancel", s); callback(p, "instrumented", "cancel", s);
                assert.deepEqual(s, running, "Late observation callbacks cannot cancel verification");
                s.day += r.days[combo] - 0.01; fire(mission, "timeout", s);
                assert(!has(s, id(p) + "_done")); assert.deepEqual(permanent(s), before);
                const early = structuredClone(s);
                for (const answer of ["a", "b"]) for (let c = 0; c < 4; c++) if (answer !== response || c !== combo) {
                    fire(verify(p, c, answer), "timeout", s); fire(verify(p, c, answer), "cancel", s);
                }
                assert.deepEqual(s, early, "A different response or combination cannot finish the paid verification");
                s.day = running.day;
                tick(s, r.days[combo], removalFirst);
                released(p, s, true);
                assert.equal(s.pp, pp - cost(p, s) - r.cost[combo]);
                assert(has(s, id(p) + "_response_" + response));
                assert.equal(has(s, id(p) + "_paid_rig_b"), !!(combo & 2));
                assert.equal(has(s, id(p) + "_paid_control_b"), !!(combo & 1));
                for (const m of modifiers.filter(m => m !== "civilian_factory_use"))
                    assert(Math.abs(permanent(s)[m] - before[m] - (B.rewards[p.id][m] || 0)) < 1e-10, m);
                if (p.outcome === "failure") assert.deepEqual(permanent(s), before);
                const result = structuredClone(s);
                for (const answer of ["a", "b"]) for (let c = 0; c < 4; c++) {
                    fire(verify(p, c, answer), "timeout", s); fire(verify(p, c, answer), "cancel", s);
                }
                run(p, "cancel_trials", s); run(p, "begin_experiment", s);
                for (const part of ["rig", "control"]) for (const option of ["a", "b"]) run(p, `prepare_${part}_${option}`, s);
                effect(P + "projects_pulse", s);
                assert.deepEqual(s, result, "Completed report and rewards survive callback replay");
            }
        });

    for (const p of projects) {
        test(`${p.id}: no implicit preparation, exclusive choices, idle/theory guards and exact start resources`, () => {
            const s = world(); preparations(p, s); page(p, s);
            for (const part of ["rig", "control"]) for (const option of ["a", "b"]) {
                const before = structuredClone(s); run(p, `prepare_${part}_${option}`, s); assert.deepEqual(s, before);
            }
            flag(s, id(p) + "_theory");
            assert(!allowed(p, "begin_experiment", s));
            let before = structuredClone(s); run(p, "begin_experiment", s); assert.deepEqual(s, before);
            run(p, "prepare_rig_a", s); assert(!allowed(p, "begin_experiment", s));
            before = structuredClone(s); run(p, "begin_experiment", s); assert.deepEqual(s, before);
            for (const combo of [3, 0, 2, 1]) prepare(p, combo, s);
            for (const axis of ["rig", "control"]) {
                const contradictory = ready(p, 0); flag(contradictory, `${id(p)}_${axis}_b`);
                const before = structuredClone(contradictory); assert(!allowed(p, "begin_experiment", contradictory));
                run(p, "begin_experiment", contradictory); assert.deepEqual(contradictory, before);
            }
            for (const instrumented of [false, true]) {
                const paid = ready(p, 1, instrumented), required = B.factories(p, method(paid));
                paid.pp = cost(p, paid) - 0.01;
                before = structuredClone(paid); run(p, "begin_experiment", paid); assert.deepEqual(paid, before);
                assert(!allowed(p, "begin_experiment", paid)); paid.pp = cost(p, paid);
                for (let count = 0; count < required; count++) {
                    paid.factories = count; assert(!allowed(p, "begin_experiment", paid));
                    before = structuredClone(paid); run(p, "begin_experiment", paid); assert.deepEqual(paid, before);
                }
                paid.factories = required; begin(p, 1, paid); assert.equal(paid.pp, 0);
            }
        });
        for (let combo = 0; combo < 4; combo++) for (const response of ["a", "b"])
            test(`${p.id}/${combo}/${response}: exact response price and verification mission contract`, () => {
                const s = ready(p, combo), r = responseData(p, response), mission = missions[verify(p, combo, response)];
                assert(mission); assert.equal(Number(one(mission, "days_mission_timeout")), r.days[combo]);
                for (const key of ["activation", "available", "visible"]) assert(!condition(one(mission, key), s));
                assert.equal(one(mission, "cancel_if_not_visible"), "no");
                assert.equal(one(one(mission, "ai_will_do"), "factor"), "0");
                assert(!mission.some(n => ["cost", "complete_effect", "modifier", "selectable_mission"].includes(n.key)));
                s.factories = B.factories(p, method(s));
                begin(p, combo, s); checkpoint(p, s);
                assert.equal(s.factories - s.cache[P + "research"].civilian_factory_use, 0, "Response reuses the fully reserved laboratories");
                s.pp = r.cost[combo] - 0.01; const before = structuredClone(s);
                assert(!allowed(p, "respond_" + response, s)); run(p, "respond_" + response, s); assert.deepEqual(s, before);
                s.pp = r.cost[combo]; respond(p, combo, response, s); assert.equal(s.pp, 0);
            });
        test(`${p.id}: save fixture survives paid observation, indefinite checkpoint and verification resume`, () => {
            let s = ready(p, 3, true); begin(p, 3, s); tick(s, 7);
            const due = s.missions.get(id(p) + "_instrumented_mission"), pp = s.pp;
            s = reload(s); effect(P + "projects_pulse", s);
            assert.equal(s.missions.get(id(p) + "_instrumented_mission"), due); assert.equal(s.pp, pp);
            tick(s, due - s.day); s = reload(s); tick(s, 45); effect(P + "projects_pulse", s);
            assert(has(s, id(p) + "_observation_ready")); reservation(p, s); assert.equal(s.pp, pp);
            respond(p, 3, "b", s); const deadline = s.missions.get(verify(p, 3, "b")), paidPP = s.pp;
            tick(s, 1); s = reload(s); effect(P + "projects_pulse", s);
            assert.equal(s.missions.get(verify(p, 3, "b")), deadline); assert.equal(s.pp, paidPP);
            tick(s, deadline - s.day); released(p, s, true); s = reload(s);
            const record = structuredClone(s); effect(P + "projects_pulse", s); assert.deepEqual(s, record);
        });
        for (const stage of ["observation", "checkpoint", "verification"]) {
            test(`${p.id}/${stage}: explicit cancellation clears payment snapshots and cannot be replayed`, () => {
                const s = ready(p, 3, true); begin(p, 3, s);
                if (stage !== "observation") checkpoint(p, s);
                if (stage === "verification") respond(p, 3, "b", s);
                const pp = s.pp; run(p, "cancel_trials", s); released(p, s, false);
                assert(has(s, id(p) + "_theory")); assert.equal(s.pp, pp);
                for (const m of ["trials", "instrumented", ...["a", "b"].flatMap(r => [0, 1, 2, 3].map(c => `verify_${r}_${c}`))]) {
                    callback(p, m, "timeout", s); callback(p, m, "cancel", s);
                }
                released(p, s, false); assert.equal(s.pp, pp);
            });
            for (const [label, invalidate] of Object.entries({ ...invalidators,
                ...Object.fromEntries(B.faculties(p).flatMap(d => [[d + "_dead", s => s.flags.delete(departments[d].alive)],
                    [d + "_retired", s => s.characters.delete(departments[d].character)]])) }))
                test(`${p.id}/${stage}: ${label} releases every reserved faculty with no premature result`, () => {
                    const s = ready(p, 3, true); begin(p, 3, s);
                    if (stage !== "observation") checkpoint(p, s);
                    if (stage === "verification") respond(p, 3, "b", s);
                    const pp = s.pp; invalidate(s); effect(P + "projects_pulse", s);
                    released(p, s, false); assert.equal(s.pp, pp);
                    if (stage === "verification") fire(verify(p, 3, "b"), "timeout", s);
                    else callback(p, "instrumented", "timeout", s);
                    assert(!has(s, id(p) + "_done"));
                });
        }
        for (const stage of ["observation", "verification"]) test(`${p.id}/${stage}: missing native mission cancels without a bonus`, () => {
            const s = ready(p, 2, true); begin(p, 2, s);
            if (stage === "verification") { checkpoint(p, s); respond(p, 2, "a", s); }
            const m = stage === "verification" ? verify(p, 2, "a") : id(p) + "_instrumented_mission";
            const due = s.missions.get(m), before = permanent(s), pp = s.pp;
            s.missions.delete(m); effect(P + "projects_pulse", s); released(p, s, false);
            s.day = due; fire(m, "timeout", s);
            assert.deepEqual(permanent(s), before); assert.equal(s.pp, pp); released(p, s, false);
        });
        test(`${p.id}: cancelling then restarting rejects old observation and verification callbacks`, () => {
            for (const sameContract of [false, true]) {
                const s = ready(p, 3, true); begin(p, 3, s); checkpoint(p, s); respond(p, 3, "b", s);
                const oldDue = s.missions.get(verify(p, 3, "b"));
                tick(s, responseData(p, "b").days[3] - 1); run(p, "cancel_trials", s);
                const combo = sameContract ? 3 : 0, response = sameContract ? "b" : "a";
                prepare(p, combo, s); begin(p, combo, s);
                s.day = oldDue;
                const fresh = structuredClone(s);
                fire(verify(p, 3, "b"), "timeout", s); fire(verify(p, 3, "b"), "cancel", s);
                callback(p, "instrumented", "timeout", s); callback(p, "instrumented", "cancel", s);
                assert.deepEqual(s, fresh);
                tick(s, s.missions.get(id(p) + "_instrumented_mission") - s.day);
                respond(p, combo, response, s); const second = structuredClone(s);
                fire(verify(p, 3, "b"), "timeout", s); fire(verify(p, 3, "b"), "cancel", s);
                assert.deepEqual(s, second, "The dated verification flag protects the restarted contract");
                tick(s, responseData(p, response).days[combo]); released(p, s, true);
            }
        });
        test(`${p.id}: actual preparation, start and response UI effects reject foreign and wrong-page calls`, () => {
            for (const operation of ["prepare_rig_a", "prepare_rig_b", "prepare_control_a", "prepare_control_b", "begin_experiment", "respond_a", "respond_b"]) {
                const base = ready(p, 3);
                if (operation.startsWith("respond_")) { begin(p, 3, base); checkpoint(p, base); }
                for (const invalidate of [s => { s.tag = "WIT"; }, s => { s.ai = true; }, s => { delete s.variables.HSM_BAR_mtk_open; },
                    ...[1, 2, 3, 4, 6, 7].map(d => s => { s.variables.HSM_BAR_mtk_document = d; }),
                    s => { s.variables.HSM_BAR_mtk_project = 0; }, s => { s.variables.HSM_BAR_mtk_department = 0; }]) {
                    const s = structuredClone(base); invalidate(s); const before = structuredClone(s);
                    ui(p, operation, s); assert.deepEqual(s, before, operation);
                }
            }
        });
    }
    for (const p of projects.filter(p => p.partners)) test(`${p.id}: checkpoint locks both faculties and reserves laboratories once`, () => {
        const s = ready(p, 1, true); begin(p, 1, s); checkpoint(p, s);
        for (const d of B.faculties(p)) {
            const q = projects.find(q => q.department === d && !q.opus && !q.partners && !(p.prerequisites || []).includes(q.id));
            assert(!condition(triggers[id(q) + "_can_theory"], s));
        }
        const other = projects.find(q => !B.faculties(p).includes(q.department) && !q.partners && !q.opus);
        assert(condition(triggers[id(other) + "_can_theory"], s));
        effect(id(other) + "_start_theory", s);
        assert.equal(s.variables[variable("civilian_factory_use")], B.factories(p, "instrumented") + 1);
        run(p, "respond_a", s);
        assert(s.missions.has(verify(p, 1, "a")));
        run(p, "cancel_trials", s);
        assert.equal(s.variables[variable("civilian_factory_use")], 1);
        assert(s.missions.has(id(other) + "_theory_mission")); exactTotals(s);
    });
};

if (require.main === module) require("./Test-BarradCollegiumProjects.cjs");
