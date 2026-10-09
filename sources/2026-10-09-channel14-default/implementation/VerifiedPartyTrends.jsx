import React from 'react';
import {DataComponent,useDataApp} from '../../data-app-public.jsx';
import {PartyName} from './PartyName.jsx';
import {dateLabel,numberLabel} from './transparency-data.js';
import './verified-party-trends.css';

const signed=value=>`${value>0?'+':''}${numberLabel(Math.abs(value)<.005?0:value,2)}`;
const pLabel=value=>Number.isFinite(value)?numberLabel(value,4):'—';
const direction=value=>value>.00001?'is-positive':value<-.00001?'is-negative':'';
function downloadCsv(rows,filename){
 const columns=Object.keys(rows[0]??{});
 const cell=value=>`"${String(value??'').replaceAll('"','""')}"`;
 const text='\uFEFF'+[columns,...rows.map(row=>columns.map(key=>row[key]))].map(row=>row.map(cell).join(',')).join('\r\n');
 const url=URL.createObjectURL(new Blob([text],{type:'text/csv;charset=utf-8'}));
 const link=document.createElement('a');link.href=url;link.download=filename;link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
}

export function VerifiedPartyTrends({parties=[],config={},dataAsOf}){
 const {queries}=useDataApp();
 const prefix=config.includeChannel14===false?'verified_party_trends_without_channel14':'verified_party_trends';
 const metadataId=prefix+'_metadata',pollsId=config.includeChannel14===false?prefix+'_polls':'verified_party_trend_polls';
 const report=queries?.[metadataId]?.rows?.[0];
 const rawRows=queries?.[prefix]?.rows??[];
 if(!report||!rawRows.length)return null;
 const coverage=report.coverage;
 const rows=[...rawRows].sort((a,b)=>a.pValue-b.pValue||Math.abs(b.weightedNetDelta)-Math.abs(a.weightedNetDelta));
 const partyById=new Map(parties.map(p=>[p.id,p]));
 const sourceIds=[prefix,pollsId,metadataId];
 const sourceRowsByQuery=Object.fromEntries(sourceIds.map(id=>[id,queries[id]?.rows??[]]));
 const bind={queryId:sourceIds[0],queryIds:sourceIds,sourceRows:rawRows,sourceRowsByQuery};
 const significant=rows.filter(row=>!row.zeroSeatsThroughout&&row.qValue<.05);
 const nominal=rows.filter(row=>!row.zeroSeatsThroughout&&row.pValue<.05);
 const sensitivity=rows.filter(row=>!row.zeroSeatsThroughout&&row.wholeSeriesSignFlipQ<.05);
 const individual=rows.flatMap(row=>row.byPollster??[]);
 const individualNominal=individual.filter(row=>row.pValue<.05);
 const individualSignificant=individual.filter(row=>row.qValue<.05);
 const zeroNames=rows.filter(row=>row.zeroSeatsThroughout).map(row=>row.partyName).join(', ');
 const changes=rows.filter(row=>!row.zeroSeatsThroughout).sort((a,b)=>Math.abs(b.weightedNetDelta)-Math.abs(a.weightedNetDelta)).slice(0,4);
 const conclusion=significant.length?`מגמה מובהקת לאחר תיקון ב־${significant.map(row=>row.partyName).join(', ')}`:'אין מפלגה עם מגמה מובהקת לאחר תיקון לריבוי בדיקות';
 const stale=Boolean(dataAsOf&&dataAsOf>report.asOf);
 const seriesLengths=report.weights.map(item=>item.nPolls);
 const seriesLengthRange=`${Math.min(...seriesLengths)}–${Math.max(...seriesLengths)}`;
 const displayRows=rows.map(row=>({מפלגה:row.partyName,'שינוי מצטבר משוקלל':row.weightedNetDelta,'מגמה במנדטים לשבוע':row.slopePerWeek,
  'p לפני תיקון':row.zeroSeatsThroughout?null:row.pValue,'q אחרי BH':row.zeroSeatsThroughout?null:row.qValue,
  'p בבדיקת רגישות':row.zeroSeatsThroughout?null:row.wholeSeriesSignFlipP,'q ברגישות':row.zeroSeatsThroughout?null:row.wholeSeriesSignFlipQ,
  'מצב':row.zeroSeatsThroughout?'אפס מנדטים בכל הסקרים; אין שונות לבדיקה':row.qValue<.05?'מובהק אחרי תיקון':'לא מובהק אחרי תיקון',
  'תאריך הניתוח':report.asOf,'תחילת איסוף':coverage.from,'סוף איסוף':coverage.to,'שקלול':'דיוק היסטורי — ניתוח שמור','סקרי ערוץ 14':config.includeChannel14===false?'מוחרגים':'כלולים'}));
 const detailRows=rows.flatMap(row=>(row.byPollster??[]).map(item=>({מפלגה:row.partyName,סדרה:item.label??item.pollsterId,
  'סקרים':item.nPolls,'תאריכי פרסום':(item.dates??[]).join(' | '),'מנדטים לאורך הסדרה':(item.seats??[]).join(' | '),
  'Δ ראשון–אחרון':item.netDelta,'מגמה לשבוע':item.slopePerWeek,'p לפני תיקון':item.pValue,[`q אחרי BH ל־${report.methodology.individualTests} בדיקות`]:item.qValue,'תאריך הניתוח':report.asOf})));
 return <section className="vpt" data-verified-party-trends aria-labelledby="vpt-title">
  <div className="vpt-intro">
   <div className="vpt-heading"><div><span className="vpt-eyebrow">כל הסדרה לאחר סגירת הרשימות · איסוף מאומת בלבד</span><h2 id="vpt-title">מה השתנה אצל כל מפלגה?</h2></div><span className="vpt-date">ניתוח שמור ל־{dateLabel(report.asOf)}</span></div>
   <div className="vpt-facts"><span><b>{coverage.pollCount}</b> סקרים</span><span><b>{coverage.seriesCount}</b> סדרות סקרים</span><span><b>{coverage.deltaCount}</b> שינויים עוקבים</span><span><b>{dateLabel(coverage.from)}–{dateLabel(coverage.to)}</b> מועדי האיסוף</span></div>
   <p className="vpt-fixed"><strong>הגדרות הניתוח: דיוק היסטורי · ערוץ 14 {config.includeChannel14===false?'מוחרג':'כלול'}.</strong> המשקלים מנורמלים ל־{coverage.seriesCount} הסדרות שנכללו. מתג ערוץ 14 בוחר בין שתי גרסאות של הניתוח שחושבו בנפרד, כולל המובהקות. יתר בחירות הסקרים והמשקלים משנות את החקירה האינטראקטיבית בהמשך העמוד. אחוזי הצבעה והרכב גושים אינם חלק מבדיקה זו.</p>
   {stale&&<p className="vpt-stale" role="note">במאגר יש סקרים מאוחרים יותר. סקרים ללא מועד איסוף מאומת מוצגים בחקירה האינטראקטיבית אך מוחרגים מהניתוח המחמיר עד לאימות המועד.</p>}
  </div>
  <div className="vpt-conclusion" role="note"><strong>{conclusion}</strong>
   <p>השינויים המצטברים הבולטים הם {changes.map(row=>`${row.partyName} (${signed(row.weightedNetDelta)} מנדטים)`).join(', ')}. {nominal.length?`לפני התיקון מופיעים אותות אצל ${nominal.map(row=>row.partyName).join(', ')}; `:''}{!significant.length?`לאחר שמביאים בחשבון שבדקנו ${coverage.partyCount} מפלגות, אין די ראיות להכריז על מגמה מובהקת במפלגה מסוימת.`:'המובהקות מותנית בהנחות המבחן.'}</p>
   <p>{sensitivity.length?`בבדיקת הרגישות לסדרות שלמות התקבלה מובהקות לאחר תיקון אצל ${sensitivity.map(row=>row.partyName).join(', ')}.`:'בבדיקת הרגישות המבוססת על סדרות שלמות לא התקבלה מפלגה מובהקת לאחר תיקון.'} אי־מובהקות אינה הוכחה שאין שינוי; בכל סדרה יש רק {seriesLengthRange} סקרים.</p>
  </div>
  <div className="vpt-method"><h3>מה נותח ואיך?</h3><p>נכללו רק סקרים שאומת במקור שאיסופם התחיל מ־9.9.2026, אחרי סגירת הרשימות ב־8.9. בתוך כל סדרת סקרים חושבו כל השינויים העוקבים ונאמד קצב שינוי במנדטים לשבוע לפי מועדי האיסוף. הקצבים שוקללו לפי הדיוק ההיסטורי. המובהקות נבדקה בערבוב מועדי התוצאות בתוך כל סדרה, ותוקנה בשיטת Benjamini–Hochberg עבור 17 מפלגות. הבדיקה מתייחסת למנדטים שפורסמו בסקרים, ולא לסימולציית הבחירות או לנתוני הצבעה גולמיים.</p></div>
  <DataComponent id="verified-party-trend-table" title="שינוי ומובהקות לכל מפלגה — התקופה המאומתת" variant="card" kind="table" {...bind} displayRows={displayRows}>
   <div className="vpt-toolbar"><span>מובהקות לאחר תיקון: q קטן מ־0.05</span><button type="button" className="vpt-button" onClick={()=>downloadCsv(displayRows,`party-trends-verified-${report.asOf}.csv`)}>הורדת הטבלה CSV</button></div>
   <div className="pt-table-scroll" tabIndex={0} role="region" aria-label="טבלת מגמות מפלגות בתקופה המאומתת"><table className="pt-table vpt-table" data-reviewed-rows><thead><tr><th scope="col">מפלגה</th><th scope="col">Δ מצטבר*</th><th scope="col">מנדטים לשבוע</th><th scope="col">p לפני תיקון</th><th scope="col">q אחרי תיקון BH</th><th scope="col">מסקנה לאחר תיקון</th></tr></thead><tbody>{rows.map(row=><tr key={row.partyId} data-verified-party-id={row.partyId} data-significant={(!row.zeroSeatsThroughout&&row.qValue<.05)||undefined}><th scope="row"><PartyName party={partyById.get(row.partyId)??{id:row.partyId,name:row.partyName}} bloc={config.partyBlocs?.[row.partyId]}/></th><td className={direction(row.weightedNetDelta)}><bdi>{signed(row.weightedNetDelta)}</bdi></td><td className={direction(row.slopePerWeek)}><bdi>{signed(row.slopePerWeek)}</bdi></td><td><bdi>{row.zeroSeatsThroughout?'—':pLabel(row.pValue)}</bdi>{!row.zeroSeatsThroughout&&row.pValue<.05&&row.qValue>=.05&&<small>אות לפני תיקון בלבד</small>}</td><td><bdi>{row.zeroSeatsThroughout?'—':pLabel(row.qValue)}</bdi></td><td>{row.zeroSeatsThroughout?'אפס מנדטים לאורך הסדרה':row.qValue<.05?'מובהק':'לא מובהק'}</td></tr>)}</tbody></table></div>
   <p className="vpt-note">* Δ מצטבר הוא ממוצע משוקלל של ההפרש מהסקר הראשון לאחרון בכל סדרה; טווחי הסדרות אינם זהים. ערכי p בודקים את המגמה מכל הסקרים, ולא רק את הפרש הקצוות. צבע השינוי מציין כיוון, ואינו מעיד על מובהקות.</p>
   <p className="vpt-note">{zeroNames}: אפס מנדטים בכל הסקרים שנכללו. אין להסיק מכך שהתמיכה מתחת לאחוז החסימה לא השתנתה. הן נכללו בתיקון עם p=1 לסדרה קבועה, ומוצגות עם מקף כדי להבהיר שאין שונות במנדטים לבדיקה.</p>
  </DataComponent>
  <details className="vpt-details"><summary>פירוט לפי סדרת סקרים ובדיקת הרגישות — לחצו לפתיחה</summary>
   <p>{individualNominal.length?`לפני התיקון נמצאו ${individualNominal.length} אותות במבחני מכון–מפלגה; `:'אצל אף גוף סקרים בנפרד לא התקבלה מפלגה מובהקת אפילו לפני תיקון. '}{individualSignificant.length?`לאחר תיקון נותרו ${individualSignificant.length} מובהקים. `:'לאחר תיקון לא נותרה בדיקה מובהקת. '}בבדיקות הנפרדות בוצע תיקון ל־{report.methodology.individualTests} השוואות: {coverage.partyCount} מפלגות × {coverage.seriesCount} סדרות.</p>
   <button type="button" className="vpt-button" onClick={()=>downloadCsv(detailRows,`party-trends-by-pollster-${report.asOf}.csv`)}>הורדת פירוט לכל מפלגה וסוקר CSV</button>
   <div className="pt-table-scroll" tabIndex={0} role="region" aria-label="בדיקת רגישות למגמות המפלגות"><table className="pt-table vpt-sensitivity"><thead><tr><th scope="col">מפלגה</th><th scope="col">p בהיפוך סדרות שלמות</th><th scope="col">q ברגישות אחרי BH</th></tr></thead><tbody>{rows.filter(row=>!row.zeroSeatsThroughout).map(row=><tr key={row.partyId}><th scope="row">{row.partyName}</th><td><bdi>{pLabel(row.wholeSeriesSignFlipP)}</bdi></td><td><bdi>{pLabel(row.wholeSeriesSignFlipQ)}</bdi></td></tr>)}</tbody></table></div>
  </details>
  <details className="vpt-details"><summary>מועדי האיסוף, ההחרגות והנחות המבחן — לחצו לפתיחה</summary>
   <p>{coverage.unverifiedExcludedPollCount??coverage.excludedPollCount} סקרים הוחרגו משום שלא נמצא להם מועד איסוף מאומת.{config.includeChannel14===false?` בנוסף הוחרגו ${coverage.channel14ExcludedPollCount??7} סקרי ערוץ 14 לפי המתג.`:''} הסקרים נשמרים במאגר הכללי; מועד איסוף שלא אומת אינו מעיד בהכרח שאיסופם קדם לסגירת הרשימות.</p>
   <p>המבחן הראשי בדק את כל {numberLabel(report.methodology.permutations,0)} צירופי הפרמוטציות האפשריים. בדיקת הרגישות בדקה {report.methodology.signPatterns} היפוכי כיוון של סדרות שלמות. שתי הבדיקות מניחות תנאים לגבי התפלגות הטעויות ועצמאות בין סדרות; טעויות משותפות או תלויות בזמן עלולות לפגוע בכיול המובהקות.</p>
   <p>המגמה חושבה מכל הדלתות תוך התחשבות בכך שדלתות סמוכות חולקות סקר. תאריכי האמצע של טווחי האיסוף משמשים כציר הזמן. עיגול ואחוז החסימה יכולים ליצור קפיצות במנדטים — במיוחד מאפס לארבעה — גם כשהשינוי באחוז התמיכה קטן.</p>
   <div className="vpt-weights">{report.weights.map(item=><span key={item.pollsterId}>{item.label}: <bdi>{numberLabel(100*item.weight,2)}%</bdi></span>)}</div>
   <div className="pt-table-scroll" tabIndex={0} role="region" aria-label="הסקרים שנבדקו לצורך חלון האיסוף"><table className="pt-table vpt-cohort"><thead><tr><th>סדרה</th><th>פרסום</th><th>תחילת איסוף</th><th>סיום איסוף</th><th>הכללה</th><th>מקור</th></tr></thead><tbody>{(queries[pollsId]?.rows??[]).map(poll=><tr key={poll.pollId}><th scope="row">{report.weights.find(w=>w.pollsterId===poll.pollsterId)?.label??(poll.pollsterId==='next_data'?'ערוץ 14 / NEXT DATA':poll.pollsterId==='maagar_mochot'?'ערוץ 16 / מאגר מוחות':poll.pollsterId)}</th><td>{dateLabel(poll.publicationDate)}</td><td>{poll.fieldworkStart?dateLabel(poll.fieldworkStart):'לא אומת'}</td><td>{poll.fieldworkEnd?dateLabel(poll.fieldworkEnd):'לא אומת'}</td><td>{poll.eligibleStrict?'נכלל':poll.channel14Excluded?'הוחרג לפי מתג ערוץ 14':'הוחרג'}</td><td>{poll.sourceUrls?.[0]?<a href={poll.sourceUrls[0]} target="_blank" rel="noreferrer">מקור הסקר</a>:'—'}</td></tr>)}</tbody></table></div>
  </details>
 </section>;
}
