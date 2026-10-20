import fs from 'node:fs';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';

const art='artifacts/poll-checks/2026-10-20/';
const read=p=>JSON.parse(fs.readFileSync(p,'utf8').replace(/^\uFEFF/,''));
const sha=p=>createHash('sha256').update(fs.readFileSync(p)).digest('hex');
const stable=({generatedAt,...rest})=>rest;
const plan=read(art+'source-plan.json'),checked=read(art+'ingestion-validation.json');
const checkpoint=read(art+'before/manifest.json'),snapshot=read('dashboard/src/data.json');
const comparison=read(art+'model-comparison.json'),baseline=read('artifacts/dashboard-baseline.json');
const replay=read(art+'model-comparison.after-replay.json');
const config=Object.fromEntries(snapshot.queries.model_configuration.rows.map(r=>[r.key,r.value]));
const input=Object.fromEntries(snapshot.queries.model_input.rows.map(r=>[r.key,r.value]));
assert.equal(plan.status,'reviewed');assert.equal(plan.asOf,'2026-10-20');
assert.equal(checked.status,'PASS');assert.equal(checkpoint.historyPollCount,128);
assert.equal(checkpoint.publishedHead,'769317e59fcfe29e610d24dc4944cdbc6ff8188f');
const changed=['hamadad_consortium','lazar','midgam_geva','next_data'];
assert.deepEqual(plan.polls.map(p=>p.pollsterId).sort(),changed);
assert.deepEqual(comparison.pollChanges.filter(p=>p.changed).map(p=>p.pollsterId).sort(),changed);
assert.equal(comparison.status,'passed');assert.equal(comparison.onlyControlDateDiffers,true);
assert.deepEqual(replay.config,config);assert.deepEqual(baseline.config,config);
assert.deepEqual(replay.input,input);assert.deepEqual(stable(replay.result),stable(baseline.result));
assert.equal(snapshot.dataAsOf,plan.asOf);assert.equal(snapshot.features.chatGPT,false);
assert.equal(config.weightMode,'quality');
for(const key of ['includeChannel14','pollCorrelationEnabled','signalNoiseEnabled'])assert.equal(config[key],false);
assert.equal(input.current.polls.length,8);assert.equal(input.history.polls.length,132);
assert.equal(checked.historyPollCount,132);
for(const spec of plan.polls){
 assert.equal(sha(spec.candidatePath),spec.candidateSha256);
 const candidate=read(spec.candidatePath),active=input.current.polls.find(p=>p.id===candidate.id);
 assert.ok(active);assert.deepEqual(active.seats,candidate.seats);
 assert.deepEqual(active.reportedPercentages,candidate.reportedPercentages);
 assert.deepEqual(active.publishedBounds??{},candidate.publishedBounds??{});
 for(const key of ['sampleSize','fieldworkStart','fieldworkEnd','fieldworkVerified','sourceTier'])assert.equal(active[key],candidate[key],key);
 assert.ok(!input.current.polls.some(p=>p.id===candidate.replacesPollId));
 assert.ok(input.history.polls.some(p=>p.sourcePollId===candidate.replacesPollId));
 assert.equal(active.fieldworkVerified,spec.strictEligible);
}
const expectedLifecycle=Object.fromEntries(plan.polls.map(s=>{const c=read(s.candidatePath);return ['history_'+c.replacesPollId+'_current',c.id];}));
const old=read(art+'before/data/poll-history.json');
for(const row of old.polls){
 const expected={...row};
 if(expectedLifecycle[row.id])Object.assign(expected,{recordStatus:'superseded-reviewed-record',replacedByPollId:expectedLifecycle[row.id]});
 assert.deepEqual(input.history.polls.find(p=>p.id===row.id),expected,row.id);
}
for(const phase of ['before','after']){
 const r=read(art+`model-comparison.${phase}-replay.json`);
 assert.equal(r.result.pollWeights.length,7);
 assert.ok(r.result.pollWeights.every(p=>p.pollsterId!=='next_data'));
 assert.equal(r.result.checks.eachWorld120,true);
 assert.equal(r.input.current.asOf,phase==='before'?'2026-10-19':'2026-10-20');
 for(const p of r.input.current.polls)assert.equal(Object.values(p.seats).reduce((a,b)=>a+b,0),120);
}
const output={status:'PASS',asOf:plan.asOf,currentReplayExactlyMatchesWebsiteBaseline:true,bothReplaysExcludeChannel14:true,sameControlsExceptAsOf:true,allSimulatedWorldsHave120Seats:true,activeSelectedInstitutes:7,changedPollsters:changed,newObservationIds:plan.polls.map(s=>read(s.candidatePath).id),publicationDates:plan.polls.map(s=>read(s.candidatePath).date),activePolls:8,historyPolls:132,allPreviousHistoricalObservationsPreserved:true,comparisonSha256:sha(art+'model-comparison.json'),snapshotSha256:sha('dashboard/src/data.json'),baselineSha256:sha('artifacts/dashboard-baseline.json'),sourcePlanSha256:sha(art+'source-plan.json'),validationScope:'Both endpoints use the identical unchanged model and explicit historical-accuracy default settings; differences are not a significance test.'};
const file=art+'model-comparison-validation.json';assert.ok(!fs.existsSync(file),'Preserve dated validation');
fs.writeFileSync(file,JSON.stringify(output,null,2)+'\n');console.log(JSON.stringify(output));
