import {createSimulation,defaultConfig} from "./model/simulate.js";
let input=null,currentId=0;
self.onmessage=async({data})=>{
 if(data.type==="init"){input=data.input;return;}
 if(data.type!=="run"||!input)return;
 const id=data.id;currentId=id;
 try{
  const defaults=defaultConfig(input),c=data.config;
  const base={...c,turnout:defaults.turnout,externalMultiplier:1,blocMultipliers:defaults.blocMultipliers};
  const same=JSON.stringify(c.turnout)===JSON.stringify(base.turnout)&&c.externalMultiplier===1&&Object.values(c.blocMultipliers).every(v=>v===1);
  const configs=same?[c]:[c,base],results=[];
  for(let k=0;k<configs.length;k++){
   const job=createSimulation(input,configs[k]);
   while(job.done<configs[k].iterations){
    if(id!==currentId)return;
    const progress=job.step(500);
    self.postMessage({type:"progress",id,done:k*c.iterations+progress.done,total:configs.length*c.iterations});
    await new Promise(resolve=>setTimeout(resolve,0));
   }
   results.push(job.finish());
  }
  if(id===currentId)self.postMessage({type:"result",id,result:results[0],baseline:results[1]||results[0]});
 }catch(e){if(id===currentId)self.postMessage({type:"error",id,message:e.message});}
};