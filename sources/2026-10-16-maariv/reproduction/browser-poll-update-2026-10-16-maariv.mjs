/**
 * Browser evidence for the Maariv/Lazar update preserving the reviewed UI12 threshold alignment, 16 October 2026.
 * Run only after the official source build. This script reads canonical data
 * and writes new evidence solely under the selected dated browser phase.
 * Usage: node scripts/browser-poll-update-2026-10-16-maariv.mjs --base URL --phase local|public
 */
import {createRequire} from 'node:module';
import {fileURLToPath} from 'node:url';
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import assert from 'node:assert/strict';

const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const evidenceRoot=path.join(root,'artifacts','poll-checks','2026-10-16-maariv');
const checkpoint='artifacts/poll-checks/2026-10-16-maariv/before';
const ui12CanonicalCheckpoint='artifacts/poll-checks/2026-10-12-evening/before';
const read=rel=>JSON.parse(fs.readFileSync(path.join(root,rel),'utf8').replace(/^\uFEFF/,''));
const sha=rel=>crypto.createHash('sha256').update(fs.readFileSync(path.join(root,rel))).digest('hex');
const manifest=read(checkpoint+'/manifest.json');
const uiBaselinePath='C:/Users/User/.codex/visualizations/2026/09/12/01a0952c-a40b-7b01-b019-621f0cee2656/artifacts/ui-threshold-alignment-2026-10-12/frozen-baseline-hashes.json';
const frozenBaseline=JSON.parse(fs.readFileSync(uiBaselinePath,'utf8').replace(/^\uFEFF/,''));
const updatedCanonical=new Set(['data/current-polls.json','data/poll-history.json','data/poll-correlation.json','data/strict-party-trends.json','data/strict-party-trends-without-channel14.json']);
function preserveFiles(){
  for(const [rel,digest] of Object.entries(manifest.files))assert.equal(sha(checkpoint+'/'+rel),digest,'Immutable evening checkpoint: '+rel);
  for(const category of ['authorContentHashes','protectedRuntimeHashes','frozenEvidenceHashes','frozenConditionalAndArtisticHashes','reviewedExactHelpers'])
    for(const [rel,digest] of Object.entries(manifest[category]))assert.equal(sha(rel),digest,'Preserved '+category+': '+rel);
  assert.equal(Object.keys(manifest.authorContentHashes).length,117,'All authored content is in scope');
  assert.equal(Object.keys(manifest.protectedRuntimeHashes).length,234);
  assert.ok(Object.keys(manifest.frozenEvidenceHashes).length>0,'Every previously published evidence file remains protected');
  assert.equal(Object.keys(manifest.frozenConditionalAndArtisticHashes).length,14);
  assert.equal(Object.keys(manifest.reviewedExactHelpers).length,4);
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
const DAY='2026-10-16';
const current=read('data/current-polls.json'),history=read('data/poll-history.json');
const fullStrict=read('data/strict-party-trends.json'),strict=read('data/strict-party-trends-without-channel14.json');
const correlation=read('data/poll-correlation.json'),snapshot=read('dashboard/src/data.json');
const plan=read('artifacts/poll-checks/2026-10-16-maariv/source-plan.json');
const preflight=read('artifacts/poll-checks/2026-10-16-maariv/ingestion-preflight.json');
const ingestion=read('artifacts/poll-checks/2026-10-16-maariv/ingestion-validation.json');
assert.equal(plan.status,'reviewed');assert.equal(ingestion.status,'PASS');
assert.equal(sha('artifacts/poll-checks/2026-10-16-maariv/source-plan.json'),preflight.sourcePlanSha256);
assert.equal(preflight.sourcePlanSha256,ingestion.sourcePlanSha256);
const beforeCurrent=read(checkpoint+'/data/current-polls.json'),beforeHistory=read(checkpoint+'/data/poll-history.json');
const beforeFull=read(checkpoint+'/data/strict-party-trends.json'),beforeStrict=read(checkpoint+'/data/strict-party-trends-without-channel14.json');
for(const value of [current,history,fullStrict,strict,correlation,plan])assert.equal(value.asOf,DAY,'Post-update prerequisite date');
assert.equal(beforeCurrent.asOf,manifest.baselineAsOf);assert.equal(manifest.updateDate,DAY);
assert.equal(current.polls.length,manifest.activePollCount);assert.equal(current.polls.length,ingestion.activePollCount);
assert.equal(history.polls.length,manifest.historyPollCount+plan.polls.length);assert.equal(history.polls.length,ingestion.historyPollCount);
const expectedFull={pollCount:preflight.expectedStrictEligible,seriesCount:ingestion.fullStrict.series,deltaCount:ingestion.fullStrict.deltas};
const expectedWithout14={pollCount:preflight.expectedStrictWithoutChannel14,seriesCount:ingestion.defaultWithoutChannel14.series,deltaCount:ingestion.defaultWithoutChannel14.deltas};
for(const [value,expected] of [[fullStrict,expectedFull],[strict,expectedWithout14]]){
 for(const [key,n] of Object.entries(expected))assert.equal(value.coverage[key],n);
 assert.equal(value.cohort.length,beforeFull.cohort.length+plan.polls.length);
 assert.equal(value.coverage.partyCount,snapshot.queries.verified_party_trends.rows.length);
}
assert.equal(snapshot.features.chatGPT,false);
const snapshotInput=Object.fromEntries(snapshot.queries.model_input.rows.map(r=>[r.key,r.value]));
assert.deepEqual(snapshotInput.current,current);assert.deepEqual(snapshotInput.history,history);assert.deepEqual(snapshotInput.calibration.pollCorrelation,correlation);
for(const [prefix,value,pollsId] of [['verified_party_trends',fullStrict,'verified_party_trend_polls'],['verified_party_trends_without_channel14',strict,'verified_party_trends_without_channel14_polls']]){
 assert.equal(snapshot.queries[prefix+'_metadata'].rows[0].asOf,DAY);assert.deepEqual(snapshot.queries[prefix+'_metadata'].rows[0].coverage,value.coverage);
 assert.deepEqual(snapshot.queries[prefix].rows,value.rows);assert.deepEqual(snapshot.queries[pollsId].rows,value.cohort);
}
const candidates=plan.polls.map(spec=>{assert.equal(sha(spec.candidatePath),spec.candidateSha256);return read(spec.candidatePath);});
const removedIds=new Set(candidates.map(p=>p.replacesPollId)),addedIds=new Set(candidates.map(p=>p.id));
assert.deepEqual(beforeCurrent.polls.map(p=>p.id).filter(id=>!current.polls.some(p=>p.id===id)).sort(),[...removedIds].sort());
assert.deepEqual(current.polls.map(p=>p.id).filter(id=>!beforeCurrent.polls.some(p=>p.id===id)).sort(),[...addedIds].sort());
for(const old of beforeCurrent.polls)if(!removedIds.has(old.id))assert.deepEqual(current.polls.find(p=>p.id===old.id),old,'Unrelated active observation unchanged: '+old.id);
for(const old of beforeHistory.polls){const successor=candidates.find(p=>'history_'+p.replacesPollId+'_current'===old.id);assert.deepEqual(history.polls.find(p=>p.id===old.id),successor?{...old,recordStatus:'superseded-reviewed-record',replacedByPollId:successor.id}:old,'Prior history retained: '+old.id);}
assert.deepEqual(history.polls.filter(p=>!beforeHistory.polls.some(old=>old.id===p.id)).map(p=>p.id).sort(),candidates.map(p=>'history_'+p.id+'_current').sort());
for(const candidate of candidates){
 const poll=current.polls.find(p=>p.id===candidate.id);assert.ok(poll);assert.equal(poll.pollsterId,candidate.pollsterId);
 for(const key of ['id','pollsterId','date','fieldworkStart','fieldworkEnd','sampleSize','seats','reportedPercentages','percentages','modelOnlyPercentageIds','sourceBlocSeats','sourceBlocDefinitions','unmodelledNamedParties','publishedBounds','sourceTier','samplingMethod','panelProvider','percentageDenominator','reportedMarginOfErrorPct','reportedMarginOfErrorConfidencePct','invitedSampleSize','requestedParticipationCount'])assert.deepEqual(poll[key],candidate[key],'Fresh reviewed field: '+key);
 assert.equal(Object.values(poll.seats).reduce((a,b)=>a+b,0),120);
 const cohort=strict.cohort.find(p=>p.pollId==='history_'+poll.id+'_current');assert.ok(cohort);
 assert.equal(cohort.eligibleStrict,plan.polls.find(p=>p.pollsterId===poll.pollsterId).strictEligible);
 assert.equal(cohort.fieldworkStart,poll.fieldworkStart);assert.equal(cohort.fieldworkEnd,poll.fieldworkEnd);
}
const newCohorts=candidates.map(p=>strict.cohort.find(row=>row.pollId==='history_'+p.id+'_current'));
const c16=current.polls.find(p=>p.pollsterId==='maagar_mochot');
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
  sourceHashes:sourceHashBaseline,sourcePlanSha256:sha('artifacts/poll-checks/2026-10-16-maariv/source-plan.json'),
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
  assert.equal(value.config.asOf,DAY);
  assert.equal(value.config.weightMode,'quality');
  assert.equal(value.config.includeChannel14,false);
  assert.equal(value.config.signalNoiseEnabled,false);
  assert.equal(value.config.pollCorrelationEnabled,false);
  assert.equal(value.result.checks.eachWorld120,true);
  assert.equal(value.result.checks.blocPartition120,true);
  assert.ok(Math.abs(value.result.parties.reduce((sum,p)=>sum+p.mean,0)-120)<1e-8);
  assert.deepEqual(value.input.current,current,'Served app must contain all corrected canonical poll metadata');
  assert.deepEqual(value.input.history,history);assert.deepEqual(value.input.calibration.pollCorrelation,correlation);
  assert.equal(value.input.current.polls.length,ingestion.activePollCount);assert.equal(value.input.history.polls.length,ingestion.historyPollCount);
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
  assert.match(await section.locator('.vpt-date').innerText(),/16\.10\.2026/);
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
  const freshRows=[];
  for(const [index,poll] of candidates.entries()){
    const cohort=newCohorts[index],date=poll.date.split('-').reverse().join('.');
    const matches=visible.filter(row=>row.href===cohort.sourceUrls[0]&&row.text.includes(date));
    assert.equal(matches.length,1,'One fresh reviewed observation in visible cohort: '+poll.id);
    assert.equal(matches[0].decision,cohort.eligibleStrict?'נכלל':cohort.channel14Excluded?'הוחרג לפי מתג ערוץ 14':'הוחרג');
    for(const key of ['fieldworkStart','fieldworkEnd'])if(poll[key])assert.ok(matches[0].text.includes(poll[key].split('-').reverse().join('.')));
    const missingDates=['fieldworkStart','fieldworkEnd'].filter(key=>poll[key]==null).length;
    if(missingDates)assert.ok((matches[0].text.match(/לא אומת/g)??[]).length>=missingDates,'Unknown fieldwork is visibly marked for '+poll.id);
    freshRows.push({pollId:poll.id,...matches[0]});
  }
  report.strict={asOf:strict.asOf,coverage:strict.coverage,significant,cohortRows:visible.length,freshRows};
  return section;
}
async function pollDataView(){
  const register=page.locator('[data-component-id="source-poll-register"]');
  const matrix=page.locator('[data-poll-matrix]');
  const targets=current.polls;const rendered=[];
  assert.equal(await register.locator('.tp-register tbody tr').count(),current.polls.length);
  for(const poll of targets){
    const row=register.locator('.tp-register tbody tr').filter({hasText:poll.publisher});assert.equal(await row.count(),1);
    const cells=await row.locator('td').allTextContents();
    const date=value=>value.split('-').reverse().join('.');
    const interval=poll.fieldworkStart&&poll.fieldworkEnd?(poll.fieldworkStart===poll.fieldworkEnd?date(poll.fieldworkStart):date(poll.fieldworkStart)+'–'+date(poll.fieldworkEnd)):'לא אומת';
    assert.equal(cells[0].trim(),date(poll.date));assert.equal(cells[1].trim(),interval);assert.ok(cells[2].trim().startsWith(poll.sampleSize==null?'לא פורסם':String(poll.sampleSize)),'Sample exact value / absence: '+poll.id);
    const sampleLink=row.getByRole('link',{name:'מקור גודל המדגם',exact:true});
    if(poll.sampleSizeSourceUrl)assert.equal(await sampleLink.getAttribute('href'),poll.sampleSizeSourceUrl);else assert.equal(await sampleLink.count(),0);
    if(candidates.some(p=>p.id===poll.id)){
      const label=poll.sourceTier==='original-publisher'?'פרסום מקורי':poll.sourceTier==='pollster-report'?'דוח הסוקר PDF':'מקור שנאסף';
      assert.equal(await row.getByRole('link',{name:label,exact:true}).getAttribute('href'),poll.sourceUrl);
      assert.ok(cells[4].includes(poll.sourceTier==='original-publisher'?'מקור ראשוני':poll.sourceTier==='pollster-report'?'קובץ שנמסר ונבדק':'נתונים ממאגר משני'));
    }
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
  report.checks.push('New reviewed Maariv observation and all authenticated history rows are served exactly; October16 strict/correlation date, quality weights, Channel14 off, signal/noise off, similarity off and120-seat partition');

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
  report.checks.push('Fresh October16 full/default cohorts match authenticated ingestion counts; exact p/q/verdicts and fieldwork eligibility displayed. Publisher exclusion remains separate from unverified fieldwork.');
  await tab('poll-data');const register=await pollDataView();
  await register.evaluate(node=>{node.scrollIntoView({block:'start'});window.scrollBy(0,-120);});
  await page.screenshot({path:path.join(out,'1440-poll-data.png'),fullPage:false});
  report.checks.push('All active observation/fieldwork dates, sample sources or absence, seat vectors, exact reported percentages, censored bounds and missingness match authenticated canonical inputs. New Maariv retrieval category is shown truthfully; model-only other is not displayed as published support.');

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
  report.checks.push('Checkpoint, all authenticated author/runtime/prior-public/conditional files and correctly bound old289baseline remain immutable; canonical identity/hash is unchanged through this QA run');
  assert.deepEqual(report.pageErrors,[]);report.status='passed';report.checkedAt=new Date().toISOString();
}catch(error){
  report.status='failed';report.failure={message:error.message,stack:error.stack};process.exitCode=1;
  if(page)await page.screenshot({path:path.join(out,'failure.png'),fullPage:true}).catch(()=>{});
}finally{
  fs.writeFileSync(path.join(out,'report.json'),JSON.stringify(report,null,2)+'\n');
  await browser.close();
  console.log(JSON.stringify({status:report.status,phase:options.phase,report:path.join(out,'report.json'),checks:report.checks.length,geometry:report.geometry.length,pair:report.pair?.probability,triple:report.triple?.probability,failure:report.failure?.message}));
}

