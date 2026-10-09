import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import React from '../dashboard/node_modules/react/index.js';
import {transformSync} from '../dashboard/node_modules/rolldown/dist/experimental-index.mjs';
import * as copy from '../dashboard/src/content/dashboard/signal-noise-content.js';
import * as selectionPolicy from '../dashboard/src/content/dashboard/model/poll-selection-policy.js';

const queries=Object.fromEntries(['polls','model_configuration','weight_presets','calibration','poll_correlation_profile','signal_noise_observations'].map(id=>[id,{rows:[{id}]}]));
const stub=()=>null;
function component(file,name,extra={}){
 const source=fs.readFileSync(new URL('../dashboard/src/content/dashboard/'+file,import.meta.url),'utf8');
 const compiled=transformSync(file,source,{jsx:{runtime:'classic'}});assert.equal(compiled.errors.length,0);
 const code=compiled.code.replace(/^import[^;]*;\s*/gm,'').replace(/export default[^;]*;/g,'').replace(/export (function|const) /g,'$1 ');
 const bindings={React,useState:value=>[value,()=>{}],DataComponent:stub,Dropdown:stub,Switch:stub,Button:stub,useDataApp:()=>({queries}),StepControl:stub,PollSelectionControl:stub,SignalNoiseInstituteControl:stub,SignalNoiseDiagnostics:stub,...copy,...selectionPolicy,...extra};
 return Function(...Object.keys(bindings),code+'\nreturn '+name+';')(...Object.values(bindings));
}
function elements(tree){const out=[];function visit(value){if(Array.isArray(value)){value.forEach(visit);return;}if(!value||typeof value!=='object'||!value.props)return;out.push(value);visit(value.props.children);}visit(tree);return out;}

test('three global switches share the always-visible feature row and patch only their own flag',()=>{
 const Control=component('ScenarioControls.jsx','ScenarioControls',{WEIGHTING_LABELS:{quality:'דיוק היסטורי'}});
 const config={weightMode:'quality',signalNoiseEnabled:true,includeChannel14:false,pollCorrelationEnabled:false,excludedPolls:['manual'],pollWeights:{kantar:1.4},blocMultipliers:{a:1,b:1}},before=structuredClone(config),patches=[];
 const tree=Control({config,onConfigChange:patch=>patches.push(patch)}),all=elements(tree);
 const row=all.find(element=>element.props.className==='scenario-controls__features');assert.ok(row);
 const cards=elements(row).filter(element=>element.props['data-scenario-control']);
 assert.deepEqual(cards.map(element=>element.props['data-scenario-control']),['signal-noise','channel14','poll-correlation']);
 const controls=elements(row).filter(element=>element.props.label);
 assert.equal(controls.length,3);
 const dependence=controls.find(element=>element.props.label==='דמיון בין סקרים');assert.ok(dependence);
 assert.equal(dependence.props.checked,false);dependence.props.onChange(true);
 assert.deepEqual(patches,[{pollCorrelationEnabled:true}]);assert.deepEqual(config,before);
 assert.equal(all.filter(element=>element.props['aria-controls']?.startsWith('scenario-panel-')).length,3);
 assert.match(JSON.stringify(cards[2]),/לאורך זמן/);assert.match(JSON.stringify(cards[2]),/מגמה אמיתית/);assert.match(JSON.stringify(cards[2]),/אינו מוכיח מדגם משותף/);assert.match(JSON.stringify(cards[2]),/הדיוק ההיסטורי נשמר/);
});

test('current poll similarity remains independent when switching among eight displayed weighting policies',()=>{
 const Control=component('WeightingControl.jsx','WeightingControl');
 const config={weightMode:'reference',pollCorrelationEnabled:true,signalNoiseEnabled:true,includeChannel14:false,excludedPolls:['poll'],pollWeights:{kantar:1.4}},before=structuredClone(config),patches=[];
 const tree=Control({input:{current:{polls:[]}},config,weights:{},onConfigChange:patch=>patches.push(patch)}),all=elements(tree),menu=all.find(element=>element.props.label==='גישת השקלול');
 assert.equal(menu.props.choices.length,8);assert.ok(!menu.props.choices.includes('correlation'));
 for(const mode of menu.props.choices)menu.props.onChange(mode);
 assert.deepEqual(patches.map(patch=>patch.weightMode),menu.props.choices);
 assert.ok(patches.every(patch=>!Object.hasOwn(patch,'pollCorrelationEnabled')));assert.deepEqual(config,before);
 const flag=tree.props.displayRows.find(row=>row.parameter==='pollCorrelationEnabled');assert.equal(flag.value,true);
 assert.ok(tree.props.queryIds.includes('poll_correlation_profile'));assert.deepEqual(tree.props.sourceRowsByQuery.poll_correlation_profile,queries.poll_correlation_profile.rows);
 assert.match(JSON.stringify(tree),/סדרת הסקרים הנוכחית/);assert.match(JSON.stringify(tree),/שיטת השקלול והדיוק ההיסטורי נשמרים/);assert.match(JSON.stringify(tree),/מידע חסר לא מניחים קורלציה אפסית/);
});

test('legacy correlation import remains an explicitly old conditional dropdown choice',()=>{
 const Control=component('WeightingControl.jsx','WeightingControl');
 const config={weightMode:'correlation',pollCorrelationEnabled:false,veteranClusterDiscount:.7},patches=[];
 const tree=Control({input:{current:{polls:[]}},config,weights:{},onConfigChange:patch=>patches.push(patch)}),all=elements(tree),menu=all.find(element=>element.props.label==='גישת השקלול');
 assert.equal(menu.props.value,'correlation');assert.equal(menu.props.choices.length,9);assert.ok(menu.props.choices.includes('correlation'));assert.match(menu.props.choiceLabels.correlation,/ישן/);
 assert.ok(all.some(element=>element.props.label==='מכפיל אשכול ותיקים — הנחה'));
 assert.equal(tree.props.displayRows.find(row=>row.parameter==='veteranClusterDiscount').value,.7);
 menu.props.onChange('quality');assert.deepEqual(patches,[{weightMode:'quality'}]);assert.equal(config.pollCorrelationEnabled,false);
});
