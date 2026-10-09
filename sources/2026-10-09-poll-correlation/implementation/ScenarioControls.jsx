import React,{useState} from 'react';
import {Button,Switch} from '../../data-app-public.jsx';
import {WEIGHTING_LABELS} from './WeightingControl.jsx';
import {SIGNAL_NOISE_CREDIT} from './signal-noise-content.js';
import {channel14Included} from './model/poll-selection-policy.js';
import './scenario-controls.css';

export function ScenarioControls({config,blocSummary,turnoutChanged,polls,blocs,turnout,onConfigChange}){
 const [open,setOpen]=useState(null);
 const choices=[
  {id:'polls',label:'סקרים ושקלול',description:'בחרו שיטת שקלול והתאימו את המשקל של כל סקר.',value:WEIGHTING_LABELS[config.weightMode]??config.weightMode,content:polls},
  {id:'blocs',label:'הרכב הגושים',description:'שייכו כל מפלגה לקואליציה, לאופוזיציה או ללא שיוך.',value:blocSummary??'הרכב ידני',content:blocs},
  {id:'turnout',label:'אחוזי הצבעה ומוטיבציה',description:'שנו את המוטיבציה בגושים ואת ההצבעה בקרב ערבים וחרדים.',value:(turnoutChanged?'השתתפות מותאמת':'בסיס 2022')+' · מוטיבציה: קואליציה '+Math.round((config.blocMultipliers?.a??1)*100)+'%, אופוזיציה '+Math.round((config.blocMultipliers?.b??1)*100)+'%',content:turnout},
 ];
 const selected=choices.find(item=>item.id===open);
 return <section className="scenario-controls" data-open={open??''} aria-label="הגדרות התרחיש">
  <div className="scenario-controls__buttons">{choices.map(item=><Button key={item.id} className="scenario-controls__trigger" data-scenario-control={item.id} aria-expanded={open===item.id} aria-controls={'scenario-panel-'+item.id} onClick={()=>setOpen(previous=>previous===item.id?null:item.id)}>
   <span className="scenario-controls__intro"><span className="scenario-controls__label">{item.label}<span aria-hidden="true">{open===item.id?'▴':'▾'}</span></span><span className="scenario-controls__description">{item.description}</span><span className="scenario-controls__hint">{open===item.id?'פתוח · לחצו לסגירה':'לחצו לפתיחה'}</span></span><span className="scenario-controls__value">{item.value}</span>
  </Button>)}</div>
  <div className="scenario-controls__features" aria-label="אפשרויות חיזוי ומקורות">
  <div className="scenario-controls__signal-noise" data-scenario-control="signal-noise" data-signal-noise-enabled={config.signalNoiseEnabled===true} data-reviewed-rows>
   <div className="scenario-controls__signal-noise-heading"><Switch label="אות ורעש — ניסיוני" checked={config.signalNoiseEnabled===true} disabled={!onConfigChange} onChange={value=>onConfigChange?.({signalNoiseEnabled:value})}/><span className="scenario-controls__signal-noise-state">{config.signalNoiseEnabled===true?'ON · מופעל':'OFF · כבוי'}</span></div>
   <p className="scenario-controls__signal-noise-description">מנסה להפריד שינוי בתמיכה מרעש בסקרים. עובד עם שיטת השקלול שבחרתם, בכל תוצאות הסימולציה וההשוואות.</p>
   <p className="scenario-controls__signal-noise-credit">יישום שלנו בהשראת <a href={SIGNAL_NOISE_CREDIT.methodology} target="_blank" rel="noreferrer">{SIGNAL_NOISE_CREDIT.name}</a> · טרם הוכחה עדיפות בחיזוי.</p>
  </div>
  <div className="scenario-controls__channel14" id="scenario-channel14-switch" data-scenario-control="channel14" data-channel14-enabled={channel14Included(config)} data-reviewed-rows>
   <div className="scenario-controls__channel14-heading"><Switch label="כלול סקרי ערוץ 14" checked={channel14Included(config)} disabled={!onConfigChange} onChange={value=>onConfigChange?.({includeChannel14:value})}/><span className="scenario-controls__channel14-state">{channel14Included(config)?'ON · נכללים':'OFF · אינם נכללים'}</span></div>
   <p className="scenario-controls__channel14-description">ברירת המחדל ללא סקרי ערוץ 14. הפעילו כדי לאפשר את הכללתם בשקלול ובתחזיות; הבחירות והמשקלים הידניים נשמרים.</p>
  </div>
  <div className="scenario-controls__poll-correlation" id="scenario-poll-correlation-switch" data-scenario-control="poll-correlation" data-poll-correlation-enabled={config.pollCorrelationEnabled===true} data-reviewed-rows>
   <div className="scenario-controls__poll-correlation-heading"><Switch label="דמיון בין סקרים" checked={config.pollCorrelationEnabled===true} disabled={!onConfigChange} onChange={value=>onConfigChange?.({pollCorrelationEnabled:value})}/><span className="scenario-controls__poll-correlation-state">{config.pollCorrelationEnabled===true?'ON · מופעל':'OFF · כבוי'}</span></div>
   <p className="scenario-controls__poll-correlation-description">ממתן את המשקל ואת הביטחון בסקרים שתוצאותיהם דומות לאורך זמן. הדיוק ההיסטורי נשמר. ניסיוני: הדמיון עשוי לשקף מגמה אמיתית, ואינו מוכיח מדגם משותף.</p>
  </div>
  </div>
  {selected&&<div className="scenario-controls__panel" id={'scenario-panel-'+selected.id} role="region" aria-label={selected.label} tabIndex={0}>
   {selected.id==='polls'&&<p className="scenario-controls__uncertainty">הסימולציה כוללת תמיד אפשרות לטעות בסקרים.</p>}
   {selected.content}
  </div>}
 </section>;
}
