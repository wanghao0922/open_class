// Run: node tests/test_preload_images.cjs (after frontend npm ci).
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const ts = require('../frontend/node_modules/typescript');
const source = fs.readFileSync(require.resolve('../frontend/src/preloadImages.ts'), 'utf8');

function setup() {
 const images=[];const timers=new Map();let sequence=0;
 class FakeImage {
  constructor(){images.push(this);}
  set src(value){this.url=value;}
  removeAttribute(){this.aborted=true;}
 }
 const context={exports:{},Image:FakeImage,URL,location:{origin:'https://classroom.test'},
  setTimeout:fn=>{const id=++sequence;timers.set(id,fn);return id;},clearTimeout:id=>timers.delete(id)};
 vm.runInNewContext(ts.transpileModule(source,{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText,context);
 return {start:context.exports.preloadImages,images,timers};
}

(async()=>{
 const {start,images,timers}=setup();
 const queue=start(['/active.webp','/second.webp','/slow.webp','/next.webp','/last.webp','/next.webp']);
 assert.equal(images.length,3);
 assert.ok(images.every(image=>image.fetchPriority==='low'));
 images[1].onerror();await Promise.resolve();
 assert.equal(images.length,4,'failure must not wait for the other workers');
 images[3].onload();await Promise.resolve();
 assert.equal(images.length,5,'duplicate URLs must be removed');
 // Simulate timeouts on remaining requests; the queue must still complete.
 for(const timeout of [...timers.values()])timeout();
 await queue.done;assert.equal(timers.size,0);
 const other=setup();const cancelled=other.start(['/one','/two','/three','/never']);
 cancelled.cancel();await cancelled.done;
 assert.equal(other.images.length,3,'cancellation must stop new requests');
 assert.ok(other.images.every(image=>image.aborted));assert.equal(other.timers.size,0);
 console.log('PASS: concurrency, ordering, failures, timeout, deduplication and cancellation');
})().catch(error=>{console.error(error);process.exit(1);});
