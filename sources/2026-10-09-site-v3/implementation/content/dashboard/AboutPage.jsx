import React from 'react';
import {Button} from '../../data-app-public.jsx';
import portrait from '../assets/victor-rina-ben-david.jpg';
import './about-page.css';

// The author, portrait, contact and original explanatory passages are restored
// from the published pre-Version-2 SimulatorIntro, rather than invented biography.
const credits=[
 {name:'מדד 120',url:'https://madad120.co.il/',role:'ריכוז ועיבוד הסקרים, פרסום משקלי המקורות והסבר המתודולוגיה.'},
 {name:'מואיז הקטן — LittlePolls',url:'https://littlepolls.com/#/method',role:'איסוף סקרים, דירוג הסוקרים וניתוח הדיוק ההיסטורי.'},
 {name:'המדד — שמואל רוזנר',url:'https://themadad.com/polls26/',role:'מאגר סקרים וניתוחי מגמות. גישת השקלול באתר זה היא קירוב שלנו בהשראת המדד.'},
 {name:'מיכאל גלעד',url:'https://x.com/Michael_Gilead/status/2083925571101217253',role:'ניתוח טעויות הסקרים והדיון בשקלול סוקרים בעלי טעויות מתואמות.'},
 {name:'IsraelPolls',url:'https://x.com/IsraelPolls?s=20',role:'גילוי סקרים, גרפיקות וטבלאות היסטוריות; אימות מול המקור הראשוני כשזמין.'},
];
const SourceLink=({href,children})=><a href={href} target="_blank" rel="noopener noreferrer">{children}</a>;

export function AboutPage({asOf,updateNote,onStart,onOpenPollData,onOpenGuide}){
 const formattedAsOf=String(asOf||'').replace(/^(\d{4})-(\d{2})-(\d{2})(?:T.*)?$/, '$3.$2.$1');
 return <section className="about-page" aria-labelledby="about-page-title" data-about-page>
  <div className="about-hero">
   <div className="about-hero-copy"><p className="about-eyebrow">סקרים ושקרים · סימולטור בחירות פתוח</p><h1 id="about-page-title">מה יכול להשתנות בדרך ל־120?</h1><p className="about-hero-lead">הסקרים הם נקודת ההתחלה. כאן אפשר לשנות השתתפות, לבחור מי בכל גוש ולהשוות בין שיטות שקלול — ולראות מה קורה בתרחיש שבחרתם.</p>
    {asOf&&<p className="about-freshness"><span className="about-freshness-dot" aria-hidden="true"/>נתוני הסקרים מעודכנים ל־<time dateTime={asOf}><bdi dir="ltr">{formattedAsOf}</bdi></time></p>}
    {updateNote&&<p className="about-update-note">{updateNote}</p>}
    <div className="about-actions"><Button className="about-start" onClick={onStart} disabled={!onStart}>להתחיל בסימולציה <span aria-hidden="true">←</span></Button>{onOpenPollData&&<Button className="about-secondary" onClick={onOpenPollData}>לסקרים ולמקורות</Button>}</div>
    <p className="about-hero-limit">זה כלי לבדיקת תרחישים. סיכוי לרוב של 61 מנדטים אינו סיכוי להרכבת ממשלה.</p>
   </div>
   <div className="about-author"><img className="about-photo" src={portrait} alt="ויקטור רינה בן דוד" width="320" height="320" decoding="async"/><div className="about-author-copy"><span>נבנה על ידי</span><strong>ויקטור רינה בן דוד</strong><a href="mailto:victor.china@gmail.com" aria-label="לפרטים: victor.china@gmail.com"><bdi dir="ltr">victor.china@gmail.com</bdi></a><span>לפרטים וליצירת קשר</span></div></div>
  </div>
  <div className="about-grid" aria-label="איך משתמשים באתר?">
   <section className="about-card"><span className="about-card-number" aria-hidden="true">01</span><h3>בוחרים מה נכנס</h3><p>בחרו את הסקרים ואת שיטת השקלול. ברירת המחדל היא דיוק היסטורי, ללא ערוץ 14.</p></section>
   <section className="about-card"><span className="about-card-number" aria-hidden="true">02</span><h3>משנים את התרחיש</h3><p>התאימו אחוזי הצבעה ומוטיבציה. אפשר להעביר כל מפלגה בין הגושים, גם ישירות מתוך התוצאות.</p></section>
   <section className="about-card"><span className="about-card-number" aria-hidden="true">03</span><h3>בודקים מה מתקבל</h3><p>ראו סיכויי רוב, מעבר חסימה ופיזור מנדטים. בדף המגמות בודקים בנפרד אם השינוי בסקרים מובהק.</p></section>
  </div>
  <section className="about-explanation" aria-labelledby="about-method-title"><div><p className="about-eyebrow">ההסבר המקורי</p><h3 id="about-method-title">איך עובדת הסימולציה?</h3></div><p>משקללים את נתוני הסקרים ומתרגמים אותם להסתברויות הצבעה. בכל הרצה מדמים הצבעה עם טעות סקרים, בודקים מי עובר את אחוז החסימה ומחלקים 120 מנדטים לפי באדר–עופר והסכמי העודפים שהוגדרו. מהחזרות מחשבים ממוצע וחציון מנדטים, פיזור תוצאות וסיכוי של כל גוש להגיע ל־61. ברירת המחדל היא 10,000 הרצות.</p><p>השקלול השמרני והסימולציה הם עיבוד שלנו, ואינם שחזור מלא של תחזיות המקורות. הסיכויים מתייחסים לרוב של 61 מנדטים לפי ההנחות שנבחרו; הם אינם אומדים את המשא ומתן להרכבת ממשלה.</p>{onOpenGuide&&<Button className="about-secondary" onClick={onOpenGuide}>איך השיטות עובדות ומה המגבלות?</Button>}</section>
  <section className="about-credits" aria-labelledby="about-credits-title"><h3 id="about-credits-title">מקורות וקרדיטים</h3><p>תודה ליוצרי המקורות על עבודתם באיסוף, בעיבוד ובניתוח הנתונים שעליהם נשען הסימולטור:</p><ul className="about-credit-grid">{credits.map(source=><li key={source.url}><SourceLink href={source.url}>{source.name} ↗</SourceLink><span>{source.role}</span></li>)}</ul><p>תודה גם למכוני הסקרים ולגופי התקשורת על ביצוע הסקרים ופרסומם. הקישורים לכל סקר ותאריכי הנתונים מופיעים ב־{onOpenPollData?<button type="button" className="about-text-link" onClick={onOpenPollData}>נתוני הסקרים</button>:'נתוני הסקרים'}.</p><p>בסיס ההשתתפות מחושב מנתוני בחירות 2022 של <SourceLink href="https://media25.bechirot.gov.il/files/expc.csv">ועדת הבחירות המרכזית</SourceLink> ומסיווגי היישובים של <SourceLink href="https://www.cbs.gov.il/he/publications/doclib/2019/ishuvim/bycode2022.xlsx">הלמ״ס</SourceLink>, והוצלב עם ניתוחי <SourceLink href="https://www.idi.org.il/articles/46440">המכון הישראלי לדמוקרטיה</SourceLink>.</p><p className="about-archive-credit">ניסוי אות ורעש הקודם, שהוסר מהאתר, נבנה בהשראת <SourceLink href="https://twonetwenty.com/he/articles/he-about-to-120">To120 של אריאל דניאלי</SourceLink>. התיעוד והקרדיט נשמרים בארכיון.</p></section>
  <p className="about-attribution">משתמשים בתוצאות או בתרשימים? אנא תנו קרדיט לויקטור רינה בן דוד ולמקורות הנתונים, וצרפו <SourceLink href="https://victorchina-ops.github.io/israel-election-simulator/">קישור לסימולטור</SourceLink>.</p>
 </section>;
}
export default AboutPage;
