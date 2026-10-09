import {createRequire} from 'node:module';
import fs from 'node:fs';
import path from 'node:path';
import assert from 'node:assert/strict';
const require=createRequire('C:/Users/User/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright/package.json');
const {chromium}=require('playwright');
const base=process.argv[2]||'http://127.0.0.1:8791/';
const tag=new URL(base).hostname==='127.0.0.1'?'local':'public';
const out=path.resolve('artifacts/turnout-reset-2026-10-09/qa',tag);fs.mkdirSync(out,{recursive:true});
const browser=await chromium.launch({headless:true,executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe'});
const context=await browser.newContext({viewport:{width:1440,height:1080},acceptDownloads:true});
const page=await context.newPage();page.setDefaultTimeout(60000);
const errors=[];page.on('pageerror',error=>errors.push(error.message));
const report={status:'running',base,checks:[],geometry:[],errors};
const exportName='ייצוא תרחיש ומקורות JSON';
const topReset=()=>page.locator('[data-quick-scenario-controls]').getByRole('button',{name:'איפוס השתתפות ומוטיבציה',exact:true});
async function ready(){await page.locator('#run-settings').waitFor();await page.waitForTimeout(400);await page.waitForFunction(name=>{const b=[...document.querySelectorAll('button')].find(n=>n.textContent.trim()===name);return b&&!b.disabled;},exportName);assert.equal(await page.locator('.e-error').count(),0);}
async function exported(name){
 await ready();const detail=page.locator('#run-settings');if(!await detail.evaluate(n=>n.open))await detail.locator(':scope > summary').click();
 const pending=page.waitForEvent('download');await page.getByRole('button',{name:exportName,exact:true}).click();const file=path.join(out,name+'.json');await(await pending).saveAs(file);
 await detail.locator(':scope > summary').click();const v=JSON.parse(fs.readFileSync(file,'utf8'));
 assert.equal(v.result.checks.eachWorld120,true);assert.equal(v.result.checks.blocPartition120,true);return v;
}
async function load(config){await page.locator('input[type=file]').setInputFiles({name:'scenario.json',mimeType:'application/json',buffer:Buffer.from(JSON.stringify({config}))});await ready();}
function checkReset(before,after,baseline){
 assert.deepEqual(after.turnout,baseline.turnout);assert.deepEqual(after.blocMultipliers,baseline.blocMultipliers);assert.equal(after.externalMultiplier,1);
 const rest=({turnout,blocMultipliers,externalMultiplier,...v})=>v;assert.deepEqual(rest(after),rest(before));
}
try{
 const url=new URL(base);url.searchParams.set('version','20261009-turnout-reset-qa');url.searchParams.set('tab','dashboard');url.searchParams.set('view','1');await page.goto(url.href,{waitUntil:'load'});await ready();
 const baseline=await exported('default');const frozen=JSON.parse(fs.readFileSync('artifacts/turnout-reset-2026-10-09/before.json','utf8'));
 assert.deepEqual(baseline.result.parties,frozen.queries.simulation_results.rows);report.checks.push('Default forecast exactly matches prior published results');
 const custom=structuredClone(baseline.config);custom.turnout=Object.fromEntries(Object.entries(custom.turnout).map(([key,v])=>[key,Math.min(98,v+2)]));custom.blocMultipliers={a:.95,b:1.05,other:1.03};custom.externalMultiplier=1.1;custom.weightMode='equal';custom.includeChannel14=true;custom.iterations=100;custom.seed+=1;custom.partyBlocs.likud='b';
 await load(custom);const changed=await exported('custom');assert.notDeepEqual(changed.config.turnout,baseline.config.turnout);assert.notDeepEqual(changed.config.blocMultipliers,baseline.config.blocMultipliers);assert.equal(changed.config.externalMultiplier,1.1);
 await topReset().click();const reset=await exported('top-reset');checkReset(changed.config,reset.config,baseline.config);
 report.checks.push('Top reset restores all participation groups, bloc motivation and external multiplier; preserves every other scenario setting');
 await load(custom);await page.getByRole('button',{name:'חזרה להשתתפות 2022',exact:true}).click();const lower=await exported('lower-reset');checkReset(changed.config,lower.config,baseline.config);assert.deepEqual(lower.config,reset.config);report.checks.push('Existing lower reset remains available and produces the same configuration');
 await load(baseline.config);
 for(const width of [1440,390,320]){
  await page.setViewportSize({width,height:900});await topReset().scrollIntoViewIfNeeded();assert.equal(await topReset().isVisible(),true);
  const rect=await topReset().boundingBox();assert.ok(rect.height>=44);assert.ok(rect.x>=0&&rect.x+rect.width<=width);
  const g=await page.evaluate(()=>({viewport:innerWidth,client:document.documentElement.clientWidth,scroll:document.documentElement.scrollWidth}));assert.ok(g.scroll<=g.client+2);report.geometry.push({width,...g,button:rect});
  if(width!==320)await page.locator('[data-quick-scenario-controls]').screenshot({path:path.join(out,width+'-quick-controls.png')});
 }
 await page.setViewportSize({width:390,height:900});await page.locator('[data-appearance-toggle]').click();assert.equal(await topReset().isVisible(),true);await page.locator('[data-quick-scenario-controls]').screenshot({path:path.join(out,'390-quick-controls-alternate-theme.png')});
 await topReset().focus();assert.equal(await topReset().evaluate(n=>n===document.activeElement),true);await topReset().press('Enter');await ready();report.checks.push('Reset remains visible and keyboard operable at desktop/mobile sizes and both themes, with no horizontal overflow');
 await page.getByRole('tab',{name:'מפלגות וחסימה',exact:true}).click();await ready();assert.equal(await topReset().isVisible(),true);report.checks.push('Shared quick reset is available on another forecast tab');
 assert.deepEqual(errors,[]);report.status='passed';report.checkedAt=new Date().toISOString();fs.writeFileSync(path.join(out,'report.json'),JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify({status:'passed',tag,checks:report.checks.length,geometry:report.geometry.length}));
}catch(error){report.status='failed';report.failure=error.stack;fs.writeFileSync(path.join(out,'report.json'),JSON.stringify(report,null,2)+'\n');await page.screenshot({path:path.join(out,'failure.png'),fullPage:true}).catch(()=>{});throw error;}finally{await browser.close();}
