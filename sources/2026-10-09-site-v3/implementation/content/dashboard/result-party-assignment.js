import {POLITICAL_BLOCS} from './bloc-presets.js';

// Dragging is only a convenience. The native select on each result card is the
// complete keyboard/touch route through exactly the same assignment callback.
export const PARTY_ASSIGNMENT_MIME='application/x-election-party-assignment';

export function partyAssignmentRequest(parties,partyId,bloc){
 const party=(parties??[]).find(row=>row.id===partyId&&row.ballot!==false);
 return party&&POLITICAL_BLOCS.includes(bloc)?{partyId:party.id,bloc}:null;
}

export function createPartyAssignmentDragData(partyId){
 return JSON.stringify({kind:'election-party-assignment',version:1,partyId});
}

export function parsePartyAssignmentDragData(raw,parties){
 if(typeof raw!=='string'||raw.length>1024)return null;
 try{
  const value=JSON.parse(raw);
  if(value?.kind!=='election-party-assignment'||value.version!==1||typeof value.partyId!=='string')return null;
  return (parties??[]).some(party=>party.id===value.partyId&&party.ballot!==false)?value.partyId:null;
 }catch{return null;}
}

export function groupResultParties(parties,partyBlocs={}){
 const groups={a:[],b:[],other:[]};
 for(const party of parties??[]){
  if(party.ballot===false)continue;
  const requested=partyBlocs[party.id]??party.defaultBloc;
  groups[requested==='a'||requested==='b'?requested:'other'].push(party);
 }
 return groups;
}
