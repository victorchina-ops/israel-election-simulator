import React from 'react';
import {DataComponent,Button,useDataApp} from '../../data-app-public.jsx';
import {StepControl} from './StepControl.jsx';
import {signalNoiseInstituteSelection,signalNoiseBaseMethodLabel} from './signal-noise-content.js';
import './signal-noise.css';

export function SignalNoiseInstituteControl({input,config={},onConfigChange}){
 const {queries}=useDataApp(),rows=signalNoiseInstituteSelection(input,config);
 const selectedCount=rows.filter(row=>row.selected).length;
 const ids=['polls','signal_noise_observations','model_configuration','calibration'].filter(id=>queries?.[id]);
 function select(row,selected){
  if(!onConfigChange||row.channel14Excluded||(!selected&&row.selected&&selectedCount<=1))return;
  const excluded=new Set(config.excludedPolls??[]);
  if(selected)excluded.delete(row.pollId);else excluded.add(row.pollId);
  const patch={excludedPolls:[...excluded]};
  if(selected&&!(row.manualMultiplier>0))patch.pollWeights={...config.pollWeights,[row.pollsterId]:1};
  onConfigChange(patch);
 }
 return <DataComponent id="signal-noise-institute-selection" title="המכונים שנכללים בסדרת הזמן" kind="custom" variant="plain" className="sn-institutes" queryId="polls" queryIds={ids} sourceRows={queries?.polls?.rows??[]} sourceRowsByQuery={Object.fromEntries(ids.map(id=>[id,queries[id].rows]))} displayRows={rows} description="בחירת מכון כוללת את כל הסקרים שלו בחלון הזמן המאומת שאחרי סגירת הרשימות. מכפיל ידני משנה את רמת האמון במדידות שלו במהלך התאמת מודל האות והרעש; הוא אינו אחוז תמיכה או משקל סופי קבוע לכל המפלגות.">
  <div className="sn-toolbar"><Button disabled={!onConfigChange} onClick={()=>onConfigChange?.({excludedPolls:[],pollWeights:{}})}>איפוס הבחירה והמשקלים הידניים</Button><span data-reviewed-rows>{selectedCount} מתוך {rows.length} מכונים נבחרו</span></div>
  <p className="sn-caption">סימון מכון כולל את הסקרים שלו בחלון הניתוח שיש בהם אחוזים מקוריים ועבודת שדה מאומתת. הבסיס הוא ״{signalNoiseBaseMethodLabel(config)}״; מכפיל 100% משמר אותו. ההשפעה בפועל תלויה גם במפלגה ובמיקום המדידה בסדרת הזמן. מכון ללא דוח אחוזים מתאים אינו נכנס לאמידה.</p>
  <div className="sn-institute-grid" data-reviewed-rows>{rows.map(row=><section className={'sn-institute'+(row.selected?'':' is-excluded')} key={row.pollId} data-pollster-id={row.pollsterId}>
   <label><input type="checkbox" aria-label={'לכלול את כל סקרי '+row.publisher} checked={row.selected} disabled={!onConfigChange||row.channel14Excluded||(row.selected&&selectedCount===1)} onChange={event=>select(row,event.target.checked)}/><strong>{row.publisher}</strong></label>
   <p className="sn-caption">{row.pollster}</p>
   {row.channel14Excluded&&<p className="sn-caption">סקרי ערוץ 14 אינם נכנסים לסדרת הזמן. <a href="#scenario-channel14-switch">אפשר להפעיל את המתג למעלה</a>; הבחירה והמכפיל הידניים נשמרים.</p>}
   <p className="sn-caption" data-institute-coverage={row.availableObservationCount??undefined}>{row.availableObservationCount===0?'אין סקרי אחוזים מאומתים למכון זה במאגר':row.availableObservationCount!=null?row.availableObservationCount+' סקרי אחוזים מאומתים במאגר':'כיסוי המקורות יוצג לאחר טעינת הנתונים'}</p>
   {row.manualMultiplier>0?<StepControl label={'רמת אמון ידנית: '+row.publisher} min={.05} max={3} step={.05} value={row.manualMultiplier} displayScale={100} suffix="%" disabled={!onConfigChange||!row.selected} onChange={value=>onConfigChange?.({pollWeights:{...config.pollWeights,[row.pollsterId]:value}})}/>:<p className="sn-caption">סימון המכון יחזיר את רמת האמון ל־100%.</p>}
   {row.selected&&selectedCount===1&&<p className="sn-caption">זהו המכון האחרון שנבחר; כללו מכון נוסף לפני הסרתו.</p>}
  </section>)}</div>
 </DataComponent>;
}
