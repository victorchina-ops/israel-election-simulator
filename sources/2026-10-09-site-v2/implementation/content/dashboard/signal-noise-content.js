// Public-facing metadata stays separate from numerical estimation.
import {pollAllowedByChannelPolicy} from './model/poll-selection-policy.js';
export const SIGNAL_NOISE_CREDIT={
 name:'אריאל דניאלי — עד 120',
 methodology:'https://twonetwenty.com/he/methodology',
 explanation:'https://x.com/realGreenerik/status/2108279713685016913?s=20',
};
export const SIGNAL_NOISE_LABEL='אות ורעש — ניסיוני';
export const SIGNAL_NOISE_DESCRIPTION='תוספת ניסיונית לכל שיטת שקלול: אומדן תמיכה מתוך אחוזים מקוריים בסדרת הסקרים המאומתת שאחרי סגירת הרשימות. המודל מנסה ללמוד כמה מהתנודות הן שינוי בתמיכה וכמה הן רעש, באמצעות חיזוי הסקר הבא. שיטת השקלול שנבחרה קובעת את רמת האמון במדידות פעם אחת, בתוך האמידה. יישום מקומי בהשראת אריאל דניאלי ועד 120, שטרם כויל לתוצאות בחירות.';
export function signalNoiseBaseMethodLabel(config={}){
 return {robust:'שילוב שמרני',ensemble:'שילוב שיטות',equal:'משקל שווה',reference:'מדד 120',littlepolls:'מואיז הקטן',gilead:'גלעד — תרחיש 50%',rosner:'רוזנר — קירוב',quality:'דיוק היסטורי',correlation:'תלות בין סוקרים'}[config.weightMode]??config.weightMode??'דיוק היסטורי';
}

export function signalNoiseInstituteSelection(input,config={}){
 const excluded=new Set(config.excludedPolls??[]),factors=config.pollWeights??{};
 const observations=input?.signalNoiseData?.observations;
 return (input?.current?.polls??[]).map(poll=>{
  const factor=factors[poll.pollsterId]??1;
  return {pollId:poll.id,pollsterId:poll.pollsterId,publisher:poll.publisher,pollster:poll.pollster,
   selected:pollAllowedByChannelPolicy(poll,config)&&!excluded.has(poll.id)&&Number.isFinite(factor)&&factor>0,
   channel14Excluded:!pollAllowedByChannelPolicy(poll,config),
   manualMultiplier:Number.isFinite(factor)?factor:null,
   availableObservationCount:Array.isArray(observations)?new Set(observations.filter(row=>row.pollsterId===poll.pollsterId).map(row=>row.pollId)).size:null,
   selectionScope:'all eligible historical observations for this institute',
   weightingMethod:config.weightMode??'quality',signalNoiseEnabled:config.signalNoiseEnabled===true};
 });
}
