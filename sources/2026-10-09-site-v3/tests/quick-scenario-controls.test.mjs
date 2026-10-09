import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import React from '../dashboard/node_modules/react/index.js';
import {transformSync} from '../dashboard/node_modules/rolldown/dist/experimental-index.mjs';
import * as selection from '../dashboard/src/content/dashboard/model/poll-selection-policy.js';
const StepControl=()=>null;
const choices=['quality','equal','reference','littlepolls','gilead','rosner','ensemble','robust'];
function quick(props){
 const source=fs.readFileSync(new URL('../dashboard/src/content/dashboard/QuickScenarioControls.jsx',import.meta.url),'utf8');
 const compiled=transformSync('QuickScenarioControls.jsx',source,{jsx:{runtime:'classic'}});assert.equal(compiled.errors.length,0);
 const code=compiled.code.replace(/^import[^;]*;\s*/gm,'').replace(/export (function|const) /g,'$1 ').replace(/export default QuickScenarioControls;/,'');
 const bindings={React,StepControl,WEIGHTING_CHOICES:choices,WEIGHTING_LABELS:Object.fromEntries([...choices,'correlation'].map(id=>[id,id])),...selection};
 return Function(...Object.keys(bindings),code+'\nreturn QuickScenarioControls;')(...Object.values(bindings))(props);
}
function elements(tree){const out=[];function visit(value){if(Array.isArray(value))return value.forEach(visit);if(!value||typeof value!=='object'||!value.props)return;out.push(value);visit(value.props.children);}visit(tree);return out;}
const config={weightMode:'quality',includeChannel14:false,pollCorrelationEnabled:false,turnout:{arab_localities:53.45,haredi_three_cities:81.4,other:70},blocMultipliers:{a:1,b:1,other:.97},pollWeights:{next_data:.5},excludedPolls:['sample']};

test('quick controls expose six immediately usable controls without shadowing their full-setting labels',()=>{
 const all=elements(quick({config,onConfigChange:()=>{}}));
 assert.equal(all.filter(node=>node.props['data-quick-control']).length,6);
 const select=all.find(node=>node.type==='select');assert.deepEqual(elements(select).filter(node=>node.type==='option').map(node=>node.props.value),choices);
 assert.equal(select.props.value,'quality');assert.equal(select.props['aria-label'],'שיטת שקלול מהירה');
 assert.deepEqual(all.filter(node=>node.type==='input').map(node=>[node.props['aria-label'],node.props.checked]),[['סקרי ערוץ 14',false],['צמצום משקל לסקרים דומים',false]]);
 assert.equal(all.filter(node=>node.type===StepControl).length,3);
 assert.ok(all.filter(node=>node.type===StepControl).every(node=>node.props.label.endsWith('— שינוי מהיר')));
 assert.ok(!all.some(node=>node.type==='details'));
});

test('quick settings preserve nested choices and manual survey exclusions when applying changes',()=>{
 const patches=[],all=elements(quick({config,onConfigChange:patch=>patches.push(patch)}));
 all.find(node=>node.type==='select').props.onChange({target:{value:'equal'}});
 const checks=all.filter(node=>node.type==='input');checks[0].props.onChange({target:{checked:true}});checks[1].props.onChange({target:{checked:true}});
 const steps=all.filter(node=>node.type===StepControl);steps[0].props.onChange(60);steps[1].props.onChange(.95);steps[2].props.onChange(1.05);
 assert.deepEqual(patches,[{weightMode:'equal'},{includeChannel14:true},{pollCorrelationEnabled:true},{turnout:{...config.turnout,arab_localities:60}},{blocMultipliers:{...config.blocMultipliers,a:.95}},{blocMultipliers:{...config.blocMultipliers,b:1.05}}]);
 assert.equal(config.turnout.arab_localities,53.45);assert.deepEqual(config.pollWeights,{next_data:.5});assert.deepEqual(config.excludedPolls,['sample']);
 assert.equal(steps[0].props.value,53.45);assert.equal(steps[0].props.displayPrecision,1);assert.equal(steps[0].props.formatValue(53.1642655),'53.2%');assert.equal(steps[1].props.displayScale,100);assert.equal(steps[2].props.step,.01);
});

test('quick settings safely display legacy weight mode and read-only selected values',()=>{
 const all=elements(quick({config:{...config,weightMode:'correlation',includeChannel14:true,pollCorrelationEnabled:true}}));
 assert.equal(all.find(node=>node.type==='select').props.disabled,true);
 assert.ok(all.some(node=>node.type==='option'&&node.props.value==='correlation'));
 assert.ok(all.filter(node=>node.type==='input').every(node=>node.props.checked&&node.props.disabled));
 assert.ok(all.filter(node=>node.type===StepControl).every(node=>node.props.disabled));
 for(const node of all.filter(node=>node.type==='input'))assert.doesNotThrow(()=>node.props.onChange({target:{checked:false}}));
 const patches=[],robust=elements(quick({config,onConfigChange:patch=>patches.push(patch)}));robust.find(node=>node.type==='select').props.onChange({target:{value:'robust'}});
 assert.deepEqual(patches,[{weightMode:'robust',robustShrinkage:.25}]);
});
