import React,{useMemo} from "react";
import {Button,EvidenceChart,DataComponent,useDataApp} from "../../data-app-public.jsx";
import {MeanSeats} from "./MeanSeats.jsx";
import {PartyName} from "./PartyName.jsx";
import {hasSeatProbabilitySupport} from "./seat-probabilities.js";
import {summarizeSeatDistribution} from "./seat-distribution-summary.js";
import {getReportingGroups} from "./reporting-groups.js";
import {downloadRows} from "./transparency-data.js";
import "./seat-distribution-summary.css";

const BLOC_FIELDS={a:"קואליציה נוכחית (%)",b:"אופוזיציה (%)"};
const SOURCE_IDS=["polls","turnout_baseline","model_configuration","weight_presets","calibration","agreements"];
const number=(value,digits=0)=>Number.isFinite(value)?value.toLocaleString("he-IL",{minimumFractionDigits:digits,maximumFractionDigits:digits}):"—";
const available=summary=>summary.status==="ready"||summary.status==="single";

function summaryRecord(item,iterations){
 const valid=available(item.summary);
 return {"סוג רשומה":"מדדי סיכום","סוג ישות":item.party?"מפלגה":"גוש","מזהה":item.id,"שם":item.label,"הרצות":iterations,"מצב":item.unmodelled?"אין אומדן תמיכה נפרד":item.summary.status,"ממוצע":valid?item.summary.mean:null,"גבול תחתון 95% לממוצע":valid&&iterations>1?item.stats?.meanCI?.[0]??null:null,"גבול עליון 95% לממוצע":valid&&iterations>1?item.stats?.meanCI?.[1]??null:null,"חציון":valid?item.summary.median:null,"אחוזון 5":valid?item.summary.low:null,"אחוזון 95":valid?item.summary.high:null};
}

function SummaryTable({items,iterations,label}){
 return <div className="sds-table-scroll" role="region" aria-label={label+" — טבלה נגללת"} tabIndex={0}>
  <table className="sds-table" data-summary-table={items.some(item=>item.party)?"parties":"blocs"} data-reviewed-rows><caption>{label}</caption><thead><tr><th scope="col">{items.some(item=>item.party)?"מפלגה":"גוש"}</th><th scope="col">ממוצע ± 95% מההרצות</th><th scope="col">חציון</th><th scope="col">אחוזון 5</th><th scope="col">אחוזון 95</th></tr></thead>
   <tbody>{items.map(item=><tr key={item.id} data-distribution-entity={item.id} data-party-summary={item.party?item.id:undefined} data-bloc-summary={!item.party?item.id:undefined}><th scope="row">{item.party?<PartyName party={item.party}/>:<span className="sds-bloc-label" style={{color:item.color}}>{item.label}{item.memberNames?.length>0&&<small className="sds-members">{item.memberNames.join(" · ")}</small>}</span>}{item.unmodelled&&<small className="sds-unmodelled">אין אומדן תמיכה נפרד</small>}</th><td>{available(item.summary)?<MeanSeats stats={{...item.stats,mean:item.summary.mean}} iterations={iterations}/>:"—"}</td><td>{number(item.summary.median)}</td><td>{number(item.summary.low)}</td><td>{number(item.summary.high)}</td></tr>)}</tbody>
  </table>
 </div>;
}

export function SeatDistributionSummary({result,input,busy=false,error}){
 const {queries}=useDataApp(),iterations=result?.iterations;
 const model=useMemo(()=>{
  const names=new Map((result?.parties??input?.parties??[]).map(p=>[p.id,p.name]));
  const blocs=getReportingGroups(result,input).map(bloc=>({...bloc,memberNames:bloc.partyIds.map(id=>names.get(id)||id),summary:summarizeSeatDistribution(bloc.hist,iterations)}));
  const parties=(result?.parties??input?.parties??[]).filter(party=>party.ballot!==false).map(party=>{
   const unmodelled=!hasSeatProbabilitySupport(party),bloc=result?.config?.partyBlocs?.[party.id]??party.bloc??party.defaultBloc??"other";
   return {id:party.id,label:party.name,party:{...party,bloc},stats:party,unmodelled,summary:summarizeSeatDistribution(unmodelled?null:party.hist,iterations)};
  });
  const plotted=Object.fromEntries(blocs.filter(b=>b.id==='a'||b.id==='b').map(b=>[b.id,b]));
  const ready=['a','b'].every(id=>plotted[id]?.summary.status==='ready');
  const scope={"סך הרצות":iterations,"תאריך סקרים":result?.config?.asOf??input?.current?.asOf??"","זרע":result?.config?.seed??null,"הגדרות התרחיש":JSON.stringify(result?.config??{})};
  const chartData=ready?Array.from({length:121},(_,seats)=>({"מנדטים":seats,...scope,"קואליציה נוכחית — הרצות":plotted.a.hist[seats],"אופוזיציה — הרצות":plotted.b.hist[seats],[BLOC_FIELDS.a]:100*plotted.a.hist[seats]/iterations,[BLOC_FIELDS.b]:100*plotted.b.hist[seats]/iterations})):[];
  const observed=chartData.filter(row=>row["קואליציה נוכחית — הרצות"]>0||row["אופוזיציה — הרצות"]>0).map(row=>row.מנדטים);
  const first=Math.max(0,Math.min(61,...observed)-1),last=Math.min(120,Math.max(61,...observed)+1);
  const chartRows=chartData.filter(row=>row.מנדטים>=first&&row.מנדטים<=last);
  const bins=blocs.flatMap(bloc=>bloc.summary.distribution.map(row=>({"סוג רשומה":"התפלגות מלאה","מזהה גוש":bloc.id,"גוש":bloc.label,"מפלגות בקבוצה":bloc.memberNames.join(" · "),"מנדטים":row.seats,"הרצות":row.count,"סיכוי (%)":100*row.probability,...scope})));
  return {blocs,parties,ready,chartData,chartRows,bins,rows:[...blocs,...parties].map(item=>summaryRecord(item,iterations)).concat(bins)};
 },[result,input,iterations]);
 const ids=SOURCE_IDS.filter(id=>queries?.[id]),sourceRowsByQuery=Object.fromEntries(ids.map(id=>[id,queries[id].rows]));
 const description="התפלגות תדירויות מלאה של מנדטי הקואליציה והאופוזיציה: לכל מספר שלם, מספר ההרצות שבהן התקבל חלקי מספר ההרצות הכולל. ללא דגימת נקודות, ללא סינון תוצאות נדירות וללא החלקה. הממוצע, החציון ואחוזונים 5 ו־95 מחושבים מההיסטוגרמות המלאות. קבוצת הרשימות הערביות שמחוץ לגושים כוללת רק רשימות שלא נכללו בקואליציה או באופוזיציה בתרחיש. יתר הרשימות שמחוץ לגושים נספרות בקבוצה נפרדת; אין חפיפה בין השורות. קבוצה ללא מפלגות אינה מוצגת. רווח סמך 95% לממוצע מתאר שגיאת מונטה־קרלו; האחוזונים מתארים את פיזור תוצאות המודל. התרחיש: "+JSON.stringify(result?.config??{});
 const chartBinding={queryId:"polls",queryIds:ids,sourceRows:queries?.polls?.rows??[],sourceRowsByQuery,description};
 return <DataComponent id="e-seat-distribution-summary" title="התפלגות המנדטים של הגושים" variant="card" kind="custom" className="seat-distribution-summary" queryId="polls" queryIds={ids} sourceRows={queries?.polls?.rows??[]} sourceRowsByQuery={sourceRowsByQuery} displayRows={!busy&&!error?model.rows:[]} description={description} loading={busy} loadingError={error||undefined} loadingHeight={420}>
  <div data-reviewed-rows>
   {model.ready?<>
    <p className="sds-intro">ההתפלגות מבוססת על כל {number(iterations)} ההרצות. לכל מספר מנדטים, גובה העמודה הוא אחוז ההרצות שבהן התקבל — כולל תוצאות נדירות. רוב מתקבל מ־61 מנדטים.</p>
    <div data-full-seat-distribution data-total-runs={iterations} data-plotted-count-a={model.chartRows.reduce((sum,row)=>sum+row["קואליציה נוכחית — הרצות"],0)} data-plotted-count-b={model.chartRows.reduce((sum,row)=>sum+row["אופוזיציה — הרצות"],0)}>
     <EvidenceChart id="e-seat-distribution-histogram" title="תדירות מספרי המנדטים — כל ההרצות" variant="plain" {...chartBinding} rows={model.chartRows} displayRows={model.chartData} height={320}
      spec={{type:"bar",x:"מנדטים",y:BLOC_FIELDS.a,fields:[BLOC_FIELDS.a,BLOC_FIELDS.b],stackable:false,distribution:true,valueDecimals:4,xLabel:"מספר מנדטים",yLabel:"אחוז ההרצות (%)",colors:{[BLOC_FIELDS.a]:"#dc454c",[BLOC_FIELDS.b]:"#2378cf"}}}
      renderPlot={plot=><div className="sds-histogram-scroll" dir="ltr" role="region" tabIndex={0} aria-label="התפלגות מלאה — אפשר לגלול לרוחב"><div style={{minWidth:Math.max(760,model.chartRows.length*28)}}>{plot}</div></div>}/>
    </div>
    <details className="sds-frequency-details"><summary>טבלת התדירויות המלאה של שני הגושים</summary><div className="sds-table-scroll" role="region" tabIndex={0} aria-label="תדירות כל מספר מנדטים"><table className="sds-table" data-frequency-table><thead><tr><th scope="col">מנדטים</th><th scope="col">קואליציה — הרצות</th><th scope="col">קואליציה — סיכוי</th><th scope="col">אופוזיציה — הרצות</th><th scope="col">אופוזיציה — סיכוי</th></tr></thead><tbody>{model.chartData.map(row=><tr key={row.מנדטים} data-frequency-seats={row.מנדטים} data-count-a={row["קואליציה נוכחית — הרצות"]} data-count-b={row["אופוזיציה — הרצות"]}><th scope="row">{row.מנדטים}</th><td>{number(row["קואליציה נוכחית — הרצות"])}</td><td>{number(row[BLOC_FIELDS.a],4)}%</td><td>{number(row["אופוזיציה — הרצות"])}</td><td>{number(row[BLOC_FIELDS.b],4)}%</td></tr>)}</tbody></table></div></details>
   </>:<p className="sds-state" role="status">{iterations===1?"בהרצה אחת מוצגת תוצאה אחת. נדרשות לפחות שתי הרצות כדי לאמוד התפלגות.":"התפלגות מלאה של הגושים אינה זמינה עדיין."}</p>}
   {model.blocs.some(bloc=>available(bloc.summary))&&<SummaryTable items={model.blocs} iterations={iterations} label="מדדי המנדטים לפי גוש"/>}
   <p className="sds-note">חציון ואחוזונים 5 ו־95 מבוססים על כל ההרצות ומוצגים במנדטים שלמים. כאשר שני ערכי האמצע שונים, החציון הוא התחתון מביניהם; חציונים של גושים או מפלגות אינם חייבים להסתכם ל־120. הטווח <bdi dir="ltr">5–95</bdi> מתאר את פיזור התוצאות במודל; ± 95% ליד הממוצע מתאר את שגיאת אמידת הממוצע מההרצות בלבד.</p>
   {model.parties.length>0&&<details className="sds-party-details"><summary>מדדי כל המפלגות — ממוצע, חציון ואחוזונים</summary><SummaryTable items={model.parties} iterations={iterations} label="מדדי המנדטים לפי מפלגה"/></details>}
  </div>
  <div className="sds-actions"><Button disabled={busy||Boolean(error)||!model.bins.length} onClick={()=>downloadRows("seat-distributions-all-bins.csv",model.bins)}>הורדת ההתפלגויות המלאות CSV</Button><span>כל 121 ערכי המנדטים לכל קבוצה המוצגת בטבלה, עם הספירות המדויקות והגדרות התרחיש.</span></div>
  <p className="sds-credit">בהשראת תצוגת ההתפלגות והטבלאות ב<a href="https://themadad.com/modelb/" target="_blank" rel="noreferrer">מודל הבחירות של המדד</a>. הנתונים וההגדרות כאן הם של הסימולטור הזה.</p>
 </DataComponent>;
}
export default SeatDistributionSummary;
