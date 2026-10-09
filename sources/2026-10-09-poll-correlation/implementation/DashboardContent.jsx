import React,{useEffect,useMemo,useRef,useState} from "react";
import {DataComponent,EvidenceChart,MetricCard,Dropdown,Switch,Button,SortableRegion,SortableItem,useDataApp,useDashboardTabs} from "../../data-app-public.jsx";
import {StepControl as Slider} from "./StepControl.jsx";
import {PartyName,PartyLogoSources} from "./PartyName.jsx";
import {BlocSettings} from "./BlocSettings.jsx";
import {applyBlocPreset,normalizeBlocConfig,describeBlocComposition} from "./bloc-presets.js";
import {PollViewer} from "./PollViewer.jsx";
import {PollDataPage} from "./PollDataPage.jsx";
import {MethodDataPage} from "./MethodDataPage.jsx";
import {WeightingControl,WEIGHTING_LABELS as modes} from "./WeightingControl.jsx";
import {ScenarioControls} from "./ScenarioControls.jsx";
import {withPollUncertainty} from "./scenario-policy.js";
import {MeanSeats} from "./MeanSeats.jsx";
import {SeatDistributionSummary} from "./SeatDistributionSummary.jsx";
import {TakeHomeMessage} from "./TakeHomeMessage.jsx";
import {SimulatorIntro} from "./SimulatorIntro.jsx";
import "./simple-layout.css";
import Worker from "./simulation.worker.js?worker&inline";
import {createSimulation,defaultConfig} from "./model/simulate.js";
import {createTurnoutModel} from "./model/turnout.js";
import {combineForecast,isSignalNoiseEnabled,resolveForecastConfig} from "./model/forecast.js";
import "./election.css";
import {SeatProbabilityPage} from "./SeatProbabilityPage.jsx";
import {PollTrendsPage} from "./PollTrendsPage.jsx";
import {ThresholdPage} from "./ThresholdPage.jsx";
import {WeightComparisonPage} from "./WeightComparisonPage.jsx";
import {WeightRationale} from "./WeightRationale.jsx";
import "./readability.css";
const blocColors={a:"#dc454c",b:"#2378cf",neither:"#87909d"};
const bn={a:"קואליציה נוכחית",b:"אופוזיציה",other:"ללא שיוך לגושים"};
const blendDefaults={equal:1,reference:1,littlepolls:1,gilead:1,rosner:0};
const n=(v,d=1)=>v==null?"—":Number(v).toLocaleString("he-IL",{minimumFractionDigits:d,maximumFractionDigits:d}),pc=(v,d=1)=>v==null?"—":n(v*100,d)+"%";
function download(name,text,type="application/json"){const u=URL.createObjectURL(new Blob([text],{type})),a=document.createElement("a");a.href=u;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(u),1000);}
function Chart(p){return <EvidenceChart variant="card" className="e-chart" renderPlot={plot=><div dir="ltr">{plot}</div>} {...p}/>;}
function tableRows(r,b){return r?r.parties.map(p=>({id:p.id,מפלגה:p.name,רשימה:p.ballot!==false,"קולות":p.meanVotes,"הסתברות למצביע (%)":r.iterations===1?100*(r.worlds[0].probabilities?.[r.parties.indexOf(p)]??r.pointProbabilities[r.parties.indexOf(p)]):null,תוחלת:p.mean,חציון:p.hasModelledSupport===false?null:p.median,"רווח תוחלת 95% תחתון":p.meanCI?.[0]??null,"רווח תוחלת 95% עליון":p.meanCI?.[1]??null,"מרווח תוחלת 95%":p.meanMargin??null,"מנדטים בהדמיה":p.mean,"בסיס הצבעה 2022":b?.parties.find(x=>x.id===p.id)?.mean??p.mean,"מעבר (%)":r.iterations>1?100*p.passProbability:null,"אי מעבר (%)":r.iterations>1?100*p.failProbability:null,"חסימה בהדמיה":p.passProbability===1?"עברה":p.passProbability===0?"לא עברה":"משתנה","קולות (%)":p.meanVotePct,נמוך:p.hasModelledSupport===false?null:p.low,גבוה:p.hasModelledSupport===false?null:p.high,בהינתןמעבר:p.meanIfPass,מפתתוחלתקולות:p.pointSeats,iterations:r.iterations,seed:r.config.seed,asOf:r.config.asOf,weightMode:r.config.weightMode,signalNoiseEnabled:Boolean(r.signalNoise),includeChannel14:r.config.includeChannel14!==false,pollCorrelationEnabled:r.config.pollCorrelationEnabled===true})):[];}
const TAKE_HOME_STORAGE="election:ad5864c5-c821-45f8-abfc-62e02191e56c:take-home:v1";
const emptyTakeHome={mode:"auto",text:"",scenarioKey:""};
function normalizeTakeHome(value){return value&&value.mode==="custom"&&typeof value.text==="string"?{mode:"custom",text:value.text,scenarioKey:typeof value.scenarioKey==="string"?value.scenarioKey:""}:{...emptyTakeHome};}
function readTakeHome(){try{return normalizeTakeHome(JSON.parse(localStorage.getItem(TAKE_HOME_STORAGE)||"null"));}catch{return {...emptyTakeHome};}}
export function DashboardContent(){
 const app=useDataApp(),{queries}=app;
 const knownTabLabels=["תמונה כללית","Dashboard","בית · תמונה כללית","בית — תמונה כללית","מפלגות ואחוז החסימה","סיכוי למספר מנדטים","מגמות סקרים","השוואת גישות","נתוני הסקרים","סקרים ושקלול","הרכב הגושים לפי שיטה"];
 const {activeTabId}=useDashboardTabs([{id:"dashboard",label:"בית — תמונה כללית",aliases:["comparison"],resetOrderOnLabelMigration:true},{id:"probabilities",label:"מפלגות ואחוז החסימה"},{id:"seat-probabilities",label:"סיכוי למספר מנדטים"},{id:"poll-trends",label:"מגמות סקרים"},{id:"method-data",label:"השוואת גישות"},{id:"poll-data",label:"נתוני הסקרים"}].map(tab=>({...tab,resetOrderOnLabelMigration:true,previousLabels:knownTabLabels.filter(label=>label!==tab.label)})));
 const input=useMemo(()=>Object.fromEntries(queries.model_input.rows.map(r=>[r.key,r.value])),[queries.model_input]);
 const defaults=useMemo(()=>(applyBlocPreset({...defaultConfig(input),samplingMode:"poll",iterations:10000,applyRecency:false,weightMode:"quality",signalNoiseEnabled:false,includeChannel14:false,pollCorrelationEnabled:false,robustShrinkage:.25,methodWeights:blendDefaults},input.parties,"none")),[input]);
 const [c,setRawC]=useState(()=>defaults),[r,setR]=useState(null),[base,setBase]=useState(null),[busy,setBusy]=useState(true),[progress,setProgress]=useState(0),[error,setError]=useState(""),[focus,setFocus]=useState("winter"),[worldSide,setWorldSide]=useState("pass"),[pair,setPair]=useState(["",""]);
 const setC=next=>setRawC(previous=>withPollUncertainty(resolveForecastConfig(typeof next==="function"?next(previous):next)));
 const [seatQuestion,setSeatQuestion]=useState({partyId:"likud",target:null,comparison:"atLeast"});
 const [takeHome,setTakeHome]=useState(readTakeHome);
 useEffect(()=>{try{localStorage.setItem(TAKE_HOME_STORAGE,JSON.stringify(takeHome));}catch{}},[takeHome]);
 const worker=useRef(null),rid=useRef(0),file=useRef(null);
 const upd=(k,v)=>setC(x=>({...x,[k]:v})),nest=(k,id,v)=>setC(x=>({...x,[k]:{...x[k],[id]:v}}));
 useEffect(()=>{try{const w=new Worker();w.postMessage({type:"init",input});worker.current=w;return()=>{w.terminate();worker.current=null;};}catch{}},[input]);
 useEffect(()=>{
  let cancelled=false;const id=++rid.current;setBusy(true);setError("");setProgress(0);
  const accept=d=>{if(cancelled||d.id!==id)return;if(d.type==="progress")setProgress(d.done/d.total);if(d.type==="result"){setR(d.result);setBase(d.baseline);setBusy(false);}if(d.type==="error"){setError(d.message);setBusy(false);}};
  const timer=setTimeout(async()=>{
   if(worker.current){worker.current.onmessage=e=>accept(e.data);worker.current.onerror=e=>accept({type:"error",id,message:e.message});worker.current.postMessage({type:"run",id,config:c});}
   else try{const outputs=[];for(const cfg of [c,{...c,turnout:defaults.turnout,externalMultiplier:1,blocMultipliers:defaults.blocMultipliers}]){const job=createSimulation(input,cfg);while(job.done<cfg.iterations){if(cancelled)return;job.step(250);accept({type:"progress",id,done:job.done+outputs.length*cfg.iterations,total:2*cfg.iterations});await new Promise(resolve=>setTimeout(resolve,0));}outputs.push(job.finish());}accept({type:"result",id,result:outputs[0],baseline:outputs[1]});}catch(e){accept({type:"error",id,message:e.message});}
  },280);return()=>{cancelled=true;clearTimeout(timer);};
 },[c,input]);
 useEffect(()=>{app.setDashboardBusy?.(busy);return()=>app.setDashboardBusy?.(false);},[busy]);
 const weights=useMemo(()=>{try{return combineForecast(input,c);}catch{return null;}},[input,c]);
 const turnout=useMemo(()=>{try{return createTurnoutModel(input.turnout,input.parties,c);}catch{return null;}},[input,c]);
 const single=c.iterations===1;
 const signalNoise=isSignalNoiseEnabled(c);
 const usesRosner=c.weightMode==='rosner'||(['ensemble','robust'].includes(c.weightMode)&&Number(c.methodWeights?.rosner??c.ensembleMix?.rosner??0)>0);
 const blocDescription=describeBlocComposition(c,input.parties);
 const scenarioDescription="נתונים "+input.current.asOf+"; "+(c.samplingMode==="fixed"?"הסתברויות קבועות לכל מצביע":"עם אי־ודאות בסקרים")+"; "+n(c.iterations,0)+" חזרות; השתתפות ביישובים לא יהודיים "+n(c.turnout.arab_localities)+"%, בשלוש ערים חרדיות "+n(c.turnout.haredi_three_cities)+"%; "+modes[c.weightMode]+"; אות ורעש: "+(signalNoise?"מופעל":"כבוי")+"; סקרי ערוץ 14: "+(c.includeChannel14===false?"מוחרגים":"כלולים")+"; דמיון בין סקרים: "+(c.pollCorrelationEnabled?"מופעל — ניסיוני":"כבוי")+"; הרכב גושים: "+blocDescription+". הסתברויות מותנות בהנחות.";
 const names=Object.fromEntries(input.parties.map(p=>[p.id,p.name])),ids=input.parties.filter(p=>p.ballot!==false).map(p=>p.id),rows=tableRows(r,base),selected=r?.parties.find(p=>p.id===focus),world=selected?.[worldSide==="pass"?"worldPass":"worldFail"];
 const cfgRows=Object.entries(c).map(([parameter,value])=>({parameter,value:typeof value==="object"?JSON.stringify(value):value}));
 const inputQuery=signalNoise?'signal_noise_observations':'polls';
 const bindingIds=[...new Set([inputQuery,"polls"]),"turnout_baseline","model_configuration","weight_presets","calibration","poll_correlation_profile","agreements"];
 const bindingRows=Object.fromEntries(bindingIds.map(id=>[id,queries[id]?.rows??[]]));
 const bind={queryId:inputQuery,queryIds:bindingIds,sourceRows:bindingRows[inputQuery],displayRows:rows,sourceRowsByQuery:bindingRows,description:scenarioDescription,loading:busy,loadingError:error||undefined};
 const panel={queryId:"model_configuration",sourceRows:queries.model_configuration.rows,displayRows:cfgRows};
 const hist=r?Array.from({length:121},(_,i)=>({מנדטים:i,"קואליציה נוכחית (%)":100*r.blocHist.a[i]/r.iterations,"אופוזיציה (%)":100*r.blocHist.b[i]/r.iterations})):[];
 const shareHist=selected?selected.voteHist.map((count,i)=>({"אחוז קולות":i/10,"שכיחות (%)":100*count/r.iterations})).filter(v=>v["אחוז קולות"]<=Math.max(6,selected.meanVotePct*1.6)): [];
 function rule(side,key,id,value){const k="coalition"+side;setC(x=>({...x,[k]:{...x[k],[key]:value?[...new Set([...x[k][key],id])]:x[k][key].filter(v=>v!==id)}}));}
 async function loadScenario(e){try{const v=JSON.parse(await e.target.files[0].text()),raw=v.config||v,legacyMode=raw.oppositionMode||((raw.partyBlocs?.joint==="b"?"all":raw.partyBlocs?.raam==="b"?"raam":"none")),merged=withPollUncertainty({...defaults,...raw,partyBlocs:Object.prototype.hasOwnProperty.call(raw,"partyBlocs")?raw.partyBlocs:undefined}),config=normalizeBlocConfig(merged,input.parties,{legacyMode});createSimulation(input,{...config,iterations:1});setC(config);setTakeHome(normalizeTakeHome(v.presentation?.takeHome));}catch(e){setError("תרחיש לא תקין: "+e.message);}e.target.value="";}
 function csv(){const cols=Object.keys(rows[0]||{}),esc=v=>'"'+String(v??"").replaceAll('"','""')+'"';download("election-results.csv","\uFEFF"+[cols.join(","),...rows.map(row=>cols.map(k=>esc(row[k])).join(","))].join("\r\n"),"text/csv;charset=utf-8");}
 const change=patch=>setC(x=>({...x,...patch}));
 const exportScenario=()=>download("election-scenario.json",JSON.stringify({input,config:c,result:r,baseline:base,presentation:{takeHome},limitations:queries.simulation_results.source.caveats},null,2));
 const weightingControl=<WeightingControl input={input} config={c} weights={weights} onConfigChange={change}/>;
 const blocControl=<BlocSettings input={input} config={c} onChange={setC}/>;
 const runControls=<details className="e-disclosure" id="run-settings"><summary>הרצות, שמירה וייצוא</summary><div className="e-toolbar">
  <Dropdown triggerClassName="filter-trigger e-content-select" contentClassName="election-select-menu" label="מספר חזרות" showLabel value={String(c.iterations)} choices={["1","100","1000","10000","50000","100000"]} choiceLabels={{1:"אחת — תוצאה אפשרית",100:"100",1000:"1,000",10000:"10,000",50000:"50,000",100000:"100,000"}} onChange={v=>upd("iterations",+v)}/>
  <Button onClick={()=>upd("seed",c.seed+1)}>הגרלה חדשה</Button>
  <Button disabled={busy||!r||!!error} onClick={csv}>ייצוא CSV</Button>
  <Button disabled={busy||!r||!!error} onClick={exportScenario}>ייצוא תרחיש ומקורות JSON</Button>
  <Button onClick={()=>file.current.click()}>טעינת תרחיש</Button><input hidden type="file" accept=".json" ref={file} onChange={loadScenario}/>
  <Button onClick={()=>setC(defaults)}>איפוס כל ההנחות</Button>
 </div><p className="e-caption">בכל חזרה מדמים הצבעה מלאה ומחלקים מחדש את המנדטים. המסר האישי נשמר בדפדפן הזה ונכלל בייצוא התרחיש.</p></details>;
 const turnoutPanel=(<DataComponent variant="plain" id="e-turnout" title="אחוזי הצבעה ומוטיבציה" queryId="turnout_baseline" sourceRows={queries.turnout_baseline.rows} kind="custom">
    <section className="e-motivation-controls" data-motivation-controls aria-label="מוטיבציה להצבעה לפי גוש">
     <h3>מוטיבציה להצבעה</h3>
     <p className="e-caption">100% = ללא שינוי. 97% = ירידה יחסית של 3%; 103% = עלייה יחסית של 3%. השינוי חל על ההגעה לקלפי של מצביעי הגוש לפי ההרכב שנבחר.</p>
     <div className="e-motivation-grid">{["a","b"].map(b=><div className="e-motivation-control" data-motivation-bloc={b} key={b}>
      <Slider label={"מוטיבציה — "+bn[b]} displayScale={100} suffix="%" min={.6} max={1.4} step={.01} value={c.blocMultipliers[b]} onChange={v=>nest("blocMultipliers",b,v)}/>
     </div>)}</div>
     <details className="e-motivation-other"><summary>מוטיבציה של מפלגות מחוץ לגושים</summary>
      <Slider label={bn.other} displayScale={100} suffix="%" min={.6} max={1.4} step={.01} value={c.blocMultipliers.other} onChange={v=>nest("blocMultipliers","other",v)}/>
     </details>
    </section>
    <h3 className="e-turnout-groups-heading">אחוזי הצבעה לפי קבוצות</h3>
    {input.turnout.groups.filter(g=>g.eligible>0).map(g=><div className="e-lever" key={g.id} data-turnout-group={g.id}><Slider label={g.label} suffix="%" min={0} max={100} step={.1} value={c.turnout[g.id]} formatValue={v=>n(v)+"%"} onChange={v=>nest("turnout",g.id,v)}/>
     <small>בסיס: {n(g.turnoutPct,2)}% · {n(g.localityCount,0)} יישובים · שינוי {n(c.turnout[g.id]-g.turnoutPct)} נק׳ אחוז</small></div>)}
    <p className="e-caption">שלוש הערים החרדיות הן אלעד, ביתר עילית ומודיעין עילית. ערבים בערים מעורבות וחרדים בערים אחרות נכללים ביתר היישובים. אלו קבוצות גאוגרפיות, לא כלל המגזרים.</p>
    <Slider label="מעטפות חיצוניות — מכפיל ערוץ" min={.5} max={1.5} step={.01} value={c.externalMultiplier} formatValue={v=>"×"+n(v,2)} onChange={v=>upd("externalMultiplier",v)}/>
    <small>462,807 מצביעים ב־2022; אין להם מכנה זכאים נוסף.</small>
    <Button onClick={()=>setC(x=>({...x,turnout:defaults.turnout,externalMultiplier:1,blocMultipliers:defaults.blocMultipliers}))}>חזרה להשתתפות 2022</Button>
   </DataComponent>);
 const uncertaintyPanel=(<DataComponent variant="card" id="e-model-controls" title="הנחות אי־הוודאות" kind="custom" {...panel}><p className="e-caption">{c.samplingMode==="fixed"?"שכבת אי־הוודאות כבויה. המחוונים הבאים אינם משנים את הדגימה במצב הקבוע, למעט יתרת רשימות קטנות שמשפיעה על שחזור הקלט.":"שכבת אי־הוודאות פעילה; היא משנה את הסתברויות ההצבעה בין חזרות."}</p><details><summary>מה אפשר לשנות במודל?</summary>
    {[["uncertaintyScale",signalNoise?"מכפיל אי־הוודאות באומדן התמיכה":"מכפיל טעות דגימה",.1,3,.1],["scatterStrength","פיזור בין סוקרים — עוצמה",0,1,.05],["commonBlocSD","שגיאת קואליציה נוכחית משותפת — נק׳ אחוז",0,4,.1],["designEffect","אפקט תכנון המדגם",1,4,.1],["forecastDays","אופק קדימה — ימים",0,90,1],["dailyDrift","תנודה יומית — נק׳ אחוז לשורש יום",0,.3,.01],["unreportedSmallPct",signalNoise?"יתרת רשימות קטנות לצורך משקלי רוזנר — %":"יתרת רשימות קטנות בשחזור — %",0,3,.1]].filter(([key])=>!signalNoise||(!['scatterStrength','dailyDrift','unreportedSmallPct'].includes(key)||(key==='unreportedSmallPct'&&usesRosner))).map(([key,label,min,max,step])=><Slider key={key} label={label} min={min} max={max} step={step} value={c[key]} disabled={c.samplingMode==="fixed"&&key!=="unreportedSmallPct"} onChange={v=>upd(key,v)}/>)}
    <p className="e-caption">{c.forecastDays===0?"תמונת מצב: ללא תוספת שינוי עד יום הבחירות.":"תחזית תרחיש קדימה עם תוספת שונות בזמן."} מועד הבחירות: {input.current.electionDate}.</p>
    <Button onClick={()=>upd("forecastDays",Math.max(0,Math.round((Date.parse(input.current.electionDate)-Date.parse(input.current.asOf))/864e5)))}>אופק עד יום הבחירות</Button>
    {!signalNoise&&<Switch label="אי־ודאות מעיגול מנדטים בסקר" disabled={c.samplingMode==="fixed"} checked={c.rounding} onChange={v=>upd("rounding",v)}/>}
    {[["registered","בעלי זכות בחירה — פנקס זמני 2026"],["seed","זרע אקראי לשחזור"]].map(([key,label])=><label className="e-number" key={key}>{label}<input type="number" value={c[key]} onChange={e=>upd(key,+e.target.value)}/></label>)}
    <p className="e-caption">{signalNoise?'אות–רעש כולל את אי־הוודאות של האומדן ואת השינוי בזמן. שגיאת הגוש המשותפת היא הנחת רגישות נוספת שמופעלת פעם אחת. החיזוי מניח תמיכה יציבה בממוצע ומרחיב את אי־הוודאות באופק קדימה.':'שונות הסקרים והשינוי העתידי מוגדרים כהנחות תרחיש ניתנות לשינוי; אינם פרמטרים שאומתו במלואם מן העבר.'}</p>
   </details></DataComponent>);
 const turnoutChanged=input.turnout.groups.filter(g=>g.eligible>0).some(g=>Math.abs(c.turnout[g.id]-defaults.turnout[g.id])>1e-8)||c.externalMultiplier!==1||Object.keys(bn).some(b=>c.blocMultipliers[b]!==defaults.blocMultipliers[b]);
 const scenarioControls=<ScenarioControls config={c} onConfigChange={change} blocSummary={blocDescription} turnoutChanged={turnoutChanged} polls={weightingControl} blocs={blocControl} turnout={turnoutPanel}/>;
 const advancedModelSettings=<details className="e-disclosure" id="uncertainty-settings"><summary>הנחות נוספות של המודל</summary>{uncertaintyPanel}</details>;
 const intro=<SimulatorIntro asOf={input.current.asOf} updateNote={input.current.updateNote??null} onOpenPollData={()=>app.exploreDashboard("poll-data")}/>;
 const message=<TakeHomeMessage result={r} input={input} config={c} busy={busy} error={error} value={takeHome} onChange={setTakeHome} onReset={()=>setC({...defaults})} controls={scenarioControls}/>;
 const pageSettings=<section className="e-page-settings" aria-label="הגדרות התרחיש">{scenarioControls}<div className="e-page-settings__actions"><Button onClick={()=>setC({...defaults})}>איפוס פרמטרים</Button></div></section>;
 const dataCaption=<p className="e-data-caption">סקרים: {input.current.asOf} · {n(c.iterations,0)} הרצות · שקלול: {modes[c.weightMode]} · אות ורעש: {signalNoise?"מופעל":"כבוי"} · ערוץ 14: {c.includeChannel14===false?"מחוץ לשקלול":"כלול"} · דמיון בין סקרים: {c.pollCorrelationEnabled?"מופעל":"כבוי"}{busy?" · מחשב…":""}</p>;
 if(activeTabId==="poll-data"||activeTabId==="method-data")return <article className="election-app e-simple-app" data-page={activeTabId} dir="rtl">
  <header className="e-page-heading"><h1>{activeTabId==="poll-data"?"נתוני הסקרים":"השוואת גישות השקלול"}</h1></header>
  {intro}
  {pageSettings}
  {activeTabId==="poll-data"?<><PollDataPage input={input} config={c}/><details className="e-disclosure"><summary>צפייה בכל סקר בנפרד</summary><PollViewer input={input} config={c}/></details></>:<MethodDataPage input={input} config={c}/>}
  {runControls}<PartyLogoSources/>
 </article>;
 if(activeTabId==="poll-trends")return <article className="election-app e-simple-app" data-page={activeTabId} dir="rtl">
  <header className="e-page-heading"><h1>מגמות סקרים לאורך זמן</h1><p>איך השתנתה תחזית המנדטים המשוקללת של כל מפלגה?</p></header>
  {intro}{pageSettings}{dataCaption}
  <PollTrendsPage input={input} config={c} weights={input.weightPresets}/>
  {runControls}<PartyLogoSources/>
 </article>;
 if(activeTabId==="seat-probabilities")return <article className="election-app e-simple-app" data-page={activeTabId} dir="rtl">
  <header className="e-page-heading"><h1>סיכוי למספר מנדטים</h1></header>
  {intro}{pageSettings}
  <SeatProbabilityPage result={r} input={input} config={c} busy={busy} error={error} question={seatQuestion} onQuestionChange={setSeatQuestion} onConfigChange={change}/>
  {runControls}<PartyLogoSources/>
 </article>;
 if(activeTabId==="probabilities")return <article className="election-app e-simple-app" data-page={activeTabId} dir="rtl">
  <header className="e-page-heading"><h1>מפלגות ואחוז החסימה</h1><p>מה הסיכוי של כל רשימה לעבור, וכמה מנדטים היא מקבלת בממוצע?</p></header>
  {intro}
  {pageSettings}{dataCaption}
  <ThresholdPage result={r} baseline={base} input={input} config={c} busy={busy} error={error} progress={progress} onConfigChange={change} simplified/>
  {runControls}<PartyLogoSources/>
 </article>;
 return <article className="election-app e-simple-app" data-page={activeTabId} dir="rtl">
  <header className="e-page-heading"><h1>תמונה כללית</h1>{dataCaption}</header>
  {intro}
  <div data-dashboard-home-anchor>{message}</div>
  <section className="e-home-methods" aria-label="הרכב הגושים לפי שיטה" data-home-methods>
   <h2>הרכב הגושים לפי שיטה</h2>
   <WeightComparisonPage input={input} config={c} result={r} baseline={base} busy={busy} error={error} progress={progress} onConfigChange={change} onSelectMethod={(weightMode,patch={})=>change({...patch,weightMode})}/>
   <details className="e-disclosure" id="weight-rationale-details"><summary>איך פועלות שיטות השקלול?</summary><WeightRationale/></details>
  </section>
  <SeatDistributionSummary result={r} input={input} busy={busy} error={error}/>
  {error&&<p role="alert" className="e-error">{error}</p>}
  <div className="e-next-actions"><Button onClick={()=>app.exploreDashboard("probabilities")}>סיכויי המעבר של כל מפלגה</Button><Button onClick={()=>app.exploreDashboard("seat-probabilities")}>סיכוי למספר מנדטים</Button><Button onClick={()=>app.exploreDashboard("poll-trends")}>מגמות הסקרים לאורך זמן</Button></div>
  {runControls}{advancedModelSettings}
  <details className="e-disclosure" id="detailed-results"><summary>פירוט המנדטים והתרחישים</summary><div className="e-results"><SortableRegion id="election:canvas" label="תוצאות הסימולציה" variant="canvas" columns={12} spacing="standard" rows={[{id:"e-summary",kind:"metrics",items:["e-a","e-b","e-neither"]},{id:"e-seat-row",items:["e-seats"]},{id:"e-pass-row",items:["e-pass"]},{id:"e-bloc-row",items:["e-blocs"]}]}>
    {[["a","רוב של 61 לקואליציה הנוכחית"],["b","רוב של 61 לאופוזיציה"],["neither","לשני הגושים אין 61"]].map(([key,title])=><SortableItem id={"e-"+key} key={key} label={title} kind="metric" span={4}><MetricCard id={"e-"+key} title={single?(key==="neither"?"מצביעים בהדמיה":key==="a"?"מנדטים לקואליציה הנוכחית":"מנדטים לאופוזיציה"):title} {...bind} value={<span style={{color:blocColors[key]}}>{single?n(key==="neither"?r?.meanBallots:r?.worlds[0]?.blocs[key],0):pc(r?.probabilities[key])}</span>} comparison={single?"":base?"בסיס השתתפות: "+pc(base.probabilities[key]):""} description={single?"תוצאה אחת של הצבעה, ולא אומדן הסתברות.":r?"טווח שגיאת ההרצה בלבד: "+pc(r.probabilityCI[key][0],2)+"–"+pc(r.probabilityCI[key][1],2):""}/></SortableItem>)}
    <SortableItem id="e-seats" label="תוחלת המנדטים" kind="chart" span={12}><Chart id="e-seats" title={single?"המנדטים בהדמיה — לאחר החסימה ובאדר–עופר":"תוחלת מנדטים — לאחר החסימה ובאדר–עופר"} {...bind} rows={rows.filter(v=>v.רשימה)} height={560}
     spec={{type:"horizontalBar",x:"מפלגה",y:single?"מנדטים בהדמיה":"תוחלת",fields:[single?"מנדטים בהדמיה":"תוחלת","בסיס הצבעה 2022"],stackable:false,valueDecimals:2,colors:{"מנדטים בהדמיה":"var(--chart-1)","תוחלת":"var(--chart-1)","בסיס הצבעה 2022":"var(--chart-8)"}}}>
     <p className="e-caption">{single?"כרגע זו תוצאה אקראית אחת, לא תוחלת. ":""}ההשוואה מחזירה רק את ההשתתפות והמוטיבציה ל־2022; יתר ההנחות זהות. תוחלת של 2 מנדטים אפשרית כשהרשימה מקבלת בכל סימולציה 0 או לפחות 4.</p></Chart></SortableItem>
    {!single&&<SortableItem id="e-pass" label="סיכויי מעבר החסימה" kind="chart" span={12}><Chart id="e-pass" title="מי תעבור את 3.25%?" {...bind} rows={rows.filter(v=>v.רשימה)} height={480}
     spec={{type:"horizontalStackedBar",x:"מפלגה",y:"מעבר (%)",fields:["מעבר (%)","אי מעבר (%)"],valueDecimals:1,colors:{"מעבר (%)":"var(--chart-3)","אי מעבר (%)":"var(--chart-8)"}}}>
     <p className="e-caption">תדירויות בסימולציות המודל. אפס מקרים שנצפו אינו הוכחה לאפס סיכון; טווחי שגיאת ההרצה בטבלה.</p></Chart></SortableItem>}
    {!single&&<SortableItem id="e-blocs" label="התפלגות מנדטי הגושים" kind="chart" span={12}><Chart id="e-blocs" title="התפלגות מנדטי הגושים — רוב מ־61" {...bind} rows={hist} height={270}
     spec={{type:"bar",x:"מנדטים",y:"קואליציה נוכחית (%)",fields:["קואליציה נוכחית (%)","אופוזיציה (%)"],stackable:false,valueDecimals:2,colors:{"קואליציה נוכחית (%)":blocColors.a,"אופוזיציה (%)":blocColors.b}}}/></SortableItem>}
   </SortableRegion>
   {single&&<DataComponent variant="card" id="e-voter-table" title="מההסתברות לכל מצביע אל הקולות והמנדטים" kind="table" {...bind}><div className="e-scroll"><table data-reviewed-rows><thead><tr><th>מפלגה</th><th>הסתברות למצביע</th><th>קולות שנדגמו</th><th>אחוז בפועל</th><th>מנדטים</th><th>חסימה</th></tr></thead><tbody>{r?.parties.map((p,j)=><tr key={p.id}><th><PartyName party={p} bloc={c.partyBlocs[p.id]}/></th><td>{pc(r.worlds[0].probabilities?.[j]??r.pointProbabilities[j],3)}</td><td>{n(r.worlds[0].votes[j],0)}</td><td>{pc(r.worlds[0].votes[j]/r.worlds[0].valid,3)}</td><td>{r.worlds[0].seats[j]}</td><td>{p.ballot===false?"יתרת רשימות":r.worlds[0].passed[j]?"עברה":"לא עברה"}</td></tr>)}</tbody></table></div><p className="e-caption">נדגמו {n(r?.worlds[0]?.ballots,0)} מצביעים, מהם {n(r?.worlds[0]?.valid,0)} קולות כשרים. עמודת ההסתברות מציגה את ההסתברויות ששימשו בפועל לכל מצביע בהדמיה הזאת, לאחר שקלול והשתתפות.</p></DataComponent>}
   {!single&&<DataComponent variant="card" id="e-table" title="התוצאה המלאה לכל רשימה" kind="table" {...bind} displayRows={rows}><div className="e-scroll"><table data-reviewed-rows><thead><tr><th>מפלגה</th><th>תוחלת ± 95%</th><th>חציון</th><th>אחוזונים <bdi dir="ltr">5–95</bdi></th><th>מעבר</th><th>אי מעבר</th><th>טווח להרצת המעבר</th><th>תוחלת אם עברה</th><th>מפת תוחלת קולות</th></tr></thead><tbody>
    {r?.parties.filter(p=>p.ballot!==false).map(p=><tr key={p.id}><th><button onClick={()=>setFocus(p.id)}><PartyName party={p} bloc={c.partyBlocs[p.id]}/></button></th><td><MeanSeats stats={p} iterations={r.iterations}/></td><td>{p.hasModelledSupport===false?"—":p.median}</td><td>{p.hasModelledSupport===false?"—":p.low+"–"+p.high}</td><td>{pc(p.passProbability,2)}</td><td>{pc(p.failProbability,2)}</td><td>{pc(p.passCI[0],2)}–{pc(p.passCI[1],2)}</td><td>{n(p.meanIfPass,2)}</td><td>{p.pointSeats}</td></tr>)}</tbody></table></div>
    <p className="e-caption">± לצד התוחלת: רווח סמך 95% לממוצע מההרצות. טווח המנדטים הוא בין אחוזונים 5 ו־95; בשלמות המנדטים הוא עשוי לכלול יותר מ־90% מתוצאות המודל. טווח המעבר: רווח Wilson של 95% לשגיאת ההרצה בלבד. מפת תוחלת הקולות מחלקת את ממוצע הקולות פעם אחת, בשונה מממוצע המנדטים. רשימות קטנות שלא דווחו בנפרד אינן בהכרח בעלות אפס תמיכה.</p>
   </DataComponent>}
   {!single&&<Chart id="e-party-dist" title="התפלגות התמיכה ברשימה" {...bind} rows={shareHist} height={240} spec={{type:"bar",x:"אחוז קולות",y:"שכיחות (%)",valueDecimals:2}} headerControls={<Dropdown triggerClassName="filter-trigger e-content-select" contentClassName="election-select-menu" label="רשימה" value={focus} choices={ids} choiceLabels={names} onChange={setFocus}/>}>
    <p className="e-caption">כל עמודה היא טווח של 0.1 נקודת אחוז; הסף 3.25% נמצא באמצע הטווח 3.2–3.3. הקביעה המדויקת נעשית לפי מספרי הקולות, ללא עיגול לתרשים.</p></Chart>}
   {!single&&<DataComponent variant="card" id="e-world" title="כשהרשימה עוברת — וכשהיא נופלת" kind="custom" {...bind}>
    <div className="e-comparison e-coalition-comparison"><div><small>סיכוי ל־61 בקואליציה הנוכחית כשהרשימה עוברת</small><strong>{pc(selected?.conditional.passA)}</strong></div><div><small>סיכוי ל־61 בקואליציה הנוכחית כשהרשימה לא עוברת</small><strong>{pc(selected?.conditional.failA)}</strong></div></div>
    <p className="e-caption">השוואה מותנית בין עולמות שונים, לא אומדן סיבתי. מקף: לא נצפו מקרים.</p>
    <Dropdown triggerClassName="filter-trigger e-content-select" contentClassName="election-select-menu" label="בדיקת מערכת בחירות אחת" showLabel value={worldSide} choices={["pass","fail"]} choiceLabels={{pass:"דוגמה שבה עברה",fail:"דוגמה שבה לא עברה"}} onChange={setWorldSide}/>
    {world?<><p>סימולציה {world.iteration}: {n(world.valid,0)} קולות כשרים · קואליציה נוכחית {world.blocs.a} · אופוזיציה {world.blocs.b}</p><div className="e-worlds" data-reviewed-rows>{ids.map(id=>{const j=input.parties.findIndex(p=>p.id===id);return <div key={id}><PartyName party={input.parties.find(p=>p.id===id)} bloc={c.partyBlocs[id]}/><strong>{world.seats[j]}</strong><small>{n(world.votes[j]/world.valid*100,2)}%</small></div>;})}</div></>:<p className="e-caption">לא נצפתה תוצאה כזאת בהרצה הנוכחית.</p>}
   </DataComponent>}</div></details>

  <PartyLogoSources/>
 </article>;
}
