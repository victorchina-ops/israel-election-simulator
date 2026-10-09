import {createRequire} from 'node:module';
import fs from 'node:fs';import path from 'node:path';import assert from 'node:assert/strict';
const require=createRequire('C:/Users/User/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright/package.json');
const {chromium}=require('playwright');
const base=process.argv[2]||'http://127.0.0.1:8791/';
const tag=new URL(base).hostname==='127.0.0.1'?'local':'public';const out=path.resolve('artifacts/site-v3-2026-10-09/qa',tag);fs.mkdirSync(out,{recursive:true});
const browser=await chromium.launch({headless:true,executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe'});
const context=await browser.newContext({viewport:{width:1440,height:1080},acceptDownloads:true});const page=await context.newPage();page.setDefaultTimeout(60000);
const errors=[];page.on('pageerror',error=>errors.push(error.message));
const report={status:'running',base,checks:[],geometry:[],errors};
const tabs=[['about','אודות והתחלה'],['dashboard','סימולציה ותוצאות'],['probabilities','מפלגות וחסימה'],['poll-trends','מגמות'],['seat-probabilities','תרחישי מנדטים'],['poll-data','הסקרים'],['method-data','שיטות והסברים']];
const exportName='ייצוא תרחיש ומקורות JSON';
async function ready(){await page.locator('#run-settings').waitFor();await page.waitForTimeout(400);await page.waitForFunction(name=>{const b=[...document.querySelectorAll('button')].find(n=>n.textContent.trim()===name);return b&&!b.disabled;},exportName);assert.equal(await page.locator('.e-error').count(),0);assert.deepEqual(errors,[]);}
async function tab(id){await page.getByRole('tab',{name:tabs.find(t=>t[0]===id)[1],exact:true}).click();await page.locator('.election-app[data-page="'+id+'"]').waitFor();if(id!=='about')await ready();}
async function detail(selector,open){const d=page.locator(selector);if(await d.evaluate(n=>n.open)!==open)await d.locator(':scope > summary').click();}
async function downloaded(label,name){const pending=page.waitForEvent('download');await page.getByRole('button',{name:label,exact:true}).click();const file=path.join(out,name);await(await pending).saveAs(file);return file;}
async function exported(name){await ready();await detail('#run-settings',true);const v=JSON.parse(fs.readFileSync(await downloaded(exportName,name+'.json'),'utf8'));await detail('#run-settings',false);assert.equal(v.siteVersion,3);assert.equal(v.config.signalNoiseEnabled,false);assert.equal(v.result.checks.eachWorld120,true);assert.equal(v.result.checks.blocPartition120,true);assert.ok(Math.abs(v.result.parties.reduce((s,p)=>s+p.mean,0)-120)<1e-8);return v;}
async function load(config){await page.locator('input[type=file]').setInputFiles({name:'scenario.json',mimeType:'application/json',buffer:Buffer.from(JSON.stringify({config}))});await ready();}
async function geometry(label){const g=await page.evaluate(()=>({viewport:innerWidth,client:document.documentElement.clientWidth,scroll:document.documentElement.scrollWidth,height:document.documentElement.scrollHeight}));assert.ok(g.scroll<=g.client+2,'overflow: '+label);report.geometry.push({label,...g});}
const channel=()=>page.getByRole('switch',{name:'כלול סקרי ערוץ 14',exact:true});const similarity=()=>page.getByRole('switch',{name:'דמיון בין סקרים',exact:true});
try{
 const fresh=new URL(base);fresh.searchParams.set('version','20261009-site-v3-qa');await page.goto(fresh.href,{waitUntil:'load'});await page.locator('.election-app[data-page="about"]').waitFor();
 assert.equal(await page.getByRole('button',{name:/Ask ChatGPT/}).count(),0);assert.equal(await page.getByRole('link',{name:/Ask ChatGPT/}).count(),0);
 const photos=page.locator('.election-app[data-page="about"] img');assert.ok(await photos.count()>0);assert.ok(await photos.first().evaluate(n=>n.complete&&n.naturalWidth>0));assert.match(await page.locator('.election-app[data-page="about"]').innerText(),/ויקטור רינה בן דוד/);
 await geometry('fresh-about');await page.screenshot({path:path.join(out,'1440-about.png'),fullPage:true});
 const appearance=page.locator('[data-appearance-toggle]');assert.equal(await appearance.count(),1);await appearance.click();await page.waitForTimeout(250);assert.equal(await appearance.getAttribute('data-color-scheme'),'dark');await page.reload({waitUntil:'load'});await page.locator('.election-app[data-page="about"]').waitFor();assert.equal(await appearance.getAttribute('data-color-scheme'),'dark');await page.screenshot({path:path.join(out,'1440-about-dark.png'),fullPage:true});await appearance.click();
 report.checks.push('Fresh-visits-open-About-with-original-loaded-photo-and-author-copy','AskChatGPT-absent-and-light-dark-toggle-persists-on-reload');
 await tab('dashboard');const baseline=await exported('default');assert.equal(baseline.config.weightMode,'quality');assert.equal(baseline.config.includeChannel14,false);assert.equal(baseline.config.pollCorrelationEnabled,false);
 const frozen=JSON.parse(fs.readFileSync('artifacts/site-v3-2026-10-09/before/dashboard/src/data.json','utf8'));assert.deepEqual(baseline.result.parties,frozen.queries.simulation_results.rows);
 assert.equal(await page.locator('#scenario-workspace').evaluate(n=>n.tagName),'SECTION');assert.equal(await page.locator('#scenario-workspace > summary').count(),0);assert.equal(await page.locator('#scenario-panel-polls').isVisible(),true);assert.equal(await page.locator('#scenario-panel-blocs').isVisible(),true);assert.equal(await page.locator('#scenario-panel-turnout').isVisible(),true);assert.equal(await channel().isVisible(),true);assert.equal(await similarity().isVisible(),true);
 report.checks.push('Default10k-results-exactly-match-published-V2','All-three-settings-panels-and-independent-switches-visible-without-opening');
 assert.ok(await page.locator('[data-quick-scenario-controls]').evaluate(n=>n.getBoundingClientRect().top<document.querySelector('[data-summary-probability]').getBoundingClientRect().top));
 await page.getByRole('combobox',{name:'שיטת שקלול מהירה',exact:true}).selectOption('equal');await ready();assert.equal((await exported('quick-equal')).config.weightMode,'equal');
 await page.getByRole('checkbox',{name:'סקרי ערוץ 14',exact:true}).check();await ready();assert.equal(await channel().getAttribute('aria-checked'),'true');await page.getByRole('checkbox',{name:'סקרי ערוץ 14',exact:true}).uncheck();
 await page.getByRole('checkbox',{name:'צמצום משקל לסקרים דומים',exact:true}).check();await ready();assert.equal(await similarity().getAttribute('aria-checked'),'true');await page.getByRole('checkbox',{name:'צמצום משקל לסקרים דומים',exact:true}).uncheck();
 const motive=page.getByRole('spinbutton',{name:/מוטיבציה לאופוזיציה — שינוי מהיר — הזנת ערך/});await motive.fill('105');await motive.press('Enter');await ready();const quick=await exported('quick-motivation');assert.equal(quick.config.blocMultipliers.b,1.05);assert.equal(quick.config.blocMultipliers.a,baseline.config.blocMultipliers.a);assert.deepEqual(quick.config.turnout,baseline.config.turnout);await load(baseline.config);
 report.checks.push('Quick-controls-precede-results-and-change-the-same-shared-configuration');
 for(const bloc of ['b','other','a']){const select=page.locator('select[data-party-assignment-select="likud"]');await select.selectOption(bloc);await ready();const v=await exported('party-'+bloc);assert.equal(v.config.partyBlocs.likud,bloc);assert.equal(await page.locator('.thm-assignment-card[data-party-assignment][data-party-id="likud"]').count(),1);assert.equal(await page.locator('[data-party-drop-zone="'+bloc+'"] .thm-assignment-card[data-party-id="likud"]').count(),1);}
 await page.locator('.thm-assignment-card[data-party-assignment][data-party-id="likud"]').dragTo(page.locator('[data-party-drop-zone="b"]'));await ready();assert.equal((await exported('party-drag')).config.partyBlocs.likud,'b');await load(baseline.config);
 report.checks.push('Native-party-select-and-desktop-drag-move-exclusive-membership-with-120-total');
 await similarity().click();await ready();await channel().click();await ready();const both=await exported('both-flags');assert.equal(both.config.includeChannel14,true);assert.equal(both.config.pollCorrelationEnabled,true);assert.equal(both.result.pollWeights.length,8);
 for(const [id] of tabs){await tab(id);if(id!=='about'){assert.equal(await channel().getAttribute('aria-checked'),'true');assert.equal(await similarity().getAttribute('aria-checked'),'true');}await geometry('shared-state-'+id);}
 report.checks.push('Independent-switches-persist-across-all-seven-tabs');
 await tab('dashboard');await load({...baseline.config,signalNoiseEnabled:true});const legacy=await exported('retired-import');assert.deepEqual(legacy.result.parties,baseline.result.parties);assert.match(await page.locator('.e-scenario-notice').innerText(),/בוטלה בגרסה 2/);await load(baseline.config);
 await downloaded('הורדת תמונת סיכום PNG','summary.png');await detail('#run-settings',true);assert.match(fs.readFileSync(await downloaded('ייצוא CSV','forecast.csv'),'utf8'),/pollCorrelationEnabled/);await detail('#run-settings',false);
 await tab('probabilities');await downloaded('ייצוא התרשים PNG','threshold.png');await downloaded('יצוא טבלת סיכויים CSV','threshold.csv');await tab('poll-data');await downloaded('הורדת נתוני הסקרים CSV','original-polls.csv');
 report.checks.push('Canceled-feature-stays-disabled-on-import-and-PNG-CSV-JSON-export-works');
 for(const width of [1440,390,320]){await page.setViewportSize({width,height:844});for(const [id] of tabs){await tab(id);await geometry(width+'-'+id);if(['about','dashboard'].includes(id))await page.screenshot({path:path.join(out,width+'-'+id+'.png'),fullPage:true});}}
 await page.setViewportSize({width:390,height:844});await tab('dashboard');await page.locator('[data-appearance-toggle]').click();await geometry('390-dashboard-dark');await page.screenshot({path:path.join(out,'390-dashboard-dark.png'),fullPage:true});
 report.checks.push('All-seven-pages-without-horizontal-overflow-at1440-390-320-and-mobile-dark');
 const deep=new URL(base);deep.searchParams.set('tab','poll-trends');deep.searchParams.set('view','1');await page.goto(deep.href,{waitUntil:'load'});await page.locator('.election-app[data-page="poll-trends"]').waitFor();await ready();report.checks.push('Explicit-tab-links-preserved');
 assert.deepEqual(errors,[]);report.status='passed';report.checkedAt=new Date().toISOString();fs.writeFileSync(path.join(out,'report.json'),JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify({status:'passed',tag,checks:report.checks.length,geometry:report.geometry.length}));
}catch(error){report.status='failed';report.failure=error.stack;fs.writeFileSync(path.join(out,'report.json'),JSON.stringify(report,null,2)+'\n');await page.screenshot({path:path.join(out,'failure.png'),fullPage:true}).catch(()=>{});throw error;}finally{await browser.close();}


