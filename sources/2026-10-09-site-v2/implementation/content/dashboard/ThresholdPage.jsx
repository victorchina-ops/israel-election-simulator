import React,{useMemo,useState} from "react";
import {DataComponent,EvidenceChart,Dropdown,Button,Section,SectionHeader,useDataApp,barChartSpec} from "../../data-app-public.jsx";
import "./threshold-page.css";
import {MeanSeats} from "./MeanSeats.jsx";
import {PartyName,PartyLogo,PARTY_LOGOS} from "./PartyName.jsx";

import {downloadThresholdFigure} from "./threshold-figure-export.js";
import {WEIGHTING_LABELS} from "./WeightingControl.jsx";

const BLOC_COLORS={a:"#dc454c",b:"#2378cf",arab:"#87909d",other:"#87909d"};
const BLOC_LABELS={a:"הקואליציה הנוכחית",b:"האופוזיציה",arab:"ללא שיוך לגוש",other:"ללא שיוך לגוש"};
const FAIL_COLOR="#e8edf2";
const number=(v,d=1)=>v==null||!Number.isFinite(Number(v))?"—":Number(v).toLocaleString("he-IL",{maximumFractionDigits:d,minimumFractionDigits:d});
const percent=(v,d=1)=>v==null?"—":number(v*100,d)+"%";
const modelled=p=>p?.hasModelledSupport===true||(p?.hasModelledSupport==null&&Number(p?.meanVotePct)>0);
const SOURCE_IDS=["polls","turnout_baseline","model_configuration","weight_presets","calibration","poll_correlation_profile","agreements"];

function saveCSV(rows){
 const columns=["מפלגה","גוש","תמיכה במודל","מעבר (%)","אי מעבר (%)","גבול מעבר תחתון (%)","גבול מעבר עליון (%)","תוחלת מנדטים","חציון מנדטים","אחוזון 5","אחוזון 95","גבול תוחלת תחתון 95%","גבול תוחלת עליון 95%","תוחלת אם עברה","תמיכה ממוצעת (%)","מעבר בבסיס השתתפות (%)","הרצות","מצב דגימה","זרע","תאריך נתונים","שיטת שקלול","סקרי ערוץ 14","דמיון בין סקרים"];
 const quote=value=>'"'+String(value??"").replaceAll('"','""')+'"';
 const text="\uFEFF"+[columns.map(quote).join(","),...rows.map(row=>columns.map(key=>quote(row[key])).join(","))].join("\r\n");
 const url=URL.createObjectURL(new Blob([text],{type:"text/csv;charset=utf-8"})),link=document.createElement("a");
 link.href=url;link.download="threshold-probabilities.csv";link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
}

// The stored histogram contains actual simulated frequencies in 0.1-point bins.
// Aggregate adjacent bins only for display; all observed counts remain represented.
function histogram(p,iterations){
 const counts=Array.isArray(p?.voteHist)?p.voteHist:[];
 const active=counts.map((v,i)=>v>0?i:-1).filter(i=>i>=0);
 if(!active.length||!iterations)return {rows:[],width:null,includesThreshold:false};
 let lo=Math.max(0,active[0]-2),hi=Math.min(counts.length-1,active[active.length-1]+2);
 if(p.meanVotePct<=8){lo=Math.min(lo,30);hi=Math.max(hi,35);}
 const stride=Math.max(1,Math.ceil((hi-lo+1)/20));lo=Math.floor(lo/stride)*stride;
 const rows=[];
 for(let start=lo;start<=hi;start+=stride){
  const end=Math.min(start+stride,counts.length),count=counts.slice(start,end).reduce((a,b)=>a+b,0);
  const startPct=Math.min(100,start/10),endPct=Math.min(100,end/10);
  rows.push({מפלגה:p.name,"אחוז קולות":Number(((startPct+endPct)/2).toFixed(3)),"שכיחות (%)":100*count/iterations,"תחילת טווח (%)":startPct,"סוף טווח (%)":endPct,"הדמיות בטווח":count,"סף חוקי (%)":3.25});
 }
 return {rows,width:stride/10,includesThreshold:lo/10<=3.25&&(hi+1)/10>=3.25};
}

function centerPartyDistribution(event,h,party){
 const details=event.currentTarget;
 if(!details.open||!h.rows.length)return;
 const viewport=details.querySelector('.tp-party-plot-scroll');
 if(!viewport)return;
 const lo=h.rows[0]['תחילת טווח (%)'],hi=h.rows[h.rows.length-1]['סוף טווח (%)'];
 const target=h.includesThreshold?3.25:party.meanVotePct;
 const ratio=Number.isFinite(target)&&hi>lo?Math.max(0,Math.min(1,(target-lo)/(hi-lo))):.5;
 viewport.scrollLeft=Math.max(0,Math.min(viewport.scrollWidth-viewport.clientWidth,ratio*viewport.scrollWidth-viewport.clientWidth/2));
}

function partyRow(p,result,baseline){
 const measurable=modelled(p),repeated=result?.iterations>1;
 const base=baseline?.parties?.find(x=>x.id===p.id);
 return {id:p.id,מפלגה:p.name,"צבע הגוש":BLOC_COLORS[p.bloc||p.defaultBloc]||BLOC_COLORS.other,"סיכוי מעבר":measurable&&repeated?p.passProbability:null,"סיכוי אי מעבר":measurable&&repeated?p.failProbability:null,"גבול מעבר תחתון":measurable&&repeated?p.passCI?.[0]??null:null,"גבול מעבר עליון":measurable&&repeated?p.passCI?.[1]??null:null,"שלם":1,גוש:BLOC_LABELS[p.bloc||p.defaultBloc]||BLOC_LABELS.other,
  "תמיכה במודל":measurable?"יש אומדן תמיכה":"לא נאמדה בנפרד",
  "מעבר (%)":measurable&&repeated?100*p.passProbability:null,"אי מעבר (%)":measurable&&repeated?100*p.failProbability:null,
  "גבול מעבר תחתון (%)":measurable&&repeated&&p.passCI?100*p.passCI[0]:null,"גבול מעבר עליון (%)":measurable&&repeated&&p.passCI?100*p.passCI[1]:null,
  "תוחלת מנדטים":measurable&&repeated?p.mean:null,"חציון מנדטים":measurable&&repeated?p.median:null,"אחוזון 5":measurable&&repeated?p.low:null,"אחוזון 95":measurable&&repeated?p.high:null,"גבול תוחלת תחתון 95%":measurable&&repeated?p.meanCI?.[0]??null:null,"גבול תוחלת עליון 95%":measurable&&repeated?p.meanCI?.[1]??null:null,"תוחלת אם עברה":measurable&&repeated?p.meanIfPass:null,
  "תמיכה ממוצעת (%)":measurable?p.meanVotePct:null,
  "מעבר בבסיס השתתפות (%)":measurable&&repeated&&baseline?.iterations>1&&modelled(base)?100*base.passProbability:null,
  "הרצות":result?.iterations??0,"מצב דגימה":result?.config?.samplingMode==="fixed"?"הסתברויות קבועות":"אי־ודאות בסקרים",
  "זרע":result?.config?.seed??null,"תאריך נתונים":result?.config?.asOf??null,"שיטת שקלול":WEIGHTING_LABELS[result?.config?.weightMode]??result?.config?.weightMode??null,"סקרי ערוץ 14":result?.config?.includeChannel14===false?"מחוץ לשקלול":"כלולים","דמיון בין סקרים":result?.config?.pollCorrelationEnabled?"מופעל — ניסיוני":"כבוי"};
}

// Adorn the connected chart through its public slot; preserve its native marks,
// editor, tooltips and export. Follow the effective chart order and row limit.
function PartyLogosPlot({plot,chart,rows,parties,iterations,asOf}){
 const [exporting,setExporting]=useState(false),[exportError,setExportError]=useState("");
 const options=chart.barOptions||{};
 if(chart.presentation!=="progress"||chart.x!=="מפלגה"||options.labels?.position==="summary"||options.expandable)return <div dir="rtl">{plot}</div>;
 let displayed=[...rows];
 if(options.sort==="descending")displayed.sort((a,b)=>Number(b[chart.y])-Number(a[chart.y]));
 if(options.sort==="ascending")displayed.sort((a,b)=>Number(a[chart.y])-Number(b[chart.y]));
 if(options.visibleRows!=null)displayed=displayed.slice(0,options.visibleRows);
 if(!displayed.length)return <div dir="rtl">{plot}</div>;
 const exportFigure=async()=>{
  setExporting(true);setExportError("");
  try{await downloadThresholdFigure({rows:displayed,parties,iterations,asOf,chart,logoSources:PARTY_LOGOS});}
  catch(error){setExportError("לא ניתן לייצא את התרשים: "+error.message);}
  finally{setExporting(false);}
 };
 return <div className="tp-overview-figure" dir="rtl">
  <div className="tp-figure-actions"><Button disabled={exporting} onClick={exportFigure}>{exporting?"מייצא…":"ייצוא התרשים PNG"}</Button></div>
  {exportError&&<p className="tp-error" role="alert">{exportError}</p>}
  <div className="tp-overview-columns"><span>ממוצע מנדטים<small>בכל ההרצות</small></span><span>סיכוי לעבור לפי המודל</span></div>
  <div className="tp-logo-chart" data-reviewed-rows>
   <div className="tp-chart-logos" style={{gridTemplateRows:`repeat(${displayed.length},minmax(0,1fr))`,gap:options.style?.gap??20}}>
    {displayed.map(row=>{const party=parties.find(p=>p.id===row.id);return <span className="tp-chart-logo" key={row.id} data-party-id={row.id} title={party?.name}>
     <PartyLogo party={party}/>
     <span className="tp-overview-mean" style={{color:row["צבע הגוש"]}} aria-label={party?.name+" — ממוצע מנדטים"}>{number(party?.mean,1)}</span>
    </span>;})}
   </div>
   <div className="tp-logo-chart-plot">{plot}</div>
  </div>
 </div>;
}

function ProbabilitySummary({party,result,baseline}){
 const measurable=modelled(party),repeated=result?.iterations>1;
 const bloc=party.bloc||party.defaultBloc||"other",base=baseline?.parties?.find(p=>p.id===party.id);
 const interval=party.passCI;
 return <div className="tp-summary" data-reviewed-rows style={{"--tp-bloc-color":BLOC_COLORS[bloc]||BLOC_COLORS.other}}>
  <h3 className="party-heading"><PartyName party={party}/></h3>
  <div className="tp-party-context" style={{borderColor:BLOC_COLORS[bloc]||BLOC_COLORS.other}}>
   <span>{BLOC_LABELS[bloc]||BLOC_LABELS.other}</span>
   {measurable&&<span>תמיכה ממוצעת {number(party.meanVotePct,2)}%</span>}
  </div>
  {!measurable?<p className="tp-missing">אין למפלגה אומדן תמיכה נפרד בנתוני המודל. אי אפשר להסיק מכך שסיכוייה לעבור הם אפס.</p>:!repeated?<p className="tp-missing">הרצה אחת נותנת תוצאה אחת. נדרשות חזרות כדי לאמוד מעבר ואי־מעבר.</p>:<>
   <div className="tp-probabilities">
    <div className="tp-pass"><span>תעבור את החסימה</span><strong>{percent(party.passProbability)}</strong></div>
    <div className="tp-fail"><span>לא תעבור</span><strong>{percent(party.failProbability)}</strong></div>
   </div>
   <dl className="tp-seat-summary"><div><dt>תוחלת מנדטים ± 95%</dt><dd><MeanSeats stats={party} iterations={result.iterations}/></dd></div><div><dt>תוחלת אם עברה</dt><dd>{party.meanIfPass==null?"לא נצפה מעבר":number(party.meanIfPass,2)}</dd></div><div><dt>חציון מנדטים</dt><dd>{party.median}</dd></div><div><dt>אחוזונים <bdi dir="ltr">5–95</bdi></dt><dd><bdi dir="ltr">{party.low}–{party.high}</bdi></dd></div></dl>
   <p className="tp-interval">± ליד התוחלת: רווח סמך 95% לממוצע מההרצות, ולא טווח תוצאות הבחירות.</p>
   {interval&&<p className="tp-interval">טווח 95% לשגיאת ההרצה של המעבר: <bdi>{percent(interval[0],2)}–{percent(interval[1],2)}</bdi>.</p>}
   {party.passProbability===0&&interval&&<p className="tp-observed">לא נצפה מעבר בהרצות האלה; הגבול העליון בטווח ההרצה הוא {percent(interval[1],3)}. זו אינה הוכחה לאפס סיכוי.</p>}
   {party.passProbability===1&&interval&&<p className="tp-observed">לא נצפה כישלון בהרצות האלה; הגבול העליון לכישלון בטווח ההרצה הוא {percent(1-interval[0],3)}. זו אינה ודאות.</p>}
   {base&&baseline.iterations>1&&modelled(base)&&<p className="tp-baseline">בבסיס ההשתתפות של 2022: מעבר {percent(base.passProbability)}.</p>}
  </>}
 </div>;
}

export function ThresholdPage({result,baseline,input,config,busy=false,error="",progress=0,onConfigChange,children,simplified=false}){
 const {queries,visible}=useDataApp();
 const [sort,setSort]=useState("threshold");
 const repeated=Boolean(result&&result.iterations>1),single=Boolean(result&&result.iterations<=1);
 const inputQuery="polls";
 const sourceIds=[...new Set([inputQuery,...SOURCE_IDS])].filter(id=>queries[id]?.rows),sourceRowsByQuery=Object.fromEntries(sourceIds.map(id=>[id,queries[id].rows]));
 const selectedMode=config?.samplingMode||"fixed";
 const resultMode=result?.config?.samplingMode||selectedMode;
 const runCount=result?.iterations??0;
 const description="נתוני "+(result?.config?.asOf||input?.current?.asOf||"")+"; "+number(runCount,0)+" הדמיות; "+(resultMode==="fixed"?"הסתברויות קבועות לבוחר":"אי־ודאות בסקרים")+". מעבר נבדק בכל עולם על קולות שלמים מול 3.25% מכל הקולות הכשרים. לאחר מכן מחושבים באדר–עופר והסכמי עודפים מחדש.";
 const parties=useMemo(()=>{
  const source=result?.parties||input?.parties||[];
  return source.filter(p=>p.ballot!==false).slice().sort((a,b)=>{
   if(modelled(a)!==modelled(b))return modelled(a)?-1:1;
   if(sort==="name")return a.name.localeCompare(b.name,"he");
   if(sort==="pass")return (b.passProbability??-1)-(a.passProbability??-1)||(b.mean??0)-(a.mean??0)||a.name.localeCompare(b.name,"he");
   return Math.abs((a.passProbability??-1)-.5)-Math.abs((b.passProbability??-1)-.5)||a.name.localeCompare(b.name,"he");
  });
 },[result,input,sort]);
 const rows=useMemo(()=>parties.map(p=>partyRow(p,result,baseline)),[parties,result,baseline]);
 const plotRows=repeated?rows.filter(row=>row["מעבר (%)"]!=null):[];
 const unmeasured=parties.filter(p=>!modelled(p));
 const bind={queryId:inputQuery,queryIds:sourceIds,sourceRows:queries[inputQuery]?.rows??[],sourceRowsByQuery,description:description+" שקלול: "+(WEIGHTING_LABELS[config?.weightMode]??config?.weightMode)+"; ערוץ 14: "+(config?.includeChannel14===false?"מוחרג":"כלול")+"; דמיון בין סקרים: "+(config?.pollCorrelationEnabled?"מופעל — ניסיוני":"כבוי")+"."};
 const configRows=Object.entries(config||{}).map(([parameter,value])=>({parameter,value:typeof value==="object"?JSON.stringify(value):value}));
 const choices=[...new Set([Number(config?.iterations)||1000,1000,10000,50000])].sort((a,b)=>a-b);
 const change=patch=>onConfigChange?.(patch);
 const isVisible=id=>typeof visible!=="function"||visible(id);
 return <section className="threshold-page" dir="rtl" aria-label="סיכויי הגושים ומעבר אחוז החסימה">
  <SectionHeader id="threshold-page-heading" title="מי קרוב לאחוז החסימה?" filters={<div className="tp-controls">
   {!simplified&&<Dropdown triggerClassName="filter-trigger e-content-select" contentClassName="election-select-menu" label="מצב הסימולציה" showLabel value={selectedMode} choices={["fixed","poll"]} choiceLabels={{fixed:"הסתברויות קבועות",poll:"אי־ודאות בסקרים"}} onChange={samplingMode=>change({samplingMode})}/>}
   {!simplified&&<Dropdown triggerClassName="filter-trigger e-content-select" contentClassName="election-select-menu" label="מספר הדמיות" showLabel value={Number(config?.iterations)||1000} choices={choices} formatChoice={value=>value===1?"הרצה אחת — ללא הסתברויות":number(value,0)} onChange={value=>change({iterations:Number(value)})}/>}
   <Dropdown triggerClassName="filter-trigger e-content-select" contentClassName="election-select-menu" label="סדר המפלגות" showLabel value={sort} choices={["threshold","pass","name"]} choiceLabels={{threshold:"הכי קרובות ל־50% מעבר",pass:"סיכוי מעבר גבוה תחילה",name:"לפי שם"}} onChange={setSort}/>
   <Button disabled={!repeated||busy||!rows.length} onClick={()=>saveCSV(rows)}>יצוא טבלת סיכויים CSV</Button>
  </div>}/>
  <p className="tp-model-note">הסיכויים מחושבים מהסקרים ומההנחות שבחרתם, ואינם הבטחה לתוצאת הבחירות. סף החסימה הוא 3.25% מהקולות הכשרים; זה שונה מהסיכוי של מפלגה לעבור אותו.</p>
  {!simplified&&<DataComponent id="threshold-run-context" title="הנחות ההרצה" kind="custom" variant="plain" queryId="model_configuration" sourceRows={queries.model_configuration.rows} displayRows={configRows} description={description}>
   <div className="tp-assumptions" data-reviewed-rows>
    <p>{selectedMode==="fixed"?"ההסתברויות לכל מצביע קבועות. החזרות מודדות רעש הצבעה עצמאי בהינתן שקלול הסקרים, בלי להוסיף שגיאת סקר.":"בכל הדמיה משתנה גם התמיכה לפי שכבות אי־הוודאות שנבחרו. אלה הסתברויות מותנות במודל, שטרם כוילו כהסתברויות מול בחירות עצמאיות."}</p>
    <div className="tp-run-status" role="status" aria-live="polite">{busy?"מחשב את סיכויי המעבר…":result?number(runCount,0)+" הדמיות הושלמו":"ממתין לתוצאות"}{busy&&<progress max="1" value={Math.max(0,Math.min(1,progress||0))} aria-label="התקדמות ההדמיות"/>}</div>
   </div>
  </DataComponent>}
  {error&&<div className="tp-error" role="alert">ההרצה לא הושלמה: {error}</div>}
  {single&&!busy&&<p className="tp-single-guard" role="status">כעת קיימת הדמיה בודדת. בחרו לפחות 1,000 חזרות כדי לראות הסתברויות; הצלחה או כישלון בהרצה אחת אינם אומדן סיכוי.</p>}
  {children}
  {isVisible("threshold-overview")&&<EvidenceChart id="threshold-overview" title="סיכוי מעבר לפי המודל — כל הרשימות" variant="card" className="tp-overview" {...bind} displayRows={rows} rows={plotRows} height={Math.max(430,plotRows.length*56+80)} loading={busy} loadingError={error||undefined}
   renderPlot={(plot,chart)=><PartyLogosPlot plot={plot} chart={chart} rows={plotRows} parties={parties} iterations={runCount} asOf={result?.config?.asOf||input?.current?.asOf}/>}
   spec={barChartSpec({presentation:"progress",category:"מפלגה",value:"סיכוי מעבר",track:{max:"שלם",color:FAIL_COLOR},labels:{value:"formatted"},format:{style:"percent",minimumFractionDigits:2,maximumFractionDigits:2},style:{colorField:"צבע הגוש",textColorField:"צבע הגוש",thickness:20,fontSize:13,gap:12},tooltipFields:[{key:"סיכוי מעבר",label:"מעבר"},{key:"סיכוי אי מעבר",label:"אי מעבר"},{key:"גבול מעבר תחתון",label:"גבול תחתון 95%"},{key:"גבול מעבר עליון",label:"גבול עליון 95%"}]})}>
   <div className="tp-bloc-legend" aria-label="מקרא צבעי הגושים">{["a","b","other"].map(bloc=><span key={bloc} style={{color:BLOC_COLORS[bloc]}}><i style={{background:BLOC_COLORS[bloc]}} aria-hidden="true"/>{BLOC_LABELS[bloc]}</span>)}</div>
   <p className="tp-caption">אורך הפס הוא הסיכוי לעבור לפי המודל; ההשלמה הבהירה היא הסיכוי שלא לעבור. צבעי הרשימות מציינים את הגוש שבחרתם.</p>
   {unmeasured.length>0&&<p className="tp-caption">ללא אומדן תמיכה נפרד, ולכן ללא פס הסתברות: {unmeasured.map(p=><React.Fragment key={p.id}><PartyName party={p}/>{" · "}</React.Fragment>)}.</p>}
   <p className="tp-caption">ממוצע המנדטים כולל גם הרצות שבהן הרשימה לא עברה וקיבלה אפס. טווחי התוצאות ושגיאת החישוב נמצאים בפירוט לכל מפלגה.</p>
  </EvidenceChart>}
  <Section id="threshold-details-section" title="פירוט לפי מפלגה" columns={1} spacing="section">
   <p className="tp-detail-hint">לחצו על מפלגה לפתיחת המנדטים, טווח התוצאות והתפלגות התמיכה. ברירת המחדל מציגה קודם את הרשימות הקרובות ל־50% סיכוי מעבר.</p>
   <div className="tp-party-grid">
    {parties.map(p=>{
     const id="threshold-party-"+p.id;if(!isVisible(id))return null;
     const h=repeated&&modelled(p)?histogram(p,runCount):{rows:[],width:null,includesThreshold:false};
     const summary=<ProbabilitySummary party={p} result={result} baseline={baseline}/>;
     return <details className="tp-party-slot tp-party-details" key={p.id} data-threshold-party={p.id} aria-busy={busy} onToggle={event=>centerPartyDistribution(event,h,p)}>
      <summary className="tp-party-toggle">
       <span className="tp-party-toggle__identity"><PartyName party={p}/><small>{BLOC_LABELS[p.bloc||p.defaultBloc]||BLOC_LABELS.other}</small></span>
       <span className="tp-party-toggle__result" data-reviewed-rows><small>סיכוי מעבר במודל</small><strong>{busy?"מחשב…":!modelled(p)?"לא נאמד":!repeated?"נדרשות חזרות":percent(p.passProbability,1)}</strong>{!busy&&repeated&&modelled(p)&&<small>ממוצע {number(p.mean,1)} מנדטים</small>}</span>
       <span className="tp-party-toggle__action"><span className="tp-party-toggle__closed">פתיחת פירוט</span><span className="tp-party-toggle__open">סגירת פירוט</span><span className="tp-party-toggle__chevron" aria-hidden="true">⌄</span></span>
      </summary>
      <div className="tp-party-details__body">
      {h.rows.length?<EvidenceChart id={id} title={p.name} showHeading={false} variant="card" className="tp-party-card" {...bind} displayRows={[partyRow(p,result,baseline),...h.rows]} rows={h.rows} height={210} loading={busy} loadingError={error||undefined}
       spec={{type:"bar",x:"אחוז קולות",y:"שכיחות (%)",valueDecimals:2,colors:{"שכיחות (%)":BLOC_COLORS[p.bloc||p.defaultBloc]||BLOC_COLORS.other},xLabel:"אחוז מהקולות הכשרים"}}
       renderPlot={plot=><>{summary}<div className="tp-party-plot-scroll" dir="ltr" tabIndex={0} role="region" aria-label={p.name+" — התפלגות התמיכה; אפשר לגלול לרוחב"}><div className="tp-party-plot" dir="ltr">{plot}</div></div></>}>
       <p className="tp-caption">עמודה מכסה עד {number(h.width,1)} נקודת אחוז. {h.includesThreshold?"הסף 3.25% עשוי לחצות עמודה; ההכרעה מחושבת מהקולות המדויקים בכל הדמיה.":"הסף 3.25% מחוץ לטווח התמיכה שנצפה כאן."} אפשר לגלול את התרשים לרוחב.</p>
      </EvidenceChart>:<DataComponent id={id} title={p.name} showHeading={false} variant="card" className="tp-party-card" kind="custom" {...bind} displayRows={[partyRow(p,result,baseline)]} loading={busy} loadingError={error||undefined}>{summary}</DataComponent>}
      </div>
     </details>;
    })}
   </div>
  </Section>
 </section>;
}
