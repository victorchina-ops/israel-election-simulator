import React,{useEffect,useMemo,useRef,useState} from 'react';
import {DataComponent,Button,useDataApp} from '../../data-app-public.jsx';
import './bloc-outcomes.css';
import {describeBlocComposition} from './bloc-presets.js';

const TITLE='סיכויי רוב — קואליציה, תיקו ואופוזיציה';
const OUTCOMES=[
  {id:'a',label:'קואליציה נוכחית',color:'#dc454c'},
  {id:'neither',label:'תיקו / ללא רוב',color:'#89939f'},
  {id:'b',label:'אופוזיציה',color:'#2378cf'},
];
const percent=value=>(100*value).toLocaleString('he-IL',{minimumFractionDigits:2,maximumFractionDigits:2})+'%';
const integer=value=>Number(value).toLocaleString('he-IL',{maximumFractionDigits:0});
const SVG_NS='http://www.w3.org/2000/svg';
const sourceIds=['polls','turnout_baseline','model_configuration','weight_presets','calibration','agreements'];

// Visual rounding only: keep exactly 100 equal-area cells. Exact probabilities
// and Wilson intervals below remain untouched by this largest-remainder step.
export function allocateWaffleSquares(probabilities){
  if(!Array.isArray(probabilities)||probabilities.length!==3||probabilities.some(p=>!Number.isFinite(p)||p<0))throw new Error('Invalid waffle probabilities');
  const sum=probabilities.reduce((a,b)=>a+b,0);if(!(sum>0))throw new Error('Empty waffle probabilities');
  const quotas=probabilities.map(p=>100*p/sum),counts=quotas.map(Math.floor);
  const order=quotas.map((q,i)=>({i,remainder:q-counts[i]})).sort((a,b)=>b.remainder-a.remainder||a.i-b.i);
  const remaining=100-counts.reduce((a,b)=>a+b,0);
  for(let i=0;i<remaining;i++)counts[order[i].i]++;
  return counts;
}

// Fill each column before moving left. Geometry is deliberately independent of
// CSS direction: the red coalition is always at the physical right, blue left.
export function waffleCellPosition(index){
  return {column:9-Math.floor(index/10),row:index%10};
}

function inspectResult(result,baseline){
  if(!result||result.iterations<2)return {rows:[],invalid:null};
  const rows=OUTCOMES.map(outcome=>{
    const p=result.probabilities?.[outcome.id],ci=result.probabilityCI?.[outcome.id];
    return {...outcome,probability:p,low:ci?.[0],high:ci?.[1],count:result.counts?.[outcome.id],iterations:result.iterations,
      baselineProbability:baseline?.iterations>1?baseline.probabilities?.[outcome.id]??null:null,
      confidenceLevel:.95,intervalMeaning:'Wilson Monte Carlo sampling error conditional on the model',
      definition:outcome.id==='neither'?'Both defined blocs have fewer than 61 seats':'Defined bloc has at least 61 seats',
      seed:result.config?.seed,asOf:result.config?.asOf,scenario:result.config};
  });
  const invalid=rows.some(r=>![r.probability,r.low,r.high].every(v=>Number.isFinite(v)&&v>=0&&v<=1)||r.low>r.high||r.probability<r.low-1e-12||r.probability>r.high+1e-12)
    ||Math.abs(rows.reduce((s,r)=>s+r.probability,0)-1)>1e-8;
  if(!invalid){const squares=allocateWaffleSquares(rows.map(r=>r.probability));rows.forEach((row,i)=>{row.roundedSquares=squares[i];});}
  return {rows:invalid?[]:rows,invalid:invalid?'תוצאת ההרצה אינה כוללת שלוש הסתברויות ורווחי סמך תקינים.':null};
}
export function OutcomeWaffle({result,compact=false,showLegend=true,showNote=true,className=''}){
  const {rows,invalid}=useMemo(()=>inspectResult(result),[result]);
  if(!rows.length)return <p className="outcome-waffle__empty" role="status">{invalid||'סיכויי הגושים יוצגו לאחר חישוב של שתי הרצות לפחות.'}</p>;
  const squares=rows.flatMap(row=>Array.from({length:row.roundedSquares},()=>row));
  const description=rows.map(row=>row.label+': '+percent(row.probability)).join('. ');
  return <div className={'outcome-waffle'+(compact?' outcome-waffle--compact':'')+(className?' '+className:'')} data-reviewed-rows>
    <svg className="outcome-waffle__grid" viewBox="0 0 220 220" role="img" aria-label={'100 קוביות: קואליציה באדום מימין, אופוזיציה בכחול משמאל וללא רוב באפור ביניהן. '+description}>
      <title>סיכויי רוב מתוך 100</title><desc>{description}. כל קובייה היא נקודת אחוז אחת, בעיגול ל־100 קוביות. ללא רוב פירושו ששני הגושים מתחת ל־61 מנדטים.</desc>
      <g data-waffle-grid="100">
        {squares.map((row,i)=>{const position=waffleCellPosition(i);return <rect key={i} data-waffle-cell={i+1} data-outcome={row.id} x={position.column*22+1} y={position.row*22+1} width="19" height="19" rx="2" fill={row.color}><title>{row.label}: {row.roundedSquares} קוביות; הסתברות {percent(row.probability)}</title></rect>;})}
      </g>
    </svg>
    {showLegend&&<div className="outcome-waffle__legend" aria-label="מקרא והסתברויות מדויקות">{rows.map(row=><span className={'outcome-waffle__outcome outcome-waffle__outcome--'+row.id} key={row.id}><i style={{background:row.color}} aria-hidden="true"/><span>{row.id==='a'?'קואליציה':row.id==='b'?'אופוזיציה':'ללא רוב'}</span><strong dir="ltr">{percent(row.probability)}</strong></span>)}</div>}
    {showNote&&<p className="outcome-waffle__note">כל קובייה ≈ 1% · ללא רוב: אף גוש לא הגיע ל־61</p>}
  </div>;
}

function wrapText(text,maxCharacters){
  const lines=[];let line='';
  for(const word of text.split(' ')){
    if(line&&(line+' '+word).length>maxCharacters){lines.push(line);line=word;}
    else line+=(line?' ':'')+word;
  }
  if(line)lines.push(line);return lines;
}
function saveBlob(blob,filename){
  const url=URL.createObjectURL(blob),anchor=document.createElement('a');
  anchor.href=url;anchor.download=filename;anchor.click();
  setTimeout(()=>URL.revokeObjectURL(url),1000);
}
// The same SVG contains the composition, every interval, legend and assumptions.
// Its exported copy adds a title; no chart schema omits the custom whiskers.
function serializeChart(svg){
  const clone=svg.cloneNode(true),box=svg.viewBox.baseVal,width=box.width;
  const titleLines=wrapText(TITLE,Math.max(24,Math.floor((width-48)/8.5))),offset=20+titleLines.length*26,height=box.height+offset;
  clone.setAttribute('xmlns',SVG_NS);clone.setAttribute('viewBox',`0 0 ${width} ${height}`);
  clone.setAttribute('width',width);clone.setAttribute('height',height);clone.removeAttribute('class');
  const group=document.createElementNS(SVG_NS,'g');group.setAttribute('transform','translate(0 '+offset+')');
  while(clone.firstChild)group.appendChild(clone.firstChild);clone.appendChild(group);
  const background=document.createElementNS(SVG_NS,'rect');
  background.setAttribute('width',width);background.setAttribute('height',height);background.setAttribute('fill','#fff');clone.insertBefore(background,group);
  const heading=document.createElementNS(SVG_NS,'text');
  heading.setAttribute('x',width-24);heading.setAttribute('y','30');heading.setAttribute('direction','rtl');heading.setAttribute('text-anchor','start');
  heading.setAttribute('fill','#172536');heading.setAttribute('font-family','Tahoma, Arial, sans-serif');heading.setAttribute('font-size',width<580?'16':'22');heading.setAttribute('font-weight','700');
  titleLines.forEach((line,i)=>{const part=heading.cloneNode();part.setAttribute('y',30+i*26);part.textContent=line;clone.appendChild(part);});
  return {text:new XMLSerializer().serializeToString(clone),width,height};
}
async function saveChart(svg,format,filename){
  if(document.fonts?.ready)await document.fonts.ready;
  const rendered=serializeChart(svg),blob=new Blob([rendered.text],{type:'image/svg+xml;charset=utf-8'});
  if(format==='svg'){saveBlob(blob,filename+'.svg');return;}
  const url=URL.createObjectURL(blob);
  try{
    const image=new Image();
    await new Promise((resolve,reject)=>{image.onload=resolve;image.onerror=()=>reject(new Error('לא ניתן היה להמיר את התרשים ל־PNG.'));image.src=url;});
    const canvas=document.createElement('canvas');canvas.width=Math.ceil(rendered.width*2);canvas.height=Math.ceil(rendered.height*2);
    const ctx=canvas.getContext('2d');if(!ctx)throw new Error('ציור PNG אינו זמין בדפדפן הזה.');
    ctx.scale(2,2);ctx.fillStyle='#fff';ctx.fillRect(0,0,rendered.width,rendered.height);ctx.drawImage(image,0,0,rendered.width,rendered.height);
    const png=await new Promise(resolve=>canvas.toBlob(resolve,'image/png'));
    if(!png)throw new Error('יצירת קובץ PNG נכשלה.');saveBlob(png,filename+'.png');
  }finally{URL.revokeObjectURL(url);}
}

function OutcomeGraphic({rows,result,input,svgRef,width,hideWaffle=false}){
  const compact=width<580,pad=26,plotWidth=width-2*pad,rowStep=compact?96:78;
  const gridSize=Math.min(240,plotWidth),gridTop=64,gridBottom=gridTop+gridSize,gridLeft=(width-gridSize)/2;
  const gap=compact?3:4,cellSize=(gridSize-9*gap)/10;
  const graphicBottom=hideWaffle?38:gridBottom;
  const firstLabel=graphicBottom+(hideWaffle?66:compact?124:114),firstLine=firstLabel+(compact?46:27);
  const lastLine=firstLine+2*rowStep,axisY=lastLine+27,footerY=axisY+32;
  const lines=[
    'הרכב הגושים: '+describeBlocComposition(result.config,result.parties)+'.',
    'כל ריבוע = נקודת אחוז אחת. הצבעים מעוגלים בשיטת השאריות הגדולות ל־100 ריבועים.',
    'רוב: 61 מנדטים ומעלה. תיקו / ללא רוב: שני הגושים מתחת ל־61; לאו דווקא 60–60.',
    'רווחי 95%: שגיאת מונטה־קרלו מותנית במודל, ולא אי־ודאות התחזית.',
    'בכל הרצה: חסימה 3.25%, הסכמי עודפים ובאדר–עופר.',
  ].flatMap(text=>wrapText(text,Math.max(32,Math.floor(plotWidth/6.1))));
  const height=footerY+lines.length*17+15,x=p=>pad+plotWidth*p;
  const squares=rows.flatMap(row=>Array.from({length:row.roundedSquares},()=>row));
  const mode=result.config?.samplingMode==='fixed'?'אם הסקרים מדויקים':'כולל אפשרות לטעות בסקרים';
  const description=rows.map(r=>`${r.label}: ${percent(r.probability)}, רווח 95% ${percent(r.low)} עד ${percent(r.high)}`).join('. ');
  return <svg ref={svgRef} className="bloc-outcomes__svg" xmlns={SVG_NS} viewBox={`0 0 ${width} ${height}`} width={width} height={height} role="img" aria-label={`${TITLE}. ${description}`} style={{fontFamily:'Tahoma, Arial, sans-serif'}}>
    <title>{TITLE}</title><desc>{description}. רווחי הסמך מתארים שגיאת הרצה בלבד. ללא רוב אינו בהכרח תיקו של 60 מול 60.</desc>
    <rect width={width} height={height} fill="#fff"/>
    <text x={width-pad} y="22" direction="rtl" textAnchor="start" fill="#445268" fontSize={compact?12:14}>{integer(result.iterations)} חזרות · {mode}</text>
    <text x={width-pad} y="42" direction="rtl" textAnchor="start" fill="#667487" fontSize="11">סקרים: {result.config?.asOf??input?.current?.asOf??'—'} · זרע: {result.config?.seed??'—'}</text>
    {!hideWaffle&&<g aria-label="100 ריבועים, קואליציה מימין ואופוזיציה משמאל; כל ריבוע נקודת אחוז" data-waffle-grid="100">
      {squares.map((row,i)=><rect key={i} data-waffle-cell={i+1} data-outcome={row.id}
        x={gridLeft+waffleCellPosition(i).column*(cellSize+gap)} y={gridTop+waffleCellPosition(i).row*(cellSize+gap)}
        width={cellSize} height={cellSize} rx="2" fill={row.color}>
        <title>{row.label}: {row.roundedSquares} ריבועים מתוך 100; הסתברות מדויקת {percent(row.probability)}</title>
      </rect>)}
      {rows.map((row,i)=><g key={row.id}>
        <rect x={width-pad-plotWidth*(i+.5)/3-5} y={gridBottom+16} width="10" height="10" rx="2" fill={row.color}/>
        <text x={width-pad-plotWidth*(i+.5)/3} y={gridBottom+46} textAnchor="middle" direction="rtl" fill="#27364a" fontSize={compact?11:14}>{compact?(i===0?'קואליציה':i===1?'תיקו /':row.label):row.label}</text>
        {compact&&i<2&&<text x={width-pad-plotWidth*(i+.5)/3} y={gridBottom+61} textAnchor="middle" direction="rtl" fill="#27364a" fontSize="11">{i===0?'נוכחית':'ללא רוב'}</text>}
        <text x={width-pad-plotWidth*(i+.5)/3} y={gridBottom+(compact?80:67)} textAnchor="middle" fill="#344359" fontSize="13" fontWeight="700">{row.roundedSquares}%</text>
      </g>)}
    </g>}
    <text x={width-pad} y={graphicBottom+(hideWaffle?32:compact?101:90)} textAnchor="start" direction="rtl" fill="#445268" fontSize={compact?12:14}>{compact?"אומדן מדויק ורווח 95%":"אומדן מדויק · נקודה: אומדן · קו: רווח 95%"}</text>
    <g aria-label="רווחי הסמך של שלוש התוצאות">
      {[0,.25,.5,.75,1].map(tick=><g key={tick}>
        <line x1={x(tick)} x2={x(tick)} y1={firstLine-8} y2={lastLine+8} stroke="#e9edf2" strokeWidth="1"/>
        <text x={x(tick)} y={axisY} textAnchor="middle" fill="#68758a" fontSize="11">{tick*100}%</text>
      </g>)}
      {rows.map((row,i)=>{
        const labelY=firstLabel+i*rowStep,lineY=firstLine+i*rowStep;
        return <g key={row.id} aria-label={`${row.label}: ${percent(row.probability)}, ${percent(row.low)} עד ${percent(row.high)}`}>
          <text x={width-pad} y={labelY} textAnchor="start" direction="rtl" fill="#243449" fontWeight="700" fontSize={compact?13:15}>{row.label}</text>
          <text x={pad} y={labelY+(compact?22:0)} textAnchor="start" direction="ltr" fill="#344359" fontSize="13">{percent(row.probability)} · [{percent(row.low)} – {percent(row.high)}]</text>
          <line x1={x(0)} x2={x(1)} y1={lineY} y2={lineY} stroke="#eef1f5" strokeWidth="3"/>
          <line x1={x(row.low)} x2={x(row.high)} y1={lineY} y2={lineY} stroke={row.color} strokeWidth="4"/>
          {[row.low,row.high].map((value,k)=><line key={k} x1={x(value)} x2={x(value)} y1={lineY-6} y2={lineY+6} stroke={row.color} strokeWidth="2"/>)}
          <circle cx={x(row.probability)} cy={lineY} r="5" fill={row.color} stroke="#fff" strokeWidth="1.5"/>
        </g>;
      })}
    </g>
    {lines.map((line,i)=><text key={i} x={width-pad} y={footerY+i*17} textAnchor="start" direction="rtl" fill="#627084" fontSize="11.5">{line}</text>)}
  </svg>;
}

export function BlocOutcomes({result,baseline,busy=false,error,input,config,hideWaffle=false}){
  const {queries}=useDataApp(),host=useRef(null),svg=useRef(null);
  const [width,setWidth]=useState(840),[exporting,setExporting]=useState(false),[exportError,setExportError]=useState('');
  const {rows,invalid}=useMemo(()=>inspectResult(result,baseline),[result,baseline]);
  const ids=sourceIds.filter(id=>queries?.[id]);
  const sourceRowsByQuery=Object.fromEntries(ids.map(id=>[id,queries[id].rows]));
  useEffect(()=>{
    const element=host.current;if(!element)return;
    const update=()=>{const w=Math.round(element.getBoundingClientRect().width);if(w>0)setWidth(Math.max(280,w));};
    update();if(typeof ResizeObserver==='undefined')return;
    const observer=new ResizeObserver(update);observer.observe(element);return()=>observer.disconnect();
  },[busy,Boolean(result)]);
  async function onExport(format){
    if(!svg.current||!rows.length)return;
    setExporting(true);setExportError('');
    try{await saveChart(svg.current,format,`coalition-outcomes-${result.config?.asOf??'scenario'}-${result.config?.seed??'seed'}`);}
    catch(e){setExportError(e.message||'ייצוא התרשים נכשל.');}
    finally{setExporting(false);}
  }
  const scenario=result?.config??config;
  const description='100 ריבועים של נקודת אחוז כל אחד, בעיגול בשיטת השאריות הגדולות. ההסתברויות ורווחי הסמך המוצגים בנפרד אינם מעוגלים לריבועים. שלוש תוצאות זרות ומשלימות של הסימולציה לפי שיוך הרשימות לגושים: הקואליציה הנוכחית (a), האופוזיציה (b), או ששניהם מתחת ל־61. רווחי Wilson של 95% מכמתים שגיאת מונטה־קרלו מותנית בהנחות, לא כיול של אי־ודאות התחזית. ההסתברויות אינן סיכויי הצלחה במשא ומתן. תרחיש נוכחי: '+JSON.stringify(scenario??{});
  return <DataComponent id="e-bloc-outcomes" title={TITLE} kind="custom" variant="card" className="bloc-outcomes" queryId="polls" queryIds={ids} sourceRows={queries?.polls?.rows??[]} sourceRowsByQuery={sourceRowsByQuery} displayRows={rows} description={description} loading={busy} loadingError={error||invalid||undefined} loadingHeight={500}
    >
    <div className="bloc-outcomes__exports" role="group" aria-label="ייצוא התרשים עם רווחי הסמך" data-block-no-drag><Button disabled={busy||exporting||!rows.length||Boolean(error)} onClick={()=>onExport('svg')}>SVG עם רווחי סמך</Button><Button disabled={busy||exporting||!rows.length||Boolean(error)} onClick={()=>onExport('png')}>PNG עם רווחי סמך</Button></div>
    <div ref={host} className="bloc-outcomes__body" data-reviewed-rows>
      {rows.length?<OutcomeGraphic rows={rows} result={result} input={input} svgRef={svg} width={width} hideWaffle={hideWaffle}/>:<p className="bloc-outcomes__empty" role="status">להערכת סיכויים ורווחי סמך יש להריץ יותר מהדמיה אחת. מומלץ לבחור אלפי חזרות; תוצאה יחידה אינה אומדן סיכוי.</p>}
    </div>
    {exportError&&<p className="bloc-outcomes__error" role="alert">{exportError}</p>}
  </DataComponent>;
}
export default BlocOutcomes;
