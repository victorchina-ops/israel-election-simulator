import {combineForecast} from './model/forecast.js';

export const COMPARISON_METHODS=[
 {id:'robust',name:'השקלול השמרני שלנו',qualifier:'המיזוג שלנו',description:'חציון משוקלל של משקלי השיטות שנבחרו, נרמול ושילוב עם בסיס שווה לסקרים. מכפילים ידניים מוחלים בסוף. זו שיטת המיזוג שלנו, ולא סקר נוסף או שיטה שהוכחה כמדויקת יותר.'},
 {id:'reference',name:'מדד 120',qualifier:'משקלי בסיס שפורסמו',description:'משקלי הבסיס של שמונת המקורות. התאמות נוספות של הפרויקט אינן משוחזרות; בפרט, השכבה המיוחדת לרשימות הערביות אינה מיושמת, משום שחלוקת יתרת המשקל לא פורסמה במלואה.'},
 {id:'gilead',name:'מיכאל גלעד',qualifier:'תרחיש 50%',description:'50% למכון היעד ו־50% ליתר הסוקרים, לפני מכפילים ידניים. שיוך ההצעה לדיירקט פולס או ל־NEXT DATA כיום הוא הנחת תרחיש, ולא העברה מוכחת של הדיוק ההיסטורי.'},
 {id:'littlepolls',name:'מואיז הקטן',qualifier:'ציוני סוקרים שפורסמו',description:'ציוני הסוקרים מוחלים על מאגר הסקרים שלנו ומנורמלים ל־100%. חלון הזמן, הצבירה השבועית ותמהיל הסקרים בפרויקט המקורי אינם משוחזרים במלואם.'},
 {id:'rosner',name:'שמואל רוזנר',qualifier:'קירוב שלנו בהשראת המדד',description:'אין במאגר נוסחת משקלים עדכנית מאומתת של המדד. הקירוב המקומי משלב דעיכת זמן, שורש גודל המדגם והפחתת חריגות; הפרמטרים המספריים הם הנחות שלנו.'}
];
export const dateLabel=value=>value?String(value).slice(0,10).split('-').reverse().join('.'):'לא ידוע';
export const numberLabel=(value,d=2)=>value==null?'—':Number(value).toLocaleString('he-IL',{maximumFractionDigits:d,minimumFractionDigits:d});
export function fieldworkLabel(poll){
 const a=poll.fieldworkStart,b=poll.fieldworkEnd;
 if(a&&b)return a===b?dateLabel(a):dateLabel(a)+'–'+dateLabel(b);
 if(b)return 'עד '+dateLabel(b)+'; התחלה לא ידועה';
 if(a)return 'מ־'+dateLabel(a)+'; סיום לא ידוע';
 return 'לא אומת';
}
export function reportedSupport(poll,id){
 const value=(poll.modelOnlyPercentageIds ?? []).includes(id)?null:poll.reportedPercentages?.[id] ?? poll.percentages?.[id];
 if(value!=null)return {value,label:numberLabel(value,2)+'%',kind:'reported'};
 const bounds=poll.publishedBounds?.[id];
 if(bounds?.max!=null&&bounds.maxExclusive)return {value:null,label:'פחות מ־'+numberLabel(bounds.max,0)+'%',kind:'bound'};
 return {value:null,label:'—',kind:'missing'};
}
export function methodComparisons(input,config){
 return COMPARISON_METHODS.map(method=>({method,combined:combineForecast(input,{...config,weightMode:method.id})}));
}
// Compare displayed precision so visually equal numbers are never ranked differently.
export function extremeAt(values,index,digits=2){
 if(values.some(v=>!Number.isFinite(v)))return null;
 const rounded=values.map(v=>Number(v.toFixed(digits))),lo=Math.min(...rounded),hi=Math.max(...rounded);
 if(lo===hi)return null;
 return rounded[index]===hi?'max':rounded[index]===lo?'min':null;
}
export function downloadRows(filename,rows){
 const columns=[...new Set(rows.flatMap(row=>Object.keys(row)))];
 const cell=value=>'"'+String(value??'').replaceAll('"','""')+'"';
 const body='\uFEFF'+[columns.map(cell).join(','),...rows.map(row=>columns.map(k=>cell(row[k])).join(','))].join('\r\n');
 const url=URL.createObjectURL(new Blob([body],{type:'text/csv;charset=utf-8'})),link=document.createElement('a');
 link.href=url;link.download=filename;link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
}
