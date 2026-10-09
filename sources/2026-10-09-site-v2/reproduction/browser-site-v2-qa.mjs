import {createRequire} from 'node:module';
import fs from 'node:fs';
import path from 'node:path';
import assert from 'node:assert/strict';
const require=createRequire('C:/Users/User/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright/package.json');
const {chromium}=require('playwright');
const base=process.argv[2]||'http://127.0.0.1:8791/',tag=new URL(base).hostname==='127.0.0.1'?'local':'public';
const out=path.resolve('artifacts/site-v2-2026-10-09/qa',tag);fs.mkdirSync(out,{recursive:true});
const source=fs.readFileSync('dashboard/src/content/dashboard/DashboardContent.jsx','utf8'),block=source.match(/useDashboardTabs\(\[([\s\S]*?)\]\.map/);
const tabs=[...block[1].matchAll(/\{id:"([^"]+)",label:"([^"]+)"/g)].map(m=>({id:m[1],label:m[2]}));
const browser=await chromium.launch({headless:true,executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe'}),context=await browser.newContext({viewport:{width:1440,height:1080},acceptDownloads:true}),page=await context.newPage(),errors=[];
page.setDefaultTimeout(60000);page.on('pageerror',e=>errors.push(e.message));
const report={status:'running',base,checks:[],geometry:[],errors},exportName='ייצוא תרחיש ומקורות JSON';
async function ready(){await page.waitForTimeout(400);await page.waitForFunction(name=>{const b=[...document.querySelectorAll('button')].find(n=>n.textContent.trim()===name);return b&&!b.disabled;},exportName);assert.equal(await page.locator('.e-error').count(),0);assert.deepEqual(errors,[]);}
async function detail(selector,open){const d=page.locator(selector);if(await d.evaluate(n=>n.open)!==open)await d.locator(':scope > summary').click();}
async function downloaded(label,name){const pending=page.waitForEvent('download');await page.getByRole('button',{name:label,exact:true}).click();const file=path.join(out,name);await(await pending).saveAs(file);return file;}
async function exported(name){await ready();await detail('#run-settings',true);const file=await downloaded(exportName,name+'.json'),value=JSON.parse(fs.readFileSync(file,'utf8'));await detail('#run-settings',false);return value;}
async function load(config,name){await page.locator('input[type=file]').setInputFiles({name:name+'.json',mimeType:'application/json',buffer:Buffer.from(JSON.stringify({config}))});await ready();}
async function polls(){await detail('#scenario-workspace',true);const b=page.locator('[data-scenario-control="polls"]');if(await b.getAttribute('aria-expanded')!=='true')await b.click();}
async function tab(id){await page.getByRole('tab',{name:tabs.find(t=>t.id===id).label,exact:true}).click();await page.locator('.election-app[data-page="'+id+'"]').waitFor();await ready();}
const channel=()=>page.getByRole('switch',{name:'כלול סקרי ערוץ 14',exact:true}),similarity=()=>page.getByRole('switch',{name:'דמיון בין סקרים',exact:true});
const outcome=v=>({counts:v.result.counts,parties:v.result.parties.map(r=>({id:r.id,mean:r.mean,pass:r.passProbability}))});
function valid(v){assert.equal(v.config.signalNoiseEnabled,false);assert.equal(v.result.signalNoise,undefined);assert.equal(v.result.checks.eachWorld120,true);assert.equal(v.result.checks.blocPartition120,true);assert.ok(Math.abs(v.result.parties.reduce((s,r)=>s+r.mean,0)-120)<1e-8);for(const w of v.result.worlds)assert.equal(w.seats.reduce((s,n)=>s+n,0),120);}
async function geometry(label){const sizes=await page.evaluate(()=>({width:innerWidth,client:document.documentElement.clientWidth,scroll:document.documentElement.scrollWidth,height:document.documentElement.scrollHeight,firstNumberY:document.querySelector('[data-summary-probability]')?.getBoundingClientRect().y}));assert.ok(sizes.scroll<=sizes.client+2,label);report.geometry.push({label,...sizes});}
try{
 const url=new URL(base);url.searchParams.set('version','20261009-site-v2-qa');url.searchParams.set('view','1');url.searchParams.set('tab','dashboard');await page.goto(url.href,{waitUntil:'load'});await ready();
 assert.equal(await page.locator('#scenario-workspace').evaluate(n=>n.open),false);assert.equal(await page.getByRole('switch',{name:'אות ורעש — ניסיוני',exact:true}).count(),0);
 const baseline=await exported('default');valid(baseline);assert.equal(baseline.config.weightMode,'quality');assert.equal(baseline.config.includeChannel14,false);assert.equal(baseline.config.pollCorrelationEnabled,false);assert.equal(baseline.siteVersion,2);
 const frozen=JSON.parse(fs.readFileSync('artifacts/site-v2-2026-10-09/before/dashboard/src/data.json','utf8')),oldRows=frozen.queries.simulation_results.rows;
 assert.deepEqual(baseline.result.parties,oldRows);report.checks.push('Default10k-party-results-exactly-match-published-V1');
 await polls();await similarity().click();const similar=await exported('similarity');valid(similar);assert.notDeepEqual(outcome(similar),outcome(baseline));await channel().click();const both=await exported('similarity-and-channel14');valid(both);assert.equal(both.result.pollWeights.length,8);
 for(const item of tabs){await tab(item.id);await polls();assert.equal(await channel().getAttribute('aria-checked'),'true');assert.equal(await similarity().getAttribute('aria-checked'),'true');await geometry('shared-settings-'+item.id);}
 await tab('poll-trends');const verified=await page.locator('.vpt-table tbody').innerText();assert.match(await page.locator('.vpt-fixed[role=note]').innerText(),/ללא תיקון הדמיון/);assert.ok((await page.locator('.pt-delta-combined-table tbody tr td:nth-child(5)').allTextContents()).every(v=>v.trim()==='—'));await polls();await similarity().click();await ready();assert.deepEqual(await page.locator('.vpt-table tbody').innerText(),verified);assert.ok(await page.locator('.pt-delta-combined-table tbody tr td:nth-child(5) bdi').count()>0);
 report.checks.push('Current-switches-preserved-across6tabs-and-significance-clearly-separated');
 await tab('dashboard');await load(baseline.config,'reset-baseline');const restored=await exported('restored');valid(restored);assert.deepEqual(outcome(restored),outcome(baseline));
 for(const mode of ['equal','quality','reference','littlepolls','gilead','rosner','ensemble','robust']){await load({...baseline.config,iterations:300,weightMode:mode,signalNoiseEnabled:true},'canceled-import-'+mode);const v=await exported('policy-'+mode);valid(v);assert.equal(v.config.weightMode,mode);assert.match(await page.locator('.e-scenario-notice').innerText(),/בוטלה בגרסה 2/);}
 await load({...baseline.config,weightMode:'signal_noise'},'legacy-mode');const legacy=await exported('legacy-normalized');assert.equal(legacy.config.weightMode,'quality');assert.deepEqual(outcome(legacy),outcome(baseline));valid(legacy);
 const fileInput=page.locator('input[type=file]');await fileInput.setInputFiles({name:'invalid.json',mimeType:'application/json',buffer:Buffer.from(JSON.stringify({config:{...baseline.config,pollCorrelationEnabled:'false'}}))});await page.waitForFunction(()=>document.querySelector('.e-error')?.textContent.includes('תרחיש לא תקין'));await load(baseline.config,'after-invalid');
 report.checks.push('All8policies-work-retired-option-blocked-through-import-legacy-mode-normalized-invalid-flags-rejected');
 await detail('#scenario-workspace',false);await downloaded('הורדת תמונת סיכום PNG','summary.png');await detail('#run-settings',true);const csv=fs.readFileSync(await downloaded('ייצוא CSV','forecast.csv'),'utf8');assert.match(csv,/pollCorrelationEnabled/);await detail('#run-settings',false);
 await tab('probabilities');await downloaded('ייצוא התרשים PNG','threshold.png');const threshold=fs.readFileSync(await downloaded('יצוא טבלת סיכויים CSV','threshold.csv'),'utf8');assert.match(threshold,/דיוק היסטורי/);assert.doesNotMatch(threshold,/אות ורעש/);
 await tab('poll-data');await downloaded('הורדת נתוני הסקרים CSV','original-polls.csv');assert.equal(await page.locator('.tp-document-archive').evaluate(n=>n.open),false);
 for(const row of baseline.result.parties.filter(p=>p.ballot!==false)){
  if(row.hasModelledSupport===false){
   const cell=page.locator('td[data-method="quality"][data-party-id="'+row.id+'"]');
   assert.equal(await cell.getAttribute('data-model-supported'),'false');assert.match(await cell.innerText(),/אין אומדן תמיכה נפרד/);assert.equal(await cell.locator('[data-mean]').count(),0);continue;
  }
  const value=await page.locator('td[data-method="quality"][data-party-id="'+row.id+'"] [data-mean]').getAttribute('data-mean');
  assert.equal(Number(value),row.mean,'source-model-column must equal main simulation: '+row.id);
 }
 const sourceRows=JSON.parse(fs.readFileSync('dashboard/src/data.json','utf8')).queries.polls.rows;
 assert.deepEqual(sourceRows,frozen.queries.polls.rows);
 report.checks.push('Source-model-column-matches-selected-main-simulation-original-source-rows-unchanged');
 await tab('method-data');assert.equal(await page.locator('#method-guide-coverage').count(),0);assert.ok(await page.locator('[data-component-id="method-guide-coverage"]').count()>0);
 report.checks.push('PNG-CSV-JSON-exports-and-folded-archives-preserved');
 for(const width of [1440,390,320]){await page.setViewportSize({width,height:width===1440?1080:844});for(const item of tabs){await tab(item.id);await detail('#scenario-workspace',false);await geometry(width+'-'+item.id);await page.screenshot({path:path.join(out,width+'-'+item.id+'.png')});}}
 await tab('dashboard');await page.emulateMedia({colorScheme:'dark'});await geometry('dark-home');await page.screenshot({path:path.join(out,'dark-home.png')});await page.emulateMedia({colorScheme:'light'});
 const mobile=report.geometry.find(r=>r.label==='390-dashboard');assert.ok(mobile.firstNumberY<844,'Numeric home result should be visible on mobile first screen');
 report.checks.push('All6pages-no-overflow1440-390-320-light-and-dark');report.status='passed';
}catch(e){report.status='failed';report.failure={message:e.message,stack:e.stack};await page.screenshot({path:path.join(out,'failure.png'),fullPage:true}).catch(()=>{});throw e;}finally{fs.writeFileSync(path.join(out,'report.json'),JSON.stringify(report,null,2)+'\n');await browser.close();console.log(JSON.stringify({status:report.status,checks:report.checks,geometry:report.geometry,errors}));}
