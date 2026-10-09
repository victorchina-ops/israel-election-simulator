import React from 'react';
import {DataComponent,Button,useDataApp} from '../../data-app-public.jsx';
import {StepControl} from './StepControl.jsx';
import {pollAllowedByChannelPolicy} from './model/poll-selection-policy.js';
import './poll-selection-control.css';

const SOURCE_IDS=['polls','model_configuration','weight_presets','calibration'];
const percent=(value,digits=2)=>Number.isFinite(value)?(100*value).toLocaleString('he-IL',{maximumFractionDigits:digits})+'%':'—';
function pollDate(value){
 const match=typeof value==='string'&&value.match(/^(\d{4})-(\d{2})-(\d{2})/);
 return match?match[3]+'.'+match[2]+'.'+match[1]:value||'תאריך לא נמסר';
}

export function PollSelectionControl({input,config,weights,onConfigChange}){
 const {queries}=useDataApp();
 const polls=Array.isArray(input?.current?.polls)?input.current.polls:[];
 const excludedIds=Array.isArray(config?.excludedPolls)?config.excludedPolls:[];
 const excluded=new Set(excludedIds),manualWeights=config?.pollWeights??{};
 const factorFor=poll=>manualWeights[poll.pollsterId]??1;
 const isIncluded=poll=>pollAllowedByChannelPolicy(poll,config)&&!excluded.has(poll.id)&&Number.isFinite(factorFor(poll))&&factorFor(poll)>0;
 const activeCount=polls.filter(isIncluded).length;
 const validVector=Array.isArray(weights?.polls)&&Array.isArray(weights?.weights)&&weights.polls.length===weights.weights.length&&weights.weights.length>0
  &&weights.weights.every(weight=>Number.isFinite(weight)&&weight>=0&&weight<=1)&&Math.abs(weights.weights.reduce((sum,weight)=>sum+weight,0)-1)<1e-8;
 const effectiveById=new Map(validVector?weights.polls.map((poll,i)=>[poll.id,weights.weights[i]]):[]);
 const rows=polls.map(poll=>{
  const included=isIncluded(poll),factor=factorFor(poll);
  const effectiveWeight=validVector?(included?(effectiveById.get(poll.id)??null):0):null;
  return {pollId:poll.id,pollsterId:poll.pollsterId,publisher:poll.publisher,pollster:poll.pollster,date:poll.date,
   included,channel14Excluded:!pollAllowedByChannelPolicy(poll,config),explicitlyExcluded:excluded.has(poll.id),manualMultiplier:Number.isFinite(factor)?factor:null,manualInfluencePercent:Number.isFinite(factor)?100*factor:null,
   finalNormalizedWeight:effectiveWeight,finalNormalizedPercent:effectiveWeight==null?null:100*effectiveWeight,
   weightMode:config?.weightMode,methodWeights:config?.methodWeights??null,
   influenceDefinition:'Multiplier on the selected weighting method before final normalization; not a vote share'};
 });
 const ids=SOURCE_IDS.filter(id=>queries?.[id]);
 const sourceRowsByQuery=Object.fromEntries(ids.map(id=>[id,queries[id].rows]));
 function toggle(poll,include){
  if(!onConfigChange||!pollAllowedByChannelPolicy(poll,config)||(!include&&isIncluded(poll)&&activeCount<=1))return;
  const next=new Set(excludedIds);
  if(include)next.delete(poll.id);else next.add(poll.id);
  const patch={excludedPolls:[...next]};
  if(include&&(!Number.isFinite(factorFor(poll))||factorFor(poll)<=0))patch.pollWeights={...manualWeights,[poll.pollsterId]:1};
  onConfigChange(patch);
 }
 function setFactor(poll,factor){
  if(!onConfigChange||!isIncluded(poll)||!Number.isFinite(factor)||factor<.05||factor>3)return;
  onConfigChange({pollWeights:{...manualWeights,[poll.pollsterId]:factor}});
 }
 const description='בחירת הסקרים הפעילים ומכפילי ההשפעה הידניים. הסקר נכלל כאשר מתג ערוץ 14 מאפשר אותו, הוא אינו ברשימת ההחרגות והמכפיל שלו חיובי. מכפיל 100% משמר את משקל הבסיס שהציעה שיטת השקלול; המשקל הסופי שמוצג חושב ונורמל במודל המשותף. הוצאת סקר שומרת את מכפילו לשימוש חוזר. איפוס הבחירה משנה רק excludedPolls ו-pollWeights, ומשמר את מתג ערוץ 14, שיטת השקלול ואת יתר הנחות המודל.';
 return <DataComponent id="e-poll-selection" title="בחירת סקרים והשפעת הסוקרים" kind="custom" variant="plain" className="poll-selection-control" queryId="polls" queryIds={ids} sourceRows={queries?.polls?.rows??[]} sourceRowsByQuery={sourceRowsByQuery} displayRows={rows} description={description}>
  <div className="poll-selection-toolbar" data-block-no-drag><Button disabled={!onConfigChange||!polls.length} onClick={()=>onConfigChange?.({excludedPolls:[],pollWeights:{}})}>איפוס הבחירה והמשקלים הידניים</Button><span data-reviewed-rows>{activeCount} מתוך {polls.length} סקרים נכללים במדד</span></div>
  <p className="poll-selection-caption">השפעה של 100% משאירה את משקל הבסיס של הסקר בשיטת השקלול שנבחרה. המשקל הסופי מנורמל בין הסקרים שנכללו; אלה אחוזי השפעה במדד, לא אחוזי הצבעה.</p>
  {polls.length>0&&activeCount===0&&<p className="poll-selection-empty" role="status">אין כרגע סקרים פעילים. סמנו סקר או אפסו את הבחירה והמשקלים הידניים כדי לחדש את החישוב.</p>}
  <div className="poll-selection-grid" data-reviewed-rows>{polls.map((poll,index)=>{
   const row=rows[index],factor=factorFor(poll),lastActive=row.included&&activeCount===1;
   const importedOff=!Number.isFinite(factor)||factor<=0;
   const outsideRange=Number.isFinite(factor)&&factor>0&&(factor<.05||factor>3);
   const reasonId='poll-selection-last-'+poll.id;
   return <section className={'poll-selection-card'+(row.included?' is-included':' is-excluded')} data-poll-id={poll.id} data-pollster-id={poll.pollsterId} key={poll.id}>
    <label className="poll-selection-check"><input type="checkbox" aria-label={'לכלול את '+poll.publisher} aria-describedby={row.channel14Excluded||lastActive?reasonId:undefined} checked={row.included} disabled={!onConfigChange||lastActive||row.channel14Excluded} onChange={event=>toggle(poll,event.target.checked)}/><strong>{poll.publisher}</strong></label>
    <p className="poll-selection-meta">{poll.pollster} · <time dateTime={poll.date}>{pollDate(poll.date)}</time></p>
    {row.channel14Excluded&&<p className="poll-selection-inactive" id={reasonId}>סקרי ערוץ 14 אינם נכללים. <a href="#scenario-channel14-switch">אפשר להפעיל את המתג למעלה</a>; הבחירה והמכפיל הידניים נשמרים.</p>}
    {importedOff?<p className="poll-selection-inactive">{factor===0?'השפעה של 0% משביתה את הסקר.':'מכפיל ההשפעה המיובא אינו תקין.'} סימון הסקר יחזיר את ההשפעה ל־100%.</p>:<>
     {outsideRange&&<p className="poll-selection-inactive">המכפיל המיובא הוא {percent(factor)}. הכוונון כאן מוגבל ל־5%–300%; שינוי הבקר יחליף את הערך המיובא.</p>}
     <StepControl label={'השפעת '+poll.publisher} min={.05} max={3} step={.05} value={factor} displayScale={100} suffix="%" formatValue={value=>percent(value,0)} disabled={!row.included||!onConfigChange} onChange={value=>setFactor(poll,value)}/>
    </>}
    <div className="poll-selection-final" data-effective-weight={row.finalNormalizedWeight??undefined}><span>משקל סופי במדד</span><strong>{percent(row.finalNormalizedWeight)}</strong></div>
    {lastActive&&<p className="poll-selection-last" id={reasonId}>זהו הסקר הפעיל האחרון; יש לכלול סקר נוסף לפני שמוציאים אותו.</p>}
   </section>;
  })}</div>
  {!polls.length&&<p className="poll-selection-empty" role="status">לא נמצאו סקרים במאגר הנוכחי.</p>}
 </DataComponent>;
}
export default PollSelectionControl;
