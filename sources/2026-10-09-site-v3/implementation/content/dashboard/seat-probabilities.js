import {wilson} from "./model/random.js";

export const SEAT_COMPARISON_LABELS=Object.freeze({exact:"בדיוק",atLeast:"לפחות",atMost:"לכל היותר"});

const validSeatTarget=value=>Number.isInteger(value)&&value>=0&&value<=120;

/** A null target follows the deterministic allocation of the weighted poll
 * support after turnout adjustments. Explicit targets remain manual until reset.
 * Loading/errors never expose a previous run's forecast as the current target.
 */
export function resolveSeatQuestionTarget(party,requestedTarget,{busy=false,error=false}={}){
  const isAutomatic=requestedTarget==null;
  const manualTarget=validSeatTarget(requestedTarget)?requestedTarget:null;
  const empty=status=>({status,isAutomatic,target:isAutomatic?null:manualTarget,predictedSeats:null});
  if(busy)return empty("loading");
  if(error)return empty("error");
  if(!party)return empty("unavailable");
  if(!hasSeatProbabilitySupport(party))return empty("unmodelled");
  const predictedSeats=validSeatTarget(party.pollPointSeats)?party.pollPointSeats:null;
  const target=isAutomatic?predictedSeats:manualTarget;
  return {status:target===null?"unavailable":"ready",isAutomatic,target,predictedSeats};
}

/** Selecting a different party starts from that party's own forecast. Changing
 * comparison or global model settings preserves an explicitly selected target.
 */
export function updateSeatQuestion(question,changes){
  const next={...question,...changes};
  if(changes.partyId!==undefined&&changes.partyId!==question.partyId)next.target=null;
  return next;
}

function matches(seats,target,comparison){
  return comparison==="exact"?seats===target:comparison==="atLeast"?seats>=target:seats<=target;
}

// Keep the support rule compatible with ThresholdPage, including older results
// saved before hasModelledSupport was added to the simulation schema.
export function hasSeatProbabilitySupport(party){
  return party?.hasModelledSupport===true||(party?.hasModelledSupport==null&&Number(party?.meanVotePct)>0);
}

/**
 * Read a completed party seat histogram without changing or rerunning the model.
 * `target` is an integer 0..120 and `comparison` is exact / atLeast / atMost.
 * Ready probabilities are frequencies on [0,1]; ci is the existing model's 95%
 * Wilson interval for Monte Carlo sampling error, not election uncertainty.
 * Every ready distribution has all 121 bins, including observed zero counts.
 * Non-ready states have null probability/ci and an empty distribution. Valid
 * single-run data retain the observed count/total; unmodelled data retain only
 * the total. Invalid/missing inputs return unavailable and null count/total.
 */
export function analyzeSeatProbability(party,iterations,target,comparison){
  const empty=(status,count=null,total=null)=>({status,count,total,probability:null,ci:null,distribution:[]});
  if(!party||!Number.isSafeInteger(iterations)||iterations<1||!Number.isInteger(target)||target<0||target>120||typeof comparison!=="string"||!Object.hasOwn(SEAT_COMPARISON_LABELS,comparison))return empty("unavailable");
  if(!Array.isArray(party.hist)||party.hist.length!==121)return empty("unavailable");
  let total=0,count=0;
  for(let seats=0;seats<=120;seats++){
    const frequency=party.hist[seats];
    if(!Number.isSafeInteger(frequency)||frequency<0)return empty("unavailable");
    total+=frequency;
    if(!Number.isSafeInteger(total))return empty("unavailable");
    if(matches(seats,target,comparison))count+=frequency;
  }
  // A partial run or mismatched denominator must never look like a probability.
  if(total!==iterations)return empty("unavailable");
  if(!hasSeatProbabilitySupport(party))return empty("unmodelled",null,total);
  if(total===1)return empty("single",count,total);
  return {status:"ready",count,total,probability:count/total,ci:wilson(count,total),
    distribution:party.hist.map((frequency,seats)=>({seats,count:frequency,probability:frequency/total,selected:matches(seats,target,comparison)}))};
}
