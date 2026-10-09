import React from 'react';
import './simulator-intro.css';
export function SimulatorIntro({onOpenPollData,onOpenGuide,asOf}){
 const formattedAsOf=String(asOf||'').replace(/^(\d{4})-(\d{2})-(\d{2})(?:T.*)?$/, '$3.$2.$1');
 return <section className="sim-intro" aria-labelledby="sim-intro-title" data-simulator-intro>
  <div className="sim-intro__overview"><p id="sim-intro-title"><strong>נתונים מעודכנים</strong>{asOf&&<> · <time dateTime={asOf}><bdi dir="ltr">{formattedAsOf}</bdi></time></>}</p>
  <nav className="sim-intro__projects" aria-label="עזרה ומקורות"><button type="button" className="sim-intro__text-button" onClick={onOpenPollData}>הסקרים והמקורות</button>{onOpenGuide&&<button type="button" className="sim-intro__text-button" onClick={onOpenGuide}>איך המודל עובד?</button>}</nav></div>
 </section>;
}
