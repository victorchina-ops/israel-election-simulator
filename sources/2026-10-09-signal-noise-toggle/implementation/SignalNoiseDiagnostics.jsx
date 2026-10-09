import React from 'react';
import {DataComponent,useDataApp} from '../../data-app-public.jsx';
import {SIGNAL_NOISE_CREDIT,signalNoiseBaseMethodLabel} from './signal-noise-content.js';
import './signal-noise.css';

const date=value=>value?String(value).slice(0,10).split('-').reverse().join('.'):'לא פורסם';
const num=(value,d=2)=>Number.isFinite(value)?value.toLocaleString('he-IL',{maximumFractionDigits:d}):'—';
export function SignalNoiseCredit(){return <span className="sn-credit">בהשראת <a href={SIGNAL_NOISE_CREDIT.methodology} target="_blank" rel="noreferrer">{SIGNAL_NOISE_CREDIT.name}</a> · <a href={SIGNAL_NOISE_CREDIT.explanation} target="_blank" rel="noreferrer">ההסבר על אות ורעש</a></span>;}

export function SignalNoiseDiagnostics({id='signal-noise-diagnostics',input,config={},result,compact=false}){
 const {queries}=useDataApp(),diagnostics=result?.signalNoise;
 const coverage=diagnostics?.coverage??{},parties=diagnostics?.parties??{};
 const unavailable=diagnostics?.weightingPolicy?.unavailableInstitutes??[];
 const unavailableNames=unavailable.map(id=>input?.current?.polls?.find(poll=>poll.pollsterId===id)?.publisher??id);
 const unavailableGileadTarget=config.weightMode==='gilead'&&unavailable.includes(config.gileadTarget??'direct_polls');
 const rows=Object.entries(parties).map(([partyId,row])=>({partyId,party:input?.parties?.find(p=>p.id===partyId)?.name??partyId,
  observationCount:row.count??null,estimatedSupportPercent:Number.isFinite(row.normalizedMean)?100*row.normalizedMean:null,
  latentUncertaintySDPercentagePoints:Number.isFinite(row.variance)?100*Math.sqrt(Math.max(0,row.variance)):null,
  estimationStatus:row.count===0?'explicit sensitivity assumption':row.fallback?'fixed Q/R for short series':'Q/R fitted from time series',
  signalVariancePerDay:row.qPerDay??null,noiseVariance:row.r??null,
  weightingMethod:config.weightMode??'quality',signalNoiseEnabled:config.signalNoiseEnabled===true,
  from:coverage.from??null,to:coverage.to??null,dataAsOf:input?.current?.asOf??null}));
 const ids=['signal_noise_observations','model_input','calibration','weight_presets'].filter(queryId=>queries?.[queryId]);
 const queryId=ids[0];
 if(!queryId)return null;
 return <DataComponent id={id} title="איך נקבע אומדן האות והרעש?" variant={compact?'plain':'card'} kind="custom" className="sn-diagnostics" queryId={queryId} queryIds={ids} sourceRows={queries[queryId].rows} sourceRowsByQuery={Object.fromEntries(ids.map(key=>[key,queries[key].rows]))} displayRows={[{kind:'coverage',...coverage,dataAsOf:input?.current?.asOf,weightingMethod:config.weightMode??'quality',weightingPolicy:diagnostics?.weightingPolicy??null},...rows]} description="יישום מקומי ניסיוני של מודל רמה מקומית בהשראת אריאל דניאלי ועד 120. אומדני האות והרעש נבחרים מתוך חיזוי קדימה בסדרת הסקרים המאומתת. זו אינה העתקה של קוד או תחזית האתר המקורי. ההפרדה תלויה במודל; הסתברויותיו טרם כוילו מול בחירות שלא שימשו לפיתוח.">
  <SignalNoiseCredit/>
  <p className="sn-caption">התמיכה יכולה להשתנות, וגם סקר יכול לסטות ממנה. המודל מנסה ללמוד את האיזון מתוך הסדרה: חיזוי הסקר הבא מלמד כמה להסתמך על מדידה חדשה וכמה לשמור מההיסטוריה. הוא אומד את עוצמת הרעש, ולא יודע מה תהיה הטעות בסקר מסוים.</p>
  <p className="sn-caption">שיטת השקלול ״{signalNoiseBaseMethodLabel(config)}״ קובעת את רמת האמון במכונים בתוך התאמת המודל, פעם אחת. מדידה ממכון עם יותר אמון מקבלת פחות אי־ודאות; את האומדן המסונן לא משקללים שוב. זו תוספת ניסיונית; עוד לא הוכח שהיא חוזה בחירות טוב יותר.</p>
  {unavailable.length>0&&<p className="sn-caption sn-coverage-warning" role="note" data-unavailable-institutes={unavailable.join(',')}>אין כרגע דוחות אחוזים מתאימים ל{unavailableNames.join(', ')}. המכונים האלה אינם נכנסים לאמידה; רמת האמון מנורמלת מחדש בין המכונים עם נתונים מתאימים.{unavailableGileadTarget?' לכן יעד ה־50% בתרחיש גלעד אינו מיושם כאן.':''}</p>}
  {diagnostics&&<p className="sn-coverage" data-reviewed-rows><strong>{num(coverage.observationCount,0)} סקרים · {num(coverage.instituteCount,0)} מכונים</strong><span>חלון עבודת השדה: <bdi>{date(coverage.from)}–{date(coverage.to)}</bdi> · נתונים עד {date(input?.current?.asOf)}</span></p>}
  {rows.length>0&&<details className="sn-details"><summary>פתיחה לאומדני המפלגות ולכיסוי הנתונים</summary>
   <p className="sn-caption">האומדנים כאן מנורמלים יחד ל־100%, לפני התאמות ההצבעה. בסדרה קצרה אין די מידע ללמידת האות והרעש, ולכן משתמשים בפרמטרים קבועים ומוצהרים. מעט נתונים והבדלים בין מכונים מגבילים את ההפרדה בין שינוי אמיתי לרעש.</p>
   <p className="sn-caption">אי־הוודאות נאמדת לכל מפלגה בנפרד; המודל אינו לומד את כל הקשרים בין מפלגות. לכן סיכויי רוב ומעבר חסימה עדיין ניסיוניים. אומדן של מעט שינוי אינו מבחן מובהקות ואינו מוכיח שאין שינוי.</p>
   <div className="sn-table-scroll" tabIndex={0} role="region" aria-label="אומדני מודל האות והרעש"><table className="sn-table" data-reviewed-rows><thead><tr><th>מפלגה</th><th>מדידות זמינות</th><th>אומדן תמיכה</th><th>בסיס האמידה</th></tr></thead><tbody>{rows.filter(row=>input?.parties?.find(p=>p.id===row.partyId)?.ballot!==false).map(row=><tr key={row.partyId}><th scope="row">{row.party}</th><td>{num(row.observationCount,0)}</td><td>{num(row.estimatedSupportPercent)}%</td><td>{row.observationCount===0?'הנחת רגישות':parties[row.partyId].fallback?'פרמטרי אות ורעש קבועים':'למידה מסדרת הזמן'}</td></tr>)}</tbody></table></div>
   <p className="sn-caption">מודל זה משתמש באחוזים מקוריים עם בסיס אחוזים תואם ומתועד, ללא שחזור ממנדטים. בחלק מהדוחות בסיס האחוזים מוסק ממבנה הטבלה. חסר אינו אפס תמיכה. אם אין נתון למפלגה, נדרשת הנחת רגישות מפורשת עם מקור. המקורות, אי־הוודאות והפרמטרים המלאים זמינים בבדיקת מקור הנתונים של הכרטיס.</p>
  </details>}
 </DataComponent>;
}
