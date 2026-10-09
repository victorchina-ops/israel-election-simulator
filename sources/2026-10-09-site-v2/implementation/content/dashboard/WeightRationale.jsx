import React from "react";
import {DataComponent,useDataApp} from "../../data-app-public.jsx";
import "./weight-rationale.css";
export function WeightRationale(){
 const {queries,visible}=useDataApp(),query=queries.weight_rationale;
 if(!query||(typeof visible==="function"&&!visible("weight-rationale-evidence")))return null;
 return <section id="weight-rationale" className="weight-rationale">
  <DataComponent id="weight-rationale-evidence" title="למה לתת לסקרים משקלים שונים?" kind="custom" variant="card" queryId="weight_rationale" sourceRows={query.rows} displayRows={query.rows}>
   <p>ברירת המחדל היא דיוק היסטורי: נותנים למכונים משקל לפי ביצועי תחזיותיהם בעבר, תוך מיתון הבדלים כשהראיות מעטות. אפשר לבחור בסיס שווה או גישה אחרת כדי לבדוק עד כמה התוצאה רגישה לבחירה. שילוב שיטות משנה את משקלם של אותם סקרים; הוא אינו מוסיף נשאלים או ראיות עצמאיות.</p>
   <div className="wr-grid" data-reviewed-rows>{query.rows.map(row=><section className="wr-method" key={row.id}>
    <h3>{row.label}</h3><p>{row.rationale}</p><details><summary>יתרונות, מגבלות והיישום אצלנו</summary><p><b>מה הוא נותן:</b> {row.strength}</p><p><b>המגבלה:</b> {row.limitation}</p><p><b>במודל הזה:</b> {row.implementation}</p></details>
    <div className="wr-links">{row.sourceUrls.map((url,i)=><a href={url} key={url} target="_blank" rel="noreferrer">מקור {i+1}</a>)}</div>
   </section>)}</div>
   <details><summary>השקלול השמרני שלנו — הסבר ונוסחה</summary><p>לכל סקר לוקחים המלצת משקל אמצעית מהשיטות שנבחרו, ואז מקרבים אותה לבסיס שווה. כך מצמצמים את השפעתה של המלצת משקל חריגה. מידת הקירוב היא פרמטר של התרחיש; זו אינה ברירת המחדל הראשית באתר.</p><p className="wr-formula" dir="ltr">robust weights = (1 − λ) × normalize(weighted median of selected method weights) + λ × uniform poll weights</p><p>החציון נלקח לכל סקר בנפרד; בשוויון של חצי המשקל נלקח ממוצע שתי ההצעות האמצעיות. לאחר השילוב מופעלים המכפילים הידניים ומנרמלים שוב. ההגנה היא מפני המלצת משקל חריגה, ולא מפני טעות משותפת לכל הסוקרים.</p><p>כדי לקבוע שהשילוב חוזה טוב יותר, צריך לבחון אותו בבחירות שלא שימשו לבחירת הפרמטרים. הבדיקות החישוביות באתר אינן מוכיחות יתרון כזה.</p></details>
  </DataComponent>
 </section>;
}
