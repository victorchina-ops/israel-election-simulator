import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import {analyzeJointThreshold} from "../dashboard/src/content/dashboard/joint-threshold-probabilities.js";
import {runSimulation} from "../dashboard/src/content/dashboard/model/simulate.js";
// Frozen Version 3 implementation predates the added accounting. Its complete
// output remains an independent replay reference, including all RNG draws.
import {runSimulation as runFrozenSimulation} from "../github-pages/sources/2026-10-09-site-v3/implementation/content/dashboard/model/simulate.js";

const close=(actual,expected)=>assert.ok(Math.abs(actual-expected)<1e-12,`${actual} != ${expected}`);
const read=relative=>JSON.parse(fs.readFileSync(new URL(relative,import.meta.url),"utf8").replace(/^\uFEFF/,""));
const input={
  current:read("../data/current-polls.json"),parties:read("../data/parties.json"),
  turnout:read("../data/turnout-2022.json"),calibration:read("../data/calibration.json"),
  weightPresets:read("../data/weight-presets.json"),pollCorrelation:read("../data/poll-correlation.json"),
};

function fixture(entries,partyIds=["a","b"]){
  const patterns=entries.map(([failed,count])=>({failed,count}));
  const total=patterns.reduce((sum,pattern)=>sum+pattern.count,0);
  return {iterations:total,parties:partyIds.map(id=>({id,ballot:true,hasModelledSupport:true,meanVotePct:3.25})),thresholdJoint:{partyIds,patterns,total}};
}
const assertEmpty=(analysis,status)=>{
  assert.equal(analysis.status,status);
  assert.equal(analysis.probability,null);
  assert.equal(analysis.ci,null);
  assert.deepEqual(analysis.distribution,[]);
};

test("perfect positive dependence preserves a joint 50% failure instead of a product of 25%",()=>{
  const result=fixture([["00",50],["11",50]]);
  const analysis=analyzeJointThreshold(result,["a","b"]);
  assert.equal(analysis.status,"ready");
  assert.equal(analysis.count,50);
  assert.equal(analysis.total,100);
  assert.equal(analysis.probability,.5);
  assert.notEqual(analysis.probability,.5*.5);
  assert.ok(analysis.ci[0]<.5&&analysis.ci[1]>.5);
  assert.deepEqual(analysis.distribution,[{failedCount:0,count:50,probability:.5},{failedCount:1,count:0,probability:0},{failedCount:2,count:50,probability:.5}]);
  assert.deepEqual(analyzeJointThreshold(result,["a","b"],"allFail"),analysis);
});

test("perfect negative dependence yields no observed joint failure with a nonzero uncertainty bound",()=>{
  const result=fixture([["01",50],["10",50]]);
  const analysis=analyzeJointThreshold(result,["a","b"],"allFail");
  assert.equal(analysis.status,"ready");
  assert.equal(analysis.count,0);
  assert.equal(analysis.probability,0);
  assert.notEqual(analysis.probability,.5*.5);
  assert.equal(analysis.ci[0],0);
  assert.ok(analysis.ci[1]>0);
  assert.equal(analysis.distribution[1].count,100);
});

test("two-or-more and all-selected events remain distinct for three parties",()=>{
  const result=fixture([["000",10],["001",20],["011",30],["101",25],["111",15]],["a","b","c"]);
  const atLeast=analyzeJointThreshold(result,["a","b","c"]);
  const all=analyzeJointThreshold(result,["a","b","c"],"allFail");
  assert.equal(atLeast.count,70);
  assert.equal(atLeast.probability,.7);
  assert.equal(all.count,15);
  assert.equal(all.probability,.15);
  assert.deepEqual(atLeast.distribution.map(row=>row.count),[10,20,55,15]);
  assert.equal(atLeast.distribution.reduce((sum,row)=>sum+row.count,0),100);
  close(atLeast.distribution.reduce((sum,row)=>sum+row.probability,0),1);
  // Query specific party columns, regardless of selection order; duplicate IDs
  // do not count the same party as two failures.
  const subset=analyzeJointThreshold(result,["b","a","b"]);
  assert.equal(subset.probability,.15);
  assert.deepEqual(subset.selectedIds,["b","a"]);
  assert.deepEqual(subset.distribution.map(row=>row.count),[30,55,15]);
  const reordered=structuredClone(result);
  reordered.thresholdJoint.partyIds=["c","a","b"];
  reordered.thresholdJoint.patterns=reordered.thresholdJoint.patterns.map(({failed,count})=>({failed:failed[2]+failed[0]+failed[1],count}));
  assert.deepEqual(analyzeJointThreshold(reordered,["a","b","c"]),atLeast);
});

test("selection requires at least two distinct known ballot parties",()=>{
  const result=fixture([["00",100]]);
  result.parties.push({id:"other",ballot:false,hasModelledSupport:true});
  for(const ids of [undefined,null,"a",[],["a"],["a","a"],["a","missing"],["a","other"],["a",null],["a",""]]){
    assertEmpty(analyzeJointThreshold(result,ids),"selection");
  }
  assertEmpty(analyzeJointThreshold(result,["a","b"],"unknown"),"selection");
});

test("missing separate support stays unavailable while reconstruction and explicit scenario zeros remain modeled",()=>{
  const result=fixture([["01",100]]);
  result.parties[1].hasModelledSupport=false;
  result.parties[1].meanVotePct=0;
  result.parties[1].hasRawReportedSupport=false;
  const missing=analyzeJointThreshold(result,["a","b"]);
  assertEmpty(missing,"unmodelled");
  assert.equal(missing.count,null);
  assert.equal(missing.total,100);
  // An explicit unsupported flag takes precedence over incidental positive data.
  result.parties[1].meanVotePct=3.25;
  assertEmpty(analyzeJointThreshold(result,["a","b"]),"unmodelled");
  // A reconstructed estimate is eligible even when no raw percent was reported.
  result.parties[1].hasModelledSupport=true;
  assert.equal(analyzeJointThreshold(result,["a","b"]).status,"ready");
  // A measured party forced to zero by the scenario still has modeled support.
  result.parties[1].meanVotePct=0;
  assert.equal(analyzeJointThreshold(result,["a","b"]).status,"ready");
  delete result.parties[1].hasModelledSupport;
  assertEmpty(analyzeJointThreshold(result,["a","b"]),"unmodelled");
  result.parties[1].meanVotePct=.1;
  assert.equal(analyzeJointThreshold(result,["a","b"]).status,"ready");
});

test("one observed election does not become an estimated probability",()=>{
  const result=fixture([["11",1]]);
  const analysis=analyzeJointThreshold(result,["a","b"]);
  assertEmpty(analysis,"single");
  assert.equal(analysis.count,1);
  assert.equal(analysis.total,1);
  assert.deepEqual(analysis.selectedIds,["a","b"]);
});

test("complete histogram validation rejects partial, malformed, and incompatible result data",()=>{
  const valid=fixture([["00",50],["11",50]]);
  for(const result of [null,{}, {...valid,iterations:0},{...valid,iterations:2.5}])assertEmpty(analyzeJointThreshold(result,["a","b"]),"unavailable");
  const mutations=[
    result=>delete result.thresholdJoint,
    result=>{result.thresholdJoint.total=99;},
    result=>{result.thresholdJoint.patterns[0].count=49;},
    result=>{result.thresholdJoint.patterns=[];},
    result=>{result.thresholdJoint.patterns[0].count=-1;},
    result=>{result.thresholdJoint.patterns[0].count=1.5;},
    result=>{result.thresholdJoint.patterns[0].count="50";},
    result=>{result.thresholdJoint.patterns[0].count=Infinity;},
    result=>{result.thresholdJoint.patterns[0].failed="0x";},
    result=>{result.thresholdJoint.patterns[0].failed="0";},
    result=>{result.thresholdJoint.patterns[0].failed=0;},
    result=>{result.thresholdJoint.patterns[1].failed="00";},
    result=>{result.thresholdJoint.partyIds=["a","a"];},
    result=>{result.thresholdJoint.partyIds=["a","missing"];},
    result=>{result.thresholdJoint.partyIds=["a"];},
    result=>{result.parties.push({...result.parties[0]});},
    result=>{result.parties[0].id="";},
    result=>{result.parties.push({id:"other",ballot:false});result.thresholdJoint.partyIds[1]="other";},
    result=>{result.iterations=Number.MAX_SAFE_INTEGER;result.thresholdJoint.total=Number.MAX_SAFE_INTEGER;result.thresholdJoint.patterns[0].count=Number.MAX_SAFE_INTEGER;},
  ];
  for(const mutate of mutations){
    const result=structuredClone(valid);mutate(result);
    assertEmpty(analyzeJointThreshold(result,["a","b"]),"unavailable");
  }
  // Invalid unselected columns must not be silently ignored.
  const invalidUnselected=fixture([["000",100]],["a","b","c"]);
  invalidUnselected.thresholdJoint.patterns[0].failed="00x";
  assertEmpty(analyzeJointThreshold(invalidUnselected,["a","b"]),"unavailable");
  // The histogram must describe every ballot party, even an unselected party.
  const missingUnselected=structuredClone(valid);
  missingUnselected.parties.push({id:"c",ballot:true,hasModelledSupport:true});
  assertEmpty(analyzeJointThreshold(missingUnselected,["a","b"]),"unavailable");
});

test("returned analysis does not mutate saved selections or reviewed simulation data",()=>{
  const result=fixture([["00",50],["11",50]]),selected=["b","a","b"];
  const before=JSON.stringify(result),selectionBefore=JSON.stringify(selected);
  const analysis=analyzeJointThreshold(result,selected);
  assert.equal(JSON.stringify(result),before);
  assert.equal(JSON.stringify(selected),selectionBefore);
  analysis.selectedIds.push("x");
  assert.equal(JSON.stringify(selected),selectionBefore);
});

function stableOldFields(result){
  const copy=structuredClone(result);
  delete copy.generatedAt;
  delete copy.thresholdJoint;
  return copy;
}

test("every simulated joint marginal reconciles and accounting preserves frozen stochastic outputs",()=>{
  const configs=[
    {samplingMode:"poll",includeChannel14:false,pollCorrelationEnabled:false},
    {samplingMode:"poll",includeChannel14:true,pollCorrelationEnabled:true},
    {samplingMode:"fixed",includeChannel14:false,pollCorrelationEnabled:false},
  ];
  for(const options of configs){
    const config={...options,iterations:240,seed:20261009,weightMode:"quality",applyRecency:false,signalNoiseEnabled:false};
    const inputBefore=JSON.stringify(input);
    const frozen=runFrozenSimulation(input,config),result=runSimulation(input,config);
    assert.deepEqual(stableOldFields(result),stableOldFields(frozen));
    assert.equal(JSON.stringify(input),inputBefore);
    const joint=result.thresholdJoint;
    assert.equal(joint.total,config.iterations);
    assert.equal(joint.patterns.reduce((sum,row)=>sum+row.count,0),config.iterations);
    assert.deepEqual(joint.partyIds,input.parties.filter(party=>party.ballot!==false).map(party=>party.id));
    assert.equal(joint.partyIds.includes("other"),false);
    for(let j=0;j<joint.partyIds.length;j++){
      const party=result.parties.find(p=>p.id===joint.partyIds[j]);
      const failures=joint.patterns.reduce((sum,row)=>sum+(row.failed[j]==="1"?row.count:0),0);
      close(failures/config.iterations,party.failProbability);
      close((config.iterations-failures)/config.iterations,party.passProbability);
    }
    const selected=result.parties.filter(party=>party.ballot!==false&&party.hasModelledSupport).slice(0,3).map(party=>party.id);
    const all=analyzeJointThreshold(result,selected,"allFail"),atLeast=analyzeJointThreshold(result,selected);
    assert.equal(all.status,"ready");
    assert.ok(all.probability<=atLeast.probability);
    for(const id of selected)assert.ok(all.probability<=result.parties.find(party=>party.id===id).failProbability+1e-12);
    assert.equal(atLeast.distribution.reduce((sum,row)=>sum+row.count,0),config.iterations);
    assert.equal(result.worlds.length,6);
    assert.equal(result.checks.eachWorld120,true);
  }
});
