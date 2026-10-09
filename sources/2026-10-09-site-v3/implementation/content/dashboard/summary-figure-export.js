import {quantileHistogram} from './model/random.js';
import {getReportingGroups} from './reporting-groups.js';

const WIDTH = 1360;
const SCALE = 2;
const PAD = 48;
const INK = '#14273e';
const MUTED = '#526477';
const COLORS = {a:'#dc454c', b:'#2378cf', neither:'#89939f', other:'#87909d', arab:'#87909d'};
const BLOC_LABELS = {a:'קואליציה נוכחית', b:'אופוזיציה', arab:'רשימות ערביות בגוש נפרד', other:'ללא שיוך לגושים'};
const METHOD_LABELS = {robust:'שילוב שמרני',ensemble:'שילוב שיטות',equal:'משקל שווה',reference:'מדד 120',littlepolls:'מואיז הקטן',gilead:'מיכאל גלעד — תרחיש 50%',rosner:'רוזנר — קירוב',quality:'דיוק היסטורי',correlation:'תלות בין סוקרים'};
const OUTCOMES = [{id:'a',label:'קואליציה נוכחית'}, {id:'neither',label:'תיקו / ללא רוב'}, {id:'b',label:'אופוזיציה'}];
const num = (value, digits=2) => Number(value).toLocaleString('he-IL', {minimumFractionDigits:digits, maximumFractionDigits:digits});
const pct = value => num(100*value)+'%';
const date = value => String(value??'—').replace(/^(\d{4})-(\d{2})-(\d{2})(?:T.*)?$/, '$3.$2.$1');
const present = value => value!==undefined && value!==null;
const fail = message => { throw new Error(message); };

// Same largest-remainder order and physical geometry as OutcomeWaffle.
export function summaryWaffleCounts(probabilities) {
  if (!Array.isArray(probabilities) || probabilities.length!==3 || probabilities.some(p=>!Number.isFinite(p)||p<0)) fail('הסתברויות הקוביות אינן תקינות.');
  const total=probabilities.reduce((a,b)=>a+b,0);
  if (!(total>0)) fail('הסתברויות הקוביות ריקות.');
  const quotas=probabilities.map(p=>100*p/total), counts=quotas.map(Math.floor);
  const order=quotas.map((q,i)=>({i,remainder:q-counts[i]})).sort((a,b)=>b.remainder-a.remainder||a.i-b.i);
  for(let i=0,left=100-counts.reduce((a,b)=>a+b,0);i<left;i++) counts[order[i].i]++;
  return counts;
}

function validMean(stats) {
  const {mean,meanMargin,meanCI}=stats??{};
  return Number.isFinite(mean)&&mean>=0&&mean<=120&&Number.isFinite(meanMargin)&&meanMargin>=0
    &&Array.isArray(meanCI)&&meanCI.length===2&&meanCI.every(Number.isFinite)
    &&Math.abs(meanCI[0]-(mean-meanMargin))<1e-7&&Math.abs(meanCI[1]-(mean+meanMargin))<1e-7;
}

// Read quantiles from all completed runs; never infer them from rounded means.
export function summarySeatDistribution(stats,histogram,iterations) {
  const hist=histogram??stats?.hist;
  if(!Array.isArray(hist)||hist.length!==121||hist.some(count=>!Number.isSafeInteger(count)||count<0)
    ||hist.reduce((sum,count)=>sum+count,0)!==iterations) fail('חסרה התפלגות מנדטים מלאה ותקינה ליצוא החציון והטווח.');
  const distribution={median:quantileHistogram(hist,.5),low:quantileHistogram(hist,.05),high:quantileHistogram(hist,.95)};
  for(const key of ['median','low','high']) {
    if(present(stats?.[key])&&stats[key]!==distribution[key]) fail('החציון או טווח המנדטים אינם תואמים להיסטוגרמת ההרצות.');
  }
  return distribution;
}
const ltr=value=>'\u2066'+value+'\u2069';
const distributionLabel=stats=>`חציון: ${num(stats.median,0)} · אחוזונים ${ltr('5–95')}: ${ltr(num(stats.low,0)+'–'+num(stats.high,0))}`;
const shortDistributionLabel=stats=>`חציון ${num(stats.median,0)} · ${ltr('5–95')}: ${ltr(num(stats.low,0)+'–'+num(stats.high,0))}`;
/** Reject incomplete/inconsistent results instead of exporting a misleading figure. */
export function validateSummaryFigureData(result, input) {
  if (!result || !Number.isSafeInteger(result.iterations) || result.iterations<2) fail('יצוא הסיכום דורש לפחות שתי הרצות שהושלמו.');
  if (!result.config || result.config.iterations!==result.iterations) fail('תוצאת הסימולציה אינה תואמת למספר ההרצות שהוגדר.');
  const outcomes=OUTCOMES.map(outcome=>({...outcome, probability:result.probabilities?.[outcome.id], ci:result.probabilityCI?.[outcome.id], count:result.counts?.[outcome.id]}));
  if(outcomes.some(row=>!Number.isSafeInteger(row.count)||row.count<0||!Number.isFinite(row.probability)||row.probability<0||row.probability>1
    ||Math.abs(row.probability-row.count/result.iterations)>1e-9
    ||!Array.isArray(row.ci)||row.ci.length!==2||row.ci.some(v=>!Number.isFinite(v)||v<0||v>1)
    ||row.ci[0]>row.probability+1e-12||row.ci[1]<row.probability-1e-12)
    ||outcomes.reduce((sum,row)=>sum+row.count,0)!==result.iterations) fail('ההסתברויות, הספירות או רווחי הסמך אינם תקינים.');
  if(!Array.isArray(result.parties)||!result.parties.length||result.parties.some(p=>!p?.id||!validMean(p))) fail('חסרות תוחלות מפלגות או רווחי סמך תקינים.');
  const byId=new Map(result.parties.map(p=>[p.id,p]));
  if(byId.size!==result.parties.length||Math.abs(result.parties.reduce((sum,p)=>sum+p.mean,0)-120)>1e-7) fail('סכום תוחלות המנדטים או מזהי המפלגות אינם תקינים.');
  const ballotDefinitions=(input?.parties??result.parties).filter(p=>p.ballot!==false);
  if(!ballotDefinitions.length||new Set(ballotDefinitions.map(p=>p.id)).size!==ballotDefinitions.length||ballotDefinitions.some(p=>!byId.has(p.id))) fail('חסרות תוצאות לרשימות המשתתפות בבחירות.');
  const parties=ballotDefinitions.map(definition=>({...definition,...byId.get(definition.id)}));
  const reportingGroups=getReportingGroups(result,input);
  for(const group of reportingGroups) {
    if(group.status==='unavailable') {
      if(group.id==='a'||group.id==='b') fail('חסרה התפלגות גוש תקינה ליצוא התמונה.');
      continue;
    }
    const expected=group.partyIds.reduce((sum,id)=>sum+(byId.get(id)?.mean??NaN),0);
    if(!validMean(group.stats)||Math.abs(group.stats.mean-expected)>1e-7) fail('תוחלת קבוצת הדיווח או רווח הסמך אינם תואמים לתוצאות המפלגות.');
  }
  if(result.parties.some(p=>!Object.hasOwn(BLOC_LABELS,p.bloc??p.defaultBloc))) fail('שיוך גוש אינו מוכר בתוצאת הסימולציה.');
  if(!Array.isArray(result.pollWeights)||!result.pollWeights.length||result.pollWeights.some(p=>!Number.isFinite(p.weight)||p.weight<0)
    ||Math.abs(result.pollWeights.reduce((sum,p)=>sum+p.weight,0)-1)>1e-8) fail('משקלי הסקרים האפקטיביים אינם תקינים.');
  const counts=summaryWaffleCounts(outcomes.map(row=>row.probability));
  outcomes.forEach((row,i)=>{row.squares=counts[i];});
  const seatDistributions={parties:Object.fromEntries(parties.map(p=>[p.id,summarySeatDistribution(p,p.hist,result.iterations)])),
    blocs:Object.fromEntries(reportingGroups.map(group=>[group.id,group.status==='unavailable'?null:summarySeatDistribution(group.stats,group.hist,result.iterations)]))};
  return {outcomes,parties,counts,seatDistributions,reportingGroups};
}

function meanLabel(stats) {
  const margin=stats.meanMargin;
  const digits=margin>0&&margin<.005?Math.min(6,Math.max(3,Math.ceil(-Math.log10(margin))+1)):2;
  return `${num(stats.mean)} ± ${num(margin,digits)}`;
}

async function loadLogo(source) {
  if(typeof source!=='string'||!source) return null;
  try {
    const url=new URL(source,window.location.href);
    if(!['data:','blob:'].includes(url.protocol)&&url.origin!==window.location.origin) return null;
    return await new Promise(resolve=>{
      const image=new Image(); let settled=false;
      const finish=value=>{if(settled)return;settled=true;clearTimeout(timer);image.onload=null;image.onerror=null;resolve(value);};
      const timer=setTimeout(()=>{finish(null);image.src='';},3500);
      image.onload=()=>finish(image.naturalWidth&&image.naturalHeight?image:null);
      image.onerror=()=>finish(null); image.src=url.href;
    });
  } catch { return null; }
}

function makePainter(ctx) {
  const operations=[], textRecords=[];
  function font({size=20,weight=400}={}) {ctx.font=`${weight} ${size}px Arial, sans-serif`;}
  function measure(value,style={}) {font(style);return ctx.measureText(String(value)).width;}
  function wrap(value,width,style={}) {
    const lines=[];
    for(const paragraph of String(value??'').split(/\r?\n/)) {
      let line='';
      for(const word of paragraph.split(/\s+/).filter(Boolean)) {
        const candidate=line?line+' '+word:word;
        if(measure(candidate,style)<=width) {line=candidate;continue;}
        if(line) {lines.push(line);line='';}
        if(measure(word,style)<=width) {line=word;continue;}
        for(const character of Array.from(word)) {
          if(line&&measure(line+character,style)>width) {lines.push(line);line='';}
          line+=character;
        }
      }
      lines.push(line);
    }
    return lines;
  }
  function text(value,x,y,style={}) {
    const {size=20,weight=400,color=INK,align='right',direction='rtl'}=style;
    textRecords.push({text:String(value),x,y,size,align});
    operations.push(()=>{font({size,weight});ctx.fillStyle=color;ctx.textAlign=align;ctx.direction=direction;ctx.textBaseline='top';ctx.fillText(String(value),x,y);});
  }
  function block(value,x,y,width,style={}) {
    const lineHeight=style.lineHeight??Math.ceil((style.size??20)*1.45), lines=wrap(value,width,style);
    lines.forEach((line,i)=>text(line,x,y+i*lineHeight,style));
    return lines.length*lineHeight;
  }
  function box(x,y,width,height,fill='#f5f8fb',radius=12) {
    operations.push(()=>{ctx.beginPath();ctx.roundRect(x,y,width,height,radius);ctx.fillStyle=fill;ctx.fill();});
  }
  function logo(image,x,y,width,height,id) {
    box(x,y,width,height,id==='israel_first'?'#172436':'#fff',7);
    if(image) operations.push(()=>{const ratio=Math.min((width-10)/image.naturalWidth,(height-8)/image.naturalHeight),w=image.naturalWidth*ratio,h=image.naturalHeight*ratio;ctx.drawImage(image,x+(width-w)/2,y+(height-h)/2,w,h);});
  }
  return {operations,textRecords,measure,wrap,text,block,box,logo};
}

function scenarioLines(result,input,weightingLabel,oppositionLabel) {
  const c=result.config, partyNames=Object.fromEntries(result.parties.map(p=>[p.id,p.name||p.id]));
  const pollNames=new Map((input?.current?.polls??[]).map(p=>[p.id,p]));
  const groupNames=new Map((input?.turnout?.groups??[]).map(g=>[g.id,g.label||g.id]));
  const lines=[];
  const add=(label,value)=>{if(present(value)&&String(value).length)lines.push(label+': '+value);};
  const names=ids=>(ids??[]).map(id=>partyNames[id]||id).join(' + ');
  add('שקלול הסקרים',weightingLabel||METHOD_LABELS[c.weightMode]||c.weightMode||'לא נשמר');
  if(result.signalNoise)add('אות ורעש','מופעל — תוספת ניסיונית'); // Archived experiment exports only; V2 site cannot activate it.
  add('סקרי ערוץ 14',c.includeChannel14===false?'מחוץ לשקלול':'כלולים לפי הבחירה');
  add('דמיון בין סקרים',c.pollCorrelationEnabled?'מופעל — ניסיוני, סדרות הסקרים הנוכחיות':'כבוי');
  if(result.signalNoise){
    const coverage=result.signalNoise.coverage??{};
    add('כיסוי אחוזי המקור',`${coverage.observationCount??coverage.pollCount??'—'} סקרים · ${coverage.instituteCount??'—'} מכונים`);
    add('חלון עבודת השדה של אחוזי המקור',`${date(coverage.from)}–${date(coverage.to)}`);
  }
  add(result.signalNoise?'השפעת המכונים על האומדן (משתנה בין מפלגות)':'משקלי הסקרים האפקטיביים',result.pollWeights.map(p=>{
    const source=pollNames.get(p.id),name=p.pollster||source?.pollster||p.pollsterId||p.id;
    const publisher=p.publisher||source?.publisher;
    return `${name}${publisher?' / '+publisher:''}: ${pct(p.weight)}`;
  }).join(' · '));
  add('הרכב הגושים',oppositionLabel||c.oppositionMode||'לפי שיוך הרשימות בתמונה');
  const turnoutKeys=[...new Set([...(input?.turnout?.groups??[]).filter(g=>g.eligible>0).map(g=>g.id),...Object.keys(c.turnout??{})])];
  add('שיעורי הצבעה',turnoutKeys.map(id=>`${groupNames.get(id)||id}: ${present(c.turnout?.[id])?num(c.turnout[id],2)+'%':'לא נשמר'}`).join(' · '));
  add('מכפילי מוטיבציה של גושים',Object.entries(c.blocMultipliers??{}).map(([id,value])=>`${BLOC_LABELS[id]||id}: ${pct(value)}`).join(' · '));
  add('מכפיל מעטפות חיצוניות',present(c.externalMultiplier)?pct(c.externalMultiplier):'לא נשמר');
  add('המשמעות של המכפילים','100% משמר את ההשתתפות הבסיסית; זהו שינוי יחסי, ולא תוספת נקודות אחוז.');
  add('מצב הסימולציה',c.samplingMode==='poll'?'כולל אפשרות לטעות בסקרים':c.samplingMode==='fixed'?'בהנחה שהתמיכה בסקרים נכונה':c.samplingMode);
  const errorFields=[['uncertaintyScale','עוצמת אי־ודאות'],['scatterStrength','פיזור בין סוקרים'],['commonBlocSD','סטיית תקן משותפת לגושים (נק׳ אחוז)'],['designEffect','אפקט תכנון'],['forecastDays','אופק תחזית (ימים)'],['dailyDrift','סחיפה יומית (נק׳ אחוז)'],['unreportedSmallPct','תמיכה קטנה שלא דווחה (%)']];
  add('הנחות טעות הסקרים',errorFields.filter(([key])=>present(c[key])&&(!result.signalNoise||!['scatterStrength','dailyDrift','unreportedSmallPct'].includes(key))).map(([key,label])=>`${label}: ${num(c[key],2)}`).join(' · '));
  add('אי־ודאות בעיגול מנדטי הסקרים',!result.signalNoise&&present(c.rounding)?c.rounding?'מופעלת':'כבויה':undefined);
  const agreementDefinitions=new Map((input?.current?.agreements??[]).map(a=>[a.id,a]));
  const agreements=(c.agreements??[]).map(id=>{const definition=agreementDefinitions.get(id);return definition?.parties?names(definition.parties):id;});
  agreements.push(...(c.customAgreements??[]).map(pair=>names(pair)));
  add('הסכמי עודפים שנבחרו',agreements.length?agreements.join(' · '):'ללא הסכמים');
  add('בעלי זכות בחירה',present(c.registered)?num(c.registered,0):undefined);
  const blend=['ensemble','robust'].includes(c.weightMode);
  const mixture=c.methodWeights??c.ensembleMix??result.methodWeights??{};
  const activeMethods=blend?Object.entries(mixture).filter(([,value])=>value>0):[[c.weightMode,1]];
  // At 100% uniform shrinkage, the method vectors cannot affect the result.
  const uses=id=>!(c.weightMode==='robust'&&c.robustShrinkage===1)&&activeMethods.some(([method])=>method===id);
  const usesTime=['equal','quality','correlation'].some(uses);
  const methodLabel=id=>METHOD_LABELS[id]||input?.weightPresets?.methods?.[id]?.labelHe||input?.weightPresets?.methods?.[id]?.label||id;
  if(blend&&activeMethods.length&&!(c.weightMode==='robust'&&c.robustShrinkage===1)) {
    const sum=activeMethods.reduce((total,[,value])=>total+value,0);
    add('תמהיל השיטות (משקלים מנורמלים)',activeMethods.map(([id,value])=>`${methodLabel(id)}: ${pct(value/sum)}`).join(' · '));
  }
  const weightSettings=[];
  const setting=(label,value)=>{if(present(value))weightSettings.push(`${label}: ${typeof value==='number'?num(value,2):value}`);};
  if(c.weightMode==='robust'&&present(c.robustShrinkage)) setting('חלק הבסיס השווה',pct(c.robustShrinkage));
  if(uses('gilead')&&present(c.gileadTarget)) {
    const target=(input?.current?.polls??[]).find(p=>p.pollsterId===c.gileadTarget);
    setting('מכון היעד בתרחיש גלעד',target?.pollster||({direct_polls:'דיירקט פולס',next_data:'נקסט דאטה'}[c.gileadTarget])||c.gileadTarget);
  }
  if(usesTime&&c.applyRecency!==false) setting('מחצית חיים בימים',c.halfLifeDays);
  if(uses('rosner')) {
    setting('מחצית חיים בקירוב רוזנר',c.rosnerHalfLifeDays??c.halfLifeDays);
    setting('סף חריגות בקירוב רוזנר',c.rosnerOutlierCutoffPP);
  }
  if(uses('correlation')) setting('מכפיל אשכול ותיקים',c.veteranClusterDiscount);
  add('הגדרות השקלול הפעילות',weightSettings.join(' · '));
  if(usesTime) add('דעיכת זמן נוספת',c.applyRecency!==false?'מופעלת':'כבויה');
  if(c.excludedPolls?.length) add('סקרים שהוצאו',(c.excludedPolls).map(id=>{const p=pollNames.get(id);return p?[p.pollster,p.publisher].filter(Boolean).join(' / ')||id:id;}).join(' · '));
  if(Object.keys(c.partyMultipliers??{}).length) add('מכפילי תמיכה במפלגות',Object.entries(c.partyMultipliers).map(([id,value])=>`${partyNames[id]||id}: ${pct(value)}`).join(' · '));
  if(Object.keys(c.turnoutMappings??{}).length) add('מיפוי השתתפות שהוגדר',Object.entries(c.turnoutMappings).map(([id,value])=>`${partyNames[id]||id}: ${typeof value==='object'?JSON.stringify(value):value}`).join(' · '));
  return lines;
}

/** Build a deterministic 2× PNG from a completed result snapshot, without downloading. */
export async function buildSummaryFigure({result,input,summaryText='',logoSources={},weightingLabel='',oppositionLabel=''}) {
  const checked=validateSummaryFigureData(result,input);
  // Capture serializable evidence before any asynchronous image/font work.
  const snapshot=JSON.parse(JSON.stringify(result)), config=snapshot.config;
  const parties=JSON.parse(JSON.stringify(checked.parties)), outcomes=JSON.parse(JSON.stringify(checked.outcomes));
  const seatDistributions=JSON.parse(JSON.stringify(checked.seatDistributions));
  const reportingGroups=JSON.parse(JSON.stringify(checked.reportingGroups));
  const settings=scenarioLines(snapshot,input,weightingLabel,oppositionLabel);
  const suppliedText=String(summaryText??'');
  await document.fonts?.ready;
  const loaded=await Promise.all(parties.map(p=>loadLogo(logoSources[p.id])));
  const logos=new Map(parties.map((p,i)=>[p.id,loaded[i]]));
  const canvas=document.createElement('canvas'),ctx=canvas.getContext('2d');
  if(!ctx) fail('הדפדפן אינו מאפשר יצוא תמונה.');
  const draw=makePainter(ctx), right=WIDTH-PAD, contentWidth=WIDTH-2*PAD;
  draw.box(0,0,WIDTH,12,INK,0);
  let y=42;
  y+=draw.block('סיכום תרחיש הבחירות',right,y,contentWidth,{size:36,weight:700,lineHeight:48});
  y+=draw.block(`נתוני הסקרים: ${date(config.asOf)}  ·  ${num(snapshot.iterations,0)} הרצות  ·  זרע: ${config.seed??'—'}`,right,y+4,contentWidth,{size:21,weight:700,lineHeight:31})+18;
  if(suppliedText.trim()) {
    const lines=draw.wrap(suppliedText,contentWidth-40,{size:22,weight:600}),height=lines.length*33+32;
    draw.box(PAD,y,contentWidth,height,'#edf3f9');
    draw.block(suppliedText,right-20,y+16,contentWidth-40,{size:22,weight:600,lineHeight:33}); y+=height+24;
  }
  const heroY=y,sideWidth=388;
  const sideHeight=row=>206+draw.wrap(row.label,sideWidth-48,{size:27,weight:700}).length*38
    +draw.wrap('סיכוי לרוב של 61 מנדטים ומעלה',sideWidth-48,{size:19}).length*28
    +draw.wrap(`רווח סמך 95%: ${pct(row.ci[0])} עד ${pct(row.ci[1])}`,sideWidth-48,{size:18}).length*27
    +draw.wrap('ממוצע ± רווח סמך 95% מההרצות',sideWidth-48,{size:19}).length*29
    +draw.wrap(distributionLabel(seatDistributions.blocs[row.id]),sideWidth-48,{size:18}).length*27+6
    +draw.wrap(`${num(row.count,0)} מתוך ${num(snapshot.iterations,0)} הרצות`,sideWidth-48,{size:18}).length*27;
  const heroHeight=Math.max(420,...outcomes.filter(row=>row.id!=='neither').map(sideHeight));
  const side=(id,x)=>{
    const row=outcomes.find(o=>o.id===id),color=COLORS[id],r=x+sideWidth-24;
    draw.box(x,heroY,sideWidth,heroHeight,'#f5f8fb');draw.box(x,heroY,sideWidth,7,color,0);
    let cy=heroY+20;
    cy+=draw.block(row.label,r,cy,sideWidth-48,{size:27,weight:700,color,lineHeight:38})+10;
    draw.text(pct(row.probability),x+sideWidth/2,cy,{size:55,weight:700,color,align:'center',direction:'ltr'});cy+=64;
    cy+=draw.block('סיכוי לרוב של 61 מנדטים ומעלה',r,cy,sideWidth-48,{size:19,lineHeight:28});
    cy+=draw.block(`רווח סמך 95%: ${pct(row.ci[0])} עד ${pct(row.ci[1])}`,r,cy+10,sideWidth-48,{size:18,color:MUTED,lineHeight:27})+30;
    draw.text(meanLabel(reportingGroups.find(group=>group.id===id).stats),x+sideWidth/2,cy,{size:31,weight:700,color,align:'center',direction:'ltr'});cy+=46;
    cy+=draw.block('ממוצע ± רווח סמך 95% מההרצות',r,cy,sideWidth-48,{size:19,lineHeight:29})+6;
    cy+=draw.block(distributionLabel(seatDistributions.blocs[id]),r,cy,sideWidth-48,{size:18,weight:600,color,lineHeight:27})+16;
    draw.block(`${num(row.count,0)} מתוך ${num(snapshot.iterations,0)} הרצות`,r,cy,sideWidth-48,{size:18,color:MUTED,lineHeight:27});
  };
  side('a',WIDTH-PAD-sideWidth);side('b',PAD);
  const neutral=outcomes.find(row=>row.id==='neither'),center=WIDTH/2;
  draw.text(neutral.label,center,heroY+4,{size:23,weight:700,align:'center'});
  draw.text(pct(neutral.probability),center,heroY+37,{size:34,weight:700,color:COLORS.neither,align:'center',direction:'ltr'});
  draw.text(`95%: ${pct(neutral.ci[0])} – ${pct(neutral.ci[1])}`,center,heroY+79,{size:17,color:MUTED,align:'center',direction:'ltr'});
  const gridSize=250,gap=4,cell=(gridSize-9*gap)/10,gridX=center-gridSize/2,gridY=heroY+108,cells=[];
  outcomes.forEach(row=>{for(let i=0;i<row.squares;i++)cells.push(row.id);});
  cells.forEach((id,i)=>{const column=9-Math.floor(i/10),row=i%10;draw.box(gridX+column*(cell+gap),gridY+row*(cell+gap),cell,cell,COLORS[id],3);});
  draw.text('100 קוביות · כל קובייה ≈ 1%',center,heroY+371,{size:18,color:MUTED,align:'center'});
  draw.text('ללא רוב: שני הגושים מתחת ל־61',center,heroY+397,{size:17,color:MUTED,align:'center'});
  y+=heroHeight+30;
  y+=draw.block('מנדטים לכל רשימה: ממוצע, חציון וטווח',right,y,contentWidth,{size:27,weight:700,lineHeight:38});
  y+=draw.block('ממוצע ± רווח סמך 95% לשגיאת האמידה; טווח \u20665–95\u2069 מתאר את פיזור תוצאות הסימולציה.',right,y,contentWidth,{size:18,color:MUTED,lineHeight:27})+18;
  const grouped=Object.fromEntries(['a','b','other'].map(id=>[id,parties.filter(p=>{const bloc=p.bloc??p.defaultBloc;return (bloc==='a'||bloc==='b'?bloc:'other')===id;})]));
  const partyColumn=(group,x,top,width)=>{
    const color=COLORS[group],r=x+width-18;let py=top;
    py+=draw.block(BLOC_LABELS[group],r,py,width-36,{size:23,weight:700,color,lineHeight:34})+10;
    for(const party of grouped[group]) {
      const nameWidth=width-350,nameLines=draw.wrap(party.name||party.id,nameWidth,{size:20,weight:700});
      const missing=party.hasModelledSupport===false;
      const distribution=shortDistributionLabel(seatDistributions.parties[party.id]);
      const distributionHeight=draw.wrap(distribution,204,{size:17}).length*24;
      const rowHeight=Math.max(76,nameLines.length*28+22,missing?90:44+distributionHeight+10);
      draw.box(x,py,width,rowHeight-6,'#f5f8fb');
      draw.logo(logos.get(party.id),x+width-100,py+12,82,46,party.id);
      draw.block(party.name||party.id,x+width-114,py+15,nameWidth,{size:20,weight:700,color,lineHeight:28});
      if(missing) draw.block('ללא אומדן תמיכה נפרד',x+174,py+16,156,{size:17,color:MUTED,lineHeight:25});
      else {
        draw.text(meanLabel(party),x+112,py+12,{size:21,weight:700,color,align:'center',direction:'ltr'});
        draw.block(distribution,x+112,py+42,204,{size:17,color,align:'center',lineHeight:24});
      }
      py+=rowHeight;
    }
    return py;
  };
  const columnGap=28,columnWidth=(contentWidth-columnGap)/2;
  y=Math.max(partyColumn('a',PAD+columnWidth+columnGap,y,columnWidth),partyColumn('b',PAD,y,columnWidth))+22;
  y+=draw.block('רשימות ללא שיוך לשני הגושים',right,y,contentWidth,{size:24,weight:700,color:MUTED,lineHeight:35});
  y+=3;
  for(const group of reportingGroups.filter(group=>group.id!=='a'&&group.id!=='b')) {
    const label=group.status==='unavailable'
      ? `${group.label}: התפלגות משותפת אינה זמינה בקובץ זה; יש להריץ מחדש.`
      : `${group.label}: ממוצע ${ltr(meanLabel(group.stats))} · ${distributionLabel(seatDistributions.blocs[group.id])}`;
    y+=draw.block(label,right,y,contentWidth,{size:18,color:MUTED,lineHeight:27});
  }
  y+=12;
  const cardsPerRow=3,cardGap=16,cardWidth=(contentWidth-cardGap*(cardsPerRow-1))/cardsPerRow;
  for(let start=0;start<grouped.other.length;start+=cardsPerRow) {
    const row=grouped.other.slice(start,start+cardsPerRow);
    const rowHeight=Math.max(...row.map(p=>draw.wrap(p.name||p.id,cardWidth-132,{size:20,weight:700}).length*28+102),134);
    row.forEach((party,i)=>{
      const x=right-cardWidth-(cardWidth+cardGap)*i;
      draw.box(x,y,cardWidth,rowHeight-8,'#f5f8fb');draw.logo(logos.get(party.id),x+cardWidth-100,y+13,82,46,party.id);
      draw.block(party.name||party.id,x+cardWidth-114,y+17,cardWidth-132,{size:20,weight:700,color:MUTED,lineHeight:28});
      if(party.hasModelledSupport===false)draw.block('ללא אומדן תמיכה נפרד',x+cardWidth-18,y+rowHeight-46,cardWidth-36,{size:17,color:MUTED,lineHeight:26});
      else {
        draw.text(meanLabel(party),x+cardWidth/2,y+rowHeight-68,{size:22,weight:700,color:MUTED,align:'center',direction:'ltr'});
        draw.text(distributionLabel(seatDistributions.parties[party.id]),x+cardWidth/2,y+rowHeight-34,{size:17,color:MUTED,align:'center'});
      }
    });y+=rowHeight;
  }
  y+=20;
  y+=draw.block('ההגדרות ששימשו לחישוב',right,y,contentWidth,{size:27,weight:700,lineHeight:40})+8;
  settings.forEach((line,index)=>{
    const lines=draw.wrap(line,contentWidth-36,{size:18}),height=lines.length*28+16;
    if(index%2===0)draw.box(PAD,y,contentWidth,height,'#f5f8fb',6);
    draw.block(line,right-18,y+8,contentWidth-36,{size:18,lineHeight:28});y+=height+3;
  });
  y+=24;
  const captions=[
    'מקורות וקרדיט: מדד 120 · מואיז הקטן (LittlePolls) · המדד / שמואל רוזנר · מיכאל גלעד.'+(snapshot.signalNoise?' אות ורעש: יישום עצמאי בהשראת עד120 / אריאל דניאלי.':''),
    'הסיכויים מותנים בסקרים ובהנחות שנבחרו. רוב פירושו 61 מנדטים ומעלה; אין זה אומדן להצלחת משא ומתן להרכבת ממשלה.',
    'רווחי הסמך של 95% מתארים שגיאת מונטה־קרלו בלבד. הם אינם טווח תוצאות הבחירות או מדד לכיול התחזית.',
    'טווח \u20665–95\u2069 הוא הטווח בין אחוזוני 5 ו־95 של תוצאות ההרצות. החציון הוא אחוזון 50 התחתון; סכום החציונים אינו חייב להיות 120.',
    'הקוביות מעוגלות בשיטת השאריות הגדולות ל־100; ההסתברויות המספריות אינן מעוגלות לקוביות. תוחלת מפלגה כוללת גם הרצות שבהן לא עברה.',
    'בכל הרצה מחושבים אחוז החסימה (3.25%), הסכמי העודפים ובאדר–עופר. נתוני הסקרים אינם מתעדכנים אוטומטית.'
  ];
  for(const caption of captions)y+=draw.block(caption,right,y,contentWidth,{size:17,color:MUTED,lineHeight:26})+6;
  y+=20;
  draw.text('ויקטור רינה בן דוד',right,y,{size:18,weight:700});
  draw.text('victorchina-ops.github.io/israel-election-simulator/',PAD,y,{size:17,color:MUTED,align:'left',direction:'ltr'});
  const cssHeight=Math.ceil(y+56);
  canvas.width=WIDTH*SCALE;canvas.height=cssHeight*SCALE;
  ctx.scale(SCALE,SCALE);ctx.fillStyle='#fff';ctx.fillRect(0,0,WIDTH,cssHeight);
  for(const operation of draw.operations)operation();
  const blob=await new Promise((resolve,reject)=>canvas.toBlob(value=>value?resolve(value):reject(new Error('יצוא הסיכום לתמונה נכשל.')),'image/png'));
  return {blob,width:canvas.width,height:canvas.height,metadata:{cssWidth:WIDTH,cssHeight,scale:SCALE,asOf:config.asOf,iterations:snapshot.iterations,seed:config.seed,config,
    waffleCounts:Object.fromEntries(outcomes.map(row=>[row.id,row.squares])),waffleCells:cells,outcomes,seatDistributions,reportingGroups,partyIds:parties.map(p=>p.id),
    missingLogoIds:parties.filter(p=>!logos.get(p.id)).map(p=>p.id),settings,textRecords:draw.textRecords}};
}

export async function downloadSummaryFigure(options) {
  const built=await buildSummaryFigure(options),url=URL.createObjectURL(built.blob),link=document.createElement('a');
  const safe=value=>String(value??'scenario').replace(/[^a-zA-Z0-9._-]/g,'-');
  const filename=`election-summary-${safe(built.metadata.asOf)}-${safe(built.metadata.seed)}.png`;
  try {link.href=url;link.download=filename;document.body.appendChild(link);link.click();}
  finally {link.remove();setTimeout(()=>URL.revokeObjectURL(url),1000);}
  return {width:built.width,height:built.height,filename,metadata:built.metadata};
}
