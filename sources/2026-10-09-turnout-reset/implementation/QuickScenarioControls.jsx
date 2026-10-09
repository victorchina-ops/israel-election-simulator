import React from 'react';
import {StepControl} from './StepControl.jsx';
import {WEIGHTING_CHOICES,WEIGHTING_LABELS} from './WeightingControl.jsx';
import {channel14Included} from './model/poll-selection-policy.js';
import './quick-scenario-controls.css';

/** Shortcuts share the full settings' configuration; none introduce a second state. */
export function QuickScenarioControls({config={},onConfigChange,onResetParticipation}){
 const patch=value=>onConfigChange?.(value),disabled=!onConfigChange;
 const mode=config.weightMode??'quality';
 const modes=mode==='correlation'?[...WEIGHTING_CHOICES,'correlation']:WEIGHTING_CHOICES;
 const motive=(bloc,value)=>patch({blocMultipliers:{...config.blocMultipliers,[bloc]:value}});
 function chooseMode(weightMode){patch(weightMode==='robust'&&config.robustShrinkage===undefined?{weightMode,robustShrinkage:.25}:{weightMode});}
 return <section className="quick-scenario-controls" aria-label="שינוי מהיר של התרחיש" data-quick-scenario-controls>
  <div className="quick-scenario-controls__header">
   <p className="quick-scenario-controls__intro">התאימו את התרחיש כאן — התוצאות מתעדכנות אוטומטית.</p>
   <button type="button" className="quick-scenario-controls__reset" onClick={onResetParticipation} disabled={!onResetParticipation} title="חזרה לאחוזי ההשתתפות של 2022 ולמוטיבציה של 100%">איפוס השתתפות ומוטיבציה</button>
  </div>
  <div className="quick-scenario-controls__grid" data-reviewed-rows>
   <div className="quick-scenario-controls__card" data-quick-control="weights"><label className="quick-scenario-controls__label">שיטת שקלול<select aria-label="שיטת שקלול מהירה" value={mode} onChange={event=>chooseMode(event.target.value)} disabled={disabled}>{modes.map(id=><option value={id} key={id}>{WEIGHTING_LABELS[id]??id}</option>)}</select></label><p>אותם סקרים, השפעה שונה.</p></div>
   <div className="quick-scenario-controls__card" data-quick-control="channel14"><label className="quick-scenario-controls__toggle"><span className="quick-scenario-controls__label">סקרי ערוץ 14</span><span className="quick-scenario-controls__toggle-row"><input type="checkbox" aria-label="סקרי ערוץ 14" checked={channel14Included(config)} onChange={event=>patch({includeChannel14:event.target.checked})} disabled={disabled}/><strong>{channel14Included(config)?'ON · נכללים':'OFF · מוחרגים'}</strong></span></label><p>כבוי בברירת המחדל.</p></div>
   <div className="quick-scenario-controls__card" data-quick-control="similarity"><label className="quick-scenario-controls__toggle"><span className="quick-scenario-controls__label">צמצום משקל לסקרים דומים</span><span className="quick-scenario-controls__toggle-row"><input type="checkbox" aria-label="צמצום משקל לסקרים דומים" checked={config.pollCorrelationEnabled===true} onChange={event=>patch({pollCorrelationEnabled:event.target.checked})} disabled={disabled}/><strong>{config.pollCorrelationEnabled===true?'ON · ניסיוני':'OFF · ניסיוני'}</strong></span></label><p>דמיון אינו הוכחה למדגם משותף.</p></div>
   <div className="quick-scenario-controls__card" data-quick-control="arab-turnout"><h3 className="quick-scenario-controls__label" title="קבוצת היישובים הלא־יהודיים בבסיס 2022; לא כל הבוחרים הערבים, ובפרט לא כלל הערים המעורבות.">הצבעה ביישובים לא־יהודיים</h3><StepControl label="הצבעה ביישובים לא־יהודיים — שינוי מהיר" labelPlacement="hidden" min={0} max={100} step={.1} displayPrecision={1} formatValue={value=>Number(value).toLocaleString('he-IL',{minimumFractionDigits:1,maximumFractionDigits:1})+'%'} suffix="%" value={config.turnout?.arab_localities??0} onChange={value=>patch({turnout:{...config.turnout,arab_localities:value}})} disabled={disabled}/><p>קירוב גאוגרפי למגזר הערבי.</p></div>
   <div className="quick-scenario-controls__card quick-scenario-controls__card--coalition" data-quick-control="coalition-motivation"><h3 className="quick-scenario-controls__label">מוטיבציה לקואליציה</h3><StepControl label="מוטיבציה לקואליציה — שינוי מהיר" labelPlacement="hidden" min={.6} max={1.4} step={.01} displayScale={100} suffix="%" value={config.blocMultipliers?.a??1} onChange={value=>motive('a',value)} disabled={disabled}/><p>100% = ללא שינוי בהשתתפות.</p></div>
   <div className="quick-scenario-controls__card quick-scenario-controls__card--opposition" data-quick-control="opposition-motivation"><h3 className="quick-scenario-controls__label">מוטיבציה לאופוזיציה</h3><StepControl label="מוטיבציה לאופוזיציה — שינוי מהיר" labelPlacement="hidden" min={.6} max={1.4} step={.01} displayScale={100} suffix="%" value={config.blocMultipliers?.b??1} onChange={value=>motive('b',value)} disabled={disabled}/><p>105% = עלייה יחסית של 5%.</p></div>
  </div>
 </section>;
}
export default QuickScenarioControls;
