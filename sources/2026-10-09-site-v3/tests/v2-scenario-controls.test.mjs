import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import React from '../dashboard/node_modules/react/index.js';
import {transformSync} from '../dashboard/node_modules/rolldown/dist/experimental-index.mjs';
import * as selectionPolicy from '../dashboard/src/content/dashboard/model/poll-selection-policy.js';

const stub=()=>null;
function control(){
 const source=fs.readFileSync(new URL('../dashboard/src/content/dashboard/ScenarioControls.jsx',import.meta.url),'utf8');
 const compiled=transformSync('ScenarioControls.jsx',source,{jsx:{runtime:'classic'}});assert.equal(compiled.errors.length,0);
 const code=compiled.code.replace(/^import[^;]*;\s*/gm,'').replace(/export (function|const) /g,'$1 ');
 const bindings={React,Switch:stub,WEIGHTING_LABELS:{quality:'דיוק היסטורי'},...selectionPolicy};
 return Function(...Object.keys(bindings),code+'\nreturn ScenarioControls;')(...Object.values(bindings));
}
function elements(tree){const out=[];function visit(value){if(Array.isArray(value))return value.forEach(visit);if(!value||typeof value!=='object'||!value.props)return;out.push(value);visit(value.props.children);}visit(tree);return out;}
const config={weightMode:'quality',includeChannel14:false,pollCorrelationEnabled:false,signalNoiseEnabled:true,blocMultipliers:{a:1,b:1}};
const props={config,blocSummary:'קואליציה 7 · אופוזיציה 4 · ללא שיוך 6',polls:React.createElement('div',{'data-test-panel':'polls'}),blocs:React.createElement('div',{'data-test-panel':'blocs'}),turnout:React.createElement('div',{'data-test-panel':'turnout'}),onConfigChange:()=>{}};

test('v3 exposes all three labeled settings regions and their supplied controls immediately',()=>{
 const all=elements(control()(props));
 const panels=all.filter(node=>node.props.id?.startsWith('scenario-panel-'));
 assert.deepEqual(panels.map(node=>node.props.id),['scenario-panel-polls','scenario-panel-blocs','scenario-panel-turnout']);
 assert.ok(panels.every(node=>node.type==='section'&&node.props['aria-labelledby']));
 assert.deepEqual(all.filter(node=>node.props['data-test-panel']).map(node=>node.props['data-test-panel']),['polls','blocs','turnout']);
 assert.ok(!all.some(node=>node.props['aria-expanded']!==undefined));
 assert.equal(all[0].props['aria-label'],'הגדרות התרחיש');assert.match(JSON.stringify(all),/התוצאות מתעדכנות אוטומטית/);
 assert.match(JSON.stringify(all),/בחירות 2022/);assert.match(JSON.stringify(all),/דיוק היסטורי/);
 assert.ok(!JSON.stringify(all).includes('אות ורעש'));
});

test('v3 Channel 14 and similarity switches are directly reachable and change only their own flag',()=>{
 const patches=[],all=elements(control()({...props,onConfigChange:patch=>patches.push(patch)}));
 const switches=all.filter(node=>node.type===stub);assert.equal(switches.length,2);
 assert.deepEqual(switches.map(node=>node.props.checked),[false,false]);
 switches.find(node=>node.props.label==='כלול סקרי ערוץ 14').props.onChange(true);
 switches.find(node=>node.props.label==='דמיון בין סקרים').props.onChange(true);
 assert.deepEqual(patches,[{includeChannel14:true},{pollCorrelationEnabled:true}]);
 assert.equal(config.includeChannel14,false);assert.equal(config.pollCorrelationEnabled,false);
 for(const flag of ['channel14','poll-correlation'])assert.equal(all.filter(node=>node.props['data-scenario-control']===flag).length,1);
});

test('v3 switches reflect explicit imported choices and remain safe in a read-only view',()=>{
 const all=elements(control()({...props,config:{...config,includeChannel14:true,pollCorrelationEnabled:true},onConfigChange:undefined}));
 assert.ok(all.filter(node=>node.type===stub).every(node=>node.props.checked===true&&node.props.disabled===true));
 for(const node of all.filter(node=>node.type===stub))assert.doesNotThrow(()=>node.props.onChange(false));
 assert.match(JSON.stringify(all),/ON · נכללים/);assert.match(JSON.stringify(all),/ON · ניסיוני/);
 assert.match(JSON.stringify(all),/אינו מוכיח מדגם משותף/);assert.match(JSON.stringify(all),/סדרות קצרות/);
});

test('v3 settings use spread desktop columns and natural-height mobile sections',()=>{
 const css=fs.readFileSync(new URL('../dashboard/src/content/dashboard/scenario-controls.css',import.meta.url),'utf8');
 assert.match(css,/scenario-controls__grid\{display:grid;grid-template-columns:repeat\(3,minmax\(0,1fr\)\)/);
 assert.match(css,/scenario-controls__panel\{[^}]*max-height:none;overflow:visible/);
 assert.match(css,/@media\(max-width:700px\)\{\.scenario-controls__grid\{grid-template-columns:1fr/);
 assert.ok(!css.includes('dvh'));assert.ok(!css.includes('scenario-controls__signal-noise'));
});
