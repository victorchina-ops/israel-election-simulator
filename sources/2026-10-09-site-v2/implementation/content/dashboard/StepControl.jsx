import React,{useEffect,useId,useRef,useState} from 'react';
import {Slider as PublicSlider} from '../../data-app-public.jsx';
import './step-control.css';

function decimalPlaces(value){
  const [coefficient,exponent='0']=String(value).toLowerCase().split('e');
  return Math.max(0,(coefficient.split('.')[1]?.length??0)-Number(exponent));
}
function cleanNumber(value,precision){return Number(value.toFixed(Math.min(12,Math.max(0,precision))));}
function textNumber(value){return Number(value.toPrecision(12)).toString();}
function parseDraft(text){
  const normalized=text.trim().replace(/−/g,'-');
  if(!/^[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:e[+-]?\d+)?$/i.test(normalized))return null;
  const value=Number(normalized);return Number.isFinite(value)?value:null;
}

/** Drop-in single-value Slider wrapper; displayScale affects entry/presentation only. */
export function StepControl({label='ערך',min=0,max=100,step=1,value=min,onChange,disabled=false,
  formatValue,labelPlacement='outside',displayScale=1,suffix='',className='',...sliderProps}){
  const scale=Number.isFinite(displayScale)&&displayScale>0?displayScale:1;
  const first=Number.isFinite(min)?min:0,last=Number.isFinite(max)?max:100;
  const lower=Math.min(first,last),upper=Math.max(first,last),increment=Number.isFinite(step)&&step>0?step:1;
  const clamp=number=>Math.min(upper,Math.max(lower,number));
  const current=clamp(Number.isFinite(value)?value:lower);
  const precision=Math.min(12,Math.max(decimalPlaces(increment),decimalPlaces(lower),decimalPlaces(upper)));
  const printable=number=>textNumber(number*scale);
  const presented=number=>formatValue?formatValue(number):printable(number)+suffix;
  const accessibleLabel=typeof label==='string'?label:'ערך המחוון';
  const inputId='step-control-'+useId().replace(/:/g,''),errorId=inputId+'-error';
  const [draft,setDraft]=useState(()=>printable(current)),[invalid,setInvalid]=useState(false);
  const draftRef=useRef(draft),dirty=useRef(false),currentRef=useRef(current);
  function writeDraft(text){draftRef.current=text;setDraft(text);}
  useEffect(()=>{
    currentRef.current=current;dirty.current=false;writeDraft(printable(current));setInvalid(false);
  },[current,scale,increment,lower,upper]);

  function publish(raw){
    const next=clamp(raw);currentRef.current=next;dirty.current=false;
    writeDraft(printable(next));setInvalid(false);
    if(next!==current)onChange?.(next);
  }
  function commit(){
    if(disabled||!dirty.current)return;
    const parsed=parseDraft(draftRef.current);
    if(parsed===null){dirty.current=false;writeDraft(printable(currentRef.current));setInvalid(true);return;}
    // Text may temporarily be empty, '-' or an unfinished exponent; only a
    // completed Enter/blur commit reaches the model. Snap committed text to step.
    const raw=parsed/scale,bounded=clamp(raw);
    const snapped=lower+Math.round((bounded-lower)/increment)*increment;
    publish(cleanNumber(clamp(snapped),precision));
  }
  function move(direction){
    if(disabled)return;
    const parsed=dirty.current?parseDraft(draftRef.current):null;
    const start=parsed===null?currentRef.current:clamp(parsed/scale);
    // Preserve precise source baselines: one click adds exactly one model step,
    // with decimal cleanup, rather than moving to a different anchored grid.
    const digits=Math.min(12,Math.max(precision,decimalPlaces(start)));
    publish(cleanNumber(clamp(start+direction*increment),digits));
  }
  function onKeyDown(event){
    if(event.key==='ArrowUp'||event.key==='ArrowDown'){
      event.preventDefault();move(event.key==='ArrowUp'?1:-1);
    }else if(event.key==='Enter'){event.preventDefault();commit();}
    else if(event.key==='Escape'){
      event.preventDefault();dirty.current=false;writeDraft(printable(currentRef.current));setInvalid(false);
    }
  }
  const displayedStep=textNumber(increment*scale)+suffix;
  const draftNumber=dirty.current?parseDraft(draft):null;
  const buttonBase=draftNumber===null?current:clamp(draftNumber/scale);
  return <div className={['step-control',className].filter(Boolean).join(' ')} data-step-control data-disabled={disabled||undefined}>
    <PublicSlider {...sliderProps} label={label} min={lower} max={upper} step={increment} value={current} disabled={disabled}
      labelPlacement={labelPlacement} formatValue={presented} onChange={next=>{if(Number.isFinite(next)&&!disabled)publish(clamp(next));}}/>
    <div className="step-control__entry" role="group" aria-label={'שינוי מדויק של '+accessibleLabel}>
      <div className="step-control__field">
        <input id={inputId} className="step-control__input" type="text" inputMode="decimal" role="spinbutton" dir="ltr"
          aria-label={accessibleLabel+' — הזנת ערך'+(suffix?' ('+suffix+')':'')} aria-valuemin={lower*scale} aria-valuemax={upper*scale}
          aria-valuenow={current*scale} aria-valuetext={String(presented(current))} aria-invalid={invalid||undefined}
          aria-describedby={invalid?errorId:undefined} value={draft} disabled={disabled} autoComplete="off" spellCheck={false}
          onChange={event=>{dirty.current=true;writeDraft(event.target.value);setInvalid(false);}}
          onBlur={commit} onKeyDown={onKeyDown}/>
        {suffix&&<span className="step-control__suffix" aria-hidden="true">{suffix}</span>}
      </div>
      <div className="step-control__buttons">
        <button type="button" className="step-control__arrow" disabled={disabled||buttonBase>=upper}
          aria-label={'הגדלת '+accessibleLabel+' ב־'+displayedStep} title={'הגדלה ב־'+displayedStep}
          onMouseDown={event=>event.preventDefault()} onClick={()=>move(1)}>▲</button>
        <button type="button" className="step-control__arrow" disabled={disabled||buttonBase<=lower}
          aria-label={'הקטנת '+accessibleLabel+' ב־'+displayedStep} title={'הקטנה ב־'+displayedStep}
          onMouseDown={event=>event.preventDefault()} onClick={()=>move(-1)}>▼</button>
      </div>
    </div>
    {invalid&&<span id={errorId} className="step-control__error" role="status">יש להזין מספר; הערך הקודם נשמר.</span>}
  </div>;
}
export default StepControl;
