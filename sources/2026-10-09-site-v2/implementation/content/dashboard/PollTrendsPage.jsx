import React,{useMemo,useState} from 'react';
import {Button,DataComponent,EvidenceChart,useDataApp} from '../../data-app-public.jsx';
import {PartyName} from './PartyName.jsx';
import {VerifiedPartyTrends} from './VerifiedPartyTrends.jsx';
import {buildPollDeltaAnalysis,buildPollDeltaSummaryRows,buildPollTrendSeries} from './poll-trends.js';
import {dateLabel,numberLabel} from './transparency-data.js';
import './poll-trends.css';
import {isSignalNoiseEnabled,resolveForecastConfig} from './model/forecast.js';

const METHOD_LABELS={
 equal:'משקל שווה',
 quality:'דיוק היסטורי מכווץ',
 correlation:'תיקון קורלציה',
 reference:'מדד 120',
 littlepolls:'מואיז הקטן',
 rosner:'קירוב בהשראת שמואל רוזנר',
 gilead:'תרחיש מיכאל גלעד',
 ensemble:'שילוב השיטות שנבחרו',
 robust:'שקלול שמרני',
};
const DAY_MS=86_400_000;

function normalizedCoverage(value){
 if(Array.isArray(value))return value;
 if(value&&typeof value==='object')return Object.entries(value).map(([pollsterId,details])=>({pollsterId,...(details&&typeof details==='object'?details:{})}));
 return [];
}
function normalizeNotes(value){
 if(Array.isArray(value))return value.map(String).filter(Boolean);
 if(typeof value==='string'&&value.trim())return [value.trim()];
 if(value&&typeof value==='object')return Object.values(value).flatMap(normalizeNotes);
 return [];
}
function pollsterLabel(poll){
 const publisher=poll?.publisher??poll?.sourceName;
 const pollster=poll?.pollster??poll?.name;
 return [publisher,pollster].filter(Boolean).filter((value,index,array)=>array.indexOf(value)===index).join(' — ')||poll?.pollsterId||'מקור לא ידוע';
}
function signLabel(value){
 if(!Number.isFinite(value))return '—';
 const rounded=Math.abs(value)<.005?0:value;
 return `${rounded>0?'+':''}${numberLabel(rounded,2)}`;
}
function significanceLabel(value){
 if(!Number.isFinite(value))return 'לא ניתן לחשב';
 return value<=.05?'מובהק ברמת 5%':'לא מובהק ברמת 5%';
}
function currentMethodLabel(config={}){
 const mode=config.weightMode??'equal';
 const base=METHOD_LABELS[mode]??mode;
 if(!['robust','ensemble'].includes(mode))return base;
 const mix=config.methodWeights??config.ensembleMix??{};
 const methods=Object.entries(mix).filter(([,weight])=>Number(weight)>0).map(([id])=>METHOD_LABELS[id]??id);
 return methods.length?`${base}: ${methods.join(', ')}`:base;
}
function sourceBinding(queries={}){
 const ids=['poll_history','weight_presets','calibration','poll_correlation_profile'];
 const sourceRowsByQuery=Object.fromEntries(ids.map(id=>[id,queries[id]?.rows??[]]));
 return {queryId:'poll_history',queryIds:ids,sourceRows:sourceRowsByQuery.poll_history,sourceRowsByQuery};
}
function partyColor(party,index){
 if(typeof party?.color==='string'&&party.color.trim())return party.color;
 const hue=(index*67+212)%360;
 return `hsl(${hue} 58% 47%)`;
}

export function PollTrendsPage({input,config,weights,weightingControl}){
 const {queries}=useDataApp();
 const history=input?.history??{};
 const historicalPolls=Array.isArray(history.polls)?history.polls:[];
 const currentPolls=Array.isArray(input?.current?.polls)?input.current.polls:[];
 const parties=Array.isArray(input?.parties)?input.parties:[];
 const calibration=input?.calibration??{};
 const weightPresets=weights?.methods?weights:(weights?.weightPresets??input?.weightPresets);
 const trendConfig=useMemo(()=>resolveForecastConfig(config),[config]);
 const bind=sourceBinding(queries);
 const calculation=useMemo(()=>{
  try{
   if(!historicalPolls.length)return {series:null,error:'עדיין לא נקלטו סקרים היסטוריים.'};
   return {series:buildPollTrendSeries({historicalPolls,currentPolls,parties,config:trendConfig,calibration,weightPresets}),error:''};
  }catch(error){return {series:null,error:error instanceof Error?error.message:String(error)};}
 },[historicalPolls,currentPolls,parties,trendConfig,calibration,weightPresets]);
 const deltaCalculation=useMemo(()=>{
  try{
   if(!historicalPolls.length)return {delta:null,error:''};
   return {delta:buildPollDeltaAnalysis({historicalPolls,currentPolls,parties,config:trendConfig,calibration,weightPresets}),error:''};
  }catch(error){return {delta:null,error:error instanceof Error?error.message:String(error)};}
 },[historicalPolls,currentPolls,parties,trendConfig,calibration,weightPresets]);
 const series=calculation.series;
 const delta=deltaCalculation.delta;
 const calculated=series?.checkpoints.filter(point=>point.status==='ok')??[];
 const latest=calculated.at(-1);
 const ballotParties=parties.filter(party=>party.ballot!==false);
 const defaultTopSix=useMemo(()=>{
  if(!latest)return [];
  return latest.parties.filter(item=>Number.isFinite(item.seats)).sort((a,b)=>b.seats-a.seats||a.partyName.localeCompare(b.partyName,'he')).slice(0,6).map(item=>item.partyId);
 },[latest]);
 const [selection,setSelection]=useState(null);
 const selectedIds=selection??defaultTopSix;
 const selectedSet=new Set(selectedIds);
 const selectedParties=ballotParties.filter(party=>selectedSet.has(party.id));
 const colors=Object.fromEntries(selectedParties.map((party,index)=>[party.name,partyColor(party,index)]));
 const chartRows=calculated.map(point=>{
  const byId=new Map(point.parties.map(item=>[item.partyId,item]));
  return Object.assign({
   'תאריך':point.date,
   'מספר סקרים פעילים':point.pollCount,
   'כיסוי מכונים':`${point.pollCount}/${point.eligiblePollsterCount}`,
  },Object.fromEntries(selectedParties.map(party=>[party.name,byId.get(party.id)?.seats??null])));
 });
 const coverageRows=useMemo(()=>{
  if(!series)return [];
  const coverage=normalizedCoverage(history.coverage);
  const labelById=new Map();
  for(const row of coverage)if(row?.pollsterId)labelById.set(row.pollsterId,pollsterLabel(row));
  for(const poll of [...historicalPolls,...currentPolls])if(poll?.pollsterId&&!labelById.has(poll.pollsterId))labelById.set(poll.pollsterId,pollsterLabel(poll));
  return series.checkpoints.map(point=>{
   const ages=(point.pollWeights??[]).map(item=>(Date.parse(`${point.date}T00:00:00Z`)-Date.parse(`${item.date}T00:00:00Z`))/DAY_MS).filter(Number.isFinite);
   return {
    'תאריך':point.date,
    'סטטוס':point.status==='ok'?'מחושב':'אין די סקרים',
    'מספר סקרים':point.pollCount,
    'מספר מכונים שנבחרו':point.eligiblePollsterCount,
    'מכונים משתתפים':point.availablePollsterIds.map(id=>labelById.get(id)??id).join(', '),
    'גיל הסקר הישן ביותר (ימים)':ages.length?Math.max(...ages):null,
    'מכונים חסרים':point.missingPollsterIds.map(id=>labelById.get(id)??id).join(', '),
   };
  });
 },[series,history.coverage,historicalPolls,currentPolls]);
 const changeRows=useMemo(()=>selectedParties.map(party=>{
  const observed=calculated.map(point=>({date:point.date,value:point.parties.find(item=>item.partyId===party.id)?.seats})).filter(item=>Number.isFinite(item.value));
  const first=observed[0],last=observed.at(-1);
  return {
   party,
   firstDate:first?.date??null,
   firstValue:first?.value??null,
   latestDate:last?.date??null,
   latestValue:last?.value??null,
   change:first&&last?last.value-first.value:null,
  };
 }),[selectedParties,calculated]);
 const methodLabel=currentMethodLabel(trendConfig);
 const excludedCount=Array.isArray(config?.excludedPolls)?config.excludedPolls.length:0;
 const manualCount=Object.values(config?.pollWeights??{}).filter(value=>Number(value)!==1).length;
 const notes=normalizeNotes(history.notes);
 const firstDate=calculated[0]?.date;
 const latestDate=latest?.date;
 const displayRows=chartRows.flatMap(row=>selectedParties.map(party=>({תאריך:row['תאריך'],מפלגה:party.name,'מנדטים משוקללים':row[party.name],'מספר סקרים פעילים':row['מספר סקרים פעילים']})));
 const combinedDeltaRows=useMemo(()=>buildPollDeltaSummaryRows(delta,parties).map(row=>config.pollCorrelationEnabled===true?{...row,pValue:null,qValue:null}:row),[delta,parties,config.pollCorrelationEnabled]);
 const pollsterDeltaGroups=(delta?.pairs??[]).map(pair=>({pair,rows:selectedParties.map(party=>({party,...pair.parties.find(item=>item.partyId===party.id)})).filter(row=>Number.isFinite(row.rawDelta))})).filter(group=>group.rows.length);
 const deltaDisplayRows=combinedDeltaRows.map(row=>({מפלגה:row.party.name,'Δ משוקלל בין שני הסקרים האחרונים':row.modelRawDelta,'Δ משוקלל לשבוע':row.modelWeeklyDelta,'מספר מכונים':row.modelPollsterCount,'p לפני תיקון':row.pValue,'מובהקות לפני תיקון':significanceLabel(row.pValue),'q אחרי תיקון BH':row.qValue,'מובהקות אחרי תיקון':significanceLabel(row.qValue)}));
 const pollsterDeltaDisplayRows=pollsterDeltaGroups.flatMap(({pair,rows})=>rows.map(row=>({מכון:pollsterLabel(pair.latestPoll),'מתאריך':pair.previousDate,'עד תאריך':pair.latestDate,ימים:pair.days,מפלגה:row.party.name,'מנדטים קודמים':row.previous,'מנדטים אחרונים':row.latest,'שינוי גולמי':row.rawDelta,'שינוי לשבוע':row.weeklyDelta})));
 function toggleParty(id){setSelection(current=>{const active=current??defaultTopSix;return active.includes(id)?active.filter(item=>item!==id):[...active,id];});}

 return <section className="poll-trends-page" data-poll-trends-page>
  <VerifiedPartyTrends parties={parties} config={config} dataAsOf={input?.current?.asOf}/>
  <div className="pt-interactive-heading"><h2>חקירה לפי בחירת הסקרים שלכם</h2><p>כאן אפשר לשנות את השקלול ולבחון את שני הסקרים האחרונים בכל מכון ואת הגרפים ההיסטוריים. הניתוח השמור של כל התקופה מופיע למעלה.</p></div>
  {weightingControl&&<section className="e-page-settings" aria-label="הגדרת שקלול הסקרים למגמות">{weightingControl}</section>}

  {config.pollCorrelationEnabled===true&&<p className="e-caption" role="note"><strong>דמיון בין סקרים מופעל — שקלול תיאורי בדיעבד.</strong> הגרפים והדלתא המשוקללת משתמשים בפרופיל הדמיון שנאמד מכל התקופה המאומתת עד {dateLabel(input.calibration.pollCorrelation?.asOf??input.current.asOf)}; אלו אינם שחזורים של תחזיות שניתן היה להפיק בזמן אמת. מבחן החלפת הסימן של שני הסקרים האחרונים מניח עצמאות בין מכונים, ולכן ערכי p/q שלו אינם מוצגים כשהמתג מופעל. טבלת המובהקות המאומתת למעלה מוצגת בנפרד, ללא תיקון הדמיון.</p>}
  <div className="pt-intro" role="note">
   <div>
    <strong>מגמה תיאורית של תחזיות המנדטים שפורסמו</strong>
    <p>בכל תאריך נלקח הסקר האחרון של כל מכון שנבחר, כל עוד הוא בן 21 ימים לכל היותר. תחזיות המנדטים של המכונים הזמינים משוקללות לפי הגדרת הסקרים הפעילה שלכם.</p>
   </div>
   <dl>
    <div><dt>שיטת שקלול</dt><dd>{methodLabel}</dd></div>
    <div><dt>כיסוי אחרון</dt><dd>{latest?`${latest.pollCount} מתוך ${latest.eligiblePollsterCount} מכונים`:'—'}</dd></div>
    <div><dt>טווח מחושב</dt><dd>{firstDate&&latestDate?`${dateLabel(firstDate)}–${dateLabel(latestDate)}`:'—'}</dd></div>
   </dl>
   <p className="pt-definition"><strong>מה משתנה כאן?</strong> בחירת הסקרים, המשקל הידני ושיטת השקלול. הגדרות ההצבעה והרכב הגושים אינן משנות את הגרף, משום שהוא מתאר את פרסומי הסקרים ולא סימולציית בחירות. אין כאן הרצות, אחוז חסימה או חלוקת באדר–עופר.</p>
   {(excludedCount>0||manualCount>0)&&<p className="pt-adjustments">הגדרה פעילה: {excludedCount>0&&`${excludedCount} סקרים הוסרו`}{excludedCount>0&&manualCount>0?' · ':''}{manualCount>0&&`ל־${manualCount} מכונים הוגדר מכפיל ידני`}.</p>}
  </div>

  {calculation.error&&<div className="pt-error" role="alert"><strong>לא ניתן לחשב את המגמות.</strong><span>{calculation.error}</span></div>}
  {deltaCalculation.error&&<div className="pt-error" role="alert"><strong>לא ניתן לחשב את השינויים בתוך המכונים.</strong><span>{deltaCalculation.error}</span></div>}
  {series&&<>
   <section className="pt-delta-section pt-delta-overview" aria-labelledby="pt-delta-title">
    <div className="pt-delta-intro">
     <div><strong id="pt-delta-title">השינוי בין שני הסקרים האחרונים — לפי הבחירה שלכם</strong><p>לכל מפלגה מחושב שינוי בתוך כל מכון: תוצאת הסקר האחרון פחות התוצאה בסקר הקודם של אותו מכון, ורק בפרסומים מ־9.9. השינויים הגולמיים מאוחדים לפי משקלי השקלול שבחרתם. כאן הסינון הוא לפי תאריך פרסום; הוא אינו מאמת את חלון האיסוף ואינו הבדיקה של כל התקופה המוצגת למעלה.</p></div>
     <dl><div><dt>חתך הנתונים</dt><dd>פרסומים מ־9.9.2026</dd></div><div><dt>זוגות זמינים</dt><dd>{delta?(delta.pairs.length+' מתוך '+delta.selectedPollsterIds.length+' מכונים'):'—'}</dd></div></dl>
     <p className="pt-delta-caveat"><strong>איך נבדקת המובהקות?</strong> ערך p מתקבל ממבחן החלפת־סימן דו־צדדי מדויק על קצב השינוי השבועי: נבדקים כל הצירופים שבהם כיוון השינוי של כל מכון עשוי להתהפך באקראי. ערך q הוא אותו מבחן לאחר תיקון Benjamini–Hochberg לבדיקת כל המפלגות יחד. סף המובהקות הוא 0.05. ה־Δ הגולמי מוצג כמדד הראשי; הקצב השבועי משמש במבחן כדי להשוות בין מרווחי זמן שונים.</p>
    </div>

    <DataComponent id="poll-delta-combined" title="השינוי והמובהקות — כל המפלגות" variant="card" kind="table" {...bind} displayRows={deltaDisplayRows} description="הטבלה כוללת את כל הרשימות בקלפי ואינה מושפעת מבחירת המפלגות בגרף שמתחתיה.">
     {delta?.pairs.length?<><div className="pt-delta-weight-strip" aria-label="משקל כל מכון בדלתא המשולבת">{delta.pairs.map(pair=><span key={pair.pollsterId}><b>{pollsterLabel(pair.latestPoll)}</b><bdi>{numberLabel(100*pair.weight,1)}%</bdi></span>)}</div>
      <div className="pt-table-scroll" tabIndex={0} role="region" aria-label="טבלת שינוי ומובהקות לכל המפלגות"><table className="pt-table pt-delta-combined-table" data-reviewed-rows><thead><tr><th>מפלגה</th><th>Δ גולמי משוקלל</th><th>Δ לשבוע</th><th>מכונים</th><th>p לפני תיקון</th><th>q אחרי תיקון BH</th></tr></thead><tbody>{combinedDeltaRows.map(row=><tr key={row.party.id} data-significant={(Number.isFinite(row.qValue)&&row.qValue<=.05)||undefined}><th scope="row"><PartyName party={row.party} bloc={config?.partyBlocs?.[row.party.id]} showLogo={false}/></th><td className={row.modelRawDelta>0?'is-positive':row.modelRawDelta<0?'is-negative':''}><bdi>{signLabel(row.modelRawDelta)}</bdi></td><td className={row.modelWeeklyDelta>0?'is-positive':row.modelWeeklyDelta<0?'is-negative':''}><bdi>{signLabel(row.modelWeeklyDelta)}</bdi></td><td><bdi>{row.modelPollsterCount||'—'}</bdi></td><td data-significant={(Number.isFinite(row.pValue)&&row.pValue<=.05)||undefined}>{Number.isFinite(row.pValue)?<><bdi>{numberLabel(row.pValue,3)}</bdi><small>{significanceLabel(row.pValue)}</small></>:<span title={config.pollCorrelationEnabled?"לא מוצג במצב דמיון: המבחן מניח עצמאות בין מכונים":"נדרשים לפחות שני מכונים בעלי משקל חיובי"}>—</span>}</td><td data-significant={(Number.isFinite(row.qValue)&&row.qValue<=.05)||undefined}>{Number.isFinite(row.qValue)?<><bdi>{numberLabel(row.qValue,3)}</bdi><small>{significanceLabel(row.qValue)}</small></>:<span>—</span>}</td></tr>)}</tbody></table></div>
      <p className="pt-method-note">מספר זוגות קטן יוצר ערכי p בדידים ועוצמה סטטיסטית מוגבלת. מובהקות לפני תיקון היא אות ראשוני; המסקנה השמרנית נשענת על q אחרי התיקון לריבוי בדיקות.</p></>:<p className="pt-empty">עדיין אין לשני סקרים לפחות מאותו מכון מאז 9.9.2026.</p>}
    </DataComponent>
   </section>
   <div className="pt-party-controls" aria-labelledby="pt-party-controls-title">
    <div className="pt-control-heading"><div><strong id="pt-party-controls-title">מפלגות בגרף</strong><span>{selectedParties.length} נבחרו</span></div><div className="pt-presets"><Button onClick={()=>setSelection(defaultTopSix)}>6 הגדולות</Button><Button onClick={()=>setSelection(ballotParties.map(party=>party.id))}>כל הרשימות בקלפי</Button><Button onClick={()=>setSelection([])}>ניקוי</Button></div></div>
    <div className="pt-party-grid">{ballotParties.map((party,index)=><label key={party.id} className="pt-party-chip" data-selected={selectedSet.has(party.id)||undefined} style={{'--pt-party-color':partyColor(party,index)}}><input type="checkbox" checked={selectedSet.has(party.id)} onChange={()=>toggleParty(party.id)}/><span className="pt-color-dot" aria-hidden="true"/><PartyName party={party} bloc={config?.partyBlocs?.[party.id]} showLogo={false}/></label>)}</div>
   </div>

   {selectedParties.length?<EvidenceChart id="poll-trend-lines" title="מגמת המנדטים המשוקללת" variant="card" className="pt-trend-chart" {...bind} displayRows={displayRows} rows={chartRows} height={440}
    description="ממוצע משוקלל של תחזיות המנדטים שפורסמו. בכל נקודת זמן נלקח הסקר האחרון, בן 21 ימים לכל היותר, מכל מכון פעיל."
    spec={{type:'line',x:'תאריך',y:selectedParties[0].name,fields:selectedParties.map(party=>party.name),colors,valueDecimals:2,startAtZero:false,showLegend:true,yLabel:'מנדטים משוקללים',tooltipFields:['מספר סקרים פעילים','כיסוי מכונים'],missingValues:'gap'}}
    renderPlot={plot=><div className="pt-chart-plot" dir="ltr">{plot}</div>}>
    <p className="pt-chart-caption">כל נקודה מחושבת מתוך המכונים שהיו זמינים באותו יום; לכן יש לקרוא שינוי יחד עם טבלת הכיסוי. ערך חסר נשאר חסר ואינו הופך לאפס.</p>
   </EvidenceChart>:<DataComponent id="poll-trend-empty" title="מגמת המנדטים המשוקללת" variant="card" kind="custom" {...bind} displayRows={[]}><p className="pt-empty">בחרו מפלגה אחת לפחות כדי להציג את המגמה.</p></DataComponent>}

   <details className="e-disclosure pt-delta-section pt-delta-details" aria-label="פירוט השינוי בתוך כל מכון"><summary>פירוט השינויים בתוך כל מכון</summary>    <DataComponent id="poll-delta-by-pollster" title="הדלתא הנפרדת בתוך כל מכון" variant="card" kind="table" {...bind} displayRows={pollsterDeltaDisplayRows} description="הסקר האחרון מול הסקר הקודם מאותו מכון, ללא ערבוב בין מכונים.">
     <p className="pt-detail-intro">הטבלה מתעדכנת לפי המפלגות שבחרתם לגרף ומציגה את הנתונים שמהם חושב הסיכום שלמעלה.</p>
     {pollsterDeltaGroups.length?<div className="pt-table-scroll pt-delta-detail-scroll" tabIndex={0} role="region" aria-label="טבלת שינוי נפרד בכל מכון"><table className="pt-table pt-delta-detail-table" data-reviewed-rows><thead><tr><th>מכון והמרווח</th><th>מפלגה</th><th>קודם</th><th>אחרון</th><th>Δ גולמי</th><th>Δ לשבוע</th></tr></thead>{pollsterDeltaGroups.map(({pair,rows})=><tbody key={pair.pollsterId}><tr>{rows.length>0&&<th rowSpan={rows.length} scope="rowgroup"><strong>{pollsterLabel(pair.latestPoll)}</strong><small>{dateLabel(pair.previousDate)} ← {dateLabel(pair.latestDate)}</small><small>{pair.days} ימים · משקל {numberLabel(100*pair.weight,1)}%</small></th>}<th scope="row"><PartyName party={rows[0].party} bloc={config?.partyBlocs?.[rows[0].party.id]} showLogo={false}/></th><td>{rows[0].previous}</td><td>{rows[0].latest}</td><td className={rows[0].rawDelta>0?'is-positive':rows[0].rawDelta<0?'is-negative':''}><bdi>{signLabel(rows[0].rawDelta)}</bdi></td><td className={rows[0].weeklyDelta>0?'is-positive':rows[0].weeklyDelta<0?'is-negative':''}><bdi>{signLabel(rows[0].weeklyDelta)}</bdi></td></tr>{rows.slice(1).map(row=><tr key={row.party.id}><th scope="row"><PartyName party={row.party} bloc={config?.partyBlocs?.[row.party.id]} showLogo={false}/></th><td>{row.previous}</td><td>{row.latest}</td><td className={row.rawDelta>0?'is-positive':row.rawDelta<0?'is-negative':''}><bdi>{signLabel(row.rawDelta)}</bdi></td><td className={row.weeklyDelta>0?'is-positive':row.weeklyDelta<0?'is-negative':''}><bdi>{signLabel(row.weeklyDelta)}</bdi></td></tr>)}</tbody>)}</table></div>:<p className="pt-empty">בחרו מפלגות, או המתינו לצמד פרסומים מאותו מכון אחרי החתך.</p>}
    </DataComponent>
   </details>

   <details className="e-disclosure"><summary>טבלאות השינוי והכיסוי לאורך הזמן</summary><div className="pt-two-column">
    <DataComponent id="poll-trend-change" title="השינוי בטווח המוצג" variant="card" kind="table" {...bind} displayRows={changeRows.map(row=>({מפלגה:row.party.name,'תאריך ראשון':row.firstDate,'ערך ראשון':row.firstValue,'תאריך אחרון':row.latestDate,'ערך אחרון':row.latestValue,שינוי:row.change}))}>
     {changeRows.length?<div className="pt-table-scroll" tabIndex={0} role="region" aria-label="טבלת שינוי במנדטים"><table className="pt-table" data-reviewed-rows><thead><tr><th>מפלגה</th><th>תחילת הטווח</th><th>הערך האחרון</th><th>שינוי</th></tr></thead><tbody>{changeRows.map(row=><tr key={row.party.id}><th scope="row"><PartyName party={row.party} bloc={config?.partyBlocs?.[row.party.id]} showLogo={false}/></th><td>{Number.isFinite(row.firstValue)?<><bdi>{numberLabel(row.firstValue,2)}</bdi><small>{dateLabel(row.firstDate)}</small></>:'—'}</td><td>{Number.isFinite(row.latestValue)?<><bdi>{numberLabel(row.latestValue,2)}</bdi><small>{dateLabel(row.latestDate)}</small></>:'—'}</td><td className={row.change>0?'is-positive':row.change<0?'is-negative':''}><bdi>{signLabel(row.change)}</bdi></td></tr>)}</tbody></table></div>:<p className="pt-empty">בחרו מפלגות כדי לראות את השינוי.</p>}
    </DataComponent>

    <DataComponent id="poll-trend-coverage" title="כיסוי הסקרים בכל נקודת זמן" variant="card" kind="table" {...bind} displayRows={coverageRows} description="המכונים שנכנסו בפועל לכל חישוב. סקר שגילו מעל 21 ימים אינו נכלל.">
     <div className="pt-coverage-summary"><strong>{series.calculatedCheckpointCount}</strong><span>נקודות זמן מחושבות</span><strong>{series.selectedPollsterIds.length}</strong><span>מכונים שנבחרו בהגדרה הנוכחית</span></div>
     <div className="pt-table-scroll pt-coverage-scroll" tabIndex={0} role="region" aria-label="כיסוי מכונים לפי תאריך"><table className="pt-table pt-coverage-table" data-reviewed-rows><thead><tr><th>תאריך</th><th>כיסוי</th><th>המכונים בחישוב</th><th>הסקר הישן ביותר</th><th>חסר</th></tr></thead><tbody>{coverageRows.map(row=><tr key={row['תאריך']} data-status={row['סטטוס']==='מחושב'?'ok':'insufficient'}><th scope="row">{dateLabel(row['תאריך'])}</th><td><bdi>{row['מספר סקרים']}/{row['מספר מכונים שנבחרו']}</bdi><small>{row['סטטוס']}</small></td><td>{row['מכונים משתתפים']||'—'}</td><td>{row['גיל הסקר הישן ביותר (ימים)']==null?'—':`${row['גיל הסקר הישן ביותר (ימים)']} ימים`}</td><td>{row['מכונים חסרים']||'אין'}</td></tr>)}</tbody></table></div>
    </DataComponent>
   </div></details>

   {notes.length>0&&<details className="pt-notes"><summary>הערות על הכיסוי והסדרות ההיסטוריות</summary><ul>{notes.map((note,index)=><li key={index}>{note}</li>)}</ul></details>}
  </>}
 </section>;
}
