// Reuse the pinned unchanged replay programs for site defaults and the reporting preference.
import fs from 'node:fs';
import path from 'node:path';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {spawnSync} from 'node:child_process';
const root=process.cwd(), art='artifacts/poll-checks/2026-10-24';
const read=p=>JSON.parse(fs.readFileSync(p,'utf8').replace(/^\uFEFF/,''));
const sha=p=>createHash('sha256').update(fs.readFileSync(p)).digest('hex');
const frozen=read(art+'/before/manifest.json'),plan=read(art+'/source-plan.json');
assert.equal(plan.asOf,'2026-10-24');
assert.equal(read(art+'/strict-validation.json').status,'PASS');
assert.equal(read('dashboard/src/data.json').dataAsOf,plan.asOf);
for(const [script,stem] of [['scripts/compare-poll-update.mjs','model-comparison'],['scripts/compare-poll-update-similarity-2026-10-20-evening.mjs','model-comparison-similarity']]){
 assert.equal(sha(script),frozen.files[script]);
 const out=path.join(art,stem+'.json');
 for(const file of [out,out.replace(/\.json$/,'.before-replay.json'),out.replace(/\.json$/,'.after-replay.json')])assert.ok(!fs.existsSync(file),'Preserve dated replay: '+file);
 const result=spawnSync(process.execPath,[script,'--before='+path.join(art,'before/dashboard/src/data.json'),'--after=dashboard/src/data.json','--out='+out,'--opposition=none','--weight-mode=quality'],{cwd:root,encoding:'utf8',maxBuffer:8*1024*1024});
 fs.writeFileSync(path.join(art,stem+'.log'),result.stdout+result.stderr,{flag:'wx'});
 assert.equal(result.status,0,result.stderr);
 console.log(result.stdout);
}
