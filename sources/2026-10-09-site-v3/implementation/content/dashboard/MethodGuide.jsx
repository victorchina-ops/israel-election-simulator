import React,{useMemo} from 'react';
import {Button,DataComponent,useDataApp} from '../../data-app-public.jsx';
import {selectActivePolls} from './model/weights.js';
import {dateLabel,fieldworkLabel} from './transparency-data.js';
import portrait from '../assets/victor-rina-ben-david.jpg';
import './method-guide.css';

const METHOD_NAMES={equal:'משקל שווה',quality:'דיוק היסטורי',reference:'מדד 120',littlepolls:'מואיז הקטן',rosner:'קירוב בהשראת המדד',gilead:'תרחיש מיכאל גלעד',ensemble:'שילוב שיטות',robust:'שקלול שמרני',correlation:'מכפיל ותיקים — תרחיש ישן'};
const credits=[
 {name:'מדד 120',url:'https://madad120.co.il/',role:'משקלי מקורות שפורסמו והסבר שיטת הפרויקט.'},
 {name:'מואיז הקטן — LittlePolls',url:'https://littlepolls.com/#/method',role:'איסוף סקרים, ציוני סוקרים וניתוח הדיוק ההיסטורי.'},
 {name:'המדד — שמואל רוזנר',url:'https://themadad.com/polls26/',role:'מאגר סקרים ועקרונות שקלול. השיטה כאן היא קירוב שלנו, לא שחזור מלא.'},
 {name:'מיכאל גלעד',url:'https://x.com/Michael_Gilead/status/2083925571101217253',role:'דיון בטעויות סקרים ובתרחישי משקל לסוקרים.'},
 {name:'IsraelPolls',url:'https://x.com/IsraelPolls?s=20',role:'גילוי סקרים, גרפיקות וטבלאות היסטוריות; אימות מול המקור הראשוני כשזמין.'},
];
const sourceLink=poll=>poll.sourceUrls?.[0]??poll.sourceUrl??poll.sampleSizeSourceUrl??null;
function Evidence({id,title,queries,ids,rows,children}){
 const available=ids.filter(key=>queries[key]),primary=available[0];
 if(!primary)return <section className="mg-section"><h3>{title}</h3>{children}</section>;
 return <DataComponent id={id} title={title} kind="custom" variant="card" queryId={primary} queryIds={available} sourceRows={queries[primary].rows} sourceRowsByQuery={Object.fromEntries(available.map(key=>[key,queries[key].rows]))} displayRows={rows}>{children}</DataComponent>;
}
export function MethodGuide({input,config,onOpenPollData,onOpenTrends}){
 const {queries}=useDataApp();
 const current=input.current.polls??[],history=input.history?.polls??[];
 const active=useMemo(()=>{try{return selectActivePolls(current,config);}catch{return [];}},[current,config]);
 const activeIds=new Set(active.map(poll=>poll.id));
 const strictId=config.includeChannel14===false?'verified_party_trends_without_channel14_metadata':'verified_party_trends_metadata';
 const strict=queries[strictId]?.rows?.[0],coverage=strict?.coverage;
 const dates=active.map(poll=>poll.date).filter(Boolean).sort();
 const historicalElections=[...new Set([...(input.calibration?.history?.trainElections??[]),input.calibration?.history?.holdoutElection].filter(Boolean))];
 const missingSizes=active.filter(poll=>poll.sampleSize==null).length;
 const currentRows=current.map(poll=>({סקר:poll.publisher,סוקר:poll.pollster,פרסום:poll.date,איסוף:fieldworkLabel(poll),מדגם:poll.sampleSize??null,משתתף:activeIds.has(poll.id),מקור:sourceLink(poll)}));
 const summaryRows=[{תאריך:input.current.asOf,'סקרים עדכניים במאגר':current.length,'סקרים נבחרים':active.length,'סקרים היסטוריים':history.length,'שיטת שקלול':METHOD_NAMES[config.weightMode]??config.weightMode,'ערוץ 14':config.includeChannel14===false?'מוחרג':'כלול','דמיון בין סקרים':config.pollCorrelationEnabled===true?'מופעל':'כבוי','סקרים בניתוח המובהקות השמור':coverage?.pollCount??null}];
 const steps=[
  {title:'אוספים תוצאות שפורסמו',text:'לשקלול העדכני לוקחים את הסקר האחרון מכל מכון שנבחר. הסקרים הישנים נשמרים לחקר המגמות.',detail:'שומרים בנפרד את תאריך הפרסום ואת מועדי האיסוף, וגם גודל מדגם, שיטה וקישור למקור כשפורסמו. פרסום חוזר של אותו סקר אינו סקר נוסף.'},
  {title:'משקללים את הסקרים',text:'ברירת המחדל היא דיוק היסטורי: מכונים נבדלים במשקלם לפי בדיקות של תחזיות קודמות.',detail:`נתוני הכיול כוללים ${historicalElections.length?historicalElections.join(', '):'מערכות בחירות קודמות'}. הציונים ממתנים הבדלים כשהראיות מעטות. אפשר לבחור משקל שווה, גישה אחרת או מכפילים ידניים. הצלחה בעבר אינה מבטיחה דיוק בבחירות הבאות.`},
  {title:'משנים השתתפות ומדמים טעות',text:'אחוזי הצבעה ומוטיבציה משנים את התרחיש. הרצות רבות מציגות גם תוצאות שונות שאפשר לקבל סביבו.',detail:'בסיס ההשתתפות מגיע מבחירות 2022 ומסיווגי יישובים. זהו בסיס גאוגרפי ולא מדידה אישית של דת או לאום. טעות סקרים, עיגול ופערים בין מכונים הם חלק מהנחות הסימולציה; שינוי מוטיבציה הוא תרחיש, לא ממצא מסקר.'},
  {title:'בודקים את אחוז החסימה',text:'בכל הרצה נבדק מי מגיע ל־3.25% מהקולות התקפים. קולות לרשימה שלא עוברת אינם מקבלים מנדטים.',detail:'קפיצה מאפס לארבעה מנדטים יכולה לנבוע מתזוזה קטנה סביב החסימה. סיכוי מעבר של 60% פירושו שהרשימה עברה ב־60% מהרצות המודל באותן הנחות; זה אינו אחוז התמיכה בה.'},
  {title:'מחלקים 120 מנדטים',text:'באדר–עופר והסכמי העודפים מחלקים את המנדטים. מסכמים את הסיכוי של הגושים שנבחרו להגיע ל־61.',detail:'כל הרצה מסתכמת ב־120 מנדטים. מפלגה משויכת לכל היותר לגוש אחד; אפשר להשאיר רשימות ללא שיוך. רוב של 61 הוא אפשרות חשבונית לפי ההרכב שבחרתם, ולא תחזית למשא ומתן או לזהות הממשלה.'},
 ];
 return <section className="method-guide" aria-labelledby="method-guide-title">
  <div className="mg-heading"><div><h2 id="method-guide-title">מהסקר לתרחיש הבחירות</h2><p>מה הנתונים אומרים, מה המודל מוסיף, ואיך לקרוא את התוצאה.</p></div><span className="mg-version">גרסה 3</span></div>
  <Evidence id="method-guide-coverage" title="אילו נתונים נכנסים כרגע?" queries={queries} ids={['polls','poll_history','model_input',strictId]} rows={summaryRows}>
   <div className="mg-facts" data-reviewed-rows><div><strong><bdi dir="ltr">{active.length}<small> / {current.length}</small></bdi></strong><span>סקרים עדכניים נבחרים</span></div><div><strong>{history.length}</strong><span>סקרים בארכיון המגמות</span></div><div><strong>{coverage?.pollCount??'—'}</strong><span>סקרים בניתוח המובהקות השמור</span></div><div><strong><bdi dir="ltr">{dateLabel(input.current.asOf)}</bdi></strong><span>תאריך עדכון המאגר</span></div></div>
   <p className="mg-note">השקלול העדכני: <strong>{METHOD_NAMES[config.weightMode]??config.weightMode}</strong> · ערוץ 14 {config.includeChannel14===false?'מוחרג':'כלול'} · דמיון בין סקרים {config.pollCorrelationEnabled===true?'מופעל':'כבוי'}.</p>
   <p className="mg-note">{dates.length?`מועדי הפרסום של הסקרים הנבחרים: ${dateLabel(dates[0])}–${dateLabel(dates.at(-1))}. `:''}ניתוח המובהקות הוא ניתוח שמור ונפרד; בחירה במשקלים או מכפילים אחרים אינה מחשבת מחדש את ערכי המובהקות שלו.</p>
   <div className="mg-actions">{onOpenPollData&&<Button onClick={onOpenPollData}>פתיחת הסקרים והמקורות</Button>}{onOpenTrends&&<Button onClick={onOpenTrends}>למגמות ולבדיקות המובהקות</Button>}</div>
  </Evidence>
  <Evidence id="method-guide-pipeline" title="איך נבנית התוצאה?" queries={queries} ids={['model_input','calibration','turnout_baseline','agreements']} rows={summaryRows}>
   <ol className="mg-pipeline">{steps.map((step,index)=><li key={step.title}><span className="mg-step-number" aria-hidden="true">{index+1}</span><h3>{step.title}</h3><p>{step.text}</p><details><summary>עוד על השלב הזה</summary><p>{step.detail}</p></details></li>)}</ol>
  </Evidence>
  <div className="mg-reading-grid">
   <Evidence id="method-guide-interpretation" title="שלושה מספרים, שלוש משמעויות" queries={queries} ids={['polls','model_input','simulation_results']} rows={[{סוג:'מנדטים שפורסמו',הגדרה:'תוצאת הסקר המקורי'},{סוג:'תמיכה ששוחזרה',הגדרה:'אומדן מקומי לצורך הסימולציה'},{סוג:'סיכוי במודל',הגדרה:'שיעור ההרצות שבהן התרחש אירוע'}]}>
    <dl className="mg-definitions"><div><dt>מנדטים שפורסמו</dt><dd>מה שהסקר המקורי הציג. זהו הבסיס להשוואת המגמות.</dd></div><div><dt>אחוזי תמיכה ששוחזרו</dt><dd>כשפורסמו רק מנדטים, המודל משחזר מהם תמיכה לצורך החישוב. אלה אינם אחוזים שנמדדו בסקר.</dd></div><div><dt>סיכוי במודל</dt><dd>כמה מהרצות הסימולציה הסתיימו במעבר החסימה או ברוב. הוא תלוי בנתונים ובהנחות שבחרתם.</dd></div></dl>
    <details className="mg-detail"><summary>מה אומר הטווח ליד התחזית?</summary><p>טווח תוצאות הבחירות מציג את הפיזור בין ההרצות. רווח הסמך ליד ממוצע או הסתברות מתאר את שגיאת האמידה מהמספר הסופי של ההרצות; הוא אינו כולל את כל טעויות המודל. ממוצע מדויק של ההרצות עדיין יכול להיות תחזית שגויה.</p></details>
   </Evidence>
   <Evidence id="method-guide-trend-tests" title="רואים שינוי — האם הוא מובהק?" queries={queries} ids={[strictId,'poll_history']} rows={coverage?[{...coverage,מבחן:strict.methodology?.kind,תיקון:strict.methodology?.multipleTesting}]:[]}>
    <p>בודקים את <strong>השינוי בתוך כל סדרת סקרים</strong>, ביחס לתחילת אותה סדרה. לכן מכון שנותן מלכתחילה יותר מנדטים אינו יוצר בעצמו מגמת עלייה.</p>
    <dl className="mg-definitions"><div><dt>המבחן הראשי</dt><dd>מערבבים את סדר התוצאות בזמן בתוך כל מכון, ומשווים את המגמה המשוקללת לרצפים שאפשר לקבל בלי קשר לזמן.</dd></div><div><dt>תיקון לריבוי בדיקות</dt><dd>כשבודקים מפלגות רבות, חלק מהאותות עשויים לצוץ במקרה. תיקון BH מצמצם הכרזות שווא בין הממצאים שמסומנים כמובהקים.</dd></div><div><dt>בדיקת רגישות לפי סוקרים</dt><dd>מחליפים את כיוון השינוי של סדרות שלמות, ולא של סקרים בודדים. כך בודקים אם הראיות נשארות חזקות כשכל מכון נחשב יחידה אחת.</dd></div></dl>
    <details className="mg-detail"><summary>למה שתי הבדיקות יכולות לתת תשובה שונה?</summary><p>הן בודקות את הראיות תחת הנחות שונות. תוצאה מובהקת במבחן הראשי ולא ברגישות היא אות שתלוי יותר באופן הטיפול במדידות בתוך כל מכון; היא מחייבת זהירות לגבי יציבות המגמה. אי־מובהקות אינה הוכחה שאין שינוי או שהשינויים אקראיים.</p><p>המבחנים מניחים תנאים לגבי התנהגות הטעויות ועצמאות בין סדרות. סדרות קצרות, עיגול למנדטים ואחוז החסימה מגבילים את כוח הבדיקה. ערך p אינו ההסתברות שהמגמה שגויה.</p></details>
    {coverage&&<p className="mg-note" data-reviewed-rows>התקופה המאומתת: {dateLabel(coverage.from)}–{dateLabel(coverage.to)} · {coverage.seriesCount} סדרות · {coverage.deltaCount} שינויים עוקבים. מועדי איסוף שלא אומתו אינם נכללים.</p>}
   </Evidence>
  </div>
  <details className="mg-disclosure"><summary>מה אפשר לשנות, ומה נשאר הנחה?</summary><div className="mg-disclosure-body"><ul><li><strong>אחוזי הצבעה ומוטיבציה:</strong> בודקים תרחישי השתתפות שונים; אין כאן תחזית עצמאית למי יגיע לקלפי.</li><li><strong>הרכב הגושים:</strong> מעבירים מפלגה בין קואליציה, אופוזיציה וללא שיוך. הסיכוי ל־61 מתייחס להרכב שנבחר.</li><li><strong>סקרים ושקלול:</strong> בוחרים שיטת משקל, סקרים ומכפילים. שינוי משקלים אינו מוסיף נשאלים.</li><li><strong>דמיון בין סקרים:</strong> מתג ניסיוני שממתן את המשקל והביטחון של תחזיות דומות בסדרות הנוכחיות. דמיון אינו הוכחה לחפיפת משיבים או לטעויות משותפות.</li><li><strong>ערוץ 14:</strong> כבוי בברירת המחדל. ההפעלה כוללת את סקריו וגם בוחרת גרסת מגמות מאומתת שחושבה בנפרד.</li><li><strong>אי־ודאות:</strong> טעות משותפת, פיזור בין מכונים ועיגול הם הנחות גלויות שאפשר לבחון בהגדרות המתקדמות.</li></ul><p>נתון שלא פורסם נשאר חסר, ולא מוצג כאפס. {missingSizes?`ל־${missingSizes} מהסקרים הנבחרים אין גודל מדגם מתועד; לחישובי אי־ודאות משתמשים ב־500 כהנחה.`:'גדלי המדגם המתועדים מוצגים ליד הסקרים; כאשר נתון חסר במקור, הנחת השלמה מסומנת בנפרד.'}</p></div></details>
  <details className="mg-disclosure"><summary>הסקרים הנבחרים, מועדי האיסוף והמקורות</summary><Evidence id="method-guide-source-register" title="מקורות השקלול העדכני" queries={queries} ids={['polls','model_input']} rows={currentRows}><ul className="mg-sources" data-reviewed-rows>{current.map(poll=><li key={poll.id}><div><strong>{poll.publisher}</strong><span>{poll.pollster}</span></div><div><span>פרסום: {dateLabel(poll.date)}</span><span>איסוף: {fieldworkLabel(poll)}</span></div><div><span>מדגם: {poll.sampleSize??'לא פורסם'}</span><span>{activeIds.has(poll.id)?'נבחר לשקלול':'מוחרג מהשקלול הנוכחי'}</span></div>{sourceLink(poll)&&<a href={sourceLink(poll)} target="_blank" rel="noreferrer">מקור הסקר ↗</a>}</li>)}</ul></Evidence></details>
  <details className="mg-disclosure"><summary>מי בנה את האתר, וממי למדנו?</summary><div className="mg-disclosure-body"><div className="mg-author"><img src={portrait} alt="ויקטור רינה בן דוד" width="72" height="72" decoding="async"/><div><strong>ויקטור רינה בן דוד</strong><span>בניית הסימולטור והעיבוד המקומי</span><a href="mailto:victor.china@gmail.com"><bdi>victor.china@gmail.com</bdi></a></div></div><ul className="mg-credits">{credits.map(source=><li key={source.url}><a href={source.url} target="_blank" rel="noreferrer">{source.name} ↗</a><span>{source.role}</span></li>)}</ul><p>תודה למכוני הסקרים ולמפרסמים. בסיס ההשתתפות מבוסס על <a href="https://media25.bechirot.gov.il/files/expc.csv" target="_blank" rel="noreferrer">ועדת הבחירות המרכזית</a>, סיווגי <a href="https://www.cbs.gov.il/he/publications/doclib/2019/ishuvim/bycode2022.xlsx" target="_blank" rel="noreferrer">הלמ״ס</a> והצלבה עם <a href="https://www.idi.org.il/articles/46440" target="_blank" rel="noreferrer">המכון הישראלי לדמוקרטיה</a>.</p><p>ניסוי ״אות ורעש״ הקודם, שאינו פעיל בגרסה 2, נבנה בהשראת <a href="https://twonetwenty.com/he/articles/he-about-to-120" target="_blank" rel="noreferrer">To120 של אריאל דניאלי</a>. התיעוד והקרדיט נשמרים בארכיון; היישום שלנו היה התאמה מקומית ולא השיטה המקורית.</p><p>משתמשים בתוצאות או בתרשימים? תנו קרדיט ליוצר ולמקורות הנתונים וצרפו <a href="https://victorchina-ops.github.io/israel-election-simulator/" target="_blank" rel="noreferrer">קישור לסימולטור</a>.</p></div></details>
 </section>;
}
