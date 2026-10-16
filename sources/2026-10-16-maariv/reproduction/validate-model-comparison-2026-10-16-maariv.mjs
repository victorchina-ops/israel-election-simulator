import fs from 'node:fs';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';

// Independently bind the like-for-like replays to the reviewed source plan,
// immutable pre-update snapshot, final website baseline and explicit defaults.
const root='artifacts/poll-checks/2026-10-16-maariv/';
const read=p=>JSON.parse(fs.readFileSync(p,'utf8').replace(/^\uFEFF/,''));
const sha=p=>createHash('sha256').update(fs.readFileSync(p)).digest('hex');
const stable=({generatedAt,...rest})=>rest;
const report=read(root+'model-comparison.json');
const replay=read(root+'model-comparison.after-replay.json');
const baseline=read('artifacts/dashboard-baseline.json');
const snapshot=read('dashboard/src/data.json');
const plan=read(root+'source-plan.json');
const ingestion=read(root+'ingestion-validation.json');
const checkpoint=read(root+'before/manifest.json');
const cfg=Object.fromEntries(snapshot.queries.model_configuration.rows.map(r=>[r.key,r.value]));
const input=Object.fromEntries(snapshot.queries.model_input.rows.map(r=>[r.key,r.value]));
assert.equal(plan.status,'reviewed');
assert.equal(plan.asOf,'2026-10-16');
assert.equal(ingestion.status,'PASS');
assert.equal(checkpoint.publishedHead,'367de70f0e889d64789a2db4c19b607803d83bd7');
assert.equal(checkpoint.historyPollCount,124);
assert.equal(plan.polls.length,1);
assert.equal(plan.polls[0].pollsterId,'lazar');
assert.equal(plan.polls[0].strictEligible,false);
const candidate=read(plan.polls[0].candidatePath);
assert.equal(sha(plan.polls[0].candidatePath),plan.polls[0].candidateSha256);
assert.equal(candidate.id,'lazar_2026-10-16');
assert.equal(candidate.sourceTier,'secondary-aggregator');
assert.equal(candidate.firstPublisherPublicationVerified,false);
assert.equal(candidate.sourceDocument.primaryPublicationVerified,false);
assert.equal(candidate.sourceRepostPublishedAtUtc,'2026-10-16T03:45:19Z');
for(const key of ['sampleSize','fieldworkStart','fieldworkEnd','samplingMethod','reportedMarginOfErrorPct','publishedAt'])assert.equal(candidate[key],null,key);
assert.equal(candidate.fieldworkVerified,false);
assert.deepEqual(candidate.sourceBlocSeats,{coalition:51,opposition:51,arab_parties:14,hendel:4});
assert.deepEqual(candidate.reportedPercentages,{gantz:1.1,haredi_public:0.5,noam:0.5});
assert.equal(candidate.seats.winter,4);assert.equal(candidate.seats.hendel,4);
assert.ok(!Object.hasOwn(candidate.reportedPercentages,'winter'));
assert.ok(!Object.hasOwn(candidate.reportedPercentages,'hendel'));
assert.deepEqual(replay.config,cfg);assert.deepEqual(replay.config,baseline.config);
assert.deepEqual(replay.input,input);assert.deepEqual(stable(replay.result),stable(baseline.result));
assert.equal(report.status,'passed');assert.equal(report.onlyControlDateDiffers,true);
assert.equal(snapshot.dataAsOf,plan.asOf);assert.equal(snapshot.features.chatGPT,false);
assert.equal(cfg.weightMode,'quality');
for(const key of ['includeChannel14','signalNoiseEnabled','pollCorrelationEnabled'])assert.equal(cfg[key],false);
assert.deepEqual(report.pollChanges.filter(p=>p.changed).map(p=>p.pollsterId),['lazar']);
assert.deepEqual(report.pollChanges.filter(p=>p.changed).flatMap(p=>p.afterIds),[candidate.id]);
for(const phase of ['before','after']){
 const r=read(root+`model-comparison.${phase}-replay.json`);
 const expectedSelected=r.input.current.polls.filter(p=>p.pollsterId!=='next_data').length;
 assert.equal(r.result.pollWeights.length,expectedSelected);
 assert.ok(r.result.pollWeights.every(p=>p.pollsterId!=='next_data'));
 assert.equal(r.result.checks.eachWorld120,true);
 assert.equal(r.input.current.asOf,phase==='before'?checkpoint.baselineAsOf:plan.asOf);
 assert.equal(r.input.current.polls.length,ingestion.activePollCount);
}
assert.equal(input.current.polls.length,8);assert.equal(ingestion.activePollCount,8);
assert.equal(input.history.polls.length,125);assert.equal(ingestion.historyPollCount,125);
const active=input.current.polls.find(p=>p.id===candidate.id);
assert.ok(active);assert.equal(active.sourceTier,candidate.sourceTier);
assert.equal(active.fieldworkVerified,false);assert.equal(active.sampleSize,null);
assert.ok(!input.current.polls.some(p=>p.id==='lazar_2026-10-13'));
assert.ok(input.current.polls.some(p=>p.id==='kantar_2026-10-15'));
assert.ok(input.current.polls.some(p=>p.id==='tatika_2026-10-15'));
for(const poll of input.current.polls)assert.equal(Object.values(poll.seats).reduce((a,b)=>a+b,0),120);
const old=read(root+'before/data/poll-history.json');
for(const p of old.polls){
 const expected={...p};
 // Replacing an active poll changes its lifecycle metadata, never its values,
 // source, dates or method. This is the one approved superseded record.
 if(p.id==='history_lazar_2026-10-13_current'){
  assert.equal(p.recordStatus,'current-reviewed-record');
  assert.ok(!Object.hasOwn(p,'replacedByPollId'));
  expected.recordStatus='superseded-reviewed-record';
  expected.replacedByPollId=candidate.id;
 }
 assert.deepEqual(input.history.polls.find(q=>q.id===p.id),expected,'Preserved historical observation '+p.id);
}
const output={status:'PASS',asOf:plan.asOf,currentReplayExactlyMatchesWebsiteBaseline:true,bothReplaysExcludeChannel14:true,
 activeSelectedInstitutes:replay.result.pollWeights.length,sameControlsExceptAsOf:true,allSimulatedWorldsHave120Seats:true,
 changedPollsters:['lazar'],newObservationIds:[candidate.id],publicationDates:[candidate.date],
 publicationDateScope:'First observed in the verified16Oct IsraelPolls repost; first publisher date/time and fieldwork remain unverified.',
 activePolls:8,historyPolls:125,unknownNewFieldworkExcluded:true,allPreviousHistoricalObservationsPreserved:true,supersededRecordLifecycleFieldsOnly:true,
 comparisonSha256:sha(root+'model-comparison.json'),snapshotSha256:sha('dashboard/src/data.json'),baselineSha256:sha('artifacts/dashboard-baseline.json'),sourcePlanSha256:sha(root+'source-plan.json'),
 validationScope:'Both snapshots replayed with the same unchanged model and explicit historical-accuracy website defaults. Model differences are not a significance test.'};
const file=root+'model-comparison-validation.json';
assert.ok(!fs.existsSync(file),'Do not overwrite a frozen receipt.');
fs.writeFileSync(file,JSON.stringify(output,null,2)+'\n');
console.log(JSON.stringify(output));
