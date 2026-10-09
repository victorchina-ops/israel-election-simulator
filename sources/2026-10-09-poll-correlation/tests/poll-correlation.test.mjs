import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {computePollWeights,WEIGHT_MODES} from '../dashboard/src/content/dashboard/model/weights.js';
import {computePollWeights as frozenWeights} from '../github-pages/sources/2026-10-09-channel14-default/implementation/weights.js';
import {applyPollCorrelationDiscount,covarianceInflation,getPollCorrelationMatrix,reviewedPollCorrelationProfile} from '../dashboard/src/content/dashboard/model/poll-correlation.js';
import {combinePolls,reconstructPoll} from '../dashboard/src/content/dashboard/model/reconstruct.js';
import {combineForecast,resolveForecastConfig} from '../dashboard/src/content/dashboard/model/forecast.js';
import {runSimulation,defaultConfig} from '../dashboard/src/content/dashboard/model/simulate.js';

const read=path=>JSON.parse(fs.readFileSync(new URL(path,import.meta.url),'utf8').replace(/^\uFEFF/,''));
const current=read('../data/current-polls.json'),parties=read('../data/parties.json'),profile=read('../data/poll-correlation.json');
const calibration={...read('../data/calibration.json'),weightPresets:read('../data/weight-presets.json'),pollCorrelation:profile};
const close=(a,b,tolerance=1e-12)=>assert.ok(Math.abs(a-b)<tolerance,`${a} != ${b}`);
const vector=(a,b)=>{assert.equal(a.length,b.length);a.forEach((value,i)=>close(value,b[i]));};
const base={asOf:current.asOf,includeChannel14:false,applyRecency:false,weightMode:'quality',gileadTarget:'next_data'};
const probabilities=current.polls.map(poll=>reconstructPoll(poll,parties).probabilities);
const run=(extra={},polls=current.polls,cal=calibration)=>computePollWeights(polls,{...base,...extra},cal,{probabilities});
const cloned=value=>JSON.parse(JSON.stringify(value));
function syntheticProfile(matrix=[[1,.25,0],[.25,1,0],[0,0,1]]){
  return {id:'2026-published-prediction-fixture',instituteIds:['a','b','c'],modeledCorrelationMatrix:matrix,similarityStrength:.25,bandwidthSeats:2};
}
const syntheticPolls=['a','b','c','unknown'].map(id=>({id:`${id}-current`,pollsterId:id,date:current.asOf,sampleSize:1000}));
const syntheticCalibration=profile=>({pollsterQuality:{a:{weight:10},b:{weight:.1},c:{weight:5},unknown:{weight:8}},pollCorrelation:profile});

test('OFF and omitted flag exactly reproduce published weights for every policy and Channel 14 state',()=>{
  for(const weightMode of WEIGHT_MODES)for(const includeChannel14 of [false,true]){
    const config={...base,weightMode,includeChannel14,pollWeights:{kantar:1.7},excludedPolls:[current.polls.find(p=>p.pollsterId==='tatika').id]};
    const archived=frozenWeights(current.polls,config,calibration,{probabilities});
    assert.deepEqual(computePollWeights(current.polls,config,calibration,{probabilities}),archived);
    assert.deepEqual(computePollWeights(current.polls,{...config,pollCorrelationEnabled:false},calibration,{probabilities}),archived);
  }
});

test('reviewed similarity profile describes current forecasts, with no 2022 outcome calibration',()=>{
  const reviewed=reviewedPollCorrelationProfile(calibration);
  assert.equal(reviewed.id,profile.id);assert.equal(reviewed.instituteIds.length,8);
  assert.equal(reviewed.similarityStrength,.25);assert.equal(reviewed.additionalIdentityShrinkage,0);
  assert.ok(reviewed.modeledCorrelationMatrix.every((row,i)=>row[i]===1));
  assert.ok(!JSON.stringify(reviewed).includes('final-polls-2022'));
});

test('more similar forecasts receive a continuous redundancy discount, not a hard duplicate merge',()=>{
  const polls=syntheticPolls.slice(0,3),weights=Array(3).fill(1/3);
  const weak=applyPollCorrelationDiscount(polls,weights,syntheticProfile([[1,.1,0],[.1,1,0],[0,0,1]]));
  const strong=applyPollCorrelationDiscount(polls,weights,syntheticProfile());
  vector(strong.weights,[4/13,4/13,5/13]);
  assert.ok(strong.weights[0]<weak.weights[0]);assert.ok(strong.weights[2]>weak.weights[2]);
  close(strong.metadata.redundancyDensity.a,1.25);
  close((strong.weights[0]+strong.weights[1])/strong.weights[2],1.6);
});

test('zero modeled similarity leaves base weights and effective information unchanged',()=>{
  const diagonal=syntheticProfile([[1,0,0],[0,1,0],[0,0,1]]),cal=syntheticCalibration(diagonal);
  const config={...base,includeChannel14:true},off=computePollWeights(syntheticPolls,config,cal);
  const on=computePollWeights(syntheticPolls,{...config,pollCorrelationEnabled:true},cal);
  assert.deepEqual(on.weights,off.weights);
  const information=covarianceInflation(syntheticPolls,on.weights,{...config,pollCorrelationEnabled:true},cal);
  close(information.factor,1);close(information.nEffectiveIndependent,information.nEffectiveModeled);
});

test('existing historical accuracy is neither replaced nor multiplied by another accuracy profile',()=>{
  const cal=syntheticCalibration(syntheticProfile()),config={...base,includeChannel14:true};
  const off=computePollWeights(syntheticPolls,config,cal),on=computePollWeights(syntheticPolls,{...config,pollCorrelationEnabled:true},cal);
  vector(on.baseWeightsBeforeCorrelation,off.baseWeights);
  vector(on.weights,applyPollCorrelationDiscount(syntheticPolls,off.weights,cal.pollCorrelation).weights);
  assert.equal(on.pollCorrelation.historicalAccuracyApplied,'unchanged_selected_base_policy');
  const changed=cloned(cal);changed.pollsterQuality.a.weight=.01;
  const changedOff=computePollWeights(syntheticPolls,config,changed),changedOn=computePollWeights(syntheticPolls,{...config,pollCorrelationEnabled:true},changed);
  vector(changedOn.weights,applyPollCorrelationDiscount(syntheticPolls,changedOff.weights,cal.pollCorrelation).weights);
  assert.notDeepEqual(changedOn.weights,on.weights);
});

test('all policies keep base method vectors and truthful post-discount contribution attribution',()=>{
  for(const weightMode of WEIGHT_MODES)for(const includeChannel14 of [true,false]){
    const on=run({weightMode,includeChannel14,pollCorrelationEnabled:true,pollWeights:{lazar:1.8}});
    const off=run({weightMode,includeChannel14,pollWeights:{lazar:1.8}});
    vector(on.baseWeightsBeforeCorrelation,off.baseWeights);
    assert.deepEqual(on.contributions.map(c=>({weights:c.weights,parameters:c.parameters})),off.contributions.map(c=>({weights:c.weights,parameters:c.parameters})));
    close(on.weights.reduce((a,b)=>a+b,0),1);assert.ok(on.weights.every(w=>Number.isFinite(w)&&w>=0));
    if(weightMode!=='robust')on.weights.forEach((weight,i)=>close(weight,on.contributions.reduce((s,c)=>s+c.contributionAfterManual[i],0)));
    else assert.ok(on.contributions.every(c=>c.contributionAfterManual===null));
    assert.ok(on.polls.every(p=>includeChannel14||p.pollsterId!=='next_data'));
  }
});

test('manual multipliers apply after redundancy exactly once and exclusions cannot be resurrected',()=>{
  const on=run({pollCorrelationEnabled:true}),manual=run({pollCorrelationEnabled:true,pollWeights:{lazar:2}});
  const expected=on.weights.map((w,i)=>w*(on.polls[i].pollsterId==='lazar'?2:1)),sum=expected.reduce((a,b)=>a+b,0);
  vector(manual.weights,expected.map(w=>w/sum));
  const removed=run({pollCorrelationEnabled:true,pollWeights:{kantar:0},excludedPolls:[current.polls.find(p=>p.pollsterId==='lazar').id]});
  assert.ok(removed.polls.every(p=>!['kantar','lazar','next_data'].includes(p.pollsterId)));
  assert.ok(removed.pollCorrelation.eligibleInstitutes.every(id=>!['kantar','lazar','next_data'].includes(id)));
});

test('Gilead policy remains the initial 50-percent prior and positive manual target changes remain effective',()=>{
  const target='direct_polls',on=run({weightMode:'gilead',gileadTarget:target,pollCorrelationEnabled:true});
  const index=on.polls.findIndex(p=>p.pollsterId===target);close(on.baseWeightsBeforeCorrelation[index],.5);
  const manual=run({weightMode:'gilead',gileadTarget:target,pollCorrelationEnabled:true,pollWeights:{[target]:2}});
  close(manual.weights[index],2*on.weights[index]/(1+on.weights[index]));
});

test('unknown institutes keep proposed mass and missing pair similarity stays explicitly unknown',()=>{
  const profile=syntheticProfile(),result=applyPollCorrelationDiscount(syntheticPolls,Array(4).fill(.25),profile);
  close(result.weights[3],.25);close(result.weights.slice(0,3).reduce((a,b)=>a+b,0),.75);
  const matrix=getPollCorrelationMatrix(syntheticPolls,{pollCorrelation:profile});
  assert.deepEqual(matrix.unmodeledInstitutes,['unknown']);assert.equal(matrix.unmodeledPairs.length,3);
  assert.ok(matrix.unmodeledPairs.every(pair=>pair.similarity===null));
  assert.equal(matrix.unknownPairAssumption,'uncorrected_variance_fallback_not_estimated_independence');
});

test('effective information includes positive cross terms and does not modify common bloc sensitivity',()=>{
  const polls=syntheticPolls.slice(0,3),cal={pollCorrelation:syntheticProfile()},weights=[4/13,4/13,5/13];
  const result=covarianceInflation(polls,weights,{pollCorrelationEnabled:true,designEffect:1.5},cal);
  close(result.independentVarianceScale,(57/169)*.0015);
  close(result.modeledVarianceScale,(65/169)*.0015);
  close(result.factor,65/57);assert.ok(result.nEffectiveModeled<result.nEffectiveIndependent);
  assert.equal(result.commonBlocSensitivityChanged,false);
  const stronger=covarianceInflation(polls,weights,{pollCorrelationEnabled:true,designEffect:1.5},{pollCorrelation:syntheticProfile([[1,.5,0],[.5,1,0],[0,0,1]])});
  assert.ok(stronger.factor>result.factor);
});

test('unit perfect correlation adds no information in a simple duplicated forecast unit, without claiming general hard deduplication',()=>{
  const polls=syntheticPolls.slice(0,3),full=syntheticProfile([[1,1,0],[1,1,0],[0,0,1]]);
  const discounted=applyPollCorrelationDiscount(polls,Array(3).fill(1/3),full);vector(discounted.weights,[.25,.25,.5]);
  const result=covarianceInflation(polls,discounted.weights,{pollCorrelationEnabled:true},{pollCorrelation:full});
  const unique=covarianceInflation([polls[0],polls[2]],[.5,.5],{},{});
  close(result.nEffectiveModeled,unique.nEffectiveIndependent);
});

test('every policy and Channel 14 combination applies information correction once and preserves total 120',()=>{
  const input={current,parties,calibration,pollCorrelation:profile,weightPresets:calibration.weightPresets,turnout:read('../data/turnout-2022.json')};
  for(const weightMode of WEIGHT_MODES)for(const includeChannel14 of [true,false]){
    const config={...defaultConfig(input),...base,weightMode,includeChannel14,pollCorrelationEnabled:true,iterations:100,seed:991};
    const combined=combineForecast(input,config),information=combined.pollCorrelation.informationCorrection;
    close(combined.nEffective,information.nEffectiveModeled);assert.ok(combined.nEffective<=information.nEffectiveIndependent);
    const result=runSimulation(input,config);
    assert.equal(result.checks.eachWorld120,true);assert.equal(result.checks.blocPartition120,true);
    assert.equal(result.pollCorrelation.profileId,profile.id);assert.equal(result.config.pollCorrelationEnabled,true);
    assert.ok(!Object.hasOwn(result,'history2022Dependence'));
  }
});

test('same institute histories do not gain independent institute count and absent profile stays OFF-compatible',()=>{
  const polls=[{id:'a1',pollsterId:'a',sampleSize:1000},{id:'a2',pollsterId:'a',sampleSize:1000}];
  const result=covarianceInflation(polls,[.5,.5],{pollCorrelationEnabled:true},{pollCorrelation:syntheticProfile()});
  close(result.nEffectiveModeled,1000/1.5);
  const off=covarianceInflation(polls,[.5,.5],{pollCorrelationEnabled:false},{});close(off.factor,1);
});

test('ordinary covariance correction retains exactly the old global DEFF and published sample-size baseline',()=>{
  const polls=current.polls.map((poll,i)=>({...poll,designEffect:10+i,percentageSampleSize:55,measurementSampleSize:60}));
  const config={...base,pollCorrelationEnabled:true,designEffect:1.5},combined=combinePolls(polls,parties,config,calibration);
  const exactOldVariance=combined.weights.reduce((s,w,i)=>s+w*w/(Math.max(100,combined.polls[i].sampleSize??500)/config.designEffect),0);
  assert.equal(combined.pollCorrelation.informationCorrection.independentVarianceScale,exactOldVariance);
  const measurement=covarianceInflation(combined.polls,combined.weights,config,calibration,{minimumSampleSize:1});
  assert.ok(measurement.independentVarianceScale>exactOldVariance);
});

test('invalid flag, missing/non-PSD/asymmetric profiles, duplicate IDs and negative information weights reject',()=>{
  for(const value of ['true',1,null,{}]){
    assert.throws(()=>run({pollCorrelationEnabled:value}),/בוליאני/);
    assert.throws(()=>resolveForecastConfig({pollCorrelationEnabled:value}),/מופעל או כבוי/);
  }
  assert.throws(()=>run({pollCorrelationEnabled:true},current.polls,{...calibration,pollCorrelation:null}),/חסר פרופיל/);
  for(const mutate of [p=>p.instituteIds.push(p.instituteIds[0]),p=>p.modeledCorrelationMatrix[0][0]=.9,
    p=>p.modeledCorrelationMatrix[0][1]=1.5,p=>p.modeledCorrelationMatrix[0][1]=.7,
    p=>p.modeledCorrelationMatrix=[[1,.9,.9],[.9,1,0],[.9,0,1]]]){
    const p=cloned(syntheticProfile());mutate(p);assert.throws(()=>reviewedPollCorrelationProfile({pollCorrelation:p}));
  }
  assert.throws(()=>covarianceInflation(syntheticPolls,[1,-1,0,0],{},{}));
  assert.throws(()=>run({pollCorrelationEnabled:true},[current.polls[0],current.polls[0]],calibration),/יותר מפעם אחת/);
});
