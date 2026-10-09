import {allocateSeats} from "./allocate.js";
import {seededRandom, gamma, binomial, multinomial, normalise, wilson} from "./random.js";
import {reconstructPoll} from "./reconstruct.js";
import {combineForecast,resolveForecastConfig} from './forecast.js';
import {sampleSignalNoise} from './signal-noise.js';
import {createTurnoutModel} from "./turnout.js";
import {createReportingGroupDefinitions,summarizeSeatHistogram} from "../reporting-groups.js";

export const BLOCS=["a","b","arab","other"];
export {summarizeSeatHistogram} from "../reporting-groups.js";
export function defaultConfig(input){
  return {
    asOf:input.current.asOf,iterations:50000,seed:20260912,registered:7336553,samplingMode:"poll",
    weightMode:"equal",pollCorrelationEnabled:false,pollWeights:{},excludedPolls:[],halfLifeDays:14,designEffect:1.5,
    scatterStrength:.65,commonBlocSD:1,uncertaintyScale:1,forecastDays:0,dailyDrift:.06,
    unreportedSmallPct:.5,rounding:true,partyBlocs:Object.fromEntries(input.parties.map(p=>[p.id,p.ballot===false?"other":p.defaultBloc==="a"?"a":p.defaultBloc==="b"?"b":"other"])),partyMultipliers:{},
    turnout:Object.fromEntries(input.turnout.groups.filter(g=>g.eligible>0).map(g=>[g.id,g.turnoutPct])),
    turnoutMappings:{},externalMultiplier:1,blocMultipliers:{a:1,b:1,arab:1,other:1},
    agreements:input.current.agreements.filter(a=>a.defaultEnabled).map(a=>a.id),customAgreements:[],
    coalitionA:{extraSupport:[],abstain:[],minority:false},
    coalitionB:{extraSupport:[],abstain:[],minority:false}
  };
}
function dirichlet(p,k,rng){
  if(!Number.isFinite(k)||k>1e12)return p.slice();
  const draw=p.map(v=>v>0?gamma(Math.max(1e-7,v*k),rng):0);
  return normalise(draw);
}
function choose(weights,rng){let u=rng();for(let i=0;i<weights.length;i++){u-=weights[i];if(u<=0)return i;}return weights.length-1;}
function roundVotes(n,p){const v=p.map(x=>Math.floor(n*x));let left=n-v.reduce((a,b)=>a+b,0);const order=p.map((x,i)=>({i,r:n*x-v[i]})).sort((a,b)=>b.r-a.r);for(let i=0;i<left;i++)v[order[i%order.length].i]++;return v;}
function roundExpectedVotes(means,total){
  const votes=means.map(Math.floor),left=total-votes.reduce((a,b)=>a+b,0);
  const order=means.map((v,i)=>({i,remainder:v-votes[i]})).sort((a,b)=>b.remainder-a.remainder);
  for(let i=0;i<left;i++)votes[order[i].i]++;
  return votes;
}
function coalitionOutcome(seats,parties,blocs,side,rules){
  let support=0,abstain=0;
  for(let j=0;j<seats.length;j++){
    if(blocs[j]===side||(rules.extraSupport||[]).includes(parties[j].id))support+=seats[j];
    else if((rules.abstain||[]).includes(parties[j].id))abstain+=seats[j];
  }
  return {support,success:rules.minority?support>120-support-abstain:support>=61};
}
export function createSimulation(input,options={}){
  const config=resolveForecastConfig({...defaultConfig(input),...options});
  if(!["poll","fixed"].includes(config.samplingMode))throw new Error("מצב הדגימה אינו מוכר.");
  if(!Number.isInteger(config.iterations)||config.iterations<1||config.iterations>1000000)throw new Error("מספר סימולציות לא תקין.");
  if(!Number.isSafeInteger(config.registered)||config.registered<100000)throw new Error("מספר בעלי זכות הבחירה אינו תקין.");
  for(const [key,min,max] of [["scatterStrength",0,1],["uncertaintyScale",0,10],["commonBlocSD",0,20],["forecastDays",0,3650],["dailyDrift",0,5],["designEffect",.01,100],["halfLifeDays",.01,3650],["unreportedSmallPct",0,50]]){
    if(!Number.isFinite(config[key])||config[key]<min||config[key]>max)throw new Error("פרמטר לא תקין: "+key);
  }
  for(const key of ["pollWeights","partyMultipliers","blocMultipliers"]){
    if(Object.values(config[key]||{}).some(v=>!Number.isFinite(v)||v<0))throw new Error("משקל חייב להיות מספר סופי ולא שלילי: "+key);
  }
  if(!Number.isFinite(config.seed)||!Number.isFinite(Date.parse(config.asOf)))throw new Error("תאריך או זרע אינם תקינים.");
  if(Object.values(config.partyBlocs||{}).some(b=>!BLOCS.includes(b)))throw new Error("שיוך גוש לא מוכר.");
  const parties=input.parties,partyIds=new Set(parties.map(p=>p.id)),ballotIds=new Set(parties.filter(p=>p.ballot!==false).map(p=>p.id));
  if(Object.keys(config.partyBlocs||{}).some(id=>!partyIds.has(id)))throw new Error("שיוך מתייחס לרשימה לא מוכרת.");
  config.partyBlocs=Object.fromEntries(parties.map(p=>[p.id,p.ballot===false?"other":config.partyBlocs?.[p.id]==="a"?"a":config.partyBlocs?.[p.id]==="b"?"b":"other"]));
  if(!Array.isArray(config.agreements)||config.agreements.some(id=>!input.current.agreements.some(a=>a.id===id)))throw new Error("נבחר הסכם עודפים לא מוכר.");
  for(const key of ["partyBlocs","partyMultipliers"]){
    if(Object.keys(config[key]||{}).some(id=>!partyIds.has(id)))throw new Error("הגדרה מתייחסת לרשימה לא מוכרת: "+key);
  }
  for(const key of ["coalitionA","coalitionB"]){
    const rules=config[key];
    if(!rules||typeof rules!=="object"||Array.isArray(rules))throw new Error("כללי קואליציה אינם תקינים.");
    for(const relation of ["extraSupport","abstain"]){
      const ids=rules[relation]??[];
      if(!Array.isArray(ids)||ids.some(id=>!ballotIds.has(id)))throw new Error("כלל קואליציה כולל רשימה לא מוכרת: "+key);
    }
    if(rules.minority!==undefined&&typeof rules.minority!=="boolean")throw new Error("כלל ממשלת מיעוט אינו תקין.");
  }
  const combinationConfig=config.samplingMode==="fixed"?{...config,rounding:false}:config;
  const combined=combineForecast(input,combinationConfig);
  const signalNoise=Boolean(combined.signalNoise);
  const turnoutModel=createTurnoutModel(input.turnout,parties,config);
  const mask=parties.map(p=>p.ballot!==false);
  const blocs=parties.map(p=>config.partyBlocs[p.id]);
  const byBloc=BLOCS.map(b=>blocs.map((v,i)=>v===b?i:-1).filter(i=>i>=0));
  const reportingGroups=createReportingGroupDefinitions(parties,config).map(group=>({...group,hist:new Array(121).fill(0)}));
  // Coalition scenarios do not redefine the shared-error process. Only explicit
  // motivation factors use the user's bloc classification to change support.
  const errorBlocs=parties.map(p=>p.defaultBloc||"other");
  const byErrorBloc=BLOCS.map(b=>errorBlocs.map((v,i)=>v===b?i:-1).filter(i=>i>=0));
  const agreements=[...input.current.agreements.filter(a=>config.agreements.includes(a.id)).map(a=>a.parties),...(config.customAgreements||[])]
    .map(pair=>pair.map(id=>parties.findIndex(p=>p.id===id)));
  if(agreements.some(pair=>pair.some(i=>i<0)))throw new Error("הסכם עודפים כולל רשימה לא מוכרת.");
  const partyMult=parties.map(p=>Math.max(0,config.partyMultipliers?.[p.id]??1));
  const pointPre=normalise(combined.center.map((p,j)=>p*partyMult[j]));
  const point=turnoutModel.adjust(pointPre);
  const invalidRate=input.turnout.national.invalid/input.turnout.national.voters;
  const pointVotes=roundVotes(Math.round(config.registered*point.turnoutRate*(1-invalidRate)),point.probabilities);
  // Validate the complete agreement set before starting a potentially long run.
  const pollPointAllocation=allocateSeats(pointVotes,agreements,{eligibleMask:mask,rng:seededRandom(config.seed)});
  const totals=parties.map(()=>({hist:new Array(121).fill(0),voteHist:new Array(1001).fill(0),sum:0,sumSq:0,voteSum:0,voteCountSum:0,pass:0,passA:0,failA:0,passB:0,failB:0,passASeats:0,failASeats:0,passBSeats:0,failBSeats:0,worldPass:null,worldFail:null}));
  const blocHist=Object.fromEntries(BLOCS.map(b=>[b,new Array(121).fill(0)]));
  const coalitionHist={coalitionA:new Array(121).fill(0),coalitionB:new Array(121).fill(0)};
  const counts={a:0,b:0,neither:0,coalitionA:0,coalitionB:0,coalitionNeither:0,coalitionBoth:0};
  let done=0,ballotSum=0,validSum=0,turnoutSum=0,eachWorld120=true,blocPartition120=true;
  // The local-level posterior already projects Q over the requested horizon.
  // Keep the separate shared-error sensitivity once; do not add legacy drift.
  const commonSD=Math.sqrt(config.commonBlocSD**2+(signalNoise?0:config.dailyDrift**2*config.forecastDays))/100;
  const sampleK=config.uncertaintyScale>0?Math.max(1,combined.nEffective/config.uncertaintyScale**2):Infinity;
  const worlds=[];
  function trial(i){
    const rng=seededRandom((Number(config.seed)+Math.imul(i+1,0x9e3779b1))>>>0);
    const ballotRng=seededRandom((Number(config.seed)^Math.imul(i+1,0x85ebca6b))>>>0);
    let p=combined.center.slice();
    if(config.samplingMode==="poll"){
      if(signalNoise){
        p=sampleSignalNoise(combined,rng,config.forecastDays);
      }else{
      const which=choose(combined.weights,rng),alpha=config.scatterStrength;
      const selected=config.rounding?reconstructPoll(combined.polls[which],parties,{...config,rng,rounding:true}).probabilities:combined.recon[which].probabilities;
      p=combined.center.map((v,j)=>(1-alpha)*v+alpha*selected[j]);
      p=dirichlet(p,sampleK,rng);
      }
      if(commonSD>0){
        const masses=byErrorBloc.map(indices=>indices.reduce((s,j)=>s+p[j],0));
        // Bloc A fixes the reference SD; other bloc SDs follow the same joint concentration.
        const ref=Math.max(.01,Math.min(.99,masses[0]));
        const k=Math.max(1,ref*(1-ref)/(commonSD*commonSD)-1);
        const drawn=dirichlet(masses,k,rng);
        p=p.map((v,j)=>{const b=BLOCS.indexOf(errorBlocs[j]);return masses[b]>0?v*drawn[b]/masses[b]:v;});
      }
    }
    p=normalise(p.map((v,j)=>v*partyMult[j]));
    const adjusted=turnoutModel.adjust(p);
    const ballots=binomial(config.registered,adjusted.turnoutRate,ballotRng);
    const valid=binomial(ballots,1-invalidRate,ballotRng);
    const votes=multinomial(valid,adjusted.probabilities,ballotRng);
    const allocated=allocateSeats(votes,agreements,{eligibleMask:mask,rng:ballotRng});
    const bs=Object.fromEntries(BLOCS.map((b,k)=>[b,byBloc[k].reduce((s,j)=>s+allocated.seats[j],0)]));
    eachWorld120=eachWorld120&&allocated.seats.reduce((sum,seats)=>sum+seats,0)===120;
    blocPartition120=blocPartition120&&bs.a+bs.b+bs.other===120&&bs.arab===0;
    for(const b of BLOCS)blocHist[b][bs[b]]++;
    for(const group of reportingGroups){
      const seats=group.partyIndices.reduce((sum,j)=>sum+allocated.seats[j],0);
      group.hist[seats]++;
    }
    const a=bs.a>=61,b=bs.b>=61;
    if(a)counts.a++;if(b)counts.b++;if(!a&&!b)counts.neither++;
    const outcomeA=coalitionOutcome(allocated.seats,parties,blocs,"a",config.coalitionA);
    const outcomeB=coalitionOutcome(allocated.seats,parties,blocs,"b",config.coalitionB);
    const ca=outcomeA.success,cb=outcomeB.success;
    coalitionHist.coalitionA[outcomeA.support]++;
    coalitionHist.coalitionB[outcomeB.support]++;
    counts.coalitionA+=+ca;counts.coalitionB+=+cb;counts.coalitionNeither+=+(!ca&&!cb);counts.coalitionBoth+=+(ca&&cb);
    const world={iteration:i+1,probabilities:adjusted.probabilities,votes,seats:allocated.seats,passed:allocated.passed,valid,ballots,blocs:bs};
    if(worlds.length<6)worlds.push(world);
    for(let j=0;j<parties.length;j++){
      const t=totals[j],s=allocated.seats[j],pass=allocated.passed[j],share=votes[j]/valid*100;
      t.hist[s]++;t.sum+=s;t.sumSq+=s*s;t.voteSum+=share;t.voteCountSum+=votes[j];t.voteHist[Math.min(1000,Math.floor(share*10))]++;
      if(pass){t.pass++;t.passA+=+a;t.passB+=+b;t.passASeats+=bs.a;t.passBSeats+=bs.b;if(!t.worldPass)t.worldPass=world;}
      else{t.failA+=+a;t.failB+=+b;t.failASeats+=bs.a;t.failBSeats+=bs.b;if(!t.worldFail)t.worldFail=world;}
    }
    ballotSum+=ballots;validSum+=valid;turnoutSum+=adjusted.turnoutRate;
  }
  return {
    step(n=500){const end=Math.min(config.iterations,done+n);for(;done<end;done++)trial(done);return {done,total:config.iterations};},
    get done(){return done;},
    finish(){
      if(done!==config.iterations)throw new Error("הסימולציה טרם הסתיימה.");
      const meanVotes=totals.map(t=>t.voteCountSum/done);
      const expectedVotesRounded=roundExpectedVotes(meanVotes,Math.round(validSum/done));
      const expectedVoteAllocation=allocateSeats(expectedVotesRounded,agreements,{eligibleMask:mask,rng:seededRandom(config.seed)});
      return {schemaVersion:1,generatedAt:new Date().toISOString(),config,iterations:done,singleElection:done===1,
        calibrationStatus:config.samplingMode==="fixed"
          ?"ההסתברויות לבוחר קבועות לפי שקלול הסקרים והתרחיש. ההגרלות מייצגות הצבעות עצמאיות בהינתן הסתברויות אלה; הן אינן כוללות שגיאת סקר או שינוי עתידי בתמיכה."
          :"הסתברויות מותנות במודל; הכיול ההיסטורי בודק תחזיות נקודה ואינו מאמת את ההסתברויות.",
        parties:parties.map((p,j)=>{const t=totals[j];return {...p,bloc:blocs[j],...summarizeSeatHistogram(t.hist),
          passProbability:t.pass/done,failProbability:1-t.pass/done,passCI:wilson(t.pass,done),
          meanIfPass:t.pass?t.sum/t.pass:null,meanVotePct:t.voteSum/done,meanVotes:meanVotes[j],
          pointSeats:expectedVoteAllocation.seats[j],pollPointSeats:pollPointAllocation.seats[j],hist:t.hist,voteHist:t.voteHist,
          conditional:{passA:t.pass?t.passA/t.pass:null,failA:t.pass<done?t.failA/(done-t.pass):null,
            passB:t.pass?t.passB/t.pass:null,failB:t.pass<done?t.failB/(done-t.pass):null,
            passASeats:t.pass?t.passASeats/t.pass:null,failASeats:t.pass<done?t.failASeats/(done-t.pass):null},
          worldPass:t.worldPass,worldFail:t.worldFail,
          hasModelledSupport:signalNoise?combined.center[j]>0:combined.recon.some(r=>r.probabilities[j]>0),hasRawReportedSupport:signalNoise?(combined.signalNoise.parties[p.id]?.count??0)>0:combined.polls.some(poll=>Object.hasOwn(poll.percentages||{},p.id))};}),
        blocHist,blocStats:Object.fromEntries(BLOCS.map(b=>[b,summarizeSeatHistogram(blocHist[b])])),
        reportingGroups:reportingGroups.map(({partyIndices,...group})=>({...group,stats:summarizeSeatHistogram(group.hist),empty:group.partyIds.length===0,status:done===1?"single":"ready",source:"joint-simulation"})),
        coalitionHist,coalitionStats:Object.fromEntries(Object.entries(coalitionHist).map(([key,hist])=>[key,summarizeSeatHistogram(hist)])),
        meanCIDefinition:{level:.95,method:"normal approximation using sample variance",scope:"Monte Carlo error of mean seats; not election outcome uncertainty",singleElection:"unavailable"},
        seatDistributionDefinition:{mean:"frequency-weighted mean of all simulated seat counts",quantileMethod:"discrete inverse empirical CDF: smallest integer with cumulative count >= q*n",median:{q:.5,convention:"lower median; no averaging of central outcomes"},low:{q:.05},high:{q:.95},intervalScope:"5th to 95th percentiles of simulated election outcomes conditional on the model; not a 95% confidence interval for the mean",discreteCoverage:"inclusive coverage may exceed 90% because seat counts are discrete",singleElection:"the one observed seat count; not an estimated outcome distribution"},
        counts,probabilities:Object.fromEntries(Object.entries(counts).map(([k,v])=>[k,v/done])),
        probabilityCI:Object.fromEntries(Object.entries(counts).map(([k,v])=>[k,wilson(v,done)])),
        meanBallots:ballotSum/done,meanValid:validSum/done,meanTurnout:turnoutSum/done,worlds,
        pollWeights:combined.polls.map((p,i)=>({id:p.id,pollsterId:p.pollsterId,pollster:p.pollster,publisher:p.publisher,weight:combined.weights[i],sampleSize:p.sampleSize,reconstructed:combined.recon[i].reconstructed,notes:combined.recon[i].notes})),
        nEffective:combined.nEffective,methodWeights:combined.methodWeights,weightContributions:combined.contributions,weightNotes:combined.weightNotes||combined.notes,pointProbabilities:point.probabilities,
        ...(combined.pollCorrelation?{pollCorrelation:combined.pollCorrelation}:{}),
        ...(signalNoise?{signalNoise:combined.signalNoise}:{}),
        pollPointSeatsDefinition:"Bader-Ofer applied to weighted central poll support after turnout and party adjustments, threshold and surplus agreements, before simulation draws",
        expectedVotesRounded,pointSeatsDefinition:"Bader-Ofer applied to mean simulated vote counts, rounded preserving the total",
        turnout:{exposures:turnoutModel.exposures,notes:turnoutModel.notes,baselineRates:turnoutModel.baselineRates},
        assumptions:{samplingMode:config.samplingMode,errorBlocs:Object.fromEntries(parties.map((p,j)=>[p.id,errorBlocs[j]])),commonBlocSD:config.commonBlocSD,dailyDrift:config.dailyDrift,forecastDays:config.forecastDays,
          scatterStrength:config.scatterStrength,designEffect:config.designEffect,rounding:config.rounding,
          unreportedSmallPct:config.unreportedSmallPct,uncalibrated:true,
          ...(signalNoise?{effectiveNoiseModel:'local_level_posterior_plus_shared_bloc_sensitivity_once',signalNoiseEnabled:true,ignoredLegacyNoise:['scatterStrength','seat_rounding','dailyDrift'],weightingPolicyAppliedAt:'measurement_variance_once',weightMode:config.weightMode,forecastMean:'constant_local_level',forecastVariance:'posterior_variance_plus_fitted_Q_times_forecastDays'}:{})},
        checks:{seatsSum:totals.reduce((s,t)=>s+t.sum,0)/done,eachWorld120,blocPartition120,probabilityTotal:counts.a/done+counts.b/done+counts.neither/done}
      };
    }
  };
}
export function runSimulation(input,config){const job=createSimulation(input,config);job.step(config?.iterations||50000);return job.finish();}
