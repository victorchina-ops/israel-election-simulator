import {useEffect,useMemo,useState} from 'react';
import {createSimulation} from './model/simulate.js';

// Share the same cancellable calculation path across the two reference tables.
export function useMethodSimulation(input,config,methodIds,enabled){
 const key=methodIds.join('|');
 const request=useMemo(()=>({input,config,methodIds:key.split('|')}),[input,config,key]);
 const [state,setState]=useState({request:null,results:null,error:'',progress:0});
 useEffect(()=>{
  if(!enabled)return;
  let cancelled=false;setState({request,results:null,error:'',progress:0});
  (async()=>{try{
   const results={},total=request.methodIds.length;
   for(let i=0;i<total;i++){
    const id=request.methodIds[i],job=createSimulation(request.input,{...request.config,weightMode:id});
    while(job.done<request.config.iterations){
     if(cancelled)return;
     job.step(125);setState({request,results:null,error:'',progress:(i+job.done/request.config.iterations)/total});
     await new Promise(resolve=>setTimeout(resolve,0));
    }
    results[id]=job.finish();
   }
   if(!cancelled)setState({request,results,error:'',progress:1});
  }catch(e){if(!cancelled)setState({request,results:null,error:e.message,progress:0});}})();
  return()=>{cancelled=true;};
 },[request,enabled]);
 const current=state.request===request?state:{results:null,error:'',progress:0};
 return {...current,loading:enabled&&!current.results&&!current.error};
}
