export const COALITION_IDS=Object.freeze(['likud','shas','utj','otzma','rz_zehut','winter','noam']);
export const OPPOSITION_IDS=Object.freeze(['yashar','beyachad','democrats','yisrael_beiteinu']);
export const ARAB_IDS=Object.freeze(['raam','joint']);
export const POLITICAL_BLOCS=Object.freeze(['a','b','other']);
export const OPPOSITION_MODES=Object.freeze({none:'ללא מפלגות ערביות',raam:'עם רע״ם בלבד',all:'עם כל המפלגות הערביות',custom:'הרכב ידני'});

const validBloc=new Set(POLITICAL_BLOCS);

function presetPartyBlocs(parties,mode){
  if(!['none','raam','all'].includes(mode))throw new Error('הרכב אופוזיציה לא מוכר: '+mode);
  if(!Array.isArray(parties))throw new Error('דרושה רשימת מפלגות להחלת הרכב הגושים.');
  const coalition=new Set(COALITION_IDS),opposition=new Set([...OPPOSITION_IDS,...(mode==='all'?ARAB_IDS:mode==='raam'?['raam']:[])]);
  const partyBlocs={},seen=new Set();
  for(const party of parties){
    if(!party||typeof party.id!=='string'||!party.id||seen.has(party.id))throw new Error('מזהה מפלגה חסר או כפול בהרכב הגושים.');
    seen.add(party.id);
    partyBlocs[party.id]=party.ballot===false?'other':coalition.has(party.id)?'a':opposition.has(party.id)?'b':'other';
  }
  return partyBlocs;
}

/** Build a complete, exclusive a/b/other assignment for every available party. */
export function normalizePartyBlocs(parties,source={}){
  if(!Array.isArray(parties))throw new Error('דרושה רשימת מפלגות לנרמול הרכב הגושים.');
  const input=source&&typeof source==='object'&&!Array.isArray(source)?source:{};
  const partyBlocs={},seen=new Set();
  for(const party of parties){
    if(!party||typeof party.id!=='string'||!party.id||seen.has(party.id))throw new Error('מזהה מפלגה חסר או כפול בהרכב הגושים.');
    seen.add(party.id);
    const requested=input[party.id];
    partyBlocs[party.id]=party.ballot===false?'other':validBloc.has(requested)?requested:'other';
  }
  return partyBlocs;
}

export function inferOppositionMode(parties,partyBlocs){
  const normalized=normalizePartyBlocs(parties,partyBlocs);
  for(const mode of ['none','raam','all']){
    const preset=presetPartyBlocs(parties,mode);
    if(parties.every(p=>preset[p.id]===normalized[p.id]))return mode;
  }
  return 'custom';
}

/** Return explicit membership for every party while preserving all other settings. */
export function applyBlocPreset(config,parties,mode='none'){
  const partyBlocs=presetPartyBlocs(parties,mode);
  return {...config,oppositionMode:mode,partyBlocs};
}

/** Preserve an explicit saved map; use a legacy preset only when a map is absent. */
export function normalizeBlocConfig(config,parties,{legacyMode='none'}={}){
  const hasExplicit=config?.partyBlocs&&typeof config.partyBlocs==='object'&&!Array.isArray(config.partyBlocs)&&Object.keys(config.partyBlocs).length>0;
  if(!hasExplicit)return applyBlocPreset(config??{},parties,['none','raam','all'].includes(legacyMode)?legacyMode:'none');
  const partyBlocs=normalizePartyBlocs(parties,config.partyBlocs);
  return {...config,partyBlocs,oppositionMode:inferOppositionMode(parties,partyBlocs)};
}

/** A party has one value, so moving it automatically removes it from the other bloc. */
export function assignPartyToBloc(config,parties,partyId,bloc){
  if(!validBloc.has(bloc))throw new Error('שיוך גוש לא מוכר: '+bloc);
  const party=parties.find(item=>item.id===partyId);
  if(!party||party.ballot===false)throw new Error('אפשר לשייך רק רשימה שמתמודדת בבחירות.');
  const partyBlocs=normalizePartyBlocs(parties,{...(config?.partyBlocs??{}),[partyId]:bloc});
  return {...config,partyBlocs,oppositionMode:inferOppositionMode(parties,partyBlocs)};
}

export function describeBlocComposition(config,parties=[]){
  const partyBlocs=normalizePartyBlocs(parties,config?.partyBlocs);
  const ballot=parties.filter(p=>p.ballot!==false);
  const count=bloc=>ballot.filter(p=>partyBlocs[p.id]===bloc).length;
  return `קואליציה ${count('a')} · אופוזיציה ${count('b')} · ללא שיוך ${count('other')}`;
}
