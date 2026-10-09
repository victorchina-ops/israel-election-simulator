import React,{useEffect,useMemo,useState} from "react";
import {DataComponent,EvidenceChart,SectionHeader,Dropdown,Button,useDataApp} from "../../data-app-public.jsx";
import {MeanSeats} from "./MeanSeats.jsx";
import {PartyName} from "./PartyName.jsx";
import {createSimulation} from "./model/simulate.js";
import {SignalNoiseDiagnostics} from "./SignalNoiseDiagnostics.jsx";
import "./weight-comparison.css";

const METHODS=[
 {id:"equal",title:"משקל שווה לסקרים",note:"כל סקר פעיל מקבל משקל בסיס שווה. מכפילים ידניים ודעיכת זמן, אם הופעלה, נשמרים לפי ההגדרות המשותפות."},
 {id:"reference",title:"מדד 120 — משקלי הבסיס",note:"שמונת משקלי הבסיס שפורסמו. השוואה זו אינה משחזרת את כל השכבות של מדד 120."},
 {id:"littlepolls",title:"מואיז הקטן — ציוני הסוקרים",note:"ציוני הסוקרים המפורסמים מוחלים על מאגר הסקרים המקומי. אין כאן שכפול של כל הפרויקט."},
 {id:"gilead",title:"מיכאל גלעד — תרחיש 50%",note:"תרחיש רגישות של 50% למכון שנבחר, לפני מכפילי הסקרים הידניים."},
 {id:"rosner",title:"בהשראת המדד של רוזנר — קירוב שלנו",note:"קירוב מקומי עם פרמטרים גלויים. נוסחת השקלול העדכנית ומשקלי הסוקרים של המדד אינם ידועים במלואם."}
];
const BLEND_DEFAULTS={equal:1,reference:1,littlepolls:1,gilead:1,rosner:0};
const ENSEMBLE={id:"ensemble",title:"השילוב שנבחר",note:"ממוצע משוקלל של משקלי הסקרים שהציעו השיטות שנבחרו. כל סקר נספר פעם אחת; מספר התצפיות אינו גדל."};
const ROBUST={id:"robust",title:"שילוב עמיד ושמרני",note:"חציון משוקלל של הצעות השיטות לכל סקר, נרמול וחיבור לבסיס שווה. זו שיטה שלנו שטרם הוכחה כמדויקת יותר."};
const BLOCS={a:{name:"הקואליציה הנוכחית",color:"#dc454c"},b:{name:"האופוזיציה",color:"#2378cf"},arab:{name:"המפלגות הערביות",color:"#87909d"},other:{name:"ללא שיוך לגוש",color:"#87909d"}};
const OUTCOMES=[{id:"a",label:"רוב לקואליציה",color:"#dc454c"},{id:"b",label:"רוב לאופוזיציה",color:"#2378cf"},{id:"neither",label:"לשניהם אין רוב",color:"#89939f"}];
const SOURCE_IDS=["polls","turnout_baseline","model_configuration","weight_presets","calibration","poll_correlation_profile","agreements","signal_noise_observations"];
const num=(value,d=1)=>value==null||!Number.isFinite(Number(value))?"—":Number(value).toLocaleString("he-IL",{minimumFractionDigits:d,maximumFractionDigits:d});
const pct=(value,d=1)=>value==null?"—":num(100*value,d)+"%";
const yieldFrame=()=>new Promise(resolve=>setTimeout(resolve,0));
const blocOf=party=>party.bloc||party.defaultBloc||"other";
const blocMean=(result,bloc)=>result.parties.reduce((sum,p)=>sum+(blocOf(p)===bloc?p.mean:0),0);

function displayRows(method,result,bloc){
 if(!result)return [];
 const repeated=result.iterations>1,common={שיטה:method.title,"קוד שיטה":method.id,"הרצות":result.iterations,"מצב דגימה":result.config.samplingMode,"זרע":result.config.seed,"תאריך נתונים":result.config.asOf,"משקלי שילוב":["ensemble","robust"].includes(method.id)?JSON.stringify(result.config.methodWeights):null,"בסיס שווה בשילוב העמיד":method.id==="robust"?(result.config.robustShrinkage??.25):null,"סקרי ערוץ 14 כלולים":result.config.includeChannel14!==false,"דמיון בין סקרים מופעל":result.config.pollCorrelationEnabled===true,"אות ורעש מופעל":!!result.signalNoise,"סקרים בסדרת הזמן":result.signalNoise?.coverage?.observationCount??null,"מכונים בסדרת הזמן":result.signalNoise?.coverage?.instituteCount??null,"תחילת חלון אות ורעש":result.signalNoise?.coverage?.from??null,"סיום חלון אות ורעש":result.signalNoise?.coverage?.to??null};
 const probabilities=repeated?OUTCOMES.map(outcome=>({...common,"סוג נתון":"הסתברות רוב",מדד:outcome.label,מפלגה:null,גוש:outcome.id,ערך:100*result.probabilities[outcome.id],יחידה:"%","גבול תחתון 95%":100*result.probabilityCI[outcome.id][0],"גבול עליון 95%":100*result.probabilityCI[outcome.id][1]})):[];
 const sums=["a","b"].map(group=>({...common,"סוג נתון":repeated?"תוחלת גוש":"מנדטים בהדמיה",מדד:BLOCS[group].name,מפלגה:null,גוש:group,ערך:blocMean(result,group),יחידה:"מנדטים","גבול תחתון 95%":result.blocStats?.[group]?.meanCI?.[0]??null,"גבול עליון 95%":result.blocStats?.[group]?.meanCI?.[1]??null}));
 const composition=result.parties.filter(p=>p.ballot!==false&&blocOf(p)===bloc).sort((a,b)=>b.mean-a.mean).map(p=>({...common,"סוג נתון":repeated?"תוחלת מפלגה":"מנדטים בהדמיה",מדד:"הרכב "+BLOCS[bloc].name,מפלגה:p.name,גוש:bloc,ערך:p.mean,יחידה:"מנדטים","גבול תחתון 95%":p.meanCI?.[0]??null,"גבול עליון 95%":p.meanCI?.[1]??null}));
 return [...probabilities,...sums,...composition];
}
function downloadComparison(rows,filename){
 const columns=["שיטה","קוד שיטה","סוג נתון","מדד","מפלגה","גוש","ערך","יחידה","גבול תחתון 95%","גבול עליון 95%","הרצות","מצב דגימה","זרע","תאריך נתונים","משקלי שילוב","בסיס שווה בשילוב העמיד","סקרי ערוץ 14 כלולים","דמיון בין סקרים מופעל","אות ורעש מופעל","סקרים בסדרת הזמן","מכונים בסדרת הזמן","תחילת חלון אות ורעש","סיום חלון אות ורעש"];
 const quote=value=>'"'+String(value??"").replaceAll('"','""')+'"';
 const text="\uFEFF"+[columns.map(quote).join(","),...rows.map(row=>columns.map(key=>quote(row[key])).join(","))].join("\r\n");
 const url=URL.createObjectURL(new Blob([text],{type:"text/csv;charset=utf-8"})),link=document.createElement("a");
 link.href=url;link.download=filename;link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
}

function methodNote(method,result){
 if(result?.signalNoise&&method.id==='gilead'&&result.signalNoise.weightingPolicy?.unavailableInstitutes?.includes(result.config.gileadTarget??'direct_polls'))return 'אין כרגע דוח אחוזים מתאים ממכון היעד שנבחר בתרחיש גלעד. לכן יעד ה־50% אינו מיושם באמידת האות והרעש, ורמת האמון מנורמלת מחדש בין המכונים עם נתונים מתאימים.';
 if(result?.signalNoise)return method.note+' כשאות ורעש מופעל, המשקלים משמשים כרמת אמון במכונים בתוך התאמת סדרת הזמן, פעם אחת. זו התאמה שלנו ולא תחזית רשמית של פרויקט המקור.';
 if(method.id==="robust"&&result)return "לכל סקר מחשבים חציון משוקלל של הצעות השיטות שנבחרו, לפי משקלי השיטות; מנרמלים ומשלבים "+pct(result.config.robustShrinkage??.25,0)+" בסיס שווה. מכפילי הסקרים הידניים מופעלים בסוף. הבחירה בבסיס שווה היא פרמטר שלנו, ולא תוצאה של כיול לדיוק בבחירות.";
 if(method.id!=="gilead"||!result)return method.note;
 const target=result.config.gileadTarget??"direct_polls";
 const names={direct_polls:"דיירקט פולס הנוכחי",next_data:"NEXT DATA הנוכחי"};
 const polls=result.pollWeights.filter(p=>p.pollsterId===target);
 const name=names[target]||polls[0]?.pollster||target;
 const effective=polls.reduce((sum,p)=>sum+p.weight,0);
 return "50% ל"+name+" כמשקל מוצע לפני מכפילי הסקרים הידניים. "+(polls.length?"המשקל האפקטיבי בהרצה הוא "+pct(effective)+".":"המכון אינו בין הסקרים הפעילים, ולכן תרחיש ה־50% אינו מוחל עליו.")+" זהו תרחיש רגישות, ולא העברה מוכחת של הדיוק ההיסטורי.";
}

function MethodDetails({method,result,bloc,onApply,input,diagnosticsId}){
 const repeated=result?.iterations>1;
 const parties=result?.parties.filter(p=>p.ballot!==false&&blocOf(p)===bloc).sort((a,b)=>b.mean-a.mean)||[];
 return <div className="wc-method-details" data-reviewed-rows>
  {result&&<>
   {repeated?<div className="wc-outcomes">{OUTCOMES.map(outcome=><div key={outcome.id} style={{"--wc-outcome":outcome.color}}>
    <span>{outcome.label}</span><strong>{pct(result.probabilities[outcome.id])}</strong>
    <small>95%: <bdi>{pct(result.probabilityCI[outcome.id][0],2)}–{pct(result.probabilityCI[outcome.id][1],2)}</bdi></small>
   </div>)}</div>:<p className="wc-single">זו הדמיה אחת. מוצגים מנדטים בפועל; נדרשות חזרות כדי לאמוד סיכויים ורווחי סמך.</p>}
   <dl className="wc-bloc-totals">{["a","b"].map(group=><div key={group} style={{"--wc-outcome":BLOCS[group].color}}><dt>{repeated?"תוחלת ":"מנדטי "}{BLOCS[group].name}</dt><dd><MeanSeats stats={result.blocStats?.[group]} iterations={result.iterations}/></dd></div>)}</dl>
   <div className="wc-composition-heading" style={{borderColor:BLOCS[bloc].color}}><h3>הרכב {BLOCS[bloc].name}</h3><span><MeanSeats stats={result.blocStats?.[bloc]} iterations={result.iterations}/> מנדטים {repeated?"בתוחלת":"בהדמיה"}</span></div>
   {parties.length?<div className="wc-composition-scroll" role="region" aria-label={"הרכב "+BLOCS[bloc].name+" — טבלה נגללת"} tabIndex={0}><table className="wc-composition" data-reviewed-rows><thead><tr><th>מפלגה</th><th>{repeated?"תוחלת מנדטים ± 95%":"מנדטים"}</th></tr></thead><tbody>{parties.map(p=><tr key={p.id}><th scope="row"><PartyName party={p} bloc={blocOf(p)}/></th><td><MeanSeats stats={p} iterations={result.iterations}/></td></tr>)}</tbody></table></div>:<p className="wc-method-note">אין רשימות המשויכות לגוש הזה בתרחיש הנוכחי.</p>}
   <p className="wc-caption">{num(result.iterations,0)} הדמיות · {result.signalNoise?(result.config.samplingMode==='poll'?'אות ורעש מופעל — כולל אי־ודאות של האומדן':'לפי אומדן התמיכה של מודל האות והרעש'):(result.config.samplingMode==="poll"?"כולל אפשרות לטעות בסקרים":"אם הסקרים מדויקים")}. רוב פירושו לפחות 61 מנדטים. ± ליד התוחלת הוא רווח סמך 95% לממוצע. רווחי 95% מודדים שגיאת הרצה בלבד; אין כאן אומדן למשא ומתן בין מפלגות.</p>
   {result.signalNoise&&<SignalNoiseDiagnostics id={diagnosticsId} input={input} config={result.config} result={result} compact/>}
   <details className="wc-method-about"><summary>על שיטת השקלול והנחותיה</summary><p className="wc-method-note">{methodNote(method,result)}</p></details>
   {onApply&&<div className="wc-apply-separate"><Button onClick={()=>onApply(method.id)}>להחיל שיטה זו במדד הראשי</Button></div>}
  </>}
 </div>;
}

function ResultCard({id,title,method,result,bloc,busy,error,progress,bind,onApply,input}){
 const ready=!busy&&!error?result:null;
 const repeated=ready?.iterations>1;
 const rows=displayRows(method,ready,bloc);
 const details=<MethodDetails method={method} result={ready} bloc={bloc} onApply={onApply} input={input} diagnosticsId={id+'-signal-noise-diagnostics'}/>;
 const chartRows=repeated?[{תרחיש:"סיכויי רוב","רוב לקואליציה (%)":100*ready.probabilities.a,"רוב לאופוזיציה (%)":100*ready.probabilities.b,"לשניהם אין רוב (%)":100*ready.probabilities.neither}]:[];
 return <div className="wc-result" data-weight-mode={method.id}>
  {busy&&<div className="wc-progress" role="status" aria-live="polite">מחשב את התוצאה…<progress max="1" value={progress||0} aria-label="התקדמות חישוב המדד"/></div>}
  {repeated?<EvidenceChart id={id} title={title} variant="card" className="wc-method-card" {...bind} displayRows={[...rows,...chartRows]} rows={chartRows} height={130}
   spec={{type:"horizontalStackedBar100",x:"תרחיש",y:"רוב לקואליציה (%)",fields:["רוב לקואליציה (%)","רוב לאופוזיציה (%)","לשניהם אין רוב (%)"],valueDecimals:2,colors:{"רוב לקואליציה (%)":"#dc454c","רוב לאופוזיציה (%)":"#2378cf","לשניהם אין רוב (%)":"#89939f"}}}
   renderPlot={plot=><><div dir="ltr">{plot}</div>{details}</>}/>:<DataComponent id={id} title={title} variant="card" className="wc-method-card" kind="custom" {...bind} displayRows={rows} loading={busy} loadingError={error||undefined} loadingHeight={440}>{details}</DataComponent>}
 </div>;
}

export function WeightComparisonPage({input,config,result,baseline,busy=false,error,progress=0,onConfigChange,onSelectMethod}){
 const {queries,visible}=useDataApp();
 const methodWeights=config?.methodWeights??BLEND_DEFAULTS;
 const selectedMethods=Object.entries(methodWeights).filter(([,weight])=>weight>0);
 const [bloc,setBloc]=useState("a"),[separateOpen,setSeparateOpen]=useState(false),[separateMode,setSeparateMode]=useState("reference");
 const [separate,setSeparate]=useState({request:null,result:null,busy:false,error:"",progress:0});
 const separateRequest=useMemo(()=>({input,config,mode:separateMode}),[input,config,separateMode]);
 useEffect(()=>{
  let cancelled=false;
  if(!separateOpen){setSeparate({request:null,result:null,busy:false,error:"",progress:0});return;}
  setSeparate({request:separateRequest,result:null,busy:true,error:"",progress:0});
  async function compute(){
   try{
    const total=separateRequest.config?.iterations??1000;
    const job=createSimulation(separateRequest.input,{...separateRequest.config,iterations:total,weightMode:separateRequest.mode});
    while(job.done<total){
     if(cancelled)return;job.step(125);
     setSeparate(previous=>({...previous,progress:job.done/total}));await yieldFrame();
    }
    if(!cancelled)setSeparate({request:separateRequest,result:job.finish(),busy:false,error:"",progress:1});
   }catch(cause){if(!cancelled)setSeparate({request:separateRequest,result:null,busy:false,error:cause.message||"לא ניתן להשלים את החישוב.",progress:0});}
  }
  compute();return()=>{cancelled=true;};
 },[separateOpen,separateRequest]);
 const sourceIds=SOURCE_IDS.filter(id=>queries[id]?.rows),sourceRowsByQuery=Object.fromEntries(sourceIds.map(id=>[id,queries[id].rows]));
 const activeMode=config?.weightMode??"ensemble";
 const activeMethod=[...METHODS,ENSEMBLE,ROBUST].find(method=>method.id===activeMode)||{id:activeMode,title:activeMode==="quality"?"משקלי דיוק היסטוריים":"תרחיש תלות בין סוקרים",note:"ההנחות מפורטות בהגדרות המודל."};
 const separateMethod=METHODS.find(method=>method.id===separateMode);
 const separateCurrent=separate.request===separateRequest?separate:{result:null,busy:separateOpen,error:"",progress:0};
 const needsSelection=["ensemble","robust"].includes(activeMode)&&!selectedMethods.length;
 const readyResult=!busy&&!error&&!needsSelection?result:null;
 const mainRows=useMemo(()=>displayRows(activeMethod,readyResult,bloc),[activeMethod,readyResult,bloc]);
 const separateRows=useMemo(()=>displayRows(separateMethod,separateCurrent.result,bloc),[separateMethod,separateCurrent.result,bloc]);
 const applyMethod=mode=>onSelectMethod?.(mode);
 const description="התוצאה הראשית היא תוצאת המודל המשותפת לכל עמודי האפליקציה, באותה שיטת חיזוי ובאותן הדמיות. בפתיחת תוצאות השיטות בנפרד מחושבת חלופה נוספת, באותו זרע ותנאי הצבעה. מתג האות והרעש חל גם על כל החלופות: המשקלים קובעים את רמת האמון בתוך התאמת סדרת הזמן. השיטות אינן מקורות מידע עצמאיים. התוצאות מותנות במודל ואינן תחזית משא ומתן.";
 const bind={queryId:"polls",queryIds:sourceIds,sourceRows:queries.polls.rows,sourceRowsByQuery,description};
 const isVisible=id=>typeof visible!=="function"||visible(id);
 return <section className="weight-comparison-page" dir="rtl" aria-label="תוצאת המדד המשוקלל">
  <SectionHeader id="weight-comparison-heading" title="תוצאת המדד המשוקלל"/>
  <div className="wc-controls wc-main-controls">
   <Dropdown triggerClassName="filter-trigger e-content-select" contentClassName="election-select-menu" label="הרכב הגוש" showLabel value={bloc} choices={["a","b","other"]} choiceLabels={Object.fromEntries(Object.entries(BLOCS).map(([key,value])=>[key,value.name]))} onChange={setBloc}/>
   <Button disabled={!readyResult} onClick={()=>downloadComparison(mainRows,"weighted-index-"+activeMode+"-"+bloc+".csv")}>יצוא תוצאת המדד CSV</Button>
  </div>
  {needsSelection?<p className="wc-empty" role="status">בחרו לפחות שיטה אחת בהרחבת ״סקרים ומשקלים״ שבבורר גישת השקלול כדי לחשב את המדד.</p>:isVisible("weight-comparison-active")&&<ResultCard id="weight-comparison-active" title={activeMethod.title} method={activeMethod} result={result} bloc={bloc} busy={busy} error={error} progress={progress} bind={bind} input={input}/>}
  <details className="wc-disclosure wc-separate-disclosure" open={separateOpen} onToggle={event=>setSeparateOpen(event.currentTarget.open)}>
   <summary>תוצאות השיטות בנפרד</summary>
   {separateOpen&&<div className="wc-separate-body">
    <div className="wc-controls wc-separate-controls">
     <Dropdown triggerClassName="filter-trigger e-content-select" contentClassName="election-select-menu" label="שיטה לצפייה בנפרד" showLabel value={separateMode} choices={METHODS.map(method=>method.id)} choiceLabels={Object.fromEntries(METHODS.map(method=>[method.id,method.title]))} onChange={setSeparateMode}/>
     <Button disabled={separateCurrent.busy||!!separateCurrent.error||!separateCurrent.result} onClick={()=>downloadComparison(separateRows,"individual-method-"+separateMode+"-"+bloc+".csv")}>יצוא השיטה הנפרדת CSV</Button>
    </div>
    <p className="wc-caption">כל שיטה משקללת את אותם סקרים פעילים, באותם תנאי הצבעה. הצפייה בהשוואה אינה מחליפה את המדד הראשי; אפשר לבחור שיטה אחרת מתוך ההגדרות.</p>
    {isVisible("weight-comparison-individual")&&<ResultCard id="weight-comparison-individual" title={separateMethod.title} method={separateMethod} result={separateCurrent.result} bloc={bloc} busy={separateCurrent.busy} error={separateCurrent.error} progress={separateCurrent.progress} bind={bind} onApply={applyMethod} input={input}/>}
   </div>}
  </details>
 </section>;
}
export default WeightComparisonPage;
