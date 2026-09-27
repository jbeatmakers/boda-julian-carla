const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const src=fs.readFileSync('js/public-pista.js','utf8');
function run(hasRelease){
  let replaced='';
  const context={Date,URL,document:{querySelector(){return hasRelease?{content:'current'}:null}},window:{location:{hash:'#rsvp',replace(v){replaced=v}}}};
  context.location=context.window.location;
  vm.runInNewContext(src,context);
  return replaced;
}
assert.equal(run(true),'','Current invitation must not be redirected by legacy shim');
const target=run(false);
assert.match(target,/^https:\/\/bodajulianycarla\.bpm\.red\/actualizar\.html\?/);
assert.match(target,/legacy=1/);
assert.match(target,/#rsvp$/);
const updater=fs.readFileSync('actualizar.html','utf8');
assert.match(updater,/20260927-access-2/);
assert.doesNotMatch(updater,/20260927-access-1/);
console.log('PASS: legacy cached invitation is recovered to current BODA release');
