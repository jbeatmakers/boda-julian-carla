const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync('assets/app.js', 'utf8');

function setup(fetch) {
  const nodes = new Map();
  function node(id) {
    if (!nodes.has(id)) {
      const classes = new Set(id === 'site' ? ['hidden'] : []);
      nodes.set(id, {textContent: '', classList: {
        add: c => classes.add(c), remove: c => classes.delete(c),
        contains: c => classes.has(c)
      }});
    }
    return nodes.get(id);
  }
  const context = vm.createContext({structuredClone, AbortController, setTimeout, clearTimeout,
    fetch, document: {getElementById: node, addEventListener() {},
      querySelector: () => ({content: 'https://example.test'}), body: node('body')}});
  // Observe the reveal order while keeping unrelated rendering and network calls out of this test.
  vm.runInContext(source.replace(/\}\)\(\);\s*$/, `
    globalThis.openInvitation = unlock;
    applyConfig = c => { globalThis.applied = c; globalThis.hiddenWhenApplied = $('site').classList.contains('hidden'); };
    startCountdown = loadInstagram = flushOutbox = () => {};
  })();`), context);
  return {context, node};
}

(async () => {
  let resolve;
  const state = setup(() => new Promise(r => { resolve = r; }));
  const pending = state.context.openInvitation(false);
  assert(state.node('site').classList.contains('hidden'), 'Must remain hidden during a slow request');
  resolve({ok: true, json: async () => ({ticket: {enabled: true, price: 80000, text: 'Actual'}, copy: {}, ceremony: {}, celebration: {time: '19:00'}})});
  await pending;
  assert.equal(state.context.applied.ticket.price, 80000);
  assert.equal(state.context.applied.celebration.time, '19:00');
  assert(state.context.hiddenWhenApplied, 'Apply current content before revealing the invitation');
  assert(!state.node('site').classList.contains('hidden'));

  for (const fetch of [async () => {throw new Error('offline');}, async () => ({ok:true, json:async () => ({})}), async () => ({ok:false, json:async () => ({})})]) {
    const failed = setup(fetch);
    await failed.context.openInvitation(false);
    assert(!failed.node('site').classList.contains('hidden'), 'Accepted BODA must reveal the invitation even if config fails');
    assert(failed.node('configRetry').classList.contains('hidden'));
    assert(failed.context.applied, 'Fallback config must be applied when the live config is unavailable');
  }
  console.log('PASS: slow response, current settings, and network/HTTP/invalid config fallback');
})().catch(error => { console.error(error); process.exitCode = 1; });
