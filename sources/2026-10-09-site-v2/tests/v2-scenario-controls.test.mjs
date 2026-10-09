import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import React from '../dashboard/node_modules/react/index.js';
import {transformSync} from '../dashboard/node_modules/rolldown/dist/experimental-index.mjs';
import * as selectionPolicy from '../dashboard/src/content/dashboard/model/poll-selection-policy.js';

const stub=()=>null;
function control(open=null,setOpen=()=>{}){
 const source=fs.readFileSync(new URL('../dashboard/src/content/dashboard/ScenarioControls.jsx',import.meta.url),'utf8');
 const compiled=transformSync('ScenarioControls.jsx',source,{jsx:{runtime:'classic'}});assert.equal(compiled.errors.length,0);
 const code=compiled.code.replace(/^import[^;]*;\s*/gm,'').replace(/export (function|const) /g,'$1 ');
 const bindings={React,useState:()=>[open,setOpen],Button:stub,Switch:stub,WEIGHTING_LABELS:{quality:'דיוק היסטורי'},...selectionPolicy};
 return Function(...Object.keys(bindings),code+'\nreturn ScenarioControls;')(...Object.values(bindings));
}
function elements(tree){const out=[];function visit(value){if(Array.isArray(value))return value.forEach(visit);if(!value||typeof value!=='object'||!value.props)return;out.push(value);visit(value.props.children);}visit(tree);return out;}
const config={weightMode:'quality',includeChannel14:false,pollCorrelationEnabled:false,signalNoiseEnabled:true,blocMultipliers:{a:1,b:1}};
const props={config,blocSummary:'קואליציה 7 · אופוזיציה 4 · ללא שיוך 6',polls:React.createElement('div',{'data-test-panel':'polls'}),blocs:React.createElement('div',{'data-test-panel':'blocs'}),turnout:React.createElement('div',{'data-test-panel':'turnout'}),onConfigChange:()=>{}};

test('v2 workspace starts with clear category summaries, while advanced switches wait inside poll settings',()=>{
 const all=elements(control()(props));
 assert.equal(all.filter(node=>node.props['aria-controls']?.startsWith('scenario-panel-')).length,3);
 assert.ok(all.filter(node=>node.props['aria-expanded']!==undefined).every(node=>node.props['aria-expanded']===false));
 assert.ok(!all.some(node=>node.props.role==='region'));
 assert.ok(!all.some(node=>node.props['data-scenario-control']==='channel14'));
 assert.ok(!all.some(node=>node.props['data-scenario-control']==='poll-correlation'));
 assert.match(JSON.stringify(all),/ללא ערוץ 14/);assert.match(JSON.stringify(all),/התוצאות מתעדכנות אוטומטית/);
 assert.match(JSON.stringify(all),/לחצו לשינוי/);assert.match(JSON.stringify(all),/השתתפות בהצבעה/);
 assert.ok(!JSON.stringify(all).includes('אות ורעש'));
});

test('v2 exposes exactly one panel at a time and reserves both independent switches for poll settings',()=>{
 for(const open of ['polls','blocs','turnout']){
  const all=elements(control(open)(props));
  const panels=all.filter(node=>node.props.role==='region');assert.equal(panels.length,1);assert.equal(panels[0].props.id,'scenario-panel-'+open);
  const rendered=all.filter(node=>node.props['data-test-panel']);assert.deepEqual(rendered.map(node=>node.props['data-test-panel']),[open]);
  assert.equal(all.filter(node=>['channel14','poll-correlation'].includes(node.props['data-scenario-control'])).length,open==='polls'?2:0);
  assert.equal(all.filter(node=>node.props['aria-expanded']===true).length,1);
 }
});

test('closing a panel or pressing Escape returns focus to its trigger without changing a scenario',()=>{
 let closed=undefined,focused=0,stopped=0,selector='';
 const all=elements(control('polls',value=>{closed=value;})(props));
 const event={key:'Escape',stopPropagation:()=>{stopped++;},currentTarget:{closest:()=>({querySelector:value=>{selector=value;return {focus:()=>{focused++;}};}})}};
 all.find(node=>node.props['aria-label']==='סגירת הגדרות סקרים ושקלול').props.onClick(event);
 assert.equal(closed,null);assert.equal(focused,1);assert.equal(selector,'[data-scenario-control="polls"]');
 closed=undefined;all.find(node=>node.props.role==='region').props.onKeyDown(event);
 assert.equal(closed,null);assert.equal(focused,2);assert.equal(stopped,1);
 closed=undefined;all.find(node=>node.props.role==='region').props.onKeyDown({...event,defaultPrevented:true});
 assert.equal(closed,undefined);assert.equal(focused,2);assert.equal(stopped,1);
});

test('v2 panel CSS removes cramped nested scrolling and stacks controls on narrow screens',()=>{
 const css=fs.readFileSync(new URL('../dashboard/src/content/dashboard/scenario-controls.css',import.meta.url),'utf8');
 assert.match(css,/scenario-controls__panel\{[^}]*max-height:none;overflow:visible/);
 assert.match(css,/@media\(max-width:760px\)\{\s*\.scenario-controls__buttons\{grid-template-columns:1fr/);
 assert.match(css,/scenario-controls__features\{display:grid;grid-template-columns:repeat\(2,minmax\(0,1fr\)\)/);
 assert.ok(!css.includes('dvh'));assert.ok(!css.includes('scenario-controls__signal-noise'));
});
