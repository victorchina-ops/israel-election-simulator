import {normal, normalise} from './random.js';
import {selectActivePolls} from './weights.js';

// A local, experimental adaptation of a local-level state-space model. This is
// our implementation, not To120's code, calibration or forecast. The state is
// [latent support, static institute offsets]; the latter do not disappear just
// because an institute published many surveys. Units throughout are vote-share
// fractions, variances in squared fractions, and Q per elapsed calendar day.
export const SIGNAL_NOISE_CREDIT = Object.freeze({
  name:'אריאל דניאלי — To120',
  status:'our_local_adaptation_not_replica',
  sourceUrls:['https://twonetwenty.com/he/articles/he-about-to-120','https://twonetwenty.com/he/methodology','https://x.com/realGreenerik/status/2108279713685016913'],
  technicalSourceUrls:['https://www.statsmodels.org/stable/examples/notebooks/generated/statespace_concentrated_scale.html'],
});
const DAY=864e5;
const own=(o,k)=>Object.prototype.hasOwnProperty.call(o??{},k);
const clamp=(v,lo,hi)=>Math.min(hi,Math.max(lo,v));
// These are publisher calendar dates. An Israeli midnight ISO timestamp must
// not turn into the previous UTC date and leak/exclude a whole day's surveys.
const dayOf=(date)=>{
  const value=typeof date==='string'&&/^\d{4}-\d{2}-\d{2}(?:$|T)/.test(date)?date.slice(0,10):date;
  const t=Date.parse(value);return Number.isFinite(t)?Math.floor(t/DAY):NaN;
};
function requireNumber(v,name,min=0,max=Infinity){
  if(typeof v!=='number'||!Number.isFinite(v)||v<min||v>max)throw new Error(`פרמטר אות–רעש לא תקין: ${name}`);
  return v;
}
const isoDay=(day)=>new Date(day*DAY).toISOString().slice(0,10);
const avg=(xs)=>xs.reduce((s,v)=>s+v,0)/xs.length;
const zeros=(n)=>Array(n).fill(0);
const matrix=(n)=>Array.from({length:n},()=>zeros(n));

function settings(options={}){
  const result={designEffect:1.5,assumedSampleSize:500,minimumMeasurementVariance:1e-8,
    instituteOffsetSD:.0075,minimumFitObservations:8,minimumFitSpanDays:14,
    fallbackQPerDay:.0006**2,fallbackR:.003**2,regularization:.5,
    qMax:.015**2,rMax:.05**2,gridSteps:13,...options};
  for(const k of ['minimumMeasurementVariance','instituteOffsetSD','fallbackQPerDay','fallbackR','regularization','qMax','rMax'])requireNumber(result[k],k);
  requireNumber(result.designEffect,'designEffect',.01,100);
  requireNumber(result.assumedSampleSize,'assumedSampleSize',1);
  requireNumber(result.minimumFitSpanDays,'minimumFitSpanDays');
  for(const k of ['minimumFitObservations','gridSteps'])if(!Number.isInteger(result[k])||result[k]<2||result[k]>1000)throw new Error(`פרמטר אות–רעש לא תקין: ${k}`);
  return result;
}

function prepareSeries(observations,opts){
  if(!Array.isArray(observations)||!observations.length)throw new Error('אין מדידות אחוזי תמיכה מתאימות למודל אות–רעש.');
  const coords=new Map(),sameDay=new Map(),duplicateIds=[];
  for(const raw of observations){
    if(!raw||typeof raw.pollId!=='string'||typeof raw.pollsterId!=='string')throw new Error('למדידת אות–רעש דרושים מזהה סקר ומזהה מכון.');
    const day=dayOf(raw.date??raw.fieldworkEnd);
    if(!Number.isFinite(day))throw new Error(`תאריך מדידת אות–רעש לא תקין: ${raw.pollId}`);
    const value=requireNumber(raw.value,`${raw.pollId}.value`,0,1);
    const n=raw.sampleSize==null?opts.assumedSampleSize:requireNumber(raw.sampleSize,`${raw.pollId}.sampleSize`,1);
    const deff=raw.designEffect==null?opts.designEffect:requireNumber(raw.designEffect,`${raw.pollId}.designEffect`,.01,100);
    const qualityMultiplier=requireNumber(raw.qualityMultiplier??1,`${raw.pollId}.qualityMultiplier`,Number.MIN_VALUE);
    // The actual sampling variance is a floor. A source-supplied larger variance
    // is honored; neither n=missing nor p=0 creates a zero-variance observation.
    const floor=Math.max(opts.minimumMeasurementVariance,value*(1-value)*deff/n);
    const measurementVariance=raw.measurementVariance==null?floor:Math.max(floor,requireNumber(raw.measurementVariance,'measurementVariance'));
    const item={...raw,date:isoDay(day),day,value,sampleSize:n,assumedSampleSize:raw.sampleSize==null,
      measurementVariance,qualityMultiplier,originalPollIds:[raw.pollId]};
    if(coords.has(raw.pollId)){
      const previous=coords.get(raw.pollId);
      if(previous.pollsterId!==item.pollsterId||previous.day!==day||Math.abs(previous.value-value)>1e-12||Math.abs(previous.measurementVariance-measurementVariance)>1e-12)throw new Error(`נתונים סותרים לאותו סקר: ${raw.pollId}`);
      duplicateIds.push(raw.pollId);continue;
    }
    coords.set(raw.pollId,item);
    const key=`${raw.pollsterId}|${day}`;
    if(!sameDay.has(key))sameDay.set(key,[]);
    sameDay.get(key).push(item);
  }
  const rows=[...sameDay.values()].map(group=>group.length===1?group[0]:{
    ...group[0],value:avg(group.map(x=>x.value)),
    // Same institute/day reports may share respondents: average centers once,
    // retain the largest variance, never multiply the effective sample size.
    measurementVariance:Math.max(...group.map(x=>x.measurementVariance)),
    sampleSize:Math.min(...group.map(x=>x.sampleSize)),qualityMultiplier:Math.min(...group.map(x=>x.qualityMultiplier)),
    assumedSampleSize:group.some(x=>x.assumedSampleSize),originalPollIds:group.flatMap(x=>x.originalPollIds),
  }).sort((a,b)=>a.day-b.day||a.pollsterId.localeCompare(b.pollsterId)||a.pollId.localeCompare(b.pollId));
  return {rows,duplicateIds,sameDayCollapsed:coords.size-rows.length};
}

function kalman(rows,q,r,opts,withContributions=false){
  const institutes=[...new Set(rows.map(o=>o.pollsterId))].sort(),dim=1+institutes.length;
  const indexes=new Map(institutes.map((id,i)=>[id,i+1]));
  const bvar=opts.instituteOffsetSD**2;
  const means=zeros(dim),cov=matrix(dim),coeff=withContributions?Array.from({length:dim},()=>zeros(rows.length)):null;
  // Exact diffuse initial support: condition on the first observation rather
  // than count it twice in a guessed normal prior. The offset/support negative
  // covariance preserves the unresolved first institute bias.
  const first=rows[0],bi=indexes.get(first.pollsterId),firstV=(first.measurementVariance+r)/first.qualityMultiplier;
  means[0]=first.value;cov[0][0]=firstV+bvar;
  for(let j=1;j<dim;j++)cov[j][j]=bvar;
  cov[0][bi]=cov[bi][0]=-bvar;
  if(coeff)coeff[0][0]=1;
  let nll=0,lastDay=first.day;
  const diagnostics=[];
  for(let i=1;i<rows.length;i++){
    const row=rows[i],j=indexes.get(row.pollsterId),elapsed=row.day-lastDay;
    cov[0][0]+=q*elapsed;
    const variance=(row.measurementVariance+r)/row.qualityMultiplier;
    const projection=cov.map(x=>x[0]+x[j]);
    const f=Math.max(opts.minimumMeasurementVariance,projection[0]+projection[j]+variance);
    const innovation=row.value-means[0]-means[j],gain=projection.map(x=>x/f);
    nll+=.5*(Math.log(2*Math.PI*f)+innovation*innovation/f);
    if(coeff){
      const observedCoefficient=coeff[0].map((v,k)=>v+coeff[j][k]);
      for(let s=0;s<dim;s++)for(let k=0;k<rows.length;k++)coeff[s][k]+=gain[s]*((k===i?1:0)-observedCoefficient[k]);
      diagnostics.push({pollId:row.pollId,innovation,predictionVariance:f,measurementVariance:variance,elapsedDays:elapsed,gain:gain[0]});
    }
    for(let s=0;s<dim;s++)means[s]+=gain[s]*innovation;
    for(let s=0;s<dim;s++)for(let t=s;t<dim;t++){
      const value=cov[s][t]-projection[s]*projection[t]/f;
      cov[s][t]=cov[t][s]=s===t?Math.max(0,value):value;
    }
    lastDay=row.day;
  }
  return {mean:means[0],variance:cov[0][0],negativeLogLikelihood:nll,
    institutes,instituteOffsets:Object.fromEntries(institutes.map((id,i)=>[id,{mean:means[i+1],variance:cov[i+1][i+1],priorSD:opts.instituteOffsetSD}])),
    coefficients:coeff?.[0],diagnostics,lastDay};
}
function grid(max,steps,fallback){
  if(max===0)return [0];
  const lower=Math.min(max,Math.max(1e-10,Math.min(fallback||max/100,max/10000)));
  return [...new Set([0,...Array.from({length:steps},(_,i)=>lower*(max/lower)**(i/(steps-1))),clamp(fallback,0,max)])].sort((a,b)=>a-b);
}

export function fitLocalLevel(observations,options={}){
  const opts=settings(options),prepared=prepareSeries(observations,opts),rows=prepared.rows;
  const spanDays=rows.at(-1).day-rows[0].day;
  const fallback=rows.length<opts.minimumFitObservations||spanDays<opts.minimumFitSpanDays;
  let q=opts.fallbackQPerDay,r=opts.fallbackR,objective=null,candidates=0;
  if(!fallback){
    let best=Infinity;
    for(const candidateQ of grid(opts.qMax,opts.gridSteps,opts.fallbackQPerDay))for(const candidateR of grid(opts.rMax,opts.gridSteps,opts.fallbackR)){
      const ll=kalman(rows,candidateQ,candidateR,opts).negativeLogLikelihood;
      // Weak stated shrinkage toward low variances limits unstable separation
      // of Q/R in short series. It is our prior, not a learned To120 parameter.
      const penalty=opts.regularization*(Math.log1p(candidateQ/Math.max(opts.fallbackQPerDay,1e-10))+Math.log1p(candidateR/Math.max(opts.fallbackR,1e-10)));
      const score=ll+penalty;candidates++;
      if(score<best){best=score;q=candidateQ;r=candidateR;objective=score;}
    }
  }
  const result=kalman(rows,q,r,opts,true);
  const requestedAsOf=options.asOf==null?result.lastDay:dayOf(options.asOf);
  if(!Number.isFinite(requestedAsOf)||requestedAsOf<result.lastDay)throw new Error('תאריך התחזית קודם למדידה שנכללה.');
  const elapsed=requestedAsOf-result.lastDay;
  return {...result,mean:clamp(result.mean,0,1),unconstrainedMean:result.mean,
    variance:result.variance+q*elapsed,qPerDay:q,r,count:rows.length,spanDays,
    from:rows[0].date,to:rows.at(-1).date,asOf:isoDay(requestedAsOf),elapsedSinceLastMeasurementDays:elapsed,
    instituteCount:result.institutes.length,fallback,fallbackReason:fallback?'insufficient_series_for_separate_Q_R_estimation':null,
    fallbackParameters:fallback?{qPerDay:q,r}:null,fitMethod:'regularized_sequential_one_step_predictive_gaussian_likelihood',
    objective,gridCandidateCount:candidates,regularization:opts.regularization,instituteOffsetSD:opts.instituteOffsetSD,
    duplicatePollIds:prepared.duplicateIds,sameDayCollapsed:prepared.sameDayCollapsed,
    assumedSampleSizePollIds:rows.filter(x=>x.assumedSampleSize).flatMap(x=>x.originalPollIds),
    contributions:rows.map((row,i)=>({pollId:row.pollId,pollsterId:row.pollsterId,date:row.date,originalPollIds:row.originalPollIds,
      coefficient:result.coefficients[i],value:row.value,qualityMultiplier:row.qualityMultiplier,
      measurementSampleSize:row.sampleSize,measurementSampleSizeIsEstimate:row.measurementSampleSizeIsEstimate===true,
      measurementSampleSizeMethod:row.measurementSampleSizeMethod??null,
      measurementVarianceBeforeQuality:row.measurementVariance+r,measurementVariance:(row.measurementVariance+r)/row.qualityMultiplier})),
    notes:['Q ו־R הם אומדנים מותנים במודל, ואינם הפרדה ודאית בין שינוי אמיתי לרעש.',
      'הבדלי מכונים מתוארים באמצעות היסט קבוע עם שונות קודמת מפורשת; אין כאן כיול הטיות מכון מבחירות קודמות.',
      'לא הופעל משקל נוסף לאחר סינון קלמן; דיוק היסטורי ומכפילים ידניים משנים את שונות המדידה פעם אחת.',
      ...(fallback?['אין די מדידות או טווח זמן לאמידת אות ורעש בנפרד: הופעלו ערכי רגישות קבועים ומוצהרים.']:[])],
  };
}

function percentageBasis(row){
  return ['decided_valid_votes','valid_votes','decided_voters'].includes(row.percentageBasis);
}
function sourceRows(input){
  if(Array.isArray(input.signalNoiseData?.observations))return input.signalNoiseData.observations;
  const history=input.history??input.pollHistory;
  const rows=Array.isArray(history)?history:history?.polls??history?.observations??[];
  return rows.filter(row=>row.reportedPercentages&&percentageBasis(row)).map(row=>({...row,
    pollId:row.pollId??row.id,publicationDate:row.publicationDate??row.date,
    fieldworkVerified:row.fieldworkVerified===true||row.fieldworkVerification?.status==='verified',
  }));
}
function explicitPrior(id,data){
  const prior=data.priors?.[id],bound=data.bounds?.[id];
  if(prior){
    if(!Array.isArray(prior.sourceUrls)||!prior.sourceUrls.length||typeof prior.reason!=='string')throw new Error(`לקודם מפורש דרושים מקור והסבר: ${id}`);
    return {mean:requireNumber(prior.meanPct,`${id}.meanPct`,0,100)/100,
      variance:(requireNumber(prior.sdPct,`${id}.sdPct`,Number.MIN_VALUE,100)/100)**2,
      qPerDay:requireNumber(prior.qPerDay??.0006**2,`${id}.qPerDay`),r:null,count:0,instituteCount:0,
      fallback:true,fallbackReason:'explicit_sensitivity_prior_not_observed_support',contributions:[],sourceUrls:prior.sourceUrls,
      notes:[prior.reason,'הערך הוא הנחת רגישות מפורשת, ולא מדידת תמיכה או אפס שפורסם.']};
  }
  if(bound){
    const lo=requireNumber(bound.minPct,`${id}.minPct`,0,100)/100,hi=requireNumber(bound.maxPct,`${id}.maxPct`,0,100)/100;
    if(lo>hi||!Array.isArray(bound.sourceUrls)||!bound.sourceUrls.length)throw new Error(`גבול תמיכה לא תקין או ללא מקור: ${id}`);
    return {mean:(lo+hi)/2,variance:(hi-lo)**2/12,qPerDay:.0006**2,r:null,count:0,instituteCount:0,
      fallback:true,fallbackReason:'uniform_within_published_bound_sensitivity',contributions:[],bounds:{min:lo,max:hi},sourceUrls:bound.sourceUrls,
      notes:['מיקום אחיד בתוך הגבול שפורסם הוא הנחת רגישות; אין כאן אחוז נקודתי שנמדד.']};
  }
  return null;
}

export function createSignalNoiseCombination(input,config={},calibration=input.calibration??{}){
  const data=input.signalNoiseData??{},asOf=config.asOf??input.current?.asOf??data.asOf;
  if(config.signalNoiseHistoricalQuality!==undefined&&typeof config.signalNoiseHistoricalQuality!=='boolean')throw new Error('שקלול הדיוק ההיסטורי חייב להיות ערך בוליאני.');
  const cutoff=dayOf(asOf),closure=dayOf(data.listClosureDate??'2026-09-08');
  if(!Number.isFinite(cutoff)||!Number.isFinite(closure))throw new Error('חלון הזמן של מודל אות–רעש אינו תקין.');
  const polls=selectActivePolls(input.current.polls,config),selectedInstitutes=new Set(polls.map(p=>p.pollsterId)),excluded=new Set(config.excludedPolls??[]);
  const skipped=[],eligible=[];
  for(const row of sourceRows(input)){
    const start=dayOf(row.fieldworkStart),end=dayOf(row.fieldworkEnd),publication=dayOf(row.publicationDate??row.date);
    let reason=null;
    if(!selectedInstitutes.has(row.pollsterId)||excluded.has(row.pollId))reason='not_selected';
    else if(!Number.isFinite(publication)||publication>cutoff)reason='publication_after_cutoff_or_missing';
    else if(!Number.isFinite(start)||!Number.isFinite(end)||row.fieldworkVerified!==true)reason='unverified_fieldwork';
    else if(start<=closure||end<start||end>cutoff||end>publication)reason='outside_strict_post_closure_window';
    else if(!percentageBasis(row))reason='unverified_percentage_denominator';
    else if(!row.reportedPercentages||row.reconstructed===true||row.percentagesReconstructed===true)reason='no_published_vote_share';
    if(reason){skipped.push({pollId:row.pollId??row.id,reason});continue;}
    eligible.push({...row,pollId:row.pollId??row.id,date:isoDay(end)});
  }
  if(!eligible.length)throw new Error('לא נותרו סקרים עם אחוזים שפורסמו ומכנה מאומת לאחר סגירת הרשימות.');
  // Normalize existing, already-shrunk historical calibration across the
  // selected institutes. Manual multipliers enter only the observation R.
  const qualityOn=config.signalNoiseHistoricalQuality!==false;
  const eligibleInstitutes=new Set(eligible.map(row=>row.pollsterId));
  const rawQuality=Object.fromEntries([...eligibleInstitutes].map(id=>[id,qualityOn?requireNumber(calibration.pollsterQuality?.[id]?.weight??1,`pollsterQuality.${id}`,Number.MIN_VALUE):1]));
  const meanQuality=avg(Object.values(rawQuality));
  const quality=Object.fromEntries(Object.entries(rawQuality).map(([id,v])=>[id,v/meanQuality]));
  const opts=settings({designEffect:config.designEffect??1.5,
    instituteOffsetSD:(config.signalNoiseInstituteOffsetSDPP??.75)/100,
    ...(config.signalNoiseOptions??{}),asOf:isoDay(cutoff)});
  const models={},missing=[];
  let reportedCount=0;
  const knownIds=new Set(input.parties.map(p=>p.id));
  for(const row of eligible)for(const [id,value] of Object.entries(row.reportedPercentages)){
    if(!knownIds.has(id))throw new Error(`רשימה לא מוכרת באחוזי מודל אות–רעש: ${id}`);
    if(value!==null&&value!==undefined)requireNumber(value,`${row.pollId}.${id}`,0,100);
  }
  for(const party of input.parties){
    const observations=eligible.filter(row=>own(row.reportedPercentages,party.id)&&row.reportedPercentages[party.id]!=null).map(row=>({
      pollId:row.pollId,pollsterId:row.pollsterId,date:row.date,value:row.reportedPercentages[party.id]/100,
      sampleSize:row.percentageSampleSize??row.sampleSize,designEffect:row.designEffect,
      measurementSampleSizeIsEstimate:row.percentageSampleSizeIsEstimate===true,
      measurementSampleSizeMethod:row.percentageSampleSizeMethod,
      qualityMultiplier:quality[row.pollsterId]*requireNumber(config.pollWeights?.[row.pollsterId]??1,`pollWeights.${row.pollsterId}`,Number.MIN_VALUE),
    }));
    reportedCount+=observations.length;
    const model=observations.length?fitLocalLevel(observations,opts):explicitPrior(party.id,data);
    if(!model){missing.push(party.id);continue;}
    models[party.id]={id:party.id,name:party.name,...model};
  }
  if(missing.length)throw new Error('חסרים אחוזים מקוריים או קודם רגישות מפורש לרשימות: '+missing.join(', '));
  const center=normalise(input.parties.map(p=>models[p.id].mean));
  const magnitudeByInstitute=Object.fromEntries([...selectedInstitutes].map(id=>[id,0]));
  const pollMass=Object.fromEntries(polls.map(p=>[p.id,0]));
  for(const party of input.parties){
    const model=models[party.id];model.normalizedMean=center[input.parties.indexOf(party)];
    for(const c of model.contributions)magnitudeByInstitute[c.pollsterId]+=Math.abs(c.coefficient)/input.parties.length;
  }
  for(const poll of polls)pollMass[poll.id]=magnitudeByInstitute[poll.pollsterId];
  const rawMass=polls.map(p=>pollMass[p.id]),weights=rawMass.some(v=>v>0)?normalise(rawMass):polls.map(()=>1/polls.length);
  const dates=eligible.map(row=>dayOf(row.date)),unique=new Set(eligible.map(row=>row.pollId));
  const measurementCoordinates=new Set(eligible.map(row=>`${row.pollsterId}|${row.date}`));
  const notes=[
    'חלופה ניסיונית שלנו בהשראת To120 ואריאל דניאלי; אינה העתקה של קוד, כיול או תחזית האתר המקורי.',
    'נכללו אחוזי תמיכה שפורסמו עם מכנה תואם ומתועד, מפורש או מוסק לפי דוח המקור, ורק עבודת שדה מאומתת אחרי סגירת הרשימות. נתון חסר אינו אפס.',
    'דיוק היסטורי ומכפילים ידניים משפיעים פעם אחת על שונות המדידה; אין שקלול נוסף לאחר מסנן קלמן.',
    'כאשר דווח שיעור מתלבטים בנפרד, מספר בעלי הדעה עשוי להיקבע בקירוב מתוך גודל המדגם. זהו אומדן לצורך שונות המדידה, ולא מספר משיבים נפרד או גודל מדגם אפקטיבי שפורסם.',
    'סדרות קצרות משתמשות בפרמטרי אות ורעש קבועים ומוצהרים; Q/R אינם מזוהים היטב בכל מפלגה.',
    'המשקלים הכלליים המוצגים הם סיכום גודל תרומות לצורכי תצוגה; החישוב בפועל משתמש בתרומות נפרדות לכל מפלגה, שעשויות להיות שליליות בתיקון היסט מכון.',
    'הגרלה ממרווחי התמיכה הנפרדים ונרמול לסכום 100% הם קירוב להרכב משותף; מתאמים בין מפלגות לא נאמדו.',
    'הסתברויות המעבר והרוב לא כוילו בבחירות שהושארו מחוץ לפיתוח. אין טענה לעדיפות חיזוי מוכחת.',
  ];
  const signalNoise={schemaVersion:1,mode:'signal_noise',status:'experimental_not_probability_calibrated',credit:SIGNAL_NOISE_CREDIT,
    asOf:isoDay(cutoff),listClosureDate:isoDay(closure),parties:models,
    historicalQualityEnabled:qualityOn,historicalQuality:quality,
    weightingAppliedAt:'measurement_variance_once',displayWeightDefinition:'normalized_absolute_party_filter_coefficients_by_institute',
    covarianceAssumption:'independent_party_marginals_then_simplex_normalization; static institute offsets within each party',
    coverage:{observationCount:measurementCoordinates.size,sourcePollCount:unique.size,instituteCount:new Set(eligible.map(r=>r.pollsterId)).size,
      from:isoDay(Math.min(...dates)),to:isoDay(Math.max(...dates)),reportedPercentageCount:reportedCount,reconstructedPercentageCount:0,
      estimatedDecidedSampleSizePollCount:eligible.filter(row=>row.percentageSampleSizeIsEstimate===true).length,
      includedPollIds:[...unique],excluded:skipped,missingPartyIds:[],priorPartyIds:input.parties.filter(p=>models[p.id].count===0).map(p=>p.id)},
    parameters:{instituteOffsetSDPP:100*opts.instituteOffsetSD,fallbackQPerDay:opts.fallbackQPerDay,fallbackR:opts.fallbackR,
      minimumFitObservations:opts.minimumFitObservations,minimumFitSpanDays:opts.minimumFitSpanDays,regularization:opts.regularization},notes,
  };
  return {polls,weights,center,nEffective:null,recon:polls.map(p=>({id:p.id,probabilities:center.slice(),reconstructed:false,
    notes:['הסקר משמש בורר מכון בלבד; מרכז החלופה נאמד מאחוזים מקוריים לאורך זמן.']})),
    assumedSampleSizes:[...new Set(Object.values(models).flatMap(m=>m.assumedSampleSizePollIds??[]))],
    methodWeights:{signal_noise:1},contributions:[],weightNotes:notes,notes,signalNoise,
    signalNoiseSampling:{partyIds:input.parties.map(p=>p.id),uncertaintyScale:config.uncertaintyScale??1},
  };
}

export function sampleSignalNoise(combined,rng,forecastDays=0,uncertaintyScale=combined.signalNoiseSampling?.uncertaintyScale??1){
  if(typeof rng!=='function'||!combined.signalNoise||!combined.signalNoiseSampling)throw new Error('קלט הגרלת אות–רעש אינו תקין.');
  requireNumber(forecastDays,'forecastDays',0,3650);
  const scale=requireNumber(uncertaintyScale,'uncertaintyScale',0,10);
  const values=combined.signalNoiseSampling.partyIds.map(id=>{
    const model=combined.signalNoise.parties[id];
    const sd=scale*Math.sqrt(Math.max(0,model.variance+model.qPerDay*forecastDays));
    // Posterior Q is the only time-drift term here. Caller may add its explicitly
    // labeled shared bloc sensitivity once, but never a second poll Dirichlet,
    // poll-mixture, seat-rounding jitter or legacy dailyDrift to this posterior.
    if(model.bounds&&model.count===0){
      const spread=(rng()-.5)*(model.bounds.max-model.bounds.min)*scale;
      return clamp(model.mean+spread+(forecastDays?normal(rng)*scale*Math.sqrt(model.qPerDay*forecastDays):0),0,1);
    }
    return clamp(model.mean+(sd?normal(rng)*sd:0),0,1);
  });
  // A rare all-zero clipped Gaussian draw falls back to the fitted center;
  // missing values were already rejected rather than transformed into zeros.
  return values.some(v=>v>0)?normalise(values):combined.center.slice();
}
