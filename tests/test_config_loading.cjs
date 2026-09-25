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
    assert(failed.node('site').classList.contains('hidden'), 'Never reveal old defaults after a failure');
    assert(!failed.node('configRetry').classList.contains('hidden'));
    assert.equal(failed.context.applied, undefined);
    failed.context.fetch = async () => ({ok:true, json:async () => ({ticket:{enabled:true,price:90000,text:'Updated'}, copy:{},ceremony:{},celebration:{}})});
    await failed.context.openInvitation(false);
    assert.equal(failed.context.applied.ticket.price, 90000, 'Retry must fetch fresh settings');
    assert(!failed.node('site').classList.contains('hidden'));
  }
  console.log('PASS: slow response, current settings, network/HTTP/invalid responses, and retry');
})().catch(error => { console.error(error); process.exitCode = 1; });
