import {summarizeSeatHistogram} from "./model/simulate.js";

export const SEAT_DISTRIBUTION_METADATA=Object.freeze({
 method:"full empirical frequency histogram; one bin per integer seat count, 0..120",
 statisticSource:"all completed runs, with no representative sampling, rare-outcome cutoff or smoothing",
 probability:"bin count divided by the total completed runs",
 quantileMethod:"discrete inverse empirical CDF; lower median",
 singleElection:"one observed result, not an estimated probability distribution"
});

export function summarizeSeatDistribution(hist,iterations){
 const empty={status:"unavailable",total:null,mean:null,median:null,low:null,high:null,distribution:[],metadata:SEAT_DISTRIBUTION_METADATA};
 if(!Array.isArray(hist)||hist.length!==121||!Number.isSafeInteger(iterations)||iterations<1)return empty;
 let total=0;
 for(let seats=0;seats<=120;seats++){
  if(!Number.isSafeInteger(hist[seats])||hist[seats]<0)return empty;
  total+=hist[seats];if(!Number.isSafeInteger(total))return empty;
 }
 if(total!==iterations)return empty;
 const {mean,median,low,high}=summarizeSeatHistogram(hist);
 return {status:total===1?"single":"ready",total,mean,median,low,high,
  distribution:hist.map((count,seats)=>({seats,count,probability:count/total})),metadata:SEAT_DISTRIBUTION_METADATA};
}
