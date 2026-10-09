import React,{useState} from 'react';
import {Button,Switch} from '../../data-app-public.jsx';
import {WEIGHTING_LABELS} from './WeightingControl.jsx';
import {channel14Included} from './model/poll-selection-policy.js';
import './scenario-controls.css';

export function ScenarioControls({config,blocSummary,turnoutChanged,polls,blocs,turnout,onConfigChange}){
 const [open,setOpen]=useState(null);
 const choices=[
  {id:'polls',label:'סקרים ושקלול',description:'אילו סקרים נכללים וכמה הם משפיעים.',value:(WEIGHTING_LABELS[config.weightMode]??config.weightMode)+' · '+(channel14Included(config)?'עם ערוץ 14':'ללא ערוץ 14')+(config.pollCorrelationEnabled===true?' · תיקון דמיון פעיל':''),content:polls},
  {id:'blocs',label:'הרכב הגושים',description:'מי בקואליציה, באופוזיציה או ללא שיוך.',value:blocSummary??'הרכב ידני',content:blocs},
  {id:'turnout',label:'השתתפות בהצבעה',description:'אחוזי הצבעה ומוטיבציה בכל קבוצה.',value:(turnoutChanged?'השתתפות מותאמת':'בסיס 2022')+' · קואליציה '+Math.round((config.blocMultipliers?.a??1)*100)+'% · אופוזיציה '+Math.round((config.blocMultipliers?.b??1)*100)+'%',content:turnout},
 ];
 const selected=choices.find(item=>item.id===open);
 function closePanel(event){
  event?.currentTarget?.closest?.('.scenario-controls')?.querySelector?.('[data-scenario-control="'+open+'"]')?.focus?.();
  setOpen(null);
 }
 return <section className="scenario-controls" data-open={open??''} aria-label="הגדרות התרחיש">
  <p className="scenario-controls__scope">הבחירות חלות על כל דפי התחזית. התוצאות מתעדכנות אוטומטית.</p>
  <div className="scenario-controls__buttons">{choices.map(item=><Button key={item.id} className="scenario-controls__trigger" data-scenario-control={item.id} aria-expanded={open===item.id} aria-controls={'scenario-panel-'+item.id} onClick={()=>setOpen(previous=>previous===item.id?null:item.id)}>
   <span className="scenario-controls__intro"><span className="scenario-controls__label">{item.label}<span className="scenario-controls__arrow" aria-hidden="true">{open===item.id?'−':'+'}</span></span><span className="scenario-controls__description">{item.description}</span></span>
   <span className="scenario-controls__value">{item.value}</span>
   <span className="scenario-controls__hint">{open===item.id?'פתוח · לחצו לסגירה':'לחצו לשינוי'}</span>
  </Button>)}</div>
  {selected&&<div className="scenario-controls__panel" id={'scenario-panel-'+selected.id} role="region" aria-label={selected.label} onKeyDown={event=>{if(event.key==='Escape'&&!event.defaultPrevented){event.stopPropagation();closePanel(event);}}}>
   <div className="scenario-controls__panel-heading"><h3>{selected.label}</h3><Button className="scenario-controls__close" aria-label={'סגירת הגדרות '+selected.label} onClick={closePanel}>סגירה <span aria-hidden="true">×</span></Button></div>
   {selected.id==='polls'&&<>
   <div className="scenario-controls__features" aria-label="מקורות ואפשרויות שקלול">
  <div className="scenario-controls__channel14" id="scenario-channel14-switch" data-scenario-control="channel14" data-channel14-enabled={channel14Included(config)} data-reviewed-rows>
   <div className="scenario-controls__channel14-heading"><Switch label="כלול סקרי ערוץ 14" checked={channel14Included(config)} disabled={!onConfigChange} onChange={value=>onConfigChange?.({includeChannel14:value})}/><span className="scenario-controls__channel14-state">{channel14Included(config)?'נכללים':'לא נכללים'}</span></div>
   <p className="scenario-controls__channel14-description">כבוי כברירת מחדל. הפעילו כדי לכלול גם אותם בתחזית ובמגמות; הבחירות והמשקלים הידניים נשמרים.</p>
  </div>
  <div className="scenario-controls__poll-correlation" id="scenario-poll-correlation-switch" data-scenario-control="poll-correlation" data-poll-correlation-enabled={config.pollCorrelationEnabled===true} data-reviewed-rows>
   <div className="scenario-controls__poll-correlation-heading"><Switch label="דמיון בין סקרים" checked={config.pollCorrelationEnabled===true} disabled={!onConfigChange} onChange={value=>onConfigChange?.({pollCorrelationEnabled:value})}/><span className="scenario-controls__poll-correlation-state">{config.pollCorrelationEnabled===true?'מופעל · ניסיוני':'כבוי · ניסיוני'}</span></div>
   <p className="scenario-controls__poll-correlation-description">ממתן משקל וביטחון בסקרים דומים לאורך זמן. הדיוק ההיסטורי נשמר. הדמיון יכול לשקף מגמה אמיתית ואינו מוכיח מדגם משותף.</p>
  </div>
  </div>
   <p className="scenario-controls__uncertainty">כל התחזיות כוללות אפשרות לטעות בסקרים.</p>
   </>}
   {selected.content}
  </div>}
 </section>;
}
