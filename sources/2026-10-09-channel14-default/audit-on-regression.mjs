import fs from 'node:fs';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {runSimulation} from '../dashboard/src/content/dashboard/model/simulate.js';
const root=new URL('../',import.meta.url);
const read=path=>JSON.parse(fs.readFileSync(new URL(path,root),'utf8').replace(/^\uFEFF/,''));
const hash=path=>createHash('sha256').update(fs.readFileSync(new URL(path,root))).digest('hex');
const snapshot=read('artifacts/channel14-default-2026-10-09/before/dashboard/src/data.json');
const previous=Object.fromEntries(snapshot.queries.simulation_summary.rows.map(row=>[row.key,row.value]));
previous.parties=snapshot.queries.simulation_results.rows;
const config=Object.fromEntries(snapshot.queries.model_configuration.rows.map(row=>[row.key,row.value]));
const input={parties:read('data/parties.json'),current:read('data/current-polls.json'),turnout:read('data/turnout-2022.json'),
  calibration:read('data/calibration.json'),weightPresets:read('data/weight-presets.json'),signalNoiseData:read('data/signal-noise-observations.json')};
const current=runSimulation(input,{...config,includeChannel14:true});
const fields=['iterations','parties','blocHist','blocStats','reportingGroups','coalitionHist','coalitionStats','counts','probabilities','probabilityCI',
  'meanBallots','meanValid','meanTurnout','worlds','nEffective','methodWeights','pointProbabilities','expectedVotesRounded','turnout','checks'];
for(const field of fields)assert.deepEqual(current[field],previous[field],field+' must reproduce the frozen public release');
const off=runSimulation(input,{...config,includeChannel14:false});
assert.equal(off.pollWeights.length,7);assert.ok(off.pollWeights.every(row=>row.pollsterId!=='next_data'));
const summary=result=>({polls:result.pollWeights.length,meanSeats:Object.fromEntries(Object.entries(result.blocStats).map(([key,value])=>[key,value.mean])),
  winProbability:result.parties.find(row=>row.id==='winter').passProbability,hendelProbability:result.parties.find(row=>row.id==='hendel').passProbability,
  blocMajorityProbability:result.probabilities,checks:result.checks});
const receipt={status:'PASS',frozenPublicCommit:read('artifacts/channel14-default-2026-10-09/before/manifest.json').publishedCommit,
  frozenSnapshotSha256:hash('artifacts/channel14-default-2026-10-09/before/dashboard/src/data.json'),iterations:config.iterations,
  seed:config.seed,weightMode:config.weightMode,exactFrozenComparisons:fields,
  comparisonReason:'Explicit ON restores all numerical results of the frozen previous public default; OFF changes only the active publisher selection.',
  on:summary(current),off:summary(off)};
const output=new URL('artifacts/channel14-default-2026-10-09/on-regression.json',root);
fs.writeFileSync(output,JSON.stringify(receipt,null,2)+'\n');
console.log(JSON.stringify(receipt,null,2));
