import React from 'react';
import {DataComponent,Dropdown,Switch,Button,useDataApp} from '../../data-app-public.jsx';
import {StepControl} from './StepControl.jsx';
import {PollSelectionControl} from './PollSelectionControl.jsx';
import {SignalNoiseInstituteControl} from './SignalNoiseInstituteControl.jsx';
import {SignalNoiseDiagnostics} from './SignalNoiseDiagnostics.jsx';
import {channel14Included,pollAllowedByChannelPolicy} from './model/poll-selection-policy.js';
import './weighting-control.css';

export const WEIGHTING_LABELS={robust:'שילוב שמרני',ensemble:'שילוב שיטות',equal:'משקל שווה',reference:'מדד 120',littlepolls:'מואיז הקטן',gilead:'גלעד — תרחיש 50%',rosner:'רוזנר — קירוב',quality:'דיוק היסטורי',correlation:'תלות — מכפיל ותיקים ישן'};
export const WEIGHTING_CHOICES=Object.keys(WEIGHTING_LABELS).filter(id=>id!=='correlation');
const BLEND_DEFAULTS={equal:1,reference:1,littlepolls:1,gilead:1,rosner:0};
const BLEND_IDS=Object.keys(BLEND_DEFAULTS);
const BLEND_LABELS={equal:'משקל שווה לסקרים',reference:'מדד 120 — משקלי הבסיס',littlepolls:'מואיז הקטן — ציוני הסוקרים',gilead:'מיכאל גלעד — תרחיש 50%',rosner:'בהשראת המדד של רוזנר — קירוב שלנו',quality:WEIGHTING_LABELS.quality,correlation:WEIGHTING_LABELS.correlation};
const SOURCE_IDS=['polls','model_configuration','weight_presets','calibration','poll_correlation_profile','signal_noise_observations'];
const number=(value,digits=1)=>Number(value).toLocaleString('he-IL',{maximumFractionDigits:digits});
const percent=value=>number(100*value,0)+'%';
function approachDescription(mode,config,weights){
 const target=config.gileadTarget==='next_data'?'NEXT DATA':'דיירקט פולס';
 if(mode==='gilead'&&Array.isArray(weights?.polls)&&!weights.polls.some(poll=>poll.pollsterId===(config.gileadTarget??'direct_polls')))return 'מכון היעד '+target+' אינו נכלל בבחירה הנוכחית, ולכן יעד ה־50% אינו מיושם. המשקלים מנורמלים בין הסקרים שנשארו פעילים.';
 if(mode==='gilead'&&config.signalNoiseEnabled===true&&weights?.signalNoise?.weightingPolicy?.unavailableInstitutes?.includes(config.gileadTarget??'direct_polls'))return 'בתרחיש שבחרתם יעד ה־50% הוא '+target+', אבל אין כרגע דוח אחוזים מתאים ממנו. הוא אינו נכנס לאמידת האות והרעש, ורמת האמון מנורמלת מחדש בין המכונים עם נתונים.';
 const descriptions={
  robust:'חציון משוקלל של השיטות שנבחרו, עם '+percent(config.robustShrinkage??.25)+' בסיס שווה. זהו כלל שמרני שלנו, שטרם הוכחה עדיפותו.',
  ensemble:'ממוצע משוקלל של השיטות שנבחרו, על אותם סקרים. בהרחבה אפשר לבחור את השיטות ואת השפעתן.',
  equal:'משקל בסיס שווה לכל סקר פעיל, לפני התאמות הזמן והמכפילים הידניים שבחרת.',
  reference:'משקלי הבסיס שפורסמו במדד 120, על הסקרים שבמאגר שלנו. אין כאן שחזור של כל התאמות האתר.',
  littlepolls:'ציוני הסוקרים שפרסם מואיז הקטן, על הסקרים שבמאגר שלנו. חלון הזמן והצבירה של האתר אינם משוחזרים במלואם.',
  gilead:'תרחיש של 50% ל'+target+' לפני מכפילי הסוקרים הידניים. שיוך ההישגים ההיסטוריים למכון הנוכחי הוא הנחת תרחיש.',
  rosner:'קירוב שלנו בהשראת המדד: טריות, גודל מדגם והפחתת חריגות. זו אינה נוסחת שקלול עדכנית שפורסמה בידי המדד.',
  quality:'משקלי המכונים לפי הדיוק ההיסטורי בבחירות 2019–2022, עם כיווץ שממתן הבדלים. זו ברירת המחדל; אפשר לבחור גישה אחרת או לשנות משקלים ידנית.',
  correlation:'תרחיש ישן שנשמר בקובץ שייבאתם: הפחתה משותפת של משקל הסוקרים הוותיקים לפי מכפיל קבוע. זו הנחה גלויה, ללא אמידת תלות, ונפרדת ממתג ״דמיון בין סקרים״ למעלה.',
 };
 return descriptions[mode]||'בחרו גישת שקלול כדי לקבוע את משקלי הבסיס של הסקרים.';
}

export function WeightingControl({input,config={},weights,onConfigChange}){
 const {queries}=useDataApp();
 const mode=config.weightMode??'ensemble',blend=['ensemble','robust'].includes(mode),signalNoise=config.signalNoiseEnabled===true;
 const methodWeights=config.methodWeights??BLEND_DEFAULTS;
 // Preserve explicitly imported advanced mixture members and make them visible.
 const blendIds=[...BLEND_IDS,...['quality','correlation'].filter(id=>(methodWeights[id]??0)>0)];
 const activeMethods=Object.entries(methodWeights).filter(([,weight])=>weight>0);
 const uses=id=>mode===id||(blend&&(methodWeights[id]??0)>0);
 const usesTime=['equal','quality','correlation'].some(uses);
 const activePollCount=(input?.current?.polls??[]).filter(poll=>pollAllowedByChannelPolicy(poll,config)&&!config.excludedPolls?.includes(poll.id)&&(config.pollWeights?.[poll.pollsterId]??1)>0).length;
 const ids=SOURCE_IDS.filter(id=>queries?.[id]);
 const sourceRowsByQuery=Object.fromEntries(ids.map(id=>[id,queries[id].rows]));
 const displayRows=[{kind:'selected-weighting-approach',mode,label:WEIGHTING_LABELS[mode]??mode,activePollCount,description:approachDescription(mode,config,weights)},
  ...Object.entries(config).filter(([key])=>['weightMode','signalNoiseEnabled','includeChannel14','pollCorrelationEnabled','methodWeights','robustShrinkage','gileadTarget','rosnerHalfLifeDays','rosnerOutlierCutoffPP','applyRecency','halfLifeDays','veteranClusterDiscount','excludedPolls','pollWeights'].includes(key)).map(([parameter,value])=>({kind:'weighting-configuration',parameter,value:typeof value==='object'?JSON.stringify(value):value})),
  ...blendIds.map(id=>({kind:'mixture-member',method:id,label:BLEND_LABELS[id],relativeWeight:methodWeights[id]??0,selected:(methodWeights[id]??0)>0}))];
 const patch=value=>onConfigChange?.(value);
 const setMethodWeight=(id,value)=>patch({methodWeights:{...methodWeights,[id]:value}});
 function chooseMode(weightMode){
  // Changing approach leaves turnout, selection and saved method parameters intact.
  patch(weightMode==='robust'&&config.robustShrinkage===undefined?{weightMode,robustShrinkage:.25}:{weightMode});
 }
 return <DataComponent id="e-weighting-control" title="שקלול הסקרים" kind="custom" variant="card" className="weighting-control" queryId="polls" queryIds={ids} sourceRows={queries?.polls?.rows??[]} sourceRowsByQuery={sourceRowsByQuery} displayRows={displayRows} description="בקר שקלול משותף ללשוניות. הרחבת האזור מאפשרת לבחור מכונים וסקרים ולכוון השפעה ידנית. כשמתג האות והרעש מופעל, השיטה שנבחרה קובעת את רמת האמון במדידות בתוך התאמת סדרת הזמן המאומתת. משקלים אינם מוסיפים ראיות עצמאיות. שינוי הגישה משמר את יתר הגדרות התרחיש.">
  <div className="weighting-control__primary" data-reviewed-rows>
   <Dropdown triggerClassName="filter-trigger e-content-select" contentClassName="election-select-menu" label="גישת השקלול" showLabel value={mode} choices={mode==='correlation'?[...WEIGHTING_CHOICES,'correlation']:WEIGHTING_CHOICES} choiceLabels={WEIGHTING_LABELS} onChange={chooseMode} disabled={!onConfigChange}/>
   <p className="weighting-control__description">{approachDescription(mode,config,weights)}</p>
  </div>
  {config.pollCorrelationEnabled===true&&<p className="weighting-control__caption" data-reviewed-rows>דמיון בין סקרים מופעל במתג הנפרד למעלה. שיטת השקלול והדיוק ההיסטורי נשמרים; התיקון חל פעם אחת על המשקלים, ומתאים גם את אי־הוודאות לפי סדרת הסקרים הנוכחית. זו בדיקת רגישות ניסיונית: תוצאות דומות יכולות לנבוע משינוי אמיתי בתמיכה. לזוגות סוקרים עם מידע חסר לא מניחים קורלציה אפסית.</p>}
  {signalNoise&&<div className="sn-method-choice" data-reviewed-rows>
   <p className="weighting-control__caption">אות ורעש מופעל במתג הנפרד למעלה. ״{WEIGHTING_LABELS[mode]??mode}״ קובעת את רמת האמון במדידות בתוך התאמת המודל, פעם אחת; השפעת המדידה משתנה לאורך הזמן ובין מפלגות.</p>
   <SignalNoiseDiagnostics id="signal-noise-active-explanation" input={input} config={config} result={{signalNoise:weights?.signalNoise}} compact/>
  </div>}
  <details className="weighting-control__details" id="poll-selection-settings">
   <summary>{signalNoise?'מכונים וסדרת הזמן':'סקרים ומשקלים'} <span>{activePollCount} מתוך {input?.current?.polls?.length??0} {signalNoise?'מכונים':'סקרים'} · פתיחה לבחירה ולכוונון</span></summary>
   {signalNoise?<SignalNoiseInstituteControl input={input} config={config} onConfigChange={onConfigChange}/>:<PollSelectionControl input={input} config={config} weights={weights} onConfigChange={onConfigChange}/>}
   {blend&&<section className="weighting-control__tuning" aria-label="תמהיל השיטות" data-reviewed-rows>
    <h3>השיטות שמשתתפות בשילוב</h3>
    <p className="weighting-control__caption">סימון ומשקל חיובי כוללים את השיטה; אפס מוציא אותה. השיטות מציעות משקלים לאותו מאגר סקרים, ומספר התצפיות אינו גדל.</p>
    <div className="weighting-control__actions"><Button onClick={()=>patch({methodWeights:{...methodWeights,...Object.fromEntries(blendIds.map(id=>[id,1]))}})}>בחירת כל השיטות</Button><Button onClick={()=>patch({methodWeights:{...BLEND_DEFAULTS}})}>ברירת המחדל של התמהיל</Button></div>
    <div className="weighting-control__mixture">{blendIds.map(id=><div className="weighting-control__method" data-method-id={id} key={id}>
     <label><input type="checkbox" checked={(methodWeights[id]??0)>0} disabled={!onConfigChange} onChange={event=>setMethodWeight(id,event.target.checked?1:0)}/><span>{BLEND_LABELS[id]}</span></label>
     <StepControl label={'משקל בשילוב: '+BLEND_LABELS[id]} labelPlacement="hidden" min={0} max={3} step={.1} value={methodWeights[id]??0} formatValue={value=>number(value,1)} onChange={value=>setMethodWeight(id,value)} disabled={!onConfigChange}/>
    </div>)}</div>
    {!activeMethods.length&&<p className="weighting-control__empty" role="status">בחרו לפחות שיטה אחת או החזירו את ברירת המחדל של התמהיל כדי לחשב את המדד.</p>}
   </section>}
   {mode==='robust'&&<section className="weighting-control__tuning" data-reviewed-rows><h3>מידת ההישענות על בסיס שווה</h3><StepControl label="משקל בסיס שווה בשילוב העמיד" displayScale={100} suffix="%" min={0} max={1} step={.05} value={config.robustShrinkage??.25} onChange={value=>patch({robustShrinkage:value})}/><p className="weighting-control__caption">מנרמלים את חציון הצעות השיטות ומשלבים בסיס שווה לסקרים. ברירת 25% היא פרמטר שלנו, שטרם כויל לדיוק; מכפילי הסוקרים מופעלים לאחר מכן.</p></section>}
   {uses('gilead')&&<section className="weighting-control__tuning" data-reviewed-rows><h3>תרחיש גלעד</h3><Dropdown triggerClassName="filter-trigger e-content-select" contentClassName="election-select-menu" label="למי משייכים את תרחיש ה־50%?" showLabel value={config.gileadTarget??'direct_polls'} choices={['direct_polls','next_data']} choiceLabels={{direct_polls:'דיירקט פולס הנוכחי',next_data:'NEXT DATA הנוכחי'}} onChange={value=>patch({gileadTarget:value})}/><p className="weighting-control__caption">{config.gileadTarget==='next_data'&&!channel14Included(config)?'NEXT DATA של ערוץ 14 אינו נכלל כשהמתג למעלה כבוי, ולכן יעד ה־50% אינו מיושם עבורו. ':'50% לפני מכפילי הסוקרים הידניים. '}זו הנחת תרחיש, ללא העברה אוטומטית של הדיוק ההיסטורי לאחר שינויי הארגון.</p></section>}
   {uses('rosner')&&<section className="weighting-control__tuning" data-reviewed-rows><h3>הקירוב לרוזנר — פרמטרים שלנו</h3><div className="weighting-control__parameter-grid"><StepControl label="קירוב המדד — מחצית חיים בימים" min={1} max={60} step={1} value={config.rosnerHalfLifeDays??config.halfLifeDays??14} onChange={value=>patch({rosnerHalfLifeDays:value})}/><StepControl label="קירוב המדד — סף חריגות בנק׳ אחוז" min={.2} max={5} step={.1} value={config.rosnerOutlierCutoffPP??2} onChange={value=>patch({rosnerOutlierCutoffPP:value})}/></div><p className="weighting-control__caption">דעיכת זמן, שורש גודל המדגם והפחתת חריגות. הפרמטרים ניתנים לשינוי ואינם נוסחת המדד.</p></section>}
   {usesTime&&<section className="weighting-control__tuning" data-reviewed-rows><h3>עדכניות הסקרים</h3><Switch label="להוסיף דעיכת זמן" checked={config.applyRecency!==false} onChange={value=>patch({applyRecency:value})}/><StepControl label="מחצית חיים — לשיטות עם דעיכת זמן" disabled={config.applyRecency===false} min={1} max={60} step={1} value={config.halfLifeDays??14} onChange={value=>patch({halfLifeDays:value})}/><p className="weighting-control__caption">ההתאמה חלה על גישת המשקל השווה ועל גישות הדיוק והתלות המתקדמות, גם כשהן כלולות בתמהיל. לקירוב רוזנר פרמטר זמן נפרד.</p></section>}
   {uses('correlation')&&<section className="weighting-control__tuning" data-reviewed-rows><h3>בדיקת רגישות לתלות</h3><StepControl label="מכפיל אשכול ותיקים — הנחה" min={.1} max={1} step={.05} value={config.veteranClusterDiscount??.5} onChange={value=>patch({veteranClusterDiscount:value})}/><p className="weighting-control__caption">הפחתה משותפת לסוקרים הוותיקים; דיירקט ו־NEXT DATA מחוץ לאשכול. זו אינה אמידת מטריצת תלות עדכנית.</p></section>}
   {(input?.weightPresets?.methods?.[mode]?.notes?.length>0)&&<details className="weighting-control__notes"><summary>הערות ומקורות של הגישה</summary>{input.weightPresets.methods[mode].notes.map((note,i)=><p className="weighting-control__caption" key={i}>{note}</p>)}</details>}
  </details>
 </DataComponent>;
}
export default WeightingControl;
