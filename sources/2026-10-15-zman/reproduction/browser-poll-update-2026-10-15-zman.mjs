/**
 * Browser evidence for the Tatika update preserving the reviewed UI12 threshold alignment, 15 October 2026.
 * Run only after the official source build. This script reads canonical data
 * and writes new evidence solely under the selected dated browser phase.
 * Usage: node scripts/browser-poll-update-2026-10-15-zman.mjs --base URL --phase local|public
 */
import {createRequire} from 'node:module';
import {fileURLToPath} from 'node:url';
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import assert from 'node:assert/strict';

const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const evidenceRoot=path.join(root,'artifacts','poll-checks','2026-10-15-zman');
const checkpoint='artifacts/poll-checks/2026-10-15-zman/before';
const ui12CanonicalCheckpoint='artifacts/poll-checks/2026-10-12-evening/before';
const read=rel=>JSON.parse(fs.readFileSync(path.join(root,rel),'utf8').replace(/^\uFEFF/,''));
const sha=rel=>crypto.createHash('sha256').update(fs.readFileSync(path.join(root,rel))).digest('hex');
const manifest=read(checkpoint+'/manifest.json');
const uiBaselinePath='C:/Users/User/.codex/visualizations/2026/09/12/01a0952c-a40b-7b01-b019-621f0cee2656/artifacts/ui-threshold-alignment-2026-10-12/frozen-baseline-hashes.json';
const frozenBaseline=JSON.parse(fs.readFileSync(uiBaselinePath,'utf8').replace(/^\uFEFF/,''));
const updatedCanonical=new Set(['data/current-polls.json','data/poll-history.json','data/poll-correlation.json','data/strict-party-trends.json','data/strict-party-trends-without-channel14.json']);
function preserveFiles(){
  for(const [rel,digest] of Object.entries(manifest.files))assert.equal(sha(checkpoint+'/'+rel),digest,'Immutable evening checkpoint: '+rel);
  for(const category of ['authorContentHashes','protectedRuntimeHashes','frozenEvidenceHashes','frozenConditionalAndArtisticHashes'])
    for(const [rel,digest] of Object.entries(manifest[category]))assert.equal(sha(rel),digest,'Preserved '+category+': '+rel);
  assert.equal(Object.keys(manifest.authorContentHashes).length,117,'All authored content is in scope');
  assert.equal(Object.keys(manifest.protectedRuntimeHashes).length,234);
  assert.equal(Object.keys(manifest.frozenEvidenceHashes).length,1831,'Every previously published evidence file remains protected');
  assert.equal(Object.keys(manifest.frozenConditionalAndArtisticHashes).length,14);
  assert.equal(frozenBaseline.fileCount,289);
  for(const record of frozenBaseline.files){
    const target=updatedCanonical.has(record.path)?ui12CanonicalCheckpoint+'/'+record.path:record.path;
    assert.equal(sha(target),record.sha256,'UI12 prior evidence / checkpoint binding: '+record.path);
  }
}
preserveFiles();
const options={};
for(let i=2;i<process.argv.length;i+=2){assert.ok(['--base','--phase'].includes(process.argv[i]));assert.ok(process.argv[i+1]);options[process.argv[i].slice(2)]=process.argv[i+1];}
assert.ok(options.base,'--base is required');assert.ok(['local','public'].includes(options.phase));
const base=new URL(options.base);assert.ok(['http:','https:'].includes(base.protocol),'Use a served HTTP(S) URL after source-build GO');
const current=read('data/current-polls.json'),history=read('data/poll-history.json');
const fullStrict=read('data/strict-party-trends.json'),strict=read('data/strict-party-trends-without-channel14.json');
const correlation=read('data/poll-correlation.json'),snapshot=read('dashboard/src/data.json');
const beforeCurrent=read(checkpoint+'/data/current-polls.json'),beforeHistory=read(checkpoint+'/data/poll-history.json');
const beforeFull=read(checkpoint+'/data/strict-party-trends.json'),beforeStrict=read(checkpoint+'/data/strict-party-trends-without-channel14.json');
for(const value of [current,history,fullStrict,strict,correlation])assert.equal(value.asOf,'2026-10-15','Post-update prerequisite date');
assert.equal(beforeCurrent.asOf,manifest.baselineAsOf);assert.equal(manifest.updateDate,'2026-10-15');
assert.equal(current.polls.length,manifest.activePollCount);assert.equal(current.polls.length,8);
assert.equal(history.polls.length,manifest.historyPollCount+1);assert.equal(history.polls.length,123);
const expectedFull={pollCount:beforeFull.coverage.pollCount+1,seriesCount:beforeFull.coverage.seriesCount,deltaCount:beforeFull.coverage.deltaCount+1};
const expectedWithout14={pollCount:beforeStrict.coverage.pollCount+1,seriesCount:beforeStrict.coverage.seriesCount,deltaCount:beforeStrict.coverage.deltaCount+1};
assert.deepEqual(expectedFull,{pollCount:46,seriesCount:8,deltaCount:38});assert.deepEqual(expectedWithout14,{pollCount:37,seriesCount:7,deltaCount:30});
for(const [report,expected] of [[fullStrict,expectedFull],[strict,expectedWithout14]]){
  for(const [key,value] of Object.entries(expected))assert.equal(report.coverage[key],value);
  assert.equal(report.coverage.partyCount,17);assert.equal(report.cohort.length,beforeFull.cohort.length+1);assert.equal(report.cohort.length,52);
}
assert.equal(snapshot.features.chatGPT,false);
const snapshotInput=Object.fromEntries(snapshot.queries.model_input.rows.map(r=>[r.key,r.value]));
assert.deepEqual(snapshotInput.current,current);assert.deepEqual(snapshotInput.history,history);assert.deepEqual(snapshotInput.calibration.pollCorrelation,correlation);
for(const [prefix,report,pollsId] of [['verified_party_trends',fullStrict,'verified_party_trend_polls'],['verified_party_trends_without_channel14',strict,'verified_party_trends_without_channel14_polls']]){
  assert.equal(snapshot.queries[prefix+'_metadata'].rows[0].asOf,'2026-10-15');
  assert.deepEqual(snapshot.queries[prefix+'_metadata'].rows[0].coverage,report.coverage);
  assert.deepEqual(snapshot.queries[prefix].rows,report.rows);assert.deepEqual(snapshot.queries[pollsId].rows,report.cohort);
}
const n12=current.polls.find(p=>p.id==='midgam_geva_2026-10-12'),c14=current.polls.find(p=>p.id==='next_data_2026-10-14');
const c13=current.polls.find(p=>p.id==='hamadad_consortium_2026-10-14'),kan=current.polls.find(p=>p.id==='kantar_2026-10-11');
const i24=current.polls.find(p=>p.id==='direct_polls_2026-10-13'),c16=current.polls.find(p=>p.id==='maagar_mochot_2026-10-13'),walla=current.polls.find(p=>p.id==='lazar_2026-10-13');
const candidates=[read('artifacts/poll-checks/2026-10-15-zman/source/reviewed-tatika-poll.json')];
const tatika=current.polls.find(p=>p.id===candidates[0].id);assert.ok(tatika);
assert.ok(n12&&c14&&c13&&kan&&i24&&c16&&walla);
const removedIds=new Set(candidates.map(p=>p.replacesPollId)),addedIds=new Set(candidates.map(p=>p.id));
assert.deepEqual([...new Set(beforeCurrent.polls.map(p=>p.id))].filter(id=>!current.polls.some(p=>p.id===id)).sort(),[...removedIds].sort());
assert.deepEqual(current.polls.map(p=>p.id).filter(id=>!beforeCurrent.polls.some(p=>p.id===id)).sort(),[...addedIds].sort());
for(const old of beforeCurrent.polls)if(!removedIds.has(old.id))assert.deepEqual(current.polls.find(p=>p.id===old.id),old,'Unrelated current row unchanged: '+old.id);
for(const old of beforeHistory.polls){
  const successor=candidates.find(p=>'history_'+p.replacesPollId+'_current'===old.id);
  const expected=successor?{...old,recordStatus:'superseded-reviewed-record',replacedByPollId:successor.id}:old;
  assert.deepEqual(history.polls.find(p=>p.id===old.id),expected,'Prior history preserved apart from explicit supersession metadata: '+old.id);
}
const newHistory=history.polls.filter(p=>!beforeHistory.polls.some(old=>old.id===p.id));
assert.deepEqual(newHistory.map(p=>p.id).sort(),candidates.map(p=>'history_'+p.id+'_current').sort());
for(const candidate of candidates){
  const poll=current.polls.find(p=>p.id===candidate.id);
  for(const key of ['id','pollsterId','date','fieldworkStart','fieldworkEnd','sampleSize','seats','reportedPercentages','percentages','modelOnlyPercentageIds','sourceBlocSeats','sourceBlocDefinitions','unmodelledNamedParties','publishedBounds'])assert.deepEqual(poll[key],candidate[key],'Reviewed Tatika field: '+key);
  assert.equal(poll.date,'2026-10-15');assert.equal(poll.sampleSize,500);
  assert.equal(poll.fieldworkStart,'2026-10-14');assert.equal(poll.fieldworkEnd,'2026-10-15');assert.equal(poll.fieldworkVerified,true);
  assert.equal(Object.values(poll.seats).reduce((sum,n)=>sum+n,0),120);
  assert.deepEqual(poll.reportedPercentages,{winter:2.8,gantz:1.2});
  assert.equal(poll.seats.yashar,26);assert.equal(poll.seats.hendel,4);assert.equal(poll.seats.winter,0);
  assert.ok(!Object.hasOwn(poll.reportedPercentages,'hendel'),'Passing exact share remains missing');
}
assert.deepEqual(c13,beforeCurrent.polls.find(p=>p.id===c13.id));assert.deepEqual(c14,beforeCurrent.polls.find(p=>p.id===c14.id));
assert.equal(i24.sampleSize,1210);assert.equal(i24.fieldworkStart,'2026-10-13');assert.equal(i24.fieldworkEnd,'2026-10-13');assert.equal(i24.fieldworkVerified,true);
assert.deepEqual(i24.reportedPercentages,{winter:3.1,hendel:2.2});assert.equal(i24.reportedMarginOfErrorPct,2.8);assert.equal(i24.reportedMarginOfErrorConfidencePct,95);
for(const id of ['gantz','haredi_public','noam','israel_first']){assert.deepEqual(i24.publishedBounds[id],{min:0,max:1,maxExclusive:true});assert.ok(!Object.hasOwn(i24.reportedPercentages,id));}
assert.equal(i24.unmodelledNamedParties.length,2);for(const row of i24.unmodelledNamedParties){assert.equal(row.pct,null);assert.equal(row.pctUpperBound,1);assert.equal(row.maxExclusive,true);}
assert.deepEqual(i24.sourceBlocSeats,{coalition:57,opposition:50,arab_parties:13});assert.deepEqual(i24.publishedPreviousBlocSeats,{coalition:60,opposition:48,arab_parties:12});
assert.equal(c16.sampleSize,null);assert.equal(c16.sampleSizeLowerBoundExclusive,2000);assert.equal(c16.sampleSizeQualifier,beforeCurrent.polls.find(p=>p.id===c16.id).sampleSizeQualifier);
assert.equal(c16.fieldworkStart,null);assert.equal(c16.fieldworkEnd,null);assert.equal(c16.fieldworkVerified,false);assert.equal(c16.reportedMarginOfErrorPct,2.1);
assert.deepEqual(c16.reportedPercentages,{gantz:1.2,haredi_public:1.1});assert.deepEqual(c16.sourceBlocSeats,{coalition:52,opposition:50,arab_parties:13,hendel:5});
assert.deepEqual(c16.sourceHistoryBlocSeats,{coalition:52,others:55,arab_parties:13});assert.match(c16.sourceBlocDefinitions.coalition,/עמך ישראל|Winter/);
assert.deepEqual(c16.fixedBlocSeatsForAudit,{coalition:52,opposition:50,arab_parties:13,unassigned:5});
assert.equal(walla.sampleSize,601);assert.equal(walla.fieldworkStart,'2026-10-12');assert.equal(walla.fieldworkEnd,'2026-10-12');assert.equal(walla.fieldworkVerified,true);
assert.deepEqual(walla.reportedPercentages,{winter:2.8,gantz:1.1,haredi_public:1,noam:.2});assert.equal(walla.requestedParticipationCount,4089);assert.equal(walla.invitedSampleSize,null);
assert.deepEqual(n12,beforeCurrent.polls.find(p=>p.id===n12.id));assert.equal(n12.sampleSize,509);assert.equal(n12.fieldworkEnd,'2026-10-12');
assert.equal(c14.sampleSize,568);assert.equal(c14.fieldworkStart,'2026-10-14');assert.equal(c14.fieldworkEnd,'2026-10-14');assert.equal(c14.fieldworkVerified,true);
assert.deepEqual(c14.sourceBlocSeats,{coalition:62,opposition:44,arab_parties:14});assert.deepEqual(c14.reportedPercentages,{hendel:3.1,winter:2.7,gantz:1.2,noam:.8,haredi_public:.4});
assert.equal(c14.undecidedPct,null);assert.equal(c14.reportedMarginOfErrorPct,null);assert.equal(c14.reportedMarginOfErrorConfidencePct,null);assert.equal(c14.samplingMethod,null);assert.equal(c14.invitedSampleSize,null);
assert.deepEqual(c14.modelOnlyPercentageIds,['other']);assert.equal(c14.percentages.other,.2);assert.equal(c14.unmodelledNamedParties[0].pct,.2);assert.equal(c14.unmodelledNamedParties[0].mappedTo,'other');
for(const unchanged of [i24,c16,walla])assert.deepEqual(unchanged,beforeCurrent.polls.find(p=>p.id===unchanged.id),'13Oct poll retained exactly');
assert.deepEqual(kan,beforeCurrent.polls.find(p=>p.id===kan.id));assert.equal(kan.sampleSize,554);assert.equal(kan.fieldworkStart,null);assert.equal(kan.fieldworkEnd,null);
assert.deepEqual(kan.modelOnlyPercentageIds,['other']);assert.equal(kan.percentages.other,1.2);assert.ok(!Object.hasOwn(kan.reportedPercentages,'other'));
assert.equal(c13.sampleSize,1018);assert.equal(c13.fieldworkStart,'2026-10-13');assert.equal(c13.fieldworkEnd,'2026-10-13');assert.equal(c13.fieldworkVerified,true);
assert.deepEqual(c13.reportedPercentages,{gantz:1.2,haredi_public:1.1});assert.equal(c13.seats.winter,4);assert.equal(c13.seats.hendel,4);
assert.deepEqual(c13.seats,{likud:18,yashar:20,beyachad:12,democrats:9,yisrael_beiteinu:9,joint:9,otzma:8,utj:8,shas:7,rz_zehut:6,raam:6,winter:4,hendel:4,gantz:0,haredi_public:0});

const kanSeats=kan.seats;
const cohortTatika=strict.cohort.find(p=>p.pollId==='history_'+tatika.id+'_current');
const cohortC13=strict.cohort.find(p=>p.pollId==='history_'+c13.id+'_current');
const cohortKan=strict.cohort.find(p=>p.pollId==='history_'+kan.id+'_current');
const cohortN12=strict.cohort.find(p=>p.pollId==='history_'+n12.id+'_current');
const cohortC14=strict.cohort.find(p=>p.pollId==='history_'+c14.id+'_current');
const cohortI24=strict.cohort.find(p=>p.pollId==='history_'+i24.id+'_current'),cohortC16=strict.cohort.find(p=>p.pollId==='history_'+c16.id+'_current'),cohortWalla=strict.cohort.find(p=>p.pollId==='history_'+walla.id+'_current');
for(const report of [fullStrict,strict]){
  const k=report.cohort.find(p=>p.pollId==='history_'+kan.id+'_current');assert.equal(k.eligibleStrict,false);assert.equal(k.fieldworkStart,null);assert.equal(k.fieldworkEnd,null);
  for(const poll of [n12,i24,walla,c13,tatika]){const n=report.cohort.find(p=>p.pollId==='history_'+poll.id+'_current');assert.equal(n.eligibleStrict,true);assert.equal(n.fieldworkStart,poll.fieldworkStart);assert.equal(n.fieldworkEnd,poll.fieldworkEnd);}
  const c=report.cohort.find(p=>p.pollId==='history_'+c16.id+'_current');assert.equal(c.eligibleStrict,false);assert.equal(c.fieldworkStart,null);assert.equal(c.fieldworkEnd,null);assert.ok(!c.channel14Excluded);
}
const fullC14=fullStrict.cohort.find(p=>p.pollId==='history_'+c14.id+'_current');assert.equal(fullC14.eligibleStrict,true);
assert.equal(cohortC14.eligibleStrict,false);assert.equal(cohortC14.channel14Excluded,true);assert.equal(cohortC14.fieldworkStart,'2026-10-14');assert.equal(cohortC14.fieldworkEnd,'2026-10-14');
const boundSourcePaths=['data/current-polls.json','data/poll-history.json','data/strict-party-trends.json','data/strict-party-trends-without-channel14.json','data/poll-correlation.json','dashboard/src/data.json','dashboard-snapshot.json'];
const sourceHashBaseline=Object.fromEntries(boundSourcePaths.map(rel=>[rel,sha(rel)]));

const runId=new Date().toISOString().replace(/[:.]/g,'-')+'-'+process.pid;
const phaseRoot=path.join(evidenceRoot,'browser-'+options.phase);
fs.mkdirSync(phaseRoot,{recursive:true});
const out=path.join(phaseRoot,runId);
fs.mkdirSync(out); // No prior run or frozen evidence can be overwritten.
fs.copyFileSync(fileURLToPath(import.meta.url),path.join(out,'qa-script-used.mjs'));
const require=createRequire('C:/Users/User/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright/package.json');
const {chromium}=require('playwright');
const report={
  status:'running',phase:options.phase,runId,base:base.href,asOf:current.asOf,
  expectedCoverage:strict.coverage,checks:[],geometry:[],pageErrors:[],thresholdAlignments:[],frozenFilesVerified:frozenBaseline.fileCount,authorFilesVerified:Object.keys(manifest.authorContentHashes).length,protectedFilesVerified:Object.keys(manifest.protectedRuntimeHashes).length,frozenPublicFilesVerified:Object.keys(manifest.frozenEvidenceHashes).length,frozenConditionalFilesVerified:Object.keys(manifest.frozenConditionalAndArtisticHashes).length,ui12CanonicalCheckpoint,beforeCheckpointSha256:sha(checkpoint+'/manifest.json'),beforeCurrentSha256:sha(checkpoint+'/data/current-polls.json'),beforeHistorySha256:sha(checkpoint+'/data/poll-history.json'),
  qaScriptSha256:crypto.createHash('sha256').update(fs.readFileSync(fileURLToPath(import.meta.url))).digest('hex'),
  sourceHashes:sourceHashBaseline,
};
const browser=await chromium.launch({headless:true,executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe'});
let page;
const tabs=[
  ['about','אודות והתחלה'],['dashboard','סימולציה ותוצאות'],['probabilities','מפלגות וחסימה'],
  ['poll-trends','מגמות'],['seat-probabilities','תרחישי מנדטים'],['poll-data','הסקרים'],['method-data','שיטות והסברים'],
];
const exportName='ייצוא תרחיש ומקורות JSON';
const format=(value,digits=2)=>Number(value).toLocaleString('he-IL',{minimumFractionDigits:digits,maximumFractionDigits:digits});
const numeric=text=>Number(text.replace(/[^0-9.\-]/g,''));
async function ready(){
  await page.locator('#run-settings').waitFor();
  await page.waitForFunction(name=>{const b=[...document.querySelectorAll('button')].find(n=>n.textContent.trim()===name);return b&&!b.disabled;},exportName);
  assert.equal(await page.locator('.e-error').count(),0);
  assert.deepEqual(report.pageErrors,[]);
}
async function tab(id){
  await page.getByRole('tab',{name:tabs.find(t=>t[0]===id)[1],exact:true}).click();
  await page.locator('.election-app[data-page="'+id+'"]').waitFor();
  if(id!=='about')await ready();
}
async function noChatGPT(){
  assert.equal(await page.getByRole('button',{name:/Ask ChatGPT/i}).count(),0);
  assert.equal(await page.getByRole('link',{name:/Ask ChatGPT/i}).count(),0);
}
async function detail(locator,open){
  if(await locator.evaluate(node=>node.open)!==open)await locator.locator(':scope > summary').click();
}
async function choose(label,choice){
  await page.getByRole('button',{name:label,exact:true}).click();
  await page.getByRole('menuitemradio',{name:choice,exact:true}).click();
}
async function downloaded(button,name){
  const pending=page.waitForEvent('download');
  await button.click();
  const download=await pending;
  assert.equal(await download.failure(),null);
  const file=path.join(out,name);
  await download.saveAs(file);
  return file;
}
async function exported(name){
  await ready();
  const settings=page.locator('#run-settings');
  await detail(settings,true);
  const file=await downloaded(page.getByRole('button',{name:exportName,exact:true}),name+'.json');
  await detail(settings,false);
  const value=JSON.parse(fs.readFileSync(file,'utf8').replace(/^\uFEFF/,''));
  assert.equal(value.siteVersion,3);
  assert.equal(value.config.asOf,'2026-10-15');
  assert.equal(value.config.weightMode,'quality');
  assert.equal(value.config.includeChannel14,false);
  assert.equal(value.config.signalNoiseEnabled,false);
  assert.equal(value.config.pollCorrelationEnabled,false);
  assert.equal(value.result.checks.eachWorld120,true);
  assert.equal(value.result.checks.blocPartition120,true);
  assert.ok(Math.abs(value.result.parties.reduce((sum,p)=>sum+p.mean,0)-120)<1e-8);
  assert.deepEqual(value.input.current,current,'Served app must contain all corrected canonical poll metadata');
  assert.deepEqual(value.input.history,history);assert.deepEqual(value.input.calibration.pollCorrelation,correlation);
  assert.equal(value.input.current.polls.length,8);assert.equal(value.input.history.polls.length,123);
  assert.ok(!value.result.pollWeights.some(p=>p.pollsterId==='next_data'),'Default excludes C14 before weights');
  return value;
}
async function geometry(label){
  const g=await page.evaluate(()=>({viewport:innerWidth,client:document.documentElement.clientWidth,scroll:document.documentElement.scrollWidth,height:document.documentElement.scrollHeight}));
  assert.ok(g.scroll<=g.client+2,'Horizontal overflow at '+label+': '+g.scroll+' > '+g.client);
  report.geometry.push({label,...g});
}
async function strictView(){
  const section=page.locator('[data-verified-party-trends]');
  await section.waitFor();
  assert.match(await section.locator('.vpt-date').innerText(),/15\.10\.2026/);
  assert.equal(await section.locator('.vpt-stale').count(),0);
  assert.match(await section.locator('.vpt-fixed').first().innerText(),/ערוץ 14 מוחרג/);
  const facts=await section.locator('.vpt-facts').innerText();
  for(const [key,label] of [['pollCount','סקרים'],['seriesCount','סדרות סקרים'],['deltaCount','שינויים עוקבים']])
    assert.match(facts,new RegExp('\\b'+strict.coverage[key]+'\\b\\s+'+label));
  const table=section.locator('[data-component-id="verified-party-trend-table"]');
  assert.equal(await table.locator('tbody tr').count(),strict.rows.length);
  const significant=strict.rows.filter(row=>!row.zeroSeatsThroughout&&row.qValue<.05).map(row=>row.partyId).sort();
  assert.deepEqual((await table.locator('tr[data-significant]').evaluateAll(rows=>rows.map(row=>row.dataset.verifiedPartyId))).sort(),significant);
  for(const expected of strict.rows){
    const row=table.locator('tr[data-verified-party-id="'+expected.partyId+'"]');
    const cells=await row.locator('td').allTextContents();
    assert.equal(cells.length,5);
    if(expected.zeroSeatsThroughout){assert.equal(cells[2].trim(),'—');assert.equal(cells[3].trim(),'—');}
    else{
      assert.equal((await row.locator('td').nth(2).locator('bdi').innerText()).trim(),format(expected.pValue,4));
      assert.equal((await row.locator('td').nth(3).locator('bdi').innerText()).trim(),format(expected.qValue,4));
      assert.equal(cells[4].trim(),expected.qValue<.05?'מובהק':'לא מובהק');
    }
  }
  const disclosure=section.locator('details').last();
  await detail(disclosure,true);
  const cohort=disclosure.locator('.vpt-cohort');
  assert.equal(await cohort.locator('tbody tr').count(),strict.cohort.length);
  const visible=await cohort.locator('tbody tr').evaluateAll(rows=>rows.map(row=>({text:row.innerText,href:row.querySelector('a')?.href??null,decision:row.children[4]?.textContent.trim()})));
  assert.equal(visible.filter(row=>row.decision==='נכלל').length,strict.coverage.pollCount);
  assert.equal(visible.filter(row=>row.decision==='הוחרג לפי מתג ערוץ 14').length,strict.coverage.channel14ExcludedPollCount);
  assert.equal(visible.filter(row=>row.decision==='הוחרג').length,strict.coverage.unverifiedExcludedPollCount??strict.coverage.fieldworkExcludedPollCount);
  const target=visible.filter(row=>row.href===cohortTatika.sourceUrls[0]&&/15\.10\.2026/.test(row.text));
  assert.equal(target.length,1,'One new Tatika row must link to original evidence');
  assert.match(target[0].text,/14\.10\.2026/);assert.match(target[0].text,/15\.10\.2026/);
  assert.equal(target[0].decision,'נכלל');
  const kanTarget=visible.filter(row=>row.href===cohortKan.sourceUrls[0]&&/11\.10\.2026/.test(row.text));
  assert.equal(kanTarget.length,1,'New Kan source must appear once in the audit');
  assert.equal(kanTarget[0].decision,'הוחרג');
  assert.equal((kanTarget[0].text.match(/לא אומת/g)??[]).length,2,'Both Kan fieldwork dates remain visibly unverified');
  for(const [poll,expectedDecision,day] of [[cohortN12,'נכלל','12'],[cohortC14,'הוחרג לפי מתג ערוץ 14','14']]){
    const datePattern=new RegExp(day+'\\.10\\.2026');
    const match=visible.filter(row=>row.href===poll.sourceUrls[0]&&datePattern.test(row.text));
    assert.equal(match.length,1);assert.equal(match[0].decision,expectedDecision);assert.ok((match[0].text.match(new RegExp(day+'\\.10\\.2026','g'))??[]).length>=3);
  }
  const newRows=[];
  for(const [poll,decision] of [[cohortI24,'נכלל'],[cohortWalla,'נכלל'],[cohortC16,'הוחרג']]){
    const match=visible.filter(row=>row.href===poll.sourceUrls[0]&&/13\.10\.2026/.test(row.text));
    assert.equal(match.length,1,'One row for new '+poll.pollId);assert.equal(match[0].decision,decision);
    if(poll===cohortC16)assert.equal((match[0].text.match(/לא אומת/g)??[]).length,2);
    else assert.match(match[0].text,poll===cohortI24?/13\.10\.2026/:/12\.10\.2026/);
    newRows.push({pollId:poll.pollId,...match[0]});
  }
  report.strict={asOf:strict.asOf,coverage:strict.coverage,significant,tatika:target[0],kan:kanTarget[0],cohortRows:visible.length,preservedN12:cohortN12.pollId,newVerifiedPublisherExcludedC14:cohortC14.pollId,newRows};
  return section;
}
async function pollDataView(){
  const register=page.locator('[data-component-id="source-poll-register"]');
  const matrix=page.locator('[data-poll-matrix]');
  const targets=[tatika,i24,c16,walla,n12,c14,c13,kan];const rendered=[];
  assert.equal(await register.locator('.tp-register tbody tr').count(),current.polls.length);
  for(const poll of targets){
    const row=register.locator('.tp-register tbody tr').filter({hasText:poll.publisher});assert.equal(await row.count(),1);
    const cells=await row.locator('td').allTextContents();
    const date=value=>value.split('-').reverse().join('.');
    const interval=poll.fieldworkStart&&poll.fieldworkEnd?(poll.fieldworkStart===poll.fieldworkEnd?date(poll.fieldworkStart):date(poll.fieldworkStart)+'–'+date(poll.fieldworkEnd)):'לא אומת';
    assert.equal(cells[0].trim(),date(poll.date));assert.equal(cells[1].trim(),interval);assert.ok(cells[2].trim().startsWith(poll.sampleSize==null?'לא פורסם':String(poll.sampleSize)),'Sample exact value / absence: '+poll.id);
    assert.equal(await row.getByRole('link',{name:'מקור גודל המדגם',exact:true}).getAttribute('href'),poll.sampleSizeSourceUrl);
    for(const [id,seats] of Object.entries(poll.seats)){
      const cell=matrix.locator('td[data-poll-id="'+poll.id+'"][data-party-id="'+id+'"]');assert.equal(await cell.count(),1);
      assert.equal((await cell.locator('bdi').innerText()).trim(),String(seats));
    }
    rendered.push({pollId:poll.id,text:await row.innerText(),source:poll.sourceUrl,sampleSource:poll.sampleSizeSourceUrl});
    assert.equal(await matrix.locator('td[data-poll-id="'+poll.id+'"][data-party-id="other"]').count(),0);
  }
  await choose('מה להציג בטבלה','אחוזי תמיכה שפורסמו');const support=[];
  for(const poll of targets){
    const cells={};
    for(const party of snapshotInput.parties.filter(p=>p.ballot!==false)){
      const cell=matrix.locator('td[data-poll-id="'+poll.id+'"][data-party-id="'+party.id+'"]');assert.equal(await cell.count(),1);
      const text=(await cell.locator('bdi').innerText()).trim();
      const bound=poll.publishedBounds?.[party.id];
      const expected=Object.hasOwn(poll.reportedPercentages??{},party.id)?format(poll.reportedPercentages[party.id],2)+'%':bound?.maxExclusive&&bound.max!=null?'פחות מ־'+format(bound.max,0)+'%':'—';
      assert.equal(text,expected,'Published percentage / missingness: '+poll.id+'/'+party.id);cells[party.id]=text;
    }
    support.push({pollId:poll.id,cells,modelOnlyIds:poll.modelOnlyPercentageIds??[],derivedOther:poll.percentages.other??null,derivedOtherShownAsPublished:false});
  }
  const c16Notes=register.locator('details').filter({has:page.getByText('הערות ומגבלות — '+c16.publisher,{exact:true})});
  await detail(c16Notes,true);assert.match(await c16Notes.innerText(),/2000|2,000/);await detail(c16Notes,false);
  report.pollRegisters=rendered;report.reportedSupport=support;
  await choose('מה להציג בטבלה','מנדטים בסקר');return register;
}
async function checkThresholdAlignment(label,result,sort="threshold"){
  const section=page.locator('[data-component-id="threshold-overview"]');
  await section.waitFor();
  const rows=await section.evaluate(node=>{
    const marks=[...node.querySelectorAll('.bar-family-list-row')];
    const logos=[...node.querySelectorAll('.tp-chart-logo')];
    const plot=node.querySelector('.tp-logo-chart-plot').getBoundingClientRect();
    return logos.map((logo,index)=>{
      const a=logo.getBoundingClientRect(),mark=marks[index],b=mark?.getBoundingClientRect();
      const value=mark?.querySelector('.bar-family-list-copy strong')?.getBoundingClientRect();
      return {partyId:logo.dataset.partyId,title:logo.title,meanText:logo.querySelector('.tp-overview-mean')?.textContent,markLabel:mark?.getAttribute('aria-label')??null,
        logoCenterY:a.top+a.height/2,markCenterY:b?b.top+b.height/2:null,
        logoHeight:logo.querySelector('.party-logo')?.getBoundingClientRect().height??null,
        rowHeight:b?.height??null,valueLeft:value?.left??null,valueRight:value?.right??null,plotLeft:plot.left,plotRight:plot.right,offsetPx:b?(a.top+a.height/2)-(b.top+b.height/2):null};
    });
  });
  const modelled=p=>p.hasModelledSupport===true||(p.hasModelledSupport==null&&Number(p.meanVotePct)>0);
  const expectedParties=result.parties.filter(p=>p.ballot!==false&&modelled(p)).slice().sort((a,b)=>sort==='name'?a.name.localeCompare(b.name,'he'):sort==='pass'?(b.passProbability-a.passProbability)||(b.mean-a.mean)||a.name.localeCompare(b.name,'he'):Math.abs(a.passProbability-.5)-Math.abs(b.passProbability-.5)||a.name.localeCompare(b.name,'he'));
  assert.deepEqual(rows.map(row=>row.partyId),expectedParties.map(p=>p.id),'Every modeled party rail follows the selected ordering: '+label);
  assert.ok(rows.length>0,'Threshold chart must expose native rows and matching custom logos');
  for(const row of rows){
    const expected=result.parties.find(p=>p.id===row.partyId);
    assert.ok(expected,'Threshold row must match an exported result: '+row.partyId);
    assert.equal(row.meanText,format(expected.mean,1),'Displayed mean retains actual result: '+row.partyId);
    assert.equal(row.markLabel,expected.name+': '+format(expected.passProbability*100,2)+'%','Native mark must retain its exact party/probability');
    assert.ok(row.markCenterY!==null,'Threshold logo requires a native mark: '+row.partyId);
    assert.ok(Math.abs(row.offsetPx)<=2,'Threshold logo/mean rail is vertically misaligned at '+label+': '+row.partyId+' '+row.offsetPx+'px');
    assert.ok(row.logoHeight>=24,'Party logos must remain readable: '+row.partyId);
    assert.ok(row.valueLeft!==null&&row.valueRight!==null,'Native percent must remain visible: '+row.partyId);
    assert.ok(row.valueLeft>=row.plotLeft-1&&row.valueRight<=row.plotRight+1,'Native percent is clipped at '+label+': '+row.partyId);
  }
  report.thresholdAlignments.push({label,rows,maxOffsetPx:Math.max(...rows.map(row=>Math.abs(row.offsetPx)))});
  return section;
}

async function checkDirectAssignment(baseline){
  const board=page.locator('[data-direct-party-board]');await board.waitFor();
  const ballotIds=baseline.input.parties.filter(p=>p.ballot!==false).map(p=>p.id).sort();
  const original=baseline.config.partyBlocs.likud;
  for(const bloc of ['b','other',original]){
    await board.locator('select[data-party-assignment-select="likud"]').selectOption(bloc);await ready();
    const state=await exported('direct-assignment-'+bloc);
    assert.equal(state.config.partyBlocs.likud,bloc);assert.equal(await board.locator('[data-party-assignment][data-party-id="likud"]').count(),1);
    assert.equal(await board.locator('[data-party-drop-zone="'+bloc+'"] [data-party-assignment][data-party-id="likud"]').count(),1);
    const rows=await board.locator('[data-party-assignment]').evaluateAll(nodes=>nodes.map(n=>({id:n.dataset.partyId,bloc:n.dataset.assignedBloc})));
    assert.deepEqual(rows.map(r=>r.id).sort(),ballotIds);assert.equal(new Set(rows.map(r=>r.id)).size,ballotIds.length);
    for(const row of rows)assert.equal(row.bloc,state.config.partyBlocs[row.id]);
  }
  const restored=await exported('direct-assignment-restored');assert.deepEqual(restored.config,baseline.config);assert.deepEqual(restored.result.parties,baseline.result.parties);assert.deepEqual(restored.result.thresholdJoint,baseline.result.thresholdJoint);
  report.checks.push('Direct click/select assignment moves each party to exactly one group or unassigned, preserves the120-seat partition, and restoring the prior assignment reproduces exact seeded results');
}

// Independent exact histogram aggregation, without importing the UI's analyzer.
function allFail(result,ids){
  const joint=result.thresholdJoint;
  assert.ok(joint&&Array.isArray(joint.partyIds)&&Array.isArray(joint.patterns));
  assert.equal(joint.total,result.iterations);
  assert.equal(new Set(joint.partyIds).size,joint.partyIds.length);
  const indices=ids.map(id=>joint.partyIds.indexOf(id));
  assert.ok(indices.every(i=>i>=0));
  const counts=Array(ids.length+1).fill(0),seen=new Set();
  const marginals=Array(ids.length).fill(0);
  for(const pattern of joint.patterns){
    assert.equal(pattern.failed.length,joint.partyIds.length);
    assert.match(pattern.failed,/^[01]+$/);
    assert.ok(!seen.has(pattern.failed));seen.add(pattern.failed);
    assert.ok(Number.isSafeInteger(pattern.count)&&pattern.count>=0);
    const bits=indices.map(index=>Number(pattern.failed[index]));
    counts[bits.reduce((sum,bit)=>sum+bit,0)]+=pattern.count;
    bits.forEach((bit,index)=>{marginals[index]+=bit*pattern.count;});
  }
  const total=counts.reduce((sum,n)=>sum+n,0);
  assert.equal(total,joint.total);
  const count=counts[ids.length],probability=count/total;
  const z=1.959963984540054,z2=z*z,denominator=1+z2/total;
  const center=(probability+z2/(2*total))/denominator;
  const half=z*Math.sqrt(probability*(1-probability)/total+z2/(4*total*total))/denominator;
  return {ids,count,total,probability,distribution:counts,ci:[center-half,center+half],
    atLeastTwoCount:counts.slice(2).reduce((sum,n)=>sum+n,0),independenceProduct:marginals.reduce((p,n)=>p*n/total,1)};
}
async function checkJoint(result,ids){
  const panel=page.locator('[data-joint-threshold-panel]');
  assert.equal(await panel.getAttribute('data-status'),'ready');
  const selected=(await panel.locator('input[data-joint-party]:checked').evaluateAll(nodes=>nodes.map(node=>node.dataset.jointParty))).sort();
  assert.deepEqual(selected,[...ids].sort());
  assert.equal(await panel.getByRole('combobox').count(),0);
  const expected=allFail(result,ids),answer=panel.locator('[data-joint-probability]');
  assert.equal(await answer.getAttribute('data-joint-mode'),'allFail');
  assert.equal(Number(await answer.getAttribute('data-joint-count')),expected.count);
  assert.equal(Number(await answer.getAttribute('data-joint-total')),expected.total);
  assert.equal(Number(await answer.getAttribute('data-joint-probability')),expected.probability);
  for(const [key,index] of [['data-joint-ci-low',0],['data-joint-ci-high',1]])
    assert.ok(Math.abs(Number(await answer.getAttribute(key))-expected.ci[index])<1e-7);
  const details=panel.locator('.jtp-details');await detail(details,true);
  const histogram=await details.locator('tbody tr').evaluateAll(rows=>rows.map(row=>({failed:Number(row.dataset.jointFailedCount),selected:row.dataset.selected,count:row.children[1].textContent})));
  assert.equal(histogram.length,ids.length+1);
  for(const row of histogram){assert.equal(numeric(row.count),expected.distribution[row.failed]);assert.equal(row.selected,String(row.failed===ids.length));}
  assert.equal(histogram.filter(row=>row.selected==='true').length,1);
  return expected;
}
try{
  const context=await browser.newContext({viewport:{width:1440,height:1080},colorScheme:'light',acceptDownloads:true});
  page=await context.newPage();page.setDefaultTimeout(60000);
  page.on('pageerror',error=>report.pageErrors.push(error.message));
  const fresh=new URL(base);fresh.searchParams.delete('tab');fresh.searchParams.delete('view');fresh.hash='';fresh.searchParams.set('qa',runId);
  const response=await page.goto(fresh.href,{waitUntil:'load'});
  assert.ok(response?.ok(),'The served page must be accessible');report.response={url:response?.url()??page.url(),status:response?.status()??null};
  await page.locator('.election-app[data-page="about"]').waitFor();
  assert.equal(await page.getByRole('tab').count(),tabs.length);
  for(const [,label] of tabs)assert.equal(await page.getByRole('tab',{name:label,exact:true}).count(),1);
  await noChatGPT();
  const about=page.locator('.election-app[data-page="about"]');
  assert.match(await about.innerText(),/ויקטור רינה בן דוד/);
  const photo=about.locator('img').first();
  assert.ok(await about.locator('img').count()>0);
  await photo.waitFor();
  await page.waitForFunction(()=>{const img=document.querySelector('.election-app[data-page="about"] img');return img?.complete&&img.naturalWidth>0;});
  await geometry('1440-about');
  await page.screenshot({path:path.join(out,'1440-about-light.png'),fullPage:false});
  const appearance=page.locator('[data-appearance-toggle]');
  assert.equal(await appearance.count(),1);assert.equal(await appearance.getAttribute('data-color-scheme'),'light');
  await appearance.click();await page.waitForFunction(()=>document.querySelector('[data-appearance-toggle]')?.dataset.colorScheme==='dark');
  await page.reload({waitUntil:'load'});await about.waitFor();
  assert.equal(await appearance.getAttribute('data-color-scheme'),'dark');
  await page.screenshot({path:path.join(out,'1440-about-dark.png'),fullPage:false});
  await appearance.click();await page.waitForFunction(()=>document.querySelector('[data-appearance-toggle]')?.dataset.colorScheme==='light');
  report.checks.push('Fresh About with loaded author photo; seven stable tab labels; no Ask ChatGPT; light/dark persists after reload');

  await tab('dashboard');const baseline=await exported('default-scenario');
  for(const [label,key] of [['כלול סקרי ערוץ 14','includeChannel14'],['דמיון בין סקרים','pollCorrelationEnabled']]){
    const control=page.getByRole('switch',{name:label,exact:true});assert.ok(await control.isVisible());assert.equal(await control.getAttribute('aria-checked'),'false');assert.equal(baseline.config[key],false);
  }
  report.checks.push('New Tatika published15Oct/field14–15/n500 and123history rows, same-day audit15Oct, fresh strict/correlation date, retained N12/Kan/i24/C16/Walla served exactly; quality weights, Channel14 off, signal/noise off, similarity off; 120-seat partition');

  await page.locator('#run-settings input[type=file]').setInputFiles(path.join(out,'default-scenario.json'));
  await ready();const savedRoundtrip=await exported('saved-scenario-roundtrip');
  assert.deepEqual(savedRoundtrip.config,baseline.config,'Saved JSON preserves every scenario setting');
  assert.deepEqual(savedRoundtrip.result.parties,baseline.result.parties,'Saved JSON replays the same seeded party results');
  assert.deepEqual(savedRoundtrip.result.thresholdJoint,baseline.result.thresholdJoint,'Saved JSON replays the complete joint histogram');
  assert.equal(await page.locator('[data-appearance-toggle]').getAttribute('data-color-scheme'),'light');
  report.checks.push('Saved scenario JSON roundtrip retains all settings, flags, canonical inputs and exact seeded party/joint results');
  await checkDirectAssignment(baseline);
  for(const [id] of tabs){await tab(id);await noChatGPT();await geometry('1440-'+id);}
  report.checks.push('All seven stable tab IDs render and preserve desktop geometry');
  await tab('poll-trends');const trends=await strictView();
  await trends.evaluate(node=>{node.scrollIntoView({block:'start'});window.scrollBy(0,-120);});
  await page.screenshot({path:path.join(out,'1440-trends.png'),fullPage:false});
  report.checks.push('Strict analysis is audited October15 and defaults to independently recomputed37/7/30 without14 coverage;46/8/38 full. Exact p/q/verdicts, C13 field13/publication14 eligible, C14 field14 verified but publisher-excluded, C16/Kan still excluded for unverified fieldwork.');
  await tab('poll-data');const register=await pollDataView();
  await register.evaluate(node=>{node.scrollIntoView({block:'start'});window.scrollBy(0,-120);});
  await page.screenshot({path:path.join(out,'1440-poll-data.png'),fullPage:false});
  report.checks.push('Poll register shows new Tatika published15/field14–15/n500, unchanged C13 published14/field13/n1018 and C14 published14/field14/n568; i24 bounds, Walla13/field12/n601, C16 unknownfieldwork/exactn with separate>2000 qualifier and Kan unknownfieldwork preserved. All raw vectors/pcts/missingness retained; C14 Ahi0.2 mapped to model-only other, not shown as a published aggregate.');

  await tab('probabilities');
  const thresholdOverview=await checkThresholdAlignment('1440-default',baseline.result);
  await thresholdOverview.screenshot({path:path.join(out,'1440-default-threshold-overview.png')});
  await choose('סדר המפלגות','סיכוי מעבר גבוה תחילה');
  await checkThresholdAlignment('1440-pass-sorted',baseline.result,'pass');
  await choose('סדר המפלגות','לפי שם');
  await checkThresholdAlignment('1440-name-sorted',baseline.result,'name');
  await choose('סדר המפלגות','הכי קרובות ל־50% מעבר');
  report.chartCustomizationLimits='Progress-chart editor does not expose thickness or native sort controls in this copied runtime; public party ordering is verified instead. No storage or protected runtime mutations performed.';
  report.pair=await checkJoint(baseline.result,['winter','hendel']);
  await page.locator('input[data-joint-party="raam"]').check();
  report.triple=await checkJoint(baseline.result,['winter','hendel','raam']);
  assert.match(await page.locator('.jtp-answer h3').innerText(),/כל 3 המפלגות/);
  const csvFile=await downloaded(page.locator('[data-joint-threshold-panel]').getByRole('button',{name:'יצוא הסיכוי המשותף CSV',exact:true}),'triple-all-fail.csv');
  const csv=fs.readFileSync(csvFile,'utf8');
  assert.match(csv,/allFail/);assert.match(csv,/winter;hendel;raam/);assert.match(csv,/כל 3 המפלגות/);assert.ok(!csv.includes('atLeastTwo'));
  report.checks.push('Default threshold logos/means align with native rows; percentages fit their plot at every tested width, retain full accessible labels, large logos and exact exported probabilities; pair and triple ALL-selected-fail counts/probabilities/Wilson intervals/distributions match independent aggregation of the same exported simulation histogram; CSV retains the event');

  for(const width of [390,320]){
    await page.setViewportSize({width,height:844});
    for(const [id] of tabs){await tab(id);await geometry(width+'-'+id);await noChatGPT();
      if(id==='probabilities'){const overview=await checkThresholdAlignment(width+'-default',baseline.result);await overview.screenshot({path:path.join(out,width+'-default-threshold-overview.png')});}
      if(width===390&&id==='poll-trends'){
        const section=await strictView();await section.evaluate(node=>{node.scrollIntoView({block:'start'});window.scrollBy(0,-100);});
        await page.screenshot({path:path.join(out,'390-trends.png'),fullPage:false});
      }
      if(width===390&&id==='poll-data'){
        const table=await pollDataView();await table.evaluate(node=>{node.scrollIntoView({block:'start'});window.scrollBy(0,-100);});
        await page.screenshot({path:path.join(out,'390-poll-data.png'),fullPage:false});
      }
    }
  }
  await page.setViewportSize({width:390,height:844});await tab('probabilities');
  // Tab mounting resets local selections. Verify the current pair, then select the triple again.
  await checkJoint(baseline.result,['winter','hendel']);
  await page.locator('input[data-joint-party="raam"]').check();await checkJoint(baseline.result,['winter','hendel','raam']);
  await page.locator('[data-joint-threshold-panel]').screenshot({path:path.join(out,'390-triple-all-fail.png')});
  await geometry('390-joint-triple');
  const deep=new URL(base);deep.searchParams.set('tab','poll-trends');deep.searchParams.set('view','1');deep.searchParams.set('qa',runId);
  await page.goto(deep.href,{waitUntil:'load'});await page.locator('.election-app[data-page="poll-trends"]').waitFor();await ready();await strictView();
  report.checks.push('All seven tabs fit 390px and 320px without document overflow; mobile joint selection and explicit poll-trends deep link work');
  preserveFiles();
  for(const [rel,digest] of Object.entries(sourceHashBaseline))assert.equal(sha(rel),digest,'Browser QA must not mutate canonical data/snapshot: '+rel);
  report.afterSourceHashes=Object.fromEntries(boundSourcePaths.map(rel=>[rel,sha(rel)]));
  report.thresholdAlignedRowChecks=report.thresholdAlignments.reduce((sum,test)=>sum+test.rows.length,0);
  assert.ok(report.thresholdAlignedRowChecks>=80,'At least the existing80 complete row-alignment/percent-bound checks must remain covered');
  report.checks.push('Checkpoint, all117author/234runtime/1831public/14conditional files and correctly bound old289baseline remain immutable; canonical identity/hash is unchanged through this QA run');
  assert.deepEqual(report.pageErrors,[]);report.status='passed';report.checkedAt=new Date().toISOString();
}catch(error){
  report.status='failed';report.failure={message:error.message,stack:error.stack};process.exitCode=1;
  if(page)await page.screenshot({path:path.join(out,'failure.png'),fullPage:true}).catch(()=>{});
}finally{
  fs.writeFileSync(path.join(out,'report.json'),JSON.stringify(report,null,2)+'\n');
  await browser.close();
  console.log(JSON.stringify({status:report.status,phase:options.phase,report:path.join(out,'report.json'),checks:report.checks.length,geometry:report.geometry.length,pair:report.pair?.probability,triple:report.triple?.probability,failure:report.failure?.message}));
}

