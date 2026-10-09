import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import React from '../dashboard/node_modules/react/index.js';
import {transformSync} from '../dashboard/node_modules/rolldown/dist/experimental-index.mjs';
const PublicSlider=()=>null;
function stepControl(props){
 const source=fs.readFileSync(new URL('../dashboard/src/content/dashboard/StepControl.jsx',import.meta.url),'utf8');
 const compiled=transformSync('StepControl.jsx',source,{jsx:{runtime:'classic'}});assert.equal(compiled.errors.length,0);
 const code=compiled.code.replace(/^import[^;]*;\s*/gm,'').replace(/export function /g,'function ').replace(/export default StepControl;/,'');
 const bindings={React,PublicSlider,useState:initial=>[typeof initial==='function'?initial():initial,()=>{}],useRef:current=>({current}),useId:()=>':test:',useEffect:callback=>callback()};
 return Function(...Object.keys(bindings),code+'\nreturn StepControl;')(...Object.values(bindings))(props);
}
function elements(tree){const out=[];function visit(value){if(Array.isArray(value))return value.forEach(visit);if(!value||typeof value!=='object'||!value.props)return;out.push(value);visit(value.props.children);}visit(tree);return out;}
const baseline=53.1642655457856;

test('display-only rounding leaves the precise baseline unchanged after untouched Enter or blur',()=>{
 const changes=[],all=elements(stepControl({value:baseline,min:0,max:100,step:.1,suffix:'%',displayPrecision:1,onChange:value=>changes.push(value)}));
 const input=all.find(node=>node.type==='input');
 assert.equal(input.props.value,'53.2');assert.equal(input.props['aria-valuenow'],baseline);assert.equal(input.props['aria-valuetext'],'53.2%');
 assert.equal(all.find(node=>node.type===PublicSlider).props.value,baseline);
 input.props.onBlur();input.props.onKeyDown({key:'Enter',preventDefault:()=>{}});
 assert.deepEqual(changes,[]);
});

test('arrows use the precise baseline rather than the rounded display value',()=>{
 for(const direction of [1,-1]){
  const changes=[],all=elements(stepControl({value:baseline,min:0,max:100,step:.1,displayPrecision:1,onChange:value=>changes.push(value)}));
  const arrows=all.filter(node=>node.type==='button');arrows[direction===1?0:1].props.onClick();
  assert.deepEqual(changes,[Number((baseline+direction*.1).toFixed(12))]);
  assert.ok(Math.abs(changes[0]-(53.2+direction*.1))>.03);
 }
});

test('editing then committing the rounded field intentionally updates the model, while the default display remains unrounded',()=>{
 const changes=[],all=elements(stepControl({value:baseline,min:0,max:100,step:.1,displayPrecision:1,onChange:value=>changes.push(value)}));
 const input=all.find(node=>node.type==='input');input.props.onChange({target:{value:'60'}});input.props.onBlur();
 assert.deepEqual(changes,[60]);
 const defaultInput=elements(stepControl({value:baseline,min:0,max:100,step:.1})).find(node=>node.type==='input');
 assert.equal(defaultInput.props.value,Number(baseline.toPrecision(12)).toString());
 assert.notEqual(defaultInput.props.value,'53.2');assert.equal(defaultInput.props['aria-valuenow'],baseline);
});
