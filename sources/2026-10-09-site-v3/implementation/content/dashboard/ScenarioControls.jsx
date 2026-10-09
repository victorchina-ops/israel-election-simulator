import React from 'react';
import {Switch} from '../../data-app-public.jsx';
import {WEIGHTING_LABELS} from './WeightingControl.jsx';
import {channel14Included} from './model/poll-selection-policy.js';
import './scenario-controls.css';

export function ScenarioControls({config,blocSummary,turnoutChanged,polls,blocs,turnout,onConfigChange}){
 const choices=[
  {id:'polls',number:'01',label:'סקרים ושקלול',description:'בחרו שיטה ומקורות לתחזית.',value:WEIGHTING_LABELS[config.weightMode]??config.weightMode,content:polls},
  {id:'blocs',number:'02',label:'מי בכל גוש?',description:'שייכו מפלגות לקואליציה, לאופוזיציה או ללא שיוך.',value:blocSummary??'הרכב ידני',content:blocs},
  {id:'turnout',number:'03',label:'מי מגיע לקלפי?',description:'שנו אחוזי הצבעה ומוטיבציה.',value:turnoutChanged?'תרחיש השתתפות מותאם':'בסיס ההשתתפות: בחירות 2022',content:turnout},
 ];
 return <section className="scenario-controls scenario-controls--spread" aria-label="הגדרות התרחיש">
  <div className="scenario-controls__heading"><div><p className="scenario-controls__scope">שנו כאן את ההנחות. התוצאות מתעדכנות אוטומטית והבחירות נשמרות במעבר בין הדפים.</p></div><span className="scenario-controls__live"><span aria-hidden="true"/>עדכון אוטומטי</span></div>
  <div className="scenario-controls__grid">{choices.map(item=><section className="scenario-controls__panel" id={'scenario-panel-'+item.id} data-scenario-control={item.id} key={item.id} aria-labelledby={'scenario-heading-'+item.id}>
   <header className="scenario-controls__panel-heading"><span className="scenario-controls__number" aria-hidden="true">{item.number}</span><div><h3 id={'scenario-heading-'+item.id}>{item.label}</h3><p className="scenario-controls__description">{item.description}</p></div></header>
   <p className="scenario-controls__value" data-current-scenario-summary={item.id}>{item.value}</p>
   {item.id==='polls'&&<div className="scenario-controls__features" aria-label="מקורות ואפשרויות שקלול">
    <div className="scenario-controls__channel14" id="scenario-channel14-switch" data-scenario-control="channel14" data-channel14-enabled={channel14Included(config)} data-reviewed-rows>
     <div className="scenario-controls__channel14-heading"><Switch label="כלול סקרי ערוץ 14" checked={channel14Included(config)} disabled={!onConfigChange} onChange={value=>onConfigChange?.({includeChannel14:value})}/><span className="scenario-controls__channel14-state">{channel14Included(config)?'ON · נכללים':'OFF · מוחרגים'}</span></div>
     <p className="scenario-controls__channel14-description">כבוי בברירת המחדל. ההפעלה מוסיפה אותם לתחזית ולמגמות.</p>
    </div>
    <div className="scenario-controls__poll-correlation" id="scenario-poll-correlation-switch" data-scenario-control="poll-correlation" data-poll-correlation-enabled={config.pollCorrelationEnabled===true} data-reviewed-rows>
     <div className="scenario-controls__poll-correlation-heading"><Switch label="דמיון בין סקרים" checked={config.pollCorrelationEnabled===true} disabled={!onConfigChange} onChange={value=>onConfigChange?.({pollCorrelationEnabled:value})}/><span className="scenario-controls__poll-correlation-state">{config.pollCorrelationEnabled===true?'ON · ניסיוני':'OFF · ניסיוני'}</span></div>
     <p className="scenario-controls__poll-correlation-description">ממתן משקל וביטחון בסקרים דומים לאורך זמן; הדיוק ההיסטורי נשמר.</p>
     <details className="scenario-controls__feature-note"><summary>מה מגבלת האפשרות הזו?</summary><p>דמיון יכול לשקף מגמה אמיתית, ואינו מוכיח מדגם משותף או טעויות משותפות. ההשוואה מבוססת על סדרות קצרות ועל מפלגות שאפשר להשוות; לזוגות שחסר עליהם מידע לא מניחים דמיון אפסי. החוזק שמרני, וההתאמה לא הוכחה כמדויקת יותר.</p></details>
    </div>
   </div>}
   <div className="scenario-controls__content">{item.content}</div>
  </section>)}</div>
 </section>;
}
