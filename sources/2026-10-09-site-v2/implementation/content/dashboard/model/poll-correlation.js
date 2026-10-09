// Experimental redundancy inferred from similar published 2026 forecasts.
// This is not measured respondent overlap or correlation of forecast errors.
const sum=values=>values.reduce((a,b)=>a+b,0);
const own=(object,key)=>Object.prototype.hasOwnProperty.call(object??{},key);
const positive=(value,name)=>{if(typeof value!=='number'||!Number.isFinite(value)||value<=0)throw new Error(`פרמטר דמיון סקרים לא תקין: ${name}`);return value;};

export function isPollCorrelationEnabled(config={}){
  if(config.pollCorrelationEnabled!==undefined&&typeof config.pollCorrelationEnabled!=='boolean')throw new Error('pollCorrelationEnabled חייב להיות ערך בוליאני.');
  return config.pollCorrelationEnabled===true;
}

function assertPSD(matrix){
  const n=matrix.length,L=Array.from({length:n},()=>Array(n).fill(0)),tolerance=1e-10;
  for(let i=0;i<n;i++)for(let j=0;j<=i;j++){
    let value=matrix[i][j];for(let k=0;k<j;k++)value-=L[i][k]*L[j][k];
    if(i===j){if(value< -tolerance)throw new Error('מטריצת דמיון הסקרים אינה חיובית למחצה.');L[i][j]=Math.sqrt(Math.max(0,value));}
    else if(L[j][j]>tolerance)L[i][j]=value/L[j][j];
    else if(Math.abs(value)>tolerance)throw new Error('מטריצת דמיון הסקרים אינה חיובית למחצה.');
  }
}

export function reviewedPollCorrelationProfile(calibration={}){
  const profile=calibration.pollCorrelation;
  if(!profile||typeof profile!=='object'||Array.isArray(profile))throw new Error('חסר פרופיל דמיון סקרים מאומת מסדרת 2026.');
  const ids=profile.instituteIds,matrix=profile.modeledCorrelationMatrix;
  if(!Array.isArray(ids)||!ids.length||ids.length>64||ids.some(id=>typeof id!=='string'||!id)||new Set(ids).size!==ids.length)throw new Error('מזהי המכונים בפרופיל דמיון הסקרים אינם תקינים.');
  if(!Array.isArray(matrix)||matrix.length!==ids.length||matrix.some(row=>!Array.isArray(row)||row.length!==ids.length||row.some(v=>typeof v!=='number'||!Number.isFinite(v)||v<0||v>1+1e-12)))throw new Error('מטריצת דמיון הסקרים אינה תקינה.');
  for(let i=0;i<ids.length;i++){
    if(Math.abs(matrix[i][i]-1)>1e-10)throw new Error('אלכסון מטריצת דמיון הסקרים חייב להיות 1.');
    for(let j=0;j<ids.length;j++)if(Math.abs(matrix[i][j]-matrix[j][i])>1e-10)throw new Error('מטריצת דמיון הסקרים אינה סימטרית.');
  }
  assertPSD(matrix);
  return profile;
}

export function getPollCorrelationMatrix(polls,calibration={}){
  const profile=reviewedPollCorrelationProfile(calibration),indexes=new Map(profile.instituteIds.map((id,i)=>[id,i]));
  const unmodeledPairs=[];
  const matrix=polls.map((poll,i)=>polls.map((other,j)=>{
    if(i===j||poll.pollsterId===other.pollsterId)return 1;
    if(indexes.has(poll.pollsterId)&&indexes.has(other.pollsterId))return profile.modeledCorrelationMatrix[indexes.get(poll.pollsterId)][indexes.get(other.pollsterId)];
    if(i<j)unmodeledPairs.push({firstInstitute:poll.pollsterId,secondInstitute:other.pollsterId,similarity:null});
    // This is only the uncorrected variance fallback, never a source estimate
    // of zero similarity. Unknown institutes receive no point-weight bonus.
    return 0;
  }));
  return {matrix,profileId:profile.id,unmodeledPairs,
    eligibleInstitutes:[...new Set(polls.map(p=>p.pollsterId))].filter(id=>indexes.has(id)),
    unmodeledInstitutes:[...new Set(polls.map(p=>p.pollsterId))].filter(id=>!indexes.has(id)),
    unknownPairAssumption:'uncorrected_variance_fallback_not_estimated_independence'};
}

export function applyPollCorrelationDiscount(polls,weights,profile){
  const indexes=new Map(profile.instituteIds.map((id,i)=>[id,i])),massByInstitute={};
  polls.forEach((poll,i)=>{if(indexes.has(poll.pollsterId)&&weights[i]>0)massByInstitute[poll.pollsterId]=(massByInstitute[poll.pollsterId]??0)+weights[i];});
  const ids=profile.instituteIds.filter(id=>(massByInstitute[id]??0)>0),mass=sum(Object.values(massByInstitute));
  const density=Object.fromEntries(ids.map(id=>[id,ids.reduce((s,other)=>s+profile.modeledCorrelationMatrix[indexes.get(id)][indexes.get(other)],0)]));
  const discounts=Object.fromEntries(ids.map(id=>[id,1/density[id]]));
  const denominator=ids.reduce((s,id)=>s+massByInstitute[id]*discounts[id],0);
  const uniformDiscount=ids.every(id=>discounts[id]===discounts[ids[0]]);
  // With zero similarity (or equal redundancy for every eligible institute),
  // preserve the original policy vector bit for bit rather than renormalize it.
  const factors=polls.map(poll=>!uniformDiscount&&own(discounts,poll.pollsterId)?discounts[poll.pollsterId]*mass/denominator:1);
  return {weights:weights.map((weight,i)=>weight*factors[i]),factors,
    metadata:{enabled:true,profileId:profile.id,kind:'forecast_similarity_density_discount',
      similarityDataset:'verified_post_closure_2026_published_forecasts',historicalAccuracyApplied:'unchanged_selected_base_policy',
      eligibleInstitutes:ids,eligibleMassBeforeManual:mass,
      unmodeledInstitutes:[...new Set(polls.map(p=>p.pollsterId))].filter(id=>!ids.includes(id)),
      unknownInstituteWeightPolicy:'preserve_proposed_mass_before_manual',redundancyDensity:density,redundancyDiscounts:discounts,
      weightCorrectionApplied:'once_after_policy_aggregation_before_manual',manualMultipliersApplied:'last',
      similarityStrength:profile.similarityStrength??null,bandwidthSeats:profile.bandwidthSeats??null,
      evidenceLimit:'experimental_forecast_similarity_not_measured_sampling_dependence',
      coverage:profile.coverage??null}};
}

export function covarianceInflation(polls,weights,config={},calibration={},options={}){
  if(!Array.isArray(polls)||!Array.isArray(weights)||polls.length!==weights.length||!polls.length||weights.some(w=>typeof w!=='number'||!Number.isFinite(w)||w<0)||!(sum(weights)>0))throw new Error('משקלי חישוב המידע האפקטיבי אינם תקינים.');
  if(options.weightsAreNormalized&&Math.abs(sum(weights)-1)>1e-10)throw new Error('משקלים שסומנו כמנורמלים אינם מסתכמים ל־1.');
  const normalized=options.weightsAreNormalized?weights.slice():weights.map(w=>w/sum(weights)),minimumSampleSize=positive(options.minimumSampleSize??100,'minimumSampleSize');
  const denominators=polls.map(poll=>{
    const designEffect=positive(options.useGlobalDesignEffect?config.designEffect??1.5:poll.designEffect??config.designEffect??1.5,'designEffect');
    const sampleSize=positive(options.sampleSizeField?poll[options.sampleSizeField]??500:poll.measurementSampleSize??poll.percentageSampleSize??poll.sampleSize??500,'sampleSize');
    return Math.max(minimumSampleSize,sampleSize)/designEffect;
  });
  // The ordinary forecast supplies its original global DEFF/sample-size policy;
  // signal/noise supplies its measurement sample size and row DEFF. Only the
  // off-diagonal covariance is new, never a silent change to either baseline.
  const independentVarianceScale=normalized.reduce((s,w,i)=>s+w*w/denominators[i],0);
  const variances=denominators.map(value=>1/value);
  let modeledVarianceScale=independentVarianceScale,details=null;
  if(isPollCorrelationEnabled(config)){
    details=getPollCorrelationMatrix(polls,calibration);
    for(let i=0;i<polls.length;i++)for(let j=i+1;j<polls.length;j++)modeledVarianceScale+=2*normalized[i]*normalized[j]*details.matrix[i][j]*Math.sqrt(variances[i]*variances[j]);
  }
  return {factor:modeledVarianceScale/independentVarianceScale,independentVarianceScale,modeledVarianceScale,
    nEffectiveIndependent:1/independentVarianceScale,nEffectiveModeled:1/modeledVarianceScale,
    ...(details?{profileId:details.profileId,eligibleInstitutes:details.eligibleInstitutes,unmodeledInstitutes:details.unmodeledInstitutes,
      unmodeledPairs:details.unmodeledPairs,unknownPairAssumption:details.unknownPairAssumption}:{}),
    correctedAt:'sampling_information_once',commonBlocSensitivityChanged:false};
}
