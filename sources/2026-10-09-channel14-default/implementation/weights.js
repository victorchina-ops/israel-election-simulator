// Poll-weight policies operate on one shared observation set, never on
// aggregator outputs treated as additional independent polls.
import {pollAllowedByChannelPolicy,validatePollSelectionPolicy} from './poll-selection-policy.js';
export const WEIGHT_MODES = Object.freeze(['equal','quality','correlation','reference','littlepolls','rosner','gilead','ensemble','robust']);
export const DEFAULT_METHOD_WEIGHTS = Object.freeze({equal:1,reference:1,littlepolls:1,gilead:1,rosner:0});
export const REFERENCE_WEIGHTS = Object.freeze({midgam_geva:26,kantar:24,hamadad_consortium:14,lazar:11,maagar_mochot:10,tatika:9,direct_polls:4,next_data:2});
export const LITTLEPOLLS_WEIGHTS = Object.freeze({midgam_geva:1,kantar:.75,hamadad_consortium:.6,lazar:.75,maagar_mochot:.75,tatika:.6,direct_polls:1,next_data:.6});
const own=(object,key)=>Object.prototype.hasOwnProperty.call(object??{},key);
const nonnegative=(v,name)=>{if(typeof v!=='number'||!Number.isFinite(v)||v<0)throw new Error(`משקל לא תקין: ${name}`);return v;};
const positive=(v,name)=>{nonnegative(v,name);if(v===0)throw new Error(`הערך חייב להיות חיובי: ${name}`);return v;};
function normalized(values,name){
  values.forEach((v,i)=>nonnegative(v,`${name}[${i}]`));
  const max=Math.max(...values);
  if(!(max>0))throw new Error(`יש לבחור לפחות משקל חיובי אחד: ${name}`);
  // Scaling avoids overflow when an imported scenario contains large weights.
  const scaled=values.map(v=>v/max),sum=scaled.reduce((a,b)=>a+b,0);
  return scaled.map(v=>v/sum);
}
function checkMap(map,name){
  if(map===undefined)return;
  if(!map||typeof map!=='object'||Array.isArray(map))throw new Error(`מפת משקלים לא תקינה: ${name}`);
  for(const [id,value] of Object.entries(map))nonnegative(value,`${name}.${id}`);
}
export function selectActivePolls(polls,config={}){
  if(!Array.isArray(polls))throw new Error('רשימת הסקרים אינה תקינה.');
  validatePollSelectionPolicy(config);
  checkMap(config.pollWeights,'pollWeights');
  if(config.excludedPolls!==undefined&&!Array.isArray(config.excludedPolls))throw new Error('excludedPolls חייב להיות מערך.');
  const ids=new Set();
  for(const p of polls){
    if(!p||typeof p.id!=='string'||typeof p.pollsterId!=='string')throw new Error('לכל סקר דרושים מזהה סקר ומזהה סוקר.');
    if(ids.has(p.id))throw new Error(`סקר מופיע יותר מפעם אחת: ${p.id}`);
    ids.add(p.id);
  }
  const excluded=new Set(config.excludedPolls??[]);
  const active=polls.filter(p=>pollAllowedByChannelPolicy(p,config)&&(config.pollWeights?.[p.pollsterId]??1)>0&&!excluded.has(p.id));
  if(!active.length)throw new Error('יש לבחור לפחות סקר אחד במשקל חיובי.');
  return active;
}
function ageDays(poll,config){
  const date=Date.parse(poll.fieldworkEnd||poll.date),asOf=Date.parse(config.asOf);
  if(!Number.isFinite(date)||!Number.isFinite(asOf))throw new Error(`תאריך חסר או לא תקין לחישוב דעיכת זמן: ${poll.id}`);
  return Math.max(0,(asOf-date)/864e5);
}
function recency(poll,config,halfLife){return Math.pow(.5,ageDays(poll,config)/positive(halfLife,'halfLifeDays'));}
function profileFor(id,calibration){
  const p=calibration.weightPresets?.methods?.[id]??{};
  if(!p||typeof p!=='object'||Array.isArray(p))throw new Error(`פרופיל שיטה לא תקין: ${id}`);
  if(p.weights!==null)checkMap(p.weights,'weights');if(p.weightsByPollster!==null)checkMap(p.weightsByPollster,'weightsByPollster');
  return p;
}
function profileMetadata(id,profile){
  const defaultNotes={
    equal:['משקל שווה לסקרים הפעילים, לפני מכפילים ידניים; דעיכת זמן נוספת רק אם הופעלה.'],
    quality:['משקלי דיוק מכווצים מבדיקת תחזיות נקודה היסטוריות; אינם כיול להסתברויות הבחירות.'],
    correlation:['הפחתת אשכול הוותיקים היא הנחת רגישות; אינה אמידת מטריצת תלות עדכנית.'],
    reference:['משקלי הבסיס המפורסמים במדד 120 על הסקרים הפעילים שלנו; ללא דעיכת זמן נוספת וללא שחזור מלוא שיטת האתר.'],
    littlepolls:['ציוני הסוקרים המפורסמים ב-LittlePolls על הסקרים הפעילים שלנו; ללא שחזור חלון הזמן, האיגום השבועי או מלוא שיטת האתר.'],
    rosner:['קירוב שלנו בהשראת עקרונות המדד: דעיכת זמן, שורש גודל מדגם והפחתת חריגות. הפרמטרים אינם נוסחה שפורסמה בידי רוזנר.'],
    gilead:['תרחיש רגישות בהשראת מיכאל גלעד: 50% למכון הנבחר לפני המכפילים הידניים; שיוך המכון הנוכחי אינו העברה מוכחת של דיוק היסטורי.'],
  };
  return {label:profile.label??profile.labelHe??id,status:profile.status??profile.exactness??(id==='rosner'?'our_inspired_proxy':'local_policy'),notes:[...(defaultNotes[id]??[]),...(Array.isArray(profile.notes)?profile.notes:[])],sourceUrls:profile.sourceUrls??(profile.sourceUrl?[profile.sourceUrl]:[])};
}
function methodVector(id,polls,config,calibration,probabilities){
  const profile=profileFor(id,calibration),meta=profileMetadata(id,profile),parameters={};
  const halfLife=config.halfLifeDays??14;
  let raw;
  if(id==='reference'||id==='littlepolls'){
    const published=profile.weightsByPollster??profile.weights??(id==='reference'?REFERENCE_WEIGHTS:LITTLEPOLLS_WEIGHTS);
    const unmapped=polls.filter(p=>!own(published,p.pollsterId));
    if(unmapped.length)meta.notes.push('לסוקרים ללא ציון מפורסם ניתן משקל אפס בשיטה זו: '+unmapped.map(p=>p.pollsterId).join(', '));
    raw=polls.map(p=>published[p.pollsterId]??0);
    parameters.extraRecency=false;
  }else if(id==='rosner'){
    const hl=config.rosnerHalfLifeDays??config.halfLifeDays??profile.proxy?.halfLifeDays??profile.halfLifeDays??14;
    const cutoff=positive(config.rosnerOutlierCutoffPP??profile.proxy?.cutoffPP??profile.outlierCutoffPP??2,'rosnerOutlierCutoffPP');
    if(!Array.isArray(probabilities)||probabilities.length!==polls.length||!probabilities.length)throw new Error('קירוב רוזנר דורש וקטור הסתברויות לכל סקר.');
    const width=probabilities[0].length;
    if(!width||probabilities.some(row=>!Array.isArray(row)||row.length!==width||row.some(x=>!Number.isFinite(x)||x<0||x>1)))throw new Error('וקטורי ההסתברויות לקירוב רוזנר אינם תקינים.');
    const center=Array.from({length:width},(_,j)=>probabilities.reduce((s,row)=>s+row[j],0)/polls.length);
    const distances=probabilities.map(row=>100*Math.sqrt(row.reduce((s,p,j)=>s+(p-center[j])**2,0)/width));
    raw=polls.map((p,i)=>recency(p,config,hl)*Math.sqrt(positive(p.sampleSize??500,`sampleSize ${p.id}`)/500)*(distances[i]===0?1:Math.min(1,cutoff/distances[i])));
    Object.assign(parameters,{halfLifeDays:hl,outlierCutoffPP:cutoff,distance:'RMS percentage-point distance to unweighted active-poll consensus',distancesPP:distances,sampleSizeExponent:.5,assumedSampleSize:500});
  }else{
    const ageOn=config.applyRecency!==false&&id!=='gilead';
    raw=polls.map(p=>{
      let weight=['quality','correlation'].includes(id)?nonnegative(calibration.pollsterQuality?.[p.pollsterId]?.weight??1,`pollsterQuality.${p.pollsterId}`):1;
      if(id==='correlation'&&!['direct_polls','next_data'].includes(p.pollsterId))weight*=nonnegative(config.veteranClusterDiscount??.5,'veteranClusterDiscount');
      return weight*(ageOn?recency(p,config,halfLife):1);
    });
    parameters.extraRecency=ageOn;
    if(ageOn)parameters.halfLifeDays=halfLife;
    if(id==='gilead'){
      const target=config.gileadTarget??'direct_polls';
      if(typeof target!=='string'||!target)throw new Error('מכון יעד לא תקין בתרחיש 50%.');
      const targets=polls.map((p,i)=>p.pollsterId===target?i:-1).filter(i=>i>=0),others=polls.map((p,i)=>p.pollsterId!==target?i:-1).filter(i=>i>=0);
      if(targets.length&&others.length){
        for(const group of [targets,others])for(const i of group)raw[i]=.5/group.length;
      }else meta.notes.push('מכון היעד או יתר הסוקרים אינם פעילים; המשקלים מנורמלים בין הסקרים שנותרו.');
      Object.assign(parameters,{target,targetShareBeforeManual:.5});
    }
  }
  return {weights:normalized(raw,id),...meta,parameters};
}
function coordinateWeightedMedian(values,shares){
  const ordered=values.map((value,i)=>({value,share:shares[i]})).sort((a,b)=>a.value-b.value);
  let cumulative=0;
  for(let i=0;i<ordered.length;i++){
    cumulative+=ordered[i].share;
    // Equal central mass uses the midpoint, including the familiar even median.
    if(Math.abs(cumulative-.5)<=Number.EPSILON*4&&i+1<ordered.length)return (ordered[i].value+ordered[i+1].value)/2;
    if(cumulative>.5)return ordered[i].value;
  }
  return ordered[ordered.length-1].value;
}
function robustVector(contributions,pollCount,config){
  const shrinkage=nonnegative(config.robustShrinkage===undefined?.25:config.robustShrinkage,'robustShrinkage');
  if(shrinkage>1)throw new Error('robustShrinkage חייב להיות בין 0 ל־1.');
  const methodShares=contributions.map(c=>c.mixWeight);
  const medians=Array.from({length:pollCount},(_,i)=>coordinateWeightedMedian(contributions.map(c=>c.weights[i]),methodShares));
  const zeroMedian=medians.every(v=>v===0),uniform=Array(pollCount).fill(1/pollCount);
  const normalizedMedian=zeroMedian?uniform:normalized(medians,'coordinateMedians');
  const weights=normalizedMedian.map((v,i)=>(1-shrinkage)*v+shrinkage*uniform[i]);
  return {weights,aggregation:{kind:'weighted_coordinate_median_then_uniform_shrinkage',nonlinear:true,shrinkage,
    coordinateMedians:medians,normalizedMedian,uniformWeights:uniform,zeroMedianFallback:zeroMedian,
    selectedMethodCount:contributions.length,manualMultipliersApplied:'after_aggregation_and_shrinkage'}};
}
export function computePollWeights(polls,config={},calibration={},options={}){
  const active=selectActivePolls(polls,config),mode=config.weightMode??'equal';
  if(!WEIGHT_MODES.includes(mode))throw new Error(`שיטת שקלול לא מוכרת: ${mode}`);
  if(config.applyRecency!==undefined&&typeof config.applyRecency!=='boolean')throw new Error('applyRecency חייב להיות ערך בוליאני.');
  let mixture=['ensemble','robust'].includes(mode)?(config.methodWeights??config.ensembleMix??DEFAULT_METHOD_WEIGHTS):{[mode]:1};
  checkMap(mixture,'methodWeights');
  for(const id of Object.keys(mixture))if(!WEIGHT_MODES.includes(id)||['ensemble','robust'].includes(id))throw new Error(`שיטת שילוב לא מוכרת: ${id}`);
  const methodIds=Object.keys(mixture).filter(id=>mixture[id]>0);
  const shares=normalized(methodIds.map(id=>mixture[id]),'methodWeights');
  const methodWeights=Object.fromEntries(methodIds.map((id,i)=>[id,shares[i]]));
  let probabilities=options.probabilities;
  if(probabilities&&active.length!==polls.length){
    if(probabilities.length!==polls.length)throw new Error('וקטורי ההסתברויות אינם תואמים לסקרים.');
    const byId=new Map(polls.map((p,i)=>[p.id,probabilities[i]]));
    probabilities=active.map(p=>byId.get(p.id));
  }
  const contributions=methodIds.map((method,k)=>({method,mixWeight:shares[k],...methodVector(method,active,config,calibration,probabilities)}));
  const robust=mode==='robust'?robustVector(contributions,active.length,config):null;
  const baseWeights=robust?.weights??active.map((_,i)=>contributions.reduce((s,c)=>s+c.mixWeight*c.weights[i],0));
  const manual=active.map(p=>config.pollWeights?.[p.pollsterId]??1);
  // Apply controls once AFTER policy normalization: a positive target multiplier
  // must remain effective even under the Gilead 50% policy or an ensemble.
  const maxManual=Math.max(...manual),scaledManual=manual.map(v=>v/maxManual);
  const raw=baseWeights.map((v,i)=>v*scaledManual[i]);
  const denominator=raw.reduce((a,b)=>a+b,0),weights=normalized(raw,'finalPollWeights');
  for(const c of contributions){
    if(robust){
      // These are inputs to a nonlinear operator, not additive attribution.
      c.aggregationRole='input_vector_to_nonlinear_weighted_coordinate_median';
      c.contributionBeforeManual=null;c.contributionAfterManual=null;
      c.robustAggregation=robust.aggregation;
    }else{
      c.contributionBeforeManual=c.weights.map(v=>v*c.mixWeight);
      c.contributionAfterManual=c.contributionBeforeManual.map((v,i)=>v*scaledManual[i]/denominator);
    }
  }
  const notes=[...new Set(contributions.flatMap(c=>c.notes))];
  if(mode==='ensemble')notes.unshift('שילוב שיטות משנה את משקלי אותם סקרים; הוא אינו מוסיף תצפיות או מגדיל את המדגם.');
  if(robust){
    const profile=profileFor('robust',calibration);
    notes.unshift('שילוב עמיד ושמרני: חציון משוקלל של משקלי הסוקר בכל שיטה, נרמול, ואז '+Math.round(100*robust.aggregation.shrinkage)+'% לכיוון משקל שווה. זהו כלל שלנו שלא הוכחה עדיפותו בחיזוי.');
    notes.push('השיטות פועלות על אותם סקרים; החציון אינו מוסיף תצפיות. וקטורי השיטות הם קלט לא־ליניארי ואינם תרומות שניתן לחבר.');
    notes.push(...(Array.isArray(profile.notes)?profile.notes:[]));
    if(robust.aggregation.selectedMethodCount<3)notes.push('נבחרו פחות משלוש שיטות: ההגנה של החציון מפני המלצה חריגה מוגבלת.');
    if(robust.aggregation.zeroMedianFallback)notes.push('כל חציוני המשקלים היו אפס; הופעל משקל שווה מפורש כחלופה.');
  }
  return {polls:active,weights,baseWeights,methodWeights,contributions,notes:[...new Set(notes)],mode,aggregation:robust?.aggregation??{kind:'arithmetic_mixture',nonlinear:false}};
}
