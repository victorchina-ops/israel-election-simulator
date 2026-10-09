import test from 'node:test';
import assert from 'node:assert/strict';
import {adjustSignalNoiseSimilarity} from '../dashboard/src/content/dashboard/model/signal-noise.js';
const closure=Date.parse('2026-09-08')/864e5;
const calibration={pollCorrelation:{id:'synthetic-forecast-similarity',instituteIds:['a','b'],modeledCorrelationMatrix:[[1,.25],[.25,1]]}};
const rows=[{pollId:'a1',pollsterId:'a',date:'2026-09-10',value:.2,sampleSize:500,qualityMultiplier:1},{pollId:'b1',pollsterId:'b',date:'2026-09-11',value:.2,sampleSize:500,qualityMultiplier:1}];
test('similarity reduces weekly measurement precision before filtering, without mutating source shares',()=>{
 const before=structuredClone(rows),result=adjustSignalNoiseSimilarity(rows,{pollCorrelationEnabled:true,designEffect:1},calibration,closure);
 assert.deepEqual(rows,before);assert.equal(result.diagnostics.length,1);
 assert.equal(result.diagnostics[0].factor,1.25);
 for(const row of result.observations){assert.equal(row.value,.2);assert.equal(row.sampleSize,500);assert.equal(row.qualityMultiplier,.8);}
});
test('separate weeks and a single institute get no additional cross-institute reduction',()=>{
 const result=adjustSignalNoiseSimilarity([rows[0],{...rows[1],date:'2026-09-18'}],{pollCorrelationEnabled:true},calibration,closure);
 assert.deepEqual(result.observations.map(row=>row.qualityMultiplier),[1,1]);
 const same=adjustSignalNoiseSimilarity([rows[0],{...rows[0],pollId:'a2',date:'2026-09-11'}],{pollCorrelationEnabled:true},calibration,closure);
 assert.equal(same.diagnostics[0].factor,1);
});
test('OFF retains prior observations and requires no new profile',()=>{
 const result=adjustSignalNoiseSimilarity(rows,{pollCorrelationEnabled:false},{},closure);
 assert.equal(result.observations,rows);assert.deepEqual(result.diagnostics,[]);
});
test('reused source ID and same-institute/day reports do not inflate similarity precision',()=>{
 const config={pollCorrelationEnabled:true,designEffect:1};
 const reference=adjustSignalNoiseSimilarity(rows,config,calibration,closure);
 for(const extra of [rows[0],{...rows[0],pollId:'same-day-report'}]){
  const result=adjustSignalNoiseSimilarity([...rows,extra],config,calibration,closure);
  assert.deepEqual(result.diagnostics,reference.diagnostics);
  assert.deepEqual(result.observations.slice(0,2),reference.observations);
 }
});
