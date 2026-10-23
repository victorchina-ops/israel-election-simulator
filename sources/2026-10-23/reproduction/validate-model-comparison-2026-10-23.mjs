import fs from 'node:fs';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
const art='artifacts/poll-checks/2026-10-23/';
const read=p=>JSON.parse(fs.readFileSync(p,'utf8').replace(/^\uFEFF/,''));
const sha=p=>createHash('sha256').update(fs.readFileSync(p)).digest('hex');
const inputFrom=s=>Object.fromEntries(s.queries.model_input.rows.map(r=>[r.key,r.value]));
const configFrom=s=>Object.fromEntries(s.queries.model_configuration.rows.map(r=>[r.key,r.value]));
const stable=({generatedAt,...rest})=>rest;
const plan=read(art+'source-plan.json'),checked=read(art+'ingestion-validation.json');
const checkpoint=read(art+'before/manifest.json'),snapshot=read('dashboard/src/data.json');
const comparison=read(art+'model-comparison.json'),baseline=read('artifacts/dashboard-baseline.json');
const replay=read(art+'model-comparison.after-replay.json');
const input=inputFrom(snapshot),config=configFrom(snapshot),oldSnapshot=read(art+'before/dashboard/src/data.json');
assert.equal(plan.status,'reviewed');assert.equal(plan.asOf,'2026-10-23');assert.equal(checked.status,'PASS');
const changed=plan.polls.map(p=>p.pollsterId).sort();
assert.deepEqual(comparison.pollChanges.filter(p=>p.changed).map(p=>p.pollsterId).sort(),changed);
assert.equal(comparison.status,'passed');assert.equal(comparison.onlyControlDateDiffers,true);
assert.deepEqual(replay.config,config);assert.deepEqual(baseline.config,config);
assert.deepEqual(replay.input,input);assert.deepEqual(stable(replay.result),stable(baseline.result));
assert.equal(snapshot.dataAsOf,plan.asOf);assert.equal(snapshot.features.chatGPT,false);
assert.equal(config.weightMode,'quality');
for(const key of ['includeChannel14','pollCorrelationEnabled','signalNoiseEnabled'])assert.equal(config[key],false);
assert.equal(config.partyBlocs.winter,'a');assert.equal(config.partyBlocs.hendel,'other');
assert.equal(input.current.polls.length,checkpoint.activePollCount);
assert.equal(input.history.polls.length,checkpoint.historyPollCount+plan.polls.length);
assert.equal(checked.historyPollCount,input.history.polls.length);
for(const spec of plan.polls){
 assert.equal(sha(spec.candidatePath),spec.candidateSha256);
 const candidate=read(spec.candidatePath),active=input.current.polls.find(p=>p.id===candidate.id);
 assert.ok(active);
 for(const key of ['seats','reportedPercentages'])assert.deepEqual(active[key],candidate[key]);
 assert.deepEqual(active.publishedBounds??{},candidate.publishedBounds??{});
 for(const key of ['date','sampleSize','fieldworkStart','fieldworkEnd','fieldworkVerified','sourceTier'])assert.deepEqual(active[key],candidate[key],key);
 assert.ok(!input.current.polls.some(p=>p.id===candidate.replacesPollId));
 assert.ok(input.history.polls.some(p=>p.sourcePollId===candidate.replacesPollId));
}
const lifecycle=Object.fromEntries(plan.polls.map(s=>{const c=read(s.candidatePath);return ['history_'+c.replacesPollId+'_current',c.id];}));
for(const row of read(art+'before/data/poll-history.json').polls){
 const expected={...row};if(lifecycle[row.id])Object.assign(expected,{recordStatus:'superseded-reviewed-record',replacedByPollId:lifecycle[row.id]});
 assert.deepEqual(input.history.polls.find(p=>p.id===row.id),expected,row.id);
}
const selected=input.current.polls.filter(p=>p.pollsterId!=='next_data').length;
for(const [stem,enabled] of [['model-comparison',false],['model-comparison-similarity',true]])for(const phase of ['before','after']){
 const r=read(art+`${stem}.${phase}-replay.json`),expected=phase==='before'?inputFrom(oldSnapshot):input;
 assert.deepEqual(r.input,expected);
 assert.equal(r.config.pollCorrelationEnabled,enabled);assert.equal(r.config.includeChannel14,false);assert.equal(r.config.signalNoiseEnabled,false);
 assert.equal(r.config.weightMode,'quality');assert.equal(r.config.partyBlocs.winter,'a');assert.equal(r.config.partyBlocs.hendel,'other');
 assert.equal(r.config.iterations,10000);assert.equal(r.config.seed,20260912);
 assert.equal(r.result.pollWeights.length,selected);assert.ok(r.result.pollWeights.every(p=>p.pollsterId!=='next_data'));
 assert.equal(r.result.checks.eachWorld120,true);assert.equal(r.input.current.asOf,expected.current.asOf);
 for(const p of r.input.current.polls)assert.equal(Object.values(p.seats).reduce((a,b)=>a+b,0),120);
}
const output={status:'PASS',asOf:plan.asOf,currentReplayExactlyMatchesWebsiteBaseline:true,bothReplaysExcludeChannel14:true,
 sameControlsExceptAsOf:true,allSimulatedWorldsHave120Seats:true,activeSelectedInstitutes:selected,changedPollsters:changed,
 newObservationIds:plan.polls.map(s=>read(s.candidatePath).id),publicationDates:plan.polls.map(s=>read(s.candidatePath).date),
 activePolls:input.current.polls.length,historyPolls:input.history.polls.length,allPreviousHistoricalObservationsPreserved:true,
 comparisonSha256:sha(art+'model-comparison.json'),snapshotSha256:sha('dashboard/src/data.json'),baselineSha256:sha('artifacts/dashboard-baseline.json'),
 sourcePlanSha256:sha(art+'source-plan.json'),validationScope:'Both endpoints replay the unchanged model; conditional differences are not a significance test.'};
const file=art+'model-comparison-validation.json';assert.ok(!fs.existsSync(file),'Preserve dated validation');
fs.writeFileSync(file,JSON.stringify(output,null,2)+'\n');console.log(JSON.stringify(output));
