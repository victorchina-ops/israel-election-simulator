import React from 'react';
import './mean-seats.css';
const number=(v,d)=>Number(v).toLocaleString('he-IL',{minimumFractionDigits:d,maximumFractionDigits:d});
export function MeanSeats({stats,iterations,statId,className=''}){
 const mean=stats?.mean,margin=stats?.meanMargin,ci=stats?.meanCI;
 if(!Number.isFinite(mean))return <span className={className}>—</span>;
 const repeated=iterations>1,valid=repeated&&Number.isFinite(margin)&&Array.isArray(ci)&&ci.every(Number.isFinite);
 const digits=valid&&margin>0&&margin<.005?Math.min(6,Math.max(3,Math.ceil(-Math.log10(margin))+1)):2;
 const hint=valid?'רווח סמך 95% לתוחלת: '+number(ci[0],digits)+' עד '+number(ci[1],digits)+' מנדטים. שגיאת אמידה מההרצות בלבד.':repeated?'רווח סמך אינו זמין':'הרצה אחת — ללא רווח סמך';
 return <bdi dir="ltr" className={'mean-seats '+className} title={hint} data-summary-stat={statId} data-mean={mean} data-half-width={valid?margin:undefined} data-ci-low={valid?ci[0]:undefined} data-ci-high={valid?ci[1]:undefined}>
  {number(mean,repeated?2:0)}{valid&&<span className="mean-seats__margin"> ± {number(margin,digits)}</span>}
 </bdi>;
}
