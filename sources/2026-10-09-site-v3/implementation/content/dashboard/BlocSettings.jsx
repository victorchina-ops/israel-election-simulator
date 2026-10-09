import React,{useMemo} from 'react';
import {Button,DataComponent,SegmentedControl,useDataApp} from '../../data-app-public.jsx';
import {PartyName} from './PartyName.jsx';
import {COALITION_IDS,OPPOSITION_IDS,ARAB_IDS,applyBlocPreset,assignPartyToBloc,normalizeBlocConfig} from './bloc-presets.js';
import './bloc-settings.css';

const OPTIONS=[
  {value:'a',label:'קואליציה',ariaLabel:'שיוך לקואליציה'},
  {value:'b',label:'אופוזיציה',ariaLabel:'שיוך לאופוזיציה'},
  {value:'other',label:'ללא שיוך',ariaLabel:'השארה ללא שיוך'}
];
const GROUPS=[
  {id:'a',title:'קואליציה',subtitle:'הגוש האדום · מוצג מימין'},
  {id:'other',title:'ערביות וללא שיוך',subtitle:'המפלגות האפורות · במרכז'},
  {id:'b',title:'אופוזיציה',subtitle:'הגוש הכחול · מוצג משמאל'}
];

export function BlocSettings({input,config,onChange,compact=false}){
  const {queries}=useDataApp();
  const normalized=useMemo(()=>normalizeBlocConfig(config,input.parties,{legacyMode:config.oppositionMode??'none'}),[config,input.parties]);
  const order=[...COALITION_IDS,...OPPOSITION_IDS,...ARAB_IDS];
  const sorted=[...input.parties.filter(p=>p.ballot!==false)].sort((a,b)=>{
    const ia=order.indexOf(a.id),ib=order.indexOf(b.id);
    return (ia<0?order.length:ia)-(ib<0?order.length:ib);
  });
  const assignments=normalized.partyBlocs;
  const displayRows=sorted.map(p=>({partyId:p.id,party:p.name,bloc:assignments[p.id],oppositionMode:normalized.oppositionMode,
    motivationMultiplier:config.blocMultipliers?.[assignments[p.id]]??1}));
  const counts=Object.fromEntries(['a','b','other'].map(bloc=>[bloc,displayRows.filter(p=>p.bloc===bloc).length]));
  const assign=(partyId,bloc)=>onChange(assignPartyToBloc(normalized,input.parties,partyId,bloc));
  const assignArabs=mode=>{
    let next=normalized;
    for(const id of ARAB_IDS)next=assignPartyToBloc(next,input.parties,id,mode==='all'||(mode==='raam'&&id==='raam')?'b':'other');
    onChange(next);
  };
  const partyCard=p=>{
    const bloc=assignments[p.id];
    return <div className="bloc-settings__party" key={p.id} data-party-assignment data-party-id={p.id} data-assigned-bloc={bloc}>
      <PartyName party={p} bloc={bloc}/>
      <SegmentedControl className="bloc-settings__segmented" ariaLabel={'שיוך '+p.name+' לגוש'} size="default" fullWidth value={bloc} options={OPTIONS.map(option=>({...option,ariaLabel:option.ariaLabel+' — '+p.name}))} onChange={value=>assign(p.id,value)}/>
    </div>;
  };
  const editor=<div className="bloc-settings__editor" data-bloc-editor data-reviewed-rows>
      {GROUPS.map(group=>{
        const members=sorted.filter(p=>assignments[p.id]===group.id);
        return <section className="bloc-settings__column" data-bloc-column={group.id} key={group.id} aria-labelledby={'bloc-column-'+group.id}>
          <header><h3 id={'bloc-column-'+group.id}>{group.title} <strong>{members.length}</strong></h3><p>{group.subtitle}</p></header>
          <div className="bloc-settings__party-list">{members.length?members.map(partyCard):<p className="bloc-settings__empty">אין כרגע מפלגות בקבוצה זו.</p>}</div>
        </section>;
      })}
    </div>;
  return <DataComponent id="e-bloc-settings" title="בחירת הקואליציה והאופוזיציה" kind="custom" variant="card" className={'bloc-settings'+(compact?' bloc-settings--compact':'')}
    queryId="model_configuration" sourceRows={queries.model_configuration.rows} displayRows={displayRows}
    description={'כל רשימה משויכת פעם אחת בלבד לקואליציה, לאופוזיציה או ללא שיוך. הממשק מפריד בין שלוש הקבוצות, ושינוי שיוך מעביר את המפלגה לקבוצה החדשה. הגדרת התרחיש: '+JSON.stringify({oppositionMode:normalized.oppositionMode,partyBlocs:assignments,blocMultipliers:config.blocMultipliers??{}})}>
    <div className="bloc-settings__intro">
      <p>{compact?'אפשר לשייך כל מפלגה לכל גוש, גם ישירות בכרטיסי התוצאות שמתחת להגדרות.':'הקואליציה מוצגת ברצף אדום מימין, האופוזיציה ברצף כחול משמאל, והמפלגות הערביות או הלא־משויכות באפור ביניהן. אפשר להעביר כל מפלגה לכל קבוצה.'}</p>
      <div className="bloc-settings__summary" aria-live="polite" data-reviewed-rows>
        <span data-bloc-count="a"><strong>{counts.a}</strong> בקואליציה</span>
        <span data-bloc-count="b"><strong>{counts.b}</strong> באופוזיציה</span>
        <span data-bloc-count="other"><strong>{counts.other}</strong> ללא שיוך</span>
        <span className="bloc-settings__exclusive">כל {sorted.length} הרשימות משויכות פעם אחת</span>
      </div>
    </div>
    <div className="bloc-settings__quick" role="group" aria-label="קיצורי דרך למפלגות הערביות">
      <span>קיצור דרך לערביות:</span>
      <Button className="bloc-settings__quick-button" onClick={()=>assignArabs('none')}>ללא ערביות באופוזיציה</Button>
      <Button className="bloc-settings__quick-button" onClick={()=>assignArabs('raam')}>רע״ם באופוזיציה</Button>
      <Button className="bloc-settings__quick-button" onClick={()=>assignArabs('all')}>כל הערביות באופוזיציה</Button>
      <Button className="bloc-settings__quick-button" onClick={()=>onChange(applyBlocPreset(config,input.parties,'none'))}>הרכב ברירת המחדל</Button>
    </div>
    {compact?<details className="bloc-settings__full-editor"><summary>שינוי שיוך לכל מפלגה כאן</summary>{editor}</details>:editor}
    <p className="bloc-settings__caption">{compact?'כל מפלגה משויכת פעם אחת. שינוי גוש משנה גם את המוטיבציה שחלה עליה.':'ברירת המחדל כוללת את מפלגות הקואליציה הנוכחית באדום ואת מפלגות האופוזיציה הלא־ערביות בכחול. שינוי השיוך משפיע גם על ספירת 61 המנדטים וגם על בקרי המוטיבציה של הגושים. בכל הרצה כל 120 המנדטים נחלקים בין שני הגושים והמפלגות האפורות.'}</p>
  </DataComponent>;
}
export default BlocSettings;
