import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import React from '../dashboard/node_modules/react/index.js';
import {transformSync} from '../dashboard/node_modules/rolldown/dist/experimental-index.mjs';

const Button=()=>null;
function about(props){
 const source=fs.readFileSync(new URL('../dashboard/src/content/dashboard/AboutPage.jsx',import.meta.url),'utf8');
 const compiled=transformSync('AboutPage.jsx',source,{jsx:{runtime:'classic'}});assert.equal(compiled.errors.length,0);
 const code=compiled.code.replace(/^import[^;]*;\s*/gm,'').replace(/export (function|const) /g,'$1 ').replace(/export default AboutPage;/,'');
 return Function('React','Button','portrait',code+'\nreturn AboutPage;')(React,Button,'preserved-original-portrait.jpg')(props);
}
function elements(tree){const out=[];function visit(value){if(Array.isArray(value))return value.forEach(visit);if(!value||typeof value!=='object'||!value.props)return;out.push(value);visit(value.props.children);}visit(tree);return out;}
function text(tree){if(tree==null||typeof tree==='boolean')return '';if(Array.isArray(tree))return tree.map(text).join('');if(typeof tree!=='object')return String(tree);return text(tree.props?.children);}

test('about restores the author portrait, original contact and original simulation explanation visibly',()=>{
 const tree=about({asOf:'2026-10-09',onStart:()=>{}}),all=elements(tree),copy=text(tree);
 assert.equal(all.filter(node=>node.type==='h1').length,1);const photo=all.find(node=>node.type==='img');assert.equal(photo.props.src,'preserved-original-portrait.jpg');assert.equal(photo.props.alt,'ויקטור רינה בן דוד');
 assert.equal(all.filter(node=>node.props.href==='mailto:victor.china@gmail.com').length,1);
 assert.match(copy,/משקללים את נתוני הסקרים ומתרגמים אותם להסתברויות הצבעה/);
 assert.match(copy,/מחלקים 120 מנדטים לפי באדר–עופר/);assert.match(copy,/ברירת המחדל היא 10,000 הרצות/);
 assert.match(copy,/קרדיט לויקטור רינה בן דוד/);assert.match(copy,/09\.10\.2026/);
 assert.ok(!all.some(node=>node.type==='details'));
 for(const href of ['https://madad120.co.il/','https://littlepolls.com/#/method','https://themadad.com/polls26/','https://x.com/Michael_Gilead/status/2083925571101217253'])assert.ok(all.some(node=>node.props.href===href));
});

test('about start, original source register and methods actions navigate through the supplied callbacks',()=>{
 const actions=[];const all=elements(about({onStart:()=>actions.push('dashboard'),onOpenPollData:()=>actions.push('poll-data'),onOpenGuide:()=>actions.push('method-data')}));
 const buttons=all.filter(node=>node.type===Button);assert.equal(buttons.length,3);
 for(const button of buttons)button.props.onClick();
 assert.deepEqual(actions,['dashboard','poll-data','method-data']);
 assert.equal(all.find(node=>node.props.className==='about-start').props.disabled,false);
 assert.equal(elements(about({})).find(node=>node.props.className==='about-start').props.disabled,true);
});
