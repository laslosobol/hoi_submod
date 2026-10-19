#Requires -Version 7.2
param([string] $NodeCommand = 'node')

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$nodeRuntime = Get-Command $NodeCommand -CommandType Application -ErrorAction Stop

# Read-only checks against EaW/, including queued native diplomacy callbacks.
# The limited evaluator rejects unknown predicates; this is not an HOI4 runtime.
$javascript = @'
const fs = require('fs');
const path = require('path');
const assert = require('assert/strict');
const root = process.argv[2];
const read = p => fs.readFileSync(path.join(root, p), 'utf8');
const categoryId = 'BAR_ambrosius_diplomacy';
const societyCategoryId = 'BAR_society_upgrade_lame';
const routeFlags = ['HSM_BAR_active', 'HSM_BAR_collegium', 'HSM_BAR_directorate'];
const unlockFlag = 'BAR_ambrosius_diplomacy_unlocked';
const ids = [
  'BAR_ambrosius_zes_cosmetic',
  'BAR_ambrosius_gru_cosmetic',
  'BAR_ambrosius_gry_cosmetic',
  'BAR_ambrosius_wit_cosmetic',
  'BAR_ambrosius_claim_wittenland_crown',
  'BAR_ambrosius_proclaim_grand_county',
  'BAR_ambrosius_keep_promise_for_griffons',
  'BAR_ambrosius_keep_promise_for_griffons_integration',
  'BAR_ambrosius_steppe_integration',
  'BAR_ambrosius_bring_order_to_south',
  'BAR_ambrosius_high_kingdom_claims',
  'BAR_ambrosius_strike_wittenland',
  'BAR_ambrosius_secure_steppe',
  'BAR_ambrosius_provoke_wittenlands',
  'BAR_ambrosius_invite_back_ponies'
];
function parse(text) {
  const tokens = [...text.matchAll(/"(?:\\.|[^"\\])*"|#[^\r\n]*|[{}]|[<>!=?]+|[^\s{}=<>!?#]+/g)]
    .filter(m => !m[0].startsWith('#'));
  let i = 0;
  function block(nested = false) {
    const nodes = [];
    while (i < tokens.length) {
      const token = tokens[i++], key = token[0];
      if (key === '}') { assert(nested, 'unexpected closing brace'); return nodes; }
      assert(key !== '{', 'unexpected opening brace');
      const node = {key, op: '', value: '', start: token.index};
      if (/^[<>!=?]+$/.test(tokens[i]?.[0] || '')) {
        node.op = tokens[i++][0];
        assert(i < tokens.length, 'missing value');
        if (tokens[i][0] === '{') { i++; node.children = block(true); }
        else node.value = tokens[i++][0];
      }
      node.end = tokens[i - 1].index + tokens[i - 1][0].length;
      nodes.push(node);
    }
    assert(!nested, 'unclosed block');
    return nodes;
  }
  return block();
}
const prop = (nodes, key) => (nodes || []).find(n => n.key === key);
const body = (nodes, key) => prop(nodes, key)?.children || [];
const val = (nodes, key) => prop(nodes, key)?.value;
const ast = nodes => nodes.map(({start, end, children, ...n}) => children ? {...n, children: ast(children)} : n);
const guard = parse(routeFlags.map(f => `NOT = { has_country_flag = ${f} }`).join('\n'));
let passed = 0, failed = 0;
function test(name, fn) {
  try { fn(); passed++; console.log('PASS ' + name); }
  catch (error) { failed++; console.error('FAIL ' + name + '\n' + error.message); }
}
function loadPair(relative) {
  const upstream = read('EaW/' + relative), current = read('mod/HoISubmod/' + relative);
  const oldNodes = parse(upstream), newNodes = parse(current);
  const oldCategory = prop(oldNodes, categoryId), newCategory = prop(newNodes, categoryId);
  assert(oldCategory && newCategory, relative + ': missing native category');
  const oldSociety = prop(oldNodes, societyCategoryId), newSociety = prop(newNodes, societyCategoryId);
  assert(oldSociety && newSociety, relative + ': missing native society category');
  test(relative + ': all bytes outside the two explicitly guarded native categories preserved', () => {
    let restored = current;
    for (const [old, updated] of [[oldCategory, newCategory], [oldSociety, newSociety]].sort((a, b) => b[1].start - a[1].start)) {
      restored = restored.slice(0, updated.start) + upstream.slice(old.start, old.end) + restored.slice(updated.end);
    }
    assert(Buffer.from(restored).equals(Buffer.from(upstream)), 'Unrelated upstream bytes changed');
    assert.deepEqual(newNodes.map(n => n.key), oldNodes.map(n => n.key), 'Duplicate or missing categories');
  });
  test(relative + ': society override adds only route visibility guards and preserves every native payload byte', () => {
    let restored = current.slice(newSociety.start, newSociety.end);
    const newline = upstream.slice(oldSociety.start, oldSociety.end).includes('\r\n') ? '\r\n' : '\n';
    if (relative.includes('/categories/')) {
      assert.deepEqual(ast(newSociety.children.filter(n => n.key !== 'visible')), ast(oldSociety.children));
      assert.deepEqual(ast(body(newSociety.children, 'visible')), ast(guard));
      const inserted = '\tvisible = {' + newline + routeFlags.map(f => '\t\tNOT = { has_country_flag = ' + f + ' }' + newline).join('') + '\t}' + newline;
      assert.equal(restored.split(inserted).length, 2, 'Expected exactly one inserted visibility block');
      restored = restored.replace(inserted, '');
    } else {
      assert.deepEqual(newSociety.children.map(n => n.key), ['BAR_society_upgrade_pp']);
      const old = body(oldSociety.children, 'BAR_society_upgrade_pp'), updated = body(newSociety.children, 'BAR_society_upgrade_pp');
      for (const key of ['visible', 'available']) {
        const native = body(old, key);
        assert.equal(native[0].key, 'original_tag');
        assert.deepEqual(ast(body(updated, key)), ast([native[0], ...guard, ...native.slice(1)]));
      }
      assert.deepEqual(ast(updated.filter(n => !['visible', 'available'].includes(n.key))), ast(old.filter(n => !['visible', 'available'].includes(n.key))));
      assert.equal(val(updated, 'cost'), '70');
      assert.equal(val(updated, 'days_remove'), '80');
      assert.deepEqual(ast(body(updated, 'complete_effect')), ast(body(old, 'complete_effect')));
      for (const flag of routeFlags) {
        const inserted = '\t\t\tNOT = { has_country_flag = ' + flag + ' }' + newline;
        assert.equal(restored.split(inserted).length, 3, 'Expected exactly visible and available guards');
        restored = restored.replaceAll(inserted, '');
      }
    }
    assert.equal(restored, upstream.slice(oldSociety.start, oldSociety.end), 'Native society bytes changed beyond exact exclusions');
  });
  return {old: oldCategory.children, current: newCategory.children};
}
const decisions = loadPair('common/decisions/BAR_decisions.txt');
const category = loadPair('common/decisions/categories/BAR_decision_categories.txt');
test('category metadata preserved; runtime visibility guards all new-path flags', () => {
  assert.deepEqual(ast(category.current.filter(n => n.key !== 'visible')), ast(category.old));
  assert.deepEqual(ast(body(category.current, 'visible')), ast(guard));
});
test('exact native decision IDs retained once each', () => {
  assert.deepEqual(decisions.old.map(n => n.key), ids);
  assert.deepEqual(decisions.current.map(n => n.key), ids);
});
const callbackKeys = ['complete_effect', 'remove_effect', 'timeout_effect', 'cancel_effect'];
for (const id of ids) test(id + ': legacy conditions, metadata and callback payloads preserved', () => {
  const old = body(decisions.old, id), current = body(decisions.current, id);
  const metadata = nodes => nodes.filter(n => !['visible', 'available', ...callbackKeys].includes(n.key));
  assert.deepEqual(ast(metadata(current)), ast(metadata(old)), 'Cost, duration, AI or one-shot behavior changed');
  for (const key of ['visible', 'available']) {
    assert.equal(current.filter(n => n.key === key).length, 1, 'Duplicate/missing ' + key);
    assert.deepEqual(ast(body(current, key)), ast([...guard, ...body(old, key)]), 'Changed native ' + key);
  }
  const callbacks = old.filter(n => callbackKeys.includes(n.key));
  assert(callbacks.length > 0, 'Missing native effect');
  assert.deepEqual(current.filter(n => callbackKeys.includes(n.key)).map(n => n.key), callbacks.map(n => n.key));
  for (const callback of callbacks) {
    const wrapped = body(current, callback.key);
    assert.equal(wrapped.length, 1, 'Effects outside runtime guard');
    assert.equal(wrapped[0].key, 'if');
    assert.deepEqual(ast(body(wrapped[0].children, 'limit')), ast(guard));
    assert.deepEqual(ast(wrapped[0].children.filter(n => n.key !== 'limit')), ast(callback.children), 'Changed native payload');
  }
});
function world(flags) {
  return {BAR: new Set(flags), WIT: new Set(), ZES: new Set()};
}
function condition(nodes, w, scope) {
  return nodes.every(n => {
    if (['AND', 'hidden_trigger'].includes(n.key)) return condition(n.children, w, scope);
    if (n.key === 'OR') return n.children.some(c => condition([c], w, scope));
    if (n.key === 'NOT' || n.key === 'NOR') return !n.children.some(c => condition([c], w, scope));
    if (Object.hasOwn(w, n.key)) return condition(n.children, w, n.key);
    if (n.key === 'has_country_flag') return w[scope].has(n.value);
    if (n.key === 'always') return n.value === 'yes';
    if (n.key === 'tag' || n.key === 'original_tag') return n.value === scope;
    if (n.key === 'HSM_BAR_dip_route') {
      const flags = w[scope];
      const active = scope === 'BAR' && flags.has('HSM_BAR_active') &&
        flags.has('HSM_BAR_collegium') !== flags.has('HSM_BAR_directorate');
      return active === (n.value === 'yes');
    }
    throw Error('Unimplemented test predicate ' + n.key);
  });
}
// Record reached commands without executing game effects. Guard failures must
// prevent even reaching a native effect or scheduling its delayed event.
function trace(nodes, w, scope, out = []) {
  let matched = false;
  for (const n of nodes) {
    if (n.key === 'if' || n.key === 'else_if') {
      if (n.key === 'if') matched = false;
      if (!matched && condition(body(n.children, 'limit'), w, scope)) {
        matched = true;
        trace(n.children.filter(c => c.key !== 'limit'), w, scope, out);
      }
    } else if (n.key === 'else') {
      if (!matched) trace(n.children, w, scope, out);
      matched = true;
    } else if (Object.hasOwn(w, n.key)) trace(n.children, w, n.key, out);
    else if (n.key === 'hidden_effect') trace(n.children, w, scope, out);
    else if (!['name', 'trigger', 'ai_chance', 'log', 'custom_effect_tooltip'].includes(n.key)) {
      const target = n.children ? val(n.children, 'target') || val(n.children, 'id') || '' : n.value;
      out.push(scope + ':' + n.key + (target ? '=' + target : ''));
    }
  }
  return out;
}
test('legacy guards allow all old routes regardless of their native unlock flag', () => {
  for (const flags of [[], [unlockFlag], ['barrad_ambrosius_alive', unlockFlag]]) {
    assert(condition(guard, world(flags), 'BAR'));
  }
});
for (const id of ids) test(id + ': new paths and partial/stale saves cannot show, select or execute', () => {
  const current = body(decisions.current, id);
  for (let mask = 1; mask < 8; mask++) for (const unlocked of [false, true]) {
    const flags = routeFlags.filter((_, i) => mask & (1 << i));
    if (unlocked) flags.push(unlockFlag);
    const w = world(flags);
    assert(!condition(body(category.current, 'visible'), w, 'BAR'), 'Category visible: ' + flags);
    for (const key of ['visible', 'available']) {
      assert(!condition(body(current, key), w, 'BAR'), key + ': ' + flags);
    }
    for (const callback of current.filter(n => callbackKeys.includes(n.key))) {
      assert.deepEqual(trace(callback.children, w, 'BAR'), [], callback.key + ': ' + flags);
    }
  }
});
test('native war goals, claims and delayed-event IDs remain behind guarded effects', () => {
  const expected = [
    ['BAR_ambrosius_keep_promise_for_griffons', 'target', 'GRU'],
    ['BAR_ambrosius_high_kingdom_claims', 'target', 'OLV'],
    ['BAR_ambrosius_high_kingdom_claims', 'target', 'FRE'],
    ['BAR_ambrosius_high_kingdom_claims', 'add_claim_by', 'BAR'],
    ['BAR_ambrosius_strike_wittenland', 'target', 'WIT'],
    ['BAR_ambrosius_secure_steppe', 'target', 'GRY'],
    ['BAR_ambrosius_provoke_wittenlands', 'id', 'barrad_wit.1'],
    ['BAR_ambrosius_invite_back_ponies', 'id', 'barrad_ccamb.8']
  ];
  const contains = (nodes, key, value) => nodes.some(n => (n.key === key && n.value === value) || (n.children && contains(n.children, key, value)));
  for (const [id, key, value] of expected) assert(contains(body(body(decisions.current, id), 'complete_effect'), key, value), id + ': ' + value);
});

// Check options directly as well as event arrival: an already-open event can
// outlive the regime switch and must not grant a claim or declare war.
const eventText = read('mod/HoISubmod/events/Barrad Events.txt');
const nativeEventText = read('EaW/events/Barrad Events.txt');
const events = parse(eventText), nativeEvents = parse(nativeEventText);
const eventCases = [
  ['barrad_wit.1', 'WIT', ['barrad_wit.1.a', 'barrad_wit.1.b']],
  ['barrad_ccamb.8', 'ZES', ['barrad_ccamb.8.a']],
  ['barrad_ccamb.81', 'BAR', ['barrad_ccamb.81.a', 'barrad_ccamb.81.b']]
];
const actorGuard = parse('BAR = { NOT = { has_country_flag = HSM_BAR_active } }');
for (const [id, scope, optionIds] of eventCases) {
  const event = events.find(n => n.key === 'country_event' && val(n.children, 'id') === id);
  const native = nativeEvents.find(n => n.key === 'country_event' && val(n.children, 'id') === id);
  assert(event && native, 'Missing native event ' + id);
  const options = event.children.filter(n => n.key === 'option');
  const nativeOptions = native.children.filter(n => n.key === 'option');
  test(id + ': stripping only wrapper lines restores every native event byte', () => {
    assert.equal(events.filter(n => n.key === 'country_event' && val(n.children, 'id') === id).length, 1);
    assert.deepEqual(options.map(n => val(n.children, 'name')), optionIds);
    assert.deepEqual(nativeOptions.map(n => val(n.children, 'name')), optionIds);
    let restored = eventText.slice(event.start, event.end);
    for (const option of [...options].reverse()) {
      assert.deepEqual(option.children.map(n => n.key), ['name', 'if'], 'Unguarded effects or altered option metadata');
      const wrapper = prop(option.children, 'if');
      assert.deepEqual(ast(body(wrapper.children, 'limit')), ast(actorGuard), 'Guard must check BAR, not the event recipient');
      const start = eventText.lastIndexOf('\n', wrapper.start) + 1;
      const payloadStart = eventText.indexOf('\n', prop(wrapper.children, 'limit').end) + 1;
      const payloadEnd = eventText.lastIndexOf('\n', wrapper.end - 1) + 1;
      const end = eventText.indexOf('\n', wrapper.end) + 1;
      assert.equal(eventText.slice(start, payloadStart), '\t\tif = { limit = { BAR = { NOT = { has_country_flag = HSM_BAR_active } } }\r\n');
      assert.equal(eventText.slice(payloadEnd, end), '\t\t}\r\n');
      restored = restored.slice(0, start - event.start) + eventText.slice(payloadStart, payloadEnd) + restored.slice(end - event.start);
    }
    assert(Buffer.from(restored).equals(Buffer.from(nativeEventText.slice(native.start, native.end))), 'Native event bytes changed beyond wrappers');
  });
  test(id + ': BAR active flag alone gates effects regardless of WIT/ZES flags', () => {
    for (let mask = 0; mask < 8; mask++) for (const unlocked of [false, true]) {
      const w = world(unlocked ? [unlockFlag] : []);
      for (const [i, tag] of ['BAR', 'WIT', 'ZES'].entries()) {
        if (mask & (1 << i)) w[tag].add('HSM_BAR_active');
      }
      const original = nativeOptions.flatMap(option => trace(option.children, w, scope));
      assert(original.length > 0, 'Legacy positive control must execute native effects');
      const expected = w.BAR.has('HSM_BAR_active') ? [] : original;
      assert.deepEqual(options.flatMap(option => trace(option.children, w, scope)), expected, 'Country-scope regression: mask ' + mask);
    }
  });
  for (const route of ['collegium', 'directorate']) test(id + '/' + route + ': already-queued and already-open callbacks are inert', () => {
    for (const unlocked of [false, true]) {
      const flags = ['HSM_BAR_active', 'HSM_BAR_' + route];
      if (unlocked) flags.push(unlockFlag);
      const w = world(flags);
      const reached = options.flatMap(option => trace(option.children, w, scope)
        .map(effect => val(option.children, 'name') + ': ' + effect));
      assert.deepEqual(reached, [], 'Legacy callbacks remain active: ' + reached.join('; '));
      if (condition(body(event.children, 'trigger'), w, scope)) {
        assert.deepEqual(trace(body(event.children, 'immediate'), w, scope), [], 'Queued event has active immediate effects');
      }
    }
  });
}
console.log('RESULT ' + passed + ' passed, ' + failed + ' failed; deterministic script checks, not an HOI4 runtime test.');
if (failed) process.exitCode = 1;
'@
$javascript | & $nodeRuntime.Source - $root
if ($LASTEXITCODE -ne 0) {
    throw "Barrad legacy decision validation failed (Node exit code $LASTEXITCODE)."
}
