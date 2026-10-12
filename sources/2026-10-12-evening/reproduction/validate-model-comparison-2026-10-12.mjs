import fs from 'node:fs';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
const read=p=>JSON.parse(fs.readFileSync(p,'utf8').replace(/^\uFEFF/,''));
const root='artifacts/poll-checks/2026-10-12-evening/';
const report=read(root+'model-comparison.json');
const replay=read(root+'model-comparison.after-replay.json');
const baseline=read('artifacts/dashboard-baseline.json');
const snapshot=read('dashboard/src/data.json');
const cfg=Object.fromEntries(snapshot.queries.model_configuration.rows.map(r=>[r.key,r.value]));
assert.deepEqual(replay.config,cfg);
assert.deepEqual(replay.config,baseline.config);
const stableResult=({generatedAt,...rest})=>rest;
assert.deepEqual(stableResult(replay.result),stableResult(baseline.result));
assert.equal(report.onlyControlDateDiffers,true);
for(const key of ['includeChannel14','signalNoiseEnabled','pollCorrelationEnabled'])assert.equal(cfg[key],false);
assert.deepEqual(report.pollChanges.filter(p=>p.changed).map(p=>p.pollsterId).sort(),['midgam_geva','next_data']);
for(const phase of ['before','after']){
 const r=read(root+`model-comparison.${phase}-replay.json`);
 assert.equal(r.result.pollWeights.length,7);
 assert.ok(r.result.pollWeights.every(p=>p.pollsterId!=='next_data'));
 assert.equal(r.result.checks.eachWorld120,true);
}
const digest=p=>createHash('sha256').update(fs.readFileSync(p)).digest('hex');
const output={status:'PASS',asOf:'2026-10-12',currentReplayExactlyMatchesWebsiteBaseline:true,bothReplaysExcludeChannel14:true,activeSelectedInstitutes:7,sameControlsExceptAsOf:true,allSimulatedWorldsHave120Seats:true,comparisonSha256:digest(root+'model-comparison.json'),snapshotSha256:digest('dashboard/src/data.json'),baselineSha256:digest('artifacts/dashboard-baseline.json'),validationScope:'Explicit flags and actual selected weights are bound to the website defaults; archive results are never reused.'};
fs.writeFileSync(root+'model-comparison-validation.json',JSON.stringify(output,null,2)+'\n');
console.log(JSON.stringify(output));
