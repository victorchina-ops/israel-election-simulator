import React from 'react';
import {DataComponent,Dropdown,useDataApp} from '../../data-app-public.jsx';
import './sampling-mode.css';

export const SAMPLING_MODE_LABELS={
  fixed:'אם הסקרים מדויקים',
  poll:'כולל אפשרות לטעות בסקרים'
};

const MODE_EXPLANATIONS={
  fixed:'התמיכה המשוקללת בכל מפלגה נשארת קבועה בין ההרצות. רק ההצבעה עצמה אקראית; במיליוני קולות, התוצאות נוטות להיות כמעט זהות.',
  poll:'גם התמיכה בכל מפלגה יכולה להשתנות בין ההרצות, לפי ההנחות על טעויות בסקרים והטיות שמשותפות להם. סיכויי המודל תלויים בהנחות האלה.'
};

/** onChange receives a config patch: {samplingMode: 'fixed' | 'poll'}. */
export function SamplingModeControl({config,onChange,compact=false}){
  const {queries}=useDataApp();
  const mode=config?.samplingMode==='poll'?'poll':'fixed';
  const iterations=Number.isInteger(config?.iterations)&&config.iterations>0?config.iterations:1000;
  const id=compact?'threshold-sampling-mode':'e-sampling-mode';
  const displayRows=Object.entries({...config,samplingMode:mode,iterations}).map(([parameter,value])=>({
    parameter,value:value!==null&&typeof value==='object'?JSON.stringify(value):value
  }));
  const context=iterations===1
    ?'נבחרה מערכת בחירות אחת. כדי לאמוד סיכויים צריך לחזור על ההדמיה.'
    :'בשני המצבים מדמים '+iterations.toLocaleString('he-IL')+' מערכות בחירות.';
  const description='הגדרות התרחיש הנבחרות; שינוי מצב הדגימה משמר את יתר ההגדרות. fixed משאיר את התמיכה קבועה; poll מאפשר גם שונות בתמיכה לפי הנחות המודל. מספר החזרות מתאר דיוק חישובי ואינו מוסיף מדידות סקר. הגדרות נוכחיות: '+JSON.stringify({...config,samplingMode:mode,iterations});
  return <DataComponent id={id} title="איך להתייחס לסקרים?" kind="custom" variant={compact?'plain':'card'}
    className={'sampling-mode'+(compact?' sampling-mode--compact':'')} queryId="model_configuration"
    sourceRows={queries.model_configuration.rows} displayRows={displayRows} description={description}
  >
    <div className="sampling-mode__content" dir="rtl" data-reviewed-rows>
      <div className="sampling-mode__selector">
        <Dropdown triggerClassName="filter-trigger e-content-select" contentClassName="election-select-menu" label="מצב הסימולציה" showLabel value={mode}
          choices={['fixed','poll']} choiceLabels={SAMPLING_MODE_LABELS}
          onChange={samplingMode=>{
            if(samplingMode==='fixed'||samplingMode==='poll')onChange?.({samplingMode});
          }}/>
      </div>
      <p className="sampling-mode__explanation" role="status" aria-live="polite">{MODE_EXPLANATIONS[mode]}</p>
      <p className="sampling-mode__shared">{context} בכל הרצה דוגמים פתק לכל מצביע ומחשבים מחדש את אחוז החסימה ואת חלוקת המנדטים לפי באדר–עופר והסכמי העודפים.</p>
      <details className="sampling-mode__details">
        <summary>מה ההבדל? דוגמה</summary>
        <div className="sampling-mode__details-body">
          <p>דוגמה להמחשה בלבד: מפלגה שהתמיכה בה במודל היא <bdi>3.3%</bdi>, מעט מעל אחוז החסימה של <bdi>3.25%</bdi>.</p>
          <dl className="sampling-mode__example">
            <div><dt>{SAMPLING_MODE_LABELS.fixed}</dt><dd>התמיכה נשארת <bdi>3.3%</bdi>; שיעור הקולות שנדגם יהיה קרוב מאוד לכך בכל הרצה.</dd></div>
            <div><dt>{SAMPLING_MODE_LABELS.poll}</dt><dd>התמיכה יכולה לרדת מתחת ל־<bdi>3.25%</bdi> בחלק מההרצות, בהתאם להנחות על טעויות הסקרים.</dd></div>
          </dl>
          <p className="sampling-mode__precision">טווח 95% שמוצג ליד סיכוי מתאר את שגיאת ההרצה בגלל מספר החזרות המוגבל (מונטה קרלו). הוא אינו טווח לטעות של הסקרים. גם 1,000 חזרות אינן מוסיפות מידע מסקר חדש; הן חוזרות על אותן הנחות. סיכויי המודל טרם אומתו כתחזית הסתברותית.</p>
        </div>
      </details>
    </div>
  </DataComponent>;
}

export default SamplingModeControl;
