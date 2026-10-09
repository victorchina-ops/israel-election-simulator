import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import React from '../dashboard/node_modules/react/index.js';
import {transformSync} from '../dashboard/node_modules/rolldown/dist/experimental-index.mjs';
import * as copy from '../dashboard/src/content/dashboard/signal-noise-content.js';
import * as selectionPolicy from '../dashboard/src/content/dashboard/model/poll-selection-policy.js';

// Exercise the actual authored controls without substituting their logic. The
// evidence wrapper is a recorded React element; production numerical fits are
// independently tested by the model tests.
const queries=Object.fromEntries(['polls','signal_noise_observations','model_configuration','model_input','calibration','weight_presets'].map(id=>[id,{rows:[{id}]}]));
const stub=()=>null;
function component(file,name,extra={}){
 const source=fs.readFileSync(new URL('../dashboard/src/content/dashboard/'+file,import.meta.url),'utf8');
 const compiled=transformSync(file,source,{jsx:{runtime:'classic'}});
 assert.equal(compiled.errors.length,0);
 const code=compiled.code.replace(/^import[^;]*;\s*/gm,'').replace(/export default[^;]*;/g,'').replace(/export (function|const) /g,'$1 ');
 const bindings={React,useState:value=>[value,()=>{}],DataComponent:stub,Dropdown:stub,Switch:stub,Button:stub,useDataApp:()=>({queries}),StepControl:stub,PollSelectionControl:stub,SignalNoiseInstituteControl:stub,SignalNoiseDiagnostics:stub,...copy,...selectionPolicy,...extra};
 return Function(...Object.keys(bindings),code+'\nreturn '+name+';')(...Object.values(bindings));
}
function elements(tree){
 const out=[];
 function visit(value){if(Array.isArray(value)){value.forEach(visit);return;}if(!value||typeof value!=='object'||!value.props)return;out.push(value);visit(value.props.children);}
 visit(tree);return out;
}
const input={current:{asOf:'2026-10-09',polls:[{id:'latest-a',pollsterId:'a',publisher:'מכון א',pollster:'א'},{id:'latest-b',pollsterId:'b',publisher:'מכון ב',pollster:'ב'}]},parties:[{id:'party',name:'מפלגה',ballot:true}]};

test('retired signal/noise has no live weighting explanation and regular policies remain available',()=>{
 const Control=component('WeightingControl.jsx','WeightingControl');
 const config={weightMode:'quality',signalNoiseEnabled:true,turnout:{arab_localities:60},methodWeights:{equal:1,reference:1},excludedPolls:[],pollWeights:{}};
 const unchanged=structuredClone(config),patches=[];
 const tree=Control({input,config,weights:{},onConfigChange:patch=>patches.push(patch)}),all=elements(tree);
 const menu=all.find(e=>e.props.label==='גישת השקלול');
 assert.ok(!menu.props.choices.includes('signal_noise'));
 assert.equal(menu.props.choices.length,8);
 assert.ok(!menu.props.choices.includes('correlation'));
 assert.ok(!all.some(e=>e.props.label==='גם דיוק היסטורי'));
 assert.equal(menu.props.value,'quality');menu.props.onChange('reference');
 assert.deepEqual(patches,[{weightMode:'reference'}]);
 assert.deepEqual(config,unchanged);
 assert.ok(!all.some(e=>e.props['aria-label']==='תמהיל השיטות'));
 assert.ok(all.some(e=>e.props.label==='להוסיף דעיכת זמן'));
 assert.ok(!all.some(e=>e.props.id==='signal-noise-active-explanation'));
});

test('V2 live scenario controls never display the canceled signal/noise switch',()=>{
 const labels={quality:'דיוק היסטורי',reference:'מדד 120'};
 const Control=component('ScenarioControls.jsx','ScenarioControls',{WEIGHTING_LABELS:labels});
 for(const signalNoiseEnabled of [false,true]){
  const config={weightMode:'reference',signalNoiseEnabled,blocMultipliers:{a:1,b:1}},before=structuredClone(config),patches=[];
  const tree=Control({config,onConfigChange:patch=>patches.push(patch)}),all=elements(tree);
  assert.ok(!all.some(e=>e.props['data-scenario-control']==='signal-noise'));
  assert.ok(!all.some(e=>e.props.label==='אות ורעש — ניסיוני'));
  assert.equal(all.filter(e=>e.props['aria-controls']?.startsWith('scenario-panel-')).length,3);
  assert.deepEqual(config,before);assert.deepEqual(patches,[]);
 }
});

// The remaining tests deliberately retain the archived experiment's reproducibility.
test('institute selection restores its full-history selector without resetting scenario assumptions',()=>{
 const Control=component('SignalNoiseInstituteControl.jsx','SignalNoiseInstituteControl');
 const config={weightMode:'reference',signalNoiseEnabled:true,excludedPolls:['latest-a'],pollWeights:{a:0,b:1},turnout:{arab_localities:60}},before=structuredClone(config),patches=[];
 const tree=Control({input,config,onConfigChange:patch=>patches.push(patch)}),all=elements(tree);
 const checkbox=all.find(e=>e.props['aria-label']==='לכלול את כל סקרי מכון א');
 assert.equal(checkbox.props.checked,false);checkbox.props.onChange({target:{checked:true}});
 assert.deepEqual(patches,[{excludedPolls:[],pollWeights:{a:1,b:1}}]);
 assert.deepEqual(config,before);
 const last=all.find(e=>e.props['aria-label']==='לכלול את כל סקרי מכון ב');
 assert.equal(last.props.disabled,true);
 assert.equal(tree.props.displayRows[0].selectionScope,'all eligible historical observations for this institute');
 assert.equal(tree.props.displayRows[0].weightingMethod,'reference');
 assert.equal(tree.props.displayRows[0].signalNoiseEnabled,true);
 assert.ok(!all.some(e=>e.props['data-effective-weight']!==undefined));
});

test('diagnostics distinguish normalized support, latent uncertainty and explicit assumptions',()=>{
 const Diagnostics=component('SignalNoiseDiagnostics.jsx','SignalNoiseDiagnostics');
 const diagnostics={coverage:{observationCount:12,instituteCount:2,from:'2026-09-09',to:'2026-10-08'},parties:{party:{mean:.15,normalizedMean:.12,variance:.0004,qPerDay:.000001,r:.0001,count:0,fallback:true}}};
 const tree=Diagnostics({input,config:{weightMode:'equal',signalNoiseEnabled:true},result:{signalNoise:diagnostics}});
 assert.equal(tree.props.queryId,'signal_noise_observations');
 assert.equal(tree.props.displayRows[0].observationCount,12);
 const row=tree.props.displayRows.find(r=>r.partyId==='party');
 assert.equal(row.estimatedSupportPercent,12);
 assert.equal(row.latentUncertaintySDPercentagePoints,2);
 assert.equal(row.estimationStatus,'explicit sensitivity assumption');
 assert.equal(row.weightingMethod,'equal');
 assert.equal(row.signalNoiseEnabled,true);
 assert.ok(tree.props.sourceRowsByQuery.signal_noise_observations.length);
});

test('each ordinary comparison result discloses the same global signal/noise feature',()=>{
 const Details=component('WeightComparisonPage.jsx','MethodDetails',{MeanSeats:stub,PartyName:stub});
 const result={iterations:10000,config:{weightMode:'reference',signalNoiseEnabled:true,samplingMode:'poll'},parties:[],
  probabilities:{a:.1,b:.2,neither:.7},probabilityCI:{a:[.09,.11],b:[.19,.21],neither:[.69,.71]},
  signalNoise:{coverage:{observationCount:11,instituteCount:5},parties:{}}};
 const tree=Details({method:{id:'reference',title:'מדד 120',note:'משקלי הבסיס'},result,bloc:'a',input,diagnosticsId:'ordinary-method-signal-noise'});
 const diagnostics=elements(tree).find(element=>element.props.id==='ordinary-method-signal-noise');
 assert.ok(diagnostics);
 assert.equal(diagnostics.props.result,result);
 assert.equal(diagnostics.props.config.signalNoiseEnabled,true);
 const text=JSON.stringify(tree);
 assert.match(text,/אות ורעש מופעל/);
 assert.match(text,/פעם אחת/);
});

test('diagnostics visibly disclose unavailable institutes and an inapplicable Gilead target',()=>{
 const Diagnostics=component('SignalNoiseDiagnostics.jsx','SignalNoiseDiagnostics');
 const diagnostics={coverage:{observationCount:11,instituteCount:5},parties:{},weightingPolicy:{unavailableInstitutes:['b']}};
 const tree=Diagnostics({input,config:{weightMode:'gilead',gileadTarget:'b',signalNoiseEnabled:true},result:{signalNoise:diagnostics}});
 const warning=elements(tree).find(element=>element.props['data-unavailable-institutes']==='b');
 assert.ok(warning);
 assert.match(JSON.stringify(warning),/מכון ב/);
 assert.match(JSON.stringify(warning),/מנורמלת מחדש/);
 assert.match(JSON.stringify(warning),/אינו מיושם/);
});
