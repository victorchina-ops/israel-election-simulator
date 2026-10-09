import React,{useEffect,useRef,useState} from 'react';
import {DataComponent,Button,useDataApp} from '../../data-app-public.jsx';
import './take-home-message.css';
import {OutcomeWaffle} from './BlocOutcomes.jsx';
import {PartyName,PARTY_COLORS,PARTY_LOGOS} from './PartyName.jsx';
import {MeanSeats} from './MeanSeats.jsx';
import {downloadSummaryFigure} from './summary-figure-export.js';
import {WEIGHTING_LABELS} from './WeightingControl.jsx';
import {describeBlocComposition} from './bloc-presets.js';
import {PARTY_ASSIGNMENT_MIME,createPartyAssignmentDragData,parsePartyAssignmentDragData,partyAssignmentRequest,groupResultParties} from './result-party-assignment.js';
import './result-party-assignment.css';

// TAKE_HOME_PURE_START
const TAKE_HOME_OUTCOMES=[
 {id:'a',label:'רוב לקואליציה הנוכחית'},
 {id:'b',label:'רוב לאופוזיציה'},
 {id:'neither',label:'היעדר רוב לשני הגושים'},
];
const takeHomeNumber=(value,digits=0)=>Number(value).toLocaleString('he-IL',{maximumFractionDigits:digits});
function takeHomeCondition(result){
 if(result.config?.samplingMode==='fixed')return 'בהנחה שהתמיכה בסקרים נכונה';
 if(result.signalNoise)return 'לפי מודל האות והרעש והנחותיו';
 if(result.config?.samplingMode==='poll')return 'לפי הנחות הטעות בסקרים';
 return 'לפי הנחות הסימולציה שנבחרו';
}
function takeHomeSeats(result){
 if(result.iterations===1){
  const world=result.worlds?.[0]?.blocs;
  if(world&&[world.a,world.b].every(Number.isFinite)&&world.a>=0&&world.b>=0&&world.a+world.b<=120)return {a:world.a,b:world.b};
 }
 if(!Array.isArray(result.parties)||!result.parties.length||result.parties.some(p=>!Number.isFinite(p.mean)||p.mean<0))return null;
 const seats={a:0,b:0};
 for(const party of result.parties){const bloc=party.bloc??party.defaultBloc;if(bloc==='a'||bloc==='b')seats[bloc]+=party.mean;}
 return seats.a+seats.b<=120+1e-8?seats:null;
}
function takeHomeStats(result){
 if(!result||!Number.isSafeInteger(result.iterations)||result.iterations<1)return null;
 const iterations=result.iterations,seats=takeHomeSeats(result);
 if(iterations===1)return seats?{iterations,seats,probabilities:null,counts:null}:null;
 const ids=TAKE_HOME_OUTCOMES.map(outcome=>outcome.id);
 const hasCounts=result.counts&&ids.some(id=>result.counts[id]!==undefined);
 const counts=hasCounts?ids.map(id=>result.counts[id]):null;
 if(counts&&(counts.some(count=>!Number.isSafeInteger(count)||count<0)||counts.reduce((a,b)=>a+b,0)!==iterations))return null;
 const supplied=ids.map(id=>result.probabilities?.[id]);
 const validProbabilities=supplied.every(p=>Number.isFinite(p)&&p>=0&&p<=1)&&Math.abs(supplied.reduce((a,b)=>a+b,0)-1)<1e-9;
 if(!counts&&!validProbabilities)return null;
 const probabilities=counts?counts.map(count=>count/iterations):supplied;
 if(counts&&result.probabilities&&(!validProbabilities||supplied.some((p,i)=>Math.abs(p-probabilities[i])>1e-9)))return null;
 return {iterations,seats,probabilities,counts};
}
export function generateTakeHome(result){
 const stats=takeHomeStats(result);if(!stats)return '';
 const condition=takeHomeCondition(result),{iterations,seats}=stats;
 if(iterations===1)return 'בהדמיה היחידה בתרחיש הזה התקבלו '+takeHomeNumber(seats.a,0)+' מנדטים לקואליציה הנוכחית ו־'+takeHomeNumber(seats.b,0)+' לאופוזיציה. החישוב נעשה '+condition+'; הדמיה אחת אינה אומדן לסיכוי.';
 const highest=Math.max(...stats.probabilities);
 const winners=TAKE_HOME_OUTCOMES.filter((outcome,i)=>Math.abs(stats.probabilities[i]-highest)<1e-12);
 const digits=Math.max(2,Math.min(6,Math.ceil(Math.log10(iterations))-2));
 const frequency=takeHomeNumber(100*highest,digits)+'%',runs=takeHomeNumber(iterations);
 let first;
 if(winners.length===1)first='בתרחיש הזה, '+winners[0].label+' היה המצב השכיח: '+frequency+' מ־'+runs+' ההרצות.';
 else if(winners.length===3)first='בתרחיש הזה לא הייתה תוצאה שכיחה יחידה: שלוש התוצאות הופיעו באותה שכיחות, '+frequency+' כל אחת מ־'+runs+' ההרצות.';
 else first='בתרחיש הזה, '+winners.map(outcome=>outcome.label).join(' ו־')+' הופיעו באותה שכיחות: '+frequency+' כל אחד מ־'+runs+' ההרצות.';
 const second='החישוב נעשה '+condition+(seats?'; בתוחלת התקבלו '+takeHomeNumber(seats.a,2)+' מנדטים לקואליציה ו־'+takeHomeNumber(seats.b,2)+' לאופוזיציה.':'.');
 return first+' '+second;
}
function stableTakeHomeValue(value){
 if(Array.isArray(value))return value.map(stableTakeHomeValue);
 if(value&&typeof value==='object')return Object.fromEntries(Object.keys(value).sort().filter(key=>value[key]!==undefined).map(key=>[key,stableTakeHomeValue(value[key])]));
 return value;
}
export function takeHomeScenarioKey(result){
 if(!result||!Number.isSafeInteger(result.iterations)||result.iterations<1)return '';
 // Exact canonical evidence, rather than a lossy hash. Excludes run timestamps.
 const evidence={config:result.config??{},iterations:result.iterations,counts:result.counts??null,probabilities:result.probabilities??null,
  probabilityCI:result.probabilityCI??null,seats:takeHomeSeats(result),
  parties:(result.parties??[]).map(p=>({id:p.id,bloc:p.bloc??p.defaultBloc,mean:p.mean,meanVotes:p.meanVotes,passProbability:p.passProbability})).sort((a,b)=>String(a.id).localeCompare(String(b.id))),
  polls:(result.pollWeights??[]).map(p=>({id:p.id,pollsterId:p.pollsterId,date:p.date,weight:p.weight})).sort((a,b)=>String(a.id).localeCompare(String(b.id)))};
 return 'take-home-v1:'+JSON.stringify(stableTakeHomeValue(evidence));
}
export function resolveTakeHomeMessage(result,value){
 const automaticText=generateTakeHome(result),scenarioKey=takeHomeScenarioKey(result);
 const custom=value?.mode==='custom'&&typeof value.text==='string'&&value.text.trim().length>0;
 return {mode:custom?'custom':'auto',text:custom?value.text:automaticText,automaticText,scenarioKey,
  savedScenarioKey:custom?value.scenarioKey??'':'',stale:Boolean(custom&&scenarioKey&&value.scenarioKey!==scenarioKey)};
}
// TAKE_HOME_PURE_END

const SOURCE_IDS=['polls','turnout_baseline','model_configuration','weight_presets','calibration','poll_correlation_profile','agreements'];
function downloadText(text,filename){
 const url=URL.createObjectURL(new Blob(['\uFEFF'+text],{type:'text/plain;charset=utf-8'})),link=document.createElement('a');
 link.href=url;link.download=filename;link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
}
function messageRows(result,resolved,ready){
 const rows=[];
 if(ready){
  const stats=takeHomeStats(result);
  const common={iterations:result.iterations,samplingMode:result.config?.samplingMode,seed:result.config?.seed,asOf:result.config?.asOf,weightMode:result.config?.weightMode,signalNoiseEnabled:Boolean(result.signalNoise),includeChannel14:result.config?.includeChannel14!==false,pollCorrelationEnabled:result.config?.pollCorrelationEnabled===true};
  rows.push({...common,kind:'calculated-summary',text:resolved.automaticText,scenarioKey:resolved.scenarioKey});
  if(stats?.probabilities)TAKE_HOME_OUTCOMES.forEach((outcome,i)=>rows.push({...common,kind:'model-outcome',outcome:outcome.id,label:outcome.label,count:stats.counts?.[i]??null,probability:stats.probabilities[i],ciLow:result.probabilityCI?.[outcome.id]?.[0]??null,ciHigh:result.probabilityCI?.[outcome.id]?.[1]??null,intervalMeaning:'Wilson Monte Carlo sampling error conditional on the model'}));
  if(stats?.seats)for(const bloc of ['a','b'])rows.push({...common,kind:result.iterations===1?'single-election-seats':'mean-seats',bloc,seats:stats.seats[bloc],meanMargin:result.blocStats?.[bloc]?.meanMargin,meanCI:result.blocStats?.[bloc]?.meanCI,intervalMeaning:'95% Monte Carlo confidence interval for the mean'});
  for(const party of result.parties??[])rows.push({...common,kind:'mean-seats',partyId:party.id,bloc:party.bloc??party.defaultBloc,seats:party.hasModelledSupport===false?null:party.mean,meanMargin:party.meanMargin,meanCI:party.meanCI,intervalMeaning:'95% Monte Carlo confidence interval for the mean'});
 }
 if(resolved.mode==='custom')rows.push({kind:'user-authored-message',text:resolved.text,computed:false,savedScenarioKey:resolved.savedScenarioKey,currentScenarioKey:ready?resolved.scenarioKey:null,scenarioChanged:ready?resolved.stale:null});
 return rows;
}

export function TakeHomeMessage({result,input,config,busy=false,error,value,onChange,onReset,onAssignParty,controls,compact=false}){
 const {queries}=useDataApp();
 const [compactExpanded,setCompactExpanded]=useState(false);
 const [exporting,setExporting]=useState(false),[exportError,setExportError]=useState('');
 const [editing,setEditing]=useState(false),[draft,setDraft]=useState(''),[draftScenarioKey,setDraftScenarioKey]=useState(''),[feedback,setFeedback]=useState('');
 const [draggedParty,setDraggedParty]=useState(null),[dropTarget,setDropTarget]=useState(null),[assignmentNotice,setAssignmentNotice]=useState('');
 const assignmentBoard=useRef(null),pendingAssignmentFocus=useRef(null);
 const resolved=resolveTakeHomeMessage(result,value);
 const ready=Boolean(!busy&&!error&&resolved.automaticText),custom=resolved.mode==='custom';
 const stats=takeHomeStats(result);
 const mostLikely=ready&&stats?.probabilities?TAKE_HOME_OUTCOMES.filter((v,i)=>Math.abs(stats.probabilities[i]-Math.max(...stats.probabilities))<1e-12):[];
 const concise=mostLikely.length?(mostLikely.length===1?'המצב השכיח: ':'מצבים שכיחים באותה מידה: ')+mostLikely.map(v=>v.label).join(' / ')+' ('+takeHomeNumber(100*Math.max(...stats.probabilities),1)+'%). '+takeHomeCondition(result)+'.':resolved.automaticText;
 const activeText=custom?resolved.text:ready?concise:'';
 const parties=input?.parties?.filter(p=>p.ballot!==false)??[];
 const groups=groupResultParties(parties,config?.partyBlocs);
 const canAssignParties=typeof onAssignParty==='function';
 const assignmentLabels={a:'קואליציה',b:'אופוזיציה',other:'ללא שיוך'};
 useEffect(()=>{
  const partyId=pendingAssignmentFocus.current;if(!partyId||!assignmentBoard.current)return;
  const field=[...assignmentBoard.current.querySelectorAll('[data-party-assignment-select]')].find(element=>element.getAttribute('data-party-assignment-select')===partyId);
  if(field){field.focus();pendingAssignmentFocus.current=null;}
 },[config?.partyBlocs]);
 function assignParty(partyId,bloc){
  const request=partyAssignmentRequest(parties,partyId,bloc);
  if(!canAssignParties||!request)return;
  const oldBloc=config?.partyBlocs?.[partyId]??parties.find(p=>p.id===partyId)?.defaultBloc;
  if(oldBloc===bloc)return;
  pendingAssignmentFocus.current=partyId;
  onAssignParty(request.partyId,request.bloc);
  setAssignmentNotice((parties.find(p=>p.id===partyId)?.name??partyId)+' הועברה לקבוצה ״'+assignmentLabels[bloc]+'״. השיוך הישן הוסר והתוצאות מתעדכנות.');
 }
 function startPartyDrag(event,partyId){
  if(event.target.closest('select')){event.preventDefault();return;}
  event.dataTransfer.effectAllowed='move';
  event.dataTransfer.setData(PARTY_ASSIGNMENT_MIME,createPartyAssignmentDragData(partyId));
  setDraggedParty(partyId);
 }
 function finishPartyDrag(){setDraggedParty(null);setDropTarget(null);}
 function acceptPartyDrop(event,bloc){
  event.preventDefault();
  const partyId=parsePartyAssignmentDragData(event.dataTransfer.getData(PARTY_ASSIGNMENT_MIME),parties);
  if(!partyId)return;
  assignParty(partyId,bloc);finishPartyDrag();
 }
 function assignmentCard(p,group){
  const party=result?.parties?.find(row=>row.id===p.id);
  const mean=ready&&party?.hasModelledSupport!==false&&Number.isFinite(party?.mean)?party.mean:null;
  return <div key={p.id} className="thm-assignment-card" data-summary-party={p.id} data-party-assignment data-party-id={p.id} data-assigned-bloc={group} data-dragging={draggedParty===p.id?'true':'false'} draggable onDragStart={event=>startPartyDrag(event,p.id)} onDragEnd={finishPartyDrag}>
   <PartyName party={p} bloc={group}/>
   <span className="thm-party-seats" data-party-mean={mean??undefined} aria-label={p.name+' — '+(mean==null?'אין ממוצע זמין':takeHomeNumber(mean,1)+' מנדטים בממוצע')}><bdi dir="ltr">{mean==null?'—':takeHomeNumber(mean,1)}</bdi><small>מנדטים</small></span>
   <label className="thm-assignment-field"><span><span className="thm-assignment-field-name">{p.name}</span><span className="thm-assignment-field-label">שיוך לגוש</span></span><select data-party-assignment-select={p.id} value={group} aria-label={'שיוך '+p.name+' לגוש'} onChange={event=>assignParty(p.id,event.target.value)}><option value="a">קואליציה</option><option value="b">אופוזיציה</option><option value="other">ללא שיוך</option></select></label>
  </div>;
 }
 function partyAssignmentBoard(){return <div className="thm-direct-assignments" data-block-no-drag>
  <div className="thm-assignment-intro"><h3>המפלגות בתרחיש שלכם</h3><p><span className="thm-assignment-desktop-hint">בחרו גוש מתחת לכל מפלגה, או גררו אותה לגוש הרצוי.</span><span className="thm-assignment-mobile-hint">בחרו גוש מתחת לכל מפלגה כדי להעביר אותה.</span></p></div>
  <div ref={assignmentBoard} className="thm-assignment-board" data-direct-party-board>
   {['a','other','b'].map(group=><section key={group} className="thm-assignment-group" data-party-drop-zone={group} data-drop-active={dropTarget===group?'true':'false'} style={{'--thm-bloc-color':PARTY_COLORS[group]}} aria-label={'מפלגות '+assignmentLabels[group]} onDragOver={event=>{if(draggedParty){event.preventDefault();event.dataTransfer.dropEffect='move';setDropTarget(group);}}} onDragLeave={event=>{if(!event.currentTarget.contains(event.relatedTarget))setDropTarget(null);}} onDrop={event=>acceptPartyDrop(event,group)}>
    <h4>{assignmentLabels[group]}<small>{groups[group].length} מפלגות</small></h4>
    <p className="thm-assignment-group-note">{group==='a'?'מימין · הגוש האדום':group==='b'?'משמאל · הגוש הכחול':'ערביות ומפלגות ללא שיוך'}</p>
    <div className="thm-assignment-list">{groups[group].length?groups[group].map(p=>assignmentCard(p,group)):<p className="thm-assignment-empty">אפשר להעביר לכאן כל מפלגה.</p>}</div>
   </section>)}
  </div>
  <p className="thm-assignment-status" role="status" aria-live="polite">{assignmentNotice}</p>
  <p className="thm-assignment-accounting">כל מפלגה נמצאת בקבוצה אחת בלבד. בכל הדמיה יש בסך הכול 120 מנדטים; הממוצעים שמוצגים כאן מעוגלים. שינוי גוש משנה גם את המוטיבציה שחלה על אותה מפלגה.</p>
 </div>;}
 const likud=result?.parties?.find(p=>p.id==='likud');
 function logos(group){return <div className={'thm-logos thm-logos--'+group} data-summary-bloc={group}>{groups[group].map(p=>{
  const party=result?.parties?.find(row=>row.id===p.id);
  const mean=ready&&party?.hasModelledSupport!==false&&Number.isFinite(party?.mean)?party.mean:null;
  const label=mean==null?'התוחלת אינה זמינה':takeHomeNumber(mean,2)+' מנדטים בתוחלת';
  const interval=mean!=null&&result.iterations>1&&party?.meanCI?.every(Number.isFinite)?'; רווח סמך 95% לתוחלת מההרצות: '+party.meanCI.map(v=>takeHomeNumber(v,2)).join(' עד '):'';
  return <span className="thm-party-chip" key={p.id} data-summary-party={p.id} style={{color:PARTY_COLORS[group]}}>
   <PartyName party={p} bloc={group} compact/>
   <span className="thm-party-seats" data-party-mean={mean??undefined} title={p.name+' — '+label+interval} aria-label={p.name+' — '+label}><bdi dir="ltr">{mean==null?'—':takeHomeNumber(mean,1)}</bdi></span>
  </span>;
 })}</div>;}
 const chance=id=>ready&&result.iterations>1?takeHomeNumber(result.probabilities[id]*100,1)+'%':'—';
 function blocMetric(group){return <div className={'thm-bloc thm-bloc--'+group} style={{color:PARTY_COLORS[group]}}><strong className="thm-bloc-name">{group==='a'?'קואליציה':'אופוזיציה'}</strong><div className="thm-chance" data-summary-probability={group}>{chance(group)}</div><span className="thm-chance-label">סיכוי לרוב של 61</span><div className="thm-mean">{ready?<bdi dir="ltr" data-summary-mean={group}>{takeHomeNumber(result.blocStats?.[group]?.mean,1)}</bdi>:<span>—</span>}</div><span className="thm-seat-label">{result?.iterations===1?'מנדטים בהדמיה':'מנדטים בממוצע'}</span>{ready&&result.iterations>1&&Number.isInteger(result.blocStats?.[group]?.median)&&<span className="thm-distribution" data-summary-median={group}>טווח ב־90% מההדמיות: <bdi dir="ltr">{result.blocStats[group].low}–{result.blocStats[group].high}</bdi></span>}{!canAssignParties&&logos(group)}{group==='a'&&!canAssignParties&&<div className="thm-likud"><span>הליכוד: </span>{ready?<MeanSeats stats={likud} iterations={result.iterations} statId="likud"/>:'—'}</div>}</div>;}
 const inputQuery='polls';
 const ids=[...new Set([inputQuery,...SOURCE_IDS])].filter(id=>queries?.[id]);
 const sourceRowsByQuery=Object.fromEntries(ids.map(id=>[id,queries[id].rows]));
 const currentScenario=result?.config??config??{};
 const description='המסר האוטומטי מסכם את התוצאה השכיחה בסימולציה ואת תוחלת המנדטים. רווחי הסמך במקור הם שגיאת הרצה מותנית בהנחות. מסר אישי הוא טקסט שהמשתמש כתב, לא תוצאת חישוב; הוא נשמר בנפרד ומסומן אם התרחיש השתנה. הנתונים המחושבים אינם ניתנים לעריכה באמצעות עורך המסר. תרחיש: '+JSON.stringify(currentScenario);
 function startEditing(){
  setDraft(activeText);setDraftScenarioKey(ready?resolved.scenarioKey:resolved.savedScenarioKey);setFeedback('');setEditing(true);
 }
 function save(){
  if(!ready||!draft.trim()||!onChange)return;
  // Bind to the evidence that was present when editing began. A mid-edit
  // scenario change must not silently relabel older prose as a current finding.
  onChange({mode:'custom',text:draft,scenarioKey:draftScenarioKey});setEditing(false);setFeedback('המסר נשמר.');
 }
 function reset(){onChange?.({mode:'auto',text:'',scenarioKey:''});setEditing(false);setFeedback('המסר האוטומטי הוחזר.');}
 async function copy(){
  if(!activeText||busy||error)return;
  try{if(!navigator.clipboard?.writeText)throw new Error('unavailable');await navigator.clipboard.writeText(activeText);setFeedback('המסר הועתק.');}
  catch{setFeedback('ההעתקה אינה זמינה כאן. אפשר לסמן את הטקסט או להוריד אותו כקובץ.');}
 }
 const changedDuringEdit=editing&&ready&&draftScenarioKey!==resolved.scenarioKey;
 async function exportImage(){
  if(!ready||result.iterations<2||exporting)return;
  setExporting(true);setExportError('');
  try{
   await downloadSummaryFigure({result,input,summaryText:custom&&resolved.stale?resolved.automaticText:activeText,logoSources:PARTY_LOGOS,weightingLabel:(WEIGHTING_LABELS[result.config.weightMode]||result.config.weightMode),oppositionLabel:describeBlocComposition(result.config,input.parties)});
  }catch(error){setExportError('לא ניתן להוריד את התמונה: '+error.message);}
  finally{setExporting(false);}
 }
 const exportButton=<Button className="thm-export-button" disabled={!ready||result?.iterations<2||exporting} onClick={exportImage} title={result?.iterations<2?'נדרשות לפחות שתי הרצות כדי להציג סיכויים בתמונה':undefined}>{exporting?'מכין תמונה…':'הורדת תמונת סיכום PNG'}</Button>;
 const exportNotice=exportError?<p className="thm-error" role="alert">{exportError}</p>:null;
 if(compact&&!compactExpanded)return <div className="thm-pin thm-pin--reference">{controls}<DataComponent id="e-take-home-message" title="המסר המרכזי" kind="custom" variant="card" className="take-home-message" queryId={inputQuery} queryIds={ids} sourceRows={queries?.[inputQuery]?.rows??[]} sourceRowsByQuery={sourceRowsByQuery} displayRows={messageRows(result,resolved,ready)} description={description}>
  <div className="thm-reference-outcomes" data-reviewed-rows>{[['a','קואליציה'],['neither','ללא רוב'],['b','אופוזיציה']].map(([id,label])=><div key={id} style={{color:PARTY_COLORS[id]||'var(--secondary)'}}><span>{label}</span><strong data-summary-probability={id}>{chance(id)}</strong></div>)}</div>
  <div className="thm-reference-actions">{exportButton}<Button onClick={()=>setCompactExpanded(true)}>תרשים הקוביות והמסר</Button><Button onClick={()=>onReset?.()}>איפוס פרמטרים</Button></div>
  {exportNotice}
  <p className="thm-reference-note">{busy?'מחשב את התרחיש…':error?'החישוב אינו זמין: '+error:result?.iterations===1?'הרצה אחת אינה אומדן סיכוי':'סיכויי רוב של 61 לפי השקלול הראשי שנבחר; מותנים בהנחות המודל.'}</p>
 </DataComponent></div>;
 return <div className="thm-pin">{controls}<DataComponent id="e-take-home-message" title="סיכויי רוב של 61 מנדטים" kind="custom" variant="card" className="take-home-message" queryId={inputQuery} queryIds={ids} sourceRows={queries?.[inputQuery]?.rows??[]} sourceRowsByQuery={sourceRowsByQuery} displayRows={messageRows(result,resolved,ready)} description={description}>
  {exportNotice}
  <div className="thm-body" data-reviewed-rows>
   {custom&&<div className="thm-toolbar"><span className="thm-label">המסר שלך</span>{compact&&<Button onClick={()=>setCompactExpanded(false)}>צמצום הסיכום</Button>}</div>}
   {activeText&&<p className="thm-message">{activeText}</p>}
   {busy&&<p className="thm-status" role="status">מחשב את התרחיש הנוכחי…</p>}
   {error&&<p className="thm-error" role="alert">הסיכום המחושב אינו זמין: {error}</p>}
   {!busy&&!error&&!ready&&<p className="thm-status" role="status">המסר האוטומטי יוצג לאחר שתתקבל תוצאת סימולציה תקינה.</p>}
   {custom&&ready&&resolved.stale&&<p className="thm-stale" role="status">התרחיש השתנה מאז עריכת המסר.</p>}
   {custom&&<details className="thm-calculated"><summary>הסיכום המחושב לתרחיש הנוכחי</summary><p>{ready?resolved.automaticText:'הסיכום יתעדכן כשהחישוב יושלם.'}</p></details>}
  </div>
  <div className="thm-live" data-reviewed-rows aria-busy={busy}>
   {blocMetric('a')}
   <div className="thm-visual"><div className="thm-neither"><span>תיקו / ללא רוב</span><strong data-summary-probability="neither">{chance('neither')}</strong></div>{ready&&result.iterations>1?<OutcomeWaffle result={result} compact showLegend={false} showNote={false}/>:<p className="thm-waffle-placeholder">{busy?'מעדכן את התוצאות…':result?.iterations===1?'הרצה אחת אינה אומדן סיכוי':'ממתין לתוצאה'}</p>}{!canAssignParties&&<div className="thm-neutral"><span>ללא שיוך לגושים</span>{logos('other')}</div>}</div>
   {blocMetric('b')}
  </div>
  <p className="thm-ci-note">כל קובייה ≈ 1% מההדמיות. סיכוי לרוב אינו סיכוי להרכיב ממשלה.</p>
  {canAssignParties&&partyAssignmentBoard()}
  <details className="thm-uncertainty"><summary>מה אומר הטווח, וכמה בטוחה התחזית?</summary><p>הטווח מציג את אחוזוני 5–95 של המנדטים בהדמיות, לפי ההנחות שבחרתם. הוא אינו הבטחה לתוצאת הבחירות. ההסתברויות תלויות בדגימה, בשקלול ובתרחיש; הן לא כוילו במלואן מול בחירות קודמות.</p><p>בפירוט ובייצוא מופיע גם ± רווח סמך 95% לתוחלת: זו שגיאת ההרצה של הממוצע בלבד, ולא אי־הוודאות לגבי הבחירות.</p></details>
  <div className="thm-reference-actions thm-share-actions">{exportButton}<Button onClick={()=>{onReset?.();setFeedback('הפרמטרים אופסו לברירת המחדל.');}}>איפוס פרמטרים</Button></div>
  <details className="thm-tools"><summary>עריכה, העתקה ופרטים</summary>
  {editing?<div className="thm-editor" data-block-no-drag>
   <label htmlFor="take-home-message-draft">נוסח המסר שלך</label>
   <textarea id="take-home-message-draft" value={draft} onChange={event=>setDraft(event.target.value)} rows={4} dir="rtl"/>
   <p className="thm-editor-note">העריכה משנה את המסר בלבד; נתוני הסימולציה נשארים כפי שחושבו.</p>
   {changedDuringEdit&&<p className="thm-stale" role="status">התרחיש השתנה בזמן העריכה. המסר יישמר עם התרחיש שאליו התייחס כשפתחת את העורך.</p>}
   <div className="thm-actions"><Button disabled={!ready||!draft.trim()||!onChange} onClick={save}>שמירת המסר</Button><Button onClick={()=>{setEditing(false);setFeedback('');}}>ביטול</Button></div>
  </div>:<div className="thm-actions" data-block-no-drag>
   <Button disabled={(!ready&&!custom)||!onChange} onClick={startEditing}>עריכת המסר</Button>
   {custom&&<Button disabled={!onChange} onClick={reset}>חזרה למסר האוטומטי</Button>}
   <Button disabled={!activeText||busy||!!error} onClick={copy}>העתקת המסר</Button>
   <Button disabled={!activeText||busy||!!error} onClick={()=>{downloadText(activeText,'take-home-message-'+(result?.config?.asOf??input?.current?.asOf??'scenario')+'-'+resolved.mode+'.txt');setFeedback('המסר הורד.');}}>הורדת המסר TXT</Button>
  </div>}
  {feedback&&<p className="thm-feedback" role="status" aria-live="polite">{feedback}</p>}
 </details>
 </DataComponent></div>;
}
export default TakeHomeMessage;
