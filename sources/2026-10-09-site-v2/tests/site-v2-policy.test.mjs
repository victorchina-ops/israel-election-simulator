import test from 'node:test';
import assert from 'node:assert/strict';
import {normalizeSiteScenario,retiredSignalNoiseRequested} from '../dashboard/src/content/dashboard/site-scenario-policy.js';
test('V2 cannot re-enable the retired feature through old saved configurations',()=>{
  for(const mode of ['equal','quality','reference','littlepolls','gilead','rosner','ensemble','robust','correlation']){
    const original={weightMode:mode,signalNoiseEnabled:true,pollCorrelationEnabled:true,includeChannel14:true,pollWeights:{a:1.5},excludedPolls:['x']};
    const next=normalizeSiteScenario(original);
    assert.equal(retiredSignalNoiseRequested(original),true);assert.equal(next.signalNoiseEnabled,false);
    assert.equal(next.weightMode,mode);assert.deepEqual(next.pollWeights,original.pollWeights);assert.deepEqual(next.excludedPolls,['x']);assert.equal(original.signalNoiseEnabled,true);
  }
  assert.equal(normalizeSiteScenario({weightMode:'signal_noise'}).weightMode,'quality');
  assert.equal(normalizeSiteScenario({weightMode:'signal_noise',signalNoiseHistoricalQuality:false}).weightMode,'equal');
  assert.throws(()=>normalizeSiteScenario({weightMode:'quality',signalNoiseEnabled:'false'}),/boolean/);
});
test('ordinary site policy is idempotent and preserves the current defaults',()=>{
  const original={weightMode:'quality',signalNoiseEnabled:false,includeChannel14:false,pollCorrelationEnabled:false,iterations:10000};
  assert.equal(retiredSignalNoiseRequested(original),false);assert.deepEqual(normalizeSiteScenario(original),original);assert.deepEqual(normalizeSiteScenario(normalizeSiteScenario(original)),original);
});
