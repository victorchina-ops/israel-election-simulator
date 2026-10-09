import {normalise, seededRandom} from "./random.js";
import {selectActivePolls, computePollWeights} from "./weights.js";
import {covarianceInflation} from './poll-correlation.js';

export function reconstructPoll(poll,parties,{rounding=false,rng=seededRandom(120),unreportedSmallPct=0.5}={}){
  const values=parties.map(()=>null), notes=[], index=new Map(parties.map((p,i)=>[p.id,i]));
  const pct=poll.percentages||{},seats=poll.seats||{};
  if(!Number.isFinite(unreportedSmallPct)||unreportedSmallPct<0||unreportedSmallPct>100)throw new Error("יתרת אחוזים להשלמה אינה תקינה.");
  for(const [id,v] of Object.entries(pct)){
    if(!index.has(id))throw new Error("אחוזים פורסמו לרשימה לא מוכרת: "+id);
    if(!Number.isFinite(v)||v<0||v>100)throw new Error("אחוז תמיכה לא תקין בסקר "+poll.id+": "+id);
    values[index.get(id)]=v;
  }
  const known=values.reduce((s,v)=>s+(v??0),0);
  if(known>100.001)throw new Error("Poll percentages exceed 100: "+poll.id);
  const missingSeat=parties.map((p,i)=>({p,i,s:seats[p.id]})).filter(({i,s})=>values[i]===null&&Number.isFinite(s)&&s>0);
  const other=index.get("other");
  if(missingSeat.length){
    const hasPartialRaw=Object.keys(pct).some(id=>(seats[id]||0)>0);
    // A reported other-list share already supplies the reserve; do not withhold it twice.
    const reserve=hasPartialRaw||(other!==undefined&&values[other]!==null)?0:Math.min(unreportedSmallPct,Math.max(0,100-known));
    const pool=100-known-reserve;
    const seatWeights=missingSeat.map(({s})=>Math.max(.1,s+(rounding?(rng()-.5):0)));
    if(pool < 3.25*missingSeat.length)throw new Error("Published seats and percentages cannot be reconciled: "+poll.id);
    // A reported passing list constrains the latent poll estimate, not the election draw.
    let remaining=pool, free=seatWeights.map((_,k)=>k);
    while(free.length){
      const denom=free.reduce((s,k)=>s+seatWeights[k],0);
      const below=free.filter(k=>remaining*seatWeights[k]/denom<3.25);
      if(!below.length){free.forEach(k=>values[missingSeat[k].i]=remaining*seatWeights[k]/denom);break;}
      below.forEach(k=>{values[missingSeat[k].i]=3.25;remaining-=3.25;});
      free=free.filter(k=>!below.includes(k));
    }
    if(other!==undefined&&values[other]===null)values[other]=reserve;
    notes.push("אחוזי חלק מהרשימות שוחזרו ממנדטים, לאחר שמירת האחוזים שפורסמו. השחזור אינו נתוני גלם.");
  }else{
    // Decimal percentages totaling 100 can exceed it by floating-point epsilon.
    const remaining=Math.max(0,100-known);
    if(other!==undefined&&values[other]===null)values[other]=remaining;
    else if(remaining>.001&&other!==undefined)values[other]+=remaining;
    if(remaining>.1)notes.push("יתרת אחוזים שלא דווחה נשמרה כאחרים שאינם רשימה מאוחדת.");
  }
  const unresolved=parties.filter((p,i)=>values[i]===null&&p.ballot!==false&&seats[p.id]===undefined);
  if(unresolved.length)notes.push("רשימות שלא נמדדו בנפרד כלולות ביתרה, אם ישנה; אין כאן מדידת תמיכה אפס.");
  return {id:poll.id,probabilities:normalise(values.map(v=>(v??0)/100)),notes,reconstructed:missingSeat.length>0,unresolved:unresolved.map(p=>p.id)};
}

export function combinePolls(polls,parties,config,calibration={}){
  const active=selectActivePolls(polls,config);
  // The point reconstruction must not consume a seed or rounding jitter. Only
  // each trial reconstructs rounded seat reports with its own stochastic draw.
  const recon=active.map(p=>reconstructPoll(p,parties,{...config,rounding:false}));
  const weighting=computePollWeights(active,config,calibration,{probabilities:recon.map(r=>r.probabilities)});
  const weights=weighting.weights;
  const center=parties.map((_,j)=>weights.reduce((sum,w,i)=>sum+w*recon[i].probabilities[j],0));
  const designEffect=config.designEffect??1.5;
  if(!Number.isFinite(designEffect)||designEffect<=0)throw new Error("אפקט התכנון חייב להיות חיובי וסופי.");
  for(const poll of active)if(poll.sampleSize!=null&&(!Number.isFinite(poll.sampleSize)||poll.sampleSize<=0))throw new Error("גודל מדגם לא תקין: "+poll.id);
  // A blend changes these same unique poll weights, never the observation count.
  const invN=weights.reduce((s,w,i)=>s+w*w/(Math.max(100,active[i].sampleSize??500)/designEffect),0);
  const information=weighting.pollCorrelation?covarianceInflation(active,weights,config,calibration,{weightsAreNormalized:true,useGlobalDesignEffect:true,sampleSizeField:'sampleSize'}):null;
  return {polls:active,weights,center,nEffective:information?.nEffectiveModeled??1/invN,recon,assumedSampleSizes:active.filter(p=>p.sampleSize==null).map(p=>p.id),methodWeights:weighting.methodWeights,contributions:weighting.contributions,weightNotes:weighting.notes,notes:weighting.notes,
    ...(weighting.pollCorrelation?{pollCorrelation:{...weighting.pollCorrelation,informationCorrection:information}}:{})};
}
