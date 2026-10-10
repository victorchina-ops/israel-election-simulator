/**
 * Browser evidence for the C13 official metadata revision, 10 October 2026.
 * Run only after the official source build. This script reads canonical data
 * and writes new evidence solely under the selected dated browser phase.
 * Usage: node scripts/browser-c13-official-revision-2026-10-10.mjs --base URL --phase local|public
 */
import {createRequire} from 'node:module';
import {fileURLToPath} from 'node:url';
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import assert from 'node:assert/strict';

const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const read=rel=>JSON.parse(fs.readFileSync(path.join(root,rel),'utf8').replace(/^\uFEFF/,''));
const sha=rel=>crypto.createHash('sha256').update(fs.readFileSync(path.join(root,rel))).digest('hex');
const options={};
for(let i=2;i<process.argv.length;i+=2){
  assert.ok(['--base','--phase'].includes(process.argv[i]),'Unknown option '+process.argv[i]);
  assert.ok(process.argv[i+1],'Missing value for '+process.argv[i]);
  options[process.argv[i].slice(2)]=process.argv[i+1];
}
assert.ok(options.base,'--base is required');
assert.ok(['local','public'].includes(options.phase),'--phase must be local or public');
const base=new URL(options.base);
assert.ok(['http:','https:','file:'].includes(base.protocol),'--base must be an HTTP(S) or local dist file URL');
if(base.protocol==='file:'){assert.equal(options.phase,'local');assert.equal(path.resolve(fileURLToPath(base)),path.join(root,'dashboard','dist','index.html'));}
const current=read('data/current-polls.json');
const fullStrict=read('data/strict-party-trends.json');
const strict=read('data/strict-party-trends-without-channel14.json');
for(const value of [current,fullStrict,strict])assert.equal(value.asOf,'2026-10-10','Build prerequisites must have the corrected analysis date');
const c13=current.polls.find(p=>p.id==='hamadad_consortium_2026-10-07');
assert.ok(c13,'C13 must remain the existing poll ID');
assert.equal(c13.fieldworkStart,'2026-10-06');
assert.equal(c13.fieldworkEnd,'2026-10-07');
assert.equal(c13.sampleSize,1263);
const cohortC13=strict.cohort.find(p=>p.pollId==='history_hamadad_consortium_2026-10-07_current');
assert.ok(cohortC13?.eligibleStrict,'Corrected C13 must remain in the strict cohort');
assert.equal(cohortC13.fieldworkEnd,'2026-10-07');

const runId=new Date().toISOString().replace(/[:.]/g,'-')+'-'+process.pid;
const phaseRoot=path.join(root,'artifacts','poll-checks','2026-10-10','browser-'+options.phase);
fs.mkdirSync(phaseRoot,{recursive:true});
const out=path.join(phaseRoot,runId);
fs.mkdirSync(out); // No prior run or frozen evidence can be overwritten.
const require=createRequire('C:/Users/User/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright/package.json');
const {chromium}=require('playwright');
const report={
  status:'running',phase:options.phase,runId,base:base.href,asOf:current.asOf,
  expectedCoverage:strict.coverage,checks:[],geometry:[],pageErrors:[],
  sourceHashes:Object.fromEntries([
    'data/current-polls.json','data/strict-party-trends.json','data/strict-party-trends-without-channel14.json',
    'scripts/browser-c13-official-revision-2026-10-10.mjs',
  ].map(rel=>[rel,sha(rel)])),
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
  assert.equal(value.config.asOf,'2026-10-10');
  assert.equal(value.config.weightMode,'quality');
  assert.equal(value.config.includeChannel14,false);
  assert.equal(value.config.signalNoiseEnabled,false);
  assert.equal(value.config.pollCorrelationEnabled,false);
  assert.equal(value.result.checks.eachWorld120,true);
  assert.equal(value.result.checks.blocPartition120,true);
  assert.ok(Math.abs(value.result.parties.reduce((sum,p)=>sum+p.mean,0)-120)<1e-8);
  assert.deepEqual(value.input.current,current,'Served app must contain all corrected canonical poll metadata');
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
  assert.match(await section.locator('.vpt-date').innerText(),/10\.10\.2026/);
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
  const target=visible.filter(row=>row.href===cohortC13.sourceUrls[0]);
  assert.equal(target.length,1,'One displayed strict C13 row must link to its retained original evidence');
  assert.match(target[0].text,/06\.10\.2026/);
  assert.match(target[0].text,/07\.10\.2026/);
  assert.equal(target[0].decision,'נכלל');
  report.strict={asOf:strict.asOf,coverage:strict.coverage,significant,c13:target[0],cohortRows:visible.length};
  return section;
}
async function pollDataView(){
  const register=page.locator('[data-component-id="source-poll-register"]');
  const row=register.locator('.tp-register tbody tr').filter({hasText:c13.publisher});
  assert.equal(await row.count(),1);
  const cells=await row.locator('td').allTextContents();
  assert.equal(cells[0].trim(),'07.10.2026');
  assert.equal(cells[1].trim(),'06.10.2026–07.10.2026');
  assert.match(cells[2],/^1263/);
  assert.equal(await row.getByRole('link',{name:'מקור גודל המדגם',exact:true}).getAttribute('href'),c13.sampleSizeSourceUrl);
  const matrix=page.locator('[data-poll-matrix]');
  for(const [id,seats] of Object.entries(c13.seats)){
    const cell=matrix.locator('td[data-poll-id="'+c13.id+'"][data-party-id="'+id+'"]');
    if(await cell.count())assert.equal((await cell.locator('bdi').innerText()).trim(),String(seats));
  }
  report.c13Register={pollId:c13.id,text:await row.innerText(),source:c13.sourceUrl,sampleSource:c13.sampleSizeSourceUrl};
  return register;
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
  assert.ok(base.protocol==='file:'||response?.ok(),'The served page must be accessible');report.response={url:response?.url()??page.url(),status:response?.status()??null};
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
  report.checks.push('Current data/date and C13 metadata served exactly; quality weights, Channel 14 off, signal/noise off, similarity off; 120-seat partition');
  for(const [id] of tabs){await tab(id);await noChatGPT();await geometry('1440-'+id);}
  report.checks.push('All seven stable tab IDs render and preserve desktop geometry');
  await tab('poll-trends');const trends=await strictView();
  await trends.evaluate(node=>{node.scrollIntoView({block:'start'});window.scrollBy(0,-120);});
  await page.screenshot({path:path.join(out,'1440-trends.png'),fullPage:false});
  report.checks.push('Strict analysis is dated October 10 and defaults to independently recomputed without-14 coverage, exact p/q/verdicts and corrected C13 cohort dates');
  await tab('poll-data');const register=await pollDataView();
  await register.evaluate(node=>{node.scrollIntoView({block:'start'});window.scrollBy(0,-120);});
  await page.screenshot({path:path.join(out,'1440-poll-data.png'),fullPage:false});
  report.checks.push('Poll register shows C13 publication October 7, fieldwork October 6-7, n=1263, retained source links and published seat vector');

  await tab('probabilities');
  report.pair=await checkJoint(baseline.result,['winter','hendel']);
  await page.locator('input[data-joint-party="raam"]').check();
  report.triple=await checkJoint(baseline.result,['winter','hendel','raam']);
  assert.match(await page.locator('.jtp-answer h3').innerText(),/כל 3 המפלגות/);
  const csvFile=await downloaded(page.locator('[data-joint-threshold-panel]').getByRole('button',{name:'יצוא הסיכוי המשותף CSV',exact:true}),'triple-all-fail.csv');
  const csv=fs.readFileSync(csvFile,'utf8');
  assert.match(csv,/allFail/);assert.match(csv,/winter;hendel;raam/);assert.match(csv,/כל 3 המפלגות/);assert.ok(!csv.includes('atLeastTwo'));
  report.checks.push('Pair and triple ALL-selected-fail counts/probabilities/Wilson intervals/distributions match independent aggregation of the same exported simulation histogram; CSV retains the event');

  for(const width of [390,320]){
    await page.setViewportSize({width,height:844});
    for(const [id] of tabs){await tab(id);await geometry(width+'-'+id);await noChatGPT();
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
  assert.deepEqual(report.pageErrors,[]);report.status='passed';report.checkedAt=new Date().toISOString();
}catch(error){
  report.status='failed';report.failure={message:error.message,stack:error.stack};process.exitCode=1;
  if(page)await page.screenshot({path:path.join(out,'failure.png'),fullPage:true}).catch(()=>{});
}finally{
  fs.writeFileSync(path.join(out,'report.json'),JSON.stringify(report,null,2)+'\n');
  await browser.close();
  console.log(JSON.stringify({status:report.status,phase:options.phase,report:path.join(out,'report.json'),checks:report.checks.length,geometry:report.geometry.length,pair:report.pair?.probability,triple:report.triple?.probability,failure:report.failure?.message}));
}

