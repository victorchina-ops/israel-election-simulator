import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {createHash} from 'node:crypto';

const read=path=>JSON.parse(fs.readFileSync(new URL(path,import.meta.url),'utf8').replace(/^\uFEFF/,''));
const sha=path=>createHash('sha256').update(fs.readFileSync(new URL(path,import.meta.url))).digest('hex');
const snapshot=read('../data/strict-party-trends-without-channel14.json');
const original=read('../data/strict-party-trends.json');
const datedRoot='../artifacts/strict-post-close/without-channel14/'+snapshot.asOf+'/';
// A same-day revision may have a distinct run id; bind the promoted snapshot to its actual receipt.
const run=fs.readdirSync(new URL(datedRoot,import.meta.url)).find(name=>{
  const validation=datedRoot+name+'/validation.json';
  if(!fs.existsSync(new URL(validation,import.meta.url)))return false;
  const row=read(validation);
  return row.analysisSha256===snapshot.provenance.analysisSha256&&row.snapshotSha256===sha('../data/strict-party-trends-without-channel14.json');
});
assert.ok(run,'the active snapshot must have a matching dated validation receipt');
const evidence=datedRoot+run+'/';
const analysis=read(evidence+'party-analysis.json');
const audit=read(evidence+'independent-numeric-audit.json');
const receipt=read(evidence+'validation.json');
const frozen='../artifacts/channel14-default-2026-10-09/strict-without14/';
const checkpoint='../artifacts/poll-checks/2026-10-10/before/';
const close=(a,b,tolerance=1e-12)=>assert.ok(Math.abs(a-b)<tolerance,`${a} != ${b}`);
function bh(values){
  const entries=values.map((value,index)=>({value,index})).sort((a,b)=>a.value-b.value);
  const result=[];let previous=1;
  for(let index=entries.length-1;index>=0;index--){previous=Math.min(previous,entries[index].value*entries.length/(index+1),1);result[entries[index].index]=previous;}
  return result;
}

test('without14 snapshot reuses the identical verified cohort and marks publisher exclusions separately',()=>{
  assert.equal(snapshot.asOf,original.asOf);assert.equal(snapshot.asOf,analysis.asOf);assert.equal(snapshot.asOf,receipt.asOf);
  const eligible=original.cohort.filter(row=>row.eligibleStrict);
  const included=eligible.filter(row=>row.pollsterId!=='next_data');
  const series=new Set(included.map(row=>row.pollsterId)).size;
  assert.equal(original.coverage.pollCount,eligible.length);
  assert.equal(original.coverage.seriesCount,new Set(eligible.map(row=>row.pollsterId)).size);
  assert.equal(snapshot.includeChannel14,false);assert.equal(snapshot.coverage.pollCount,included.length);
  assert.equal(snapshot.coverage.seriesCount,series);assert.equal(snapshot.coverage.deltaCount,included.length-series);
  assert.equal(snapshot.coverage.partyCount,original.rows.length);
  assert.equal(snapshot.coverage.channel14ExcludedPollCount,eligible.length-included.length);
  assert.equal(snapshot.coverage.unverifiedExcludedPollCount,original.cohort.length-eligible.length);
  assert.equal(snapshot.coverage.excludedPollCount,original.cohort.length-included.length);
  assert.equal(analysis.primary.nPolls,included.length);assert.equal(analysis.primary.nSeries,series);
  assert.equal(analysis.primary.nDeltas,included.length-series);
  assert.deepEqual(snapshot.cohort.map(row=>row.pollId),original.cohort.map(row=>row.pollId));
  const byId=new Map(original.cohort.map(row=>[row.pollId,row]));
  for(const row of snapshot.cohort){
    const before=byId.get(row.pollId);assert.equal(row.fieldworkStart,before.fieldworkStart);assert.equal(row.fieldworkEnd,before.fieldworkEnd);
    assert.deepEqual(row.sourceUrls,before.sourceUrls);
    assert.equal(row.eligibleStrict,before.eligibleStrict&&before.pollsterId!=='next_data');
    if(row.pollsterId==='next_data')assert.equal(row.exclusionReason,'channel14_disabled');
    if(row.eligibleStrict)assert.ok(row.fieldworkStart>='2026-09-09');
  }
});

test('historical weights renormalize once across the selected series without changing relative quality',()=>{
  const raw=read('../data/calibration.json').pollsterQuality;
  const denominator=snapshot.weights.reduce((sum,row)=>sum+raw[row.pollsterId].weight,0);
  close(snapshot.weights.reduce((sum,row)=>sum+row.weight,0),1);
  assert.ok(snapshot.weights.every(row=>row.pollsterId!=='next_data'));
  for(const row of snapshot.weights)close(row.weight,raw[row.pollsterId].weight/denominator);
  assert.equal(snapshot.weights.reduce((sum,row)=>sum+row.nPolls,0),snapshot.coverage.pollCount);
});

test('new effect estimates reconstruct from unchanged individual series and retain the same 17-party BH family',()=>{
  assert.deepEqual(snapshot.rows.map(row=>row.partyId),original.rows.map(row=>row.partyId));
  for(const row of snapshot.rows){
    assert.equal(row.byPollster.length,snapshot.coverage.seriesCount);
    close(row.weightedNetDelta,row.byPollster.reduce((sum,series)=>sum+series.weight*series.netDelta,0));
    close(row.slopePerWeek,row.byPollster.reduce((sum,series)=>sum+series.weight*series.slopePerWeek,0));
    for(const series of row.byPollster){
      const before=original.rows.find(item=>item.partyId===row.partyId).byPollster.find(item=>item.pollsterId===series.pollsterId);
      assert.deepEqual(series.pollIds,before.pollIds);assert.deepEqual(series.seats,before.seats);assert.deepEqual(series.deltas,before.deltas);
      close(series.slopePerWeek,before.slopePerWeek);
    }
  }
  for(const [p,q] of [['pValue','qValue'],['wholeSeriesSignFlipP','wholeSeriesSignFlipQ']]){
    const expected=bh(snapshot.rows.map(row=>row[p]));snapshot.rows.forEach((row,index)=>close(row[q],expected[index]));
  }
  const individual=snapshot.rows.flatMap(row=>row.byPollster),expected=bh(individual.map(row=>row.pValue));
  assert.equal(individual.length,snapshot.rows.length*snapshot.coverage.seriesCount);individual.forEach((row,index)=>close(row.qValue,expected[index]));
});

test('primary exact counts retain integer multiplicities and both statistical verdicts are recomputed',()=>{
  const primary=analysis.primary,total=BigInt(primary.exactCounting.nPermutationsExact);
  const factorial=n=>Array.from({length:n},(_,index)=>BigInt(index+1)).reduce((product,value)=>product*value,1n);
  assert.equal(total,snapshot.weights.reduce((product,row)=>product*factorial(row.nPolls),1n));
  assert.equal(total,BigInt(audit.nPermutationsExact));
  assert.equal(primary.wholeSeriesSignPatterns,2**snapshot.coverage.seriesCount);
  for(const [index,row] of primary.overall.entries()){
    close(row.pValue,Number(BigInt(primary.exactCounting.extremeCountsExact[index]))/Number(total));
    const shown=snapshot.rows.find(item=>item.partyId===row.partyId);assert.ok(shown,row.partyId);
    for(const key of ['weightedNetDelta','slopePerWeek','pValue','qValue','wholeSeriesSignFlipP','wholeSeriesSignFlipQ'])close(shown[key],row[key]);
  }
  assert.deepEqual(snapshot.rows.filter(row=>row.qValue<.05).map(row=>row.partyId),receipt.primarySignificantAfterBH);
  assert.deepEqual(snapshot.rows.filter(row=>row.wholeSeriesSignFlipQ<.05).map(row=>row.partyId),receipt.sensitivitySignificantAfterBH);
  assert.equal(snapshot.methodology.individualTests,snapshot.rows.length*snapshot.coverage.seriesCount);
  assert.equal(snapshot.methodology.partyTests,snapshot.rows.length);
});

test('three bloc definitions aggregate party slopes and changes, with a separate three-test correction',()=>{
  const rows=analysis.primary.blocOverall;
  assert.equal(rows.length,3);
  for(const row of rows){
    const parties=snapshot.rows.filter(party=>analysis.groups[row.group].includes(party.partyId));
    close(row.weightedNetDelta,parties.reduce((sum,party)=>sum+party.weightedNetDelta,0));
    close(row.slopePerWeek,parties.reduce((sum,party)=>sum+party.slopePerWeek,0));
  }
  for(const [p,q] of [['pValue','qValue'],['wholeInstituteSignFlipP','wholeInstituteSignFlipQ']]){
    const expected=bh(rows.map(row=>row[p]));rows.forEach((row,index)=>close(row[q],expected[index]));
  }
  assert.ok(rows.every(row=>row.qValue>=.05&&row.wholeInstituteSignFlipQ>=.05));
});

test('independent audit records its actual sampled tail scope and binds every immutable source hash',()=>{
  assert.equal(audit.status,'PASS');assert.match(audit.independentTailScope,/not a new all-outcome exhaustive/);
  assert.ok(audit.independentlyCountedOutcomeIds.length>=3);
  assert.equal(audit.extremeCountsExact.length,audit.independentlyCountedOutcomeIds.length);
  for(const [index,id] of audit.independentlyCountedOutcomeIds.entries()){
    const primaryIndex=analysis.primary.overall.findIndex(row=>row.partyId===id);
    assert.ok(primaryIndex>=0,id);
    assert.equal(BigInt(audit.extremeCountsExact[index]),BigInt(analysis.primary.exactCounting.extremeCountsExact[primaryIndex]),id);
  }
  assert.equal(audit.primaryAnalysisSha256,sha(evidence+'party-analysis.json'));
  assert.equal(snapshot.provenance.analysisSha256,audit.primaryAnalysisSha256);
  assert.equal(snapshot.provenance.independentAuditSha256,sha(evidence+'independent-numeric-audit.json'));
  for(const [path,hash] of Object.entries(receipt.immutableSourceHashes))assert.equal(sha('../'+path.replaceAll('\\','/')),hash,path);
  assert.equal(receipt.snapshotSha256,sha('../data/strict-party-trends-without-channel14.json'));
});


test('the frozen 9 October verdicts and receipts remain bound to their original checkpoint bytes',()=>{
  const saved=read(checkpoint+'data/strict-party-trends-without-channel14.json');
  const validation=read(frozen+'validation.json');
  const numeric=read(frozen+'independent-numeric-audit.json');
  assert.equal(saved.asOf,'2026-10-09');assert.equal(validation.asOf,saved.asOf);
  assert.equal(validation.status,'PASS');assert.equal(numeric.status,'PASS');
  assert.equal(validation.snapshotSha256,sha(checkpoint+'data/strict-party-trends-without-channel14.json'));
  assert.equal(saved.provenance.analysisSha256,sha(frozen+'party-analysis.json'));
  assert.equal(saved.provenance.independentAuditSha256,sha(frozen+'independent-numeric-audit.json'));
  for(const [path,hash] of Object.entries(validation.immutableSourceHashes)){
    const relative=path.replaceAll('\\','/');
    const location=relative==='data/parties.json'?'../'+relative:checkpoint+relative;
    assert.equal(sha(location),hash,path);
  }
  const joint=saved.rows.find(row=>row.partyId==='joint');close(joint.qValue,.01615);close(joint.wholeSeriesSignFlipQ,.53125);
  assert.deepEqual(saved.rows.filter(row=>row.qValue<.05).map(row=>row.partyId),['joint']);
  assert.deepEqual(saved.rows.filter(row=>row.wholeSeriesSignFlipQ<.05).map(row=>row.partyId),[]);
});
