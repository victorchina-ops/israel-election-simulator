import test from 'node:test';
import assert from 'node:assert/strict';
import {createPartyAssignmentDragData,parsePartyAssignmentDragData,partyAssignmentRequest,groupResultParties} from '../dashboard/src/content/dashboard/result-party-assignment.js';
import {assignPartyToBloc} from '../dashboard/src/content/dashboard/bloc-presets.js';

const parties=[{id:'likud',name:'הליכוד',defaultBloc:'a'},{id:'yashar',name:'ישר',defaultBloc:'b'},{id:'joint',name:'המשותפת',defaultBloc:'other'},{id:'remainder',ballot:false}];
test('result cards form one exclusive group per available party',()=>{
 const groups=groupResultParties(parties,{likud:'b',yashar:'other',joint:'a',remainder:'a'});
 assert.deepEqual(Object.fromEntries(Object.entries(groups).map(([key,rows])=>[key,rows.map(row=>row.id)])),{a:['joint'],b:['likud'],other:['yashar']});
 assert.equal(new Set(Object.values(groups).flat().map(p=>p.id)).size,3);
 assert.deepEqual(groupResultParties(parties,{likud:'invalid'}).other.map(p=>p.id),['likud','joint']);
});
test('drag payload only identifies an available ballot party from this app',()=>{
 assert.equal(parsePartyAssignmentDragData(createPartyAssignmentDragData('likud'),parties),'likud');
 for(const raw of ['',null,'not json','"likud"',createPartyAssignmentDragData('remainder'),createPartyAssignmentDragData('unknown'),JSON.stringify({kind:'election-party-assignment',version:2,partyId:'likud'}),'x'.repeat(1025)])assert.equal(parsePartyAssignmentDragData(raw,parties),null);
});
test('native select and drop use the same validated assignment and retain unrelated settings',()=>{
 const initial={weightMode:'quality',includeChannel14:false,pollCorrelationEnabled:true,iterations:10000,partyBlocs:{likud:'a',yashar:'b',joint:'other',remainder:'other'},blocMultipliers:{a:.95,b:1.05}};
 let current=initial;
 for(const bloc of ['b','other','a']){
  const request=partyAssignmentRequest(parties,'likud',bloc);assert.deepEqual(request,{partyId:'likud',bloc});
  current=assignPartyToBloc(current,parties,request.partyId,request.bloc);
  const groups=groupResultParties(parties,current.partyBlocs);
  assert.deepEqual(groups[bloc].filter(p=>p.id==='likud').map(p=>p.id),['likud']);
  assert.equal(Object.values(groups).flat().filter(p=>p.id==='likud').length,1);
  assert.equal(current.weightMode,'quality');assert.equal(current.includeChannel14,false);assert.equal(current.pollCorrelationEnabled,true);assert.equal(current.iterations,10000);assert.deepEqual(current.blocMultipliers,initial.blocMultipliers);
 }
 assert.equal(initial.partyBlocs.likud,'a');
 assert.equal(partyAssignmentRequest(parties,'remainder','a'),null);assert.equal(partyAssignmentRequest(parties,'unknown','a'),null);assert.equal(partyAssignmentRequest(parties,'likud','both'),null);
});
