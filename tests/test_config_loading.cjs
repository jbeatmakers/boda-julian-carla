const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync('assets/app.js','utf8');
function setup(fetch){
  const nodes=new Map();
  function node(id){
    if(!nodes.has(id)){
      const classes=new Set(id==='site'?['hidden']:[]);
      nodes.set(id,{textContent:'',classList:{add:c=>classes.add(c),remove:c=>classes.delete(c),contains:c=>classes.has(c),toggle:(c,b)=>b?classes.add(c):classes.delete(c)}});
    }
    return nodes.get(id);
  }
  const context=vm.createContext({AbortController,setTimeout,clearTimeout,fetch,
    document:{getElementById:node,addEventListener(){},querySelector:()=>({content:'https://api.example.test'}),body:node('body')}});
  vm.runInContext(source.replace(/\}\)\(\);\s*$/,`
    globalThis.openInvitation=unlock;
    globalThis.refresh=refreshPublicConfig;
    applyConfig=c=>{globalThis.applied=c;};
    startCountdown=()=>{};
    loadInstagram=flushOutbox=async()=>{};
  })();`),context);
  return {context,node};
}
const valid=(price=80000)=>({ticket:{enabled:true,price,text:'Actual'},copy:{},ceremony:{time:'17:00'},celebration:{time:'19:00'}});
(async()=>{
  let resolve,requests=0;
  const slow=setup(()=>{requests++;return new Promise(r=>{resolve=r;});});
  await slow.context.openInvitation(false);
  assert(!slow.node('site').classList.contains('hidden'),'BODA must open without waiting for a slow API');
  assert.equal(slow.context.applied,undefined,'Never apply old/default prices while waiting');
  assert(slow.node('ticketCard').classList.contains('hidden'));
  const pending=slow.context.refresh();
  assert.equal(requests,1,'Refreshes share one in-flight config request');
  resolve({ok:true,json:async()=>valid()});
  assert.equal(await pending,true);
  assert.equal(slow.context.applied.ticket.price,80000);
  assert.equal(slow.context.applied.celebration.time,'19:00');
  assert(slow.node('configStatus').classList.contains('hidden'));
  for(const fetch of [async()=>{throw Error('offline');},async()=>({ok:true,json:async()=>({})}),async()=>({ok:false,status:503,json:async()=>({})}),async()=>({ok:true,json:async()=>{throw Error('bad JSON');}})]){
    const failed=setup(fetch);
    await failed.context.openInvitation(false);
    assert(!failed.node('site').classList.contains('hidden'),'Config failure must not lock out a guest');
    assert.equal(await failed.context.refresh(),false);
    assert.equal(failed.context.applied,undefined,'Unverified defaults must never appear as current settings');
    assert(failed.node('ticketCard').classList.contains('hidden'));
    assert(!failed.node('configRetryInline').classList.contains('hidden'));
    failed.context.fetch=async()=>({ok:true,json:async()=>valid(90000)});
    assert.equal(await failed.context.refresh(),true);
    assert.equal(failed.context.applied.ticket.price,90000);
  }
  console.log('PASS: BODA never waits for config; no stale prices; single-flight; HTTP/JSON/network failure and recovery');
})().catch(e=>{console.error(e);process.exitCode=1;});
