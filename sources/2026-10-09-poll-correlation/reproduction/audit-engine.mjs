import fs from 'node:fs';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {createSimulation} from '../dashboard/src/content/dashboard/model/simulate.js';

const read=name=>JSON.parse(fs.readFileSync(name,'utf8').replace(/^\uFEFF/,''));
const sha=name=>createHash('sha256').update(fs.readFileSync(name)).digest('hex');
const out='artifacts/poll-correlation-2026-10-09';fs.mkdirSync(out,{recursive:true});
const before='artifacts/dependence-2022-toggle-2026-10-09/before';
const frozen=read(before+'/dashboard/src/data.json');
const input=Object.fromEntries(frozen.queries.model_input.rows.map(row=>[row.key,row.value]));
input.calibration={...input.calibration,pollCorrelation:read('data/poll-correlation.json')};
const base=Object.fromEntries(frozen.queries.model_configuration.rows.map(row=>[row.key,row.value]));
const previous={...Object.fromEntries(frozen.queries.simulation_summary.rows.map(row=>[row.key,row.value])),parties:frozen.queries.simulation_results.rows};
const run=config=>{const job=createSimulation(input,config);while(job.done<config.iterations)job.step(1000);return job.finish();};
const off=run({...base,pollCorrelationEnabled:false});
const exact=['iterations','parties','blocHist','blocStats','reportingGroups','coalitionHist','coalitionStats','counts','probabilities','probabilityCI','meanBallots','meanValid','meanTurnout','worlds','nEffective','methodWeights','pointProbabilities','expectedVotesRounded','turnout','checks'];
for(const key of exact)assert.deepEqual(off[key],previous[key],key);
const summarize=result=>({polls:result.pollWeights.length,weights:result.pollWeights,nEffective:result.nEffective,
 meanSeats:Object.fromEntries(Object.entries(result.blocStats).map(([key,value])=>[key,value.mean])),
 winterPass:result.parties.find(row=>row.id==='winter').passProbability,
 hendelPass:result.parties.find(row=>row.id==='hendel').passProbability,
 majority:result.probabilities,checks:result.checks,correlation:result.pollCorrelation??null,
 signalNoiseCorrelation:result.signalNoise?.pollCorrelation??null});
const results=[];
for(const includeChannel14 of [false,true])for(const signalNoiseEnabled of [false,true]){
 const result=run({...base,includeChannel14,signalNoiseEnabled,pollCorrelationEnabled:true});
 assert.equal(result.checks.eachWorld120,true);assert.equal(result.checks.blocPartition120,true);
 assert.equal(result.pollCorrelation.enabled,true);
 assert.ok(result.nEffective===null||Number.isFinite(result.nEffective));
 assert.equal(result.parties.reduce((s,row)=>s+row.mean,0).toFixed(6),'120.000000');
 results.push({includeChannel14,signalNoiseEnabled,...summarize(result)});
}
const immutablePaths=['data/current-polls.json','data/poll-history.json','data/calibration.json','data/history/final-polls-2022.json','data/weight-presets.json','data/strict-party-trends.json','data/strict-party-trends-without-channel14.json','data/signal-noise-observations.json'];
const preserved=immutablePaths.map(name=>{assert.equal(sha(name),sha(before+'/'+name),name);return {path:name,sha256:sha(name)};});
const report={status:'PASS',newPollCount:0,frozenPublicCommit:'f3d7dd03a077d321f767708ed2dadcd5ad7c78fe',iterations:base.iterations,exactOffNumericalCollections:exact,
 off:summarize(off),on:results,historicalAccuracyUnchanged:true,immutableFiles:preserved,profileSha256:sha('data/poll-correlation.json'),
 significance:'Audited historical-accuracy tests unchanged; similarity is not a validated error covariance. Interactive sign-flip p/q hidden when ON.'};
fs.writeFileSync(out+'/engine-audit.json',JSON.stringify(report,null,2)+'\n');
console.log(JSON.stringify({status:report.status,offExactlyRestored:true,checkedOnScenarios:results.length,off:summarize(off),on:results.map(row=>({includeChannel14:row.includeChannel14,signalNoiseEnabled:row.signalNoiseEnabled,meanSeats:row.meanSeats,nEffective:row.nEffective,winterPass:row.winterPass,hendelPass:row.hendelPass,checks:row.checks}))},null,2));
