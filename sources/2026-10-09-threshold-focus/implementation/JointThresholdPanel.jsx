import React,{useMemo,useState} from "react";
import {DataComponent,Button,useDataApp} from "../../data-app-public.jsx";
import {PartyName} from "./PartyName.jsx";
import {analyzeJointThreshold} from "./joint-threshold-probabilities.js";
import {downloadRows} from "./transparency-data.js";
import {WEIGHTING_LABELS} from "./WeightingControl.jsx";
import "./joint-threshold-panel.css";

const SOURCE_IDS=["polls","turnout_baseline","model_configuration","weight_presets","calibration","poll_correlation_profile","agreements"];
const MODES={atLeastTwo:"לפחות שתיים מהנבחרות לא יעברו",allFail:"כל הנבחרות לא יעברו"};
const number=(value,digits=0)=>Number(value).toLocaleString("he-IL",{minimumFractionDigits:digits,maximumFractionDigits:digits});
const percent=value=>number(100*value,2)+"%";
const hasSupport=party=>party?.hasModelledSupport===true||(party?.hasModelledSupport==null&&Number(party?.meanVotePct)>0);

export function JointThresholdPanel({result,input,config,busy=false,error="",onConfigChange}){
  const {queries}=useDataApp();
  const [selectedIds,setSelectedIds]=useState(["winter","hendel"]);
  const [mode,setMode]=useState("atLeastTwo");
  const parties=useMemo(()=>{
    const results=new Map((result?.parties||[]).map(party=>[party.id,party]));
    return (input?.parties||result?.parties||[]).filter(party=>party.ballot!==false).map(party=>({...party,...results.get(party.id)}));
  },[input,result]);
  const selected=parties.filter(party=>selectedIds.includes(party.id));
  const analysis=useMemo(()=>analyzeJointThreshold(busy||error?null:result,selectedIds,mode),[result,selectedIds,mode,busy,error]);
  const ready=!busy&&!error&&analysis.status==="ready";
  const status=busy?"loading":error?"error":analysis.status;
  const asOf=result?.config?.asOf||input?.current?.asOf||"";
  const activeConfig=result?.config||config||{};
  const eventLabel=MODES[mode]+" את אחוז החסימה";
  const selectedNames=selected.map(party=>party.name).join(" · ");
  const context="תאריך נתוני הסקרים: "+asOf+"; רשימות שנבחרו: "+selectedNames+"; תנאי: "+eventLabel+"; שקלול: "+(WEIGHTING_LABELS[activeConfig.weightMode]??activeConfig.weightMode??"")+"; ערוץ 14: "+(activeConfig.includeChannel14===false?"מוחרג":"כלול")+"; דמיון בין סקרים: "+(activeConfig.pollCorrelationEnabled?"מופעל — ניסיוני":"כבוי")+". הספירה מבוססת על תוצאות החסימה המדויקות באותן הדמיות, ללא הנחת עצמאות בין הרשימות.";
  const scope={"מפלגות שנבחרו":selectedNames,"מזהי מפלגות":selectedIds.join(";"),"מספר מפלגות שנבחרו":selectedIds.length,"תנאי":eventLabel,"מצב השאילתה":mode,"הרצות":ready?analysis.total:null,"הרצות שעונות על התנאי":ready?analysis.count:null,"סיכוי לפי המודל (%)":ready?100*analysis.probability:null,"גבול Wilson תחתון 95% (%)":ready?100*analysis.ci[0]:null,"גבול Wilson עליון 95% (%)":ready?100*analysis.ci[1]:null,"פירוש הטווח":"שגיאת האמידה מההרצות בלבד; לא אי־הוודאות הכוללת בבחירות","תאריך נתוני הסקרים":asOf,"זרע":ready?activeConfig.seed:null,"הגדרות התרחיש":ready?JSON.stringify(activeConfig):null};
  const distribution=ready?analysis.distribution.map(row=>({...scope,"סוג רשומה":"התפלגות מספר הרשימות שלא עברו","מספר נבחרות שלא עברו":row.failedCount,"הרצות עם מספר זה":row.count,"סיכוי למספר זה (%)":100*row.probability,"עונה על התנאי":mode==="allFail"?row.failedCount===selectedIds.length:row.failedCount>=2})):[];
  const rows=ready?[{...scope,"סוג רשומה":"תשובה לשאלה"},...distribution]:[];
  const sourceIds=SOURCE_IDS.filter(id=>queries[id]?.rows);
  const bind={queryId:"polls",queryIds:sourceIds,sourceRows:queries.polls?.rows??[],sourceRowsByQuery:Object.fromEntries(sourceIds.map(id=>[id,queries[id].rows])),description:context,loading:busy,loadingError:error||undefined};
  const toggle=id=>setSelectedIds(current=>current.includes(id)?current.filter(value=>value!==id):[...current,id]);
  const rerun=()=>{
    const seed=Number(config?.seed);
    onConfigChange?.({seed:Number.isSafeInteger(seed)&&seed<Number.MAX_SAFE_INTEGER?seed+1:1});
  };

  return <section className="joint-threshold-panel" dir="rtl" aria-label="אי־מעבר משותף של אחוז החסימה" data-joint-threshold-panel data-status={status}>
    <DataComponent id="threshold-joint-failure" title="מה הסיכוי שכמה מפלגות לא יעברו יחד?" kind="custom" variant="card" {...bind} displayRows={rows}>
      <div className="jtp-layout" data-reviewed-rows>
        <div className="jtp-selection">
          <fieldset className="jtp-parties">
            <legend>בחרו לפחות שתי מפלגות</legend>
            <div className="jtp-party-grid">{parties.map(party=>{
              const supported=hasSupport(party),checked=selectedIds.includes(party.id);
              return <label className={"jtp-party-choice"+(checked?" jtp-party-choice--selected":"")} key={party.id} data-supported={supported}>
                <input type="checkbox" value={party.id} data-joint-party={party.id} checked={checked} disabled={!supported&&!checked} onChange={()=>toggle(party.id)}/>
                <span className="jtp-party-label"><PartyName party={party} bloc="other"/>{!supported&&<small>ללא אומדן</small>}</span>
              </label>;
            })}</div>
          </fieldset>
          <label className="jtp-mode">
            <span>מה לבדוק?</span>
            <select value={mode} aria-label="תנאי אי־המעבר המשותף" onChange={event=>setMode(event.target.value)}>
              {Object.entries(MODES).map(([value,label])=><option key={value} value={value}>{label}</option>)}
            </select>
          </label>
          <p className="jtp-caption">הבחירה מתעדכנת מיד מתוך אותן הדמיות. נבדק מי לא עבר יחד בכל הרצה, בלי להניח שהסיכויים של המפלגות עצמאיים.</p>
        </div>
        <div className="jtp-answer" aria-live="polite" aria-atomic="true">
          <h3>{eventLabel}</h3>
          {selectedNames&&<p className="jtp-selected-names">{selectedNames}</p>}
          {busy?<p role="status">מחשב מחדש לפי ההגדרות שבחרתם…</p>:error?<p role="alert">ההרצה לא הושלמה: {error}</p>:analysis.status==="selection"?<p>בחרו לפחות שתי מפלגות עם אומדן תמיכה כדי לחשב סיכוי משותף.</p>:analysis.status==="unmodelled"?<p>לאחת הרשימות שנבחרו אין אומדן תמיכה נפרד. אי אפשר להסיק מכך שהיא בוודאות לא תעבור.</p>:analysis.status==="single"?<>
            <p>הרצה אחת מציגה תוצאה אחת. נדרשות חזרות כדי לאמוד סיכוי משותף.</p>
            <Button onClick={()=>onConfigChange?.({iterations:10000})}>הרצת 10,000 הדמיות</Button>
          </>:!ready?<>
            <p>אין עדיין תוצאות משותפות תקינות מההרצה הזו. הריצו מחדש כדי לחשב את הסיכוי.</p>
            <Button onClick={rerun}>הרצה מחדש</Button>
          </>:<>
            <span className="jtp-result-label">סיכוי לפי המודל</span>
            <strong className="jtp-probability" data-joint-probability={analysis.probability} data-joint-count={analysis.count} data-joint-total={analysis.total} data-joint-mode={mode} data-joint-ci-low={analysis.ci[0]} data-joint-ci-high={analysis.ci[1]}>{percent(analysis.probability)}</strong>
            <p>{number(analysis.count)} מתוך {number(analysis.total)} הרצות ענו על התנאי.</p>
            <p className="jtp-interval">טווח שגיאת החישוב (95%): <bdi dir="ltr">{percent(analysis.ci[0])}–{percent(analysis.ci[1])}</bdi></p>
            <p className="jtp-caption">הטווח מתאר את שגיאת האמידה מההרצות בלבד. הוא אינו מתאר את כל אי־הוודאות בתוצאת הבחירות.</p>
            {analysis.count===0&&<p className="jtp-boundary">התנאי לא נצפה בהרצות האלה; 0% אינו הוכחה לאפס סיכוי.</p>}
            {analysis.count===analysis.total&&<p className="jtp-boundary">התנאי התקיים בכל ההרצות האלה; 100% אינו מבטיח את תוצאת הבחירות.</p>}
            <Button onClick={()=>downloadRows("joint-threshold-probabilities.csv",rows)}>יצוא הסיכוי המשותף CSV</Button>
          </>}
        </div>
      </div>
      {ready&&<details className="jtp-details" data-reviewed-rows>
        <summary>כמה מהנבחרות לא עברו בכל הרצה?</summary>
        <div className="jtp-table-scroll"><table>
          <thead><tr><th scope="col">מספר שלא עברו</th><th scope="col">הרצות</th><th scope="col">סיכוי</th><th scope="col">עונה על התנאי</th></tr></thead>
          <tbody>{distribution.map(row=><tr key={row["מספר נבחרות שלא עברו"]} data-joint-failed-count={row["מספר נבחרות שלא עברו"]} data-selected={row["עונה על התנאי"]}><td>{row["מספר נבחרות שלא עברו"]}</td><td>{number(row["הרצות עם מספר זה"])}</td><td>{number(row["סיכוי למספר זה (%)"],2)}%</td><td>{row["עונה על התנאי"]?"כן":"לא"}</td></tr>)}</tbody>
        </table></div>
      </details>}
    </DataComponent>
  </section>;
}
