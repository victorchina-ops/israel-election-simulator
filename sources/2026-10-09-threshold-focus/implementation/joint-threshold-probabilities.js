import {wilson} from "./model/random.js";

// Preserve the threshold page's support rule, including older result metadata.
// Missing separate support must never become a certain threshold failure.
const hasSupport=party=>party?.hasModelledSupport===true||(party?.hasModelledSupport==null&&Number(party?.meanVotePct)>0);

/**
 * Query the complete joint threshold histogram from the same simulation run.
 * A failed bit is the allocator's exact threshold verdict, not a binned vote
 * share or a seat-count proxy. No independence assumption is introduced.
 *
 * atLeastTwo counts at least two failures among the selected parties; allFail
 * counts failure of every selected party. At least two distinct modeled ballot
 * parties are required. Duplicate selection IDs are normalized once.
 *
 * Ready probabilities are frequencies on [0,1], with a 95% Wilson interval for
 * Monte Carlo sampling error, not election uncertainty. Single-run data retain
 * the observed count/total but expose no probability or distribution. Every
 * non-ready result has null probability/ci and an empty distribution.
 */
export function analyzeJointThreshold(result,selectedIds,mode="atLeastTwo"){
  const validSelection=Array.isArray(selectedIds)&&selectedIds.every(id=>typeof id==="string"&&id.length>0);
  const ids=validSelection?[...new Set(selectedIds)]:[];
  const empty=(status,count=null,total=null)=>({status,count,total,probability:null,ci:null,distribution:[],selectedIds:ids});
  if(!validSelection||ids.length<2||!["atLeastTwo","allFail"].includes(mode))return empty("selection");
  if(!Array.isArray(result?.parties)||!Number.isSafeInteger(result.iterations)||result.iterations<1)return empty("unavailable");

  const parties=new Map();
  for(const party of result.parties){
    if(!party||typeof party.id!=="string"||!party.id||parties.has(party.id))return empty("unavailable");
    parties.set(party.id,party);
  }
  if(ids.some(id=>!parties.has(id)||parties.get(id).ballot===false))return empty("selection");

  const joint=result.thresholdJoint,ballotIds=result.parties.filter(party=>party.ballot!==false).map(party=>party.id);
  if(!joint||!Array.isArray(joint.partyIds)||joint.partyIds.length!==ballotIds.length||!Array.isArray(joint.patterns)||!joint.patterns.length||joint.total!==result.iterations)return empty("unavailable");
  const indices=new Map();
  for(let j=0;j<joint.partyIds.length;j++){
    const id=joint.partyIds[j];
    if(typeof id!=="string"||indices.has(id)||!parties.has(id)||parties.get(id).ballot===false)return empty("unavailable");
    indices.set(id,j);
  }
  if(ballotIds.some(id=>!indices.has(id)))return empty("unavailable");

  const selectedIndices=ids.map(id=>indices.get(id)),counts=new Array(ids.length+1).fill(0),seen=new Set();
  let total=0;
  for(const pattern of joint.patterns){
    if(!pattern||typeof pattern.failed!=="string"||pattern.failed.length!==joint.partyIds.length||!/^[01]+$/.test(pattern.failed)||seen.has(pattern.failed)||!Number.isSafeInteger(pattern.count)||pattern.count<0)return empty("unavailable");
    seen.add(pattern.failed);
    total+=pattern.count;
    if(!Number.isSafeInteger(total))return empty("unavailable");
    const failedCount=selectedIndices.reduce((sum,j)=>sum+(pattern.failed[j]==="1"?1:0),0);
    counts[failedCount]+=pattern.count;
  }
  // Reject incomplete runs and incompatible denominators before any inference.
  if(total!==joint.total)return empty("unavailable");
  if(ids.some(id=>!hasSupport(parties.get(id))))return empty("unmodelled",null,total);
  const count=mode==="allFail"?counts[ids.length]:counts.slice(2).reduce((sum,frequency)=>sum+frequency,0);
  if(total===1)return empty("single",count,total);
  return {status:"ready",count,total,probability:count/total,ci:wilson(count,total),
    distribution:counts.map((frequency,failedCount)=>({failedCount,count:frequency,probability:frequency/total})),selectedIds:ids};
}
