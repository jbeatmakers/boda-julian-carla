const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

const source = fs.readFileSync('assets/app.js', 'utf8');

function page({code, storageThrows = false, missingRetry = false, failures = 0} = {}) {
  const elements = new Map();
  const listeners = new Map();
  let configRequests = 0;
  let storedAccess;
  const element = id => {
    if (missingRetry && id === 'configRetry') return null;
    if (!elements.has(id)) {
      const classes = new Set(id === 'site' ? ['hidden'] : []);
      elements.set(id, {
        id, value: '', textContent: '', dataset: {}, tagName: 'DIV',
        classList: {
          contains: name => classes.has(name),
          add: name => classes.add(name),
          remove: name => classes.delete(name),
          toggle: (name, force) => force ? classes.add(name) : classes.delete(name)
        },
        addEventListener(name, fn) { listeners.set(`${id}:${name}`, fn); },
        select() {},
      });
    }
    return elements.get(id);
  };
  const context = {
    JSON, Date, Intl, Number, Object, Map, Array, String, Math,
    // Old browser simulation: no structuredClone global.
    structuredClone: undefined,
    AbortController, setTimeout, clearTimeout, setInterval() {},
    requestAnimationFrame(fn) { fn(); },
    matchMedia() { return {matches: true}; },
    navigator: {onLine: true},
    localStorage: {getItem() { return '[]'; }},
    sessionStorage: {
      getItem() { if (storageThrows) throw Error('storage unavailable'); return storedAccess; },
      setItem(_key, value) { if (storageThrows) throw Error('storage unavailable'); storedAccess = value; }
    },
    document: {
      body: {classList: {remove() {}}}, hidden: false,
      getElementById: element,
      querySelector(selector) {
        if (selector === 'meta[name="wedding-api"]') return {content: 'https://api.example.test'};
        if (selector === 'input[name="attendance"]:checked') return {value: 'yes'};
        return null;
      },
      querySelectorAll() { return []; },
      addEventListener(name, fn) { listeners.set(`document:${name}`, fn); }
    },
    window: {addEventListener(name, fn) { listeners.set(`window:${name}`, fn); }},
    fetch: async url => {
      if (!url.endsWith('/api/public/config')) throw Error(`unexpected fetch: ${url}`);
      configRequests++;
      if(failures-- > 0) throw Error('network unavailable');
      return {ok: true, json: async () => ({ticket: {enabled: false}, copy: {}, ceremony: {}, celebration: {}})};
    }
  };
  vm.runInNewContext(source, context);
  listeners.get('document:DOMContentLoaded')();
  element('gateCode').value = code;
  return {
    async submit() {
      await listeners.get('gateForm:submit')({preventDefault() {}});
      await new Promise(resolve => setImmediate(resolve));
    },
    get unlocked() { return !element('site').classList.contains('hidden'); },
    get error() { return element('gateError').textContent; },
    get configRequests() { return configRequests; },
    get storedAccess() { return storedAccess; },
    get onlineListenerRegistered() { return listeners.has('window:online'); }
    ,async reconnect() { await listeners.get('window:online')(); }
  };
}

(async () => {
  const blockedStorage = page({code: ' \u200bbO\u200ddA\u00a0', storageThrows: true, missingRetry: true});
  await blockedStorage.submit();
  assert.equal(blockedStorage.unlocked, true, 'BODA should open when storage throws and retry button is absent');
  assert.equal(blockedStorage.configRequests, 1);
  assert.equal(blockedStorage.onlineListenerRegistered, true, 'storage read must not stop event setup');

  const normal = page({code: 'bOdA'});
  await normal.submit();
  assert.equal(normal.unlocked, true);
  assert.equal(normal.storedAccess, 'ok');

  const interrupted = page({code:'boda', failures:3, storageThrows:true});
  await interrupted.submit();
  await new Promise(resolve=>setTimeout(resolve,1800));
  assert.equal(interrupted.unlocked,false);
  assert.match(interrupted.error,/Código aceptado/);
  await interrupted.reconnect();
  assert.equal(interrupted.unlocked,true,'Connection recovery opens automatically without entering BODA again');

  for (const code of ['18dic', 'dic23', 'otro']) {
    const wrong = page({code});
    await wrong.submit();
    assert.equal(wrong.unlocked, false, `${code} must remain rejected`);
    assert.equal(wrong.configRequests, 0);
    assert.match(wrong.error, /no coincide/);
  }
  console.log('PASS: BODA gate opens with blocked storage and no structuredClone; old/wrong codes stay rejected');
})().catch(error => { console.error(error); process.exitCode = 1; });
