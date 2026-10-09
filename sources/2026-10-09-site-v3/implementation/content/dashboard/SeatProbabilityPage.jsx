import React,{useMemo,useRef,useEffect} from "react";
import {DataComponent,EvidenceChart,Dropdown,Button,useDataApp} from "../../data-app-public.jsx";
import {StepControl} from "./StepControl.jsx";
import {PartyName,PARTY_COLORS} from "./PartyName.jsx";
import {MeanSeats} from "./MeanSeats.jsx";
import {analyzeSeatProbability,resolveSeatQuestionTarget,updateSeatQuestion,SEAT_COMPARISON_LABELS} from "./seat-probabilities.js";
import {downloadRows} from "./transparency-data.js";
import {WEIGHTING_LABELS} from "./WeightingControl.jsx";
import "./seat-probability-page.css";

const comparisons=SEAT_COMPARISON_LABELS;
const format=(value,digits=2)=>Number(value).toLocaleString("he-IL",{minimumFractionDigits:digits,maximumFractionDigits:digits});
const percent=value=>format(100*value)+"%";
const sourceIds=["polls","turnout_baseline","model_configuration","weight_presets","calibration","poll_correlation_profile","agreements"];

function DistributionPlot({plot,bins,focus}){
  const viewport=useRef(null);
  useEffect(()=>{
    const element=viewport.current;if(!element)return;
    const frame=requestAnimationFrame(()=>{element.scrollLeft=Math.max(0,(focus+.5)/bins*element.scrollWidth-element.clientWidth/2);});
    return()=>cancelAnimationFrame(frame);
  },[bins,focus]);
  return <div ref={viewport} dir="ltr" className="spp-plot-scroll" role="region" aria-label="התפלגות המנדטים — אפשר לגלול לרוחב" tabIndex={0}><div className="spp-plot" style={{minWidth:Math.max(500,bins*25+80)}}>{plot}</div></div>;
}

export function SeatProbabilityPage({result,input,config,busy,error,question,onQuestionChange,onConfigChange}){
  const {queries}=useDataApp();
  const {partyId,comparison}=question;
  const parties=input.parties.filter(p=>p.ballot!==false);
  const selected=result?.parties?.find(p=>p.id===partyId);
  const party={...(selected||parties.find(p=>p.id===partyId)),bloc:config.partyBlocs?.[partyId]};
  const targetState=resolveSeatQuestionTarget(selected,question.target,{busy,error});
  const {target,predictedSeats,isAutomatic}=targetState;
  const analysis=useMemo(()=>analyzeSeatProbability(busy||error?null:selected,result?.iterations,target,comparison),[selected,result,target,comparison,busy,error]);
  const ready=!busy&&!error&&analysis.status==="ready";
  const color=PARTY_COLORS[party.bloc]||PARTY_COLORS.other;
  const questionLabel="מה הסיכוי של "+party.name+" לקבל "+comparisons[comparison]+" "+(target===null?"את מספר המנדטים שבתחזית?":target+" מנדטים?");
  const context="סקרים: "+input.current.asOf+"; "+WEIGHTING_LABELS[config.weightMode]+"; סקרי ערוץ 14: "+(config.includeChannel14===false?"מוחרגים":"כלולים")+"; דמיון בין סקרים: "+(config.pollCorrelationEnabled?"מופעל — ניסיוני":"כבוי")+"; "+format(config.iterations,0)+" הרצות. החישוב משתמש באותן הרצות ובאותן הנחות כמו יתר הלשוניות. בכל הרצה מחושבים החסימה, באדר–עופר והסכמי העודפים מחדש.";
  const scope={"מפלגה":party.name,"מזהה מפלגה":partyId,"תנאי":comparisons[comparison],"יעד מנדטים":target,"מצב יעד":isAutomatic?"תחזית סקרים אוטומטית":"יעד ידני","מנדטים בתחזית הסקרים":predictedSeats,"פירוש התחזית":"חלוקת באדר–עופר של התמיכה המשוקללת בסקרים לאחר התאמות הצבעה, חסימה והסכמי עודפים; לפני ההרצות","הרצות":ready?analysis.total:null,"מספר הצלחות":ready?analysis.count:null,"סיכוי השאילתה (%)":ready?analysis.probability*100:null,"גבול תחתון 95% (%)":ready?analysis.ci[0]*100:null,"גבול עליון 95% (%)":ready?analysis.ci[1]*100:null,"תאריך הסקרים":input.current.asOf,"זרע":config.seed,"הגדרות התרחיש":JSON.stringify(config)};
  const distribution=ready?analysis.distribution.map(row=>({...scope,"מנדטים":row.seats,"הרצות עם מספר זה":row.count,"סיכוי למספר זה (%)":100*row.probability,"נכלל בשאילתה":row.selected,"בתנאי שנבחר (%)":row.selected?100*row.probability:0,"שאר התוצאות (%)":row.selected?0:100*row.probability})):[];
  const lastObserved=ready?Math.max(0,...analysis.distribution.filter(row=>row.count>0).map(row=>row.seats)):0;
  const maxShown=Math.min(120,Math.max(6,(target??0)+1,lastObserved+1));
  const chartRows=distribution.filter(row=>row.מנדטים<=maxShown);
  const bind={queryId:"polls",queryIds:sourceIds,sourceRows:queries.polls.rows,sourceRowsByQuery:Object.fromEntries(sourceIds.map(id=>[id,queries[id].rows])),description:context,loading:busy,loadingError:error||undefined};

  return <section className="seat-probability-page" aria-label="הסיכוי למספר מנדטים" data-seat-probability-page data-status={busy?"loading":error?"error":targetState.status==="unmodelled"?"unmodelled":analysis.status} data-seat-target={target??undefined} data-seat-target-mode={isAutomatic?"automatic":"manual"} data-seat-predicted-target={predictedSeats??undefined}>
    <div className="spp-controls">
      <Dropdown triggerClassName="filter-trigger e-content-select" contentClassName="election-select-menu" label="בחירת מפלגה" showLabel value={partyId} choices={parties.map(p=>p.id)} choiceLabels={Object.fromEntries(parties.map(p=>[p.id,p.name]))} onChange={value=>onQuestionChange(updateSeatQuestion(question,{partyId:value}))}/>
      <Dropdown triggerClassName="filter-trigger e-content-select" contentClassName="election-select-menu" label="איזה סיכוי לבדוק?" showLabel value={comparison} choices={Object.keys(comparisons)} choiceLabels={comparisons} onChange={value=>onQuestionChange(updateSeatQuestion(question,{comparison:value}))}/>
      {target!==null?<StepControl label="מספר מנדטים" min={0} max={120} step={1} value={target} disabled={busy||Boolean(error)} onChange={value=>onQuestionChange(updateSeatQuestion(question,{target:value}))}/>:<p className="spp-context" role="status">{busy?"מחשב את יעד המנדטים לפי ההגדרות…":"יעד אוטומטי יופיע כשיש תחזית סקרים תקינה למפלגה."}</p>}
    </div>
    <div className="spp-context" data-seat-forecast-caption aria-live="polite">
      {busy?<p>תחזית הסקרים מתעדכנת לפי ההגדרות שבחרת…</p>:error?<p>תחזית הסקרים אינה זמינה עד להשלמת ההרצה.</p>:predictedSeats!==null?<p><strong>תחזית הסקרים ל{party.name}: {predictedSeats} מנדטים.</strong> לפי הסקרים המשוקללים ואחוזי ההצבעה שנבחרו, לפני ההגרלות ולאחר חסימה, הסכמי עודפים ובאדר–עופר. {isAutomatic?"מספר המנדטים בשאלה מתעדכן אוטומטית עם ההגדרות.":"בשאלה מוצג היעד הידני שבחרת."}</p>:<p>{targetState.status==="unmodelled"?"אין למפלגה אומדן תמיכה נפרד, ולכן לא נקבע עבורה יעד אוטומטי.":"תחזית סקרים דטרמיניסטית אינה זמינה בתוצאה הזו; ניתן להריץ מחדש עם ההגדרות הנוכחיות."}</p>}
      {!isAutomatic&&<Button disabled={busy||Boolean(error)} onClick={()=>onQuestionChange(updateSeatQuestion(question,{target:null}))}>חזרה לתחזית הסקרים</Button>}
    </div>
    <p className="spp-context">הסקרים, המשקלים ואחוזי ההצבעה משותפים לכל הלשוניות. החלפת מפלגה או מספר מנדטים מציגה מיד תשובה מאותן הרצות.</p>
    <DataComponent id="party-seat-question" title="התשובה לשאלה שנבחרה" kind="custom" variant="card" {...bind} displayRows={ready?[scope]:[]}>
      <div className="spp-answer" data-reviewed-rows aria-live="polite" aria-atomic="true">
        <PartyName party={party}/>
        <h2>{questionLabel}</h2>
        {busy?<p role="status">מחשב מחדש לפי ההגדרות שבחרת…</p>:error?<p role="alert">ההרצה לא הושלמה: {error}</p>:targetState.status==="unmodelled"||analysis.status==="unmodelled"?<p>אין למפלגה אומדן תמיכה נפרד במודל. אי אפשר להסיק מכך שהסיכוי שלה לקבל מנדטים הוא אפס.</p>:analysis.status==="single"?<div><p>הרצה אחת נותנת תוצאה אחת, ולא אומדן הסתברות. הפעילו חזרות כדי לבדוק את הסיכוי.</p><Button onClick={()=>onConfigChange({iterations:10000})}>הרצת 10,000 הדמיות</Button></div>:!ready?<p role="status">אין עדיין התפלגות תקינה לחישוב הסיכוי.</p>:<>
          <strong className="spp-probability" style={{color}} data-seat-chance={analysis.probability} data-seat-successes={analysis.count} data-seat-trials={analysis.total} data-seat-ci-low={analysis.ci[0]} data-seat-ci-high={analysis.ci[1]}>{percent(analysis.probability)}</strong>
          <p className="spp-interval">רווח סמך 95%: <bdi dir="ltr">{percent(analysis.ci[0])}–{percent(analysis.ci[1])}</bdi></p>
          <p>{format(analysis.count,0)} מתוך {format(analysis.total,0)} הרצות ענו על התנאי.</p>
          <p className="spp-mean">תוחלת המפלגה: <MeanSeats stats={selected} iterations={result.iterations}/> מנדטים</p>
          <p className="spp-median">חציון: <b data-party-median={selected.median}>{selected.median}</b> מנדטים · אחוזונים <bdi dir="ltr">5–95</bdi>: <bdi dir="ltr">{selected.low}–{selected.high}</bdi> מנדטים</p>
          {analysis.count===0&&<p className="spp-boundary-note">התוצאה לא נצפתה בהרצות האלה; 0% במדגם ההרצות אינו הוכחה לאפס סיכוי.</p>}
          {analysis.count===analysis.total&&<p className="spp-boundary-note">התנאי התקיים בכל ההרצות האלה; 100% במדגם ההרצות אינו מבטיח את תוצאת הבחירות.</p>}
        </>}
      </div>
      <p className="spp-caption">רווחי הסמך מתארים את שגיאת האמידה מההרצות בלבד. הסיכויים עצמם מותנים בהנחות על טעות הסקרים ואחוזי ההצבעה. אפס מנדטים נכלל בהתפלגות כשהמפלגה אינה עוברת את החסימה.</p>
    </DataComponent>
    {ready&&<EvidenceChart id="party-seat-distribution" title={"התפלגות המנדטים — "+party.name} variant="card" {...bind} displayRows={distribution} rows={chartRows} height={300}
      spec={{type:"stackedBar",x:"מנדטים",y:"בתנאי שנבחר (%)",fields:["בתנאי שנבחר (%)","שאר התוצאות (%)"],valueDecimals:2,xLabel:"מספר מנדטים",yLabel:"סיכוי (%)",colors:{"בתנאי שנבחר (%)":color,"שאר התוצאות (%)":"#a1a8b2"}}}
      renderPlot={plot=><DistributionPlot plot={plot} bins={chartRows.length} focus={selected.mean}/>}>
      <p className="spp-caption">כל עמודה היא מספר מנדטים שלם. הצבע של המפלגה מדגיש את התוצאות שעונות על השאלה; האפור מציג את השאר. ההתפלגות כוללת גם 0, והרווחים בין מספרי המנדטים נשמרים. בטווח שלא מוצג לא נצפו תוצאות. במסך צר אפשר לגלול את התרשים לרוחב.</p>
      <Button onClick={()=>downloadRows("party-seat-probabilities-"+partyId+".csv",distribution)}>ייצוא התפלגות מלאה CSV</Button>
      <details className="spp-table-details"><summary>טבלת הסיכויים למספרי המנדטים</summary><div className="spp-table-scroll"><table><thead><tr><th scope="col">מנדטים</th><th scope="col">הרצות</th><th scope="col">סיכוי</th><th scope="col">בתנאי שנבחר</th></tr></thead><tbody>{chartRows.map(row=><tr key={row.מנדטים} data-seat-bin={row.מנדטים} data-selected={row["נכלל בשאילתה"]}><td>{row.מנדטים}</td><td>{format(row["הרצות עם מספר זה"],0)}</td><td>{format(row["סיכוי למספר זה (%)"])}%</td><td>{row["נכלל בשאילתה"]?"כן":"לא"}</td></tr>)}</tbody></table></div></details>
    </EvidenceChart>}
  </section>;
}
