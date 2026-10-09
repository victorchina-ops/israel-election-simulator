import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
const source=fs.readFileSync(new URL('../dashboard/src/content/dashboard/ThresholdPage.jsx',import.meta.url),'utf8');
const body=source.slice(source.indexOf('function histogram('),source.indexOf('function partyRow('));
const histogram=Function(body+'return histogram;')();

test('compact threshold histograms retain all counts with at most 21 display bins',()=>{
 for(let k=0;k<500;k++){
  const counts=Array.from({length:1001},(_,i)=>i>100+k%430&&i<200+k%550?(i+k)%37:0);
  const iterations=counts.reduce((a,b)=>a+b,0);
  const display=histogram({name:'party',meanVotePct:(k%300)/10,voteHist:counts},iterations);
  assert.equal(display.rows.reduce((sum,row)=>sum+row['הדמיות בטווח'],0),iterations);
  assert.ok(display.rows.length<=21);
  assert.ok(Math.abs(display.rows.reduce((sum,row)=>sum+row['שכיחות (%)'],0)-100)<1e-9);
  assert.ok(display.rows.every(row=>row['סף חוקי (%)']===3.25));
 }
});

test('near-threshold display retains the exact cutoff without turning missing observations into zeros',()=>{
 const counts=Array(1001).fill(0);counts[32]=34;counts[33]=66;
 const display=histogram({name:'party',meanVotePct:3.27,voteHist:counts},100);
 assert.equal(display.includesThreshold,true);
 assert.equal(display.rows.reduce((sum,row)=>sum+row['הדמיות בטווח'],0),100);
 assert.ok(display.rows.some(row=>row['תחילת טווח (%)']<=3.25&&row['סוף טווח (%)']>=3.25));
 assert.deepEqual(histogram({voteHist:[]},0),{rows:[],width:null,includesThreshold:false});
});
