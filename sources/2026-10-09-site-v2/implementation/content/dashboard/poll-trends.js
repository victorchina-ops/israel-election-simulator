import {combinePolls} from './model/reconstruct.js';
import {selectActivePolls} from './model/weights.js';

export const DEFAULT_TREND_MAX_AGE_DAYS=21;
export const DEFAULT_TREND_MIN_POLLS=2;
// Candidate lists closed late on 8 September. Poll history is day-grained, so
// the first unambiguously post-deadline publication day is 9 September.
export const POST_LISTS_CUTOFF_DATE='2026-09-09';

const DAY_MS=86_400_000;
const own=(object,key)=>Object.prototype.hasOwnProperty.call(object??{},key);

function dateKey(value,label='date'){
  if(typeof value!=='string'||!value.trim())throw new Error(`Missing ${label}.`);
  const match=value.match(/^(\d{4}-\d{2}-\d{2})/);
  const parsed=Date.parse(value);
  if(!Number.isFinite(parsed))throw new Error(`Invalid ${label}: ${value}`);
  return match?.[1]??new Date(parsed).toISOString().slice(0,10);
}

function pollDate(poll){return dateKey(poll?.date??poll?.fieldworkEnd,`poll date (${poll?.id??'unknown'})`);}
function dayNumber(value){return Date.parse(`${dateKey(value)}T00:00:00.000Z`);}

function validateHistory(polls){
  if(!Array.isArray(polls))throw new Error('historicalPolls must be an array.');
  const ids=new Set();
  for(const poll of polls){
    if(!poll||typeof poll.id!=='string'||typeof poll.pollsterId!=='string')throw new Error('Every historical poll needs id and pollsterId.');
    if(ids.has(poll.id))throw new Error(`Duplicate historical poll id: ${poll.id}`);
    ids.add(poll.id);pollDate(poll);
  }
}

/** Resolve the user's current poll cards to pollster-level history selection. */
export function getSelectedPollsterIds(currentPolls,config={}){
  const active=selectActivePolls(currentPolls,config),seen=new Set(),ids=[];
  for(const poll of active)if(!seen.has(poll.pollsterId)){seen.add(poll.pollsterId);ids.push(poll.pollsterId);}
  return ids;
}

/** Latest non-stale observation for every selected pollster at one checkpoint. */
export function latestPollsAtCheckpoint(historicalPolls,selectedPollsterIds,checkpoint,{maxAgeDays=DEFAULT_TREND_MAX_AGE_DAYS}={}){
  if(!Number.isFinite(maxAgeDays)||maxAgeDays<0)throw new Error('maxAgeDays must be a finite non-negative number.');
  const checkpointKey=dateKey(checkpoint,'checkpoint'),checkpointDay=dayNumber(checkpointKey),selected=new Set(selectedPollsterIds),latest=new Map();
  for(const poll of historicalPolls){
    if(!selected.has(poll.pollsterId))continue;
    const key=pollDate(poll),ageDays=(checkpointDay-dayNumber(key))/DAY_MS;
    if(ageDays<0||ageDays>maxAgeDays)continue;
    const previous=latest.get(poll.pollsterId);
    if(!previous||key>previous.key||(key===previous.key&&poll.id.localeCompare(previous.poll.id)<0))latest.set(poll.pollsterId,{key,poll});
  }
  return selectedPollsterIds.map(id=>latest.get(id)?.poll).filter(Boolean);
}

function publishedSeatMetrics(polls,weights,parties){
  return parties.map(party=>{
    const reports=[];
    polls.forEach((poll,index)=>{
      if(!own(poll.seats,party.id)||!Number.isFinite(poll.seats[party.id]))return;
      if(poll.seats[party.id]<0)throw new Error(`Negative published seats in ${poll.id}: ${party.id}`);
      reports.push({poll,index,seats:poll.seats[party.id],weight:weights[index]});
    });
    const weightCoverage=reports.reduce((sum,item)=>sum+item.weight,0);
    const seats=weightCoverage>0?reports.reduce((sum,item)=>sum+item.weight*item.seats,0)/weightCoverage:null;
    const reportingIds=new Set(reports.map(item=>item.poll.pollsterId));
    return {
      partyId:party.id,partyName:party.name??party.id,seats,
      reportingPollCount:reports.length,
      reportingWeightCoverage:Math.min(1,Math.max(0,weightCoverage)),
      reportingPollsterIds:[...reportingIds],
      missingReportingPollsterIds:[...new Set(polls.map(poll=>poll.pollsterId).filter(id=>!reportingIds.has(id)))],
    };
  });
}

export function toWideTrendRows(checkpoints){
  return checkpoints.map(point=>Object.assign({
    date:point.date,status:point.status,pollCount:point.pollCount,
    eligiblePollsterCount:point.eligiblePollsterCount,missingPollsterIds:[...point.missingPollsterIds],
  },Object.fromEntries(point.parties.map(party=>[party.partyId,party.seats]))));
}


function mean(values){return values.length?values.reduce((sum,value)=>sum+value,0)/values.length:null;}
function weightedMean(items,valueKey='value'){
  const usable=items.filter(item=>Number.isFinite(item[valueKey])&&Number.isFinite(item.weight)&&item.weight>0);
  const denominator=usable.reduce((sum,item)=>sum+item.weight,0);
  return denominator>0?usable.reduce((sum,item)=>sum+item.weight*item[valueKey],0)/denominator:null;
}

/** Exact, two-sided randomization test under pollster-level sign exchangeability. */
function exactVectorSignFlipP(items,{maxPollsters=16}={}){
  const usable=items.filter(item=>Number.isFinite(item.value)&&Number.isFinite(item.weight)&&item.weight>0);
  if(usable.length<2||usable.length>maxPollsters)return null;
  const denominator=usable.reduce((sum,item)=>sum+item.weight,0);
  if(!(denominator>0))return null;
  const observed=Math.abs(usable.reduce((sum,item)=>sum+item.weight*item.value,0)/denominator);
  const permutations=2**usable.length;
  let extreme=0;
  for(let mask=0;mask<permutations;mask++){
    const statistic=Math.abs(usable.reduce((sum,item,index)=>sum+item.weight*item.value*((mask>>index)&1?1:-1),0)/denominator);
    if(statistic>=observed-1e-12)extreme++;
  }
  return extreme/permutations;
}

function withBenjaminiHochberg(rows){
  const tested=rows.map((row,index)=>({row,index,p:row.pValue})).filter(item=>Number.isFinite(item.p)).sort((a,b)=>a.p-b.p||a.index-b.index);
  let next=1;
  for(let i=tested.length-1;i>=0;i--){
    const adjusted=Math.min(1,tested[i].p*tested.length/(i+1),next);
    tested[i].row.qValue=adjusted;next=adjusted;
  }
  for(const row of rows)if(!Number.isFinite(row.qValue))row.qValue=null;
  return rows;
}

/**
 * Compare each selected pollster with itself after the candidate-list cutoff.
 * Keeping a pollster's whole party vector together reduces house-effect noise
 * and is also the randomization unit in the exact sign-flip sensitivity test.
 */
export function buildPollDeltaAnalysis({
  historicalPolls,currentPolls,parties,config={},calibration={},weightPresets,
  cutoffDate=POST_LISTS_CUTOFF_DATE,
}={}){
  validateHistory(historicalPolls);
  if(!Array.isArray(parties)||!parties.length)throw new Error('parties must be a non-empty array.');
  const cutoff=dateKey(cutoffDate,'delta cutoff'),selectedPollsterIds=getSelectedPollsterIds(currentPolls,config),selected=new Set(selectedPollsterIds);
  const observationsByPollster=new Map(selectedPollsterIds.map(id=>[id,new Map()]));
  for(const poll of historicalPolls){
    if(!selected.has(poll.pollsterId))continue;
    const date=pollDate(poll);
    if(date<cutoff)continue;
    const byDate=observationsByPollster.get(poll.pollsterId),existing=byDate.get(date);
    // A same-day duplicate is one observation, not a zero-day trend interval.
    if(!existing||poll.id.localeCompare(existing.id)<0)byDate.set(date,poll);
  }
  const pairs=[],omittedPollsters=[];
  for(const pollsterId of selectedPollsterIds){
    const observations=[...(observationsByPollster.get(pollsterId)?.values()??[])].sort((a,b)=>pollDate(a).localeCompare(pollDate(b))||a.id.localeCompare(b.id));
    if(observations.length<2){omittedPollsters.push({pollsterId,observationCount:observations.length});continue;}
    const previousPoll=observations.at(-2),latestPoll=observations.at(-1),previousDate=pollDate(previousPoll),latestDate=pollDate(latestPoll);
    const days=(dayNumber(latestDate)-dayNumber(previousDate))/DAY_MS;
    if(!(days>0)){omittedPollsters.push({pollsterId,observationCount:observations.length});continue;}
    pairs.push({pollsterId,previousPoll,latestPoll,previousDate,latestDate,days});
  }
  if(!pairs.length)return {cutoffDate:cutoff,selectedPollsterIds,pairs:[],combined:[],omittedPollsters,modelWeights:[],exactTest:null};

  const asOf=pairs.map(pair=>pair.latestDate).sort().at(-1),modelCalibration=weightPresets===undefined?calibration:{...calibration,weightPresets};
  const combinedPolls=combinePolls(pairs.map(pair=>pair.latestPoll),parties,{...config,asOf,excludedPolls:[]},modelCalibration);
  const weightByPollId=new Map(combinedPolls.polls.map((poll,index)=>[poll.id,combinedPolls.weights[index]]));
  for(const pair of pairs){
    pair.weight=weightByPollId.get(pair.latestPoll.id)??0;
    pair.parties=parties.map(party=>{
      const previous=pair.previousPoll.seats?.[party.id],latest=pair.latestPoll.seats?.[party.id];
      const reported=Number.isFinite(previous)&&Number.isFinite(latest);
      const rawDelta=reported?latest-previous:null;
      return {partyId:party.id,partyName:party.name??party.id,previous:reported?previous:null,latest:reported?latest:null,
        rawDelta,weeklyDelta:reported?rawDelta*7/pair.days:null};
    });
  }

  const combined=withBenjaminiHochberg(parties.map(party=>{
    const records=pairs.map(pair=>({pair,delta:pair.parties.find(item=>item.partyId===party.id)})).filter(item=>Number.isFinite(item.delta?.weeklyDelta));
    const modelRecords=records.map(item=>({value:item.delta.weeklyDelta,raw:item.delta.rawDelta,weight:item.pair.weight})).filter(item=>item.weight>0);
    return {
      partyId:party.id,partyName:party.name??party.id,pollsterCount:records.length,modelPollsterCount:modelRecords.length,
      modelRawDelta:weightedMean(modelRecords,'raw'),modelWeeklyDelta:weightedMean(modelRecords),
      equalRawDelta:mean(records.map(item=>item.delta.rawDelta)),equalWeeklyDelta:mean(records.map(item=>item.delta.weeklyDelta)),
      pValue:exactVectorSignFlipP(modelRecords),qValue:null,
    };
  }));
  return {
    cutoffDate:cutoff,asOf,selectedPollsterIds,pairs,combined,omittedPollsters,
    modelWeights:pairs.map(pair=>({pollsterId:pair.pollsterId,pollId:pair.latestPoll.id,weight:pair.weight})),
    exactTest:{kind:'exact_whole_pollster_vector_sign_flip',twoSided:true,statistic:'absolute weighted mean weekly seat delta',
      multipleTesting:'Benjamini-Hochberg across all supplied parties',maxExactPollsters:16},
  };
}

/**
 * Stable, all-party rows for the headline delta table. Graph selection is a
 * presentation concern and must never filter the statistical comparison.
 */
export function buildPollDeltaSummaryRows(delta,parties){
  const byParty=new Map((delta?.combined??[]).map(row=>[row.partyId,row]));
  return (Array.isArray(parties)?parties:[]).filter(party=>party?.ballot!==false).map(party=>({
    party,
    ...(byParty.get(party.id)??{
      partyId:party.id,partyName:party.name??party.id,pollsterCount:0,modelPollsterCount:0,
      modelRawDelta:null,modelWeeklyDelta:null,equalRawDelta:null,equalWeeklyDelta:null,pValue:null,qValue:null,
    }),
  })).sort((a,b)=>{
    const aTested=Number.isFinite(a.qValue),bTested=Number.isFinite(b.qValue);
    if(aTested!==bTested)return aTested?-1:1;
    if(aTested&&a.qValue!==b.qValue)return a.qValue-b.qValue;
    const weeklyDifference=Math.abs(b.modelWeeklyDelta??0)-Math.abs(a.modelWeeklyDelta??0);
    return weeklyDifference||String(a.party.name??a.party.id).localeCompare(String(b.party.name??b.party.id),'he');
  });
}

/**
 * Build a deterministic history of weighted, published seat projections.
 * This intentionally does not simulate elections or rerun Bader-Ofer.
 */
export function buildPollTrendSeries({
  historicalPolls,currentPolls,parties,config={},calibration={},weightPresets,
  maxAgeDays=DEFAULT_TREND_MAX_AGE_DAYS,minPolls=DEFAULT_TREND_MIN_POLLS,
}={}){
  validateHistory(historicalPolls);
  if(!Array.isArray(parties)||!parties.length)throw new Error('parties must be a non-empty array.');
  if(!Number.isInteger(minPolls)||minPolls<2)throw new Error('minPolls must be an integer of at least 2.');
  const selectedPollsterIds=getSelectedPollsterIds(currentPolls,config),selected=new Set(selectedPollsterIds);
  const selectedHistory=historicalPolls.filter(poll=>selected.has(poll.pollsterId));
  const dates=[...new Set(selectedHistory.map(pollDate))].sort();
  const modelCalibration=weightPresets===undefined?calibration:{...calibration,weightPresets};
  const checkpoints=dates.map(date=>{
    const available=latestPollsAtCheckpoint(selectedHistory,selectedPollsterIds,date,{maxAgeDays});
    const availableIds=new Set(available.map(poll=>poll.pollsterId));
    const base={date,pollCount:available.length,eligiblePollsterCount:selectedPollsterIds.length,
      availablePollsterIds:selectedPollsterIds.filter(id=>availableIds.has(id)),
      missingPollsterIds:selectedPollsterIds.filter(id=>!availableIds.has(id))};
    if(available.length<minPolls){
      return {...base,status:'insufficient-polls',pollWeights:[],weightSum:0,
        parties:parties.map(party=>{
          const reporting=available.filter(poll=>own(poll.seats,party.id)&&Number.isFinite(poll.seats[party.id]));
          const reportingIds=new Set(reporting.map(poll=>poll.pollsterId));
          return {partyId:party.id,partyName:party.name??party.id,seats:null,reportingPollCount:reporting.length,
            reportingWeightCoverage:null,reportingPollsterIds:[...reportingIds],
            missingReportingPollsterIds:base.availablePollsterIds.filter(id=>!reportingIds.has(id))};
        })};
    }
    // Current-card exclusions have already been translated to selected pollsters.
    // Clearing poll ids here prevents a current poll id from accidentally excluding
    // an identically named historical observation; manual pollster multipliers remain.
    const combined=combinePolls(available,parties,{...config,asOf:date,excludedPolls:[]},modelCalibration);
    const pollWeights=combined.polls.map((poll,index)=>({
      pollId:poll.id,pollsterId:poll.pollsterId,date:pollDate(poll),weight:combined.weights[index],
    }));
    return {...base,status:'ok',pollCount:combined.polls.length,pollWeights,
      weightSum:combined.weights.reduce((sum,weight)=>sum+weight,0),
      parties:publishedSeatMetrics(combined.polls,combined.weights,parties)};
  });
  const rows=toWideTrendRows(checkpoints),seriesRows=checkpoints.flatMap(point=>point.parties.map(party=>({
    date:point.date,status:point.status,pollCount:point.pollCount,eligiblePollsterCount:point.eligiblePollsterCount,
    missingPollsterIds:[...point.missingPollsterIds],...party,
  })));
  return {
    metric:{id:'weighted_published_seats',labelHe:'ממוצע משוקלל של תחזיות המנדטים שפורסמו',simulation:false,baderOfer:false},
    weightMode:config.weightMode??'equal',maxAgeDays,minPolls,selectedPollsterIds,
    checkpoints,rows,seriesRows,calculatedCheckpointCount:checkpoints.filter(point=>point.status==='ok').length,
  };
}
