const vm=require('node:vm'),fs=require('node:fs'),assert=require('node:assert/strict');
const source=fs.readFileSync('assets/updates.js','utf8');
async function run({next='old',disabled=false,offline=false,draft=null,fail=false}={}){
  let pageshow,reloaded,saved,removed=false,changed=false;
  const name={id:'fullName',name:'',type:'text',value:'Invitado'};
  const seats={id:'seats',name:'',type:'select-one',options:[{value:'1'}],selected:'1',
    get value(){return this.selected},set value(v){this.selected=this.options.some(o=>o.value===v)?v:''},
    appendChild(o){this.options.push(o)}};
  const context={URL,AbortController,setTimeout,clearTimeout,setInterval(){},Date,JSON,Event,
    navigator:{onLine:!offline},sessionStorage:{getItem(){return JSON.stringify(draft)},removeItem(){removed=true},setItem(k,v){saved=JSON.parse(v)}},
    document:{hidden:false,createElement(){return {}},
      querySelector(s){return s.includes('meta')?{content:'old'}:s.includes('attendance')?{dispatchEvent(){changed=true}}:{disabled}},
      querySelectorAll(){return [name,seats]},addEventListener(){}},
    window:{location:{href:'https://example.test/#rsvp',replace(v){reloaded=v}},addEventListener(n,f){if(n==='pageshow')pageshow=f}},
    DOMParser:class{parseFromString(){return {querySelector(){return next?{content:next}:null}}}},
    fetch:async()=>{if(fail)throw Error('offline');return {ok:true,text:async()=>''}}};
  vm.runInNewContext(source,context);pageshow();await new Promise(r=>setTimeout(r,0));
  return {reloaded,saved,removed,changed,seats,name};
}
(async()=>{
  assert.equal((await run()).reloaded,undefined);
  const updated=await run({next:'new'});
  assert.equal(updated.reloaded,'https://example.test/?_v=new#rsvp');
  assert.equal(updated.saved.fields[0].value,'Invitado');
  for(const args of [{next:'new',disabled:true},{next:'new',offline:true},{next:'new',fail:true},{next:null}])
    assert.equal((await run(args)).reloaded,undefined);
  const restored=await run({draft:{savedAt:Date.now(),fields:[{id:'seats',name:'',value:'4'},{id:'fullName',name:'',value:'Borrador'}]}});
  assert.equal(restored.seats.value,'4');assert.equal(restored.name.value,'Borrador');assert(restored.changed);assert(restored.removed);
  const expired=await run({draft:{savedAt:0,fields:[{id:'fullName',name:'',value:'Expired'}]}});
  assert.equal(expired.name.value,'Invitado');
  console.log('PASS: release detection, cache-busting URL, offline/errors, active submission, draft/seat restoration and expiry');
})().catch(e=>{console.error(e);process.exitCode=1});
