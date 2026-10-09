import {ARAB_IDS} from "./bloc-presets.js";
import {quantileHistogram} from "./model/random.js";

const DEFINITIONS=Object.freeze([
  {id:"a",label:"הקואליציה הנוכחית",color:"#dc454c"},
  {id:"b",label:"האופוזיציה",color:"#2378cf"},
  {id:"arab",label:"המפלגות הערביות מחוץ לגושים",color:"#87909d"},
  {id:"other",label:"שאר הרשימות מחוץ לגושים",color:"#87909d"}
]);
const ARAB_PARTIES=new Set(ARAB_IDS);
const blocFor=(party,config)=>config?.partyBlocs?.[party.id]??party.bloc??party.defaultBloc??"other";
const sameMembers=(left,right)=>Array.isArray(left)&&Array.isArray(right)&&left.length===right.length&&new Set(left).size===left.length&&left.every(id=>right.includes(id));
const validHistogram=(hist,iterations)=>Array.isArray(hist)&&hist.length===121&&Number.isSafeInteger(iterations)&&iterations>0&&hist.every(count=>Number.isSafeInteger(count)&&count>=0)&&hist.reduce((sum,count)=>sum+count,0)===iterations;

// Approximate 95% Monte Carlo CI for the expected seat count. This estimates
// simulation error, not the interval containing 95% of election outcomes.
// Compute the sample variance from the joint seat histogram so bloc/coalition
// covariance is preserved rather than adding party standard errors.
export function summarizeSeatHistogram(hist){
  const n=hist.reduce((s,count)=>s+count,0);
  if(!n)return {mean:null,meanSE:null,meanMargin:null,meanCI:null,median:null,low:null,high:null};
  const mean=hist.reduce((s,count,seats)=>s+count*seats,0)/n;
  // Discrete inverse empirical CDF: the smallest integer seat count whose
  // cumulative count reaches q*n. For an even sample this is the lower median,
  // never the average of the two central outcomes.
  const median=quantileHistogram(hist,.5),low=quantileHistogram(hist,.05),high=quantileHistogram(hist,.95);
  if(n===1)return {mean,meanSE:null,meanMargin:null,meanCI:null,median,low,high};
  const variance=hist.reduce((s,count,seats)=>s+count*(seats-mean)**2,0)/(n-1);
  const meanSE=Math.sqrt(variance/n),meanMargin=1.96*meanSE;
  return {mean,meanSE,meanMargin,meanCI:[mean-meanMargin,mean+meanMargin],median,low,high};
}
/** Reporting is separate from political membership, motivation and error blocs.
 * Partition ballot lists into a, b, Arab lists outside both, and other lists
 * outside both. The last two are omitted when they have no member lists.
 * Excluded non-ballot residuals cannot receive seats and are not party members.
 */
export function createReportingGroupDefinitions(parties=[],config={}){
  const groups=DEFINITIONS.map(group=>({...group,partyIds:[],partyIndices:[]}));
  parties.forEach((party,index)=>{
    if(party.ballot===false)return;
    const bloc=blocFor(party,config);
    const id=bloc==="a"||bloc==="b"?bloc:ARAB_PARTIES.has(party.id)?"arab":"other";
    const group=groups.find(item=>item.id===id);
    group.partyIds.push(party.id);group.partyIndices.push(index);
  });
  return groups.filter(group=>group.id==="a"||group.id==="b"||group.partyIds.length>0);
}

/** Read completed reporting histograms without inventing a joint distribution.
 * Old result compatibility is exact only: an identically composed old bloc, a
 * single party, or an empty a/b group. Never convolve marginal histograms or add
 * variances/quantiles of parties whose simulated outcomes are correlated.
 */
export function getReportingGroups(result,input){
  const parties=result?.parties??input?.parties??[];
  const config=result?.config??{};
  const iterations=result?.iterations;
  return createReportingGroupDefinitions(parties,config).map(({partyIndices,...group})=>{
    const saved=(Array.isArray(result?.reportingGroups)?result.reportingGroups:[]).find(item=>item?.id===group.id&&sameMembers(item.partyIds,group.partyIds));
    let hist=null,source="unavailable";
    if(saved&&validHistogram(saved.hist,iterations)){hist=saved.hist;source="joint-simulation";}
    else {
      const legacy=Object.entries(result?.blocHist??{}).find(([id,candidate])=>{
        const members=parties.filter(party=>party.ballot!==false&&blocFor(party,config)===id).map(party=>party.id);
        return sameMembers(members,group.partyIds)&&validHistogram(candidate,iterations);
      });
      if(legacy){hist=legacy[1];source="legacy-bloc";}
      else if(group.partyIds.length===1){
        const party=parties.find(item=>item.id===group.partyIds[0]);
        if(validHistogram(party?.hist,iterations)){hist=party.hist;source="single-party";}
      }else if(group.partyIds.length===0&&Number.isSafeInteger(iterations)&&iterations>0){
        hist=Array(121).fill(0);hist[0]=iterations;source="empty";
      }
    }
    const stats=summarizeSeatHistogram(hist??[]);
    return {...group,hist,stats,empty:group.partyIds.length===0,status:hist?(iterations===1?"single":"ready"):"unavailable",source};
  });
}
